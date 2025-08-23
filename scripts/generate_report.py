#!/usr/bin/env python3
################################################################################
#
# Script Name: generate_report.py
# ----------------
# Generates a comprehensive fantasy football analysis report in Markdown format.
#
# @author Nicholas Wilde, 0xb299a622
# @date 2025-08-20
# @version 0.2.0
#
################################################################################

import pandas as pd
import os
import sys
from datetime import datetime
import argparse

# Assume the analysis.py script is in the same directory and can be imported
from analysis import (
    get_advanced_draft_recommendations,
    check_bye_week_conflicts,
    get_trade_recommendations,
    calculate_fantasy_points,
    get_team_roster,
    analyze_team_needs
)
import draft_strategizer # Import the draft_strategizer script
from compare_roster_positions import compare_roster_positions
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

def generate_markdown_report(draft_recs_df, bye_conflicts_df, trade_recs_df, team_analysis_str, output_dir, my_team_raw, pickup_suggestions_df, sell_high_df, buy_low_df, simulated_roster, simulated_draft_order, positional_breakdown_df, roster_comparison_table, roster_mismatch_table, last_game_analysis_str, next_game_analysis_str):
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
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Correctly formatted YAML Front Matter
    front_matter = f'''---
title: 'Fantasy Football Analysis: {current_date}'
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

    with open(output_file, "w") as f:
        f.write(front_matter)
        f.write("Welcome to your weekly fantasy football analysis, powered by Gemini. This report provides a summary of player performance and key recommendations to help you dominate your league.\n\n")
        f.write("---\n\n")

        # Team Analysis
        f.write("## My Team Analysis\n\n")

        f.write("### Current Roster\n\n")
        
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
        f.write(my_roster_display_df.to_markdown(index=False))
        f.write("\n\n")

        f.write("### Roster vs. League Settings Comparison\n\n")
        f.write(roster_comparison_table)
        f.write("\n\n")
        if roster_mismatch_table:
            f.write("#### Mismatches\n\n")
            f.write(roster_mismatch_table)
            f.write("\n\n")

        f.write(team_analysis_str)
        f.write("\n#### Positional Breakdown (VOR vs. League Average)\n\n")
        f.write(positional_breakdown_df.to_markdown(index=False, floatfmt=".2f"))
        f.write("\n\n---\n\n")

        # Last Game Analysis
        f.write("## Last Game Analysis\n\n")
        f.write(last_game_analysis_str)
        f.write("\n\n---\n\n")

        # Next Game Analysis
        f.write("## Next Game Analysis\n\n")
        f.write(next_game_analysis_str)
        f.write("\n\n---\n\n")


        # Draft Recommendations
        f.write("## Top Players to Target\n\n")
        f.write("These players are ranked based on their **Value Over Replacement (VOR)**, a metric that measures a player's value relative to a typical starter at their position. We also look at consistency to see who you can rely on week in and week out.\n\n")
        
        draft_recs_display_df = draft_recs_df[['player_name', 'recent_team', 'position', 'vor', 'consistency_std_dev']].head(10).copy()
        draft_recs_display_df.rename(columns={
            'player_name': 'Player',
            'recent_team': 'Team',
            'position': 'Position',
            'vor': 'VOR',
            'consistency_std_dev': 'Consistency (Std Dev)'
        }, inplace=True)
        
        f.write(draft_recs_display_df.to_markdown(index=False))
        f.write("\n\n---\n\n")

        # Bye Week Analysis
        f.write("## Bye Week Cheat Sheet\n\n")
        if not bye_conflicts_df.empty:
            f.write("### Heads Up! Potential Bye Week Conflicts\n\n")
            f.write("Drafting strategically means planning for bye weeks. The following highly-ranked players share a bye week, which could leave your roster thin. Plan accordingly!\n\n")

            # Format bye week conflicts
            for _, row in bye_conflicts_df.iterrows():
                f.write(f"**Week {int(row['bye_week'])}**: {int(row['player_count'])} top players are on bye.\n\n")

            f.write("\n")
        else:
            f.write("No major bye week conflicts were found among the top-ranked players. Smooth sailing!\n\n")

        f.write("---\n\n")

        # Trade Recommendations
        f.write("## Smart Trade Targets\n\n")
        f.write("Looking to make a move? These are potential trade targets based on their positional value and consistency. Acquiring one of these players could be the key to a championship run.\n\n")
        
        # Select and rename columns for a more readable trade targets table
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
        
        f.write(trade_recs_display_df.to_markdown(index=False))
        f.write("\n")

        f.write("\n\n---\n\n")

        # Simulated Draft Results
        f.write("## Simulated Draft Results\n\n")
        f.write("Here's a simulation of your draft, round by round, based on optimal VBD strategy and ADP.\n\n")
        f.write("### Your Simulated Roster\n\n")
        for pos, players in simulated_roster.items():
            if players:
                f.write(f"**{pos}**:\n")
                for player in players:
                    f.write(f"- {player}\n")
        f.write("\n")

        f.write("### Simulated Draft Order\n\n")
        for i, player_name in enumerate(simulated_draft_order):
            f.write(f"{i+1}. {player_name}\n")
        f.write("\n")

        f.write("\n\n---\n\n")

        # Pickup Suggestions
        f.write("## Top Waiver Wire Pickups\n\n")
        f.write("Here are some of the top players available on the waiver wire, based on their recent performance and potential.\n\n")
        pickup_display_df = pickup_suggestions_df[['player_name', 'position', 'recent_team', 'vor']].copy()
        pickup_display_df.rename(columns={
            'player_name': 'Player',
            'position': 'Position',
            'recent_team': 'Team',
            'vor': 'VOR'
        }, inplace=True)
        f.write(pickup_display_df.to_markdown(index=False))
        f.write("\n")

        f.write("\n\n---\n\n")

        # Trade Suggestions
        f.write("## Trade Suggestions\n\n")
        f.write("### Sell-High Candidates\n\n")
        sell_high_display_df = sell_high_df[['player_display_name', 'position', 'recent_team', 'fantasy_points', 'avg_fantasy_points', 'point_difference']].copy()
        sell_high_display_df.rename(columns={
            'player_display_name': 'Player',
            'position': 'Position',
            'recent_team': 'Team',
            'fantasy_points': 'Current Week Pts',
            'avg_fantasy_points': 'Avg Pts (Prev Weeks)',
            'point_difference': 'Point Difference'
        }, inplace=True)
        f.write(sell_high_display_df.to_markdown(index=False))
        f.write("\n\n")
        f.write("### Buy-Low Candidates\n\n")
        buy_low_display_df = buy_low_df[['player_display_name', 'position', 'recent_team', 'fantasy_points', 'avg_fantasy_points', 'point_difference']].copy()
        buy_low_display_df.rename(columns={
            'player_display_name': 'Player',
            'position': 'Position',
            'recent_team': 'Team',
            'fantasy_points': 'Current Week Pts',
            'avg_fantasy_points': 'Avg Pts (Prev Weeks)',
            'point_difference': 'Point Difference'
        }, inplace=True)
        f.write(buy_low_display_df.to_markdown(index=False))
        f.write("\n")

    print(f"Blog post successfully generated at '{output_file}'!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate a fantasy football analysis report.")
    parser.add_argument(
        "--output-dir",
        default="docs/reports/posts",
        help="The directory to save the report in."
    )
    args = parser.parse_args()

    # Ensure the data file exists before running
    data_file = "data/player_stats.csv"
    if not os.path.exists(data_file):
        print(f"Error: Data file not found at '{data_file}'. Please run 'download_stats.py' first.", file=sys.stderr)
        sys.exit(1)

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
    stats_df = pd.read_csv(data_file, dtype={'proTeam': object})
    stats_with_points = calculate_fantasy_points(stats_df)

    # Add a placeholder bye_week column for demonstration purposes
    if 'week' in stats_with_points.columns:
        stats_with_points['bye_week'] = stats_with_points['week'].apply(lambda x: (x % 14) + 4)
    else:
        stats_with_points['bye_week'] = 0

    # Get analysis data
    draft_recs = get_advanced_draft_recommendations(stats_with_points)
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
    sell_high_suggestions, buy_low_suggestions = get_trade_suggestions(draft_recs)

    # Run simulated draft
    simulated_roster, simulated_draft_order = draft_strategizer.main()

    # Roster comparison
    roster_comparison_table, roster_mismatch_table = compare_roster_positions("config.yaml", roster_file)

    # Analyze last game
    last_game_analysis_str = analyze_last_game()

    # Analyze next game
    next_game_analysis_str = analyze_next_game()

    # Generate the report
    generate_markdown_report(draft_recs, bye_conflicts, trade_recs, team_analysis_str, args.output_dir, my_team_raw, pickup_suggestions, sell_high_suggestions, buy_low_suggestions, simulated_roster, simulated_draft_order, positional_breakdown_df, roster_comparison_table, roster_mismatch_table, last_game_analysis_str, next_game_analysis_str)
