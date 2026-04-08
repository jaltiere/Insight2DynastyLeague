import React, { createContext, useContext, useState, useCallback } from 'react';
import type { ReactNode } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../services/api';
import type { PlayerProfile, PlayerOwner } from '../types';

// ─── Context ─────────────────────────────────────────────────────────────────

interface PlayerModalContextValue {
  openPlayer: (playerId: string) => void;
}

const PlayerModalContext = createContext<PlayerModalContextValue | null>(null);

export function usePlayerModal(): PlayerModalContextValue {
  const ctx = useContext(PlayerModalContext);
  if (!ctx) throw new Error('usePlayerModal must be used within PlayerModalProvider');
  return ctx;
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

function avatarUrl(avatarId: string | null | undefined): string | null {
  if (!avatarId) return null;
  return `https://sleepercdn.com/avatars/thumbs/${avatarId}`;
}

function getPositionColor(position: string | null): string {
  switch (position) {
    case 'QB': return 'text-pink-700 bg-pink-100';
    case 'RB': return 'text-sky-700 bg-sky-100';
    case 'WR': return 'text-orange-700 bg-orange-100';
    case 'TE': return 'text-yellow-700 bg-yellow-100';
    case 'K':  return 'text-purple-700 bg-purple-100';
    case 'DEF': return 'text-amber-800 bg-amber-100';
    default:   return 'text-gray-700 bg-gray-100';
  }
}

function getStatusBadge(status: string | null, injury: string | null) {
  if (injury) return { label: injury, style: 'bg-red-100 text-red-700' };
  if (status === 'Inactive') return { label: 'Inactive', style: 'bg-gray-100 text-gray-600' };
  if (status === 'Active') return { label: 'Active', style: 'bg-green-100 text-green-700' };
  if (status) return { label: status, style: 'bg-yellow-100 text-yellow-700' };
  return null;
}

function ownerName(owner: Partial<PlayerOwner> | null): string {
  return owner?.display_name ?? '—';
}

// ─── Modal ───────────────────────────────────────────────────────────────────

function PlayerModal({ playerId, onClose }: { playerId: string; onClose: () => void }) {
  const { data: player, isLoading, isError } = useQuery<PlayerProfile>({
    queryKey: ['player', playerId],
    queryFn: () => api.getPlayerDetails(playerId).then(res => res.data),
  });

  const careerTotals = player?.scoring_history.reduce(
    (acc, s) => ({ pts: acc.pts + s.total_points, games: acc.games + s.games }),
    { pts: 0, games: 0 }
  ) ?? { pts: 0, games: 0 };

  return (
    <div
      className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-xl shadow-2xl w-full max-w-2xl max-h-[90vh] flex flex-col overflow-hidden"
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100 shrink-0">
          <h2 className="text-lg font-semibold text-gray-900">
            {isLoading ? 'Loading…' : player?.full_name ?? 'Player Profile'}
          </h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 text-2xl leading-none"
            aria-label="Close"
          >
            ×
          </button>
        </div>

        {/* Body */}
        <div className="overflow-y-auto flex-1 p-5 space-y-5">
          {isLoading && (
            <div className="flex justify-center py-12">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
            </div>
          )}

          {isError && (
            <p className="text-center text-gray-400 py-10">Failed to load player.</p>
          )}

          {player && (() => {
            const statusBadge = getStatusBadge(player.status, player.injury_status);
            return (
              <>
                {/* Bio */}
                <div className="flex flex-wrap items-start gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex flex-wrap items-center gap-2 mb-1">
                      {player.position && (
                        <span className={`text-xs font-bold px-2 py-0.5 rounded ${getPositionColor(player.position)}`}>
                          {player.position}
                        </span>
                      )}
                      {statusBadge && (
                        <span className={`text-xs font-medium px-2 py-0.5 rounded ${statusBadge.style}`}>
                          {statusBadge.label}
                        </span>
                      )}
                    </div>
                    <p className="text-xl font-bold text-gray-900">
                      {player.full_name}
                      {player.number && (
                        <span className="ml-2 text-base font-normal text-gray-400">#{player.number}</span>
                      )}
                    </p>
                    {player.team && <p className="text-sm text-gray-500">{player.team}</p>}
                  </div>

                  {player.current_owner ? (
                    <div className="flex items-center gap-2 bg-gray-50 rounded-lg px-3 py-2 border border-gray-100">
                      {player.current_owner.avatar && (
                        <img
                          src={avatarUrl(player.current_owner.avatar) ?? undefined}
                          alt={player.current_owner.display_name}
                          className="w-8 h-8 rounded-full"
                        />
                      )}
                      <div className="text-sm">
                        <p className="text-gray-400 text-xs">Current Owner</p>
                        <p className="font-semibold text-gray-900">{player.current_owner.display_name}</p>
                        {player.current_owner.team_name && (
                          <p className="text-gray-500 text-xs">{player.current_owner.team_name}</p>
                        )}
                      </div>
                    </div>
                  ) : (
                    <div className="bg-gray-50 rounded-lg px-3 py-2 border border-gray-100 text-sm text-gray-400">
                      Free Agent
                    </div>
                  )}
                </div>

                {/* Bio stats */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
                  {player.age != null && (
                    <div>
                      <p className="text-gray-400 text-xs uppercase tracking-wide">Age</p>
                      <p className="font-semibold text-gray-900">{player.age}</p>
                    </div>
                  )}
                  {player.height && (
                    <div>
                      <p className="text-gray-400 text-xs uppercase tracking-wide">Height</p>
                      <p className="font-semibold text-gray-900">{player.height}</p>
                    </div>
                  )}
                  {player.weight != null && (
                    <div>
                      <p className="text-gray-400 text-xs uppercase tracking-wide">Weight</p>
                      <p className="font-semibold text-gray-900">{player.weight} lbs</p>
                    </div>
                  )}
                  {player.college && (
                    <div>
                      <p className="text-gray-400 text-xs uppercase tracking-wide">College</p>
                      <p className="font-semibold text-gray-900">{player.college}</p>
                    </div>
                  )}
                  {player.years_exp != null && (
                    <div>
                      <p className="text-gray-400 text-xs uppercase tracking-wide">Experience</p>
                      <p className="font-semibold text-gray-900">
                        {player.years_exp === 0 ? 'Rookie' : `${player.years_exp} yr${player.years_exp !== 1 ? 's' : ''}`}
                      </p>
                    </div>
                  )}
                </div>

                {/* Scoring history */}
                {player.scoring_history.length > 0 && (
                  <div className="rounded-lg border border-gray-200 overflow-hidden">
                    <div className="px-4 py-2.5 bg-gray-50 border-b border-gray-100 flex items-center justify-between">
                      <span className="text-sm font-semibold text-gray-700">Fantasy Scoring</span>
                      <span className="text-xs text-gray-400">
                        Career: {careerTotals.pts.toFixed(1)} pts · {careerTotals.games} games
                      </span>
                    </div>
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="text-xs text-gray-400 uppercase tracking-wide bg-gray-50">
                          <th className="px-4 py-2 text-left">Season</th>
                          <th className="px-4 py-2 text-right">Total</th>
                          <th className="px-4 py-2 text-right">Games</th>
                          <th className="px-4 py-2 text-right">Avg</th>
                          <th className="px-4 py-2 text-right">Started</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-100">
                        {player.scoring_history.map(row => (
                          <tr key={row.season} className="hover:bg-gray-50">
                            <td className="px-4 py-2 font-medium text-gray-900">{row.season}</td>
                            <td className="px-4 py-2 text-right text-gray-700">{row.total_points.toFixed(1)}</td>
                            <td className="px-4 py-2 text-right text-gray-500">{row.games}</td>
                            <td className="px-4 py-2 text-right text-gray-700">{row.avg_points.toFixed(1)}</td>
                            <td className="px-4 py-2 text-right text-gray-500">{row.starter_games}/{row.games}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}

                {/* Draft history */}
                {player.draft_history.length > 0 && (
                  <div className="rounded-lg border border-gray-200 overflow-hidden">
                    <div className="px-4 py-2.5 bg-gray-50 border-b border-gray-100">
                      <span className="text-sm font-semibold text-gray-700">Draft History</span>
                    </div>
                    <div className="divide-y divide-gray-100">
                      {player.draft_history.map((pick, i) => (
                        <div key={i} className="px-4 py-3 flex items-center justify-between gap-3 text-sm">
                          <div>
                            <span className="font-medium text-gray-900">{pick.year}</span>
                            <span className="text-gray-400 ml-2 capitalize text-xs">{pick.draft_type}</span>
                          </div>
                          <div className="text-right">
                            <span className="text-gray-500">Rd {pick.round}, Pk {pick.pick_in_round}</span>
                            <span className="text-gray-400 ml-1 text-xs">(#{pick.overall_pick})</span>
                            {pick.owner?.display_name && (
                              <span className="block text-gray-600 text-xs">by {pick.owner.display_name}</span>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Ownership history */}
                {player.ownership_history.length > 0 && (
                  <div className="rounded-lg border border-gray-200 overflow-hidden">
                    <div className="px-4 py-2.5 bg-gray-50 border-b border-gray-100">
                      <span className="text-sm font-semibold text-gray-700">Ownership History</span>
                    </div>
                    <div className="divide-y divide-gray-100">
                      {player.ownership_history.map((evt, i) => {
                        let badge: { label: string; style: string };
                        let description: React.ReactNode;

                        if (evt.event_type === 'trade') {
                          badge = { label: 'TRADE', style: 'bg-blue-100 text-blue-700' };
                          description = (
                            <span className="text-gray-900">
                              <span className="font-medium">{ownerName(evt.from_owner)}</span>
                              <span className="text-gray-400 mx-1.5">→</span>
                              <span className="font-medium">{ownerName(evt.to_owner)}</span>
                            </span>
                          );
                        } else if (evt.event_type === 'waiver') {
                          badge = { label: 'WAIVER', style: 'bg-green-100 text-green-700' };
                          description = <span className="font-medium text-gray-900">{ownerName(evt.to_owner)}</span>;
                        } else if (evt.event_type === 'free_agent') {
                          badge = { label: 'FA', style: 'bg-green-100 text-green-700' };
                          description = <span className="font-medium text-gray-900">{ownerName(evt.to_owner)}</span>;
                        } else {
                          badge = { label: 'DROP', style: 'bg-red-100 text-red-700' };
                          description = <span className="font-medium text-gray-900">{ownerName(evt.from_owner)}</span>;
                        }

                        return (
                          <div key={i} className="px-4 py-2.5 flex items-center gap-3 text-sm">
                            <span className={`text-xs font-semibold px-2 py-0.5 rounded shrink-0 ${badge.style}`}>
                              {badge.label}
                            </span>
                            {description}
                            <span className="text-gray-400 ml-auto text-xs shrink-0">
                              {evt.season} Wk {evt.week}
                            </span>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}

                {player.scoring_history.length === 0 &&
                 player.draft_history.length === 0 &&
                 player.ownership_history.length === 0 && (
                  <p className="text-center text-gray-400 text-sm py-4">No league history found.</p>
                )}
              </>
            );
          })()}
        </div>
      </div>
    </div>
  );
}

// ─── Provider ────────────────────────────────────────────────────────────────

export function PlayerModalProvider({ children }: { children: ReactNode }) {
  const [activePlayerId, setActivePlayerId] = useState<string | null>(null);

  const openPlayer = useCallback((playerId: string) => {
    setActivePlayerId(playerId);
  }, []);

  const closePlayer = useCallback(() => {
    setActivePlayerId(null);
  }, []);

  return (
    <PlayerModalContext.Provider value={{ openPlayer }}>
      {children}
      {activePlayerId && (
        <PlayerModal playerId={activePlayerId} onClose={closePlayer} />
      )}
    </PlayerModalContext.Provider>
  );
}
