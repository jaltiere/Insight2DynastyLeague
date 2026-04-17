import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../services/api';
import { usePlayerModal } from '../context/PlayerModalContext';

interface FreeAgent {
  player_id: string;
  full_name: string;
  position: string | null;
  team: string | null;
  age: number | null;
  years_exp: number | null;
  ktc_value: number;
  ktc_rank: number | null;
  injury_status: string | null;
}

interface FreeAgentsData {
  total: number;
  limit: number;
  offset: number;
  season: number | null;
  players: FreeAgent[];
}

const POSITIONS = ['QB', 'RB', 'WR', 'TE', 'K'];
const PAGE_SIZE = 50;

function getPositionColor(position: string | null): string {
  switch (position) {
    case 'QB': return 'text-pink-700 bg-pink-100';
    case 'RB': return 'text-sky-700 bg-sky-100';
    case 'WR': return 'text-orange-700 bg-orange-100';
    case 'TE': return 'text-yellow-700 bg-yellow-100';
    case 'K':  return 'text-purple-700 bg-purple-100';
    default:   return 'text-gray-700 bg-gray-100';
  }
}

function getInjuryBadge(status: string | null): string | null {
  if (!status) return null;
  const s = status.toLowerCase();
  if (s === 'ir' || s === 'injured reserve') return 'IR';
  if (s === 'out') return 'Out';
  if (s === 'doubtful') return 'Dtf';
  if (s === 'questionable') return 'Q';
  return null;
}

export default function FreeAgents() {
  const { openPlayer } = usePlayerModal();
  const [search, setSearch] = useState('');
  const [position, setPosition] = useState('');
  const [page, setPage] = useState(0);

  const { data, isLoading, error } = useQuery<FreeAgentsData>({
    queryKey: ['freeAgents', search, position, page],
    queryFn: () =>
      api.getFreeAgents({
        search: search || undefined,
        position: position || undefined,
        limit: PAGE_SIZE,
        offset: page * PAGE_SIZE,
      }),
  });

  const totalPages = data ? Math.ceil(data.total / PAGE_SIZE) : 0;

  function handleSearch(e: React.ChangeEvent<HTMLInputElement>) {
    setSearch(e.target.value);
    setPage(0);
  }

  function handlePosition(pos: string) {
    setPosition(prev => (prev === pos ? '' : pos));
    setPage(0);
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="flex items-baseline gap-3 mb-6">
        <h1 className="text-4xl font-bold">Free Agent Market</h1>
        {data?.season && (
          <span className="text-lg text-gray-500">{data.season} Season</span>
        )}
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg shadow p-4 mb-6 flex flex-col sm:flex-row gap-4 items-start sm:items-center">
        <input
          type="text"
          placeholder="Search players..."
          value={search}
          onChange={handleSearch}
          className="border border-gray-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 w-full sm:w-64"
        />

        <div className="flex flex-wrap gap-2">
          {POSITIONS.map(pos => (
            <button
              key={pos}
              onClick={() => handlePosition(pos)}
              className={`px-3 py-1.5 rounded-md text-sm font-semibold transition ${
                position === pos
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              {pos}
            </button>
          ))}
          {position && (
            <button
              onClick={() => { setPosition(''); setPage(0); }}
              className="px-3 py-1.5 rounded-md text-sm text-gray-500 hover:text-gray-700 hover:bg-gray-100 transition"
            >
              Clear
            </button>
          )}
        </div>

        {data && (
          <span className="text-sm text-gray-500 sm:ml-auto whitespace-nowrap">
            {data.total.toLocaleString()} players
          </span>
        )}
      </div>

      {/* Table */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        {isLoading ? (
          <div className="p-8 text-center text-gray-500">Loading free agents...</div>
        ) : error ? (
          <div className="p-8 text-center text-red-600">
            Error loading free agents: {(error as Error).message}
          </div>
        ) : !data || data.players.length === 0 ? (
          <div className="p-8 text-center text-gray-500">No free agents found.</div>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b bg-gray-50 text-xs text-gray-500 uppercase tracking-wide">
                    <th className="px-4 py-3 text-left w-12">#</th>
                    <th className="px-4 py-3 text-left">Player</th>
                    <th className="px-4 py-3 text-center w-16">Pos</th>
                    <th className="px-4 py-3 text-center w-16">Team</th>
                    <th className="px-4 py-3 text-center w-16">Age</th>
                    <th className="px-4 py-3 text-center w-16">Exp</th>
                    <th className="px-4 py-3 text-right w-24">KTC Value</th>
                  </tr>
                </thead>
                <tbody>
                  {data.players.map((player, idx) => {
                    const injury = getInjuryBadge(player.injury_status);
                    const rank = player.ktc_rank ?? page * PAGE_SIZE + idx + 1;
                    return (
                      <tr
                        key={player.player_id}
                        className="border-b last:border-b-0 hover:bg-gray-50 dark:hover:bg-gray-700 transition"
                      >
                        <td className="px-4 py-2.5 text-gray-400 text-xs">{rank}</td>
                        <td className="px-4 py-2.5 font-medium">
                          <div className="flex items-center gap-2">
                            <button
                              onClick={() => openPlayer(player.player_id)}
                              className="hover:text-blue-600 hover:underline text-left"
                            >
                              {player.full_name}
                            </button>
                            {injury && (
                              <span className="text-xs bg-red-100 text-red-700 px-1.5 py-0.5 rounded font-semibold">
                                {injury}
                              </span>
                            )}
                          </div>
                        </td>
                        <td className="px-4 py-2.5 text-center">
                          {player.position ? (
                            <span className={`text-xs font-semibold px-2 py-0.5 rounded ${getPositionColor(player.position)}`}>
                              {player.position}
                            </span>
                          ) : (
                            <span className="text-gray-400">--</span>
                          )}
                        </td>
                        <td className="px-4 py-2.5 text-center text-gray-600">
                          {player.team || '--'}
                        </td>
                        <td className="px-4 py-2.5 text-center text-gray-600">
                          {player.age ?? '--'}
                        </td>
                        <td className="px-4 py-2.5 text-center text-gray-500">
                          {player.years_exp != null ? `Y${player.years_exp}` : '--'}
                        </td>
                        <td className="px-4 py-2.5 text-right font-semibold">
                          {player.ktc_value > 0 ? (
                            <span className="text-blue-700">{player.ktc_value.toLocaleString()}</span>
                          ) : (
                            <span className="text-gray-400">--</span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between px-4 py-3 border-t text-sm text-gray-600">
                <span>
                  Showing {page * PAGE_SIZE + 1}–{Math.min((page + 1) * PAGE_SIZE, data.total)} of {data.total.toLocaleString()}
                </span>
                <div className="flex gap-2">
                  <button
                    onClick={() => setPage(p => Math.max(0, p - 1))}
                    disabled={page === 0}
                    className="px-3 py-1 rounded border border-gray-300 disabled:opacity-40 hover:bg-gray-50 transition"
                  >
                    Prev
                  </button>
                  <button
                    onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))}
                    disabled={page >= totalPages - 1}
                    className="px-3 py-1 rounded border border-gray-300 disabled:opacity-40 hover:bg-gray-50 transition"
                  >
                    Next
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
