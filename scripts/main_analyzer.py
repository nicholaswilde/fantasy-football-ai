#!/usr/bin/env python3
################################################################################
#
# Script Name: main_analyzer.py
# --------------
# Main entry point for running fantasy football analysis.
#
# @author Nicholas Wilde, 0xb299a622
# @date 29 08 2025
# @version 0.1.0
#
################################################################################

import os
import pandas as pd
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
from scripts.llm import initialize_globals, configure_llm_api, ask_llm
from scripts.data_manager import get_team_roster

# Set up logging
setup_logging(level='INFO', format_type='console', log_file='logs/main_analyzer.log')
logger = get_logger(__name__)

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

def main():
    """Main function to run the fantasy situation analysis and handle errors."""
    import argparse
    parser = argparse.ArgumentParser(description="Analyze a fantasy football situation.")
    parser.add_argument(
        "query",
        help="The user's query or question."
    )
    args = parser.parse_args()

    try:
        analysis_output = analyze_fantasy_situation(args.query)
        if analysis_output:
            print("\n--- AI Analysis ---")
            print(analysis_output)
            print("\n-------------------")
            return 0
        else:
            logger.error("AI analysis returned empty.")
            return 1
    except (ConfigurationError, FileOperationError, DataValidationError, APIError, AuthenticationError, NetworkError) as e:
        logger.error(f"Fantasy situation analysis error: {e.get_detailed_message()}")
        print(f"\n❌ Error during analysis: {e}")
        return 1
    except Exception as e:
        logger.critical(f"An unhandled critical error occurred: {e}", exc_info=True)
        print(f"\n❌ An unexpected critical error occurred: {e}")
        print("Please check the log file for more details.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
