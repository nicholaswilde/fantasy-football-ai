import pandas as pd
import numpy as np

def generate_dummy_player_data(num_players=300):
    """
    Generates dummy player data for ADP and projections.
    """
    print(f"Generating dummy data for {num_players} players...")

    player_names = [f'Player {i}' for i in range(1, num_players + 1)]
    positions = ['QB', 'RB', 'WR', 'TE', 'K', 'D/ST']
    position_distribution = {
        'QB': 0.1,
        'RB': 0.25,
        'WR': 0.35,
        'TE': 0.1,
        'K': 0.1,
        'D/ST': 0.1
    }

    # Assign positions based on distribution
    player_positions = np.random.choice(
        list(position_distribution.keys()),
        size=num_players,
        p=list(position_distribution.values())
    )

    # Generate ADP (lower ADP for higher-ranked players)
    adp = np.arange(1, num_players + 1)
    np.random.shuffle(adp) # Shuffle to make it less perfectly ordered

    # Generate projected points (higher points for lower ADP, with some randomness)
    projected_points = (num_players - adp + 1) * 2.5 + np.random.normal(0, 20, num_players)
    projected_points = np.maximum(0, projected_points) # Ensure no negative points

    # Create DataFrame for ADP
    adp_df = pd.DataFrame({
        'player_name': player_names,
        'position': player_positions,
        'adp': adp
    })
    adp_df = adp_df.sort_values(by='adp').reset_index(drop=True)

    # Create DataFrame for Projections
    projections_df = pd.DataFrame({
        'player_name': player_names,
        'projected_points': projected_points
    })

    # Save to CSV
    adp_df.to_csv('data/player_adp.csv', index=False)
    projections_df.to_csv('data/player_projections.csv', index=False)

    print("Dummy player_adp.csv and player_projections.csv created in the 'data/' directory.")

if __name__ == "__main__":
    generate_dummy_player_data()
