import React, { useState } from 'react';
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

type ViewType = 'teams' | 'age-curve' | 'positional-scarcity';

const AGE_BUCKETS = [
  { label: 'Emerging', range: '≤23', min: 0, max: 23, bar: 'bg-emerald-500', pill: 'bg-emerald-100 text-emerald-800', border: 'border-emerald-400' },
  { label: 'Rising',   range: '24–25', min: 24, max: 25, bar: 'bg-blue-500',    pill: 'bg-blue-100 text-blue-800',       border: 'border-blue-400' },
  { label: 'Prime',    range: '26–27', min: 26, max: 27, bar: 'bg-violet-500',  pill: 'bg-violet-100 text-violet-800',   border: 'border-violet-400' },
  { label: 'Veteran',  range: '28–29', min: 28, max: 29, bar: 'bg-amber-500',   pill: 'bg-amber-100 text-amber-800',     border: 'border-amber-400' },
  { label: 'Declining',range: '30+',   min: 30, max: 99, bar: 'bg-red-500',     pill: 'bg-red-100 text-red-800',         border: 'border-red-400' },
] as const;

const BUCKET_WEIGHTS: Record<string, number> = {
  Emerging: 5, Rising: 4, Prime: 3, Veteran: 2, Declining: 1,
};

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

function getAgeBucketLabel(age: number | null): string | null {
  if (age === null) return null;
  for (const b of AGE_BUCKETS) {
    if (age >= b.min && age <= b.max) return b.label;
  }
  return null;
}

interface BucketData { count: number; score: number; }
interface TeamCurveRow {
  team: RosterTeam;
  buckets: Record<string, BucketData>;
  dynastyCount: number;
  youthScore: number;
}

function buildTeamCurve(team: RosterTeam): TeamCurveRow {
  const dp = team.players.filter(p => ['QB', 'RB', 'WR', 'TE'].includes(p.position ?? ''));
  const buckets: Record<string, BucketData> = Object.fromEntries(
    AGE_BUCKETS.map(b => [b.label, { count: 0, score: 0 }])
  );
  for (const p of dp) {
    const lbl = getAgeBucketLabel(p.age);
    if (lbl) {
      buckets[lbl].count++;
      buckets[lbl].score += p.power_score;
    }
  }
  const youthScore = AGE_BUCKETS.reduce(
    (s, b) => s + (buckets[b.label]?.count ?? 0) * (BUCKET_WEIGHTS[b.label] ?? 1), 0
  );
  return { team, buckets, dynastyCount: dp.length, youthScore };
}

// ─── Team Card ────────────────────────────────────────────────────────────────

function TeamCard({ team, leagueMaxScore }: { team: RosterTeam; leagueMaxScore: number }) {
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

      {/* Positional breakdown */}
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
                  <td className="px-2 py-1.5 text-center text-gray-500 text-xs">{player.team ?? '—'}</td>
                  <td className="px-2 py-1.5 text-center text-gray-500">{player.age ?? '—'}</td>
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

// ─── Age Curve View ───────────────────────────────────────────────────────────

function AgeCurveView({ teams }: { teams: RosterTeam[] }) {
  const [sortKey, setSortKey] = useState<string>('youthScore');
  const [expandedTeam, setExpandedTeam] = useState<number | null>(null);
  const { openPlayer } = usePlayerModal();

  const rows: TeamCurveRow[] = teams.map(buildTeamCurve);

  const sorted = [...rows].sort((a, b) => {
    if (sortKey === 'youthScore') return b.youthScore - a.youthScore;
    if (sortKey === 'avgAge') return a.team.avg_age - b.team.avg_age;
    const bucket = AGE_BUCKETS.find(bk => bk.label === sortKey);
    if (bucket) return (b.buckets[bucket.label]?.count ?? 0) - (a.buckets[bucket.label]?.count ?? 0);
    return 0;
  });

  // League totals per bucket (for the header legend)
  const leagueBuckets: Record<string, number> = Object.fromEntries(
    AGE_BUCKETS.map(b => [b.label, rows.reduce((s, r) => s + (r.buckets[b.label]?.count ?? 0), 0)])
  );
  const leagueTotal = Object.values(leagueBuckets).reduce((a, b) => a + b, 0);

  return (
    <div className="space-y-4">
      {/* Legend + league distribution */}
      <div className="bg-white rounded-lg shadow p-4">
        <h2 className="text-xs font-bold uppercase tracking-wider text-gray-500 mb-3">Age Bucket Guide</h2>
        <div className="flex flex-wrap gap-2 mb-4">
          {AGE_BUCKETS.map(b => (
            <span key={b.label} className={`text-xs font-semibold px-2 py-1 rounded-full border ${b.pill} ${b.border}`}>
              {b.label} ({b.range})
            </span>
          ))}
        </div>

        {/* League-wide age distribution bar */}
        <div className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">
          League-Wide Age Distribution ({leagueTotal} dynasty players)
        </div>
        <div className="flex h-5 rounded-full overflow-hidden gap-px">
          {AGE_BUCKETS.map(b => {
            const pct = leagueTotal > 0 ? (leagueBuckets[b.label] / leagueTotal) * 100 : 0;
            return pct > 0 ? (
              <div
                key={b.label}
                className={`${b.bar} flex items-center justify-center text-white text-xs font-bold`}
                style={{ width: `${pct}%` }}
                title={`${b.label}: ${leagueBuckets[b.label]} players (${pct.toFixed(0)}%)`}
              >
                {pct >= 8 ? leagueBuckets[b.label] : ''}
              </div>
            ) : null;
          })}
        </div>
        <div className="flex justify-between mt-1">
          {AGE_BUCKETS.map(b => (
            <span key={b.label} className="text-xs text-gray-400 text-center" style={{ width: `${leagueTotal > 0 ? (leagueBuckets[b.label] / leagueTotal) * 100 : 0}%` }}>
              {leagueTotal > 0 && (leagueBuckets[b.label] / leagueTotal) * 100 >= 6
                ? `${((leagueBuckets[b.label] / leagueTotal) * 100).toFixed(0)}%`
                : ''}
            </span>
          ))}
        </div>
      </div>

      {/* Sort controls */}
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Sort by:</span>
        {[
          { key: 'youthScore', label: 'Youth Score' },
          { key: 'avgAge', label: 'Youngest' },
          ...AGE_BUCKETS.map(b => ({ key: b.label, label: b.label })),
        ].map(opt => (
          <button
            key={opt.key}
            onClick={() => setSortKey(opt.key)}
            className={`px-3 py-1 rounded-full text-xs font-semibold transition border ${
              sortKey === opt.key
                ? 'bg-blue-600 text-white border-blue-600'
                : 'bg-white text-gray-600 border-gray-300 hover:border-gray-400'
            }`}
          >
            {opt.label}
          </button>
        ))}
      </div>

      {/* Team rows */}
      <div className="space-y-2">
        {sorted.map((row, idx) => {
          const isExpanded = expandedTeam === row.team.roster_id;
          const avatar = avatarUrl(row.team.avatar);
          const dynastyByBucket: Record<string, RosterPlayer[]> = Object.fromEntries(
            AGE_BUCKETS.map(b => [b.label, []])
          );
          row.team.players
            .filter(p => ['QB', 'RB', 'WR', 'TE'].includes(p.position ?? ''))
            .forEach(p => {
              const lbl = getAgeBucketLabel(p.age);
              if (lbl) dynastyByBucket[lbl].push(p);
            });

          return (
            <div key={row.team.roster_id} className="bg-white rounded-lg shadow overflow-hidden">
              <div className="px-4 py-3 flex items-center gap-3">
                {/* Rank */}
                <div className="text-sm font-bold text-gray-400 w-5 text-right flex-shrink-0">{idx + 1}</div>

                {/* Avatar */}
                {avatar ? (
                  <img src={avatar} alt={row.team.owner_name} className="w-8 h-8 rounded-full flex-shrink-0" />
                ) : (
                  <div className="w-8 h-8 rounded-full bg-blue-500 flex items-center justify-center text-white text-sm font-bold flex-shrink-0">
                    {row.team.owner_name.charAt(0).toUpperCase()}
                  </div>
                )}

                {/* Name + classification */}
                <div className="min-w-0 flex-1">
                  <div className="font-semibold text-sm truncate">{row.team.owner_name}</div>
                  <div className="text-xs text-gray-400">Avg age {row.team.avg_age} · {row.dynastyCount} dynasty players</div>
                </div>

                {/* Youth score */}
                <div className="text-right flex-shrink-0">
                  <div className="text-xs text-gray-400 uppercase tracking-wide">Youth</div>
                  <div className="text-base font-bold text-blue-600">{row.youthScore}</div>
                </div>
              </div>

              {/* Stacked age bar */}
              <div className="px-4 pb-1">
                {row.dynastyCount > 0 ? (
                  <div className="flex h-4 rounded-full overflow-hidden gap-px">
                    {AGE_BUCKETS.map(b => {
                      const pct = (row.buckets[b.label]?.count ?? 0) / row.dynastyCount * 100;
                      return pct > 0 ? (
                        <div
                          key={b.label}
                          className={`${b.bar} flex items-center justify-center text-white text-xs font-bold cursor-pointer`}
                          style={{ width: `${pct}%` }}
                          title={`${b.label}: ${row.buckets[b.label]?.count} players`}
                        >
                          {pct >= 10 ? row.buckets[b.label]?.count : ''}
                        </div>
                      ) : null;
                    })}
                  </div>
                ) : (
                  <div className="h-4 bg-gray-100 rounded-full" />
                )}
              </div>

              {/* Bucket count pills */}
              <div className="px-4 pb-3 pt-1.5 flex flex-wrap gap-1.5">
                {AGE_BUCKETS.map(b => {
                  const cnt = row.buckets[b.label]?.count ?? 0;
                  return (
                    <span
                      key={b.label}
                      className={`text-xs px-2 py-0.5 rounded-full font-semibold ${cnt > 0 ? b.pill : 'bg-gray-100 text-gray-400'}`}
                    >
                      {b.label} {cnt}
                    </span>
                  );
                })}
              </div>

              {/* Expand to see player breakdown by bucket */}
              <button
                onClick={() => setExpandedTeam(isExpanded ? null : row.team.roster_id)}
                className="w-full px-4 py-2 text-xs text-blue-600 hover:bg-blue-50 transition font-medium flex items-center justify-center gap-1 border-t"
              >
                {isExpanded ? 'Hide Players' : 'View Players by Age'}
                <svg className={`w-3 h-3 transition-transform ${isExpanded ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </button>

              {isExpanded && (
                <div className="border-t divide-y">
                  {AGE_BUCKETS.map(b => {
                    const players = dynastyByBucket[b.label];
                    if (players.length === 0) return null;
                    return (
                      <div key={b.label} className="px-4 py-2">
                        <div className={`text-xs font-bold uppercase tracking-wide mb-1.5 ${b.pill.split(' ')[1]}`}>
                          {b.label} ({b.range})
                        </div>
                        <div className="flex flex-wrap gap-1.5">
                          {players.sort((a, b) => b.power_score - a.power_score).map(p => (
                            <button
                              key={p.player_id}
                              onClick={() => openPlayer(p.player_id)}
                              className="flex items-center gap-1 text-xs bg-gray-50 hover:bg-gray-100 rounded px-2 py-1 transition"
                            >
                              <span className={`font-bold px-1 rounded ${getPositionColor(p.position)}`}>{p.position}</span>
                              <span className="font-medium">{p.player_name}</span>
                              <span className="text-gray-400">({p.age ?? '?'})</span>
                            </button>
                          ))}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ─── Positional Scarcity View ─────────────────────────────────────────────────

function PositionalScarcityView({ teams }: { teams: RosterTeam[] }) {
  const [sortPos, setSortPos] = useState<string | null>(null);
  const { openPlayer } = usePlayerModal();
  const [expandedTeam, setExpandedTeam] = useState<number | null>(null);

  // Compute league averages per position
  const posAvgs: Record<string, number> = {};
  const posMaxes: Record<string, number> = {};
  for (const pos of DYNASTY_POSITIONS) {
    const scores = teams.map(t => t.positional_scores[pos] ?? 0);
    posAvgs[pos] = scores.reduce((a, b) => a + b, 0) / scores.length;
    posMaxes[pos] = Math.max(...scores, 1);
  }

  // Scarcity = how many teams are below league average (higher = more scarce)
  const scarcity: Record<string, number> = {};
  for (const pos of DYNASTY_POSITIONS) {
    scarcity[pos] = teams.filter(t => (t.positional_scores[pos] ?? 0) < posAvgs[pos]).length;
  }

  const sorted = sortPos
    ? [...teams].sort((a, b) => (b.positional_scores[sortPos] ?? 0) - (a.positional_scores[sortPos] ?? 0))
    : [...teams].sort((a, b) => b.total_roster_score - a.total_roster_score);

  function cellColor(score: number, avg: number): string {
    const pct = avg > 0 ? (score - avg) / avg : 0;
    if (pct >= 0.2)  return 'bg-emerald-100 text-emerald-800 font-bold';
    if (pct >= 0.05) return 'bg-green-50 text-green-700';
    if (pct >= -0.05) return 'bg-gray-50 text-gray-600';
    if (pct >= -0.2) return 'bg-amber-50 text-amber-700';
    return 'bg-red-100 text-red-700 font-semibold';
  }

  function scarcityLabel(belowCount: number, total: number): { label: string; color: string } {
    const pct = belowCount / total;
    if (pct >= 0.7) return { label: 'Scarce', color: 'bg-red-100 text-red-700' };
    if (pct >= 0.5) return { label: 'Thin', color: 'bg-amber-100 text-amber-700' };
    return { label: 'Deep', color: 'bg-emerald-100 text-emerald-700' };
  }

  return (
    <div className="space-y-4">
      {/* League position health */}
      <div className="bg-white rounded-lg shadow p-4">
        <h2 className="text-xs font-bold uppercase tracking-wider text-gray-500 mb-3">League Position Depth</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {DYNASTY_POSITIONS.map(pos => {
            const { label, color } = scarcityLabel(scarcity[pos], teams.length);
            return (
              <div key={pos} className="text-center border rounded-lg p-3">
                <span className={`inline-block text-sm font-bold px-2 py-0.5 rounded mb-2 ${getPositionColor(pos)}`}>{pos}</span>
                <div className="text-xs text-gray-500">Avg score</div>
                <div className="text-lg font-bold">{posAvgs[pos].toFixed(0)}</div>
                <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${color}`}>{label}</span>
                <div className="text-xs text-gray-400 mt-1">{scarcity[pos]}/{teams.length} below avg</div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Color scale legend */}
      <div className="bg-white rounded-lg shadow px-4 py-3 flex flex-wrap items-center gap-3 text-xs">
        <span className="font-semibold text-gray-500 uppercase tracking-wide">Score vs league avg:</span>
        <span className="bg-emerald-100 text-emerald-800 font-bold px-2 py-0.5 rounded">Elite (+20%+)</span>
        <span className="bg-green-50 text-green-700 px-2 py-0.5 rounded border border-green-200">Above (+5–20%)</span>
        <span className="bg-gray-50 text-gray-600 px-2 py-0.5 rounded border border-gray-200">Average (±5%)</span>
        <span className="bg-amber-50 text-amber-700 px-2 py-0.5 rounded border border-amber-200">Below (–5–20%)</span>
        <span className="bg-red-100 text-red-700 font-semibold px-2 py-0.5 rounded">Weak (–20%+)</span>
      </div>

      {/* Sort by position */}
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Sort by:</span>
        <button
          onClick={() => setSortPos(null)}
          className={`px-3 py-1 rounded-full text-xs font-semibold transition border ${!sortPos ? 'bg-blue-600 text-white border-blue-600' : 'bg-white text-gray-600 border-gray-300 hover:border-gray-400'}`}
        >
          Overall
        </button>
        {DYNASTY_POSITIONS.map(pos => (
          <button
            key={pos}
            onClick={() => setSortPos(pos)}
            className={`px-3 py-1 rounded-full text-xs font-semibold transition border ${sortPos === pos ? 'bg-blue-600 text-white border-blue-600' : 'bg-white text-gray-600 border-gray-300 hover:border-gray-400'}`}
          >
            {pos}
          </button>
        ))}
      </div>

      {/* Scarcity table */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-50 border-b text-xs text-gray-500 uppercase tracking-wide">
                <th className="px-4 py-3 text-left">Team</th>
                {DYNASTY_POSITIONS.map(pos => (
                  <th key={pos} className="px-3 py-3 text-center w-24">
                    <span className={`font-bold px-1.5 py-0.5 rounded ${getPositionColor(pos)}`}>{pos}</span>
                  </th>
                ))}
                <th className="px-3 py-3 text-right w-20">Total</th>
              </tr>
            </thead>
            <tbody>
              {/* League average row */}
              <tr className="border-b bg-blue-50">
                <td className="px-4 py-2 font-semibold text-blue-700 text-xs uppercase tracking-wide">League Avg</td>
                {DYNASTY_POSITIONS.map(pos => (
                  <td key={pos} className="px-3 py-2 text-center text-blue-700 font-semibold">
                    {posAvgs[pos].toFixed(0)}
                  </td>
                ))}
                <td className="px-3 py-2 text-right text-blue-700 font-semibold">
                  {DYNASTY_POSITIONS.reduce((s, p) => s + posAvgs[p], 0).toFixed(0)}
                </td>
              </tr>

              {sorted.map((team) => {
                const isExpanded = expandedTeam === team.roster_id;
                const avatar = avatarUrl(team.avatar);
                return (
                  <React.Fragment key={team.roster_id}>
                    <tr
                      className="border-b hover:bg-gray-50 cursor-pointer"
                      className="border-b hover:bg-gray-50 cursor-pointer"
                      onClick={() => setExpandedTeam(isExpanded ? null : team.roster_id)}
                    >
                      <td className="px-4 py-2">
                        <div className="flex items-center gap-2">
                          {avatar ? (
                            <img src={avatar} alt={team.owner_name} className="w-6 h-6 rounded-full flex-shrink-0" />
                          ) : (
                            <div className="w-6 h-6 rounded-full bg-blue-500 flex items-center justify-center text-white text-xs font-bold flex-shrink-0">
                              {team.owner_name.charAt(0)}
                            </div>
                          )}
                          <div>
                            <div className="font-medium text-sm">{team.owner_name}</div>
                            <span className={`text-xs px-1.5 py-0.5 rounded-full font-semibold ${getClassificationStyle(team.classification)}`}>
                              {team.classification}
                            </span>
                          </div>
                        </div>
                      </td>
                      {DYNASTY_POSITIONS.map(pos => {
                        const score = team.positional_scores[pos] ?? 0;
                        const count = team.positional_counts[pos] ?? 0;
                        return (
                          <td key={pos} className={`px-3 py-2 text-center ${cellColor(score, posAvgs[pos])}`}>
                            <div className="font-semibold">{score > 0 ? score.toFixed(0) : '—'}</div>
                            <div className="text-xs opacity-70">{count} pl.</div>
                          </td>
                        );
                      })}
                      <td className="px-3 py-2 text-right font-bold text-gray-700">
                        {DYNASTY_POSITIONS.reduce((s, p) => s + (team.positional_scores[p] ?? 0), 0).toFixed(0)}
                      </td>
                    </tr>

                    {/* Expanded: show top players per position */}
                    {isExpanded && (
                      <tr className="bg-gray-50 border-b">
                        <td colSpan={DYNASTY_POSITIONS.length + 2} className="px-4 py-3">
                          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                            {DYNASTY_POSITIONS.map(pos => {
                              const posPlayers = team.players
                                .filter(p => p.position === pos)
                                .sort((a, b) => b.power_score - a.power_score)
                                .slice(0, 4);
                              const score = team.positional_scores[pos] ?? 0;
                              const avgScore = posAvgs[pos];
                              const diff = avgScore > 0 ? ((score - avgScore) / avgScore * 100) : 0;
                              return (
                                <div key={pos}>
                                  <div className="flex items-center gap-1.5 mb-1.5">
                                    <span className={`text-xs font-bold px-1.5 py-0.5 rounded ${getPositionColor(pos)}`}>{pos}</span>
                                    <span className={`text-xs font-semibold ${diff >= 5 ? 'text-green-600' : diff <= -5 ? 'text-red-600' : 'text-gray-500'}`}>
                                      {diff >= 0 ? '+' : ''}{diff.toFixed(0)}%
                                    </span>
                                  </div>
                                  {posPlayers.length === 0 ? (
                                    <div className="text-xs text-gray-400">No players</div>
                                  ) : (
                                    <div className="space-y-0.5">
                                      {posPlayers.map(p => (
                                        <button
                                          key={p.player_id}
                                          onClick={(e) => { e.stopPropagation(); openPlayer(p.player_id); }}
                                          className="flex items-center justify-between w-full text-xs hover:text-blue-600 text-left gap-1"
                                        >
                                          <span className="truncate font-medium">{p.player_name}</span>
                                          <span className="text-gray-400 flex-shrink-0">({p.age ?? '?'}) {p.power_score.toFixed(1)}</span>
                                        </button>
                                      ))}
                                    </div>
                                  )}
                                </div>
                              );
                            })}
                          </div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function RosterAnalysis() {
  const [filter, setFilter] = useState<Classification>('All');
  const [view, setView] = useState<ViewType>('teams');

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

      {/* View toggle */}
      <div className="flex gap-1 mb-6 bg-gray-100 rounded-lg p-1 w-fit">
        {([
          { key: 'teams', label: 'Teams' },
          { key: 'age-curve', label: 'Age Curve' },
          { key: 'positional-scarcity', label: 'Positional Scarcity' },
        ] as { key: ViewType; label: string }[]).map(v => (
          <button
            key={v.key}
            onClick={() => setView(v.key)}
            className={`px-4 py-1.5 rounded-md text-sm font-semibold transition ${
              view === v.key
                ? 'bg-white text-gray-900 shadow-sm'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            {v.label}
          </button>
        ))}
      </div>

      {/* Teams view */}
      {view === 'teams' && (
        <>
          {/* Classification legend */}
          <div className="bg-white rounded-lg shadow p-4 mb-6">
            <h2 className="text-xs font-bold uppercase tracking-wider text-gray-500 mb-3">Classification Guide</h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
              <div className="flex items-start gap-2">
                <span className="flex-shrink-0 w-2 h-2 rounded-full bg-green-500 mt-1.5" />
                <div>
                  <div className="font-semibold text-green-800">Win Now</div>
                  <div className="text-xs text-gray-500">Veteran roster, strong value — championship window is open</div>
                </div>
              </div>
              <div className="flex items-start gap-2">
                <span className="flex-shrink-0 w-2 h-2 rounded-full bg-blue-500 mt-1.5" />
                <div>
                  <div className="font-semibold text-blue-800">Future Contender</div>
                  <div className="text-xs text-gray-500">Young roster with strong value — best years ahead</div>
                </div>
              </div>
              <div className="flex items-start gap-2">
                <span className="flex-shrink-0 w-2 h-2 rounded-full bg-amber-500 mt-1.5" />
                <div>
                  <div className="font-semibold text-amber-800">Rebuilding</div>
                  <div className="text-xs text-gray-500">Young but unproven — investing in the future</div>
                </div>
              </div>
              <div className="flex items-start gap-2">
                <span className="flex-shrink-0 w-2 h-2 rounded-full bg-red-500 mt-1.5" />
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

          {/* Team cards */}
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
        </>
      )}

      {/* Age Curve view */}
      {view === 'age-curve' && <AgeCurveView teams={data.teams} />}

      {/* Positional Scarcity view */}
      {view === 'positional-scarcity' && <PositionalScarcityView teams={data.teams} />}
    </div>
  );
}
