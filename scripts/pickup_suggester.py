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
from tabulate import tabulate

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

def find_waiver_gems(player_stats_df, my_team_roster):
    """
    Identifies waiver wire 'gems' based on recent usage trends and underperforming fantasy points.
    """
    if player_stats_df.empty:
        return pd.DataFrame()

    # Filter out players already on my team
    my_team_players = [player for sublist in my_team_roster.values() for player in sublist]
    available_stats_df = player_stats_df[~player_stats_df['player_display_name'].isin(my_team_players)].copy()

    if available_stats_df.empty:
        return pd.DataFrame()

    # Ensure 'week' is numeric and get the current (max) week
    available_stats_df['week'] = pd.to_numeric(available_stats_df['week'], errors='coerce')
    current_week = available_stats_df['week'].max()
    
    if pd.isna(current_week):
        print("Warning: Could not determine current week from player stats.")
        return pd.DataFrame()

    # Calculate season averages for all players
    season_avg_df = available_stats_df.groupby(['player_display_name', 'position', 'recent_team']).agg(
        season_ppr_avg=('fantasy_points_ppr', 'mean'),
        season_games_played=('week', 'nunique')
    ).reset_index()
    
    # Filter for players with at least 3 games played in the season to have a meaningful average
    season_avg_df = season_avg_df[season_avg_df['season_games_played'] >= 3]

    # Calculate recent (last 3 weeks) averages
    recent_weeks = [current_week, current_week - 1, current_week - 2]
    recent_stats_df = available_stats_df[available_stats_df['week'].isin(recent_weeks)].copy()

    if recent_stats_df.empty:
        return pd.DataFrame()

    recent_avg_df = recent_stats_df.groupby(['player_display_name', 'position', 'recent_team']).agg(
        recent_ppr_avg=('fantasy_points_ppr', 'mean'),
        recent_targets_avg=('targets', 'mean'),
        recent_carries_avg=('carries', 'mean'),
        recent_target_share_avg=('target_share', 'mean'),
        recent_air_yards_share_avg=('air_yards_share', 'mean'),
        recent_games_played=('week', 'nunique')
    ).reset_index()

    # Merge season and recent averages
    merged_gems_df = pd.merge(
        recent_avg_df,
        season_avg_df,
        on=['player_display_name', 'position', 'recent_team'],
        how='inner'
    )

    # Filter for players who played in at least 2 of the last 3 weeks
    merged_gems_df = merged_gems_df[merged_gems_df['recent_games_played'] >= 2]

    # Apply gem logic
    # High Usage:
    # WR/TE: >= 7 targets/game OR >= 20% target share OR >= 25% air yards share in last 3 weeks
    # RB: >= 15 carries/game in last 3 weeks
    # Underperforming: recent_ppr_avg < season_ppr_avg

    # Define thresholds
    WR_TE_TARGETS_THRESHOLD = 7
    WR_TE_TARGET_SHARE_THRESHOLD = 0.20
    WR_TE_AIR_YARDS_SHARE_THRESHOLD = 0.25
    RB_CARRIES_THRESHOLD = 15

    # Apply conditions
    is_wr_te = merged_gems_df['position'].isin(['WR', 'TE'])
    is_rb = merged_gems_df['position'] == 'RB'

    high_usage_wr_te = (
        (merged_gems_df['recent_targets_avg'] >= WR_TE_TARGETS_THRESHOLD) |
        (merged_gems_df['recent_target_share_avg'] >= WR_TE_TARGET_SHARE_THRESHOLD) |
        (merged_gems_df['recent_air_yards_share_avg'] >= WR_TE_AIR_YARDS_SHARE_THRESHOLD)
    )
    high_usage_rb = (merged_gems_df['recent_carries_avg'] >= RB_CARRIES_THRESHOLD)

    underperforming = (merged_gems_df['recent_ppr_avg'] < merged_gems_df['season_ppr_avg'])

    # Combine all conditions
    waiver_gems = merged_gems_df[
        ((is_wr_te & high_usage_wr_te) | (is_rb & high_usage_rb)) |
        underperforming
    ].sort_values(by='recent_ppr_avg', ascending=False) # Sort by recent PPR for display

    return waiver_gems[['player_display_name', 'position', 'recent_team',
                        'recent_ppr_avg', 'season_ppr_avg',
                        'recent_targets_avg', 'recent_carries_avg',
                        'recent_target_share_avg', 'recent_air_yards_share_avg']]

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

    # Calculate player value (e.g., AvgPoints) for general recommendations
    player_value = calculate_player_value(player_stats.copy()) # Pass a copy to avoid modifying original

    # --- General Waiver Wire Pickups ---
    recommendations_df = recommend_pickups(available_players, player_value, my_team)

    if not recommendations_df.empty:
        print("\n--- Top Waiver Wire Pickups ---")
        # Select and rename columns for display
        display_df = recommendations_df[['player_display_name', 'position', 'recent_team', 'AvgPoints']].copy()
        display_df.rename(columns={
            'player_display_name': 'Player',
            'position': 'Position',
            'recent_team': 'Team',
            'AvgPoints': 'Avg Pts/Game'
        }, inplace=True)
        print(tabulate(display_df, headers='keys', tablefmt='fancy_grid'))
    else:
        print("\nNo general waiver wire pickup suggestions at this time.")

    # --- Waiver Wire Gems ---
    print("\n--- Waiver Wire Gems (High Usage, Underperforming) ---")
    waiver_gems_df = find_waiver_gems(player_stats.copy(), my_team) # Pass a copy

    if not waiver_gems_df.empty:
        display_gems_df = waiver_gems_df.copy()
        display_gems_df.rename(columns={
            'player_display_name': 'Player',
            'position': 'Position',
            'recent_team': 'Team',
            'recent_ppr_avg': 'Recent PPR Avg',
            'season_ppr_avg': 'Season PPR Avg',
            'recent_targets_avg': 'Recent Targets Avg',
            'recent_carries_avg': 'Recent Carries Avg',
            'recent_target_share_avg': 'Recent Target Share Avg',
            'recent_air_yards_share_avg': 'Recent Air Yards Share Avg'
        }, inplace=True)
        # Format percentages
        display_gems_df['Recent Target Share Avg'] = display_gems_df['Recent Target Share Avg'].apply(lambda x: f"{x:.1%}")
        display_gems_df['Recent Air Yards Share Avg'] = display_gems_df['Recent Air Yards Share Avg'].apply(lambda x: f"{x:.1%}")
        
        print(tabulate(display_gems_df, headers='keys', tablefmt='fancy_grid'))
        print("\nWaiver wire gem finder executed successfully.")
    else:
        print("\nNo waiver wire gems identified at this time.")
    
    print("\nPickup suggester script executed successfully.")
    return recommendations_df # Still return the original recommendations_df for consistency if needed by caller

if __name__ == "__main__":
    main()

