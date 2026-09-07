
from pydantic import BaseModel, ConfigDict, Field, RootModel


class LeagueSettings(BaseModel):
    league_name: str
    number_of_teams: int
    playoff_teams: int
    year: int
    data_years: list[int]

class RosterSettings(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    BE: int
    D_ST: int = Field(alias="D/ST")
    DP: int
    IR: int
    K: int
    QB: int
    RB: int
    RB_WR: int = Field(alias="RB/WR")
    TE: int
    WR: int
    WR_TE: int = Field(alias="WR/TE")

class ScoringRules(RootModel[dict[str, float]]):
    pass

class LLMSettings(BaseModel):
    provider: str
    model: str
    openai_request_delay: float | None = None

class Config(BaseModel):
    league_settings: LeagueSettings
    roster_settings: RosterSettings
    scoring_rules: ScoringRules
    my_team_id: int | None = None
    llm_settings: LLMSettings
