import { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../services/api';
import { usePlayerModal } from '../context/PlayerModalContext';

interface SearchResult {
  type: 'player' | 'owner' | 'draft';
  id: string;
  label: string;
  subtitle: string;
  meta?: { avatar?: string; year?: number };
}

interface SearchResponse {
  query: string;
  results: SearchResult[];
}

interface SearchModalProps {
  isOpen: boolean;
  onClose: () => void;
}

const TYPE_LABELS: Record<string, string> = { player: 'Players', owner: 'Owners', draft: 'Drafts' };
const TYPE_ORDER: SearchResult['type'][] = ['player', 'owner', 'draft'];

function TypeIcon({ type }: { type: string }) {
  if (type === 'player') {
    return (
      <svg className="w-4 h-4 text-blue-500 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
      </svg>
    );
  }
  if (type === 'owner') {
    return (
      <svg className="w-4 h-4 text-green-500 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />
      </svg>
    );
  }
  return (
    <svg className="w-4 h-4 text-purple-500 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
    </svg>
  );
}

export default function SearchModal({ isOpen, onClose }: SearchModalProps) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);
  const inputRef = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();
  const { openPlayer } = usePlayerModal();

  useEffect(() => {
    if (isOpen) {
      setQuery('');
      setResults([]);
      setActiveIndex(-1);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [isOpen]);

  useEffect(() => {
    if (query.length < 2) {
      setResults([]);
      setIsLoading(false);
      return;
    }
    setIsLoading(true);
    const timer = setTimeout(async () => {
      try {
        const data: SearchResponse = await api.search(query);
        setResults(data.results);
        setActiveIndex(-1);
      } catch {
        setResults([]);
      } finally {
        setIsLoading(false);
      }
    }, 300);
    return () => clearTimeout(timer);
  }, [query]);

  const handleSelect = useCallback(
    (result: SearchResult) => {
      onClose();
      if (result.type === 'player') {
        openPlayer(result.id);
      } else if (result.type === 'owner') {
        navigate('/owners');
      } else if (result.type === 'draft') {
        navigate(result.meta?.year ? `/drafts?year=${result.meta.year}` : '/drafts');
      }
    },
    [navigate, onClose, openPlayer]
  );

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') { onClose(); return; }
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setActiveIndex(i => Math.min(i + 1, results.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setActiveIndex(i => Math.max(i - 1, -1));
    } else if (e.key === 'Enter' && activeIndex >= 0) {
      handleSelect(results[activeIndex]);
    }
  };

  if (!isOpen) return null;

  // Group results in display order, preserving flat indices for keyboard nav
  const groups = TYPE_ORDER
    .map(type => ({ label: TYPE_LABELS[type], items: results.filter(r => r.type === type) }))
    .filter(g => g.items.length > 0);

  // Map each item to its flat index in `results` for keyboard nav
  const flatIndexOf = (item: SearchResult) => results.indexOf(item);

  return (
    <div
      className="fixed inset-0 bg-black bg-opacity-50 flex items-start justify-center z-50 pt-[15vh] px-4"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-xl shadow-2xl w-full max-w-lg overflow-hidden"
        onClick={e => e.stopPropagation()}
      >
        {/* Input row */}
        <div className="flex items-center gap-3 px-4 py-3 border-b border-gray-100">
          <svg className="w-5 h-5 text-gray-400 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={e => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Search players, owners, drafts…"
            className="flex-1 text-base text-gray-900 placeholder-gray-400 bg-transparent outline-none"
          />
          {isLoading && (
            <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin shrink-0" />
          )}
          {!isLoading && query && (
            <button
              onClick={() => setQuery('')}
              className="text-gray-400 hover:text-gray-600 shrink-0"
              aria-label="Clear search"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          )}
          <kbd className="hidden sm:flex items-center text-xs text-gray-400 border border-gray-200 rounded px-1.5 py-0.5 shrink-0">
            esc
          </kbd>
        </div>

        {/* Results */}
        {query.length >= 2 && !isLoading && results.length === 0 && (
          <p className="px-4 py-8 text-sm text-gray-400 text-center">No results for "{query}"</p>
        )}

        {groups.length > 0 && (
          <div className="max-h-80 overflow-y-auto pb-2">
            {groups.map(group => (
              <div key={group.label}>
                <div className="px-3 pt-3 pb-1 text-xs font-bold uppercase tracking-wider text-gray-400">
                  {group.label}
                </div>
                {group.items.map(item => {
                  const idx = flatIndexOf(item);
                  const isActive = idx === activeIndex;
                  return (
                    <button
                      key={`${item.type}-${item.id}`}
                      className={`w-full flex items-center gap-3 px-3 py-2.5 text-left transition ${
                        isActive ? 'bg-blue-50' : 'hover:bg-gray-50'
                      }`}
                      onClick={() => handleSelect(item)}
                      onMouseEnter={() => setActiveIndex(idx)}
                    >
                      <TypeIcon type={item.type} />
                      <span className="flex-1 min-w-0">
                        <span className="block text-sm font-medium text-gray-900 truncate">{item.label}</span>
                        {item.subtitle && (
                          <span className="block text-xs text-gray-500">{item.subtitle}</span>
                        )}
                      </span>
                    </button>
                  );
                })}
              </div>
            ))}
          </div>
        )}

        {query.length < 2 && (
          <p className="px-4 py-6 text-sm text-gray-400 text-center">
            Type at least 2 characters to search
          </p>
        )}

        {/* Footer */}
        <div className="px-4 py-2 border-t border-gray-100 flex items-center gap-4 text-xs text-gray-400">
          <span>
            <kbd className="border border-gray-200 rounded px-1 py-0.5">↑↓</kbd> navigate
          </span>
          <span>
            <kbd className="border border-gray-200 rounded px-1 py-0.5">↵</kbd> select
          </span>
          <span>
            <kbd className="border border-gray-200 rounded px-1 py-0.5">esc</kbd> close
          </span>
        </div>
      </div>
    </div>
  );
}
