"""Configuration settings for the NBA Underdog Betting system."""

import os
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment."""

    # BallDon'tLie API
    balldontlie_api_key: str = ""
    balldontlie_base_url: str = "https://api.balldontlie.io/v1"

    # The Odds API
    odds_api_key: str = ""
    odds_base_url: str = "https://api.the-odds-api.com/v4"

    # OpenRouter for AI
    openrouter_api_key: str = ""
    openrouter_model: str = "anthropic/claude-3.5-sonnet"

    # Underdog filter settings
    min_spread: float = 3.5
    max_spread: float = 7.5
    min_ml_odds: int = 150
    max_ml_odds: int = 300

    # v0.8.0 Optimization filters (based on backtesting)
    min_underdog_rest: int = 2  # Require underdog to have 2+ days rest (100% of wins had this)
    high_confidence_only: bool = True  # Skip MEDIUM confidence picks (-61.7% ROI)
    calibration_factor: float = 0.90  # Slight deflation (0.75 was too aggressive)

    # Analysis settings
    lookback_days: int = 7  # For recent form analysis

    # Kelly Criterion / Bankroll settings
    bankroll: float = 1000.0  # Total bankroll in dollars
    kelly_fraction: float = 0.15  # Reduced from 0.25 (more conservative due to calibration issues)
    max_bet_pct: float = 0.03  # Reduced from 5% to 3% max per bet
    min_bet_pct: float = 0.005  # Min 0.5% ($5 on $1000) to bet

    # Notifications
    notifications_enabled: bool = True
    notify_high_only: bool = True  # Only notify for HIGH confidence picks

    # Discord
    discord_webhook_url: str = ""

    # Telegram (future)
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
