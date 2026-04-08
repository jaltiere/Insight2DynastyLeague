"""Test H2H query discrepancy between recap service and H2H matrix."""
import asyncio
from sqlalchemy import select, or_, and_
from app.database import AsyncSessionLocal
from app.models.user import User
from app.models.roster import Roster
from app.models.matchup import Matchup


async def test_h2h_queries():
    """Test different H2H query approaches."""
    async with AsyncSessionLocal() as db:
        # Get jaltiere and ankurdeora
        result = await db.execute(
            select(User).where(User.username.in_(['jaltiere', 'ankurdeora']))
        )
        users = result.scalars().all()

        if len(users) != 2:
            print(f"Error: Found {len(users)} users, expected 2")
            return

        user1 = next(u for u in users if u.username == 'jaltiere')
        user2 = next(u for u in users if u.username == 'ankurdeora')

        print(f"User 1: {user1.username} (ID: {user1.id})")
        print(f"User 2: {user2.username} (ID: {user2.id})")

        # Get rosters for both users
        result = await db.execute(
            select(Roster).where(Roster.user_id.in_([user1.id, user2.id]))
        )
        rosters = result.scalars().all()

        user1_roster_ids = [r.id for r in rosters if r.user_id == user1.id]
        user2_roster_ids = [r.id for r in rosters if r.user_id == user2.id]

        print(f"\nUser1 roster IDs: {user1_roster_ids}")
        print(f"User2 roster IDs: {user2_roster_ids}")

        # Query 1: Current recap service approach (potentially buggy)
        print("\n=== RECAP SERVICE QUERY (Current) ===")
        result1 = await db.execute(
            select(Matchup)
            .join(Roster, Matchup.home_roster_id == Roster.id)
            .where(
                and_(
                    Roster.user_id.in_([user1.id, user2.id]),
                    Matchup.away_roster_id.in_(
                        select(Roster.id).where(Roster.user_id.in_([user1.id, user2.id]))
                    )
                )
            )
        )
        matchups1 = result1.scalars().all()
        print(f"Found {len(matchups1)} matchups")

        # Query 2: H2H endpoint approach (correct)
        print("\n=== H2H ENDPOINT QUERY (Correct) ===")
        result2 = await db.execute(
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
        )
        matchups2 = result2.scalars().all()
        print(f"Found {len(matchups2)} matchups")

        # Compare results
        print("\n=== COMPARISON ===")
        ids1 = set(m.id for m in matchups1)
        ids2 = set(m.id for m in matchups2)

        missing_from_recap = ids2 - ids1
        extra_in_recap = ids1 - ids2

        if missing_from_recap:
            print(f"\nMissing from recap query: {len(missing_from_recap)} matchups")
            for mid in missing_from_recap:
                m = next(m for m in matchups2 if m.id == mid)
                print(f"  - Week {m.week}, Season {m.season_id}, Type: {m.match_type}")
                print(f"    Home: {m.home_roster_id}, Away: {m.away_roster_id}")
                print(f"    Score: {m.home_points} - {m.away_points}")

        if extra_in_recap:
            print(f"\nExtra in recap query: {len(extra_in_recap)} matchups")
            for mid in extra_in_recap:
                m = next(m for m in matchups1 if m.id == mid)
                print(f"  - Week {m.week}, Season {m.season_id}, Type: {m.match_type}")

        # Break down by match type
        print("\n=== BREAKDOWN BY MATCH TYPE (H2H Endpoint Query) ===")
        by_type = {}
        user1_wins_by_type = {}

        for m in matchups2:
            match_type = m.match_type or 'regular'
            if match_type not in by_type:
                by_type[match_type] = []
                user1_wins_by_type[match_type] = 0

            by_type[match_type].append(m)

            # Check who won
            if m.home_roster_id in user1_roster_ids:
                user1_points = m.home_points
                user2_points = m.away_points
            else:
                user1_points = m.away_points
                user2_points = m.home_points

            if user1_points > user2_points:
                user1_wins_by_type[match_type] += 1

        for match_type in sorted(by_type.keys()):
            games = by_type[match_type]
            user1_wins = user1_wins_by_type[match_type]
            user2_wins = len(games) - user1_wins
            print(f"{match_type}: {len(games)} games, {user1.username} {user1_wins}-{user2_wins}")

        total_games = len(matchups2)
        total_user1_wins = sum(user1_wins_by_type.values())
        total_user2_wins = total_games - total_user1_wins
        print(f"\nALL-TIME: {total_games} games, {user1.username} {total_user1_wins}-{total_user2_wins}")


if __name__ == "__main__":
    asyncio.run(test_h2h_queries())
