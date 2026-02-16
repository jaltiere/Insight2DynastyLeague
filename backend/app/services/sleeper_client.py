import httpx
from typing import Optional, List, Dict, Any
from app.config import get_settings

settings = get_settings()


class SleeperClient:
    """Client for interacting with the Sleeper API."""

    def __init__(self):
        self.base_url = settings.SLEEPER_BASE_URL
        self.league_id = settings.SLEEPER_LEAGUE_ID
        self.client = httpx.AsyncClient(timeout=30.0)

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

    async def get_league(self, league_id: Optional[str] = None) -> Dict[str, Any]:
        """Get league information."""
        lid = league_id or self.league_id
        response = await self.client.get(f"{self.base_url}/league/{lid}")
        response.raise_for_status()
        return response.json()

    async def get_rosters(self, league_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all rosters for a league."""
        lid = league_id or self.league_id
        response = await self.client.get(f"{self.base_url}/league/{lid}/rosters")
        response.raise_for_status()
        return response.json()

    async def get_users(self, league_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all users in a league."""
        lid = league_id or self.league_id
        response = await self.client.get(f"{self.base_url}/league/{lid}/users")
        response.raise_for_status()
        return response.json()

    async def get_matchups(self, week: int, league_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get matchups for a specific week."""
        lid = league_id or self.league_id
        response = await self.client.get(f"{self.base_url}/league/{lid}/matchups/{week}")
        response.raise_for_status()
        return response.json()

    async def get_winners_bracket(self, league_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get winners bracket for playoffs."""
        lid = league_id or self.league_id
        response = await self.client.get(f"{self.base_url}/league/{lid}/winners_bracket")
        response.raise_for_status()
        return response.json()

    async def get_losers_bracket(self, league_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get losers (consolation) bracket for playoffs."""
        lid = league_id or self.league_id
        response = await self.client.get(f"{self.base_url}/league/{lid}/losers_bracket")
        response.raise_for_status()
        return response.json()

    async def get_transactions(self, round_num: int, league_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get transactions for a specific round (week)."""
        lid = league_id or self.league_id
        response = await self.client.get(f"{self.base_url}/league/{lid}/transactions/{round_num}")
        response.raise_for_status()
        return response.json()

    async def get_traded_picks(self, league_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all traded draft picks."""
        lid = league_id or self.league_id
        response = await self.client.get(f"{self.base_url}/league/{lid}/traded_picks")
        response.raise_for_status()
        return response.json()

    async def get_drafts(self, league_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all drafts for a league."""
        lid = league_id or self.league_id
        response = await self.client.get(f"{self.base_url}/league/{lid}/drafts")
        response.raise_for_status()
        return response.json()

    async def get_draft(self, draft_id: str) -> Dict[str, Any]:
        """Get specific draft information."""
        response = await self.client.get(f"{self.base_url}/draft/{draft_id}")
        response.raise_for_status()
        return response.json()

    async def get_draft_picks(self, draft_id: str) -> List[Dict[str, Any]]:
        """Get all picks for a specific draft."""
        response = await self.client.get(f"{self.base_url}/draft/{draft_id}/picks")
        response.raise_for_status()
        return response.json()

    async def get_all_players(self) -> Dict[str, Any]:
        """Get all NFL players (~5MB response)."""
        response = await self.client.get(f"{self.base_url}/players/nfl")
        response.raise_for_status()
        return response.json()

    async def get_nfl_state(self) -> Dict[str, Any]:
        """Get current NFL season state."""
        response = await self.client.get(f"{self.base_url}/state/nfl")
        response.raise_for_status()
        return response.json()


# Singleton instance
sleeper_client = SleeperClient()
