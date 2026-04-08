from tests.conftest import (
    create_player, create_league, create_season, create_user, create_roster,
    create_matchup, create_matchup_player_point, create_transaction,
    create_draft, create_draft_pick,
)


async def test_get_players_default(client, db_session):
    await create_player(db_session, id="p1", full_name="Aaron Rodgers", first_name="Aaron", last_name="Rodgers", position="QB", team="NYJ")
    await create_player(db_session, id="p2", full_name="Derrick Henry", first_name="Derrick", last_name="Henry", position="RB", team="TEN")
    await create_player(db_session, id="p3", full_name="Tyreek Hill", first_name="Tyreek", last_name="Hill", position="WR", team="MIA")

    response = await client.get("/api/players")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert len(data["players"]) == 3
    assert data["limit"] == 50
    assert data["offset"] == 0


async def test_get_players_search_by_name(client, db_session):
    await create_player(db_session, id="p1", full_name="Patrick Mahomes", first_name="Patrick", last_name="Mahomes")
    await create_player(db_session, id="p2", full_name="Travis Kelce", first_name="Travis", last_name="Kelce")
    await create_player(db_session, id="p3", full_name="Patrick Surtain", first_name="Patrick", last_name="Surtain")

    response = await client.get("/api/players?search=Patrick")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    names = {p["full_name"] for p in data["players"]}
    assert "Patrick Mahomes" in names
    assert "Patrick Surtain" in names


async def test_get_players_filter_by_position(client, db_session):
    await create_player(db_session, id="p1", full_name="QB Player", position="QB")
    await create_player(db_session, id="p2", full_name="RB Player", position="RB")
    await create_player(db_session, id="p3", full_name="WR Player", position="WR")

    response = await client.get("/api/players?position=QB")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["players"][0]["position"] == "QB"


async def test_get_players_filter_by_team(client, db_session):
    await create_player(db_session, id="p1", full_name="KC Player", team="KC")
    await create_player(db_session, id="p2", full_name="DAL Player", team="DAL")

    response = await client.get("/api/players?team=KC")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["players"][0]["team"] == "KC"


async def test_get_players_combined_filters(client, db_session):
    await create_player(db_session, id="p1", full_name="KC QB", position="QB", team="KC")
    await create_player(db_session, id="p2", full_name="DAL QB", position="QB", team="DAL")
    await create_player(db_session, id="p3", full_name="KC RB", position="RB", team="KC")

    response = await client.get("/api/players?position=QB&team=KC")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["players"][0]["full_name"] == "KC QB"


async def test_get_players_pagination(client, db_session):
    for i in range(5):
        await create_player(db_session, id=f"p{i}", full_name=f"Player {i:02d}", first_name="Player", last_name=f"{i:02d}")

    response = await client.get("/api/players?limit=2&offset=0")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 5
    assert len(data["players"]) == 2

    response2 = await client.get("/api/players?limit=2&offset=2")
    data2 = response2.json()
    assert len(data2["players"]) == 2
    # Different players than first page
    first_ids = {p["id"] for p in data["players"]}
    second_ids = {p["id"] for p in data2["players"]}
    assert first_ids.isdisjoint(second_ids)


async def test_get_players_empty_database(client):
    response = await client.get("/api/players")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["players"] == []


async def test_get_player_details_success(client, db_session):
    await create_player(db_session, id="mahomes_1", full_name="Patrick Mahomes", college="Texas Tech")

    response = await client.get("/api/players/mahomes_1")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "mahomes_1"
    assert data["full_name"] == "Patrick Mahomes"
    assert data["college"] == "Texas Tech"
    # Verify all detail fields are present
    for key in ["first_name", "last_name", "position", "team", "number", "age",
                "height", "weight", "years_exp", "status", "injury_status", "stats"]:
        assert key in data


async def test_get_player_details_not_found(client):
    response = await client.get("/api/players/nonexistent_id")
    assert response.status_code == 404
    assert "Player not found" in response.json()["detail"]


async def test_get_players_position_case_insensitive(client, db_session):
    await create_player(db_session, id="p1", full_name="QB Player", position="QB")

    response = await client.get("/api/players?position=qb")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1


# ─── Player Profile (extended) tests ─────────────────────────────────────────

async def test_get_player_details_has_profile_fields(client, db_session):
    """Profile endpoint returns all new fields in addition to bio fields."""
    await create_player(db_session, id="mahomes_1", full_name="Patrick Mahomes")

    response = await client.get("/api/players/mahomes_1")
    assert response.status_code == 200
    data = response.json()
    for key in ["scoring_history", "current_owner", "ownership_history", "draft_history"]:
        assert key in data


async def test_get_player_scoring_history(client, db_session):
    """Scoring history aggregates points by season correctly."""
    league = await create_league(db_session)
    season = await create_season(db_session, league, year=2023)
    user = await create_user(db_session)
    home_roster = await create_roster(db_session, season, user, roster_id=1)
    away_roster = await create_roster(db_session, season, user, roster_id=2)
    player = await create_player(db_session, id="player_score_1")

    matchup1 = await create_matchup(db_session, season, home_roster, away_roster, week=1)
    matchup2 = await create_matchup(db_session, season, home_roster, away_roster, week=2, matchup_id=2)

    await create_matchup_player_point(db_session, matchup1, home_roster, player, points=20.0, is_starter=True)
    await create_matchup_player_point(db_session, matchup2, home_roster, player, points=15.0, is_starter=False)

    response = await client.get(f"/api/players/{player.id}")
    assert response.status_code == 200
    data = response.json()

    assert len(data["scoring_history"]) == 1
    row = data["scoring_history"][0]
    assert row["season"] == 2023
    assert row["total_points"] == 35.0
    assert row["games"] == 2
    assert row["avg_points"] == 17.5
    assert row["starter_games"] == 1


async def test_get_player_current_owner(client, db_session):
    """Current owner is resolved from the latest season's roster."""
    league = await create_league(db_session)
    season = await create_season(db_session, league, year=2024)
    user = await create_user(db_session, display_name="Roster Owner")
    player = await create_player(db_session, id="player_owner_1")
    await create_roster(db_session, season, user, roster_id=1, players=[player.id], team_name="The Champs")

    response = await client.get(f"/api/players/{player.id}")
    assert response.status_code == 200
    data = response.json()

    assert data["current_owner"] is not None
    assert data["current_owner"]["display_name"] == "Roster Owner"
    assert data["current_owner"]["team_name"] == "The Champs"
    assert data["current_owner"]["season"] == 2024


async def test_get_player_current_owner_none_when_not_rostered(client, db_session):
    """current_owner is None when the player is on no roster."""
    player = await create_player(db_session, id="player_free_agent")

    response = await client.get(f"/api/players/{player.id}")
    assert response.status_code == 200
    assert response.json()["current_owner"] is None


async def test_get_player_ownership_history_waiver_and_release(client, db_session):
    """Waiver claims appear as event_type='waiver'; plain drops as 'release'."""
    league = await create_league(db_session)
    season = await create_season(db_session, league, year=2023)
    user = await create_user(db_session)
    await create_roster(db_session, season, user, roster_id=1)
    player = await create_player(db_session, id="player_txn_1")

    await create_transaction(
        db_session, season,
        id="txn_add_1", type="waiver", week=3,
        adds={player.id: 1}, drops=None,
    )
    await create_transaction(
        db_session, season,
        id="txn_drop_1", type="waiver", week=7,
        adds=None, drops={player.id: 1},
    )

    response = await client.get(f"/api/players/{player.id}")
    assert response.status_code == 200
    data = response.json()

    history = data["ownership_history"]
    assert len(history) == 2
    assert history[0]["event_type"] == "waiver"
    assert history[0]["week"] == 3
    assert history[0]["to_owner"] is not None
    assert history[0]["from_owner"] is None
    assert history[1]["event_type"] == "release"
    assert history[1]["week"] == 7
    assert history[1]["from_owner"] is not None
    assert history[1]["to_owner"] is None


async def test_get_player_ownership_history_trade_merged(client, db_session):
    """Trade transactions are merged into a single event with from/to owners."""
    league = await create_league(db_session)
    season = await create_season(db_session, league, year=2023)
    user1 = await create_user(db_session, id="u1", display_name="Sender")
    user2 = await create_user(db_session, id="u2", display_name="Receiver")
    await create_roster(db_session, season, user1, roster_id=1)
    await create_roster(db_session, season, user2, roster_id=2)
    player = await create_player(db_session, id="player_trade_1")

    await create_transaction(
        db_session, season,
        id="txn_trade_1", type="trade", week=5,
        adds={player.id: 2},   # player goes TO roster 2
        drops={player.id: 1},  # player leaves FROM roster 1
    )

    response = await client.get(f"/api/players/{player.id}")
    assert response.status_code == 200
    data = response.json()

    history = data["ownership_history"]
    assert len(history) == 1
    evt = history[0]
    assert evt["event_type"] == "trade"
    assert evt["week"] == 5
    assert evt["from_owner"]["display_name"] == "Sender"
    assert evt["to_owner"]["display_name"] == "Receiver"


async def test_get_player_draft_history(client, db_session):
    """Draft history returns pick details and owner for a drafted player."""
    league = await create_league(db_session)
    season = await create_season(db_session, league, year=2022)
    user = await create_user(db_session, display_name="Draft Owner")
    await create_roster(db_session, season, user, roster_id=1)
    player = await create_player(db_session, id="player_draft_1")

    draft = await create_draft(db_session, season, year=2022)
    await create_draft_pick(
        db_session, draft,
        player_id=player.id, roster_id=1,
        round=2, pick_in_round=3, pick_no=15,
    )

    response = await client.get(f"/api/players/{player.id}")
    assert response.status_code == 200
    data = response.json()

    assert len(data["draft_history"]) == 1
    pick = data["draft_history"][0]
    assert pick["year"] == 2022
    assert pick["round"] == 2
    assert pick["pick_in_round"] == 3
    assert pick["overall_pick"] == 15
    assert pick["owner"]["display_name"] == "Draft Owner"


async def test_get_player_empty_history_when_undrafted(client, db_session):
    """Player with no history returns empty lists, not errors."""
    player = await create_player(db_session, id="player_no_history")

    response = await client.get(f"/api/players/{player.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["scoring_history"] == []
    assert data["draft_history"] == []
    assert data["ownership_history"] == []
    assert data["current_owner"] is None
