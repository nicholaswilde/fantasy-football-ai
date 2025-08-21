#!/usr/bin/env python3
################################################################################
#
# Script Name: get_my_team.py
# ----------------
# Fetches the user's fantasy football team from ESPN and saves it to a Markdown file.
#
# @author Nicholas Wilde, 0xb299a622
# @date 2025-08-20
# @version 0.1.0
#
################################################################################

import os
from datetime import datetime
from espn_api.football import League
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def get_my_team():
    """
    Fetches the user's fantasy football team and formats it as a markdown file.
    """
    league_id = os.getenv("LEAGUE_ID")
    espn_s2 = os.getenv("ESPN_S2")
    swid = os.getenv("SWID")

    if not all([league_id, espn_s2, swid]):
        raise ValueError(
            "Missing required environment variables. Please set LEAGUE_ID, "
            "ESPN_S2, and SWID in your .env file."
        )

    try:
        league = League(league_id=int(league_id), year=2024, espn_s2=espn_s2, swid=swid)

        # Find the user's team
        # We are assuming the user is the one who owns the team
        # There is no easy way to get the team of the current user
        # So we will have to iterate over all teams and find the one that has the user's name
        # For now, we will just get the first team in the league
        # TODO: Find a better way to get the user's team

        team = league.teams[0]

        roster = {
            "QB": [],
            "RB": [],
            "WR": [],
            "TE": [],
            "FLEX": [],
            "BENCH": [],
        }

        for player in team.roster:
            if player.position in roster:
                roster[player.position].append(player.name)
            else:
                # Handle other positions like K, D/ST etc.
                # For now, we will add them to the bench
                roster["BENCH"].append(player.name)

        with open("data/my_team.md", "w") as f:
            now = datetime.now()
            dt_string = now.strftime("%Y-%m-%d %H:%M:%S")
            f.write(f"<!-- Last updated: {dt_string} -->\n")
            f.write("# My Team\n\n")
            for position, players in roster.items():
                f.write(f"## {position}\n")
                for player in players:
                    f.write(f"- {player}\n")
                f.write("\n")

        print("Successfully created data/my_team.md")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    get_my_team()
