import { Link, Outlet } from 'react-router-dom';

export default function Layout() {
  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-blue-600 text-white shadow-lg">
        <div className="container mx-auto px-4">
          <div className="flex items-center justify-between h-16">
            <Link to="/" className="text-2xl font-bold">
              Insight2Dynasty
            </Link>
            <div className="flex space-x-6">
              <Link to="/" className="hover:text-blue-200 transition">
                Standings
              </Link>
              <Link to="/players" className="hover:text-blue-200 transition">
                Players
              </Link>
              <Link to="/head-to-head" className="hover:text-blue-200 transition">
                H2H
              </Link>
              <Link to="/owners" className="hover:text-blue-200 transition">
                Owners
              </Link>
              <Link to="/drafts" className="hover:text-blue-200 transition">
                Drafts
              </Link>
              <Link to="/league-history" className="hover:text-blue-200 transition">
                History
              </Link>
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
