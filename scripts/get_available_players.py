#!/usr/bin/env python3
################################################################################
#
# Script Name: get_available_players.py
# ----------------
# Fetches available players from an ESPN fantasy football league.
#
# @author Nicholas Wilde, 0xb299a622
# @date 2025-08-20
# @version 0.1.0
#
################################################################################

import os
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
from espn_api.football import League
import sys

# Add src to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from fantasy_ai.errors import (
    FileOperationError,
    DataValidationError,
    AuthenticationError,
    APIError,
    NetworkError,
    wrap_exception
)
from scripts.utils import load_config
from fantasy_ai.utils.logging import setup_logging, get_logger
from fantasy_ai.utils.retry import retry
from scripts.utils import normalize_player_name

# Set up logging
setup_logging(level='INFO', format_type='console', log_file='logs/get_available_players.log')
logger = get_logger(__name__)

@retry(max_attempts=3, base_delay=1.0, backoff_factor=2.0, retryable_exceptions=(APIError, NetworkError))
def get_available_players(league_id: int, espn_s2: str, swid: str) -> None:
    """
    Fetches available players from an ESPN fantasy football league 
    and saves them to a CSV file with error handling.
    
    Args:
        league_id: ESPN league ID.
        espn_s2: ESPN S2 cookie.
        swid: ESPN SWID cookie.
        
    Raises:
        APIError: If there's an issue with the ESPN API response.
        NetworkError: If there's a network connectivity issue.
        DataValidationError: If no free agents are found.
        FileOperationError: If the CSV file cannot be written.
    """
    logger.info("Fetching available players from ESPN API...")
    output_path = 'data/available_players.csv'

    try:
        # Initialize League object
        league = League(league_id=league_id, year=datetime.now().year, espn_s2=espn_s2, swid=swid)

        # Get free agents
        free_agents = league.free_agents(size=1000)

        # Get all rostered players in the league
        rostered_player_names = set()
        for team in league.teams:
            for player in team.roster:
                rostered_player_names.add(normalize_player_name(player.name))

        # Filter free agents to only include those not on any team's roster
        truly_available_players = []
        for player in free_agents:
            normalized_free_agent_name = normalize_player_name(player.name)
            if normalized_free_agent_name not in rostered_player_names:
                truly_available_players.append(player)

        if not truly_available_players:
            raise DataValidationError(
                "No truly available free agents found in the league after filtering rostered players.",
                field_name="truly_available_players",
                expected_type="non-empty list",
                actual_value="empty list"
            )

        # Convert player data to a list of dictionaries
        players_data = []
                # Get all rostered players in the league
        rostered_player_names = set()
        for team in league.teams:
            for player in team.roster:
                rostered_player_names.add(player.name)

        # Filter free agents to only include those not on any team's roster
        truly_available_players = [
            player for player in free_agents if player.name not in rostered_player_names
        ]

        if not truly_available_players:
            raise DataValidationError(
                "No truly available free agents found in the league after filtering rostered players.",
                field_name="truly_available_players",
                expected_type="non-empty list",
                actual_value="empty list"
            )

        # Convert player data to a list of dictionaries
        players_data = []
                # Get all rostered players in the league
        rostered_player_names = set()
        for team in league.teams:
            for player in team.roster:
                rostered_player_names.add(normalize_player_name(player.name))
        logger.info(f"Rostered players in league: {list(rostered_player_names)}")

        # Filter free agents to only include those not on any team's roster
        truly_available_players = [
            player for player in free_agents if normalize_player_name(player.name) not in rostered_player_names
        ]
        logger.info(f"Truly available players after filtering: {[normalize_player_name(p.name) for p in truly_available_players]}")

        if not truly_available_players:
            raise DataValidationError(
                "No truly available free agents found in the league after filtering rostered players.",
                field_name="truly_available_players",
                expected_type="non-empty list",
                actual_value="empty list"
            )

        # Convert player data to a list of dictionaries
        players_data = []
        for player in truly_available_players: # Use truly_available_players here
            players_data.append({
                'name': player.name,
                'normalized_name': normalize_player_name(player.name),
                'position': player.position,
                'pro_team': player.proTeam,
                'total_points': player.total_points,
                'projected_points': player.projected_points,
                'percent_owned': player.percent_owned,
            })
            players_data.append({
                'name': player.name,
                'position': player.position,
                'pro_team': player.proTeam,
                'total_points': player.total_points,
                'projected_points': player.projected_points,
                'percent_owned': player.percent_owned,
            })
            players_data.append({
                'name': player.name,
                'position': player.position,
                'pro_team': player.proTeam,
                'total_points': player.total_points,
                'projected_points': player.projected_total_points,
                'percent_owned': player.percent_owned,
            })

        # Create a pandas DataFrame
        df = pd.DataFrame(players_data)

        # Ensure data directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Save to CSV
        df.to_csv(output_path, index=False)

        mod_time = os.path.getmtime(output_path)
        dt_string = datetime.fromtimestamp(mod_time).strftime("%Y-%m-%d %H:%M:%S")

        logger.info(f"Successfully saved available players to {output_path}")
        logger.info(f"Last updated: {dt_string}")
        print(f"Successfully saved available players to {output_path}")
        print(f"Last updated: {dt_string}")

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
        elif isinstance(e, pd.errors.EmptyDataError) or isinstance(e, pd.errors.ParserError):
            raise DataValidationError(
                f"Error parsing data from ESPN API: {e}",
                field_name="ESPN_API_response",
                original_error=e
            )
        elif isinstance(e, IOError) or isinstance(e, OSError):
            raise FileOperationError(
                f"Error writing available players to {output_path}: {e}",
                file_path=output_path,
                operation="write",
                original_error=e
            )
        else:
            raise wrap_exception(
                e, APIError,
                f"An unexpected error occurred while fetching available players: {e}",
                api_name="ESPN"
            )


def main():
    """Main function to fetch available players and handle errors."""
    logger.info("Starting available players fetch process.")
    load_dotenv()

    league_id = os.getenv("LEAGUE_ID")
    espn_s2 = os.getenv("ESPN_S2")
    swid = os.getenv("SWID")

    try:
        if not all([league_id, espn_s2, swid]):
            raise AuthenticationError(
                "Please set LEAGUE_ID, ESPN_S2, and SWID environment variables in your .env file.",
                api_name="ESPN",
                credential_type="API credentials"
            )
        get_available_players(int(league_id), espn_s2, swid)
        logger.info("Available players fetch completed successfully!")
        return 0
    except (AuthenticationError, APIError, NetworkError, DataValidationError, FileOperationError) as e:
        logger.error(f"Available players fetch error: {e.get_detailed_message()}")
        print(f"\n❌ Error fetching available players: {e}")
        return 1
    except Exception as e:
        logger.critical(f"An unhandled critical error occurred: {e}", exc_info=True)
        print(f"\n❌ An unexpected critical error occurred: {e}")
        print("Please check the log file for more details.")
        return 1


if __name__ == "__main__":
    sys.exit(main())