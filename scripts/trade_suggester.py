#!/usr/bin/env python3

import pandas as pd
from analysis import calculate_fantasy_points
import os

def suggest_trades(df, week):
    """
    Suggests trades based on the previous week's stats.

    Args:
        df (pd.DataFrame): The DataFrame with calculated fantasy points.
        week (int): The most recent week to analyze.

    Returns:
        pd.DataFrame: A DataFrame of trade suggestions.
    """
    print(f"Analyzing player performance for week {week}...")

    # Filter for the most recent week and previous weeks
    this_week_df = df[df['week'] == week]
    last_week_df = df[df['week'] < week]

    # Calculate average points for previous weeks
    player_avg_pts = last_week_df.groupby('player_display_name')['fantasy_points'].mean().reset_index()
    player_avg_pts.rename(columns={'fantasy_points': 'avg_fantasy_points'}, inplace=True)

    # Merge average points with this week's data
    merged_df = pd.merge(this_week_df, player_avg_pts, on='player_display_name', how='left')

    # Calculate the difference between this week's points and the average
    merged_df['point_difference'] = merged_df['fantasy_points'] - merged_df['avg_fantasy_points']

    # Identify sell-high and buy-low candidates
    sell_high = merged_df[merged_df['point_difference'] > 10].sort_values(by='point_difference', ascending=False)
    buy_low = merged_df[merged_df['point_difference'] < -5].sort_values(by='point_difference', ascending=True)

    print("\n--- Trade Suggestions ---")

    print("\nSell-High Candidates (Players who overperformed this week):")
    print(sell_high[['player_display_name', 'position', 'recent_team', 'fantasy_points', 'avg_fantasy_points', 'point_difference']].to_markdown(index=False))

    print("\nBuy-Low Candidates (Players who underperformed this week):")
    print(buy_low[['player_display_name', 'position', 'recent_team', 'fantasy_points', 'avg_fantasy_points', 'point_difference']].to_markdown(index=False))


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

        # Find the most recent week
        most_recent_week = stats_with_points['week'].max()

        # Get trade suggestions
        suggest_trades(stats_with_points, most_recent_week)
