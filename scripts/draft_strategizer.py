#!/usr/bin/env python3
################################################################################
#
# Script Name: draft_strategizer.py
# ----------------
# Provides tools for optimizing fantasy football draft strategy, including VBD calculations and mock draft simulations.
#
# @author Nicholas Wilde, 0xb299a622
# @date 2025-08-20
# @version 0.1.0
#
################################################################################

import os
import pandas as pd
import yaml
import sys

# Add src to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from fantasy_ai.errors import (
    FileOperationError,
    DataValidationError,
    ConfigurationError,
    wrap_exception
)
from scripts.utils import load_config
from fantasy_ai.utils.logging import setup_logging, get_logger

# Set up logging
setup_logging(level='INFO', format_type='console', log_file='logs/draft_strategizer.log')
logger = get_logger(__name__)

# --- Configuration and Data Paths ---
CONFIG_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', 'config.yaml'
)
PLAYER_ADP_PATH = 'data/player_adp.csv'
PLAYER_PROJECTIONS_PATH = 'data/player_projections.csv'

def load_config() -> dict:
    """
    Loads configuration from the config.yaml file with proper error handling.
    
    Returns:
        Configuration dictionary.
        
    Raises:
        ConfigurationError: If config file cannot be read or parsed.
        FileOperationError: If config file cannot be accessed.
    """
    try:
        logger.debug(f"Loading configuration from {CONFIG_FILE}")
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        if not isinstance(config, dict):
            raise ConfigurationError(
                "Configuration file does not contain a valid dictionary",
                config_file=CONFIG_FILE
            )
        
        logger.info("Configuration loaded successfully")
        return config
        
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
    except PermissionError as e:
        raise FileOperationError(
            f"Permission denied reading configuration file: {CONFIG_FILE}",
            file_path=CONFIG_FILE,
            operation="read",
            original_error=e
        )
    except Exception as e:
        raise wrap_exception(
            e, ConfigurationError,
            f"Failed to load configuration from {CONFIG_FILE}",
            config_file=CONFIG_FILE
        )


CONFIG = load_config()

def load_player_data(adp_path: str, projections_path: str) -> pd.DataFrame:
    """
    Loads player ADP and projected points data with error handling.
    Generates dummy data if files are not found or are empty.
    
    Args:
        adp_path: Path to player ADP CSV file.
        projections_path: Path to player projections CSV file.
        
    Returns:
        DataFrame with combined player data.
        
    Raises:
        FileOperationError: If files cannot be read.
        DataValidationError: If files are malformed.
    """
    logger.info(f"Loading player data from {adp_path} and {projections_path}...")
    try:
        adp_df = pd.read_csv(adp_path, low_memory=False)
    except (FileNotFoundError, pd.errors.EmptyDataError, pd.errors.ParserError) as e:
        logger.warning(f"Could not load {adp_path}: {e}. Generating dummy ADP data.")
        adp_df = pd.DataFrame({
            'full_name': [f'Player {i}' for i in range(1, 101)],
            'position': ['QB', 'RB', 'WR', 'TE'] * 25,
            'adp': range(1, 101)
        })

    try:
        projections_df = pd.read_csv(projections_path, low_memory=False)
    except (FileNotFoundError, pd.errors.EmptyDataError, pd.errors.ParserError) as e:
        logger.warning(f"Could not load {projections_path}: {e}. Generating dummy projections data.")
        projections_df = pd.DataFrame({
            'full_name': [f'Player {i}' for i in range(1, 101)],
            'position': ['QB', 'RB', 'WR', 'TE'] * 25,
            'projected_points': [i * 2.5 for i in range(100, 0, -1)]
        })

    # Merge dataframes
    player_data = pd.merge(adp_df, projections_df, on='full_name', how='outer')

    # Rename position_x to position and drop position_y
    if 'position_x' in player_data.columns:
        player_data.rename(columns={'position_x': 'position'}, inplace=True)
    if 'position_y' in player_data.columns:
        player_data.drop(columns=['position_y'], inplace=True)

    # Fill NaNs. For 'position', fill with an empty string, otherwise fill with 0.
    if 'position' in player_data.columns:
        player_data['position'].fillna('', inplace=True)
    player_data.fillna(0, inplace=True)
    
    if player_data.empty:
        raise DataValidationError("Combined player data is empty.", field_name="player_data")

    logger.info(f"Successfully loaded and combined {len(player_data)} player records.")
    return player_data


def calculate_vbd(player_data: pd.DataFrame, roster_settings: dict, scoring_settings: dict) -> pd.DataFrame:
    """
    Calculates Value-Based Drafting (VBD) scores for players.
    
    Args:
        player_data: DataFrame with player data including 'position' and 'projected_points'.
        roster_settings: Dictionary of roster settings from config.
        scoring_settings: Dictionary of scoring settings from config.
        
    Returns:
        DataFrame with an added 'vbd' column.
        
    Raises:
        DataValidationError: If input DataFrame is empty or missing required columns.
    """
    logger.info("Calculating VBD scores...")
    if player_data.empty:
        raise DataValidationError("Player data for VBD calculation is empty.", field_name="player_data")

    required_cols = ['position', 'projected_points']
    missing_cols = [col for col in required_cols if col not in player_data.columns]
    if missing_cols:
        raise DataValidationError(
            f"Missing required columns for VBD calculation: {missing_cols}",
            field_name="player_data_columns",
            expected_type=f"columns: {required_cols}",
            actual_value=f"missing: {missing_cols}"
        )

    core_positions = ['QB', 'RB', 'WR', 'TE']
    
    total_starters_per_position = {
        pos: roster_settings.get(pos, 0) * CONFIG.get('league_settings', {}).get('number_of_teams', 12) for pos in core_positions
    }
    
    replacement_level_count = {
        'QB': total_starters_per_position['QB'],
        'RB': total_starters_per_position['RB'] + CONFIG.get('league_settings', {}).get('number_of_teams', 12) * 1.5,
        'WR': total_starters_per_position['WR'] + CONFIG.get('league_settings', {}).get('number_of_teams', 12) * 1.5,
        'TE': total_starters_per_position['TE'] + CONFIG.get('league_settings', {}).get('number_of_teams', 12) * 0.5,
    }

    player_data['vbd'] = 0.0 # Initialize VBD column

    for position in core_positions:
        position_players = player_data[player_data['position'] == position].sort_values(by='projected_points', ascending=False)
        
        if not position_players.empty:
            rl_index = min(int(replacement_level_count.get(position, 0)) - 1, len(position_players) - 1)
            
            if rl_index >= 0:
                replacement_level_points = position_players.iloc[rl_index]['projected_points']
                player_data.loc[player_data['position'] == position, 'vbd'] = \
                    player_data['projected_points'] - replacement_level_points
            else:
                player_data.loc[player_data['position'] == position, 'vbd'] = player_data['projected_points']
        else:
            player_data.loc[player_data['position'] == position, 'vbd'] = 0.0

    for position in ['K', 'D/ST']:
        position_players = player_data[player_data['position'] == position].sort_values(by='projected_points', ascending=False)
        if not position_players.empty:
            num_starters_pos = roster_settings.get(position, 0) * CONFIG.get('league_settings', {}).get('number_of_teams', 12)
            rl_index = min(num_starters_pos - 1, len(position_players) - 1)
            
            if rl_index >= 0:
                replacement_level_points = position_players.iloc[rl_index]['projected_points']
                player_data.loc[player_data['position'] == position, 'vbd'] = \
                    player_data['projected_points'] - replacement_level_points
            else:
                player_data.loc[player_data['position'] == position, 'vbd'] = player_data['projected_points']
        else:
            player_data.loc[player_data['position'] == position, 'vbd'] = 0.0
        
    logger.info("VBD scores calculated successfully.")
    return player_data


def get_team_needs(my_team: dict, roster_settings: dict) -> dict:
    """
    Determines the current positional needs of the user's team.
    
    Args:
        my_team: Dictionary representing the user's current team roster.
        roster_settings: Dictionary of roster settings from config.
        
    Returns:
        Dictionary with positional needs.
    """
    needs = {}
    if not isinstance(roster_settings, dict) or not roster_settings:
        logger.warning("Invalid or empty roster_settings provided for get_team_needs.")
        return needs

    for pos, count in roster_settings.items():
        if pos in my_team and len(my_team[pos]) < count:
            needs[pos] = count - len(my_team[pos])
    return needs


def get_best_available_player(available_players: pd.DataFrame, my_team: dict, roster_settings: dict) -> pd.Series:
    """
    Suggests the best available player based on VBD and current team needs.
    
    Args:
        available_players: DataFrame of players not yet drafted.
        my_team: Dictionary representing the user's current team roster.
        roster_settings: Dictionary of roster settings from config.
        
    Returns:
        Pandas Series representing the best available player, or None if no players are available.
    """
    if available_players.empty:
        logger.info("No available players left to suggest.")
        return None

    current_needs = get_team_needs(my_team, roster_settings)

    priority_order = [
        'QB', 'RB', 'WR', 'TE', 
        'RB/WR', 'WR/TE', 
        'K', 'D/ST', 
        'DP', 
        'BE'
    ]

    for pos_type in priority_order:
        if pos_type in current_needs and current_needs[pos_type] > 0:
            eligible_players = pd.DataFrame()
            if pos_type in ['QB', 'RB', 'WR', 'TE', 'K', 'D/ST', 'DP']:
                eligible_players = available_players[available_players['position'] == pos_type]
            elif pos_type == 'RB/WR':
                eligible_players = available_players[available_players['position'].isin(['RB', 'WR'])]
            elif pos_type == 'WR/TE':
                eligible_players = available_players[available_players['position'].isin(['WR', 'TE'])]
            elif pos_type == 'BE':
                eligible_players = available_players
            
            if not eligible_players.empty:
                eligible_players = eligible_players.sort_values(by='vbd', ascending=False)
                return eligible_players.iloc[0]
    
    if not available_players.empty:
        return available_players.sort_values(by='vbd', ascending=False).iloc[0]
    
    return None


def display_my_team(my_team: dict) -> None:
    """
    Displays the current roster of the user's team.
    
    Args:
        my_team: Dictionary representing the user's current team roster.
    """
    print("\n--- Your Current Roster ---")
    for pos, players in my_team.items():
        if players:
            print(f"{pos}: {', '.join(players)}")
        else:
            print(f"{pos}: (Empty)")
    print("---------------------------")


def live_draft_assistant() -> int:
    """
    Simulates a live draft and provides draft recommendations.
    
    Returns:
        Exit code (0 for success, 1 for error).
    """
    logger.info("Starting Live Draft Assistant.")
    print("\n--- Starting Live Draft Assistant ---")
    
    try:
        player_data = load_player_data(PLAYER_ADP_PATH, PLAYER_PROJECTIONS_PATH)
        player_data = calculate_vbd(player_data, CONFIG.get('roster_settings', {}), CONFIG.get('scoring_rules', {}))
    except (FileOperationError, DataValidationError, ConfigurationError) as e:
        logger.error(f"Draft assistant setup error: {e.get_detailed_message()}")
        print(f"\n❌ Error setting up draft assistant: {e}")
        return 1
    except Exception as e:
        logger.critical(f"An unhandled critical error occurred during draft assistant setup: {e}", exc_info=True)
        print(f"\n❌ An unexpected critical error occurred during setup: {e}")
        print("Please check the log file for more details.")
        return 1

    available_players = player_data.copy()
    roster_settings = CONFIG.get('roster_settings', {})
    my_team = {pos: [] for pos in roster_settings}
    
    flex_map = {
        'RB/WR': ['RB', 'WR'],
        'WR/TE': ['WR', 'TE']
    }

    total_roster_spots = sum(roster_settings.values())
    total_teams = CONFIG.get('league_settings', {}).get('number_of_teams', 12)
    total_picks = total_roster_spots * total_teams

    current_pick_number = 1
    my_draft_position = CONFIG.get('draft_position', 7)

    while current_pick_number <= total_picks and not available_players.empty:
        current_round = (current_pick_number - 1) // total_teams + 1
        pick_in_round = (current_pick_number - 1) % total_teams + 1

        is_my_pick = False
        if current_round % 2 != 0: # Odd rounds (forward)
            if pick_in_round == my_draft_position:
                is_my_pick = True
        else: # Even rounds (backward)
            if pick_in_round == (total_teams - my_draft_position + 1):
                is_my_pick = True

        if is_my_pick:
            print(f"\n--- Round {current_round}, Pick {current_pick_number} (YOUR PICK!) ---")
            suggestion = get_best_available_player(available_players, my_team, roster_settings)
            if suggestion is not None:
                print(f"Recommendation: {suggestion['full_name']} ({suggestion['position']}) - VBD: {suggestion['vbd']:.2f}")
                print("Top 5 available players by VBD:")
                print(tabulate(available_players.head(5)[['full_name', 'position', 'vbd']], headers='keys', tablefmt='fancy_grid'))
            else:
                print("No recommendations available. All players drafted or an error occurred.")
            
            player_name_input = input("Enter your pick (full name, or 'exit' to quit): ").strip()
            if player_name_input.lower() in ['exit', 'quit']:
                break
            
            picked_player_df = available_players[available_players['full_name'].str.lower() == player_name_input.lower()]
            if picked_player_df.empty:
                print(f"Player '{player_name_input}' not found or already drafted. Please try again.")
                continue
            picked_player = picked_player_df.iloc[0]

            # Add player to my team
            pos_added = False
            if picked_player['position'] in my_team and len(my_team[picked_player['position']]) < roster_settings.get(picked_player['position'], 0):
                my_team[picked_player['position']].append(picked_player['full_name'])
                pos_added = True
            else:
                for flex_pos, base_positions in flex_map.items():
                    if flex_pos in my_team and picked_player['position'] in base_positions and len(my_team[flex_pos]) < roster_settings.get(flex_pos, 0):
                        my_team[flex_pos].append(picked_player['full_name'])
                        pos_added = True
                        break
            
            if not pos_added and 'BE' in my_team and len(my_team['BE']) < roster_settings.get('BE', 0):
                my_team['BE'].append(picked_player['full_name'])
                pos_added = True
            
            if pos_added:
                available_players = available_players[available_players['full_name'] != picked_player['full_name']] # Remove from available
                print(f"You drafted {picked_player['full_name']} ({picked_player['position']}).")
                display_my_team(my_team)
            else:
                print(f"Could not add {picked_player['full_name']} to your roster. Check roster settings or team capacity.")
                continue

        else:
            print(f"\n--- Round {current_round}, Pick {current_pick_number} (Other Team's Pick) ---")
            player_name_input = input("Enter player drafted by other team (full name, or 'exit' to quit): ").strip()
            if player_name_input.lower() in ['exit', 'quit']:
                break
            
            picked_player_df = available_players[available_players['full_name'].str.lower() == player_name_input.lower()]
            if picked_player_df.empty:
                print(f"Player '{player_name_input}' not found or already drafted. Please try again.")
                continue
            picked_player = picked_player_df.iloc[0]
            available_players = available_players[available_players['full_name'] != picked_player['full_name']] # Remove from available
            print(f"{picked_player['full_name']} ({picked_player['position']}) was drafted.")

        current_pick_number += 1

    print("\n--- Draft Assistant Session Ended ---")
    display_my_team(my_team)
    logger.info(f"Final available players count: {len(available_players)}")
    return 0



def main() -> int:
    """Entry point for the draft strategizer with error handling."""
    try:
        return live_draft_assistant()
    except KeyboardInterrupt:
        logger.info("Draft assistant interrupted by user.")
        print("\nDraft assistant interrupted by user.")
        return 130
    except (FileOperationError, DataValidationError, ConfigurationError) as e:
        logger.error(f"Draft strategizer error: {e.get_detailed_message()}")
        print(f"\n❌ Error during draft strategizer: {e}")
        return 1
    except Exception as e:
        logger.critical(f"An unhandled critical error occurred: {e}", exc_info=True)
        print(f"\n❌ An unexpected critical error occurred: {e}")
        print("Please check the log file for more details.")
        return 1


if __name__ == "__main__":
    sys.exit(main())