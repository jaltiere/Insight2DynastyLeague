import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../services/api';

interface DraftSummary {
  draft_id: string;
  year: number;
  type: string;
  status: string;
  rounds: number;
}

interface DraftListData {
  total_drafts: number;
  drafts: DraftSummary[];
}

interface SlotOwner {
  user_id: string | null;
  display_name: string;
  avatar: string | null;
}

interface DraftPick {
  pick_no: number;
  round: number;
  pick_in_round: number;
  roster_id: number;
  player_id: string | null;
  player_name?: string;
  position?: string;
  team?: string;
  owner_user_id?: string;
  owner_display_name?: string;
}

interface DraftDetail {
  draft_id: string;
  year: number;
  type: string;
  status: string;
  rounds: number;
  draft_order: Record<string, number>;
  slot_owners: Record<string, SlotOwner>;
  total_picks: number;
  picks: DraftPick[];
}

function getPositionColor(position?: string): string {
  switch (position) {
    case 'QB':
      return 'bg-pink-200 border-pink-300 dark:bg-pink-900/40 dark:border-pink-700 dark:text-pink-100';
    case 'RB':
      return 'bg-sky-200 border-sky-300 dark:bg-sky-900/40 dark:border-sky-700 dark:text-sky-100';
    case 'WR':
    case 'DB':
      return 'bg-orange-200 border-orange-300 dark:bg-orange-900/40 dark:border-orange-700 dark:text-orange-100';
    case 'TE':
      return 'bg-yellow-200 border-yellow-300 dark:bg-yellow-900/40 dark:border-yellow-700 dark:text-yellow-100';
    case 'DEF':
      return 'bg-amber-800 border-amber-900 text-white';
    default:
      return 'bg-gray-100 border-gray-200';
  }
}

function avatarUrl(avatarId: string | null): string | null {
  if (!avatarId) return null;
  return `https://sleepercdn.com/avatars/thumbs/${avatarId}`;
}

export default function Drafts() {
  const [selectedYear, setSelectedYear] = useState<number | null>(null);

  const { data: draftList, isLoading: listLoading, error: listError } = useQuery<DraftListData>({
    queryKey: ['drafts'],
    queryFn: api.getAllDrafts,
  });

  // Auto-select the most recent year once loaded
  const activeYear = selectedYear ?? draftList?.drafts[0]?.year ?? null;

  const { data: draftDetail, isLoading: detailLoading, error: detailError } = useQuery<DraftDetail>({
    queryKey: ['draftDetail', activeYear],
    queryFn: () => api.getDraftByYear(activeYear!),
    enabled: !!activeYear,
  });

  // Organize picks into a grid: [round][slot] -> pick
  const { slots, grid, slotOwnerMap } = useMemo(() => {
    if (!draftDetail) return { slots: [] as string[], grid: {} as Record<number, Record<number, DraftPick>>, slotOwnerMap: {} as Record<string, SlotOwner> };

    const draftOrder = draftDetail.draft_order || {};
    const apiSlotOwners = draftDetail.slot_owners || {};

    // Fall back to deriving slots from round 1 picks if draft_order is empty
    let slotKeys = Object.keys(draftOrder).sort((a, b) => Number(a) - Number(b));
    if (slotKeys.length === 0 && draftDetail.picks.length > 0) {
      const uniqueSlots = new Set(draftDetail.picks.map(p => String(p.pick_in_round)));
      slotKeys = Array.from(uniqueSlots).sort((a, b) => Number(a) - Number(b));
    }

    // Use API slot_owners (original draft slot owners from draft_order)
    const owners: Record<string, SlotOwner> = { ...apiSlotOwners };

    const pickGrid: Record<number, Record<number, DraftPick>> = {};
    for (const pick of draftDetail.picks) {
      if (!pickGrid[pick.round]) pickGrid[pick.round] = {};
      pickGrid[pick.round][pick.pick_in_round] = pick;
    }

    return { slots: slotKeys, grid: pickGrid, slotOwnerMap: owners };
  }, [draftDetail]);

  if (listLoading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <h1 className="text-4xl font-bold mb-6">Draft Results</h1>
        <div className="bg-white rounded-lg shadow p-6">
          <p className="text-gray-600">Loading drafts...</p>
        </div>
      </div>
    );
  }

  if (listError) {
    return (
      <div className="container mx-auto px-4 py-8">
        <h1 className="text-4xl font-bold mb-6">Draft Results</h1>
        <div className="bg-white rounded-lg shadow p-6">
          <p className="text-red-600">Error loading drafts: {(listError as Error).message}</p>
        </div>
      </div>
    );
  }

  if (!draftList || draftList.total_drafts === 0) {
    return (
      <div className="container mx-auto px-4 py-8">
        <h1 className="text-4xl font-bold mb-6">Draft Results</h1>
        <div className="bg-white rounded-lg shadow p-6">
          <p className="text-gray-600">No draft data available yet.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-4xl font-bold mb-6">Draft Results</h1>

      {/* Year selector */}
      <div className="flex flex-wrap gap-2 mb-6">
        {draftList.drafts.map((d) => (
          <button
            key={d.year}
            onClick={() => setSelectedYear(d.year)}
            className={`px-4 py-2 rounded-lg font-medium transition-colors ${
              activeYear === d.year
                ? 'bg-blue-600 dark:bg-blue-800 text-white'
                : 'bg-white text-gray-700 hover:bg-gray-100 shadow'
            }`}
          >
            {d.year}
          </button>
        ))}
      </div>

      {/* Draft board */}
      {detailLoading && (
        <div className="bg-white rounded-lg shadow p-6">
          <p className="text-gray-600">Loading draft board...</p>
        </div>
      )}

      {detailError && (
        <div className="bg-white rounded-lg shadow p-6">
          <p className="text-red-600">Error loading draft: {(detailError as Error).message}</p>
        </div>
      )}

      {draftDetail && !detailLoading && (
        <div className="bg-white rounded-lg shadow">
          <div className="bg-blue-600 dark:bg-blue-800 text-white px-6 py-3 rounded-t-lg flex items-center justify-between">
            <h2 className="text-xl font-semibold">{draftDetail.year} Draft</h2>
            <span className="text-sm opacity-80 capitalize">{draftDetail.type} - {draftDetail.rounds} rounds</span>
          </div>

          <div className="p-2">
            <table className="w-full border-collapse table-fixed">
              {/* Column headers - owner names + avatars */}
              <colgroup>
                <col className="w-8" />
                {slots.map((slot) => (
                  <col key={slot} />
                ))}
              </colgroup>
              <thead>
                <tr>
                  <th className="p-1 text-[10px] text-gray-500 font-medium">Rd</th>
                  {slots.map((slot) => {
                    const owner = slotOwnerMap[slot];
                    const avatar = avatarUrl(owner?.avatar);
                    return (
                      <th key={slot} className="p-1 text-center">
                        <div className="flex flex-col items-center gap-0.5">
                          {avatar ? (
                            <img
                              src={avatar}
                              alt={owner?.display_name}
                              className="w-7 h-7 rounded-full"
                            />
                          ) : (
                            <div className="w-7 h-7 rounded-full bg-gray-300 flex items-center justify-center text-gray-600 text-[10px] font-bold">
                              {owner?.display_name?.charAt(0)?.toUpperCase() || '?'}
                            </div>
                          )}
                          <span className="text-[10px] font-medium text-gray-700 truncate w-full">
                            {owner?.display_name || `Slot ${slot}`}
                          </span>
                        </div>
                      </th>
                    );
                  })}
                </tr>
              </thead>

              {/* Draft picks grid */}
              <tbody>
                {Array.from({ length: draftDetail.rounds }, (_, i) => i + 1).map((round) => (
                  <tr key={round}>
                    <td className="p-0.5 text-center text-[10px] font-bold text-gray-400 align-top pt-2">
                      {round}
                    </td>
                    {slots.map((slot) => {
                      const pick = grid[round]?.[Number(slot)];
                      if (!pick) {
                        return (
                          <td key={slot} className="p-0.5">
                            <div className="bg-gray-50 border border-gray-200 rounded p-1 h-full min-h-[48px]" />
                          </td>
                        );
                      }

                      const posColor = getPositionColor(pick.position);
                      const draftOrderMap = draftDetail.draft_order || {};
                      const originalRosterId = draftOrderMap[String(pick.pick_in_round)];
                      const isTraded = originalRosterId !== undefined && pick.roster_id !== originalRosterId;

                      return (
                        <td key={slot} className="p-0.5">
                          <div className={`${posColor} border rounded p-1 min-h-[48px]`}>
                            <div className="flex justify-between items-start">
                              <span className="font-semibold text-[11px] leading-tight truncate">
                                {pick.player_name || 'Unknown'}
                              </span>
                              <span className="text-[9px] opacity-60 ml-0.5 whitespace-nowrap">
                                {pick.round}.{pick.pick_in_round}
                              </span>
                            </div>
                            <div className="text-[10px] opacity-75">
                              {pick.position && pick.team
                                ? `${pick.position} - ${pick.team}`
                                : pick.position || ''}
                            </div>
                            {pick.owner_display_name && (
                              <div className={`mt-0.5 inline-flex items-center gap-0.5 rounded-sm px-1 py-px ${
                                isTraded ? 'bg-black/20 dark:bg-yellow-400/80 dark:text-black' : ''
                              }`}>
                                {isTraded && <span className="text-[8px] font-bold">&rarr;</span>}
                                <span className="text-[8px] font-semibold truncate">{pick.owner_display_name}</span>
                              </div>
                            )}
                          </div>
                        </td>
                      );
                    })}
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
