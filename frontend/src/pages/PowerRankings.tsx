import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../services/api';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
  LineChart,
  Line,
  Legend,
} from 'recharts';
import RosterBreakdownModal from '../components/RosterBreakdownModal';
import {
  defaultDirectionFor,
  sortTeams,
  type SortDirection,
  type SortField,
} from '../utils/powerRankingSort';

interface PowerRankingTeam {
  rank: number;
  roster_id: number;
  user_id: string;
  username: string;
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
  previous_rank: number | null;
}

interface PowerRankingsResponse {
  season: number;
  rankings: PowerRankingTeam[];
}

interface SnapshotWeek {
  week: number;
  rank: number;
  total_score: number;
}

interface TrendTeam {
  roster_id: number;
  display_name: string;
  team_name: string | null;
  current_rank: number;
  ranks_by_week: SnapshotWeek[];
}

interface TrendsResponse {
  season: number;
  weeks: number[];
  teams: TrendTeam[];
}

const TREND_COLORS = [
  '#059669', '#3B82F6', '#F59E0B', '#EF4444', '#8B5CF6',
  '#EC4899', '#14B8A6', '#F97316', '#6366F1', '#10B981',
  '#84CC16', '#06B6D4',
];

function SortArrow({
  field,
  sortField,
  sortDir,
}: {
  field: SortField;
  sortField: SortField;
  sortDir: SortDirection;
}) {
  if (field !== sortField) return null;
  return <span className="text-blue-600 ml-1">{sortDir === 'asc' ? '▲' : '▼'}</span>;
}

export default function PowerRankings() {
  const [selectedRosterId, setSelectedRosterId] = useState<number | null>(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [sortField, setSortField] = useState<SortField>('rank');
  const [sortDir, setSortDir] = useState<SortDirection>('asc');

  const { data, isLoading, error } = useQuery<PowerRankingsResponse>({
    queryKey: ['powerRankings'],
    queryFn: () => api.getPowerRankings(),
  });

  const { data: trendsData } = useQuery<TrendsResponse>({
    queryKey: ['powerRankingsTrends', data?.season],
    queryFn: () => api.getPowerRankingsTrends(data!.season),
    enabled: !!data?.season,
  });

  const handleBarClick = (rosterId: number) => {
    setSelectedRosterId(rosterId);
    setModalOpen(true);
  };

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDir((prev) => (prev === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortField(field);
      setSortDir(defaultDirectionFor(field));
    }
  };

  // Memoised so the identity is stable across renders; a fresh [] each time
  // would invalidate the sort memo below on every render.
  const rankings = useMemo(() => data?.rankings ?? [], [data]);

  // Only the table reorders. The bar chart stays in rank order so it keeps
  // reading as a ranking rather than silently re-scrambling underneath.
  const sortedRankings = useMemo(
    () => sortTeams(rankings, sortField, sortDir),
    [rankings, sortField, sortDir]
  );

  if (isLoading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <h1 className="text-4xl font-bold mb-6">Power Rankings</h1>
        <div className="bg-white rounded-lg shadow p-6">
          <p className="text-gray-600">Loading power rankings...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="container mx-auto px-4 py-8">
        <h1 className="text-4xl font-bold mb-6">Power Rankings</h1>
        <div className="bg-white rounded-lg shadow p-6">
          <p className="text-red-600">
            Error loading power rankings: {(error as Error).message}
          </p>
        </div>
      </div>
    );
  }

  const thClass =
    'px-4 py-3 text-xs font-medium text-gray-500 uppercase cursor-pointer select-none hover:bg-gray-100';

  const chartData = rankings.map((team) => ({
    name: team.team_name || team.display_name,
    score: team.total_score,
    rosterId: team.roster_id,
    rank: team.rank,
  }));

  // Build line chart data: one row per week, each team label as a key
  const hasTrends = (trendsData?.weeks?.length ?? 0) > 0;
  const trendChartData = hasTrends
    ? trendsData!.weeks.map((week) => {
        const row: Record<string, number | string> = { week: `Wk ${week}` };
        for (const team of trendsData!.teams) {
          const snap = team.ranks_by_week.find((s) => s.week === week);
          if (snap) {
            row[team.team_name || team.display_name] = snap.rank;
          }
        }
        return row;
      })
    : [];

  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-4xl font-bold mb-6">Power Rankings</h1>

      {/* Algorithm Explanation */}
      <div className="bg-white rounded-lg shadow mb-6 p-6">
        <h2 className="text-xl font-semibold mb-3">How Rankings Work</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <h3 className="font-semibold text-blue-600 dark:text-blue-400">
              Current Season (40%)
            </h3>
            <p className="text-sm text-gray-600">
              Win %, points scored, point differential, recent form
            </p>
          </div>
          <div>
            <h3 className="font-semibold text-green-600 dark:text-green-400">
              Roster Value (40%)
            </h3>
            <p className="text-sm text-gray-600">
              Player ages, positional value, roster depth (dynasty-focused)
            </p>
          </div>
          <div>
            <h3 className="font-semibold text-purple-600 dark:text-purple-400">
              Historical (20%)
            </h3>
            <p className="text-sm text-gray-600">
              Playoff appearances, championships, consistency
            </p>
          </div>
        </div>
      </div>

      {/* Rankings Table */}
      <div className="bg-white rounded-lg shadow overflow-x-auto mb-6">
        <table className="w-full">
          <thead className="bg-gray-50">
            <tr>
              <th
                className={`${thClass} text-center`}
                onClick={() => handleSort('rank')}
              >
                Rank
                <SortArrow field="rank" sortField={sortField} sortDir={sortDir} />
              </th>
              <th
                className={`${thClass} text-center`}
                onClick={() => handleSort('trend')}
              >
                Trend
                <SortArrow field="trend" sortField={sortField} sortDir={sortDir} />
              </th>
              <th
                className={`${thClass} text-left`}
                onClick={() => handleSort('team')}
              >
                Team
                <SortArrow field="team" sortField={sortField} sortDir={sortDir} />
              </th>
              <th
                className={`${thClass} text-right`}
                onClick={() => handleSort('total')}
              >
                Total
                <SortArrow field="total" sortField={sortField} sortDir={sortDir} />
              </th>
              <th
                className={`${thClass} text-right`}
                onClick={() => handleSort('current')}
              >
                Current
                <SortArrow field="current" sortField={sortField} sortDir={sortDir} />
              </th>
              <th
                className={`${thClass} text-right`}
                onClick={() => handleSort('roster')}
              >
                Roster
                <SortArrow field="roster" sortField={sortField} sortDir={sortDir} />
              </th>
              <th
                className={`${thClass} text-right`}
                onClick={() => handleSort('historical')}
              >
                Historical
                <SortArrow field="historical" sortField={sortField} sortDir={sortDir} />
              </th>
              <th
                className={`${thClass} text-center`}
                onClick={() => handleSort('record')}
              >
                Record
                <SortArrow field="record" sortField={sortField} sortDir={sortDir} />
              </th>
              <th
                className={`${thClass} text-right`}
                onClick={() => handleSort('pf')}
              >
                PF
                <SortArrow field="pf" sortField={sortField} sortDir={sortDir} />
              </th>
              <th
                className={`${thClass} text-right`}
                onClick={() => handleSort('age')}
              >
                Avg Age
                <SortArrow field="age" sortField={sortField} sortDir={sortDir} />
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {sortedRankings.map((team) => (
              <tr
                key={team.roster_id}
                className="hover:bg-gray-50 cursor-pointer"
                onClick={() => handleBarClick(team.roster_id)}
              >
                <td className="px-4 py-3 text-sm font-bold text-center">
                  {team.rank}
                </td>
                <td className="px-4 py-3 text-sm text-center">
                  <TrendArrow change={team.rank_change} />
                </td>
                <td className="px-4 py-3 text-sm font-medium">
                  {team.team_name || team.display_name}
                </td>
                <td className="px-4 py-3 text-sm text-right font-semibold text-blue-600 dark:text-blue-400">
                  {team.total_score.toFixed(2)}
                </td>
                <td className="px-4 py-3 text-sm text-right">
                  {team.current_season_score.toFixed(1)}
                </td>
                <td className="px-4 py-3 text-sm text-right">
                  {team.roster_value_score.toFixed(1)}
                </td>
                <td className="px-4 py-3 text-sm text-right">
                  {team.historical_score.toFixed(1)}
                </td>
                <td className="px-4 py-3 text-sm text-center">
                  {team.wins}-{team.losses}
                  {team.ties > 0 ? `-${team.ties}` : ''}
                </td>
                <td className="px-4 py-3 text-sm text-right">
                  {team.points_for.toFixed(1)}
                </td>
                <td className="px-4 py-3 text-sm text-right">
                  {team.avg_roster_age.toFixed(1)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Rank Trajectory Chart (shown only when snapshots exist) */}
      {hasTrends && (
        <div className="bg-white rounded-lg shadow mb-6 p-6">
          <h2 className="text-xl font-semibold mb-1">Rank Trajectory</h2>
          <p className="text-sm text-gray-500 mb-4">Lower = better. Week-by-week snapshot.</p>
          <ResponsiveContainer width="100%" height={420}>
            <LineChart
              data={trendChartData}
              margin={{ top: 10, right: 20, left: 0, bottom: 10 }}
            >
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="week" />
              <YAxis
                reversed
                domain={[1, rankings.length]}
                tickCount={rankings.length}
                allowDecimals={false}
                label={{ value: 'Rank', angle: -90, position: 'insideLeft', offset: 10 }}
              />
              <Tooltip
                formatter={(value: number | undefined, name: string | undefined) => [`#${value}`, name ?? '']}
              />
              <Legend />
              {trendsData!.teams.map((team, idx) => (
                <Line
                  key={team.roster_id}
                  type="monotone"
                  dataKey={team.team_name || team.display_name}
                  stroke={TREND_COLORS[idx % TREND_COLORS.length]}
                  strokeWidth={2}
                  dot={{ r: 4 }}
                  activeDot={{ r: 6 }}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Bar Chart */}
      <div className="bg-white rounded-lg shadow mb-6 p-6">
        <h2 className="text-xl font-semibold mb-4">Score Breakdown</h2>
        {chartData.length === 0 ? (
          <p className="text-gray-600">No data available for chart</p>
        ) : (
          <ResponsiveContainer width="100%" height={600}>
            <BarChart
              data={chartData}
              layout="vertical"
              margin={{ top: 20, right: 30, left: 150, bottom: 20 }}
            >
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis type="number" domain={[0, 100]} />
              <YAxis dataKey="name" type="category" width={140} />
              <Tooltip
                content={({ active, payload }) => {
                  if (active && payload?.[0]) {
                    const d = payload[0].payload;
                    return (
                      <div className="bg-white p-3 border border-gray-200 rounded shadow">
                        <p className="font-semibold">
                          #{d.rank} {d.name}
                        </p>
                        <p className="text-sm">Score: {d.score.toFixed(2)}</p>
                        <p className="text-xs text-gray-500">Click for details</p>
                      </div>
                    );
                  }
                  return null;
                }}
              />
              <Bar dataKey="score" fill="#3B82F6" cursor="pointer">
                {chartData.map((entry, index) => (
                  <Cell
                    key={`cell-${index}`}
                    fill={getBarColor(entry.rank)}
                    onClick={() => handleBarClick(entry.rosterId)}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Roster Breakdown Modal */}
      {modalOpen && selectedRosterId && data?.season && (
        <RosterBreakdownModal
          rosterId={selectedRosterId}
          season={data.season}
          onClose={() => setModalOpen(false)}
        />
      )}
    </div>
  );
}

function TrendArrow({ change }: { change: number | null }) {
  if (change === null || change === undefined) {
    return <span className="text-gray-400 text-xs">—</span>;
  }
  if (change === 0) {
    return <span className="text-gray-500 text-xs font-medium">=</span>;
  }
  if (change > 0) {
    return (
      <span className="text-green-600 font-semibold text-xs whitespace-nowrap">
        ▲{change}
      </span>
    );
  }
  return (
    <span className="text-red-500 font-semibold text-xs whitespace-nowrap">
      ▼{Math.abs(change)}
    </span>
  );
}

function getBarColor(rank: number): string {
  if (rank === 1) return '#059669';
  if (rank <= 3) return '#10B981';
  if (rank <= 6) return '#3B82F6';
  if (rank <= 9) return '#6366F1';
  return '#9CA3AF';
}
