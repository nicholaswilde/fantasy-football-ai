#!/usr/bin/env python3

import os
import google.generativeai as genai
import pandas as pd
from dotenv import load_dotenv
import argparse
import yaml

# Load environment variables from .env file
load_dotenv()

# Load configuration from config.yaml
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'config.yaml')


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
    """Reads the team roster from the specified file."""
    if not os.path.exists(roster_file):
        return None
    with open(roster_file, "r") as f:
        roster = f.read()
    return roster

def calculate_fantasy_points(df):

    """
    Calculates fantasy points for each player based on the SCORING_RULES.
    Assumes the DataFrame contains columns matching common football statistics.
    """
    df['fantasy_points'] = 0.0

    # Offensive stats
    if 'passing_yards' in df.columns:
        df['fantasy_points'] += df['passing_yards'] * SCORING_RULES.get('passing_yards', 0)
    if 'passing_touchdowns' in df.columns:
        df['fantasy_points'] += df['passing_touchdowns'] * SCORING_RULES.get('passing_touchdowns', 0)
    if 'interceptions_thrown' in df.columns:
        df['fantasy_points'] += df['interceptions_thrown'] * SCORING_RULES.get('interceptions_thrown', 0)
    if 'rushing_yards' in df.columns:
        df['fantasy_points'] += df['rushing_yards'] * SCORING_RULES.get('rushing_yards', 0)
    if 'rushing_touchdowns' in df.columns:
        df['fantasy_points'] += df['rushing_touchdowns'] * SCORING_RULES.get('rushing_touchdowns', 0)
    if 'receiving_yards' in df.columns:
        df['fantasy_points'] += df['receiving_yards'] * SCORING_RULES.get('receiving_yards', 0)
    if 'receiving_touchdowns' in df.columns:
        df['fantasy_points'] += df['receiving_touchdowns'] * SCORING_RULES.get('receiving_touchdowns', 0)
    if 'receptions' in df.columns:
        df['fantasy_points'] += df['receptions'] * SCORING_RULES.get('receptions', 0)
    if '2pt_conversion_pass' in df.columns:
        df['fantasy_points'] += df['2pt_conversion_pass'] * SCORING_RULES.get('2pt_conversion_pass', 0)
    if '2pt_conversion_rush' in df.columns:
        df['fantasy_points'] += df['2pt_conversion_rush'] * SCORING_RULES.get('2pt_conversion_rush', 0)
    if '2pt_conversion_rec' in df.columns:
        df['fantasy_points'] += df['2pt_conversion_rec'] * SCORING_RULES.get('2pt_conversion_rec', 0)
    if 'fumbles_lost' in df.columns:
        df['fantasy_points'] += df['fumbles_lost'] * SCORING_RULES.get('fumbles_lost', 0)

    # Kicking stats
    if 'field_goals_made_0_39' in df.columns:
        df['fantasy_points'] += df['field_goals_made_0_39'] * SCORING_RULES.get('field_goals_made_0_39', 0)
    if 'field_goals_made_40_49' in df.columns:
        df['fantasy_points'] += df['field_goals_made_40_49'] * SCORING_RULES.get('field_goals_made_40_49', 0)
    if 'field_goals_made_50_59' in df.columns:
        df['fantasy_points'] += df['field_goals_made_50_59'] * SCORING_RULES.get('field_goals_made_50_59', 0)
    if 'field_goals_made_60_plus' in df.columns:
        df['fantasy_points'] += df['field_goals_made_60_plus'] * SCORING_RULES.get('field_goals_made_60_plus', 0)
    if 'field_goals_missed_0_39' in df.columns:
        df['fantasy_points'] += df['field_goals_missed_0_39'] * SCORING_RULES.get('field_goals_missed_0_39', 0)
    if 'extra_points_made' in df.columns:
        df['fantasy_points'] += df['extra_points_made'] * SCORING_RULES.get('extra_points_made', 0)
    if 'extra_points_missed' in df.columns:
        df['fantasy_points'] += df['extra_points_missed'] * SCORING_RULES.get('extra_points_missed', 0)

    # Defensive/ST stats
    if 'sacks' in df.columns:
        df['fantasy_points'] += df['sacks'] * SCORING_RULES.get('sacks', 0)
    if 'interceptions' in df.columns:
        df['fantasy_points'] += df['interceptions'] * SCORING_RULES.get('interceptions', 0)
    if 'fumbles_recovered' in df.columns:
        df['fantasy_points'] += df['fumbles_recovered'] * SCORING_RULES.get('fumbles_recovered', 0)
    if 'fumbles_forced' in df.columns:
        df['fantasy_points'] += df['fumbles_forced'] * SCORING_RULES.get('fumbles_forced', 0)
    if 'safeties' in df.columns:
        df['fantasy_points'] += df['safeties'] * SCORING_RULES.get('safeties', 0)
    if 'blocked_kicks' in df.columns:
        df['fantasy_points'] += df['blocked_kicks'] * SCORING_RULES.get('blocked_kicks', 0)
    if 'defensive_touchdowns' in df.columns:
        df['fantasy_points'] += df['defensive_touchdowns'] * SCORING_RULES.get('defensive_touchdowns', 0)
    if 'solo_tackles' in df.columns:
        df['fantasy_points'] += df['solo_tackles'] * SCORING_RULES.get('solo_tackles', 0)
    if 'assisted_tackles' in df.columns:
        df['fantasy_points'] += df['assisted_tackles'] * SCORING_RULES.get('assisted_tackles', 0)
    if 'passes_defensed' in df.columns:
        df['fantasy_points'] += df['passes_defensed'] * SCORING_RULES.get('passes_defensed', 0)
    if 'stuffs' in df.columns:
        df['fantasy_points'] += df['stuffs'] * SCORING_RULES.get('stuffs', 0)
    if 'kickoff_return_touchdowns' in df.columns:
        df['fantasy_points'] += df['kickoff_return_touchdowns'] * SCORING_RULES.get('kickoff_return_touchdowns', 0)
    if 'punt_return_touchdowns' in df.columns:
        df['fantasy_points'] += df['punt_return_touchdowns'] * SCORING_RULES.get('punt_return_touchdowns', 0)

    # Bonus stats (assuming these are separate columns or can be derived)
    if '40_plus_yard_td_pass_bonus' in df.columns:
        df['fantasy_points'] += df['40_plus_yard_td_pass_bonus'] * SCORING_RULES.get('40_plus_yard_td_pass_bonus', 0)
    if '50_plus_yard_td_pass_bonus' in df.columns:
        df['fantasy_points'] += df['50_plus_yard_td_pass_bonus'] * SCORING_RULES.get('50_plus_yard_td_pass_bonus', 0)
    if '40_plus_yard_td_rec_bonus' in df.columns:
        df['fantasy_points'] += df['40_plus_yard_td_rec_bonus'] * SCORING_RULES.get('40_plus_yard_td_rec_bonus', 0)
    if '50_plus_yard_td_rec_bonus' in df.columns:
        df['fantasy_points'] += df['50_plus_yard_td_rec_bonus'] * SCORING_RULES.get('50_plus_yard_td_rec_bonus', 0)
    if '40_plus_yard_td_rush_bonus' in df.columns:
        df['fantasy_points'] += df['40_plus_yard_td_rush_bonus'] * SCORING_RULES.get('40_plus_yard_td_rush_bonus', 0)
    if '50_plus_yard_td_rush_bonus' in df.columns:
        df['fantasy_points'] += df['50_plus_yard_td_rush_bonus'] * SCORING_RULES.get('50_plus_yard_td_rush_bonus', 0)

    # Yardage game bonuses
    if '100_199_yard_receiving_game' in df.columns:
        df['fantasy_points'] += df['100_199_yard_receiving_game'] * SCORING_RULES.get('100_199_yard_receiving_game', 0)
    if '200_plus_yard_receiving_game' in df.columns:
        df['fantasy_points'] += df['200_plus_yard_receiving_game'] * SCORING_RULES.get('200_plus_yard_receiving_game', 0)
    if '100_199_yard_rushing_game' in df.columns:
        df['fantasy_points'] += df['100_199_yard_rushing_game'] * SCORING_RULES.get('100_199_yard_rushing_game', 0)
    if '200_plus_yard_rushing_game' in df.columns:
        df['fantasy_points'] += df['200_plus_yard_rushing_game'] * SCORING_RULES.get('200_plus_yard_rushing_game', 0)
    if '300_399_yard_passing_game' in df.columns:
        df['fantasy_points'] += df['300_399_yard_passing_game'] * SCORING_RULES.get('300_399_yard_passing_game', 0)
    if '400_plus_yard_passing_game' in df.columns:
        df['fantasy_points'] += df['400_plus_yard_passing_game'] * SCORING_RULES.get('400_plus_yard_passing_game', 0)

    # Return yards
    if 'kickoff_return_yards' in df.columns:
        df['fantasy_points'] += df['kickoff_return_yards'] * SCORING_RULES.get('every_25_kickoff_return_yards', 0)
    if 'punt_return_yards' in df.columns:
        df['fantasy_points'] += df['punt_return_yards'] * SCORING_RULES.get('every_25_punt_return_yards', 0)

    # Points allowed (D/ST) - This needs careful handling as it's usually a range
    # For simplicity, assuming a 'points_allowed' column and applying the most relevant rule
    def apply_points_allowed_scoring(row):
        points = 0
        if 'points_allowed' in row:
            pa = row['points_allowed']
            if pa == 0:
                points += SCORING_RULES.get('points_allowed_0', 0)
            elif 1 <= pa <= 6:
                points += SCORING_RULES.get('points_allowed_1_6', 0)
            elif 7 <= pa <= 13:
                points += SCORING_RULES.get('points_allowed_7_13', 0)
            elif 14 <= pa <= 17:
                points += SCORING_RULES.get('points_allowed_14_17', 0)
            elif 22 <= pa <= 27:
                points += SCORING_RULES.get('points_allowed_22_27', 0)
            elif 28 <= pa <= 34:
                points += SCORING_RULES.get('points_allowed_28_34', 0)
            elif 35 <= pa <= 45:
                points += SCORING_RULES.get('points_allowed_35_45', 0)
            elif pa >= 46:
                points += SCORING_RULES.get('points_allowed_46_plus', 0)
        return points

    if 'points_allowed' in df.columns:
        df['fantasy_points'] += df.apply(apply_points_allowed_scoring, axis=1)

    # Total yards allowed (D/ST) - Similar to points allowed
    def apply_yards_allowed_scoring(row):
        points = 0
        if 'total_yards_allowed' in row:
            tya = row['total_yards_allowed']
            if tya < 100:
                points += SCORING_RULES.get('total_yards_allowed_less_100', 0)
            elif 100 <= tya <= 199:
                points += SCORING_RULES.get('total_yards_allowed_100_199', 0)
            elif 200 <= tya <= 299:
                points += SCORING_RULES.get('total_yards_allowed_200_299', 0)
            elif 300 <= tya <= 349:
                points += SCORING_RULES.get('total_yards_allowed_300_349', 0)
            elif 400 <= tya <= 449:
                points += SCORING_RULES.get('total_yards_allowed_400_449', 0)
            elif 450 <= tya <= 499:
                points += SCORING_RULES.get('total_yards_allowed_450_499', 0)
            elif 500 <= tya <= 549:
                points += SCORING_RULES.get('total_yards_allowed_500_549', 0)
            elif tya >= 550:
                points += SCORING_RULES.get('total_yards_allowed_550_plus', 0)
        return points

    if 'total_yards_allowed' in df.columns:
        df['fantasy_points'] += df.apply(apply_yards_allowed_scoring, axis=1)

    # Add a placeholder bye_week column for demonstration purposes
    # In a real scenario, this data would come from a reliable source
    if 'week' in df.columns:
        df['bye_week'] = df['week'].apply(lambda x: (x % 14) + 4) # Simple placeholder for bye week
    else:
        df['bye_week'] = 0 # Default if no week column

    return df

def get_advanced_draft_recommendations(df):
    """
    Generates advanced draft recommendations based on VOR and consistency.
    Assumes 'fantasy_points' and 'position' columns exist.
    """
    recommendations = []
    for position in df['position'].unique():
        pos_df = df[df['position'] == position].copy()
        if not pos_df.empty:
            # Calculate VOR (Value Over Replacement)
            # Simple VOR: difference from the average of the top N players (replacement level)
            # N can be adjusted based on league size and roster settings
            # For now, let's assume top 12 for QB, TE, K, D/ST, top 24 for RB/WR
            if position in ['QB', 'TE', 'K', 'D/ST']:
                replacement_level_players = pos_df.nlargest(12, 'fantasy_points')
            elif position in ['RB', 'WR']:
                replacement_level_players = pos_df.nlargest(24, 'fantasy_points')
            else: # For other positions or if not enough data, use a simpler approach
                replacement_level_players = pos_df.nlargest(min(len(pos_df), 12), 'fantasy_points') # Take top 12 or all if less than 12

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
            pos_df['consistency_std_dev'] = pos_df['consistency_std_dev'].fillna(0) # Fill NaN for players with only one week of data

            recommendations.append(pos_df)

    if recommendations:
        return pd.concat(recommendations).sort_values(by='vor', ascending=False)
    return pd.DataFrame()

def check_bye_week_conflicts(df):
    """
    Checks for bye week conflicts among highly-ranked players.
    Assumes 'bye_week' and 'fantasy_points' columns exist.
    """
    # Consider top N players for conflict checking
    top_players = df.nlargest(50, 'fantasy_points') # Adjust N as needed

    bye_conflicts = top_players.groupby('bye_week').agg(player_count=('player_name', 'count')).reset_index()
    # Filter for weeks with more than a certain number of top players on bye
    # Threshold can be adjusted based on roster size and league settings
    conflict_threshold = 3 # Example: more than 3 top players on bye in the same week
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
    return trade_targets.head(10) # Adjust N as needed

