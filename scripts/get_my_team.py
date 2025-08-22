#!/usr/bin/env python3
################################################################################
#
# Script Name: get_my_team.py
# ----------------
# Fetches the user's fantasy football team from ESPN and saves it to a Markdown file.
#
# @author Nicholas Wilde, 0xb299a622
# @date 21 08 2025
# @version 0.4.0
#
################################################################################

import os
from datetime import datetime
from espn_api.football import League
from dotenv import load_dotenv
import yaml
from tabulate import tabulate

# Load environment variables from .env file
load_dotenv()

# Load configuration from config.yaml
CONFIG_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', 'config.yaml'
)

def load_config():
    with open(CONFIG_FILE, 'r') as f:
        return yaml.safe_load(f)

CONFIG = load_config()

def get_my_team():
    """
    Fetches the user's fantasy football team and formats it as a markdown file.
    """
    league_id = os.getenv("LEAGUE_ID")
    espn_s2 = os.getenv("ESPN_S2")
    swid = os.getenv("SWID")
    year = CONFIG.get('league_settings', {}).get('year', datetime.now().year)

    if not all([league_id, espn_s2, swid]):
        raise ValueError(
            "Missing required environment variables. Please set LEAGUE_ID, "
            "ESPN_S2, and SWID in your .env file."
        )

    try:
        league = League(league_id=int(league_id), year=year, espn_s2=espn_s2, swid=swid)

        # Get team from config
        my_team_id = CONFIG.get('my_team_id')
        if not my_team_id:
            raise ValueError("my_team_id not found in config.yaml. Please run identify_my_team.py first.")

        team = None
        for t in league.teams:
            if t.team_id == my_team_id:
                team = t
                break
        
        if team is None:
            raise ValueError(f"Could not find team with ID {my_team_id}")

        roster = {
            pos: [] for pos, count in CONFIG.get('roster_settings', {}).items() if count > 0
        }
        # Add FLEX and BENCH if they are not explicitly in roster_settings but are common
        if "FLEX" not in roster: roster["FLEX"] = []
        if "BENCH" not in roster: roster["BENCH"] = []

        for player in team.roster:
            # Normalize position names from espn_api to match config.yaml if necessary
            # For example, 'D/ST' in config might be 'DST' in espn_api
            player_pos = player.position.replace('/', '').upper() # Simple normalization

            if player_pos == 'DST' or player_pos == 'K': # Check for D/ST or K
                pass

            if player_pos in roster:
                roster[player_pos].append(player.name)
            else:
                # If the position is not explicitly in our roster settings,
                # or if it's a special case like 'FLEX' that needs to be handled,
                # we'll put it in the BENCH for now.
                # A more sophisticated mapping might be needed for FLEX positions
                # if espn_api provides specific flex indicators.
                roster["BENCH"].append(player.name)

        with open("data/my_team.md", "w") as f:
            now = datetime.now()
            dt_string = now.strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"<!-- Last updated: {dt_string} -->\n")
            f.write("# My Team\n\n")
            for position, players in roster.items():
                if players: # Only write sections that have players
                    f.write(f"## {position} ({len(players)})\n")
                    for player in players:
                        f.write(f"- {player}\n")
                    f.write("\n")

        print("Successfully created data/my_team.md")


    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    try:
        league_id = os.getenv("LEAGUE_ID")
        espn_s2 = os.getenv("ESPN_S2")
        swid = os.getenv("SWID")
        year = CONFIG.get('league_settings', {}).get('year', datetime.now().year)

        if not all([league_id, espn_s2, swid]):
            raise ValueError(
                "Missing required environment variables. Please set LEAGUE_ID, "
                "ESPN_S2, and SWID in your .env file."
            )

        league = League(league_id=int(league_id), year=year, espn_s2=espn_s2, swid=swid)

        # Get team from config
        my_team_id = CONFIG.get('my_team_id')
        if not my_team_id:
            raise ValueError("my_team_id not found in config.yaml. Please run identify_my_team.py first.")

        team = None
        for t in league.teams:
            if t.team_id == my_team_id:
                team = t
                break
        
        if team is None:
            raise ValueError(f"Could not find team with ID {my_team_id}")

        roster_data = []
        for player in team.roster:
            roster_data.append([player.name, player.position, player.proTeam])

        headers = ["Player Name", "Position", "NFL Team"]
        print("### My Current Team Roster\n")
        print(tabulate(roster_data, headers=headers, tablefmt="grid"))
        print("\n")

        # Call the function to generate the markdown file
        get_my_team()
        print("get_my_team.py script executed. It generates 'data/my_team.md' for use by other scripts.")

    except Exception as e:
        print(f"An error occurred: {e}")
