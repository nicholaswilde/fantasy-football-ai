import pandas as pd
import yaml

# --- Configuration and Data Paths ---
LEAGUE_SETTINGS_PATH = 'GEMINI.md' # Path to the file containing league settings
PLAYER_ADP_PATH = 'data/player_adp.csv'
PLAYER_PROJECTIONS_PATH = 'data/player_projections.csv'

# --- League Settings (to be parsed from GEMINI.md) ---
LEAGUE_SETTINGS = {
    "roster_settings": {
        "QB": 1, "RB": 2, "WR": 2, "TE": 1, "RB/WR": 1, "WR/TE": 1,
        "K": 1, "D/ST": 1, "DP": 2, "BE": 7, "IR": 1
    },
    "scoring_settings": {
        # This will be a comprehensive dictionary of scoring rules
        # For now, we'll use a simplified example for projected points calculation
        "passing_yards_per_point": 25,
        "passing_td": 6,
        "interceptions_thrown": -3,
        "rushing_yards_per_point": 10,
        "rushing_td": 6,
        "receiving_yards_per_point": 10,
        "receiving_td": 6,
        "reception": 1 # Assuming full PPR based on context
    },
    "draft_position": 7,
    "num_teams": 12
}

def load_league_settings(file_path):
    """
    Loads league settings from the GEMINI.md file.
    In a real scenario, this would parse the markdown to extract settings.
    For this prototype, we'll use the hardcoded LEAGUE_SETTINGS.
    """
    print(f"Loading league settings from {file_path}...")
    # Placeholder for actual parsing logic
    return LEAGUE_SETTINGS

def load_player_data(adp_path, projections_path):
    """
    Loads player ADP and projected points data.
    These files are assumed to exist for the purpose of this script's structure.
    """
    print(f"Loading player ADP from {adp_path}...")
    try:
        adp_df = pd.read_csv(adp_path)
    except FileNotFoundError:
        print(f"Warning: {adp_path} not found. Creating dummy ADP data.")
        adp_df = pd.DataFrame({
            'full_name': [f'Player {i}' for i in range(1, 101)],
            'position': ['QB', 'RB', 'WR', 'TE'] * 25,
            'adp': range(1, 101)
        })

    print(f"Loading player projections from {projections_path}...")
    try:
        projections_df = pd.read_csv(projections_path)
    except FileNotFoundError:
        print(f"Warning: {projections_path} not found. Creating dummy projections data.")
        projections_df = pd.DataFrame({
            'full_name': [f'Player {i}' for i in range(1, 101)],
            'position': ['QB', 'RB', 'WR', 'TE'] * 25, # Added position for dummy data
            'projected_points': [i * 2.5 for i in range(100, 0, -1)]
        })

    
    # print(adp_df.columns)
    
    # print(projections_df.columns)

    # Merge dataframes
    player_data = pd.merge(adp_df, projections_df, on='full_name', how='outer')

    # Rename position_x to position and drop position_y
    if 'position_x' in player_data.columns:
        player_data.rename(columns={'position_x': 'position'}, inplace=True)
    if 'position_y' in player_data.columns:
        player_data.drop(columns=['position_y'], inplace=True)

    # print("--- Debug: player_data columns after merge and rename ---")
    # print(player_data.columns)
    # 
    

    # Fill NaNs. For 'position', fill with an empty string, otherwise fill with 0.
    # This line will be executed only if 'position' column exists after merge
    if 'position' in player_data.columns:
        player_data['position'].fillna('', inplace=True)
    player_data.fillna(0, inplace=True)
    return player_data

def calculate_vbd(player_data, roster_settings, scoring_settings):
    """
    Calculates Value-Based Drafting (VBD) scores for players.
    A more robust VBD calculation considering replacement level players for each position
    across the entire league.
    """
    print("Calculating VBD scores...")
    
    # Define core offensive positions for VBD calculation
    core_positions = ['QB', 'RB', 'WR', 'TE']
    
    # Calculate total number of starters for each core position across the league
    total_starters_per_position = {
        pos: roster_settings.get(pos, 0) * LEAGUE_SETTINGS['num_teams'] for pos in core_positions
    }
    
    # Determine a reasonable "replacement level" for each position
    # This is often the last drafted player at that position in a typical draft
    # For simplicity, we'll use the total number of starters + a few bench players
    replacement_level_count = {
        'QB': total_starters_per_position['QB'], # Only consider starting QBs for replacement level
        'RB': total_starters_per_position['RB'] + LEAGUE_SETTINGS['num_teams'] * 1.5, # 1.5 bench RBs per team
        'WR': total_starters_per_position['WR'] + LEAGUE_SETTINGS['num_teams'] * 1.5, # 1.5 bench WRs per team
        'TE': total_starters_per_position['TE'] + LEAGUE_SETTINGS['num_teams'] * 0.5, # 0.5 bench TEs per team
    }

    player_data['vbd'] = 0 # Initialize VBD column

    for position in core_positions:
        position_players = player_data[player_data['position'] == position].sort_values(by='projected_points', ascending=False)
        
        if not position_players.empty:
            # Determine the replacement level player for this position
            # Ensure we don't go out of bounds if there aren't enough players
            rl_index = min(int(replacement_level_count.get(position, 0)) - 1, len(position_players) - 1)
            
            if rl_index >= 0:
                replacement_level_points = position_players.iloc[rl_index]['projected_points']
                
                # Calculate VBD for players at this position
                player_data.loc[player_data['position'] == position, 'vbd'] = \
                    player_data['projected_points'] - replacement_level_points
            else:
                # If no replacement level can be determined (e.g., not enough players), VBD is just projected points
                player_data.loc[player_data['position'] == position, 'vbd'] = player_data['projected_points']
        else:
            player_data.loc[player_data['position'] == position, 'vbd'] = 0 # No players, no VBD

    # For K and D/ST, calculate VBD relative to a replacement level
    for position in ['K', 'D/ST']:
        position_players = player_data[player_data['position'] == position].sort_values(by='projected_points', ascending=False)
        if not position_players.empty:
            # For K and D/ST, replacement level can be much lower, e.g., the 12th or 15th best
            # We'll use the number of starters for that position across the league as replacement level
            num_starters_pos = roster_settings.get(position, 0) * LEAGUE_SETTINGS['num_teams']
            rl_index = min(num_starters_pos - 1, len(position_players) - 1)
            
            if rl_index >= 0:
                replacement_level_points = position_players.iloc[rl_index]['projected_points']
                player_data.loc[player_data['position'] == position, 'vbd'] = \
                    player_data['projected_points'] - replacement_level_points
            else:
                player_data.loc[player_data['position'] == position, 'vbd'] = player_data['projected_points']
        else:
            player_data.loc[player_data['position'] == position, 'vbd'] = 0
        
    return player_data


def suggest_draft_picks(player_data, league_settings):
    """
    Suggests optimal draft picks based on VBD, ADP, and roster needs.
    This simulation aims for a more realistic draft strategy by prioritizing roster spots.
    """
    print("Generating draft recommendations...")
    my_team = {pos: [] for pos in league_settings['roster_settings']}
    available_players = player_data.copy()
    draft_order = [] # To simulate picks

    # Define the order of roster spots to fill
    # Prioritize starting positions, then flex, then bench
    roster_fill_order = [
        'QB', 'RB', 'RB', 'WR', 'WR', 'TE', # Primary starters
        'RB/WR', 'WR/TE', # Flex spots
        'K', 'D/ST', # K and D/ST often drafted later
        'DP', 'DP', # DP spots
        'BE', 'BE', 'BE', 'BE', 'BE', 'BE', 'BE' # Bench spots
    ]

    # Filter out positions that are not in roster_settings (e.g., if DP is 0)
    roster_fill_order = [pos for pos in roster_fill_order if league_settings['roster_settings'].get(pos, 0) > 0]

    # Ensure we don't try to fill more spots than available in roster_settings
    actual_roster_fill_order = []
    temp_roster_counts = {pos: 0 for pos in league_settings['roster_settings']}
    for pos in roster_fill_order:
        if temp_roster_counts.get(pos, 0) < league_settings['roster_settings'].get(pos, 0):
            actual_roster_fill_order.append(pos)
            temp_roster_counts[pos] += 1

    num_rounds = len(actual_roster_fill_order) # Each team fills all spots

    for round_num in range(1, num_rounds + 1):
        print(f"--- Round {round_num} ---")
        # Determine pick number for this round (snake draft)
        if round_num % 2 != 0: # Odd rounds (forward)
            my_pick_in_round = league_settings['draft_position']
        else: # Even rounds (backward)
            my_pick_in_round = (league_settings['num_teams'] - league_settings['draft_position'] + 1)

        # Simulate other teams' picks (remove players by ADP up to my pick)
        num_picks_before_me = (my_pick_in_round - 1) + (league_settings['num_teams'] * (round_num - 1))
        if num_picks_before_me > 0:
            drafted_by_others = available_players.sort_values(by='adp').head(num_picks_before_me)
            available_players = available_players[~available_players['full_name'].isin(drafted_by_others['full_name'])]

        # My turn to pick
        print(f"Your pick in Round {round_num}:")
        
        picked_player = None
        target_pos_type = actual_roster_fill_order[round_num - 1] # Get the position to fill for this round

        # Find the best available player for the target position
        eligible_players = pd.DataFrame()
        if target_pos_type in ['RB', 'WR', 'QB', 'TE', 'K', 'D/ST', 'DP']:
            eligible_players = available_players[available_players['position'] == target_pos_type].sort_values(by='vbd', ascending=False)
        elif target_pos_type == 'RB/WR':
            eligible_players = available_players[available_players['position'].isin(['RB', 'WR'])].sort_values(by='vbd', ascending=False)
        elif target_pos_type == 'WR/TE':
            eligible_players = available_players[available_players['position'].isin(['WR', 'TE'])].sort_values(by='vbd', ascending=False)
        elif target_pos_type == 'BE':
            eligible_players = available_players.sort_values(by='vbd', ascending=False) # For bench, any position

        if not eligible_players.empty:
            picked_player = eligible_players.iloc[0]

        if picked_player is not None:
            print(f"  Recommended Pick: {picked_player['full_name']} ({picked_player['position']}) - Projected Points: {picked_player['projected_points']:.2f}")
            
            # Add player to the team
            my_team[target_pos_type].append(picked_player['full_name'])

            available_players = available_players[available_players['full_name'] != picked_player['full_name']]
            draft_order.append(picked_player['full_name'])
        else:
            print(f"  No suitable player found for {target_pos_type} in this pick based on current logic or player pool.")
            # If a critical spot cannot be filled, we might need to adjust strategy or stop
            break 

    print("\n--- Your Final Simulated Roster ---")
    for pos, players in my_team.items():
        if players:
            print(f"{pos}: {', '.join(players)}")

    # Check if all roster spots are filled (excluding IR for now)
    all_filled = True
    for pos, count in league_settings['roster_settings'].items():
        if pos != 'IR' and len(my_team.get(pos, [])) < count:
            all_filled = False
            break
    if all_filled:
        print("\nAll roster spots have been filled!")
    else:
        pass


def main():
    
    league_settings = load_league_settings(LEAGUE_SETTINGS_PATH)
    player_data = load_player_data(PLAYER_ADP_PATH, PLAYER_PROJECTIONS_PATH)
    player_data = calculate_vbd(player_data, league_settings['roster_settings'], league_settings['scoring_settings'])
    suggest_draft_picks(player_data, league_settings)
    

if __name__ == "__main__":
    main()
