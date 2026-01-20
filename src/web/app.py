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
    description="AI-powered NBA underdog betting analysis with ML predictions",
    version="0.9.0",
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
    shadow_metrics = db.get_shadow_metrics()

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
        "shadow_metrics": shadow_metrics,
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


# ============== v0.9.0 PAGES ==============

@app.get("/clv", response_class=HTMLResponse)
async def clv_page(request: Request):
    """CLV Analysis page."""
    settings = get_settings()
    bankroll_mgr = get_bankroll_manager()
    ctx = bankroll_mgr.get_bankroll_context()

    return templates.TemplateResponse("clv.html", {
        "request": request,
        "page": "clv",
        "settings": settings,
        "risk_level": ctx["risk_level"].value,
        "dynamic_kelly": ctx["dynamic_kelly"],
        "now": datetime.now(),
    })


@app.get("/ml", response_class=HTMLResponse)
async def ml_page(request: Request):
    """ML Model page."""
    settings = get_settings()
    bankroll_mgr = get_bankroll_manager()
    ctx = bankroll_mgr.get_bankroll_context()

    return templates.TemplateResponse("ml.html", {
        "request": request,
        "page": "ml",
        "settings": settings,
        "risk_level": ctx["risk_level"].value,
        "dynamic_kelly": ctx["dynamic_kelly"],
        "now": datetime.now(),
    })


@app.get("/calibration", response_class=HTMLResponse)
async def calibration_page(request: Request):
    """Calibration settings page."""
    settings = get_settings()
    bankroll_mgr = get_bankroll_manager()
    ctx = bankroll_mgr.get_bankroll_context()

    return templates.TemplateResponse("calibration.html", {
        "request": request,
        "page": "calibration",
        "settings": settings,
        "risk_level": ctx["risk_level"].value,
        "dynamic_kelly": ctx["dynamic_kelly"],
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


# ============== v0.9.0 API ENDPOINTS ==============

@app.get("/api/clv-analysis")
async def api_clv_analysis():
    """v0.9.0: Get CLV (Closing Line Value) analysis."""
    db = get_db()
    clv_metrics = db.get_clv_metrics()

    # Calculate interpretation
    overall = clv_metrics.get("overall", {})
    avg_clv_line = overall.get("avg_clv_line", 0) or 0
    avg_clv_odds = overall.get("avg_clv_odds", 0) or 0

    if overall.get("total_with_clv", 0) > 0:
        interpretation = []
        if avg_clv_line > 0.5:
            interpretation.append(f"Excellent: +{avg_clv_line:.1f} pts CLV on average")
        elif avg_clv_line > 0:
            interpretation.append(f"Good: +{avg_clv_line:.1f} pts CLV on average")
        else:
            interpretation.append(f"Poor: {avg_clv_line:.1f} pts CLV on average")

        if avg_clv_odds > 0.02:
            interpretation.append(f"Beating closing odds by {avg_clv_odds*100:.1f}%")
        elif avg_clv_odds < -0.02:
            interpretation.append(f"Behind closing odds by {abs(avg_clv_odds)*100:.1f}%")

        clv_metrics["interpretation"] = " | ".join(interpretation)
    else:
        clv_metrics["interpretation"] = "No CLV data yet - will populate after games start"

    return JSONResponse(clv_metrics)


@app.get("/api/calibration")
async def api_calibration():
    """v0.9.0: Get auto-calibration analysis."""
    try:
        from src.services.auto_calibration import AutoCalibrator
        calibrator = AutoCalibrator()
        result = calibrator.calculate_optimal_calibration()
        return JSONResponse(result)
    except Exception as e:
        return JSONResponse({"error": str(e)})


@app.post("/api/calibration/update")
async def api_update_calibration():
    """v0.9.0: Update calibration factor based on analysis."""
    try:
        from src.services.auto_calibration import AutoCalibrator
        calibrator = AutoCalibrator()
        result = calibrator.update_calibration()
        return JSONResponse(result)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.get("/api/ml/info")
async def api_ml_info():
    """v0.9.0: Get ML model information."""
    try:
        from src.ml.model import UnderdogPredictor
        predictor = UnderdogPredictor()
        return JSONResponse(predictor.get_model_info())
    except Exception as e:
        return JSONResponse({"error": str(e), "is_trained": False})


@app.post("/api/ml/train")
async def api_ml_train(force: bool = Query(False)):
    """v0.9.0: Train or retrain the ML model."""
    try:
        from src.ml.model import UnderdogPredictor
        predictor = UnderdogPredictor()
        result = predictor.train(force=force)
        return JSONResponse(result)
    except Exception as e:
        return JSONResponse({"error": str(e), "status": "failed"}, status_code=500)


@app.get("/api/ml/features")
async def api_ml_features():
    """v0.9.0: Get feature statistics and importance."""
    try:
        from src.ml.features import FeatureExtractor
        from src.ml.model import UnderdogPredictor

        extractor = FeatureExtractor()
        predictor = UnderdogPredictor()

        stats = extractor.get_feature_stats()
        importance = predictor.get_feature_importance()

        return JSONResponse({
            "feature_stats": stats,
            "feature_importance": importance
        })
    except Exception as e:
        return JSONResponse({"error": str(e)})


@app.get("/api/line-movement")
async def api_line_movement():
    """v0.9.0: Get line movement analysis for all tracked games."""
    try:
        from src.services.line_movement import LineMovementTracker
        from src.api.odds import OddsAPIClient
        settings = get_settings()

        # Create tracker (won't need to fetch, just analyze stored data)
        odds_client = OddsAPIClient(settings.odds_api_key)
        tracker = LineMovementTracker(odds_client)

        movements = tracker.get_all_movements()
        rlm_alerts = tracker.get_rlm_alerts()

        return JSONResponse({
            "movements": movements,
            "rlm_alerts": rlm_alerts,
            "total_tracked": len(movements)
        })
    except Exception as e:
        return JSONResponse({"error": str(e)})


@app.get("/api/picks")
async def api_picks_filtered(
    filter_type: Optional[str] = Query("all", description="all, real, or shadow"),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
):
    """v0.9.0: Get picks with filtering options."""
    import sqlite3
    db = get_db()

    with sqlite3.connect(db.db_path) as conn:
        conn.row_factory = sqlite3.Row

        # Build query
        conditions = []
        params = []

        if filter_type == "real":
            conditions.append("(p.is_shadow = 0 OR p.is_shadow IS NULL)")
        elif filter_type == "shadow":
            conditions.append("p.is_shadow = 1")

        if date_from:
            conditions.append("date(p.game_date) >= ?")
            params.append(date_from)

        if date_to:
            conditions.append("date(p.game_date) <= ?")
            params.append(date_to)

        where_clause = " AND ".join(conditions) if conditions else "1=1"

        query = f"""
            SELECT p.*, r.result, r.profit_loss, r.home_score, r.away_score
            FROM picks p
            LEFT JOIN results r ON p.id = r.pick_id
            WHERE {where_clause}
            ORDER BY p.game_date DESC
        """

        rows = conn.execute(query, params).fetchall()

    return JSONResponse([dict(row) for row in rows])


def run_server(host: str = "127.0.0.1", port: int = 8000):
    """Run the web server."""
    import uvicorn
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run_server()
