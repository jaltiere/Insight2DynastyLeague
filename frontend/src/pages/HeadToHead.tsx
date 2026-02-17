import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../services/api';

type RecordCategory = 'regular_season' | 'playoff' | 'consolation';

interface H2HRecord {
  wins: number;
  losses: number;
  ties: number;
}

interface H2HOwner {
  user_id: string;
  display_name: string;
  username: string;
  avatar: string;
}

interface H2HMatrixResponse {
  owners: H2HOwner[];
  matrix: Record<string, Record<string, H2HRecord>>;
  median_records: Record<string, H2HRecord>;
}

const categories: { key: RecordCategory; label: string; matchType: string }[] = [
  { key: 'regular_season', label: 'Regular Season', matchType: 'regular' },
  { key: 'playoff', label: 'Playoff', matchType: 'playoff' },
  { key: 'consolation', label: 'Consolation', matchType: 'consolation' },
];

function RecordCell({ record }: { record: H2HRecord | undefined }) {
  if (!record || (record.wins === 0 && record.losses === 0 && record.ties === 0)) {
    return <span className="text-gray-400">0-0-0</span>;
  }

  const { wins, losses, ties } = record;
  let bg = '';
  if (wins > losses) bg = 'bg-green-50 text-green-800';
  else if (losses > wins) bg = 'bg-red-50 text-red-800';

  return (
    <span className={`inline-block px-2 py-1 rounded text-xs font-medium ${bg}`}>
      {wins}-{losses}-{ties}
    </span>
  );
}

export default function HeadToHead() {
  const [activeCategory, setActiveCategory] = useState<RecordCategory>('regular_season');

  const matchType = categories.find(c => c.key === activeCategory)!.matchType;

  const { data, isLoading, error } = useQuery<H2HMatrixResponse>({
    queryKey: ['h2h-matrix', matchType],
    queryFn: () => api.getH2HMatrix(matchType).then(res => res.data),
  });

  const sortedMedian = useMemo(() => {
    if (!data) return [];
    return data.owners
      .map(owner => {
        const rec = data.median_records[owner.user_id] || { wins: 0, losses: 0, ties: 0 };
        const total = rec.wins + rec.losses + rec.ties;
        const winPct = total > 0 ? rec.wins / total : 0;
        return { ...owner, ...rec, winPct };
      })
      .sort((a, b) => b.winPct - a.winPct);
  }, [data]);

  if (isLoading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <h1 className="text-4xl font-bold mb-6">Head-to-Head History</h1>
        <div className="bg-white rounded-lg shadow p-6">
          <p className="text-gray-600">Loading head-to-head records...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="container mx-auto px-4 py-8">
        <h1 className="text-4xl font-bold mb-6">Head-to-Head History</h1>
        <div className="bg-white rounded-lg shadow p-6">
          <p className="text-red-600">Error loading head-to-head records: {(error as Error).message}</p>
        </div>
      </div>
    );
  }

  const owners = data?.owners || [];
  const matrix = data?.matrix || {};

  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-4xl font-bold mb-6">Head-to-Head History</h1>

      {/* H2H Matrix Card */}
      <div className="bg-white rounded-lg shadow mb-6">
        <div className="bg-blue-600 text-white px-6 py-3 rounded-t-lg">
          <h2 className="text-xl font-semibold">Head-to-Head Records</h2>
        </div>

        {/* Category Tabs */}
        <div className="flex border-b border-gray-200">
          {categories.map(cat => (
            <button
              key={cat.key}
              onClick={() => setActiveCategory(cat.key)}
              className={`px-6 py-3 text-sm font-medium border-b-2 transition-colors ${
                activeCategory === cat.key
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              {cat.label}
            </button>
          ))}
        </div>

        {/* Matrix Grid */}
        <div className="overflow-x-auto p-4">
          {owners.length === 0 ? (
            <p className="text-gray-500 text-center py-4">No matchup data available.</p>
          ) : (
            <table className="w-full border-collapse">
              <thead>
                <tr>
                  <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase sticky left-0 bg-white z-10 border-b border-r border-gray-200 min-w-[120px]">
                    Owner
                  </th>
                  {owners.map(col => (
                    <th
                      key={col.user_id}
                      className="px-2 py-2 text-center text-xs font-medium text-gray-500 uppercase border-b border-gray-200 min-w-[80px]"
                    >
                      <span className="whitespace-nowrap">
                        {(col.display_name || col.username).split(' ')[0]}
                      </span>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {owners.map(row => (
                  <tr key={row.user_id} className="hover:bg-gray-50">
                    <td className="px-3 py-2 text-sm font-medium text-gray-900 sticky left-0 bg-white z-10 border-r border-gray-200">
                      {row.display_name || row.username}
                    </td>
                    {owners.map(col => (
                      <td
                        key={col.user_id}
                        className={`px-2 py-2 text-center border-gray-100 ${
                          row.user_id === col.user_id ? 'bg-gray-100' : ''
                        }`}
                      >
                        {row.user_id === col.user_id ? (
                          <span className="text-gray-300">—</span>
                        ) : (
                          <RecordCell record={matrix[row.user_id]?.[col.user_id]} />
                        )}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {/* Median Record Card - Regular Season only */}
      {activeCategory === 'regular_season' && (
        <div className="bg-white rounded-lg shadow">
          <div className="bg-green-600 text-white px-6 py-3 rounded-t-lg">
            <h2 className="text-xl font-semibold">Record vs. League Median</h2>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Owner</th>
                  <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">W</th>
                  <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">L</th>
                  <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">T</th>
                  <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Win%</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {sortedMedian.map(owner => (
                  <tr key={owner.user_id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-sm font-medium text-gray-900">
                      {owner.display_name || owner.username}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-900 text-center">{owner.wins}</td>
                    <td className="px-4 py-3 text-sm text-gray-900 text-center">{owner.losses}</td>
                    <td className="px-4 py-3 text-sm text-gray-900 text-center">{owner.ties}</td>
                    <td className="px-4 py-3 text-sm text-gray-900 text-center">
                      {(owner.winPct * 100).toFixed(1)}%
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
