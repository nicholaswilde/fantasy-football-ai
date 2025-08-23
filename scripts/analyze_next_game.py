import os
import pandas as pd
import yaml
from dotenv import load_dotenv
from espn_api.football import League
from datetime import datetime
from analysis import ask_llm, configure_llm_api

# Load environment variables
load_dotenv()

# Configuration file paths
CONFIG_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', 'config.yaml'
)
PLAYER_STATS_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'player_stats.csv'
)
MY_TEAM_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'my_team.md'
)

def load_config():
    """Loads the configuration from config.yaml."""
    with open(CONFIG_FILE, 'r') as f:
        return yaml.safe_load(f)

def get_my_team_roster(file_path):
    """Reads the my_team.md file (Markdown table format) and extracts player names."""
    players = []
    with open(file_path, 'r') as f:
        lines = f.readlines()
        # Skip header and separator lines (first 3 lines after the comment and title)
        # So, actual data starts from line 5 (index 4)
        if len(lines) > 4:
            for line in lines[4:]:
                line = line.strip()
                if line.startswith('|') and '|' in line[1:]:
                    parts = [p.strip() for p in line.split('|')]
                    if len(parts) > 2: # Ensure there's at least a player name column
                        player_name = parts[1] # Assuming player name is in the second column
                        if player_name: # Ensure it's not empty
                            players.append(player_name)
    return players

def get_next_opponent_roster():
    """Fetches the user's next opponent's roster from ESPN."""
    config = load_config()
    my_team_id = config.get('my_team_id')
    if not my_team_id:
        return None, "Error: 'my_team_id' not found in config.yaml. Please run 'task identify_my_team' to set it."

    league_id = os.getenv("LEAGUE_ID")
    espn_s2 = os.getenv("ESPN_S2")
    swid = os.getenv("SWID")
    
    if not all([league_id, espn_s2, swid]):
        return None, "Error: LEAGUE_ID, ESPN_S2, and SWID environment variables must be set."

    try:
        league = League(league_id=int(league_id), year=datetime.now().year, espn_s2=espn_s2, swid=swid)
        current_week = league.current_week
        if current_week == 0:
            return None, "The fantasy football season has not started yet."
        matchups = league.scoreboard(week=current_week)
        
        my_matchup = None
        for matchup in matchups:
            if matchup.home_team.team_id == my_team_id or matchup.away_team.team_id == my_team_id:
                my_matchup = matchup
                break

        if my_matchup:
            if my_matchup.home_team.team_id == my_team_id:
                opponent = my_matchup.away_team
            else:
                opponent = my_matchup.home_team
            return [player.name for player in opponent.roster], None

    except Exception as e:
        return None, f"An error occurred while fetching opponent's roster: {e}"

    return None, "Could not determine next opponent."


def normalize_player_name(name):
    """Normalizes player names to match the format in player_stats.csv (e.g., 'Patrick Mahomes' to 'P.Mahomes')."""
    parts = name.split(' ')
    if len(parts) > 1:
        return f"{parts[0][0]}.{' '.join(parts[1:])}"
    return name

def analyze_next_game(opponent_players_raw=None):
    """
    Analyzes the next game and provides suggestions to win.
    If opponent_players_raw is None, it attempts to fetch the roster automatically.
    """
    if opponent_players_raw is None:
        opponent_players_raw, error_message = get_next_opponent_roster()
        if error_message:
            return error_message

    config = load_config()
    league_settings = config.get('league_settings', {})
    roster_settings = config.get('roster_settings', {})
    scoring_rules = config.get('scoring_rules', {})
    league_year = league_settings.get('year')

    if not league_year:
        return "Error: 'year' not found in config.yaml under 'league_settings'."

    try:
        player_stats_df = pd.read_csv(PLAYER_STATS_FILE)
    except FileNotFoundError:
        return f"Error: {PLAYER_STATS_FILE} not found. Please run 'task download' to get player stats."

    my_team_players_raw = get_my_team_roster(MY_TEAM_FILE)
    if not my_team_players_raw:
        return f"Error: No players found in {MY_TEAM_FILE}. Please ensure your team roster is correctly set up."

    my_team_players_normalized = [normalize_player_name(p) for p in my_team_players_raw]

    opponent_players_normalized = [normalize_player_name(p) for p in opponent_players_raw]

    current_year_stats = player_stats_df[player_stats_df['season'] == league_year]

    if current_year_stats.empty:
        return f"No player stats found for the year {league_year}. Please ensure data is available for this season."

    my_team_avg_points = current_year_stats[current_year_stats['player_name'].isin(my_team_players_normalized)]['fantasy_points'].mean()
    opponent_avg_points = current_year_stats[current_year_stats['player_name'].isin(opponent_players_normalized)]['fantasy_points'].mean()

    league_settings_str = yaml.dump(league_settings, default_flow_style=False)
    roster_settings_str = yaml.dump(roster_settings, default_flow_style=False)
    scoring_rules_str = yaml.dump(scoring_rules, default_flow_style=False)

    llm_prompt = f"""
    Analyze the upcoming fantasy football game based on the following information.

    **League Context:**

    **1. League Settings:**
    ```yaml
    {league_settings_str}
    ```

    **2. Roster Settings:**
    ```yaml
    {roster_settings_str}
    ```

    **3. Scoring Rules:**
    ```yaml
    {scoring_rules_str}
    ```

    **Matchup Details:**

    My Team Roster:
    {', '.join(my_team_players_raw)}
    My Team Average Fantasy Points (Season-to-Date): {my_team_avg_points:.2f}

    Opponent Team Roster:
    {', '.join(opponent_players_raw)}
    Opponent Team Average Fantasy Points (Season-to-Date): {opponent_avg_points:.2f}

    Based on this, please provide:
    1. An assessment of my team's strengths and weaknesses against the opponent.
    2. Key player matchups to watch.
    3. Strategic suggestions to win the game, considering potential lineup changes, waiver wire pickups, or trade targets.
    4. Identify any players on either team who might be overperforming or underperforming based on their season averages.

    Important Note: This analysis is based on season-to-date averages. For more accurate predictions, weekly projections would be ideal, but are not available for this analysis.
    """

    try:
        configure_llm_api()
        analysis_result = ask_llm(llm_prompt)
        return analysis_result
    except Exception as e:
        return f"Failed to get AI analysis: {e}. Please ensure your API key is correctly set and the LLM service is available."

if __name__ == "__main__":
    print("Analyzing next game...")
    analysis_output = analyze_next_game()
    if analysis_output:
        print("\n--- AI Analysis ---")
        print(analysis_output)
        print("\n-------------------")