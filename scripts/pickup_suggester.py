#!/usr/bin/env python3
################################################################################
#
# Script Name: pickup_suggester.py
# ----------------
# Suggests waiver wire pickups based on player performance and team needs.
#
# @author Nicholas Wilde, 0xb299a622
# @date 2025-08-20
# @version 0.1.0
#
################################################################################

import pandas as pd
import os
import yaml

# Define file paths
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AVAILABLE_PLAYERS_PATH = os.path.join(PROJECT_ROOT, 'data', 'available_players.csv')
PLAYER_STATS_PATH = os.path.join(PROJECT_ROOT, 'data', 'player_stats.csv')
MY_TEAM_PATH = os.path.join(PROJECT_ROOT, 'data', 'my_team.md')

# Load configuration from config.yaml
CONFIG_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', 'config.yaml'
)

def load_config():
    with open(CONFIG_FILE, 'r') as f:
        return yaml.safe_load(f)

CONFIG = load_config()

def load_available_players(file_path):
    """Loads available players from the CSV file and renames columns for consistency."""
    try:
        df = pd.read_csv(file_path, low_memory=False)
        # Rename columns to match player_stats_df for merging
        df = df.rename(columns={'name': 'player_display_name', 'pro_team': 'recent_team'})
        return df
    except FileNotFoundError:
        print(f"Error: Available players file not found at {file_path}")
        return pd.DataFrame()

def load_player_stats(file_path):
    """Loads player season stats from the CSV file."""
    try:
        return pd.read_csv(file_path, low_memory=False)
    except FileNotFoundError:
        print(f"Error: Player stats file not found at {file_path}")
        return pd.DataFrame()

def load_my_team(file_path):
    """
    Loads and parses the user's team from the Markdown file.
    This is a simplified parser. It expects headings like '## QB', '## RB', etc.,
    followed by bulleted lists of player names.
    """
    my_team = {
        'QB': [], 'RB': [], 'WR': [], 'TE': [], 'FLEX': [], 'K': [], 'DST': [], 'BENCH': []
    }
    current_position = None
    try:
        with open(file_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line.startswith('## '):
                    pos = line.replace('## ', '').strip().upper()
                    if pos in my_team:
                        current_position = pos
                    else:
                        current_position = None
                elif line.startswith('- ') and current_position:
                    player_name = line.replace('- ', '').strip()
                    my_team[current_position].append(player_name)
    except FileNotFoundError:
        print(f"Warning: My team file not found at {file_path}. Cannot analyze team needs.")
    return my_team

def calculate_player_value(player_stats_df):
    """Calculates average points per game (PPG) for players using fantasy_points_ppr."""
    # Group by player and calculate total PPR points and games played
    player_summary = player_stats_df.groupby(['player_display_name', 'position', 'recent_team']).agg(
        total_fantasy_points_ppr=('fantasy_points_ppr', 'sum'),
        games_played=('week', 'nunique') # Count unique weeks played
    ).reset_index()

    # Calculate AvgPoints (PPG)
    player_summary['AvgPoints'] = player_summary['total_fantasy_points_ppr'] / player_summary['games_played']

    # Handle cases where games_played might be 0 to avoid division by zero
    player_summary['AvgPoints'] = player_summary['AvgPoints'].fillna(0)

    return player_summary[['player_display_name', 'position', 'recent_team', 'AvgPoints']]

def identify_team_needs(my_team_roster):
    """Identifies positions where the user's team needs improvement or depth."""
    needs = {}
    # Define standard roster sizes from config.yaml
    roster_settings = CONFIG.get('roster_settings', {})
    standard_roster_spots = {
        'QB': roster_settings.get('QB', 1),
        'RB': roster_settings.get('RB', 2),
        'WR': roster_settings.get('WR', 2),
        'TE': roster_settings.get('TE', 1),
        'RB/WR': roster_settings.get('RB_WR', 1), # Using RB_WR for flex
        'WR/TE': roster_settings.get('WR_TE', 1), # Using WR_TE for flex
        'K': roster_settings.get('K', 1),
        'DST': roster_settings.get('DST', 1),
        'DP': roster_settings.get('DP', 2),
        'BE': roster_settings.get('BE', 7),
        'IR': roster_settings.get('IR', 1)
    }

    # Map config keys to the keys used in my_team_roster if they differ
    # For example, config might have RB_WR but my_team_roster uses FLEX
    # This needs careful consideration based on how my_team.md is generated
    # For now, I'll assume direct mapping or handle common flex cases.
    
    # Simplified mapping for common positions, assuming my_team_roster uses standard position names
    # and FLEX is a combination.
    mapped_roster_settings = {
        'QB': roster_settings.get('QB', 1),
        'RB': roster_settings.get('RB', 2),
        'WR': roster_settings.get('WR', 2),
        'TE': roster_settings.get('TE', 1),
        'K': roster_settings.get('K', 1),
        'DST': roster_settings.get('DST', 1),
    }
    # Add flex spots to the total count for RB, WR, TE if they exist in config
    mapped_roster_settings['RB'] += roster_settings.get('RB_WR', 0)
    mapped_roster_settings['WR'] += roster_settings.get('RB_WR', 0) + roster_settings.get('WR_TE', 0)
    mapped_roster_settings['TE'] += roster_settings.get('WR_TE', 0)

    for pos, count in mapped_roster_settings.items():
        if len(my_team_roster.get(pos, [])) < count:
            needs[pos] = count - len(my_team_roster.get(pos, []))
    
    # Consider bench spots as well
    bench_needed = roster_settings.get('BE', 7) - len(my_team_roster.get('BENCH', []))
    if bench_needed > 0:
        needs['BENCH'] = bench_needed

    return needs

def recommend_pickups(available_players_df, player_value_df, my_team_roster):
    """Generates pickup recommendations."""
    if available_players_df.empty or player_value_df.empty:
        return pd.DataFrame()

    # Merge available players with their performance data
    merged_df = pd.merge(
        available_players_df,
        player_value_df,
        on=['player_display_name', 'position', 'recent_team'], # Assuming these columns exist in both
        how='inner'
    )

    # Filter out players already on my team
    my_team_players = [player for sublist in my_team_roster.values() for player in sublist]
    merged_df = merged_df[~merged_df['player_display_name'].isin(my_team_players)]

    team_needs = identify_team_needs(my_team_roster)
    
    recommendations = []

    # Prioritize positions with needs
    for pos, count in sorted(team_needs.items(), key=lambda item: item[1], reverse=True):
        if pos == 'FLEX':
            # For FLEX, recommend top RBs, WRs, TEs
            flex_candidates = merged_df[merged_df['position'].isin(['RB', 'WR', 'TE'])]
            top_players_at_pos = flex_candidates.sort_values(by='AvgPoints', ascending=False).head(count * 2)
        elif pos in ['K', 'DST']:
            continue
        else:
            top_players_at_pos = merged_df[
                (merged_df['position'] == pos)
            ].sort_values(by='AvgPoints', ascending=False).head(count * 2) # Get a few more than needed

        if not top_players_at_pos.empty:
            recommendations.append(top_players_at_pos)

    # Also show top overall available players if no specific needs
    if not team_needs:
        top_overall = merged_df.sort_values(by='AvgPoints', ascending=False).head(10)
        if not top_overall.empty:
            recommendations.append(top_overall)

    if not recommendations:
        return pd.DataFrame()
    
    return pd.concat(recommendations).drop_duplicates().reset_index(drop=True)

def main():
    print("Loading data...")
    available_players = load_available_players(AVAILABLE_PLAYERS_PATH)
    player_stats = load_player_stats(PLAYER_STATS_PATH)
    my_team = load_my_team(MY_TEAM_PATH)

    if player_stats.empty:
        print("Player stats data is empty. Cannot proceed with recommendations.")
        return

    # Ensure 'Player', 'Position', 'Team' columns exist in player_stats
    required_cols = ['player_display_name', 'position', 'recent_team']
    if not all(col in player_stats.columns for col in required_cols):
        print(f"Error: Player stats file must contain {required_cols} columns.")
        return

    # Calculate player value (e.g., AvgPoints)
    player_value = calculate_player_value(player_stats.copy()) # Pass a copy to avoid modifying original

    recommend_pickups(available_players, player_value, my_team)
    print("Pickup suggester script executed. It returns data structures for use by other scripts.")

if __name__ == "__main__":
    main()
