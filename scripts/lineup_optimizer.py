#!/usr/bin/env python3
################################################################################
#
# Script Name: lineup_optimizer.py
# ----------------
# Generates an optimal fantasy football lineup based on projected points and roster settings.
#
# @author Nicholas Wilde, 0xb299a622
# @date 23 08 2025
# @version 0.2.0
#
################################################################################

import os
import pandas as pd
import yaml
from tabulate import tabulate
from pulp import LpProblem, LpMaximize, LpVariable, LpBinary, lpSum, LpStatus, value
import re # Added import for regex
import sys

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from fantasy_ai.errors import (
    FileOperationError,
    DataValidationError,
    ConfigurationError,
    wrap_exception
)
from fantasy_ai.utils.logging import setup_logging, get_logger

# Set up logging
setup_logging(level='INFO', format_type='console', log_file='logs/lineup_optimizer.log')
logger = get_logger(__name__)

# Define file paths
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_FILE = os.path.join(PROJECT_ROOT, 'config.yaml')
PLAYER_PROJECTIONS_PATH = os.path.join(PROJECT_ROOT, 'data', 'player_projections.csv')
MY_TEAM_FILE = os.path.join(PROJECT_ROOT, 'data', 'my_team.md')

def load_config() -> dict:
    """Loads the configuration from config.yaml."""
    try:
        with open(CONFIG_FILE, 'r') as f:
            return yaml.safe_load(f)
    except FileNotFoundError as e:
        raise ConfigurationError(
            f"Configuration file not found: {CONFIG_FILE}. Please run 'task init' first.",
            config_file=CONFIG_FILE,
            original_error=e
        )
    except yaml.YAMLError as e:
        raise ConfigurationError(
            f"Invalid YAML in configuration file: {CONFIG_FILE}",
            config_file=CONFIG_FILE,
            original_error=e
        )
    except Exception as e:
        raise wrap_exception(
            e, ConfigurationError,
            f"Failed to load configuration from {CONFIG_FILE}",
            config_file=CONFIG_FILE
        )

CONFIG = load_config()

def get_my_team_roster(file_path: str) -> list:
    """Reads the my_team.md file (Markdown table format) and extracts player names."""
    try:
        with open(file_path, 'r') as f:
            lines = f.readlines()
            # Data rows start from line 6 (index 5) after comment, title, empty line, header, separator
            if len(lines) > 5:
                players = []
                for line in lines[5:]:
                    line = line.strip()
                    # Check if it's a valid table data row (starts and ends with '|', contains multiple '|')
                    if line.startswith('|') and line.endswith('|') and '|' in line[1:-1]:
                        parts = [p.strip() for p in line.split('|')]
                        # Player name is in the second column (index 1 after split)
                        if len(parts) > 1: 
                            player_name = parts[1]
                            if player_name: # Ensure it's not empty
                                players.append(player_name)
                logger.info(f"Players extracted from my_team.md: {players}")
                return players
            else:
                raise DataValidationError("my_team.md is not in the expected format.", file_path=file_path)
    except FileNotFoundError as e:
        raise FileOperationError(f"my_team.md not found at {file_path}", file_path=file_path, original_error=e)
    except Exception as e:
        raise wrap_exception(e, FileOperationError, f"Failed to read my_team.md from {file_path}", file_path=file_path)

def normalize_player_name(name: str) -> str:
    """Normalizes player names to match the format in player_projections.csv (e.g., 'Patrick Mahomes' to 'P.Mahomes')."""
    # This is a simplified normalization. More robust normalization might be needed.
    # For now, it tries to match common variations.
    if isinstance(name, str):
        # Remove Jr., Sr., III, etc.
        name = re.sub(r'\s(Jr\.|Sr\.|III|II|IV|V)$', '', name, flags=re.IGNORECASE)
        # Remove periods from initials (e.g., P. Mahomes -> P Mahomes)
        name = name.replace('.', '')
        # Remove extra spaces
        name = re.sub(r'\s+', ' ', name).strip()
    return name

def optimize_lineup():
    logger.info("Loading data for lineup optimization...")
    
    # Load roster settings
    roster_settings = CONFIG.get('roster_settings', {})
    logger.info(f"Roster Settings from config.yaml: {roster_settings}")
    if not roster_settings:
        raise ConfigurationError("Roster settings not found in config.yaml.", config_key="roster_settings")

    # Load player projections
    try:
        projections_df = pd.read_csv(PLAYER_PROJECTIONS_PATH)
    except FileNotFoundError as e:
        raise FileOperationError(f"{PLAYER_PROJECTIONS_PATH} not found. Please run 'task download_player_data' first.", file_path=PLAYER_PROJECTIONS_PATH, original_error=e)
    except pd.errors.EmptyDataError as e:
        raise DataValidationError(f"{PLAYER_PROJECTIONS_PATH} is empty.", file_path=PLAYER_PROJECTIONS_PATH, original_error=e)
    except pd.errors.ParserError as e:
        raise DataValidationError(f"Could not parse {PLAYER_PROJECTIONS_PATH}.", file_path=PLAYER_PROJECTIONS_PATH, original_error=e)

    # Load my team roster
    my_team_players_raw = get_my_team_roster(MY_TEAM_FILE)
    if not my_team_players_raw:
        raise DataValidationError(f"No players found in {MY_TEAM_FILE}. Please ensure your team roster is correctly set up.", file_path=MY_TEAM_FILE)

    # Normalize player names from my_team.md
    my_team_players_normalized = [normalize_player_name(p) for p in my_team_players_raw]

    # Normalize player names in projections_df for consistent matching
    projections_df['full_name_normalized'] = projections_df['full_name'].apply(normalize_player_name)

    # Filter projections to only include players on my team using normalized names
    my_team_projections = projections_df[projections_df['full_name_normalized'].isin(my_team_players_normalized)].copy()
    my_team_projections = my_team_projections.reset_index(drop=True) # Reset index to avoid non-contiguous issues

    # Add players from my_team_players_raw that are not in projections_df (e.g., DST)
    missing_players = [p for p in my_team_players_normalized if p not in my_team_projections['full_name_normalized'].values]
    if missing_players:
        logger.warning(f"Projections not found for: {missing_players}. Adding with placeholder points.")
        for player_name in missing_players:
            # Attempt to get position from my_team.md if possible, otherwise default
            # This is a simplified way; a more robust solution would parse my_team.md more thoroughly
            position = 'DST' if 'D/ST' in player_name or 'DST' in player_name else 'UNKNOWN'
            # Add a dummy row for the missing player
            my_team_projections = pd.concat([
                my_team_projections,
                pd.DataFrame([{'full_name': player_name, 'position': position, 'projected_points': 0.0, 'full_name_normalized': player_name}])
            ], ignore_index=True)

    logger.info(f"\nMy Team Projections (first 5 rows):\n{my_team_projections.head()}")
    logger.info(f"\nMy Team Projections Info:\n{my_team_projections.info()}")
    logger.info(f"\nPlayer counts by position in My Team Projections:\n{my_team_projections['position'].value_counts()}")

    if my_team_projections.empty:
        raise DataValidationError("No projections found for players on your team. Ensure player names match.")

    # --- Lineup Optimization with PuLP ---
    prob = LpProblem("Fantasy Football Lineup Optimization", LpMaximize)

    # Define position mapping for roster slots
    position_map = {
        'QB': ['QB'],
        'RB': ['RB'],
        'WR': ['WR'],
        'TE': ['TE'],
        'K': ['K'],
        'DST': ['DST'], # Team Defense/Special Teams
        'RB_WR': ['RB', 'WR'], # Flex
        'WR_TE': ['WR', 'TE'], # Flex
        'FLEX': ['RB', 'WR', 'TE'], # General FLEX if present
        'DP': ['DB', 'LB', 'DE', 'DL', 'CB', 'S', 'DT', 'NT'] # Defensive Player Utility
    }

    # Filter out roster settings that are not starting positions (e.g., BE, IR)
    starting_slots = {slot: count for slot, count in roster_settings.items() 
                      if slot not in ['BE', 'IR']}

    # Decision Variables: player_in_slot[(player_index, slot_name)] = 1 if player is selected for that slot
    player_in_slot = LpVariable.dicts("player_in_slot", 
                                      [(i, slot) for i in my_team_projections.index 
                                       for slot in starting_slots.keys()],
                                      0, 1, LpBinary)

    # Objective Function: Maximize total projected points
    prob += lpSum(my_team_projections.loc[i, 'projected_points'] * player_in_slot[(i, slot)] 
                  for i in my_team_projections.index 
                  for slot in starting_slots.keys()), "Total Projected Points"

    # Constraints:

    # 1. Each player can be selected at most once across all starting slots
    for i in my_team_projections.index:
        prob += lpSum(player_in_slot[(i, slot)] for slot in starting_slots.keys()) <= 1, \
                f"Player {my_team_projections.loc[i, 'full_name']} selected at most once"

    # 2. Fill each roster slot with the required number of players
    for slot_name, count in starting_slots.items():
        # Sum of players assigned to this slot must equal the required count
        prob += lpSum(player_in_slot[(i, slot_name)] 
                      for i in my_team_projections.index 
                      if my_team_projections.loc[i, 'position'] in position_map.get(slot_name, [])) == count, \
                f"Fill {slot_name} slots"

    # 3. Player-Position Compatibility: A player can only be assigned to a slot if their actual position is allowed in that slot
    # This is implicitly handled by the sum in constraint 2, but can be made explicit if needed.
    # For example: if player_in_slot[(i, 'QB')] == 1, then my_team_projections.loc[i, 'position'] must be 'QB'
    # This is already covered by the 'if my_team_projections.loc[i, 'position'] in position_map.get(slot_name, [])' part of the sum.

    # Solve the problem
    prob.solve()

    logger.info(f"Optimization Status: {LpStatus[prob.status]}")

    if prob.status == 1: # LpStatus.Optimal
        optimal_lineup_data = []
        total_projected_points = value(prob.objective)

        # Collect selected players and their assigned slots
        for slot_name in starting_slots.keys():
            for i in my_team_projections.index:
                if player_in_slot[(i, slot_name)].varValue == 1:
                    optimal_lineup_data.append({
                        "Slot": slot_name,
                        "Player": my_team_projections.loc[i, 'full_name'],
                        "Position": my_team_projections.loc[i, 'position'],
                        "Projected Points": my_team_projections.loc[i, 'projected_points']
                    })
        
        # Sort for display
        optimal_lineup_df = pd.DataFrame(optimal_lineup_data)
        optimal_lineup_df = optimal_lineup_df.sort_values(by=['Slot', 'Projected Points'], ascending=[True, False])

        print("\n--- Optimal Lineup ---")
        print(tabulate(optimal_lineup_df, headers='keys', tablefmt='fancy_grid'))
        print(f"Total Projected Points: {total_projected_points:.2f}")

    elif prob.status == -1: # LpStatus.Infeasible
        raise DataValidationError("No optimal solution found. The problem is infeasible. Check your roster and league settings.")
    else:
        raise DataValidationError(f"Solver status: {LpStatus[prob.status]}. No optimal solution found.")

def main():
    try:
        optimize_lineup()
        return 0
    except (ConfigurationError, FileOperationError, DataValidationError) as e:
        logger.error(f"Lineup optimization error: {e.get_detailed_message()}")
        print(f"\n❌ Error during lineup optimization: {e}")
        return 1
    except Exception as e:
        logger.critical(f"An unhandled critical error occurred: {e}", exc_info=True)
        print(f"\n❌ An unexpected critical error occurred: {e}")
        print("Please check the log file for more details.")
        return 1

if __name__ == "__main__":
    sys.exit(main())