#!/usr/bin/env python3

import pandas as pd
import os
import sys

# Assume the analysis.py script is in the same directory and can be imported
# This is for modularity; in a real-world scenario, you might want to refactor
# analysis.py to be a module that can be imported
from analysis import get_advanced_draft_recommendations, check_bye_week_conflicts, get_trade_recommendations, calculate_fantasy_points

def generate_markdown_report(draft_recs_df, bye_conflicts_df, trade_recs_df, output_file="reports/report.md"):
    """
    Generates a Markdown report from the analysis data.

    Args:
        draft_recs_df (pd.DataFrame): DataFrame with draft recommendations.
        bye_conflicts_df (pd.DataFrame): DataFrame with bye week conflicts.
        trade_recs_df (pd.DataFrame): DataFrame with trade recommendations.
        output_file (str): The path and filename for the output Markdown file.
    """
    # Create the reports directory if it doesn't exist
    output_dir = os.path.dirname(output_file)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)

    with open(output_file, "w") as f:
        f.write("# Fantasy Football Analysis Report\n\n")
        f.write("This report provides a summary of player performance and recommendations for your fantasy football league, generated with the help of Gemini.\n\n")
        f.write("---\n\n")

        # Draft Recommendations
        f.write("## Draft Recommendations\n\n")
        f.write("These players are ranked based on their **Value Over Replacement (VOR)**, a metric that measures a player's value relative to a typical starter at their position. It also includes their consistency, measured by the standard deviation of their weekly points.\n\n")
        f.write(draft_recs_df[['player_name', 'recent_team', 'position', 'vor', 'consistency_std_dev']].to_markdown(index=False))
        f.write("\n\n---\n\n")
        
        # Bye Week Analysis
        f.write("## Bye Week Analysis\n\n")
        if not bye_conflicts_df.empty:
            f.write("### Potential Bye Week Conflicts\n\n")
            f.write("The following highly-ranked players share a bye week. Drafting too many of these players could leave you with a weak roster on that specific week.\n\n")
            
            # Format bye week conflicts
            for _, row in bye_conflicts_df.iterrows():
                f.write(f"**Week {int(row['bye_week'])}**: {int(row['player_count'])} highly-ranked players are on bye.\n")
            
            f.write("\n")
        else:
            f.write("No major bye week conflicts were found among the top-ranked players.\n\n")
            
        f.write("---\n\n")

        # Trade Recommendations
        f.write("## Trade Recommendations\n\n")
        f.write("These are potential trade targets based on their positional value and consistency. Consider acquiring these players to stabilize or upgrade your roster.\n\n")
        f.write(trade_recs_df.to_markdown(index=False))
        f.write("\n")
    
    print(f"Report successfully generated at '{output_file}'!")

if __name__ == "__main__":
    # Ensure the data file exists before running
    data_file = "data/player_stats.csv"
    if not os.path.exists(data_file):
        print(f"Error: Data file not found at '{data_file}'. Please run 'download_stats.py' first.", file=sys.stderr)
        sys.exit(1)
        
    # Load and process data
    stats_df = pd.read_csv(data_file)
    stats_with_points = calculate_fantasy_points(stats_df)
    
    # Get analysis data
    draft_recs = get_advanced_draft_recommendations(stats_with_points)
    bye_conflicts = check_bye_week_conflicts(stats_with_points)
    
    # Using a placeholder team for trade recommendations
    my_team_roster = ['Patrick Mahomes', 'Tyreek Hill', 'Saquon Barkley']
    trade_recs = get_trade_recommendations(draft_recs, team_roster=my_team_roster)
    
    # Generate the report
    generate_markdown_report(draft_recs, bye_conflicts, trade_recs)
