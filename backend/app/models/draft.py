from sqlalchemy import Column, String, Integer, ForeignKey, DateTime, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class Draft(Base):
    """Draft model - draft metadata."""

    __tablename__ = "drafts"

    id = Column(String(50), primary_key=True)  # Sleeper draft ID
    season_id = Column(Integer, ForeignKey("seasons.id"), nullable=False)
    year = Column(Integer, nullable=False)

    # Draft info
    type = Column(String(50))  # snake, linear, auction
    status = Column(String(50))  # pre_draft, drafting, complete
    rounds = Column(Integer)

    # Settings
    settings = Column(JSON)
    draft_order = Column(JSON)  # Slot to roster mapping

    # Timestamps
    start_time = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    season = relationship("Season", back_populates="drafts")
    picks = relationship("DraftPick", back_populates="draft", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Draft {self.year} - {self.type}>"


class DraftPick(Base):
    """DraftPick model - individual draft selections."""

    __tablename__ = "draft_picks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    draft_id = Column(String(50), ForeignKey("drafts.id"), nullable=False)

    # Pick info
    pick_no = Column(Integer, nullable=False)  # Overall pick number
    round = Column(Integer, nullable=False)
    pick_in_round = Column(Integer, nullable=False)
    roster_id = Column(Integer)  # Which roster made the pick

    # Player selected
    player_id = Column(String(50), ForeignKey("players.id"))

    # Additional data
    pick_metadata = Column(JSON)
    picked_at = Column(DateTime)

    # Relationships
    draft = relationship("Draft", back_populates="picks")

    def __repr__(self):
        return f"<DraftPick Round {self.round}, Pick {self.pick_in_round}>"
