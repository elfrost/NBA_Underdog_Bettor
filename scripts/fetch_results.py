"""Fetch results for pending picks and update database."""

import asyncio
import sys
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from rich.console import Console
from rich.table import Table

from config import get_settings
from src.api import BallDontLieClient
from src.db import get_db, ResultRecord

console = Console()


def calculate_profit_loss(odds: int, bet_amount: float, won: bool) -> float:
    """Calculate profit/loss based on American odds."""
    if not won:
        return -bet_amount

    if odds > 0:
        return bet_amount * (odds / 100)
    else:
        return bet_amount * (100 / abs(odds))


def determine_spread_result(
    pick_team: str,
    home_team: str,
    home_score: int,
    away_score: int,
    spread: float,
) -> str:
    """Determine if spread bet won, lost, or pushed."""
    # spread is from the underdog's perspective (positive = getting points)
    if pick_team == home_team:
        # Underdog is home team, they're getting points
        adjusted_score = home_score + spread
        if adjusted_score > away_score:
            return "WIN"
        elif adjusted_score < away_score:
            return "LOSS"
        else:
            return "PUSH"
    else:
        # Underdog is away team, they're getting points
        adjusted_score = away_score + spread
        if adjusted_score > home_score:
            return "WIN"
        elif adjusted_score < home_score:
            return "LOSS"
        else:
            return "PUSH"


def determine_moneyline_result(
    pick_team: str,
    home_team: str,
    home_score: int,
    away_score: int,
) -> str:
    """Determine if moneyline bet won or lost."""
    if pick_team == home_team:
        if home_score > away_score:
            return "WIN"
        else:
            return "LOSS"
    else:
        if away_score > home_score:
            return "WIN"
        else:
            return "LOSS"


async def fetch_results():
    """Fetch results for all pending picks."""
    settings = get_settings()
    db = get_db()

    # Get pending picks (games that should be finished)
    pending = db.get_pending_picks(before_date=datetime.now())

    if not pending:
        console.print("[yellow]No pending picks to update.[/yellow]")
        return

    console.print(f"[blue]Found {len(pending)} pending picks to check...[/blue]\n")

    # Initialize API client
    client = BallDontLieClient(
        api_key=settings.balldontlie_api_key,
        base_url=settings.balldontlie_base_url,
    )

    results_table = Table(title="Results Update")
    results_table.add_column("Game", style="cyan")
    results_table.add_column("Pick", style="green")
    results_table.add_column("Type", style="blue")
    results_table.add_column("Line", style="yellow")
    results_table.add_column("Score", style="white")
    results_table.add_column("Result", style="magenta")
    results_table.add_column("P&L", style="cyan")

    updated = 0
    total_pl = 0.0

    try:
        for pick in pending:
            # Fetch game result
            game = await client.get_game_by_id(pick.game_id)

            if not game:
                console.print(f"[dim]Game {pick.game_id} not found[/dim]")
                continue

            if game.status != "Final":
                console.print(f"[dim]Game {pick.home_team} vs {pick.away_team} not finished ({game.status})[/dim]")
                continue

            home_score = game.home_score or 0
            away_score = game.away_score or 0

            # Determine result based on bet type
            if pick.bet_type == "SPREAD":
                result = determine_spread_result(
                    pick.underdog,
                    pick.home_team,
                    home_score,
                    away_score,
                    pick.line,
                )
            else:  # MONEYLINE
                result = determine_moneyline_result(
                    pick.underdog,
                    pick.home_team,
                    home_score,
                    away_score,
                )

            # Calculate P&L
            if result == "WIN":
                profit_loss = calculate_profit_loss(pick.odds, pick.bet_amount, True)
            elif result == "LOSS":
                profit_loss = calculate_profit_loss(pick.odds, pick.bet_amount, False)
            else:  # PUSH
                profit_loss = 0.0

            actual_margin = home_score - away_score
            roi_pct = (profit_loss / pick.bet_amount * 100) if pick.bet_amount > 0 else 0

            # Save result
            result_record = ResultRecord(
                pick_id=pick.id,
                home_score=home_score,
                away_score=away_score,
                result=result,
                actual_margin=actual_margin,
                profit_loss=profit_loss,
                roi_pct=roi_pct,
            )
            db.save_result(result_record)
            updated += 1
            total_pl += profit_loss

            # Display result
            result_color = {"WIN": "green", "LOSS": "red", "PUSH": "yellow"}[result]
            pl_color = "green" if profit_loss >= 0 else "red"

            results_table.add_row(
                f"{pick.away_team} @ {pick.home_team}",
                pick.underdog,
                pick.bet_type,
                f"{'+' if pick.line > 0 else ''}{pick.line}",
                f"{away_score}-{home_score}",
                f"[{result_color}]{result}[/{result_color}]",
                f"[{pl_color}]${profit_loss:+.2f}[/{pl_color}]",
            )

    finally:
        await client.close()

    if updated > 0:
        console.print(results_table)
        pl_color = "green" if total_pl >= 0 else "red"
        console.print(f"\n[bold]Updated {updated} picks[/bold]")
        console.print(f"Session P&L: [{pl_color}]${total_pl:+.2f}[/{pl_color}]")
    else:
        console.print("[yellow]No games have finished yet.[/yellow]")


if __name__ == "__main__":
    asyncio.run(fetch_results())
