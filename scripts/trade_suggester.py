#!/usr/bin/env python3
################################################################################
#
# Script Name: trade_suggester.py
# ----------------
# Suggests sell-high and buy-low trade candidates based on recent player performance.
#
# @author Nicholas Wilde, 0xb299a622
# @date 23 08 2025
# @version 0.2.0
#
################################################################################

import pandas as pd
import os
import yaml
from tabulate import tabulate
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
setup_logging(level='INFO', format_type='console', log_file='logs/trade_suggester.log')
logger = get_logger(__name__)

# Load configuration from config.yaml
CONFIG_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', 'config.yaml'
)

def load_config() -> dict:
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

def suggest_trades(df: pd.DataFrame, week: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Suggests trades based on the previous week's stats.

    Args:
        df (pd.DataFrame): The DataFrame with calculated fantasy points.
        week (int): The most recent week to analyze.

    Returns:
        tuple[pd.DataFrame, pd.DataFrame]: A tuple of DataFrames (sell_high, buy_low).
    """
    required_cols = ['week', 'player_display_name', 'fantasy_points']
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise DataValidationError(f"Missing required columns for trade suggestions: {missing_cols}", field_name="player_stats_columns")

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

def main():
    """Main function to run trade suggester and handle errors."""
    try:
        # Define the path to your data file
        data_file = "data/player_stats.csv"

        # Check if the data file exists
        if not os.path.exists(data_file):
            raise FileOperationError(f"Data file not found at '{data_file}'. Please run 'download_stats.py' first.", file_path=data_file, operation="read")

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
        return 0
    except (ConfigurationError, FileOperationError, DataValidationError) as e:
        logger.error(f"Trade suggestion error: {e.get_detailed_message()}")
        print(f"\n❌ Error during trade suggestion: {e}")
        return 1
    except Exception as e:
        logger.critical(f"An unhandled critical error occurred: {e}", exc_info=True)
        wrapped_e = wrap_exception(e, DataValidationError, "An unexpected error occurred during trade suggestion.")
        print(f"\n❌ An unexpected critical error occurred: {wrapped_e}")
        print("Please check the log file for more details.")
        return 1

if __name__ == "__main__":
    sys.exit(main())