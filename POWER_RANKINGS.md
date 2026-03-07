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
- Peak scoring: ages 22-25
- Formula: Normalized curve with bonus for young core
- Example: 25.5 avg age → **13.2 points**

#### 2. Positional Value (15 points)
- Weighted by player production scores
- Counts elite players (power_score > threshold) at premium positions
- QB/RB/WR valued higher than K/DEF
- Formula: Based on distribution of top-tier players

#### 3. Roster Depth (10 points)
- Count of startable players (production_score > threshold)
- Weighted by position scarcity
- Example: 18 startable players → **8.5 points**

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
- K/DEF: 3 points

**Production Score (max 10 pts):**
- Based on rolling 15-game average points per game
- 0 ppg → 0 points
- 20+ ppg → 10 points
- Scales linearly between 0-20 ppg
- Formula: `min(10, (avg_ppg / 20) * 10)`

**Total Player Power Score:**
```
player_power_score = age_score + position_score + production_score
Max: 30 points per player
```

## Historical Performance (20 points)

Evaluates sustained success over the last 3 seasons.

### Components

#### 1. Playoff Appearances (8 points)
- Last 3 seasons
- Formula: `(playoff_appearances / 3) * 8`
- Example: 2 playoff appearances → 2/3 * 8 = **5.3 points**

#### 2. Championships (8 points)
- Last 3 seasons
- Formula: `(championships / 3) * 8`
- Example: 1 championship → 1/3 * 8 = **2.7 points**

#### 3. Consistency (4 points)
- Based on standard deviation of win totals
- Lower deviation = more consistent = higher score
- Formula: `max(0, 4 - (stdev_wins / 3))`
- Example: stdev of 2.5 wins → 4 - (2.5/3) = **3.2 points**

## Example Calculation

**Brown Indians (2025 Season):**

| Component | Calculation | Points |
|-----------|-------------|--------|
| Win % (10-5) | 0.667 * 15 | 10.0 |
| Points Percentile (143.9 ppg, 2nd) | 0.909 * 12 | 10.9 |
| Point Differential (+10) | (10+20)/5 | 6.0 |
| Recent Form (2-1) | 0.667 * 5 | 3.3 |
| **Current Season Total** | | **30.2** |
| Average Roster Age (25.5) | | 13.2 |
| Positional Value | | 12.5 |
| Roster Depth (18 players) | | 9.2 |
| **Roster Value Total** | | **34.9** |
| Playoff Appearances (2/3) | 2/3 * 8 | 5.3 |
| Championships (1/3) | 1/3 * 8 | 2.7 |
| Consistency (stdev 2.5) | 4 - 2.5/3 | 3.2 |
| **Historical Total** | | **11.2** |
| **TOTAL POWER RANKING** | | **76.3** |

## API Endpoints

### Get Power Rankings
```
GET /api/power-rankings
GET /api/power-rankings/{season_year}
```

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
      "team_name": "Macedonia Moose",
      "total_score": 77.92,
      "current_season_score": 35.17,
      "roster_value_score": 30.41,
      "historical_score": 12.34,
      "wins": 22,
      "losses": 6,
      "ties": 0,
      "points_for": 2027.3,
      "avg_roster_age": 27.4
    }
  ]
}
```

### Get Roster Breakdown
```
GET /api/power-rankings/{season_year}/roster/{roster_id}
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

## Frontend Visualization

### Bar Chart
- Horizontal bars sorted by rank
- Color-coded by performance:
  - 🟢 Green (#059669): Rank 1
  - 🟢 Light Green (#10B981): Ranks 2-3
  - 🔵 Blue (#3B82F6): Ranks 4-6
  - 🟣 Indigo (#6366F1): Ranks 7-9
  - ⚪ Gray (#9CA3AF): Ranks 10+

### Interactive Features
- Click any bar or table row to view roster breakdown
- Modal shows individual player power scores
- Sortable by total score, current season, roster value, or historical

## Algorithm Philosophy

The power rankings balance:
1. **Current Performance (40%)**: Rewards teams performing well now
2. **Dynasty Value (40%)**: Emphasizes young talent and future potential
3. **Track Record (20%)**: Respects sustained success

This weighting creates a **forward-looking dynasty ranking** that values both current competitiveness and long-term roster construction.

## Recent Fixes

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
