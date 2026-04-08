"""Test recap generation directly."""
import asyncio
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.season import Season
from app.services.matchup_recap_service import MatchupRecapService
from app.config import get_settings

settings = get_settings()


async def test_generation():
    """Test generating recaps for week 17, 2025."""
    async with AsyncSessionLocal() as db:
        # Get season
        result = await db.execute(select(Season).where(Season.year == 2025))
        season = result.scalar_one()
        print(f"Season: {season.id}, Year: {season.year}")

        # Create service
        service = MatchupRecapService(db, settings.ANTHROPIC_API_KEY)
        print(f"Mock mode: {service.mock_mode}")
        print(f"API key set: {bool(settings.ANTHROPIC_API_KEY)}")

        # Generate recaps
        print(f"\nGenerating recaps for week 17...")
        recap_count = await service.generate_weekly_recaps(season.id, 17)
        print(f"Generated {recap_count} recaps")


if __name__ == "__main__":
    asyncio.run(test_generation())
