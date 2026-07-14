# Power Rankings Algorithm

The Power Rankings feature provides a comprehensive evaluation of dynasty league teams based on current performance, roster value (with emphasis on player age for dynasty), and historical success.

## Overview

Teams are ranked on a **100-point scale** with three weighted components:

| Component | Weight | Max Points | Focus |
|-----------|--------|------------|-------|
| **Current Season Performance** | 40% | 40 pts | Recent form, win rate, scoring |
| **Roster Value** | 40% | 40 pts | Player ages, positional value, depth |
| **Historical Performance** | 20% | 20 pts | Championships, playoffs, consistency |

## Current Season Performance (40 points)

Uses a **rolling 15-game window** to evaluate recent performance, preventing zeros at season start and capturing trends across season boundaries.

### Components

#### 1. Win Percentage (15 points)
- Based on last 15 games
- Formula: `win_percentage * 15`
- Example: 10-5 record → 0.667 * 15 = **10.0 points**

#### 2. Points For Percentile (12 points)
- Compares average points per game against all teams
- Uses rolling 15-game average
- Formula: `(teams_with_lower_avg / total_teams) * 12`
- Example: 143.9 ppg ranking 2nd out of 12 teams → 0.909 * 12 = **10.9 points**

#### 3. Point Differential (8 points)
- Average margin of victory/defeat
- Scaled from -20 to +20 point range
- Formula: `min(8, max(0, (avg_diff + 20) / 5))`
- Example: +10 avg differential → (10 + 20) / 5 = **6.0 points**

#### 4. Recent Form (5 points)
- Win percentage of last 3 games only
- Formula: `recent_win_pct * 5`
- Example: 2-1 in last 3 games → 0.667 * 5 = **3.3 points**

### Rolling Window Implementation

The rolling 15-game window:
- Orders games chronologically by `(season_year DESC, week DESC)`
- Pulls from multiple seasons if needed
- Tracks performance across season boundaries
- Prevents empty/zero scores at season start

**Query Logic:**
```python
select(Matchup, Season.year)
  .join(Season, Matchup.season_id == Season.id)
  .where((home_roster_id IN user_rosters) OR (away_roster_id IN user_rosters))
  .order_by(desc(Season.year), desc(Matchup.week))
  .limit(15)
```

## Roster Value (40 points)

Dynasty-focused scoring emphasizing young talent and roster construction.

### Components

#### 1. Average Roster Age (15 points)
- Younger rosters score higher (dynasty focus)
- Age-to-score curve:
  - ≤ 25: 1.0 → **15.0 points**
  - 26–28: `1.0 - (age - 25) * 0.1` → linear decline
  - 29+: `max(0.3, 0.7 - (age - 28) * 0.1)` → floor at 0.3 → **4.5 points minimum**
- Formula: `age_score * 15`
- Example: 25.5 avg age → 0.95 * 15 = **14.25 points**

#### 2. Player Production Value (15 points)
- Sums normalized production across all roster players
- Each player contributes `min(1.0, avg_ppg / 20.0)` to the total
- Total is capped at 15
- Formula: `min(15, Σ min(1.0, player_avg_ppg / 20.0))`
- Example: 12 starters averaging 10 ppg → 12 * 0.5 = 6.0, plus bench depth

#### 3. Roster Depth (10 points)
- Count of startable players × 0.5, capped at 10
- A player is **startable** if Active status, position is QB/RB/WR/TE, and
  age is below a **position-aware ceiling** (QB < 38, TE < 33, WR < 32,
  RB < 30). Positions age very differently, so a single flat cutoff wrongly
  zeroed out veteran QBs/WRs/TEs.
- Formula: `min(10, startable_count * 0.5)`
- Example: 18 startable players → min(10, 9.0) = **9.0 points**

### Player Power Scores

Individual player rankings based on:

**Age Score (max 10 pts):**
- Ages 22-25: 10 points (prime dynasty value)
- Ages 26-27: 8 points
- Ages 28-29: 5 points
- Ages 30+: 2 points
- Rookies: 7 points (potential)

**Position Score (max 10 pts):**
- QB: 10 points (premium scoring position)
- RB: 9 points (scarcity)
- WR: 8 points (volume)
- TE: 7 points (positional advantage)
- DEF: 4 points
- K: 3 points
- Other: 5 points (default)

**Production Score (max 10 pts):**
- Based on career average points per game
- 0 ppg (active player) → 2.0 points; inactive → 0.5 points
- 20+ ppg → 10 points
- Scales linearly between 0-20 ppg
- Formula: `min(10, (avg_ppg / 20) * 10)` when avg_ppg > 0

**Total Player Power Score:**
```
player_power_score = age_score + position_score + production_score
Max: 30 points per player
```

## Historical Performance (20 points)

Evaluates all-time success based on season awards accumulated across the full league history.

### Components

#### 1. Championships (10 points)
- Counts all-time championship wins
- Formula: `min(10, championships * 5)`
- Example: 1 championship → 5.0 pts; 2 championships → 10.0 pts (capped)

#### 2. Playoff Appearances (10 points)
- Counts all-time playoff appearances (champion + division_winner awards)
- Formula: `min(10, playoff_appearances * 3.5)`
- Example: 1 appearance → 3.5 pts; 3 appearances → 10.0 pts (capped)

The two components sum to the 20-point max. (A previous version capped each
at 8 with a flat 2-point baseline; the baseline was rank-neutral dead weight,
and championships now count for a little more.)

## Example Calculation

**Brown Indians (2025 Season):**

| Component | Calculation | Points |
|-----------|-------------|--------|
| Win % (10-5) | 0.667 * 15 | 10.0 |
| Points Percentile (143.9 ppg, 2nd) | 0.909 * 12 | 10.9 |
| Point Differential (+10) | (10+20)/5 | 6.0 |
| Recent Form (2-1) | 0.667 * 5 | 3.3 |
| **Current Season Total** | | **30.2** |
| Average Roster Age (25.5) | (1.0 - 0.05) * 15 | 14.25 |
| Player Production Value | Σ normalized ppg, capped 15 | 12.5 |
| Roster Depth (18 startable) | min(10, 18 * 0.5) | 9.0 |
| **Roster Value Total** | | **35.75** |
| Championships (1) | min(8, 1 * 5) | 5.0 |
| Playoff Appearances (3) | min(8, 3 * 2.67) | 8.0 |
| Consistency Baseline | flat | 2.0 |
| **Historical Total** | | **15.0** |
| **TOTAL POWER RANKING** | | **80.95** |

## API Endpoints

### Get Power Rankings
```
GET /api/{league_slug}/power-rankings
GET /api/{league_slug}/power-rankings/{season_year}
```

Includes `rank_change` and `previous_rank` fields populated from the most recent weekly snapshot (both `null` before first snapshot is saved).

**Response:**
```json
{
  "season": 2026,
  "rankings": [
    {
      "rank": 1,
      "roster_id": 7,
      "user_id": "852976104321982464",
      "username": "mbrenner00",
      "display_name": "Macedonia Moose Owner",
      "team_name": "Macedonia Moose",
      "total_score": 77.92,
      "current_season_score": 35.17,
      "roster_value_score": 30.41,
      "historical_score": 12.34,
      "wins": 22,
      "losses": 6,
      "ties": 0,
      "points_for": 2027.3,
      "avg_roster_age": 27.4,
      "rank_change": 2,
      "previous_rank": 3
    }
  ]
}
```

`rank_change` is positive when a team moved up (e.g., `2` means rose 2 spots), negative when down, `0` for unchanged, `null` before any snapshot exists.

### Get Roster Breakdown
```
GET /api/{league_slug}/power-rankings/{season_year}/roster/{roster_id}
```

**Response:**
```json
{
  "roster_id": 3,
  "team_name": "Brown Indians",
  "owner_name": "ankurdeora",
  "total_roster_score": 34.93,
  "avg_roster_age": 25.5,
  "players": [
    {
      "player_id": "8146",
      "player_name": "Ja'Marr Chase",
      "position": "WR",
      "team": "CIN",
      "age": 25,
      "power_score": 27.8,
      "age_score": 10.0,
      "position_score": 8.0,
      "production_score": 9.8
    }
  ]
}
```

### Get Rank Trajectory (Trends)
```
GET /api/{league_slug}/power-rankings/{season_year}/trends
```

Returns all weekly snapshots for the season, formatted for the rank trajectory line chart. Returns empty `weeks` and `teams` arrays before first snapshot is saved (offseason-safe).

**Response:**
```json
{
  "season": 2026,
  "weeks": [1, 2, 3, 4],
  "teams": [
    {
      "roster_id": 7,
      "display_name": "mbrenner00",
      "team_name": "Macedonia Moose",
      "current_rank": 1,
      "ranks_by_week": [
        { "week": 1, "rank": 3, "total_score": 74.1 },
        { "week": 2, "rank": 2, "total_score": 75.8 },
        { "week": 3, "rank": 1, "total_score": 77.92 }
      ]
    }
  ]
}
```

### Save Snapshot (Admin)
```
POST /api/{league_slug}/power-rankings/snapshot?season_year={year}&week={week}
Authorization: Bearer {CRON_SECRET}
```

Calculates and upserts a weekly snapshot for all teams. Called automatically by Tuesday sync; can also be triggered manually.

**Response:**
```json
{ "status": "ok", "week": 5, "season_year": 2026, "teams_saved": 12 }
```

## Weekly Snapshot System

### How Snapshots Are Saved
- **Automatic**: Every Tuesday sync saves a snapshot for the week that just completed (same time recaps are generated)
- **Manual**: `POST /api/power-rankings/snapshot?season_year={year}&week={week}` with CRON_SECRET auth
- **Upsert**: Re-running for the same `(season_year, week, roster_id)` updates the existing row

### Database Table: `power_ranking_snapshots`
| Column | Type | Description |
|--------|------|-------------|
| `id` | INT | Primary key |
| `season_year` | INT | e.g. 2026 |
| `week` | INT | NFL week number |
| `roster_id` | INT | Sleeper roster ID |
| `rank` | INT | Rank at snapshot time |
| `total_score` | FLOAT | Overall score |
| `current_season_score` | FLOAT | Current season component |
| `roster_value_score` | FLOAT | Roster value component |
| `historical_score` | FLOAT | Historical component |
| `snapped_at` | DATETIME | When snapshot was saved |

Unique constraint on `(season_year, week, roster_id)`.

### Offseason Behavior
- Snapshot table queries are non-fatal — if the table doesn't exist or returns no rows, the main rankings endpoint still loads normally with `rank_change: null`
- The trend chart on the frontend only renders when at least one week of snapshot data exists
- No new snapshots are saved during offseason (Tuesday sync skips recap/snapshot generation when `season_type == "off"`)

## Implementation Notes

### Database Queries
- All calculations performed server-side for consistency
- Uses `AsyncSession` with SQLAlchemy 2.0
- Queries optimized to minimize database calls
- Rolling window queries join Season table for proper chronological ordering

### Caching
- Frontend caches via React Query (5 minute stale time)
- No server-side caching (calculations are fast enough)
- Recalculates on each request for accuracy

### Edge Cases Handled
1. **New teams (< 15 games)**: Uses available games, no penalties
2. **Missing player ages**: Estimated from years_exp or position defaults
3. **Tie games**: Counted as 0.5 wins in win percentage
4. **Empty rosters**: Returns 0 for roster value components
5. **Division by zero**: Safe handling in all percentile calculations
6. **Missing snapshot table**: Non-fatal; rankings load without trend data

## Frontend Visualization

### Rankings Table
- **Trend column**: ▲N (green, moved up), ▼N (red, moved down), = (unchanged), — (no prior snapshot)
- Click any row to open roster breakdown modal

### Rank Trajectory Chart
- Line chart (Recharts `LineChart`) showing each team's rank week-over-week
- Title: "Rank Trajectory" with subtitle "Lower = better. Week-by-week snapshot."
- Only rendered when at least one week of snapshot data exists (`hasTrends` guard)
- X-axis: week labels formatted as `Wk N` (e.g., "Wk 1", "Wk 5")
- Y-axis: reversed so rank #1 appears at top; domain `[1, total_teams]`; integer ticks only
- Tooltip: rank formatted as `#N` (e.g., "#1", "#3")
- One colored line per team using 12 rotating distinct colors
- Teams sorted by `current_rank` ascending in the legend

### Score Breakdown Bar Chart
- Horizontal bars sorted by rank
- Color-coded by performance:
  - 🟢 Green (#059669): Rank 1
  - 🟢 Light Green (#10B981): Ranks 2-3
  - 🔵 Blue (#3B82F6): Ranks 4-6
  - 🟣 Indigo (#6366F1): Ranks 7-9
  - ⚪ Gray (#9CA3AF): Ranks 10+
- Click any bar to open roster breakdown modal

## Algorithm Philosophy

The power rankings balance:
1. **Current Performance (40%)**: Rewards teams performing well now
2. **Dynasty Value (40%)**: Emphasizes young talent and future potential
3. **Track Record (20%)**: Respects sustained success

This weighting creates a **forward-looking dynasty ranking** that values both current competitiveness and long-term roster construction.

## Recent Fixes & Enhancements

### 2026-04-08: Fix Recharts Tooltip Formatter Type Error (PRs #59, #60)
- **Fix**: `Formatter` type in Recharts expects `value: number | undefined` and `name: string | undefined`
- **Impact**: Production frontend build was failing due to strict TypeScript type mismatch

### 2026-04-08: Added Weekly History & Trend Tracking (PR #58)
- **Feature**: New `power_ranking_snapshots` table stores weekly rank snapshots per team
- **Feature**: Trend arrows (▲/▼/=/—) added to rankings table
- **Feature**: Rank trajectory line chart showing week-by-week movement
- **Feature**: `GET /api/power-rankings/{season}/trends` endpoint
- **Feature**: `POST /api/power-rankings/snapshot` admin endpoint
- **Automation**: Tuesday sync auto-saves snapshots alongside recap generation
- **Fix**: Snapshot queries are non-fatal (no CORS-breaking 500s if table missing)

### 2026-03-07: Fixed Rolling Window Query
- **Issue**: Query ordered by `Matchup.id` instead of chronological order
- **Impact**: Pulled games from wrong seasons, incorrect win percentages
- **Fix**: Join Season table, order by `(Season.year DESC, Matchup.week DESC)`
- **Result**: Brown Indians jumped from rank 6 to rank 4 (+15.37 points)

### 2026-03-06: Fixed Percentile Calculation
- **Issue**: Used `.index()` for float comparison, failed to find exact matches
- **Impact**: Incorrect points for percentile ranking
- **Fix**: Count teams with lower averages using comparison operator
- **Result**: More accurate percentile scores for all teams
