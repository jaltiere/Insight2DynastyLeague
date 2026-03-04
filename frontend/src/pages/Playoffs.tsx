import { useQuery } from '@tanstack/react-query';
import { api } from '../services/api';

interface PlayoffTeam {
  roster_id: number;
  user_id: string;
  display_name: string;
  username: string;
  team_name: string;
  avatar: string;
  division: number;
  division_name: string;
  current_record: string;
  projected_record: string;
  team_rating: number;
  rating_change: number;
  make_playoffs_pct: number;
  make_playoffs_display: string;
  win_division_pct: number;
  win_division_display: string;
  first_round_bye_pct: number;
  first_round_bye_display: string;
  win_finals_pct: number;
  win_finals_display: string;
  points_for: number;
  points_against: number;
  median_wins: number;
  median_losses: number;
  max_potential_points: number;
}

interface DraftOrderEntry {
  pick: number;
  roster_id: number;
  user_id: string;
  display_name: string;
  team_name: string;
  avatar: string;
  reason: string;
  max_potential_points: number;
  projected_record: string;
}

interface PlayoffOddsResponse {
  season: number;
  season_started: boolean;
  current_week: number;
  regular_season_weeks: number;
  playoff_odds: PlayoffTeam[];
  draft_order: DraftOrderEntry[];
}

function getAvatarUrl(avatar: string | null): string {
  if (!avatar) return '';
  return `https://sleepercdn.com/avatars/thumbs/${avatar}`;
}

function getPctBgClass(pct: number): string {
  if (pct >= 99) return 'bg-blue-800 text-white';
  if (pct >= 90) return 'bg-blue-700 text-white';
  if (pct >= 70) return 'bg-blue-600 text-white';
  if (pct >= 50) return 'bg-blue-500 text-white';
  if (pct >= 30) return 'bg-blue-400 text-white';
  if (pct >= 10) return 'bg-blue-300 text-blue-900';
  if (pct >= 1) return 'bg-blue-200 text-blue-900';
  return 'bg-blue-50 text-blue-800';
}

export default function Playoffs() {
  const { data, isLoading, error } = useQuery<PlayoffOddsResponse>({
    queryKey: ['playoffOdds'],
    queryFn: () => api.getPlayoffOdds(),
  });

  if (isLoading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <h1 className="text-4xl font-bold mb-6">Playoffs</h1>
        <div className="bg-white rounded-lg shadow p-6">
          <p className="text-gray-600">Loading playoff odds...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="container mx-auto px-4 py-8">
        <h1 className="text-4xl font-bold mb-6">Playoffs</h1>
        <div className="bg-white rounded-lg shadow p-6">
          <p className="text-red-600">Error loading playoff odds: {(error as Error).message}</p>
        </div>
      </div>
    );
  }

  if (!data || !data.season_started) {
    return (
      <div className="container mx-auto px-4 py-8">
        <h1 className="text-4xl font-bold mb-6">Playoffs</h1>
        <div className="bg-white rounded-lg shadow p-12 text-center">
          <div className="text-6xl mb-4">🏈</div>
          <h2 className="text-2xl font-bold text-gray-700 mb-2">In Season Feature</h2>
          <p className="text-gray-500">Playoff odds will be available once the season begins.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8">
      {/* Playoff Odds Section */}
      <div className="mb-10">
        <div className="flex items-baseline gap-3 mb-1">
          <h1 className="text-4xl font-bold uppercase">Playoff Odds</h1>
          <span className="text-sm text-gray-500">
            Week {data.current_week} of {data.regular_season_weeks}
          </span>
        </div>
        <p className="text-sm text-gray-500 mb-4">
          Based on {(10000).toLocaleString()} Monte Carlo simulations
        </p>

        <div className="bg-white rounded-lg shadow overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="bg-gray-800 text-white text-xs uppercase">
                  <th className="px-3 py-3 text-left font-medium">
                    <div>Team</div>
                    <div className="font-normal text-gray-400">Rating</div>
                  </th>
                  <th className="px-2 py-3 text-center font-medium">Change</th>
                  <th className="px-3 py-3 text-left font-medium min-w-[180px]">Team</th>
                  <th className="px-3 py-3 text-left font-medium">Team Division</th>
                  <th className="px-3 py-3 text-center font-medium">
                    <div>Current</div>
                    <div className="font-normal text-gray-400">Record</div>
                  </th>
                  <th className="px-3 py-3 text-center font-medium">
                    <div>Projected</div>
                    <div className="font-normal text-gray-400">Record</div>
                  </th>
                  <th className="px-3 py-3 text-center font-medium">
                    <div>Make</div>
                    <div className="font-normal text-gray-400">Playoffs</div>
                  </th>
                  <th className="px-3 py-3 text-center font-medium">
                    <div>Win</div>
                    <div className="font-normal text-gray-400">Division</div>
                  </th>
                  <th className="px-3 py-3 text-center font-medium">
                    <div>1st-Round</div>
                    <div className="font-normal text-gray-400">Bye</div>
                  </th>
                  <th className="px-3 py-3 text-center font-medium">
                    <div>Win</div>
                    <div className="font-normal text-gray-400">Finals</div>
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {data.playoff_odds.map((team) => (
                  <tr key={team.roster_id} className="hover:bg-gray-50">
                    {/* Team Rating */}
                    <td className="px-3 py-3 text-sm font-bold text-gray-900 text-center">
                      {team.team_rating}
                    </td>

                    {/* Change */}
                    <td className="px-2 py-3 text-sm font-bold text-center">
                      {team.rating_change !== 0 ? (
                        <span className={
                          team.rating_change > 0
                            ? 'text-green-600 bg-green-100 px-2 py-1 rounded'
                            : 'text-red-600 bg-red-100 px-2 py-1 rounded'
                        }>
                          {team.rating_change > 0 ? `+${team.rating_change}` : team.rating_change}
                        </span>
                      ) : (
                        <span className="text-gray-400">-</span>
                      )}
                    </td>

                    {/* Team Name + Avatar */}
                    <td className="px-3 py-3">
                      <div className="flex items-center gap-3">
                        {team.avatar && (
                          <img
                            src={getAvatarUrl(team.avatar)}
                            alt=""
                            className="w-8 h-8 rounded-full flex-shrink-0"
                          />
                        )}
                        <div className="min-w-0">
                          <div className="text-sm font-semibold text-gray-900 truncate">
                            {team.team_name || team.display_name}
                          </div>
                          <div className="text-xs text-gray-500 truncate">
                            {team.username}
                          </div>
                        </div>
                      </div>
                    </td>

                    {/* Division */}
                    <td className="px-3 py-3 text-sm text-gray-700">
                      {team.division_name}
                    </td>

                    {/* Current Record */}
                    <td className="px-3 py-3 text-sm text-gray-900 text-center whitespace-nowrap">
                      {team.current_record}
                    </td>

                    {/* Projected Record */}
                    <td className="px-3 py-3 text-sm text-gray-900 text-center whitespace-nowrap">
                      {team.projected_record}
                    </td>

                    {/* Probability cells with color intensity */}
                    <td className="px-1 py-1">
                      <div className={`${getPctBgClass(team.make_playoffs_pct)} text-center py-2 px-2 rounded text-sm font-semibold`}>
                        {team.make_playoffs_display}
                      </div>
                    </td>
                    <td className="px-1 py-1">
                      <div className={`${getPctBgClass(team.win_division_pct)} text-center py-2 px-2 rounded text-sm font-semibold`}>
                        {team.win_division_display}
                      </div>
                    </td>
                    <td className="px-1 py-1">
                      <div className={`${getPctBgClass(team.first_round_bye_pct)} text-center py-2 px-2 rounded text-sm font-semibold`}>
                        {team.first_round_bye_display}
                      </div>
                    </td>
                    <td className="px-1 py-1">
                      <div className={`${getPctBgClass(team.win_finals_pct)} text-center py-2 px-2 rounded text-sm font-semibold`}>
                        {team.win_finals_display}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Draft Order Section */}
      {data.draft_order.length > 0 && (
        <div>
          <h2 className="text-3xl font-bold uppercase mb-1">Projected Draft Order</h2>
          <p className="text-sm text-gray-500 mb-4">
            If the season ended today
          </p>

          <div className="bg-white rounded-lg shadow overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="bg-gray-800 text-white text-xs uppercase">
                    <th className="px-4 py-3 text-center font-medium w-16">Pick</th>
                    <th className="px-4 py-3 text-left font-medium">Team</th>
                    <th className="px-4 py-3 text-left font-medium">Basis</th>
                    <th className="px-4 py-3 text-center font-medium">Max Potential Pts</th>
                    <th className="px-4 py-3 text-center font-medium">Projected Record</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {data.draft_order.map((entry) => (
                    <tr key={entry.pick} className="hover:bg-gray-50">
                      <td className="px-4 py-3 text-center">
                        <span className="inline-flex items-center justify-center w-8 h-8 rounded-full bg-gray-800 text-white text-sm font-bold">
                          {entry.pick}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-3">
                          {entry.avatar && (
                            <img
                              src={getAvatarUrl(entry.avatar)}
                              alt=""
                              className="w-8 h-8 rounded-full flex-shrink-0"
                            />
                          )}
                          <div className="min-w-0">
                            <div className="text-sm font-semibold text-gray-900 truncate">
                              {entry.team_name || entry.display_name}
                            </div>
                            <div className="text-xs text-gray-500 truncate">
                              {entry.display_name}
                            </div>
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-700">
                        {entry.reason}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-900 text-center">
                        {entry.max_potential_points.toFixed(1)}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-900 text-center whitespace-nowrap">
                        {entry.projected_record}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
