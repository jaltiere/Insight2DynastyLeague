"""Tests for the Sleeper API client."""
import time
from unittest.mock import AsyncMock, Mock

import pytest

from app.services.sleeper_client import SleeperClient, NFL_STATE_TTL_SECONDS


def _mock_http_client(payload: dict) -> AsyncMock:
    response = Mock()
    response.json.return_value = payload
    response.raise_for_status = Mock()
    http = AsyncMock()
    http.get = AsyncMock(return_value=response)
    return http


@pytest.mark.anyio
async def test_nfl_state_is_cached_within_ttl():
    """Repeated get_nfl_state calls inside the TTL hit Sleeper only once."""
    client = SleeperClient()
    client.client = _mock_http_client({"week": 5, "season": "2024"})

    first = await client.get_nfl_state()
    second = await client.get_nfl_state()

    assert first == second == {"week": 5, "season": "2024"}
    assert client.client.get.call_count == 1


@pytest.mark.anyio
async def test_nfl_state_refetches_after_ttl():
    """An expired cache entry triggers a fresh fetch."""
    client = SleeperClient()
    client.client = _mock_http_client({"week": 5, "season": "2024"})

    await client.get_nfl_state()
    # Age the cache past the TTL
    client._nfl_state_cached_at = time.monotonic() - NFL_STATE_TTL_SECONDS - 1
    await client.get_nfl_state()

    assert client.client.get.call_count == 2
