// Standings types
export interface StandingsTeam {
  roster_id: number;
  user_id: string;
  username: string;
  display_name: string;
  team_name: string | null;
  division: number;
  wins: number;
  losses: number;
  ties: number;
  points_for: number;
  points_against: number;
  win_percentage: number;
  median_wins: number;
  median_losses: number;
  median_ties: number;
  max_potential_points: number;
  points_left_on_bench: number;
}

export interface StandingsResponse {
  season: number;
  num_divisions: number;
  division_names: Record<string, string>;
  total_teams: number;
  standings: StandingsTeam[];
}

// Transaction types
export interface TransactionPlayer {
  player_id: string;
  player_name: string;
  position: string | null;
  team: string | null;
  roster_id: number;
}

export interface TransactionOwner {
  user_id: string;
  username: string;
  team_name: string | null;
  roster_id: number;
}

export interface TransactionDraftPick {
  season: string;
  round: number;
  roster_id: number;
  previous_owner_id: number;
  owner_id: number;
  owner_name: string | null;
}

export interface Transaction {
  id: number;
  type: string;
  status: string;
  season: number;
  week: number;
  waiver_bid: number | null;
  adds: TransactionPlayer[];
  drops: TransactionPlayer[];
  owners: TransactionOwner[];
  draft_picks: TransactionDraftPick[];
  status_updated: number | null;
  metadata_notes: string | null;
}
