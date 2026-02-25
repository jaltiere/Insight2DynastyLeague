import { useState, useMemo, useEffect } from 'react';
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

const STATUS_COLORS: Record<string, string> = {
  complete: 'text-green-500 dark:text-green-400',
  failed: 'text-red-500',
};

function PositionBadge({ position }: { position: string | null }) {
  if (!position) return null;
  const bg = POSITION_COLORS[position] || 'bg-gray-400';
  return (
    <span className={`${bg} text-white text-xs font-bold px-2 py-1 rounded mr-2`}>
      {position}
    </span>
  );
}

function formatDate(ms: number | null): string {
  if (!ms) return '';
  return new Date(ms).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

type SortField = 'team' | 'waiver_adds' | 'free_agent_adds' | 'trades' | 'total';
type SortDir = 'asc' | 'desc';

interface SummaryEntry {
  user_id: string;
  username: string;
  team_name: string;
  waiver_adds: number;
  free_agent_adds: number;
  trades: number;
  total: number;
}

function SortArrow({ field, sortField, sortDir }: { field: SortField; sortField: SortField; sortDir: SortDir }) {
  if (field !== sortField) return null;
  return <span className="text-blue-600 dark:text-blue-400 ml-1">{sortDir === 'asc' ? '\u25B2' : '\u25BC'}</span>;
}

interface ModalProps {
  teamName: string;
  typeName: string;
  userId: string;
  type: string;
  onClose: () => void;
}

function TransactionModal({ teamName, typeName, userId, type, onClose }: ModalProps) {
  const { data, isLoading } = useQuery({
    queryKey: ['transactionsByOwner', userId, type],
    queryFn: () => api.getTransactionsByOwner(userId, type),
  });

  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [onClose]);

  const transactions = data?.transactions || [];

  return (
    <div
      className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[80vh] flex flex-col">
        <div className="bg-blue-600 dark:bg-blue-800 text-white px-6 py-4 rounded-t-lg flex items-center justify-between">
          <h2 className="text-lg font-semibold">{teamName} &mdash; {typeName}</h2>
          <button onClick={onClose} className="text-white hover:text-blue-200 text-2xl leading-none">&times;</button>
        </div>
        <div className="overflow-y-auto p-4 flex-1">
          {isLoading ? (
            <div className="flex justify-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 dark:border-blue-400"></div>
            </div>
          ) : transactions.length === 0 ? (
            <p className="text-gray-500 text-center py-8">No transactions found.</p>
          ) : (
            <div className="space-y-3">
              {transactions.map((txn: any) => {
                const typeLabel = txn.type === 'free_agent'
                  ? 'Free Agent'
                  : txn.type?.charAt(0).toUpperCase() + txn.type?.slice(1);

                const isTrade = txn.type === 'trade';

                return (
                  <div key={txn.id} className="border border-gray-200 rounded-lg p-3">
                    <div className="flex items-center justify-between mb-1">
                      <h3 className="text-sm font-bold text-gray-900">{typeLabel}</h3>
                      <span className={`text-xs font-medium ${STATUS_COLORS[txn.status] || 'text-gray-500'}`}>
                        {txn.status}
                      </span>
                    </div>
                    <div className="text-xs text-gray-500 mb-2">
                      <span>{txn.season} &middot; Week {txn.week}</span>
                      {txn.waiver_bid != null && <span className="ml-2">Bid: ${txn.waiver_bid}</span>}
                      {txn.status_updated && <span className="ml-2">{formatDate(txn.status_updated)}</span>}
                    </div>

                    {isTrade ? (
                      // Trade layout: show each team's side
                      <div className="space-y-2">
                        {txn.owners?.map((owner: any) => {
                          const rid = owner.roster_id;
                          const teamName = owner.team_name || owner.username;
                          const received = txn.adds?.filter((a: any) => a.roster_id === rid) || [];
                          const gave = txn.drops?.filter((d: any) => d.roster_id === rid) || [];
                          // previous_owner_id = who owned the pick before the trade
                          // owner_id = who owns the pick after the trade
                          const picksGot = txn.draft_picks?.filter(
                            (p: any) => p.owner_id === rid && p.previous_owner_id !== rid
                          ) || [];
                          const picksLost = txn.draft_picks?.filter(
                            (p: any) => p.previous_owner_id === rid && p.owner_id !== rid
                          ) || [];

                          const hasReceived = received.length > 0 || picksGot.length > 0;
                          const hasGave = gave.length > 0 || picksLost.length > 0;

                          if (!hasReceived && !hasGave) return null;

                          return (
                            <div key={rid} className="bg-gray-50 rounded p-2">
                              <div className="text-xs font-bold text-gray-800 mb-1">{teamName}</div>
                              {(received.length > 0 || picksGot.length > 0) && (
                                <div className="mb-1">
                                  <span className="text-xs font-semibold text-green-600 dark:text-green-400">Received:</span>
                                  {received.map((add: any) => (
                                    <div key={add.player_id} className="flex items-center mt-0.5 ml-2">
                                      <PositionBadge position={add.position} />
                                      <span className="text-xs text-gray-800">{add.player_name}</span>
                                    </div>
                                  ))}
                                  {picksGot.map((pick: any, idx: number) => (
                                    <div key={`pick-got-${idx}`} className="text-xs text-gray-800 mt-0.5 ml-2">
                                      {pick.season} Round {pick.round} pick
                                    </div>
                                  ))}
                                </div>
                              )}
                              {(gave.length > 0 || picksLost.length > 0) && (
                                <div>
                                  <span className="text-xs font-semibold text-red-600">Gave up:</span>
                                  {gave.map((drop: any) => (
                                    <div key={drop.player_id} className="flex items-center mt-0.5 ml-2">
                                      <PositionBadge position={drop.position} />
                                      <span className="text-xs text-gray-800">{drop.player_name}</span>
                                    </div>
                                  ))}
                                  {picksLost.map((pick: any, idx: number) => (
                                    <div key={`pick-lost-${idx}`} className="text-xs text-gray-800 mt-0.5 ml-2">
                                      {pick.season} Round {pick.round} pick
                                    </div>
                                  ))}
                                </div>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    ) : (
                      // Non-trade layout (waiver / free agent)
                      <>
                        {txn.owners?.length > 0 && (
                          <div className="text-xs font-medium text-gray-700 mb-1">
                            {txn.owners.map((o: any) => o.team_name || o.username).join(', ')}
                          </div>
                        )}
                        {txn.adds?.length > 0 && (
                          <div className="mb-1">
                            <span className="text-xs font-semibold text-green-600 dark:text-green-400">Add:</span>
                            {txn.adds.map((add: any) => (
                              <div key={add.player_id} className="flex items-center mt-0.5 ml-1">
                                <PositionBadge position={add.position} />
                                <span className="text-xs text-gray-800">{add.player_name}</span>
                              </div>
                            ))}
                          </div>
                        )}
                        {txn.drops?.length > 0 && (
                          <div className="mb-1">
                            <span className="text-xs font-semibold text-red-600">Drop:</span>
                            {txn.drops.map((drop: any) => (
                              <div key={drop.player_id} className="flex items-center mt-0.5 ml-1">
                                <PositionBadge position={drop.position} />
                                <span className="text-xs text-gray-800">{drop.player_name}</span>
                              </div>
                            ))}
                          </div>
                        )}
                      </>
                    )}

                    {txn.status === 'failed' && txn.metadata_notes && (
                      <p className="text-xs text-red-500 italic mt-1">{txn.metadata_notes}</p>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default function Transactions() {
  const [sortField, setSortField] = useState<SortField>('total');
  const [sortDir, setSortDir] = useState<SortDir>('desc');
  const [modal, setModal] = useState<{
    userId: string;
    teamName: string;
    type: string;
    typeName: string;
  } | null>(null);

  const { data: summaryData, isLoading, error } = useQuery({
    queryKey: ['transactionSummary'],
    queryFn: () => api.getTransactionSummary(),
  });

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDir(prev => (prev === 'desc' ? 'asc' : 'desc'));
    } else {
      setSortField(field);
      setSortDir('desc');
    }
  };

  const sortedSummary = useMemo(() => {
    const data: SummaryEntry[] = summaryData?.summary || [];
    return [...data].sort((a, b) => {
      let cmp: number;
      if (sortField === 'team') {
        const nameA = (a.team_name || a.username).toLowerCase();
        const nameB = (b.team_name || b.username).toLowerCase();
        cmp = nameA.localeCompare(nameB);
      } else {
        cmp = a[sortField] - b[sortField];
      }
      return sortDir === 'asc' ? cmp : -cmp;
    });
  }, [summaryData, sortField, sortDir]);

  const openModal = (entry: SummaryEntry, type: string, typeName: string) => {
    setModal({ userId: entry.user_id, teamName: entry.team_name || entry.username, type, typeName });
  };

  if (isLoading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="flex justify-center py-12">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 dark:border-blue-400"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="bg-red-50 border border-red-200 rounded-lg p-6 dark:bg-red-900/20 dark:border-red-800">
          <h2 className="text-red-800 text-lg font-semibold dark:text-red-400">Error loading transactions</h2>
          <p className="text-red-600 mt-2 dark:text-red-400">Please try refreshing the page.</p>
        </div>
      </div>
    );
  }

  const thClass = 'px-4 py-3 text-xs font-medium text-gray-500 uppercase cursor-pointer hover:bg-gray-100';

  return (
    <div className="container mx-auto px-4 py-8">
      <h1 className="text-4xl font-bold mb-6">Transactions</h1>

      {/* Summary table */}
      <div className="bg-white rounded-lg shadow">
        <div className="bg-blue-600 dark:bg-blue-800 text-white px-6 py-3 rounded-t-lg">
          <h2 className="text-xl font-semibold">
            Transaction Summary
          </h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50">
              <tr>
                <th onClick={() => handleSort('team')} className={`${thClass} text-left`}>
                  Team<SortArrow field="team" sortField={sortField} sortDir={sortDir} />
                </th>
                <th onClick={() => handleSort('waiver_adds')} className={`${thClass} text-center`}>
                  Waiver Adds<SortArrow field="waiver_adds" sortField={sortField} sortDir={sortDir} />
                </th>
                <th onClick={() => handleSort('free_agent_adds')} className={`${thClass} text-center`}>
                  Free Agent Adds<SortArrow field="free_agent_adds" sortField={sortField} sortDir={sortDir} />
                </th>
                <th onClick={() => handleSort('trades')} className={`${thClass} text-center`}>
                  Trades<SortArrow field="trades" sortField={sortField} sortDir={sortDir} />
                </th>
                <th onClick={() => handleSort('total')} className={`${thClass} text-center`}>
                  Total<SortArrow field="total" sortField={sortField} sortDir={sortDir} />
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {sortedSummary.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-4 py-8 text-center text-gray-500">
                    No transactions found.
                  </td>
                </tr>
              ) : (
                sortedSummary.map((entry) => (
                  <tr key={entry.user_id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-sm font-medium text-gray-900">
                      {entry.team_name
                        ? <>{entry.team_name} <span className="text-gray-500 font-normal">({entry.username})</span></>
                        : entry.username}
                    </td>
                    <td className="px-4 py-3 text-sm text-center">
                      {entry.waiver_adds > 0 ? (
                        <button
                          onClick={() => openModal(entry, 'waiver', 'Waiver Adds')}
                          className="text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300 hover:underline font-medium"
                        >
                          {entry.waiver_adds}
                        </button>
                      ) : (
                        <span className="text-gray-400">0</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-sm text-center">
                      {entry.free_agent_adds > 0 ? (
                        <button
                          onClick={() => openModal(entry, 'free_agent', 'Free Agent Adds')}
                          className="text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300 hover:underline font-medium"
                        >
                          {entry.free_agent_adds}
                        </button>
                      ) : (
                        <span className="text-gray-400">0</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-sm text-center">
                      {entry.trades > 0 ? (
                        <button
                          onClick={() => openModal(entry, 'trade', 'Trades')}
                          className="text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300 hover:underline font-medium"
                        >
                          {entry.trades}
                        </button>
                      ) : (
                        <span className="text-gray-400">0</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-sm text-center font-semibold text-gray-900">
                      {entry.total}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Transaction detail modal */}
      {modal && (
        <TransactionModal
          teamName={modal.teamName}
          typeName={modal.typeName}
          userId={modal.userId}
          type={modal.type}
          onClose={() => setModal(null)}
        />
      )}
    </div>
  );
}
