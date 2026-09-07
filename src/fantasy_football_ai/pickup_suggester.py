import os
import sys

import pandas as pd
from tabulate import tabulate

from fantasy_football_ai.analysis import calculate_fantasy_points, find_waiver_gems, recommend_pickups
from fantasy_football_ai.data_utils import load_available_players, load_config, load_my_team, load_player_stats

# Add src to path for imports
from fantasy_football_ai.errors import ConfigurationError, DataValidationError, FileOperationError
from fantasy_football_ai.utils.logging import get_logger, setup_logging

# Set up logging
setup_logging(level='INFO', format_type='console', log_file='logs/pickup_suggester.log')
logger = get_logger(__name__)

# Define file paths
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
AVAILABLE_PLAYERS_PATH = os.path.join(PROJECT_ROOT, 'data', 'available_players.csv')
PLAYER_STATS_PATH = os.path.join(PROJECT_ROOT, 'data', 'player_stats.csv')
MY_TEAM_PATH = os.path.join(PROJECT_ROOT, 'data', 'my_team.md')

# Load configuration from config.yaml
CONFIG_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', '..', 'config.yaml'
)

def suggest_pickups() -> int:
    """
    Main function to generate pickup suggestions with comprehensive error handling.
    
    Returns:
        Exit code (0 for success, 1 for error)
    """
    try:
        logger.info("Starting pickup suggestion process")
        
        # Step 1: Load configuration
        logger.info("Step 1: Loading configuration")
        config = load_config()
        
        # Step 2: Load data files
        logger.info("Step 2: Loading data files")
        available_players = load_available_players(AVAILABLE_PLAYERS_PATH)
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
        
        # Step 3: Calculate player values
        logger.info("Step 3: Calculating player values")
        scoring_rules = config.get('scoring_rules', {})
        player_value = calculate_fantasy_points(player_stats.copy(), scoring_rules)
        
        # Step 4: Generate pickup recommendations
        logger.info("Step 4: Generating pickup recommendations")
        recommendations_df = recommend_pickups(available_players, player_value, my_team, config)  # noqa: F841
        
        # Step 5: Display general recommendations
        # Removed due to inaccuracies in ESPN API's free agent list.
        # Focusing on Waiver Wire Gems instead.
        
        # Step 6: Find and display waiver gems
        logger.info("Step 6: Finding waiver wire gems")
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
                display_gems_df['Target Share'] = display_gems_df['Target Share'].apply(
                    lambda x: f"{x:.1%}" if pd.notna(x) else "N/A"
                )
                display_gems_df['Air Yards Share'] = display_gems_df['Air Yards Share'].apply(
                    lambda x: f"{x:.1%}" if pd.notna(x) else "N/A"
                )
            except Exception as e:  # noqa: BLE001
                logger.warning(f"Error formatting percentages: {e}")
            
            print(tabulate(display_gems_df, headers='keys', tablefmt='fancy_grid'))
            logger.info(f"Displayed {len(display_gems_df)} waiver wire gems")
        else:
            print("\nNo waiver wire gems identified at this time.")
            logger.info("No waiver wire gems found")
        
        print("\n✓ Pickup suggester completed successfully!")
        logger.info("Pickup suggestion process completed successfully")
        return 0
        
    except KeyboardInterrupt:
        logger.info("Process interrupted by user")
        print("\nProcess interrupted by user.")
        return 130
    except (ConfigurationError, FileOperationError, DataValidationError) as e:
        logger.error(f"Pickup suggestion error: {e.get_detailed_message()}")
        print(f"\n❌ Error during pickup suggestion: {e}")
        return 1
    except Exception as e:
        logger.critical(f"An unhandled critical error occurred: {e}", exc_info=True)
        print(f"\n❌ An unexpected critical error occurred: {e}")
        print("Please check the log file for more details.")
        return 1


def main() -> int:
    """Entry point with proper error handling."""
    return suggest_pickups()


if __name__ == "__main__":
    sys.exit(main())
