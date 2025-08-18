#!/usr/bin/env python3

import pandas as pd
import numpy as np
import os

def calculate_fantasy_points(player_stats_df):
    """
    Calculates fantasy points for each player based on a specific scoring system.
    The scoring system is based on the rules defined in the GEMINI.md file.

    Args:
        player_stats_df (pd.DataFrame): A DataFrame containing player stats.

    Returns:
        pd.DataFrame: A new DataFrame with a 'fantasy_points' column added.
    """
    # Defensive players and kickers are not included in the standard nfl_data_py stats,
    # so we will focus on offensive skill positions.
    scoring_rules = {
        "passing_yards": 0.04,  # 1 point for every 25 yards
        "passing_tds": 4,
        "receptions": 1,         # Full PPR (1 point per reception)
        "receiving_yards": 0.1, # 1 point for every 10 yards
        "receiving_tds": 6,
        "rushing_yards": 0.1,   # 1 point for every 10 yards
        "rushing_tds": 6,
        "interceptions": -2,
        "fumbles_lost": -2,
    }

    # Initialize a new column for fantasy points
    player_stats_df['fantasy_points'] = 0

    # Calculate fantasy points for each player based on the scoring rules
    player_stats_df['fantasy_points'] += player_stats_df['passing_yards'] * scoring_rules['passing_yards']
    player_stats_df['fantasy_points'] += player_stats_df['passing_tds'] * scoring_rules['passing_tds']
    player_stats_df['fantasy_points'] += player_stats_df['receptions'] * scoring_rules['receptions']
    player_stats_df['fantasy_points'] += player_stats_df['receiving_yards'] * scoring_rules['receiving_yards']
    player_stats_df['fantasy_points'] += player_stats_df['receiving_tds'] * scoring_rules['receiving_tds']
    player_stats_df['fantasy_points'] += player_stats_df['rushing_yards'] * scoring_rules['rushing_yards']
    player_stats_df['fantasy_points'] += player_stats_df['rushing_tds'] * scoring_rules['rushing_tds']
    player_stats_df['fantasy_points'] += player_stats_df['interceptions'] * scoring_rules['interceptions']
    player_stats_df['fantasy_points'] += player_stats_df['fumbles_lost'] * scoring_rules['fumbles_lost']

    return player_stats_df

def get_advanced_draft_recommendations(df, num_recommendations=30):
    """
    Generates a list of top players for a fantasy football draft based on
    multiple advanced metrics, including Value Over Replacement and Consistency.

    Args:
        df (pd.DataFrame): The DataFrame with calculated fantasy points.
        num_recommendations (int): The number of top players to recommend.

    Returns:
        pd.DataFrame: A DataFrame of top players for the draft.
    """
    print("Generating advanced draft recommendations...")
    
    # Calculate average fantasy points per game
    player_summary = df.groupby(['player_name', 'position', 'recent_team', 'team', 'bye_week'])['fantasy_points'].mean().reset_index()
    player_summary.rename(columns={'fantasy_points': 'avg_fantasy_points'}, inplace=True)

    # Calculate consistency (Standard Deviation of weekly points)
    consistency_df = df.groupby('player_name')['fantasy_points'].std().reset_index()
    consistency_df.rename(columns={'fantasy_points': 'consistency_std_dev'}, inplace=True)
    player_summary = pd.merge(player_summary, consistency_df, on='player_name', how='left')

    # Calculate Value Over Replacement (VOR)
    # This is a conceptual calculation; a real-world model would be more complex
    replacement_values = {}
    for pos in ['QB', 'RB', 'WR', 'TE']:
        positional_players = player_summary[player_summary['position'] == pos]
        # Assumes a 12-team league with standard starters
        if pos == 'QB':
            num_starters = 12 
        elif pos == 'RB':
            num_starters = 24
        elif pos == 'WR':
            num_starters = 24
        elif pos == 'TE':
            num_starters = 12
        else:
            num_starters = 0
        
        if num_starters > 0 and len(positional_players) >= num_starters:
            replacement_player = positional_players.sort_values(by='avg_fantasy_points', ascending=False).iloc[num_starters - 1]
            replacement_values[pos] = replacement_player['avg_fantasy_points']
        else:
            replacement_values[pos] = 0
    
    # Calculate VOR for each player
    def calculate_vor(row):
        if row['position'] in replacement_values:
            return row['avg_fantasy_points'] - replacement_values[row['position']]
        return 0

    player_summary['vor'] = player_summary.apply(calculate_vor, axis=1)

    # Sort players by VOR for draft recommendations
    top_players = player_summary.sort_values(by='vor', ascending=False).head(num_recommendations)

    return top_players


def check_bye_week_conflicts(df):
    """
    Checks for bye week conflicts among a list of players.

    Args:
        df (pd.DataFrame): A DataFrame containing player information with 'bye_week' column.

    Returns:
        pd.DataFrame: A DataFrame highlighting players with potential bye week conflicts.
    """
    print("Checking for bye week conflicts...")
    
    # Focus on the top 30 players by VOR as potential draft picks
    top_players = get_advanced_draft_recommendations(df, num_recommendations=30)
    
    bye_week_counts = top_players['bye_week'].value_counts().reset_index()
    bye_week_counts.columns = ['bye_week', 'player_count']
    
    conflicts = bye_week_counts[bye_week_counts['player_count'] > 2].sort_values(by='player_count', ascending=False)

    if not conflicts.empty:
        print("\n*** WARNING: Potential Bye Week Conflicts Detected! ***")
        for index, row in conflicts.iterrows():
            players_in_conflict = top_players[top_players['bye_week'] == row['bye_week']]
            print(f"  > Week {int(row['bye_week'])}: {int(row['player_count'])} highly-ranked players are on bye.")
            print(f"    Players: {', '.join(players_in_conflict['player_name'])}")
    else:
        print("\nNo major bye week conflicts found among top players.")
    
    return conflicts


def get_trade_recommendations(df, team_roster=None, target_position='RB'):
    """
    Identifies potential trade targets based on consistency and positional value.
    This is a conceptual function and can be expanded for more complex analysis.

    Args:
        df (pd.DataFrame): The DataFrame with calculated fantasy points.
        team_roster (list): A list of player names on your current roster.
        target_position (str): The position you are looking to trade for.

    Returns:
        pd.DataFrame: A DataFrame of recommended trade targets.
    """
    print(f"Generating trade recommendations for position: {target_position}")
    
    # Get advanced player data
    advanced_df = get_advanced_draft_recommendations(df, num_recommendations=100)
    
    # Filter out players on your hypothetical roster
    if team_roster:
        advanced_df = advanced_df[~advanced_df['player_name'].isin(team_roster)]
    
    # Get players at the target position
    positional_targets = advanced_df[advanced_df['position'] == target_position]
    
    # Identify consistent, high-value players
    trade_targets = positional_targets.sort_values(by='consistency_std_dev', ascending=True).head(5)
    
    return trade_targets[['player_name', 'recent_team', 'position', 'avg_fantasy_points', 'consistency_std_dev']]

if __name__ == "__main__":
    # Define the path to your data file
    data_file = "data/player_stats.csv"

    # Check if the data file exists
    if not os.path.exists(data_file):
        print(f"Error: Data file not found at '{data_file}'. Please run 'download_stats.py' first.")
    else:
        # Read the stats file
        stats_df = pd.read_csv(data_file)
        
        # Calculate fantasy points for each player
        stats_with_points = calculate_fantasy_points(stats_df)
        
        # Get advanced draft recommendations
        draft_recs = get_advanced_draft_recommendations(stats_with_points)
        print("\n--- Advanced Draft Recommendations (Top 30 Players by Value Over Replacement) ---")
        print(draft_recs[['player_name', 'recent_team', 'position', 'vor', 'consistency_std_dev']].to_markdown(index=False))

        # Check for bye week conflicts
        check_bye_week_conflicts(stats_with_points)

        # Example trade recommendations
        my_team = ['Patrick Mahomes', 'Tyreek Hill', 'Saquon Barkley'] # This is a placeholder for your actual team
        trade_recs = get_trade_recommendations(stats_with_points, team_roster=my_team, target_position='RB')
        print("\n--- Trade Recommendations (Top 5 Consistent RBs not on your team) ---")
        print(trade_recs.to_markdown(index=False))


