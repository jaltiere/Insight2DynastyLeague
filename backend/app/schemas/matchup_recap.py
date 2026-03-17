from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime


class MatchupRecapResponse(BaseModel):
    """Response schema for a matchup recap."""
    matchup_id: int
    week: int
    season: int
    home_team: str
    away_team: str
    home_score: Optional[float]
    away_score: Optional[float]
    recap_text: Optional[str]
    predictions_text: Optional[str]
    recap_type: str
    recap_metadata: Optional[Dict[str, Any]]
    generated_at: Optional[datetime]

    class Config:
        from_attributes = True


class WeekRecapsResponse(BaseModel):
    """Response containing all recaps for a specific week."""
    week: int
    season: int
    recaps: List[MatchupRecapResponse]


class CurrentWeekMatchupsResponse(BaseModel):
    """Response containing current week matchups with predictions."""
    week: int
    season: int
    matchups: List[MatchupRecapResponse]


class NewsletterRecapResponse(BaseModel):
    """Response formatted for newsletter inclusion."""
    week: int
    season: int
    completed_matchups: List[MatchupRecapResponse]
    upcoming_matchups: List[MatchupRecapResponse]
    summary: Optional[str]

    def to_markdown(self) -> str:
        """Convert recaps to markdown format for newsletter."""
        lines = [f"# Week {self.week} Matchups\n"]

        if self.completed_matchups:
            lines.append("## Last Week's Results\n")
            for recap in self.completed_matchups:
                lines.append(f"### {recap.home_team} vs {recap.away_team}")
                lines.append(f"**Score:** {recap.home_score:.2f} - {recap.away_score:.2f}\n")
                if recap.recap_text:
                    lines.append(f"{recap.recap_text}\n")

        if self.upcoming_matchups:
            lines.append("## This Week's Matchups\n")
            for matchup in self.upcoming_matchups:
                lines.append(f"### {matchup.home_team} vs {matchup.away_team}")
                if matchup.predictions_text:
                    lines.append(f"{matchup.predictions_text}\n")

        return "\n".join(lines)
