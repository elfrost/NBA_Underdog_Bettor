"""FastAPI web dashboard for NBA Underdog Bet."""

from pathlib import Path
from datetime import datetime, date
from typing import Optional

from fastapi import FastAPI, Request, Query
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse

from config import get_settings
from src.db import get_db
from src.bankroll import get_bankroll_manager

# App setup
app = FastAPI(
    title="NBA Underdog Bet",
    description="AI-powered NBA underdog betting analysis dashboard",
    version="0.8.0",
)

# Paths
BASE_DIR = Path(__file__).parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

# Templates
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Static files (if exists)
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# Template filters
def format_currency(value: float) -> str:
    """Format number as currency."""
    if value >= 0:
        return f"${value:,.2f}"
    return f"-${abs(value):,.2f}"


def format_percent(value: float) -> str:
    """Format number as percentage."""
    return f"{value:.1%}"


def format_line(value: float) -> str:
    """Format spread/ML line."""
    if value > 0:
        return f"+{value}"
    return str(value)


# Add filters to Jinja2
templates.env.filters["currency"] = format_currency
templates.env.filters["percent"] = format_percent
templates.env.filters["line"] = format_line


# ============== ROUTES ==============

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard page."""
    settings = get_settings()
    db = get_db()
    bankroll_mgr = get_bankroll_manager()

    # Get context
    ctx = bankroll_mgr.get_bankroll_context()
    metrics = ctx["metrics"]

    # Get today's picks
    today_picks = db.get_picks_by_date(datetime.now())

    # Get overall metrics
    db_metrics = db.get_metrics()

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "page": "dashboard",
        "settings": settings,
        "bankroll": settings.bankroll,
        "risk_level": ctx["risk_level"].value,
        "dynamic_kelly": ctx["dynamic_kelly"],
        "kelly_adjustment": ctx["kelly_adjustment"],
        "picks": today_picks,
        "metrics": db_metrics,
        "performance": metrics,
        "now": datetime.now(),
    })


@app.get("/picks", response_class=HTMLResponse)
async def picks_page(
    request: Request,
    date_filter: Optional[str] = Query(None),
    confidence: Optional[str] = Query(None),
):
    """Today's picks page."""
    settings = get_settings()
    db = get_db()
    bankroll_mgr = get_bankroll_manager()
    ctx = bankroll_mgr.get_bankroll_context()

    # Parse date or use today
    if date_filter:
        try:
            filter_date = datetime.strptime(date_filter, "%Y-%m-%d")
        except ValueError:
            filter_date = datetime.now()
    else:
        filter_date = datetime.now()

    # Get picks
    picks = db.get_picks_by_date(filter_date)

    # Filter by confidence if specified
    if confidence:
        picks = [p for p in picks if p.confidence.lower() == confidence.lower()]

    return templates.TemplateResponse("picks.html", {
        "request": request,
        "page": "picks",
        "settings": settings,
        "risk_level": ctx["risk_level"].value,
        "dynamic_kelly": ctx["dynamic_kelly"],
        "picks": picks,
        "filter_date": filter_date.strftime("%Y-%m-%d"),
        "confidence_filter": confidence,
        "now": datetime.now(),
    })


@app.get("/results", response_class=HTMLResponse)
async def results_page(request: Request):
    """Results history page."""
    settings = get_settings()
    db = get_db()
    bankroll_mgr = get_bankroll_manager()
    ctx = bankroll_mgr.get_bankroll_context()

    # Get all results
    results = db.get_all_results()

    # Get metrics
    metrics = db.get_metrics()

    return templates.TemplateResponse("results.html", {
        "request": request,
        "page": "results",
        "settings": settings,
        "risk_level": ctx["risk_level"].value,
        "dynamic_kelly": ctx["dynamic_kelly"],
        "results": results,
        "metrics": metrics,
        "now": datetime.now(),
    })


@app.get("/analytics", response_class=HTMLResponse)
async def analytics_page(request: Request):
    """Analytics and charts page."""
    settings = get_settings()
    db = get_db()
    bankroll_mgr = get_bankroll_manager()
    ctx = bankroll_mgr.get_bankroll_context()

    # Get all results for charts
    results = db.get_all_results()
    metrics = db.get_metrics()
    calibration = ctx["calibration"]

    return templates.TemplateResponse("analytics.html", {
        "request": request,
        "page": "analytics",
        "settings": settings,
        "risk_level": ctx["risk_level"].value,
        "dynamic_kelly": ctx["dynamic_kelly"],
        "results": results,
        "metrics": metrics,
        "calibration": calibration,
        "now": datetime.now(),
    })


# ============== API ENDPOINTS ==============

@app.get("/api/picks/today")
async def api_today_picks():
    """Get today's picks as JSON."""
    db = get_db()
    picks = db.get_picks_by_date(datetime.now())
    return JSONResponse([{
        "id": p.id,
        "game": f"{p.away_team} @ {p.home_team}",
        "underdog": p.underdog,
        "bet_type": p.bet_type,
        "line": p.line,
        "odds": p.odds,
        "confidence": p.confidence,
        "bet_amount": p.bet_amount,
        "expected_value": p.expected_value,
        "should_bet": p.should_bet,
    } for p in picks])


@app.get("/api/metrics")
async def api_metrics():
    """Get performance metrics as JSON."""
    db = get_db()
    bankroll_mgr = get_bankroll_manager()

    metrics = db.get_metrics()
    ctx = bankroll_mgr.get_bankroll_context()

    return JSONResponse({
        "metrics": metrics,
        "risk_level": ctx["risk_level"].value,
        "dynamic_kelly": ctx["dynamic_kelly"],
        "bankroll": ctx["current_bankroll"],
    })


@app.get("/api/results")
async def api_results():
    """Get all results as JSON."""
    db = get_db()
    results = db.get_all_results()
    return JSONResponse(results)


@app.get("/api/shadow-analysis")
async def api_shadow_analysis():
    """v0.8.0: Compare shadow bets vs real bets performance.

    This helps validate if our filters are correctly identifying winning patterns.
    """
    import sqlite3
    db = get_db()

    with sqlite3.connect(db.db_path) as conn:
        conn.row_factory = sqlite3.Row

        # Real bets performance
        real_stats = conn.execute("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN r.result = 'WIN' THEN 1 ELSE 0 END) as wins,
                SUM(r.profit_loss) as pl,
                SUM(p.bet_amount) as wagered
            FROM picks p
            JOIN results r ON p.id = r.pick_id
            WHERE (p.is_shadow = 0 OR p.is_shadow IS NULL) AND p.should_bet = 1
        """).fetchone()

        # Shadow bets performance (what would have happened)
        shadow_stats = conn.execute("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN r.result = 'WIN' THEN 1 ELSE 0 END) as wins,
                SUM(r.profit_loss) as pl,
                SUM(p.bet_amount) as wagered,
                p.filter_reason
            FROM picks p
            JOIN results r ON p.id = r.pick_id
            WHERE p.is_shadow = 1
        """).fetchone()

        # Breakdown by filter reason
        filter_breakdown = conn.execute("""
            SELECT
                p.filter_reason,
                COUNT(*) as total,
                SUM(CASE WHEN r.result = 'WIN' THEN 1 ELSE 0 END) as wins,
                SUM(r.profit_loss) as pl
            FROM picks p
            JOIN results r ON p.id = r.pick_id
            WHERE p.is_shadow = 1
            GROUP BY p.filter_reason
        """).fetchall()

    def calc_metrics(stats):
        if not stats or not stats['total']:
            return {"total": 0, "wins": 0, "win_rate": 0, "pl": 0, "roi": 0}
        return {
            "total": stats['total'],
            "wins": stats['wins'] or 0,
            "win_rate": (stats['wins'] or 0) / stats['total'] * 100 if stats['total'] else 0,
            "pl": stats['pl'] or 0,
            "roi": (stats['pl'] or 0) / (stats['wagered'] or 1) * 100 if stats['wagered'] else 0,
        }

    return JSONResponse({
        "real_bets": calc_metrics(real_stats),
        "shadow_bets": calc_metrics(shadow_stats),
        "filter_breakdown": [
            {
                "reason": row['filter_reason'],
                "total": row['total'],
                "wins": row['wins'] or 0,
                "win_rate": (row['wins'] or 0) / row['total'] * 100 if row['total'] else 0,
                "pl": row['pl'] or 0,
            }
            for row in filter_breakdown
        ],
        "conclusion": "Si shadow_bets.win_rate > real_bets.win_rate, les filtres sont TROP restrictifs!"
    })


def run_server(host: str = "127.0.0.1", port: int = 8000):
    """Run the web server."""
    import uvicorn
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run_server()
