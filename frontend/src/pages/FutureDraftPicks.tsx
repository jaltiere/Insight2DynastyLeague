import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../services/api';
import type { FutureDraftPick, FuturePickOwner, FutureDraftPicksResponse } from '../types';

// ─── Constants ────────────────────────────────────────────────────────────────

// Tailwind bg+text color pairs — one per team (up to 16)
const OWNER_COLORS = [
  { bg: 'bg-blue-100',   text: 'text-blue-800',   border: 'border-blue-300'   },
  { bg: 'bg-green-100',  text: 'text-green-800',  border: 'border-green-300'  },
  { bg: 'bg-purple-100', text: 'text-purple-800', border: 'border-purple-300' },
  { bg: 'bg-orange-100', text: 'text-orange-800', border: 'border-orange-300' },
  { bg: 'bg-pink-100',   text: 'text-pink-800',   border: 'border-pink-300'   },
  { bg: 'bg-yellow-100', text: 'text-yellow-800', border: 'border-yellow-300' },
  { bg: 'bg-teal-100',   text: 'text-teal-800',   border: 'border-teal-300'   },
  { bg: 'bg-red-100',    text: 'text-red-800',    border: 'border-red-300'    },
  { bg: 'bg-indigo-100', text: 'text-indigo-800', border: 'border-indigo-300' },
  { bg: 'bg-lime-100',   text: 'text-lime-800',   border: 'border-lime-300'   },
  { bg: 'bg-cyan-100',   text: 'text-cyan-800',   border: 'border-cyan-300'   },
  { bg: 'bg-rose-100',   text: 'text-rose-800',   border: 'border-rose-300'   },
  { bg: 'bg-amber-100',  text: 'text-amber-800',  border: 'border-amber-300'  },
  { bg: 'bg-violet-100', text: 'text-violet-800', border: 'border-violet-300' },
  { bg: 'bg-sky-100',    text: 'text-sky-800',    border: 'border-sky-300'    },
  { bg: 'bg-fuchsia-100',text: 'text-fuchsia-800',border: 'border-fuchsia-300'},
];

// ─── Helpers ─────────────────────────────────────────────────────────────────

function avatarUrl(avatarId: string | null): string | null {
  if (!avatarId) return null;
  return `https://sleepercdn.com/avatars/thumbs/${avatarId}`;
}

function ordinal(n: number): string {
  const s = ['th', 'st', 'nd', 'rd'];
  const v = n % 100;
  return n + (s[(v - 20) % 10] || s[v] || s[0]);
}

// ─── Sub-components ───────────────────────────────────────────────────────────

interface PickCellProps {
  pick: FutureDraftPick;
  colorByRosterId: Record<number, typeof OWNER_COLORS[0]>;
}

function PickCell({ pick, colorByRosterId }: PickCellProps) {
  const color = colorByRosterId[pick.current_roster_id] ?? OWNER_COLORS[0];
  const isTraded = pick.is_traded;

  return (
    <div
      className={`
        relative rounded-lg border px-2 py-1.5 text-center min-w-[100px]
        ${color.bg} ${color.text} ${color.border}
      `}
    >
      <div className="text-xs font-semibold leading-tight truncate">
        {pick.current_owner.display_name}
      </div>

      {isTraded && (
        <div className="flex items-center justify-center gap-0.5 mt-0.5">
          <span className="text-[10px] font-medium opacity-75">from</span>
          <span className="text-[10px] font-medium opacity-75 truncate">
            {pick.original_owner.display_name}
          </span>
        </div>
      )}

      {isTraded && (
        <span
          className="absolute -top-1.5 -right-1.5 w-3.5 h-3.5 rounded-full bg-yellow-400 border border-yellow-600 flex items-center justify-center"
          title={`Traded from ${pick.original_owner.display_name}`}
        >
          <svg className="w-2 h-2 text-yellow-900" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M7.707 3.293a1 1 0 010 1.414L5.414 7H11a7 7 0 017 7v2a1 1 0 11-2 0v-2a5 5 0 00-5-5H5.414l2.293 2.293a1 1 0 11-1.414 1.414l-4-4a1 1 0 010-1.414l4-4a1 1 0 011.414 0z" clipRule="evenodd" />
          </svg>
        </span>
      )}
    </div>
  );
}

// ─── Season Grid ─────────────────────────────────────────────────────────────

interface SeasonGridProps {
  season: number;
  numRounds: number;
  owners: FuturePickOwner[];
  picks: FutureDraftPick[];
  colorByRosterId: Record<number, typeof OWNER_COLORS[0]>;
}

function SeasonGrid({ season, numRounds, owners, picks, colorByRosterId }: SeasonGridProps) {
  // picks for this season indexed by (original_roster_id, round)
  const pickIndex: Record<string, FutureDraftPick> = {};
  for (const p of picks) {
    if (p.season === season) {
      pickIndex[`${p.original_roster_id}_${p.round}`] = p;
    }
  }

  const rounds = Array.from({ length: numRounds }, (_, i) => i + 1);

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full text-sm">
        <thead>
          <tr>
            <th className="sticky left-0 z-10 bg-white dark:bg-gray-900 text-left px-3 py-2 font-semibold text-gray-600 border-b border-r border-gray-200 dark:border-gray-700 whitespace-nowrap">
              Original Team
            </th>
            {rounds.map(rnd => (
              <th
                key={rnd}
                className="px-3 py-2 font-semibold text-gray-600 text-center border-b border-gray-200 dark:border-gray-700 whitespace-nowrap"
              >
                {ordinal(rnd)} Round
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {owners.map((owner, idx) => {
            const rowColor = colorByRosterId[owner.roster_id];
            const avatar = avatarUrl(owner.avatar);
            return (
              <tr key={owner.roster_id} className={idx % 2 === 0 ? '' : 'bg-gray-50 dark:bg-gray-800/40'}>
                {/* Original team column */}
                <td className="sticky left-0 z-10 bg-white dark:bg-gray-900 px-3 py-2 border-r border-gray-200 dark:border-gray-700">
                  <div className="flex items-center gap-2 min-w-[140px]">
                    {avatar ? (
                      <img src={avatar} alt="" className="w-6 h-6 rounded-full flex-shrink-0" />
                    ) : (
                      <div className={`w-6 h-6 rounded-full flex-shrink-0 ${rowColor?.bg ?? 'bg-gray-200'} flex items-center justify-center`}>
                        <span className={`text-[10px] font-bold ${rowColor?.text ?? 'text-gray-600'}`}>
                          {owner.display_name.charAt(0).toUpperCase()}
                        </span>
                      </div>
                    )}
                    <span className="font-medium text-gray-800 dark:text-gray-200 text-xs whitespace-nowrap truncate max-w-[120px]">
                      {owner.display_name}
                    </span>
                  </div>
                </td>

                {/* Round columns */}
                {rounds.map(rnd => {
                  const pick = pickIndex[`${owner.roster_id}_${rnd}`];
                  return (
                    <td key={rnd} className="px-2 py-1.5 text-center">
                      {pick ? (
                        <PickCell pick={pick} colorByRosterId={colorByRosterId} />
                      ) : (
                        <span className="text-gray-400 text-xs">—</span>
                      )}
                    </td>
                  );
                })}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

// ─── Legend ──────────────────────────────────────────────────────────────────

interface LegendProps {
  owners: FuturePickOwner[];
  colorByRosterId: Record<number, typeof OWNER_COLORS[0]>;
}

function Legend({ owners, colorByRosterId }: LegendProps) {
  return (
    <div className="flex flex-wrap gap-2">
      {owners.map(owner => {
        const color = colorByRosterId[owner.roster_id];
        const avatar = avatarUrl(owner.avatar);
        return (
          <div
            key={owner.roster_id}
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-xs font-medium ${color?.bg ?? 'bg-gray-100'} ${color?.text ?? 'text-gray-700'} ${color?.border ?? 'border-gray-300'}`}
          >
            {avatar ? (
              <img src={avatar} alt="" className="w-4 h-4 rounded-full" />
            ) : (
              <span className="w-4 h-4 rounded-full bg-current opacity-30 inline-block" />
            )}
            {owner.display_name}
          </div>
        );
      })}
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function FutureDraftPicks() {
  const { data, isLoading, isError } = useQuery<FutureDraftPicksResponse>({
    queryKey: ['future-draft-picks'],
    queryFn: () => api.getFutureDraftPicks(),
    staleTime: 5 * 60 * 1000,
  });

  const [selectedSeason, setSelectedSeason] = useState<number | null>(null);

  if (isLoading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-gray-200 rounded w-64" />
          <div className="h-4 bg-gray-200 rounded w-96" />
          <div className="h-64 bg-gray-200 rounded" />
        </div>
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className="container mx-auto px-4 py-8">
        <p className="text-red-600">Failed to load future draft picks.</p>
      </div>
    );
  }

  const { future_seasons, num_rounds, owners, picks } = data;
  const activeSeason = selectedSeason ?? future_seasons[0] ?? null;

  // Assign a stable color to each owner (alphabetical order from API)
  const colorByRosterId: Record<number, typeof OWNER_COLORS[0]> = {};
  owners.forEach((owner, idx) => {
    colorByRosterId[owner.roster_id] = OWNER_COLORS[idx % OWNER_COLORS.length];
  });

  // Traded pick count for selected season (for summary badge)
  const tradedCount = picks.filter(
    p => p.season === activeSeason && p.is_traded
  ).length;

  return (
    <div className="container mx-auto px-4 py-6 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl md:text-3xl font-bold text-gray-900">Future Draft Pick Tracker</h1>
        <p className="text-gray-500 mt-1 text-sm">
          Who currently holds each future draft pick, and where it came from.
        </p>
      </div>

      {/* Year tabs */}
      {future_seasons.length > 0 ? (
        <>
          <div className="flex items-center gap-2 flex-wrap">
            {future_seasons.map(year => (
              <button
                key={year}
                onClick={() => setSelectedSeason(year)}
                className={`
                  px-4 py-2 rounded-lg text-sm font-semibold border transition
                  ${activeSeason === year
                    ? 'bg-blue-600 text-white border-blue-600'
                    : 'bg-white text-gray-700 border-gray-300 hover:border-blue-400 hover:text-blue-600'}
                `}
              >
                {year}
              </button>
            ))}
          </div>

          {/* Summary bar */}
          <div className="flex items-center gap-4 flex-wrap">
            <div className="flex items-center gap-2 text-sm text-gray-600">
              <span className="font-semibold text-gray-900">{activeSeason}</span>
              <span>·</span>
              <span>{num_rounds} rounds</span>
              <span>·</span>
              {tradedCount > 0 ? (
                <span className="flex items-center gap-1">
                  <span className="w-3 h-3 rounded-full bg-yellow-400 border border-yellow-600 inline-block" />
                  {tradedCount} traded pick{tradedCount !== 1 ? 's' : ''}
                </span>
              ) : (
                <span className="text-gray-400">No traded picks</span>
              )}
            </div>
          </div>

          {/* Legend */}
          <Legend owners={owners} colorByRosterId={colorByRosterId} />

          {/* Grid */}
          {activeSeason && (
            <div className="bg-white dark:bg-gray-900 rounded-xl shadow border border-gray-200 dark:border-gray-700 overflow-hidden">
              <SeasonGrid
                season={activeSeason}
                numRounds={num_rounds}
                owners={owners}
                picks={picks}
                colorByRosterId={colorByRosterId}
              />
            </div>
          )}

          {/* Key */}
          <div className="flex items-start gap-3 text-xs text-gray-500 bg-gray-50 dark:bg-gray-800 rounded-lg p-3">
            <span className="w-3.5 h-3.5 rounded-full bg-yellow-400 border border-yellow-600 flex-shrink-0 mt-0.5" />
            <span>Yellow dot indicates the pick was traded away from the original team. The small "from" label shows the original owner.</span>
          </div>
        </>
      ) : (
        <div className="bg-gray-50 dark:bg-gray-800 rounded-xl p-8 text-center text-gray-500">
          No future draft picks found. Picks may appear once teams begin trading future-year selections.
        </div>
      )}
    </div>
  );
}
