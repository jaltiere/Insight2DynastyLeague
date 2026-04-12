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

// Matchup Recap types
export interface MatchupRecap {
  matchup_id: number;
  week: number;
  season: number;
  home_team: string;
  away_team: string;
  home_score: number | null;
  away_score: number | null;
  recap_text: string | null;
  predictions_text: string | null;
  recap_type: string;
  recap_metadata: Record<string, any> | null;
  generated_at: string | null;
}

export interface WeekRecapsResponse {
  week: number;
  season: number;
  recaps: MatchupRecap[];
}

export interface CurrentWeekMatchupsResponse {
  week: number;
  season: number;
  matchups: MatchupRecap[];
}

export interface CurrentWeekInfo {
  week: number;
  season: number;
}

// Player Profile types
export interface PlayerScoringHistory {
  season: number;
  total_points: number;
  games: number;
  avg_points: number;
  starter_games: number;
}

export interface PlayerOwner {
  user_id: string;
  display_name: string;
  username: string;
  avatar?: string;
  team_name?: string | null;
  roster_id?: number;
  season?: number;
}

export interface PlayerOwnershipEvent {
  event_type: 'trade' | 'waiver' | 'free_agent' | 'release';
  season: number;
  week: number;
  from_owner: Partial<PlayerOwner> | null;
  to_owner: Partial<PlayerOwner> | null;
}

export interface PlayerDraftHistory {
  year: number;
  draft_type: string;
  round: number;
  pick_in_round: number;
  overall_pick: number;
  owner: Partial<PlayerOwner>;
}

// Future Draft Pick Tracker types
export interface FuturePickOwner {
  roster_id: number;
  user_id: string | null;
  display_name: string;
  avatar: string | null;
}

export interface FutureDraftPick {
  season: number;
  round: number;
  original_roster_id: number;
  original_owner: FuturePickOwner;
  current_roster_id: number;
  current_owner: FuturePickOwner;
  is_traded: boolean;
}

export interface FutureDraftPicksResponse {
  current_season: number;
  future_seasons: number[];
  num_rounds: number;
  owners: FuturePickOwner[];
  picks: FutureDraftPick[];
}

export interface PlayerProfile {
  id: string;
  first_name: string;
  last_name: string;
  full_name: string;
  position: string | null;
  team: string | null;
  number: number | null;
  age: number | null;
  height: string | null;
  weight: number | null;
  college: string | null;
  years_exp: number | null;
  status: string | null;
  injury_status: string | null;
  stats: Record<string, unknown> | null;
  scoring_history: PlayerScoringHistory[];
  current_owner: PlayerOwner | null;
  ownership_history: PlayerOwnershipEvent[];
  draft_history: PlayerDraftHistory[];
}
