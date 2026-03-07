import { useState } from 'react';
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
} from 'recharts';
import RosterBreakdownModal from '../components/RosterBreakdownModal';

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
}

interface PowerRankingsResponse {
  season: number;
  rankings: PowerRankingTeam[];
}

export default function PowerRankings() {
  const [selectedRosterId, setSelectedRosterId] = useState<number | null>(null);
  const [modalOpen, setModalOpen] = useState(false);

  const { data, isLoading, error } = useQuery<PowerRankingsResponse>({
    queryKey: ['powerRankings'],
    queryFn: () => api.getPowerRankings(),
  });

  const handleBarClick = (rosterId: number) => {
    setSelectedRosterId(rosterId);
    setModalOpen(true);
  };

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

  const rankings = data?.rankings || [];

  // Chart data transformation
  const chartData = rankings.map((team) => ({
    name: team.team_name || team.display_name,
    score: team.total_score,
    rosterId: team.roster_id,
    rank: team.rank,
  }));

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

      {/* Bar Chart */}
      <div className="bg-white rounded-lg shadow mb-6 p-6">
        <h2 className="text-xl font-semibold mb-4">Team Rankings</h2>
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
                    const data = payload[0].payload;
                    return (
                      <div className="bg-white p-3 border border-gray-200 rounded shadow">
                        <p className="font-semibold">
                          #{data.rank} {data.name}
                        </p>
                        <p className="text-sm">
                          Score: {data.score.toFixed(2)}
                        </p>
                        <p className="text-xs text-gray-500">
                          Click for details
                        </p>
                      </div>
                    );
                  }
                  return null;
                }}
              />
              <Bar
                dataKey="score"
                fill="#3B82F6"
                cursor="pointer"
              >
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

      {/* Rankings Table */}
      <div className="bg-white rounded-lg shadow overflow-x-auto">
        <table className="w-full">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-xs font-medium text-gray-500 uppercase">
                Rank
              </th>
              <th className="px-4 py-3 text-xs font-medium text-gray-500 uppercase text-left">
                Team
              </th>
              <th className="px-4 py-3 text-xs font-medium text-gray-500 uppercase text-right">
                Total
              </th>
              <th className="px-4 py-3 text-xs font-medium text-gray-500 uppercase text-right">
                Current
              </th>
              <th className="px-4 py-3 text-xs font-medium text-gray-500 uppercase text-right">
                Roster
              </th>
              <th className="px-4 py-3 text-xs font-medium text-gray-500 uppercase text-right">
                Historical
              </th>
              <th className="px-4 py-3 text-xs font-medium text-gray-500 uppercase text-center">
                Record
              </th>
              <th className="px-4 py-3 text-xs font-medium text-gray-500 uppercase text-right">
                PF
              </th>
              <th className="px-4 py-3 text-xs font-medium text-gray-500 uppercase text-right">
                Avg Age
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {rankings.map((team) => (
              <tr
                key={team.roster_id}
                className="hover:bg-gray-50 cursor-pointer"
                onClick={() => handleBarClick(team.roster_id)}
              >
                <td className="px-4 py-3 text-sm font-bold text-center">
                  {team.rank}
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

function getBarColor(rank: number): string {
  if (rank === 1) return '#059669'; // green-600
  if (rank <= 3) return '#10B981'; // green-500
  if (rank <= 6) return '#3B82F6'; // blue-500
  if (rank <= 9) return '#6366F1'; // indigo-500
  return '#9CA3AF'; // gray-400
}
