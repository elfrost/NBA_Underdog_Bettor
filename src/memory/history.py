"""Historical pick tracking and pattern analysis."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

from src.db import get_db


@dataclass
class TeamStats:
    """Statistics for a specific team."""
    team: str
    total_picks: int = 0
    wins: int = 0
    losses: int = 0
    pushes: int = 0
    total_pl: float = 0.0

    # By bet type
    spread_record: str = "0-0"
    spread_pl: float = 0.0
    ml_record: str = "0-0"
    ml_pl: float = 0.0

    # As underdog specifically
    as_underdog_record: str = "0-0"
    as_underdog_pl: float = 0.0

    @property
    def win_rate(self) -> float:
        """Calculate win rate."""
        total = self.wins + self.losses
        return self.wins / total if total > 0 else 0.0

    @property
    def record(self) -> str:
        """Return W-L record string."""
        return f"{self.wins}-{self.losses}"


@dataclass
class HistoricalContext:
    """Historical context to pass to the agent."""
    # Overall performance
    total_picks: int = 0
    overall_record: str = "0-0"
    overall_win_rate: float = 0.0
    overall_pl: float = 0.0
    overall_roi: float = 0.0

    # By confidence level
    high_conf_record: str = "0-0"
    high_conf_win_rate: float = 0.0
    medium_conf_record: str = "0-0"
    medium_conf_win_rate: float = 0.0

    # Current team stats (if available)
    team_stats: Optional[TeamStats] = None

    # Recent streak
    last_5_record: str = "0-0"
    current_streak: str = ""  # e.g., "W3" or "L2"

    def format_for_prompt(self) -> str:
        """Format historical context for the AI prompt."""
        lines = []

        if self.total_picks == 0:
            return "No historical picks recorded yet."

        lines.append(f"=== YOUR BETTING HISTORY ===")
        lines.append(f"Overall: {self.overall_record} ({self.overall_win_rate:.1%} win rate)")
        lines.append(f"P&L: ${self.overall_pl:+.2f} (ROI: {self.overall_roi:+.1%})")
        lines.append(f"Last 5: {self.last_5_record} | Streak: {self.current_streak or 'N/A'}")

        if self.high_conf_record != "0-0":
            lines.append(f"HIGH confidence: {self.high_conf_record} ({self.high_conf_win_rate:.1%})")
        if self.medium_conf_record != "0-0":
            lines.append(f"MEDIUM confidence: {self.medium_conf_record} ({self.medium_conf_win_rate:.1%})")

        if self.team_stats and self.team_stats.total_picks > 0:
            ts = self.team_stats
            lines.append(f"")
            lines.append(f"=== HISTORY ON {ts.team} ===")
            lines.append(f"Record: {ts.record} ({ts.win_rate:.1%})")
            lines.append(f"P&L: ${ts.total_pl:+.2f}")
            if ts.spread_record != "0-0":
                lines.append(f"Spread: {ts.spread_record} (${ts.spread_pl:+.2f})")
            if ts.ml_record != "0-0":
                lines.append(f"ML: {ts.ml_record} (${ts.ml_pl:+.2f})")

        return "\n".join(lines)


class PickHistory:
    """Query and analyze historical picks."""

    def __init__(self, db_path: str = "data/picks.db"):
        self.db = get_db(db_path)

    def get_team_stats(self, team: str) -> TeamStats:
        """Get historical stats for a specific team (as underdog)."""
        import sqlite3

        stats = TeamStats(team=team)

        with sqlite3.connect(self.db.db_path) as conn:
            conn.row_factory = sqlite3.Row

            # Get all picks where this team was the underdog
            rows = conn.execute("""
                SELECT p.*, r.result, r.profit_loss
                FROM picks p
                LEFT JOIN results r ON p.id = r.pick_id
                WHERE p.underdog = ? AND r.id IS NOT NULL
            """, (team,)).fetchall()

            if not rows:
                return stats

            spread_wins, spread_losses = 0, 0
            ml_wins, ml_losses = 0, 0

            for row in rows:
                stats.total_picks += 1
                result = row["result"]
                pl = row["profit_loss"] or 0
                bet_type = row["bet_type"]

                stats.total_pl += pl

                if result == "WIN":
                    stats.wins += 1
                    if bet_type == "SPREAD":
                        spread_wins += 1
                        stats.spread_pl += pl
                    else:
                        ml_wins += 1
                        stats.ml_pl += pl
                elif result == "LOSS":
                    stats.losses += 1
                    if bet_type == "SPREAD":
                        spread_losses += 1
                        stats.spread_pl += pl
                    else:
                        ml_losses += 1
                        stats.ml_pl += pl
                else:
                    stats.pushes += 1

            stats.spread_record = f"{spread_wins}-{spread_losses}"
            stats.ml_record = f"{ml_wins}-{ml_losses}"
            stats.as_underdog_record = stats.record
            stats.as_underdog_pl = stats.total_pl

        return stats

    def get_performance_by_confidence(self) -> dict:
        """Get win rates by confidence level."""
        import sqlite3

        results = {"high": {"wins": 0, "losses": 0}, "medium": {"wins": 0, "losses": 0}}

        with sqlite3.connect(self.db.db_path) as conn:
            rows = conn.execute("""
                SELECT p.confidence, r.result
                FROM picks p
                JOIN results r ON p.id = r.pick_id
                WHERE p.confidence IN ('high', 'medium')
            """).fetchall()

            for row in rows:
                conf = row[0]
                result = row[1]
                if conf in results:
                    if result == "WIN":
                        results[conf]["wins"] += 1
                    elif result == "LOSS":
                        results[conf]["losses"] += 1

        return results

    def get_recent_results(self, limit: int = 5) -> list[dict]:
        """Get most recent results."""
        return self.db.get_all_results()[:limit]

    def get_current_streak(self) -> str:
        """Calculate current win/loss streak."""
        results = self.get_recent_results(10)

        if not results:
            return ""

        streak_type = results[0].get("result")
        if streak_type not in ("WIN", "LOSS"):
            return ""

        count = 0
        for r in results:
            if r.get("result") == streak_type:
                count += 1
            else:
                break

        return f"{'W' if streak_type == 'WIN' else 'L'}{count}"

    def get_historical_context(self, team: str = None) -> HistoricalContext:
        """Build full historical context for the agent."""
        metrics = self.db.get_metrics()
        context = HistoricalContext()

        # Overall stats
        context.total_picks = metrics["total_picks"]
        context.overall_record = metrics["record"]
        context.overall_win_rate = metrics["win_rate"]
        context.overall_pl = metrics["total_pl"]
        context.overall_roi = metrics["roi"]

        # By confidence
        conf_stats = self.get_performance_by_confidence()

        high = conf_stats.get("high", {})
        hw, hl = high.get("wins", 0), high.get("losses", 0)
        context.high_conf_record = f"{hw}-{hl}"
        context.high_conf_win_rate = hw / (hw + hl) if (hw + hl) > 0 else 0

        med = conf_stats.get("medium", {})
        mw, ml = med.get("wins", 0), med.get("losses", 0)
        context.medium_conf_record = f"{mw}-{ml}"
        context.medium_conf_win_rate = mw / (mw + ml) if (mw + ml) > 0 else 0

        # Last 5
        recent = self.get_recent_results(5)
        recent_wins = sum(1 for r in recent if r.get("result") == "WIN")
        recent_losses = sum(1 for r in recent if r.get("result") == "LOSS")
        context.last_5_record = f"{recent_wins}-{recent_losses}"

        # Streak
        context.current_streak = self.get_current_streak()

        # Team-specific stats
        if team:
            context.team_stats = self.get_team_stats(team)

        return context


# Singleton instance
_history: Optional[PickHistory] = None


def get_history(db_path: str = "data/picks.db") -> PickHistory:
    """Get history instance (singleton)."""
    global _history
    if _history is None:
        _history = PickHistory(db_path)
    return _history
