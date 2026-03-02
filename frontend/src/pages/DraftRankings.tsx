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

const GRADE_ORDER: Record<string, number> = {
  'A+': 0, A: 1, 'A-': 2,
  'B+': 3, B: 4, 'B-': 5,
  'C+': 6, C: 7, 'C-': 8,
  'D+': 9, D: 10, 'D-': 11,
  F: 12,
};

const GRADE_TO_POINTS: Record<string, number> = {
  'A+': 4.3, A: 4.0, 'A-': 3.7,
  'B+': 3.3, B: 3.0, 'B-': 2.7,
  'C+': 2.3, C: 2.0, 'C-': 1.7,
  'D+': 1.3, D: 1.0, 'D-': 0.7,
  F: 0.0,
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

interface AggregateOwnerStats {
  user_id: string;
  username: string;
  total_drafts: number;
  avg_grade_points: number;
  avg_grade: string;
  total_value: number;
  avg_value: number;
  grades: string[];
  draft_details: Array<{
    year: number;
    grade: string;
    total_value: number;
    picks: PickDetail[];
  }>;
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

function SmallGradeBadge({ grade }: { grade: string }) {
  const colors = GRADE_COLORS[grade] || 'bg-gray-400 text-white';
  return (
    <span className={`${colors} text-sm font-bold px-2 py-0.5 rounded inline-block min-w-[2.5rem] text-center`}>
      {grade}
    </span>
  );
}

function PicksDetailView({ picks }: { picks: PickDetail[] }) {
  return (
    <div className="px-6 py-4 bg-gray-50">
      <div className="text-xs font-semibold text-gray-500 uppercase mb-2">
        Draft Picks
      </div>
      <div className="space-y-2">
        {picks.map((pick) => (
          <div key={pick.pick_no} className="bg-white rounded p-2">
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
  );
}

// Cross-draft aggregate ranking table
function CrossDraftRankingTable({ drafts }: { drafts: DraftGrade[] }) {
  const [expandedOwner, setExpandedOwner] = useState<string | null>(null);

  // Aggregate stats by owner across all drafts
  const ownerStatsMap = new Map<string, AggregateOwnerStats>();

  drafts.forEach((draft) => {
    draft.owners.forEach((owner) => {
      const existing = ownerStatsMap.get(owner.user_id);
      const gradePoints = GRADE_TO_POINTS[owner.grade] || 0;

      if (existing) {
        existing.total_drafts += 1;
        existing.total_value += owner.total_value;
        existing.avg_grade_points = (existing.avg_grade_points * (existing.total_drafts - 1) + gradePoints) / existing.total_drafts;
        existing.grades.push(owner.grade);
        existing.draft_details.push({
          year: draft.year,
          grade: owner.grade,
          total_value: owner.total_value,
          picks: owner.picks,
        });
      } else {
        ownerStatsMap.set(owner.user_id, {
          user_id: owner.user_id,
          username: owner.username,
          total_drafts: 1,
          avg_grade_points: gradePoints,
          avg_grade: owner.grade,
          total_value: owner.total_value,
          avg_value: owner.total_value,
          grades: [owner.grade],
          draft_details: [{
            year: draft.year,
            grade: owner.grade,
            total_value: owner.total_value,
            picks: owner.picks,
          }],
        });
      }
    });
  });

  // Calculate averages and determine letter grade
  const ownerStats = Array.from(ownerStatsMap.values()).map((stats) => {
    stats.avg_value = stats.total_value / stats.total_drafts;
    // Sort draft details by year descending
    stats.draft_details.sort((a, b) => b.year - a.year);
    // Map avg grade points back to letter grade
    const sortedGrades = Object.entries(GRADE_TO_POINTS).sort((a, b) => b[1] - a[1]);
    let closestGrade = 'F';
    let closestDiff = 999;
    for (const [grade, points] of sortedGrades) {
      const diff = Math.abs(points - stats.avg_grade_points);
      if (diff < closestDiff) {
        closestDiff = diff;
        closestGrade = grade;
      }
    }
    stats.avg_grade = closestGrade;
    return stats;
  });

  // Sort by average grade points (descending)
  ownerStats.sort((a, b) => b.avg_grade_points - a.avg_grade_points);

  return (
    <div className="bg-white rounded-lg shadow overflow-hidden">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Rank
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Owner
            </th>
            <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
              Drafts
            </th>
            <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
              Total Value
            </th>
            <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
              Avg Value
            </th>
            <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
              Avg Grade
            </th>
            <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
              All Grades
            </th>
            <th className="px-6 py-3"></th>
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-200">
          {ownerStats.map((stats, index) => (
            <>
              <tr
                key={stats.user_id}
                className="hover:bg-gray-50 cursor-pointer"
                onClick={() => setExpandedOwner(expandedOwner === stats.user_id ? null : stats.user_id)}
              >
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-500">
                  #{index + 1}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                  {stats.username}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 text-center">
                  {stats.total_drafts}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 text-right">
                  {stats.total_value.toFixed(1)}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 text-right">
                  {stats.avg_value.toFixed(1)}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-center">
                  <SmallGradeBadge grade={stats.avg_grade} />
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-center">
                  <div className="flex items-center justify-center gap-1 flex-wrap">
                    {stats.grades.map((grade, idx) => (
                      <span key={idx} className="text-xs text-gray-600">
                        {grade}{idx < stats.grades.length - 1 ? ',' : ''}
                      </span>
                    ))}
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-right text-sm text-gray-400">
                  {expandedOwner === stats.user_id ? '\u25B2' : '\u25BC'}
                </td>
              </tr>
              {expandedOwner === stats.user_id && (
                <tr>
                  <td colSpan={8} className="px-0 py-0">
                    <div className="bg-gray-50 px-6 py-4">
                      <div className="text-sm font-semibold text-gray-700 mb-3">
                        Draft Breakdown
                      </div>
                      <div className="space-y-3">
                        {stats.draft_details.map((detail, idx) => (
                          <div key={idx} className="bg-white rounded-lg p-3">
                            <div className="flex items-center justify-between mb-2">
                              <span className="text-sm font-semibold text-gray-900">
                                {detail.year} Draft
                              </span>
                              <div className="flex items-center gap-3">
                                <span className="text-sm text-gray-500">
                                  {detail.total_value.toFixed(1)} pts
                                </span>
                                <SmallGradeBadge grade={detail.grade} />
                              </div>
                            </div>
                            <div className="space-y-1">
                              {detail.picks.map((pick) => (
                                <div key={pick.pick_no} className="flex items-center justify-between text-xs bg-gray-50 rounded px-2 py-1">
                                  <div className="flex items-center">
                                    <span className="text-gray-500 mr-2 w-10">
                                      {pick.round}.{pick.pick_no}
                                    </span>
                                    <PositionBadge position={pick.position} />
                                    <span className="text-gray-900">{pick.player_name}</span>
                                  </div>
                                  <span className="text-gray-600">
                                    {pick.weighted_points.toFixed(1)} pts
                                  </span>
                                </div>
                              ))}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </td>
                </tr>
              )}
            </>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// Owner's individual draft table (when owner is selected)
function OwnerDraftsTable({ drafts, ownerName }: { drafts: DraftGrade[]; ownerName: string }) {
  const [expandedDraft, setExpandedDraft] = useState<string | null>(null);

  // Extract owner's performance from each draft and sort by grade
  const ownerDraftPerformance = drafts
    .map((draft) => {
      const ownerData = draft.owners.find((o) => o.username === ownerName);
      return {
        draft,
        ownerData,
      };
    })
    .filter((item) => item.ownerData) // Only include drafts where owner participated
    .sort((a, b) => {
      // Sort by grade (best to worst)
      const gradeA = GRADE_ORDER[a.ownerData!.grade] ?? 99;
      const gradeB = GRADE_ORDER[b.ownerData!.grade] ?? 99;
      return gradeA - gradeB;
    });

  if (ownerDraftPerformance.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow p-8 text-center">
        <p className="text-gray-500">No draft data found for {ownerName}.</p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow overflow-hidden">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Year
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Type
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
              Picks
            </th>
            <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
              Total Value
            </th>
            <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
              Avg/Pick
            </th>
            <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
              vs Average
            </th>
            <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
              Grade
            </th>
            <th className="px-6 py-3"></th>
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-200">
          {ownerDraftPerformance.map(({ draft, ownerData }) => (
            <>
              <tr
                key={draft.draft_id}
                className="hover:bg-gray-50 cursor-pointer"
                onClick={() => setExpandedDraft(expandedDraft === draft.draft_id ? null : draft.draft_id)}
              >
                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                  {draft.year}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {draft.rounds >= 20 ? 'Startup' : 'Rookie'} ({draft.rounds}r)
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {ownerData!.num_picks}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 text-right">
                  {ownerData!.total_value.toFixed(1)}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 text-right">
                  {ownerData!.avg_value_per_pick.toFixed(1)}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-right">
                  <span className={ownerData!.value_vs_average >= 1 ? 'text-green-600 font-semibold' : 'text-red-600 font-semibold'}>
                    {(ownerData!.value_vs_average * 100).toFixed(0)}%
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-center">
                  <SmallGradeBadge grade={ownerData!.grade} />
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-right text-sm text-gray-400">
                  {expandedDraft === draft.draft_id ? '\u25B2' : '\u25BC'}
                </td>
              </tr>
              {expandedDraft === draft.draft_id && ownerData && (
                <tr>
                  <td colSpan={8} className="px-0 py-0">
                    <PicksDetailView picks={ownerData.picks} />
                  </td>
                </tr>
              )}
            </>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// Comparison view - show all owners in each draft
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
              {draft.rounds >= 20 ? 'Startup' : 'Rookie'} • {draft.rounds} rounds • {draft.total_picks} picks
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
  const [viewMode, setViewMode] = useState<'individual' | 'aggregate'>('individual');

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

  // Find selected owner's name
  const selectedOwner = owners.find((o) => o.user_id === ownerId);
  const selectedOwnerName = selectedOwner?.display_name || '';

  // Determine if we should show aggregate view toggle
  const showAggregateToggle = !ownerId && drafts.length > 1;

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
          {showAggregateToggle && (
            <div className="flex items-center gap-2">
              <label className="text-sm font-medium text-gray-700">View:</label>
              <select
                value={viewMode}
                onChange={(e) => setViewMode(e.target.value as 'individual' | 'aggregate')}
                className="border border-gray-300 rounded px-3 py-1.5 text-sm bg-white text-gray-900"
              >
                <option value="individual">Individual Drafts</option>
                <option value="aggregate">Aggregate Ranking</option>
              </select>
            </div>
          )}
          <div className="text-sm text-gray-500 ml-auto">
            {drafts.length} draft{drafts.length !== 1 ? 's' : ''}
          </div>
        </div>
      </div>

      {/* Content - switch between different view modes */}
      {drafts.length === 0 ? (
        <div className="bg-white rounded-lg shadow p-8 text-center">
          <p className="text-gray-500">No drafts found.</p>
        </div>
      ) : ownerId ? (
        // Owner table view - show selected owner's draft performance
        <div>
          <div className="mb-4">
            <h2 className="text-2xl font-semibold text-gray-900">
              {selectedOwnerName}'s Draft Performance
            </h2>
            <p className="text-sm text-gray-500 mt-1">
              Sorted by grade (best to worst) • Click to expand
            </p>
          </div>
          <OwnerDraftsTable drafts={drafts} ownerName={selectedOwnerName} />
        </div>
      ) : viewMode === 'aggregate' ? (
        // Aggregate ranking view - rank all owners across all drafts
        <div>
          <div className="mb-4">
            <h2 className="text-2xl font-semibold text-gray-900">
              Cross-Draft Rankings
            </h2>
            <p className="text-sm text-gray-500 mt-1">
              All owners ranked by aggregate performance across {drafts.length} draft{drafts.length !== 1 ? 's' : ''} • Click to expand
            </p>
          </div>
          <CrossDraftRankingTable drafts={drafts} />
        </div>
      ) : (
        // Individual draft view - show all owners in each draft
        <div>
          <div className="mb-4">
            <h2 className="text-2xl font-semibold text-gray-900">
              Individual Draft Performance
            </h2>
            <p className="text-sm text-gray-500 mt-1">
              View each draft separately with all owners' performance • Click cards to expand
            </p>
          </div>
          {drafts.map((draft) => (
            <DraftCard key={draft.draft_id} draft={draft} />
          ))}
        </div>
      )}
    </div>
  );
}
