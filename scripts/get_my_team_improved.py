#!/usr/bin/env python3
"""
Improved script to fetch team roster with comprehensive error handling.

This script demonstrates enhanced error handling for ESPN API interactions
and file operations.
"""

import os
import sys
from datetime import datetime
from espn_api.football import League
from dotenv import load_dotenv
import yaml
from tabulate import tabulate

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from fantasy_ai.errors import (
    APIError, AuthenticationError, ConfigurationError, 
    FileIOError, DataValidationError, wrap_exception
)
from fantasy_ai.utils.retry import retry
from fantasy_ai.utils.logging import setup_logging, get_logger

# Set up logging
setup_logging(level='INFO', format_type='console', log_file='logs/get_my_team.log')
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
    except ConfigurationError:
        raise  # Re-raise configuration errors
    except Exception as e:
        logger.warning(f"Could not load year from config, using current year: {e}")
        year = datetime.now().year
    
    logger.info("ESPN credentials validated successfully")
    return league_id_int, espn_s2, swid, year


def get_my_team_id() -> int:
    """
    Get team ID from configuration with proper validation.
    
    Returns:
        Team ID
        
    Raises:
        ConfigurationError: If team ID is not configured or invalid
    """
    try:
        config = load_config()
        my_team_id = config.get('my_team_id')
        
        if my_team_id is None:
            raise ConfigurationError(
                "my_team_id not found in config.yaml. Please run 'task identify_my_team' first.",
                config_key="my_team_id",
                config_file=CONFIG_FILE
            )
        
        # Validate team ID is numeric
        try:
            team_id_int = int(my_team_id)
        except (ValueError, TypeError) as e:
            raise ConfigurationError(
                f"my_team_id must be a number, got: {my_team_id}",
                config_key="my_team_id",
                config_file=CONFIG_FILE,
                original_error=e
            )
        
        logger.debug(f"Team ID loaded: {team_id_int}")
        return team_id_int
        
    except ConfigurationError:
        raise  # Re-raise configuration errors
    except Exception as e:
        raise wrap_exception(
            e, ConfigurationError,
            "Failed to get team ID from configuration",
            config_key="my_team_id"
        )


@retry(max_attempts=3, base_delay=2.0, backoff_factor=2.0)
def create_espn_league(league_id: int, year: int, espn_s2: str, swid: str) -> League:
    """
    Create ESPN League instance with retry logic and error handling.
    
    Args:
        league_id: ESPN league ID
        year: League year
        espn_s2: ESPN S2 cookie
        swid: ESPN SWID cookie
        
    Returns:
        ESPN League instance
        
    Raises:
        AuthenticationError: If credentials are invalid
        APIError: If league cannot be accessed
    """
    try:
        logger.debug(f"Creating ESPN League instance for league {league_id}, year {year}")
        league = League(league_id=league_id, year=year, espn_s2=espn_s2, swid=swid)
        
        # Test access by trying to get league info
        _ = league.teams  # This will trigger API call
        
        logger.info(f"Successfully connected to ESPN league {league_id}")
        return league
        
    except Exception as e:
        error_msg = str(e).lower()
        
        # Check for authentication errors
        if any(auth_term in error_msg for auth_term in ['401', 'unauthorized', 'invalid', 'forbidden']):
            raise AuthenticationError(
                "ESPN API authentication failed. Please check your ESPN_S2 and SWID credentials.",
                api_name="ESPN",
                credential_type="S2/SWID",
                original_error=e
            )
        
        # Check for not found errors
        elif any(nf_term in error_msg for nf_term in ['404', 'not found', 'does not exist']):
            raise APIError(
                f"ESPN league {league_id} not found for year {year}. "
                f"Please verify your LEAGUE_ID and year in config.yaml.",
                api_name="ESPN",
                status_code=404,
                original_error=e
            )
        
        # Check for network/timeout errors
        elif any(net_term in error_msg for net_term in ['timeout', 'connection', 'network']):
            raise wrap_exception(
                e, APIError,
                f"Network error connecting to ESPN league {league_id}",
                api_name="ESPN"
            )
        
        # Generic API error
        else:
            raise wrap_exception(
                e, APIError,
                f"Failed to connect to ESPN league {league_id}",
                api_name="ESPN"
            )


def find_team_by_id(league: League, team_id: int):
    """
    Find team by ID with proper error handling.
    
    Args:
        league: ESPN League instance
        team_id: Team ID to find
        
    Returns:
        Team object
        
    Raises:
        DataValidationError: If team not found
        APIError: If error accessing teams
    """
    try:
        logger.debug(f"Looking for team with ID {team_id}")
        
        # Get all teams
        teams = league.teams
        if not teams:
            raise APIError(
                "No teams found in league. League may be empty or inaccessible.",
                api_name="ESPN"
            )
        
        # Find team by ID
        for team in teams:
            if team.team_id == team_id:
                logger.info(f"Found team: {team.team_name} (ID: {team_id})")
                return team
        
        # Team not found - provide helpful error message
        available_teams = [(t.team_id, t.team_name) for t in teams[:5]]  # Show first 5 teams
        team_list = ", ".join([f"{name} (ID: {tid})" for tid, name in available_teams])
        
        raise DataValidationError(
            f"Team with ID {team_id} not found in league. "
            f"Available teams include: {team_list}{'...' if len(teams) > 5 else ''}",
            field_name="my_team_id",
            expected_type="valid team ID",
            actual_value=team_id
        )
        
    except (DataValidationError, APIError):
        raise  # Re-raise our custom exceptions
    except Exception as e:
        raise wrap_exception(
            e, APIError,
            f"Error finding team {team_id} in league",
            api_name="ESPN"
        )


def extract_roster_data(team) -> list:
    """
    Extract roster data from team with validation.
    
    Args:
        team: ESPN team object
        
    Returns:
        List of player data dictionaries
        
    Raises:
        DataValidationError: If roster data is invalid
    """
    try:
        logger.debug(f"Extracting roster data for team {team.team_name}")
        
        if not hasattr(team, 'roster') or not team.roster:
            raise DataValidationError(
                f"Team {team.team_name} has no roster data",
                field_name="roster",
                expected_type="list of players",
                actual_value="empty or missing"
            )
        
        roster_data = []
        for player in team.roster:
            try:
                # Validate required player attributes
                player_name = getattr(player, 'name', 'Unknown Player')
                player_position = getattr(player, 'position', 'UNKNOWN')
                player_team = getattr(player, 'proTeam', 'N/A')
                
                if not player_name or player_name.strip() == '':
                    logger.warning(f"Player with empty name found, skipping")
                    continue
                
                roster_data.append({
                    'name': player_name,
                    'position': player_position,
                    'team': player_team
                })
                
            except Exception as e:
                logger.warning(f"Error processing player {getattr(player, 'name', 'Unknown')}: {e}")
                continue
        
        if not roster_data:
            raise DataValidationError(
                f"No valid players found in roster for team {team.team_name}",
                field_name="roster",
                expected_type="list of valid players",
                actual_value="empty after validation"
            )
        
        logger.info(f"Successfully extracted {len(roster_data)} players from roster")
        return roster_data
        
    except DataValidationError:
        raise  # Re-raise validation errors
    except Exception as e:
        raise wrap_exception(
            e, DataValidationError,
            f"Failed to extract roster data from team",
            field_name="roster"
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


def save_roster_to_markdown(roster_data: list, team_name: str) -> None:
    """
    Save roster data to markdown file with comprehensive error handling.
    
    Args:
        roster_data: List of player dictionaries
        team_name: Name of the team
        
    Raises:
        FileIOError: If file cannot be written
    """
    # Ensure data directory exists
    data_dir = 'data'
    safe_create_directory(data_dir)
    
    file_path = os.path.join(data_dir, 'my_team.md')
    
    try:
        logger.debug(f"Writing roster to {file_path}")
        
        # Prepare data for tabulate
        table_data = [[player['name'], player['position'], player['team']] for player in roster_data]
        headers = ["Player Name", "Position", "NFL Team"]
        markdown_table = tabulate(table_data, headers=headers, tablefmt="pipe")
        
        # Generate markdown content
        now = datetime.now()
        dt_string = now.strftime("%Y-%m-%d %H:%M:%S")
        
        content = f\"\"\"<!-- Last updated: {dt_string} -->\n# My Team: {team_name}\n\n{markdown_table}\n\"\"\"\n        \n        # Write to file with error handling\n        try:\n            with open(file_path, \"w\", encoding='utf-8') as f:\n                f.write(content)\n            \n            logger.info(f\"Successfully saved roster to {file_path}\")\n            \n        except PermissionError as e:\n            raise FileIOError(\n                f\"Permission denied writing to {file_path}\",\n                file_path=file_path,\n                operation=\"write\",\n                original_error=e\n            )\n        except UnicodeEncodeError as e:\n            raise FileIOError(\n                f\"Unicode encoding error writing to {file_path}\",\n                file_path=file_path,\n                operation=\"write\",\n                original_error=e\n            )\n        except Exception as e:\n            raise wrap_exception(\n                e, FileIOError,\n                f\"Failed to write roster file to {file_path}\",\n                file_path=file_path,\n                operation=\"write\"\n            )\n            \n    except FileIOError:\n        raise  # Re-raise our file IO errors\n    except Exception as e:\n        raise wrap_exception(\n            e, FileIOError,\n            \"Unexpected error saving roster to markdown\"\n        )\n\n\ndef display_roster_table(roster_data: list, team_name: str) -> None:\n    \"\"\"Display roster table in console with error handling.\"\"\"\n    try:\n        table_data = [[player['name'], player['position'], player['team']] for player in roster_data]\n        headers = ["Player Name", "Position", "NFL Team"]\n        \n        print(f\"\\n### {team_name} - Current Roster\\n\")\n        print(tabulate(table_data, headers=headers, tablefmt=\"fancy_grid\"))\n        print(\"\\n\")\n        \n    except Exception as e:\n        logger.warning(f\"Error displaying roster table: {e}\")\n        # Fallback to simple display\n        print(f\"\\n### {team_name} - Current Roster\\n\")\n        for player in roster_data:\n            print(f\"- {player['name']} ({player['position']}) - {player['team']}\")\n        print(\"\\n\")\n\n\ndef get_my_team() -> int:\n    \"\"\"\n    Main function to fetch team roster with comprehensive error handling.\n    \n    Returns:\n        Exit code (0 for success, 1 for error)\n    \"\"\"\n    try:\n        logger.info(\"Starting team roster fetch process\")\n        \n        # Step 1: Validate credentials\n        logger.info(\"Step 1: Validating ESPN credentials\")\n        league_id, espn_s2, swid, year = validate_espn_credentials()\n        \n        # Step 2: Get team ID\n        logger.info(\"Step 2: Getting team ID from configuration\")\n        my_team_id = get_my_team_id()\n        \n        # Step 3: Create league connection\n        logger.info(\"Step 3: Connecting to ESPN league\")\n        league = create_espn_league(league_id, year, espn_s2, swid)\n        \n        # Step 4: Find team\n        logger.info(\"Step 4: Finding team in league\")\n        team = find_team_by_id(league, my_team_id)\n        \n        # Step 5: Extract roster data\n        logger.info(\"Step 5: Extracting roster data\")\n        roster_data = extract_roster_data(team)\n        \n        # Step 6: Display roster\n        logger.info(\"Step 6: Displaying roster\")\n        display_roster_table(roster_data, team.team_name)\n        \n        # Step 7: Save to markdown\n        logger.info(\"Step 7: Saving roster to markdown file\")\n        save_roster_to_markdown(roster_data, team.team_name)\n        \n        logger.info(\"Team roster fetch completed successfully!\")\n        print(f\"✓ Team roster saved to data/my_team.md\")\n        return 0\n        \n    except KeyboardInterrupt:\n        logger.info(\"Process interrupted by user\")\n        print(\"\\nProcess interrupted by user.\")\n        return 130\n    except AuthenticationError as e:\n        logger.error(f\"Authentication error: {e.get_detailed_message()}\")\n        print(f\"\\n❌ Authentication Error: {e}\")\n        print(\"\\nTroubleshooting:\")\n        print(\"- Check your .env file contains valid ESPN credentials\")\n        print(\"- Verify LEAGUE_ID, ESPN_S2, and SWID are correct\")\n        print(\"- Make sure you have access to the specified league\")\n        return 1\n    except ConfigurationError as e:\n        logger.error(f\"Configuration error: {e.get_detailed_message()}\")\n        print(f\"\\n❌ Configuration Error: {e}\")\n        print(\"\\nTroubleshooting:\")\n        if \"my_team_id\" in str(e):\n            print(\"- Run 'task identify_my_team' to set up your team ID\")\n        if \"config.yaml\" in str(e):\n            print(\"- Run 'task init' to create configuration file\")\n        return 1\n    except (APIError, DataValidationError) as e:\n        logger.error(f\"API/Data error: {e.get_detailed_message()}\")\n        print(f\"\\n❌ Error: {e}\")\n        return 1\n    except FileIOError as e:\n        logger.error(f\"File I/O error: {e.get_detailed_message()}\")\n        print(f\"\\n❌ File Error: {e}\")\n        print(\"\\nTroubleshooting:\")\n        print(\"- Check file permissions in the current directory\")\n        print(\"- Make sure the data/ directory is writable\")\n        return 1\n    except Exception as e:\n        logger.error(f\"Unexpected error: {e}\", exc_info=True)\n        print(f\"\\n❌ Unexpected error occurred: {e}\")\n        print(\"Check the log file for more details.\")\n        return 1\n\n\ndef main():\n    \"\"\"Entry point with proper error handling.\"\"\"\n    exit_code = get_my_team()\n    return exit_code\n\n\nif __name__ == \"__main__\":\n    sys.exit(main())
