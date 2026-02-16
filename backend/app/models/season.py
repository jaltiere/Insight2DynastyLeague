from sqlalchemy import Column, String, Integer, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.database import Base


class Season(Base):
    """Season model - tracks season metadata and structure."""

    __tablename__ = "seasons"

    id = Column(Integer, primary_key=True, autoincrement=True)
    league_id = Column(String(50), ForeignKey("leagues.id"), nullable=False)
    year = Column(Integer, nullable=False)
    num_divisions = Column(Integer, default=2)  # Changed from 4 to 2
    playoff_structure = Column(JSON)  # Playoff bracket configuration
    regular_season_weeks = Column(Integer, default=14)
    playoff_weeks = Column(Integer, default=3)

    # Relationships
    league = relationship("League", back_populates="seasons")
    rosters = relationship("Roster", back_populates="season", cascade="all, delete-orphan")
    awards = relationship("SeasonAward", back_populates="season", cascade="all, delete-orphan")
    drafts = relationship("Draft", back_populates="season", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Season {self.year} - {self.num_divisions} divisions>"
