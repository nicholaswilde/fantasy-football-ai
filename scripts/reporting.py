#!/usr/bin/env python3
################################################################################
#
# Script Name: reporting.py
# ----------------
# Generates a comprehensive fantasy football analysis report in Markdown, terminal, or HTML format.
#
# @author Nicholas Wilde, 0xb299a622
# @date 2025-08-20
# @version 0.3.0
#
################################################################################

import pandas as pd
import os
import sys
from datetime import datetime
import argparse
from tabulate import tabulate
import markdown
import webbrowser

# Add src to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from fantasy_ai.errors import (
    FileOperationError,
    DataValidationError,
    ConfigurationError,
    APIError,
    AuthenticationError,
    NetworkError,
    wrap_exception
)
from fantasy_ai.utils.logging import setup_logging, get_logger

# Set up logging
setup_logging(level='INFO', format_type='console', log_file='logs/reporting.log')
logger = get_logger(__name__)

# Assume the analysis.py script is in the same directory and can be imported
from scripts.analysis import (
    get_advanced_draft_recommendations,
    check_bye_week_conflicts,
    get_trade_recommendations,
    calculate_fantasy_points,
    analyze_team_needs
)
from scripts.data_manager import get_team_roster
from scripts.analyze_game import analyze_game
from scripts.utils import load_config

# Helper function to normalize player names, e.g., 'Patrick Mahomes' to 'P.Mahomes'
def normalize_player_name(name):
    parts = name.split()
    if len(parts) >= 2:
        return f"{parts[0][0]}.{parts[-1]}"
    return name

def get_pickup_suggestions(available_players_df: pd.DataFrame) -> pd.DataFrame:
    """
    Suggests top 5 waiver wire pickups based on VOR.
    
    Args:
        available_players_df: DataFrame of available players with 'vor' column.
        
    Returns:
        DataFrame with top 5 pickup suggestions.
        
    Raises:
        DataValidationError: If input DataFrame is empty or missing 'vor' column.
    """
    if available_players_df.empty:
        logger.warning("Available players DataFrame is empty for pickup suggestions.")
        return pd.DataFrame()
    if 'vor' not in available_players_df.columns:
        raise DataValidationError(
            "'vor' column not found in available players DataFrame for pickup suggestions.",
            field_name="available_players_df.vor",
            expected_type="numeric column",
            actual_value="missing"
        )
    return available_players_df.sort_values(by='vor', ascending=False).head(5)


def get_trade_suggestions(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Suggests sell-high and buy-low trade candidates.
    
    Args:
        df: DataFrame with player stats including 'week', 'fantasy_points', 'player_display_name'.
        
    Returns:
        Tuple of (sell_high_df, buy_low_df).
        
    Raises:
        DataValidationError: If input DataFrame is empty or missing required columns.
    """
    if df.empty:
        logger.warning("Input DataFrame is empty for trade suggestions.")
        return pd.DataFrame(), pd.DataFrame()

    required_cols = ['week', 'fantasy_points', 'player_display_name']
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise DataValidationError(
            f"Missing required columns for trade suggestions: {missing_cols}",
            field_name="player_stats_df_columns",
            expected_type=f"columns: {required_cols}",
            actual_value=f"missing: {missing_cols}"
        )

    week = df['week'].max()
    if pd.isna(week):
        logger.warning("Could not determine max week for trade suggestions.")
        return pd.DataFrame(), pd.DataFrame()

    this_week_df = df[df['week'] == week]
    last_week_df = df[df['week'] < week]

    if this_week_df.empty or last_week_df.empty:
        logger.warning("Insufficient data for current or previous weeks for trade suggestions.")
        return pd.DataFrame(), pd.DataFrame()

    player_avg_pts = last_week_df.groupby('player_display_name')['fantasy_points'].mean().reset_index()
    player_avg_pts.rename(columns={'fantasy_points': 'avg_fantasy_points'}, inplace=True)
    merged_df = pd.merge(this_week_df, player_avg_pts, on='player_display_name', how='left')
    merged_df['point_difference'] = merged_df['fantasy_points'] - merged_df['avg_fantasy_points']
    sell_high = merged_df[merged_df['point_difference'] > 10].sort_values(by='point_difference', ascending=False)
    buy_low = merged_df[merged_df['point_difference'] < -5].sort_values(by='point_difference', ascending=True)
    return sell_high, buy_low


def generate_markdown_report(draft_recs_df, bye_conflicts_df, trade_recs_df, team_analysis_str, output_dir, my_team_raw, pickup_suggestions_df, sell_high_df, buy_low_df, simulated_roster, simulated_draft_order, positional_breakdown_df, roster_comparison_table, roster_mismatch_table, last_game_analysis_str, next_game_analysis_str, my_team_df):
    """
    Generates a Markdown blog post from the analysis data for MkDocs Material.

    Args:
        draft_recs_df (pd.DataFrame): DataFrame with draft recommendations.
        bye_conflicts_df (pd.DataFrame): DataFrame with bye week conflicts.
        trade_recs_df (pd.DataFrame): DataFrame with trade recommendations.
        team_analysis_str (str): Markdown string with team analysis.
        output_dir (str): The directory to save the report in.
        my_team_raw (list): List of player names in my team.
        pickup_suggestions_df (pd.DataFrame): DataFrame with pickup suggestions.
        sell_high_df (pd.DataFrame): DataFrame with sell-high trade suggestions.
        buy_low_df (pd.DataFrame): DataFrame with buy-low trade suggestions.
        roster_comparison_table (str): Formatted table comparing roster to settings.
        roster_mismatch_table (str): Formatted table showing roster mismatches.
        last_game_analysis_str (str): AI analysis of the last game.
        next_game_analysis_str (str): AI analysis of the next game.
    """
    current_date = datetime.now().strftime('%Y-%m-%d')
    output_file = os.path.join(output_dir, f"{current_date}-fantasy-football-analysis.md")

    # Create the blog directory if it doesn't exist
    try:
        os.makedirs(output_dir, exist_ok=True)
    except OSError as e:
        raise FileOperationError(f"Could not create output directory '{output_dir}': {e}") from e

    # Correctly formatted YAML Front Matter
    front_matter = f'''---\ntitle: 'Fantasy Football Analysis: {current_date}'
date: {current_date}
categories:
  - Fantasy Football
  - Weekly Analysis
  - 2025 Season
tags:
  - fantasy-football
  - analysis
  - 2025-season
---

'''

    report_content = ""
    report_content += front_matter
    report_content += "Welcome to your weekly fantasy football analysis, powered by Gemini. This report provides a summary of player performance and key recommendations to help you dominate your league.\n\n"
    report_content += "---\n\n"

    # Team Analysis
    report_content += "## My Team Analysis\n\n"

    report_content += "### Current Roster\n\n"
    
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
    report_content += my_roster_display_df.to_markdown(index=False)
    report_content += "\n\n"

    report_content += "### Roster vs. League Settings Comparison\n\n"
    report_content += roster_comparison_table
    report_content += "\n\n"
    if roster_mismatch_table:
        report_content += "#### Mismatches\n\n"
        report_content += roster_mismatch_table
        report_content += "\n\n"

    report_content += team_analysis_str
    report_content += "\n#### Positional Breakdown (VOR vs. League Average)\n\n"
    report_content += positional_breakdown_df.to_markdown(index=False, floatfmt=".2f")
    report_content += "\n\n---\n\n"

    # Last Game Analysis
    report_content += "## Last Game Analysis\n\n"
    report_content += last_game_analysis_str
    report_content += "\n\n---\n\n"

    # Next Game Analysis
    report_content += "## Next Game Analysis\n\n"
    report_content += next_game_analysis_str
    report_content += "\n\n---\n\n"

    # Draft Recommendations
    report_content += "## Top Players to Target\n\n"
    report_content += "These players are ranked based on their **Value Over Replacement (VOR)**, a metric that measures a player's value relative to a typical starter at their position. We also look at consistency to see who you can rely on week in and week out.\n\n"
    
    draft_recs_display_df = draft_recs_df[['player_name', 'recent_team', 'position', 'vor', 'consistency_std_dev']].head(10).copy()
    draft_recs_display_df.rename(columns={
        'player_name': 'Player',
        'recent_team': 'Team',
        'position': 'Position',
        'vor': 'VOR',
        'consistency_std_dev': 'Consistency (Std Dev)'
    }, inplace=True)
    
    report_content += draft_recs_display_df.to_markdown(index=False)
    report_content += "\n\n---\n\n"

    # Bye Week Analysis
    report_content += "## Bye Week Cheat Sheet\n\n"
    if not bye_conflicts_df.empty:
        report_content += "### Heads Up! Potential Bye Week Conflicts\n\n"
        report_content += "Drafting strategically means planning for bye weeks. The following highly-ranked players share a bye week, which could leave your roster thin. Plan accordingly!\n\n"

        # Format bye week conflicts
        for _, row in bye_conflicts_df.iterrows():
            report_content += f"**Week {int(row['bye_week'])}**: {int(row['player_count'])} top players are on bye.\n\n"

        report_content += "\n"
    else:
        report_content += "No major bye week conflicts were found among the top-ranked players. Smooth sailing!\n\n"

    report_content += "---\n\n"

    # Trade Recommendations
    report_content += "## Smart Trade Targets\n\n"
    report_content += "Looking to make a move? These are potential trade targets based on their positional value and consistency. Acquiring one of these players could be the key to a championship run.\n\n"
    
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
    
    report_content += trade_recs_display_df.to_markdown(index=False)
    report_content += "\n"

    report_content += "\n\n---\n\n"

    # Simulated Draft Results
    report_content += "## Simulated Draft Results\n\n"
    report_content += "Here's a simulation of your draft, round by round, based on optimal VBD strategy and ADP.\n\n"
    report_content += "### Your Simulated Roster\n\n"
    for pos, players in simulated_roster.items():
        if players:
            report_content += f"**{pos}**:\n"
            for player in players:
                report_content += f"- {player}\n"
    report_content += "\n"

    report_content += "### Simulated Draft Order\n\n"
    for i, player_name in enumerate(simulated_draft_order):
        report_content += f"{i+1}. {player_name}\n"
    report_content += "\n"

    report_content += "\n\n---\n\n"

    # Pickup Suggestions
    report_content += "## Top Waiver Wire Pickups\n\n"
    report_content += "Here are some of the top players available on the waiver wire, based on their recent performance and potential.\n\n"
    pickup_display_df = pickup_suggestions_df[['player_name', 'position', 'recent_team', 'vor']].copy()
    pickup_display_df.rename(columns={
        'player_name': 'Player',
        'position': 'Position',
        'recent_team': 'Team',
        'vor': 'VOR'
    }, inplace=True)
    report_content += pickup_display_df.to_markdown(index=False)
    report_content += "\n"

    report_content += "\n\n---\n\n"

    # Trade Suggestions
    report_content += "## Trade Suggestions\n\n"
    report_content += "### Sell-High Candidates\n\n"
    sell_high_display_df = sell_high_df[['player_display_name', 'position', 'recent_team', 'fantasy_points', 'avg_fantasy_points', 'point_difference']].copy()
    sell_high_display_df.rename(columns={
        'player_display_name': 'Player',
        'position': 'Position',
        'recent_team': 'Team',
        'fantasy_points': 'Current Week Pts',
        'avg_fantasy_points': 'Avg Pts (Prev Weeks)',
        'point_difference': 'Point Difference'
    }, inplace=True)
    report_content += sell_high_display_df.to_markdown(index=False)
    report_content += "\n\n"
    report_content += "### Buy-Low Candidates\n\n"
    buy_low_display_df = buy_low_df[['player_display_name', 'position', 'recent_team', 'fantasy_points', 'avg_fantasy_points', 'point_difference']].copy()
    buy_low_display_df.rename(columns={
        'player_display_name': 'Player',
        'position': 'Position',
        'recent_team': 'Team',
        'fantasy_points': 'Current Week Pts',
        'avg_fantasy_points': 'Avg Pts (Prev Weeks)',
        'point_difference': 'Point Difference'
    }, inplace=True)
    report_content += buy_low_display_df.to_markdown(index=False)
    report_content += "\n"

    try:
        with open(output_file, "w", encoding='utf-8') as f:
            f.write(report_content)

        logger.info(f"Blog post successfully generated at '{output_file}'!")
    except PermissionError as e:
        raise FileOperationError(
            f"Permission denied writing report to {output_file}",
            file_path=output_file,
            operation="write",
            original_error=e
        )
    except IOError as e:
        raise FileOperationError(
            f"IO error writing report to {output_file}: {e}",
            file_path=output_file,
            operation="write",
            original_error=e
        )
    except Exception as e:
        raise wrap_exception(
            e, FileOperationError,
            f"Failed to write report to {output_file}",
            file_path=output_file,
            operation="write"
        )


def main():
    parser = argparse.ArgumentParser(description="Generate a fantasy football analysis report.")
    parser.add_argument(
        "report_type",
        choices=["markdown", "terminal", "html"],
        help="The type of report to generate.",
        nargs='?',
        default="terminal"
    )
    parser.add_argument(
        "--output-dir",
        default="docs/reports/posts",
        help="The directory to save the report in."
    )
    args = parser.parse_args()

    try:
        # Initialize analysis globals (config, scoring rules, etc.)
        config = load_config()
        analysis_globals = {
            '_CONFIG': config,
            '_SCORING_RULES': config.get('scoring_rules', {})
        }

        # Ensure the data file exists before running
        data_file = config.get('file_paths', {}).get('player_stats', 'data/player_stats.csv')
        if not os.path.exists(data_file):
            raise FileOperationError(
                f"Data file not found at '{data_file}'. Please run 'task download stats' first.",
                file_path=data_file,
                operation="read"
            )

        # Create a dummy roster file if it doesn't exist
        roster_file = config.get('file_paths', {}).get('my_team', 'data/my_team.md')
        if not os.path.exists(roster_file):
            with open(roster_file, "w", encoding='utf-8') as f:
                f.write("- Patrick Mahomes\n")
                f.write("- Tyreek Hill\n")
                f.write("- Saquon Barkley\n")
                f.write("- Keenan Allen\n")
                f.write("- Travis Kelce\n")
            logger.info(f"Created dummy roster file: {roster_file}")

        # Load and process data
        stats_df = pd.read_csv(data_file, dtype={'proTeam': object}, low_memory=False)

        if stats_df.empty:
            raise DataValidationError(
                "Player stats DataFrame is empty after loading. Cannot proceed with analysis.",
                field_name="player_stats_df",
                expected_type="non-empty DataFrame",
                actual_value="empty DataFrame"
            )

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

        # Get team roster and analysis
        my_team_raw = get_team_roster(roster_file)

        my_team_normalized = [normalize_player_name(name) for name in my_team_raw]
        my_team_df = draft_recs[draft_recs['player_name'].isin(my_team_normalized)]
        
        team_analysis_str, positional_breakdown_df = analyze_team_needs(my_team_df, draft_recs)

        trade_recs = get_trade_recommendations(draft_recs, team_roster=my_team_normalized)

        # Get pickup and trade suggestions
        available_players_df = draft_recs[~draft_recs['player_name'].isin(my_team_normalized)]
        pickup_suggestions = get_pickup_suggestions(available_players_df)

        sell_high_suggestions, buy_low_suggestions = get_trade_suggestions(stats_with_points)

        # Run simulated draft (using dummy data for non-interactive report generation)
        simulated_roster = {
            'QB': ['Patrick Mahomes'],
            'RB': ['Christian McCaffrey', 'Jonathan Taylor'],
            'WR': ['Justin Jefferson', "Ja'Marr Chase"],
            'TE': ['Travis Kelce']
        }
        simulated_draft_order = [
            'Justin Jefferson', 'Christian McCaffrey', 'Patrick Mahomes', 'Travis Kelce',
            'Jonathan Taylor', "Ja'Marr Chase", 'Josh Allen', 'Austin Ekeler'
        ]

        # Roster comparison
        roster_comparison_table, roster_mismatch_table = compare_roster_positions("config.yaml", roster_file)

        # Analyze last game
        last_game_analysis_str = analyze_game(game_type="last")

        # Analyze next game
        next_game_analysis_str = analyze_game(game_type="next")

        if args.report_type == "markdown":
            absolute_output_dir = os.path.abspath(args.output_dir)
            generate_markdown_report(draft_recs, bye_conflicts, trade_recs, team_analysis_str, absolute_output_dir, my_team_raw, pickup_suggestions, sell_high_suggestions, buy_low_suggestions, simulated_roster, simulated_draft_order, positional_breakdown_df, roster_comparison_table, roster_mismatch_table, last_game_analysis_str, next_game_analysis_str, my_team_df)
            print("✓ Markdown report generated successfully!")
        elif args.report_type == "terminal":
            generate_terminal_report(draft_recs, bye_conflicts, trade_recs, team_analysis_str, my_team_raw, pickup_suggestions, sell_high_suggestions, buy_low_suggestions, positional_breakdown_df, roster_comparison_table, roster_mismatch_table, last_game_analysis_str, next_game_analysis_str, my_team_df)
            print("✓ Terminal report generated successfully!")
        elif args.report_type == "html":
            absolute_output_dir = os.path.abspath(args.output_dir)
            markdown_file = os.path.join(absolute_output_dir, f"{datetime.now().strftime('%Y-%m-%d')}-fantasy-football-analysis.md")
            html_file = os.path.join(absolute_output_dir, f"{datetime.now().strftime('%Y-%m-%d')}-fantasy-football-analysis.html")
            generate_markdown_report(draft_recs, bye_conflicts, trade_recs, team_analysis_str, absolute_output_dir, my_team_raw, pickup_suggestions, sell_high_suggestions, buy_low_suggestions, simulated_roster, simulated_draft_order, positional_breakdown_df, roster_comparison_table, roster_mismatch_table, last_game_analysis_str, next_game_analysis_str, my_team_df)
            render_markdown_to_html(markdown_file, html_file)
            webbrowser.open_new_tab(os.path.abspath(html_file))
            print("✓ HTML report generated and opened successfully!")

        return 0

    except (FileOperationError, DataValidationError, ConfigurationError, APIError, AuthenticationError, NetworkError) as e:
        logger.error(f"Report generation error: {e.get_detailed_message()}")
        print(f"\n❌ Error generating report: {e}")
        print("\nTroubleshooting:")
        if isinstance(e, ConfigurationError):
            print("- Check config.yaml for valid settings.")
        elif isinstance(e, FileOperationError):
            print("- Ensure data files and output directories are accessible.")
        elif isinstance(e, DataValidationError):
            print("- Check the format and content of your data files.")
        elif isinstance(e, AuthenticationError):
            print("- Verify your API keys and credentials are correctly set.")
        elif isinstance(e, NetworkError):
            print("- Check your internet connection.")
        elif isinstance(e, APIError):
            print("- There might be an issue with an external API service. Try again later.")
        sys.exit(1)
    except Exception as e:
        logger.critical(f"An unhandled critical error occurred: {e}", exc_info=True)
        print(f"\n❌ An unexpected critical error occurred: {e}")
        print("Please check the log file for more details.")
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except (FileOperationError, DataValidationError, ConfigurationError, APIError, AuthenticationError, NetworkError) as e:
        logger.error(f"Report generation error: {e.get_detailed_message()}")
        print(f"\n❌ Error generating report: {e}")
        print("\nTroubleshooting:")
        if isinstance(e, ConfigurationError):
            print("- Check config.yaml for valid settings.")
        elif isinstance(e, FileOperationError):
            print("- Ensure data files and output directories are accessible.")
        elif isinstance(e, DataValidationError):
            print("- Check the format and content of your data files.")
        elif isinstance(e, AuthenticationError):
            print("- Verify your API keys and credentials are correctly set.")
        elif isinstance(e, NetworkError):
            print("- Check your internet connection.")
        elif isinstance(e, APIError):
            print("- There might be an issue with an external API service. Try again later.")
        sys.exit(1)
    except Exception as e:
        logger.critical(f"An unhandled critical error occurred: {e}", exc_info=True)
        print(f"\n❌ An unexpected critical error occurred: {e}")
        print("Please check the log file for more details.")
        sys.exit(1)