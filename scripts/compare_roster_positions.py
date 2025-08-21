#!/usr/bin/env python3
################################################################################
#
# Script Name: compare_roster_positions.py
# ----------------
# Compares the number of positions in config.yaml roster_settings with the
# actual number of positions in data/my_team.md.
#
# @author Nicholas Wilde, 0xb299a622
# @date 21 August 2025
# @version 1.0.0
#
################################################################################

import yaml
import re

def compare_roster_positions(config_path, my_team_path):
    """
    Compares the number of positions in config.yaml roster_settings with the
    actual number of positions in data/my_team.md.

    Args:
        config_path (str): The path to the config.yaml file.
        my_team_path (str): The path to the my_team.md file.
    """
    # Read config.yaml
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    expected_roster = config.get('roster_settings', {})

    # Read my_team.md
    with open(my_team_path, 'r') as f:
        my_team_content = f.read()

    actual_roster = {}
    # Mapping from my_team.md position names to config.yaml position names
    position_map = {
        'QB': 'QB',
        'RB': 'RB',
        'WR': 'WR',
        'TE': 'TE',
        'K': 'K',
        'DST': 'D_ST',
        'BENCH': 'BE',
        'DP': 'DP', # Assuming DP might appear in my_team.md
        'IR': 'IR',   # Assuming IR might appear in my_team.md
        'RB/WR': 'RB_WR', # Assuming RB/WR might appear in my_team.md
        'WR/TE': 'WR_TE', # Assuming WR/TE might appear in my_team.md
    }

    # Regex to find position headers like "## QB (2)"
    # It captures the position name and the number in parentheses
    position_pattern = re.compile(r'##\s+([A-Z/]+)\s*\((\d+)\)')
    
    # Split the content by lines and iterate to find positions and players
    lines = my_team_content.split('\n')
    current_position_raw = None
    for line in lines:
        match = position_pattern.match(line)
        if match:
            current_position_raw = match.group(1)
            # Map the raw position name to the config.yaml equivalent
            current_position_mapped = position_map.get(current_position_raw, current_position_raw)
            actual_roster[current_position_mapped] = 0
        elif line.strip().startswith('- ') and current_position_raw:
            current_position_mapped = position_map.get(current_position_raw, current_position_raw)
            actual_roster[current_position_mapped] += 1

    print("Roster Comparison:")
    print("------------------")

    all_positions = sorted(list(set(expected_roster.keys()) | set(actual_roster.keys())))

    for position in all_positions:
        expected_count = expected_roster.get(position, 0)
        actual_count = actual_roster.get(position, 0)

        if expected_count == actual_count:
            print(f"  {position}: OK (Expected: {expected_count}, Actual: {actual_count})")
        else:
            print(f"  {position}: MISMATCH (Expected: {expected_count}, Actual: {actual_count})")

    print("\nSummary:")
    mismatches = {pos: (expected_roster.get(pos, 0), actual_roster.get(pos, 0))
                  for pos in all_positions if expected_roster.get(pos, 0) != actual_roster.get(pos, 0)}

    if not mismatches:
        print("All roster positions match the configuration.")
    else:
        print("Mismatches found in the following positions:")
        for pos, (expected, actual) in mismatches.items():
            print(f"- {pos}: Expected {expected}, Actual {actual}")

if __name__ == "__main__":
    CONFIG_FILE = "/home/nicholas/git/nicholaswilde/fantasy-football-ai/config.yaml"
    MY_TEAM_FILE = "/home/nicholas/git/nicholaswilde/fantasy-football-ai/data/my_team.md"
    compare_roster_positions(CONFIG_FILE, MY_TEAM_FILE)
