import type { MatchupRecap } from '../types';

interface RecapCardProps {
  recap: MatchupRecap;
}

export default function RecapCard({ recap }: RecapCardProps) {
  const winner = (recap.home_score || 0) > (recap.away_score || 0) ? recap.home_team : recap.away_team;
  const bracketLabel = recap.recap_metadata?.bracket_label;
  const matchType = recap.recap_metadata?.match_type;
  const hasStandingsImpact = recap.recap_metadata?.standings_impact;

  return (
    <div className="bg-white rounded-lg shadow-md p-5 hover:shadow-lg transition-shadow">
      {/* Header with bracket label */}
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-gray-900">
          {bracketLabel || `Week ${recap.week} Result`}
        </h3>
        <div className="flex gap-2">
          {matchType === 'playoff' && !bracketLabel && (
            <span className="bg-purple-100 text-purple-800 text-xs font-medium px-2 py-0.5 rounded">
              Playoff
            </span>
          )}
          {matchType === 'consolation' && !bracketLabel && (
            <span className="bg-orange-100 text-orange-800 text-xs font-medium px-2 py-0.5 rounded">
              Consolation
            </span>
          )}
          {hasStandingsImpact && (
            <span className="bg-green-100 text-green-800 text-xs font-medium px-2 py-0.5 rounded">
              Standings Impact
            </span>
          )}
        </div>
      </div>

      {/* Final Score */}
      <div className="space-y-3 mb-4">
        {/* Home Team */}
        <div className="flex items-center justify-between">
          <div className="flex-1">
            <p className={`font-semibold ${winner === recap.home_team ? 'text-green-600' : 'text-gray-700'}`}>
              {recap.home_team}
              {winner === recap.home_team && ' ✓'}
            </p>
          </div>
          <p className={`text-xl font-bold ${winner === recap.home_team ? 'text-green-600' : 'text-gray-600'}`}>
            {recap.home_score?.toFixed(2) || '0.00'}
          </p>
        </div>

        <div className="border-t border-gray-200" />

        {/* Away Team */}
        <div className="flex items-center justify-between">
          <div className="flex-1">
            <p className={`font-semibold ${winner === recap.away_team ? 'text-green-600' : 'text-gray-700'}`}>
              {recap.away_team}
              {winner === recap.away_team && ' ✓'}
            </p>
          </div>
          <p className={`text-xl font-bold ${winner === recap.away_team ? 'text-green-600' : 'text-gray-600'}`}>
            {recap.away_score?.toFixed(2) || '0.00'}
          </p>
        </div>
      </div>

      {/* Recap Text */}
      {recap.recap_text ? (
        <div className="p-3 bg-gray-50 rounded-lg">
          <p className="text-sm text-gray-700 leading-relaxed">{recap.recap_text}</p>
        </div>
      ) : (
        <div className="p-3 bg-yellow-50 rounded-lg">
          <p className="text-sm text-gray-600 italic">Recap generation in progress...</p>
        </div>
      )}

      {/* Standings Delta */}
      {recap.recap_metadata?.standings_impact && (
        <div className="mt-3 text-xs text-gray-600 bg-blue-50 p-2 rounded">
          📊 {recap.recap_metadata.standings_impact}
        </div>
      )}

      {/* H2H History */}
      {recap.recap_metadata?.h2h_history && (
        <div className="mt-2 text-xs text-gray-500 text-center">
          {recap.recap_metadata.h2h_history}
        </div>
      )}
    </div>
  );
}
