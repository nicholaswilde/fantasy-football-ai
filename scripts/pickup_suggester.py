#!/usr/bin/env python3
"""
Script to suggest waiver wire pickups with comprehensive error handling.

Suggests waiver wire pickups based on player performance and team needs
with robust error handling and data validation.

@author Nicholas Wilde, 0xb299a622
@date 2025-08-20
@version 0.2.0
"""

import pandas as pd
import os
import sys
import yaml
from tabulate import tabulate

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from fantasy_ai.errors import (
    APIError, AuthenticationError, ConfigurationError, 
    FileOperationError, DataValidationError, wrap_exception
)
from fantasy_ai.utils.logging import setup_logging, get_logger

# Set up logging
setup_logging(level='INFO', format_type='console', log_file='logs/pickup_suggester.log')
logger = get_logger(__name__)

# Define file paths
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AVAILABLE_PLAYERS_PATH = os.path.join(PROJECT_ROOT, 'data', 'available_players.csv')
PLAYER_STATS_PATH = os.path.join(PROJECT_ROOT, 'data', 'player_stats.csv')
MY_TEAM_PATH = os.path.join(PROJECT_ROOT, 'data', 'my_team.md')

# Load configuration from config.yaml
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

def load_available_players(file_path: str) -> pd.DataFrame:
    """
    Load available players from CSV file with error handling.
    
    Args:
        file_path: Path to available players CSV file
        
    Returns:
        DataFrame with available players data
        
    Raises:
        FileOperationError: If file cannot be read
        DataValidationError: If data format is invalid
    """
    try:
        logger.debug(f"Loading available players from {file_path}")
        
        if not os.path.exists(file_path):
            logger.warning(f"Available players file not found at {file_path}, returning empty DataFrame")
            return pd.DataFrame()
            
        df = pd.read_csv(file_path, low_memory=False)
        
        if df.empty:
            logger.warning(f"Available players file is empty: {file_path}")
            return pd.DataFrame()
        
        # Rename columns to match player_stats_df for merging
        column_mapping = {'name': 'player_display_name', 'pro_team': 'recent_team'}
        df = df.rename(columns=column_mapping)
        
        logger.info(f"Successfully loaded {len(df)} available players")
        return df
        
    except pd.errors.EmptyDataError as e:
        raise DataValidationError(
            f"Available players file is empty or invalid: {file_path}",
            field_name="available_players_file",
            expected_type="valid CSV with player data",
            actual_value="empty file",
            original_error=e
        )
    except pd.errors.ParserError as e:
        raise DataValidationError(
            f"Cannot parse available players CSV file: {file_path}",
            field_name="available_players_file",
            expected_type="valid CSV format",
            actual_value="malformed CSV",
            original_error=e
        )
    except PermissionError as e:
        raise FileOperationError(
            f"Permission denied reading available players file: {file_path}",
            file_path=file_path,
            operation="read",
            original_error=e
        )
    except Exception as e:
        raise wrap_exception(
            e, FileOperationError,
            f"Failed to load available players from {file_path}",
            file_path=file_path,
            operation="read"
        )


def load_player_stats(file_path: str) -> pd.DataFrame:
    """
    Load player stats from CSV file with error handling.
    
    Args:
        file_path: Path to player stats CSV file
        
    Returns:
        DataFrame with player stats data
        
    Raises:
        FileOperationError: If file cannot be read
        DataValidationError: If data format is invalid
    """
    try:
        logger.debug(f"Loading player stats from {file_path}")
        
        if not os.path.exists(file_path):
            raise FileOperationError(
                f"Player stats file not found: {file_path}. Please run 'task download_stats' first.",
                file_path=file_path,
                operation="read"
            )
            
        df = pd.read_csv(file_path, low_memory=False)
        
        if df.empty:
            raise DataValidationError(
                f"Player stats file is empty: {file_path}",
                field_name="player_stats_file",
                expected_type="CSV with player statistics",
                actual_value="empty file"
            )
        
        # Validate required columns
        required_cols = ['player_display_name', 'position', 'fantasy_points_ppr', 'week']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            raise DataValidationError(
                f"Player stats file missing required columns: {missing_cols}",
                field_name="player_stats_columns",
                expected_type=f"columns: {required_cols}",
                actual_value=f"missing: {missing_cols}"
            )
        
        logger.info(f"Successfully loaded {len(df)} player stat records")
        return df
        
    except (DataValidationError, FileOperationError):
        raise  # Re-raise our custom exceptions
    except pd.errors.EmptyDataError as e:
        raise DataValidationError(
            f"Player stats file is empty or invalid: {file_path}",
            field_name="player_stats_file",
            expected_type="valid CSV with player data",
            actual_value="empty file",
            original_error=e
        )
    except pd.errors.ParserError as e:
        raise DataValidationError(
            f"Cannot parse player stats CSV file: {file_path}",
            field_name="player_stats_file",
            expected_type="valid CSV format",
            actual_value="malformed CSV",
            original_error=e
        )
    except PermissionError as e:
        raise FileOperationError(
            f"Permission denied reading player stats file: {file_path}",
            file_path=file_path,
            operation="read",
            original_error=e
        )
    except Exception as e:
        raise wrap_exception(
            e, FileOperationError,
            f"Failed to load player stats from {file_path}",
            file_path=file_path,
            operation="read"
        )


def load_my_team(file_path: str) -> dict:
    """
    Load and parse the user's team from the Markdown file with error handling.
    
    Args:
        file_path: Path to my_team.md file
        
    Returns:
        Dictionary with team roster by position
        
    Raises:
        FileOperationError: If file cannot be read
        DataValidationError: If file format is invalid
    """
    my_team = {
        'QB': [], 'RB': [], 'WR': [], 'TE': [], 'FLEX': [], 'K': [], 'DST': [], 'BENCH': []
    }
    current_position = None
    
    try:
        logger.debug(f"Loading my team from {file_path}")
        
        if not os.path.exists(file_path):
            logger.warning(f"My team file not found at {file_path}, cannot analyze team needs")
            return my_team
            
        with open(file_path, 'r', encoding='utf-8') as f:
            line_count = 0
            player_count = 0
            
            for line in f:
                line_count += 1
                line = line.strip()
                
                if line.startswith('## '):
                    pos = line.replace('## ', '').strip().upper()
                    if pos in my_team:
                        current_position = pos
                    else:
                        current_position = None
                        logger.debug(f"Unknown position '{pos}' found in team file at line {line_count}")
                        
                elif line.startswith('- ') and current_position:
                    player_name = line.replace('- ', '').strip()
                    if player_name:  # Only add non-empty player names
                        my_team[current_position].append(player_name)
                        player_count += 1
                        
        logger.info(f"Successfully loaded team with {player_count} players from {len([pos for pos, players in my_team.items() if players])} positions")
        return my_team
        
    except UnicodeDecodeError as e:
        raise DataValidationError(
            f"Cannot decode my team file (encoding issue): {file_path}",
            field_name="my_team_file_encoding",
            expected_type="UTF-8 encoded text",
            actual_value="unreadable encoding",
            original_error=e
        )
    except PermissionError as e:
        raise FileOperationError(
            f"Permission denied reading my team file: {file_path}",
            file_path=file_path,
            operation="read",
            original_error=e
        )
    except Exception as e:
        raise wrap_exception(
            e, FileOperationError,
            f"Failed to load my team from {file_path}",
            file_path=file_path,
            operation="read"
        )

def calculate_player_value(player_stats_df):
    """Calculates average points per game (PPG) for players using fantasy_points_ppr."""
    # Group by player and calculate total PPR points and games played
    player_summary = player_stats_df.groupby(['player_display_name', 'position', 'recent_team']).agg(
        total_fantasy_points_ppr=('fantasy_points_ppr', 'sum'),
        games_played=('week', 'nunique') # Count unique weeks played
    ).reset_index()

    # Calculate AvgPoints (PPG)
    player_summary['AvgPoints'] = player_summary['total_fantasy_points_ppr'] / player_summary['games_played']

    # Handle cases where games_played might be 0 to avoid division by zero
    player_summary['AvgPoints'] = player_summary['AvgPoints'].fillna(0)

    return player_summary[['player_display_name', 'position', 'recent_team', 'AvgPoints']]

def identify_team_needs(my_team_roster, config=None):
    """Identifies positions where the user's team needs improvement or depth."""
    needs = {}
    # Define standard roster sizes from config.yaml
    if config is None:
        try:
            config = load_config()
        except Exception:
            logger.warning("Could not load config for team needs analysis, using defaults")
            config = {}
    
    roster_settings = config.get('roster_settings', {})
    standard_roster_spots = {
        'QB': roster_settings.get('QB', 1),
        'RB': roster_settings.get('RB', 2),
        'WR': roster_settings.get('WR', 2),
        'TE': roster_settings.get('TE', 1),
        'RB/WR': roster_settings.get('RB_WR', 1), # Using RB_WR for flex
        'WR/TE': roster_settings.get('WR_TE', 1), # Using WR_TE for flex
        'K': roster_settings.get('K', 1),
        'DST': roster_settings.get('DST', 1),
        'DP': roster_settings.get('DP', 2),
        'BE': roster_settings.get('BE', 7),
        'IR': roster_settings.get('IR', 1)
    }

    # Map config keys to the keys used in my_team_roster if they differ
    # For example, config might have RB_WR but my_team_roster uses FLEX
    # This needs careful consideration based on how my_team.md is generated
    # For now, I'll assume direct mapping or handle common flex cases.
    
    # Simplified mapping for common positions, assuming my_team_roster uses standard position names
    # and FLEX is a combination.
    mapped_roster_settings = {
        'QB': roster_settings.get('QB', 1),
        'RB': roster_settings.get('RB', 2),
        'WR': roster_settings.get('WR', 2),
        'TE': roster_settings.get('TE', 1),
        'K': roster_settings.get('K', 1),
        'DST': roster_settings.get('DST', 1),
    }
    # Add flex spots to the total count for RB, WR, TE if they exist in config
    mapped_roster_settings['RB'] += roster_settings.get('RB_WR', 0)
    mapped_roster_settings['WR'] += roster_settings.get('RB_WR', 0) + roster_settings.get('WR_TE', 0)
    mapped_roster_settings['TE'] += roster_settings.get('WR_TE', 0)

    for pos, count in mapped_roster_settings.items():
        if len(my_team_roster.get(pos, [])) < count:
            needs[pos] = count - len(my_team_roster.get(pos, []))
    
    # Consider bench spots as well
    bench_needed = roster_settings.get('BE', 7) - len(my_team_roster.get('BENCH', []))
    if bench_needed > 0:
        needs['BENCH'] = bench_needed

    return needs

def recommend_pickups(available_players_df, player_value_df, my_team_roster):
    """
    Generates pickup recommendations."""
    if available_players_df.empty or player_value_df.empty:
        return pd.DataFrame()

    # Merge available players with their performance data
    merged_df = pd.merge(
        available_players_df,
        player_value_df,
        on=['player_display_name', 'position', 'recent_team'], # Assuming these columns exist in both
        how='inner'
    )

    # Filter out players already on my team
    my_team_players = [player for sublist in my_team_roster.values() for player in sublist]
    merged_df = merged_df[~merged_df['player_display_name'].isin(my_team_players)]

    team_needs = identify_team_needs(my_team_roster)
    
    recommendations = []

    # Prioritize positions with needs
    for pos, count in sorted(team_needs.items(), key=lambda item: item[1], reverse=True):
        if pos == 'FLEX':
            # For FLEX, recommend top RBs, WRs, TEs
            flex_candidates = merged_df[merged_df['position'].isin(['RB', 'WR', 'TE'])]
            top_players_at_pos = flex_candidates.sort_values(by='AvgPoints', ascending=False).head(count * 2)
        elif pos in ['K', 'DST']:
            continue
        else:
            top_players_at_pos = merged_df[
                (merged_df['position'] == pos)
            ].sort_values(by='AvgPoints', ascending=False).head(count * 2) # Get a few more than needed

        if not top_players_at_pos.empty:
            recommendations.append(top_players_at_pos)

    # Also show top overall available players if no specific needs
    if not team_needs:
        top_overall = merged_df.sort_values(by='AvgPoints', ascending=False).head(10)
        if not top_overall.empty:
            recommendations.append(top_overall)

    if not recommendations:
        return pd.DataFrame()
    
    return pd.concat(recommendations).drop_duplicates().reset_index(drop=True)

def find_waiver_gems(player_stats_df, my_team_roster):
    """
    Identifies waiver wire 'gems' based on recent usage trends and underperforming fantasy points.
    """
    if player_stats_df.empty:
        return pd.DataFrame()

    # Filter out players already on my team
    my_team_players = [player for sublist in my_team_roster.values() for player in sublist]
    available_stats_df = player_stats_df[~player_stats_df['player_display_name'].isin(my_team_players)].copy()

    if available_stats_df.empty:
        return pd.DataFrame()

    # Ensure 'week' is numeric and get the current (max) week
    available_stats_df['week'] = pd.to_numeric(available_stats_df['week'], errors='coerce')
    current_week = available_stats_df['week'].max()
    
    if pd.isna(current_week):
        print("Warning: Could not determine current week from player stats.")
        return pd.DataFrame()

    # Calculate season averages for all players
    season_avg_df = available_stats_df.groupby(['player_display_name', 'position', 'recent_team']).agg(
        season_ppr_avg=('fantasy_points_ppr', 'mean'),
        season_games_played=('week', 'nunique')
    ).reset_index()
    
    # Filter for players with at least 3 games played in the season to have a meaningful average
    season_avg_df = season_avg_df[season_avg_df['season_games_played'] >= 3]

    # Calculate recent (last 3 weeks) averages
    recent_weeks = [current_week, current_week - 1, current_week - 2]
    recent_stats_df = available_stats_df[available_stats_df['week'].isin(recent_weeks)].copy()

    if recent_stats_df.empty:
        return pd.DataFrame()

    recent_avg_df = recent_stats_df.groupby(['player_display_name', 'position', 'recent_team']).agg(
        recent_ppr_avg=('fantasy_points_ppr', 'mean'),
        recent_targets_avg=('targets', 'mean'),
        recent_carries_avg=('carries', 'mean'),
        recent_target_share_avg=('target_share', 'mean'),
        recent_air_yards_share_avg=('air_yards_share', 'mean'),
        recent_games_played=('week', 'nunique')
    ).reset_index()

    # Merge season and recent averages
    merged_gems_df = pd.merge(
        recent_avg_df,
        season_avg_df,
        on=['player_display_name', 'position', 'recent_team'],
        how='inner'
    )

    # Filter for players who played in at least 2 of the last 3 weeks
    merged_gems_df = merged_gems_df[merged_gems_df['recent_games_played'] >= 2]

    # Apply gem logic
    # High Usage:
    # WR/TE: >= 7 targets/game OR >= 20% target share OR >= 25% air yards share in last 3 weeks
    # RB: >= 15 carries/game in last 3 weeks
    # Underperforming: recent_ppr_avg < season_ppr_avg

    # Define thresholds
    WR_TE_TARGETS_THRESHOLD = 7
    WR_TE_TARGET_SHARE_THRESHOLD = 0.20
    WR_TE_AIR_YARDS_SHARE_THRESHOLD = 0.25
    RB_CARRIES_THRESHOLD = 15

    # Apply conditions
    is_wr_te = merged_gems_df['position'].isin(['WR', 'TE'])
    is_rb = merged_gems_df['position'] == 'RB'

    high_usage_wr_te = (
        (merged_gems_df['recent_targets_avg'] >= WR_TE_TARGETS_THRESHOLD) |
        (merged_gems_df['recent_target_share_avg'] >= WR_TE_TARGET_SHARE_THRESHOLD) |
        (merged_gems_df['recent_air_yards_share_avg'] >= WR_TE_AIR_YARDS_SHARE_THRESHOLD)
    )
    high_usage_rb = (merged_gems_df['recent_carries_avg'] >= RB_CARRIES_THRESHOLD)

    underperforming = (merged_gems_df['recent_ppr_avg'] < merged_gems_df['season_ppr_avg'])

    # Combine all conditions
    waiver_gems = merged_gems_df[
        ((is_wr_te & high_usage_wr_te) | (is_rb & high_usage_rb)) |
        underperforming
    ].sort_values(by='recent_ppr_avg', ascending=False) # Sort by recent PPR for display

    return waiver_gems[['player_display_name', 'position', 'recent_team',
                        'recent_ppr_avg', 'season_ppr_avg',
                        'recent_targets_avg', 'recent_carries_avg',
                        'recent_target_share_avg', 'recent_air_yards_share_avg']]

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
        try:
            player_value = calculate_player_value(player_stats.copy())
        except Exception as e:
            raise wrap_exception(
                e, DataValidationError,
                "Failed to calculate player values from stats data",
                field_name="player_value_calculation"
            )
        
        # Step 4: Generate pickup recommendations
        logger.info("Step 4: Generating pickup recommendations")
        try:
            recommendations_df = recommend_pickups(available_players, player_value, my_team)
        except Exception as e:
            raise wrap_exception(
                e, DataValidationError,
                "Failed to generate pickup recommendations",
                field_name="pickup_recommendations"
            )
        
        # Step 5: Display general recommendations
        logger.info("Step 5: Displaying general recommendations")
        if not recommendations_df.empty:
            print("\n--- Top Waiver Wire Pickups ---")
            display_df = recommendations_df[['player_display_name', 'position', 'recent_team', 'AvgPoints']].copy()
            display_df.rename(columns={
                'player_display_name': 'Player',
                'position': 'Position',
                'recent_team': 'Team',
                'AvgPoints': 'Avg Pts/Game'
            }, inplace=True)
            print(tabulate(display_df, headers='keys', tablefmt='fancy_grid'))
            logger.info(f"Displayed {len(display_df)} pickup recommendations")
        else:
            print("\nNo general waiver wire pickup suggestions at this time.")
            logger.info("No pickup recommendations found")
        
        # Step 6: Find and display waiver gems
        logger.info("Step 6: Finding waiver wire gems")
        try:
            waiver_gems_df = find_waiver_gems(player_stats.copy(), my_team)
        except Exception as e:
            logger.warning(f"Error finding waiver gems: {e}")
            waiver_gems_df = pd.DataFrame()
        
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
                'recent_target_share_avg': 'Recent Target Share Avg',
                'recent_air_yards_share_avg': 'Recent Air Yards Share Avg'
            }, inplace=True)
            
            # Format percentages safely
            try:
                display_gems_df['Recent Target Share Avg'] = display_gems_df['Recent Target Share Avg'].apply(
                    lambda x: f"{x:.1%}" if pd.notna(x) else "N/A"
                )
                display_gems_df['Recent Air Yards Share Avg'] = display_gems_df['Recent Air Yards Share Avg'].apply(
                    lambda x: f"{x:.1%}" if pd.notna(x) else "N/A"
                )
            except Exception as e:
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
    except ConfigurationError as e:
        logger.error(f"Configuration error: {e.get_detailed_message()}")
        print(f"\n❌ Configuration Error: {e}")
        print("\nTroubleshooting:")
        print("- Run 'task init' to create configuration file")
        print("- Check config.yaml for valid settings")
        return 1
    except (FileOperationError, DataValidationError) as e:
        logger.error(f"Data error: {e.get_detailed_message()}")
        print(f"\n❌ Error: {e}")
        print("\nTroubleshooting:")
        if "player_stats" in str(e):
            print("- Run 'task download_stats' to download player statistics")
        if "my_team" in str(e):
            print("- Run 'task get_my_team' to fetch your team roster")
        if "available_players" in str(e):
            print("- Run 'task get_available_players' to get available players list")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        print(f"\n❌ Unexpected error occurred: {e}")
        print("Check the log file for more details.")
        return 1


def main() -> int:
    """Entry point with proper error handling."""
    return suggest_pickups()


if __name__ == "__main__":
    sys.exit(main())