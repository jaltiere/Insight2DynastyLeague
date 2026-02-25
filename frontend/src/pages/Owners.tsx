import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../services/api';

type RecordCategory = 'regular_season' | 'playoff' | 'consolation';
type SortField = 'name' | 'seasons' | 'wins' | 'losses' | 'ties' | 'win_pct' | 'pf' | 'pa';
type SortDirection = 'asc' | 'desc';

interface CategoryRecord {
  wins: number;
  losses: number;
  ties: number;
  points_for: number;
  points_against: number;
  win_percentage: number;
}

interface Trophies {
  champion: number;
  division_winner: number;
  most_points: number;
  consolation: number;
}

interface Owner {
  user_id: string;
  username: string;
  display_name: string;
  avatar: string;
  seasons_played: number;
  trophies: Trophies;
  regular_season: CategoryRecord;
  playoff: CategoryRecord;
  consolation: CategoryRecord;
}

interface SeasonRecord {
  year: number;
  team_name: string | null;
  division: number;
  division_name: string;
  regular_season: CategoryRecord;
  playoff: CategoryRecord;
  consolation: CategoryRecord;
  median_wins: number;
  median_losses: number;
  median_ties: number;
}

const categories: { key: RecordCategory; label: string }[] = [
  { key: 'regular_season', label: 'Regular Season' },
  { key: 'playoff', label: 'Playoff' },
  { key: 'consolation', label: 'Consolation' },
];

const TROPHY_ICONS = {
  champion: { icon: '\uD83C\uDFC6', label: 'League Champion' },
  division_winner: { icon: '\uD83C\uDFC5', label: 'Division Winner' },
  most_points: { icon: '\uD83C\uDF96\uFE0F', label: 'Most Points (Regular Season)' },
  consolation: { icon: '\uD83E\uDD49', label: 'Consolation Winner' },
};

const EMPTY_TROPHIES: Trophies = { champion: 0, division_winner: 0, most_points: 0, consolation: 0 };

function TrophyDisplay({ trophies }: { trophies: Trophies }) {
  const t = trophies || EMPTY_TROPHIES;
  const items = (Object.keys(TROPHY_ICONS) as (keyof Trophies)[]).filter(
    key => t[key] > 0
  );
  if (items.length === 0) return <span className="text-gray-400">-</span>;
  return (
    <span className="inline-flex items-center gap-2">
      {items.map(key => (
        <span key={key} title={TROPHY_ICONS[key].label}>
          {TROPHY_ICONS[key].icon} x{t[key]}
        </span>
      ))}
    </span>
  );
}

function SortArrow({ field, sortField, sortDir }: { field: SortField; sortField: SortField; sortDir: SortDirection }) {
  if (field !== sortField) return null;
  return <span className="text-blue-600 ml-1">{sortDir === 'asc' ? '\u25B2' : '\u25BC'}</span>;
}

export default function Owners() {
  const [selectedOwnerId, setSelectedOwnerId] = useState<string | null>(null);
  const [activeCategory, setActiveCategory] = useState<RecordCategory>('regular_season');
  const [sortField, setSortField] = useState<SortField>('wins');
  const [sortDir, setSortDir] = useState<SortDirection>('desc');

  const { data: ownersData, isLoading, error } = useQuery({
    queryKey: ['owners'],
    queryFn: () => api.getAllOwners().then(res => res.data),
  });

  const { data: ownerDetails, isLoading: detailsLoading } = useQuery({
    queryKey: ['ownerDetails', selectedOwnerId],
    queryFn: () => api.getOwnerDetails(selectedOwnerId!).then(res => res.data),
    enabled: !!selectedOwnerId,
  });

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDir(prev => (prev === 'desc' ? 'asc' : 'desc'));
    } else {
      setSortField(field);
      setSortDir('desc');
    }
  };

  const sortedOwners = useMemo(() => {
    const owners: Owner[] = ownersData?.owners || [];
    if (!owners.length) return owners;

    return [...owners].sort((a, b) => {
      const catA = a[activeCategory];
      const catB = b[activeCategory];

      let valA: number | string;
      let valB: number | string;

      switch (sortField) {
        case 'name':
          valA = a.display_name || a.username;
          valB = b.display_name || b.username;
          break;
        case 'seasons':
          valA = a.seasons_played;
          valB = b.seasons_played;
          break;
        case 'wins':
          valA = catA.wins;
          valB = catB.wins;
          break;
        case 'losses':
          valA = catA.losses;
          valB = catB.losses;
          break;
        case 'ties':
          valA = catA.ties;
          valB = catB.ties;
          break;
        case 'win_pct':
          valA = catA.win_percentage;
          valB = catB.win_percentage;
          break;
        case 'pf':
          valA = catA.points_for;
          valB = catB.points_for;
          break;
        case 'pa':
          valA = catA.points_against;
          valB = catB.points_against;
          break;
        default:
          valA = catA.wins;
          valB = catB.wins;
      }

      const cmp =
        typeof valA === 'string'
          ? valA.localeCompare(valB as string)
          : (valA as number) - (valB as number);

      return sortDir === 'asc' ? cmp : -cmp;
    });
  }, [ownersData, activeCategory, sortField, sortDir]);

  if (isLoading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <h1 className="text-4xl font-bold mb-6">Owner Records</h1>
        <div className="bg-white rounded-lg shadow p-6">
          <p className="text-gray-600">Loading owner records...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="container mx-auto px-4 py-8">
        <h1 className="text-4xl font-bold mb-6">Owner Records</h1>
        <div className="bg-white rounded-lg shadow p-6">
          <p className="text-red-600">Error loading owner records: {(error as Error).message}</p>
        </div>
      </div>
    );
  }

  const thClass = 'px-4 py-3 text-xs font-medium text-gray-500 uppercase cursor-pointer select-none hover:bg-gray-100';

  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-4xl font-bold mb-6">Owner Records</h1>

      {/* Career Stats Table */}
      <div className="bg-white rounded-lg shadow mb-6">
        <div className="bg-blue-600 text-white px-6 py-3 rounded-t-lg">
          <h2 className="text-xl font-semibold">Career Statistics</h2>
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

        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className={`${thClass} text-left`} onClick={() => handleSort('name')}>
                  Owner<SortArrow field="name" sortField={sortField} sortDir={sortDir} />
                </th>
                <th className={`${thClass} text-center`} onClick={() => handleSort('seasons')}>
                  Seasons<SortArrow field="seasons" sortField={sortField} sortDir={sortDir} />
                </th>
                <th className={`${thClass} text-center`} onClick={() => handleSort('wins')}>
                  W<SortArrow field="wins" sortField={sortField} sortDir={sortDir} />
                </th>
                <th className={`${thClass} text-center`} onClick={() => handleSort('losses')}>
                  L<SortArrow field="losses" sortField={sortField} sortDir={sortDir} />
                </th>
                <th className={`${thClass} text-center`} onClick={() => handleSort('ties')}>
                  T<SortArrow field="ties" sortField={sortField} sortDir={sortDir} />
                </th>
                <th className={`${thClass} text-center`} onClick={() => handleSort('win_pct')}>
                  Win%<SortArrow field="win_pct" sortField={sortField} sortDir={sortDir} />
                </th>
                <th className={`${thClass} text-right`} onClick={() => handleSort('pf')}>
                  PF<SortArrow field="pf" sortField={sortField} sortDir={sortDir} />
                </th>
                <th className={`${thClass} text-right`} onClick={() => handleSort('pa')}>
                  PA<SortArrow field="pa" sortField={sortField} sortDir={sortDir} />
                </th>
                <th className={`${thClass} text-center`}>
                  Trophies
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {sortedOwners.map((owner: Owner) => {
                const rec = owner[activeCategory];
                return (
                  <tr
                    key={owner.user_id}
                    className={`cursor-pointer transition-colors ${
                      selectedOwnerId === owner.user_id ? 'bg-blue-50' : 'hover:bg-gray-50'
                    }`}
                    onClick={() =>
                      setSelectedOwnerId(
                        selectedOwnerId === owner.user_id ? null : owner.user_id
                      )
                    }
                  >
                    <td className="px-4 py-3 text-sm font-medium text-gray-900">
                      {owner.display_name || owner.username}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-900 text-center">{owner.seasons_played}</td>
                    <td className="px-4 py-3 text-sm text-gray-900 text-center">{rec.wins}</td>
                    <td className="px-4 py-3 text-sm text-gray-900 text-center">{rec.losses}</td>
                    <td className="px-4 py-3 text-sm text-gray-900 text-center">{rec.ties}</td>
                    <td className="px-4 py-3 text-sm text-gray-900 text-center">
                      {(rec.win_percentage * 100).toFixed(1)}%
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-900 text-right">{rec.points_for.toFixed(2)}</td>
                    <td className="px-4 py-3 text-sm text-gray-900 text-right">{rec.points_against.toFixed(2)}</td>
                    <td className="px-4 py-3 text-sm text-gray-900 text-center whitespace-nowrap">
                      <TrophyDisplay trophies={owner.trophies} />
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Trophy Key */}
        <div className="px-6 py-3 bg-gray-50 border-t border-gray-200 rounded-b-lg">
          <div className="flex items-center gap-6 text-xs text-gray-600">
            <span className="font-medium uppercase text-gray-500">Key:</span>
            {Object.entries(TROPHY_ICONS).map(([key, { icon, label }]) => (
              <span key={key} className="inline-flex items-center gap-1">
                {icon} {label}
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* Season Breakdown (shown when owner selected) */}
      {selectedOwnerId && (
        <div className="bg-white rounded-lg shadow">
          <div className="bg-green-600 text-white px-6 py-3 rounded-t-lg">
            <h2 className="text-xl font-semibold">
              {ownerDetails
                ? `${ownerDetails.display_name || ownerDetails.username} - Season Breakdown`
                : 'Loading...'}
            </h2>
          </div>
          {detailsLoading ? (
            <div className="p-6">
              <p className="text-gray-600">Loading season details...</p>
            </div>
          ) : ownerDetails ? (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Year</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Team Name</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">Division</th>
                    <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">W</th>
                    <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">L</th>
                    <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">T</th>
                    <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">Win%</th>
                    {activeCategory === 'regular_season' && (
                      <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase">vs Median</th>
                    )}
                    <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">PF</th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase">PA</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {ownerDetails.seasons.map((season: SeasonRecord) => {
                    const rec = season[activeCategory];
                    return (
                      <tr key={season.year} className="hover:bg-gray-50">
                        <td className="px-4 py-3 text-sm font-medium text-gray-900">{season.year}</td>
                        <td className="px-4 py-3 text-sm text-gray-900">{season.team_name || '-'}</td>
                        <td className="px-4 py-3 text-sm text-gray-900">{season.division_name}</td>
                        <td className="px-4 py-3 text-sm text-gray-900 text-center">{rec.wins}</td>
                        <td className="px-4 py-3 text-sm text-gray-900 text-center">{rec.losses}</td>
                        <td className="px-4 py-3 text-sm text-gray-900 text-center">{rec.ties}</td>
                        <td className="px-4 py-3 text-sm text-gray-900 text-center">
                          {(rec.win_percentage * 100).toFixed(1)}%
                        </td>
                        {activeCategory === 'regular_season' && (
                          <td className="px-4 py-3 text-sm text-gray-900 text-center">
                            {season.median_wins}-{season.median_losses}-{season.median_ties}
                          </td>
                        )}
                        <td className="px-4 py-3 text-sm text-gray-900 text-right">{rec.points_for.toFixed(2)}</td>
                        <td className="px-4 py-3 text-sm text-gray-900 text-right">{rec.points_against.toFixed(2)}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          ) : null}
        </div>
      )}
    </div>
  );
}
