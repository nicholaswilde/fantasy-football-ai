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

# --- Configuration and Data Paths ---
CONFIG_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', 'config.yaml'
)
PLAYER_ADP_PATH = 'data/player_adp.csv'
PLAYER_PROJECTIONS_PATH = 'data/player_projections.csv'

def load_config():
    """
    Loads configuration from the config.yaml file.
    """
    with open(CONFIG_FILE, 'r') as f:
        return yaml.safe_load(f)

CONFIG = load_config()

def load_player_data(adp_path, projections_path):
    """
    Loads player ADP and projected points data.
    These files are assumed to exist for the purpose of this script's structure.
    """
    print(f"Loading player ADP from {adp_path}...")
    try:
        adp_df = pd.read_csv(adp_path)
    except FileNotFoundError:
        print(f"Warning: {adp_path} not found. Creating dummy ADP data.")
        adp_df = pd.DataFrame({
            'full_name': [f'Player {i}' for i in range(1, 101)],
            'position': ['QB', 'RB', 'WR', 'TE'] * 25,
            'adp': range(1, 101)
        })

    print(f"Loading player projections from {projections_path}...")
    try:
        projections_df = pd.read_csv(projections_path)
    except FileNotFoundError:
        print(f"Warning: {projections_path} not found. Creating dummy projections data.")
        projections_df = pd.DataFrame({
            'full_name': [f'Player {i}' for i in range(1, 101)],
            'position': ['QB', 'RB', 'WR', 'TE'] * 25, # Added position for dummy data
            'projected_points': [i * 2.5 for i in range(100, 0, -1)]
        })

    
    # print(adp_df.columns)
    
    # print(projections_df.columns)

    # Merge dataframes
    player_data = pd.merge(adp_df, projections_df, on='full_name', how='outer')

    # Rename position_x to position and drop position_y
    if 'position_x' in player_data.columns:
        player_data.rename(columns={'position_x': 'position'}, inplace=True)
    if 'position_y' in player_data.columns:
        player_data.drop(columns=['position_y'], inplace=True)

    # print("--- Debug: player_data columns after merge and rename ---")
    # print(player_data.columns)
    # 
    

    # Fill NaNs. For 'position', fill with an empty string, otherwise fill with 0.
    # This line will be executed only if 'position' column exists after merge
    if 'position' in player_data.columns:
        player_data['position'].fillna('', inplace=True)
    player_data.fillna(0, inplace=True)
    return player_data

def calculate_vbd(player_data, roster_settings, scoring_settings):
    """
    Calculates Value-Based Drafting (VBD) scores for players.
    A more robust VBD calculation considering replacement level players for each position
    across the entire league.
    """
    print("Calculating VBD scores...")
    
    # Define core offensive positions for VBD calculation
    core_positions = ['QB', 'RB', 'WR', 'TE']
    
    # Calculate total number of starters for each core position across the league
    total_starters_per_position = {
        pos: roster_settings.get(pos, 0) * CONFIG.get('league_settings', {}).get('number_of_teams', 12) for pos in core_positions
    }
    
    # Determine a reasonable "replacement level" for each position
    # This is often the last drafted player at that position in a typical draft
    # For simplicity, we'll use the total number of starters + a few bench players
    replacement_level_count = {
        'QB': total_starters_per_position['QB'], # Only consider starting QBs for replacement level
        'RB': total_starters_per_position['RB'] + CONFIG.get('league_settings', {}).get('number_of_teams', 12) * 1.5, # 1.5 bench RBs per team
        'WR': total_starters_per_position['WR'] + CONFIG.get('league_settings', {}).get('number_of_teams', 12) * 1.5, # 1.5 bench WRs per team
        'TE': total_starters_per_position['TE'] + CONFIG.get('league_settings', {}).get('number_of_teams', 12) * 0.5, # 0.5 bench TEs per team
    }

    player_data['vbd'] = 0 # Initialize VBD column

    for position in core_positions:
        position_players = player_data[player_data['position'] == position].sort_values(by='projected_points', ascending=False)
        
        if not position_players.empty:
            # Determine the replacement level player for this position
            # Ensure we don't go out of bounds if there aren't enough players
            rl_index = min(int(replacement_level_count.get(position, 0)) - 1, len(position_players) - 1)
            
            if rl_index >= 0:
                replacement_level_points = position_players.iloc[rl_index]['projected_points']
                
                # Calculate VBD for players at this position
                player_data.loc[player_data['position'] == position, 'vbd'] = \
                    player_data['projected_points'] - replacement_level_points
            else:
                # If no replacement level can be determined (e.g., not enough players), VBD is just projected points
                player_data.loc[player_data['position'] == position, 'vbd'] = player_data['projected_points']
        else:
            player_data.loc[player_data['position'] == position, 'vbd'] = 0 # No players, no VBD

    # For K and D/ST, calculate VBD relative to a replacement level
    for position in ['K', 'D/ST']:
        position_players = player_data[player_data['position'] == position].sort_values(by='projected_points', ascending=False)
        if not position_players.empty:
            # For K and D/ST, replacement level can be much lower, e.g., the 12th or 15th best
            # We'll use the number of starters for that position across the league as replacement level
            num_starters_pos = roster_settings.get(position, 0) * CONFIG.get('league_settings', {}).get('number_of_teams', 12)
            rl_index = min(num_starters_pos - 1, len(position_players) - 1)
            
            if rl_index >= 0:
                replacement_level_points = position_players.iloc[rl_index]['projected_points']
                player_data.loc[player_data['position'] == position, 'vbd'] = \
                    player_data['projected_points'] - replacement_level_points
            else:
                player_data.loc[player_data['position'] == position, 'vbd'] = player_data['projected_points']
        else:
            player_data.loc[player_data['position'] == position, 'vbd'] = 0
        
    return player_data


def suggest_draft_picks(player_data, league_settings):
    """
    Suggests optimal draft picks based on VBD, ADP, and roster needs.
    This simulation aims for a more realistic draft strategy by prioritizing roster spots.
    """
    my_team = {pos: [] for pos in CONFIG.get('roster_settings', {})}
    available_players = player_data.copy()
    draft_order = [] # To simulate picks

    # Define the order of roster spots to fill
    # Prioritize starting positions, then flex, then bench
    roster_fill_order = [
        'QB', 'RB', 'RB', 'WR', 'WR', 'TE', # Primary starters
        'RB/WR', 'WR/TE', # Flex spots
        'K', 'D/ST', # K and D/ST often drafted later
        'DP', 'DP', # DP spots
        'BE', 'BE', 'BE', 'BE', 'BE', 'BE', 'BE' # Bench spots
    ]

    # Filter out positions that are not in roster_settings (e.g., if DP is 0)
    roster_fill_order = [pos for pos in roster_fill_order if CONFIG.get('roster_settings', {}).get(pos, 0) > 0]

    # Ensure we don't try to fill more spots than available in roster_settings
    actual_roster_fill_order = []
    temp_roster_counts = {pos: 0 for pos in CONFIG.get('roster_settings', {})}
    for pos in roster_fill_order:
        if temp_roster_counts.get(pos, 0) < CONFIG.get('roster_settings', {}).get(pos, 0):
            actual_roster_fill_order.append(pos)
            temp_roster_counts[pos] += 1

    num_rounds = len(actual_roster_fill_order) # Each team fills all spots

    for round_num in range(1, num_rounds + 1):
        # Determine pick number for this round (snake draft)
        if round_num % 2 != 0: # Odd rounds (forward)
            my_pick_in_round = CONFIG.get('draft_position', 7)
        else: # Even rounds (backward)
            my_pick_in_round = (CONFIG.get('league_settings', {}).get('number_of_teams', 12) - CONFIG.get('draft_position', 7) + 1)

        # Simulate other teams' picks (remove players by ADP up to my pick)
        num_picks_before_me = (my_pick_in_round - 1) + (CONFIG.get('league_settings', {}).get('number_of_teams', 12) * (round_num - 1))
        if num_picks_before_me > 0:
            drafted_by_others = available_players.sort_values(by='adp').head(num_picks_before_me)
            available_players = available_players[~available_players['full_name'].isin(drafted_by_others['full_name'])]

        picked_player = None
        target_pos_type = actual_roster_fill_order[round_num - 1] # Get the position to fill for this round

        # Find the best available player for the target position
        eligible_players = pd.DataFrame()
        if target_pos_type in ['QB', 'RB', 'WR', 'TE', 'K', 'D/ST', 'DP']:
            eligible_players = available_players[available_players['position'] == target_pos_type].sort_values(by='vbd', ascending=False)
        elif target_pos_type == 'RB/WR':
            eligible_players = available_players[available_players['position'].isin(['RB', 'WR'])].sort_values(by='vbd', ascending=False)
        elif target_pos_type == 'WR/TE':
            eligible_players = available_players[available_players['position'].isin(['WR', 'TE'])].sort_values(by='vbd', ascending=False)
        elif target_pos_type == 'BE':
            eligible_players = available_players.sort_values(by='vbd', ascending=False) # For bench, any position

        if not eligible_players.empty:
            picked_player = eligible_players.iloc[0]

        if picked_player is not None:
            # Add player to the team
            my_team[target_pos_type].append(picked_player['full_name'])

            available_players = available_players[available_players['full_name'] != picked_player['full_name']]
            draft_order.append(picked_player['full_name'])
        else:
            # If a critical spot cannot be filled, we might need to adjust strategy or stop
            break 

    return my_team, draft_order


def main():
    
    player_data = load_player_data(PLAYER_ADP_PATH, PLAYER_PROJECTIONS_PATH)
    player_data = calculate_vbd(player_data, CONFIG.get('roster_settings', {}), CONFIG.get('scoring_rules', {}))
    my_team, draft_order = suggest_draft_picks(player_data, CONFIG)
    return my_team, draft_order
    

if __name__ == "__main__":
    my_team, draft_order = main()
    print("Draft strategizer script executed. It returns data structures for use by other scripts.")
    print("Simulated Roster:", my_team)
    print("Simulated Draft Order:", draft_order)
