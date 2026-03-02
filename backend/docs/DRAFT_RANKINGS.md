# Draft Rankings Algorithm

## Overview

The draft rankings system evaluates each owner's draft performance by analyzing the **actual performance** of all players they drafted after the draft date. Each owner receives a letter grade (A+ through F) based on their total draft value compared to the league average.

**Key Principle**: Grades are retrospective, not predictive. We measure what actually happened, not what was expected at draft time.

## Grading Scale

The grading scale is centered around 100% (average draft performance) to create a balanced distribution:

| Grade | Value vs Average | Interpretation |
|-------|-----------------|----------------|
| **A+** | 180%+ | Elite draft performance |
| **A** | 160-179% | Excellent draft |
| **A-** | 140-159% | Very good draft |
| **B+** | 120-139% | Good draft |
| **B** | 110-119% | Above average draft |
| **B-** | 90-109% | Average draft |
| **C+** | 80-89% | Below average draft |
| **C** | 70-79% | Poor draft |
| **C-** | 60-69% | Very poor draft |
| **D+** | 50-59% | Bad draft |
| **D** | 40-49% | Very bad draft |
| **D-** | 30-39% | Terrible draft |
| **F** | <30% | Catastrophic draft |

### Example: Draft Outcomes

**Average Draft** (100% of average):
- Total value: 450 points
- League average: 450 points
- Grade: B- (right at average)

**Great Draft** (150% of average):
- Total value: 675 points
- League average: 450 points
- Grade: A- (50% above average)

**Poor Draft** (60% of average):
- Total value: 270 points
- League average: 450 points
- Grade: C- (40% below average)

## Algorithm Components

### 1. Player Value Calculation

Each drafted player's value is the **weighted sum of all points scored** after the draft date, weighted by starter/bench status.

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
- This rewards drafting players who become productive starters

#### Examples

**Scenario A**: Rookie RB drafted in Round 2, becomes starter
- Weeks 1-17: Started all games, averaged 15 pts/week
- Value = 15 × 1.5 × 17 = **382.5 points**

**Scenario B**: QB drafted in Round 5, stays on bench
- Weeks 1-17: Benched all season, averaged 18 pts/week
- Value = 18 × 0.1 × 17 = **30.6 points**

**Scenario C**: Mixed usage WR
- Weeks 1-8: Benched, scored 10 pts/week = 10 × 0.1 × 8 = 8
- Weeks 9-17: Started, scored 14 pts/week = 14 × 1.5 × 9 = 189
- Total value = **197 points**

### 2. Draft Value Computation

For each owner in each draft:

```python
owner_draft_value = 0

for each_pick in owner's_picks:
    player_value = Σ (weighted_points_after_draft)
    owner_draft_value += player_value
```

### 3. Average Calculation

Calculate the league average for the draft:

```python
total_value = sum(owner_draft_value for all owners)
num_owners = count of owners in draft
average_value = total_value / num_owners
```

### 4. Grade Assignment

Compare each owner to the average:

```python
for each owner:
    value_vs_average = owner_draft_value / average_value
    grade = lookup_grade(value_vs_average)
```

## Draft Types

### Startup Draft
- **Identification**: 20+ rounds
- **Typical Size**: 25 rounds (full roster)
- **Purpose**: Initial league draft to fill all rosters
- **Grading Scope**: Full league history from draft onward

### Rookie Drafts
- **Identification**: <20 rounds
- **Typical Size**: 3-5 rounds
- **Purpose**: Annual rookie/FA draft
- **Grading Scope**: Performance from that season forward

Startup and rookie drafts are **never shown together** in filtered views to ensure fair comparisons.

## Data Requirements

For accurate grading, the algorithm requires:

1. **Draft Data**
   - Draft picks (round, pick number, roster_id, player_id)
   - Draft order (slot assignments)
   - Draft metadata (year, rounds, type, status)

2. **Matchup Player Points**: All scoring data after draft date
   - Player ID
   - Points scored
   - Starter status (TRUE/FALSE)
   - Week and season
   - Roster ownership

3. **Player Metadata**
   - Full name
   - Position
   - Team

## Frontend Views

### 1. Individual Owner View
**Trigger**: Owner selected from dropdown

**Display**: Table showing owner's draft history
- Sorted by grade (best to worst)
- Expandable rows show all picks from that draft
- Columns: Year, Type, Picks, Total Value, Avg/Pick, vs Average %, Grade

### 2. Individual Draft View
**Trigger**: No owner selected + "Individual Drafts" view

**Display**: Cards for each draft showing all owners
- Each draft shown separately
- Owners ranked within each draft
- Expandable cards show pick details

### 3. Aggregate Ranking View
**Trigger**: No owner selected + "Aggregate Ranking" view

**Display**: Single table ranking all owners across all filtered drafts
- Calculates average grade across multiple drafts
- Shows total value, average value per draft
- Expandable rows show breakdown by draft year
- Columns: Rank, Owner, # Drafts, Total Value, Avg Value, Avg Grade, All Grades

#### Grade Averaging Algorithm

```python
GRADE_TO_POINTS = {
    'A+': 4.3, 'A': 4.0, 'A-': 3.7,
    'B+': 3.3, 'B': 3.0, 'B-': 2.7,
    'C+': 2.3, 'C': 2.0, 'C-': 1.7,
    'D+': 1.3, 'D': 1.0, 'D-': 0.7,
    'F': 0.0
}

# Convert each grade to points, average, convert back to grade
avg_points = average(grade_to_points for all drafts)
avg_grade = closest_grade(avg_points)
```

## API Endpoints

### Get All Draft Grades

```http
GET /api/draft-grades?draft_type={type}&owner_id={id}
```

**Query Parameters**:
- `draft_type` (optional): `"startup"` or `"rookie"`
- `owner_id` (optional): Filter to specific owner

**Response**:
```json
{
  "total": 2,
  "drafts": [
    {
      "draft_id": "draft_2020",
      "year": 2020,
      "type": "linear",
      "rounds": 25,
      "weeks_of_data": 68,
      "avg_value": 1250.5,
      "total_picks": 300,
      "owners": [
        {
          "user_id": "user1",
          "username": "Owner One",
          "avatar": null,
          "total_value": 1875.8,
          "num_picks": 25,
          "avg_value_per_pick": 75.0,
          "value_vs_average": 1.5000,
          "grade": "A-",
          "picks": [
            {
              "pick_no": 1,
              "round": 1,
              "player_id": "1234",
              "player_name": "Justin Jefferson",
              "position": "WR",
              "team": "MIN",
              "weighted_points": 425.5,
              "starter_weeks": 65,
              "bench_weeks": 3,
              "total_weeks": 68
            }
          ]
        }
      ]
    }
  ]
}
```

### Get Single Draft Grade

```http
GET /api/draft-grades/{draft_id}
```

**Response**: Same structure as single draft object above

## Automatic Updates

Draft grades are **calculated dynamically** and update automatically:

### What Updates with Each Sync
- ✅ **Matchup player points**: New weekly scoring data
- ✅ **Starter/bench status**: Player roster positions
- ✅ **Player metadata**: Teams, positions

### What Stays Static
- ❌ **Draft picks**: Never change after draft
- ❌ **Draft order**: Fixed
- ❌ **Draft metadata**: Year, rounds, type

### Grade Evolution

**Week 1 After Draft**:
- Limited data (1 week)
- Grades highly volatile
- Low confidence

**Mid-Season (Week 10)**:
- Moderate data (10 weeks)
- Grades stabilizing
- Medium confidence

**Multiple Seasons Later**:
- Extensive data (50+ weeks)
- Grades very stable
- High confidence

The `weeks_of_data` field indicates confidence level.

## Limitations & Considerations

### Time Horizon Bias

**Issue**: Older drafts have more data and appear more definitive.

**Mitigation**:
- Display `weeks_of_data` for transparency
- Users can judge confidence based on sample size

**Example**:
- 2020 startup draft: 68 weeks of data → High confidence
- 2025 rookie draft: 5 weeks of data → Low confidence, preliminary

### Injury Impact

**Issue**: Injuries after draft can make picks look worse than expected.

**Reality**: This is intentional. Draft involves risk, and injury outcomes are part of the result. A player who gets injured did not provide value, regardless of draft-day expectations.

### Positional Scarcity

**Issue**: Algorithm doesn't account for positional scarcity (e.g., elite TEs being more valuable).

**Current Approach**: All positions weighted equally based on points scored.

**Future Enhancement**: Could weight by positional scarcity or add positional premiums.

### Bench Depth Value

**Issue**: Deep bench players score points but may never start.

**Current Approach**: Bench points weighted at 0.1x (10% of starter value).

**Rationale**: Provides some credit for depth while heavily rewarding starters.

## Implementation Files

### Backend
- **Service**: `backend/app/services/draft_grading.py`
- **API Routes**: `backend/app/api/routes/draft_grades.py`
- **Tests**: `backend/tests/test_draft_grades.py`
- **Models**: `backend/app/models/draft.py`

### Frontend
- **Page Component**: `frontend/src/pages/DraftRankings.tsx`
- **API Service**: `frontend/src/services/api.ts` (getDraftGrades methods)
- **Route**: `/draft-rankings`

### Database Tables
- `drafts`: Draft metadata
- `draft_picks`: Individual picks
- `matchup_player_points`: Player performance data (weekly)
- `players`: Player metadata
- `rosters`: Roster ownership by season
- `users`: Owner information

## Future Enhancements

Potential improvements to consider:

1. **Age Curves**: Adjust value for player age/career trajectory
2. **Positional Scarcity**: Weight by position scarcity (premium for elite QBs/TEs)
3. **Draft Capital Value**: Include future draft picks received in trades
4. **Keeper/Dynasty Context**: Account for long-term value vs win-now
5. **Pick Value Curves**: More sophisticated valuation based on draft position
6. **Confidence Intervals**: Show grade uncertainty based on sample size
7. **Historical Comparisons**: Compare to historical league draft averages
8. **Round-by-Round Grades**: Grade performance by round (how good were Round 3 picks?)
9. **Position-Specific Grades**: Grade drafting at each position separately

## Usage Examples

### Find Best Overall Drafter
1. Select "All Drafts"
2. Select "All Owners"
3. Select "Aggregate Ranking" view
4. Top owner = best drafter overall

### Evaluate Rookie Draft Performance
1. Select "Rookie Drafts"
2. Select "Aggregate Ranking" view
3. See who consistently drafts best rookies

### Review Personal Draft History
1. Select your name from owner dropdown
2. View table of all your drafts sorted by grade
3. Expand any row to see which picks performed well/poorly

### Compare Single Draft
1. Select "All Owners"
2. Select "Individual Drafts" view
3. See all owners' performance in each draft
4. Expand cards to see pick details

---

**Last Updated**: March 2026
**Algorithm Version**: 1.0
**Related Documentation**: `TRADE_GRADING.md`
