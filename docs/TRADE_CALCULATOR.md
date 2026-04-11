# Trade Calculator

The Trade Calculator is a roster-aware trade evaluation tool built specifically for this league. It uses KeepTradeCut (KTC) values as the primary valuation source, augmented with league-specific context that generic trade tools can't provide.

## Overview

Both sides of a trade must be league owners. You browse each owner's actual roster and picks, select assets to include on each side, and the calculator evaluates the trade in real time.

### What makes it league-specific

| Feature | What it shows |
|---------|---------------|
| **League PPG delta** | How far above/below the position average a player scores in *this* league's scoring settings |
| **Roster fit badges** | Whether a player or pick fits the receiving team's competitive window |
| **H2H trade history** | All past trades between the two selected owners, graded and expandable |
| **Fair zone** | A ±6% buffer around 50/50 — trades within the zone are considered fair |
| **Fairness suggestion** | Assets from the losing side's actual roster that would bring the trade closest to even |

---

## Valuation Model

### Player values (KTC)

Player values are fetched from [keeptradecut.com/dynasty-rankings](https://keeptradecut.com/dynasty-rankings?picks=1) and cached in the `player_values` table. KTC embeds a `var playersArray` JavaScript variable in its HTML; the backend scrapes and parses this on each sync.

- Format: `1QB` (configurable via `KTC_SCORING_FORMAT` in `config.py`)
- Values range roughly 0–10,000
- Players not found on KTC show a value of 0

### Pick values (KTC)

KTC lists picks as `position: "RDP"` entries with names like `"2026 Early 1st"`. These are stored with a canonical key: `"{year}_{round}_{tier}"` (e.g. `2026_1_early`).

Pick tier is estimated dynamically at query time from the **original team's current record**:

| Record rank (among all teams) | Tier |
|-------------------------------|------|
| Bottom third (worst records) | `early` — highest value, picks first |
| Middle third | `mid` |
| Top third (best records) | `late` — lowest value, picks last |

This means a 2026 1st from a rebuilding team is valued higher than a 2026 1st from a contender, which reflects real dynasty market dynamics.

---

## League PPG Delta

Each player's roster card shows a green or red percentage badge next to their name:

- `+18%` — this player scores 18% more per game than the average player at their position across this entire league
- `−9%` — this player scores 9% below the league average for their position

**How it's calculated:**

1. Every player on every roster in the current season is fetched
2. Each player's all-time average PPG in this league is computed from `matchup_player_points`
3. A position-level average is built from all active rostered players at that position
4. The individual player's PPG is compared to that position average: `((player_ppg - pos_avg) / pos_avg) * 100`

This surfaces players who consistently over- or under-perform their KTC ranking in your specific league's scoring context.

---

## Roster Fit Badges

When assets are selected for trade, each asset in the "Sending" column shows a fit badge based on the **receiving team's classification**:

| Asset | Receiving team | Badge |
|-------|----------------|-------|
| Draft pick | Win Now | `⚠ win-now team` |
| Draft pick | Rebuilding / Future Contender | `✓ fits window` |
| Player age ≥ 28 | Win Now | `✓ fits window` |
| Player age ≥ 28 | Rebuilding | `⚠ aging out` |
| Player age ≤ 24 | Rebuilding / Future Contender | `✓ fits window` |
| Player age ≤ 24 | Win Now | `⚠ long-term fit` |

Team classifications (Win Now, Future Contender, Rebuilding, Retooling) are derived from the same algorithm used by the [Power Rankings](./POWER_RANKINGS.md) — a combination of average roster age and total roster power score relative to the league median.

---

## Fair Zone

The value bar shows each side's share of total trade value. A **green bracket** below the bar marks the fair zone: any split between 44% and 56% is considered fair.

- Trades inside the zone display: **✓ Fair trade**
- Trades outside the zone display the winning side, the value gap, and a suggestion panel

The ±6% threshold was chosen to account for normal valuation uncertainty and negotiation variance.

---

## Fairness Suggestions

When a trade is outside the fair zone, the calculator identifies which assets from the **losing side's own roster** (players and picks they actually own) would bring the trade closest to even. Up to 4 suggestions are shown, sorted by how close each asset's value is to closing the gap.

If no single asset on the losing side's roster is close enough, the panel displays:
> "No single asset on [owner]'s roster closes this gap — a package deal or restructured trade may be needed."

---

## H2H Trade History

When both owners are selected, a trade history panel appears below the result card showing all past trades between these two owners. Each trade row displays:

- Season and week
- Both sides' names and grades (e.g. `A+`, `B−`)
- Who won the trade at the time of grading

Clicking a row expands it to show the exact assets each side received, with position badges. Trades flagged as anomalies (e.g. incomplete data) are shown as "ungraded."

Trade grades come from the [Trade Grading](./TRADE_GRADING.md) system.

---

## Data Sync

KTC values are refreshed automatically as part of the daily sync (`POST /api/sync/league`). They can also be refreshed manually:

```bash
curl -X POST "https://api.insight2dynasty.com/api/trade-calculator/refresh" \
  -H "Authorization: Bearer $CRON_SECRET"
```

The refresh fetches the KTC page, parses `playersArray`, fuzzy-matches player names against the `players` table (stripping accents, suffixes like Jr/Sr/II, and punctuation), and upserts into `player_values`.

---

## Key Files

| File | Purpose |
|------|---------|
| `backend/app/services/ktc_service.py` | KTC fetch, parse, name normalization, upsert |
| `backend/app/api/routes/trade_calculator.py` | All trade calculator API endpoints |
| `backend/app/models/player_value.py` | `player_values` table model |
| `frontend/src/pages/TradeCalculator.tsx` | Full UI — panels, value bar, suggestions, H2H history |
| `frontend/src/services/api.ts` | API client calls for trade calculator endpoints |

---

## API Endpoints

All under `/api/trade-calculator/`:

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/owners` | All current-season owners with classification and avg age |
| `GET` | `/roster/{user_id}` | Owner's roster with KTC values and league PPG delta |
| `GET` | `/roster-picks/{user_id}` | Picks owned by this team, tiered by standing |
| `GET` | `/pick-values` | All cached pick values from KTC |
| `GET` | `/h2h-trades/{uid_a}/{uid_b}` | Trade history between two owners |
| `POST` | `/refresh` | Trigger a KTC value refresh (requires `CRON_SECRET`) |

---

## Configuration

| Setting | Location | Default | Description |
|---------|----------|---------|-------------|
| `KTC_SCORING_FORMAT` | `backend/app/config.py` | `"1qb"` | KTC scoring format; change to `"superflex"` if league format changes |
