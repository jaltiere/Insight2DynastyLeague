import { useQuery } from '@tanstack/react-query';
import { api } from '../services/api';

interface TaxiPlayer {
  player_id: string;
  full_name: string;
  position: string | null;
  team: string | null;
}

interface TaxiTeam {
  owner_name: string;
  team_name: string;
  avatar: string | null;
  players: TaxiPlayer[];
}

interface TaxiSquadsData {
  season: number | null;
  teams: TaxiTeam[];
}

function avatarUrl(avatarId: string | null): string | null {
  if (!avatarId) return null;
  return `https://sleepercdn.com/avatars/thumbs/${avatarId}`;
}

function getPositionColor(position: string | null): string {
  switch (position) {
    case 'QB': return 'text-pink-700 bg-pink-100';
    case 'RB': return 'text-sky-700 bg-sky-100';
    case 'WR': return 'text-orange-700 bg-orange-100';
    case 'TE': return 'text-yellow-700 bg-yellow-100';
    case 'K': return 'text-purple-700 bg-purple-100';
    case 'DEF': return 'text-amber-800 bg-amber-100';
    default: return 'text-gray-700 bg-gray-100';
  }
}

export default function TaxiSquads() {
  const { data, isLoading, error } = useQuery<TaxiSquadsData>({
    queryKey: ['taxiSquads'],
    queryFn: api.getTaxiSquads,
  });

  if (isLoading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <h1 className="text-4xl font-bold mb-6">Taxi Squads</h1>
        <div className="bg-white rounded-lg shadow p-6">
          <p className="text-gray-600">Loading taxi squads...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="container mx-auto px-4 py-8">
        <h1 className="text-4xl font-bold mb-6">Taxi Squads</h1>
        <div className="bg-white rounded-lg shadow p-6">
          <p className="text-red-600">Error loading taxi squads: {(error as Error).message}</p>
        </div>
      </div>
    );
  }

  if (!data || data.teams.length === 0) {
    return (
      <div className="container mx-auto px-4 py-8">
        <h1 className="text-4xl font-bold mb-6">Taxi Squads</h1>
        <div className="bg-white rounded-lg shadow p-6">
          <p className="text-gray-600">No taxi squad data available.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="flex items-baseline gap-3 mb-6">
        <h1 className="text-4xl font-bold">Taxi Squads</h1>
        <span className="text-lg text-gray-500">{data.season} Season</span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {data.teams.map((team) => {
          const avatar = avatarUrl(team.avatar);
          return (
            <div key={team.owner_name} className="bg-white rounded-lg shadow overflow-hidden">
              {/* Team header */}
              <div className="bg-blue-600 dark:bg-blue-800 text-white px-4 py-3 flex items-center gap-3">
                {avatar ? (
                  <img src={avatar} alt={team.owner_name} className="w-8 h-8 rounded-full" />
                ) : (
                  <div className="w-8 h-8 rounded-full bg-blue-400 dark:bg-blue-600 flex items-center justify-center text-sm font-bold">
                    {team.owner_name.charAt(0).toUpperCase()}
                  </div>
                )}
                <div className="min-w-0">
                  <div className="font-semibold truncate">{team.owner_name}</div>
                  {team.team_name && (
                    <div className="text-xs text-blue-200 truncate">{team.team_name}</div>
                  )}
                </div>
              </div>

              {/* Player list */}
              <table className="w-full">
                <thead>
                  <tr className="border-b text-xs text-gray-500 uppercase">
                    <th className="px-4 py-2 text-left">Player</th>
                    <th className="px-4 py-2 text-center w-16">Pos</th>
                    <th className="px-4 py-2 text-center w-16">Team</th>
                  </tr>
                </thead>
                <tbody>
                  {team.players.map((player) => (
                    <tr key={player.player_id} className="border-b last:border-b-0 hover:bg-gray-50">
                      <td className="px-4 py-2 text-sm font-medium">{player.full_name}</td>
                      <td className="px-4 py-2 text-center">
                        {player.position ? (
                          <span className={`text-xs font-semibold px-2 py-0.5 rounded ${getPositionColor(player.position)}`}>
                            {player.position}
                          </span>
                        ) : (
                          <span className="text-xs text-gray-400">--</span>
                        )}
                      </td>
                      <td className="px-4 py-2 text-center text-sm text-gray-600">
                        {player.team || '--'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          );
        })}
      </div>
    </div>
  );
}
