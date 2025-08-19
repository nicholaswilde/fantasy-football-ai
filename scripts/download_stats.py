#!/usr/bin/env python3

import nfl_data_py as nfl
import pandas as pd
import os

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
        # The import_weekly_data function gets the weekly player data.
        # This function returns a pandas DataFrame, which is a great format for data analysis.
        df = nfl.import_weekly_data(years)

        # Get player IDs and names
        player_ids_df = nfl.import_ids()

        # Ensure player_id and espn_id are of the same type (string) for merging
        df['player_id'] = df['player_id'].astype(str)
        player_ids_df['espn_id'] = player_ids_df['espn_id'].astype(str)

        # Merge player names into the weekly stats DataFrame
        # We'll merge on 'player_id' from weekly data and 'espn_id' from player IDs.
        # The player name column is 'name' in player_ids_df.
        df = pd.merge(df, player_ids_df[['espn_id', 'name']], left_on='player_id', right_on='espn_id', how='left')

        # Drop the 'espn_id' column as it's redundant after merging
        df.drop(columns=['espn_id'], inplace=True)

        # The 'player_display_name' column from import_weekly_data already contains the full name.
        # We will drop the 'name' column from the merge, as 'player_display_name' is preferred.
        # If 'name' exists (from the merge), drop it.
        if 'name' in df.columns:
            df.drop(columns=['name'], inplace=True)

        # Reorder columns to place 'player_display_name' at the beginning for easier viewing
        cols = df.columns.tolist()
        if 'player_display_name' in cols:
            cols.remove('player_display_name')
        df = df[['player_display_name'] + cols]

        # Save the DataFrame to a CSV file.
        # `index=False` prevents pandas from writing the DataFrame index to the CSV.
        df.to_csv(output_file, index=False)

        print(f"Download complete! Weekly data for {len(years)} seasons saved to '{output_file}'.")
    except Exception as e:
        print(f"An error occurred: {e}")
        print("Please ensure the 'nfl_data_py' library is installed and you have an active internet connection.")


if __name__ == "__main__":
    # Define the years you want to download
    seasons_to_download = [2023, 2024]
    
    # Run the function
    download_and_save_weekly_stats(seasons_to_download)


