from sqlalchemy import Column, String, Integer, Text, JSON
from sqlalchemy.orm import relationship
from app.database import Base


class League(Base):
    """League model - stores league configuration and settings."""

    __tablename__ = "leagues"

    id = Column(String(50), primary_key=True)  # Sleeper league ID
    name = Column(String(255), nullable=False)
    sport = Column(String(50), default="nfl")
    season = Column(String(10))  # e.g., "2024"
    status = Column(String(50))  # pre_draft, drafting, in_season, complete
    settings = Column(JSON)  # League settings from Sleeper
    scoring_settings = Column(JSON)  # Scoring configuration
    roster_positions = Column(JSON)  # Available roster positions
    league_metadata = Column("metadata", JSON)  # League metadata from Sleeper (division names, etc.)

    # Relationships
    seasons = relationship("Season", back_populates="league", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<League {self.name} ({self.id})>"
