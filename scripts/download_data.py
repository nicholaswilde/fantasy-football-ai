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
import subprocess
import os

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
    """
    Calls the download_adp.py script to generate player_adp.csv.
    The player_data argument is not used directly here, but kept for function signature consistency.
    """
    print("Calling scripts/download_adp.py to fetch ADP data...")
    try:
        # Execute download_adp.py as a subprocess
        result = subprocess.run(
            ['python3', os.path.join(os.path.dirname(__file__), 'download_adp.py')],
            capture_output=True, text=True, check=True
        )
        print(result.stdout)
        if result.stderr:
            print(f"Error from download_adp.py: {result.stderr}")
        print("data/player_adp.csv has been created successfully by download_adp.py.")
    except subprocess.CalledProcessError as e:
        print(f"Error running download_adp.py: {e}")
        print(f"Stdout: {e.stdout}")
        print(f"Stderr: {e.stderr}")
        print("Could not fetch ADP data. Generating with N/A placeholders (fallback)...")
        # Fallback to N/A if download_adp.py fails
        with open('data/player_adp.csv', 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['player_id', 'full_name', 'position', 'team', 'adp']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            for player_id, player in player_data.items():
                player['adp'] = 'N/A'
                writer.writerow(player)

if __name__ == "__main__":
    print("\n--- Starting data download process ---")
    print("Downloading player data from the Sleeper API...")
    all_players = fetch_sleeper_data()

    if all_players:
        generate_player_projections_csv(all_players)
        generate_player_adp_csv(all_players)
        print("\n--- Data download process finished! ---")
    else:
        print("\n--- Data download process failed! ---")