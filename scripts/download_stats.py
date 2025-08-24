#!/usr/bin/env python3
"""
Script to download weekly NFL player statistics with comprehensive error handling.

Downloads weekly player stats from nfl_data_py and ESPN API, combines them,
and saves to CSV with robust error handling.

@author Nicholas Wilde, 0xb299a622
@date 21 08 2025
@version 0.4.0
"""

import nfl_data_py as nfl
import pandas as pd
import os
import sys
import datetime
import argparse
import yaml
from espn_api.football import League
from dotenv import load_dotenv

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from fantasy_ai.errors import (
    APIError, AuthenticationError, ConfigurationError, 
    FileIOError, DataValidationError, wrap_exception
)
from fantasy_ai.utils.retry import retry
from fantasy_ai.utils.logging import setup_logging, get_logger

# Set up logging
setup_logging(level='INFO', format_type='console', log_file='logs/download_stats.log')
logger = get_logger(__name__)

# Load environment variables from .env file
load_dotenv()

# Load configuration from config.yaml
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


def validate_espn_credentials() -> tuple:
    """
    Validate ESPN API credentials and return them.
    
    Returns:
        Tuple of (league_id, espn_s2, swid)
        
    Raises:
        AuthenticationError: If credentials are missing or invalid
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
    
    logger.info("ESPN credentials validated successfully")
    return league_id_int, espn_s2, swid


def safe_create_directory(directory: str) -> None:
    """
    Safely create directory with proper error handling.
    
    Args:
        directory: Directory path to create
        
    Raises:
        FileIOError: If directory cannot be created
    """
    try:
        if directory and not os.path.exists(directory):
            os.makedirs(directory)
            logger.info(f"Created directory: {directory}")
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


@retry(max_attempts=3, base_delay=2.0, backoff_factor=2.0)
def download_nfl_data(years: list) -> pd.DataFrame:
    """
    Download NFL player stats from nfl_data_py with retry logic.
    
    Args:
        years: List of years to download data for
        
    Returns:
        DataFrame with NFL player stats
        
    Raises:
        APIError: If data download fails
        DataValidationError: If data is invalid
    """
    try:
        logger.info(f"Downloading NFL data for years: {years}")
        
        # Validate years
        current_year = datetime.datetime.now().year
        invalid_years = [y for y in years if y < 1999 or y > current_year + 1]
        if invalid_years:
            raise DataValidationError(
                f"Invalid years: {invalid_years}. Years must be between 1999 and {current_year + 1}",
                field_name="years",
                expected_type="list of valid years",
                actual_value=invalid_years
            )
        
        # Download weekly data
        df_nfl = nfl.import_weekly_data(years)
        if df_nfl.empty:
            raise DataValidationError(
                f"No data returned for years {years}",
                field_name="weekly_data",
                expected_type="non-empty DataFrame",
                actual_value="empty DataFrame"
            )
        
        # Download player IDs
        player_ids_df = nfl.import_ids()
        if player_ids_df.empty:
            logger.warning("No player IDs data available, continuing without ID mapping")
            return df_nfl
        
        # Process and merge data
        df_nfl['player_id'] = df_nfl['player_id'].astype(str)
        player_ids_df['espn_id'] = player_ids_df['espn_id'].astype(str)
        
        # Merge player names
        df_nfl = pd.merge(
            df_nfl, 
            player_ids_df[['espn_id', 'name']], 
            left_on='player_id', 
            right_on='espn_id', 
            how='left'
        )
        
        # Clean up columns
        if 'espn_id' in df_nfl.columns:
            df_nfl.drop(columns=['espn_id'], inplace=True)
        if 'name' in df_nfl.columns:
            df_nfl.drop(columns=['name'], inplace=True)
        
        # Reorder columns
        cols = df_nfl.columns.tolist()
        if 'player_display_name' in cols:
            cols.remove('player_display_name')
            df_nfl = df_nfl[['player_display_name'] + cols]
        
        logger.info(f"Successfully downloaded {len(df_nfl)} records from NFL data")
        return df_nfl
        
    except (DataValidationError, APIError):
        raise  # Re-raise our custom exceptions
    except Exception as e:
        error_msg = str(e).lower()
        if any(net_term in error_msg for net_term in ['connection', 'timeout', 'network', 'http']):
            raise wrap_exception(
                e, APIError,
                f"Network error downloading NFL data for years {years}",
                api_name="nfl_data_py"
            )
        else:
            raise wrap_exception(
                e, APIError,
                f"Failed to download NFL data for years {years}",
                api_name="nfl_data_py"
            )


@retry(max_attempts=3, base_delay=2.0, backoff_factor=2.0)
def get_espn_player_stats(years: list) -> pd.DataFrame:
    """
    Fetch K and D/ST stats from ESPN API for the given years with error handling.
    
    Args:
        years: List of years to fetch data for
        
    Returns:
        DataFrame with ESPN player stats
        
    Raises:
        APIError: If ESPN data fetch fails
        AuthenticationError: If credentials are invalid
    """
    try:
        logger.info(f"Fetching ESPN player stats for years: {years}")
        league_id, espn_s2, swid = validate_espn_credentials()
        
        espn_stats = []
        for year in years:
            try:
                logger.debug(f"Fetching ESPN data for year {year}")
                current_league = League(
                    league_id=league_id, 
                    year=year, 
                    espn_s2=espn_s2, 
                    swid=swid
                )
                
                for team in current_league.teams:
                    for player in team.roster:
                        try:
                            player_pos = player.position.replace('/', '').upper()
                            if player_pos in ['K', 'DST']:
                                if hasattr(player, 'stats') and player.stats:
                                    stats_breakdown = player.stats.get(0, {}).get('breakdown', {})
                                    player_data = {
                                        'player_display_name': player.name,
                                        'position': player.position,
                                        'proTeam': player.proTeam,
                                        'season': year,
                                    }
                                    # Add all stats from breakdown
                                    for stat_name, stat_value in stats_breakdown.items():
                                        player_data[stat_name] = stat_value
                                    espn_stats.append(player_data)
                        except Exception as e:
                            logger.warning(f"Error processing player {getattr(player, 'name', 'Unknown')}: {e}")
                            continue
                            
            except Exception as e:
                error_msg = str(e).lower()
                if any(auth_term in error_msg for auth_term in ['401', 'unauthorized', 'invalid', 'forbidden']):
                    raise AuthenticationError(
                        f"ESPN API authentication failed for year {year}. Please check your credentials.",
                        api_name="ESPN",
                        credential_type="S2/SWID",
                        original_error=e
                    )
                elif any(nf_term in error_msg for nf_term in ['404', 'not found', 'does not exist']):
                    logger.warning(f"League not found for year {year}, skipping")
                    continue
                else:
                    raise wrap_exception(
                        e, APIError,
                        f"Failed to fetch ESPN data for year {year}",
                        api_name="ESPN"
                    )
        
        df_espn = pd.DataFrame(espn_stats)
        logger.info(f"Successfully fetched {len(espn_stats)} ESPN player records")
        return df_espn
        
    except (AuthenticationError, APIError):
        raise  # Re-raise our custom exceptions
    except Exception as e:
        raise wrap_exception(
            e, APIError,
            f"Unexpected error fetching ESPN player stats",
            api_name="ESPN"
        )


def save_combined_data(df_combined: pd.DataFrame, output_file: str) -> None:
    """
    Save combined DataFrame to CSV with error handling.
    
    Args:
        df_combined: Combined DataFrame to save
        output_file: Output file path
        
    Raises:
        FileIOError: If file cannot be written
    """
    try:
        logger.debug(f"Saving combined data to {output_file}")
        
        # Ensure output directory exists
        output_dir = os.path.dirname(output_file)
        if output_dir:
            safe_create_directory(output_dir)
        
        # Save to CSV
        df_combined.to_csv(output_file, index=False)
        logger.info(f"Successfully saved {len(df_combined)} records to {output_file}")
        
    except PermissionError as e:
        raise FileIOError(
            f"Permission denied writing to {output_file}",
            file_path=output_file,
            operation="write",
            original_error=e
        )
    except Exception as e:
        raise wrap_exception(
            e, FileIOError,
            f"Failed to save data to {output_file}",
            file_path=output_file,
            operation="write"
        )


def update_last_updated_log() -> None:
    """
    Update the last_updated.log file with error handling.
    
    Raises:
        FileIOError: If log file cannot be written
    """
    log_file_path = "data/last_updated.log"
    try:
        # Ensure data directory exists
        safe_create_directory("data")
        
        now = datetime.datetime.now()
        log_content = f"Player stats last updated: {now.strftime('%Y-%m-%d %H:%M:%S')}"
        
        with open(log_file_path, "w") as log_file:
            log_file.write(log_content)
        
        logger.info(f"Updated {log_file_path}")
        
    except PermissionError as e:
        raise FileIOError(
            f"Permission denied writing to {log_file_path}",
            file_path=log_file_path,
            operation="write",
            original_error=e
        )
    except Exception as e:
        raise wrap_exception(
            e, FileIOError,
            f"Failed to update log file {log_file_path}",
            file_path=log_file_path,
            operation="write"
        )


def download_and_save_weekly_stats(years: list, output_file: str = "data/player_stats.csv") -> int:
    """
    Main function to download and save weekly stats with comprehensive error handling.
    
    Args:
        years: List of years to download data for
        output_file: Output file path
        
    Returns:
        Exit code (0 for success, 1 for error)
    """
    try:
        logger.info(f"Starting weekly data download for seasons: {years}")
        
        # Step 1: Download NFL data
        logger.info("Step 1: Downloading NFL player data")
        df_nfl = download_nfl_data(years)
        
        # Step 2: Download ESPN data
        logger.info("Step 2: Fetching ESPN player data")
        df_espn = get_espn_player_stats(years)
        
        # Step 3: Combine data
        logger.info("Step 3: Combining data")
        # Filter out K and DST from NFL data to prioritize ESPN data
        df_nfl_filtered = df_nfl[~df_nfl['position'].isin(['K', 'DST'])].copy()
        df_combined = pd.concat([df_nfl_filtered, df_espn], ignore_index=True, sort=False)
        
        if df_combined.empty:
            raise DataValidationError(
                "Combined dataset is empty after processing",
                field_name="combined_data",
                expected_type="non-empty DataFrame",
                actual_value="empty DataFrame"
            )
        
        # Step 4: Save combined data
        logger.info("Step 4: Saving combined data")
        save_combined_data(df_combined, output_file)
        
        # Step 5: Update log
        logger.info("Step 5: Updating log file")
        update_last_updated_log()
        
        logger.info(f"Download complete! Combined data for {len(years)} seasons saved to '{output_file}'.")
        print(f"✓ Download complete! Combined data for {len(years)} seasons saved to '{output_file}'.")
        return 0
        
    except KeyboardInterrupt:
        logger.info("Process interrupted by user")
        print("\nProcess interrupted by user.")
        return 130
    except AuthenticationError as e:
        logger.error(f"Authentication error: {e.get_detailed_message()}")
        print(f"\n❌ Authentication Error: {e}")
        print("\nTroubleshooting:")
        print("- Check your .env file contains valid ESPN credentials")
        print("- Verify LEAGUE_ID, ESPN_S2, and SWID are correct")
        return 1
    except ConfigurationError as e:
        logger.error(f"Configuration error: {e.get_detailed_message()}")
        print(f"\n❌ Configuration Error: {e}")
        print("\nTroubleshooting:")
        print("- Run 'task init' to create configuration file")
        print("- Check config.yaml for valid settings")
        return 1
    except (APIError, DataValidationError) as e:
        logger.error(f"API/Data error: {e.get_detailed_message()}")
        print(f"\n❌ Error: {e}")
        print("\nTroubleshooting:")
        print("- Check your internet connection")
        print("- Verify the years specified are valid")
        return 1
    except FileIOError as e:
        logger.error(f"File I/O error: {e.get_detailed_message()}")
        print(f"\n❌ File Error: {e}")
        print("\nTroubleshooting:")
        print("- Check file permissions in the current directory")
        print("- Make sure the data/ directory is writable")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        print(f"\n❌ Unexpected error occurred: {e}")
        print("Check the log file for more details.")
        return 1


def main() -> int:
    """Entry point with proper error handling."""
    try:
        parser = argparse.ArgumentParser(description="Download weekly player stats for specified years.")
        
        # Load default years from config
        try:
            config = load_config()
            default_years = config.get('league_settings', {}).get(
                'data_years', 
                [datetime.datetime.now().year - 1, datetime.datetime.now().year]
            )
        except Exception as e:
            logger.warning(f"Could not load config, using default years: {e}")
            default_years = [datetime.datetime.now().year - 1, datetime.datetime.now().year]
        
        parser.add_argument(
            "--years",
            type=int,
            nargs='+',
            default=default_years,
            help="A list of years to download data for (e.g., --years 2023 2024). "
                 "If not specified, defaults to the years defined in config.yaml."
        )
        
        parser.add_argument(
            "--output",
            type=str,
            default="data/player_stats.csv",
            help="Output file path (default: data/player_stats.csv)"
        )
        
        args = parser.parse_args()
        
        # Run the function
        return download_and_save_weekly_stats(args.years, args.output)
        
    except Exception as e:
        logger.error(f"Error in main: {e}", exc_info=True)
        print(f"❌ Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
