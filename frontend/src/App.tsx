import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import Layout from './components/Layout';
import Home from './pages/Home';
import Players from './pages/Players';
import HeadToHead from './pages/HeadToHead';
import Owners from './pages/Owners';
import Drafts from './pages/Drafts';
import LeagueHistory from './pages/LeagueHistory';
import TaxiSquads from './pages/TaxiSquads';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 5 * 60 * 1000, // 5 minutes
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<Home />} />
            <Route path="taxi-squads" element={<TaxiSquads />} />
            <Route path="players" element={<Players />} />
            <Route path="head-to-head" element={<HeadToHead />} />
            <Route path="owners" element={<Owners />} />
            <Route path="drafts" element={<Drafts />} />
            <Route path="league-history" element={<LeagueHistory />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
