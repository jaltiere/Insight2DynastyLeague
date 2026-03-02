import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../services/api';

const POSITION_COLORS: Record<string, string> = {
  QB: 'bg-pink-500',
  RB: 'bg-green-500',
  WR: 'bg-blue-500',
  TE: 'bg-orange-500',
  K: 'bg-purple-500',
  DEF: 'bg-gray-500',
};

const GRADE_COLORS: Record<string, string> = {
  'A+': 'bg-green-600 text-white',
  A: 'bg-green-600 text-white',
  'A-': 'bg-green-500 text-white',
  'B+': 'bg-blue-600 text-white',
  B: 'bg-blue-500 text-white',
  'B-': 'bg-blue-400 text-white',
  'C+': 'bg-gray-400 text-white',
  C: 'bg-gray-400 text-white',
  'C-': 'bg-gray-400 text-white',
  'D+': 'bg-orange-400 text-white',
  D: 'bg-orange-500 text-white',
  'D-': 'bg-orange-600 text-white',
  F: 'bg-red-600 text-white',
};

interface PlayerDetail {
  player_id: string;
  player_name: string;
  position: string | null;
  weighted_points: number;
  adjusted_points: number;
  starter_weeks: number;
  bench_weeks: number;
  replacement_factor: number;
}

interface PickDetail {
  season: number;
  round: number;
  status: 'projected' | 'actual';
  value: number;
  drafted_player: string | null;
}

interface TradeSide {
  roster_id: number;
  owner_name: string;
  user_id: string;
  grade: string;
  total_value: number;
  value_share: number;
  assets_received: {
    players: PlayerDetail[];
    draft_picks: PickDetail[];
  };
}

interface Trade {
  trade_id: string;
  season: number;
  week: number;
  date: number | null;
  weeks_of_data: number;
  lopsidedness: number;
  sides: TradeSide[];
}

interface Owner {
  user_id: string;
  username: string;
  display_name: string;
}

type SortMode = 'lopsided' | 'recent' | 'even';

function formatDate(ms: number | null): string {
  if (!ms) return '';
  return new Date(ms).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

function PositionBadge({ position }: { position: string | null }) {
  if (!position) return null;
  const bg = POSITION_COLORS[position] || 'bg-gray-400';
  return (
    <span className={`${bg} text-white text-xs font-bold px-1.5 py-0.5 rounded mr-1.5`}>
      {position}
    </span>
  );
}

function GradeBadge({ grade }: { grade: string }) {
  const colors = GRADE_COLORS[grade] || 'bg-gray-400 text-white';
  return (
    <span className={`${colors} text-lg font-bold px-3 py-1 rounded-lg inline-block min-w-[3rem] text-center`}>
      {grade}
    </span>
  );
}

function ValueBar({ sides }: { sides: TradeSide[] }) {
  if (sides.length !== 2) return null;
  const [a, b] = sides;
  const total = a.total_value + b.total_value;
  if (total === 0) return null;
  const pctA = (a.total_value / total) * 100;
  return (
    <div className="flex h-2 rounded-full overflow-hidden bg-gray-200 mt-2">
      <div className="bg-green-500 transition-all" style={{ width: `${pctA}%` }} />
      <div className="bg-red-400 transition-all" style={{ width: `${100 - pctA}%` }} />
    </div>
  );
}

function TradeCard({ trade }: { trade: Trade }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="bg-white rounded-lg shadow">
      {/* Header */}
      <div
        className="px-4 py-3 flex items-center justify-between cursor-pointer hover:bg-gray-50 rounded-t-lg"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-3">
          <span className="text-sm font-semibold text-gray-900">
            {trade.season} Week {trade.week}
          </span>
          <span className="text-xs text-gray-500">{formatDate(trade.date)}</span>
          <span className="text-xs text-gray-400">{trade.weeks_of_data}w of data</span>
        </div>
        <div className="flex items-center gap-3">
          {trade.sides.map((side) => (
            <div key={side.roster_id} className="flex items-center gap-1.5">
              <span className="text-xs text-gray-600 hidden sm:inline">{side.owner_name}</span>
              <GradeBadge grade={side.grade} />
            </div>
          ))}
          <span className="text-gray-400 ml-1">{expanded ? '\u25B2' : '\u25BC'}</span>
        </div>
      </div>

      {/* Value bar */}
      <div className="px-4 pb-2">
        <ValueBar sides={trade.sides} />
      </div>

      {/* Expanded details */}
      {expanded && (
        <div className="border-t border-gray-200 px-4 py-4">
          <div className={`grid gap-4 ${trade.sides.length === 2 ? 'grid-cols-1 md:grid-cols-2' : 'grid-cols-1'}`}>
            {trade.sides.map((side) => (
              <div key={side.roster_id} className="bg-gray-50 rounded-lg p-3">
                <div className="flex items-center justify-between mb-3">
                  <div>
                    <span className="font-semibold text-gray-900">{side.owner_name}</span>
                    <span className="text-xs text-gray-500 ml-2">
                      {side.total_value.toFixed(1)} pts ({(side.value_share * 100).toFixed(0)}%)
                    </span>
                  </div>
                  <GradeBadge grade={side.grade} />
                </div>

                {/* Players received */}
                {side.assets_received.players.length > 0 && (
                  <div className="mb-3">
                    <div className="text-xs font-semibold text-gray-500 uppercase mb-1.5">
                      Players Received
                    </div>
                    <div className="space-y-2">
                      {side.assets_received.players.map((p) => (
                        <div key={p.player_id} className="bg-white rounded p-2">
                          <div className="flex items-center justify-between">
                            <div className="flex items-center">
                              <PositionBadge position={p.position} />
                              <span className="text-sm font-medium text-gray-900">{p.player_name}</span>
                            </div>
                            <div className="text-right">
                              <span className="text-sm font-semibold text-gray-900">
                                {p.adjusted_points.toFixed(1)}
                              </span>
                              <span className="text-xs text-gray-500 ml-1">pts</span>
                            </div>
                          </div>
                          <div className="flex items-center gap-3 mt-1 text-xs text-gray-500">
                            <span>{p.starter_weeks}w starter</span>
                            <span>{p.bench_weeks}w bench</span>
                            <span>{p.starter_weeks + p.bench_weeks}w total</span>
                            {p.replacement_factor < 1.0 && (
                              <span className="text-orange-500" title="Position was well-replaced by sender, reducing this player's impact">
                                repl: {p.replacement_factor.toFixed(2)}x
                              </span>
                            )}
                            {p.weighted_points !== p.adjusted_points && (
                              <span className="text-gray-400">
                                (raw: {p.weighted_points.toFixed(1)})
                              </span>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Draft picks received */}
                {side.assets_received.draft_picks.length > 0 && (
                  <div>
                    <div className="text-xs font-semibold text-gray-500 uppercase mb-1.5">
                      Draft Picks Received
                    </div>
                    <div className="space-y-1">
                      {side.assets_received.draft_picks.map((pick, idx) => (
                        <div key={idx} className="bg-white rounded p-2 flex items-center justify-between">
                          <div>
                            <span className="text-sm text-gray-900">
                              {pick.season} Round {pick.round}
                            </span>
                            {pick.drafted_player && (
                              <span className="text-sm text-gray-500 ml-1">
                                ({pick.drafted_player})
                              </span>
                            )}
                          </div>
                          <div className="text-right flex items-center gap-2">
                            <span className="text-sm font-semibold text-gray-900">
                              {pick.value.toFixed(1)}
                            </span>
                            <span className="text-xs text-gray-500">pts</span>
                            <span
                              className={`text-xs px-1.5 py-0.5 rounded ${
                                pick.status === 'actual'
                                  ? 'bg-green-100 text-green-700'
                                  : 'bg-yellow-100 text-yellow-700'
                              }`}
                            >
                              {pick.status === 'actual' ? 'actual' : 'proj'}
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {side.assets_received.players.length === 0 &&
                  side.assets_received.draft_picks.length === 0 && (
                    <p className="text-xs text-gray-400 italic">No tracked assets received</p>
                  )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

export default function TradeGrades() {
  const [sort, setSort] = useState<SortMode>('lopsided');
  const [season, setSeason] = useState<number | undefined>(undefined);
  const [ownerId, setOwnerId] = useState<string | undefined>(undefined);

  const { data: seasonsData } = useQuery({
    queryKey: ['seasons'],
    queryFn: () => api.getSeasons(),
  });

  const { data: ownersData } = useQuery({
    queryKey: ['owners'],
    queryFn: () => api.getAllOwners().then(res => res.data),
  });

  const { data, isLoading, error } = useQuery({
    queryKey: ['tradeGrades', season, sort, ownerId],
    queryFn: () =>
      api.getTradeGrades({
        season,
        sort,
        owner_id: ownerId,
      }),
  });

  const trades: Trade[] = data?.trades || [];
  const seasons: number[] = (seasonsData?.seasons || [])
    .map((s: { year: number }) => s.year)
    .sort((a: number, b: number) => b - a);
  const owners: Owner[] = (ownersData?.owners || [])
    .map((o: Owner) => ({
      user_id: o.user_id,
      username: o.username,
      display_name: o.display_name || o.username,
    }))
    .sort((a: Owner, b: Owner) => a.display_name.localeCompare(b.display_name));

  if (isLoading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <h1 className="text-4xl font-bold mb-6">Trade Grades</h1>
        <div className="flex justify-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 dark:border-blue-400" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="container mx-auto px-4 py-8">
        <h1 className="text-4xl font-bold mb-6">Trade Grades</h1>
        <div className="bg-red-50 border border-red-200 rounded-lg p-6 dark:bg-red-900/20 dark:border-red-800">
          <h2 className="text-red-800 text-lg font-semibold dark:text-red-400">Error loading trade grades</h2>
          <p className="text-red-600 mt-2 dark:text-red-400">Please try refreshing the page.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-4xl font-bold mb-6">Trade Grades</h1>

      {/* Filters */}
      <div className="bg-white rounded-lg shadow mb-6">
        <div className="flex flex-wrap items-center gap-4 px-6 py-3">
          <div className="flex items-center gap-2">
            <label className="text-sm font-medium text-gray-700">Owner:</label>
            <select
              value={ownerId ?? ''}
              onChange={(e) => setOwnerId(e.target.value || undefined)}
              className="border border-gray-300 rounded px-3 py-1.5 text-sm bg-white text-gray-900"
            >
              <option value="">All Owners</option>
              {owners.map((o) => (
                <option key={o.user_id} value={o.user_id}>
                  {o.display_name}
                </option>
              ))}
            </select>
          </div>
          <div className="flex items-center gap-2">
            <label className="text-sm font-medium text-gray-700">Season:</label>
            <select
              value={season ?? ''}
              onChange={(e) => setSeason(e.target.value ? Number(e.target.value) : undefined)}
              className="border border-gray-300 rounded px-3 py-1.5 text-sm bg-white text-gray-900"
            >
              <option value="">All Seasons</option>
              {seasons.map((yr: number) => (
                <option key={yr} value={yr}>{yr}</option>
              ))}
            </select>
          </div>
          <div className="flex items-center gap-2">
            <label className="text-sm font-medium text-gray-700">Sort:</label>
            <select
              value={sort}
              onChange={(e) => setSort(e.target.value as SortMode)}
              className="border border-gray-300 rounded px-3 py-1.5 text-sm bg-white text-gray-900"
            >
              <option value="lopsided">Most Lopsided</option>
              <option value="recent">Most Recent</option>
              <option value="even">Most Even</option>
            </select>
          </div>
          <div className="text-sm text-gray-500 ml-auto">
            {trades.length} trade{trades.length !== 1 ? 's' : ''}
          </div>
        </div>
      </div>

      {/* Trade cards */}
      {trades.length === 0 ? (
        <div className="bg-white rounded-lg shadow p-8 text-center">
          <p className="text-gray-500">No trades found.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {trades.map((trade) => (
            <TradeCard key={trade.trade_id} trade={trade} />
          ))}
        </div>
      )}
    </div>
  );
}
