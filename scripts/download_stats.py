#!/usr/bin/env python3
################################################################################
#
# Script Name: download_stats.py
# ----------------
# Downloads weekly NFL player statistics from nfl_data_py and saves them to a CSV file.
#
# @author Nicholas Wilde, 0xb299a622
# @date 21 08 2025
# @version 0.3.0
#
################################################################################

import nfl_data_py as nfl
import pandas as pd
import os
import datetime
import argparse
import yaml
from espn_api.football import League
from dotenv import load_dotenv

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

def get_espn_player_stats(league, years):
    """
    Fetches K and D/ST stats from ESPN API for the given years.
    """
    espn_stats = []
    for year in years:
        # Re-initialize league for each year if necessary, or ensure it handles multiple years
        # For now, assuming league object can fetch data for different years if passed
        # or that we are only interested in the current year's stats.
        # The espn_api League object is initialized with a single year.
        # So, we need to re-initialize it for each year.
        league_id = os.getenv("LEAGUE_ID")
        espn_s2 = os.getenv("ESPN_S2")
        swid = os.getenv("SWID")
        current_league = League(league_id=int(league_id), year=year, espn_s2=espn_s2, swid=swid)

        for team in current_league.teams:
            for player in team.roster:
                player_pos = player.position.replace('/', '').upper()
                if player_pos == 'K' or player_pos == 'DST':
                    if hasattr(player, 'stats') and player.stats:
                        # Assuming stats[0] contains season totals
                        stats_breakdown = player.stats.get(0, {}).get('breakdown', {})
                        player_data = {
                            'player_display_name': player.name,
                            'position': player.position,
                            'proTeam': player.proTeam,
                            'season': year,
                        }
                        # Add all stats from breakdown
                        for stat_name, stat_value in stats_breakdown.items():
                            player_data[stat_name] = stat_value
                        espn_stats.append(player_data)
    return pd.DataFrame(espn_stats)

def download_and_save_weekly_stats(years, output_file="data/player_stats.csv"):
    """
    Downloads weekly player stats from the nfl_data_py library for the specified years
    and saves the data to a CSV file.

    Args:
        years (list[int]): A list of integer years (e.g., [2023, 2024]) for which
                          to download data.
        output_file (str): The path and filename for the output CSV file.
    """
    print(f"Starting weekly data download for seasons: {years}...")
    
    # Check if the data directory exists, and create it if not.
    output_dir = os.path.dirname(output_file)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Created directory: {output_dir}")

    try:
        # Get offensive player stats from nfl_data_py
        df_nfl = nfl.import_weekly_data(years)

        # Get player IDs and names
        player_ids_df = nfl.import_ids()

        # Ensure player_id and espn_id are of the same type (string) for merging
        df_nfl['player_id'] = df_nfl['player_id'].astype(str)
        player_ids_df['espn_id'] = player_ids_df['espn_id'].astype(str)

        # Merge player names into the weekly stats DataFrame
        df_nfl = pd.merge(df_nfl, player_ids_df[['espn_id', 'name']], left_on='player_id', right_on='espn_id', how='left')

        # Drop the 'espn_id' column as it's redundant after merging
        df_nfl.drop(columns=['espn_id'], inplace=True)

        # The 'player_display_name' column from import_weekly_data already contains the full name.
        # We will drop the 'name' column from the merge, as 'player_display_name' is preferred.
        if 'name' in df_nfl.columns:
            df_nfl.drop(columns=['name'], inplace=True)

        # Reorder columns to place 'player_display_name' at the beginning for easier viewing
        cols = df_nfl.columns.tolist()
        if 'player_display_name' in cols:
            cols.remove('player_display_name')
        df_nfl = df_nfl[['player_display_name'] + cols]

        # Get K and D/ST stats from ESPN API
        league_id = os.getenv("LEAGUE_ID")
        espn_s2 = os.getenv("ESPN_S2")
        swid = os.getenv("SWID")
        if not all([league_id, espn_s2, swid]):
            raise ValueError(
                "Missing required environment variables for ESPN API. Please set LEAGUE_ID, "
                "ESPN_S2, and SWID in your .env file."
            )
        # Initialize league object once, it will be re-initialized per year in get_espn_player_stats
        # Pass a dummy year for initial league object, as it will be overridden in the function
        dummy_year = years[0] if years else datetime.datetime.now().year
        league = League(league_id=int(league_id), year=dummy_year, espn_s2=espn_s2, swid=swid)
        df_espn = get_espn_player_stats(league, years)

        # Merge nfl_data_py and espn_api data
        # Prioritize ESPN data for K and D/ST by dropping them from nfl_data_py data first
        df_nfl_filtered = df_nfl[~df_nfl['position'].isin(['K', 'DST'])].copy()
        
        # Concatenate the two dataframes
        df_combined = pd.concat([df_nfl_filtered, df_espn], ignore_index=True, sort=False)

        # Save the DataFrame to a CSV file.
        # `index=False` prevents pandas from writing the DataFrame index to the CSV.
        df_combined.to_csv(output_file, index=False)
        
        # Update the last_updated.log file
        now = datetime.datetime.now()
        with open("data/last_updated.log", "w") as log_file:
            log_file.write(f"Player stats last updated: {now.strftime('%Y-%m-%d %H:%M:%S')}")
            print("Updated data/last_updated.log")

        print(f"Download complete! Combined data for {len(years)} seasons saved to '{output_file}'.")
    except Exception as e:
        print(f"An error occurred: {e}")
        print("Please ensure the 'nfl_data_py' library is installed and you have an active internet connection.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download weekly player stats for specified years.")
    default_years = CONFIG.get('league_settings', {}).get('data_years', [datetime.datetime.now().year - 1, datetime.datetime.now().year])
    parser.add_argument(
        "--years",
        type=int,
        nargs='+',
        default=default_years,
        help="A list of years to download data for (e.g., --years 2023 2024). If not specified, defaults to the years defined in config.yaml."
    )
    args = parser.parse_args()
    
    # Run the function
    download_and_save_weekly_stats(args.years)