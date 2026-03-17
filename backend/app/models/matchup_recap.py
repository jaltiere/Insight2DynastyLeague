from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class MatchupRecap(Base):
    """Matchup recap model - AI-generated recaps and predictions for matchups."""

    __tablename__ = "matchup_recaps"

    id = Column(Integer, primary_key=True, autoincrement=True)
    matchup_id = Column(Integer, ForeignKey("matchups.id", ondelete="CASCADE"), nullable=False)
    recap_text = Column(Text, nullable=True)  # Generated recap for completed matchups
    predictions_text = Column(Text, nullable=True)  # Generated prediction for upcoming matchups
    generated_at = Column(DateTime, server_default=func.current_timestamp(), nullable=False)
    week = Column(Integer, nullable=False)
    season_id = Column(Integer, ForeignKey("seasons.id", ondelete="CASCADE"), nullable=False)
    recap_type = Column(String(20), server_default="weekly", nullable=False)  # 'weekly', 'playoff', 'prediction'
    recap_metadata = Column(JSON, nullable=True)  # Standings deltas, H2H history, playoff implications

    # Relationships
    matchup = relationship("Matchup", back_populates="recaps")
    season = relationship("Season")

    def __repr__(self):
        return f"<MatchupRecap Week {self.week} - {self.recap_type}>"
