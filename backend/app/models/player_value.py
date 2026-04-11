from sqlalchemy import Column, String, Integer, DateTime, UniqueConstraint
from datetime import datetime
from app.database import Base


class PlayerValue(Base):
    """KTC dynasty values cached from KeepTradeCut, refreshed daily."""

    __tablename__ = "player_values"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # For players: Sleeper player_id. For picks: None (use pick_key instead).
    player_id = Column(String(50), nullable=True, index=True)

    # For draft picks: canonical key like "2026_1_early" / "2026_1_mid" / "2026_1_late"
    # Null for player rows.
    pick_key = Column(String(50), nullable=True, index=True)

    # Human-readable name from KTC (e.g. "Josh Allen" or "2026 Early 1st")
    ktc_name = Column(String(200), nullable=False)

    # KTC value on 0-10000 scale
    value = Column(Integer, nullable=False, default=0)

    # KTC overall rank
    rank = Column(Integer, nullable=True)

    # "ktc" or "internal" (fallback)
    source = Column(String(20), nullable=False, default="ktc")

    position = Column(String(10), nullable=True)  # QB/RB/WR/TE/K/RDP
    team = Column(String(10), nullable=True)
    age = Column(String(10), nullable=True)  # stored as string to handle 0.0 for picks

    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint("player_id", name="uq_player_values_player_id"),
        UniqueConstraint("pick_key", name="uq_player_values_pick_key"),
    )

    def __repr__(self):
        return f"<PlayerValue {self.ktc_name} = {self.value}>"
