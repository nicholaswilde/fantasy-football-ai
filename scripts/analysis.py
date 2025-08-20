#!/usr/bin/env python3

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
        # Assuming one player name per line, cleans up markdown list characters and whitespace
        roster = [line.strip().lstrip('- ').strip() for line in f if line.strip()]
    return roster


def calculate_fantasy_points(df):

    """
    Calculates fantasy points for each player based on the SCORING_RULES.
    Assumes the DataFrame contains columns matching common football statistics.
    """
    df['fantasy_points'] = 0.0

    # Offensive stats
    df['fantasy_points'] += (
            df['passing_yards'] * SCORING_RULES.get('passing_yards', 0)
        )
    if 'passing_touchdowns' in df.columns:
        df['fantasy_points'] += (
            df['passing_touchdowns'] * SCORING_RULES.get(
                'passing_touchdowns', 0
            )
        )
    if 'interceptions_thrown' in df.columns:
        df['fantasy_points'] += (
            df['interceptions_thrown'] * SCORING_RULES.get(
                'interceptions_thrown', 0
            )
        )
    if 'rushing_yards' in df.columns:
        df['fantasy_points'] += (
            df['rushing_yards'] * SCORING_RULES.get('rushing_yards', 0)
        )
    if 'rushing_touchdowns' in df.columns:
        df['fantasy_points'] += (
            df['rushing_touchdowns'] * SCORING_RULES.get(
                'rushing_touchdowns', 0
            )
        )
    if 'receiving_yards' in df.columns:
        df['fantasy_points'] += (
            df['receiving_yards'] * SCORING_RULES.get('receiving_yards', 0)
        )
    if 'receiving_touchdowns' in df.columns:
        df['fantasy_points'] += (
            df['receiving_touchdowns'] * SCORING_RULES.get(
                'receiving_touchdowns', 0
            )
        )
    if 'receptions' in df.columns:
        df['fantasy_points'] += (
            df['receptions'] * SCORING_RULES.get('receptions', 0)
        )
    if '2pt_conversion_pass' in df.columns:
        df['fantasy_points'] += (
            df['2pt_conversion_pass'] * SCORING_RULES.get(
                '2pt_conversion_pass', 0
            )
        )
    if '2pt_conversion_rush' in df.columns:
        df['fantasy_points'] += (
            df['2pt_conversion_rush'] * SCORING_RULES.get(
                '2pt_conversion_rush', 0
            )
        )
    if '2pt_conversion_rec' in df.columns:
        df['fantasy_points'] += (
            df['2pt_conversion_rec'] * SCORING_RULES.get(
                '2pt_conversion_rec', 0
            )
        )
    if 'fumbles_lost' in df.columns:
        df['fantasy_points'] += (
            df['fumbles_lost'] * SCORING_RULES.get('fumbles_lost', 0)
        )

    # Kicking stats
    if 'field_goals_made_0_39' in df.columns:
        df['fantasy_points'] += (
            df['field_goals_made_0_39'] * SCORING_RULES.get(
                'field_goals_made_0_39', 0
            )
        )
    if 'field_goals_made_40_49' in df.columns:
        df['fantasy_points'] += (
            df['field_goals_made_40_49'] * SCORING_RULES.get(
                'field_goals_made_40_49', 0
            )
        )
    if 'field_goals_made_50_59' in df.columns:
        df['fantasy_points'] += (
            df['field_goals_made_50_59'] * SCORING_RULES.get(
                'field_goals_made_50_59', 0
            )
        )
    if 'field_goals_made_60_plus' in df.columns:
        df['fantasy_points'] += (
            df['field_goals_made_60_plus'] * SCORING_RULES.get(
                'field_goals_made_60_plus', 0
            )
        )
    if 'field_goals_missed_0_39' in df.columns:
        df['fantasy_points'] += (
            df['field_goals_missed_0_39'] * SCORING_RULES.get(
                'field_goals_missed_0_39', 0
            )
        )
    if 'extra_points_made' in df.columns:
        df['fantasy_points'] += (
            df['extra_points_made'] * SCORING_RULES.get(
                'extra_points_made', 0
            )
        )
    if 'extra_points_missed' in df.columns:
        df['fantasy_points'] += (
            df['extra_points_missed'] * SCORING_RULES.get(
                'extra_points_missed', 0
            )
        )

    # Defensive/ST stats
    if 'sacks' in df.columns:
        df['fantasy_points'] += df['sacks'] * SCORING_RULES.get('sacks', 0)
    if 'interceptions' in df.columns:
        df['fantasy_points'] += (
            df['interceptions'] * SCORING_RULES.get('interceptions', 0)
        )
    if 'fumbles_recovered' in df.columns:
        df['fantasy_points'] += (
            df['fumbles_recovered'] * SCORING_RULES.get(
                'fumbles_recovered', 0
            )
        )
    if 'fumbles_forced' in df.columns:
        df['fantasy_points'] += (
            df['fumbles_forced'] * SCORING_RULES.get('fumbles_forced', 0)
        )
    if 'safeties' in df.columns:
        df['fantasy_points'] += (
            df['safeties'] * SCORING_RULES.get('safeties', 0)
        )
    if 'blocked_kicks' in df.columns:
        df['fantasy_points'] += (
            df['blocked_kicks'] * SCORING_RULES.get('blocked_kicks', 0)
        )
    if 'defensive_touchdowns' in df.columns:
        df['fantasy_points'] += (
            df['defensive_touchdowns'] * SCORING_RULES.get(
                'defensive_touchdowns', 0
            )
        )
    if 'solo_tackles' in df.columns:
        df['fantasy_points'] += (
            df['solo_tackles'] * SCORING_RULES.get('solo_tackles', 0)
        )
    if 'assisted_tackles' in df.columns:
        df['fantasy_points'] += (
            df['assisted_tackles'] * SCORING_RULES.get(
                'assisted_tackles', 0
            )
        )
    if 'passes_defensed' in df.columns:
        df['fantasy_points'] += (
            df['passes_defensed'] * SCORING_RULES.get(
                'passes_defensed', 0
            )
        )
    if 'stuffs' in df.columns:
        df['fantasy_points'] += df['stuffs'] * SCORING_RULES.get('stuffs', 0)
    if 'kickoff_return_touchdowns' in df.columns:
        df['fantasy_points'] += (
            df['kickoff_return_touchdowns'] * SCORING_RULES.get(
                'kickoff_return_touchdowns', 0
            )
        )
    if 'punt_return_touchdowns' in df.columns:
        df['fantasy_points'] += (
            df['punt_return_touchdowns'] * SCORING_RULES.get(
                'punt_return_touchdowns', 0
            )
        )

    # Bonus stats (assuming these are separate columns or can be derived)
    if '40_plus_yard_td_pass_bonus' in df.columns:
        df['fantasy_points'] += (
            df['40_plus_yard_td_pass_bonus'] * SCORING_RULES.get(
                '40_plus_yard_td_pass_bonus', 0
            )
        )
    if '50_plus_yard_td_pass_bonus' in df.columns:
        df['fantasy_points'] += (
            df['50_plus_yard_td_pass_bonus'] * SCORING_RULES.get(
                '50_plus_yard_td_pass_bonus', 0
            )
        )
    if '40_plus_yard_td_rec_bonus' in df.columns:
        df['fantasy_points'] += (
            df['40_plus_yard_td_rec_bonus'] * SCORING_RULES.get(
                '40_plus_yard_td_rec_bonus', 0
            )
        )
    if '50_plus_yard_td_rec_bonus' in df.columns:
        df['fantasy_points'] += (
            df['50_plus_yard_td_rec_bonus'] * SCORING_RULES.get(
                '50_plus_yard_td_rec_bonus', 0
            )
        )
    if '40_plus_yard_td_rush_bonus' in df.columns:
        df['fantasy_points'] += (
            df['40_plus_yard_td_rush_bonus'] * SCORING_RULES.get(
                '40_plus_yard_td_rush_bonus', 0
            )
        )
    if '50_plus_yard_td_rush_bonus' in df.columns:
        df['fantasy_points'] += (
            df['50_plus_yard_td_rush_bonus'] * SCORING_RULES.get(
                '50_plus_yard_td_rush_bonus', 0
            )
        )

    # Yardage game bonuses
    if '100_199_yard_receiving_game' in df.columns:
        df['fantasy_points'] += (
            df['100_199_yard_receiving_game'] * SCORING_RULES.get(
                '100_199_yard_receiving_game', 0
            )
        )
    if '200_plus_yard_receiving_game' in df.columns:
        df['fantasy_points'] += (
            df['200_plus_yard_receiving_game'] * SCORING_RULES.get(
                '200_plus_yard_receiving_game', 0
            )
        )
    if '100_199_yard_rushing_game' in df.columns:
        df['fantasy_points'] += (
            df['100_199_yard_rushing_game'] * SCORING_RULES.get(
                '100_199_yard_rushing_game', 0
            )
        )
    if '200_plus_yard_rushing_game' in df.columns:
        df['fantasy_points'] += (
            df['200_plus_yard_rushing_game'] * SCORING_RULES.get(
                '200_plus_yard_rushing_game', 0
            )
        )
    if '300_399_yard_passing_game' in df.columns:
        df['fantasy_points'] += (
            df['300_399_yard_passing_game'] * SCORING_RULES.get(
                '300_399_yard_passing_game', 0
            )
        )
    if '400_plus_yard_passing_game' in df.columns:
        df['fantasy_points'] += (
            df['400_plus_yard_passing_game'] * SCORING_RULES.get(
                '400_plus_yard_passing_game', 0
            )
        )

    # Return yards
    if 'kickoff_return_yards' in df.columns:
        df['fantasy_points'] += (
            df['kickoff_return_yards'] * SCORING_RULES.get(
                'every_25_kickoff_return_yards', 0
            )
        )
    if 'punt_return_yards' in df.columns:
        df['fantasy_points'] += (
            df['punt_return_yards'] * SCORING_RULES.get(
                'every_25_punt_return_yards', 0
            )
        )

    # Points allowed (D/ST) - This needs careful handling as it's usually a range
    # For simplicity, assuming a 'points_allowed' column and applying the most
    # relevant rule
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
            elif position == 'D/ST':
                replacement_level_count = num_teams * roster_settings.get('DST', 1)
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
        return "### Team Analysis\n\nCould not analyze your team because no players from your roster were found in the stats data.\n"

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
        analysis_str += f"**💪 Strongest Position:** Your **{pos}** group is your team's biggest strength.\n"

    weakest_pos = comparison_df.nsmallest(1, 'vor_difference')
    if not weakest_pos.empty:
        pos = weakest_pos.iloc[0]['position']
        analysis_str += f"**🤔 Area for Improvement:** Your **{pos}** group is the most immediate area to upgrade. Consider targeting players at this position.\n\n"

    analysis_str += "#### Positional Breakdown (VOR vs. League Average)\n\n"
    analysis_str += comparison_df[['position', 'my_team_avg_vor', 'league_avg_vor', 'vor_difference']].to_markdown(index=False, floatfmt=".2f")
    analysis_str += "\n"

    return analysis_str

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