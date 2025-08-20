#!/usr/bin/env python3

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

# Helper function to normalize player names, e.g., 'Patrick Mahomes' to 'P.Mahomes'
def normalize_player_name(name):
    parts = name.split()
    if len(parts) >= 2:
        return f"{parts[0][0]}.{parts[-1]}"
    return name

def generate_markdown_report(draft_recs_df, bye_conflicts_df, trade_recs_df, team_analysis_str, output_dir):
    """
    Generates a Markdown blog post from the analysis data for MkDocs Material.

    Args:
        draft_recs_df (pd.DataFrame): DataFrame with draft recommendations.
        bye_conflicts_df (pd.DataFrame): DataFrame with bye week conflicts.
        trade_recs_df (pd.DataFrame): DataFrame with trade recommendations.
        team_analysis_str (str): Markdown string with team analysis.
        output_dir (str): The directory to save the report in.
    """
    current_date = datetime.now().strftime('%Y-%m-%d')
    output_file = os.path.join(output_dir, f"{current_date}-fantasy-football-analysis.md")

    # Create the blog directory if it doesn't exist
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Correctly formatted YAML Front Matter
    front_matter = f"""---
title: 'Fantasy Football Analysis: {current_date}'
date: {current_date}
categories:
  - Fantasy Football
  - Weekly Analysis
---

"""

    with open(output_file, "w") as f:
        f.write(front_matter)
        f.write("Welcome to your weekly fantasy football analysis, powered by Gemini. This report provides a summary of player performance and key recommendations to help you dominate your league.\n\n")
        f.write("---\n\n")

        # Team Analysis
        f.write("## My Team Analysis\n\n")
        f.write(team_analysis_str)
        f.write("\n\n---\n\n")

        # Draft Recommendations
        f.write("## Top Players to Target\n\n")
        f.write("These players are ranked based on their **Value Over Replacement (VOR)**, a metric that measures a player's value relative to a typical starter at their position. We also look at consistency to see who you can rely on week in and week out.\n\n")
        f.write(draft_recs_df[['player_name', 'recent_team', 'position', 'vor', 'consistency_std_dev']].to_markdown(index=False))
        f.write("\n\n---\n\n")

        # Bye Week Analysis
        f.write("## Bye Week Cheat Sheet\n\n")
        if not bye_conflicts_df.empty:
            f.write("### Heads Up! Potential Bye Week Conflicts\n\n")
            f.write("Drafting strategically means planning for bye weeks. The following highly-ranked players share a bye week, which could leave your roster thin. Plan accordingly!\n\n")

            # Format bye week conflicts
            for _, row in bye_conflicts_df.iterrows():
                f.write(f"**Week {int(row['bye_week'])}**: {int(row['player_count'])} top players are on bye.\n")

            f.write("\n")
        else:
            f.write("No major bye week conflicts were found among the top-ranked players. Smooth sailing!\n\n")

        f.write("---\n\n")

        # Trade Recommendations
        f.write("## Smart Trade Targets\n\n")
        f.write("Looking to make a move? These are potential trade targets based on their positional value and consistency. Acquiring one of these players could be the key to a championship run.\n\n")
        f.write(trade_recs_df.to_markdown(index=False))
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
    stats_df = pd.read_csv(data_file)
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
    team_analysis = analyze_team_needs(my_team_df, draft_recs)

    trade_recs = get_trade_recommendations(draft_recs, team_roster=my_team_normalized)

    # Generate the report
    generate_markdown_report(draft_recs, bye_conflicts, trade_recs, team_analysis, args.output_dir)
