import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../services/api';

type View = 'game' | 'season' | 'career';
type MatchType = 'regular' | 'playoff' | 'consolation';
type RosterType = 'all' | 'starter' | 'bench';

const views: { key: View; label: string }[] = [
  { key: 'game', label: 'By Game' },
  { key: 'season', label: 'By Season' },
  { key: 'career', label: 'By Career' },
];

const matchTypes: { key: MatchType; label: string }[] = [
  { key: 'regular', label: 'Regular Season' },
  { key: 'playoff', label: 'Playoff' },
  { key: 'consolation', label: 'Consolation' },
];

const rosterTypes: { key: RosterType; label: string }[] = [
  { key: 'all', label: 'All' },
  { key: 'starter', label: 'Starter' },
  { key: 'bench', label: 'Bench' },
];

const positions = ['All', 'QB', 'RB', 'WR', 'TE', 'K', 'DEF'];

interface GameRecord {
  rank: number;
  player_name: string;
  position: string;
  team: string;
  points: number;
  season: number;
  week: number;
  match_type: string;
  is_starter: boolean;
  owner_name: string;
  team_name: string | null;
}

interface SeasonRecord {
  rank: number;
  player_name: string;
  position: string;
  team: string;
  total_points: number;
  games_played: number;
  avg_points: number;
  season: number;
  owner_name: string;
  team_name: string | null;
}

interface CareerRecord {
  rank: number;
  player_name: string;
  position: string;
  team: string;
  total_points: number;
  games_played: number;
  avg_points: number;
  seasons_played: number;
  owner_name: string;
  team_name: string | null;
}

export default function Players() {
  const [view, setView] = useState<View>('game');
  const [matchType, setMatchType] = useState<MatchType>('regular');
  const [rosterType, setRosterType] = useState<RosterType>('all');
  const [position, setPosition] = useState<string>('All');

  const { data, isLoading, error } = useQuery({
    queryKey: ['playerRecords', view, matchType, rosterType, position],
    queryFn: () =>
      api.getPlayerRecords({
        view,
        match_type: matchType,
        roster_type: rosterType,
        position: position === 'All' ? undefined : position,
        limit: 10,
      }),
  });

  const records = data?.records || [];

  const thClass =
    'px-4 py-3 text-xs font-medium text-gray-500 uppercase select-none';

  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-4xl font-bold mb-6">Player Records</h1>

      <div className="bg-white rounded-lg shadow mb-6">
        <div className="bg-blue-600 dark:bg-blue-800 text-white px-6 py-3 rounded-t-lg">
          <h2 className="text-xl font-semibold">Top 10 Scoring Performances</h2>
        </div>

        {/* View Tabs */}
        <div className="flex border-b border-gray-200">
          {views.map((v) => (
            <button
              key={v.key}
              onClick={() => setView(v.key)}
              className={`px-6 py-3 text-sm font-medium border-b-2 transition-colors ${
                view === v.key
                  ? 'border-blue-600 text-blue-600 dark:border-blue-400 dark:text-blue-400'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              {v.label}
            </button>
          ))}
        </div>

        {/* Filters Row */}
        <div className="flex flex-wrap items-center gap-4 px-6 py-3 border-b border-gray-200 bg-gray-50">
          {/* Match Type */}
          <div className="flex items-center gap-2">
            <span className="text-xs font-medium text-gray-500 uppercase">Type:</span>
            <div className="flex rounded-md overflow-hidden border border-gray-300">
              {matchTypes.map((mt) => (
                <button
                  key={mt.key}
                  onClick={() => setMatchType(mt.key)}
                  className={`px-3 py-1.5 text-xs font-medium transition-colors ${
                    matchType === mt.key
                      ? 'bg-blue-600 dark:bg-blue-800 text-white'
                      : 'bg-white text-gray-700 hover:bg-gray-100'
                  }`}
                >
                  {mt.label}
                </button>
              ))}
            </div>
          </div>

          {/* Roster Type */}
          <div className="flex items-center gap-2">
            <span className="text-xs font-medium text-gray-500 uppercase">Roster:</span>
            <div className="flex rounded-md overflow-hidden border border-gray-300">
              {rosterTypes.map((rt) => (
                <button
                  key={rt.key}
                  onClick={() => setRosterType(rt.key)}
                  className={`px-3 py-1.5 text-xs font-medium transition-colors ${
                    rosterType === rt.key
                      ? 'bg-blue-600 dark:bg-blue-800 text-white'
                      : 'bg-white text-gray-700 hover:bg-gray-100'
                  }`}
                >
                  {rt.label}
                </button>
              ))}
            </div>
          </div>

          {/* Position Filter */}
          <div className="flex items-center gap-2">
            <span className="text-xs font-medium text-gray-500 uppercase">Position:</span>
            <select
              value={position}
              onChange={(e) => setPosition(e.target.value)}
              className="border border-gray-300 rounded-md px-3 py-1.5 text-xs font-medium text-gray-700 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              {positions.map((p) => (
                <option key={p} value={p}>
                  {p === 'All' ? 'All Positions' : p}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Table */}
        {isLoading ? (
          <div className="p-6">
            <p className="text-gray-600">Loading player records...</p>
          </div>
        ) : error ? (
          <div className="p-6">
            <p className="text-red-600">Error loading records: {(error as Error).message}</p>
          </div>
        ) : records.length === 0 ? (
          <div className="p-6">
            <p className="text-gray-600">No records found for the selected filters.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            {view === 'game' && <GameTable records={records} thClass={thClass} />}
            {view === 'season' && <SeasonTable records={records} thClass={thClass} />}
            {view === 'career' && <CareerTable records={records} thClass={thClass} />}
          </div>
        )}
      </div>
    </div>
  );
}

function GameTable({ records, thClass }: { records: GameRecord[]; thClass: string }) {
  return (
    <table className="w-full">
      <thead className="bg-gray-50">
        <tr>
          <th className={`${thClass} text-center`}>#</th>
          <th className={`${thClass} text-left`}>Player</th>
          <th className={`${thClass} text-center`}>Pos</th>
          <th className={`${thClass} text-center`}>Team</th>
          <th className={`${thClass} text-right`}>Points</th>
          <th className={`${thClass} text-center`}>Season</th>
          <th className={`${thClass} text-center`}>Week</th>
          <th className={`${thClass} text-left`}>Owner</th>
          <th className={`${thClass} text-left`}>Team Name</th>
        </tr>
      </thead>
      <tbody className="divide-y divide-gray-200">
        {records.map((rec: GameRecord) => (
          <tr key={`${rec.rank}-${rec.season}-${rec.week}`} className="hover:bg-gray-50">
            <td className="px-4 py-3 text-sm text-gray-900 text-center font-medium">{rec.rank}</td>
            <td className="px-4 py-3 text-sm text-gray-900 font-medium">{rec.player_name}</td>
            <td className="px-4 py-3 text-sm text-gray-900 text-center">{rec.position}</td>
            <td className="px-4 py-3 text-sm text-gray-900 text-center">{rec.team}</td>
            <td className="px-4 py-3 text-sm text-gray-900 text-right font-semibold">
              {rec.points.toFixed(2)}
            </td>
            <td className="px-4 py-3 text-sm text-gray-900 text-center">{rec.season}</td>
            <td className="px-4 py-3 text-sm text-gray-900 text-center">{rec.week}</td>
            <td className="px-4 py-3 text-sm text-gray-900">{rec.owner_name}</td>
            <td className="px-4 py-3 text-sm text-gray-900">{rec.team_name || '-'}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function SeasonTable({ records, thClass }: { records: SeasonRecord[]; thClass: string }) {
  return (
    <table className="w-full">
      <thead className="bg-gray-50">
        <tr>
          <th className={`${thClass} text-center`}>#</th>
          <th className={`${thClass} text-left`}>Player</th>
          <th className={`${thClass} text-center`}>Pos</th>
          <th className={`${thClass} text-center`}>Team</th>
          <th className={`${thClass} text-right`}>Total Pts</th>
          <th className={`${thClass} text-center`}>Games</th>
          <th className={`${thClass} text-right`}>Avg Pts</th>
          <th className={`${thClass} text-center`}>Season</th>
          <th className={`${thClass} text-left`}>Owner</th>
          <th className={`${thClass} text-left`}>Team Name</th>
        </tr>
      </thead>
      <tbody className="divide-y divide-gray-200">
        {records.map((rec: SeasonRecord) => (
          <tr key={`${rec.rank}-${rec.season}`} className="hover:bg-gray-50">
            <td className="px-4 py-3 text-sm text-gray-900 text-center font-medium">{rec.rank}</td>
            <td className="px-4 py-3 text-sm text-gray-900 font-medium">{rec.player_name}</td>
            <td className="px-4 py-3 text-sm text-gray-900 text-center">{rec.position}</td>
            <td className="px-4 py-3 text-sm text-gray-900 text-center">{rec.team}</td>
            <td className="px-4 py-3 text-sm text-gray-900 text-right font-semibold">
              {rec.total_points.toFixed(2)}
            </td>
            <td className="px-4 py-3 text-sm text-gray-900 text-center">{rec.games_played}</td>
            <td className="px-4 py-3 text-sm text-gray-900 text-right">{rec.avg_points.toFixed(2)}</td>
            <td className="px-4 py-3 text-sm text-gray-900 text-center">{rec.season}</td>
            <td className="px-4 py-3 text-sm text-gray-900">{rec.owner_name}</td>
            <td className="px-4 py-3 text-sm text-gray-900">{rec.team_name || '-'}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function CareerTable({ records, thClass }: { records: CareerRecord[]; thClass: string }) {
  return (
    <table className="w-full">
      <thead className="bg-gray-50">
        <tr>
          <th className={`${thClass} text-center`}>#</th>
          <th className={`${thClass} text-left`}>Player</th>
          <th className={`${thClass} text-center`}>Pos</th>
          <th className={`${thClass} text-center`}>Team</th>
          <th className={`${thClass} text-right`}>Total Pts</th>
          <th className={`${thClass} text-center`}>Games</th>
          <th className={`${thClass} text-right`}>Avg Pts</th>
          <th className={`${thClass} text-center`}>Seasons</th>
          <th className={`${thClass} text-left`}>Owner</th>
        </tr>
      </thead>
      <tbody className="divide-y divide-gray-200">
        {records.map((rec: CareerRecord) => (
          <tr key={`${rec.rank}-${rec.player_name}`} className="hover:bg-gray-50">
            <td className="px-4 py-3 text-sm text-gray-900 text-center font-medium">{rec.rank}</td>
            <td className="px-4 py-3 text-sm text-gray-900 font-medium">{rec.player_name}</td>
            <td className="px-4 py-3 text-sm text-gray-900 text-center">{rec.position}</td>
            <td className="px-4 py-3 text-sm text-gray-900 text-center">{rec.team}</td>
            <td className="px-4 py-3 text-sm text-gray-900 text-right font-semibold">
              {rec.total_points.toFixed(2)}
            </td>
            <td className="px-4 py-3 text-sm text-gray-900 text-center">{rec.games_played}</td>
            <td className="px-4 py-3 text-sm text-gray-900 text-right">{rec.avg_points.toFixed(2)}</td>
            <td className="px-4 py-3 text-sm text-gray-900 text-center">{rec.seasons_played}</td>
            <td className="px-4 py-3 text-sm text-gray-900">{rec.owner_name}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
