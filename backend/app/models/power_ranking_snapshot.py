from sqlalchemy import Column, Integer, Float, DateTime, UniqueConstraint
from sqlalchemy.sql import func
from app.database import Base


class PowerRankingSnapshot(Base):
    __tablename__ = "power_ranking_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    season_year = Column(Integer, nullable=False, index=True)
    week = Column(Integer, nullable=False)
    roster_id = Column(Integer, nullable=False)
    rank = Column(Integer, nullable=False)
    total_score = Column(Float, nullable=False)
    current_season_score = Column(Float, nullable=False)
    roster_value_score = Column(Float, nullable=False)
    historical_score = Column(Float, nullable=False)
    snapped_at = Column(DateTime, server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "season_year", "week", "roster_id", name="uq_power_ranking_snapshot"
        ),
    )
