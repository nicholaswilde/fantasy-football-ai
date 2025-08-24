#!/usr/bin/env python3
################################################################################
#
# Script Name: download_adp.py
# ----------------
# Downloads and processes Average Draft Position (ADP) data from a specified source
# and saves it to data/player_adp.csv.
#
# @author Nicholas Wilde, 0xb299a622
# @date 23 08 2025
# @version 0.2.0
#
################################################################################

import pandas as pd
import os
import requests
import yaml
import sys

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from fantasy_ai.errors import (
    FileOperationError,
    DataValidationError,
    ConfigurationError,
    APIError,
    AuthenticationError,
    NetworkError,
    wrap_exception
)
from fantasy_ai.utils.logging import setup_logging, get_logger
from fantasy_ai.utils.retry import retry

# Set up logging
setup_logging(level='INFO', format_type='console', log_file='logs/download_adp.log')
logger = get_logger(__name__)

# Define file paths
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ADP_OUTPUT_PATH = os.path.join(PROJECT_ROOT, 'data', 'player_adp.csv')
CONFIG_FILE = os.path.join(PROJECT_ROOT, 'config.yaml')

def load_config() -> dict:
    """
    Loads configuration from the config.yaml file.
    """
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

CONFIG = load_config()

# URL for Fantasy Football Calculator ADP API
# This API provides data for 12-team standard leagues for 2025
ADP_URL = f"https://fantasyfootballcalculator.com/api/v1/adp/standard?teams={CONFIG['league_settings']['number_of_teams']}&year={CONFIG['league_settings']['year']}&position=all"

@retry(
    max_attempts=3,
    base_delay=1.0,
    backoff_factor=2.0,
    retryable_exceptions=(APIError, NetworkError)
)
def fetch_and_process_adp():
    """
    Fetches ADP data from Fantasy Football Calculator API, processes it, and saves it in the required format.
    """
    logger.info(f"Fetching ADP data from {ADP_URL}...")
    try:
        response = requests.get(ADP_URL)
        response.raise_for_status()  # Raise an HTTPError for bad responses (4xx or 5xx)
        data = response.json()

        # The API response has a 'players' key containing the list of player dictionaries
        if 'players' not in data:
            raise DataValidationError("API response does not contain 'players' key.", api_name="FantasyFootballCalculator")
        
        players_data = data['players']

        if not players_data:
            raise DataValidationError("No player data found in the API response.", api_name="FantasyFootballCalculator")

        adp_df = pd.DataFrame(players_data)

        # --- Column mapping for Fantasy Football Calculator API ---
        # API keys observed: 'name', 'position', 'adp' (among others)
        column_mapping = {
            'name': 'full_name',
            'position': 'position',
            'adp': 'adp'
        }
        
        # Rename columns to match our desired format
        adp_df = adp_df.rename(columns=column_mapping)

        # Ensure required columns exist after renaming
        required_cols = ['full_name', 'position', 'adp']
        if not all(col in adp_df.columns for col in required_cols):
            missing_cols = [col for col in required_cols if col not in adp_df.columns]
            raise DataValidationError(f"Missing required columns after processing: {missing_cols}. "
                             "Check column_mapping or API response structure.", api_name="FantasyFootballCalculator")

        # Select and reorder columns
        processed_df = adp_df[required_cols].copy()

        # Save to the target path
        processed_df.to_csv(ADP_OUTPUT_PATH, index=False)
        logger.info(f"Successfully fetched and processed ADP data and saved to {ADP_OUTPUT_PATH}")
        logger.info(f"Total players fetched: {len(processed_df)}")

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            raise AuthenticationError("Invalid API key or credentials.", api_name="FantasyFootballCalculator", original_error=e)
        else:
            raise APIError(f"HTTP error fetching data: {e}", api_name="FantasyFootballCalculator", original_error=e)
    except requests.exceptions.RequestException as e:
        raise NetworkError(f"Network or API request error: {e}", api_name="FantasyFootballCalculator", original_error=e)
    except ValueError as e:
        raise DataValidationError(f"Data processing error: {e}", api_name="FantasyFootballCalculator", original_error=e)
    except Exception as e:
        raise wrap_exception(e, APIError, f"An unexpected error occurred: {e}", api_name="FantasyFootballCalculator")

def main():
    try:
        fetch_and_process_adp()
        return 0
    except (ConfigurationError, FileOperationError, DataValidationError, APIError, AuthenticationError, NetworkError) as e:
        logger.error(f"ADP download error: {e.get_detailed_message()}")
        print(f"\n❌ Error during ADP download: {e}")
        return 1
    except Exception as e:
        logger.critical(f"An unhandled critical error occurred: {e}", exc_info=True)
        print(f"\n❌ An unexpected critical error occurred: {e}")
        print("Please check the log file for more details.")
        return 1

if __name__ == "__main__":
    sys.exit(main())