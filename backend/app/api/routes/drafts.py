from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.database import get_db
from app.models import Draft, DraftPick, Player, Roster, Season, User
from app.services.sleeper_client import sleeper_client
from collections import Counter
from typing import List, Dict, Any

router = APIRouter()


@router.get("/drafts")
async def get_all_drafts(db: AsyncSession = Depends(get_db)):
    """Get all draft years available."""
    result = await db.execute(
        select(Draft).order_by(desc(Draft.year))
    )
    drafts = result.scalars().all()

    draft_list = []
    for draft in drafts:
        draft_list.append({
            "draft_id": draft.id,
            "year": draft.year,
            "type": draft.type,
            "status": draft.status,
            "rounds": draft.rounds,
            "start_time": draft.start_time.isoformat() if draft.start_time else None
        })

    return {
        "total_drafts": len(draft_list),
        "drafts": draft_list
    }


@router.get("/drafts/current")
async def get_current_draft(db: AsyncSession = Depends(get_db)):
    """Get the most recent season's draft status for countdown display."""
    result = await db.execute(
        select(Draft).order_by(desc(Draft.year)).limit(1)
    )
    draft = result.scalar_one_or_none()

    if not draft:
        return None

    # Resolve draft order to owner names, accounting for traded picks
    draft_order_list = []
    raw_order = draft.draft_order or {}
    if raw_order:
        roster_ids = [rid for rid in raw_order.values() if rid]

        # Fetch traded picks from Sleeper to find current first-round pick owners
        try:
            traded_picks = await sleeper_client.get_traded_picks()
        except Exception:
            traded_picks = []

        # Build lookup: original_roster_id -> current_owner_roster_id for round 1
        traded_r1 = {}
        for tp in traded_picks:
            if str(tp.get("season")) == str(draft.year) and tp.get("round") == 1:
                traded_r1[tp["roster_id"]] = tp["owner_id"]

        # Collect ALL roster_ids we need to resolve (original + traded owners)
        all_roster_ids = set(roster_ids)
        for owner_id in traded_r1.values():
            all_roster_ids.add(owner_id)

        roster_to_owner = {}
        if all_roster_ids:
            result = await db.execute(
                select(Roster, User)
                .join(User, Roster.user_id == User.id)
                .join(Season, Roster.season_id == Season.id)
                .where(Roster.roster_id.in_(list(all_roster_ids)), Season.year == draft.year)
            )
            for roster, user in result.all():
                roster_to_owner[roster.roster_id] = {
                    "display_name": roster.team_name or user.display_name or user.username,
                    "avatar": user.avatar,
                }

        for slot in sorted(raw_order.keys(), key=lambda s: int(s)):
            original_roster_id = raw_order[slot]
            original_owner = roster_to_owner.get(original_roster_id)

            # Check if this pick was traded
            current_owner_roster_id = traded_r1.get(original_roster_id)
            if current_owner_roster_id and current_owner_roster_id != original_roster_id:
                current_owner = roster_to_owner.get(current_owner_roster_id)
                draft_order_list.append({
                    "slot": int(slot),
                    "display_name": current_owner["display_name"] if current_owner else f"Team {slot}",
                    "avatar": current_owner["avatar"] if current_owner else None,
                    "is_traded": True,
                    "original_owner_name": original_owner["display_name"] if original_owner else f"Team {slot}",
                })
            else:
                draft_order_list.append({
                    "slot": int(slot),
                    "display_name": original_owner["display_name"] if original_owner else f"Team {slot}",
                    "avatar": original_owner["avatar"] if original_owner else None,
                    "is_traded": False,
                    "original_owner_name": None,
                })

    return {
        "draft_id": draft.id,
        "year": draft.year,
        "status": draft.status,
        "start_time": draft.start_time.isoformat() if draft.start_time else None,
        "draft_order": draft_order_list
    }


@router.get("/drafts/{year}")
async def get_draft_by_year(year: int, db: AsyncSession = Depends(get_db)):
    """Get draft results for a specific year."""
    # Get draft for this year
    result = await db.execute(
        select(Draft).where(Draft.year == year)
    )
    draft = result.scalar_one_or_none()

    if not draft:
        raise HTTPException(status_code=404, detail=f"Draft for year {year} not found")

    # Live sync from Sleeper when draft is active so polling returns fresh picks
    if draft.status in ("in_progress", "drafting", "paused", "pre_draft"):
        try:
            draft_detail = await sleeper_client.get_draft(draft.id)
            draft.status = draft_detail.get("status", draft.status)

            picks_data = await sleeper_client.get_draft_picks(draft.id)
            for pick_data in picks_data:
                pick_no = pick_data.get("pick_no")
                pick_result = await db.execute(
                    select(DraftPick).where(
                        DraftPick.draft_id == draft.id,
                        DraftPick.pick_no == pick_no
                    )
                )
                existing = pick_result.scalar_one_or_none()
                if existing:
                    existing.player_id = pick_data.get("player_id")
                    existing.pick_metadata = pick_data.get("metadata", {})
                else:
                    db.add(DraftPick(
                        draft_id=draft.id,
                        pick_no=pick_no,
                        round=pick_data.get("round"),
                        pick_in_round=pick_data.get("draft_slot"),
                        roster_id=pick_data.get("roster_id"),
                        player_id=pick_data.get("player_id"),
                        pick_metadata=pick_data.get("metadata", {})
                    ))
            await db.flush()
        except Exception:
            pass  # Serve stale data if Sleeper is unreachable

    # Get all picks for this draft
    result = await db.execute(
        select(DraftPick)
        .where(DraftPick.draft_id == draft.id)
        .order_by(DraftPick.pick_no)
    )
    picks = result.scalars().all()

    # Get all players, rosters, and users to enrich pick data
    player_ids = [p.player_id for p in picks if p.player_id]
    draft_order = draft.draft_order or {}
    roster_ids = list(set(
        [p.roster_id for p in picks if p.roster_id] +
        [rid for rid in draft_order.values() if rid]
    ))

    # For incomplete drafts, fetch traded picks to show current owners
    traded_picks_by_slot: Dict[int, int] = {}
    if draft.status != "complete" and draft_order:
        try:
            traded_picks = await sleeper_client.get_traded_picks()
            # Build lookup: original_roster_id -> current_owner_roster_id for this draft year
            for tp in traded_picks:
                if str(tp.get("season")) == str(draft.year):
                    round_num = tp.get("round")
                    if round_num:
                        # Map original roster_id to current owner_id for all rounds
                        original_rid = tp["roster_id"]
                        current_owner_rid = tp["owner_id"]
                        # Find which slot this original roster_id corresponds to
                        for slot_str, rid in draft_order.items():
                            if rid == original_rid:
                                slot_num = int(slot_str)
                                # Store the current owner for this slot (per round)
                                key = (slot_num, round_num)
                                traded_picks_by_slot[key] = current_owner_rid
                                # Also add current owner roster_id to our lookup list
                                roster_ids.append(current_owner_rid)
        except Exception as e:
            # If Sleeper API fails, continue without traded pick info
            print(f"Error fetching traded picks: {e}")

    # Ensure unique roster_ids
    roster_ids = list(set(roster_ids))

    # Fetch players
    player_map = {}
    if player_ids:
        result = await db.execute(
            select(Player).where(Player.id.in_(player_ids))
        )
        players = result.scalars().all()
        player_map = {p.id: p for p in players}

    # Fetch rosters to get user info (filter by season year)
    roster_to_user = {}
    if roster_ids:
        result = await db.execute(
            select(Roster, User)
            .join(User, Roster.user_id == User.id)
            .join(Season, Roster.season_id == Season.id)
            .where(Roster.roster_id.in_(roster_ids), Season.year == draft.year)
        )
        for roster, user in result.all():
            roster_to_user[roster.roster_id] = {
                "user_id": user.id,
                "display_name": roster.team_name or user.display_name or user.username,
                "avatar": user.avatar
            }

    # Build slot_owners map from draft_order (always original owners)
    slot_owners = {}
    if draft_order:
        for slot, roster_id in draft_order.items():
            owner = roster_to_user.get(roster_id)
            if owner:
                slot_owners[slot] = owner
            else:
                slot_owners[slot] = {
                    "user_id": None,
                    "display_name": f"Team {slot}",
                    "avatar": None
                }
    elif picks:
        # Derive original slot owners: for each slot, the most common roster_id
        # across all rounds is likely the original owner (traded picks are minority)
        slot_rosters: Dict[int, list] = {}
        for pick in picks:
            slot_rosters.setdefault(pick.pick_in_round, []).append(pick.roster_id)
        for slot, rid_list in sorted(slot_rosters.items()):
            most_common_rid = Counter(rid_list).most_common(1)[0][0]
            owner = roster_to_user.get(most_common_rid)
            if owner:
                slot_owners[str(slot)] = owner
            else:
                slot_owners[str(slot)] = {
                    "user_id": None,
                    "display_name": f"Team {slot}",
                    "avatar": None
                }
        # Also build a synthetic draft_order for traded-pick detection
        draft_order = {
            str(slot): Counter(rid_list).most_common(1)[0][0]
            for slot, rid_list in slot_rosters.items()
        }

    # Build picks list with enriched data
    picks_list = []
    for pick in picks:
        player = player_map.get(pick.player_id)

        # For incomplete drafts, check if this pick was traded
        effective_roster_id = pick.roster_id
        if draft.status != "complete" and traded_picks_by_slot:
            key = (pick.pick_in_round, pick.round)
            if key in traded_picks_by_slot:
                effective_roster_id = traded_picks_by_slot[key]

        owner = roster_to_user.get(effective_roster_id)

        pick_data = {
            "pick_no": pick.pick_no,
            "round": pick.round,
            "pick_in_round": pick.pick_in_round,
            "roster_id": effective_roster_id,
            "player_id": pick.player_id,
        }

        # Add player info if available
        if player:
            pick_data.update({
                "player_name": player.full_name,
                "position": player.position,
                "team": player.team
            })

        # Add owner info if available
        if owner:
            pick_data.update({
                "owner_user_id": owner["user_id"],
                "owner_display_name": owner["display_name"]
            })

        picks_list.append(pick_data)

    # For incomplete drafts, build current_pick_owners map showing who owns each slot
    current_pick_owners = {}
    if draft.status != "complete" and draft_order:
        for slot_str, original_roster_id in draft_order.items():
            slot_num = int(slot_str)
            for round_num in range(1, draft.rounds + 1):
                key = f"{slot_num}_{round_num}"
                # Check if this pick was traded
                traded_rid = traded_picks_by_slot.get((slot_num, round_num))
                current_roster_id = traded_rid if traded_rid else original_roster_id

                # Get owner info for current holder
                current_owner = roster_to_user.get(current_roster_id)
                if current_owner:
                    current_pick_owners[key] = current_owner

    return {
        "draft_id": draft.id,
        "year": draft.year,
        "type": draft.type,
        "status": draft.status,
        "rounds": draft.rounds,
        "draft_order": draft_order,
        "slot_owners": slot_owners,
        "current_pick_owners": current_pick_owners if current_pick_owners else None,
        "total_picks": len(picks_list),
        "picks": picks_list
    }
