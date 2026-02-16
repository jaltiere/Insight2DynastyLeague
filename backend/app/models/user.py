from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class User(Base):
    """User model - stores league members (owners)."""

    __tablename__ = "users"

    id = Column(String(50), primary_key=True)  # Sleeper user ID
    username = Column(String(100))
    display_name = Column(String(255))
    avatar = Column(String(255))  # Avatar ID from Sleeper
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    rosters = relationship("Roster", back_populates="user", cascade="all, delete-orphan")
    awards = relationship("SeasonAward", back_populates="user")

    def __repr__(self):
        return f"<User {self.display_name} (@{self.username})>"
