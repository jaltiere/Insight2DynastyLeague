import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../services/api';

// ─── Types ───────────────────────────────────────────────────────────────────

interface Owner {
  user_id: string;
  display_name: string;
  team_name: string;
  avatar: string | null;
  roster_id: number;
  classification: string | null;
  avg_age: number | null;
}

interface TradePlayer {
  player_id: string;
  full_name: string;
  position: string | null;
  team: string | null;
  age: number | null;
  status: string | null;
  injury_status: string | null;
  ktc_value: number;
  ktc_rank: number | null;
  league_ppg: number | null;
  league_ppg_delta_pct: number | null; // +12 = 12% above position avg
  on_taxi?: boolean;
}

interface H2HTradeAssets {
  players: { player_name: string; position: string | null }[];
  picks: { season: number; round: number; slot: number | null }[];
}

interface H2HTradeSide {
  owner_name: string;
  grade: string;
  value_share: number;
  total_value: number;
  assets_received: H2HTradeAssets | null;
}

interface H2HTrade {
  trade_id: string;
  season: number;
  week: number;
  anomaly: boolean;
  sides: Record<string, H2HTradeSide>;
}

// Classification → window label + color
const CLASSIFICATION_STYLE: Record<string, { label: string; color: string }> = {
  'Win Now':          { label: 'Win Now',          color: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200' },
  'Future Contender': { label: 'Future Contender', color: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200' },
  'Rebuilding':       { label: 'Rebuilding',        color: 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200' },
  'Retooling':        { label: 'Retooling',         color: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200' },
};

interface PickValue {
  pick_key: string;
  ktc_name: string;
  year: number;
  round: number;
  tier: 'early' | 'mid' | 'late';
  value: number;
  rank: number | null;
}

interface RosterPick extends PickValue {
  original_team: string;
  original_record: string;
  own_pick: boolean;
  estimated_pick_slot: number;
}

interface TradeSideAsset {
  type: 'player' | 'pick';
  id: string; // player_id or pick_key
  label: string;
  position: string | null;
  value: number;
}

// ─── Constants ───────────────────────────────────────────────────────────────

const POSITION_COLORS: Record<string, string> = {
  QB: 'bg-pink-500',
  RB: 'bg-green-500',
  WR: 'bg-blue-500',
  TE: 'bg-orange-500',
  K: 'bg-purple-500',
  DEF: 'bg-gray-500',
  RDP: 'bg-yellow-500',
};


// ─── Small helpers ────────────────────────────────────────────────────────────

function formatValue(v: number) {
  return v.toLocaleString();
}

function positionBadge(pos: string | null) {
  const color = POSITION_COLORS[pos ?? ''] ?? 'bg-gray-400';
  return (
    <span className={`${color} text-white text-xs font-bold px-1.5 py-0.5 rounded`}>
      {pos ?? '?'}
    </span>
  );
}

// ─── Player row in roster list ────────────────────────────────────────────────

function PpgDeltaBadge({ delta }: { delta: number | null }) {
  if (delta === null || delta === 0) return null;
  const positive = delta > 0;
  return (
    <span className={`text-xs font-bold px-1 rounded ${
      positive
        ? 'text-green-700 dark:text-green-400'
        : 'text-red-600 dark:text-red-400'
    }`}>
      {positive ? '+' : ''}{delta}%
    </span>
  );
}

function RosterPlayerRow({
  player,
  added,
  onToggle,
}: {
  player: TradePlayer;
  added: boolean;
  onToggle: () => void;
}) {
  return (
    <button
      onClick={onToggle}
      className={`w-full flex items-center justify-between px-3 py-2 rounded text-left transition
        ${added
          ? 'bg-blue-100 dark:bg-blue-900 border border-blue-400 dark:border-blue-600'
          : 'hover:bg-gray-100 dark:hover:bg-gray-700'
        }`}
    >
      <div className="flex items-center gap-2 min-w-0">
        {positionBadge(player.position)}
        <span className="text-sm font-medium text-gray-900 truncate">{player.full_name}</span>
        {player.team && (
          <span className="text-xs text-gray-500 dark:text-gray-400 hidden sm:inline">{player.team}</span>
        )}
        {player.injury_status && (
          <span className="text-xs text-red-500 font-semibold hidden sm:inline">{player.injury_status}</span>
        )}
        <PpgDeltaBadge delta={player.league_ppg_delta_pct} />
      </div>
      <div className="flex items-center gap-2 flex-shrink-0 ml-2">
        <span className="text-sm font-semibold text-gray-700 dark:text-gray-300">
          {formatValue(player.ktc_value)}
        </span>
        <span className={`text-xs font-bold ${added ? 'text-blue-600 dark:text-blue-300' : 'text-gray-400'}`}>
          {added ? '✓' : '+'}
        </span>
      </div>
    </button>
  );
}

// ─── Pick selector ────────────────────────────────────────────────────────────

function PickSelector({
  rosterPicks,
  allPicks,
  addedKeys,
  onAdd,
}: {
  rosterPicks: RosterPick[] | null; // null = no owner selected, show all picks
  allPicks: PickValue[];
  addedKeys: Set<string>;
  onAdd: (pick: PickValue) => void;
}) {
  // When owner is selected, show only their picks. Otherwise show full list.
  const picksToShow: PickValue[] = rosterPicks ?? allPicks ?? [];
  const isRosterMode = rosterPicks !== null;

  const byYear = useMemo(() => {
    const map: Record<number, PickValue[]> = {};
    for (const p of picksToShow) {
      if (!map[p.year]) map[p.year] = [];
      map[p.year].push(p);
    }
    return map;
  }, [picksToShow]);

  const years = Object.keys(byYear).map(Number).sort((a, b) => a - b);

  if (picksToShow.length === 0) {
    return <p className="text-sm text-gray-400 px-1 py-2">No picks found for this team.</p>;
  }

  return (
    <div className="space-y-2">
      {isRosterMode && (
        <p className="text-xs text-gray-500 dark:text-gray-400 px-1">
          Tier estimated from current standings. Slot shown is projected draft position.
        </p>
      )}
      {years.map((year) => (
        <div key={year}>
          <div className="text-xs font-bold text-gray-500 dark:text-gray-400 uppercase mb-1 px-1">
            {year}
          </div>
          <div className="space-y-1">
            {(byYear[year] ?? []).map((pick) => {
              const added = addedKeys.has(pick.pick_key);
              const rp = pick as RosterPick;
              const isOwn = isRosterMode && rp.own_pick;
              return (
                <button
                  key={`${pick.pick_key}-${isRosterMode ? (rp.original_team ?? '') : ''}`}
                  onClick={() => !added && onAdd(pick)}
                  disabled={added}
                  className={`w-full flex items-center justify-between px-3 py-2 rounded text-left transition
                    ${added
                      ? 'bg-blue-100 dark:bg-blue-900 border border-blue-400 dark:border-blue-600 opacity-60'
                      : 'hover:bg-gray-100 dark:hover:bg-gray-700 cursor-pointer'
                    }`}
                >
                  <div className="flex items-center gap-2 min-w-0">
                    {positionBadge('RDP')}
                    <div className="min-w-0">
                      <div className="text-sm font-medium text-gray-900 truncate">
                        {pick.ktc_name}
                      </div>
                      {isRosterMode && !isOwn && (
                        <div className="text-xs text-gray-400 truncate">
                          via {rp.original_team} ({rp.original_record}) · slot ~{rp.estimated_pick_slot}
                        </div>
                      )}
                      {isRosterMode && isOwn && (
                        <div className="text-xs text-gray-400">
                          own pick · slot ~{rp.estimated_pick_slot}
                        </div>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0 ml-2">
                    <span className="text-sm font-semibold text-gray-700 dark:text-gray-300">
                      {formatValue(pick.value)}
                    </span>
                    <span className={`text-xs font-bold ${added ? 'text-blue-600' : 'text-gray-400'}`}>
                      {added ? '✓' : '+'}
                    </span>
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}

// ─── Trade side panel ─────────────────────────────────────────────────────────

type SideTab = 'roster' | 'picks';

function TradeSidePanel({
  label,
  owners,
  selectedOwnerId,
  onOwnerChange,
  rosterData,
  rosterLoading,
  rosterPicks,
  rosterPicksLoading,
  allPicks,
  assets,
  receivingClassification,
  onTogglePlayer,
  onAddPick,
  onRemoveAsset,
}: {
  label: string;
  owners: Owner[];
  selectedOwnerId: string | null;
  onOwnerChange: (id: string | null) => void;
  rosterData: { players: TradePlayer[] } | null;
  rosterLoading: boolean;
  rosterPicks: RosterPick[] | null;
  rosterPicksLoading: boolean;
  allPicks: PickValue[];
  assets: TradeSideAsset[];
  receivingClassification: string | null; // classification of the team receiving these assets
  onTogglePlayer: (player: TradePlayer) => void;
  onAddPick: (pick: PickValue) => void;
  onRemoveAsset: (id: string) => void;
}) {
  const [tab, setTab] = useState<SideTab>('roster');
  const [rosterFilter, setRosterFilter] = useState('');

  function fitBadge(asset: TradeSideAsset): string | null {
    if (!receivingClassification) return null;
    // Pick = future value → good for rebuilders, questionable for win-now
    if (asset.type === 'pick') {
      if (receivingClassification === 'Win Now') return '⚠ win-now team';
      if (receivingClassification === 'Rebuilding' || receivingClassification === 'Future Contender') return '✓ fits window';
      return null;
    }
    // Player: need age from roster data
    const rosterPlayer = (rosterData?.players ?? []).find(p => p.player_id === asset.id);
    // If we don't have the player in THIS team's roster, check both panels via position/name
    const age = rosterPlayer?.age ?? null;
    if (!age) return null;
    const isVeteran = age >= 28;
    const isYoung = age <= 24;
    if (receivingClassification === 'Win Now' && isVeteran) return '✓ fits window';
    if (receivingClassification === 'Win Now' && isYoung) return '⚠ long-term fit';
    if ((receivingClassification === 'Rebuilding' || receivingClassification === 'Future Contender') && isYoung) return '✓ fits window';
    if ((receivingClassification === 'Rebuilding' || receivingClassification === 'Future Contender') && isVeteran) return '⚠ aging out';
    return null;
  }

  const addedPlayerIds = useMemo(
    () => new Set(assets.filter((a) => a.type === 'player').map((a) => a.id)),
    [assets],
  );
  const addedPickKeys = useMemo(
    () => new Set(assets.filter((a) => a.type === 'pick').map((a) => a.id)),
    [assets],
  );

  const totalValue = assets.reduce((s, a) => s + a.value, 0);

  const filteredRoster = useMemo(() => {
    if (!rosterData?.players) return [];
    const f = rosterFilter.toLowerCase();
    if (!f) return rosterData.players;
    return rosterData.players.filter(
      (p) =>
        p.full_name.toLowerCase().includes(f) ||
        (p.position ?? '').toLowerCase().includes(f) ||
        (p.team ?? '').toLowerCase().includes(f),
    );
  }, [rosterData, rosterFilter]);

  return (
    <div className="flex flex-col gap-3">
      {/* Owner selector */}
      <div>
        <label className="block text-xs font-bold text-gray-500 dark:text-gray-400 uppercase mb-1">
          {label}
        </label>
        <select
          value={selectedOwnerId ?? ''}
          onChange={(e) => onOwnerChange(e.target.value || null)}
          className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-800 text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="">— Select an owner —</option>
          {owners.map((o) => (
            <option key={o.user_id} value={o.user_id}>
              {o.display_name} · {o.team_name}{o.classification ? ` (${o.classification})` : ''}
            </option>
          ))}
        </select>
        {/* Classification badge for selected owner */}
        {selectedOwnerId && (() => {
          const owner = owners.find(o => o.user_id === selectedOwnerId);
          const style = owner?.classification ? CLASSIFICATION_STYLE[owner.classification] : null;
          return style ? (
            <span className={`inline-block mt-1.5 text-xs font-semibold px-2 py-0.5 rounded-full ${style.color}`}>
              {style.label}{owner?.avg_age ? ` · avg age ${owner.avg_age}` : ''}
            </span>
          ) : null;
        })()}
      </div>

      {/* Assets in trade */}
      {assets.length > 0 && (
        <div className="bg-blue-50 dark:bg-blue-950 rounded-lg p-3 space-y-1.5">
          <div className="text-xs font-bold text-blue-700 dark:text-blue-300 uppercase mb-1">
            Sending
          </div>
          {assets.map((a) => {
            const fit = fitBadge(a);
            return (
              <div key={a.id} className="text-sm">
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2 min-w-0">
                    {positionBadge(a.position)}
                    <span className="text-gray-900 truncate">{a.label}</span>
                  </div>
                  <div className="flex items-center gap-2 flex-shrink-0">
                    <span className="font-semibold text-gray-700 dark:text-gray-300">
                      {formatValue(a.value)}
                    </span>
                    <button
                      onClick={() => onRemoveAsset(a.id)}
                      className="text-red-400 hover:text-red-600 font-bold text-base leading-none"
                      aria-label="Remove"
                    >
                      ×
                    </button>
                  </div>
                </div>
                {fit && (
                  <span className={`text-xs ml-7 ${fit.startsWith('✓') ? 'text-green-600 dark:text-green-400' : 'text-amber-600 dark:text-amber-400'}`}>
                    {fit}
                  </span>
                )}
              </div>
            );
          })}
          <div className="border-t border-blue-200 dark:border-blue-800 pt-1.5 flex justify-between font-bold text-sm text-blue-800 dark:text-blue-200">
            <span>Total</span>
            <span>{formatValue(totalValue)}</span>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="flex border-b border-gray-200 dark:border-gray-700 text-sm">
        {(['roster', 'picks'] as SideTab[]).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-3 py-2 font-semibold capitalize transition border-b-2 -mb-px
              ${tab === t
                ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                : 'border-transparent text-gray-500 hover:text-gray-700 dark:hover:text-gray-300'
              }`}
          >
            {t === 'roster' ? 'Roster' : 'Picks'}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="max-h-[480px] overflow-y-auto space-y-1 pr-1">
        {tab === 'roster' && (
          <>
            {!selectedOwnerId && (
              <p className="text-sm text-gray-400 px-1 py-2">Select an owner above to browse their roster.</p>
            )}
            {selectedOwnerId && rosterLoading && (
              <p className="text-sm text-gray-400 px-1 py-4 text-center">Loading roster…</p>
            )}
            {selectedOwnerId && !rosterLoading && rosterData && (
              <>
                <input
                  type="text"
                  value={rosterFilter}
                  onChange={(e) => setRosterFilter(e.target.value)}
                  placeholder="Filter roster…"
                  className="w-full px-3 py-1.5 text-sm border border-gray-200 dark:border-gray-600 rounded bg-white dark:bg-gray-800 text-gray-900 placeholder-gray-400 focus:outline-none mb-1"
                />
                <p className="text-xs text-gray-400 dark:text-gray-500 px-1 mb-2">
                  <span className="text-green-600 dark:text-green-400 font-bold">+%</span>
                  {' / '}
                  <span className="text-red-500 dark:text-red-400 font-bold">−%</span>
                  {' '}= how far above/below position avg this player scores in your league
                </p>
                {filteredRoster.map((p) => (
                  <RosterPlayerRow
                    key={p.player_id}
                    player={p}
                    added={addedPlayerIds.has(p.player_id)}
                    onToggle={() => onTogglePlayer(p)}
                  />
                ))}
              </>
            )}
          </>
        )}


        {tab === 'picks' && (
          rosterPicksLoading
            ? <p className="text-sm text-gray-400 px-1 py-4 text-center">Loading picks…</p>
            : <PickSelector
                rosterPicks={selectedOwnerId ? (rosterPicks ?? []) : null}
                allPicks={allPicks}
                addedKeys={addedPickKeys}
                onAdd={onAddPick}
              />
        )}
      </div>
    </div>
  );
}

// ─── Fairness suggestion ──────────────────────────────────────────────────────

function FairnessSuggestion({
  gap,
  losingRoster,
  losingOwnerLabel,
  picks,
  assetIds,
}: {
  gap: number;
  losingRoster: TradePlayer[];
  losingOwnerLabel: string;
  picks: PickValue[];
  assetIds: Set<string>;
}) {
  const suggestions = useMemo(() => {
    if (gap <= 0) return [];
    const results: Array<{ label: string; value: number; position: string | null; residual: number }> = [];

    // Suggest players not already in the trade
    for (const p of losingRoster) {
      if (assetIds.has(p.player_id) || p.ktc_value === 0) continue;
      results.push({
        label: p.full_name,
        value: p.ktc_value,
        position: p.position,
        residual: Math.abs(gap - p.ktc_value),
      });
    }

    // Suggest picks not already in the trade
    for (const pick of picks) {
      if (assetIds.has(pick.pick_key) || pick.value === 0) continue;
      results.push({
        label: pick.ktc_name,
        value: pick.value,
        position: 'RDP',
        residual: Math.abs(gap - pick.value),
      });
    }

    return results.sort((a, b) => a.residual - b.residual).slice(0, 4);
  }, [gap, losingRoster, picks, assetIds]);

  return (
    <div className="bg-amber-50 dark:bg-amber-950 border border-amber-200 dark:border-amber-800 rounded-lg p-4">
      <div className="text-sm font-bold text-amber-800 dark:text-amber-300 mb-2">
        For <span className="italic">{losingOwnerLabel}</span> to sweeten this deal, they could add:
      </div>
      {suggestions.length === 0 ? (
        <p className="text-sm text-amber-700 dark:text-amber-400 italic">
          No single asset on {losingOwnerLabel}'s roster closes this gap — a package deal or restructured trade may be needed.
        </p>
      ) : (
        <div className="space-y-1.5">
          {suggestions.map((s) => (
            <div key={s.label} className="flex items-center justify-between text-sm">
              <div className="flex items-center gap-2">
                {positionBadge(s.position)}
                <span className="text-gray-800 dark:text-gray-200">{s.label}</span>
                <span className="text-gray-500 dark:text-gray-400">({formatValue(s.value)})</span>
              </div>
              <span className={`text-xs font-semibold ${s.residual < 300 ? 'text-green-600 dark:text-green-400' : 'text-gray-500'}`}>
                {s.residual < 300
                  ? '≈ fair'
                  : `gap: ${formatValue(s.residual)}`}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ─── H2H expandable trade list ───────────────────────────────────────────────

function H2HTradeList({
  trades,
  sideAId,
  sideBId,
}: {
  trades: H2HTrade[];
  sideAId: string;
  sideBId: string;
}) {
  const [expandedId, setExpandedId] = useState<string | null>(null);

  return (
    <div className="space-y-1">
      {trades.map((trade) => {
        const sideA = trade.sides[sideAId];
        const sideB = trade.sides[sideBId];
        if (!sideA || !sideB) return null;
        const aWon = (sideA.value_share ?? 0) > (sideB.value_share ?? 0);
        const bWon = (sideB.value_share ?? 0) > (sideA.value_share ?? 0);
        const expanded = expandedId === trade.trade_id;

        return (
          <div key={trade.trade_id} className="border border-gray-100 dark:border-gray-700 rounded-lg overflow-hidden">
            {/* Summary row — clickable */}
            <button
              className="w-full flex items-center gap-3 text-sm px-3 py-2 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition text-left"
              onClick={() => setExpandedId(expanded ? null : trade.trade_id)}
            >
              <span className="text-xs text-gray-400 w-16 flex-shrink-0">{trade.season} Wk{trade.week}</span>
              <div className="flex items-center gap-2 flex-1 justify-between">
                <span className={`font-semibold ${aWon ? 'text-blue-600 dark:text-blue-400' : 'text-gray-500'}`}>
                  {sideA.owner_name} {!trade.anomaly && sideA.grade ? `(${sideA.grade})` : ''}
                </span>
                <span className="text-gray-300 dark:text-gray-600">vs</span>
                <span className={`font-semibold ${bWon ? 'text-rose-600 dark:text-rose-400' : 'text-gray-500'}`}>
                  {sideB.owner_name} {!trade.anomaly && sideB.grade ? `(${sideB.grade})` : ''}
                </span>
              </div>
              {trade.anomaly && <span className="text-xs text-gray-400 italic">ungraded</span>}
              <svg
                className={`w-3 h-3 text-gray-400 flex-shrink-0 transition-transform ${expanded ? 'rotate-180' : ''}`}
                fill="currentColor" viewBox="0 0 20 20"
              >
                <path fillRule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clipRule="evenodd" />
              </svg>
            </button>

            {/* Expanded detail */}
            {expanded && (
              <div className="grid grid-cols-2 gap-px bg-gray-100 dark:bg-gray-700 border-t border-gray-100 dark:border-gray-700">
                {[
                  { side: sideA, color: 'text-blue-600 dark:text-blue-400' },
                  { side: sideB, color: 'text-rose-600 dark:text-rose-400' },
                ].map(({ side, color }) => (
                  <div key={side.owner_name} className="bg-white dark:bg-gray-800 px-3 py-2">
                    <p className={`text-xs font-bold mb-1 ${color}`}>{side.owner_name} received</p>
                    {(!side.assets_received ||
                      (side.assets_received.players.length === 0 && side.assets_received.picks.length === 0)) ? (
                      <p className="text-xs text-gray-400 italic">No assets recorded</p>
                    ) : (
                      <ul className="space-y-0.5">
                        {side.assets_received.players.map((p, i) => (
                          <li key={i} className="flex items-center gap-1.5 text-xs text-gray-700 dark:text-gray-200">
                            {positionBadge(p.position)}
                            <span>{p.player_name}</span>
                          </li>
                        ))}
                        {side.assets_received.picks.map((p, i) => (
                          <li key={i} className="flex items-center gap-1.5 text-xs text-gray-700 dark:text-gray-200">
                            {positionBadge('RDP')}
                            <span>
                              {p.season} Rd{p.round}
                              {p.slot ? ` (pick ${p.slot})` : ''}
                            </span>
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────

export default function TradeCalculator() {
  const [sideAOwnerId, setSideAOwnerId] = useState<string | null>(null);
  const [sideBOwnerId, setSideBOwnerId] = useState<string | null>(null);
  const [sideAAssets, setSideAAssets] = useState<TradeSideAsset[]>([]);
  const [sideBAssets, setSideBAssets] = useState<TradeSideAsset[]>([]);

  // ── Data fetching ──────────────────────────────────────────────────────────

  const { data: ownersData } = useQuery({
    queryKey: ['tradeCalcOwners'],
    queryFn: api.getTradeCalcOwners,
    staleTime: 5 * 60_000,
  });

  const { data: rosterA, isLoading: rosterALoading } = useQuery({
    queryKey: ['tradeCalcRoster', sideAOwnerId],
    queryFn: () => api.getTradeCalcRoster(sideAOwnerId!),
    enabled: !!sideAOwnerId,
    staleTime: 5 * 60_000,
  });

  const { data: rosterB, isLoading: rosterBLoading } = useQuery({
    queryKey: ['tradeCalcRoster', sideBOwnerId],
    queryFn: () => api.getTradeCalcRoster(sideBOwnerId!),
    enabled: !!sideBOwnerId,
    staleTime: 5 * 60_000,
  });

  const { data: rosterPicksAData, isLoading: rosterPicksALoading } = useQuery({
    queryKey: ['tradeCalcRosterPicks', sideAOwnerId],
    queryFn: () => api.getTradeCalcRosterPicks(sideAOwnerId!),
    enabled: !!sideAOwnerId,
    staleTime: 5 * 60_000,
  });

  const { data: rosterPicksBData, isLoading: rosterPicksBLoading } = useQuery({
    queryKey: ['tradeCalcRosterPicks', sideBOwnerId],
    queryFn: () => api.getTradeCalcRosterPicks(sideBOwnerId!),
    enabled: !!sideBOwnerId,
    staleTime: 5 * 60_000,
  });

  const rosterPicksA: RosterPick[] | null = sideAOwnerId ? (rosterPicksAData?.picks ?? null) : null;
  const rosterPicksB: RosterPick[] | null = sideBOwnerId ? (rosterPicksBData?.picks ?? null) : null;

  const { data: picksData } = useQuery({
    queryKey: ['tradeCalcPicks'],
    queryFn: api.getPickValues,
    staleTime: 60 * 60_000,
  });

  const { data: h2hData, isLoading: h2hLoading } = useQuery({
    queryKey: ['tradeCalcH2H', sideAOwnerId, sideBOwnerId],
    queryFn: () => api.getH2HTrades(sideAOwnerId!, sideBOwnerId!),
    enabled: !!sideAOwnerId && !!sideBOwnerId,
    staleTime: 10 * 60_000,
  });

  const owners: Owner[] = ownersData?.owners ?? [];
  const picks: PickValue[] = picksData?.picks ?? [];

  // Classification for each side (used for fit badges — note: side A receives from B, so fit = A's classification)
  const ownerA = owners.find(o => o.user_id === sideAOwnerId);
  const ownerB = owners.find(o => o.user_id === sideBOwnerId);
  // Assets received by A are judged against A's window; assets received by B against B's window
  const classificationA = ownerA?.classification ?? null;
  const classificationB = ownerB?.classification ?? null;

  // ── Asset management ───────────────────────────────────────────────────────

  function togglePlayerA(player: TradePlayer) {
    setSideAAssets((prev) => {
      const exists = prev.find((a) => a.id === player.player_id);
      if (exists) return prev.filter((a) => a.id !== player.player_id);
      return [...prev, { type: 'player', id: player.player_id, label: player.full_name, position: player.position, value: player.ktc_value }];
    });
  }

  function togglePlayerB(player: TradePlayer) {
    setSideBAssets((prev) => {
      const exists = prev.find((a) => a.id === player.player_id);
      if (exists) return prev.filter((a) => a.id !== player.player_id);
      return [...prev, { type: 'player', id: player.player_id, label: player.full_name, position: player.position, value: player.ktc_value }];
    });
  }

  function addPickA(pick: PickValue) {
    setSideAAssets((prev) => {
      if (prev.find((a) => a.id === pick.pick_key)) return prev;
      return [...prev, { type: 'pick', id: pick.pick_key, label: pick.ktc_name, position: 'RDP', value: pick.value }];
    });
  }

  function addPickB(pick: PickValue) {
    setSideBAssets((prev) => {
      if (prev.find((a) => a.id === pick.pick_key)) return prev;
      return [...prev, { type: 'pick', id: pick.pick_key, label: pick.ktc_name, position: 'RDP', value: pick.value }];
    });
  }

  // ── Value math ─────────────────────────────────────────────────────────────

  const totalA = sideAAssets.reduce((s, a) => s + a.value, 0);
  const totalB = sideBAssets.reduce((s, a) => s + a.value, 0);
  const grandTotal = totalA + totalB;
  const hasAssets = grandTotal > 0;

  const shareA = grandTotal > 0 ? totalA / grandTotal : 0.5;
  const shareB = grandTotal > 0 ? totalB / grandTotal : 0.5;

  const FAIR_ZONE = 0.06; // ±6% from 50% is considered fair
  const isFair = Math.abs(shareA - 0.5) <= FAIR_ZONE;
  const winner = isFair ? 'even' : totalA > totalB ? 'A' : 'B';
  const gap = Math.abs(totalA - totalB);
  const gapPct = grandTotal > 0 ? Math.round((gap / grandTotal) * 100) : 0;

  // Losing side's roster (for suggestions)
  const losingRoster: TradePlayer[] =
    winner === 'A' ? (rosterB?.players ?? []) :
    winner === 'B' ? (rosterA?.players ?? []) : [];

  const losingAssetIds = useMemo(() => {
    const ids = new Set<string>();
    (winner === 'A' ? sideBAssets : sideAAssets).forEach((a) => ids.add(a.id));
    return ids;
  }, [winner, sideAAssets, sideBAssets]);

  // Owner labels for the verdict
  const ownerALabel = owners.find((o) => o.user_id === sideAOwnerId)?.display_name ?? 'Side A';
  const ownerBLabel = owners.find((o) => o.user_id === sideBOwnerId)?.display_name ?? 'Side B';

  return (
    <div className="container mx-auto px-4 py-6 max-w-6xl">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl md:text-3xl font-bold text-gray-900">Trade Calculator</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
          Values powered by KeepTradeCut dynasty rankings (1QB).
        </p>
      </div>

      {/* Two-column side panels */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
        {/* Side A */}
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow p-4 border border-gray-200 dark:border-gray-700">
          <TradeSidePanel
            label="Side A receives"
            owners={owners}
            selectedOwnerId={sideAOwnerId}
            onOwnerChange={setSideAOwnerId}
            rosterData={rosterA ?? null}
            rosterLoading={rosterALoading}
            rosterPicks={rosterPicksA}
            rosterPicksLoading={rosterPicksALoading}
            allPicks={picks}
            assets={sideAAssets}
            receivingClassification={classificationA}
            onTogglePlayer={togglePlayerA}
            onAddPick={addPickA}
            onRemoveAsset={(id) => setSideAAssets((prev) => prev.filter((a) => a.id !== id))}
          />
        </div>

        {/* Side B */}
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow p-4 border border-gray-200 dark:border-gray-700">
          <TradeSidePanel
            label="Side B receives"
            owners={owners}
            selectedOwnerId={sideBOwnerId}
            onOwnerChange={setSideBOwnerId}
            rosterData={rosterB ?? null}
            rosterLoading={rosterBLoading}
            rosterPicks={rosterPicksB}
            rosterPicksLoading={rosterPicksBLoading}
            allPicks={picks}
            assets={sideBAssets}
            receivingClassification={classificationB}
            onTogglePlayer={togglePlayerB}
            onAddPick={addPickB}
            onRemoveAsset={(id) => setSideBAssets((prev) => prev.filter((a) => a.id !== id))}
          />
        </div>
      </div>

      {/* Result card */}
      {hasAssets && (
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow border border-gray-200 dark:border-gray-700 p-5 space-y-4">
          {/* Bar */}
          <div>
            <div className="flex justify-between text-xs text-gray-500 dark:text-gray-400 mb-1">
              <span>{ownerALabel}</span>
              <span>{ownerBLabel}</span>
            </div>

            {/* Bar: pure blue/rose fill + white center line */}
            <div className="relative h-5 rounded-full overflow-hidden">
              <div
                className="absolute inset-y-0 left-0 bg-blue-500 transition-all duration-300"
                style={{ width: `${shareA * 100}%` }}
              />
              <div
                className="absolute inset-y-0 right-0 bg-rose-500 transition-all duration-300"
                style={{ width: `${shareB * 100}%` }}
              />
              {/* 50% center line */}
              <div
                className="absolute inset-y-0 w-px bg-white opacity-70"
                style={{ left: 'calc(50% - 0.5px)' }}
              />
            </div>

            {/* Fair zone bracket below the bar */}
            <div className="relative mt-1" style={{ height: '20px' }}>
              {/* Horizontal bracket line */}
              <div
                className="absolute bg-green-500 dark:bg-green-400"
                style={{ left: '44%', width: '12%', top: '6px', height: '2px' }}
              />
              {/* Left tick */}
              <div
                className="absolute bg-green-500 dark:bg-green-400"
                style={{ left: '44%', top: '0px', width: '2px', height: '8px' }}
              />
              {/* Right tick */}
              <div
                className="absolute bg-green-500 dark:bg-green-400"
                style={{ left: 'calc(56% - 2px)', top: '0px', width: '2px', height: '8px' }}
              />
              {/* Label */}
              <span
                className="absolute text-xs font-semibold text-green-600 dark:text-green-400 whitespace-nowrap"
                style={{ left: '50%', transform: 'translateX(-50%)', top: '9px' }}
              >
                fair zone
              </span>
            </div>

            <div className="flex justify-between text-sm font-bold mt-1">
              <span className="text-blue-600 dark:text-blue-400">{formatValue(totalA)}</span>
              <span className="text-rose-600 dark:text-rose-400">{formatValue(totalB)}</span>
            </div>
          </div>

          {/* Verdict */}
          {winner === 'even' ? (
            <div className="text-center font-bold text-green-600 dark:text-green-400 text-lg">
              ✓ Fair trade
            </div>
          ) : (
            <div className="text-center">
              <span className="font-bold text-gray-900 dark:text-gray-100">
                {winner === 'A' ? ownerALabel : ownerBLabel}
              </span>{' '}
              <span className="text-gray-600 dark:text-gray-400">wins by</span>{' '}
              <span className="font-bold text-gray-900 dark:text-gray-100">
                {formatValue(gap)}
              </span>{' '}
              <span className="text-gray-500">({gapPct}%)</span>
            </div>
          )}

          {/* Fairness suggestion */}
          {winner !== 'even' && (
            <FairnessSuggestion
              gap={gap}
              losingRoster={losingRoster}
              losingOwnerLabel={winner === 'A' ? ownerBLabel : ownerALabel}
              picks={winner === 'A' ? (rosterPicksB ?? []) : (rosterPicksA ?? [])}
              assetIds={losingAssetIds}
            />
          )}

          {/* Reset */}
          <div className="text-center pt-1">
            <button
              onClick={() => { setSideAAssets([]); setSideBAssets([]); }}
              className="text-sm text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 underline"
            >
              Clear all
            </button>
          </div>
        </div>
      )}

      {!hasAssets && (
        <div className="text-center py-12 text-gray-400 dark:text-gray-500">
          <div className="text-4xl mb-3">⇄</div>
          <p className="text-sm">Select an owner on each side, then click players or picks to add them to the trade.</p>
        </div>
      )}

      {/* H2H Trade History — shown whenever both owners are selected */}
      {sideAOwnerId && sideBOwnerId && (
        <div className="mt-4 bg-white dark:bg-gray-800 rounded-xl shadow border border-gray-200 dark:border-gray-700 p-5">
          <h2 className="text-base font-bold text-gray-900 mb-3">
            Trade History Between These Teams
          </h2>
          {h2hLoading && (
            <p className="text-sm text-gray-400">Loading…</p>
          )}
          {!h2hLoading && h2hData && h2hData.trades.length === 0 && (
            <p className="text-sm text-gray-400">No trades between these two teams.</p>
          )}
          {!h2hLoading && h2hData && h2hData.summary && h2hData.trades.length > 0 && (() => {
            const s = h2hData.summary;
            const sA = s[sideAOwnerId];
            const sB = s[sideBOwnerId];
            const totalTrades = s.total_trades;
            return (
              <div className="space-y-4">
                {/* Summary row */}
                <div className="grid grid-cols-3 gap-3 text-center">
                  <div className="bg-blue-50 dark:bg-blue-950 rounded-lg p-3">
                    <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">{ownerALabel}</div>
                    <div className="text-xl font-bold text-blue-600 dark:text-blue-400">{sA?.wins ?? 0}W</div>
                    {sA?.typical_grade && (
                      <div className="text-xs text-gray-500 mt-1">typical grade <span className="font-bold text-gray-700 dark:text-gray-300">{sA.typical_grade}</span></div>
                    )}
                  </div>
                  <div className="flex items-center justify-center">
                    <div className="text-center">
                      <div className="text-2xl font-bold text-gray-400">{totalTrades}</div>
                      <div className="text-xs text-gray-400">trades</div>
                    </div>
                  </div>
                  <div className="bg-rose-50 dark:bg-rose-950 rounded-lg p-3">
                    <div className="text-xs text-gray-500 dark:text-gray-400 mb-1">{ownerBLabel}</div>
                    <div className="text-xl font-bold text-rose-600 dark:text-rose-400">{sB?.wins ?? 0}W</div>
                    {sB?.typical_grade && (
                      <div className="text-xs text-gray-500 mt-1">typical grade <span className="font-bold text-gray-700 dark:text-gray-300">{sB.typical_grade}</span></div>
                    )}
                  </div>
                </div>

                {/* Individual trades */}
                <H2HTradeList trades={h2hData.trades} sideAId={sideAOwnerId} sideBId={sideBOwnerId} />
              </div>
            );
          })()}
        </div>
      )}
    </div>
  );
}
