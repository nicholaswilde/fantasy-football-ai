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


from tabulate import tabulate

def get_team_needs(my_team, roster_settings):
    """
    Determines the current positional needs of the user's team.
    """
    needs = {}
    for pos, count in roster_settings.items():
        if pos in my_team and len(my_team[pos]) < count:
            needs[pos] = count - len(my_team[pos])
    return needs

def get_best_available_player(available_players, my_team, roster_settings):
    """
    Suggests the best available player based on VBD and current team needs.
    """
    current_needs = get_team_needs(my_team, roster_settings)

    # Prioritize filling starting spots first, then flex, then bench
    # This order should align with how a real draft progresses
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
                # For bench, consider all remaining positions by VBD
                eligible_players = available_players
            
            if not eligible_players.empty:
                # Sort by VBD to get the best player for the current need
                eligible_players = eligible_players.sort_values(by='vbd', ascending=False)
                return eligible_players.iloc[0]
    
    # Fallback: if no specific needs, just pick the highest VBD player
    if not available_players.empty:
        return available_players.sort_values(by='vbd', ascending=False).iloc[0]
    
    return None

def display_my_team(my_team):
    """
    Displays the current roster of the user's team.
    """
    print("\n--- Your Current Roster ---")
    for pos, players in my_team.items():
        if players:
            print(f"{pos}: {', '.join(players)}")
        else:
            print(f"{pos}: (Empty)")
    print("---------------------------")

def live_draft_assistant():
    print("\n--- Starting Live Draft Assistant ---")
    print("Loading player data and calculating VBD scores...")
    player_data = load_player_data(PLAYER_ADP_PATH, PLAYER_PROJECTIONS_PATH)
    player_data = calculate_vbd(player_data, CONFIG.get('roster_settings', {}), CONFIG.get('scoring_rules', {}))

    available_players = player_data.copy()
    my_team = {pos: [] for pos in CONFIG.get('roster_settings', {})}
    
    # Initialize roster counts for flex positions
    roster_settings = CONFIG.get('roster_settings', {})
    # Map flex positions to their base positions for easier tracking
    flex_map = {
        'RB/WR': ['RB', 'WR'],
        'WR/TE': ['WR', 'TE']
    }

    # Calculate total number of picks in the draft
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
            
            player_name = input("Enter your pick (full name, or 'exit' to quit): ").strip()
            if player_name.lower() == 'exit' or player_name.lower() == 'quit':
                break
            
            picked_player_df = available_players[available_players['full_name'].str.lower() == player_name.lower()]
            if picked_player_df.empty:
                print(f"Player '{player_name}' not found or already drafted. Please try again.")
                continue
            picked_player = picked_player_df.iloc[0]

            # Add player to my team
            pos_added = False
            # Try to fill exact position first
            if picked_player['position'] in my_team and len(my_team[picked_player['position']]) < roster_settings.get(picked_player['position'], 0):
                my_team[picked_player['position']].append(picked_player['full_name'])
                pos_added = True
            else:
                # Try to fill flex spots
                for flex_pos, base_positions in flex_map.items():
                    if picked_player['position'] in base_positions and len(my_team[flex_pos]) < roster_settings.get(flex_pos, 0):
                        my_team[flex_pos].append(picked_player['full_name'])
                        pos_added = True
                        break
            
            # If not added to a specific position or flex, add to bench
            if not pos_added and len(my_team['BE']) < roster_settings.get('BE', 0):
                my_team['BE'].append(picked_player['full_name'])
                pos_added = True
            
            if pos_added:
                available_players = available_players[available_players['full_name'] != picked_player['full_name']] # Remove from available
                print(f"You drafted {picked_player['full_name']} ({picked_player['position']}).")
                display_my_team(my_team)
            else:
                print(f"Could not add {picked_player['full_name']} to your roster. Check roster settings or team capacity.")
                # Don't increment pick number if player wasn't successfully added
                continue

        else:
            print(f"\n--- Round {current_round}, Pick {current_pick_number} (Other Team's Pick) ---")
            player_name = input("Enter player drafted by other team (full name, or 'exit' to quit): ").strip()
            if player_name.lower() == 'exit' or player_name.lower() == 'quit':
                break
            
            picked_player_df = available_players[available_players['full_name'].str.lower() == player_name.lower()]
            if picked_player_df.empty:
                print(f"Player '{player_name}' not found or already drafted. Please try again.")
                continue
            picked_player = picked_player_df.iloc[0]
            available_players = available_players[available_players['full_name'] != picked_player['full_name']] # Remove from available
            print(f"{picked_player['full_name']} ({picked_player['position']}) was drafted.")

        current_pick_number += 1

    print("\n--- Draft Assistant Session Ended ---")
    display_my_team(my_team)
    print("Final available players count:", len(available_players))

def main():
    live_draft_assistant()

if __name__ == "__main__":
    main()
