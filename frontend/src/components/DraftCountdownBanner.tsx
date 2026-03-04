import { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../services/api';

interface DraftOrderEntry {
  slot: number;
  display_name: string;
  avatar: string | null;
}

interface CurrentDraft {
  draft_id: string;
  year: number;
  status: string;
  start_time: string | null;
  draft_order: DraftOrderEntry[];
}

function getTimeRemaining(targetDate: Date) {
  const now = new Date().getTime();
  const diff = targetDate.getTime() - now;

  if (diff <= 0) return null;

  const days = Math.floor(diff / (1000 * 60 * 60 * 24));
  const hours = Math.floor((diff % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
  const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
  const seconds = Math.floor((diff % (1000 * 60)) / 1000);

  return { days, hours, minutes, seconds };
}

function CountdownTimer({ targetDate }: { targetDate: Date }) {
  const [timeLeft, setTimeLeft] = useState(getTimeRemaining(targetDate));

  useEffect(() => {
    const timer = setInterval(() => {
      const remaining = getTimeRemaining(targetDate);
      setTimeLeft(remaining);
      if (!remaining) clearInterval(timer);
    }, 1000);

    return () => clearInterval(timer);
  }, [targetDate]);

  if (!timeLeft) {
    return <span className="text-lg font-semibold text-blue-600 dark:text-blue-400">Draft is underway!</span>;
  }

  return (
    <div className="flex items-center gap-2">
      <TimeUnit value={timeLeft.days} label="Days" />
      <span className="text-lg font-bold text-gray-400">:</span>
      <TimeUnit value={timeLeft.hours} label="Hrs" />
      <span className="text-lg font-bold text-gray-400">:</span>
      <TimeUnit value={timeLeft.minutes} label="Min" />
      <span className="text-lg font-bold text-gray-400">:</span>
      <TimeUnit value={timeLeft.seconds} label="Sec" />
    </div>
  );
}

function TimeUnit({ value, label }: { value: number; label: string }) {
  return (
    <div className="flex flex-col items-center">
      <span className="text-lg font-bold text-blue-600 dark:text-blue-400 tabular-nums min-w-[1.5rem] text-center">
        {String(value).padStart(2, '0')}
      </span>
      <span className="text-xs text-gray-500 uppercase tracking-wide">{label}</span>
    </div>
  );
}

function DraftOrderModal({ draftOrder, year, onClose }: { draftOrder: DraftOrderEntry[]; year: number; onClose: () => void }) {
  useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', handleEsc);
    return () => document.removeEventListener('keydown', handleEsc);
  }, [onClose]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center" onClick={onClose}>
      <div className="fixed inset-0 bg-black/50" />
      <div
        className="relative bg-white rounded-lg shadow-xl w-full max-w-sm mx-4"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-200">
          <h3 className="text-lg font-bold text-gray-900">{year} Draft Order</h3>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        <div className="px-5 py-3 max-h-96 overflow-y-auto">
          <ol className="space-y-2">
            {draftOrder.map((entry) => (
              <li key={entry.slot} className="flex items-center gap-3 py-1.5">
                <span className="w-7 h-7 flex items-center justify-center rounded-full bg-blue-100 dark:bg-blue-900 text-sm font-bold text-blue-700 dark:text-blue-300 shrink-0">
                  {entry.slot}
                </span>
                {entry.avatar && (
                  <img
                    src={`https://sleepercdn.com/avatars/thumbs/${entry.avatar}`}
                    alt=""
                    className="w-7 h-7 rounded-full shrink-0"
                  />
                )}
                <span className="text-sm font-medium text-gray-900">{entry.display_name}</span>
              </li>
            ))}
          </ol>
        </div>
      </div>
    </div>
  );
}

export default function DraftCountdownBanner() {
  const [showOrder, setShowOrder] = useState(false);

  const { data: draft } = useQuery<CurrentDraft | null>({
    queryKey: ['currentDraft'],
    queryFn: api.getCurrentDraft,
    staleTime: 5 * 60 * 1000,
  });

  // Don't show if no draft or draft is complete
  if (!draft || draft.status === 'complete') return null;

  const targetDate = draft.start_time ? new Date(draft.start_time) : null;
  const hasDraftOrder = draft.draft_order && draft.draft_order.length > 0;

  return (
    <>
      <div className="flex items-center gap-3 bg-white rounded-lg shadow px-4 py-2 border border-blue-200 dark:border-blue-800">
        <div className="flex items-center gap-2">
          <svg className="w-5 h-5 text-blue-600 dark:text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span className="text-sm font-semibold text-gray-700 uppercase tracking-wide whitespace-nowrap">
            {draft.year} Draft
          </span>
        </div>
        {targetDate ? (
          <CountdownTimer targetDate={targetDate} />
        ) : (
          <span className="text-sm font-semibold text-blue-600 dark:text-blue-400 whitespace-nowrap">Coming Soon</span>
        )}
        {hasDraftOrder && (
          <button
            onClick={() => setShowOrder(true)}
            className="text-xs font-medium text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 underline underline-offset-2 whitespace-nowrap transition-colors"
          >
            Draft Order
          </button>
        )}
      </div>
      {showOrder && hasDraftOrder && (
        <DraftOrderModal
          draftOrder={draft.draft_order}
          year={draft.year}
          onClose={() => setShowOrder(false)}
        />
      )}
    </>
  );
}
