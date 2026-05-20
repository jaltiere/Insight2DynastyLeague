# Roster Analysis

The Roster Analysis page evaluates every team's roster construction and assigns a dynasty-context **classification** based on two dimensions: roster age and overall strength. It reuses the same player power score engine as Power Rankings.

## Team Classifications

Each team is placed into one of four categories using a 2×2 matrix of **Age** vs **Strength**.

|  | **Strong** (score ≥ league median) | **Weak** (score < league median) |
|---|---|---|
| **Young** (avg age ≤ 25.5) | Future Contender | Rebuilding |
| **Veteran** (avg age > 25.5) | Win Now | Retooling |

Strength is relative — it is compared against the **median total roster score** across all teams that week, not an absolute threshold. A team that would be "strong" in a weaker league might be "weak" in a stronger one.

### Category Definitions

| Category | Meaning |
|---|---|
| **Win Now** | Veteran, high-value roster — built for immediate success, limited future runway |
| **Future Contender** | Young, high-value roster — best of both worlds; competing now with upside remaining |
| **Rebuilding** | Young, low-value roster — sacrificing near-term results for future potential |
| **Retooling** | Veteran, low-value roster — aging roster that isn't winning; needs a strategy change |

---

## How Total Roster Score Is Calculated

Each player on the roster receives a **player power score** (max 30 pts), and the team's total roster score is the sum of all player scores.

### Player Power Score (max 30 pts)

Three components are summed for each player:

#### 1. Age Score (max 10 pts)

| Age | Score |
|-----|-------|
| ≤ 25 | 10.0 |
| 26–27 | 8.0 |
| 28–29 | 5.0 |
| 30+ | 2.0 |
| Unknown (estimated from years_exp) | Same tiers, using `22 + years_exp` |
| No age data | 5.0 (default) |

#### 2. Position Score (max 10 pts)

| Position | Score |
|----------|-------|
| QB | 10.0 |
| RB | 9.0 |
| WR | 8.0 |
| TE | 7.0 |
| DEF | 4.0 |
| K | 3.0 |
| Other | 5.0 |

#### 3. Production Score (max 10 pts)

Based on the player's career average points per game (all recorded games in the database):

```
production_score = min(10.0, (avg_ppg / 20.0) * 10)
```

- 20+ ppg → 10.0 pts
- 10 ppg → 5.0 pts
- Active player with no recorded games → 2.0 pts
- Inactive player with no recorded games → 0.5 pts

---

## How Average Roster Age Is Calculated

Average age is computed across every player on the full roster (not just starters):

1. Use `player.age` when available.
2. Fall back to `22 + player.years_exp` when age is missing.
3. Skip players with neither field.
4. Default to **27.0** if no players have age data.

The age threshold for "Young" vs "Veteran" is **25.5**.

---

## Classification Logic (code reference)

[roster_analysis.py:19–37](../backend/app/api/routes/roster_analysis.py#L19-L37)

```python
def _classify_team(avg_age, total_score, median_score):
    young  = avg_age <= 25.5
    strong = total_score >= median_score
    if young and strong:   return "Future Contender"
    if not young and strong: return "Win Now"
    if young and not strong: return "Rebuilding"
    return "Retooling"
```

The `median_score` is the statistical median (not mean) of all teams' total roster scores, recalculated on every request.

---

## API Endpoint

```
GET /api/roster-analysis
```

No authentication required. Always returns data for the **most recent season**.

**Response shape:**

```json
{
  "season": 2026,
  "teams": [
    {
      "roster_id": 3,
      "owner_name": "ankurdeora",
      "team_name": "Brown Indians",
      "avatar": "abc123",
      "avg_age": 25.1,
      "total_roster_score": 412.5,
      "player_count": 24,
      "classification": "Future Contender",
      "positional_scores": { "QB": 28.0, "RB": 95.4, "WR": 143.2, "TE": 45.1 },
      "positional_counts": { "QB": 2, "RB": 6, "WR": 9, "TE": 3 },
      "players": [
        {
          "player_id": "8146",
          "player_name": "Ja'Marr Chase",
          "position": "WR",
          "team": "CIN",
          "age": 25,
          "power_score": 27.8
        }
      ]
    }
  ]
}
```

Players within each team are sorted by position order (QB → RB → WR → TE → K → DEF), then by power score descending. Teams are sorted by total roster score descending.

---

## Shared Logic with Power Rankings

Roster Analysis reuses three functions from [power_rankings.py](../backend/app/api/routes/power_rankings.py):

| Function | Purpose |
|---|---|
| `_calculate_player_stats` | Bulk-fetches career average PPG for all players in one DB round-trip |
| `_calculate_player_power_score` | Computes age + position + production scores per player |
| `_calculate_avg_roster_age` | Averages player ages with years_exp fallback |

Any change to these functions affects both pages.
