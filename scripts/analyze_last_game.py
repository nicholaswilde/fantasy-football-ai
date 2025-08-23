#!/usr/bin/env python3
################################################################################
#
# Script Name: analyze_last_game.py
# ----------------
# Analyzes the user's last fantasy football game, evaluates performance,
# and suggests improvements.
#
# @author Nicholas Wilde, 0xb299a622
# @date 23 August 2025
# @version 0.1.0
#
################################################################################

import os
import pandas as pd
import yaml
from dotenv import load_dotenv
from analysis import ask_llm, configure_llm_api, LLM_MODEL, LLM_PROVIDER

# Load environment variables
load_dotenv()

# Configuration file path
CONFIG_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', 'config.yaml'
)
PLAYER_STATS_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'player_stats.csv'
)
MY_TEAM_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'my_team.md'
)

def load_config():
    """Loads the configuration from config.yaml."""
    with open(CONFIG_FILE, 'r') as f:
        return yaml.safe_load(f)

def get_my_team_roster(file_path):
    """Reads the my_team.md file and extracts player names."""
    with open(file_path, 'r') as f:
        content = f.read()
    players = []
    # Regex to find player names in markdown list format: - Player Name (Team Pos)
    # This regex is more robust to handle various formats of player names and team/pos
    import re
    player_pattern = re.compile(r"^- \s*([A-Za-z0-9'.\s-]+)")
    for line in content.split('\n'):
        match = player_pattern.match(line)
        if match:
            players.append(match.group(1).strip())
    return players

def normalize_player_name(name):
    """Normalizes player names to match the format in player_stats.csv (e.g., 'Patrick Mahomes' to 'P.Mahomes')."""
    parts = name.split(' ')
    if len(parts) > 1:
        return f"{parts[0][0]}.{' '.join(parts[1:])}"
    return name

def analyze_last_game():
    """Analyzes the user's last game performance and suggests improvements."""
    config = load_config()
    league_year = config.get('league_settings', {}).get('year')
    if not league_year:
        print("Error: 'year' not found in config.yaml under 'league_settings'.")
        return

    try:
        player_stats_df = pd.read_csv(PLAYER_STATS_FILE, low_memory=False)
    except FileNotFoundError:
        print(f"Error: {PLAYER_STATS_FILE} not found. Please run 'task download' to get player stats.")
        return

    my_team_players_raw = get_my_team_roster(MY_TEAM_FILE)
    if not my_team_players_raw:
        print(f"Error: No players found in {MY_TEAM_FILE}. Please ensure your team roster is correctly set up.")
        return

    # Normalize player names from my_team.md to match player_stats.csv
    my_team_players_normalized = [normalize_player_name(p) for p in my_team_players_raw]

    # Filter for the current league year
    current_year_stats = player_stats_df[player_stats_df['season'] == league_year]

    if current_year_stats.empty:
        print(f"No player stats found for the year {league_year}. Please ensure data is available for this season.")
        return

    # Determine the most recent week with data
    last_week = current_year_stats['week'].max()
    if pd.isna(last_week):
        print(f"No weekly data found for the year {league_year}.")
        return

    print(f"Analyzing performance for Week {int(last_week)} of the {league_year} season...")

    # Get stats for the last week
    last_week_stats = current_year_stats[current_year_stats['week'] == last_week]

    # Calculate total points for my team
    my_team_last_week_stats = last_week_stats[last_week_stats['player_name'].isin(my_team_players_normalized)]
    my_team_total_points = my_team_last_week_stats['fantasy_points'].sum()

    print(f"Your team scored {my_team_total_points:.2f} points in Week {int(last_week)}.")

    # Prepare data for LLM analysis
    llm_prompt = f"""
    Analyze my fantasy football team's performance for Week {int(last_week)} of the {league_year} season.

    My team's roster:
    {', '.join(my_team_players_raw)}

    My team's fantasy points for Week {int(last_week)}: {my_team_total_points:.2f}

    Here are the individual player performances from my team for Week {int(last_week)}:
    """
    if not my_team_last_week_stats.empty:
        llm_prompt += my_team_last_week_stats[['player_name', 'fantasy_points', 'position']].to_markdown(index=False)
    else:
        llm_prompt += "No individual player stats found for your team this week."

    llm_prompt += """

    Based on this information, please provide:
    1. An evaluation of my team's performance in Week {int(last_week)}. Did I do well or poorly, and why?
    2. Specific suggestions for improvement, considering potential waiver wire pickups, trade targets, or lineup adjustments.
    3. Identify any underperforming players on my team.
    4. Suggest potential strategies for the upcoming weeks.
    """

    print("Asking the AI for analysis...")
    try:
        configure_llm_api()
        analysis_result = ask_llm(llm_prompt)
        return analysis_result
    except Exception as e:
        return f"Failed to get AI analysis: {e}. Please ensure your API key is correctly set and the LLM service is available."

if __name__ == "__main__":
    analysis_output = analyze_last_game()
    if analysis_output:
        print("\n--- AI Analysis ---")
        print(analysis_output)
        print("\n-------------------")
