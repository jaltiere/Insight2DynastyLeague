# Trade Grading Algorithm

## Overview

The trade grading system evaluates completed trades by analyzing the **actual performance** of all assets exchanged (players and draft picks) after the trade date. Each side receives a letter grade (A+ through F) based on their share of the total value generated.

**Key Principle**: Grades are retrospective, not predictive. We measure what actually happened, not what was expected at the time of the trade.

## Grading Scale

The grading scale is centered around 50% value share (a fair trade) to create a balanced distribution:

| Grade | Value Share | Interpretation |
|-------|-------------|----------------|
| **A+** | 70%+ | Clearly won the trade |
| **A** | 65-69% | Won handily |
| **A-** | 60-64% | Won solidly |
| **B+** | 56-59% | Won slightly |
| **B** | 52-55% | Slight edge |
| **B-** | 48-51% | Essentially even |
| **C+** | 44-47% | Slight loss |
| **C** | 40-43% | Lost slightly |
| **C-** | 35-39% | Lost solidly |
| **D+** | 30-34% | Lost handily |
| **D** | 25-29% | Clearly lost |
| **D-** | 20-24% | Badly lost |
| **F** | <20% | Catastrophically lost |

### Example: 2-Sided Trade Outcomes

- **60/40 split**: A- vs C (moderately imbalanced)
- **55/45 split**: B vs C+ (slightly favors one side)
- **50/50 split**: B- vs B- (perfectly fair)
- **70/30 split**: A+ vs D+ (clearly lopsided)

## Algorithm Components

### 1. Player Value Calculation

Each player's value is the **weighted sum of all points scored** after the trade date, weighted by whether they were started or benched.

#### Weighting Formula

```python
STARTER_WEIGHT = 1.5
BENCH_WEIGHT = 0.1

player_value = Σ (points × weight)
  where weight = STARTER_WEIGHT if started, else BENCH_WEIGHT
```

#### Why Weight by Starter Status?

- **Starters (1.5x)**: Premium for players who actually helped win matchups
- **Bench (0.1x)**: Minimal credit for unused depth
- This rewards acquiring players who become starters and penalizes trading away starters who become bench pieces

#### Examples

**Scenario A**: Player scores 20 points/week as a starter for 5 weeks
```
Value = 20 × 1.5 × 5 = 150 points
```

**Scenario B**: Player scores 20 points/week on bench for 5 weeks
```
Value = 20 × 0.1 × 5 = 10 points
```

**Scenario C**: Mixed usage
- Week 1-3: Started, scored 15 pts/week = 15 × 1.5 × 3 = 67.5
- Week 4-6: Benched, scored 12 pts/week = 12 × 0.1 × 3 = 3.6
- Total value = 71.1 points

### 2. Replacement Factor Adjustment

The replacement factor accounts for how well a team filled the hole left by trading away a player. This prevents inflating the value of players acquired when the trading partner had adequate replacements.

#### Formula

```python
REPLACEMENT_WINDOW = 4  # weeks before/after trade

before_avg = average position points in weeks [trade_week - 4, trade_week]
after_avg = average position points in weeks [trade_week + 1, trade_week + 4]

if after_avg >= before_avg:
    replacement_factor = 0.5  # Replaced perfectly
elif before_avg <= 0:
    replacement_factor = 1.0  # No baseline
else:
    replacement_factor = 1.0 - (after_avg / before_avg) × 0.5
```

#### Interpretation

- **0.5**: Team completely replaced the player (same production at position)
- **1.0**: Team did not replace the player (big hole at position)
- **0.5-1.0**: Partial replacement

#### Why Adjust for Replacement?

Without this factor, trading away a star WR would always look bad even if you had another star WR ready to step in. The replacement factor ensures we measure the **actual impact** on roster strength, not just raw player value.

#### Example

**Trade**: Team A sends WR1 (20 pts/week) to Team B, receives RB2 (10 pts/week)

**Team A's WR Position Before Trade**:
- Weeks 1-5: WR1 starting, averaging 20 pts/week
- Replacement factor calculation looks at WR production

**Team A's WR Position After Trade**:
- Weeks 6-10: WR2 (from bench) now starts, also averaging 20 pts/week
- Replacement factor = 0.5 (perfect replacement)

**Result**: WR1's value to Team B is reduced by 50% because Team A didn't actually lose production at WR.

### 3. Draft Pick Valuation

Draft picks are valued differently based on whether they've been used:

#### 3a. Resolved Picks (Already Drafted)

If the draft has occurred and we know which player was selected:

```python
pick_value = actual_player_value
  (calculated same as any other player)
```

The player drafted with the pick is treated like any other player in the trade, with full weighted scoring.

#### 3b. Projected Picks (Future/Unused)

For picks that haven't been used yet:

```python
FUTURE_PICK_DISCOUNT = 0.7

pick_baseline = average weighted points per week for all players
                historically drafted in this round

weeks_estimate = weeks of data since trade
                (accounts for multiple seasons if applicable)

pick_value = pick_baseline × weeks_estimate × FUTURE_PICK_DISCOUNT
```

#### Pick Baselines Calculation

For each round (1-15), we calculate the historical average performance:

```python
For each player ever drafted in round N:
    weighted_total = Σ (points × starter_weight or bench_weight)
    weeks_played = count of weeks with data
    ppw = weighted_total / weeks_played

round_N_baseline = average(ppw for all round N players)
```

#### Why Discount Future Picks?

- **Uncertainty**: We don't know who will be drafted
- **Risk**: Pick might bust or miss
- **Conservative**: 70% discount ensures we don't overvalue speculation

#### Example

**2025 1st Round Pick** traded in Week 5 of 2024:
- Round 1 baseline: 12.5 weighted points/week (historical average)
- Weeks since trade: 20 weeks (rest of 2024 + 5 weeks of 2025)
- Projected value: 12.5 × 20 × 0.7 = **175 points**

If the pick is later used to draft Player X who scores 15 weighted pts/week for 30 weeks:
- Actual value: 15 × 30 = **450 points**
- The grade would be recalculated with the real value once known

### 4. Final Grade Computation

#### Step 1: Calculate Total Value Per Side

For each side of the trade:

```python
side_value = 0

# Players received
for player in players_received:
    player_value = Σ (weighted_points_after_trade)
    replacement_factor = calculate_replacement_factor(player)
    adjusted_value = player_value × replacement_factor
    side_value += adjusted_value

# Draft picks received
for pick in picks_received:
    if pick.is_resolved:
        pick_value = drafted_player_value  # actual
    else:
        pick_value = baseline × weeks × discount  # projected
    side_value += pick_value
```

#### Step 2: Compute Value Share

```python
total_trade_value = sum(side_value for all sides)

for each side:
    value_share = side_value / total_trade_value
```

#### Step 3: Assign Letter Grade

```python
grade = lookup_grade(value_share)
  # Using the grading scale table above
```

## Data Requirements

For accurate grading, the algorithm requires:

1. **Matchup player points**: All scoring data after trade date
   - Player ID
   - Points scored
   - Starter status (TRUE/FALSE)
   - Week and season

2. **Roster ownership**: Who owned which players when
   - Needed to attribute points to correct owner
   - Handles mid-season trades and roster changes

3. **Draft data**: For pick resolution
   - Draft order (slot assignments)
   - Pick selections (round, slot, player drafted)

4. **Position data**: For replacement factor
   - Player positions (QB, RB, WR, TE)
   - Positional scoring by week

## Limitations & Considerations

### Time Horizon Bias

**Issue**: Older trades have more data and may appear more definitive.

**Mitigation**: The `weeks_of_data` field is returned so users can assess confidence.

**Example**:
- Trade from Week 1 with 3 seasons of data: High confidence
- Trade from Week 12 with 2 weeks of data: Low confidence, preliminary grade

### Injury Impact

**Issue**: Injuries after trades can make trades look worse/better than expected.

**Reality**: This is intentional. Trades involve risk, and injury outcomes are part of the result. A player who gets injured after being traded did not provide value, regardless of expectations.

### Multi-Team Trades

**Supported**: The algorithm handles N-sided trades.

**Grading**: Each team gets a grade based on their value share.

**Example 3-team trade**:
- Team A: 50% share → B grade
- Team B: 30% share → D+ grade
- Team C: 20% share → D- grade

### Picks Not Yet Drafted

**Issue**: Future picks are speculative and may be under/overvalued.

**Solution**: Grades are **recalculated** once picks are used and we have actual player data.

**Best Practice**: Filter to trades with resolved picks for most accurate grading, or note the `status: "projected"` field in pick details.

## API Response Structure

```json
{
  "trade_id": "txn_12345",
  "season": 2024,
  "week": 5,
  "date": 1700000000000,
  "weeks_of_data": 23,
  "lopsidedness": 0.2500,
  "sides": [
    {
      "roster_id": 1,
      "owner_name": "Owner One",
      "user_id": "user1",
      "grade": "A",
      "total_value": 450.5,
      "value_share": 0.6500,
      "assets_received": {
        "players": [
          {
            "player_id": "1234",
            "player_name": "Ja'Marr Chase",
            "position": "WR",
            "weighted_points": 380.5,
            "adjusted_points": 285.4,
            "starter_weeks": 15,
            "bench_weeks": 2,
            "replacement_factor": 0.75
          }
        ],
        "draft_picks": [
          {
            "season": 2025,
            "round": 2,
            "status": "actual",
            "value": 170.0,
            "drafted_player": "Brock Bowers"
          }
        ]
      }
    },
    {
      "roster_id": 2,
      "owner_name": "Owner Two",
      "user_id": "user2",
      "grade": "C-",
      "total_value": 242.8,
      "value_share": 0.3500,
      "assets_received": {
        "players": [
          {
            "player_id": "5678",
            "player_name": "Tony Pollard",
            "position": "RB",
            "weighted_points": 180.5,
            "adjusted_points": 180.5,
            "starter_weeks": 12,
            "bench_weeks": 0,
            "replacement_factor": 1.0
          }
        ],
        "draft_picks": []
      }
    }
  ]
}
```

## Implementation Files

- **Service**: `backend/app/services/trade_grading.py`
- **API Routes**: `backend/app/api/routes/trade_grades.py`
- **Tests**: `backend/tests/test_trade_grades.py`
- **Database Models**: `backend/app/models/transaction.py`, `matchup.py`, `draft.py`

## Future Enhancements

Potential improvements to consider:

1. **Age Curves**: Adjust value for player age/career stage
2. **Positional Scarcity**: Weight by position scarcity (premium for elite QBs)
3. **Playoff Impact**: Extra weight for playoff weeks
4. **Trade Context**: Account for team situation (rebuilding vs contending)
5. **Pick Value Curves**: More sophisticated draft pick valuations based on league history
6. **Confidence Intervals**: Show grade uncertainty based on sample size

---

**Last Updated**: March 2026
**Algorithm Version**: 1.0
