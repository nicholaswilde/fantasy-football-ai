#!/usr/bin/env python3
################################################################################
#
# Script Name: get_league_settings.py
# ----------------
# Fetches and displays league settings from an ESPN fantasy football league.
#
# @author Nicholas Wilde, 0xb299a622
# @date 2025-08-23
# @version 0.2.0
#
################################################################################

import os
import sys
from dotenv import load_dotenv
from espn_api.football import League
import yaml
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from fantasy_ai.errors import (
    APIError, AuthenticationError, ConfigurationError, 
    FileOperationError, wrap_exception
)
from fantasy_ai.utils.retry import retry
from fantasy_ai.utils.logging import setup_logging, get_logger

# Set up logging
setup_logging(level='INFO', format_type='console', log_file='logs/get_league_settings.log')
logger = get_logger(__name__)

CONFIG_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', 'config.yaml'
)

def validate_credentials():
    """
    Validate ESPN credentials and return them.
    
    Returns:
        Tuple of (league_id, espn_s2, swid, year)
        
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
    
    current_year = datetime.now().year
    logger.info("ESPN credentials validated successfully")
    return league_id_int, espn_s2, swid, current_year


def load_existing_config():
    """
    Load existing config to preserve custom fields.
    
    Returns:
        Dictionary with existing configuration
        
    Raises:
        ConfigurationError: If config file exists but cannot be parsed
        FileOperationError: If config file cannot be read
    """
    if not os.path.exists(CONFIG_FILE):
        logger.debug("No existing config file found, starting fresh")
        return {}
    
    try:
        logger.debug(f"Loading existing configuration from {CONFIG_FILE}")
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            documents = list(yaml.safe_load_all(f))
            if documents:
                existing_config = documents[0]
                logger.info("Existing configuration loaded successfully")
                return existing_config
            else:
                logger.warning("Config file is empty, starting fresh")
                return {}
                
    except yaml.YAMLError as e:
        raise ConfigurationError(
            f"Invalid YAML in configuration file: {CONFIG_FILE}",
            config_file=CONFIG_FILE,
            original_error=e
        )
    except (PermissionError, UnicodeDecodeError) as e:
        raise FileOperationError(
            f"Cannot read configuration file: {CONFIG_FILE}",
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
        
        # Test access by trying to get settings
        _ = league.settings
        
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
                f"Please verify your LEAGUE_ID and year.",
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


def extract_league_settings(league, existing_config, current_year):
    """
    Extract league settings from ESPN League instance.
    
    Args:
        league: ESPN League instance
        existing_config: Existing configuration to preserve
        current_year: Current year
        
    Returns:
        Dictionary with league settings
        
    Raises:
        APIError: If settings cannot be extracted
    """
    try:
        logger.debug("Extracting league settings")
        settings = league.settings
        
        if not settings:
            raise APIError(
                "League settings not available",
                api_name="ESPN"
            )
        
        # Prepare data for YAML output
        config_data = {
            'league_settings': {
                'league_name': getattr(settings, 'name', 'Unknown League'),
                'number_of_teams': getattr(settings, 'team_count', 0),
                'playoff_teams': getattr(settings, 'playoff_team_count', 0),
                'year': current_year,
                'data_years': [current_year - 1, current_year]
            },
            'roster_settings': {},
            'scoring_rules': {}
        }
        
        # Preserve custom fields from existing config
        if 'league_settings' in existing_config and isinstance(existing_config['league_settings'], dict):
            for key in ['year', 'data_years']:
                if key in existing_config['league_settings']:
                    config_data['league_settings'][key] = existing_config['league_settings'][key]
        
        if 'my_team_id' in existing_config:
            config_data['my_team_id'] = existing_config['my_team_id']
        
        # Extract roster settings
        if hasattr(settings, 'position_slot_counts') and settings.position_slot_counts:
            for position, count in sorted(settings.position_slot_counts.items()):
                if count > 0:
                    # Normalize position names to match config.yaml conventions
                    normalized_pos = position.replace('/', '_').upper()
                    config_data['roster_settings'][normalized_pos] = count
        
        # Extract scoring rules
        if hasattr(settings, 'scoring_format') and settings.scoring_format:
            for rule in sorted(settings.scoring_format, key=lambda x: x.get('label', '')):
                if 'label' in rule and 'points' in rule:
                    # Normalize scoring rule labels to snake_case for YAML keys
                    label = rule['label'].lower().replace(' ', '_').replace('-', '_').replace('/', '_')
                    config_data['scoring_rules'][label] = rule['points']
        
        logger.info(f"Successfully extracted settings for league: {config_data['league_settings']['league_name']}")
        return config_data
        
    except Exception as e:
        raise wrap_exception(
            e, APIError,
            "Failed to extract league settings",
            api_name="ESPN"
        )


def save_config_file(config_data):
    """
    Save configuration data to YAML file.
    
    Args:
        config_data: Configuration dictionary to save
        
    Raises:
        FileOperationError: If file cannot be written
    """
    try:
        # Ensure directory exists
        config_dir = os.path.dirname(CONFIG_FILE)
        if config_dir and not os.path.exists(config_dir):
            os.makedirs(config_dir, exist_ok=True)
        
        logger.debug(f"Writing configuration to {CONFIG_FILE}")
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            f.write("---")
            yaml.dump(config_data, f, default_flow_style=False, sort_keys=False)
        
        logger.info(f"Successfully updated {CONFIG_FILE} with league settings")
        
    except PermissionError as e:
        raise FileOperationError(
            f"Permission denied writing to {CONFIG_FILE}",
            file_path=CONFIG_FILE,
            operation="write",
            original_error=e
        )
    except Exception as e:
        raise wrap_exception(
            e, FileOperationError,
            f"Failed to write configuration to {CONFIG_FILE}",
            file_path=CONFIG_FILE,
            operation="write"
        )


def get_league_settings():
    """
    Main function to fetch and save ESPN league settings with comprehensive error handling.
    
    Returns:
        Exit code (0 for success, 1 for error)
    """
    try:
        logger.info("Starting league settings fetch process")
        
        # Step 1: Load environment variables
        load_dotenv()
        
        # Step 2: Validate credentials
        logger.info("Step 1: Validating ESPN credentials")
        league_id, espn_s2, swid, current_year = validate_credentials()
        
        # Step 3: Load existing config
        logger.info("Step 2: Loading existing configuration")
        existing_config = load_existing_config()
        
        # Step 4: Create league connection
        logger.info("Step 3: Connecting to ESPN league")
        league = create_espn_league(league_id, current_year, espn_s2, swid)
        
        # Step 5: Extract settings
        logger.info("Step 4: Extracting league settings")
        config_data = extract_league_settings(league, existing_config, current_year)
        
        # Step 6: Save configuration
        logger.info("Step 5: Saving configuration file")
        save_config_file(config_data)
        
        logger.info("League settings fetch completed successfully!")
        print(f"✅ Successfully updated {CONFIG_FILE} with league settings")
        print(f"   League: {config_data['league_settings']['league_name']}")
        print(f"   Teams: {config_data['league_settings']['number_of_teams']}")
        print(f"   Playoff Teams: {config_data['league_settings']['playoff_teams']}")
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
        print("- Make sure you have access to the specified league")
        return 1
    except ConfigurationError as e:
        logger.error(f"Configuration error: {e.get_detailed_message()}")
        print(f"\n❌ Configuration Error: {e}")
        return 1
    except APIError as e:
        logger.error(f"API error: {e.get_detailed_message()}")
        print(f"\n❌ ESPN API Error: {e}")
        print("\nTroubleshooting:")
        print("- Check your internet connection")
        print("- Verify the league exists for the specified year")
        return 1
    except FileOperationError as e:
        logger.error(f"File I/O error: {e.get_detailed_message()}")
        print(f"\n❌ File Error: {e}")
        print("\nTroubleshooting:")
        print("- Check file permissions in the current directory")
        print("- Make sure you have write access to config.yaml")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        print(f"\n❌ Unexpected error occurred: {e}")
        print("Check the log file for more details.")
        return 1


if __name__ == "__main__":
    sys.exit(get_league_settings())