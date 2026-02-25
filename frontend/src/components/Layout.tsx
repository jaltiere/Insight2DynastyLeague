import { Link, Outlet } from 'react-router-dom';
import { useTheme } from '../hooks/useTheme';

export default function Layout() {
  const { theme, toggleTheme } = useTheme();

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-blue-600 dark:bg-blue-800 text-white shadow-lg">
        <div className="container mx-auto px-4">
          <div className="flex items-center justify-between h-16">
            <Link to="/" className="text-2xl font-bold">
              Insight2Dynasty
            </Link>
            <div className="flex items-center space-x-6">
              <Link to="/" className="font-semibold hover:text-blue-200 transition">
                Standings
              </Link>
              <Link to="/taxi-squads" className="font-semibold hover:text-blue-200 transition">
                Taxi Squads
              </Link>
              <Link to="/players" className="font-semibold hover:text-blue-200 transition">
                Player Records
              </Link>
              <Link to="/rookie-records" className="font-semibold hover:text-blue-200 transition">
                Rookie Records
              </Link>
              <Link to="/head-to-head" className="font-semibold hover:text-blue-200 transition">
                H2H
              </Link>
              <Link to="/owners" className="font-semibold hover:text-blue-200 transition">
                Owners
              </Link>
              <Link to="/drafts" className="font-semibold hover:text-blue-200 transition">
                Drafts
              </Link>
              <Link to="/transactions" className="font-semibold hover:text-blue-200 transition">
                Transactions
              </Link>
              <Link to="/league-history" className="font-semibold hover:text-blue-200 transition">
                History
              </Link>
              <button
                onClick={toggleTheme}
                className="p-2 rounded-lg hover:bg-blue-500 dark:hover:bg-blue-700 transition"
                aria-label={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
              >
                {theme === 'dark' ? (
                  <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 2a1 1 0 011 1v1a1 1 0 11-2 0V3a1 1 0 011-1zm4 8a4 4 0 11-8 0 4 4 0 018 0zm-.464 4.95l.707.707a1 1 0 001.414-1.414l-.707-.707a1 1 0 00-1.414 1.414zm2.12-10.607a1 1 0 010 1.414l-.706.707a1 1 0 11-1.414-1.414l.707-.707a1 1 0 011.414 0zM17 11a1 1 0 100-2h-1a1 1 0 100 2h1zm-7 4a1 1 0 011 1v1a1 1 0 11-2 0v-1a1 1 0 011-1zM5.05 6.464A1 1 0 106.465 5.05l-.708-.707a1 1 0 00-1.414 1.414l.707.707zm1.414 8.486l-.707.707a1 1 0 01-1.414-1.414l.707-.707a1 1 0 011.414 1.414zM4 11a1 1 0 100-2H3a1 1 0 000 2h1z" clipRule="evenodd" />
                  </svg>
                ) : (
                  <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                    <path d="M17.293 13.293A8 8 0 016.707 2.707a8.001 8.001 0 1010.586 10.586z" />
                  </svg>
                )}
              </button>
            </div>
          </div>
        </div>
      </nav>
      <main>
        <Outlet />
      </main>
    </div>
  );
}
