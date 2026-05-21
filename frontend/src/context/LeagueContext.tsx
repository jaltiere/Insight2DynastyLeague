import { createContext, useContext, useState, useEffect, useCallback, useRef, type ReactNode } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import { setCurrentLeagueSlug, api } from '../services/api';

export interface League {
  id: string;
  slug: string;
  name: string;
  default: boolean;
}

interface LeagueContextType {
  leagues: League[];
  currentLeague: League | null;
  switchLeague: (slug: string) => void;
  syncLeagueFromUrl: (slug: string) => void;
}

const LeagueContext = createContext<LeagueContextType | null>(null);

const STORAGE_KEY = 'lastLeagueSlug';

export function LeagueProvider({ children }: { children: ReactNode }) {
  const navigate = useNavigate();
  const location = useLocation();
  const queryClient = useQueryClient();
  const [leagues, setLeagues] = useState<League[]>([]);
  const [currentLeague, setCurrentLeague] = useState<League | null>(null);
  // Refs keep callbacks stable without stale-closure issues
  const currentLeagueRef = useRef<League | null>(null);
  const locationRef = useRef(location.pathname);
  useEffect(() => { currentLeagueRef.current = currentLeague; }, [currentLeague]);
  useEffect(() => { locationRef.current = location.pathname; }, [location.pathname]);

  useEffect(() => {
    api.getLeagues().then((data: League[]) => {
      setLeagues(data);
      const savedSlug = localStorage.getItem(STORAGE_KEY);
      const initial =
        data.find((l) => l.slug === savedSlug) ||
        data.find((l) => l.default) ||
        data[0];
      if (initial) {
        setCurrentLeague(initial);
        setCurrentLeagueSlug(initial.slug);
      }
    });
  }, []);

  // Called by Layout when the URL slug changes (back/forward, direct link).
  // Uses a ref for currentLeague so this callback is stable relative to leagues.
  const syncLeagueFromUrl = useCallback(
    (slug: string) => {
      if (!leagues.length) return;
      const league = leagues.find((l) => l.slug === slug);
      if (!league || league.slug === currentLeagueRef.current?.slug) return;
      setCurrentLeague(league);
      setCurrentLeagueSlug(slug);
      queryClient.resetQueries();
    },
    [leagues, queryClient], // stable — currentLeague read via ref, not closure
  );

  // Called by the league switcher UI — resets cached data and navigates.
  const switchLeague = useCallback(
    (slug: string) => {
      const league = leagues.find((l) => l.slug === slug);
      if (!league || league.slug === currentLeagueRef.current?.slug) return;
      localStorage.setItem(STORAGE_KEY, slug);
      setCurrentLeague(league);
      setCurrentLeagueSlug(slug);
      // resetQueries clears both data AND error state so the new league starts clean
      queryClient.resetQueries();
      // Preserve current sub-path (e.g. /old-league/drafts → /new-league/drafts)
      const oldSlug = currentLeagueRef.current?.slug ?? '';
      const subPath = oldSlug
        ? locationRef.current.slice(1 + oldSlug.length)
        : '';
      navigate(`/${slug}${subPath}`);
    },
    [leagues, navigate, queryClient], // stable — currentLeague read via ref
  );

  return (
    <LeagueContext.Provider value={{ leagues, currentLeague, switchLeague, syncLeagueFromUrl }}>
      {children}
    </LeagueContext.Provider>
  );
}

export function useLeague() {
  const ctx = useContext(LeagueContext);
  if (!ctx) throw new Error('useLeague must be used within LeagueProvider');
  return ctx;
}
