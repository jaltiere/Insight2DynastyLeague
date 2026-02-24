from sqlalchemy import Column, String, Integer, JSON, DateTime
from datetime import datetime
from app.database import Base


class Player(Base):
    """Player model - cached player data from Sleeper."""

    __tablename__ = "players"

    id = Column(String(50), primary_key=True)  # Sleeper player ID
    first_name = Column(String(100))
    last_name = Column(String(100))
    full_name = Column(String(200))
    position = Column(String(10))  # QB, RB, WR, TE, K, DEF
    team = Column(String(10))  # NFL team abbreviation

    # Player info
    number = Column(Integer)
    age = Column(Integer)
    height = Column(String(10))
    weight = Column(Integer)
    college = Column(String(100))
    years_exp = Column(Integer)
    rookie_year = Column(Integer)  # Computed: current_season - years_exp

    # Status
    status = Column(String(50))  # Active, Inactive, Injured Reserve, etc.
    injury_status = Column(String(50))

    # Stats (can be expanded as needed)
    stats = Column(JSON)  # Career/season stats

    # Metadata
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Player {self.full_name} ({self.position} - {self.team})>"
