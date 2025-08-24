#!/usr/bin/env python3
################################################################################
#
# Script Name: get_my_team.py
# ----------------
# Fetches the user's fantasy football team from ESPN and saves it to a Markdown file.
#
# @author Nicholas Wilde, 0xb299a622
# @date 23 08 2025
# @version 0.5.0
#
################################################################################

import os
from datetime import datetime
from espn_api.football import League
from dotenv import load_dotenv
import yaml
from tabulate import tabulate
import sys

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from fantasy_ai.errors import (
    FileOperationError,
    DataValidationError,
    AuthenticationError,
    APIError,
    NetworkError,
    ConfigurationError,
    wrap_exception
)
from fantasy_ai.utils.logging import setup_logging, get_logger
from fantasy_ai.utils.retry import retry

# Set up logging
setup_logging(level='INFO', format_type='console', log_file='logs/get_my_team.log')
logger = get_logger(__name__)

# Load environment variables from .env file
load_dotenv()

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

@retry(max_attempts=3, base_delay=1.0, backoff_factor=2.0, retryable_exceptions=(APIError, NetworkError))
def get_my_team():
    """
    Fetches the user's fantasy football team and formats it as a markdown file.
    """
    league_id = os.getenv("LEAGUE_ID")
    espn_s2 = os.getenv("ESPN_S2")
    swid = os.getenv("SWID")
    year = CONFIG.get('league_settings', {}).get('year', datetime.now().year)

    if not all([league_id, espn_s2, swid]):
        raise AuthenticationError(
            "Missing required environment variables. Please set LEAGUE_ID, "
            "ESPN_S2, and SWID in your .env file.",
            api_name="ESPN"
        )

    try:
        league = League(league_id=int(league_id), year=year, espn_s2=espn_s2, swid=swid)

        # Get team from config
        my_team_id = CONFIG.get('my_team_id')
        if not my_team_id:
            raise ConfigurationError("my_team_id not found in config.yaml. Please run identify_my_team.py first.", config_key="my_team_id")

        team = None
        for t in league.teams:
            if t.team_id == my_team_id:
                team = t
                break
        
        if team is None:
            raise DataValidationError(f"Could not find team with ID {my_team_id}", field_name="my_team_id")

        roster_data = []
        for player in team.roster:
            roster_data.append([player.name, player.position, player.proTeam])

        headers = ["Player Name", "Position", "NFL Team"]
        markdown_table = tabulate(roster_data, headers=headers, tablefmt="pipe")

        with open("data/my_team.md", "w") as f:
            now = datetime.now()
            dt_string = now.strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"<!-- Last updated: {dt_string} -->\n")
            f.write("# My Team\n\n")
            f.write(markdown_table)
            f.write("\n")

        logger.info("Successfully created data/my_team.md")
        print("Successfully created data/my_team.md")

    except Exception as e:
        error_msg = str(e).lower()
        if any(auth_term in error_msg for auth_term in ['401', 'unauthorized', 'invalid', 'forbidden']):
            raise AuthenticationError(
                "ESPN API authentication failed. Please check your ESPN_S2 and SWID credentials.",
                api_name="ESPN",
                credential_type="S2/SWID",
                original_error=e
            )
        elif any(net_term in error_msg for net_term in ['timeout', 'connection', 'network', 'http']):
            raise NetworkError(
                f"Network error connecting to ESPN API: {e}",
                api_name="ESPN",
                original_error=e
            )
        else:
            raise wrap_exception(
                e, APIError,
                f"An unexpected error occurred while fetching your team: {e}",
                api_name="ESPN"
            )

def main():
    """Main function to fetch team and handle errors."""
    try:
        get_my_team()
        return 0
    except (ConfigurationError, AuthenticationError, APIError, NetworkError, DataValidationError, FileOperationError) as e:
        logger.error(f"Get my team error: {e.get_detailed_message()}")
        print(f"\n❌ Error getting your team: {e}")
        return 1
    except Exception as e:
        logger.critical(f"An unhandled critical error occurred: {e}", exc_info=True)
        print(f"\n❌ An unexpected critical error occurred: {e}")
        print("Please check the log file for more details.")
        return 1

if __name__ == "__main__":
    sys.exit(main())