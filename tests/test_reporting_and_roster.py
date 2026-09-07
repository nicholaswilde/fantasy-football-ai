"""
Tests for reporting and compare_roster_positions features.
"""

import pandas as pd

from fantasy_football_ai.compare_roster_positions import compare_roster_positions
from fantasy_football_ai.reporting import (
    generate_markdown_report,
    generate_terminal_report,
    get_team_name,
)


def test_get_team_name_existing(tmp_path):
    roster_file = tmp_path / "my_team.md"
    roster_file.write_text("# My Team: The Champions\n\n| Player | Pos |\n")
    assert get_team_name(str(roster_file)) == "The Champions"


def test_get_team_name_non_existent():
    assert get_team_name("/non/existent/path.md") == "My Team"


def test_compare_roster_positions_formats(tmp_path):
    config_file = tmp_path / "config.yaml"
    config_file.write_text("roster_settings:\n  QB: 1\n  RB: 2\n")

    roster_file = tmp_path / "my_team.md"
    roster_file.write_text(
        "# My Team: Test\n\n"
        "| Player Name | Position | NFL Team |\n"
        "|:---|:---|:---|\n"
        "| Patrick Mahomes | QB | KC |\n"
        "| Christian McCaffrey | RB | SF |\n"
    )

    # Test fancy_grid format (terminal)
    comp_grid, _mismatches_grid = compare_roster_positions(str(config_file), str(roster_file), tablefmt="fancy_grid")
    assert "╒" in comp_grid  # fancy_grid border
    assert "Position" not in [line.split()[1] for line in comp_grid.splitlines() if "MISMATCH" in line]

    # Test github format (markdown)
    comp_gh, _mismatches_gh = compare_roster_positions(str(config_file), str(roster_file), tablefmt="github")
    assert "|" in comp_gh


def test_reporting_truncation_and_team_name(capsys):
    # Prepare dummy DataFrames
    draft_recs_df = pd.DataFrame({
        'player_name': [f"Player {i}" for i in range(10)],
        'recent_team': ['KC'] * 10,
        'position': ['QB'] * 10,
        'vor': [10.0 - i for i in range(10)],
        'consistency_std_dev': [1.0] * 10,
    })
    bye_conflicts_df = pd.DataFrame()
    trade_recs_df = pd.DataFrame({
        'player_name': [f"Trade {i}" for i in range(15)],
        'position': ['WR'] * 15,
        'recent_team': ['SF'] * 15,
        'vor': [5.0] * 15,
        'consistency_std_dev': [2.0] * 15,
        'fantasy_points_ppr': [20.0] * 15,
        'bye_week': [7] * 15,
    })
    sell_high_df = pd.DataFrame({
        'player_display_name': [f"Sell {i}" for i in range(10)],
        'position': ['RB'] * 10,
        'recent_team': ['BUF'] * 10,
        'fantasy_points': [25.0] * 10,
        'avg_fantasy_points': [10.0] * 10,
        'point_difference': [15.0] * 10,
    })
    buy_low_df = pd.DataFrame({
        'player_display_name': [f"Buy {i}" for i in range(10)],
        'position': ['TE'] * 10,
        'recent_team': ['DAL'] * 10,
        'fantasy_points': [2.0] * 10,
        'avg_fantasy_points': [12.0] * 10,
        'point_difference': [-10.0] * 10,
    })
    positional_breakdown_df = pd.DataFrame()
    my_team_df = pd.DataFrame({
        'player_name': ['Player A', 'Player B'],
        'recent_team': ['KC', 'SF'],
        'position': ['QB', 'RB'],
        'vor': [5.0, 4.0],
        'consistency_std_dev': [1.0, 1.5],
    })
    waiver_gems_df = pd.DataFrame({
        'player_display_name': [f"Gem {i}" for i in range(10)],
        'position': ['WR'] * 10,
        'recent_team': ['MIA'] * 10,
        'recent_ppr_avg': [12.0] * 10,
        'season_ppr_avg': [11.0] * 10,
        'recent_targets_avg': [8.0] * 10,
        'recent_carries_avg': [0.0] * 10,
        'target_share': [0.25] * 10,
        'air_yards_share': [0.30] * 10,
    })

    # Test markdown report includes team name
    report_md = generate_markdown_report(
        draft_recs_df, bye_conflicts_df, trade_recs_df, "Team Analysis",
        ['Player A'], sell_high_df, buy_low_df, {}, [], positional_breakdown_df,
        "comp_table", "", "Last Game", "Next Game", my_team_df, waiver_gems_df,
        team_name="The Child"
    )
    assert "## My Team Analysis (The Child)" in report_md
    # Check that truncated tables only contain up to 5 items
    assert "Trade 0" in report_md
    assert "Trade 4" in report_md
    assert "Trade 5" not in report_md

    # Test terminal report includes team name
    generate_terminal_report(
        draft_recs_df, bye_conflicts_df, trade_recs_df, "Team Analysis",
        ['Player A'], sell_high_df, buy_low_df, positional_breakdown_df,
        "comp_table", "", "Last Game", "Next Game", my_team_df, waiver_gems_df,
        team_name="The Child"
    )
    captured = capsys.readouterr()
    assert "--- My Team Analysis (The Child) ---" in captured.out
