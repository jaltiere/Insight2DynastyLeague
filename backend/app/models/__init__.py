# Import all models here so they are registered with SQLAlchemy
from app.models.league import League
from app.models.user import User
from app.models.season import Season
from app.models.roster import Roster
from app.models.matchup import Matchup
from app.models.player import Player
from app.models.transaction import Transaction
from app.models.draft import Draft, DraftPick
from app.models.season_award import SeasonAward

__all__ = [
    "League",
    "User",
    "Season",
    "Roster",
    "Matchup",
    "Player",
    "Transaction",
    "Draft",
    "DraftPick",
    "SeasonAward",
]
