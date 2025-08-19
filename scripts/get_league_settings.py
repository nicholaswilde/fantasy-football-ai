import os
from dotenv import load_dotenv
from espn_api.football import League

def get_league_settings():
    """
    Fetches and prints the settings for the ESPN fantasy football league.
    """
    load_dotenv()

    league_id = os.getenv("LEAGUE_ID")
    espn_s2 = os.getenv("ESPN_S2")
    swid = os.getenv("SWID")

    if not all([league_id, espn_s2, swid]):
        raise ValueError("Please set LEAGUE_ID, ESPN_S2, and SWID environment variables.")

    league = League(league_id=int(league_id), year=2024, espn_s2=espn_s2, swid=swid)

    settings = league.settings
    settings = league.settings
    print("League Name:", settings.name)
    print("Number of Teams:", settings.team_count)
    print("Playoff Teams:", settings.playoff_team_count)

    print("\nScoring Settings:")
    for rule in sorted(settings.scoring_format, key=lambda x: x['label']):
        print(f"- {rule['label']}: {rule['points']}")

    print("\nRoster Settings:")
    for position, count in sorted(settings.position_slot_counts.items()):
        if count > 0:
            print(f"- {position}: {count}")


if __name__ == "__main__":
    get_league_settings()
