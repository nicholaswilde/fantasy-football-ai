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
# @version 1.2.0
#
################################################################################

import yaml
import re
from tabulate import tabulate

def compare_roster_positions(config_path, my_team_path):
    """
    Compares the number of positions in config.yaml roster_settings with the
    actual number of positions in data/my_team.md.

    Args:
        config_path (str): The path to the config.yaml file.
        my_team_path (str): The path to the my_team.md file.

    Returns:
        tuple: A tuple containing the main comparison table and the mismatch summary table.
    """
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    expected_roster = config.get('roster_settings', {})

    with open(my_team_path, 'r') as f:
        my_team_content = f.read()

    actual_roster = {}
    position_map = {
        'QB': 'QB', 'RB': 'RB', 'WR': 'WR', 'TE': 'TE', 'K': 'K',
        'DST': 'D_ST', 'BENCH': 'BE', 'DP': 'DP', 'IR': 'IR',
        'RB/WR': 'RB_WR', 'WR/TE': 'WR_TE',
    }

    position_pattern = re.compile(r'##\s+([A-Z/]+)\s*\((\d+)\)')
    lines = my_team_content.split('\n')
    current_position_raw = None
    for line in lines:
        match = position_pattern.match(line)
        if match:
            current_position_raw = match.group(1)
            current_position_mapped = position_map.get(current_position_raw, current_position_raw)
            actual_roster[current_position_mapped] = 0
        elif line.strip().startswith('- ') and current_position_raw:
            current_position_mapped = position_map.get(current_position_raw, current_position_raw)
            actual_roster[current_position_mapped] += 1

    headers = ["Position", "Expected", "Actual", "Status"]
    table_data = []
    mismatches = []
    all_positions = sorted(list(set(expected_roster.keys()) | set(actual_roster.keys())))

    for position in all_positions:
        expected_count = expected_roster.get(position, 0)
        actual_count = actual_roster.get(position, 0)
        status = "OK" if expected_count == actual_count else "MISMATCH"
        table_data.append([position, expected_count, actual_count, status])
        if status == "MISMATCH":
            mismatches.append([position, expected_count, actual_count])

    comparison_table = tabulate(table_data, headers=headers, tablefmt="github")
    mismatch_table = ""
    if mismatches:
        mismatch_headers = ["Position", "Expected", "Actual"]
        mismatch_table = tabulate(mismatches, headers=mismatch_headers, tablefmt="github")

    return comparison_table, mismatch_table


if __name__ == "__main__":
    CONFIG_FILE = "/home/nicholas/git/nicholaswilde/fantasy-football-ai/config.yaml"
    MY_TEAM_FILE = "/home/nicholas/git/nicholaswilde/fantasy-football-ai/data/my_team.md"
    comparison, mismatches = compare_roster_positions(CONFIG_FILE, MY_TEAM_FILE)
    print("\nRoster Comparison:")
    print(comparison)
    if mismatches:
        print("\nSummary of Mismatches:")
        print(mismatches)
