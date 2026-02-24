import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export const apiClient = axios.create({
  baseURL: `${API_BASE_URL}/api`,
  headers: {
    'Content-Type': 'application/json',
  },
});

// API endpoint functions
export const api = {
  // Standings
  getStandings: () => apiClient.get('/standings').then(res => res.data),
  getCurrentStandings: () => apiClient.get('/standings'),
  getHistoricalStandings: (season: number) => apiClient.get(`/standings/${season}`),

  // Players
  getPlayers: (params?: { search?: string; position?: string; limit?: number; offset?: number }) =>
    apiClient.get('/players', { params }),
  getPlayerDetails: (playerId: string) => apiClient.get(`/players/${playerId}`),

  // Owners
  getAllOwners: () => apiClient.get('/owners'),
  getOwnerDetails: (ownerId: string) => apiClient.get(`/owners/${ownerId}`),

  // Matchups
  getHeadToHead: (owner1: string, owner2: string) =>
    apiClient.get(`/matchups/head-to-head/${owner1}/${owner2}`),
  getH2HMatrix: (matchType?: string) =>
    apiClient.get('/matchups/head-to-head-matrix', {
      params: matchType ? { match_type: matchType } : {},
    }),

  // Drafts
  getAllDrafts: () => apiClient.get('/drafts').then(res => res.data),
  getDraftByYear: (year: number) => apiClient.get(`/drafts/${year}`).then(res => res.data),

  // League History
  getAllHistory: () => apiClient.get('/league-history').then(res => res.data),
  getSeasonHistory: (season: number) => apiClient.get(`/league-history/${season}`),

  // Player Records
  getPlayerRecords: (params?: {
    view?: string;
    match_type?: string;
    roster_type?: string;
    position?: string;
    limit?: number;
  }) => apiClient.get('/player-records', { params }).then(res => res.data),

  // Taxi Squads
  getTaxiSquads: () => apiClient.get('/taxi-squads').then(res => res.data),

  // Seasons
  getSeasons: () => apiClient.get('/seasons').then(res => res.data),

  // Transactions
  getRecentTransactions: (limit: number = 20) =>
    apiClient.get('/transactions/recent', { params: { limit } }).then(res => res.data),
  getTransactionSummary: (season?: number) =>
    apiClient.get('/transactions/summary', { params: season ? { season } : {} }).then(res => res.data),
  getTransactionsByOwner: (userId: string, type: string, season?: number) =>
    apiClient.get('/transactions/by-owner', {
      params: { user_id: userId, type, ...(season ? { season } : {}) },
    }).then(res => res.data),

  // Sync
  syncLeagueData: () => apiClient.post('/sync/league'),
};
