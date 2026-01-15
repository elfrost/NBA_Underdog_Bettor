"""Kelly Criterion calculator for optimal bet sizing."""

from src.models.schemas import Confidence


# Edge adjustment based on confidence level
CONFIDENCE_EDGE = {
    Confidence.HIGH: 0.08,    # +8% edge for HIGH confidence
    Confidence.MEDIUM: 0.04,  # +4% edge for MEDIUM confidence
    Confidence.LOW: 0.0,      # No edge for LOW confidence (don't bet)
}


def implied_probability(american_odds: int) -> float:
    """Convert American odds to implied probability.

    Args:
        american_odds: American format odds (+150, -110, etc.)

    Returns:
        Implied probability as decimal (0.0 to 1.0)
    """
    if american_odds > 0:
        # Underdog: +150 -> 100 / (150 + 100) = 0.4
        return 100 / (american_odds + 100)
    else:
        # Favorite: -110 -> 110 / (110 + 100) = 0.524
        return abs(american_odds) / (abs(american_odds) + 100)


def decimal_odds_from_american(american_odds: int) -> float:
    """Convert American odds to decimal odds.

    Args:
        american_odds: American format odds (+150, -110, etc.)

    Returns:
        Decimal odds (e.g., 2.5 for +150)
    """
    if american_odds > 0:
        return (american_odds / 100) + 1
    else:
        return (100 / abs(american_odds)) + 1


def calculate_kelly(
    american_odds: int,
    win_probability: float,
) -> float:
    """Calculate Kelly Criterion optimal bet fraction.

    Formula: f* = (bp - q) / b
    where:
        b = decimal odds - 1 (potential profit per unit wagered)
        p = probability of winning
        q = probability of losing (1 - p)

    Args:
        american_odds: American format odds (+150, -110, etc.)
        win_probability: Estimated probability of winning (0.0 to 1.0)

    Returns:
        Optimal fraction of bankroll to bet (can be negative if no edge)
    """
    decimal_odds = decimal_odds_from_american(american_odds)
    b = decimal_odds - 1  # Profit per unit
    p = win_probability
    q = 1 - p

    kelly = (b * p - q) / b
    return kelly


def estimate_win_probability(
    american_odds: int,
    confidence: Confidence,
) -> float:
    """Estimate win probability based on implied odds + confidence edge.

    Args:
        american_odds: American format odds
        confidence: AI confidence level (HIGH/MEDIUM/LOW)

    Returns:
        Estimated win probability (0.0 to 1.0)
    """
    implied_prob = implied_probability(american_odds)
    edge = CONFIDENCE_EDGE.get(confidence, 0.0)

    # Add edge to implied probability, cap at 0.95
    estimated_prob = min(implied_prob + edge, 0.95)
    return estimated_prob


def calculate_bet_sizing(
    american_odds: int,
    confidence: Confidence,
    bankroll: float,
    kelly_fraction: float = 0.25,
    max_bet_pct: float = 0.05,
    min_bet_pct: float = 0.005,
) -> dict:
    """Calculate optimal bet size using Kelly Criterion.

    Args:
        american_odds: American format odds
        confidence: AI confidence level
        bankroll: Total bankroll in dollars
        kelly_fraction: Fraction of Kelly to use (0.25 = quarter Kelly)
        max_bet_pct: Maximum bet as % of bankroll (0.05 = 5%)
        min_bet_pct: Minimum bet as % of bankroll (0.005 = 0.5%)

    Returns:
        Dictionary with sizing details:
        - implied_prob: Market implied probability
        - estimated_prob: Our estimated win probability
        - full_kelly_pct: Full Kelly percentage
        - adjusted_kelly_pct: After applying kelly_fraction
        - final_bet_pct: After applying caps
        - bet_amount: Dollar amount to bet
        - expected_value: EV of the bet
        - should_bet: Whether we recommend betting
    """
    # Calculate probabilities
    implied_prob = implied_probability(american_odds)
    estimated_prob = estimate_win_probability(american_odds, confidence)

    # Calculate full Kelly
    full_kelly = calculate_kelly(american_odds, estimated_prob)

    # Apply Kelly fraction (e.g., quarter Kelly)
    adjusted_kelly = full_kelly * kelly_fraction

    # Apply caps
    if adjusted_kelly <= 0:
        final_bet_pct = 0.0
        should_bet = False
    elif adjusted_kelly < min_bet_pct:
        final_bet_pct = 0.0
        should_bet = False
    else:
        final_bet_pct = min(adjusted_kelly, max_bet_pct)
        should_bet = True

    # Calculate dollar amount
    bet_amount = round(bankroll * final_bet_pct, 2)

    # Calculate expected value
    decimal_odds = decimal_odds_from_american(american_odds)
    potential_win = bet_amount * (decimal_odds - 1)
    ev = (estimated_prob * potential_win) - ((1 - estimated_prob) * bet_amount)

    return {
        "implied_prob": round(implied_prob, 4),
        "estimated_prob": round(estimated_prob, 4),
        "full_kelly_pct": round(full_kelly * 100, 2),
        "adjusted_kelly_pct": round(adjusted_kelly * 100, 2),
        "final_bet_pct": round(final_bet_pct * 100, 2),
        "bet_amount": bet_amount,
        "expected_value": round(ev, 2),
        "should_bet": should_bet,
    }
