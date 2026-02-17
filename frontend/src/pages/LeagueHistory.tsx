import { useQuery } from '@tanstack/react-query';
import { api } from '../services/api';

interface AwardOwner {
  user_id: string;
  username: string;
  team_name: string | null;
}

interface DivisionWinner extends AwardOwner {
  division: string;
}

interface SeasonHistory {
  year: number;
  num_divisions: number;
  division_names: Record<string, string>;
  champion: AwardOwner | null;
  division_winners: DivisionWinner[];
  consolation_winner: AwardOwner | null;
}

interface LeagueHistoryData {
  total_seasons: number;
  seasons: SeasonHistory[];
}

function OwnerName({ owner }: { owner: AwardOwner }) {
  if (owner.team_name) {
    return (
      <>
        {owner.team_name} <span className="text-gray-500 font-normal">({owner.username})</span>
      </>
    );
  }
  return <>{owner.username}</>;
}

export default function LeagueHistory() {
  const { data, isLoading, error } = useQuery<LeagueHistoryData>({
    queryKey: ['leagueHistory'],
    queryFn: api.getAllHistory,
  });

  if (isLoading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <h1 className="text-4xl font-bold mb-6">League History</h1>
        <div className="bg-white rounded-lg shadow p-6">
          <p className="text-gray-600">Loading league history...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="container mx-auto px-4 py-8">
        <h1 className="text-4xl font-bold mb-6">League History</h1>
        <div className="bg-white rounded-lg shadow p-6">
          <p className="text-red-600">Error loading league history: {(error as Error).message}</p>
        </div>
      </div>
    );
  }

  if (!data || data.total_seasons === 0) {
    return (
      <div className="container mx-auto px-4 py-8">
        <h1 className="text-4xl font-bold mb-6">League History</h1>
        <div className="bg-white rounded-lg shadow p-6">
          <p className="text-gray-600">No league history available yet.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-4xl font-bold mb-6">League History</h1>

      <div className="space-y-6">
        {data.seasons.map((season) => (
          <div key={season.year} className="bg-white rounded-lg shadow">
            <div className="bg-amber-600 text-white px-6 py-3 rounded-t-lg">
              <h2 className="text-xl font-semibold">{season.year} Season</h2>
            </div>

            <div className="p-6">
              <div className="grid md:grid-cols-3 gap-6">
                {/* Champion */}
                <div>
                  <h3 className="text-sm font-medium text-gray-500 uppercase mb-2">Champion</h3>
                  {season.champion ? (
                    <p className="text-lg font-semibold text-amber-700">
                      <OwnerName owner={season.champion} />
                    </p>
                  ) : (
                    <p className="text-sm text-gray-400">--</p>
                  )}
                </div>

                {/* Division Winners */}
                <div>
                  <h3 className="text-sm font-medium text-gray-500 uppercase mb-2">Division Winners</h3>
                  {season.division_winners.length > 0 ? (
                    <ul className="space-y-1">
                      {season.division_winners.map((dw) => (
                        <li key={dw.user_id} className="text-sm text-gray-900">
                          <span className="font-medium"><OwnerName owner={dw} /></span>
                          <span className="text-gray-500 ml-1">- {dw.division}</span>
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="text-sm text-gray-400">--</p>
                  )}
                </div>

                {/* Consolation Winner */}
                <div>
                  <h3 className="text-sm font-medium text-gray-500 uppercase mb-2">Consolation Winner</h3>
                  {season.consolation_winner ? (
                    <p className="text-sm font-medium text-gray-900">
                      <OwnerName owner={season.consolation_winner} />
                    </p>
                  ) : (
                    <p className="text-sm text-gray-400">--</p>
                  )}
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
