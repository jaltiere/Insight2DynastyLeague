from sqlalchemy import Column, String, Integer, BigInteger, JSON, DateTime, ForeignKey
from datetime import datetime
from app.database import Base


class Transaction(Base):
    """Transaction model - trade history and waiver claims."""

    __tablename__ = "transactions"

    id = Column(String(50), primary_key=True)  # Sleeper transaction ID
    season_id = Column(Integer, ForeignKey("seasons.id"), nullable=False)
    type = Column(String(50))  # trade, waiver, free_agent
    status = Column(String(50))  # complete, failed

    # Transaction details
    week = Column(Integer)
    roster_ids = Column(JSON)  # List of roster IDs involved
    adds = Column(JSON)  # {player_id: roster_id} for added players
    drops = Column(JSON)  # {player_id: roster_id} for dropped players
    players = Column(JSON)  # Player movements (legacy/raw)
    picks = Column(JSON)  # Draft pick movements
    settings = Column(JSON)  # Additional transaction settings
    waiver_bid = Column(Integer, nullable=True)  # FAAB bid amount
    status_updated = Column(BigInteger, nullable=True)  # Sleeper timestamp (ms)
    metadata_notes = Column(String(500), nullable=True)  # Failure reason or notes

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Transaction {self.type} - Week {self.week}>"
