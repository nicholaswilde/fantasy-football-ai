#!/usr/bin/env python3
################################################################################
#
# Script Name: download_data.py
# ----------------
# Downloads player data (projections and ADP) from the Sleeper API.
#
# @author Nicholas Wilde, 0xb299a622
# @date 2025-08-20
# @version 0.2.0
#
################################################################################

import requests
import csv

def fetch_sleeper_data():
    """Fetches all player data from the Sleeper API."""
    url = "https://api.sleeper.app/v1/players/nfl"
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raises an HTTPError for bad responses (4xx or 5xx)
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from Sleeper API: {e}")
        return None

def fetch_adp_data():
    """Fetches NFL ADP data from the Sleeper API."""
    url = "https://api.sleeper.app/v1/draft/nfl/adp"
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching ADP data from Sleeper API: {e}")
        return None

def generate_player_projections_csv(player_data):
    """Generates player_projections.csv from the player data."""
    if not player_data:
        print("No player data to process for projections.")
        return

    with open('data/player_projections.csv', 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['player_id', 'full_name', 'team', 'position', 'age', 'years_exp', 'projected_points']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames, extrasaction='ignore')

        writer.writeheader()
        for player_id, player in player_data.items():
            # Add a placeholder for projected_points
            player['projected_points'] = 0.0 # Placeholder value
            writer.writerow(player)
    print("data/player_projections.csv has been created successfully.")

def generate_player_adp_csv(player_data):
    """Generates player_adp.csv from the player data and fetched ADP."""
    if not player_data:
        print("No player data to process for ADP.")
        return

    adp_data = fetch_adp_data()
    if not adp_data:
        print("Could not fetch ADP data. Generating with N/A placeholders.")
        # Fallback to N/A if ADP data cannot be fetched
        with open('data/player_adp.csv', 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['player_id', 'full_name', 'position', 'team', 'adp']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            for player_id, player in player_data.items():
                player['adp'] = 'N/A'
                writer.writerow(player)
        return

    # Create a dictionary for quick ADP lookup by player_id
    adp_lookup = {item['player_id']: item['adp'] for item in adp_data}

    with open('data/player_adp.csv', 'w', newline='', encoding='utf-8') as csvfile:
        fieldnames = ['player_id', 'full_name', 'position', 'team', 'adp']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames, extrasaction='ignore')

        writer.writeheader()
        for player_id, player in player_data.items():
            # Get ADP for the player, default to 'N/A' if not found
            player['adp'] = adp_lookup.get(player_id, 'N/A')
            writer.writerow(player)
    print("data/player_adp.csv has been created successfully with ADP data.")

if __name__ == "__main__":
    print("Downloading player data from the Sleeper API...")
    all_players = fetch_sleeper_data()

    if all_players:
        generate_player_projections_csv(all_players)
        generate_player_adp_csv(all_players)
        print("\nScript finished!")
