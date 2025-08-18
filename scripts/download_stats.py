#!/usr/bin/env python3

import nfl_data_py as nfl
import pandas as pd
import os

def download_and_save_stats(years, output_file="data/player_stats.csv"):
    """
    Downloads player stats from the nfl_data_py library for the specified years
    and saves the data to a CSV file.

    Args:
        years (list[int]): A list of integer years (e.g., [2023, 2024]) for which
                          to download data.
        output_file (str): The path and filename for the output CSV file.
    """
    print(f"Starting data download for seasons: {years}...")
    
    # Check if the data directory exists, and create it if not.
    output_dir = os.path.dirname(output_file)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"Created directory: {output_dir}")

    try:
        # The import_seasonal_data function gets the seasonal player data.
        # This function returns a pandas DataFrame, which is a great format for data analysis.
        df = nfl.import_seasonal_data(years)

        # Save the DataFrame to a CSV file.
        # `index=False` prevents pandas from writing the DataFrame index to the CSV.
        df.to_csv(output_file, index=False)

        print(f"Download complete! Data for {len(years)} seasons saved to '{output_file}'.")
    except Exception as e:
        print(f"An error occurred: {e}")
        print("Please ensure the 'nfl_data_py' library is installed and you have an active internet connection.")


if __name__ == "__main__":
    # Define the years you want to download
    seasons_to_download = [2023, 2024]
    
    # Run the function
    download_and_save_stats(seasons_to_download)


