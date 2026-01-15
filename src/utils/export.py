"""Export utilities for saving recommendations."""

from datetime import datetime
from pathlib import Path

import pandas as pd

from src.models.schemas import BetRecommendation


def export_recommendations_to_csv(
    recommendations: list[BetRecommendation],
    output_dir: str = "output",
) -> Path:
    """Export recommendations to a CSV file.

    Args:
        recommendations: List of BetRecommendation objects
        output_dir: Directory to save the CSV file

    Returns:
        Path to the created CSV file
    """
    # Create output directory if it doesn't exist
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    # Build data for DataFrame
    data = []
    for reco in recommendations:
        pick = reco.pick
        data.append({
            "date": pick.game.date.strftime("%Y-%m-%d"),
            "time": pick.game.date.strftime("%H:%M"),
            "game": f"{pick.game.away_team.abbreviation} @ {pick.game.home_team.abbreviation}",
            "underdog": pick.underdog.name,
            "underdog_abbr": pick.underdog.abbreviation,
            "favorite": pick.favorite.name,
            "bet_type": pick.bet_type.value.upper(),
            "line": pick.line,
            "odds": pick.odds,
            "confidence": reco.confidence.value,
            "should_bet": reco.should_bet,
            "bankroll_pct": reco.bankroll_pct,
            "bet_amount": reco.bet_amount,
            "implied_prob": reco.implied_prob,
            "estimated_prob": reco.estimated_prob,
            "expected_value": reco.expected_value,
            "edge_factors": "; ".join(reco.edge_factors),
            "risk_factors": "; ".join(reco.risk_factors),
            "reasoning": reco.reasoning,
            "underdog_b2b": pick.underdog_context.is_back_to_back,
            "underdog_rest": pick.underdog_context.days_rest,
            "underdog_form": pick.underdog_context.recent_record,
            "favorite_b2b": pick.favorite_context.is_back_to_back,
            "favorite_rest": pick.favorite_context.days_rest,
            "favorite_form": pick.favorite_context.recent_record,
        })

    # Create DataFrame
    df = pd.DataFrame(data)

    # Generate filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = output_path / f"picks_{timestamp}.csv"

    # Save to CSV
    df.to_csv(filename, index=False)

    return filename
