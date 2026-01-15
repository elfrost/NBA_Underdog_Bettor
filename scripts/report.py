"""Generate performance report from picks database."""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from src.db import get_db

console = Console()


def generate_report():
    """Generate and display performance report."""
    db = get_db()
    metrics = db.get_metrics()
    all_results = db.get_all_results()

    if metrics["total_picks"] == 0:
        console.print("[yellow]No completed picks to report on yet.[/yellow]")
        console.print("[dim]Run picks with main.py, wait for games to finish, then run fetch_results.py[/dim]")
        return

    # Main metrics panel
    win_rate = metrics["win_rate"] * 100
    roi = metrics["roi"] * 100
    total_pl = metrics["total_pl"]

    win_color = "green" if win_rate >= 50 else "red"
    roi_color = "green" if roi >= 0 else "red"
    pl_color = "green" if total_pl >= 0 else "red"

    console.print(Panel.fit(
        f"[bold]Total Picks:[/bold] {metrics['total_picks']}\n"
        f"[bold]Record:[/bold] {metrics['record']}\n"
        f"[bold]Win Rate:[/bold] [{win_color}]{win_rate:.1f}%[/{win_color}]\n"
        f"[bold]Total P&L:[/bold] [{pl_color}]${total_pl:+.2f}[/{pl_color}]\n"
        f"[bold]ROI:[/bold] [{roi_color}]{roi:+.1f}%[/{roi_color}]",
        title="Overall Performance",
        border_style="blue",
    ))

    # By Confidence Level
    if metrics["by_confidence"]:
        conf_table = Table(title="Performance by Confidence Level")
        conf_table.add_column("Confidence", style="cyan")
        conf_table.add_column("Record", style="white")
        conf_table.add_column("Win Rate", style="yellow")
        conf_table.add_column("P&L", style="green")

        for row in metrics["by_confidence"]:
            conf = row["confidence"].upper()
            total = row["total"]
            wins = row["wins"]
            losses = total - wins
            pl = row["pl"] or 0
            wr = (wins / total * 100) if total > 0 else 0

            wr_color = "green" if wr >= 50 else "red"
            pl_color = "green" if pl >= 0 else "red"

            conf_table.add_row(
                conf,
                f"{wins}-{losses}",
                f"[{wr_color}]{wr:.1f}%[/{wr_color}]",
                f"[{pl_color}]${pl:+.2f}[/{pl_color}]",
            )

        console.print()
        console.print(conf_table)

    # By Bet Type
    if metrics["by_bet_type"]:
        type_table = Table(title="Performance by Bet Type")
        type_table.add_column("Bet Type", style="cyan")
        type_table.add_column("Record", style="white")
        type_table.add_column("Win Rate", style="yellow")
        type_table.add_column("P&L", style="green")

        for row in metrics["by_bet_type"]:
            bet_type = row["bet_type"]
            total = row["total"]
            wins = row["wins"]
            losses = total - wins
            pl = row["pl"] or 0
            wr = (wins / total * 100) if total > 0 else 0

            wr_color = "green" if wr >= 50 else "red"
            pl_color = "green" if pl >= 0 else "red"

            type_table.add_row(
                bet_type,
                f"{wins}-{losses}",
                f"[{wr_color}]{wr:.1f}%[/{wr_color}]",
                f"[{pl_color}]${pl:+.2f}[/{pl_color}]",
            )

        console.print()
        console.print(type_table)

    # Recent Results (last 10)
    if all_results:
        recent_table = Table(title="Recent Results (Last 10)")
        recent_table.add_column("Date", style="dim")
        recent_table.add_column("Game", style="cyan")
        recent_table.add_column("Pick", style="green")
        recent_table.add_column("Type", style="blue")
        recent_table.add_column("Line", style="yellow")
        recent_table.add_column("Score", style="white")
        recent_table.add_column("Result", style="magenta")
        recent_table.add_column("P&L", style="cyan")

        for row in all_results[:10]:
            result = row["result"]
            result_color = {"WIN": "green", "LOSS": "red", "PUSH": "yellow"}.get(result, "white")
            pl = row["profit_loss"] or 0
            pl_color = "green" if pl >= 0 else "red"

            game_date = row["game_date"][:10] if row["game_date"] else "N/A"
            score = f"{row['away_score']}-{row['home_score']}" if row["home_score"] else "N/A"
            line = row["line"]

            recent_table.add_row(
                game_date,
                f"{row['away_team']} @ {row['home_team']}",
                row["underdog"],
                row["bet_type"],
                f"{'+' if line > 0 else ''}{line}",
                score,
                f"[{result_color}]{result}[/{result_color}]",
                f"[{pl_color}]${pl:+.2f}[/{pl_color}]",
            )

        console.print()
        console.print(recent_table)

    # Pending picks count
    pending = db.get_pending_picks()
    if pending:
        console.print(f"\n[dim]Pending picks awaiting results: {len(pending)}[/dim]")


if __name__ == "__main__":
    generate_report()
