#!/usr/bin/env python3
################################################################################
#
# Script Name: analyze_next_game.py
# ----------------
# Analyzes the user's next fantasy football game, evaluates performance,
# and suggests improvements.
#
# @author Nicholas Wilde, 0xb299a622
# @date 23 August 2025
# @version 0.2.0
#
################################################################################

import os
import pandas as pd
import yaml
from dotenv import load_dotenv
from espn_api.football import League
from datetime import datetime
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

# Set up logging
setup_logging(level='INFO', format_type='console', log_file='logs/analyze_next_game.log')
logger = get_logger(__name__)

from analysis import ask_llm, configure_llm_api

# Load environment variables
load_dotenv()

# Configuration file paths
CONFIG_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', 'config.yaml'
)
PLAYER_STATS_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'player_stats.csv'
)
MY_TEAM_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'my_team.md'
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


def get_my_team_roster(file_path: str) -> list:
    """
    Reads the my_team.md file (Markdown table format) and extracts player names with error handling.
    
    Args:
        file_path: Path to the my_team.md file.
        
    Returns:
        List of player names.
        
    Raises:
        FileOperationError: If the file cannot be read or accessed.
        DataValidationError: If the file content is malformed.
    """
    players = []
    if not os.path.exists(file_path):
        logger.warning(f"My team roster file not found at {file_path}, returning empty list.")
        return []

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
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
                                players.append(player_name)
        logger.info(f"Successfully loaded {len(players)} players from roster file.")
        return players
    except FileNotFoundError as e:
        raise FileOperationError(
            f"My team roster file not found: {file_path}",
            file_path=file_path,
            operation="read",
            original_error=e
        )
    except PermissionError as e:
        raise FileOperationError(
            f"Permission denied reading my team roster file: {file_path}",
            file_path=file_path,
            operation="read",
            original_error=e
        )
    except UnicodeDecodeError as e:
        raise DataValidationError(
            f"Cannot decode my team roster file (encoding issue): {file_path}",
            field_name="my_team_file_encoding",
            expected_type="UTF-8 encoded text",
            actual_value="unreadable encoding",
            original_error=e
        )
    except Exception as e:
        raise wrap_exception(
            e, FileOperationError,
            f"Failed to read my team roster file {file_path}",
            file_path=file_path,
            operation="read"
        )


def get_next_opponent_roster() -> tuple[list, str]:
    """
    Fetches the user's next opponent's roster from ESPN with error handling.
    
    Returns:
        Tuple of (list of opponent player names, error message or None).
        
    Raises:
        ConfigurationError: If config settings are missing or invalid.
        AuthenticationError: If ESPN API credentials are missing or invalid.
        APIError: If there's an issue with the ESPN API response.
        NetworkError: If there's a network connectivity issue.
    """
    config = load_config()
    my_team_id = config.get('my_team_id')
    if not my_team_id:
        raise ConfigurationError(
            "'my_team_id' not found in config.yaml. Please run 'task identify_my_team' to set it.",
            config_key="my_team_id"
        )

    league_id = os.getenv("LEAGUE_ID")
    espn_s2 = os.getenv("ESPN_S2")
    swid = os.getenv("SWID")
    
    if not all([league_id, espn_s2, swid]):
        raise AuthenticationError(
            "Missing ESPN API credentials (LEAGUE_ID, ESPN_S2, SWID) in .env. Cannot fetch opponent roster.",
            api_name="ESPN"
        )

    try:
        league = League(league_id=int(league_id), year=datetime.now().year, espn_s2=espn_s2, swid=swid)
        current_week = league.current_week
        if current_week == 0:
            return [], "The fantasy football season has not started yet."
        matchups = league.scoreboard(week=current_week)
        
        my_matchup = None
        for matchup in matchups:
            if matchup.home_team.team_id == my_team_id or matchup.away_team.team_id == my_team_id:
                my_matchup = matchup
                break

        if my_matchup:
            if my_matchup.home_team.team_id == my_team_id:
                opponent = my_matchup.away_team
            else:
                opponent = my_matchup.home_team
            return [player.name for player in opponent.roster], None
        else:
            return [], "Could not determine next opponent for the current week."

    except Exception as e:
        error_msg = str(e).lower()
        if any(auth_term in error_msg for auth_term in ['401', 'unauthorized', 'invalid', 'forbidden']):
            raise AuthenticationError(
                "ESPN API authentication failed. Please check your ESPN_S2 and SWID credentials.",
                api_name="ESPN",
                credential_type="S2/SWID",
                original_error=e
            )
        elif any(net_term in error_msg for net_term in ['timeout', 'connection', 'network']):
            raise NetworkError(
                f"Network error connecting to ESPN API: {e}",
                api_name="ESPN",
                original_error=e
            )
        else:
            raise wrap_exception(
                e, APIError,
                f"An unexpected error occurred while fetching opponent's roster: {e}",
                api_name="ESPN"
            )


def normalize_player_name(name: str) -> str:
    """
    Normalizes player names to match the format in player_stats.csv (e.g., 'Patrick Mahomes' to 'P.Mahomes').
    
    Args:
        name: The player's full name.
        
    Returns:
        The normalized player name.
    """
    parts = name.split(' ')
    if len(parts) > 1:
        return f"{parts[0][0]}.{' '.join(parts[1:])}"
    return name


def analyze_next_game(opponent_players_raw: list = None) -> str:
    """
    Analyzes the next game and provides suggestions to win.
    If opponent_players_raw is None, it attempts to fetch the roster automatically.
    
    Returns:
        AI analysis as a string.
        
    Raises:
        ConfigurationError: If config settings are missing or invalid.
        FileOperationError: If data files cannot be read.
        DataValidationError: If data files are malformed or empty.
        APIError: If LLM API call fails.
        AuthenticationError: If LLM API key is missing.
        NetworkError: If there's a network issue during LLM API call.
    """
    logger.info("Starting next game analysis.")
    if opponent_players_raw is None:
        opponent_players_raw, error_message = get_next_opponent_roster()
        if error_message:
            # If get_next_opponent_roster returns an error message, it means an exception was already raised
            # and caught within that function, or it's a non-critical warning.
            # Here, we'll re-raise if it's a critical error that wasn't handled by custom exceptions.
            # If it's just a message, we'll return it.
            if not opponent_players_raw: # If opponent_players_raw is empty, it means a critical error occurred
                raise wrap_exception(Exception(error_message), APIError, "Failed to get opponent roster.")

    config = load_config()
    league_settings = config.get('league_settings', {})
    roster_settings = config.get('roster_settings', {})
    scoring_rules = config.get('scoring_rules', {})
    league_year = league_settings.get('year')

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
            "Player stats DataFrame is empty after loading. Cannot proceed with analysis.",
            field_name="player_stats_df",
            expected_type="non-empty DataFrame",
            actual_value="empty DataFrame"
        )

    my_team_players_raw = get_my_team_roster(MY_TEAM_FILE)
    if not my_team_players_raw:
        raise DataValidationError(
            f"No players found in {MY_TEAM_FILE}. Please ensure your team roster is correctly set up.",
            field_name="my_team_roster",
            expected_type="non-empty list",
            actual_value="empty list"
        )

    my_team_players_normalized = [normalize_player_name(p) for p in my_team_players_raw]

    if not opponent_players_raw:
        raise DataValidationError(
            "Opponent players list is empty. Cannot proceed with analysis.",
            field_name="opponent_players_raw",
            expected_type="non-empty list",
            actual_value="empty list"
        )
    opponent_players_normalized = [normalize_player_name(p) for p in opponent_players_raw]

    current_year_stats = player_stats_df[player_stats_df['season'] == league_year]

    if current_year_stats.empty:
        raise DataValidationError(
            f"No player stats found for the year {league_year}. Please ensure data is available for this season.",
            field_name="current_year_stats",
            expected_type="non-empty DataFrame",
            actual_value="empty DataFrame"
        )

    my_team_avg_points = current_year_stats[current_year_stats['player_name'].isin(my_team_players_normalized)]['fantasy_points'].mean()
    opponent_avg_points = current_year_stats[current_year_stats['player_name'].isin(opponent_players_normalized)]['fantasy_points'].mean()

    league_settings_str = yaml.dump(league_settings, default_flow_style=False)
    roster_settings_str = yaml.dump(roster_settings, default_flow_style=False)
    scoring_rules_str = yaml.dump(scoring_rules, default_flow_style=False)

    llm_prompt = f"""
    Analyze the upcoming fantasy football game based on the following information.

    **League Context:**

    **1. League Settings:**
    ```yaml
    {league_settings_str}
    ```

    **2. Roster Settings:**
    ```yaml
    {roster_settings_str}
    ```

    **3. Scoring Rules:**
    ```yaml
    {scoring_rules_str}
    ```

    **Matchup Details:**

    My Team Roster:
    {', '.join(my_team_players_raw)}
    My Team Average Fantasy Points (Season-to-Date): {my_team_avg_points:.2f}

    Opponent Team Roster:
    {', '.join(opponent_players_raw)}
    Opponent Team Average Fantasy Points (Season-to-Date): {opponent_avg_points:.2f}

    Based on this, please provide:
    1. An assessment of my team's strengths and weaknesses against the opponent.
    2. Key player matchups to watch.
    3. Strategic suggestions to win the game, considering potential lineup changes, waiver wire pickups, or trade targets.
    4. Identify any players on either team who might be overperforming or underperforming based on their season averages.

    Important Note: This analysis is based on season-to-date averages. For more accurate predictions, weekly projections would be ideal, but are not available for this analysis.
    """

    logger.info("Asking the AI for analysis...")
    configure_llm_api()
    analysis_result = ask_llm(llm_prompt)
    return analysis_result


def main():
    """Main function to run the next game analysis and handle errors."""
    try:
        analysis_output = analyze_next_game()
        if analysis_output:
            print("\n--- AI Analysis ---")
            print(analysis_output)
            print("\n-------------------")
            return 0
        else:
            logger.error("AI analysis returned empty.")
            return 1
    except (ConfigurationError, FileOperationError, DataValidationError, APIError, AuthenticationError, NetworkError) as e:
        logger.error(f"Next game analysis error: {e.get_detailed_message()}")
        print(f"\n❌ Error during next game analysis: {e}")
        print("\nTroubleshooting:")
        if isinstance(e, ConfigurationError):
            print("- Check config.yaml for valid settings, especially 'league_settings.year' and 'my_team_id'.")
        elif isinstance(e, FileOperationError):
            print("- Ensure data files (player_stats.csv, my_team.md) exist and are accessible.")
            print("- Run 'task download_stats' and 'task get_my_team' to prepare data.")
        elif isinstance(e, DataValidationError):
            print("- Check the format and content of your data files.")
        elif isinstance(e, AuthenticationError):
            print("- Verify your LLM API key and ESPN credentials are correctly set in your .env file.")
        elif isinstance(e, NetworkError):
            print("- Check your internet connection.")
        elif isinstance(e, APIError):
            print("- There might be an issue with the LLM or ESPN API service. Try again later.")
        return 1
    except Exception as e:
        logger.critical(f"An unhandled critical error occurred: {e}", exc_info=True)
        print(f"\n❌ An unexpected critical error occurred: {e}")
        print("Please check the log file for more details.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
