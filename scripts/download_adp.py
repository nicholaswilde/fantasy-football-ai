#!/usr/bin/env python3
################################################################################
#
# Script Name: download_adp.py
# ----------------
# Downloads and processes Average Draft Position (ADP) data from a specified source
# and saves it to data/player_adp.csv.
#
# @author Nicholas Wilde, 0xb299a622
# @date 2025-08-23
# @version 0.1.0
#
################################################################################

import pandas as pd
import os
import requests
import yaml

# Define file paths
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ADP_OUTPUT_PATH = os.path.join(PROJECT_ROOT, 'data', 'player_adp.csv')
CONFIG_FILE = os.path.join(PROJECT_ROOT, 'config.yaml')

def load_config():
    """
    Loads configuration from the config.yaml file.
    """
    with open(CONFIG_FILE, 'r') as f:
        return yaml.safe_load(f)

CONFIG = load_config()

# URL for Fantasy Football Calculator ADP API
# This API provides data for 12-team standard leagues for 2025
ADP_URL = f"https://fantasyfootballcalculator.com/api/v1/adp/standard?teams={CONFIG['league_settings']['number_of_teams']}&year={CONFIG['league_settings']['year']}&position=all"

def fetch_and_process_adp():
    """
    Fetches ADP data from Fantasy Football Calculator API, processes it, and saves it in the required format.
    """
    print(f"Fetching ADP data from {ADP_URL}...")
    try:
        response = requests.get(ADP_URL)
        response.raise_for_status()  # Raise an HTTPError for bad responses (4xx or 5xx)
        data = response.json()

        # The API response has a 'players' key containing the list of player dictionaries
        if 'players' not in data:
            raise ValueError("API response does not contain 'players' key.")
        
        players_data = data['players']

        if not players_data:
            raise ValueError("No player data found in the API response.")

        adp_df = pd.DataFrame(players_data)

        # --- Column mapping for Fantasy Football Calculator API ---
        # API keys observed: 'name', 'position', 'adp' (among others)
        column_mapping = {
            'name': 'full_name',
            'position': 'position',
            'adp': 'adp'
        }
        
        # Rename columns to match our desired format
        adp_df = adp_df.rename(columns=column_mapping)

        # Ensure required columns exist after renaming
        required_cols = ['full_name', 'position', 'adp']
        if not all(col in adp_df.columns for col in required_cols):
            missing_cols = [col for col in required_cols if col not in adp_df.columns]
            raise ValueError(f"Missing required columns after processing: {missing_cols}. "
                             "Check column_mapping or API response structure.")

        # Select and reorder columns
        processed_df = adp_df[required_cols].copy()

        # Save to the target path
        processed_df.to_csv(ADP_OUTPUT_PATH, index=False)
        print(f"Successfully fetched and processed ADP data and saved to {ADP_OUTPUT_PATH}")
        print(f"Total players fetched: {len(processed_df)}")

    except requests.exceptions.RequestException as e:
        print(f"Network or API request error: {e}")
    except ValueError as e:
        print(f"Data processing error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

def main():
    fetch_and_process_adp()

if __name__ == "__main__":
    main()
