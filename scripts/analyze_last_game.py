#!/usr/bin/env python3
################################################################################
#
# Script Name: analyze_last_game.py
# ----------------
# Analyzes the user's last fantasy football game, evaluates performance,
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
setup_logging(level='INFO', format_type='console', log_file='logs/analyze_last_game.log')
logger = get_logger(__name__)

from analysis import ask_llm, configure_llm_api, calculate_fantasy_points

# Load environment variables
load_dotenv()

# Configuration file path
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


def analyze_last_game() -> str:
    """
    Analyzes the user's last game performance and suggests improvements.
    
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
    logger.info("Starting last game analysis.")
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
    try:
        my_team_players_raw = get_my_team_roster(MY_TEAM_FILE)
        if not my_team_players_raw:
            raise DataValidationError(
                f"No players found in {MY_TEAM_FILE}. Please ensure your team roster is correctly set up.",
                field_name="my_team_roster",
                expected_type="non-empty list",
                actual_value="empty list"
            )

        my_team_players_normalized = [normalize_player_name(p) for p in my_team_players_raw]

        current_year_stats = player_stats_df[player_stats_df['season'] == league_year]

        if current_year_stats.empty:
            raise DataValidationError(
                f"No player stats found for the year {league_year}. Please ensure data is available for this season.",
                field_name="current_year_stats",
                expected_type="non-empty DataFrame",
                actual_value="empty DataFrame"
            )

        last_week = current_year_stats['week'].max()
        if pd.isna(last_week):
            raise DataValidationError(
                f"No weekly data found for the year {league_year}. Cannot determine last week.",
                field_name="last_week",
                expected_type="numeric week value",
                actual_value="NaN"
            )

        logger.info(f"Analyzing performance for Week {int(last_week)} of the {league_year} season...")

        last_week_stats = current_year_stats[current_year_stats['week'] == last_week]
        if last_week_stats.empty:
            raise DataValidationError(
                f"No stats found for Week {int(last_week)} of the {league_year} season.",
                field_name="last_week_stats",
                expected_type="non-empty DataFrame",
                actual_value="empty DataFrame"
            )

        my_team_last_week_stats = last_week_stats[last_week_stats['player_name'].isin(my_team_players_normalized)]
        if my_team_last_week_stats.empty:
            logger.warning(f"No stats found for your team players in Week {int(last_week)}.")
            # Attempt to calculate fantasy points even if some players are missing stats
            my_team_total_points = 0.0
        else:
            my_team_last_week_stats = calculate_fantasy_points(my_team_last_week_stats.copy())
            my_team_total_points = my_team_last_week_stats['fantasy_points'].sum()

        logger.info(f"Your team scored {my_team_total_points:.2f} points in Week {int(last_week)}.")
    except (FileOperationError, DataValidationError) as e:
        logger.error(f"Error processing team data: {e.get_detailed_message()}")
        raise

    league_settings_str = yaml.dump(league_settings, default_flow_style=False)
    roster_settings_str = yaml.dump(roster_settings, default_flow_style=False)
    scoring_rules_str = yaml.dump(scoring_rules, default_flow_style=False)

    player_performance_details = ""
    if not my_team_last_week_stats.empty:
        player_performance_details = my_team_last_week_stats[['player_name', 'fantasy_points', 'position']].to_markdown(index=False)
    else:
        player_performance_details = "No individual player stats found for your team this week."

    llm_prompt = f"""
    Analyze my fantasy football team's performance for Week {int(last_week)} of the {league_year} season.

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

    **Analysis Details:**

    My team's roster:
    {', '.join(my_team_players_raw)}

    My team's fantasy points for Week {int(last_week)}: {my_team_total_points:.2f}

    Here are the individual player performances from my team for Week {int(last_week)}:
{player_performance_details}

    Based on this information, please provide:
    1. An evaluation of my team's performance in Week {int(last_week)}. Did I do well or poorly, and why?
    2. Specific suggestions for improvement, considering potential waiver wire pickups, trade targets, or lineup adjustments.
    3. Identify any underperforming players on my team.
    4. Suggest potential strategies for the upcoming weeks.
    """

    logger.info("Asking the AI for analysis...")
    configure_llm_api()
    analysis_result = ask_llm(llm_prompt)
    return analysis_result


def main():
    """Main function to run the last game analysis and handle errors."""
    try:
        analysis_output = analyze_last_game()
        if analysis_output:
            print("\n--- AI Analysis ---")
            print(analysis_output)
            print("\n-------------------")
            return 0
        else:
            logger.error("AI analysis returned empty.")
            return 1
    except (ConfigurationError, FileOperationError, DataValidationError, APIError, AuthenticationError, NetworkError) as e:
        logger.error(f"Last game analysis error: {e.get_detailed_message()}")
        print(f"\n❌ Error during last game analysis: {e}")
        return 1
    except Exception as e:
        logger.critical(f"An unhandled critical error occurred: {e}", exc_info=True)
        print(f"\n❌ An unexpected critical error occurred: {e}")
        print("Please check the log file for more details.")
        return 1


if __name__ == "__main__":
    sys.exit(main())