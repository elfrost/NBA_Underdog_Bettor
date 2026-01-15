"""Dynamic bankroll management with adaptive Kelly sizing."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from config import get_settings
from src.db import get_db


class RiskLevel(Enum):
    """Risk levels for dynamic Kelly adjustment."""
    CRISIS = "crisis"      # Big drawdown, minimize risk
    CAUTIOUS = "cautious"  # After losses, reduce exposure
    NORMAL = "normal"      # Standard Kelly fraction
    AGGRESSIVE = "aggressive"  # Hot streak, well calibrated


@dataclass
class PerformanceMetrics:
    """Recent betting performance metrics."""
    # Win rates
    win_rate_l10: float = 0.0   # Last 10 picks
    win_rate_l20: float = 0.0   # Last 20 picks
    win_rate_l50: float = 0.0   # Last 50 picks
    win_rate_all: float = 0.0   # All time

    # Streaks
    current_streak: int = 0     # Positive = wins, negative = losses
    streak_type: str = ""       # "W" or "L"

    # ROI
    roi_l10: float = 0.0
    roi_l20: float = 0.0
    roi_all: float = 0.0

    # Bankroll
    total_wagered: float = 0.0
    total_pl: float = 0.0
    peak_bankroll: float = 0.0
    current_bankroll: float = 0.0
    drawdown_pct: float = 0.0   # Current drawdown from peak

    # Counts
    total_picks: int = 0
    wins: int = 0
    losses: int = 0

    def format_summary(self) -> str:
        """Format metrics for display."""
        streak_str = f"{self.streak_type}{abs(self.current_streak)}" if self.current_streak != 0 else "0"
        return (
            f"Record: {self.wins}-{self.losses} ({self.win_rate_all:.1%}) | "
            f"Streak: {streak_str} | "
            f"ROI: {self.roi_all:+.1%} | "
            f"Drawdown: {self.drawdown_pct:.1%}"
        )


@dataclass
class CalibrationMetrics:
    """Confidence level calibration metrics."""
    # Expected win rates by confidence
    expected_high: float = 0.70
    expected_medium: float = 0.55
    expected_low: float = 0.35

    # Actual win rates
    actual_high: float = 0.0
    actual_medium: float = 0.0
    actual_low: float = 0.0

    # Sample sizes
    count_high: int = 0
    count_medium: int = 0
    count_low: int = 0

    # Calibration scores (1.0 = perfectly calibrated)
    calibration_high: float = 1.0
    calibration_medium: float = 1.0
    calibration_low: float = 1.0
    overall_calibration: float = 1.0

    def format_summary(self) -> str:
        """Format calibration for display."""
        return (
            f"HIGH: {self.actual_high:.0%} vs {self.expected_high:.0%} ({self.count_high}) | "
            f"MED: {self.actual_medium:.0%} vs {self.expected_medium:.0%} ({self.count_medium}) | "
            f"Calibration: {self.overall_calibration:.2f}"
        )


class BankrollManager:
    """Manages bankroll with dynamic Kelly adjustment."""

    # Kelly adjustment factors
    STREAK_LOSS_THRESHOLD = 3     # Reduce after 3 consecutive losses
    STREAK_WIN_THRESHOLD = 5      # Slight reduction after 5 wins (avoid overconfidence)
    DRAWDOWN_CAUTION = 0.10       # 10% drawdown = cautious mode
    DRAWDOWN_CRISIS = 0.20        # 20% drawdown = crisis mode

    # Kelly multipliers by risk level
    RISK_MULTIPLIERS = {
        RiskLevel.CRISIS: 0.25,     # 25% of normal Kelly
        RiskLevel.CAUTIOUS: 0.50,   # 50% of normal Kelly
        RiskLevel.NORMAL: 1.0,      # Full Kelly fraction
        RiskLevel.AGGRESSIVE: 1.10, # 10% boost (capped)
    }

    def __init__(self, initial_bankroll: Optional[float] = None):
        self.settings = get_settings()
        self.initial_bankroll = initial_bankroll or self.settings.bankroll
        self._db = get_db()

    def get_performance_metrics(self) -> PerformanceMetrics:
        """Calculate current performance metrics from database."""
        results = self._db.get_all_results()
        metrics = PerformanceMetrics()

        if not results:
            metrics.current_bankroll = self.initial_bankroll
            metrics.peak_bankroll = self.initial_bankroll
            return metrics

        # Sort by date (newest first for streak calculation)
        sorted_results = sorted(results, key=lambda x: x.get('game_date', ''), reverse=True)

        # Calculate totals
        metrics.total_picks = len(results)
        metrics.wins = sum(1 for r in results if r.get('result') == 'WIN')
        metrics.losses = sum(1 for r in results if r.get('result') == 'LOSS')
        metrics.total_wagered = sum(r.get('bet_amount', 0) or 0 for r in results)
        metrics.total_pl = sum(r.get('profit_loss', 0) or 0 for r in results)

        # Win rates
        if metrics.total_picks > 0:
            metrics.win_rate_all = metrics.wins / metrics.total_picks

        # Last N win rates
        for n, attr in [(10, 'win_rate_l10'), (20, 'win_rate_l20'), (50, 'win_rate_l50')]:
            last_n = sorted_results[:n]
            if last_n:
                wins_n = sum(1 for r in last_n if r.get('result') == 'WIN')
                setattr(metrics, attr, wins_n / len(last_n))

        # ROI calculations
        if metrics.total_wagered > 0:
            metrics.roi_all = metrics.total_pl / metrics.total_wagered

        # Last 10/20 ROI
        for n, attr in [(10, 'roi_l10'), (20, 'roi_l20')]:
            last_n = sorted_results[:n]
            wagered_n = sum(r.get('bet_amount', 0) or 0 for r in last_n)
            pl_n = sum(r.get('profit_loss', 0) or 0 for r in last_n)
            if wagered_n > 0:
                setattr(metrics, attr, pl_n / wagered_n)

        # Current streak
        if sorted_results:
            first_result = sorted_results[0].get('result')
            streak = 0
            for r in sorted_results:
                if r.get('result') == first_result and first_result in ('WIN', 'LOSS'):
                    streak += 1
                else:
                    break
            metrics.current_streak = streak if first_result == 'WIN' else -streak
            metrics.streak_type = 'W' if first_result == 'WIN' else 'L'

        # Bankroll tracking
        metrics.current_bankroll = self.initial_bankroll + metrics.total_pl

        # Calculate peak bankroll (running max)
        running_total = self.initial_bankroll
        peak = self.initial_bankroll
        for r in reversed(sorted_results):  # Oldest first for running calculation
            running_total += r.get('profit_loss', 0) or 0
            peak = max(peak, running_total)
        metrics.peak_bankroll = peak

        # Drawdown
        if metrics.peak_bankroll > 0:
            metrics.drawdown_pct = (metrics.peak_bankroll - metrics.current_bankroll) / metrics.peak_bankroll

        return metrics

    def get_confidence_calibration(self) -> CalibrationMetrics:
        """Calculate confidence level calibration."""
        results = self._db.get_all_results()
        calibration = CalibrationMetrics()

        if not results:
            return calibration

        # Group by confidence level
        by_conf = {'high': [], 'medium': [], 'low': []}
        for r in results:
            conf = (r.get('confidence') or '').lower()
            if conf in by_conf:
                by_conf[conf].append(r)

        # Calculate actual win rates per confidence
        for conf, picks in by_conf.items():
            count = len(picks)
            if count == 0:
                continue

            wins = sum(1 for p in picks if p.get('result') == 'WIN')
            actual = wins / count

            if conf == 'high':
                calibration.count_high = count
                calibration.actual_high = actual
                if count >= 5:  # Need minimum sample
                    calibration.calibration_high = min(actual / calibration.expected_high, 1.5)
            elif conf == 'medium':
                calibration.count_medium = count
                calibration.actual_medium = actual
                if count >= 5:
                    calibration.calibration_medium = min(actual / calibration.expected_medium, 1.5)
            elif conf == 'low':
                calibration.count_low = count
                calibration.actual_low = actual
                if count >= 5:
                    calibration.calibration_low = min(actual / calibration.expected_low, 1.5)

        # Overall calibration (weighted by HIGH/MEDIUM since we bet those)
        total_bet = calibration.count_high + calibration.count_medium
        if total_bet > 0:
            calibration.overall_calibration = (
                calibration.calibration_high * calibration.count_high +
                calibration.calibration_medium * calibration.count_medium
            ) / total_bet

        return calibration

    def get_risk_assessment(self, metrics: Optional[PerformanceMetrics] = None) -> RiskLevel:
        """Determine current risk level based on performance."""
        if metrics is None:
            metrics = self.get_performance_metrics()

        # Crisis mode: significant drawdown
        if metrics.drawdown_pct >= self.DRAWDOWN_CRISIS:
            return RiskLevel.CRISIS

        # Cautious: moderate drawdown OR losing streak
        if metrics.drawdown_pct >= self.DRAWDOWN_CAUTION:
            return RiskLevel.CAUTIOUS
        if metrics.current_streak <= -self.STREAK_LOSS_THRESHOLD:
            return RiskLevel.CAUTIOUS

        # Aggressive: winning streak AND good calibration
        calibration = self.get_confidence_calibration()
        if (metrics.current_streak >= self.STREAK_WIN_THRESHOLD and
                calibration.overall_calibration >= 0.9 and
                metrics.win_rate_l10 >= 0.60):
            return RiskLevel.AGGRESSIVE

        return RiskLevel.NORMAL

    def calculate_dynamic_kelly(
        self,
        metrics: Optional[PerformanceMetrics] = None,
        calibration: Optional[CalibrationMetrics] = None,
    ) -> float:
        """Calculate dynamically adjusted Kelly fraction."""
        if metrics is None:
            metrics = self.get_performance_metrics()
        if calibration is None:
            calibration = self.get_confidence_calibration()

        base_kelly = self.settings.kelly_fraction
        risk_level = self.get_risk_assessment(metrics)

        # Apply risk multiplier
        adjusted_kelly = base_kelly * self.RISK_MULTIPLIERS[risk_level]

        # Apply calibration factor (if underperforming, reduce more)
        if calibration.overall_calibration < 0.8 and calibration.count_high + calibration.count_medium >= 10:
            adjusted_kelly *= calibration.overall_calibration

        # Apply bounds
        min_kelly = 0.05  # Never go below 5% of base
        max_kelly = base_kelly * 1.25  # Never exceed 125% of base

        return max(min_kelly, min(adjusted_kelly, max_kelly))

    def get_bankroll_context(self) -> dict:
        """Get full bankroll context for display/logging."""
        metrics = self.get_performance_metrics()
        calibration = self.get_confidence_calibration()
        risk_level = self.get_risk_assessment(metrics)
        dynamic_kelly = self.calculate_dynamic_kelly(metrics, calibration)

        return {
            "metrics": metrics,
            "calibration": calibration,
            "risk_level": risk_level,
            "base_kelly": self.settings.kelly_fraction,
            "dynamic_kelly": dynamic_kelly,
            "kelly_adjustment": dynamic_kelly / self.settings.kelly_fraction,
            "current_bankroll": metrics.current_bankroll,
        }

    def format_status(self) -> str:
        """Format current bankroll status for display."""
        ctx = self.get_bankroll_context()
        metrics = ctx["metrics"]
        risk = ctx["risk_level"]

        risk_emoji = {
            RiskLevel.CRISIS: "[red]CRISIS[/red]",
            RiskLevel.CAUTIOUS: "[yellow]CAUTIOUS[/yellow]",
            RiskLevel.NORMAL: "[green]NORMAL[/green]",
            RiskLevel.AGGRESSIVE: "[blue]AGGRESSIVE[/blue]",
        }

        return (
            f"Bankroll: ${metrics.current_bankroll:,.0f} | "
            f"Risk: {risk_emoji.get(risk, risk.value)} | "
            f"Kelly: {ctx['dynamic_kelly']:.1%} ({ctx['kelly_adjustment']:.0%} of base)"
        )


# Singleton instance
_manager: Optional[BankrollManager] = None


def get_bankroll_manager(initial_bankroll: Optional[float] = None) -> BankrollManager:
    """Get bankroll manager instance (singleton)."""
    global _manager
    if _manager is None:
        _manager = BankrollManager(initial_bankroll)
    return _manager
