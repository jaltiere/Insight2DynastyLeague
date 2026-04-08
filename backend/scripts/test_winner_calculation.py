"""Test winner calculation logic for H2H."""
import asyncio
from sqlalchemy import select, or_, and_
from app.database import AsyncSessionLocal
from app.models.user import User
from app.models.roster import Roster
from app.models.matchup import Matchup


async def test_winner_calculation():
    """Test winner calculation for jaltiere vs ankurdeora."""
    async with AsyncSessionLocal() as db:
        # Get users
        result = await db.execute(
            select(User).where(User.username.in_(['jaltiere', 'ankurdeora']))
        )
        users = result.scalars().all()
        user1 = next(u for u in users if u.username == 'jaltiere')
        user2 = next(u for u in users if u.username == 'ankurdeora')

        # Get rosters
        result = await db.execute(
            select(Roster).where(Roster.user_id.in_([user1.id, user2.id]))
        )
        rosters = result.scalars().all()
        user1_roster_ids = [r.id for r in rosters if r.user_id == user1.id]
        user2_roster_ids = [r.id for r in rosters if r.user_id == user2.id]

        # Get all matchups
        result = await db.execute(
            select(Matchup)
            .where(
                or_(
                    and_(
                        Matchup.home_roster_id.in_(user1_roster_ids),
                        Matchup.away_roster_id.in_(user2_roster_ids)
                    ),
                    and_(
                        Matchup.home_roster_id.in_(user2_roster_ids),
                        Matchup.away_roster_id.in_(user1_roster_ids)
                    )
                )
            )
            .order_by(Matchup.week)
        )
        matchups = result.scalars().all()

        print(f"Found {len(matchups)} matchups between {user1.username} and {user2.username}\n")

        user1_wins = 0
        user2_wins = 0

        for m in matchups:
            home_is_user1 = m.home_roster_id in user1_roster_ids
            user1_points = m.home_points if home_is_user1 else m.away_points
            user2_points = m.away_points if home_is_user1 else m.home_points

            winner = None
            if user1_points > user2_points:
                winner = user1.username
                user1_wins += 1
            elif user2_points > user1_points:
                winner = user2.username
                user2_wins += 1

            # Check winner_roster_id
            print(f"Week {m.week} ({m.match_type or 'regular'}):")
            print(f"  {user1.username}: {user1_points:.2f} pts (roster {m.home_roster_id if home_is_user1 else m.away_roster_id})")
            print(f"  {user2.username}: {user2_points:.2f} pts (roster {m.away_roster_id if home_is_user1 else m.home_roster_id})")
            print(f"  Winner: {winner}")
            print(f"  winner_roster_id in DB: {m.winner_roster_id}")

            # Check if winner_roster_id matches
            if winner == user1.username:
                expected_roster = m.home_roster_id if home_is_user1 else m.away_roster_id
                if m.winner_roster_id != expected_roster:
                    print(f"  ⚠️  WARNING: winner_roster_id {m.winner_roster_id} doesn't match expected {expected_roster}")
            elif winner == user2.username:
                expected_roster = m.away_roster_id if home_is_user1 else m.home_roster_id
                if m.winner_roster_id != expected_roster:
                    print(f"  ⚠️  WARNING: winner_roster_id {m.winner_roster_id} doesn't match expected {expected_roster}")

            # Now test the recap service logic
            if m.winner_roster_id:
                result = await db.execute(
                    select(Roster.user_id).where(Roster.id == m.winner_roster_id)
                )
                winner_user_id = result.scalar_one_or_none()
                recap_thinks_user1_won = (winner_user_id == user1.id)
                print(f"  Recap service thinks {user1.username if recap_thinks_user1_won else user2.username} won")
            print()

        print(f"\nFINAL TALLY:")
        print(f"{user1.username}: {user1_wins} wins")
        print(f"{user2.username}: {user2_wins} wins")
        print(f"All-time: {user1.username} leads {user1_wins}-{user2_wins}")


if __name__ == "__main__":
    asyncio.run(test_winner_calculation())
