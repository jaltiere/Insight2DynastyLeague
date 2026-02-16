import { useQuery } from '@tanstack/react-query';
import { api } from '../services/api';

export default function Home() {
  const { data: standings, isLoading, error } = useQuery({
    queryKey: ['standings'],
    queryFn: api.getStandings,
  });

  if (isLoading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <h1 className="text-4xl font-bold mb-6">Current Standings</h1>
        <div className="bg-white rounded-lg shadow p-6">
          <p className="text-gray-600">Loading standings...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="container mx-auto px-4 py-8">
        <h1 className="text-4xl font-bold mb-6">Current Standings</h1>
        <div className="bg-white rounded-lg shadow p-6">
          <p className="text-red-600">Error loading standings: {(error as Error).message}</p>
        </div>
      </div>
    );
  }

  const division1 = standings?.standings.filter((team: any) => team.division === 1) || [];
  const division2 = standings?.standings.filter((team: any) => team.division === 2) || [];

  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-4xl font-bold mb-6">Current Standings - {standings?.season}</h1>

      <div className="grid md:grid-cols-2 gap-6 mb-8">
        {/* Division 1 */}
        <div className="bg-white rounded-lg shadow">
          <div className="bg-blue-600 text-white px-6 py-3 rounded-t-lg">
            <h2 className="text-xl font-semibold">{standings?.division_names?.['1'] || 'Division 1'}</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Team</th>
                  <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">W</th>
                  <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">L</th>
                  <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">T</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">PF</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">PA</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {division1.map((team: any) => (
                  <tr key={team.roster_id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-sm font-medium text-gray-900">
                      {team.team_name
                        ? <>{team.team_name} <span className="text-gray-500 font-normal">({team.username})</span></>
                        : team.username}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-900 text-center">{team.wins}</td>
                    <td className="px-4 py-3 text-sm text-gray-900 text-center">{team.losses}</td>
                    <td className="px-4 py-3 text-sm text-gray-900 text-center">{team.ties}</td>
                    <td className="px-4 py-3 text-sm text-gray-900 text-right">{team.points_for.toFixed(2)}</td>
                    <td className="px-4 py-3 text-sm text-gray-900 text-right">{team.points_against.toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Division 2 */}
        <div className="bg-white rounded-lg shadow">
          <div className="bg-green-600 text-white px-6 py-3 rounded-t-lg">
            <h2 className="text-xl font-semibold">{standings?.division_names?.['2'] || 'Division 2'}</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Team</th>
                  <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">W</th>
                  <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">L</th>
                  <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">T</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">PF</th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">PA</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {division2.map((team: any) => (
                  <tr key={team.roster_id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-sm font-medium text-gray-900">
                      {team.team_name
                        ? <>{team.team_name} <span className="text-gray-500 font-normal">({team.username})</span></>
                        : team.username}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-900 text-center">{team.wins}</td>
                    <td className="px-4 py-3 text-sm text-gray-900 text-center">{team.losses}</td>
                    <td className="px-4 py-3 text-sm text-gray-900 text-center">{team.ties}</td>
                    <td className="px-4 py-3 text-sm text-gray-900 text-right">{team.points_for.toFixed(2)}</td>
                    <td className="px-4 py-3 text-sm text-gray-900 text-right">{team.points_against.toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
