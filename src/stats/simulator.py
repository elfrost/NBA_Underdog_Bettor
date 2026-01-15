"""Monte Carlo simulation for game outcomes."""

import random
from dataclasses import dataclass
from typing import Optional

from .ratings import TeamRatings, get_matchup_analysis


@dataclass
class SimulationResult:
    """Results from Monte Carlo simulation."""
    simulations: int = 0

    # Win probabilities
    underdog_win_pct: float = 0.0
    favorite_win_pct: float = 0.0

    # Spread coverage
    underdog_cover_pct: float = 0.0  # Covers the spread
    push_pct: float = 0.0

    # Score distributions
    underdog_avg_score: float = 0.0
    favorite_avg_score: float = 0.0
    avg_margin: float = 0.0
    margin_std: float = 0.0

    # Percentiles
    margin_10th: float = 0.0  # 10% of simulations have margin <= this
    margin_90th: float = 0.0  # 90% of simulations have margin <= this

    def format_for_prompt(self) -> str:
        """Format simulation results for AI prompt."""
        return (
            f"=== SIMULATION ({self.simulations} runs) ===\n"
            f"Underdog win: {self.underdog_win_pct:.1%}\n"
            f"Cover spread: {self.underdog_cover_pct:.1%}\n"
            f"Avg margin: {self.avg_margin:+.1f} (std: {self.margin_std:.1f})\n"
            f"Score range: {self.underdog_avg_score:.0f}-{self.favorite_avg_score:.0f}"
        )

    def format_short(self) -> str:
        """Short format for display."""
        return (
            f"Win {self.underdog_win_pct:.0%} | "
            f"Cover {self.underdog_cover_pct:.0%} | "
            f"Margin {self.avg_margin:+.1f}"
        )


class MonteCarloSimulator:
    """Monte Carlo game simulator."""

    # Standard deviation for game scoring (NBA games typically have ~12 point std)
    SCORE_STD = 12.0

    def __init__(self, simulations: int = 1000):
        self.simulations = simulations

    def simulate_game(
        self,
        underdog_ratings: TeamRatings,
        favorite_ratings: TeamRatings,
        spread: float,
        is_underdog_home: bool,
    ) -> SimulationResult:
        """Run Monte Carlo simulation for a game."""
        result = SimulationResult(simulations=self.simulations)

        # Get matchup analysis for expected scores
        matchup = get_matchup_analysis(
            underdog_ratings,
            favorite_ratings,
            is_underdog_home,
        )

        underdog_mean = matchup["underdog_expected_score"]
        favorite_mean = matchup["favorite_expected_score"]

        underdog_wins = 0
        covers = 0
        pushes = 0
        margins = []
        underdog_scores = []
        favorite_scores = []

        for _ in range(self.simulations):
            # Simulate scores with normal distribution
            underdog_score = random.gauss(underdog_mean, self.SCORE_STD)
            favorite_score = random.gauss(favorite_mean, self.SCORE_STD)

            # Ensure non-negative scores
            underdog_score = max(70, underdog_score)
            favorite_score = max(70, favorite_score)

            margin = favorite_score - underdog_score  # Positive = favorite wins
            margins.append(margin)
            underdog_scores.append(underdog_score)
            favorite_scores.append(favorite_score)

            # Track outcomes
            if underdog_score > favorite_score:
                underdog_wins += 1

            # Spread coverage (underdog gets points)
            # If spread is +5.5, underdog covers if they lose by 5 or less OR win
            adjusted_margin = margin - spread  # If negative, underdog covers
            if adjusted_margin < 0:
                covers += 1
            elif adjusted_margin == 0:
                pushes += 1

        # Calculate results
        result.underdog_win_pct = underdog_wins / self.simulations
        result.favorite_win_pct = 1 - result.underdog_win_pct
        result.underdog_cover_pct = covers / self.simulations
        result.push_pct = pushes / self.simulations

        result.underdog_avg_score = sum(underdog_scores) / self.simulations
        result.favorite_avg_score = sum(favorite_scores) / self.simulations
        result.avg_margin = sum(margins) / self.simulations

        # Standard deviation
        if len(margins) > 1:
            mean_margin = result.avg_margin
            variance = sum((m - mean_margin) ** 2 for m in margins) / (len(margins) - 1)
            result.margin_std = variance ** 0.5

        # Percentiles
        sorted_margins = sorted(margins)
        result.margin_10th = sorted_margins[int(self.simulations * 0.1)]
        result.margin_90th = sorted_margins[int(self.simulations * 0.9)]

        return result

    def calculate_ev(
        self,
        sim_result: SimulationResult,
        spread: float,
        odds: int,
        bet_amount: float,
    ) -> float:
        """Calculate expected value based on simulation."""
        # Convert American odds to probability
        if odds > 0:
            win_payout = bet_amount * (odds / 100)
        else:
            win_payout = bet_amount * (100 / abs(odds))

        # EV = (win_prob * win_payout) - (lose_prob * bet_amount)
        win_prob = sim_result.underdog_cover_pct
        lose_prob = 1 - win_prob - sim_result.push_pct

        ev = (win_prob * win_payout) - (lose_prob * bet_amount)
        return ev
