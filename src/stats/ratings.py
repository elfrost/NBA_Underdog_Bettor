"""Team ratings calculation from game data."""

from dataclasses import dataclass
from typing import Optional

from src.models.schemas import Game, Team


# NBA league averages (2023-24 season approximation)
LEAGUE_AVG_PACE = 100.0  # possessions per game
LEAGUE_AVG_PPG = 114.0  # points per game


@dataclass
class TeamRatings:
    """Advanced team ratings."""
    team: str
    games_played: int = 0

    # Offensive stats
    points_per_game: float = 0.0
    offensive_rating: float = 100.0  # points per 100 possessions

    # Defensive stats
    points_allowed: float = 0.0
    defensive_rating: float = 100.0  # points allowed per 100 possessions

    # Net rating
    net_rating: float = 0.0  # offensive - defensive

    # Pace
    pace: float = 100.0  # estimated possessions per game

    # Home/Away splits
    home_margin: float = 0.0
    away_margin: float = 0.0

    # Recent form (last 5)
    last_5_margin: float = 0.0

    def format_for_prompt(self) -> str:
        """Format ratings for AI prompt."""
        if self.games_played == 0:
            return f"{self.team}: No recent data"

        return (
            f"{self.team}: "
            f"Off {self.offensive_rating:.1f}, "
            f"Def {self.defensive_rating:.1f}, "
            f"Net {self.net_rating:+.1f}, "
            f"Pace {self.pace:.1f}, "
            f"PPG {self.points_per_game:.1f}"
        )


def calculate_team_ratings(team: Team, games: list[Game]) -> TeamRatings:
    """Calculate team ratings from recent games."""
    ratings = TeamRatings(team=team.abbreviation)

    if not games:
        return ratings

    completed = [g for g in games if g.status == "Final" and g.home_score and g.away_score]

    if not completed:
        return ratings

    ratings.games_played = len(completed)

    total_scored = 0
    total_allowed = 0
    total_pace = 0
    home_margins = []
    away_margins = []

    for game in completed:
        is_home = game.home_team.id == team.id
        team_score = game.home_score if is_home else game.away_score
        opp_score = game.away_score if is_home else game.home_score
        margin = team_score - opp_score

        total_scored += team_score
        total_allowed += opp_score

        # Estimate pace from total points (rough approximation)
        total_points = team_score + opp_score
        estimated_pace = (total_points / 2) * (LEAGUE_AVG_PACE / LEAGUE_AVG_PPG)
        total_pace += estimated_pace

        if is_home:
            home_margins.append(margin)
        else:
            away_margins.append(margin)

    n = ratings.games_played

    # Basic stats
    ratings.points_per_game = total_scored / n
    ratings.points_allowed = total_allowed / n
    ratings.pace = total_pace / n

    # Ratings (per 100 possessions)
    if ratings.pace > 0:
        ratings.offensive_rating = (ratings.points_per_game / ratings.pace) * 100
        ratings.defensive_rating = (ratings.points_allowed / ratings.pace) * 100
        ratings.net_rating = ratings.offensive_rating - ratings.defensive_rating

    # Home/Away splits
    if home_margins:
        ratings.home_margin = sum(home_margins) / len(home_margins)
    if away_margins:
        ratings.away_margin = sum(away_margins) / len(away_margins)

    # Last 5 margin
    recent = completed[:5]
    if recent:
        recent_margins = []
        for game in recent:
            is_home = game.home_team.id == team.id
            team_score = game.home_score if is_home else game.away_score
            opp_score = game.away_score if is_home else game.home_score
            recent_margins.append(team_score - opp_score)
        ratings.last_5_margin = sum(recent_margins) / len(recent_margins)

    return ratings


def get_matchup_analysis(
    underdog_ratings: TeamRatings,
    favorite_ratings: TeamRatings,
    is_underdog_home: bool,
) -> dict:
    """Analyze matchup between two teams."""
    # Pace prediction (average of both teams)
    expected_pace = (underdog_ratings.pace + favorite_ratings.pace) / 2

    # Expected points (adjusted for opponent defense)
    underdog_off_vs_fav_def = (
        underdog_ratings.offensive_rating + favorite_ratings.defensive_rating
    ) / 2
    favorite_off_vs_und_def = (
        favorite_ratings.offensive_rating + underdog_ratings.defensive_rating
    ) / 2

    # Home court advantage (~3 points)
    home_advantage = 3.0
    if is_underdog_home:
        underdog_adj = home_advantage / 2
        favorite_adj = -home_advantage / 2
    else:
        underdog_adj = -home_advantage / 2
        favorite_adj = home_advantage / 2

    # Expected scores
    underdog_expected = (underdog_off_vs_fav_def * expected_pace / 100) + underdog_adj
    favorite_expected = (favorite_off_vs_und_def * expected_pace / 100) + favorite_adj

    # Expected margin (favorite perspective)
    expected_margin = favorite_expected - underdog_expected

    return {
        "expected_pace": expected_pace,
        "underdog_expected_score": underdog_expected,
        "favorite_expected_score": favorite_expected,
        "expected_margin": expected_margin,
        "pace_differential": abs(underdog_ratings.pace - favorite_ratings.pace),
    }
