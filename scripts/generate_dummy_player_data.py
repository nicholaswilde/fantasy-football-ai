#!/usr/bin/env python3
################################################################################
#
# Script Name: generate_dummy_player_data.py
# ----------------
# Generates dummy player data for testing and development purposes.
#
# @author Nicholas Wilde, 0xb299a622
# @date 2025-08-20
# @version 0.1.0
#
################################################################################

import os
import pandas as pd
import numpy as np
import yaml
import sys

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src'))

from fantasy_ai.errors import (
    FileOperationError,
    ConfigurationError,
    wrap_exception
)
from fantasy_ai.utils.logging import setup_logging, get_logger

# Set up logging
setup_logging(level='INFO', format_type='console', log_file='logs/generate_dummy_player_data.log')
logger = get_logger(__name__)

# Load configuration from config.yaml
CONFIG_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', 'config.yaml'
)

def load_config() -> dict:
    """
    Loads configuration from the config.yaml file with proper error handling.
    
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


CONFIG = load_config()

def generate_dummy_player_data() -> None:
    """
    Generates dummy player data for ADP and projections.
    Uses configuration from config.yaml for number of players and position distribution.
    
    Raises:
        ConfigurationError: If dummy data settings are missing or invalid.
        FileOperationError: If CSV files cannot be written.
    """
    logger.info("Generating dummy player data...")
    dummy_data_settings = CONFIG.get('dummy_data_settings', {})
    num_players = dummy_data_settings.get('num_players', 300)
    position_distribution = dummy_data_settings.get('position_distribution', {
        'QB': 0.1,
        'RB': 0.25,
        'WR': 0.35,
        'TE': 0.1,
        'K': 0.1,
        'D/ST': 0.1
    })

    if not isinstance(num_players, int) or num_players <= 0:
        raise ConfigurationError(
            f"Invalid 'num_players' in config.yaml: {num_players}. Must be a positive integer.",
            config_key="dummy_data_settings.num_players"
        )
    if not isinstance(position_distribution, dict) or not position_distribution:
        raise ConfigurationError(
            f"Invalid 'position_distribution' in config.yaml: {position_distribution}. Must be a non-empty dictionary.",
            config_key="dummy_data_settings.position_distribution"
        )
    if not np.isclose(sum(position_distribution.values()), 1.0):
        logger.warning("Position distribution probabilities do not sum to 1.0. Normalizing...")
        total_sum = sum(position_distribution.values())
        position_distribution = {k: v / total_sum for k, v in position_distribution.items()}

    logger.info(f"Generating dummy data for {num_players} players...")

    # Generate player names
    player_names = [f"Player_{i}" for i in range(num_players)]

    # Assign positions based on distribution
    player_positions = np.random.choice(
        list(position_distribution.keys()),
        size=num_players,
        p=list(position_distribution.values())
    )

    # Generate ADP (lower ADP for higher-ranked players)
    adp = np.arange(1, num_players + 1)
    np.random.shuffle(adp) # Shuffle to make it less perfectly ordered

    # Generate projected points (higher points for lower ADP, with some randomness)
    projected_points = (num_players - adp + 1) * 2.5 + np.random.normal(0, 20, num_players)
    projected_points = np.maximum(0, projected_points) # Ensure no negative points

    # Create DataFrame for ADP
    adp_df = pd.DataFrame({
        'player_name': player_names,
        'position': player_positions,
        'adp': adp
    })
    adp_df = adp_df.sort_values(by='adp').reset_index(drop=True)

    # Create DataFrame for Projections
    projections_df = pd.DataFrame({
        'player_name': player_names,
        'projected_points': projected_points
    })

    # Save to CSV
    output_dir = 'data'
    try:
        os.makedirs(output_dir, exist_ok=True)
        adp_output_path = os.path.join(output_dir, 'player_adp.csv')
        projections_output_path = os.path.join(output_dir, 'player_projections.csv')
        
        adp_df.to_csv(adp_output_path, index=False)
        projections_df.to_csv(projections_output_path, index=False)
        
        logger.info(f"Dummy player_adp.csv and player_projections.csv created in {output_dir}.")
    except PermissionError as e:
        raise FileOperationError(
            f"Permission denied writing dummy data to {output_dir}",
            file_path=output_dir,
            operation="write",
            original_error=e
        )
    except IOError as e:
        raise FileOperationError(
            f"IO error writing dummy data to {output_dir}: {e}",
            file_path=output_dir,
            operation="write",
            original_error=e
        )
    except Exception as e:
        raise wrap_exception(
            e, FileOperationError,
            f"Failed to write dummy data to {output_dir}",
            file_path=output_dir,
            operation="write"
        )


def main():
    """Main function to generate dummy player data and handle errors."""
    try:
        generate_dummy_player_data()
        print("✓ Dummy player data generated successfully!")
        return 0
    except (ConfigurationError, FileOperationError) as e:
        logger.error(f"Dummy data generation error: {e.get_detailed_message()}")
        print(f"\n❌ Error generating dummy player data: {e}")
        print("\nTroubleshooting:")
        if isinstance(e, ConfigurationError):
            print("- Check config.yaml for valid 'dummy_data_settings'.")
        elif isinstance(e, FileOperationError):
            print("- Check file permissions for the 'data/' directory.")
        return 1
    except Exception as e:
        logger.critical(f"An unhandled critical error occurred: {e}", exc_info=True)
        print(f"\n❌ An unexpected critical error occurred: {e}")
        print("Please check the log file for more details.")
        return 1


if __name__ == "__main__":
    sys.exit(main())