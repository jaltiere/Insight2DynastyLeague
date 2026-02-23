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
