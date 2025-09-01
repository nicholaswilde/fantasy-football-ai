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
import nfl_data_py as nfl
import argparse

# Add src to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from fantasy_ai.errors import (
    NetworkError,
    APIError,
    AuthenticationError,
    ConfigurationError,
    FileOperationError as FileIOError,
    DataValidationError,
    wrap_exception
)
from fantasy_ai.utils.retry import retry
from fantasy_ai.utils.logging import setup_logging, get_logger
from scripts.utils import load_config

# Set up logging
setup_logging(level='INFO', format_type='console', log_file='logs/download_data.log')
logger = get_logger(__name__)

# Load environment variables
load_dotenv()

# Configuration file path
CONFIG_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', 'config.yaml'
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


@retry(
    max_attempts=3,
    base_delay=1.0,
    backoff_factor=2.0,
    retryable_exceptions=(APIError, NetworkError)
)
def download_adp_data():
    """
    Fetches ADP data from Fantasy Football Calculator API, processes it, and saves it in the required format.
    """
    CONFIG = load_config()
    ADP_URL = f"https://fantasyfootballcalculator.com/api/v1/adp/standard?teams={CONFIG['league_settings']['number_of_teams']}&year={CONFIG['league_settings']['year']}&position=all"
    ADP_OUTPUT_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'player_adp.csv')

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

def get_team_roster(roster_file: str = None) -> list:
    """
    Reads the team roster from a Markdown table file and returns a list of player names with error handling.
    
    Args:
        roster_file: Path to the my_team.md file. If None, uses default path.
        
    Returns:
        List of player names.
        
    Raises:
        FileOperationError: If the file cannot be read or accessed.
        DataValidationError: If the file content is malformed.
    """
    if roster_file is None:
        roster_file = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'my_team.md'
        )
    
    if not os.path.exists(roster_file):
        logger.warning(f"Roster file not found at {roster_file}, returning empty roster.")
        return []
    
    roster = []
    try:
        with open(roster_file, "r", encoding='utf-8') as f:
            lines = f.readlines()
            # Skip header and separator lines (first 3 lines after the comment and title)
            # So, actual data starts from line 5 (index 4)
            if len(lines) > 4:
                for line in lines[4:]:
                    line = line.strip()
                    if line.startswith('|') and '|' in line[1:]:
                        parts = [p.strip() for p in line.split('|')]
                        if len(parts) > 2: # Ensure there's at least a player name column
                            player_name = parts[1] # Assuming player name is in the second column
                            if player_name: # Ensure it's not empty
                                roster.append(player_name)
        logger.info(f"Successfully loaded {len(roster)} players from roster file.")
        return roster
    except FileNotFoundError as e:
        raise FileOperationError(
            f"Roster file not found: {roster_file}",
            file_path=roster_file,
            operation="read",
            original_error=e
        )
    except PermissionError as e:
        raise FileOperationError(
            f"Permission denied reading roster file: {roster_file}",
            file_path=roster_file,
            operation="read",
            original_error=e
        )
    except UnicodeDecodeError as e:
        raise DataValidationError(
            f"Cannot decode roster file (encoding issue): {roster_file}",
            field_name="roster_file_encoding",
            expected_type="UTF-8 encoded text",
            actual_value="unreadable encoding",
            original_error=e
        )
    except Exception as e:
        raise wrap_exception(
            e, FileIOError,
            f"Failed to read roster file {roster_file}",
            file_path=roster_file,
            operation="read"
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
        NetworkError: If there is a network connectivity issue.
    """
    try:
        logger.info(f"Downloading NFL data for years: {years}")
        
        # Validate years
        current_year = datetime.now().year
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
                e, NetworkError,
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
        NetworkError: If there is a network connectivity issue.
    """
    try:
        logger.info(f"Fetching ESPN player stats for years: {years}")
        league_id, espn_s2, swid, year = validate_espn_credentials()
        
        espn_stats = []
        for year_to_fetch in years:
            try:
                logger.debug(f"Fetching ESPN data for year {year_to_fetch}")
                current_league = League(
                    league_id=league_id, 
                    year=year_to_fetch, 
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
                                        'season': year_to_fetch,
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
                        f"ESPN API authentication failed for year {year_to_fetch}. Please check your credentials.",
                        api_name="ESPN",
                        credential_type="S2/SWID",
                        original_error=e
                    )
                elif any(nf_term in error_msg for nf_term in ['404', 'not found', 'does not exist']):
                    logger.warning(f"League not found for year {year_to_fetch}, skipping")
                    continue
                elif any(net_term in error_msg for net_term in ['connection', 'timeout', 'network', 'http']):
                    raise NetworkError(
                        f"Network error fetching ESPN data for year {year_to_fetch}: {e}",
                        api_name="ESPN",
                        original_error=e
                    )
                else:
                    raise wrap_exception(
                        e, APIError,
                        f"Failed to fetch ESPN data for year {year_to_fetch}",
                        api_name="ESPN"
                    )
        
        df_espn = pd.DataFrame(espn_stats)
        logger.info(f"Successfully fetched {len(espn_stats)} ESPN player records")
        return df_espn
        
    except (AuthenticationError, APIError, NetworkError):
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
    except IOError as e:
        raise FileIOError(
            f"IO error writing to {output_file}: {e}",
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
        
        now = datetime.now()
        log_content = f"Player stats last updated: {now.strftime('%Y-%m-%d %H:%M:%S')}"
        
        with open(log_file_path, "w", encoding='utf-8') as log_file:
            log_file.write(log_content)
        
        logger.info(f"Updated {log_file_path}")
        
    except PermissionError as e:
        raise FileIOError(
            f"Permission denied writing to {log_file_path}",
            file_path=log_file_path,
            operation="write",
            original_error=e
        )
    except IOError as e:
        raise FileIOError(
            f"IO error writing to {log_file_path}: {e}",
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


def download_and_save_weekly_stats(years: list, output_file: str) -> int:
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
        
        if not df_espn.empty:
            df_combined = pd.concat([df_nfl_filtered, df_espn], ignore_index=True, sort=False)
        else:
            df_combined = df_nfl_filtered
        
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
    except (APIError, DataValidationError, NetworkError) as e:
        logger.error(f"API/Data/Network error: {e.get_detailed_message()}")
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


import argparse

def main():
    """Main function with comprehensive error handling."""
    parser = argparse.ArgumentParser(description="Download fantasy football data.")
    parser.add_argument(
        "data_type",
        choices=["all", "stats", "projections", "adp"],
        help="The type of data to download.",
        nargs='?',
        default="all"
    )
    parser.add_argument(
        "--years",
        type=int,
        nargs='+',
        help="A list of years to download data for (e.g., --years 2023 2024). "
             "If not specified, defaults to the years defined in config.yaml."
    )
    args = parser.parse_args()

    try:
        logger.info(f"Starting Fantasy Football AI data download process for: {args.data_type}")

        if args.data_type == "all" or args.data_type == "projections":
            logger.info("Step 1: Fetching player data from Sleeper API")
            all_players = fetch_sleeper_data()
            if not all_players:
                logger.error("No player data retrieved from Sleeper API")
                return 1
            logger.info("Step 2: Generating player projections CSV")
            generate_player_projections_csv(all_players)

        if args.data_type == "all" or args.data_type == "adp":
            logger.info("Step 3: Generating player ADP CSV")
            download_adp_data()

        if args.data_type == "all" or args.data_type == "stats":
            logger.info("Step 4: Downloading weekly player stats")
            config = load_config()
            if args.years:
                years = args.years
            else:
                years = config.get('league_settings', {}).get(
                    'data_years',
                    [datetime.now().year - 1, datetime.now().year]
                )
            output_file = config.get('file_paths', {}).get('player_stats', 'data/player_stats.csv')
            download_and_save_weekly_stats(years, output_file)

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