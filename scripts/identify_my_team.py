#!/usr/bin/env python3
################################################################################
#
# Script Name: identify_my_team.py
# ----------------
# Iterates over all teams in the league, asks the user to identify their team,
# and saves the team ID to the config.yaml file.
#
# @author Nicholas Wilde, 0xb299a622
# @date 2025-08-23
# @version 0.3.0
#
################################################################################

import os
import sys
import yaml
from espn_api.football import League
from dotenv import load_dotenv
from tabulate import tabulate
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from fantasy_ai.errors import (
    APIError, AuthenticationError, ConfigurationError, 
    FileOperationError, DataValidationError, wrap_exception
)
from fantasy_ai.utils.retry import retry
from fantasy_ai.utils.logging import setup_logging, get_logger

# Set up logging
setup_logging(level='INFO', format_type='console', log_file='logs/identify_my_team.log')
logger = get_logger(__name__)

# Load environment variables from .env file
load_dotenv()

CONFIG_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', 'config.yaml'
)


def validate_credentials():
    """
    Validate ESPN credentials and return them.
    
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


def load_config():
    """
    Load configuration from config.yaml with proper error handling.
    
    Returns:
        Configuration dictionary
        
    Raises:
        ConfigurationError: If config file cannot be read or parsed
        FileOperationError: If file cannot be accessed
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
            f"Configuration file not found: {CONFIG_FILE}. Please run 'task get_league_settings' first.",
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


def save_config(config):
    """
    Save configuration to config.yaml with error handling.
    
    Args:
        config: Configuration dictionary to save
        
    Raises:
        FileOperationError: If file cannot be written
        DataValidationError: If config data is invalid
    """
    if not isinstance(config, dict):
        raise DataValidationError(
            "Configuration must be a dictionary",
            field_name="config",
            expected_type="dict",
            actual_value=type(config)
        )
    
    try:
        logger.debug(f"Saving configuration to {CONFIG_FILE}")
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)
        
        logger.info(f"Configuration saved successfully to {CONFIG_FILE}")
        
    except PermissionError as e:
        raise FileOperationError(
            f"Permission denied writing to configuration file: {CONFIG_FILE}",
            file_path=CONFIG_FILE,
            operation="write",
            original_error=e
        )
    except Exception as e:
        raise wrap_exception(
            e, FileOperationError,
            f"Failed to save configuration to {CONFIG_FILE}",
            file_path=CONFIG_FILE,
            operation="write"
        )


@retry(max_attempts=3, base_delay=2.0, backoff_factor=2.0)
def create_espn_league(league_id, year, espn_s2, swid):
    """
    Create ESPN League instance with retry logic.
    
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
        
        # Test access by trying to get teams
        _ = league.teams
        
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
        
        # Generic API error
        else:
            raise wrap_exception(
                e, APIError,
                f"Failed to connect to ESPN league {league_id}",
                api_name="ESPN"
            )


def display_teams(league):
    """
    Display all teams in the league for user selection.
    
    Args:
        league: ESPN League instance
        
    Raises:
        APIError: If teams cannot be retrieved or displayed
    """
    try:
        logger.debug("Displaying teams for user selection")
        teams = league.teams
        
        if not teams:
            raise APIError(
                "No teams found in league",
                api_name="ESPN"
            )
        
        print("\n🏈 Please identify your team from the list below:")
        print("=" * 60)
        
        for i, team in enumerate(teams):
            try:
                # Get owner name safely
                owner_name = 'Unknown Owner'
                if team.owners and len(team.owners) > 0:
                    if isinstance(team.owners[0], dict) and 'displayName' in team.owners[0]:
                        owner_name = team.owners[0]['displayName']
                    elif hasattr(team.owners[0], 'displayName'):
                        owner_name = team.owners[0].displayName
                
                print(f"\n--- Team {i+1}: {team.team_name} ({owner_name}) ---")
                
                # Display roster
                roster_data = []
                for player in team.roster[:10]:  # Limit to first 10 players for readability
                    roster_data.append([
                        getattr(player, 'name', 'Unknown Player'),
                        getattr(player, 'position', 'UNKNOWN'),
                        getattr(player, 'proTeam', 'N/A')
                    ])
                
                if roster_data:
                    headers = ["Player Name", "Position", "NFL Team"]
                    print(tabulate(roster_data, headers=headers, tablefmt="grid"))
                    
                    if len(team.roster) > 10:
                        print(f"... and {len(team.roster) - 10} more players")
                else:
                    print("No roster data available for this team")
                    
            except Exception as e:
                logger.warning(f"Error displaying team {i+1}: {e}")
                print(f"\nTeam {i+1}: {team.team_name} (roster unavailable)")
        
        logger.info(f"Successfully displayed {len(teams)} teams")
        
    except Exception as e:
        raise wrap_exception(
            e, APIError,
            "Failed to display teams",
            api_name="ESPN"
        )


def get_user_team_selection(league):
    """
    Get team selection from user with input validation.
    
    Args:
        league: ESPN League instance
        
    Returns:
        Selected team object
        
    Raises:
        DataValidationError: If user selection is invalid
    """
    teams = league.teams
    max_attempts = 5
    
    for attempt in range(max_attempts):
        try:
            print(f"\n📝 Which team is yours? (1-{len(teams)}, or 'q' to quit): ", end="")
            selection = input().strip()
            
            # Handle quit
            if selection.lower() in ['q', 'quit', 'exit']:
                print("Team identification cancelled.")
                return None
            
            # Convert to integer and validate range
            selection_index = int(selection) - 1
            
            if 0 <= selection_index < len(teams):
                selected_team = teams[selection_index]
                
                # Confirm selection
                print(f"\n✅ You selected: {selected_team.team_name}")
                confirm = input("Is this correct? (y/n): ").strip().lower()
                
                if confirm in ['y', 'yes']:
                    logger.info(f"User selected team: {selected_team.team_name} (ID: {selected_team.team_id})")
                    return selected_team
                else:
                    print("Please select again.")
                    continue
            else:
                print(f"❌ Invalid selection. Please enter a number between 1 and {len(teams)}.")
                
        except ValueError:
            print("❌ Invalid input. Please enter a number.")
        except KeyboardInterrupt:
            print("\nTeam identification cancelled.")
            return None
        except Exception as e:
            logger.warning(f"Error during user input: {e}")
            print("❌ An error occurred. Please try again.")
    
    # If we get here, user exceeded max attempts
    raise DataValidationError(
        f"Maximum selection attempts ({max_attempts}) exceeded",
        field_name="team_selection",
        expected_type="valid team number"
    )


def identify_my_team():
    """
    Main function to identify and save user's team ID with comprehensive error handling.
    
    Returns:
        Exit code (0 for success, 1 for error)
    """
    try:
        logger.info("Starting team identification process")
        
        # Step 1: Validate credentials
        logger.info("Step 1: Validating ESPN credentials")
        league_id, espn_s2, swid = validate_credentials()
        
        # Step 2: Load configuration
        logger.info("Step 2: Loading configuration")
        config = load_config()
        year = config.get('league_settings', {}).get('year', datetime.now().year)
        
        # Step 3: Create league connection
        logger.info("Step 3: Connecting to ESPN league")
        league = create_espn_league(league_id, year, espn_s2, swid)
        
        # Step 4: Display teams
        logger.info("Step 4: Displaying teams for selection")
        display_teams(league)
        
        # Step 5: Get user selection
        logger.info("Step 5: Getting user team selection")
        selected_team = get_user_team_selection(league)
        
        if selected_team is None:
            print("Team identification cancelled.")
            return 130  # Cancelled by user
        
        # Step 6: Save configuration
        logger.info("Step 6: Saving team configuration")
        config['my_team_id'] = selected_team.team_id
        save_config(config)
        
        logger.info("Team identification completed successfully!")
        print(f"\n🎉 Success! Your team has been set to: {selected_team.team_name}")
        print(f"   Team ID: {selected_team.team_id}")
        print(f"   Configuration saved to: {CONFIG_FILE}")
        return 0
        
    except KeyboardInterrupt:
        logger.info("Process interrupted by user")
        print("\nTeam identification cancelled.")
        return 130
    except AuthenticationError as e:
        logger.error(f"Authentication error: {e.get_detailed_message()}")
        print(f"\n❌ Authentication Error: {e}")
        print("\nTroubleshooting:")
        print("- Check your .env file contains valid ESPN credentials")
        print("- Verify LEAGUE_ID, ESPN_S2, and SWID are correct")
        print("- Make sure you have access to the specified league")
        return 1
    except ConfigurationError as e:
        logger.error(f"Configuration error: {e.get_detailed_message()}")
        print(f"\n❌ Configuration Error: {e}")
        print("\nTroubleshooting:")
        if "not found" in str(e):
            print("- Run 'task get_league_settings' first to create config.yaml")
        return 1
    except APIError as e:
        logger.error(f"API error: {e.get_detailed_message()}")
        print(f"\n❌ ESPN API Error: {e}")
        print("\nTroubleshooting:")
        print("- Check your internet connection")
        print("- Verify the league exists for the specified year")
        return 1
    except (FileOperationError, DataValidationError) as e:
        logger.error(f"Data/File error: {e.get_detailed_message()}")
        print(f"\n❌ Error: {e}")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        print(f"\n❌ Unexpected error occurred: {e}")
        print("Check the log file for more details.")
        return 1


if __name__ == "__main__":
    sys.exit(identify_my_team())