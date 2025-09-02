#!/usr/bin/env python3
################################################################################
#
# Script Name: utils.py
# ----------------
# A collection of utility functions for the fantasy-football-ai project.
#
# @author Nicholas Wilde, 0xb299a622
# @date 29 08 2025
# @version 0.1.0
#
################################################################################

import os
import yaml
import sys
import pandas as pd


# Add src to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from fantasy_ai.errors import (
    ConfigurationError,
    FileOperationError,
    DataValidationError,
    wrap_exception
)
from fantasy_ai.utils.logging import setup_logging, get_logger

# Set up logging
setup_logging(level='INFO', format_type='console', log_file='logs/utils.log')
logger = get_logger(__name__)

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


def load_player_stats(file_path: str) -> pd.DataFrame:
    """
    Load player stats from a CSV file.

    Args:
        file_path: Path to the player_stats.csv file.

    Returns:
        DataFrame with player stats.

    Raises:
        FileOperationError: If the file cannot be read.
        DataValidationError: If the file is empty.
    """
    try:
        df = pd.read_csv(file_path)
        if df.empty:
            raise DataValidationError(f"Player stats file is empty: {file_path}")
        return df
    except FileNotFoundError as e:
        raise FileOperationError(f"Player stats file not found: {file_path}", original_error=e)
    except Exception as e:
        raise FileOperationError(f"Error reading player stats file: {file_path}", original_error=e)


def load_available_players(file_path: str) -> pd.DataFrame:
    """
    Load available players from a CSV file.

    Args:
        file_path: Path to the available_players.csv file.

    Returns:
        DataFrame with available players.

    Raises:
        FileOperationError: If the file cannot be read.
        DataValidationError: If the file is empty.
    """
    try:
        df = pd.read_csv(file_path)
        if df.empty:
            raise DataValidationError(f"Available players file is empty: {file_path}")
        return df
    except FileNotFoundError as e:
        raise FileOperationError(f"Available players file not found: {file_path}", original_error=e)
    except Exception as e:
        raise FileOperationError(f"Error reading available players file: {file_path}", original_error=e)


def load_my_team(roster_file: str) -> list:
    """
    Reads the team roster from a Markdown table file and returns a list of player names.
    """
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
        return roster
    except FileNotFoundError:
        return [] # Return empty list if file not found
