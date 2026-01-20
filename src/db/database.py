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

                    -- v0.8.0: Shadow betting
                    is_shadow INTEGER DEFAULT 0,
                    filter_reason TEXT DEFAULT '',

                    -- v0.9.0: CLV Tracking
                    opening_line REAL DEFAULT 0.0,
                    opening_odds INTEGER DEFAULT 0,
                    closing_line REAL DEFAULT 0.0,
                    closing_odds INTEGER DEFAULT 0,
                    clv_line REAL DEFAULT 0.0,
                    clv_odds REAL DEFAULT 0.0,

                    -- v0.9.0: ML Integration
                    ml_probability REAL DEFAULT 0.0,
                    injury_impact REAL DEFAULT 0.0,

                    UNIQUE(game_id, bet_type, underdog)
                )
            """)

            # v0.9.0: Line snapshots for movement tracking
            conn.execute("""
                CREATE TABLE IF NOT EXISTS line_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    game_id TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    bookmaker TEXT,
                    home_team TEXT,
                    away_team TEXT,
                    spread REAL,
                    spread_odds INTEGER,
                    ml_underdog_odds INTEGER,
                    ml_favorite_odds INTEGER
                )
            """)

            # v0.9.0: System configuration for auto-calibration
            conn.execute("""
                CREATE TABLE IF NOT EXISTS system_config (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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

        # Migrate existing schema to add new columns
        self.migrate_schema()

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
                    favorite_form, is_shadow, filter_reason,
                    opening_line, opening_odds, closing_line, closing_odds,
                    clv_line, clv_odds, ml_probability, injury_impact
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                pick.game_date, pick.game_id, pick.home_team, pick.away_team,
                pick.underdog, pick.favorite, pick.bet_type, pick.line,
                pick.odds, pick.confidence, pick.edge_factors, pick.risk_factors,
                pick.reasoning, pick.implied_prob, pick.estimated_prob,
                pick.bankroll_pct, pick.bet_amount, pick.expected_value,
                int(pick.should_bet), int(pick.underdog_b2b), pick.underdog_rest,
                pick.underdog_form, int(pick.favorite_b2b), pick.favorite_rest,
                pick.favorite_form, pick.is_shadow, pick.filter_reason,
                pick.opening_line, pick.opening_odds, pick.closing_line, pick.closing_odds,
                pick.clv_line, pick.clv_odds, pick.ml_probability, pick.injury_impact
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

    def get_pending_picks(self, before_date: Optional[datetime] = None, include_shadow: bool = True) -> list[PickRecord]:
        """Get picks without results (pending games).

        v0.9.0: Now includes shadow picks by default for forward testing analysis.
        """
        query = """
            SELECT p.* FROM picks p
            LEFT JOIN results r ON p.id = r.pick_id
            WHERE r.id IS NULL
        """
        if not include_shadow:
            query += " AND p.should_bet = 1"
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

    def get_all_results(self, include_shadow: bool = False) -> list[dict]:
        """Get all picks with their results (including pending).

        Args:
            include_shadow: If True, include shadow bets in results.
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            if include_shadow:
                query = """
                    SELECT p.*, r.result, r.profit_loss, r.actual_margin, r.home_score, r.away_score
                    FROM picks p
                    LEFT JOIN results r ON p.id = r.pick_id
                    ORDER BY p.game_date DESC
                """
            else:
                query = """
                    SELECT p.*, r.result, r.profit_loss, r.actual_margin, r.home_score, r.away_score
                    FROM picks p
                    LEFT JOIN results r ON p.id = r.pick_id
                    WHERE p.should_bet = 1
                    ORDER BY p.game_date DESC
                """
            rows = conn.execute(query).fetchall()
            return [dict(row) for row in rows]

    def get_shadow_metrics(self) -> dict:
        """Calculate performance metrics for shadow bets only."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            stats = conn.execute("""
                SELECT
                    COUNT(*) as total_picks,
                    SUM(CASE WHEN r.result = 'WIN' THEN 1 ELSE 0 END) as wins,
                    SUM(CASE WHEN r.result = 'LOSS' THEN 1 ELSE 0 END) as losses,
                    SUM(CASE WHEN r.result = 'PUSH' THEN 1 ELSE 0 END) as pushes
                FROM picks p
                JOIN results r ON p.id = r.pick_id
                WHERE p.is_shadow = 1
            """).fetchone()

            total = stats['total_picks'] or 0
            wins = stats['wins'] or 0
            losses = stats['losses'] or 0

            return {
                "total_picks": total,
                "record": f"{wins}-{losses}",
                "win_rate": wins / total if total > 0 else 0,
            }

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

    # ===== v0.9.0: Line Snapshots =====

    def save_line_snapshot(self, game_id: str, bookmaker: str, home_team: str,
                           away_team: str, spread: float, spread_odds: int,
                           ml_underdog_odds: int, ml_favorite_odds: int) -> int:
        """Save a line snapshot for movement tracking."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO line_snapshots (
                    game_id, bookmaker, home_team, away_team, spread,
                    spread_odds, ml_underdog_odds, ml_favorite_odds
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (game_id, bookmaker, home_team, away_team, spread,
                  spread_odds, ml_underdog_odds, ml_favorite_odds))
            conn.commit()
            return cursor.lastrowid

    def get_line_history(self, game_id: str) -> list[dict]:
        """Get line movement history for a game."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT * FROM line_snapshots
                WHERE game_id = ?
                ORDER BY timestamp ASC
            """, (game_id,)).fetchall()
            return [dict(row) for row in rows]

    # ===== v0.9.0: System Config =====

    def get_config(self, key: str, default: str = "") -> str:
        """Get a system config value."""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT value FROM system_config WHERE key = ?", (key,)
            ).fetchone()
            return row[0] if row else default

    def set_config(self, key: str, value: str) -> None:
        """Set a system config value."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO system_config (key, value, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            """, (key, value))
            conn.commit()

    # ===== v0.9.0: CLV Updates =====

    def update_closing_line(self, pick_id: int, closing_line: float,
                            closing_odds: int, clv_line: float, clv_odds: float) -> None:
        """Update a pick with closing line data."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE picks SET
                    closing_line = ?,
                    closing_odds = ?,
                    clv_line = ?,
                    clv_odds = ?
                WHERE id = ?
            """, (closing_line, closing_odds, clv_line, clv_odds, pick_id))
            conn.commit()

    def get_picks_for_clv_update(self) -> list[PickRecord]:
        """Get picks that need CLV update (no closing line yet, game today or past)."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("""
                SELECT * FROM picks
                WHERE closing_line = 0 AND game_date <= datetime('now')
                ORDER BY game_date
            """).fetchall()
            return [self._row_to_pick(row) for row in rows]

    def get_clv_metrics(self) -> dict:
        """Calculate CLV performance metrics."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            # Overall CLV stats
            stats = conn.execute("""
                SELECT
                    COUNT(*) as total_with_clv,
                    AVG(clv_line) as avg_clv_line,
                    AVG(clv_odds) as avg_clv_odds,
                    SUM(CASE WHEN clv_line > 0 THEN 1 ELSE 0 END) as positive_clv_count,
                    SUM(CASE WHEN clv_odds > 0 THEN 1 ELSE 0 END) as beat_closing_count
                FROM picks
                WHERE closing_line != 0 AND should_bet = 1
            """).fetchone()

            # By confidence
            by_conf = conn.execute("""
                SELECT
                    confidence,
                    COUNT(*) as total,
                    AVG(clv_line) as avg_clv_line,
                    AVG(clv_odds) as avg_clv_odds
                FROM picks
                WHERE closing_line != 0 AND should_bet = 1
                GROUP BY confidence
            """).fetchall()

            return {
                "overall": dict(stats) if stats else {},
                "by_confidence": [dict(r) for r in by_conf]
            }

    # ===== Migration for existing databases =====

    def migrate_schema(self):
        """Add missing columns to existing database."""
        with sqlite3.connect(self.db_path) as conn:
            # Get existing columns
            cursor = conn.execute("PRAGMA table_info(picks)")
            existing_cols = {row[1] for row in cursor.fetchall()}

            # Columns to add if missing
            new_columns = [
                ("is_shadow", "INTEGER DEFAULT 0"),
                ("filter_reason", "TEXT DEFAULT ''"),
                ("opening_line", "REAL DEFAULT 0.0"),
                ("opening_odds", "INTEGER DEFAULT 0"),
                ("closing_line", "REAL DEFAULT 0.0"),
                ("closing_odds", "INTEGER DEFAULT 0"),
                ("clv_line", "REAL DEFAULT 0.0"),
                ("clv_odds", "REAL DEFAULT 0.0"),
                ("ml_probability", "REAL DEFAULT 0.0"),
                ("injury_impact", "REAL DEFAULT 0.0"),
            ]

            for col_name, col_type in new_columns:
                if col_name not in existing_cols:
                    conn.execute(f"ALTER TABLE picks ADD COLUMN {col_name} {col_type}")
                    print(f"  Added column: {col_name}")

            conn.commit()

    def _row_to_pick(self, row: sqlite3.Row) -> PickRecord:
        """Convert a database row to a PickRecord."""
        # Handle both old and new schema
        def safe_get(key, default=None):
            try:
                return row[key]
            except (IndexError, KeyError):
                return default

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
            # v0.8.0 fields
            is_shadow=safe_get('is_shadow', 0) or 0,
            filter_reason=safe_get('filter_reason', '') or '',
            # v0.9.0 CLV fields
            opening_line=safe_get('opening_line', 0.0) or 0.0,
            opening_odds=safe_get('opening_odds', 0) or 0,
            closing_line=safe_get('closing_line', 0.0) or 0.0,
            closing_odds=safe_get('closing_odds', 0) or 0,
            clv_line=safe_get('clv_line', 0.0) or 0.0,
            clv_odds=safe_get('clv_odds', 0.0) or 0.0,
            # v0.9.0 ML fields
            ml_probability=safe_get('ml_probability', 0.0) or 0.0,
            injury_impact=safe_get('injury_impact', 0.0) or 0.0,
        )


# Singleton instance
_db: Optional[Database] = None


def get_db(db_path: str = "data/picks.db") -> Database:
    """Get database instance (singleton)."""
    global _db
    if _db is None:
        _db = Database(db_path)
    return _db
