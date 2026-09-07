import os
import sys

import pandas as pd
from tabulate import tabulate

# Add src to path for imports
from fantasy_football_ai.errors import ConfigurationError, DataValidationError, FileOperationError, wrap_exception
from fantasy_football_ai.reporting import get_trade_suggestions
from fantasy_football_ai.utils.logging import get_logger, setup_logging

# Set up logging
setup_logging(level='INFO', format_type='console', log_file='logs/trade_suggester.log')
logger = get_logger(__name__)

# Load configuration from config.yaml
CONFIG_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', '..', 'config.yaml'
)

def main():
    """Main function to run trade suggester and handle errors."""
    try:
        # Define the path to your data file
        data_file = "data/player_stats.csv"

        # Check if the data file exists
        if not os.path.exists(data_file):
            raise FileOperationError(f"Data file not found at '{data_file}'. Please run 'download_stats.py' first.", file_path=data_file, operation="read")

        # Read the stats file
        stats_df = pd.read_csv(data_file, low_memory=False)

        # Get trade suggestions
        sell_high, buy_low = get_trade_suggestions(stats_df)

        # Define the columns to display
        columns_to_display = [
            'player_display_name', 'position', 'recent_team',
            'fantasy_points', 'avg_fantasy_points', 'point_difference'
        ]

        # Rename columns for better readability
        sell_high_display = sell_high[columns_to_display].rename(columns={
            'player_display_name': 'Player',
            'position': 'Pos',
            'recent_team': 'Team',
            'fantasy_points': 'Week Pts',
            'avg_fantasy_points': 'Avg Pts',
            'point_difference': 'Diff'
        })

        buy_low_display = buy_low[columns_to_display].rename(columns={
            'player_display_name': 'Player',
            'position': 'Pos',
            'recent_team': 'Team',
            'fantasy_points': 'Week Pts',
            'avg_fantasy_points': 'Avg Pts',
            'point_difference': 'Diff'
        })

        print("--- Sell-High Candidates ---")
        print(tabulate(sell_high_display, headers='keys', tablefmt='fancy_grid', showindex=False))
        print("\n--- Buy-Low Candidates ---")
        print(tabulate(buy_low_display, headers='keys', tablefmt='fancy_grid', showindex=False))
        return 0
    except (ConfigurationError, FileOperationError, DataValidationError) as e:
        logger.error(f"Trade suggestion error: {e.get_detailed_message()}")
        print(f"\n❌ Error during trade suggestion: {e}")
        return 1
    except Exception as e:
        logger.critical(f"An unhandled critical error occurred: {e}", exc_info=True)
        wrapped_e = wrap_exception(e, DataValidationError, "An unexpected error occurred during trade suggestion.")
        print(f"\n❌ An unexpected critical error occurred: {wrapped_e}")
        print("Please check the log file for more details.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
