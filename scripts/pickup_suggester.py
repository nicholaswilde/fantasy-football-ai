import pandas as pd
import os

# Define file paths
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AVAILABLE_PLAYERS_PATH = os.path.join(PROJECT_ROOT, 'data', 'available_players.csv')
PLAYER_STATS_PATH = os.path.join(PROJECT_ROOT, 'data', 'player_stats.csv')
MY_TEAM_PATH = os.path.join(PROJECT_ROOT, 'data', 'my_team.md')

def load_available_players(file_path):
    """Loads available players from the CSV file and renames columns for consistency."""
    try:
        df = pd.read_csv(file_path)
        # Rename columns to match player_stats_df for merging
        df = df.rename(columns={'name': 'player_display_name', 'pro_team': 'recent_team'})
        return df
    except FileNotFoundError:
        print(f"Error: Available players file not found at {file_path}")
        return pd.DataFrame()

def load_player_stats(file_path):
    """Loads player season stats from the CSV file."""
    try:
        return pd.read_csv(file_path)
    except FileNotFoundError:
        print(f"Error: Player stats file not found at {file_path}")
        return pd.DataFrame()

def load_my_team(file_path):
    """
    Loads and parses the user's team from the Markdown file.
    This is a simplified parser. It expects headings like '## QB', '## RB', etc.,
    followed by bulleted lists of player names.
    """
    my_team = {
        'QB': [], 'RB': [], 'WR': [], 'TE': [], 'FLEX': [], 'K': [], 'DST': [], 'BENCH': []
    }
    current_position = None
    try:
        with open(file_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line.startswith('## '):
                    pos = line.replace('## ', '').strip().upper()
                    if pos in my_team:
                        current_position = pos
                    else:
                        current_position = None
                elif line.startswith('- ') and current_position:
                    player_name = line.replace('- ', '').strip()
                    my_team[current_position].append(player_name)
    except FileNotFoundError:
        print(f"Warning: My team file not found at {file_path}. Cannot analyze team needs.")
    return my_team

def calculate_player_value(player_stats_df):
    """Calculates average points per game (PPG) for players using fantasy_points_ppr."""
    # Group by player and calculate total PPR points and games played
    player_summary = player_stats_df.groupby(['player_display_name', 'position', 'recent_team']).agg(
        total_fantasy_points_ppr=('fantasy_points_ppr', 'sum'),
        games_played=('week', 'nunique') # Count unique weeks played
    ).reset_index()

    # Calculate AvgPoints (PPG)
    player_summary['AvgPoints'] = player_summary['total_fantasy_points_ppr'] / player_summary['games_played']

    # Handle cases where games_played might be 0 to avoid division by zero
    player_summary['AvgPoints'] = player_summary['AvgPoints'].fillna(0)

    return player_summary[['player_display_name', 'position', 'recent_team', 'AvgPoints']]

def identify_team_needs(my_team_roster):
    """Identifies positions where the user's team needs improvement or depth."""
    needs = {}
    # Define standard roster sizes for a 12-team league (adjust as needed)
    standard_roster_spots = {
        'QB': 1, 'RB': 2, 'WR': 2, 'TE': 1, 'FLEX': 1, 'K': 1, 'DST': 1
    }

    for pos, count in standard_roster_spots.items():
        if len(my_team_roster.get(pos, [])) < count:
            needs[pos] = count - len(my_team_roster.get(pos, []))
        # Simple check: if a starter has very low points, it's a need
        # This would require integrating with player stats for current roster
        # For now, just focus on roster count
    return needs

def recommend_pickups(available_players_df, player_value_df, my_team_roster):
    """Generates pickup recommendations."""
    if available_players_df.empty or player_value_df.empty:
        print("Cannot generate recommendations: missing data.")
        return

    # Merge available players with their performance data
    merged_df = pd.merge(
        available_players_df,
        player_value_df,
        on=['player_display_name', 'position', 'recent_team'], # Assuming these columns exist in both
        how='inner'
    )

    # Filter out players already on my team
    my_team_players = [player for sublist in my_team_roster.values() for player in sublist]
    merged_df = merged_df[~merged_df['player_display_name'].isin(my_team_players)]

    team_needs = identify_team_needs(my_team_roster)
    print("\n--- Your Team Needs ---")
    if not team_needs:
        print("Your team seems well-rounded based on roster size. Consider upgrading low-performing players.")
    else:
        for pos, count in team_needs.items():
            print(f"- {pos}: Need {count} player(s)")

    print("\n--- Top Pickup Recommendations ---")
    recommendations = []

    # Prioritize positions with needs
    for pos, count in sorted(team_needs.items(), key=lambda item: item[1], reverse=True):
        if pos == 'FLEX':
            # For FLEX, recommend top RBs, WRs, TEs
            flex_candidates = merged_df[merged_df['position'].isin(['RB', 'WR', 'TE'])]
            top_players_at_pos = flex_candidates.sort_values(by='AvgPoints', ascending=False).head(count * 2)
        elif pos in ['K', 'DST']:
            print(f"\nNote: Recommendations for {pos} are not currently supported.")
            continue
        else:
            top_players_at_pos = merged_df[
                (merged_df['position'] == pos)
            ].sort_values(by='AvgPoints', ascending=False).head(count * 2) # Get a few more than needed

        if not top_players_at_pos.empty:
            print(f"\nTop {pos} targets:")
            for _, row in top_players_at_pos.iterrows():
                recommendations.append(row)
                print(f"- {row['player_display_name']} ({row['recent_team']}) - AvgPoints: {row['AvgPoints']:.2f}")

    # Also show top overall available players if no specific needs
    if not team_needs:
        top_overall = merged_df.sort_values(by='AvgPoints', ascending=False).head(10)
        if not top_overall.empty:
            print("\nTop overall available players (no specific team needs identified):")
            for _, row in top_overall.iterrows():
                recommendations.append(row)
                print(f"- {row['player_display_name']} ({row['recent_team']}, {row['position']}) - AvgPoints: {row['AvgPoints']:.2f}")

    if not recommendations:
        print("No suitable pickup recommendations at this time.")

def main():
    print("Loading data...")
    available_players = load_available_players(AVAILABLE_PLAYERS_PATH)
    player_stats = load_player_stats(PLAYER_STATS_PATH)
    my_team = load_my_team(MY_TEAM_PATH)

    if player_stats.empty:
        print("Player stats data is empty. Cannot proceed with recommendations.")
        return

    # Ensure 'Player', 'Position', 'Team' columns exist in player_stats
    required_cols = ['player_display_name', 'position', 'recent_team']
    if not all(col in player_stats.columns for col in required_cols):
        print(f"Error: Player stats file must contain {required_cols} columns.")
        return

    # Calculate player value (e.g., AvgPoints)
    player_value = calculate_player_value(player_stats.copy()) # Pass a copy to avoid modifying original

    recommend_pickups(available_players, player_value, my_team)

if __name__ == "__main__":
    main()
