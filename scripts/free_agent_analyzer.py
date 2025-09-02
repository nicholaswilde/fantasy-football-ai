#!/usr/bin/env python3
################################################################################
#
# Script Name: free_agent_analyzer.py
# ----------------
# Analyzes player statistics to identify potential waiver wire pickups,
# focusing on "Waiver Wire Gems" (high usage, underperforming players).
#
# @author Nicholas Wilde, 0xb299a622
# @date 01 September 2025
# @version 0.1.0
#
################################################################################

import pandas as pd
import os
import sys
from tabulate import tabulate

# Add src to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from fantasy_ai.errors import (
    FileOperationError,
    DataValidationError,
    ConfigurationError,
    wrap_exception
)
from fantasy_ai.utils.logging import setup_logging, get_logger
from scripts.utils import load_config, load_player_stats, load_my_team
from scripts.analysis import find_waiver_gems

# Set up logging
setup_logging(level='INFO', format_type='console', log_file='logs/free_agent_analyzer.log')
logger = get_logger(__name__)

# Define file paths
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLAYER_STATS_PATH = os.path.join(PROJECT_ROOT, 'data', 'player_stats.csv')
MY_TEAM_PATH = os.path.join(PROJECT_ROOT, 'data', 'my_team.md')

def analyze_free_agents() -> int:
    """
    Main function to identify and display waiver wire gems.

    Returns:
        Exit code (0 for success, 1 for error)
    """
    try:
        logger.info("Starting free agent analysis process")

        # Step 1: Load configuration
        logger.info("Step 1: Loading configuration")
        config = load_config()

        # Step 2: Load data files
        logger.info("Step 2: Loading data files")
        player_stats = load_player_stats(PLAYER_STATS_PATH)
        my_team = load_my_team(MY_TEAM_PATH)

        if player_stats.empty:
            raise DataValidationError(
                "Player stats data is empty. Cannot proceed with recommendations.",
                field_name="player_stats",
                expected_type="non-empty DataFrame",
                actual_value="empty DataFrame"
            )

        # Validate required columns
        required_cols = ['player_display_name', 'position']
        missing_cols = [col for col in required_cols if col not in player_stats.columns]
        if missing_cols:
            raise DataValidationError(
                f"Player stats file missing required columns: {missing_cols}",
                field_name="player_stats_columns",
                expected_type=f"columns: {required_cols}",
                actual_value=f"missing: {missing_cols}"
            )

        # Step 3: Find and display waiver gems
        logger.info("Step 3: Finding waiver wire gems")
        waiver_gems_df = find_waiver_gems(player_stats.copy(), my_team)

        print("\n--- Waiver Wire Gems (High Usage, Underperforming) ---")
        if not waiver_gems_df.empty:
            display_gems_df = waiver_gems_df.copy()
            display_gems_df.rename(columns={
                'player_display_name': 'Player',
                'position': 'Position',
                'recent_team': 'Team',
                'recent_ppr_avg': 'Recent PPR Avg',
                'season_ppr_avg': 'Season PPR Avg',
                'recent_targets_avg': 'Recent Targets Avg',
                'recent_carries_avg': 'Recent Carries Avg',
                'target_share': 'Target Share',
                'air_yards_share': 'Air Yards Share'
            }, inplace=True)
            
            # Format percentages safely
            try:
                if 'Target Share' in display_gems_df.columns:
                    display_gems_df['Target Share'] = display_gems_df['Target Share'].apply(
                        lambda x: f"{x:.1%}" if pd.notna(x) else "N/A"
                    )
                if 'Air Yards Share' in display_gems_df.columns:
                    display_gems_df['Air Yards Share'] = display_gems_df['Air Yards Share'].apply(
                        lambda x: f"{x:.1%}" if pd.notna(x) else "N/A"
                    )
            except Exception as e:
                logger.warning(f"Error formatting percentages: {e}")
            
            # Select and order columns for display
            display_cols = [
                'Player', 'Position', 'Team', 'Recent PPR Avg', 'Season PPR Avg',
                'Recent Targets Avg', 'Recent Carries Avg', 'Target Share', 'Air Yards Share'
            ]
            # Filter out columns that might not exist in the DataFrame
            display_cols = [col for col in display_cols if col in display_gems_df.columns]

            print(tabulate(display_gems_df[display_cols], headers='keys', tablefmt='fancy_grid', showindex=False))
            logger.info(f"Displayed {len(display_gems_df)} waiver wire gems")
        else:
            print("\nNo waiver wire gems identified at this time.")
            logger.info("No waiver wire gems found")
        
        print("\n✓ Free agent analysis completed successfully!")
        logger.info("Free agent analysis process completed successfully")
        return waiver_gems_df
        
    except KeyboardInterrupt:
        logger.info("Process interrupted by user")
        print("\nProcess interrupted by user.")
        return 130
    except (ConfigurationError, FileOperationError, DataValidationError) as e:
        logger.error(f"Free agent analysis error: {e.get_detailed_message()}")
        print(f"\n❌ Error during free agent analysis: {e}")
        return 1
    except Exception as e:
        logger.critical(f"An unhandled critical error occurred: {e}", exc_info=True)
        print(f"\n❌ An unexpected critical error occurred: {e}")
        print("Please check the log file for more details.")
        return 1

def main() -> int:
    """Entry point with proper error handling."""
    return analyze_free_agents()


if __name__ == "__main__":
    sys.exit(main())
