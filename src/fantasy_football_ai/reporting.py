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

import argparse
import os
import sys
from datetime import datetime

import pandas as pd
from tabulate import tabulate

# Add src to path for imports
from fantasy_football_ai.errors import (
    APIError,
    AuthenticationError,
    ConfigurationError,
    DataValidationError,
    FileOperationError,
    NetworkError,
)
from fantasy_football_ai.utils.logging import get_logger, setup_logging

# Set up logging
setup_logging(level='INFO', format_type='console', log_file='logs/reporting.log')
logger = get_logger(__name__)

# Assume the analysis.py script is in the same directory and can be imported
from fantasy_football_ai.analysis import (
    analyze_team_needs,
    calculate_fantasy_points,
    check_bye_week_conflicts,
    get_advanced_draft_recommendations,
    get_trade_recommendations,
)
from fantasy_football_ai.analyze_game import analyze_game
from fantasy_football_ai.compare_roster_positions import compare_roster_positions
from fantasy_football_ai.data_manager import get_team_roster
from fantasy_football_ai.data_utils import load_config
from fantasy_football_ai.free_agent_analyzer import analyze_free_agents


def get_team_name(roster_file: str) -> str:
    """Extract team name from roster file markdown header or return default."""
    if os.path.exists(roster_file):
        try:
            with open(roster_file, "r", encoding="utf-8") as f:
                for line in f:
                    stripped = line.strip()
                    if stripped.startswith("# My Team:"):
                        name = stripped.replace("# My Team:", "").strip()
                        if name:
                            return name
        except (OSError, UnicodeDecodeError) as e:
            logger.debug(f"Could not read team name from {roster_file}: {e}")
    return "My Team"


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


def generate_markdown_report(draft_recs_df, bye_conflicts_df, trade_recs_df, team_analysis_str, my_team_raw, sell_high_df, buy_low_df, simulated_roster, simulated_draft_order, positional_breakdown_df, roster_comparison_table, roster_mismatch_table, last_game_analysis_str, next_game_analysis_str, my_team_df, waiver_gems_df, team_name: str = "My Team"):
    """
    Generates a Markdown blog post from the analysis data.

    Args:
        draft_recs_df (pd.DataFrame): DataFrame with draft recommendations.
        bye_conflicts_df (pd.DataFrame): DataFrame with bye week conflicts.
        trade_recs_df (pd.DataFrame): DataFrame with trade recommendations.
        team_analysis_str (str): Markdown string with team analysis.
        my_team_raw (list): List of player names in my team.
        pickup_suggestions_df (pd.DataFrame): DataFrame with pickup suggestions.
        sell_high_df (pd.DataFrame): DataFrame with sell-high trade suggestions.
        buy_low_df (pd.DataFrame): DataFrame with buy-low trade suggestions.
        roster_comparison_table (str): Formatted table comparing roster to settings.
        roster_mismatch_table (str): Formatted table showing roster mismatches.
        last_game_analysis_str (str): AI analysis of the last game.
        next_game_analysis_str (str): AI analysis of the next game.
        team_name (str): Name of the current team.
    """
    current_date = datetime.now().strftime('%Y-%m-%d')  # noqa: DTZ005

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
    report_content += f"## My Team Analysis ({team_name})\n\n"

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
    
    report_content += trade_recs_display_df.head(5).to_markdown(index=False)
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

    # Waiver Wire Gems
    report_content += "## Waiver Wire Gems (High Usage, Underperforming)\n\n"
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
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Error formatting percentages: {e}")
        
        # Select and order columns for display
        display_cols = [
            'Player', 'Position', 'Team', 'Recent PPR Avg', 'Season PPR Avg',
            'Recent Targets Avg', 'Recent Carries Avg', 'Target Share', 'Air Yards Share'
        ]
        # Filter out columns that might not exist in the DataFrame
        display_cols = [col for col in display_cols if col in display_gems_df.columns]

        report_content += display_gems_df[display_cols].head(5).to_markdown(index=False)
        report_content += "\n\n"
    else:
        report_content += "No waiver wire gems identified at this time.\n\n"

    report_content += "---\n\n"

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
    report_content += sell_high_display_df.head(5).to_markdown(index=False)
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
    report_content += buy_low_display_df.head(5).to_markdown(index=False)
    print(report_content)
    logger.info("Blog post successfully generated and printed to console!")
    return report_content
def generate_terminal_report(draft_recs_df, bye_conflicts_df, trade_recs_df, team_analysis_str, my_team_raw, sell_high_df, buy_low_df, positional_breakdown_df, roster_comparison_table, roster_mismatch_table, last_game_analysis_str, next_game_analysis_str, my_team_df, waiver_gems_df, team_name: str = "My Team"):
    """
    Generates a terminal report from the analysis data.
    """
    print(f"--- My Team Analysis ({team_name}) ---")
    print("### Current Roster")
    my_roster_display_df = my_team_df.drop_duplicates(subset=['player_name'])[['player_name', 'recent_team', 'position', 'vor', 'consistency_std_dev']].copy()
    my_roster_display_df.rename(columns={
        'player_name': 'Player',
        'recent_team': 'Team',
        'position': 'Position',
        'vor': 'VOR',
        'consistency_std_dev': 'Consistency (Std Dev)'
    }, inplace=True)
    print(tabulate(my_roster_display_df, headers='keys', tablefmt='fancy_grid', showindex=False))
    
    print("\n### Roster vs. League Settings Comparison")
    print(roster_comparison_table)
    if roster_mismatch_table:
        print("\n#### Mismatches")
        print(roster_mismatch_table)

    print(team_analysis_str)
    print("\n#### Positional Breakdown (VOR vs. League Average)")
    print(tabulate(positional_breakdown_df, headers='keys', tablefmt='fancy_grid', showindex=False, floatfmt=".2f"))

    print("\n--- Last Game Analysis ---")
    print(last_game_analysis_str)

    print("\n--- Next Game Analysis ---")
    print(next_game_analysis_str)

    print("\n--- Top Players to Target ---")
    draft_recs_display_df = draft_recs_df[['player_name', 'recent_team', 'position', 'vor', 'consistency_std_dev']].head(10).copy()
    draft_recs_display_df.rename(columns={
        'player_name': 'Player',
        'recent_team': 'Team',
        'position': 'Position',
        'vor': 'VOR',
        'consistency_std_dev': 'Consistency (Std Dev)'
    }, inplace=True)
    print(tabulate(draft_recs_display_df, headers='keys', tablefmt='fancy_grid', showindex=False))

    print("\n--- Bye Week Cheat Sheet ---")
    if not bye_conflicts_df.empty:
        print("### Heads Up! Potential Bye Week Conflicts")
        for _, row in bye_conflicts_df.iterrows():
            print(f"**Week {int(row['bye_week'])}**: {int(row['player_count'])} top players are on bye.")
    else:
        print("No major bye week conflicts were found among the top-ranked players. Smooth sailing!")

    print("\n--- Smart Trade Targets ---")
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
    print(tabulate(trade_recs_display_df.head(5), headers='keys', tablefmt='fancy_grid', showindex=False))

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
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Error formatting percentages: {e}")
        
        # Select and order columns for display
        display_cols = [
            'Player', 'Position', 'Team', 'Recent PPR Avg', 'Season PPR Avg',
            'Recent Targets Avg', 'Recent Carries Avg', 'Target Share', 'Air Yards Share'
        ]
        # Filter out columns that might not exist in the DataFrame
        display_cols = [col for col in display_cols if col in display_gems_df.columns]

        print(tabulate(display_gems_df[display_cols].head(5), headers='keys', tablefmt='fancy_grid', showindex=False))
    else:
        print("No waiver wire gems identified at this time.")

    print("\n--- Trade Suggestions ---")
    print("### Sell-High Candidates")
    sell_high_display_df = sell_high_df[['player_display_name', 'position', 'recent_team', 'fantasy_points', 'avg_fantasy_points', 'point_difference']].copy()
    sell_high_display_df.rename(columns={
        'player_display_name': 'Player',
        'position': 'Position',
        'recent_team': 'Team',
        'fantasy_points': 'Current Week Pts',
        'avg_fantasy_points': 'Avg Pts (Prev Weeks)',
        'point_difference': 'Point Difference'
    }, inplace=True)
    print(tabulate(sell_high_display_df.head(5), headers='keys', tablefmt='fancy_grid', showindex=False))

    print("\n### Buy-Low Candidates")
    buy_low_display_df = buy_low_df[['player_display_name', 'position', 'recent_team', 'fantasy_points', 'avg_fantasy_points', 'point_difference']].copy()
    buy_low_display_df.rename(columns={
        'player_display_name': 'Player',
        'position': 'Position',
        'recent_team': 'Team',
        'fantasy_points': 'Current Week Pts',
        'avg_fantasy_points': 'Avg Pts (Prev Weeks)',
        'point_difference': 'Point Difference'
    }, inplace=True)
    print(tabulate(buy_low_display_df.head(5), headers='keys', tablefmt='fancy_grid', showindex=False))


def main():
    parser = argparse.ArgumentParser(description="Generate a fantasy football analysis report.")
    parser.add_argument(
        "report_type",
        choices=["markdown", "terminal"],
        help="The type of report to generate.",
        nargs='?',
        default="terminal"
    )
    args = parser.parse_args()

    try:
        # Initialize analysis globals (config, scoring rules, etc.)
        config = load_config()
        analysis_globals = {  # noqa: F841
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

        stats_with_points = calculate_fantasy_points(stats_df, config.get('scoring_rules', {}))

        # Add a placeholder bye_week column for demonstration purposes
        if 'week' in stats_with_points.columns:
            stats_with_points['bye_week'] = stats_with_points['week'].apply(lambda x: (x % 14) + 4)
        else:
            stats_with_points['bye_week'] = 0

        # Get analysis data
        draft_recs = get_advanced_draft_recommendations(stats_with_points, config)

        # Merge recent_team into draft_recs
        draft_recs = pd.merge(draft_recs, stats_with_points[['player_name', 'recent_team']].drop_duplicates(), on='player_name', how='left')

        bye_conflicts = check_bye_week_conflicts(stats_with_points, config)

        # Get team roster and analysis
        my_team_raw = get_team_roster(roster_file)

        my_team_normalized = [normalize_player_name(name) for name in my_team_raw]
        my_team_df = draft_recs[draft_recs['player_name'].isin(my_team_normalized)]
        
        team_analysis_str, positional_breakdown_df = analyze_team_needs(my_team_df, draft_recs, config)

        trade_recs = get_trade_recommendations(draft_recs, team_roster=my_team_normalized, config=config)

        # Get pickup and trade suggestions
        waiver_gems_df = analyze_free_agents()

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

        # Extract team name
        team_name = get_team_name(roster_file)

        # Roster comparison
        roster_tablefmt = "github" if args.report_type == "markdown" else "fancy_grid"
        roster_comparison_table, roster_mismatch_table = compare_roster_positions(
            "config.yaml", roster_file, tablefmt=roster_tablefmt
        )

        # Analyze last game
        last_game_analysis_str = analyze_game(game_type="last")

        # Analyze next game
        next_game_analysis_str = analyze_game(game_type="next")

        if args.report_type == "markdown":
            generate_markdown_report(
                draft_recs, bye_conflicts, trade_recs, team_analysis_str,
                my_team_raw, sell_high_suggestions, buy_low_suggestions,
                simulated_roster, simulated_draft_order, positional_breakdown_df,
                roster_comparison_table, roster_mismatch_table,
                last_game_analysis_str, next_game_analysis_str, my_team_df,
                waiver_gems_df, team_name=team_name
            )
            print("✓ Markdown report generated successfully!")
        elif args.report_type == "terminal":
            generate_terminal_report(
                draft_recs, bye_conflicts, trade_recs, team_analysis_str,
                my_team_raw, sell_high_suggestions, buy_low_suggestions,
                positional_breakdown_df, roster_comparison_table,
                roster_mismatch_table, last_game_analysis_str,
                next_game_analysis_str, my_team_df, waiver_gems_df,
                team_name=team_name
            )
            print("✓ Terminal report generated successfully!")


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