from tests.conftest import (
    create_league, create_season, create_user, create_roster,
    create_player, create_transaction,
)


async def test_get_recent_transactions_empty(client):
    response = await client.get("/api/transactions/recent")
    assert response.status_code == 200
    assert response.json()["transactions"] == []


async def test_get_recent_transactions_with_data(client, db_session):
    league = await create_league(db_session)
    season = await create_season(db_session, league)
    user = await create_user(db_session)
    await create_roster(db_session, season, user, roster_id=1)
    player = await create_player(db_session, id="p1", full_name="Mac Jones", position="QB")

    await create_transaction(
        db_session, season,
        id="txn_1",
        type="waiver",
        status="complete",
        week=5,
        roster_ids=[1],
        adds={"p1": 1},
        drops=None,
        waiver_bid=3,
        status_updated=1700000001000,
    )
    await db_session.flush()

    response = await client.get("/api/transactions/recent")
    assert response.status_code == 200
    data = response.json()
    assert len(data["transactions"]) == 1

    txn = data["transactions"][0]
    assert txn["type"] == "waiver"
    assert txn["status"] == "complete"
    assert txn["week"] == 5
    assert txn["waiver_bid"] == 3
    assert len(txn["adds"]) == 1
    assert txn["adds"][0]["player_name"] == "Mac Jones"
    assert txn["adds"][0]["position"] == "QB"


async def test_get_recent_transactions_limit(client, db_session):
    league = await create_league(db_session)
    season = await create_season(db_session, league)

    for i in range(5):
        await create_transaction(
            db_session, season,
            id=f"txn_{i}",
            status_updated=1700000000000 + i * 1000,
        )
    await db_session.flush()

    response = await client.get("/api/transactions/recent?limit=3")
    assert response.status_code == 200
    assert len(response.json()["transactions"]) == 3


async def test_get_recent_transactions_resolves_drops(client, db_session):
    league = await create_league(db_session)
    season = await create_season(db_session, league)
    user = await create_user(db_session)
    await create_roster(db_session, season, user, roster_id=1)
    await create_player(db_session, id="p2", full_name="Jahan Dotson", position="WR")

    await create_transaction(
        db_session, season,
        id="txn_drop",
        type="free_agent",
        adds=None,
        drops={"p2": 1},
        waiver_bid=None,
        status_updated=1700000002000,
    )
    await db_session.flush()

    response = await client.get("/api/transactions/recent")
    assert response.status_code == 200
    txn = response.json()["transactions"][0]
    assert len(txn["drops"]) == 1
    assert txn["drops"][0]["player_name"] == "Jahan Dotson"
    assert txn["drops"][0]["position"] == "WR"


async def test_get_recent_transactions_response_fields(client, db_session):
    league = await create_league(db_session)
    season = await create_season(db_session, league)
    await create_transaction(db_session, season, id="txn_fields")
    await db_session.flush()

    response = await client.get("/api/transactions/recent")
    assert response.status_code == 200
    txn = response.json()["transactions"][0]
    for key in ["id", "type", "status", "season", "week", "waiver_bid",
                "adds", "drops", "owners", "draft_picks", "status_updated"]:
        assert key in txn, f"Missing key: {key}"


# ---------------------------------------------------------------------------
# Transaction Summary endpoint tests
# ---------------------------------------------------------------------------


async def test_transaction_summary_empty(client):
    response = await client.get("/api/transactions/summary")
    assert response.status_code == 200
    assert response.json()["summary"] == []


async def test_transaction_summary_counts(client, db_session):
    league = await create_league(db_session)
    season = await create_season(db_session, league)
    user = await create_user(db_session)
    await create_roster(db_session, season, user, roster_id=1)

    await create_transaction(
        db_session, season, id="txn_w1", type="waiver",
        status="complete", roster_ids=[1], status_updated=1700000001000,
    )
    await create_transaction(
        db_session, season, id="txn_w2", type="waiver",
        status="complete", roster_ids=[1], status_updated=1700000002000,
    )
    await create_transaction(
        db_session, season, id="txn_fa1", type="free_agent",
        status="complete", roster_ids=[1], status_updated=1700000003000,
    )
    await create_transaction(
        db_session, season, id="txn_t1", type="trade",
        status="complete", roster_ids=[1], status_updated=1700000004000,
    )
    # Failed transaction should NOT count
    await create_transaction(
        db_session, season, id="txn_fail", type="waiver",
        status="failed", roster_ids=[1], status_updated=1700000005000,
    )
    await db_session.flush()

    response = await client.get("/api/transactions/summary")
    assert response.status_code == 200
    data = response.json()
    assert len(data["summary"]) == 1

    entry = data["summary"][0]
    assert entry["user_id"] == user.id
    assert entry["waiver_adds"] == 2
    assert entry["free_agent_adds"] == 1
    assert entry["trades"] == 1
    assert entry["total"] == 4


async def test_transaction_summary_filter_by_season(client, db_session):
    league = await create_league(db_session)
    season_2023 = await create_season(db_session, league, year=2023)
    season_2024 = await create_season(db_session, league, year=2024)
    user = await create_user(db_session)
    await create_roster(db_session, season_2023, user, roster_id=1)
    await create_roster(db_session, season_2024, user, roster_id=1)

    await create_transaction(
        db_session, season_2023, id="txn_2023", type="waiver",
        status="complete", roster_ids=[1], status_updated=1700000001000,
    )
    await create_transaction(
        db_session, season_2024, id="txn_2024", type="trade",
        status="complete", roster_ids=[1], status_updated=1700000002000,
    )
    await db_session.flush()

    # Filter to 2024 only
    response = await client.get("/api/transactions/summary?season=2024")
    assert response.status_code == 200
    data = response.json()
    assert len(data["summary"]) == 1
    assert data["summary"][0]["trades"] == 1
    assert data["summary"][0]["waiver_adds"] == 0


async def test_transaction_summary_response_fields(client, db_session):
    league = await create_league(db_session)
    season = await create_season(db_session, league)
    user = await create_user(db_session)
    await create_roster(db_session, season, user, roster_id=1)
    await create_transaction(
        db_session, season, id="txn_s1", type="waiver",
        status="complete", roster_ids=[1], status_updated=1700000001000,
    )
    await db_session.flush()

    response = await client.get("/api/transactions/summary")
    assert response.status_code == 200
    entry = response.json()["summary"][0]
    for key in ["user_id", "username", "team_name",
                "waiver_adds", "free_agent_adds", "trades", "total"]:
        assert key in entry, f"Missing key: {key}"


# ---------------------------------------------------------------------------
# Transactions By Owner endpoint tests
# ---------------------------------------------------------------------------


async def test_transactions_by_owner_empty(client):
    response = await client.get(
        "/api/transactions/by-owner?user_id=nobody&type=waiver"
    )
    assert response.status_code == 200
    assert response.json()["transactions"] == []


async def test_transactions_by_owner_filters_type(client, db_session):
    league = await create_league(db_session)
    season = await create_season(db_session, league)
    user = await create_user(db_session)
    await create_roster(db_session, season, user, roster_id=1)
    player = await create_player(db_session, id="p1", full_name="Player One")

    await create_transaction(
        db_session, season, id="txn_w", type="waiver",
        status="complete", roster_ids=[1], adds={"p1": 1},
        status_updated=1700000001000,
    )
    await create_transaction(
        db_session, season, id="txn_fa", type="free_agent",
        status="complete", roster_ids=[1], adds={"p1": 1},
        status_updated=1700000002000,
    )
    await db_session.flush()

    response = await client.get(
        f"/api/transactions/by-owner?user_id={user.id}&type=waiver"
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["transactions"]) == 1
    assert data["transactions"][0]["type"] == "waiver"


async def test_transactions_by_owner_filters_season(client, db_session):
    league = await create_league(db_session)
    season_2023 = await create_season(db_session, league, year=2023)
    season_2024 = await create_season(db_session, league, year=2024)
    user = await create_user(db_session)
    await create_roster(db_session, season_2023, user, roster_id=1)
    await create_roster(db_session, season_2024, user, roster_id=1)

    await create_transaction(
        db_session, season_2023, id="txn_23", type="waiver",
        status="complete", roster_ids=[1], status_updated=1700000001000,
    )
    await create_transaction(
        db_session, season_2024, id="txn_24", type="waiver",
        status="complete", roster_ids=[1], status_updated=1700000002000,
    )
    await db_session.flush()

    response = await client.get(
        f"/api/transactions/by-owner?user_id={user.id}&type=waiver&season=2024"
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["transactions"]) == 1
    assert data["transactions"][0]["season"] == 2024


async def test_transactions_by_owner_excludes_other_owners(client, db_session):
    league = await create_league(db_session)
    season = await create_season(db_session, league)
    user1 = await create_user(db_session, id="user1", username="owner1")
    user2 = await create_user(db_session, id="user2", username="owner2")
    await create_roster(db_session, season, user1, roster_id=1)
    await create_roster(db_session, season, user2, roster_id=2)

    await create_transaction(
        db_session, season, id="txn_u1", type="waiver",
        status="complete", roster_ids=[1], status_updated=1700000001000,
    )
    await create_transaction(
        db_session, season, id="txn_u2", type="waiver",
        status="complete", roster_ids=[2], status_updated=1700000002000,
    )
    await db_session.flush()

    response = await client.get(
        "/api/transactions/by-owner?user_id=user1&type=waiver"
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data["transactions"]) == 1
