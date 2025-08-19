import os
import pandas as pd
from datetime import datetime
from dotenv import load_dotenv
from espn_api.football import League

def get_available_players(league_id, espn_s2, swid):
    """
    Fetches available players from an ESPN fantasy football league 
    and saves them to a CSV file.
    """
    # Initialize League object
    league = League(league_id=league_id, year=2024, espn_s2=espn_s2, swid=swid)

    # Get free agents
    free_agents = league.free_agents(size=1000)

    # Convert player data to a list of dictionaries
    players_data = []
    for player in free_agents:
        players_data.append({
            'name': player.name,
            'position': player.position,
            'pro_team': player.proTeam,
            'total_points': player.total_points,
            'projected_points': player.projected_total_points,
            'percent_owned': player.percent_owned,
        })

    # Create a pandas DataFrame
    df = pd.DataFrame(players_data)

    # Save to CSV
    output_path = 'data/available_players.csv'
    df.to_csv(output_path, index=False)

    mod_time = os.path.getmtime(output_path)
    dt_string = datetime.fromtimestamp(mod_time).strftime("%Y-%m-%d %H:%M:%S")

    print(f"Successfully saved available players to {output_path}")
    print(f"Last updated: {dt_string}")

if __name__ == "__main__":
    load_dotenv()

    league_id = os.getenv("LEAGUE_ID")
    espn_s2 = os.getenv("ESPN_S2")
    swid = os.getenv("SWID")

    if not all([league_id, espn_s2, swid]):
        raise ValueError("Please set LEAGUE_ID, ESPN_S2, and SWID environment variables.")

    get_available_players(int(league_id), espn_s2, swid)
