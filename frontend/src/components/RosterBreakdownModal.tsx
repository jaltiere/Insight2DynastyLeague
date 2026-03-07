import { useQuery } from '@tanstack/react-query';
import { api } from '../services/api';

interface RosterBreakdownModalProps {
  rosterId: number;
  season: number;
  onClose: () => void;
}

interface PlayerPowerScore {
  player_id: string;
  player_name: string;
  position: string;
  team: string | null;
  age: number | null;
  power_score: number;
  age_score: number;
  position_score: number;
  production_score: number;
}

interface RosterBreakdown {
  roster_id: number;
  team_name: string | null;
  owner_name: string;
  total_roster_score: number;
  avg_roster_age: number;
  players: PlayerPowerScore[];
}

export default function RosterBreakdownModal({
  rosterId,
  season,
  onClose,
}: RosterBreakdownModalProps) {
  const { data, isLoading } = useQuery<RosterBreakdown>({
    queryKey: ['rosterBreakdown', season, rosterId],
    queryFn: () => api.getRosterBreakdown(season, rosterId),
  });

  return (
    <div
      className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-lg shadow-xl max-w-6xl w-full max-h-[80vh] overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="bg-blue-600 dark:bg-blue-800 text-white px-6 py-4 flex justify-between items-center">
          <div>
            <h2 className="text-2xl font-bold">
              {data?.team_name || data?.owner_name || 'Loading...'}
            </h2>
            {data && (
              <p className="text-sm">
                Roster Power Score: {data.total_roster_score.toFixed(2)} | Avg
                Age: {data.avg_roster_age.toFixed(1)}
              </p>
            )}
          </div>
          <button
            onClick={onClose}
            className="text-white hover:text-gray-200 text-2xl"
          >
            ×
          </button>
        </div>

        {/* Body */}
        <div className="p-6 overflow-y-auto max-h-[calc(80vh-80px)]">
          {isLoading ? (
            <p className="text-gray-600">Loading roster breakdown...</p>
          ) : (
            <>
              {/* Summary Stats */}
              <div className="mb-6 grid grid-cols-3 gap-4">
                <div className="bg-gray-50 rounded-lg p-4">
                  <p className="text-sm text-gray-500">Average Roster Age</p>
                  <p className="text-3xl font-bold text-blue-600 dark:text-blue-400">
                    {data?.avg_roster_age.toFixed(1)}
                  </p>
                </div>
                <div className="bg-gray-50 rounded-lg p-4">
                  <p className="text-sm text-gray-500">Total Players</p>
                  <p className="text-3xl font-bold text-blue-600 dark:text-blue-400">
                    {data?.players.length || 0}
                  </p>
                </div>
                <div className="bg-gray-50 rounded-lg p-4">
                  <p className="text-sm text-gray-500">Roster Score</p>
                  <p className="text-3xl font-bold text-blue-600 dark:text-blue-400">
                    {data?.total_roster_score.toFixed(2)}
                  </p>
                </div>
              </div>

              {/* Player Table */}
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-3 text-xs font-medium text-gray-500 uppercase text-left">
                        Player
                      </th>
                      <th className="px-4 py-3 text-xs font-medium text-gray-500 uppercase text-center">
                        Pos
                      </th>
                      <th className="px-4 py-3 text-xs font-medium text-gray-500 uppercase text-center">
                        Team
                      </th>
                      <th className="px-4 py-3 text-xs font-medium text-gray-500 uppercase text-center">
                        Age
                      </th>
                      <th className="px-4 py-3 text-xs font-medium text-gray-500 uppercase text-right">
                        Power Score
                      </th>
                      <th className="px-4 py-3 text-xs font-medium text-gray-500 uppercase text-right">
                        Age
                      </th>
                      <th className="px-4 py-3 text-xs font-medium text-gray-500 uppercase text-right">
                        Position
                      </th>
                      <th className="px-4 py-3 text-xs font-medium text-gray-500 uppercase text-right">
                        Production
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200">
                    {data?.players
                      .sort((a, b) => b.power_score - a.power_score)
                      .map((player: PlayerPowerScore) => (
                        <tr key={player.player_id} className="hover:bg-gray-50">
                          <td className="px-4 py-3 text-sm font-medium">
                            {player.player_name}
                          </td>
                          <td className="px-4 py-3 text-sm text-center">
                            <span
                              className={`px-2 py-1 rounded text-white text-xs font-semibold ${getPositionColor(
                                player.position
                              )}`}
                            >
                              {player.position}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-sm text-center">
                            {player.team || '-'}
                          </td>
                          <td className="px-4 py-3 text-sm text-center">
                            {player.age || '-'}
                          </td>
                          <td className="px-4 py-3 text-sm text-right font-semibold text-blue-600 dark:text-blue-400">
                            {player.power_score.toFixed(2)}
                          </td>
                          <td className="px-4 py-3 text-sm text-right">
                            {player.age_score.toFixed(1)}
                          </td>
                          <td className="px-4 py-3 text-sm text-right">
                            {player.position_score.toFixed(1)}
                          </td>
                          <td className="px-4 py-3 text-sm text-right">
                            {player.production_score.toFixed(1)}
                          </td>
                        </tr>
                      ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function getPositionColor(position: string): string {
  const colors: Record<string, string> = {
    QB: 'bg-pink-500',
    RB: 'bg-green-500',
    WR: 'bg-blue-500',
    TE: 'bg-orange-500',
    K: 'bg-purple-500',
    DEF: 'bg-gray-500',
  };
  return colors[position] || 'bg-gray-400';
}
