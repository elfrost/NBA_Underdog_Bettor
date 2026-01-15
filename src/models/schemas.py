"""Pydantic schemas for NBA betting data."""

from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class BetType(str, Enum):
    """Type of bet."""
    SPREAD = "spread"
    MONEYLINE = "moneyline"


class Confidence(str, Enum):
    """Confidence level for picks."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Team(BaseModel):
    """NBA Team."""
    id: int
    name: str
    abbreviation: str
    conference: str | None = None
    division: str | None = None


class Game(BaseModel):
    """NBA Game information."""
    id: int
    date: datetime
    home_team: Team
    away_team: Team
    status: str = "scheduled"
    home_score: int | None = None
    away_score: int | None = None


class Odds(BaseModel):
    """Betting odds for a game."""
    game_id: int
    bookmaker: str
    home_spread: float
    away_spread: float
    home_spread_odds: int
    away_spread_odds: int
    home_ml: int
    away_ml: int
    total: float | None = None
    timestamp: datetime = Field(default_factory=datetime.now)


class TeamContext(BaseModel):
    """Context about a team for analysis."""
    team: Team
    is_back_to_back: bool = False
    days_rest: int = 1
    recent_record: str = ""  # e.g., "3-2 L5"
    recent_form: str = ""  # e.g., "W-W-L-W-L"
    injuries: list[str] = Field(default_factory=list)

    # Advanced stats (v0.5.0)
    offensive_rating: float = 0.0
    defensive_rating: float = 0.0
    net_rating: float = 0.0
    pace: float = 100.0
    points_per_game: float = 0.0


class UnderdogPick(BaseModel):
    """Identified underdog opportunity."""
    game: Game
    underdog: Team
    favorite: Team
    bet_type: BetType
    line: float  # spread value or ML odds
    odds: int  # -110, +150, etc.
    underdog_context: TeamContext
    favorite_context: TeamContext


class BetRecommendation(BaseModel):
    """AI-generated bet recommendation."""
    pick: UnderdogPick
    confidence: Confidence
    reasoning: str
    edge_factors: list[str] = Field(default_factory=list)
    risk_factors: list[str] = Field(default_factory=list)
    suggested_units: float = 1.0
    # Kelly Criterion fields (populated post-AI analysis)
    implied_prob: float = 0.0
    estimated_prob: float = 0.0
    bankroll_pct: float = 0.0
    bet_amount: float = 0.0
    expected_value: float = 0.0
    should_bet: bool = False

    # Simulation fields (v0.5.0)
    sim_win_pct: float = 0.0
    sim_cover_pct: float = 0.0
    sim_avg_margin: float = 0.0
    sim_ev: float = 0.0
