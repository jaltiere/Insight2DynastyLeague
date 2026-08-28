import { describe, it, expect } from 'vitest';
import {
  defaultDirectionFor,
  sortTeams,
  sortValue,
  type SortableTeam,
} from './powerRankingSort';

function team(overrides: Partial<SortableTeam> & { rank: number }): SortableTeam {
  return {
    display_name: `owner${overrides.rank}`,
    team_name: null,
    total_score: 0,
    current_season_score: 0,
    roster_value_score: 0,
    historical_score: 0,
    wins: 0,
    losses: 0,
    ties: 0,
    points_for: 0,
    avg_roster_age: 0,
    rank_change: null,
    ...overrides,
  };
}

const ranks = (teams: SortableTeam[]) => teams.map((t) => t.rank);

describe('default direction', () => {
  it('leads ascending for rank and team name', () => {
    expect(defaultDirectionFor('rank')).toBe('asc');
    expect(defaultDirectionFor('team')).toBe('asc');
  });

  it('leads descending for every score column', () => {
    for (const field of ['total', 'current', 'roster', 'historical', 'pf', 'record'] as const) {
      expect(defaultDirectionFor(field)).toBe('desc');
    }
  });
});

describe('sortTeams', () => {
  it('does not mutate the input array', () => {
    const teams = [team({ rank: 2 }), team({ rank: 1 })];
    const before = ranks(teams);

    sortTeams(teams, 'rank', 'asc');

    expect(ranks(teams)).toEqual(before);
  });

  it('orders by rank ascending, matching the unsorted page default', () => {
    const teams = [team({ rank: 3 }), team({ rank: 1 }), team({ rank: 2 })];

    expect(ranks(sortTeams(teams, 'rank', 'asc'))).toEqual([1, 2, 3]);
  });

  it('reverses on descending', () => {
    const teams = [team({ rank: 3 }), team({ rank: 1 }), team({ rank: 2 })];

    expect(ranks(sortTeams(teams, 'rank', 'desc'))).toEqual([3, 2, 1]);
  });

  it('sorts scores numerically, not as strings', () => {
    const teams = [
      team({ rank: 1, total_score: 9 }),
      team({ rank: 2, total_score: 80.47 }),
      team({ rank: 3, total_score: 74.38 }),
    ];

    expect(ranks(sortTeams(teams, 'total', 'desc'))).toEqual([2, 3, 1]);
  });

  it('sorts team names case-insensitively and falls back to display name', () => {
    const teams = [
      team({ rank: 1, team_name: 'zebra' }),
      team({ rank: 2, team_name: null, display_name: 'alpha' }),
      team({ rank: 3, team_name: 'Middle' }),
    ];

    expect(ranks(sortTeams(teams, 'team', 'asc'))).toEqual([2, 3, 1]);
  });

  it('ranks records by win percentage, not raw wins', () => {
    const teams = [
      team({ rank: 1, wins: 5, losses: 4 }), // .556
      team({ rank: 2, wins: 4, losses: 1 }), // .800
    ];

    expect(ranks(sortTeams(teams, 'record', 'desc'))).toEqual([2, 1]);
  });

  it('counts a tie as half a win', () => {
    expect(sortValue(team({ rank: 1, wins: 1, losses: 0, ties: 1 }), 'record')).toBe(0.75);
  });

  it('treats a team with no games as 0 rather than dividing by zero', () => {
    expect(sortValue(team({ rank: 1 }), 'record')).toBe(0);
  });
});

describe('missing trend values', () => {
  it('sinks teams with no prior snapshot when descending', () => {
    const teams = [
      team({ rank: 1, rank_change: null }),
      team({ rank: 2, rank_change: 3 }),
      team({ rank: 3, rank_change: -1 }),
    ];

    expect(ranks(sortTeams(teams, 'trend', 'desc'))).toEqual([2, 3, 1]);
  });

  it('sinks them on ascending too, instead of leading with them', () => {
    const teams = [
      team({ rank: 1, rank_change: null }),
      team({ rank: 2, rank_change: 3 }),
      team({ rank: 3, rank_change: -1 }),
    ];

    expect(ranks(sortTeams(teams, 'trend', 'asc'))).toEqual([3, 2, 1]);
  });

  it('keeps all-null columns in rank order', () => {
    const teams = [team({ rank: 2 }), team({ rank: 1 }), team({ rank: 3 })];

    expect(ranks(sortTeams(teams, 'trend', 'desc'))).toEqual([1, 2, 3]);
  });
});

describe('ties', () => {
  it('breaks equal values by rank so the order is stable and predictable', () => {
    const teams = [
      team({ rank: 3, points_for: 100 }),
      team({ rank: 1, points_for: 100 }),
      team({ rank: 2, points_for: 100 }),
    ];

    expect(ranks(sortTeams(teams, 'pf', 'desc'))).toEqual([1, 2, 3]);
  });
});
