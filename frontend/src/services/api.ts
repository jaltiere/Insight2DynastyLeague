import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

// Module-level slug used by the league-scoped interceptor.
// Initialized from the URL path so hard refreshes use the correct league
// before LeagueContext finishes its async getLeagues() call.
let _leagueSlug = (() => {
  const slug = window.location.pathname.split('/')[1];
  return slug || 'insight2dynasty';
})();

export function setCurrentLeagueSlug(slug: string) {
  _leagueSlug = slug;
}

// Global client — no league prefix (players, leagues list, sync)
const globalApiClient = axios.create({
  baseURL: `${API_BASE_URL}/api`,
  headers: { 'Content-Type': 'application/json' },
});

// League-scoped client — automatically prefixes /{slug}/ to every request URL
const apiClient = axios.create({
  baseURL: `${API_BASE_URL}/api`,
  headers: { 'Content-Type': 'application/json' },
});

apiClient.interceptors.request.use((config) => {
  config.url = `/${_leagueSlug}${config.url}`;
  return config;
});

// API endpoint functions
export const api = {
  // Leagues (global — no slug prefix)
  getLeagues: () => globalApiClient.get('/leagues').then(res => res.data),

  // Standings (league-scoped)
  getStandings: () => apiClient.get('/standings').then(res => res.data),
  getCurrentStandings: () => apiClient.get('/standings'),
  getHistoricalStandings: (season: number) => apiClient.get(`/standings/${season}`),

  // Players (global — not league-scoped in backend)
  getPlayers: (params?: { search?: string; position?: string; limit?: number; offset?: number }) =>
    globalApiClient.get('/players', { params }),
  getPlayerDetails: (playerId: string) => globalApiClient.get(`/players/${playerId}`),

  // Owners (league-scoped)
  getAllOwners: () => apiClient.get('/owners'),
  getOwnerDetails: (ownerId: string) => apiClient.get(`/owners/${ownerId}`),

  // Matchups (league-scoped)
  getHeadToHead: (owner1: string, owner2: string) =>
    apiClient.get(`/matchups/head-to-head/${owner1}/${owner2}`),
  getH2HMatrix: (matchType?: string) =>
    apiClient.get('/matchups/head-to-head-matrix', {
      params: matchType ? { match_type: matchType } : {},
    }),

  // Drafts (league-scoped)
  getAllDrafts: () => apiClient.get('/drafts').then(res => res.data),
  getDraftByYear: (year: number) => apiClient.get(`/drafts/${year}`).then(res => res.data),
  getCurrentDraft: () => apiClient.get('/drafts/current').then(res => res.data),

  // League History (league-scoped)
  getAllHistory: () => apiClient.get('/league-history').then(res => res.data),
  getSeasonHistory: (season: number) => apiClient.get(`/league-history/${season}`),

  // Player Records (league-scoped)
  getPlayerRecords: (params?: {
    view?: string;
    match_type?: string;
    roster_type?: string;
    position?: string;
    limit?: number;
  }) => apiClient.get('/player-records', { params }).then(res => res.data),

  // Rookie Records (league-scoped)
  getRookieRecords: (params?: {
    view?: string;
    match_type?: string;
    roster_type?: string;
    position?: string;
    limit?: number;
  }) => apiClient.get('/rookie-records', { params }).then(res => res.data),

  // Taxi Squads (league-scoped)
  getTaxiSquads: () => apiClient.get('/taxi-squads').then(res => res.data),

  // Seasons (league-scoped)
  getSeasons: () => apiClient.get('/seasons').then(res => res.data),

  // Transactions (league-scoped)
  getRecentTransactions: (limit: number = 20) =>
    apiClient.get('/transactions/recent', { params: { limit } }).then(res => res.data),
  getTransactionSummary: (season?: number) =>
    apiClient.get('/transactions/summary', { params: season ? { season } : {} }).then(res => res.data),
  getTransactionsByOwner: (userId: string, type: string, season?: number) =>
    apiClient.get('/transactions/by-owner', {
      params: { user_id: userId, type, ...(season ? { season } : {}) },
    }).then(res => res.data),

  // Trade Grades (league-scoped)
  getTradeGrades: (params?: { season?: number; sort?: string; owner_id?: string }) =>
    apiClient.get('/trade-grades', { params }).then(res => res.data),
  getTradeGrade: (tradeId: string) =>
    apiClient.get(`/trade-grades/${tradeId}`).then(res => res.data),

  // Draft Grades (league-scoped)
  getDraftGrades: (params?: { draft_type?: string; owner_id?: string }) =>
    apiClient.get('/draft-grades', { params }).then(res => res.data),
  getDraftGrade: (draftId: string) =>
    apiClient.get(`/draft-grades/${draftId}`).then(res => res.data),

  // Playoffs (league-scoped)
  getPlayoffOdds: (season?: number) =>
    apiClient.get(season ? `/playoffs/${season}` : '/playoffs').then(res => res.data),

  // Power Rankings (league-scoped)
  getPowerRankings: (season?: number) =>
    apiClient.get(season ? `/power-rankings/${season}` : '/power-rankings').then(res => res.data),
  getRosterBreakdown: (season: number, rosterId: number) =>
    apiClient.get(`/power-rankings/${season}/roster/${rosterId}`).then(res => res.data),
  getPowerRankingsTrends: (season: number) =>
    apiClient.get(`/power-rankings/${season}/trends`).then(res => res.data),

  // Matchup Recaps (league-scoped)
  getCurrentWeekMatchups: () =>
    apiClient.get('/matchup-recaps/current').then(res => res.data),
  getPreviousWeekRecaps: () =>
    apiClient.get('/matchup-recaps/previous').then(res => res.data),
  getWeekRecaps: (week: number, season?: number) =>
    apiClient.get(`/matchup-recaps/week/${week}`, { params: { season } }).then(res => res.data),
  getNewsletterRecaps: (week: number, season?: number) =>
    apiClient.get(`/matchup-recaps/newsletter/${week}`, { params: { season } }).then(res => res.data),

  // Newsletter (league-scoped)
  getNewsletter: (week: number, season?: number) =>
    apiClient.get(`/newsletter/${week}`, { params: season ? { season } : {} }).then(res => res.data),

  // Roster Analysis (league-scoped)
  getRosterAnalysis: () => apiClient.get('/roster-analysis').then(res => res.data),

  // Trade Calculator (league-scoped)
  getTradeCalcOwners: () => apiClient.get('/trade-calculator/owners').then(res => res.data),
  getTradeCalcRoster: (userId: string) => apiClient.get(`/trade-calculator/roster/${userId}`).then(res => res.data),
  getTradeCalcRosterPicks: (userId: string) => apiClient.get(`/trade-calculator/roster-picks/${userId}`).then(res => res.data),
  searchTradeCalcPlayers: (q: string) => apiClient.get('/trade-calculator/search', { params: { q } }).then(res => res.data),
  getPickValues: () => apiClient.get('/trade-calculator/pick-values').then(res => res.data),
  getH2HTrades: (userIdA: string, userIdB: string) =>
    apiClient.get(`/trade-calculator/h2h-trades/${userIdA}/${userIdB}`).then(res => res.data),

  // Draft Picks (league-scoped)
  getFutureDraftPicks: () => apiClient.get('/draft-picks/future').then(res => res.data),

  // Team Records (league-scoped)
  getTeamRecords: () => apiClient.get('/team-records').then(res => res.data),

  // Free Agents (global players endpoint, filtered)
  getFreeAgents: (params?: { search?: string; position?: string; limit?: number; offset?: number }) =>
    apiClient.get('/free-agents', { params }).then(res => res.data),

  // Search (league-scoped)
  search: (q: string) => apiClient.get('/search', { params: { q } }).then(res => res.data),

  // Sync (global)
  syncLeagueData: () => globalApiClient.post('/sync/league'),
};
