import type { MatchupRecap } from '../types';

interface PredictionCardProps {
  matchup: MatchupRecap;
}

export default function PredictionCard({ matchup }: PredictionCardProps) {
  const projectedHome = matchup.recap_metadata?.projected_scores?.home || 0;
  const projectedAway = matchup.recap_metadata?.projected_scores?.away || 0;
  const predictedWinner = projectedHome > projectedAway ? matchup.home_team : matchup.away_team;

  return (
    <div className="bg-white rounded-lg shadow-md p-6 hover:shadow-lg transition-shadow">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900">
          Matchup Preview
        </h3>
        {matchup.recap_metadata?.standings_implications && (
          <span className="bg-blue-100 text-blue-800 text-xs font-medium px-2.5 py-0.5 rounded">
            Playoff Race
          </span>
        )}
      </div>

      {/* Teams and Projected Scores */}
      <div className="space-y-4 mb-4">
        {/* Home Team */}
        <div className="flex items-center justify-between">
          <div className="flex-1">
            <p className="font-semibold text-gray-900">{matchup.home_team}</p>
            <p className="text-sm text-gray-600">{matchup.recap_metadata?.home_record || ''}</p>
          </div>
          <div className="text-right">
            <p className="text-2xl font-bold text-gray-900">{projectedHome.toFixed(1)}</p>
            <p className="text-xs text-gray-500">projected</p>
          </div>
        </div>

        <div className="border-t border-gray-200 my-2" />

        {/* Away Team */}
        <div className="flex items-center justify-between">
          <div className="flex-1">
            <p className="font-semibold text-gray-900">{matchup.away_team}</p>
            <p className="text-sm text-gray-600">{matchup.recap_metadata?.away_record || ''}</p>
          </div>
          <div className="text-right">
            <p className="text-2xl font-bold text-gray-900">{projectedAway.toFixed(1)}</p>
            <p className="text-xs text-gray-500">projected</p>
          </div>
        </div>
      </div>

      {/* Prediction Text */}
      {matchup.predictions_text && (
        <div className="mt-4 p-4 bg-gray-50 rounded-lg">
          <p className="text-sm text-gray-700 italic">{matchup.predictions_text}</p>
        </div>
      )}

      {/* Predicted Winner */}
      {!matchup.predictions_text && (
        <div className="mt-4 text-center">
          <p className="text-sm text-gray-600">
            Prediction: <span className="font-semibold text-gray-900">{predictedWinner}</span>
          </p>
        </div>
      )}

      {/* H2H History */}
      {matchup.recap_metadata?.h2h_history && (
        <div className="mt-3 text-xs text-gray-500 text-center">
          {matchup.recap_metadata.h2h_history}
        </div>
      )}
    </div>
  );
}
