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

  // Drafts
  getAllDrafts: () => apiClient.get('/drafts'),
  getDraftByYear: (year: number) => apiClient.get(`/drafts/${year}`),

  // League History
  getAllHistory: () => apiClient.get('/league-history').then(res => res.data),
  getSeasonHistory: (season: number) => apiClient.get(`/league-history/${season}`),

  // Sync
  syncLeagueData: () => apiClient.post('/sync/league'),
};
