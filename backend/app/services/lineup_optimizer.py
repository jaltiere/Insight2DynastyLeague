"""Optimal lineup calculation for max potential points."""
from typing import List, Dict, Any
from collections import defaultdict


class LineupOptimizer:
    """Calculate the optimal lineup given player points and positions."""

    # Position priorities for FLEX spots (higher score takes precedence)
    FLEX_POSITIONS = ["RB", "WR", "TE"]
    SUPER_FLEX_POSITIONS = ["QB", "RB", "WR", "TE"]

    def __init__(self, roster_positions: List[str]):
        """
        Initialize with league roster position requirements.

        Args:
            roster_positions: List of position slots from league settings
                             e.g., ["QB", "RB", "RB", "WR", "WR", "WR", "TE", "FLEX", "FLEX", "SUPER_FLEX", "K", "DEF"]
        """
        self.roster_positions = roster_positions or []

    def calculate_optimal_lineup(self, player_points: List[Dict[str, Any]]) -> float:
        """
        Calculate the maximum potential points from all available players.

        Args:
            player_points: List of dicts with keys: player_id, position, points
                          e.g., [{"player_id": "123", "position": "RB", "points": 15.3}, ...]

        Returns:
            Maximum potential points from optimal lineup
        """
        if not player_points or not self.roster_positions:
            return 0.0

        # Group players by position and sort by points (descending)
        players_by_position = defaultdict(list)
        for player in player_points:
            position = player.get("position")
            points = player.get("points", 0) or 0
            if position:
                players_by_position[position].append({
                    "player_id": player.get("player_id"),
                    "position": position,
                    "points": points
                })

        # Sort each position by points descending
        for position in players_by_position:
            players_by_position[position].sort(key=lambda x: x["points"], reverse=True)

        # Track which players have been used
        used_player_ids = set()
        total_points = 0.0

        # Count position requirements
        position_counts = defaultdict(int)
        flex_count = 0
        super_flex_count = 0

        for pos in self.roster_positions:
            if pos == "FLEX":
                flex_count += 1
            elif pos == "SUPER_FLEX":
                super_flex_count += 1
            else:
                position_counts[pos] += 1

        # First pass: Fill specific position requirements
        for position, count in position_counts.items():
            available = [p for p in players_by_position.get(position, [])
                        if p["player_id"] not in used_player_ids]

            for i in range(min(count, len(available))):
                player = available[i]
                total_points += player["points"]
                used_player_ids.add(player["player_id"])

        # Second pass: Fill FLEX spots (RB/WR/TE)
        if flex_count > 0:
            flex_candidates = []
            for position in self.FLEX_POSITIONS:
                flex_candidates.extend([
                    p for p in players_by_position.get(position, [])
                    if p["player_id"] not in used_player_ids
                ])

            # Sort by points and take top flex_count players
            flex_candidates.sort(key=lambda x: x["points"], reverse=True)
            for i in range(min(flex_count, len(flex_candidates))):
                player = flex_candidates[i]
                total_points += player["points"]
                used_player_ids.add(player["player_id"])

        # Third pass: Fill SUPER_FLEX spots (QB/RB/WR/TE)
        if super_flex_count > 0:
            superflex_candidates = []
            for position in self.SUPER_FLEX_POSITIONS:
                superflex_candidates.extend([
                    p for p in players_by_position.get(position, [])
                    if p["player_id"] not in used_player_ids
                ])

            # Sort by points and take top super_flex_count players
            superflex_candidates.sort(key=lambda x: x["points"], reverse=True)
            for i in range(min(super_flex_count, len(superflex_candidates))):
                player = superflex_candidates[i]
                total_points += player["points"]
                used_player_ids.add(player["player_id"])

        return round(total_points, 2)
