"""Database models for pick tracking."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class PickRecord:
    """Record of a betting pick."""
    id: Optional[int] = None
    created_at: datetime = None
    game_date: datetime = None
    game_id: int = 0

    # Teams
    home_team: str = ""
    away_team: str = ""
    underdog: str = ""
    favorite: str = ""

    # Bet details
    bet_type: str = ""  # SPREAD or MONEYLINE
    line: float = 0.0
    odds: int = 0

    # AI analysis
    confidence: str = ""  # low, medium, high
    edge_factors: str = ""
    risk_factors: str = ""
    reasoning: str = ""

    # Kelly sizing
    implied_prob: float = 0.0
    estimated_prob: float = 0.0
    bankroll_pct: float = 0.0
    bet_amount: float = 0.0
    expected_value: float = 0.0
    should_bet: bool = False

    # Context
    underdog_b2b: bool = False
    underdog_rest: int = 0
    underdog_form: str = ""
    favorite_b2b: bool = False
    favorite_rest: int = 0
    favorite_form: str = ""

    # v0.8.0: Shadow betting for forward testing
    is_shadow: int = 0  # 0 = real bet, 1 = shadow bet (filtered out)
    filter_reason: str = ""  # Why it was filtered (for analysis)


@dataclass
class ResultRecord:
    """Record of a pick result after game completion."""
    id: Optional[int] = None
    pick_id: int = 0
    updated_at: datetime = None

    # Final scores
    home_score: int = 0
    away_score: int = 0

    # Result
    result: str = ""  # WIN, LOSS, PUSH
    actual_margin: float = 0.0  # For spread bets

    # P&L
    profit_loss: float = 0.0  # In dollars
    roi_pct: float = 0.0  # Return on investment %
