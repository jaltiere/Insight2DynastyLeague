from sqlalchemy import Column, String, Integer, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.database import Base


class Roster(Base):
    """Roster model - team rosters by season."""

    __tablename__ = "rosters"

    id = Column(Integer, primary_key=True, autoincrement=True)
    roster_id = Column(Integer, nullable=False)  # Sleeper roster ID
    season_id = Column(Integer, ForeignKey("seasons.id"), nullable=False)
    user_id = Column(String(50), ForeignKey("users.id"))

    # Team info
    team_name = Column(String(255))
    division = Column(Integer)

    # Stats
    wins = Column(Integer, default=0)
    losses = Column(Integer, default=0)
    ties = Column(Integer, default=0)
    points_for = Column(Integer, default=0)
    points_against = Column(Integer, default=0)

    # Player IDs
    players = Column(JSON)  # List of player IDs on roster
    starters = Column(JSON)  # List of starter positions
    reserve = Column(JSON)  # List of reserve/bench positions
    taxi = Column(JSON)  # Taxi squad

    # Settings
    settings = Column(JSON)  # Roster settings from Sleeper

    # Relationships
    season = relationship("Season", back_populates="rosters")
    user = relationship("User", back_populates="rosters")
    home_matchups = relationship("Matchup", foreign_keys="Matchup.home_roster_id", back_populates="home_roster")
    away_matchups = relationship("Matchup", foreign_keys="Matchup.away_roster_id", back_populates="away_roster")

    def __repr__(self):
        return f"<Roster {self.team_name} ({self.wins}-{self.losses})>"
