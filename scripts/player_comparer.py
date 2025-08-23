#!/usr/bin/env python3
################################################################################
#
# Script Name: player_comparer.py
# ----------------
# Compares fantasy football players side-by-side based on various metrics
# like fantasy points, VOR, consistency, projections, and ADP.
#
# @author Nicholas Wilde, 0xb299a622
# @date 23 08 2025
# @version 0.1.4
#
################################################################################

import os
import pandas as pd
import yaml
from dotenv import load_dotenv
from tabulate import tabulate
from analysis import calculate_fantasy_points, get_advanced_draft_recommendations

# Load environment variables
load_dotenv()

# Configuration file path
CONFIG_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', 'config.yaml'
)
PLAYER_STATS_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'player_stats.csv'
)
PLAYER_ADP_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'player_adp.csv'
)
PLAYER_PROJECTIONS_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'player_projections.csv'
)

def load_config():
    """Loads the configuration from config.yaml."""
    with open(CONFIG_FILE, 'r') as f:
        return yaml.safe_load(f)

def normalize_player_name(name):
    """Normalizes player names to match the format in player_stats.csv (e.g., 'Patrick Mahomes' to 'P.Mahomes')."""
    # Ensure name is a string before splitting
    if pd.isna(name):
        return "" # Return empty string for NaN values
    parts = str(name).split(' ')
    if len(parts) > 1:
        return f"{parts[0][0]}.{' '.join(parts[1:])}"
    return name

def compare_players(player_names):
    """Compares fantasy football players based on various metrics."""
    config = load_config()
    league_year = config.get('league_settings', {}).get('year')

    if not league_year:
        return "Error: 'year' not found in config.yaml under 'league_settings'."

    try:
        player_stats_df = pd.read_csv(PLAYER_STATS_FILE, low_memory=False)
    except FileNotFoundError:
        return f"Error: {PLAYER_STATS_FILE} not found. Please run 'task download' to get player stats."

    try:
        player_adp_df = pd.read_csv(PLAYER_ADP_FILE, low_memory=False)
    except FileNotFoundError:
        player_adp_df = pd.DataFrame()

    try:
        player_projections_df = pd.read_csv(PLAYER_PROJECTIONS_FILE, low_memory=False)
    except FileNotFoundError:
        player_projections_df = pd.DataFrame()

    # Filter for the current league year
    current_year_stats = player_stats_df[player_stats_df['season'] == league_year].copy()

    if current_year_stats.empty:
        return f"No player stats found for the year {league_year}. Please ensure data is available for this season."

    # Calculate fantasy points, VOR, and consistency for weekly data first
    current_year_stats = calculate_fantasy_points(current_year_stats)
    current_year_stats = get_advanced_draft_recommendations(current_year_stats)

    # Aggregate weekly stats to season totals for comparison
    # Group by player_name, position, and team, then sum fantasy_points, and average VOR/consistency
    # For 'team', we can take the first non-null value if there are multiple entries for a player
    aggregated_stats = current_year_stats.groupby(['player_name', 'position']).agg(
        FPts=('fantasy_points', 'sum'),
        VOR=('vor', 'mean'),
        Consistency=('consistency_std_dev', 'mean'),
        Team=('recent_team', lambda x: x.dropna().iloc[0] if not x.dropna().empty else pd.NA) # Get the most recent team
    ).reset_index()
    aggregated_stats.rename(columns={'FPts': 'fantasy_points', 'Consistency': 'consistency_std_dev'}, inplace=True)


    # Merge with ADP and Projections
    # Use aggregated_stats as the base for merging
    final_comparison_df = aggregated_stats.copy()

    if not player_adp_df.empty:
        if 'full_name' in player_adp_df.columns:
            player_adp_df.rename(columns={'full_name': 'player_name'}, inplace=True)
            player_adp_df['player_name'] = player_adp_df['player_name'].apply(normalize_player_name)
        # Convert 'adp' column to numeric, coercing errors to NaN
        player_adp_df['adp'] = pd.to_numeric(player_adp_df['adp'], errors='coerce')
        # Select only 'player_name' and 'adp' from player_adp_df to avoid merging unnecessary columns
        player_adp_df = player_adp_df[['player_name', 'adp']].copy()
        final_comparison_df = pd.merge(final_comparison_df, player_adp_df, on='player_name', how='left')

    if not player_projections_df.empty:
        # Rename 'full_name' to 'player_name' in player_projections_df
        if 'full_name' in player_projections_df.columns:
            player_projections_df.rename(columns={'full_name': 'player_name'}, inplace=True)
            player_projections_df['player_name'] = player_projections_df['player_name'].apply(normalize_player_name)
        # Select only 'player_name' and 'projected_points' from player_projections_df
        # Assuming 'projected_points' is the column for projection
        if 'projected_points' in player_projections_df.columns:
            player_projections_df.rename(columns={'projected_points': 'projection'}, inplace=True)
            player_projections_df = player_projections_df[['player_name', 'projection']].copy()
            final_comparison_df = pd.merge(final_comparison_df, player_projections_df, on='player_name', how='left')


    # Normalize input player names
    normalized_player_names = [normalize_player_name(name) for name in player_names]

    # Filter for the requested players
    comparison_df = final_comparison_df[final_comparison_df['player_name'].isin(normalized_player_names)].copy()

    if comparison_df.empty:
        return "No matching players found in the data for comparison."

    # Select and reorder columns for display
    display_columns = [
        'player_name', 'position', 'Team', 'fantasy_points', 
        'VOR', 'consistency_std_dev', 'adp', 'projection'
    ]
    # Ensure all display columns exist, fill missing with NaN or a default value
    for col in display_columns:
        if col not in comparison_df.columns:
            comparison_df[col] = pd.NA # Use pd.NA for missing data

    comparison_df = comparison_df[display_columns]

    # Rename columns for better readability
    comparison_df.rename(columns={
        'player_name': 'Player',
        'position': 'Pos',
        'fantasy_points': 'FPts',
        'consistency_std_dev': 'Consistency (Std Dev)'
    }, inplace=True)

    # Format output using tabulate
    table = tabulate(comparison_df, headers='keys', tablefmt='fancy_grid', floatfmt=".2f")
    return table

if __name__ == "__main__":
    print("\n--- Player Comparer ---")
    print("Enter player names separated by commas (e.g., 'Patrick Mahomes, Travis Kelce'):")
    input_names = input("> ")
    
    if input_names:
        player_list = [name.strip() for name in input_names.split(',')]
        comparison_result = compare_players(player_list)
        print(comparison_result)
    else:
        print("No players entered. Exiting.")
    print("\n-----------------------")