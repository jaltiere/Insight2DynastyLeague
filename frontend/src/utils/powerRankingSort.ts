export type SortField =
  | 'rank'
  | 'trend'
  | 'team'
  | 'total'
  | 'current'
  | 'roster'
  | 'historical'
  | 'record'
  | 'pf'
  | 'age';

export type SortDirection = 'asc' | 'desc';

/** The subset of a power-ranking row the sort actually reads. */
export interface SortableTeam {
  rank: number;
  display_name: string;
  team_name: string | null;
  total_score: number;
  current_season_score: number;
  roster_value_score: number;
  historical_score: number;
  wins: number;
  losses: number;
  ties: number;
  points_for: number;
  avg_roster_age: number;
  rank_change: number | null;
}

/**
 * Columns whose natural first click is ascending: rank 1 is the best rank,
 * and names read A-Z. Every other column leads with its largest value.
 */
export const ASCENDING_FIRST: SortField[] = ['rank', 'team'];

export function defaultDirectionFor(field: SortField): SortDirection {
  return ASCENDING_FIRST.includes(field) ? 'asc' : 'desc';
}

/**
 * The value a column sorts on, or null when there is nothing to sort by —
 * a team with no prior snapshot has no trend. Nulls are handled by the
 * comparator rather than substituted with a sentinel number, which would
 * park those teams at the top of an ascending sort.
 */
export function sortValue(
  team: SortableTeam,
  field: SortField
): number | string | null {
  switch (field) {
    case 'rank':
      return team.rank;
    case 'trend':
      return team.rank_change;
    case 'team':
      return (team.team_name || team.display_name).toLowerCase();
    case 'total':
      return team.total_score;
    case 'current':
      return team.current_season_score;
    case 'roster':
      return team.roster_value_score;
    case 'historical':
      return team.historical_score;
    case 'record': {
      // Win percentage, so 6-2 outranks 5-1's raw win count fairly.
      const games = team.wins + team.losses + team.ties;
      return games ? (team.wins + team.ties * 0.5) / games : 0;
    }
    case 'pf':
      return team.points_for;
    case 'age':
      return team.avg_roster_age;
  }
}

/** Sort a copy of `teams`; the input array is never mutated. */
export function sortTeams<T extends SortableTeam>(
  teams: T[],
  field: SortField,
  direction: SortDirection
): T[] {
  return [...teams].sort((a, b) => {
    const valA = sortValue(a, field);
    const valB = sortValue(b, field);

    // Missing values always sink, whichever way the column is pointing.
    if (valA === null && valB === null) return a.rank - b.rank;
    if (valA === null) return 1;
    if (valB === null) return -1;

    const cmp =
      typeof valA === 'string' || typeof valB === 'string'
        ? String(valA).localeCompare(String(valB))
        : valA - valB;

    // Ties fall back to rank so equal values keep a predictable order.
    if (cmp === 0) return a.rank - b.rank;
    return direction === 'asc' ? cmp : -cmp;
  });
}
