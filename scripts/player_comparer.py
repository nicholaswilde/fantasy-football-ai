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
import sys

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from fantasy_ai.errors import (
    FileOperationError, DataValidationError, ConfigurationError, wrap_exception
)
from fantasy_ai.utils.logging import setup_logging, get_logger

# Set up logging
setup_logging(level='INFO', format_type='console', log_file='logs/player_comparer.log')
logger = get_logger(__name__)

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

def load_config() -> dict:
    """
    Loads the configuration from config.yaml with error handling.
    
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


def normalize_player_name(name):
    """
    Normalizes player names to match the format in player_stats.csv (e.g., 'Patrick Mahomes' to 'P.Mahomes').
    Handles NaN values gracefully.
    """
    if pd.isna(name):
        return "" # Return empty string for NaN values
    parts = str(name).split(' ')
    if len(parts) >= 2:
        return f"{parts[0][0]}.{' '.join(parts[1:])}"
    return name


def compare_players(player_names: list) -> str:
    """
    Compares fantasy football players based on various metrics.
    
    Args:
        player_names: A list of player names to compare.
        
    Returns:
        A formatted string (tabulated) with player comparison data.
        
    Raises:
        ConfigurationError: If league year is not configured.
        FileOperationError: If data files cannot be read.
        DataValidationError: If data files are malformed or empty.
    """
    logger.info(f"Comparing players: {player_names}")
    config = load_config()
    league_year = config.get('league_settings', {}).get('year')

    if not league_year:
        raise ConfigurationError(
            "'year' not found in config.yaml under 'league_settings'. Please run 'task get_league_settings' first.",
            config_key="league_settings.year"
        )

    try:
        player_stats_df = pd.read_csv(PLAYER_STATS_FILE, low_memory=False)
    except FileNotFoundError as e:
        raise FileOperationError(
            f"Player stats file not found: {PLAYER_STATS_FILE}. Please run 'task download_stats' to get player stats.",
            file_path=PLAYER_STATS_FILE,
            operation="read",
            original_error=e
        )
    except pd.errors.EmptyDataError as e:
        raise DataValidationError(
            f"Player stats file is empty or invalid: {PLAYER_STATS_FILE}",
            field_name="player_stats_file",
            expected_type="valid CSV with player data",
            actual_value="empty file",
            original_error=e
        )
    except pd.errors.ParserError as e:
        raise DataValidationError(
            f"Cannot parse player stats file: {PLAYER_STATS_FILE}",
            field_name="player_stats_file",
            expected_type="valid CSV format",
            actual_value="malformed CSV",
            original_error=e
        )
    except Exception as e:
        raise wrap_exception(
            e, FileOperationError,
            f"Failed to read player stats file {PLAYER_STATS_FILE}",
            file_path=PLAYER_STATS_FILE,
            operation="read"
        )

    if player_stats_df.empty:
        raise DataValidationError(
            "Player stats DataFrame is empty after loading. Cannot proceed with comparison.",
            field_name="player_stats_df",
            expected_type="non-empty DataFrame",
            actual_value="empty DataFrame"
        )

    try:
        player_adp_df = pd.read_csv(PLAYER_ADP_FILE, low_memory=False)
    except FileNotFoundError:
        logger.warning("Player ADP file not found, proceeding without ADP data.")
        player_adp_df = pd.DataFrame()
    except pd.errors.EmptyDataError:
        logger.warning("Player ADP file is empty, proceeding without ADP data.")
        player_adp_df = pd.DataFrame()
    except pd.errors.ParserError as e:
        logger.warning(f"Cannot parse player ADP file: {e}, proceeding without ADP data.")
        player_adp_df = pd.DataFrame()
    except Exception as e:
        logger.warning(f"Failed to read player ADP file: {e}, proceeding without ADP data.")
        player_adp_df = pd.DataFrame()

    try:
        player_projections_df = pd.read_csv(PLAYER_PROJECTIONS_FILE, low_memory=False)
    except FileNotFoundError:
        logger.warning("Player projections file not found, proceeding without projections data.")
        player_projections_df = pd.DataFrame()
    except pd.errors.EmptyDataError:
        logger.warning("Player projections file is empty, proceeding without projections data.")
        player_projections_df = pd.DataFrame()
    except pd.errors.ParserError as e:
        logger.warning(f"Cannot parse player projections file: {e}, proceeding without projections data.")
        player_projections_df = pd.DataFrame()
    except Exception as e:
        logger.warning(f"Failed to read player projections file: {e}, proceeding without projections data.")
        player_projections_df = pd.DataFrame()

    # Filter for the current league year
    current_year_stats = player_stats_df[player_stats_df['season'] == league_year].copy()

    if current_year_stats.empty:
        raise DataValidationError(
            f"No player stats found for the year {league_year}. Please ensure data is available for this season.",
            field_name="current_year_stats",
            expected_type="non-empty DataFrame",
            actual_value="empty DataFrame"
        )

    # Calculate fantasy points, VOR, and consistency for weekly data first
    try:
        current_year_stats = calculate_fantasy_points(current_year_stats)
        current_year_stats = get_advanced_draft_recommendations(current_year_stats)
    except DataValidationError as e:
        raise DataValidationError(
            f"Error calculating fantasy points or draft recommendations: {e}",
            original_error=e
        )
    except Exception as e:
        raise wrap_exception(
            e, DataValidationError,
            f"An unexpected error occurred during fantasy point or draft recommendation calculation: {e}"
        )

    # Aggregate weekly stats to season totals for comparison
    aggregated_stats = current_year_stats.groupby(['player_name', 'position']).agg(
        FPts=('fantasy_points', 'sum'),
        VOR=('vor', 'mean'),
        Consistency=('consistency_std_dev', 'mean'),
        Team=('recent_team', lambda x: x.dropna().iloc[0] if not x.dropna().empty else pd.NA)
    ).reset_index()
    aggregated_stats.rename(columns={'FPts': 'fantasy_points', 'Consistency': 'consistency_std_dev'}, inplace=True)

    # Merge with ADP and Projections
    final_comparison_df = aggregated_stats.copy()

    if not player_adp_df.empty:
        if 'full_name' in player_adp_df.columns:
            player_adp_df.rename(columns={'full_name': 'player_name'}, inplace=True)
            player_adp_df['player_name'] = player_adp_df['player_name'].apply(normalize_player_name)
        player_adp_df['adp'] = pd.to_numeric(player_adp_df['adp'], errors='coerce')
        player_adp_df = player_adp_df[['player_name', 'adp']].copy()
        final_comparison_df = pd.merge(final_comparison_df, player_adp_df, on='player_name', how='left')

    if not player_projections_df.empty:
        if 'full_name' in player_projections_df.columns:
            player_projections_df.rename(columns={'full_name': 'player_name'}, inplace=True)
            player_projections_df['player_name'] = player_projections_df['player_name'].apply(normalize_player_name)
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

def main():
    """Main function to run player comparison and handle errors."""
    logger.info("Starting player comparison process.")
    print("\n--- Player Comparer ---")
    print("Enter player names separated by commas (e.g., 'Patrick Mahomes, Travis Kelce'):")
    input_names = input("> ")
    
    if input_names:
        player_list = [name.strip() for name in input_names.split(',')]
        try:
            comparison_result = compare_players(player_list)
            print(comparison_result)
            return 0
        except (ConfigurationError, FileOperationError, DataValidationError) as e:
            logger.error(f"Player comparison error: {e.get_detailed_message()}")
            print(f"\n❌ Error during player comparison: {e}")
            print("\nTroubleshooting:")
            if isinstance(e, ConfigurationError):
                print("- Check config.yaml for valid settings, especially 'league_settings.year'.")
            elif isinstance(e, FileOperationError):
                print("- Ensure data files (player_stats.csv, player_adp.csv, player_projections.csv) exist and are accessible.")
                print("- Run 'task download_stats', 'task download_adp', 'task download_projections' to prepare data.")
            elif isinstance(e, DataValidationError):
                print("- Check the format and content of your data files.")
            return 1
        except Exception as e:
            logger.critical(f"An unhandled critical error occurred: {e}", exc_info=True)
            print(f"\n❌ An unexpected critical error occurred: {e}")
            print("Please check the log file for more details.")
            return 1
    else:
        print("No players entered. Exiting.")
        logger.info("No players entered for comparison.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
