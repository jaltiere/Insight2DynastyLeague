import { useQuery } from '@tanstack/react-query';
import { api } from '../services/api';
import PredictionCard from '../components/PredictionCard';
import RecapCard from '../components/RecapCard';
import type { CurrentWeekMatchupsResponse, WeekRecapsResponse } from '../types';

export default function MatchupRecaps() {
  // Fetch current week matchups with predictions
  const {
    data: currentWeek,
    isLoading: currentWeekLoading,
    error: currentWeekError
  } = useQuery<CurrentWeekMatchupsResponse>({
    queryKey: ['current-week-matchups'],
    queryFn: () => api.getCurrentWeekMatchups()
  });

  // Fetch previous week recaps
  const {
    data: previousWeek,
    isLoading: previousWeekLoading,
    error: previousWeekError
  } = useQuery<WeekRecapsResponse>({
    queryKey: ['previous-week-recaps'],
    queryFn: () => api.getPreviousWeekRecaps()
  });

  // During offseason (week 0), show the page but with offseason message
  const isOffseason = currentWeek && currentWeek.week === 0;

  // Hide page only if it's early in the regular season (before week 2)
  if (currentWeek && currentWeek.week === 1) {
    return null;
  }

  // Loading state
  if (currentWeekLoading && previousWeekLoading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="flex justify-center items-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600" />
        </div>
      </div>
    );
  }

  // Error state
  if (currentWeekError || previousWeekError) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="bg-red-50 border border-red-200 rounded-lg p-6">
          <p className="text-red-600">
            Error loading matchup data: {(currentWeekError as Error)?.message || (previousWeekError as Error)?.message}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto px-4 py-8">
      {/* Page Header */}
      <div className="mb-8">
        <h1 className="text-4xl font-bold text-gray-900 mb-2">Weekly Matchups</h1>
        <p className="text-gray-600">
          AI-generated previews and recaps powered by Claude
        </p>
        {isOffseason && (
          <div className="mt-4 bg-blue-50 border border-blue-200 rounded-lg p-4">
            <p className="text-blue-800 text-sm">
              🏈 We're currently in the offseason. Check back when the season starts for weekly predictions and recaps!
            </p>
          </div>
        )}
      </div>

      {/* Current Week Predictions Section */}
      {currentWeek && currentWeek.matchups && currentWeek.matchups.length > 0 && (
        <section className="mb-12">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-2xl font-bold text-gray-900">
              This Week's Matchups - Week {currentWeek.week}
            </h2>
            <span className="text-sm text-gray-500">
              {currentWeek.matchups.length} {currentWeek.matchups.length === 1 ? 'game' : 'games'}
            </span>
          </div>

          {currentWeekLoading ? (
            <div className="flex justify-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {currentWeek.matchups.map((matchup) => (
                <PredictionCard key={matchup.matchup_id} matchup={matchup} />
              ))}
            </div>
          )}
        </section>
      )}

      {/* Previous Week Recaps Section */}
      {previousWeek && previousWeek.recaps && previousWeek.recaps.length > 0 && (
        <section>
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-2xl font-bold text-gray-900">
              {isOffseason ? `${previousWeek.season} Championship - Week ${previousWeek.week}` : `Last Week's Recaps - Week ${previousWeek.week}`}
            </h2>
            <span className="text-sm text-gray-500">
              {previousWeek.recaps.length} {previousWeek.recaps.length === 1 ? 'game' : 'games'}
            </span>
          </div>

          {previousWeekLoading ? (
            <div className="flex justify-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Sort championship week games for 2x2 layout: Championship (top-left), 3rd Place (top-right), Consolation Champ (bottom-left), 9th Place (bottom-right) */}
              {previousWeek.recaps
                .sort((a, b) => {
                  const getOrder = (recap: typeof a) => {
                    const label = recap.recap_metadata?.bracket_label || '';
                    if (label.includes('🏆')) return 1; // Championship - top left
                    if (label.includes('🥉')) return 2; // 3rd place - top right
                    if (label.includes('🎖️')) return 3; // Consolation champ - bottom left
                    if (label.includes('🎯')) return 4; // 9th place - bottom right
                    return 5; // Others last
                  };
                  return getOrder(a) - getOrder(b);
                })
                .map((recap) => (
                  <RecapCard key={recap.matchup_id} recap={recap} />
                ))}
            </div>
          )}
        </section>
      )}

      {/* Empty state */}
      {!isOffseason && (!currentWeek?.matchups || currentWeek.matchups.length === 0) &&
        (!previousWeek?.recaps || previousWeek.recaps.length === 0) && (
          <div className="text-center py-16">
            <p className="text-gray-500 text-lg">No matchup data available yet.</p>
            <p className="text-gray-400 text-sm mt-2">
              Recaps and predictions are generated automatically during the season.
            </p>
          </div>
        )}
    </div>
  );
}
