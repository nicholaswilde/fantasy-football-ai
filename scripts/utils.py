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

# Add src to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from fantasy_ai.errors import (
    ConfigurationError,
    FileOperationError,
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
