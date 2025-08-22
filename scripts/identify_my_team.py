#!/usr/bin/env python3
################################################################################
#
# Script Name: identify_my_team.py
# ----------------
# Iterates over all teams in the league, asks the user to identify their team,
# and saves the team ID to the config.yaml file.
#
# @author Nicholas Wilde, 0xb299a622
# @date 21 08 2025
# @version 0.2.1
#
################################################################################

import os
import yaml
from espn_api.football import League
from dotenv import load_dotenv
from tabulate import tabulate
from datetime import datetime

# Load environment variables from .env file
load_dotenv()

CONFIG_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', 'config.yaml'
)

def load_config():
    with open(CONFIG_FILE, 'r') as f:
        return yaml.safe_load(f)

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        yaml.dump(config, f, default_flow_style=False)

def identify_my_team():
    """
    Identifies and saves the user's team ID.
    """
    league_id = os.getenv("LEAGUE_ID")
    espn_s2 = os.getenv("ESPN_S2")
    swid = os.getenv("SWID")
    config = load_config()
    year = config.get('league_settings', {}).get('year', datetime.now().year)

    if not all([league_id, espn_s2, swid]):
        raise ValueError(
            "Missing required environment variables. Please set LEAGUE_ID, "
            "ESPN_S2, and SWID in your .env file."
        )

    try:
        league = League(league_id=int(league_id), year=year, espn_s2=espn_s2, swid=swid)

        print("Please identify your team from the list below:")
        for i, team in enumerate(league.teams):
            owner_name = team.owners[0].get('displayName', 'Unknown Owner') if team.owners else 'Unknown Owner'
            print(f"\n--- Team {i+1}: {team.team_name} ({owner_name}) ---")
            roster_data = []
            for player in team.roster:
                roster_data.append([player.name, player.position, player.proTeam])
            headers = ["Player Name", "Position", "NFL Team"]
            print(tabulate(roster_data, headers=headers, tablefmt="grid"))


        while True:
            try:
                selection = input(f"Which team is yours? (1-{len(league.teams)}): ")
                selection_index = int(selection) - 1
                if 0 <= selection_index < len(league.teams):
                    selected_team = league.teams[selection_index]
                    config['my_team_id'] = selected_team.team_id
                    save_config(config)
                    print(f"Your team has been set to: {selected_team.team_name}")
                    break
                else:
                    print("Invalid selection. Please try again.")
            except ValueError:
                print("Invalid input. Please enter a number.")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    identify_my_team()