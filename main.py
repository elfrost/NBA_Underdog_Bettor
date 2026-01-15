"""NBA Underdog Betting Analysis - Main Entry Point."""

import asyncio
from datetime import datetime
from rich.console import Console
from rich.table import Table

from config import get_settings
from src.api import BallDontLieClient, OddsAPIClient
from src.agents import UnderdogAgent
from src.models.schemas import BetType, UnderdogPick, BetRecommendation
from src.utils import find_odds_for_game, export_recommendations_to_csv
from src.db import get_db, PickRecord
from src.notifications import send_pick_notification, Notifier


console = Console()


def save_pick_to_db(reco: BetRecommendation) -> int | None:
    """Save a pick to the database. Returns pick ID or None if not saved."""
    pick = reco.pick

    # Only save HIGH and MEDIUM confidence picks
    if reco.confidence.value == "low":
        return None

    db = get_db()
    record = PickRecord(
        game_date=pick.game.date,
        game_id=pick.game.id,
        home_team=pick.game.home_team.abbreviation,
        away_team=pick.game.away_team.abbreviation,
        underdog=pick.underdog.abbreviation,
        favorite=pick.favorite.abbreviation,
        bet_type=pick.bet_type.value.upper(),
        line=pick.line,
        odds=pick.odds,
        confidence=reco.confidence.value,
        edge_factors=", ".join(reco.edge_factors),
        risk_factors=", ".join(reco.risk_factors),
        reasoning=reco.reasoning,
        implied_prob=reco.implied_prob,
        estimated_prob=reco.estimated_prob,
        bankroll_pct=reco.bankroll_pct,
        bet_amount=reco.bet_amount,
        expected_value=reco.expected_value,
        should_bet=reco.should_bet,
        underdog_b2b=pick.underdog_context.is_back_to_back,
        underdog_rest=pick.underdog_context.rest_days,
        underdog_form=pick.underdog_context.recent_form,
        favorite_b2b=pick.favorite_context.is_back_to_back,
        favorite_rest=pick.favorite_context.rest_days,
        favorite_form=pick.favorite_context.recent_form,
    )

    return db.save_pick(record)


async def main():
    """Run the underdog betting analysis."""
    settings = get_settings()

    # Validate API keys
    if not settings.balldontlie_api_key:
        console.print("[red]Error: BALLDONTLIE_API_KEY not set in .env[/red]")
        return
    if not settings.odds_api_key:
        console.print("[red]Error: ODDS_API_KEY not set in .env[/red]")
        return
    if not settings.openrouter_api_key:
        console.print("[red]Error: OPENROUTER_API_KEY not set in .env[/red]")
        return

    console.print("[bold blue]NBA Underdog Betting Analysis[/bold blue]")
    console.print(f"Date: {datetime.now().strftime('%Y-%m-%d')}\n")

    # Initialize clients
    bdl_client = BallDontLieClient(
        api_key=settings.balldontlie_api_key,
        base_url=settings.balldontlie_base_url,
    )
    odds_client = OddsAPIClient(
        api_key=settings.odds_api_key,
        base_url=settings.odds_base_url,
    )
    agent = UnderdogAgent()

    try:
        # Fetch today's games
        console.print("[yellow]Fetching today's games...[/yellow]")
        games = await bdl_client.get_games()
        console.print(f"Found {len(games)} games scheduled\n")

        if not games:
            console.print("[yellow]No games scheduled for today.[/yellow]")
            return

        # Fetch odds
        console.print("[yellow]Fetching odds...[/yellow]")
        odds_data = await odds_client.get_odds()
        console.print(f"Remaining API requests: {odds_client.remaining_requests}\n")

        # Process each game
        recommendations = []

        for game in games:
            # Find matching odds using normalized team names
            game_odds_data = find_odds_for_game(game, odds_data)

            if not game_odds_data:
                console.print(f"[dim]No odds found for {game.away_team.abbreviation} @ {game.home_team.abbreviation}[/dim]")
                continue

            odds = odds_client.parse_odds_for_game(game_odds_data)
            if not odds:
                continue

            # Identify underdog
            underdog_pos, fav_pos = odds_client.identify_underdog(odds)
            underdog = game.home_team if underdog_pos == "home" else game.away_team
            favorite = game.home_team if fav_pos == "home" else game.away_team

            # Check both spread and ML opportunities
            for bet_type in [BetType.SPREAD, BetType.MONEYLINE]:
                if not agent.filter_underdog(odds, bet_type):
                    continue

                # Build context for both teams
                console.print(f"[yellow]Analyzing {underdog.abbreviation} ({bet_type.value})...[/yellow]")

                underdog_ctx = await bdl_client.build_team_context(underdog, game.date)
                favorite_ctx = await bdl_client.build_team_context(favorite, game.date)

                # Create pick
                if bet_type == BetType.SPREAD:
                    line = odds.home_spread if underdog_pos == "home" else odds.away_spread
                    pick_odds = odds.home_spread_odds if underdog_pos == "home" else odds.away_spread_odds
                else:
                    line = odds.home_ml if underdog_pos == "home" else odds.away_ml
                    pick_odds = line

                pick = UnderdogPick(
                    game=game,
                    underdog=underdog,
                    favorite=favorite,
                    bet_type=bet_type,
                    line=line,
                    odds=pick_odds,
                    underdog_context=underdog_ctx,
                    favorite_context=favorite_ctx,
                )

                # Get AI recommendation
                reco = await agent.analyze_pick(pick)
                recommendations.append(reco)

                # Save to database (HIGH/MEDIUM confidence only)
                pick_id = save_pick_to_db(reco)
                if pick_id:
                    console.print(f"[dim]Saved to DB (ID: {pick_id})[/dim]")

                # Send notification (HIGH confidence by default)
                notif_result = send_pick_notification(reco)
                if notif_result.get("discord") or notif_result.get("telegram"):
                    console.print(f"[dim]Notification sent[/dim]")

        # Display results
        if recommendations:
            display_recommendations(recommendations)
            # Export to CSV
            csv_path = export_recommendations_to_csv(recommendations)
            console.print(f"\n[green]Picks exported to: {csv_path}[/green]")

            # Database summary
            saved_count = sum(1 for r in recommendations if r.confidence.value != "low")
            console.print(f"[blue]Saved to database: {saved_count} picks (HIGH/MEDIUM confidence)[/blue]")

            # Notifications summary
            notifier = Notifier()
            if notifier.has_channels:
                notified = sum(1 for r in recommendations if notifier.should_notify(r))
                console.print(f"[magenta]Notifications sent: {notified} picks (HIGH confidence)[/magenta]")
        else:
            console.print("\n[yellow]No underdog opportunities matched filters today.[/yellow]")

    finally:
        await bdl_client.close()
        await odds_client.close()


def display_recommendations(recommendations: list):
    """Display recommendations in a formatted table."""
    settings = get_settings()

    table = Table(title=f"Underdog Recommendations (Bankroll: ${settings.bankroll:,.0f})")

    table.add_column("Game", style="cyan")
    table.add_column("Pick", style="green")
    table.add_column("Type", style="blue")
    table.add_column("Line", style="yellow")
    table.add_column("Confidence", style="magenta")
    table.add_column("Kelly Bet", style="white")
    table.add_column("EV", style="cyan")

    for reco in recommendations:
        pick = reco.pick
        game_str = f"{pick.game.away_team.abbreviation} @ {pick.game.home_team.abbreviation}"
        line_str = f"{'+' if pick.line > 0 else ''}{pick.line}"
        conf_color = {"low": "red", "medium": "yellow", "high": "green"}[reco.confidence.value]

        # Kelly bet display
        if reco.should_bet:
            kelly_str = f"{reco.bankroll_pct:.1f}% (${reco.bet_amount:.0f})"
        else:
            kelly_str = "[dim]PASS[/dim]"

        # EV display
        ev_color = "green" if reco.expected_value > 0 else "red"
        ev_str = f"[{ev_color}]${reco.expected_value:+.2f}[/{ev_color}]"

        table.add_row(
            game_str,
            pick.underdog.abbreviation,
            pick.bet_type.value.upper(),
            line_str,
            f"[{conf_color}]{reco.confidence.value.upper()}[/{conf_color}]",
            kelly_str,
            ev_str,
        )

    console.print("\n")
    console.print(table)

    # Summary of actionable bets
    actionable = [r for r in recommendations if r.should_bet]
    total_exposure = sum(r.bankroll_pct for r in actionable)
    total_amount = sum(r.bet_amount for r in actionable)
    total_ev = sum(r.expected_value for r in actionable)

    console.print(f"\n[bold]Summary:[/bold] {len(actionable)}/{len(recommendations)} bets recommended")
    console.print(f"Total exposure: {total_exposure:.1f}% (${total_amount:.0f})")
    console.print(f"Total expected value: [{'green' if total_ev > 0 else 'red'}]${total_ev:+.2f}[/]")

    # Detailed analysis
    console.print("\n[bold]Detailed Analysis:[/bold]\n")
    for reco in recommendations:
        pick = reco.pick
        bet_status = "[green]BET[/green]" if reco.should_bet else "[red]PASS[/red]"
        console.print(f"[bold cyan]{pick.underdog.name}[/bold cyan] ({pick.bet_type.value}) - {bet_status}")
        console.print(f"[yellow]Kelly:[/yellow] Implied {reco.implied_prob:.1%} | Est. {reco.estimated_prob:.1%} | Bet {reco.bankroll_pct:.1f}%")
        console.print(f"[green]Edge factors:[/green] {', '.join(reco.edge_factors)}")
        console.print(f"[red]Risk factors:[/red] {', '.join(reco.risk_factors)}")
        console.print(f"[white]Reasoning:[/white] {reco.reasoning}\n")


if __name__ == "__main__":
    asyncio.run(main())
