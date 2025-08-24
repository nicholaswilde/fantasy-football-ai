#!/usr/bin/env python3
################################################################################
#
# Script Name: analysis.py
# ----------------
# Provides core analytical functions for fantasy football data, including fantasy
# point calculation, VOR, consistency, team needs analysis, and LLM-based insights.
#
# @author Nicholas Wilde, 0xb299a622
# @date 23 08 2025
# @version 0.5.2
#
################################################################################

import os
import google.generativeai as genai
from openai import OpenAI
import pandas as pd
from dotenv import load_dotenv
import yaml
import sys

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from fantasy_ai.errors import (
    FileOperationError,
    DataValidationError,
    ConfigurationError,
    APIError,
    AuthenticationError,
    NetworkError,
    wrap_exception
)
from fantasy_ai.utils.logging import setup_logging, get_logger
from fantasy_ai.utils.retry import retry

# Set up logging
setup_logging(level='INFO', format_type='console', log_file='logs/analysis.log')
logger = get_logger(__name__)

# Load environment variables from .env file
load_dotenv()

# Configuration file path
CONFIG_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), '..', 'config.yaml'
)

# Global variables for configuration and LLM client, initialized later
_CONFIG = None
_SCORING_RULES = None
_LLM_SETTINGS = None
_LLM_PROVIDER = None
_LLM_MODEL = None
_CLIENT = None

def load_config() -> dict:
    """
    Load configuration from config.yaml with proper error handling.
    
    Returns:
        Configuration dictionary
        
    Raises:
        ConfigurationError: If config file cannot be read or parsed
        FileOperationError: If file cannot be accessed
    """
    try:
        logger.debug(f"Loading configuration from {CONFIG_FILE}")
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        if not isinstance(config, dict):
            raise ConfigurationError(
                "Configuration file does not contain a valid dictionary",
                config_file=CONFIG_FILE
            )
        
        logger.info("Configuration loaded successfully")
        return config
        
    except FileNotFoundError as e:
        raise ConfigurationError(
            f"Configuration file not found: {CONFIG_FILE}. Please run 'task init' first.",
            config_file=CONFIG_FILE,
            original_error=e
        )
    except yaml.YAMLError as e:
        raise ConfigurationError(
            f"Invalid YAML in configuration file: {CONFIG_FILE}",
            config_file=CONFIG_FILE,
            original_error=e
        )
    except PermissionError as e:
        raise FileOperationError(
            f"Permission denied reading configuration file: {CONFIG_FILE}",
            file_path=CONFIG_FILE,
            operation="read",
            original_error=e
        )
    except Exception as e:
        raise wrap_exception(
            e, ConfigurationError,
            f"Failed to load configuration from {CONFIG_FILE}",
            config_file=CONFIG_FILE
        )


def initialize_globals():
    """
    Initializes global configuration and LLM settings.
    This function should be called once at the application's entry point.
    """
    global _CONFIG, _SCORING_RULES, _LLM_SETTINGS, _LLM_PROVIDER, _LLM_MODEL, _CLIENT
    _CONFIG = load_config()
    _SCORING_RULES = _CONFIG.get('scoring_rules', {})
    _LLM_SETTINGS = _CONFIG.get('llm_settings', {})
    _LLM_PROVIDER = _LLM_SETTINGS.get('provider', 'google')
    _LLM_MODEL = _LLM_SETTINGS.get('model', 'gemini-pro')
    _CLIENT = None # Reset client

def configure_llm_api():
    """
    Configure the LLM API based on the provider with error handling.
    Assumes _LLM_PROVIDER, _LLM_MODEL, and _CLIENT globals are initialized.
    """
    global _CLIENT
    if _LLM_PROVIDER is None:
        raise ConfigurationError("LLM provider not initialized. Call initialize_globals() first.")

    try:
        if _LLM_PROVIDER == 'google':
            api_key = os.getenv("GOOGLE_API_KEY")
            if not api_key:
                raise AuthenticationError(
                    "Google API key not found. Please set the GOOGLE_API_KEY environment variable.",
                    api_name="Google Gemini"
                )
            genai.configure(api_key=api_key)
            logger.info("Google Gemini API configured.")
        elif _LLM_PROVIDER == 'openai':
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise AuthenticationError(
                    "OpenAI API key not found. Please set the OPENAI_API_KEY environment variable.",
                    api_name="OpenAI"
                )
            _CLIENT = OpenAI(api_key=api_key)
            logger.info("OpenAI API configured.")
        else:
            raise ConfigurationError(
                f"Unsupported LLM provider: {_LLM_PROVIDER}",
                config_key="llm_settings.provider"
            )
    except Exception as e:
        raise wrap_exception(
            e, ConfigurationError,
            f"Failed to configure LLM API for provider {_LLM_PROVIDER}"
        )


@retry(
    max_attempts=3,
    base_delay=1.0,
    backoff_factor=2.0
)
def ask_llm(question: str) -> str:
    """
    Sends a question to the configured LLM and returns the response with error handling.
    Assumes _LLM_PROVIDER, _LLM_MODEL, and _CLIENT globals are initialized.
    
    Raises:
        APIError: If there's an issue with the LLM API response.
        NetworkError: If there's a network connectivity issue.
        AuthenticationError: If LLM client is not configured or API key is invalid.
    """
    if _LLM_PROVIDER is None:
        raise ConfigurationError("LLM provider not initialized. Call initialize_globals() first.")

    try:
        logger.debug(f"Asking LLM: {question[:50]}...")
        if _LLM_PROVIDER == 'google':
            model = genai.GenerativeModel(_LLM_MODEL)
            response = model.generate_content(question)
            if not response.text:
                raise APIError("LLM returned an empty response.", api_name=_LLM_PROVIDER)
            logger.info("Received response from Google Gemini.")
            return response.text
        elif _LLM_PROVIDER == 'openai':
            if not _CLIENT:
                raise AuthenticationError("OpenAI client not configured.", api_name="OpenAI")
            response = _CLIENT.chat.completions.create(
                model=_LLM_MODEL,
                messages=[{"role": "user", "content": question}]
            )
            if not response.choices or not response.choices[0].message.content:
                raise APIError("LLM returned an empty response.", api_name=_LLM_PROVIDER)
            logger.info("Received response from OpenAI.")
            return response.choices[0].message.content.strip()
        else:
            raise ConfigurationError(f"Unsupported LLM provider: {_LLM_PROVIDER}")
    except (genai.types.BlockedPromptException, genai.types.HarmCategory) as e:
        raise APIError(f"LLM prompt blocked due to safety concerns: {e}", api_name=_LLM_PROVIDER, original_error=e)
    except (genai.types.APIError, OpenAI.APIError) as e:
        raise APIError(f"LLM API error: {e}", api_name=_LLM_PROVIDER, original_error=e)
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
        raise NetworkError(f"Network error during LLM API call: {e}", api_name=_LLM_PROVIDER, original_error=e)
    except Exception as e:
        raise wrap_exception(e, APIError, f"An unexpected error occurred during LLM API call: {e}", api_name=_LLM_PROVIDER)


def get_team_roster(roster_file: str = None) -> list:
    """
    Reads the team roster from a Markdown table file and returns a list of player names with error handling.
    
    Args:
        roster_file: Path to the my_team.md file. If None, uses default path.
        
    Returns:
        List of player names.
        
    Raises:
        FileOperationError: If the file cannot be read or accessed.
        DataValidationError: If the file content is malformed.
    """
    if roster_file is None:
        roster_file = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'my_team.md'
        )
    
    if not os.path.exists(roster_file):
        logger.warning(f"Roster file not found at {roster_file}, returning empty roster.")
        return []
    
    roster = []
    try:
        with open(roster_file, "r", encoding='utf-8') as f:
            lines = f.readlines()
            # Skip header and separator lines (first 3 lines after the comment and title)
            # So, actual data starts from line 5 (index 4)
            if len(lines) > 4:
                for line in lines[4:]:
                    line = line.strip()
                    if line.startswith('|') and '|' in line[1:]:
                        parts = [p.strip() for p in line.split('|')]
                        if len(parts) > 2: # Ensure there's at least a player name column
                            player_name = parts[1] # Assuming player name is in the second column
                            if player_name: # Ensure it's not empty
                                roster.append(player_name)
        logger.info(f"Successfully loaded {len(roster)} players from roster file.")
        return roster
    except FileNotFoundError as e:
        raise FileOperationError(
            f"Roster file not found: {roster_file}",
            file_path=roster_file,
            operation="read",
            original_error=e
        )
    except PermissionError as e:
        raise FileOperationError(
            f"Permission denied reading roster file: {roster_file}",
            file_path=roster_file,
            operation="read",
            original_error=e
        )
    except UnicodeDecodeError as e:
        raise DataValidationError(
            f"Cannot decode roster file (encoding issue): {roster_file}",
            field_name="roster_file_encoding",
            expected_type="UTF-8 encoded text",
            actual_value="unreadable encoding",
            original_error=e
        )
    except Exception as e:
        raise wrap_exception(
            e, FileOperationError,
            f"Failed to read roster file {roster_file}",
            file_path=roster_file,
            operation="read"
        )


def analyze_fantasy_situation(user_query: str) -> str:
    """
    Generates fantasy football analysis by providing rich context to an LLM with error handling.
    
    Args:
        user_query: The question or scenario from the user.
        
    Returns:
        LLM-generated analysis.
        
    Raises:
        FileOperationError: If data files cannot be read.
        DataValidationError: If data files are malformed or empty.
        ConfigurationError: If LLM or scoring rules are misconfigured.
        APIError: If LLM API call fails.
        AuthenticationError: If LLM API key is missing.
        NetworkError: If there's a network issue during LLM API call.
    """
    logger.info(f"Analyzing fantasy situation for query: {user_query[:50]}...")
    # 1. Load all necessary data
    try:
        # Use the global _CONFIG which should be initialized
        if _CONFIG is None:
            initialize_globals()
        config = _CONFIG
        scoring_rules = _SCORING_RULES
        roster_settings = config.get('roster_settings', {})
    except ConfigurationError:
        raise # Re-raise configuration errors
    except Exception as e:
        raise wrap_exception(e, ConfigurationError, "Failed to load configuration for analysis.")

    data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')

    try:
        player_stats_df = pd.read_csv(os.path.join(data_dir, 'player_stats.csv'), low_memory=False)
    except FileNotFoundError as e:
        raise FileOperationError(
            f"player_stats.csv not found at {data_dir}. Please run data download scripts.",
            file_path=os.path.join(data_dir, 'player_stats.csv'),
            operation="read",
            original_error=e
        )
    except pd.errors.EmptyDataError as e:
        raise DataValidationError(
            f"player_stats.csv is empty or invalid: {e}",
            field_name="player_stats.csv",
            original_error=e
        )
    except pd.errors.ParserError as e:
        raise DataValidationError(
            f"Cannot parse player_stats.csv: {e}",
            field_name="player_stats.csv",
            original_error=e
        )
    except Exception as e:
        raise wrap_exception(e, FileOperationError, f"Failed to read player_stats.csv: {e}")

    try:
        player_adp_df = pd.read_csv(os.path.join(data_dir, 'player_adp.csv'), low_memory=False)
    except (FileNotFoundError, pd.errors.EmptyDataError, pd.errors.ParserError) as e:
        logger.warning(f"Could not load player_adp.csv: {e}, proceeding without ADP data.")
        player_adp_df = pd.DataFrame()

    try:
        player_projections_df = pd.read_csv(os.path.join(data_dir, 'player_projections.csv'), low_memory=False)
    except (FileNotFoundError, pd.errors.EmptyDataError, pd.errors.ParserError) as e:
        logger.warning(f"Could not load player_projections.csv: {e}, proceeding without projections data.")
        player_projections_df = pd.DataFrame()

    try:
        available_players_df = pd.read_csv(os.path.join(data_dir, 'available_players.csv'), low_memory=False)
    except (FileNotFoundError, pd.errors.EmptyDataError, pd.errors.ParserError) as e:
        logger.warning(f"Could not load available_players.csv: {e}, proceeding without available players data.")
        available_players_df = pd.DataFrame()

    try:
        my_team_roster = get_team_roster()
    except (FileOperationError, DataValidationError) as e:
        logger.warning(f"Failed to load my team roster: {e}, proceeding with empty roster.")
        my_team_roster = []

    # 2. Process and format the data for the prompt
    scoring_rules_str = yaml.dump(_SCORING_RULES, default_flow_style=False)
    roster_settings_str = yaml.dump(roster_settings, default_flow_style=False)

    # Get top available players
    if not available_players_df.empty:
        top_available_players = available_players_df['player_name'].head(15).tolist()
        top_available_players_str = "\n".join(top_available_players)
    else:
        top_available_players = []
        top_available_players_str = "Not available."

    # Filter player_stats_df to include only relevant players
    relevant_players = my_team_roster + top_available_players
    if relevant_players:
        relevant_stats_df = player_stats_df[player_stats_df['player_name'].isin(relevant_players)].copy()
    else:
        relevant_stats_df = player_stats_df.copy()

    # Merge stats with ADP and projections
    if not player_adp_df.empty:
        relevant_stats_df = pd.merge(relevant_stats_df, player_adp_df, on='player_name', how='left')
    if not player_projections_df.empty:
        relevant_stats_df = pd.merge(relevant_stats_df, player_projections_df, on='player_name', how='left')

    # 3. Construct the prompt
    my_team_roster_str = "- " + "\n- ".join(my_team_roster)
    prompt = f"""
You are a fantasy football expert. Analyze the following situation based on the provided league context.

**League Context:**

**1. Scoring Rules:**
```yaml
{scoring_rules_str}
```

**2. Roster Settings:**
```yaml
{roster_settings_str}
```

**3. My Team Roster:**
{my_team_roster_str}

**4. Top Available Players (Waiver Wire):**
{top_available_players_str}

**5. Player Data (Stats, ADP, Projections):**
Here is a summary of relevant player data:
{relevant_stats_df.to_string()}

**User's Question:**
{user_query}

Provide a detailed analysis and actionable recommendations.
"""

    # 4. Ask the LLM
    configure_llm_api()
    return ask_llm(prompt)


def calculate_fantasy_points(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculates fantasy points for each player based on the _SCORING_RULES.
    
    Args:
        df: DataFrame with player statistics.
        
    Returns:
        DataFrame with an added 'fantasy_points' column.
        
    Raises:
        DataValidationError: If required columns for scoring are missing.
    """
    if df.empty:
        logger.warning("Input DataFrame for calculate_fantasy_points is empty.")
        return df

    df['fantasy_points'] = 0.0

    # Define a helper to safely get column data
    def get_col(col_name):
        if col_name not in df.columns:
            logger.debug(f"Column '{col_name}' not found in DataFrame for fantasy points calculation.")
            return pd.Series(0.0, index=df.index) # Return a series of zeros if column is missing
        return df[col_name]

    # Offensive stats
    df['fantasy_points'] += (get_col('passing_yards') / 25) * _SCORING_RULES.get('every_25_passing_yards', 0)
    df['fantasy_points'] += get_col('passing_tds') * _SCORING_RULES.get('td_pass', 0)
    df['fantasy_points'] += get_col('interceptions') * _SCORING_RULES.get('interceptions_thrown', 0)
    df['fantasy_points'] += get_col('passing_2pt_conversions') * _SCORING_RULES.get('2pt_passing_conversion', 0)

    # Rushing
    df['fantasy_points'] += (get_col('rushing_yards') / 10) * _SCORING_RULES.get('every_10_rushing_yards', 0)
    df['fantasy_points'] += get_col('rushing_tds') * _SCORING_RULES.get('td_rush', 0)
    df['fantasy_points'] += get_col('rushing_2pt_conversions') * _SCORING_RULES.get('2pt_rushing_conversion', 0)

    # Receiving
    df['fantasy_points'] += (get_col('receiving_yards') / 10) * _SCORING_RULES.get('every_10_receiving_yards', 0)
    df['fantasy_points'] += (get_col('receptions') / 5) * _SCORING_RULES.get('every_5_receptions', 0)
    df['fantasy_points'] += get_col('receiving_tds') * _SCORING_RULES.get('td_reception', 0)
    df['fantasy_points'] += get_col('receiving_2pt_conversions') * _SCORING_RULES.get('2pt_receiving_conversion', 0)

    # Offensive Bonuses
    # Passing Bonuses
    if 'passing_td_yards' in df.columns:
        df.loc[get_col('passing_td_yards') >= 50, 'fantasy_points'] += _SCORING_RULES.get('50+_yard_td_pass_bonus', 0)
        df.loc[get_col('passing_td_yards') >= 40, 'fantasy_points'] += _SCORING_RULES.get('40+_yard_td_pass_bonus', 0)
    if 'passing_yards' in df.columns:
        df.loc[(get_col('passing_yards') >= 300) & (get_col('passing_yards') < 400), 'fantasy_points'] += _SCORING_RULES.get('300_399_yard_passing_game', 0)
        df.loc[get_col('passing_yards') >= 400, 'fantasy_points'] += _SCORING_RULES.get('400+_yard_passing_game', 0)

    # Rushing Bonuses
    if 'rushing_td_yards' in df.columns:
        df.loc[get_col('rushing_td_yards') >= 50, 'fantasy_points'] += _SCORING_RULES.get('50+_yard_td_rush_bonus', 0)
        df.loc[get_col('rushing_td_yards') >= 40, 'fantasy_points'] += _SCORING_RULES.get('40+_yard_td_rush_bonus', 0)
    if 'rushing_yards' in df.columns:
        df.loc[(get_col('rushing_yards') >= 100) & (get_col('rushing_yards') < 200), 'fantasy_points'] += _SCORING_RULES.get('100_199_yard_rushing_game', 0)
        df.loc[get_col('rushing_yards') >= 200, 'fantasy_points'] += _SCORING_RULES.get('200+_yard_rushing_game', 0)

    # Receiving Bonuses
    if 'receiving_td_yards' in df.columns:
        df.loc[get_col('receiving_td_yards') >= 50, 'fantasy_points'] += _SCORING_RULES.get('50+_yard_td_rec_bonus', 0)
        df.loc[get_col('receiving_td_yards') >= 40, 'fantasy_points'] += _SCORING_RULES.get('40+_yard_td_rec_bonus', 0)
    if 'receiving_yards' in df.columns:
        df.loc[(get_col('receiving_yards') >= 100) & (get_col('receiving_yards') < 200), 'fantasy_points'] += _SCORING_RULES.get('100_199_yard_receiving_game', 0)
        df.loc[get_col('receiving_yards') >= 200, 'fantasy_points'] += _SCORING_RULES.get('200+_yard_receiving_game', 0)

    # Fumbles
    fumbles_lost = get_col('rushing_fumbles_lost') + get_col('receiving_fumbles_lost')
    df['fantasy_points'] += fumbles_lost * _SCORING_RULES.get('total_fumbles_lost', 0)

    # Special Teams (from nfl_data_py)
    df['fantasy_points'] += get_col('special_teams_tds') * _SCORING_RULES.get('kickoff_return_td', 0)
    df['fantasy_points'] += get_col('2pt_return') * _SCORING_RULES.get('2pt_return', 0)

    # Kicking Stats (from espn_api)
    if 'position' in df.columns and 'K' in df['position'].unique():
        k_df = df[df['position'] == 'K']
        df.loc[k_df.index, 'fantasy_points'] += get_col('madeFieldGoalsFrom50Plus') * _SCORING_RULES.get('fg_made_(50_59_yards)', 0)
        df.loc[k_df.index, 'fantasy_points'] += get_col('madeFieldGoalsFrom40To49') * _SCORING_RULES.get('fg_made_(40_49_yards)', 0)
        df.loc[k_df.index, 'fantasy_points'] += get_col('madeFieldGoalsFromUnder40') * _SCORING_RULES.get('fg_made_(0_39_yards)', 0)
        df.loc[k_df.index, 'fantasy_points'] += get_col('missedFieldGoals') * _SCORING_RULES.get('fg_missed_(0_39_yards)', 0)
        df.loc[k_df.index, 'fantasy_points'] += get_col('madeExtraPoints') * _SCORING_RULES.get('each_pat_made', 0)
        df.loc[k_df.index, 'fantasy_points'] += get_col('missedExtraPoints') * _SCORING_RULES.get('each_pat_missed', 0)

    # D/ST Stats (from espn_api)
    if 'position' in df.columns and 'DST' in df['position'].unique():
        dst_df = df[df['position'] == 'DST']
        df.loc[dst_df.index, 'fantasy_points'] += get_col('defensiveSacks') * _SCORING_RULES.get('1_2_sack', 0)
        df.loc[dst_df.index, 'fantasy_points'] += get_col('defensiveInterceptions') * _SCORING_RULES.get('each_interception', 0)
        df.loc[dst_df.index, 'fantasy_points'] += get_col('defensiveFumbles') * _SCORING_RULES.get('each_fumble_recovered', 0)
        df.loc[dst_df.index, 'fantasy_points'] += get_col('defensiveBlockedKicks') * _SCORING_RULES.get('blocked_punt,_pat_or_fg', 0)
        df.loc[dst_df.index, 'fantasy_points'] += get_col('defensiveTouchdowns') * _SCORING_RULES.get('defensive_touchdowns', 0)
        df.loc[dst_df.index, 'fantasy_points'] += get_col('defensiveForcedFumbles') * _SCORING_RULES.get('each_fumble_forced', 0)
        df.loc[dst_df.index, 'fantasy_points'] += get_col('defensiveAssistedTackles') * _SCORING_RULES.get('assisted_tackles', 0)
        df.loc[dst_df.index, 'fantasy_points'] += get_col('defensiveSoloTackles') * _SCORING_RULES.get('solo_tackles', 0)
        df.loc[dst_df.index, 'fantasy_points'] += get_col('defensivePassesDefensed') * _SCORING_RULES.get('passes_defensed', 0)
        if 'defensivePointsAllowed' in dst_df.columns:
            # Apply points allowed scoring based on ranges
            def apply_points_allowed_scoring_dst(row):
                points = 0
                pa = row['defensivePointsAllowed']
                if pa == 0:
                    points += _SCORING_RULES.get('0_points_allowed', 0)
                elif 1 <= pa <= 6:
                    points += _SCORING_RULES.get('1_6_points_allowed', 0)
                elif 7 <= pa <= 13:
                    points += _SCORING_RULES.get('7_13_points_allowed', 0)
                elif 14 <= pa <= 17:
                    points += _SCORING_RULES.get('14_17_points_allowed', 0)
                elif 18 <= pa <= 21:
                    pass
                elif 22 <= pa <= 27:
                    points += _SCORING_RULES.get('22_27_points_allowed', 0)
                elif 28 <= pa <= 34:
                    points += _SCORING_RULES.get('28_34_points_allowed', 0)
                elif 35 <= pa <= 45:
                    points += _SCORING_RULES.get('35_45_points_allowed', 0)
                elif pa >= 46:
                    points += _SCORING_RULES.get('46+_points_allowed', 0)
                return points
            df.loc[dst_df.index, 'fantasy_points'] += dst_df.apply(apply_points_allowed_scoring_dst, axis=1)

        if 'defensiveYardsAllowed' in dst_df.columns:
            # Apply yards allowed scoring based on ranges
            def apply_yards_allowed_scoring_dst(row):
                points = 0
                tya = row['defensiveYardsAllowed']
                if tya < 100:
                    points += _SCORING_RULES.get('less_than_100_total_yards_allowed', 0)
                elif 100 <= tya <= 199:
                    points += _SCORING_RULES.get('100_199_total_yards_allowed', 0)
                elif 200 <= tya <= 299:
                    points += _SCORING_RULES.get('200_299_total_yards_allowed', 0)
                elif 300 <= tya <= 349:
                    points += _SCORING_RULES.get('300_349_total_yards_allowed', 0)
                elif 350 <= tya <= 399:
                    pass
                elif 400 <= tya <= 449:
                    points += _SCORING_RULES.get('400_449_total_yards_allowed', 0)
                elif 450 <= tya <= 499:
                    points += _SCORING_RULES.get('450_499_total_yards_allowed', 0)
                elif 500 <= tya <= 549:
                    points += _SCORING_RULES.get('500_549_total_yards_allowed', 0)
                elif tya >= 550:
                    points += _SCORING_RULES.get('550+_total_yards_allowed', 0)
                return points
            df.loc[dst_df.index, 'fantasy_points'] += dst_df.apply(apply_yards_allowed_scoring_dst, axis=1)

    df['fantasy_points_ppr'] = df['fantasy_points']
    return df


def get_advanced_draft_recommendations(df: pd.DataFrame) -> pd.DataFrame:
    """
    Generates advanced draft recommendations based on VOR and consistency.
    Assumes 'fantasy_points' and 'position' columns exist.
    
    Args:
        df: DataFrame with player statistics and fantasy points.
        
    Returns:
        DataFrame with VOR and consistency metrics.
        
    Raises:
        DataValidationError: If required columns are missing or data is invalid.
    """
    if df.empty:
        logger.warning("Input DataFrame for get_advanced_draft_recommendations is empty.")
        return pd.DataFrame()

    required_cols = ['fantasy_points', 'position', 'player_name', 'week']
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise DataValidationError(
            f"Missing required columns for draft recommendations: {missing_cols}",
            field_name="player_stats_columns",
            expected_type=f"columns: {required_cols}",
            actual_value=f"missing: {missing_cols}"
        )

    recommendations = []
    try:
        num_teams = _CONFIG.get('league_settings', {}).get('number_of_teams', 12)
        roster_settings = _CONFIG.get('roster_settings', {})

        for position in df['position'].unique():
            pos_df = df[df['position'] == position].copy()
            if pos_df.empty:
                continue

            # Calculate total fantasy points for each player in this position
            player_total_points = pos_df.groupby('player_name')['fantasy_points'].sum().reset_index()
            player_total_points.rename(columns={'fantasy_points': 'total_fantasy_points'}, inplace=True)

            replacement_level_count = 0
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
                replacement_level_count = num_teams

            if replacement_level_count == 0:
                logger.warning(f"Replacement level count is 0 for position {position}, skipping VOR calculation.")
                # Create a basic DataFrame for this position with default VOR and consistency
                temp_rec_df = pos_df[['player_name', 'position']].drop_duplicates().copy()
                temp_rec_df['vor'] = 0.0
                temp_rec_df['consistency_std_dev'] = 0.0
                recommendations.append(temp_rec_df)
                continue

            # Select replacement level players based on total fantasy points
            replacement_level_players = player_total_points.nlargest(replacement_level_count, 'total_fantasy_points')

            if not replacement_level_players.empty:
                replacement_level_avg = replacement_level_players['total_fantasy_points'].mean()
                # Calculate VOR for each player based on their total fantasy points
                player_total_points['vor'] = player_total_points['total_fantasy_points'] - replacement_level_avg
            else:
                player_total_points['vor'] = 0.0

            # Calculate consistency (std dev of weekly points) using the original pos_df
            player_weekly_points = pos_df.groupby(['player_name', 'week'])['fantasy_points'].sum().reset_index()
            consistency_df = player_weekly_points.groupby('player_name')['fantasy_points'].std().reset_index()
            consistency_df.rename(columns={'fantasy_points': 'consistency_std_dev'}, inplace=True)
            consistency_df['consistency_std_dev'] = consistency_df['consistency_std_dev'].fillna(0.0)

            # Merge VOR and consistency into a single DataFrame for recommendations
            # Start with player_name and position from pos_df (unique players)
            rec_df = pos_df[['player_name', 'position']].drop_duplicates().copy()
            rec_df = pd.merge(rec_df, player_total_points[['player_name', 'vor']], on='player_name', how='left')
            rec_df = pd.merge(rec_df, consistency_df, on='player_name', how='left')

            recommendations.append(rec_df)

    except KeyError as e:
        raise DataValidationError(
            f"Missing expected key in configuration or data: {e}",
            original_error=e
        )

    if recommendations:
        return pd.concat(recommendations).sort_values(by='vor', ascending=False)
    return pd.DataFrame()


def analyze_team_needs(team_roster_df: pd.DataFrame, all_players_df: pd.DataFrame) -> tuple[str, pd.DataFrame]:
    """
    Analyzes the team's roster to identify positional needs by comparing VOR to the league average.

    Args:
        team_roster_df (pd.DataFrame): DataFrame of the user's team players with their stats.
        all_players_df (pd.DataFrame): DataFrame with all players and their stats (including VOR).

    Returns:
        tuple[str, pd.DataFrame]: A markdown-formatted string with the team analysis and a DataFrame
                                   with positional breakdown.
                                   
    Raises:
        DataValidationError: If input DataFrames are missing required columns or data is invalid.
    """
    if team_roster_df.empty:
        logger.warning("Input team_roster_df for analyze_team_needs is empty.")
        return ("### Team Analysis\n\nCould not analyze your team because no players from your roster were found in the stats data.\n", pd.DataFrame())

    required_cols_team = ['player_name', 'position', 'vor']
    missing_cols_team = [col for col in required_cols_team if col not in team_roster_df.columns]
    if missing_cols_team:
        raise DataValidationError(
            f"Missing required columns in team_roster_df for team needs analysis: {missing_cols_team}",
            field_name="team_roster_df_columns",
            expected_type=f"columns: {required_cols_team}",
            actual_value=f"missing: {missing_cols_team}"
        )

    required_cols_all = ['position', 'vor']
    missing_cols_all = [col for col in required_cols_all if col not in all_players_df.columns]
    if missing_cols_all:
        raise DataValidationError(
            f"Missing required columns in all_players_df for team needs analysis: {missing_cols_all}",
            field_name="all_players_df_columns",
            expected_type=f"columns: {required_cols_all}",
            actual_value=f"missing: {missing_cols_all}"
        )
    try:
        # Calculate the average VOR for each position in the league for top-tier players
        league_players = all_players_df[all_players_df['vor'] > 0]
        if league_players.empty:
            logger.warning("No top-tier players found in all_players_df for league average VOR calculation.")
            return ("### Team Analysis\n\nCould not analyze league average VOR due to insufficient data.\n", pd.DataFrame())

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
        analysis_str = "### Team Strengths and Weaknesses\n\nThis analysis compares your team's Value Over Replacement (VOR) at each position against the league average for top-tier players. A positive difference means your players at that position are, on average, more valuable than the league's top players.\n\n"

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
    except KeyError as e:
        raise DataValidationError(
            f"Missing expected key in DataFrame for team needs analysis: {e}",
            original_error=e
        )



def check_bye_week_conflicts(df: pd.DataFrame) -> pd.DataFrame:
    """
    Checks for bye week conflicts among highly-ranked players.
    Assumes 'bye_week' and 'fantasy_points' columns exist.
    
    Args:
        df: DataFrame with player statistics including 'bye_week' and 'fantasy_points'.
        
    Returns:
        DataFrame with bye week conflicts.
        
    Raises:
        DataValidationError: If required columns are missing.
    """
    if df.empty:
        logger.warning("Input DataFrame for check_bye_week_conflicts is empty.")
        return pd.DataFrame()

    required_cols = ['bye_week', 'fantasy_points', 'player_name']
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise DataValidationError(
            f"Missing required columns for bye week conflict check: {missing_cols}",
            field_name="player_stats_columns",
            expected_type=f"columns: {required_cols}",
            actual_value=f"missing: {missing_cols}"
        )
    try:
        top_players = df.nlargest(50, 'fantasy_points')

        if top_players.empty:
            logger.warning("No top players found for bye week conflict check.")
            return pd.DataFrame()

        bye_conflicts = top_players.groupby('bye_week').agg(player_count=('player_name', 'count')).reset_index()
        conflict_threshold = _CONFIG.get('analysis_settings', {}).get('bye_week_conflict_threshold', 3)
        conflicts_df = bye_conflicts[bye_conflicts['player_count'] >= conflict_threshold]

        return conflicts_df
    except KeyError as e:
        raise DataValidationError(
            f"Missing expected key in DataFrame for bye week conflict check: {e}",
            original_error=e
        )


def get_trade_recommendations(df: pd.DataFrame, team_roster: list) -> pd.DataFrame:
    """
    Suggests potential trade targets based on player value and consistency.
    Filters out players already on the team roster.
    
    Args:
        df: DataFrame with player statistics and VOR/consistency metrics.
        team_roster: List of player names on the user's team.
        
    Returns:
        DataFrame with trade recommendations.
        
    Raises:
        DataValidationError: If input DataFrame is missing required columns.
    """
    if df.empty:
        logger.warning("Input DataFrame for get_trade_recommendations is empty.")
        return pd.DataFrame()

    required_cols = ['player_name', 'vor', 'consistency_std_dev']
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise DataValidationError(
            f"Missing required columns for trade recommendations: {missing_cols}",
            field_name="player_stats_columns",
            expected_type=f"columns: {required_cols}",
            actual_value=f"missing: {missing_cols}"
        )
    try:
        available_players = df[~df['player_name'].isin(team_roster)].copy()

        if available_players.empty:
            logger.warning("No available players for trade recommendations after filtering team roster.")
            return pd.DataFrame()

        if 'vor' in available_players.columns and 'consistency_std_dev' in available_players.columns:
            trade_targets = available_players.sort_values(by=['vor', 'consistency_std_dev'], ascending=[False, True])
        else:
            logger.warning("VOR or consistency_std_dev not available for sorting trade targets, falling back to fantasy_points.")
            if 'fantasy_points' not in available_players.columns:
                raise DataValidationError(
                    "Neither VOR, consistency_std_dev, nor fantasy_points available for sorting trade targets.",
                    field_name="player_stats_columns",
                    expected_type="at least one of VOR, consistency_std_dev, fantasy_points",
                    actual_value="none available"
                )
            trade_targets = available_players.sort_values(by=['fantasy_points'], ascending=[False])

        num_trade_targets = _CONFIG.get('analysis_settings', {}).get('num_trade_targets', 10)

        # Ensure all necessary columns are present in the returned DataFrame
        required_display_cols = ['player_name', 'position', 'recent_team', 'vor', 'consistency_std_dev', 'fantasy_points_ppr', 'bye_week']
        for col in required_display_cols:
            if col not in trade_targets.columns:
                trade_targets[col] = None # Add missing columns with None or appropriate default

        return trade_targets[required_display_cols].head(num_trade_targets)
    except KeyError as e:
        raise DataValidationError(
            f"Missing expected key in DataFrame for trade recommendations: {e}",
            original_error=e
        )
