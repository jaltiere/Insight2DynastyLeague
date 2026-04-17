import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../services/api';

type MainTab = 'scoring' | 'season' | 'margins' | 'streaks' | 'unluckiest';

interface GameRecord {
  rank: number;
  points: number;
  owner_name: string;
  team_name: string | null;
  season: number;
  week: number;
  match_type: string;
  won: boolean;
}

interface SeasonRecord {
  rank: number;
  points_for: number;
  owner_name: string;
  team_name: string | null;
  season: number;
  wins: number;
  losses: number;
  ties: number;
}

interface MarginRecord {
  rank: number;
  margin: number;
  winner_name: string;
  winner_points: number;
  loser_name: string;
  loser_points: number;
  season: number;
  week: number;
  match_type: string;
}

interface StreakRecord {
  rank: number;
  streak: number;
  owner_name: string;
  start_season: number;
  start_week: number;
  end_season: number;
  end_week: number;
}

interface TeamRecordsData {
  scoring: { highest_game: GameRecord[]; lowest_game: GameRecord[] };
  season: { highest_season: SeasonRecord[]; lowest_season: SeasonRecord[] };
  margins: { biggest_blowout: MarginRecord[]; closest_game: MarginRecord[] };
  streaks: {
    reg_win: StreakRecord[];
    reg_loss: StreakRecord[];
    playoff_win: StreakRecord[];
    playoff_loss: StreakRecord[];
  };
  unluckiest: { most_points_no_title: SeasonRecord[]; most_points_in_loss: GameRecord[] };
}

const mainTabs: { key: MainTab; label: string }[] = [
  { key: 'scoring', label: 'Scoring' },
  { key: 'season', label: 'Season Totals' },
  { key: 'margins', label: 'Margins' },
  { key: 'streaks', label: 'Streaks' },
  { key: 'unluckiest', label: 'Unluckiest' },
];

const matchTypeLabel: Record<string, string> = {
  regular: 'Regular',
  playoff: 'Playoff',
  consolation: 'Consolation',
};

const rankBadge = (rank: number) => {
  if (rank === 1) return 'text-yellow-500 font-bold';
  if (rank === 2) return 'text-gray-400 font-bold';
  if (rank === 3) return 'text-amber-600 font-bold';
  return 'text-gray-600 font-medium';
};

const thClass = 'px-4 py-3 text-xs font-medium text-gray-500 uppercase select-none';

function SectionHeader({ title, subtitle }: { title: string; subtitle?: string }) {
  return (
    <div className="bg-blue-600 dark:bg-blue-800 text-white px-6 py-3 rounded-t-lg">
      <h2 className="text-xl font-semibold">{title}</h2>
      {subtitle && <p className="text-sm text-blue-100 mt-0.5">{subtitle}</p>}
    </div>
  );
}

function SubTabs<T extends string>({
  tabs,
  active,
  onChange,
}: {
  tabs: { key: T; label: string }[];
  active: T;
  onChange: (v: T) => void;
}) {
  return (
    <div className="flex border-b border-gray-200">
      {tabs.map((t) => (
        <button
          key={t.key}
          onClick={() => onChange(t.key)}
          className={`px-6 py-3 text-sm font-medium border-b-2 transition-colors ${
            active === t.key
              ? 'border-blue-600 text-blue-600 dark:border-blue-400 dark:text-blue-400'
              : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
          }`}
        >
          {t.label}
        </button>
      ))}
    </div>
  );
}

// ---- Scoring tab ----
function ScoringSection({ data }: { data: TeamRecordsData['scoring'] }) {
  const [sub, setSub] = useState<'highest_game' | 'lowest_game'>('highest_game');
  const records = sub === 'highest_game' ? data.highest_game : data.lowest_game;
  const isHighest = sub === 'highest_game';

  return (
    <div className="bg-white rounded-lg shadow mb-6">
      <SectionHeader
        title={isHighest ? 'Highest Single-Week Team Scores' : 'Lowest Single-Week Team Scores'}
        subtitle={isHighest ? 'All match types' : 'Regular season only'}
      />
      <SubTabs
        tabs={[
          { key: 'highest_game' as const, label: 'Highest' },
          { key: 'lowest_game' as const, label: 'Lowest' },
        ]}
        active={sub}
        onChange={setSub}
      />
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-gray-50">
            <tr>
              <th className={`${thClass} text-center`}>#</th>
              <th className={`${thClass} text-left`}>Owner</th>
              <th className={`${thClass} text-left`}>Team</th>
              <th className={`${thClass} text-right`}>Points</th>
              <th className={`${thClass} text-center`}>Season</th>
              <th className={`${thClass} text-center`}>Week</th>
              <th className={`${thClass} text-center`}>Type</th>
              <th className={`${thClass} text-center`}>Result</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {records.map((r) => (
              <tr key={r.rank} className="hover:bg-gray-50">
                <td className={`px-4 py-3 text-sm text-center ${rankBadge(r.rank)}`}>{r.rank}</td>
                <td className="px-4 py-3 text-sm font-medium text-gray-900">{r.owner_name}</td>
                <td className="px-4 py-3 text-sm text-gray-600">{r.team_name || '—'}</td>
                <td className="px-4 py-3 text-sm text-right font-semibold text-gray-900">
                  {r.points.toFixed(2)}
                </td>
                <td className="px-4 py-3 text-sm text-center text-gray-700">{r.season}</td>
                <td className="px-4 py-3 text-sm text-center text-gray-700">{r.week}</td>
                <td className="px-4 py-3 text-sm text-center text-gray-500">
                  {matchTypeLabel[r.match_type] ?? r.match_type}
                </td>
                <td className="px-4 py-3 text-sm text-center">
                  <span className={r.won ? 'text-green-600 font-medium' : 'text-red-500 font-medium'}>
                    {r.won ? 'W' : 'L'}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ---- Season Totals tab ----
function SeasonSection({ data }: { data: TeamRecordsData['season'] }) {
  const [sub, setSub] = useState<'highest_season' | 'lowest_season'>('highest_season');
  const records = sub === 'highest_season' ? data.highest_season : data.lowest_season;

  return (
    <div className="bg-white rounded-lg shadow mb-6">
      <SectionHeader
        title={sub === 'highest_season' ? 'Most Points in a Season' : 'Fewest Points in a Season'}
        subtitle="Regular season totals"
      />
      <SubTabs
        tabs={[
          { key: 'highest_season' as const, label: 'Most PF' },
          { key: 'lowest_season' as const, label: 'Fewest PF' },
        ]}
        active={sub}
        onChange={setSub}
      />
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-gray-50">
            <tr>
              <th className={`${thClass} text-center`}>#</th>
              <th className={`${thClass} text-left`}>Owner</th>
              <th className={`${thClass} text-left`}>Team</th>
              <th className={`${thClass} text-right`}>Points For</th>
              <th className={`${thClass} text-center`}>Record</th>
              <th className={`${thClass} text-center`}>Season</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {records.map((r) => (
              <tr key={r.rank} className="hover:bg-gray-50">
                <td className={`px-4 py-3 text-sm text-center ${rankBadge(r.rank)}`}>{r.rank}</td>
                <td className="px-4 py-3 text-sm font-medium text-gray-900">{r.owner_name}</td>
                <td className="px-4 py-3 text-sm text-gray-600">{r.team_name || '—'}</td>
                <td className="px-4 py-3 text-sm text-right font-semibold text-gray-900">
                  {r.points_for.toFixed(2)}
                </td>
                <td className="px-4 py-3 text-sm text-center text-gray-700">
                  {r.wins}-{r.losses}{r.ties > 0 ? `-${r.ties}` : ''}
                </td>
                <td className="px-4 py-3 text-sm text-center text-gray-700">{r.season}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ---- Margins tab ----
function MarginsSection({ data }: { data: TeamRecordsData['margins'] }) {
  const [sub, setSub] = useState<'biggest_blowout' | 'closest_game'>('biggest_blowout');
  const records = sub === 'biggest_blowout' ? data.biggest_blowout : data.closest_game;

  return (
    <div className="bg-white rounded-lg shadow mb-6">
      <SectionHeader
        title={sub === 'biggest_blowout' ? 'Biggest Blowouts' : 'Closest Games'}
        subtitle="All match types"
      />
      <SubTabs
        tabs={[
          { key: 'biggest_blowout' as const, label: 'Biggest Blowout' },
          { key: 'closest_game' as const, label: 'Closest Game' },
        ]}
        active={sub}
        onChange={setSub}
      />
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-gray-50">
            <tr>
              <th className={`${thClass} text-center`}>#</th>
              <th className={`${thClass} text-left`}>Winner</th>
              <th className={`${thClass} text-right`}>Pts</th>
              <th className={`${thClass} text-left`}>Loser</th>
              <th className={`${thClass} text-right`}>Pts</th>
              <th className={`${thClass} text-right`}>Margin</th>
              <th className={`${thClass} text-center`}>Season</th>
              <th className={`${thClass} text-center`}>Week</th>
              <th className={`${thClass} text-center`}>Type</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {records.map((r) => (
              <tr key={r.rank} className="hover:bg-gray-50">
                <td className={`px-4 py-3 text-sm text-center ${rankBadge(r.rank)}`}>{r.rank}</td>
                <td className="px-4 py-3 text-sm font-medium text-green-700">{r.winner_name}</td>
                <td className="px-4 py-3 text-sm text-right font-semibold text-green-700">
                  {r.winner_points.toFixed(2)}
                </td>
                <td className="px-4 py-3 text-sm font-medium text-red-600">{r.loser_name}</td>
                <td className="px-4 py-3 text-sm text-right text-red-600">
                  {r.loser_points.toFixed(2)}
                </td>
                <td className="px-4 py-3 text-sm text-right font-bold text-gray-900">
                  {r.margin.toFixed(2)}
                </td>
                <td className="px-4 py-3 text-sm text-center text-gray-700">{r.season}</td>
                <td className="px-4 py-3 text-sm text-center text-gray-700">{r.week}</td>
                <td className="px-4 py-3 text-sm text-center text-gray-500">
                  {matchTypeLabel[r.match_type] ?? r.match_type}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ---- Streaks tab ----
type StreakSub = 'reg_win' | 'reg_loss' | 'playoff_win' | 'playoff_loss';

function StreaksSection({ data }: { data: TeamRecordsData['streaks'] }) {
  const [sub, setSub] = useState<StreakSub>('reg_win');

  const streakLabels: Record<StreakSub, { title: string; color: string }> = {
    reg_win: { title: 'Regular Season Win Streaks', color: 'text-green-700' },
    reg_loss: { title: 'Regular Season Loss Streaks', color: 'text-red-600' },
    playoff_win: { title: 'Playoff Win Streaks', color: 'text-green-700' },
    playoff_loss: { title: 'Playoff Loss Streaks', color: 'text-red-600' },
  };

  const records = data[sub];
  const { title } = streakLabels[sub];
  const isWin = sub.endsWith('win');

  const streakSubTabs: { key: StreakSub; label: string }[] = [
    { key: 'reg_win', label: 'Reg Season Wins' },
    { key: 'reg_loss', label: 'Reg Season Losses' },
    { key: 'playoff_win', label: 'Playoff Wins' },
    { key: 'playoff_loss', label: 'Playoff Losses' },
  ];

  const formatSpan = (r: StreakRecord) => {
    if (r.start_season === r.end_season) {
      return `${r.start_season} Wk ${r.start_week}–${r.end_week}`;
    }
    return `${r.start_season} Wk ${r.start_week} – ${r.end_season} Wk ${r.end_week}`;
  };

  return (
    <div className="bg-white rounded-lg shadow mb-6">
      <SectionHeader title={title} subtitle="All-time, streaks can span seasons" />
      <SubTabs tabs={streakSubTabs} active={sub} onChange={setSub} />
      {records.length === 0 ? (
        <div className="p-6 text-gray-500 text-sm">No streak data available.</div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className={`${thClass} text-center`}>#</th>
                <th className={`${thClass} text-left`}>Owner</th>
                <th className={`${thClass} text-center`}>Streak</th>
                <th className={`${thClass} text-left`}>Span</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {records.map((r) => (
                <tr key={r.rank} className="hover:bg-gray-50">
                  <td className={`px-4 py-3 text-sm text-center ${rankBadge(r.rank)}`}>{r.rank}</td>
                  <td className="px-4 py-3 text-sm font-medium text-gray-900">{r.owner_name}</td>
                  <td className="px-4 py-3 text-sm text-center">
                    <span
                      className={`text-lg font-bold ${isWin ? 'text-green-600' : 'text-red-600'}`}
                    >
                      {r.streak}
                    </span>
                    <span className="text-xs text-gray-500 ml-1">{isWin ? 'W' : 'L'}</span>
                  </td>
                  <td className="px-4 py-3 text-sm text-gray-600">{formatSpan(r)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// ---- Unluckiest tab ----
function UnluckiestSection({ data }: { data: TeamRecordsData['unluckiest'] }) {
  const [sub, setSub] = useState<'most_points_no_title' | 'most_points_in_loss'>(
    'most_points_no_title'
  );

  return (
    <div className="bg-white rounded-lg shadow mb-6">
      <SectionHeader
        title={
          sub === 'most_points_no_title'
            ? 'Most Points Without a Title'
            : 'Highest-Scoring Losses'
        }
        subtitle={
          sub === 'most_points_no_title'
            ? 'Best regular season scoring without winning the championship'
            : 'Most points scored in a regular season loss'
        }
      />
      <SubTabs
        tabs={[
          { key: 'most_points_no_title' as const, label: 'Most PF, No Title' },
          { key: 'most_points_in_loss' as const, label: 'Highest-Scoring Loss' },
        ]}
        active={sub}
        onChange={setSub}
      />
      <div className="overflow-x-auto">
        {sub === 'most_points_no_title' ? (
          <table className="w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className={`${thClass} text-center`}>#</th>
                <th className={`${thClass} text-left`}>Owner</th>
                <th className={`${thClass} text-left`}>Team</th>
                <th className={`${thClass} text-right`}>Points For</th>
                <th className={`${thClass} text-center`}>Record</th>
                <th className={`${thClass} text-center`}>Season</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {data.most_points_no_title.map((r) => (
                <tr key={r.rank} className="hover:bg-gray-50">
                  <td className={`px-4 py-3 text-sm text-center ${rankBadge(r.rank)}`}>{r.rank}</td>
                  <td className="px-4 py-3 text-sm font-medium text-gray-900">{r.owner_name}</td>
                  <td className="px-4 py-3 text-sm text-gray-600">{r.team_name || '—'}</td>
                  <td className="px-4 py-3 text-sm text-right font-semibold text-gray-900">
                    {r.points_for.toFixed(2)}
                  </td>
                  <td className="px-4 py-3 text-sm text-center text-gray-700">
                    {r.wins}-{r.losses}{r.ties > 0 ? `-${r.ties}` : ''}
                  </td>
                  <td className="px-4 py-3 text-sm text-center text-gray-700">{r.season}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <table className="w-full">
            <thead className="bg-gray-50">
              <tr>
                <th className={`${thClass} text-center`}>#</th>
                <th className={`${thClass} text-left`}>Owner</th>
                <th className={`${thClass} text-left`}>Team</th>
                <th className={`${thClass} text-right`}>Points</th>
                <th className={`${thClass} text-center`}>Season</th>
                <th className={`${thClass} text-center`}>Week</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {data.most_points_in_loss.map((r) => (
                <tr key={r.rank} className="hover:bg-gray-50">
                  <td className={`px-4 py-3 text-sm text-center ${rankBadge(r.rank)}`}>{r.rank}</td>
                  <td className="px-4 py-3 text-sm font-medium text-gray-900">{r.owner_name}</td>
                  <td className="px-4 py-3 text-sm text-gray-600">{r.team_name || '—'}</td>
                  <td className="px-4 py-3 text-sm text-right font-semibold text-gray-900">
                    {r.points.toFixed(2)}
                  </td>
                  <td className="px-4 py-3 text-sm text-center text-gray-700">{r.season}</td>
                  <td className="px-4 py-3 text-sm text-center text-gray-700">{r.week}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}

// ---- Main page ----
export default function TeamRecords() {
  const [activeTab, setActiveTab] = useState<MainTab>('scoring');

  const { data, isLoading, error } = useQuery<TeamRecordsData>({
    queryKey: ['team-records'],
    queryFn: () => api.getTeamRecords(),
  });

  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-4xl font-bold mb-2">Team Records</h1>
      <p className="text-gray-500 mb-6 text-sm">All-time franchise records across every season</p>

      {/* Main tab bar */}
      <div className="flex gap-2 flex-wrap mb-6">
        {mainTabs.map((t) => (
          <button
            key={t.key}
            onClick={() => setActiveTab(t.key)}
            className={`px-5 py-2.5 rounded-lg font-semibold text-sm transition ${
              activeTab === t.key
                ? 'bg-blue-600 dark:bg-blue-800 text-white'
                : 'bg-white text-gray-700 hover:bg-gray-100 shadow-sm'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {isLoading && (
        <div className="bg-white rounded-lg shadow p-8 text-center text-gray-500">
          Loading records…
        </div>
      )}
      {error && (
        <div className="bg-white rounded-lg shadow p-8 text-center text-red-600">
          Error loading records: {(error as Error).message}
        </div>
      )}

      {data && (
        <>
          {activeTab === 'scoring' && <ScoringSection data={data.scoring} />}
          {activeTab === 'season' && <SeasonSection data={data.season} />}
          {activeTab === 'margins' && <MarginsSection data={data.margins} />}
          {activeTab === 'streaks' && <StreaksSection data={data.streaks} />}
          {activeTab === 'unluckiest' && <UnluckiestSection data={data.unluckiest} />}
        </>
      )}
    </div>
  );
}
