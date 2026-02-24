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

const STATUS_COLORS: Record<string, string> = {
  complete: 'text-green-500',
  failed: 'text-red-500',
};

function PositionBadge({ position }: { position: string | null }) {
  if (!position) return null;
  const bg = POSITION_COLORS[position] || 'bg-gray-400';
  return (
    <span className={`${bg} text-white text-xs font-bold px-2 py-1 rounded mr-2`}>
      {position}
    </span>
  );
}

function DivisionTable({
  teams,
  divisionName,
  headerColor,
}: {
  teams: any[];
  divisionName: string;
  headerColor: string;
}) {
  return (
    <div className="bg-white rounded-lg shadow">
      <div className={`${headerColor} text-white px-6 py-3 rounded-t-lg`}>
        <h2 className="text-xl font-semibold">{divisionName}</h2>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Team</th>
              <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">W</th>
              <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">L</th>
              <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">T</th>
              <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">vs Median</th>
              <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">PF</th>
              <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">PA</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {teams.map((team: any) => (
              <tr key={team.roster_id} className="hover:bg-gray-50">
                <td className="px-4 py-3 text-sm font-medium text-gray-900">
                  {team.team_name
                    ? <>{team.team_name} <span className="text-gray-500 font-normal">({team.username})</span></>
                    : team.username}
                </td>
                <td className="px-4 py-3 text-sm text-gray-900 text-center">{team.wins}</td>
                <td className="px-4 py-3 text-sm text-gray-900 text-center">{team.losses}</td>
                <td className="px-4 py-3 text-sm text-gray-900 text-center">{team.ties}</td>
                <td className="px-4 py-3 text-sm text-gray-600 text-center">
                  {team.median_wins}-{team.median_losses}-{team.median_ties}
                </td>
                <td className="px-4 py-3 text-sm text-gray-900 text-right">{team.points_for.toFixed(2)}</td>
                <td className="px-4 py-3 text-sm text-gray-900 text-right">{team.points_against.toFixed(2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function formatDate(ms: number | null): string {
  if (!ms) return '';
  return new Date(ms).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

function TransactionCard({ txn }: { txn: any }) {
  const typeLabel = txn.type === 'free_agent'
    ? 'Free Agent'
    : txn.type?.charAt(0).toUpperCase() + txn.type?.slice(1);

  const isTrade = txn.type === 'trade';

  return (
    <div className="bg-white rounded-lg shadow p-3">
      <div className="flex items-center justify-between mb-1">
        <h3 className="text-sm font-bold text-gray-900">{typeLabel}</h3>
        <span className={`text-xs font-medium ${STATUS_COLORS[txn.status] || 'text-gray-500'}`}>
          {txn.status}
        </span>
      </div>
      <div className="text-xs text-gray-500 mb-1">
        <span>Week {txn.week}</span>
        {txn.waiver_bid != null && <span className="ml-2">Bid: ${txn.waiver_bid}</span>}
        {txn.status_updated && <span className="ml-2">{formatDate(txn.status_updated)}</span>}
      </div>

      {isTrade ? (
        <div className="space-y-1.5 mt-1">
          {txn.owners?.map((owner: any) => {
            const rid = owner.roster_id;
            const teamName = owner.team_name || owner.username;
            const received = txn.adds?.filter((a: any) => a.roster_id === rid) || [];
            const gave = txn.drops?.filter((d: any) => d.roster_id === rid) || [];
            const picksGot = txn.draft_picks?.filter(
              (p: any) => p.owner_id === rid && p.previous_owner_id !== rid
            ) || [];
            const picksLost = txn.draft_picks?.filter(
              (p: any) => p.previous_owner_id === rid && p.owner_id !== rid
            ) || [];

            if (!received.length && !gave.length && !picksGot.length && !picksLost.length) return null;

            return (
              <div key={rid} className="bg-gray-50 rounded p-1.5">
                <div className="text-xs font-bold text-gray-800 mb-0.5 truncate">{teamName}</div>
                {(received.length > 0 || picksGot.length > 0) && (
                  <div className="mb-0.5">
                    <span className="text-xs font-semibold text-green-600">Received:</span>
                    {received.map((add: any) => (
                      <div key={add.player_id} className="flex items-center mt-0.5 ml-1">
                        <PositionBadge position={add.position} />
                        <span className="text-xs text-gray-800">{add.player_name}</span>
                      </div>
                    ))}
                    {picksGot.map((pick: any, idx: number) => (
                      <div key={`pg-${idx}`} className="text-xs text-gray-800 mt-0.5 ml-1">
                        {pick.season} Rd {pick.round} pick
                      </div>
                    ))}
                  </div>
                )}
                {(gave.length > 0 || picksLost.length > 0) && (
                  <div>
                    <span className="text-xs font-semibold text-red-600">Gave up:</span>
                    {gave.map((drop: any) => (
                      <div key={drop.player_id} className="flex items-center mt-0.5 ml-1">
                        <PositionBadge position={drop.position} />
                        <span className="text-xs text-gray-800">{drop.player_name}</span>
                      </div>
                    ))}
                    {picksLost.map((pick: any, idx: number) => (
                      <div key={`pl-${idx}`} className="text-xs text-gray-800 mt-0.5 ml-1">
                        {pick.season} Rd {pick.round} pick
                      </div>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      ) : (
        <>
          {txn.owners?.length > 0 && (
            <div className="text-xs font-medium text-gray-700 mb-1 truncate">
              {txn.owners.map((o: any) => o.team_name || o.username).join(', ')}
            </div>
          )}
          {txn.adds?.length > 0 && (
            <div className="mb-1">
              <span className="text-xs font-semibold text-green-600">Add:</span>
              {txn.adds.map((add: any) => (
                <div key={add.player_id} className="flex items-center mt-0.5 ml-1">
                  <PositionBadge position={add.position} />
                  <span className="text-xs text-gray-800">{add.player_name}</span>
                </div>
              ))}
            </div>
          )}
          {txn.drops?.length > 0 && (
            <div className="mb-1">
              <span className="text-xs font-semibold text-red-600">Drop:</span>
              {txn.drops.map((drop: any) => (
                <div key={drop.player_id} className="flex items-center mt-0.5 ml-1">
                  <PositionBadge position={drop.position} />
                  <span className="text-xs text-gray-800">{drop.player_name}</span>
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {txn.status === 'failed' && txn.metadata_notes && (
        <p className="text-xs text-red-500 italic mt-1">{txn.metadata_notes}</p>
      )}
    </div>
  );
}

const DIVISION_COLORS = [
  'bg-blue-600',
  'bg-green-600',
  'bg-purple-600',
  'bg-orange-600',
];

export default function Home() {
  const [selectedSeason, setSelectedSeason] = useState<number | null>(null);

  const { data: seasonsData } = useQuery({
    queryKey: ['seasons'],
    queryFn: api.getSeasons,
  });

  const { data: standings, isLoading, error } = useQuery({
    queryKey: ['standings', selectedSeason],
    queryFn: () =>
      selectedSeason
        ? api.getHistoricalStandings(selectedSeason).then(res => res.data)
        : api.getStandings(),
  });

  const { data: transactionsData } = useQuery({
    queryKey: ['recentTransactions'],
    queryFn: () => api.getRecentTransactions(10),
  });

  if (isLoading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <h1 className="text-4xl font-bold mb-6">Standings</h1>
        <div className="bg-white rounded-lg shadow p-6">
          <p className="text-gray-600">Loading standings...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="container mx-auto px-4 py-8">
        <h1 className="text-4xl font-bold mb-6">Standings</h1>
        <div className="bg-white rounded-lg shadow p-6">
          <p className="text-red-600">Error loading standings: {(error as Error).message}</p>
        </div>
      </div>
    );
  }

  const numDivisions = standings?.num_divisions || 2;
  const divisions = [];
  for (let i = 1; i <= numDivisions; i++) {
    divisions.push({
      num: i,
      name: standings?.division_names?.[String(i)] || `Division ${i}`,
      teams: standings?.standings.filter((team: any) => team.division === i) || [],
    });
  }

  const transactions = transactionsData?.transactions || [];

  return (
    <div className="container mx-auto px-4 py-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-4xl font-bold">Standings - {standings?.season}</h1>
        {seasonsData?.seasons?.length > 0 && (
          <select
            className="border border-gray-300 rounded-lg px-4 py-2 text-sm bg-white shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            value={selectedSeason ?? ''}
            onChange={(e) => setSelectedSeason(e.target.value ? Number(e.target.value) : null)}
          >
            <option value="">Current Season</option>
            {seasonsData.seasons.map((year: number) => (
              <option key={year} value={year}>{year}</option>
            ))}
          </select>
        )}
      </div>

      <div className="grid gap-6 mb-8 md:grid-cols-2">
        {divisions.map((div) => (
          <DivisionTable
            key={div.num}
            teams={div.teams}
            divisionName={div.name}
            headerColor={DIVISION_COLORS[(div.num - 1) % DIVISION_COLORS.length]}
          />
        ))}
      </div>

      {transactions.length > 0 && (
        <div className="mt-8">
          <h2 className="text-2xl font-bold mb-4">Recent Transactions</h2>
          <div className="grid md:grid-cols-3 lg:grid-cols-5 gap-3">
            {transactions.map((txn: any) => (
              <TransactionCard key={txn.id} txn={txn} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
