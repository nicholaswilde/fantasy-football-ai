#!/usr/bin/env python3
"""
Improved script to download player data with comprehensive error handling.

This script demonstrates the new error handling architecture for the
Fantasy Football AI project.
"""

import os
import sys
import csv
import subprocess
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
import yaml
import requests
from espn_api.football import League

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from fantasy_ai.errors import (
    NetworkError, APIError, AuthenticationError, ConfigurationError,
    FileOperationError as FileIOError, DataValidationError, wrap_exception
)
from fantasy_ai.utils.retry import retry
from fantasy_ai.utils.logging import setup_logging, get_logger

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
    """
    Load configuration from config.yaml with proper error handling.
    
    Returns:
        Configuration dictionary
        
    Raises:
        ConfigurationError: If config file cannot be read or parsed
    """
    try:
        logger.debug(f"Loading configuration from {CONFIG_FILE}")
        with open(CONFIG_FILE, 'r') as f:
            config = yaml.safe_load(f)
        logger.info("Configuration loaded successfully")
        return config
    except FileNotFoundError as e:
        raise ConfigurationError(
            f"Configuration file not found: {CONFIG_FILE}",
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


@retry(max_attempts=3, base_delay=2.0, backoff_factor=2.0)
def fetch_sleeper_data() -> dict:
    """
    Fetch all player data from the Sleeper API with retry logic.
    
    Returns:
        Dictionary containing player data
        
    Raises:
        NetworkError: If API request fails after retries
        APIError: If API returns invalid data
    """
    url = "https://api.sleeper.app/v1/players/nfl"
    logger.info(f"Fetching player data from Sleeper API: {url}")
    
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        if not isinstance(data, dict):
            raise APIError(
                "Invalid response format from Sleeper API",
                api_name="Sleeper",
                endpoint=url,
                status_code=response.status_code
            )
        
        logger.info(f"Successfully fetched data for {len(data)} players from Sleeper API")
        return data
        
    except requests.exceptions.Timeout as e:
        raise NetworkError(
            "Request to Sleeper API timed out",
            url=url,
            original_error=e
        )
    except requests.exceptions.ConnectionError as e:
        raise NetworkError(
            "Failed to connect to Sleeper API",
            url=url,
            original_error=e
        )
    except requests.exceptions.HTTPError as e:
        status_code = e.response.status_code if e.response else None
        raise APIError(
            f"Sleeper API returned HTTP error: {status_code}",
            api_name="Sleeper",
            endpoint=url,
            status_code=status_code,
            original_error=e
        )
    except requests.exceptions.RequestException as e:
        raise NetworkError(
            "Network error while fetching Sleeper data",
            url=url,
            original_error=e
        )
    except Exception as e:
        raise wrap_exception(
            e, APIError,
            "Unexpected error while fetching Sleeper data",
            api_name="Sleeper",
            endpoint=url
        )


def validate_espn_credentials() -> tuple:
    """
    Validate ESPN API credentials and return them.
    
    Returns:
        Tuple of (league_id, espn_s2, swid, year)
        
    Raises:
        AuthenticationError: If credentials are missing or invalid
        ConfigurationError: If year is not configured
    """
    logger.debug("Validating ESPN credentials")
    
    league_id = os.getenv("LEAGUE_ID")
    espn_s2 = os.getenv("ESPN_S2")
    swid = os.getenv("SWID")
    
    missing_creds = []
    if not league_id:
        missing_creds.append("LEAGUE_ID")
    if not espn_s2:
        missing_creds.append("ESPN_S2")
    if not swid:
        missing_creds.append("SWID")
    
    if missing_creds:
        raise AuthenticationError(
            f"Missing ESPN API credentials: {', '.join(missing_creds)}. "
            f"Please set these environment variables in your .env file.",
            api_name="ESPN",
            credential_type="API credentials"
        )
    
    # Validate league_id is numeric
    try:
        league_id_int = int(league_id)
    except ValueError as e:
        raise AuthenticationError(
            f"LEAGUE_ID must be a number, got: {league_id}",
            api_name="ESPN",
            credential_type="LEAGUE_ID",
            original_error=e
        )
    
    # Get year from config
    try:
        config = load_config()
        year = config.get('league_settings', {}).get('year', datetime.now().year)
    except Exception as e:
        logger.warning(f"Could not load year from config, using current year: {e}")
        year = datetime.now().year
    
    logger.info("ESPN credentials validated successfully")
    return league_id_int, espn_s2, swid, year


@retry(max_attempts=2, base_delay=3.0, backoff_factor=2.0)
def fetch_player_projections() -> pd.DataFrame:
    """
    Fetch player projections from ESPN API with error handling.
    
    Returns:
        DataFrame with player projections
        
    Raises:
        AuthenticationError: If ESPN credentials are invalid
        APIError: If ESPN API request fails
        NetworkError: If network issues occur
    """
    logger.info("Fetching player projections from ESPN API")
    
    try:
        league_id, espn_s2, swid, year = validate_espn_credentials()
    except (AuthenticationError, ConfigurationError):
        logger.warning("Cannot fetch projections due to credential issues")
        return pd.DataFrame()
    
    try:
        logger.debug(f"Creating ESPN League instance for league {league_id}, year {year}")
        league = League(league_id=league_id, year=year, espn_s2=espn_s2, swid=swid)
        
        projections_data = {}
        
        # Fetch projections for the first 17 weeks
        for week in range(1, 18):
            logger.debug(f"Fetching projections for week {week}")
            box_scores = league.box_scores(week=week)
            
            for box_score in box_scores:
                lineup = getattr(box_score, 'home_lineup', []) + getattr(box_score, 'away_lineup', [])
                for player in lineup:
                    if player.name not in projections_data:
                        projections_data[player.name] = {
                            'full_name': player.name,
                            'position': getattr(player, 'position', 'UNKNOWN'),
                            'projected_points': 0.0
                        }
                    
                    # Sum up projected points across all weeks
                    projected_points = 0.0
                    if hasattr(player, 'points'):
                        projected_points = player.points
                    projections_data[player.name]['projected_points'] += projected_points

        logger.info(f"Successfully processed projections for {len(projections_data)} players")
        return pd.DataFrame(list(projections_data.values()))
        
    except Exception as e:
        # Check if it's an authentication error
        if "401" in str(e) or "unauthorized" in str(e).lower():
            raise AuthenticationError(
                "ESPN API authentication failed. Please check your credentials.",
                api_name="ESPN",
                credential_type="S2/SWID",
                original_error=e
            )
        elif "404" in str(e) or "not found" in str(e).lower():
            raise APIError(
                f"ESPN league {league_id} not found for year {year}",
                api_name="ESPN",
                status_code=404,
                original_error=e
            )
        else:
            raise wrap_exception(
                e, APIError,
                "Failed to fetch projections from ESPN API",
                api_name="ESPN"
            )


def safe_create_directory(directory: str) -> None:
    """
    Safely create directory with proper error handling.
    
    Args:
        directory: Directory path to create
        
    Raises:
        FileIOError: If directory cannot be created
    """
    try:
        os.makedirs(directory, exist_ok=True)
        logger.debug(f"Directory ensured: {directory}")
    except PermissionError as e:
        raise FileIOError(
            f"Permission denied creating directory: {directory}",
            file_path=directory,
            operation="create_directory",
            original_error=e
        )
    except Exception as e:
        raise wrap_exception(
            e, FileIOError,
            f"Failed to create directory: {directory}",
            file_path=directory,
            operation="create_directory"
        )


def generate_player_projections_csv(player_data: dict) -> None:
    """
    Generate player_projections.csv with comprehensive error handling.
    
    Args:
        player_data: Dictionary of player data from Sleeper API
        
    Raises:
        FileIOError: If file cannot be written
        DataValidationError: If data is invalid
    """
    if not player_data:
        logger.warning("No player data provided for projections CSV")
        return
    
    logger.info("Generating player projections CSV")
    
    # Ensure data directory exists
    data_dir = 'data'
    safe_create_directory(data_dir)
    
    fieldnames = ['player_id', 'full_name', 'team', 'position', 'age', 'years_exp', 'projected_points']
    csv_path = os.path.join(data_dir, 'player_projections.csv')
    
    try:
        # Fetch projections
        projections_df = fetch_player_projections()
        
        # Create players list with validation
        players_list = []
        for player_id, player_info in player_data.items():
            try:
                # Validate required fields
                if not isinstance(player_info, dict):
                    logger.warning(f"Invalid player info for {player_id}, skipping")
                    continue
                
                player_info_copy = player_info.copy()
                player_info_copy['player_id'] = player_id
                players_list.append(player_info_copy)
                
            except Exception as e:
                logger.warning(f"Error processing player {player_id}: {e}")
                continue
        
        if not players_list:
            raise DataValidationError(
                "No valid player data found",
                field_name="player_data",
                expected_type="dict",
                actual_value=type(player_data)
            )
        
        # Create DataFrame
        all_players_df = pd.DataFrame(players_list)
        
        # Ensure full_name column exists
        if 'full_name' not in all_players_df.columns:
            if 'first_name' in all_players_df.columns and 'last_name' in all_players_df.columns:
                all_players_df['full_name'] = (
                    all_players_df['first_name'].astype(str) + ' ' + 
                    all_players_df['last_name'].astype(str)
                )
            else:
                all_players_df['full_name'] = all_players_df['player_id']
        
        # Merge with projections
        if not projections_df.empty:
            merged_projections = pd.merge(
                all_players_df[['player_id', 'full_name', 'team', 'position', 'age', 'years_exp']],
                projections_df[['full_name', 'position', 'projected_points']],
                on=['full_name', 'position'],
                how='left'
            )
        else:
            logger.warning("No projections data available, using zeros")
            merged_projections = all_players_df[['player_id', 'full_name', 'team', 'position', 'age', 'years_exp']].copy()
            merged_projections['projected_points'] = 0.0
        
        # Fill missing projections
        merged_projections['projected_points'] = merged_projections['projected_points'].fillna(0.0)
        
        # Select final columns
        final_projections_df = merged_projections[fieldnames].copy()
        
        # Write to CSV with error handling
        try:
            with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames, extrasaction='ignore')
                writer.writeheader()
                
                for _, row in final_projections_df.iterrows():
                    row_dict = {field: row[field] for field in fieldnames}
                    writer.writerow(row_dict)
            
            logger.info(f"Successfully created {csv_path} with {len(final_projections_df)} players")
            
        except PermissionError as e:
            raise FileIOError(
                f"Permission denied writing to {csv_path}",
                file_path=csv_path,
                operation="write",
                original_error=e
            )
        except Exception as e:
            raise wrap_exception(
                e, FileIOError,
                f"Failed to write projections CSV to {csv_path}",
                file_path=csv_path,
                operation="write"
            )
            
    except (FileIOError, DataValidationError):
        raise  # Re-raise our custom exceptions
    except Exception as e:
        raise wrap_exception(
            e, FileIOError,
            "Unexpected error generating player projections CSV"
        )


def generate_player_adp_csv(player_data: dict) -> None:
    """
    Generate ADP CSV by calling download_adp.py with proper error handling.
    
    Args:
        player_data: Player data dictionary (used for fallback)
        
    Raises:
        FileIOError: If ADP script fails
    """
    logger.info("Generating player ADP CSV")
    adp_script_path = os.path.join(os.path.dirname(__file__), 'download_adp.py')
    
    try:
        # Execute download_adp.py as a subprocess
        result = subprocess.run(
            ['python3', adp_script_path],
            capture_output=True, 
            text=True, 
            check=True,
            timeout=60  # 60 second timeout
        )
        
        if result.stdout:
            logger.debug(f"ADP script output: {result.stdout}")
        if result.stderr:
            logger.warning(f"ADP script warnings: {result.stderr}")
            
        logger.info("Successfully generated ADP data via download_adp.py")
        
    except subprocess.TimeoutExpired as e:
        logger.error("ADP script timed out, creating fallback CSV")
        create_fallback_adp_csv(player_data)
    except subprocess.CalledProcessError as e:
        logger.error(f"ADP script failed with exit code {e.returncode}")
        if e.stdout:
            logger.debug(f"ADP script stdout: {e.stdout}")
        if e.stderr:
            logger.debug(f"ADP script stderr: {e.stderr}")
        logger.info("Creating fallback ADP CSV")
        create_fallback_adp_csv(player_data)
    except Exception as e:
        logger.error(f"Unexpected error running ADP script: {e}")
        logger.info("Creating fallback ADP CSV")
        create_fallback_adp_csv(player_data)


def create_fallback_adp_csv(player_data: dict) -> None:
    """
    Create fallback ADP CSV with N/A values.
    
    Args:
        player_data: Player data dictionary
    """
    logger.info("Creating fallback ADP CSV with N/A values")
    
    try:
        safe_create_directory('data')
        csv_path = 'data/player_adp.csv'
        
        fieldnames = ['player_id', 'full_name', 'position', 'team', 'adp']
        
        with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            
            for player_id, player_info in player_data.items():
                try:
                    row = player_info.copy()
                    row['player_id'] = player_id
                    row['adp'] = 'N/A'
                    writer.writerow(row)
                except Exception as e:
                    logger.warning(f"Error writing player {player_id} to fallback ADP CSV: {e}")
                    
        logger.info(f"Fallback ADP CSV created: {csv_path}")
        
    except Exception as e:
        raise wrap_exception(
            e, FileIOError,
            "Failed to create fallback ADP CSV"
        )


def main():
    """Main function with comprehensive error handling."""
    try:
        logger.info("Starting Fantasy Football AI data download process")
        
        # Fetch player data from Sleeper API
        logger.info("Step 1: Fetching player data from Sleeper API")
        all_players = fetch_sleeper_data()
        
        if not all_players:
            logger.error("No player data retrieved from Sleeper API")
            return 1
        
        # Generate projections CSV
        logger.info("Step 2: Generating player projections CSV")
        generate_player_projections_csv(all_players)
        
        # Generate ADP CSV
        logger.info("Step 3: Generating player ADP CSV")
        generate_player_adp_csv(all_players)
        
        logger.info("Data download process completed successfully!")
        return 0
        
    except KeyboardInterrupt:
        logger.info("Process interrupted by user")
        return 130
    except (NetworkError, APIError, AuthenticationError) as e:
        logger.error(f"API/Network error: {e.get_detailed_message()}")
        print(f"\nError: {e}")
        print("\nTroubleshooting:")
        if isinstance(e, AuthenticationError):
            print("- Check your .env file contains valid ESPN credentials")
            print("- Verify LEAGUE_ID, ESPN_S2, and SWID are correct")
        elif isinstance(e, NetworkError):
            print("- Check your internet connection")
            print("- Try again in a few minutes")
        return 1
    except (ConfigurationError, FileIOError, DataValidationError) as e:
        logger.error(f"Configuration/File error: {e.get_detailed_message()}")
        print(f"\nError: {e}")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        print(f"\nUnexpected error occurred: {e}")
        print("Check the log file for more details.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
