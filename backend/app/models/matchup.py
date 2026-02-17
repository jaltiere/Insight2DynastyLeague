from sqlalchemy import Column, Integer, Float, ForeignKey, String
from sqlalchemy.orm import relationship
from app.database import Base


class Matchup(Base):
    """Matchup model - weekly matchup results."""

    __tablename__ = "matchups"

    id = Column(Integer, primary_key=True, autoincrement=True)
    season_id = Column(Integer, ForeignKey("seasons.id"), nullable=False)
    week = Column(Integer, nullable=False)
    matchup_id = Column(Integer)  # Sleeper matchup ID

    # Home team (roster 1)
    home_roster_id = Column(Integer, ForeignKey("rosters.id"), nullable=False)
    home_points = Column(Float, default=0.0)
    home_starters = Column(String(500))  # JSON string of starter IDs

    # Away team (roster 2)
    away_roster_id = Column(Integer, ForeignKey("rosters.id"), nullable=False)
    away_points = Column(Float, default=0.0)
    away_starters = Column(String(500))  # JSON string of starter IDs

    # Result
    winner_roster_id = Column(Integer, ForeignKey("rosters.id"))
    match_type = Column(String(20), default="regular")  # "regular", "playoff", "consolation"

    # Relationships
    home_roster = relationship("Roster", foreign_keys=[home_roster_id], back_populates="home_matchups")
    away_roster = relationship("Roster", foreign_keys=[away_roster_id], back_populates="away_matchups")

    def __repr__(self):
        return f"<Matchup Week {self.week}: {self.home_points} - {self.away_points}>"
