import { useState, useRef } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../services/api';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

interface ScoreEntry {
  display_name: string;
  team_name: string;
  points: number;
  beat_median?: boolean;
}

interface LeagueMedian {
  median: number;
  teams: ScoreEntry[];
}

interface PlayerEntry {
  player_name: string;
  points: number;
  team: string;
  owner: string;
  team_name: string;
}

interface SeasonLeader {
  rank: number;
  player_name: string;
  total_points: number;
  owner: string;
}

interface RookieEntry {
  rank: number;
  player_name: string;
  total_points: number;
  overall_rank: number;
  position_label: string;
  owner: string;
}

interface StandingsEntry {
  rank: number;
  display_name: string;
  team_name: string;
  wins: number;
  losses: number;
  ties: number;
  points_for: number;
  division: number;
}

interface PlayoffEntry {
  seed: number;
  display_name: string;
  team_name: string;
  wins: number;
  losses: number;
  ties: number;
}

interface PotentialEntry {
  rank: number;
  display_name: string;
  team_name: string;
  max_potential_points: number;
}

interface RecapEntry {
  matchup_id: number;
  week: number;
  recap_type: string;
  recap_text: string | null;
  predictions_text: string | null;
  recap_metadata: Record<string, string> | null;
  home_points: number | null;
  away_points: number | null;
}

interface NewsletterData {
  week: number;
  season: number;
  is_regular_season: boolean;
  high_score: ScoreEntry;
  low_score: ScoreEntry;
  league_median: LeagueMedian;
  top_players: Record<string, PlayerEntry | null>;
  season_leaders: Record<string, SeasonLeader[]>;
  rookie_report: Record<string, RookieEntry[]>;
  standings: StandingsEntry[];
  playoff_picture: { playoff: PlayoffEntry[]; consolation: PlayoffEntry[] };
  potential_points: PotentialEntry[];
  recaps: RecapEntry[];
  upcoming_matchups: RecapEntry[];
}

// ---------------------------------------------------------------------------
// Email HTML generator
// ---------------------------------------------------------------------------

function generateEmailHTML(
  data: NewsletterData,
  intro: string,
  interestingFact: string,
): string {
  const SKILL_POSITIONS = ['QB', 'RB', 'WR', 'TE'];
  const ALL_POSITIONS = ['QB', 'RB', 'WR', 'TE', 'DEF', 'K'];
  const GREEN = '#c6f6d5';
  const ORANGE = '#fde68a';
  const HEADER_BG = '#2563eb';

  const h2 = (text: string) =>
    `<h2 style="font-size:18px;font-weight:bold;color:#1e3a8a;border-bottom:2px solid #2563eb;padding-bottom:4px;margin-top:24px;margin-bottom:8px;">${text}</h2>`;

  const section = (title: string, body: string) =>
    `${h2(title)}<div style="margin-bottom:16px;">${body}</div>`;

  const record = (e: PlayoffEntry) =>
    `${e.wins}-${e.losses}${e.ties ? `-${e.ties}` : ''}`;

  const medianRows = data.league_median.teams
    .map(
      (t) =>
        `<tr style="background-color:${t.beat_median ? GREEN : ORANGE};">` +
        `<td style="padding:4px 8px;">${t.team_name}</td>` +
        `<td style="padding:4px 8px;text-align:right;font-weight:bold;">${t.points}</td>` +
        `</tr>`,
    )
    .join('');

  const topPlayerRows = ALL_POSITIONS.map((pos) => {
    const p = data.top_players[pos];
    if (!p) return '';
    return (
      `<tr>` +
      `<td style="padding:4px 8px;font-weight:bold;">${pos}</td>` +
      `<td style="padding:4px 8px;">${p.player_name}</td>` +
      `<td style="padding:4px 8px;text-align:right;">${p.points}</td>` +
      `<td style="padding:4px 8px;">${p.owner}</td>` +
      `</tr>`
    );
  }).join('');

  const theOnesSection = SKILL_POSITIONS.map((pos) => {
    const leaders = data.season_leaders[pos] ?? [];
    if (!leaders.length) return '';
    const rows = leaders
      .map(
        (l) =>
          `<tr>` +
          `<td style="padding:2px 8px;color:#6b7280;">${l.rank}.</td>` +
          `<td style="padding:2px 8px;">${l.player_name}</td>` +
          `<td style="padding:2px 8px;text-align:right;font-weight:bold;">${l.total_points}</td>` +
          `<td style="padding:2px 8px;color:#6b7280;">[${l.owner}]</td>` +
          `</tr>`,
      )
      .join('');
    return `<p style="font-weight:bold;margin-bottom:2px;">${pos}</p><table style="width:100%;border-collapse:collapse;margin-bottom:8px;">${rows}</table>`;
  }).join('');

  const rookieSection = SKILL_POSITIONS.map((pos) => {
    const rookies = data.rookie_report[pos] ?? [];
    if (!rookies.length) return '';
    const rows = rookies
      .map(
        (r) =>
          `<tr>` +
          `<td style="padding:2px 8px;">${r.player_name}</td>` +
          `<td style="padding:2px 8px;text-align:right;font-weight:bold;">${r.total_points}</td>` +
          `<td style="padding:2px 8px;color:#6b7280;">&lt;${r.position_label}&gt;</td>` +
          `<td style="padding:2px 8px;color:#6b7280;">[${r.owner}]</td>` +
          `</tr>`,
      )
      .join('');
    return `<p style="font-weight:bold;margin-bottom:2px;">${pos}</p><table style="width:100%;border-collapse:collapse;margin-bottom:8px;">${rows}</table>`;
  }).join('');

  const playoffRows = data.playoff_picture.playoff
    .map((e) => `<div>${e.seed}. ${e.display_name} [${record(e)}]</div>`)
    .join('');
  const consolationRows = data.playoff_picture.consolation
    .map((e) => `<div>${e.seed}. ${e.display_name} [${record(e)}]</div>`)
    .join('');

  const standingsRows = data.standings
    .map(
      (s) =>
        `<tr>` +
        `<td style="padding:4px 8px;">${s.rank}.</td>` +
        `<td style="padding:4px 8px;">${s.team_name}</td>` +
        `<td style="padding:4px 8px;text-align:center;">${s.wins}-${s.losses}${s.ties ? `-${s.ties}` : ''}</td>` +
        `<td style="padding:4px 8px;text-align:right;">${s.points_for}</td>` +
        `</tr>`,
    )
    .join('');

  const playoffOddsPlayoff = data.playoff_picture.playoff
    .map((e) => `<div style="padding:2px 0;">${e.seed}. ${e.team_name} [${record(e)}] ✅</div>`)
    .join('');
  const playoffOddsConsolation = data.playoff_picture.consolation
    .map((e) => `<div style="padding:2px 0;">${e.seed}. ${e.team_name} [${record(e)}] ❌</div>`)
    .join('');

  const potentialRows = data.potential_points
    .map(
      (p) =>
        `<tr>` +
        `<td style="padding:4px 8px;">${p.rank}.</td>` +
        `<td style="padding:4px 8px;">${p.team_name}</td>` +
        `<td style="padding:4px 8px;text-align:right;font-weight:bold;">${p.max_potential_points}</td>` +
        `</tr>`,
    )
    .join('');

  const recapText = data.recaps
    .map(
      (r) =>
        `<div style="margin-bottom:12px;">` +
        `<p>${r.recap_text ?? ''}</p>` +
        `</div>`,
    )
    .join('');

  const upcomingText = data.upcoming_matchups
    .map(
      (r) =>
        `<div style="margin-bottom:12px;">` +
        `<p>${r.predictions_text ?? ''}</p>` +
        `</div>`,
    )
    .join('');

  return `<!DOCTYPE html>
<html>
<head><meta charset="UTF-8" /></head>
<body style="font-family:Arial,sans-serif;font-size:14px;color:#111827;max-width:700px;margin:0 auto;padding:16px;">

<h1 style="background-color:${HEADER_BG};color:white;padding:12px 16px;border-radius:6px;margin-bottom:16px;">
  Insight2Dynasty — Week ${data.week} Newsletter (${data.season})
</h1>

${section('', `<p>${intro || '[Add intro here]'}</p>`)}

${section('INTERESTING FACT', `<p>${interestingFact || '[Add interesting fact here]'}</p>`)}

${section('HIGH SCORE', `<p style="font-size:16px;font-weight:bold;">${data.high_score.team_name} — ${data.high_score.points}</p>`)}

${section('LOW SCORE', `<p style="font-size:16px;font-weight:bold;">${data.low_score.team_name} — ${data.low_score.points}</p>`)}

${data.is_regular_season ? section('LEAGUE MEDIAN', `
<p style="color:#6b7280;margin-bottom:4px;">Median: ${data.league_median.median}</p>
<table style="width:100%;border-collapse:collapse;">
  <tr style="background-color:${HEADER_BG};color:white;">
    <th style="padding:6px 8px;text-align:left;">Team</th>
    <th style="padding:6px 8px;text-align:right;">Score</th>
  </tr>
  ${medianRows}
</table>`) : ''}

${section('GAME RECAPS', recapText || '<p>[Recaps not yet available]</p>')}

${section('STANDINGS', `
<table style="width:100%;border-collapse:collapse;">
  <tr style="background-color:${HEADER_BG};color:white;">
    <th style="padding:6px 8px;text-align:left;">#</th>
    <th style="padding:6px 8px;text-align:left;">Team</th>
    <th style="padding:6px 8px;text-align:center;">Record</th>
    <th style="padding:6px 8px;text-align:right;">Pts For</th>
  </tr>
  ${standingsRows}
</table>`)}

${section('TOP PLAYERS (Per Position)', `
<table style="width:100%;border-collapse:collapse;">
  <tr style="background-color:${HEADER_BG};color:white;">
    <th style="padding:6px 8px;text-align:left;">Pos</th>
    <th style="padding:6px 8px;text-align:left;">Player</th>
    <th style="padding:6px 8px;text-align:right;">Pts</th>
    <th style="padding:6px 8px;text-align:left;">Owner</th>
  </tr>
  ${topPlayerRows}
</table>`)}

${section("THE 1'S", theOnesSection || '<p>[No data yet]</p>')}

${section('ROOKIE REPORT', rookieSection || '<p>[No rookies yet]</p>')}

${section('PLAYOFF ODDS', `
<p style="font-weight:bold;margin-bottom:4px;">In the Playoffs:</p>
${playoffOddsPlayoff}
<p style="font-weight:bold;margin-top:8px;margin-bottom:4px;">Out of the Playoffs:</p>
${playoffOddsConsolation}`)}

${section(`WEEK ${data.week + 1} MATCHUPS`, upcomingText || '<p>[Matchup predictions not yet available]</p>')}

${section('IF THE PLAYOFFS WERE TO START TODAY', `
<p style="font-weight:bold;">Playoff Bracket:</p>
${playoffRows}
<p style="font-weight:bold;margin-top:8px;">Consolation Bracket:</p>
${consolationRows}`)}

${section('POTENTIAL POINTS', `
<table style="width:100%;border-collapse:collapse;">
  <tr style="background-color:${HEADER_BG};color:white;">
    <th style="padding:6px 8px;text-align:left;">#</th>
    <th style="padding:6px 8px;text-align:left;">Team</th>
    <th style="padding:6px 8px;text-align:right;">Max Points</th>
  </tr>
  ${potentialRows}
</table>`)}

</body>
</html>`;
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function SectionHeader({ children }: { children: React.ReactNode }) {
  return (
    <h2 className="text-lg font-bold text-blue-900 border-b-2 border-blue-600 pb-1 mt-6 mb-3">
      {children}
    </h2>
  );
}

function MedianTable({ data }: { data: LeagueMedian }) {
  return (
    <div>
      <p className="text-sm text-gray-500 mb-1">Median: {data.median}</p>
      <table className="w-full text-sm border-collapse">
        <thead>
          <tr className="bg-blue-600 text-white">
            <th className="px-3 py-2 text-left">Team</th>
            <th className="px-3 py-2 text-right">Score</th>
          </tr>
        </thead>
        <tbody>
          {data.teams.map((t, i) => (
            <tr
              key={i}
              className={t.beat_median ? 'bg-green-100' : 'bg-amber-100'}
            >
              <td className="px-3 py-1">{t.team_name}</td>
              <td className="px-3 py-1 text-right font-bold">{t.points}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function TopPlayersTable({ players }: { players: Record<string, PlayerEntry | null> }) {
  const POSITIONS = ['QB', 'RB', 'WR', 'TE', 'DEF', 'K'];
  return (
    <table className="w-full text-sm border-collapse">
      <thead>
        <tr className="bg-blue-600 text-white">
          <th className="px-3 py-2 text-left">Pos</th>
          <th className="px-3 py-2 text-left">Player</th>
          <th className="px-3 py-2 text-right">Pts</th>
          <th className="px-3 py-2 text-left">Owner</th>
        </tr>
      </thead>
      <tbody>
        {POSITIONS.map((pos, i) => {
          const p = players[pos];
          return (
            <tr key={pos} className={i % 2 === 0 ? 'bg-gray-50' : ''}>
              <td className="px-3 py-1 font-bold">{pos}</td>
              <td className="px-3 py-1">{p?.player_name ?? '—'}</td>
              <td className="px-3 py-1 text-right font-bold">{p?.points ?? '—'}</td>
              <td className="px-3 py-1 text-gray-600">{p?.owner ?? '—'}</td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

function SeasonLeadersSection({ leaders }: { leaders: Record<string, SeasonLeader[]> }) {
  const POSITIONS = ['QB', 'RB', 'WR', 'TE'];
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {POSITIONS.map((pos) => {
        const list = leaders[pos] ?? [];
        return (
          <div key={pos}>
            <p className="font-bold text-sm mb-1">{pos}</p>
            <table className="w-full text-sm border-collapse">
              <tbody>
                {list.map((l) => (
                  <tr key={l.rank} className={l.rank % 2 === 0 ? 'bg-gray-50' : ''}>
                    <td className="px-2 py-0.5 text-gray-400 w-6">{l.rank}.</td>
                    <td className="px-2 py-0.5">{l.player_name}</td>
                    <td className="px-2 py-0.5 text-right font-bold">{l.total_points}</td>
                    <td className="px-2 py-0.5 text-gray-500 text-xs">[{l.owner}]</td>
                  </tr>
                ))}
                {!list.length && (
                  <tr><td colSpan={4} className="px-2 py-1 text-gray-400">No data</td></tr>
                )}
              </tbody>
            </table>
          </div>
        );
      })}
    </div>
  );
}

function RookieSection({ report }: { report: Record<string, RookieEntry[]> }) {
  const POSITIONS = ['QB', 'RB', 'WR', 'TE'];
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {POSITIONS.map((pos) => {
        const list = report[pos] ?? [];
        return (
          <div key={pos}>
            <p className="font-bold text-sm mb-1">{pos}</p>
            <table className="w-full text-sm border-collapse">
              <tbody>
                {list.map((r) => (
                  <tr key={r.rank} className={r.rank % 2 === 0 ? 'bg-gray-50' : ''}>
                    <td className="px-2 py-0.5">{r.player_name}</td>
                    <td className="px-2 py-0.5 text-right font-bold">{r.total_points}</td>
                    <td className="px-2 py-0.5 text-blue-600 text-xs">&lt;{r.position_label}&gt;</td>
                    <td className="px-2 py-0.5 text-gray-500 text-xs">[{r.owner}]</td>
                  </tr>
                ))}
                {!list.length && (
                  <tr><td colSpan={4} className="px-2 py-1 text-gray-400">No data</td></tr>
                )}
              </tbody>
            </table>
          </div>
        );
      })}
    </div>
  );
}

function PlayoffPicture({ picture }: { picture: { playoff: PlayoffEntry[]; consolation: PlayoffEntry[] } }) {
  const record = (e: PlayoffEntry) =>
    `${e.wins}-${e.losses}${e.ties ? `-${e.ties}` : ''}`;

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      <div>
        <p className="font-bold mb-2">Playoff Bracket:</p>
        {picture.playoff.map((e) => (
          <div key={e.seed} className="flex gap-2 py-0.5">
            <span className="text-gray-500 w-4">{e.seed}.</span>
            <span>{e.display_name}</span>
            <span className="text-gray-500">[{record(e)}]</span>
          </div>
        ))}
      </div>
      <div>
        <p className="font-bold mb-2">Consolation Bracket:</p>
        {picture.consolation.map((e) => (
          <div key={e.seed} className="flex gap-2 py-0.5">
            <span className="text-gray-500 w-4">{e.seed}.</span>
            <span>{e.display_name}</span>
            <span className="text-gray-500">[{record(e)}]</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function Newsletter() {
  const [weekInput, setWeekInput] = useState('');
  const [seasonInput, setSeasonInput] = useState('');
  const [intro, setIntro] = useState('');
  const [interestingFact, setInterestingFact] = useState('');
  const [copied, setCopied] = useState(false);
  const previewRef = useRef<HTMLDivElement>(null);

  const week = weekInput ? Number(weekInput) : undefined;
  const season = seasonInput ? Number(seasonInput) : undefined;

  const { data, isLoading, error } = useQuery<NewsletterData>({
    queryKey: ['newsletter', week, season],
    queryFn: () => api.getNewsletter(week!, season),
    enabled: !!week,
  });

  const handleCopyHTML = () => {
    if (!data) return;
    const html = generateEmailHTML(data, intro, interestingFact);
    navigator.clipboard.writeText(html).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2500);
    });
  };

  return (
    <div className="container mx-auto px-4 py-8 max-w-5xl">
      <h1 className="text-2xl font-bold mb-6">Newsletter Generator</h1>

      {/* Controls */}
      <div className="bg-white rounded-lg shadow p-4 mb-6 flex flex-wrap gap-4 items-end">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Week *</label>
          <input
            type="number"
            min={1}
            max={18}
            value={weekInput}
            onChange={(e) => setWeekInput(e.target.value)}
            placeholder="e.g. 14"
            className="border rounded px-3 py-2 w-24 text-sm"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Season (optional)</label>
          <input
            type="number"
            min={2020}
            max={2030}
            value={seasonInput}
            onChange={(e) => setSeasonInput(e.target.value)}
            placeholder="e.g. 2025"
            className="border rounded px-3 py-2 w-28 text-sm"
          />
        </div>
        {data && (
          <button
            onClick={handleCopyHTML}
            className="ml-auto bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 transition text-sm font-semibold"
          >
            {copied ? '✓ Copied!' : 'Copy HTML'}
          </button>
        )}
      </div>

      {/* Manual sections */}
      <div className="bg-white rounded-lg shadow p-4 mb-6 space-y-4">
        <h2 className="font-semibold text-gray-800">Manual Sections</h2>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Intro</label>
          <textarea
            value={intro}
            onChange={(e) => setIntro(e.target.value)}
            rows={3}
            placeholder="Write your weekly intro..."
            className="w-full border rounded px-3 py-2 text-sm resize-y"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Interesting Fact</label>
          <textarea
            value={interestingFact}
            onChange={(e) => setInterestingFact(e.target.value)}
            rows={2}
            placeholder="An interesting NFL fact for the week..."
            className="w-full border rounded px-3 py-2 text-sm resize-y"
          />
        </div>
      </div>

      {/* Loading / Error */}
      {isLoading && (
        <div className="flex justify-center py-16">
          <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-600" />
        </div>
      )}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded p-4 text-red-600 text-sm">
          Error loading newsletter data: {(error as Error).message}
        </div>
      )}
      {!week && !isLoading && (
        <div className="text-center text-gray-400 py-16">Enter a week number to generate the newsletter.</div>
      )}

      {/* Preview */}
      {data && (
        <div ref={previewRef} className="bg-white rounded-lg shadow p-6 space-y-2 text-sm">
          {/* Header */}
          <div className="bg-blue-600 text-white px-4 py-3 rounded text-lg font-bold mb-4">
            Insight2Dynasty — Week {data.week} Newsletter ({data.season})
          </div>

          {/* Intro */}
          <SectionHeader>INTRO</SectionHeader>
          <p className="whitespace-pre-wrap text-gray-700">{intro || <span className="text-gray-400 italic">[Add intro above]</span>}</p>

          {/* Interesting Fact */}
          <SectionHeader>INTERESTING FACT</SectionHeader>
          <p className="whitespace-pre-wrap text-gray-700">
            {interestingFact || <span className="text-gray-400 italic">[Add interesting fact above]</span>}
          </p>

          {/* High Score */}
          <SectionHeader>HIGH SCORE</SectionHeader>
          <p className="text-xl font-bold text-green-700">
            {data.high_score.team_name} — {data.high_score.points}
          </p>

          {/* Low Score */}
          <SectionHeader>LOW SCORE</SectionHeader>
          <p className="text-xl font-bold text-red-600">
            {data.low_score.team_name} — {data.low_score.points}
          </p>

          {/* League Median — regular season only */}
          {data.is_regular_season && (
            <>
              <SectionHeader>LEAGUE MEDIAN</SectionHeader>
              <MedianTable data={data.league_median} />
            </>
          )}

          {/* Game Recaps */}
          <SectionHeader>GAME RECAPS</SectionHeader>
          {data.recaps.length > 0 ? (
            data.recaps.map((r) => (
              <div key={r.matchup_id} className="mb-3 p-3 bg-gray-50 rounded text-sm">
                <p>{r.recap_text ?? <span className="text-gray-400 italic">No recap available</span>}</p>
              </div>
            ))
          ) : (
            <p className="text-gray-400 italic">Recaps not yet generated for this week.</p>
          )}

          {/* Standings */}
          <SectionHeader>STANDINGS</SectionHeader>
          <table className="w-full text-sm border-collapse">
            <thead>
              <tr className="bg-blue-600 text-white">
                <th className="px-3 py-2 text-left">#</th>
                <th className="px-3 py-2 text-left">Team</th>
                <th className="px-3 py-2 text-center">Record</th>
                <th className="px-3 py-2 text-right">Pts For</th>
              </tr>
            </thead>
            <tbody>
              {data.standings.map((s, i) => (
                <tr key={s.rank} className={i % 2 === 0 ? 'bg-gray-50' : ''}>
                  <td className="px-3 py-1">{s.rank}.</td>
                  <td className="px-3 py-1">{s.team_name}</td>
                  <td className="px-3 py-1 text-center">{s.wins}-{s.losses}{s.ties ? `-${s.ties}` : ''}</td>
                  <td className="px-3 py-1 text-right font-bold">{s.points_for}</td>
                </tr>
              ))}
            </tbody>
          </table>

          {/* Top Players */}
          <SectionHeader>TOP PLAYERS (Per Position)</SectionHeader>
          <TopPlayersTable players={data.top_players} />

          {/* The 1's */}
          <SectionHeader>THE 1'S</SectionHeader>
          <SeasonLeadersSection leaders={data.season_leaders} />

          {/* Rookie Report */}
          <SectionHeader>ROOKIE REPORT</SectionHeader>
          <RookieSection report={data.rookie_report} />

          {/* Playoff Odds */}
          <SectionHeader>PLAYOFF ODDS</SectionHeader>
          <p className="font-bold text-sm mb-1">In the Playoffs:</p>
          {data.playoff_picture.playoff.map((e) => (
            <div key={e.seed} className="flex gap-2 py-0.5 text-sm text-green-700">
              <span className="w-4">{e.seed}.</span>
              <span>{e.team_name}</span>
              <span className="text-gray-500">[{e.wins}-{e.losses}{e.ties ? `-${e.ties}` : ''}]</span>
              <span>✅</span>
            </div>
          ))}
          <p className="font-bold text-sm mt-3 mb-1">Out of the Playoffs:</p>
          {data.playoff_picture.consolation.map((e) => (
            <div key={e.seed} className="flex gap-2 py-0.5 text-sm text-red-600">
              <span className="w-4">{e.seed}.</span>
              <span>{e.team_name}</span>
              <span className="text-gray-500">[{e.wins}-{e.losses}{e.ties ? `-${e.ties}` : ''}]</span>
              <span>❌</span>
            </div>
          ))}

          {/* Next Week Matchups */}
          <SectionHeader>WEEK {data.week + 1} MATCHUPS</SectionHeader>
          {data.upcoming_matchups.length > 0 ? (
            data.upcoming_matchups.map((r) => (
              <div key={r.matchup_id} className="mb-3 p-3 bg-gray-50 rounded text-sm">
                <p>{r.predictions_text ?? <span className="text-gray-400 italic">No prediction available</span>}</p>
              </div>
            ))
          ) : (
            <p className="text-gray-400 italic">Matchup predictions not yet available.</p>
          )}

          {/* Playoff Picture */}
          <SectionHeader>IF THE PLAYOFFS WERE TO START TODAY</SectionHeader>
          <PlayoffPicture picture={data.playoff_picture} />

          {/* Potential Points */}
          <SectionHeader>POTENTIAL POINTS</SectionHeader>
          <table className="w-full text-sm border-collapse">
            <thead>
              <tr className="bg-blue-600 text-white">
                <th className="px-3 py-2 text-left">#</th>
                <th className="px-3 py-2 text-left">Team</th>
                <th className="px-3 py-2 text-right">Max Points</th>
              </tr>
            </thead>
            <tbody>
              {data.potential_points.map((p, i) => (
                <tr key={p.rank} className={i % 2 === 0 ? 'bg-gray-50' : ''}>
                  <td className="px-3 py-1">{p.rank}.</td>
                  <td className="px-3 py-1">{p.team_name}</td>
                  <td className="px-3 py-1 text-right font-bold">{p.max_potential_points}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
