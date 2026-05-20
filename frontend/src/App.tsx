import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { PlayerModalProvider } from './context/PlayerModalContext';
import { LeagueProvider } from './context/LeagueContext';
import Layout from './components/Layout';
import Home from './pages/Home';
import PowerRankings from './pages/PowerRankings';
import Records from './pages/Records';
import HeadToHead from './pages/HeadToHead';
import Owners from './pages/Owners';
import Drafts from './pages/Drafts';
import LeagueHistory from './pages/LeagueHistory';
import TaxiSquads from './pages/TaxiSquads';
import Transactions from './pages/Transactions';
import TradeGrades from './pages/TradeGrades';
import DraftRankings from './pages/DraftRankings';
import Playoffs from './pages/Playoffs';
import MatchupRecaps from './pages/MatchupRecaps';
import Newsletter from './pages/Newsletter';
import RosterAnalysis from './pages/RosterAnalysis';
import TradeCalculator from './pages/TradeCalculator';
import FutureDraftPicks from './pages/FutureDraftPicks';
import TeamRecords from './pages/TeamRecords';
import FreeAgents from './pages/FreeAgents';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 5 * 60 * 1000,
    },
  },
});

// Redirect root to the last visited league (or default).
function RootRedirect() {
  const saved = localStorage.getItem('lastLeagueSlug');
  return <Navigate to={`/${saved || 'insight2dynasty'}`} replace />;
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <PlayerModalProvider>
        <BrowserRouter>
          <LeagueProvider>
            <Routes>
              <Route path="/" element={<RootRedirect />} />
              <Route path="/:leagueSlug" element={<Layout />}>
                <Route index element={<Home />} />
                <Route path="power-rankings" element={<PowerRankings />} />
                <Route path="taxi-squads" element={<TaxiSquads />} />
                <Route path="records" element={<Records />} />
                <Route path="head-to-head" element={<HeadToHead />} />
                <Route path="owners" element={<Owners />} />
                <Route path="drafts" element={<Drafts />} />
                <Route path="transactions" element={<Transactions />} />
                <Route path="trade-grades" element={<TradeGrades />} />
                <Route path="draft-rankings" element={<DraftRankings />} />
                <Route path="league-history" element={<LeagueHistory />} />
                <Route path="playoffs" element={<Playoffs />} />
                <Route path="matchup-recaps" element={<MatchupRecaps />} />
                <Route path="newsletter" element={<Newsletter />} />
                <Route path="roster-analysis" element={<RosterAnalysis />} />
                <Route path="trade-calculator" element={<TradeCalculator />} />
                <Route path="future-draft-picks" element={<FutureDraftPicks />} />
                <Route path="team-records" element={<TeamRecords />} />
                <Route path="free-agents" element={<FreeAgents />} />
              </Route>
            </Routes>
          </LeagueProvider>
        </BrowserRouter>
      </PlayerModalProvider>
    </QueryClientProvider>
  );
}

export default App;
