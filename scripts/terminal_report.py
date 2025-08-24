#!/usr/bin/env python3
################################################################################
#
# Script Name: terminal_report.py
# ----------------
# Generates a comprehensive fantasy football analysis report for display in the terminal.
#
# @author Nicholas Wilde, 0xb299a622
# @date 2025-08-20
# @version 0.1.0
#
################################################################################

import pandas as pd
import os
import sys
from datetime import datetime
import argparse
from tabulate import tabulate

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from fantasy_ai.errors import (
    FileOperationError,
    DataValidationError,
    wrap_exception
)
from fantasy_ai.utils.logging import setup_logging, get_logger

# Set up logging
setup_logging(level='INFO', format_type='console', log_file='logs/terminal_report.log')
logger = get_logger(__name__)

# Assume the analysis.py script is in the same directory and can be imported
from analysis import (
    get_advanced_draft_recommendations,
    check_bye_week_conflicts,
    get_trade_recommendations,
    calculate_fantasy_points,
    get_team_roster,
    analyze_team_needs
)

import analysis

from analyze_last_game import analyze_last_game
from analyze_next_game import analyze_next_game

# Helper function to normalize player names, e.g., 'Patrick Mahomes' to 'P.Mahomes'
def normalize_player_name(name):
    parts = name.split()
    if len(parts) >= 2:
        return f"{parts[0][0]}.{parts[-1]}"
    return name

def get_pickup_suggestions(available_players_df):
    """
    Suggests top 5 waiver wire pickups based on VOR.
    """
    return available_players_df.sort_values(by='vor', ascending=False).head(5)

def get_trade_suggestions(df):
    """
    Suggests sell-high and buy-low trade candidates.
    """
    week = df['week'].max()
    this_week_df = df[df['week'] == week]
    last_week_df = df[df['week'] < week]
    player_avg_pts = last_week_df.groupby('player_display_name')['fantasy_points'].mean().reset_index()
    player_avg_pts.rename(columns={'fantasy_points': 'avg_fantasy_points'}, inplace=True)
    merged_df = pd.merge(this_week_df, player_avg_pts, on='player_display_name', how='left')
    merged_df['point_difference'] = merged_df['fantasy_points'] - merged_df['avg_fantasy_points']
    sell_high = merged_df[merged_df['point_difference'] > 10].sort_values(by='point_difference', ascending=False)
    buy_low = merged_df[merged_df['point_difference'] < -5].sort_values(by='point_difference', ascending=True)
    return sell_high, buy_low

def format_dataframe_for_terminal(df, column_names):
    """
    Formats a pandas DataFrame for better terminal output.
    """
    return tabulate(df[column_names], headers=column_names, tablefmt="fancy_grid", floatfmt=".2f", showindex=False)

def generate_terminal_report(draft_recs_df, bye_conflicts_df, trade_recs_df, team_analysis_str, my_team_raw, pickup_suggestions_df, sell_high_df, buy_low_df, positional_breakdown_df, last_game_analysis_str, next_game_analysis_str, my_team_df):

    """
    Generates a Markdown report to the terminal from the analysis data.

    Args:
        draft_recs_df (pd.DataFrame): DataFrame with draft recommendations.
        bye_conflicts_df (pd.DataFrame): DataFrame with bye week conflicts.
        trade_recs_df (pd.DataFrame): DataFrame with trade recommendations.
        team_analysis_str (str): Markdown string with team analysis.
        my_team_raw (list): List of player names in my team.
        pickup_suggestions_df (pd.DataFrame): DataFrame with pickup suggestions.
        sell_high_df (pd.DataFrame): DataFrame with sell-high trade suggestions.
        buy_low_df (pd.DataFrame): DataFrame with buy-low trade suggestions.
    """
    current_date = datetime.now().strftime('%Y-%m-%d')

    # Print to stdout
    print(f"---\ntitle: 'Fantasy Football Analysis: {current_date}'\ndate: {current_date}\ncategories:\n  - Fantasy Football\n  - Weekly Analysis\n  - 2025 Season\ntags:\n  - fantasy-football\n  - analysis\n  - 2025-season\n---\n\nWelcome to your weekly fantasy football analysis, powered by Gemini. This report provides a summary of player performance and key recommendations to help you dominate your league.\n\n---\n\n## My Team Analysis\n\n### Current Roster\n\n")
    
    # Ensure only one entry per player in the roster display
    my_roster_unique_players = my_team_df.drop_duplicates(subset=['player_name']).copy()

    my_roster_display_df = my_roster_unique_players[['player_name', 'recent_team', 'position', 'vor', 'consistency_std_dev']].copy()
    my_roster_display_df.rename(columns={
        'player_name': 'Player',
        'recent_team': 'Team',
        'position': 'Position',
        'vor': 'VOR',
        'consistency_std_dev': 'Consistency (Std Dev)'
    }, inplace=True)
    print(format_dataframe_for_terminal(my_roster_display_df, ['Player', 'Team', 'Position', 'VOR', 'Consistency (Std Dev)']))
    print("\n")

    print(team_analysis_str)

    print("#### Positional Breakdown (VOR vs. League Average)\n")
    print(format_dataframe_for_terminal(positional_breakdown_df, ['Position', 'My Team Avg VOR', 'League Avg VOR', 'VOR Difference']))
    print("---")

    # Last Game Analysis
    print("## Last Game Analysis\n")
    print(last_game_analysis_str)
    print("\n---")

    # Next Game Analysis
    print("## Next Game Analysis\n")
    print(next_game_analysis_str)
    print("\n---")


    # Draft Recommendations
    print("## Top Players to Target\n")
    print("These players are ranked based on their **Value Over Replacement (VOR)**, a metric that measures a player's value relative to a typical starter at their position. We also look at consistency to see who you can rely on week in and week out.\n")
    
    draft_recs_display_df = draft_recs_df[['player_name', 'recent_team', 'position', 'vor', 'consistency_std_dev']].head(10).copy()
    draft_recs_display_df.rename(columns={
        'player_name': 'Player',
        'recent_team': 'Team',
        'position': 'Position',
        'vor': 'VOR',
        'consistency_std_dev': 'Consistency (Std Dev)'
    }, inplace=True)
    
    print(format_dataframe_for_terminal(draft_recs_display_df, ['Player', 'Team', 'Position', 'VOR', 'Consistency (Std Dev)']))
    print("---")

    # Bye Week Analysis
    print("## Bye Week Cheat Sheet\n")
    if not bye_conflicts_df.empty:
        print("### Heads Up! Potential Bye Week Conflicts\n")
        print("Drafting strategically means planning for bye weeks. The following highly-ranked players share a bye week, which could leave your roster thin. Plan accordingly!\n")

        # Format bye week conflicts
        for _, row in bye_conflicts_df.iterrows():
            print(f"**Week {int(row['bye_week'])}**: {int(row['player_count'])} top players are on bye.")

        print()
    else:
        print("No major bye week conflicts were found among the top-ranked players. Smooth sailing!\n")

    print("---\n")

    # Trade Recommendations
    print("## Smart Trade Targets\n")
    print("Looking to make a move? These are potential trade targets based on their positional value and consistency. Acquiring one of these players could be the key to a championship run.\n")
    
    # Select and rename columns for a more readable trade targets table
    trade_recs_df.rename(columns={'player_name': 'player_display_name'}, inplace=True)
    trade_recs_display_df = trade_recs_df[['player_display_name', 'position', 'recent_team', 'vor', 'consistency_std_dev', 'fantasy_points_ppr', 'bye_week']].copy()
    trade_recs_display_df.rename(columns={
        'player_display_name': 'Player',
        'position': 'Position',
        'recent_team': 'Team',
        'vor': 'VOR',
        'consistency_std_dev': 'Consistency (Std Dev)',
        'fantasy_points_ppr': 'PPR Points',
        'bye_week': 'Bye'
    }, inplace=True)
    
    print(format_dataframe_for_terminal(trade_recs_display_df, ['Player', 'Position', 'Team', 'VOR', 'Consistency (Std Dev)', 'PPR Points', 'Bye']))
    print("\n")

    print("---")

    

    # Pickup Suggestions
    print("## Top Waiver Wire Pickups\n\n")
    print("Here are some of the top players available on the waiver wire, based on their recent performance and potential.\n\n")
    pickup_display_df = pickup_suggestions_df[['player_name', 'position', 'recent_team', 'vor']].copy()
    pickup_display_df.rename(columns={
        'player_name': 'Player',
        'position': 'Position',
        'recent_team': 'Team',
        'vor': 'VOR'
    }, inplace=True)
    print(format_dataframe_for_terminal(pickup_display_df, ['Player', 'Position', 'Team', 'VOR']))
    print("\n")

    print("---")

    # Trade Suggestions
    print("## Trade Suggestions\n\n")
    print("### Sell-High Candidates\n\n")
    sell_high_display_df = sell_high_df[['player_display_name', 'position', 'recent_team', 'fantasy_points', 'avg_fantasy_points', 'point_difference']].copy()
    sell_high_display_df.rename(columns={
        'player_display_name': 'Player',
        'position': 'Position',
        'recent_team': 'Team',
        'fantasy_points': 'Current Week Pts',
        'avg_fantasy_points': 'Avg Pts (Prev Weeks)',
        'point_difference': 'Point Difference'
    }, inplace=True)
    print(format_dataframe_for_terminal(sell_high_display_df, ['Player', 'Position', 'Team', 'Current Week Pts', 'Avg Pts (Prev Weeks)', 'Point Difference']))
    print("\n")
    print("### Buy-Low Candidates\n\n")
    buy_low_display_df = buy_low_df[['player_display_name', 'position', 'recent_team', 'fantasy_points', 'avg_fantasy_points', 'point_difference']].copy()
    buy_low_display_df.rename(columns={
        'player_display_name': 'Player',
        'position': 'Position',
        'recent_team': 'Team',
        'fantasy_points': 'Current Week Pts',
        'avg_fantasy_points': 'Avg Pts (Prev Weeks)',
        'point_difference': 'Point Difference'
    }, inplace=True)
    print(format_dataframe_for_terminal(buy_low_display_df, ['Player', 'Position', 'Team', 'Current Week Pts', 'Avg Pts (Prev Weeks)', 'Point Difference']))
    print("\n")


def main():
    parser = argparse.ArgumentParser(description="Generate a fantasy football analysis report.")
    parser.add_argument(
        "--output-dir",
        default="docs/reports/posts",
        help="The directory to save the report in."
    )
    args = parser.parse_args()

    try:
        # Initialize analysis globals (config, scoring rules, etc.)
        analysis.initialize_globals()

        # Ensure the data file exists before running
        data_file = "data/player_stats.csv"
        if not os.path.exists(data_file):
            raise FileOperationError(
                f"Data file not found at '{data_file}'. Please run 'download_stats.py' first.",
                file_path=data_file,
                operation="read"
            )

        # Create a dummy roster file if it doesn't exist
        roster_file = "data/my_team.md"
        if not os.path.exists(roster_file):
            with open(roster_file, "w") as f:
                f.write("- Patrick Mahomes\n")
                f.write("- Tyreek Hill\n")
                f.write("- Saquon Barkley\n")
                f.write("- Keenan Allen\n")
                f.write("- Travis Kelce\n")

        # Load and process data
        stats_df = pd.read_csv(data_file, low_memory=False)

        stats_with_points = calculate_fantasy_points(stats_df)

        # Add a placeholder bye_week column for demonstration purposes
        if 'week' in stats_with_points.columns:
            stats_with_points['bye_week'] = stats_with_points['week'].apply(lambda x: (x % 14) + 4)
        else:
            stats_with_points['bye_week'] = 0

        # Get analysis data
        draft_recs = get_advanced_draft_recommendations(stats_with_points)

        # Merge recent_team into draft_recs
        draft_recs = pd.merge(draft_recs, stats_with_points[['player_name', 'recent_team']].drop_duplicates(), on='player_name', how='left')

        bye_conflicts = check_bye_week_conflicts(stats_with_points)

        trade_data_combined = pd.merge(
            draft_recs,
            stats_with_points[['player_name', 'fantasy_points_ppr', 'bye_week']].drop_duplicates(subset=['player_name']),
            on='player_name',
            how='left'
        )

        my_team_raw = get_team_roster(roster_file)
        my_team_normalized = [normalize_player_name(name) for name in my_team_raw]
        my_team_df = draft_recs[draft_recs['player_name'].isin(my_team_normalized)]
        team_analysis_str, positional_breakdown_df = analyze_team_needs(my_team_df, draft_recs)

        trade_recs = get_trade_recommendations(trade_data_combined, team_roster=my_team_normalized)

        available_players_df = draft_recs[~draft_recs['player_name'].isin(my_team_normalized)]
        pickup_suggestions = get_pickup_suggestions(available_players_df)
        sell_high_suggestions, buy_low_suggestions = get_trade_suggestions(stats_with_points)

        last_game_analysis_str = analyze_last_game()

        next_game_analysis_str = analyze_next_game()

        generate_terminal_report(draft_recs, bye_conflicts, trade_recs, team_analysis_str, my_team_raw, pickup_suggestions, sell_high_suggestions, buy_low_suggestions, positional_breakdown_df, last_game_analysis_str, next_game_analysis_str, my_team_df)
        return 0
    except (FileOperationError, DataValidationError) as e:
        logger.error(f"Terminal report error: {e.get_detailed_message()}")
        print(f"\n❌ Error: {e}")
        return 1
    except Exception as e:
        logger.critical(f"An unhandled critical error occurred: {e}", exc_info=True)
        wrapped_e = wrap_exception(e, DataValidationError, "An unexpected error occurred during terminal report generation.")
        print(f"\n❌ An unexpected critical error occurred: {wrapped_e}")
        print("Please check the log file for more details.")
        return 1
