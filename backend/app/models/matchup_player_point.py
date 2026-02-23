from sqlalchemy import Column, Integer, Float, Boolean, ForeignKey, String
from sqlalchemy.orm import relationship
from app.database import Base


class MatchupPlayerPoint(Base):
    """Individual player scoring per matchup."""

    __tablename__ = "matchup_player_points"

    id = Column(Integer, primary_key=True, autoincrement=True)
    matchup_id = Column(Integer, ForeignKey("matchups.id"), nullable=False)
    roster_id = Column(Integer, ForeignKey("rosters.id"), nullable=False)
    player_id = Column(String(50), nullable=False)  # No FK — Sleeper IDs may not be in players table
    points = Column(Float, default=0.0)
    is_starter = Column(Boolean, default=False)

    # Relationships (lazy="noload" to prevent async lazy-loading errors)
    matchup = relationship("Matchup", lazy="noload")
    roster = relationship("Roster", lazy="noload")

    def __repr__(self):
        return f"<MatchupPlayerPoint {self.player_id}: {self.points}pts>"
