#!/usr/bin/env python3
################################################################################
#
# Script Name: trade_suggester.py
# ----------------
# Suggests sell-high and buy-low trade candidates based on recent player performance.
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

# Load configuration from config.yaml
CONFIG_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', 'config.yaml'
)

def load_config():
    with open(CONFIG_FILE, 'r') as f:
        return yaml.safe_load(f)

CONFIG = load_config()

def suggest_trades(df, week):
    """
    Suggests trades based on the previous week's stats.

    Args:
        df (pd.DataFrame): The DataFrame with calculated fantasy points.
        week (int): The most recent week to analyze.

    Returns:
        tuple[pd.DataFrame, pd.DataFrame]: A tuple of DataFrames (sell_high, buy_low).
    """
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

    # Get thresholds from config
    sell_high_threshold = CONFIG.get('analysis_settings', {}).get('sell_high_threshold', 10)
    buy_low_threshold = CONFIG.get('analysis_settings', {}).get('buy_low_threshold', -5)

    # Identify sell-high and buy-low candidates
    sell_high = merged_df[merged_df['point_difference'] > sell_high_threshold].sort_values(by='point_difference', ascending=False)
    buy_low = merged_df[merged_df['point_difference'] < buy_low_threshold].sort_values(by='point_difference', ascending=True)

    return sell_high, buy_low


if __name__ == "__main__":
    # Define the path to your data file
    data_file = "data/player_stats.csv"

    # Check if the data file exists
    if not os.path.exists(data_file):
        print(f"Error: Data file not found at '{data_file}'. Please run 'download_stats.py' first.")
    else:
        # Read the stats file
        stats_df = pd.read_csv(data_file, low_memory=False)

        # Find the most recent week
        most_recent_week = stats_df['week'].max()

        # Get trade suggestions
        sell_high, buy_low = suggest_trades(stats_df, most_recent_week)

        # Define the columns to display
        columns_to_display = [
            'player_display_name', 'position', 'recent_team',
            'fantasy_points', 'avg_fantasy_points', 'point_difference'
        ]

        # Rename columns for better readability
        sell_high_display = sell_high[columns_to_display].rename(columns={
            'player_display_name': 'Player',
            'position': 'Pos',
            'recent_team': 'Team',
            'fantasy_points': 'Week Pts',
            'avg_fantasy_points': 'Avg Pts',
            'point_difference': 'Diff'
        })

        buy_low_display = buy_low[columns_to_display].rename(columns={
            'player_display_name': 'Player',
            'position': 'Pos',
            'recent_team': 'Team',
            'fantasy_points': 'Week Pts',
            'avg_fantasy_points': 'Avg Pts',
            'point_difference': 'Diff'
        })

        print("--- Sell-High Candidates ---")
        print(tabulate(sell_high_display, headers='keys', tablefmt='fancy_grid', showindex=False))
        print("\n--- Buy-Low Candidates ---")
        print(tabulate(buy_low_display, headers='keys', tablefmt='fancy_grid', showindex=False))
