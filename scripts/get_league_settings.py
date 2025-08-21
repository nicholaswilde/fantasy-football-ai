#!/usr/bin/env python3
################################################################################
#
# Script Name: get_league_settings.py
# ----------------
# Fetches and displays league settings from an ESPN fantasy football league.
#
# @author Nicholas Wilde, 0xb299a622
# @date 2025-08-20
# @version 0.1.0
#
################################################################################

import os
from dotenv import load_dotenv
from espn_api.football import League
import yaml

CONFIG_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', 'config.yaml'
)

def get_league_settings():
    """
    Fetches and saves the settings for the ESPN fantasy football league to config.yaml.
    """
    load_dotenv()

    league_id = os.getenv("LEAGUE_ID")
    espn_s2 = os.getenv("ESPN_S2")
    swid = os.getenv("SWID")

    if not all([league_id, espn_s2, swid]):
        raise ValueError("Please set LEAGUE_ID, ESPN_S2, and SWID environment variables.")

    league = League(league_id=int(league_id), year=2024, espn_s2=espn_s2, swid=swid)

    settings = league.settings

    # Prepare data for YAML output
    config_data = {
        'league_settings': {
            'league_name': settings.name,
            'number_of_teams': settings.team_count,
            'playoff_teams': settings.playoff_team_count
        },
        'roster_settings': {},
        'scoring_rules': {}
    }

    for position, count in sorted(settings.position_slot_counts.items()):
        if count > 0:
            # Normalize position names to match config.yaml conventions if necessary
            # e.g., D/ST -> DST, RB/WR -> RB_WR
            normalized_pos = position.replace('/', '_').upper()
            config_data['roster_settings'][normalized_pos] = count

    for rule in sorted(settings.scoring_format, key=lambda x: x['label']):
        # Normalize scoring rule labels to snake_case for YAML keys
        label = rule['label'].lower().replace(' ', '_').replace('-', '_').replace('/', '_')
        config_data['scoring_rules'][label] = rule['points']

    # Write to config.yaml
    with open(CONFIG_FILE, 'w') as f:
        f.write("---\n") # Ensure the first line is "---" followed by a newline
        yaml.dump(config_data, f, default_flow_style=False, sort_keys=False)

    print(f"Successfully updated {CONFIG_FILE} with league settings.")


if __name__ == "__main__":
    get_league_settings()
