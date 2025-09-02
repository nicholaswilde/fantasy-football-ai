#!/usr/bin/env python3
################################################################################
#
# Script Name: compare_roster_positions.py
# ----------------
# Compares the number of positions in config.yaml roster_settings with the
# actual number of positions in data/my_team.md.
#
# @author Nicholas Wilde, 0xb299a622
# @date 21 August 2025
# @version 1.2.0
#
################################################################################

import yaml
import re
from tabulate import tabulate
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from scripts.utils import load_config
from fantasy_ai.utils.logging import setup_logging, get_logger

# Set up logging
setup_logging(level='INFO', format_type='console', log_file='logs/compare_roster_positions.log')
logger = get_logger(__name__)

def compare_roster_positions(config_path: str, my_team_path: str) -> tuple[str, str]:
    """
    Compares the number of positions in config.yaml roster_settings with the
    actual number of positions in data/my_team.md.

    Args:
        config_path (str): The path to the config.yaml file.
        my_team_path (str): The path to the my_team.md file.

    Returns:
        tuple: A tuple containing the main comparison table and the mismatch summary table.
        
    Raises:
        ConfigurationError: If config file cannot be read or parsed, or roster_settings are invalid.
        FileOperationError: If my_team.md cannot be read.
        DataValidationError: If my_team.md content is malformed.
    """
    logger.info(f"Comparing roster positions using config: {config_path} and team: {my_team_path}")
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
    except FileNotFoundError as e:
        raise ConfigurationError(
            f"Configuration file not found: {config_path}. Please run 'task init' first.",
            config_file=config_path,
            original_error=e
        )
    except yaml.YAMLError as e:
        raise ConfigurationError(
            f"Invalid YAML in configuration file: {config_path}",
            config_file=config_path,
            original_error=e
        )
    except PermissionError as e:
        raise FileOperationError(
            f"Permission denied reading configuration file: {config_path}",
            file_path=config_path,
            operation="read",
            original_error=e
        )
    except Exception as e:
        raise wrap_exception(
            e, ConfigurationError,
            f"Failed to load configuration from {config_path}",
            config_file=config_path
        )

    expected_roster = config.get('roster_settings', {})
    if not isinstance(expected_roster, dict) or not expected_roster:
        raise ConfigurationError(
            "'roster_settings' not found or is empty/invalid in config.yaml.",
            config_key="roster_settings",
            config_file=config_path
        )

    try:
        with open(my_team_path, 'r', encoding='utf-8') as f:
            my_team_content = f.read()
    except FileNotFoundError as e:
        raise FileOperationError(
            f"My team file not found: {my_team_path}. Please run 'task get_my_team' first.",
            file_path=my_team_path,
            operation="read",
            original_error=e
        )
    except PermissionError as e:
        raise FileOperationError(
            f"Permission denied reading my team file: {my_team_path}",
            file_path=my_team_path,
            operation="read",
            original_error=e
        )
    except UnicodeDecodeError as e:
        raise DataValidationError(
            f"Cannot decode my team file (encoding issue): {my_team_path}",
            field_name="my_team_file_encoding",
            expected_type="UTF-8 encoded text",
            actual_value="unreadable encoding",
            original_error=e
        )
    except Exception as e:
        raise wrap_exception(
            e, FileOperationError,
            f"Failed to read my team file {my_team_path}",
            file_path=my_team_path,
            operation="read"
        )

    if not my_team_content.strip():
        logger.warning(f"My team file is empty: {my_team_path}.")
        # Return empty tables if the file is empty
        return "No team data found.", ""

    actual_roster = {}
    position_map = {
        'QB': 'QB', 'RB': 'RB', 'WR': 'WR', 'TE': 'TE', 'K': 'K',
        'DST': 'D_ST', 'BENCH': 'BE', 'DP': 'DP', 'IR': 'IR',
        'RB/WR': 'RB_WR', 'WR/TE': 'WR_TE',
    }

    lines = my_team_content.split('\n')
    # Skip header and separator lines (first 4 lines)
    for line in lines:
        line = line.strip()
        # Skip empty lines and Markdown table separator lines
        if not line or all(c in '|-:' for c in line):
            continue
        
        if line.startswith('|') and '|' in line[1:]:
            parts = [p.strip() for p in line.split('|')]
            # Ensure there's at least a player name and position column and the position is not the separator
            if len(parts) > 2 and parts[2] != ':----------':
                position = parts[2] # Assuming position is in the third column (index 2)
                if position: # Ensure it's not empty
                    mapped_position = position_map.get(position, position)
                    actual_roster[mapped_position] = actual_roster.get(mapped_position, 0) + 1

    headers = ["Position", "Expected", "Actual", "Status"]
    table_data = []
    mismatches = []
    all_positions = sorted(list(set(expected_roster.keys()) | set(actual_roster.keys())))

    for position in all_positions:
        expected_count = expected_roster.get(position, 0)
        actual_count = actual_roster.get(position, 0)
        status = "OK" if expected_count == actual_count else "MISMATCH"
        table_data.append([position, expected_count, actual_count, status])
        if status == "MISMATCH":
            mismatches.append([position, expected_count, actual_count])

    comparison_table = tabulate(table_data, headers=headers, tablefmt="github")
    mismatch_table = ""
    if mismatches:
        mismatch_headers = ["Position", "Expected", "Actual"]
        mismatch_table = tabulate(mismatches, headers=mismatch_headers, tablefmt="github")

    logger.info("Roster comparison completed.")
    return comparison_table, mismatch_table


def main():
    """Main function to compare roster positions and handle errors."""
    CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'config.yaml')
    MY_TEAM_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'my_team.md')
    
    try:
        comparison, mismatches = compare_roster_positions(CONFIG_FILE, MY_TEAM_FILE)
        print("\nRoster Comparison:")
        print(comparison)
        if mismatches:
            print("\nSummary of Mismatches:")
            print(mismatches)
        return 0
    except (ConfigurationError, FileOperationError, DataValidationError) as e:
        logger.error(f"Roster comparison error: {e.get_detailed_message()}")
        print(f"\n❌ Error during roster comparison: {e}")
        return 1
    except Exception as e:
        logger.critical(f"An unhandled critical error occurred: {e}", exc_info=True)
        print(f"\n❌ An unexpected critical error occurred: {e}")
        print("Please check the log file for more details.")
        return 1


if __name__ == "__main__":
    sys.exit(main())