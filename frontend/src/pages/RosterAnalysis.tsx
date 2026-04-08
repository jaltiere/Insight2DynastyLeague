import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../services/api';
import { usePlayerModal } from '../context/PlayerModalContext';

// ─── Types ───────────────────────────────────────────────────────────────────

interface RosterPlayer {
  player_id: string;
  player_name: string;
  position: string | null;
  team: string | null;
  age: number | null;
  power_score: number;
}

interface RosterTeam {
  roster_id: number;
  owner_name: string;
  team_name: string | null;
  avatar: string | null;
  avg_age: number;
  total_roster_score: number;
  player_count: number;
  positional_scores: Record<string, number>;
  positional_counts: Record<string, number>;
  classification: string;
  players: RosterPlayer[];
}

interface RosterAnalysisData {
  season: number | null;
  teams: RosterTeam[];
}

// ─── Constants ────────────────────────────────────────────────────────────────

const CLASSIFICATIONS = ['All', 'Win Now', 'Future Contender', 'Rebuilding', 'Retooling'] as const;
type Classification = typeof CLASSIFICATIONS[number];

const DYNASTY_POSITIONS = ['QB', 'RB', 'WR', 'TE'] as const;

// ─── Helpers ─────────────────────────────────────────────────────────────────

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
    case 'K':  return 'text-purple-700 bg-purple-100';
    case 'DEF': return 'text-amber-800 bg-amber-100';
    default:   return 'text-gray-700 bg-gray-100';
  }
}

function getClassificationStyle(classification: string): string {
  switch (classification) {
    case 'Win Now':          return 'bg-green-100 text-green-800';
    case 'Future Contender': return 'bg-blue-100 text-blue-800';
    case 'Rebuilding':       return 'bg-amber-100 text-amber-800';
    case 'Retooling':        return 'bg-red-100 text-red-800';
    default:                 return 'bg-gray-100 text-gray-700';
  }
}

function getClassificationFilterStyle(classification: Classification, active: boolean): string {
  if (!active) return 'bg-white text-gray-600 border border-gray-300 hover:border-gray-400';
  switch (classification) {
    case 'All':              return 'bg-blue-600 text-white border border-blue-600';
    case 'Win Now':          return 'bg-green-600 text-white border border-green-600';
    case 'Future Contender': return 'bg-blue-500 text-white border border-blue-500';
    case 'Rebuilding':       return 'bg-amber-500 text-white border border-amber-500';
    case 'Retooling':        return 'bg-red-500 text-white border border-red-500';
    default:                 return 'bg-gray-600 text-white border border-gray-600';
  }
}

// ─── Team Card ────────────────────────────────────────────────────────────────

function TeamCard({
  team,
  leagueMaxScore,
}: {
  team: RosterTeam;
  leagueMaxScore: number;
}) {
  const [expanded, setExpanded] = useState(false);
  const { openPlayer } = usePlayerModal();
  const avatar = avatarUrl(team.avatar);

  return (
    <div className="bg-white rounded-lg shadow overflow-hidden flex flex-col">
      {/* Header */}
      <div className="bg-blue-600 dark:bg-blue-800 text-white px-4 py-3 flex items-center gap-3">
        {avatar ? (
          <img src={avatar} alt={team.owner_name} className="w-10 h-10 rounded-full flex-shrink-0" />
        ) : (
          <div className="w-10 h-10 rounded-full bg-blue-400 dark:bg-blue-600 flex items-center justify-center text-base font-bold flex-shrink-0">
            {team.owner_name.charAt(0).toUpperCase()}
          </div>
        )}
        <div className="min-w-0 flex-1">
          <div className="font-semibold truncate">{team.owner_name}</div>
          {team.team_name && (
            <div className="text-xs text-blue-200 truncate">{team.team_name}</div>
          )}
        </div>
        <span className={`text-xs font-semibold px-2 py-1 rounded-full flex-shrink-0 ${getClassificationStyle(team.classification)}`}>
          {team.classification}
        </span>
      </div>

      {/* Stats Strip */}
      <div className="grid grid-cols-3 divide-x text-center py-3 border-b">
        <div>
          <div className="text-xs text-gray-500 uppercase tracking-wide">Avg Age</div>
          <div className="text-lg font-bold">{team.avg_age}</div>
        </div>
        <div>
          <div className="text-xs text-gray-500 uppercase tracking-wide">Players</div>
          <div className="text-lg font-bold">{team.player_count}</div>
        </div>
        <div>
          <div className="text-xs text-gray-500 uppercase tracking-wide">Score</div>
          <div className="text-lg font-bold">{team.total_roster_score}</div>
        </div>
      </div>

      {/* Score bar */}
      <div className="px-4 pt-3 pb-1">
        <div className="flex items-center gap-2">
          <div className="flex-1 bg-gray-100 rounded-full h-2 overflow-hidden">
            <div
              className="bg-blue-500 h-2 rounded-full transition-all"
              style={{ width: `${Math.min(100, (team.total_roster_score / leagueMaxScore) * 100)}%` }}
            />
          </div>
          <span className="text-xs text-gray-400 w-8 text-right">
            {leagueMaxScore > 0 ? Math.round((team.total_roster_score / leagueMaxScore) * 100) : 0}%
          </span>
        </div>
      </div>

      {/* Positional breakdown (dynasty positions) */}
      <div className="px-4 py-3 border-b">
        <div className="grid grid-cols-4 gap-2">
          {DYNASTY_POSITIONS.map((pos) => {
            const count = team.positional_counts[pos] ?? 0;
            const score = team.positional_scores[pos] ?? 0;
            return (
              <div key={pos} className="text-center">
                <span className={`inline-block text-xs font-bold px-1.5 py-0.5 rounded ${getPositionColor(pos)}`}>
                  {pos}
                </span>
                <div className="text-sm font-semibold mt-1">{count}</div>
                <div className="text-xs text-gray-400">{score > 0 ? score.toFixed(0) : '—'}</div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Expand/collapse roster */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full px-4 py-2 text-sm text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900 dark:text-blue-300 transition font-medium flex items-center justify-center gap-1"
      >
        {expanded ? 'Hide Roster' : 'View Roster'}
        <svg
          className={`w-4 h-4 transition-transform ${expanded ? 'rotate-180' : ''}`}
          fill="none" stroke="currentColor" viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {expanded && (
        <div className="border-t">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-xs text-gray-500 uppercase border-b bg-gray-50">
                <th className="px-4 py-2 text-left">Player</th>
                <th className="px-2 py-2 text-center w-12">Pos</th>
                <th className="px-2 py-2 text-center w-12">Team</th>
                <th className="px-2 py-2 text-center w-10">Age</th>
                <th className="px-3 py-2 text-right w-14">Score</th>
              </tr>
            </thead>
            <tbody>
              {team.players.map((player) => (
                <tr
                  key={player.player_id}
                  className="border-b last:border-b-0 hover:bg-gray-50 dark:hover:bg-gray-700"
                >
                  <td className="px-4 py-1.5 font-medium truncate max-w-0 w-full">
                    <button
                      onClick={() => openPlayer(player.player_id)}
                      className="hover:text-blue-600 hover:underline text-left"
                    >
                      {player.player_name}
                    </button>
                  </td>
                  <td className="px-2 py-1.5 text-center">
                    {player.position ? (
                      <span className={`text-xs font-semibold px-1.5 py-0.5 rounded ${getPositionColor(player.position)}`}>
                        {player.position}
                      </span>
                    ) : (
                      <span className="text-xs text-gray-400">—</span>
                    )}
                  </td>
                  <td className="px-2 py-1.5 text-center text-gray-500 text-xs">
                    {player.team ?? '—'}
                  </td>
                  <td className="px-2 py-1.5 text-center text-gray-500">
                    {player.age ?? '—'}
                  </td>
                  <td className="px-3 py-1.5 text-right font-semibold text-blue-600">
                    {player.power_score.toFixed(1)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function RosterAnalysis() {
  const [filter, setFilter] = useState<Classification>('All');

  const { data, isLoading, error } = useQuery<RosterAnalysisData>({
    queryKey: ['rosterAnalysis'],
    queryFn: api.getRosterAnalysis,
  });

  if (isLoading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <h1 className="text-4xl font-bold mb-6">Roster Analysis</h1>
        <div className="bg-white rounded-lg shadow p-6">
          <p className="text-gray-600">Loading roster data...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="container mx-auto px-4 py-8">
        <h1 className="text-4xl font-bold mb-6">Roster Analysis</h1>
        <div className="bg-white rounded-lg shadow p-6">
          <p className="text-red-600">Error loading roster data: {(error as Error).message}</p>
        </div>
      </div>
    );
  }

  if (!data || data.teams.length === 0) {
    return (
      <div className="container mx-auto px-4 py-8">
        <h1 className="text-4xl font-bold mb-6">Roster Analysis</h1>
        <div className="bg-white rounded-lg shadow p-6">
          <p className="text-gray-600">No roster data available.</p>
        </div>
      </div>
    );
  }

  const filteredTeams = filter === 'All'
    ? data.teams
    : data.teams.filter((t) => t.classification === filter);

  const leagueMaxScore = Math.max(...data.teams.map((t) => t.total_roster_score), 1);

  // Classification counts for filter buttons
  const counts: Record<string, number> = { All: data.teams.length };
  for (const team of data.teams) {
    counts[team.classification] = (counts[team.classification] ?? 0) + 1;
  }

  return (
    <div className="container mx-auto px-4 py-8">
      {/* Page header */}
      <div className="flex items-baseline gap-3 mb-6">
        <h1 className="text-4xl font-bold">Roster Analysis</h1>
        <span className="text-lg text-gray-500">{data.season} Season</span>
      </div>

      {/* Classification legend */}
      <div className="bg-white rounded-lg shadow p-4 mb-6">
        <h2 className="text-xs font-bold uppercase tracking-wider text-gray-500 mb-3">Classification Guide</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
          <div className="flex items-start gap-2">
            <span className="flex-shrink-0 mt-0.5 w-2 h-2 rounded-full bg-green-500 mt-1.5" />
            <div>
              <div className="font-semibold text-green-800">Win Now</div>
              <div className="text-xs text-gray-500">Veteran roster, strong value — championship window is open</div>
            </div>
          </div>
          <div className="flex items-start gap-2">
            <span className="flex-shrink-0 mt-0.5 w-2 h-2 rounded-full bg-blue-500 mt-1.5" />
            <div>
              <div className="font-semibold text-blue-800">Future Contender</div>
              <div className="text-xs text-gray-500">Young roster with strong value — best years ahead</div>
            </div>
          </div>
          <div className="flex items-start gap-2">
            <span className="flex-shrink-0 mt-0.5 w-2 h-2 rounded-full bg-amber-500 mt-1.5" />
            <div>
              <div className="font-semibold text-amber-800">Rebuilding</div>
              <div className="text-xs text-gray-500">Young but unproven — investing in the future</div>
            </div>
          </div>
          <div className="flex items-start gap-2">
            <span className="flex-shrink-0 mt-0.5 w-2 h-2 rounded-full bg-red-500 mt-1.5" />
            <div>
              <div className="font-semibold text-red-800">Retooling</div>
              <div className="text-xs text-gray-500">Aging roster, lower value — needs a new direction</div>
            </div>
          </div>
        </div>
      </div>

      {/* Filter bar */}
      <div className="flex flex-wrap gap-2 mb-6">
        {CLASSIFICATIONS.map((cls) => (
          <button
            key={cls}
            onClick={() => setFilter(cls)}
            className={`px-4 py-1.5 rounded-full text-sm font-semibold transition ${getClassificationFilterStyle(cls, filter === cls)}`}
          >
            {cls}
            {counts[cls] !== undefined && (
              <span className="ml-1.5 opacity-75">({counts[cls]})</span>
            )}
          </button>
        ))}
      </div>

      {/* Team cards grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {filteredTeams.map((team) => (
          <TeamCard key={team.roster_id} team={team} leagueMaxScore={leagueMaxScore} />
        ))}
      </div>

      {filteredTeams.length === 0 && (
        <div className="bg-white rounded-lg shadow p-6 text-center text-gray-500">
          No teams match the selected filter.
        </div>
      )}
    </div>
  );
}
