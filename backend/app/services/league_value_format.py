"""Resolve which cached KTC value column a league should read.

KTC publishes a value per (scoring format, TE-premium tier). Both axes are
league settings, and the configured leagues genuinely differ on both: for 2026
Insight2Dynasty is 1QB while Couch Crusaders and Double Domination run
SUPER_FLEX, and all three turned on TE premium. Reading a single global column
misprices whole position groups, so every KTC lookup resolves its column from
the league's own Sleeper settings.

Both axes come from data Sleeper already syncs, so a league that changes its
roster or scoring settings switches columns on the next sync with no code
change — which is how Insight2Dynasty picks up superflex values when it adds
the slot in 2027.
"""
from dataclasses import dataclass
from typing import Any, Optional

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import League, Season
from app.models.player_value import PlayerValue

SUPERFLEX = "superflex"
ONE_QB = "1qb"


def te_premium_from_scoring(scoring_settings: Optional[dict[str, Any]]) -> bool:
    """Whether a league awards tight ends a per-reception bonus.

    Any positive bonus reads as TE premium. KTC's tepp (+1.0) and teppp (+1.5)
    tiers saturate elite tight ends at the 9999 ceiling and stop
    discriminating between them, so a single premium column serves every
    premium league better than tier-matching would.
    """
    if not scoring_settings:
        return False
    try:
        return float(scoring_settings.get("bonus_rec_te") or 0) > 0
    except (TypeError, ValueError):
        return False


def scoring_format_from_positions(roster_positions: Optional[list[str]]) -> str:
    """'superflex' when a SUPER_FLEX slot is startable, else '1qb'."""
    return SUPERFLEX if "SUPER_FLEX" in (roster_positions or []) else ONE_QB


@dataclass(frozen=True)
class LeagueValueFormat:
    """The (format, premium) pair that picks a league's KTC value columns."""

    scoring_format: str = ONE_QB
    te_premium: bool = False

    @property
    def superflex(self) -> bool:
        return self.scoring_format == SUPERFLEX

    @property
    def without_te_premium(self) -> "LeagueValueFormat":
        """The same format with the TE bonus dropped.

        Draft picks are unpositioned assets, so a tight-end bonus cannot apply
        to them, but the superflex axis still does.
        """
        return LeagueValueFormat(self.scoring_format, te_premium=False)

    @property
    def value_column(self):
        """A SQL expression for this league's value, usable in ORDER BY.

        Specialised columns are only populated for players KTC ranks, so each
        coalesces down to the next-broadest column. Without that, an unranked
        player reads as NULL and sorts as though worthless.
        """
        return self._column(
            PlayerValue.tep_value,
            PlayerValue.superflex_tep_value,
            PlayerValue.superflex_value,
            PlayerValue.value,
        )

    @property
    def rank_column(self):
        return self._column(
            PlayerValue.tep_rank,
            PlayerValue.superflex_tep_rank,
            PlayerValue.superflex_rank,
            PlayerValue.rank,
        )

    def _column(self, tep, superflex_tep, superflex, base):
        if self.superflex and self.te_premium:
            return func.coalesce(superflex_tep, superflex, base)
        if self.superflex:
            return func.coalesce(superflex, base)
        if self.te_premium:
            return func.coalesce(tep, base)
        return base


async def get_league_value_format(
    db: AsyncSession, league_id: str
) -> LeagueValueFormat:
    """Resolve the value format for a league group from its latest season.

    Falls back to plain 1QB when the league has not been synced yet, so the
    pages that call this degrade to the old behaviour instead of failing.
    """
    result = await db.execute(
        select(League)
        .join(Season, League.id == Season.league_id)
        .where(Season.group_id == league_id)
        .order_by(desc(Season.year))
        .limit(1)
    )
    league = result.scalar_one_or_none()
    if league is None:
        return LeagueValueFormat()

    return LeagueValueFormat(
        scoring_format=scoring_format_from_positions(league.roster_positions),
        te_premium=te_premium_from_scoring(league.scoring_settings),
    )
