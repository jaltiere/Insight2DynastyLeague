"""
View existing recaps from the database to see current quality.

Usage:
    python -m scripts.view_recaps
"""
import asyncio
import sys
from sqlalchemy import select
from app.database import async_session_maker
from app.models.matchup_recap import MatchupRecap
from app.models.matchup import Matchup
from app.models.roster import Roster
from app.models.user import User

# Set UTF-8 encoding for Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')


async def view_recent_recaps():
    """Display recent recaps from the database."""
    async with async_session_maker() as db:
        # Get 5 most recent recaps
        result = await db.execute(
            select(MatchupRecap)
            .order_by(MatchupRecap.generated_at.desc())
            .limit(5)
        )
        recaps = result.scalars().all()

        if not recaps:
            print("❌ No recaps found in database")
            print("\nTo generate recaps, call:")
            print("POST /api/matchup-recaps/regenerate/{week}")
            return

        print("=" * 80)
        print(f"RECENT RECAPS (showing {len(recaps)} most recent)")
        print("=" * 80)
        print()

        for recap in recaps:
            # Get matchup details
            matchup_result = await db.execute(
                select(Matchup).where(Matchup.id == recap.matchup_id)
            )
            matchup = matchup_result.scalar_one()

            # Get team names
            home_roster_result = await db.execute(
                select(Roster).where(Roster.id == matchup.home_roster_id)
            )
            away_roster_result = await db.execute(
                select(Roster).where(Roster.id == matchup.away_roster_id)
            )
            home_roster = home_roster_result.scalar_one()
            away_roster = away_roster_result.scalar_one()

            home_user_result = await db.execute(
                select(User).where(User.id == home_roster.user_id)
            )
            away_user_result = await db.execute(
                select(User).where(User.id == away_roster.user_id)
            )
            home_user = home_user_result.scalar_one()
            away_user = away_user_result.scalar_one()

            print(f"📅 Week {recap.week} - {recap.recap_type.upper()}")
            print(f"🏈 {home_user.display_name or home_user.username} vs {away_user.display_name or away_user.username}")
            print(f"🕒 Generated: {recap.generated_at}")
            print("-" * 80)

            if recap.recap_text:
                print(f"📝 Recap:\n{recap.recap_text}")
            elif recap.predictions_text:
                print(f"🔮 Prediction:\n{recap.predictions_text}")

            print()

        print("=" * 80)
        print("\n💡 These were generated with the current model (Sonnet).")
        print("Run compare_models.py to see how Haiku would compare!\n")


if __name__ == "__main__":
    asyncio.run(view_recent_recaps())
