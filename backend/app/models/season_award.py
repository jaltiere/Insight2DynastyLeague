from sqlalchemy import Column, String, Integer, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class SeasonAward(Base):
    """SeasonAward model - tracks champions, division winners, consolation winners."""

    __tablename__ = "season_awards"

    id = Column(Integer, primary_key=True, autoincrement=True)
    season_id = Column(Integer, ForeignKey("seasons.id"), nullable=False)
    user_id = Column(String(50), ForeignKey("users.id"), nullable=False)

    # Award type
    award_type = Column(String(50), nullable=False)  # champion, division_winner, consolation_winner
    award_detail = Column(String(100))  # e.g., "Division 1", "Division 2"

    # Additional info
    roster_id = Column(Integer)
    final_record = Column(String(20))  # e.g., "12-2-0"
    points_for = Column(Integer)

    # Relationships
    season = relationship("Season", back_populates="awards")
    user = relationship("User", back_populates="awards")

    def __repr__(self):
        return f"<Award {self.award_type} - {self.user_id}>"
