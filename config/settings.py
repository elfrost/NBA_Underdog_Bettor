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

    # Analysis settings
    lookback_days: int = 7  # For recent form analysis

    # Kelly Criterion / Bankroll settings
    bankroll: float = 1000.0  # Total bankroll in dollars
    kelly_fraction: float = 0.25  # Quarter Kelly (conservative)
    max_bet_pct: float = 0.05  # Max 5% of bankroll per bet
    min_bet_pct: float = 0.005  # Min 0.5% ($5 on $1000) to bet

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
