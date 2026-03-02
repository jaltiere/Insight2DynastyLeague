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

const GRADE_COLORS: Record<string, string> = {
  'A+': 'bg-green-600 text-white',
  A: 'bg-green-600 text-white',
  'A-': 'bg-green-500 text-white',
  'B+': 'bg-blue-600 text-white',
  B: 'bg-blue-500 text-white',
  'B-': 'bg-blue-400 text-white',
  'C+': 'bg-gray-400 text-white',
  C: 'bg-gray-400 text-white',
  'C-': 'bg-gray-400 text-white',
  'D+': 'bg-orange-400 text-white',
  D: 'bg-orange-500 text-white',
  'D-': 'bg-orange-600 text-white',
  F: 'bg-red-600 text-white',
};

interface PickDetail {
  pick_no: number;
  round: number;
  player_id: string;
  player_name: string;
  position: string | null;
  team: string | null;
  weighted_points: number;
  starter_weeks: number;
  bench_weeks: number;
  total_weeks: number;
}

interface OwnerDraft {
  user_id: string;
  username: string;
  avatar: string | null;
  total_value: number;
  num_picks: number;
  avg_value_per_pick: number;
  value_vs_average: number;
  grade: string;
  picks: PickDetail[];
}

interface DraftGrade {
  draft_id: string;
  year: number;
  type: string;
  rounds: number;
  weeks_of_data: number;
  avg_value: number;
  total_picks: number;
  owners: OwnerDraft[];
}

interface Owner {
  user_id: string;
  username: string;
  display_name: string;
}

function PositionBadge({ position }: { position: string | null }) {
  if (!position) return null;
  const bg = POSITION_COLORS[position] || 'bg-gray-400';
  return (
    <span className={`${bg} text-white text-xs font-bold px-1.5 py-0.5 rounded mr-1.5`}>
      {position}
    </span>
  );
}

function GradeBadge({ grade }: { grade: string }) {
  const colors = GRADE_COLORS[grade] || 'bg-gray-400 text-white';
  return (
    <span className={`${colors} text-lg font-bold px-3 py-1 rounded-lg inline-block min-w-[3rem] text-center`}>
      {grade}
    </span>
  );
}

function OwnerCard({ owner }: { owner: OwnerDraft }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="bg-white rounded-lg shadow mb-3">
      {/* Header */}
      <div
        className="px-4 py-3 flex items-center justify-between cursor-pointer hover:bg-gray-50 rounded-t-lg"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-3">
          <span className="font-semibold text-gray-900">{owner.username}</span>
          <span className="text-xs text-gray-500">
            {owner.num_picks} picks • {owner.total_value.toFixed(1)} pts
          </span>
          <span className="text-xs text-gray-400">
            {(owner.value_vs_average * 100).toFixed(0)}% vs avg
          </span>
        </div>
        <div className="flex items-center gap-3">
          <GradeBadge grade={owner.grade} />
          <span className="text-gray-400">{expanded ? '\u25B2' : '\u25BC'}</span>
        </div>
      </div>

      {/* Expanded picks */}
      {expanded && (
        <div className="border-t border-gray-200 px-4 py-4">
          <div className="text-xs font-semibold text-gray-500 uppercase mb-2">
            Draft Picks
          </div>
          <div className="space-y-2">
            {owner.picks.map((pick) => (
              <div key={pick.pick_no} className="bg-gray-50 rounded p-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center">
                    <span className="text-xs text-gray-500 mr-2 w-12">
                      {pick.round}.{pick.pick_no}
                    </span>
                    <PositionBadge position={pick.position} />
                    <span className="text-sm font-medium text-gray-900">{pick.player_name}</span>
                    {pick.team && (
                      <span className="text-xs text-gray-500 ml-1.5">({pick.team})</span>
                    )}
                  </div>
                  <div className="text-right">
                    <span className="text-sm font-semibold text-gray-900">
                      {pick.weighted_points.toFixed(1)}
                    </span>
                    <span className="text-xs text-gray-500 ml-1">pts</span>
                  </div>
                </div>
                <div className="flex items-center gap-3 mt-1 text-xs text-gray-500 ml-14">
                  <span>{pick.starter_weeks}w starter</span>
                  <span>{pick.bench_weeks}w bench</span>
                  <span>{pick.total_weeks}w total</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function DraftCard({ draft }: { draft: DraftGrade }) {
  return (
    <div className="bg-white rounded-lg shadow mb-6">
      {/* Draft header */}
      <div className="px-4 py-3 bg-gray-50 border-b border-gray-200 rounded-t-lg">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className="text-lg font-bold text-gray-900">{draft.year} Draft</span>
            <span className="text-sm text-gray-500">
              {draft.type} • {draft.rounds} rounds • {draft.total_picks} picks
            </span>
          </div>
          <div className="text-sm text-gray-500">
            {draft.weeks_of_data}w of data
          </div>
        </div>
      </div>

      {/* Owners */}
      <div className="px-4 py-4">
        {draft.owners.map((owner) => (
          <OwnerCard key={owner.user_id} owner={owner} />
        ))}
      </div>
    </div>
  );
}

export default function DraftRankings() {
  const [draftType, setDraftType] = useState<string | undefined>(undefined);
  const [ownerId, setOwnerId] = useState<string | undefined>(undefined);

  const { data: ownersData } = useQuery({
    queryKey: ['owners'],
    queryFn: () => api.getAllOwners().then(res => res.data),
  });

  const { data, isLoading, error } = useQuery({
    queryKey: ['draftGrades', draftType, ownerId],
    queryFn: () =>
      api.getDraftGrades({
        draft_type: draftType,
        owner_id: ownerId,
      }),
  });

  const drafts: DraftGrade[] = data?.drafts || [];
  const owners: Owner[] = (ownersData?.owners || [])
    .map((o: Owner) => ({
      user_id: o.user_id,
      username: o.username,
      display_name: o.display_name || o.username,
    }))
    .sort((a: Owner, b: Owner) => a.display_name.localeCompare(b.display_name));

  if (isLoading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <h1 className="text-4xl font-bold mb-6">Draft Rankings</h1>
        <div className="flex justify-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 dark:border-blue-400" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="container mx-auto px-4 py-8">
        <h1 className="text-4xl font-bold mb-6">Draft Rankings</h1>
        <div className="bg-red-50 border border-red-200 rounded-lg p-6 dark:bg-red-900/20 dark:border-red-800">
          <h2 className="text-red-800 text-lg font-semibold dark:text-red-400">Error loading draft rankings</h2>
          <p className="text-red-600 mt-2 dark:text-red-400">Please try refreshing the page.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-4xl font-bold mb-6">Draft Rankings</h1>

      {/* Filters */}
      <div className="bg-white rounded-lg shadow mb-6">
        <div className="flex flex-wrap items-center gap-4 px-6 py-3">
          <div className="flex items-center gap-2">
            <label className="text-sm font-medium text-gray-700">Draft Type:</label>
            <select
              value={draftType ?? ''}
              onChange={(e) => setDraftType(e.target.value || undefined)}
              className="border border-gray-300 rounded px-3 py-1.5 text-sm bg-white text-gray-900"
            >
              <option value="">All Drafts</option>
              <option value="startup">Startup Draft</option>
              <option value="rookie">Rookie Drafts</option>
            </select>
          </div>
          <div className="flex items-center gap-2">
            <label className="text-sm font-medium text-gray-700">Owner:</label>
            <select
              value={ownerId ?? ''}
              onChange={(e) => setOwnerId(e.target.value || undefined)}
              className="border border-gray-300 rounded px-3 py-1.5 text-sm bg-white text-gray-900"
            >
              <option value="">All Owners</option>
              {owners.map((o) => (
                <option key={o.user_id} value={o.user_id}>
                  {o.display_name}
                </option>
              ))}
            </select>
          </div>
          <div className="text-sm text-gray-500 ml-auto">
            {drafts.length} draft{drafts.length !== 1 ? 's' : ''}
          </div>
        </div>
      </div>

      {/* Draft cards */}
      {drafts.length === 0 ? (
        <div className="bg-white rounded-lg shadow p-8 text-center">
          <p className="text-gray-500">No drafts found.</p>
        </div>
      ) : (
        <div>
          {drafts.map((draft) => (
            <DraftCard key={draft.draft_id} draft={draft} />
          ))}
        </div>
      )}
    </div>
  );
}
