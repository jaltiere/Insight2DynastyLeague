from pydantic import BaseModel
from typing import List, Optional


class PowerRankingTeam(BaseModel):
    """Power ranking for a single team."""
    rank: int
    roster_id: int
    user_id: str
    username: str
    display_name: str
    team_name: Optional[str]
    total_score: float
    current_season_score: float
    roster_value_score: float
    historical_score: float
    wins: int
    losses: int
    ties: int
    points_for: float
    avg_roster_age: float


class PowerRankingsResponse(BaseModel):
    """Response containing all team power rankings."""
    season: int
    rankings: List[PowerRankingTeam]


class PlayerPowerScore(BaseModel):
    """Power score breakdown for an individual player."""
    player_id: str
    player_name: str
    position: str
    team: Optional[str]
    age: Optional[int]
    power_score: float
    age_score: float
    position_score: float
    production_score: float


class RosterBreakdown(BaseModel):
    """Detailed breakdown of a roster's power ranking."""
    roster_id: int
    team_name: Optional[str]
    owner_name: str
    total_roster_score: float
    avg_roster_age: float
    players: List[PlayerPowerScore]
