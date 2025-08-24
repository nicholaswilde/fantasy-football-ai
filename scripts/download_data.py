#!/usr/bin/env python3
################################################################################
#
# Script Name: download_data.py
# ----------------
# Downloads player data (projections and ADP) from the Sleeper API and ESPN API.
#
# @author Nicholas Wilde, 0xb299a622
# @date 2025-08-20
# @version 0.2.0
#
################################################################################

import requests
import csv
import subprocess
import os
import pandas as pd
from espn_api.football import League
import yaml
from datetime import datetime
from dotenv import load_dotenv
import sys

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from fantasy_ai.errors import (
    APIError, AuthenticationError, ConfigurationError,
    FileOperationError, NetworkError, wrap_exception
)
from fantasy_ai.utils.logging import setup_logging, get_logger
from fantasy_ai.utils.retry import retry

# Set up logging
setup_logging(level='INFO', format_type='console', log_file='logs/download_data.log')
logger = get_logger(__name__)

# Load environment variables
load_dotenv()

# Configuration file path
CONFIG_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', 'config.yaml'
)

def load_config() -> dict:
    """Loads the configuration from config.yaml with error handling."""
    try:
        logger.debug(f"Loading configuration from {CONFIG_FILE}")
        with open(CONFIG_FILE, 'r') as f:
            config = yaml.safe_load(f)
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
    except Exception as e:
        raise wrap_exception(
            e, ConfigurationError,
            f"Failed to load configuration from {CONFIG_FILE}",
            config_file=CONFIG_FILE
        )

CONFIG = load_config()

@retry(max_attempts=3, base_delay=1.0, backoff_factor=2.0, retryable_exceptions=(APIError, NetworkError))
def fetch_sleeper_data() -> dict:
    """Fetches all player data from the Sleeper API with error handling."""
    url = "https://api.sleeper.app/v1/players/nfl"
    try:
        logger.info(f"Fetching data from Sleeper API: {url}")
        response = requests.get(url)
        response.raise_for_status()  # Raises an HTTPError for bad responses (4xx or 5xx)
        logger.info("Successfully fetched data from Sleeper API")
        return response.json()
    except requests.exceptions.HTTPError as e:
        raise APIError(
            f"Sleeper API returned an HTTP error: {e.response.status_code} - {e.response.text}",
            url=url,
            status_code=e.response.status_code,
            original_error=e
        )
    except requests.exceptions.ConnectionError as e:
        raise NetworkError(
            f"Could not connect to Sleeper API: {e}",
            url=url,
            original_error=e
        )
    except requests.exceptions.Timeout as e:
        raise NetworkError(
            f"Sleeper API request timed out: {e}",
            url=url,
            original_error=e
        )
    except requests.exceptions.RequestException as e:
        raise wrap_exception(
            e, NetworkError,
            f"An unexpected error occurred while fetching from Sleeper API: {e}",
            url=url
        )

@retry(max_attempts=3, base_delay=1.0, backoff_factor=2.0, retryable_exceptions=(APIError, NetworkError))
def fetch_player_projections() -> pd.DataFrame:
    """
    Fetches player projections from ESPN API with error handling.
    
    Returns:
        pd.DataFrame: DataFrame with player projections (full_name, position, projected_points).
        
    Raises:
        AuthenticationError: If ESPN API credentials are missing.
        APIError: If there's an issue with the ESPN API response.
        NetworkError: If there's a network connectivity issue.
    """
    logger.info("Fetching real player projections from ESPN API...")
    league_id = os.getenv("LEAGUE_ID")
    espn_s2 = os.getenv("ESPN_S2")
    swid = os.getenv("SWID")
    year = CONFIG.get('league_settings', {}).get('year', datetime.now().year)

    if not all([league_id, espn_s2, swid]):
        raise AuthenticationError(
            "Missing ESPN API credentials (LEAGUE_ID, ESPN_S2, SWID) in .env. Cannot fetch projections.",
            detail="Ensure LEAGUE_ID, ESPN_S2, and SWID are set in your .env file."
        )

    try:
        league = League(league_id=int(league_id), year=year, espn_s2=espn_s2, swid=swid)
        
        projections_data = []
        for team in league.teams:
            for player in team.roster:
                projected_points = 0.0
                if hasattr(player, 'stats') and 0 in player.stats and 'projected_points' in player.stats[0]:
                    projected_points = player.stats[0]['projected_points']
                elif hasattr(player, 'projected_points_total'):
                    projected_points = player.projected_points_total

                projections_data.append({
                    'full_name': player.name,
                    'position': player.position,
                    'projected_points': projected_points
                })
        logger.info("Successfully fetched player projections from ESPN API")
        return pd.DataFrame(projections_data)

    except requests.exceptions.HTTPError as e:
        raise APIError(
            f"ESPN API returned an HTTP error: {e.response.status_code} - {e.response.text}",
            url="ESPN API",
            status_code=e.response.status_code,
            original_error=e
        )
    except requests.exceptions.ConnectionError as e:
        raise NetworkError(
            f"Could not connect to ESPN API: {e}",
            url="ESPN API",
            original_error=e
        )
    except requests.exceptions.Timeout as e:
        raise NetworkError(
            f"ESPN API request timed out: {e}",
            url="ESPN API",
            original_error=e
        )
    except Exception as e:
        raise wrap_exception(
            e, APIError,
            f"An unexpected error occurred while fetching from ESPN API: {e}",
            url="ESPN API"
        )

def generate_player_projections_csv(player_data: dict):
    """Generates player_projections.csv from the player data and fetched projections."""
    if not player_data:
        logger.warning("No player data to process for projections.")
        return

    fieldnames = ['player_id', 'full_name', 'team', 'position', 'age', 'years_exp', 'projected_points']

    try:
        projections_df = fetch_player_projections()
    except (AuthenticationError, APIError, NetworkError) as e:
        logger.error(f"Failed to fetch player projections: {e}")
        projections_df = pd.DataFrame() # Continue with empty projections if fetch fails

    players_list = []
    for player_id, player_info in player_data.items():
        player_info['player_id'] = player_id
        players_list.append(player_info)

    all_players_df = pd.DataFrame(players_list)

    if 'full_name' not in all_players_df.columns:
        if 'first_name' in all_players_df.columns and 'last_name' in all_players_df.columns:
            all_players_df['full_name'] = all_players_df['first_name'] + ' ' + all_players_df['last_name']
        else:
            all_players_df['full_name'] = all_players_df['player_id']

    if not projections_df.empty:
        merged_projections = pd.merge(
            all_players_df[['player_id', 'full_name', 'team', 'position', 'age', 'years_exp']],
            projections_df[['full_name', 'position', 'projected_points']],
            on=['full_name', 'position'],
            how='left'
        )
        merged_projections['projected_points'] = merged_projections['projected_points'].fillna(0.0)
    else:
        merged_projections = all_players_df[['player_id', 'full_name', 'team', 'position', 'age', 'years_exp']].copy()
        merged_projections['projected_points'] = 0.0

    final_projections_df = merged_projections[fieldnames].copy()

    rows_to_write = []
    for index, row in final_projections_df.iterrows():
        rows_to_write.append({field: row[field] for field in fieldnames})

    try:
        output_path = os.path.join(PROJECT_ROOT, 'data', 'player_projections.csv')
        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(rows_to_write)
        logger.info(f"{output_path} has been created successfully.")
    except IOError as e:
        raise FileOperationError(
            f"Could not write player projections CSV file: {output_path}",
            file_path=output_path,
            operation="write",
            original_error=e
        )
    except Exception as e:
        raise wrap_exception(
            e, FileOperationError,
            f"An unexpected error occurred while writing player projections to {output_path}",
            file_path=output_path,
            operation="write"
        )

def generate_player_adp_csv(player_data: dict):
    """
    Calls the download_adp.py script to generate player_adp.csv with error handling.
    """
    logger.info("Calling scripts/download_adp.py to fetch ADP data...")
    try:
        adp_script_path = os.path.join(os.path.dirname(__file__), 'download_adp.py')
        result = subprocess.run(
            ['python3', adp_script_path],
            capture_output=True, text=True, check=True
        )
        logger.info(result.stdout)
        if result.stderr:
            logger.warning(f"Stderr from download_adp.py: {result.stderr}")
        logger.info("data/player_adp.csv has been created successfully by download_adp.py.")
    except subprocess.CalledProcessError as e:
        logger.error(f"Error running download_adp.py: {e.returncode}\nStdout: {e.stdout}\nStderr: {e.stderr}")
        raise FileOperationError(
            "Failed to generate player_adp.csv due to subprocess error.",
            file_path="scripts/download_adp.py",
            operation="execute",
            original_error=e
        )
    except Exception as e:
        raise wrap_exception(
            e, FileOperationError, # Assuming most subprocess errors here are related to network issues for ADP
            f"An unexpected error occurred while running download_adp.py: {e}",
            detail="Check if python3 is in your PATH or if download_adp.py has execution permissions."
        )


def main():
    logger.info("--- Starting data download process ---")
    try:
        all_players = fetch_sleeper_data()

        if all_players:
            generate_player_projections_csv(all_players)
            generate_player_adp_csv(all_players)
            logger.info("--- Data download process finished! ---")
            return 0
        else:
            logger.error("Sleeper data fetch failed, cannot proceed with projections and ADP.")
            logger.info("--- Data download process failed! ---")
            return 1
    except (ConfigurationError, NetworkError, APIError, AuthenticationError, FileOperationError) as e:
        logger.error(f"Data download error: {e.get_detailed_message()}")
        print(f"\n❌ Data Download Error: {e}")
        return 1
    except Exception as e:
        logger.critical(f"An unhandled critical error occurred: {e}", exc_info=True)
        print(f"\n❌ An unexpected critical error occurred: {e}")
        print("Please check the log file for more details.")
        return 1

if __name__ == "__main__":
    sys.exit(main())