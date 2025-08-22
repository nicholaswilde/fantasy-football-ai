#!/usr/bin/env python3
################################################################################
#
# Script Name: analysis.py
# ----------------
# Provides core analytical functions for fantasy football data, including fantasy point calculation, VOR, consistency, and team needs analysis.
#
# @author Nicholas Wilde, 0xb299a622
# @date 21 08 2025
# @version 0.2.3
#
################################################################################

import os
import google.generativeai as genai
import pandas as pd
from dotenv import load_dotenv

import yaml

# Load environment variables from .env file
load_dotenv()

# Load configuration from config.yaml
CONFIG_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', 'config.yaml'
)


def load_config():
    with open(CONFIG_FILE, 'r') as f:
        return yaml.safe_load(f)


CONFIG = load_config()
SCORING_RULES = CONFIG.get('scoring_rules', {})


def configure_api():
    """Configure the Gemini API with the API key."""
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError(
            "API key not found. Please set the GOOGLE_API_KEY "
            "environment variable."
        )
    genai.configure(api_key=api_key)


def ask_gemini(question, model_name):
    """
    Sends a question to the Gemini model and returns the response.
    """
    model = genai.GenerativeModel(model_name)
    response = model.generate_content(question)
    return response.text


def get_team_roster(roster_file="data/my_team.md"):
    """Reads the team roster from a Markdown file and returns a list of player names."""
    if not os.path.exists(roster_file):
        return []
    with open(roster_file, "r") as f:
        # Only include lines that start with '- ' to get player names
        roster = [line.strip().lstrip('- ').strip() for line in f if line.strip().startswith('- ')]
    return roster


def calculate_fantasy_points(df):
    """
    Calculates fantasy points for each player based on the SCORING_RULES in config.yaml.
    """
    df['fantasy_points'] = 0.0

    # Offensive stats
    if 'passing_yards' in df.columns:
        df['fantasy_points'] += (df['passing_yards'] / 25) * SCORING_RULES.get('every_25_passing_yards', 0)
    if 'passing_tds' in df.columns:
        df['fantasy_points'] += df['passing_tds'] * SCORING_RULES.get('td_pass', 0)
    if 'interceptions' in df.columns:
        df['fantasy_points'] += df['interceptions'] * SCORING_RULES.get('interceptions_thrown', 0)
    if 'passing_2pt_conversions' in df.columns:
        df['fantasy_points'] += df['passing_2pt_conversions'] * SCORING_RULES.get('2pt_passing_conversion', 0)

    # Rushing
    if 'rushing_yards' in df.columns:
        df['fantasy_points'] += (df['rushing_yards'] / 10) * SCORING_RULES.get('every_10_rushing_yards', 0)
    if 'rushing_tds' in df.columns:
        df['fantasy_points'] += df['rushing_tds'] * SCORING_RULES.get('td_rush', 0)
    if 'rushing_2pt_conversions' in df.columns:
        df['fantasy_points'] += df['rushing_2pt_conversions'] * SCORING_RULES.get('2pt_rushing_conversion', 0)

    # Receiving
    if 'receiving_yards' in df.columns:
        df['fantasy_points'] += (df['receiving_yards'] / 10) * SCORING_RULES.get('every_10_receiving_yards', 0)
    if 'receiving_tds' in df.columns:
        df['fantasy_points'] += df['receiving_tds'] * SCORING_RULES.get('td_reception', 0)
    if 'receptions' in df.columns:
        df['fantasy_points'] += (df['receptions'] / 5) * SCORING_RULES.get('every_5_receptions', 0)
    if 'receiving_2pt_conversions' in df.columns:
        df['fantasy_points'] += df['receiving_2pt_conversions'] * SCORING_RULES.get('2pt_receiving_conversion', 0)

    # Fumbles
    fumbles_lost = 0
    if 'rushing_fumbles_lost' in df.columns:
        fumbles_lost += df['rushing_fumbles_lost']
    if 'receiving_fumbles_lost' in df.columns:
        fumbles_lost += df['receiving_fumbles_lost']
    df['fantasy_points'] += fumbles_lost * SCORING_RULES.get('total_fumbles_lost', 0)

    # Special Teams (from nfl_data_py)
    if 'special_teams_tds' in df.columns:
        df['fantasy_points'] += df['special_teams_tds'] * SCORING_RULES.get('kickoff_return_td', 0)

    # Kicking Stats (from espn_api)
    if 'position' in df.columns and 'K' in df['position'].unique():
        k_df = df[df['position'] == 'K']
        if 'madeFieldGoalsFrom50Plus' in k_df.columns:
            df.loc[k_df.index, 'fantasy_points'] += k_df['madeFieldGoalsFrom50Plus'] * SCORING_RULES.get('fg_made_(60+_yards)', 0) # Assuming 50+ is 60+
            df.loc[k_df.index, 'fantasy_points'] += k_df['madeFieldGoalsFrom50Plus'] * SCORING_RULES.get('fg_made_(50_59_yards)', 0) # Assuming 50+ is 50-59
        if 'madeFieldGoalsFrom40To49' in k_df.columns:
            df.loc[k_df.index, 'fantasy_points'] += k_df['madeFieldGoalsFrom40To49'] * SCORING_RULES.get('fg_made_(40_49_yards)', 0)
        if 'madeFieldGoalsFromUnder40' in k_df.columns:
            df.loc[k_df.index, 'fantasy_points'] += k_df['madeFieldGoalsFromUnder40'] * SCORING_RULES.get('fg_made_(0_39_yards)', 0)
        if 'missedFieldGoals' in k_df.columns:
            df.loc[k_df.index, 'fantasy_points'] += k_df['missedFieldGoals'] * SCORING_RULES.get('fg_missed_(0_39_yards)', 0) # Assuming all missed FGs are 0-39
        if 'madeExtraPoints' in k_df.columns:
            df.loc[k_df.index, 'fantasy_points'] += k_df['madeExtraPoints'] * SCORING_RULES.get('each_pat_made', 0)
        if 'missedExtraPoints' in k_df.columns:
            df.loc[k_df.index, 'fantasy_points'] += k_df['missedExtraPoints'] * SCORING_RULES.get('each_pat_missed', 0)

    # D/ST Stats (from espn_api)
    if 'position' in df.columns and 'DST' in df['position'].unique():
        dst_df = df[df['position'] == 'DST']
        if 'defensiveSacks' in dst_df.columns:
            df.loc[dst_df.index, 'fantasy_points'] += dst_df['defensiveSacks'] * SCORING_RULES.get('1_2_sack', 0) # Assuming 1 sack is 1 point
        if 'defensiveInterceptions' in dst_df.columns:
            df.loc[dst_df.index, 'fantasy_points'] += dst_df['defensiveInterceptions'] * SCORING_RULES.get('each_interception', 0)
        if 'defensiveFumbles' in dst_df.columns:
            df.loc[dst_df.index, 'fantasy_points'] += dst_df['defensiveFumbles'] * SCORING_RULES.get('each_fumble_recovered', 0)
        if 'defensiveBlockedKicks' in dst_df.columns:
            df.loc[dst_df.index, 'fantasy_points'] += dst_df['defensiveBlockedKicks'] * SCORING_RULES.get('blocked_punt,_pat_or_fg', 0)
        if 'defensiveTouchdowns' in dst_df.columns:
            df.loc[dst_df.index, 'fantasy_points'] += dst_df['defensiveTouchdowns'] * SCORING_RULES.get('defensive_touchdowns', 0) # Assuming a generic defensive TD rule
        if 'defensiveForcedFumbles' in dst_df.columns:
            df.loc[dst_df.index, 'fantasy_points'] += dst_df['defensiveForcedFumbles'] * SCORING_RULES.get('each_fumble_forced', 0)
        if 'defensiveAssistedTackles' in dst_df.columns:
            df.loc[dst_df.index, 'fantasy_points'] += dst_df['defensiveAssistedTackles'] * SCORING_RULES.get('assisted_tackles', 0)
        if 'defensiveSoloTackles' in dst_df.columns:
            df.loc[dst_df.index, 'fantasy_points'] += dst_df['defensiveSoloTackles'] * SCORING_RULES.get('solo_tackles', 0)
        if 'defensivePassesDefensed' in dst_df.columns:
            df.loc[dst_df.index, 'fantasy_points'] += dst_df['defensivePassesDefensed'] * SCORING_RULES.get('passes_defensed', 0)
        if 'defensivePointsAllowed' in dst_df.columns:
            # Apply points allowed scoring based on ranges
            def apply_points_allowed_scoring_dst(row):
                points = 0
                pa = row['defensivePointsAllowed']
                if pa == 0:
                    points += SCORING_RULES.get('0_points_allowed', 0)
                elif 1 <= pa <= 6:
                    points += SCORING_RULES.get('1_6_points_allowed', 0)
                elif 7 <= pa <= 13:
                    points += SCORING_RULES.get('7_13_points_allowed', 0)
                elif 14 <= pa <= 17:
                    points += SCORING_RULES.get('14_17_points_allowed', 0)
                elif 18 <= pa <= 21: # This range is not in config.yaml, but present in ESPN data
                    pass # No points for this range
                elif 22 <= pa <= 27:
                    points += SCORING_RULES.get('22_27_points_allowed', 0)
                elif 28 <= pa <= 34:
                    points += SCORING_RULES.get('28_34_points_allowed', 0)
                elif 35 <= pa <= 45:
                    points += SCORING_RULES.get('35_45_points_allowed', 0)
                elif pa >= 46:
                    points += SCORING_RULES.get('46+_points_allowed', 0)
                return points
            df.loc[dst_df.index, 'fantasy_points'] += dst_df.apply(apply_points_allowed_scoring_dst, axis=1)

        if 'defensiveYardsAllowed' in dst_df.columns:
            # Apply yards allowed scoring based on ranges
            def apply_yards_allowed_scoring_dst(row):
                points = 0
                tya = row['defensiveYardsAllowed']
                if tya < 100:
                    points += SCORING_RULES.get('less_than_100_total_yards_allowed', 0)
                elif 100 <= tya <= 199:
                    points += SCORING_RULES.get('100_199_total_yards_allowed', 0)
                elif 200 <= tya <= 299:
                    points += SCORING_RULES.get('200_299_total_yards_allowed', 0)
                elif 300 <= tya <= 349:
                    points += SCORING_RULES.get('300_349_total_yards_allowed', 0)
                elif 350 <= tya <= 399: # This range is not in config.yaml, but present in ESPN data
                    pass # No points for this range
                elif 400 <= tya <= 449:
                    points += SCORING_RULES.get('400_449_total_yards_allowed', 0)
                elif 450 <= tya <= 499:
                    points += SCORING_RULES.get('450_499_total_yards_allowed', 0)
                elif 500 <= tya <= 549:
                    points += SCORING_RULES.get('500_549_total_yards_allowed', 0)
                elif tya >= 550:
                    points += SCORING_RULES.get('550+_total_yards_allowed', 0)
                return points
            df.loc[dst_df.index, 'fantasy_points'] += dst_df.apply(apply_yards_allowed_scoring_dst, axis=1)

    return df


def get_advanced_draft_recommendations(df):
    """
    Generates advanced draft recommendations based on VOR and consistency.
    Assumes 'fantasy_points' and 'position' columns exist.
    """
    # This function needs player name normalization if it's going to be used for team analysis
    # However, for general draft recommendations, it's fine.
    recommendations = []
    for position in df['position'].unique():
        pos_df = df[df['position'] == position].copy()
        if not pos_df.empty:
            # Calculate VOR (Value Over Replacement)
            # Simple VOR: difference from the average of the top N players (replacement level)
            # N can be adjusted based on league size and roster settings
            # For now, let's assume top 12 for QB, TE, K, D/ST, top 24 for RB/WR
            num_teams = CONFIG.get('league_settings', {}).get('number_of_teams', 12)
            roster_settings = CONFIG.get('roster_settings', {})

            if position == 'QB':
                replacement_level_count = num_teams * roster_settings.get('QB', 1)
            elif position == 'RB':
                replacement_level_count = num_teams * roster_settings.get('RB', 2)
            elif position == 'WR':
                replacement_level_count = num_teams * roster_settings.get('WR', 2)
            elif position == 'TE':
                replacement_level_count = num_teams * roster_settings.get('TE', 1)
            elif position == 'K':
                replacement_level_count = num_teams * roster_settings.get('K', 1)
            elif position == 'DST':
                replacement_level_count = num_teams * roster_settings.get('D_ST', 1)
            else:
                replacement_level_count = num_teams # Default for other positions

            replacement_level_players = pos_df.nlargest(replacement_level_count, 'fantasy_points')

            if not replacement_level_players.empty:
                replacement_level_avg = replacement_level_players['fantasy_points'].mean()
                pos_df['vor'] = pos_df['fantasy_points'] - replacement_level_avg
            else:
                pos_df['vor'] = 0 # No replacement level to compare against

            # Calculate consistency (standard deviation of weekly points)
            # Group by player and calculate standard deviation of fantasy_points
            player_weekly_points = pos_df.groupby(['player_name', 'week'])['fantasy_points'].sum().reset_index()
            consistency_df = player_weekly_points.groupby('player_name')['fantasy_points'].std().reset_index()
            consistency_df.rename(columns={'fantasy_points': 'consistency_std_dev'}, inplace=True)
            pos_df = pd.merge(pos_df, consistency_df, on='player_name', how='left')
            pos_df['consistency_std_dev'] = pos_df['consistency_std_dev'].fillna(0)  # Fill NaN for players with only one week of data

            recommendations.append(pos_df)

    if recommendations:
        return pd.concat(recommendations).sort_values(by='vor', ascending=False)
    return pd.DataFrame()

def analyze_team_needs(team_roster_df, all_players_df):
    """
    Analyzes the team's roster to identify positional needs by comparing VOR to the league average.

    Args:
        team_roster_df (pd.DataFrame): DataFrame of the user's team players with their stats.
        all_players_df (pd.DataFrame): DataFrame with all players and their stats (including VOR).

    Returns:
        str: A markdown-formatted string with the team analysis.
    """
    if team_roster_df.empty:
        # Return an empty DataFrame for positional_breakdown_df if team_roster_df is empty
        return "### Team Analysis\n\nCould not analyze your team because no players from your roster were found in the stats data.\n", pd.DataFrame()

    # Calculate the average VOR for each position in the league for top-tier players
    # Consider players with VOR > 0 to represent above-replacement level players
    league_players = all_players_df[all_players_df['vor'] > 0]
    league_avg_vor = league_players.groupby('position')['vor'].mean().reset_index()
    league_avg_vor.rename(columns={'vor': 'league_avg_vor'}, inplace=True)

    # Calculate the average VOR for the user's team by position
    team_avg_vor = team_roster_df.groupby('position')['vor'].mean().reset_index()
    team_avg_vor.rename(columns={'vor': 'my_team_avg_vor'}, inplace=True)

    # Merge the two to compare
    comparison_df = pd.merge(team_avg_vor, league_avg_vor, on='position', how='left').fillna(0)
    comparison_df['vor_difference'] = comparison_df['my_team_avg_vor'] - comparison_df['league_avg_vor']
    comparison_df = comparison_df.sort_values(by='vor_difference', ascending=True)

    # Build the recommendation string
    analysis_str = "### Team Strengths and Weaknesses\n\n"
    analysis_str += "This analysis compares your team's Value Over Replacement (VOR) at each position against the league average for top-tier players. A positive difference means your players at that position are, on average, more valuable than the league's top players.\n\n"

    strongest_pos = comparison_df.nlargest(1, 'vor_difference')
    if not strongest_pos.empty:
        pos = strongest_pos.iloc[0]['position']
        analysis_str += f"**💪 Strongest Position:** Your **{pos}** group is your team's biggest strength.\n\n"

    weakest_pos = comparison_df.nsmallest(1, 'vor_difference')
    if not weakest_pos.empty:
        pos = weakest_pos.iloc[0]['position']
        analysis_str += f"**🤔 Area for Improvement:** Your **{pos}** group is the most immediate area to upgrade. Consider targeting players at this position.\n\n"

    # Initialize display_df with expected columns
    display_df = pd.DataFrame(columns=['Position', 'My Team Avg VOR', 'League Avg VOR', 'VOR Difference'])

    if not comparison_df.empty:
        display_df = comparison_df[['position', 'my_team_avg_vor', 'league_avg_vor', 'vor_difference']].copy()
        display_df.rename(columns={
            'position': 'Position',
            'my_team_avg_vor': 'My Team Avg VOR',
            'league_avg_vor': 'League Avg VOR',
            'vor_difference': 'VOR Difference'
        }, inplace=True)

    return analysis_str, display_df

def check_bye_week_conflicts(df):
    """
    Checks for bye week conflicts among highly-ranked players.
    Assumes 'bye_week' and 'fantasy_points' columns exist.
    """
    # Consider top N players for conflict checking
    top_players = df.nlargest(50, 'fantasy_points')  # Adjust N as needed

    bye_conflicts = top_players.groupby('bye_week').agg(player_count=('player_name', 'count')).reset_index()
    # Filter for weeks with more than a certain number of top players on bye
    # Threshold can be adjusted based on roster size and league settings
    conflict_threshold = CONFIG.get('analysis_settings', {}).get('bye_week_conflict_threshold', 3)
    conflicts_df = bye_conflicts[bye_conflicts['player_count'] >= conflict_threshold]

    return conflicts_df

def get_trade_recommendations(df, team_roster):
    """
    Suggests potential trade targets based on player value and consistency.
    Filters out players already on the team roster.
    """
    # Filter out players already on my team
    available_players = df[~df['player_name'].isin(team_roster)].copy()

    # Sort by fantasy points or VOR (if calculated) and consistency
    # Prioritize high fantasy points/VOR and good consistency (low std dev)
    if 'vor' in available_players.columns:
        trade_targets = available_players.sort_values(by=['vor', 'consistency_std_dev'], ascending=[False, True])
    else:
        trade_targets = available_players.sort_values(by=['fantasy_points', 'consistency_std_dev'], ascending=[False, True])

    # Return top N trade targets
    num_trade_targets = CONFIG.get('analysis_settings', {}).get('num_trade_targets', 10)
    return trade_targets.head(num_trade_targets)