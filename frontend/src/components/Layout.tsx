import { useState, useEffect } from 'react';
import { Link, Outlet, useLocation } from 'react-router-dom';
import { useTheme } from '../hooks/useTheme';
import SearchModal from './SearchModal';

interface NavLink {
  to: string;
  label: string;
}

interface NavGroup {
  label: string;
  links: NavLink[];
}

const navGroups: NavGroup[] = [
  {
    label: 'Season',
    links: [
      { to: '/', label: 'Standings' },
      { to: '/matchup-recaps', label: 'Matchups' },
      { to: '/playoffs', label: 'Playoffs' },
      { to: '/power-rankings', label: 'Power Rankings' },
      { to: '/trade-calculator', label: 'Trade Calculator' },
    ],
  },
  {
    label: 'Teams',
    links: [
      { to: '/owners', label: 'Owners' },
      { to: '/roster-analysis', label: 'Rosters' },
      { to: '/head-to-head', label: 'H2H' },
      { to: '/taxi-squads', label: 'Taxi' },
      { to: '/free-agents', label: 'Free Agents' },
    ],
  },
  {
    label: 'History',
    links: [
      { to: '/league-history', label: 'League History' },
      { to: '/records', label: 'Records' },
      { to: '/team-records', label: 'Team Records' },
      { to: '/drafts', label: 'Drafts' },
      { to: '/future-draft-picks', label: 'Future Picks' },
      { to: '/draft-rankings', label: 'Draft Rankings' },
    ],
  },
  {
    label: 'Moves',
    links: [
      { to: '/transactions', label: 'Transactions' },
      { to: '/trade-grades', label: 'Trade Grades' },
    ],
  },
];

const ThemeIcon = ({ theme }: { theme: string }) =>
  theme === 'dark' ? (
    <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
      <path
        fillRule="evenodd"
        d="M10 2a1 1 0 011 1v1a1 1 0 11-2 0V3a1 1 0 011-1zm4 8a4 4 0 11-8 0 4 4 0 018 0zm-.464 4.95l.707.707a1 1 0 001.414-1.414l-.707-.707a1 1 0 00-1.414 1.414zm2.12-10.607a1 1 0 010 1.414l-.706.707a1 1 0 11-1.414-1.414l.707-.707a1 1 0 011.414 0zM17 11a1 1 0 100-2h-1a1 1 0 100 2h1zm-7 4a1 1 0 011 1v1a1 1 0 11-2 0v-1a1 1 0 011-1zM5.05 6.464A1 1 0 106.465 5.05l-.708-.707a1 1 0 00-1.414 1.414l.707.707zm1.414 8.486l-.707.707a1 1 0 01-1.414-1.414l.707-.707a1 1 0 011.414 1.414zM4 11a1 1 0 100-2H3a1 1 0 000 2h1z"
        clipRule="evenodd"
      />
    </svg>
  ) : (
    <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
      <path d="M17.293 13.293A8 8 0 016.707 2.707a8.001 8.001 0 1010.586 10.586z" />
    </svg>
  );

const bottomTabs = [
  {
    to: '/',
    label: 'Standings',
    icon: (active: boolean) => (
      <svg className={`w-6 h-6 ${active ? 'text-blue-500' : 'text-gray-500 dark:text-gray-400'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
      </svg>
    ),
  },
  {
    to: '/matchup-recaps',
    label: 'Matchups',
    icon: (active: boolean) => (
      <svg className={`w-6 h-6 ${active ? 'text-blue-500' : 'text-gray-500 dark:text-gray-400'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
      </svg>
    ),
  },
  {
    to: '/owners',
    label: 'Teams',
    icon: (active: boolean) => (
      <svg className={`w-6 h-6 ${active ? 'text-blue-500' : 'text-gray-500 dark:text-gray-400'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />
      </svg>
    ),
  },
  {
    to: '/trade-calculator',
    label: 'Trades',
    icon: (active: boolean) => (
      <svg className={`w-6 h-6 ${active ? 'text-blue-500' : 'text-gray-500 dark:text-gray-400'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
      </svg>
    ),
  },
];

export default function Layout() {
  const { theme, toggleTheme } = useTheme();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [openDropdown, setOpenDropdown] = useState<string | null>(null);
  const [searchOpen, setSearchOpen] = useState(false);
  const location = useLocation();

  const closeMobileMenu = () => setMobileMenuOpen(false);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        setSearchOpen(open => !open);
      }
    };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, []);

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-blue-600 dark:bg-blue-800 text-white shadow-lg">
        <div className="container mx-auto px-4">
          <div className="flex items-center justify-between h-16">
            {/* Logo */}
            <Link
              to="/"
              className="text-xl md:text-2xl font-bold flex-shrink-0"
              onClick={closeMobileMenu}
            >
              Insight2Dynasty
            </Link>

            {/* Desktop Navigation */}
            <div className="hidden md:flex items-center space-x-1 lg:space-x-2">
              {navGroups.map((group) => (
                <div
                  key={group.label}
                  className="relative"
                  onMouseEnter={() => setOpenDropdown(group.label)}
                  onMouseLeave={() => setOpenDropdown(null)}
                >
                  <button className="flex items-center gap-1 px-3 py-2 text-sm lg:text-base font-semibold hover:text-blue-200 transition whitespace-nowrap rounded-md hover:bg-blue-500 dark:hover:bg-blue-700">
                    {group.label}
                    <svg className="w-3 h-3 mt-0.5 opacity-70" fill="currentColor" viewBox="0 0 20 20">
                      <path
                        fillRule="evenodd"
                        d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z"
                        clipRule="evenodd"
                      />
                    </svg>
                  </button>

                  {openDropdown === group.label && (
                    <div className="absolute top-full left-0 mt-0 w-48 bg-white dark:bg-gray-800 rounded-md shadow-lg z-50 py-1 border border-gray-200 dark:border-gray-700">
                      {group.links.map((link) => (
                        <Link
                          key={link.to}
                          to={link.to}
                          onClick={() => setOpenDropdown(null)}
                          className="block px-4 py-2 text-sm text-gray-700 dark:text-gray-200 hover:bg-blue-50 dark:hover:bg-blue-900 hover:text-blue-700 dark:hover:text-blue-200 transition"
                        >
                          {link.label}
                        </Link>
                      ))}
                    </div>
                  )}
                </div>
              ))}

              <button
                onClick={() => setSearchOpen(true)}
                className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-blue-100 bg-blue-500 dark:bg-blue-700 hover:bg-blue-400 dark:hover:bg-blue-600 rounded-lg transition ml-1"
                aria-label="Search"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
                <span className="hidden lg:inline">Search</span>
                <kbd className="hidden lg:inline text-xs opacity-70 border border-blue-400 rounded px-1">⌘K</kbd>
              </button>

              <button
                onClick={toggleTheme}
                className="p-2 rounded-lg hover:bg-blue-500 dark:hover:bg-blue-700 transition ml-1"
                aria-label={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
              >
                <ThemeIcon theme={theme} />
              </button>
            </div>

            {/* Mobile: search + theme toggle (nav handled by bottom tab bar) */}
            <div className="flex items-center gap-1 md:hidden">
              <button
                onClick={() => setSearchOpen(true)}
                className="p-2 rounded-lg hover:bg-blue-500 dark:hover:bg-blue-700 transition"
                aria-label="Search"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
              </button>
              <button
                onClick={toggleTheme}
                className="p-2 rounded-lg hover:bg-blue-500 dark:hover:bg-blue-700 transition"
                aria-label={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
              >
                <ThemeIcon theme={theme} />
              </button>
            </div>
          </div>

          {/* Mobile Navigation Menu (desktop fallback only — mobile uses bottom sheet) */}
        </div>
      </nav>
      <main className="pb-16 md:pb-0">
        <Outlet />
      </main>

      {/* Mobile More Drawer (bottom sheet) */}
      {mobileMenuOpen && (
        <div className="fixed inset-0 z-40 md:hidden" onClick={closeMobileMenu}>
          <div className="absolute inset-0 bg-black/40" />
          <div
            className="absolute bottom-14 left-0 right-0 bg-white dark:bg-gray-900 rounded-t-2xl shadow-xl max-h-[70vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex justify-between items-center px-4 pt-4 pb-2 border-b border-gray-200 dark:border-gray-700">
              <span className="text-base font-bold text-gray-900 dark:text-white">All Pages</span>
              <button onClick={closeMobileMenu} className="p-1 rounded-lg text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-800">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <div className="pb-4">
              {navGroups.map((group) => (
                <div key={group.label}>
                  <div className="px-4 pt-3 pb-1 text-xs font-bold uppercase tracking-wider text-gray-400 dark:text-gray-500">
                    {group.label}
                  </div>
                  <div className="grid grid-cols-2 gap-1 px-2">
                    {group.links.map((link) => {
                      const isActive = link.to === '/' ? location.pathname === '/' : location.pathname.startsWith(link.to);
                      return (
                        <Link
                          key={link.to}
                          to={link.to}
                          onClick={closeMobileMenu}
                          className={`px-3 py-2.5 rounded-lg text-sm font-medium transition ${
                            isActive
                              ? 'bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400'
                              : 'text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800'
                          }`}
                        >
                          {link.label}
                        </Link>
                      );
                    })}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      <SearchModal isOpen={searchOpen} onClose={() => setSearchOpen(false)} />

      {/* Mobile Bottom Tab Bar */}
      <nav className="fixed bottom-0 left-0 right-0 z-50 bg-white dark:bg-gray-900 border-t border-gray-200 dark:border-gray-700 md:hidden">
        <div className="flex items-stretch">
          {bottomTabs.map((tab) => {
            const isActive = tab.to === '/' ? location.pathname === '/' : location.pathname.startsWith(tab.to);
            return (
              <Link
                key={tab.to}
                to={tab.to}
                className="flex-1 flex flex-col items-center justify-center py-2 gap-0.5 min-h-[56px]"
              >
                {tab.icon(isActive)}
                <span className={`text-[10px] font-medium ${isActive ? 'text-blue-500' : 'text-gray-500 dark:text-gray-400'}`}>
                  {tab.label}
                </span>
              </Link>
            );
          })}
          {/* More tab */}
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="flex-1 flex flex-col items-center justify-center py-2 gap-0.5 min-h-[56px]"
          >
            <svg className={`w-6 h-6 ${mobileMenuOpen ? 'text-blue-500' : 'text-gray-500 dark:text-gray-400'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            </svg>
            <span className={`text-[10px] font-medium ${mobileMenuOpen ? 'text-blue-500' : 'text-gray-500 dark:text-gray-400'}`}>
              More
            </span>
          </button>
        </div>
      </nav>
    </div>
  );
}
