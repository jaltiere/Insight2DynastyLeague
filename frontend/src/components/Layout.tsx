import { useState, useEffect, useRef } from 'react';
import { Link, Outlet, useLocation, useParams } from 'react-router-dom';
import { useTheme } from '../hooks/useTheme';
import { useLeague } from '../context/LeagueContext';
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
      { to: '', label: 'Standings' },
      { to: 'matchup-recaps', label: 'Matchups' },
      { to: 'playoffs', label: 'Playoffs' },
      { to: 'power-rankings', label: 'Power Rankings' },
      { to: 'trade-calculator', label: 'Trade Calculator' },
    ],
  },
  {
    label: 'Teams',
    links: [
      { to: 'owners', label: 'Owners' },
      { to: 'roster-analysis', label: 'Rosters' },
      { to: 'head-to-head', label: 'H2H' },
      { to: 'taxi-squads', label: 'Taxi' },
      { to: 'free-agents', label: 'Free Agents' },
    ],
  },
  {
    label: 'History',
    links: [
      { to: 'league-history', label: 'League History' },
      { to: 'records', label: 'Records' },
      { to: 'team-records', label: 'Team Records' },
      { to: 'drafts', label: 'Drafts' },
      { to: 'future-draft-picks', label: 'Future Picks' },
      { to: 'draft-rankings', label: 'Draft Rankings' },
    ],
  },
  {
    label: 'Moves',
    links: [
      { to: 'transactions', label: 'Transactions' },
      { to: 'trade-grades', label: 'Trade Grades' },
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

export default function Layout() {
  const { theme, toggleTheme } = useTheme();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [openDropdown, setOpenDropdown] = useState<string | null>(null);
  const [leagueSwitcherOpen, setLeagueSwitcherOpen] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const location = useLocation();
  const { leagueSlug } = useParams<{ leagueSlug: string }>();
  const { leagues, currentLeague, switchLeague, syncLeagueFromUrl } = useLeague();
  const leagueSwitcherRef = useRef<HTMLDivElement>(null);

  const slug = leagueSlug || currentLeague?.slug || 'insight2dynasty';

  // Sync context when navigating directly to a league URL
  useEffect(() => {
    if (leagueSlug) syncLeagueFromUrl(leagueSlug);
  }, [leagueSlug, syncLeagueFromUrl]);

  const closeMobileMenu = () => setMobileMenuOpen(false);

  // Build an absolute path for a given page within the current league
  const p = (page: string) => (page === '' ? `/${slug}` : `/${slug}/${page}`);

  // Determine if a nav link is active
  const isActive = (page: string) =>
    page === ''
      ? location.pathname === `/${slug}` || location.pathname === `/${slug}/`
      : location.pathname.startsWith(`/${slug}/${page}`);

  // Close league switcher when clicking outside
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (leagueSwitcherRef.current && !leagueSwitcherRef.current.contains(e.target as Node)) {
        setLeagueSwitcherOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        setSearchOpen((open) => !open);
      }
    };
    document.addEventListener('keydown', handler);
    return () => document.removeEventListener('keydown', handler);
  }, []);

  const otherLeagues = leagues.filter((l) => l.slug !== slug);
  const displayName = currentLeague?.name || 'Insight2Dynasty';

  // Bottom tabs need league-prefixed paths
  const bottomTabs = [
    {
      page: '',
      label: 'Standings',
      icon: (active: boolean) => (
        <svg className={`w-6 h-6 ${active ? 'text-blue-500' : 'text-gray-500 dark:text-gray-400'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
        </svg>
      ),
    },
    {
      page: 'matchup-recaps',
      label: 'Matchups',
      icon: (active: boolean) => (
        <svg className={`w-6 h-6 ${active ? 'text-blue-500' : 'text-gray-500 dark:text-gray-400'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
        </svg>
      ),
    },
    {
      page: 'owners',
      label: 'Teams',
      icon: (active: boolean) => (
        <svg className={`w-6 h-6 ${active ? 'text-blue-500' : 'text-gray-500 dark:text-gray-400'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />
        </svg>
      ),
    },
    {
      page: 'trade-calculator',
      label: 'Trades',
      icon: (active: boolean) => (
        <svg className={`w-6 h-6 ${active ? 'text-blue-500' : 'text-gray-500 dark:text-gray-400'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
        </svg>
      ),
    },
  ];

  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-blue-600 dark:bg-blue-800 text-white shadow-lg">
        <div className="container mx-auto px-4">
          <div className="flex items-center justify-between h-16">
            {/* Logo / League Switcher */}
            <div className="relative flex-shrink-0" ref={leagueSwitcherRef}>
              {leagues.length > 1 ? (
                <button
                  onClick={() => setLeagueSwitcherOpen((o) => !o)}
                  className="flex items-center gap-1.5 text-xl md:text-2xl font-bold hover:text-blue-200 transition"
                >
                  {displayName}
                  <svg className="w-4 h-4 mt-0.5 opacity-70" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" clipRule="evenodd" />
                  </svg>
                </button>
              ) : (
                <Link
                  to={p('')}
                  className="text-xl md:text-2xl font-bold hover:text-blue-200 transition"
                  onClick={closeMobileMenu}
                >
                  {displayName}
                </Link>
              )}

              {leagueSwitcherOpen && otherLeagues.length > 0 && (
                <div className="absolute top-full left-0 mt-1 w-52 bg-white dark:bg-gray-800 rounded-md shadow-lg z-50 py-1 border border-gray-200 dark:border-gray-700">
                  <div className="px-3 py-1.5 text-xs font-bold uppercase tracking-wider text-gray-400 dark:text-gray-500">
                    Switch League
                  </div>
                  {leagues.map((league) => (
                    <button
                      key={league.slug}
                      onClick={() => {
                        setLeagueSwitcherOpen(false);
                        switchLeague(league.slug);
                      }}
                      className={`w-full text-left px-4 py-2 text-sm transition ${
                        league.slug === slug
                          ? 'text-blue-600 dark:text-blue-400 font-semibold bg-blue-50 dark:bg-blue-900/30'
                          : 'text-gray-700 dark:text-gray-200 hover:bg-blue-50 dark:hover:bg-blue-900 hover:text-blue-700 dark:hover:text-blue-200'
                      }`}
                    >
                      {league.name}
                    </button>
                  ))}
                </div>
              )}
            </div>

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
                          to={p(link.to)}
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

            {/* Mobile: search + theme toggle */}
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
        </div>
      </nav>

      <main className="pb-16 md:pb-0">
        <Outlet />
      </main>

      {/* Mobile More Drawer */}
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
            {/* League switcher in mobile drawer */}
            {leagues.length > 1 && (
              <div className="px-4 pt-3 pb-2 border-b border-gray-100 dark:border-gray-800">
                <div className="text-xs font-bold uppercase tracking-wider text-gray-400 dark:text-gray-500 mb-2">League</div>
                <div className="flex flex-wrap gap-2">
                  {leagues.map((league) => (
                    <button
                      key={league.slug}
                      onClick={() => {
                        closeMobileMenu();
                        switchLeague(league.slug);
                      }}
                      className={`px-3 py-1.5 rounded-full text-sm font-medium transition ${
                        league.slug === slug
                          ? 'bg-blue-100 dark:bg-blue-900/50 text-blue-700 dark:text-blue-300'
                          : 'bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-300 hover:bg-blue-50 dark:hover:bg-blue-900/30'
                      }`}
                    >
                      {league.name}
                    </button>
                  ))}
                </div>
              </div>
            )}
            <div className="pb-4">
              {navGroups.map((group) => (
                <div key={group.label}>
                  <div className="px-4 pt-3 pb-1 text-xs font-bold uppercase tracking-wider text-gray-400 dark:text-gray-500">
                    {group.label}
                  </div>
                  <div className="grid grid-cols-2 gap-1 px-2">
                    {group.links.map((link) => {
                      const active = isActive(link.to);
                      return (
                        <Link
                          key={link.to}
                          to={p(link.to)}
                          onClick={closeMobileMenu}
                          className={`px-3 py-2.5 rounded-lg text-sm font-medium transition ${
                            active
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
            const active = isActive(tab.page);
            return (
              <Link
                key={tab.page}
                to={p(tab.page)}
                className="flex-1 flex flex-col items-center justify-center py-2 gap-0.5 min-h-[56px]"
              >
                {tab.icon(active)}
                <span className={`text-[10px] font-medium ${active ? 'text-blue-500' : 'text-gray-500 dark:text-gray-400'}`}>
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
