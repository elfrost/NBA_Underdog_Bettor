"""SQLite database for pick tracking."""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from .models import PickRecord, ResultRecord


class Database:
    """SQLite database for tracking picks and results."""

    def __init__(self, db_path: str = "data/picks.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS picks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    game_date TIMESTAMP,
                    game_id INTEGER,

                    -- Teams
                    home_team TEXT,
                    away_team TEXT,
                    underdog TEXT,
                    favorite TEXT,

                    -- Bet details
                    bet_type TEXT,
                    line REAL,
                    odds INTEGER,

                    -- AI analysis
                    confidence TEXT,
                    edge_factors TEXT,
                    risk_factors TEXT,
                    reasoning TEXT,

                    -- Kelly sizing
                    implied_prob REAL,
                    estimated_prob REAL,
                    bankroll_pct REAL,
                    bet_amount REAL,
                    expected_value REAL,
                    should_bet INTEGER,

                    -- Context
                    underdog_b2b INTEGER,
                    underdog_rest INTEGER,
                    underdog_form TEXT,
                    favorite_b2b INTEGER,
                    favorite_rest INTEGER,
                    favorite_form TEXT,

                    UNIQUE(game_id, bet_type, underdog)
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pick_id INTEGER,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                    -- Final scores
                    home_score INTEGER,
                    away_score INTEGER,

                    -- Result
                    result TEXT,
                    actual_margin REAL,

                    -- P&L
                    profit_loss REAL,
                    roi_pct REAL,

                    FOREIGN KEY (pick_id) REFERENCES picks(id),
                    UNIQUE(pick_id)
                )
            """)

            conn.commit()

    def save_pick(self, pick: PickRecord) -> int | None:
        """Save a pick to the database. Returns pick ID or None if duplicate."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT OR IGNORE INTO picks (
                    game_date, game_id, home_team, away_team, underdog, favorite,
                    bet_type, line, odds, confidence, edge_factors, risk_factors,
                    reasoning, implied_prob, estimated_prob, bankroll_pct,
                    bet_amount, expected_value, should_bet, underdog_b2b,
                    underdog_rest, underdog_form, favorite_b2b, favorite_rest,
                    favorite_form, is_shadow, filter_reason
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                pick.game_date, pick.game_id, pick.home_team, pick.away_team,
                pick.underdog, pick.favorite, pick.bet_type, pick.line,
                pick.odds, pick.confidence, pick.edge_factors, pick.risk_factors,
                pick.reasoning, pick.implied_prob, pick.estimated_prob,
                pick.bankroll_pct, pick.bet_amount, pick.expected_value,
                int(pick.should_bet), int(pick.underdog_b2b), pick.underdog_rest,
                pick.underdog_form, int(pick.favorite_b2b), pick.favorite_rest,
                pick.favorite_form, pick.is_shadow, pick.filter_reason
            ))
            conn.commit()
            # Returns 0 if INSERT was ignored (duplicate)
            return cursor.lastrowid if cursor.rowcount > 0 else None

    def save_result(self, result: ResultRecord) -> int:
        """Save a result to the database. Returns result ID."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT OR REPLACE INTO results (
                    pick_id, home_score, away_score, result,
                    actual_margin, profit_loss, roi_pct
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                result.pick_id, result.home_score, result.away_score,
                result.result, result.actual_margin, result.profit_loss,
                result.roi_pct
            ))
            conn.commit()
            return cursor.lastrowid

    def get_pending_picks(self, before_date: Optional[datetime] = None) -> list[PickRecord]:
        """Get picks without results (pending games)."""
        query = """
            SELECT p.* FROM picks p
            LEFT JOIN results r ON p.id = r.pick_id
            WHERE r.id IS NULL AND p.should_bet = 1
        """
        if before_date:
            query += f" AND p.game_date < '{before_date.isoformat()}'"

        query += " ORDER BY p.game_date"

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(query).fetchall()
            return [self._row_to_pick(row) for row in rows]

    def get_picks_by_date(self, date: datetime) -> list[PickRecord]:
        """Get all picks for a specific date."""
        date_str = date.strftime("%Y-%m-%d")
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT * FROM picks
                WHERE date(game_date) = ?
                ORDER BY game_date
            """, (date_str,)).fetchall()
            return [self._row_to_pick(row) for row in rows]

    def get_all_results(self) -> list[dict]:
        """Get all picks with their results (including pending)."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT p.*, r.result, r.profit_loss, r.actual_margin, r.home_score, r.away_score
                FROM picks p
                LEFT JOIN results r ON p.id = r.pick_id
                WHERE p.should_bet = 1
                ORDER BY p.game_date DESC
            """).fetchall()
            return [dict(row) for row in rows]

    def get_metrics(self) -> dict:
        """Calculate performance metrics."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            # Overall stats
            total = conn.execute("""
                SELECT
                    COUNT(*) as total_picks,
                    SUM(CASE WHEN r.result = 'WIN' THEN 1 ELSE 0 END) as wins,
                    SUM(CASE WHEN r.result = 'LOSS' THEN 1 ELSE 0 END) as losses,
                    SUM(CASE WHEN r.result = 'PUSH' THEN 1 ELSE 0 END) as pushes,
                    SUM(r.profit_loss) as total_pl,
                    SUM(p.bet_amount) as total_wagered
                FROM picks p
                JOIN results r ON p.id = r.pick_id
                WHERE p.should_bet = 1
            """).fetchone()

            # By confidence
            by_confidence = conn.execute("""
                SELECT
                    p.confidence,
                    COUNT(*) as total,
                    SUM(CASE WHEN r.result = 'WIN' THEN 1 ELSE 0 END) as wins,
                    SUM(r.profit_loss) as pl
                FROM picks p
                JOIN results r ON p.id = r.pick_id
                WHERE p.should_bet = 1
                GROUP BY p.confidence
            """).fetchall()

            # By bet type
            by_bet_type = conn.execute("""
                SELECT
                    p.bet_type,
                    COUNT(*) as total,
                    SUM(CASE WHEN r.result = 'WIN' THEN 1 ELSE 0 END) as wins,
                    SUM(r.profit_loss) as pl
                FROM picks p
                JOIN results r ON p.id = r.pick_id
                WHERE p.should_bet = 1
                GROUP BY p.bet_type
            """).fetchall()

            total_dict = dict(total) if total else {}
            wins = total_dict.get('wins', 0) or 0
            losses = total_dict.get('losses', 0) or 0
            total_picks = total_dict.get('total_picks', 0) or 0
            total_pl = total_dict.get('total_pl', 0) or 0
            total_wagered = total_dict.get('total_wagered', 0) or 0

            return {
                "total_picks": total_picks,
                "record": f"{wins}-{losses}",
                "win_rate": wins / total_picks if total_picks > 0 else 0,
                "total_pl": total_pl,
                "roi": total_pl / total_wagered if total_wagered > 0 else 0,
                "by_confidence": [dict(r) for r in by_confidence],
                "by_bet_type": [dict(r) for r in by_bet_type],
            }

    def _row_to_pick(self, row: sqlite3.Row) -> PickRecord:
        """Convert a database row to a PickRecord."""
        return PickRecord(
            id=row['id'],
            created_at=row['created_at'],
            game_date=row['game_date'],
            game_id=row['game_id'],
            home_team=row['home_team'],
            away_team=row['away_team'],
            underdog=row['underdog'],
            favorite=row['favorite'],
            bet_type=row['bet_type'],
            line=row['line'],
            odds=row['odds'],
            confidence=row['confidence'],
            edge_factors=row['edge_factors'],
            risk_factors=row['risk_factors'],
            reasoning=row['reasoning'],
            implied_prob=row['implied_prob'],
            estimated_prob=row['estimated_prob'],
            bankroll_pct=row['bankroll_pct'],
            bet_amount=row['bet_amount'],
            expected_value=row['expected_value'],
            should_bet=bool(row['should_bet']),
            underdog_b2b=bool(row['underdog_b2b']),
            underdog_rest=row['underdog_rest'],
            underdog_form=row['underdog_form'],
            favorite_b2b=bool(row['favorite_b2b']),
            favorite_rest=row['favorite_rest'],
            favorite_form=row['favorite_form'],
        )


# Singleton instance
_db: Optional[Database] = None


def get_db(db_path: str = "data/picks.db") -> Database:
    """Get database instance (singleton)."""
    global _db
    if _db is None:
        _db = Database(db_path)
    return _db
