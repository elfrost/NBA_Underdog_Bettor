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
from src.db import get_db, PickRecord, ResultRecord
from src.notifications import send_pick_notification, Notifier
from src.bankroll import get_bankroll_manager


console = Console()


async def update_results(bdl_client: BallDontLieClient) -> int:
    """Update results for pending picks. Returns number of results updated."""
    db = get_db()
    pending = db.get_pending_picks()

    if not pending:
        return 0

    console.print(f"[yellow]Checking {len(pending)} pending picks for results...[/yellow]")
    updated = 0

    for pick in pending:
        # Fetch game data
        game = await bdl_client.get_game_by_id(pick.game_id)
        if not game:
            console.print(f"[dim]Game {pick.game_id} not found[/dim]")
            continue

        # Only process completed games
        if game.status != "Final":
            continue

        # Calculate result
        home_score = game.home_score or 0
        away_score = game.away_score or 0

        # Determine if underdog is home or away
        is_underdog_home = pick.underdog == pick.home_team
        underdog_score = home_score if is_underdog_home else away_score
        favorite_score = away_score if is_underdog_home else home_score

        # Actual margin (positive = underdog won by X, negative = lost by X)
        actual_margin = underdog_score - favorite_score

        # Determine WIN/LOSS/PUSH
        if pick.bet_type == "SPREAD":
            # Spread bet: underdog covers if margin + line > 0
            cover_margin = actual_margin + pick.line
            if cover_margin > 0:
                result = "WIN"
            elif cover_margin < 0:
                result = "LOSS"
            else:
                result = "PUSH"
        else:  # MONEYLINE
            # ML bet: underdog wins outright
            if actual_margin > 0:
                result = "WIN"
            elif actual_margin < 0:
                result = "LOSS"
            else:
                result = "PUSH"  # OT tie (rare)

        # Calculate profit/loss
        if result == "WIN":
            # For positive odds (underdogs): profit = bet * (odds/100)
            if pick.odds > 0:
                profit_loss = pick.bet_amount * (pick.odds / 100)
            else:
                # For negative odds: profit = bet * (100/abs(odds))
                profit_loss = pick.bet_amount * (100 / abs(pick.odds))
        elif result == "LOSS":
            profit_loss = -pick.bet_amount
        else:  # PUSH
            profit_loss = 0.0

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

        # Display result
        pl_color = "green" if profit_loss > 0 else ("red" if profit_loss < 0 else "yellow")
        console.print(
            f"  {pick.away_team} @ {pick.home_team}: {away_score}-{home_score} | "
            f"{pick.underdog} {pick.bet_type} [{result}] [{pl_color}]${profit_loss:+.2f}[/{pl_color}]"
        )

    return updated


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
        underdog_rest=pick.underdog_context.days_rest,
        underdog_form=pick.underdog_context.recent_form,
        favorite_b2b=pick.favorite_context.is_back_to_back,
        favorite_rest=pick.favorite_context.days_rest,
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

    # Display bankroll status
    bankroll_mgr = get_bankroll_manager()
    console.print(bankroll_mgr.format_status())

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
        # Update results for any pending picks first
        results_updated = await update_results(bdl_client)
        if results_updated > 0:
            console.print(f"[green]Updated {results_updated} pick results[/green]\n")

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
                elif reco.confidence.value != "low":
                    console.print(f"[dim]Already in DB (skipped)[/dim]")

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
    bankroll_mgr = get_bankroll_manager()
    ctx = bankroll_mgr.get_bankroll_context()
    risk_emoji = {"crisis": "🚨", "cautious": "⚠️", "normal": "✅", "aggressive": "🔥"}
    risk = ctx["risk_level"].value

    table = Table(title=f"Underdog Recommendations | ${settings.bankroll:,.0f} | {risk_emoji.get(risk, '')} {risk.upper()} | Kelly {ctx['dynamic_kelly']:.0%}")

    table.add_column("Game", style="cyan")
    table.add_column("Pick", style="green")
    table.add_column("Type", style="blue")
    table.add_column("Line", style="yellow")
    table.add_column("Confidence", style="magenta")
    table.add_column("Sim Win/Cover", style="white")
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

        # Simulation display
        sim_str = f"{reco.sim_win_pct:.0%}/{reco.sim_cover_pct:.0%}"

        table.add_row(
            game_str,
            pick.underdog.abbreviation,
            pick.bet_type.value.upper(),
            line_str,
            f"[{conf_color}]{reco.confidence.value.upper()}[/{conf_color}]",
            sim_str,
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
    console.print(f"[dim]Dynamic Kelly: {ctx['dynamic_kelly']:.0%} of base (Risk: {risk.upper()})[/dim]")

    # Detailed analysis
    console.print("\n[bold]Detailed Analysis:[/bold]\n")
    for reco in recommendations:
        pick = reco.pick
        bet_status = "[green]BET[/green]" if reco.should_bet else "[red]PASS[/red]"
        console.print(f"[bold cyan]{pick.underdog.name}[/bold cyan] ({pick.bet_type.value}) - {bet_status}")
        console.print(f"[yellow]Kelly:[/yellow] Implied {reco.implied_prob:.1%} | Est. {reco.estimated_prob:.1%} | Bet {reco.bankroll_pct:.1f}%")
        console.print(f"[blue]Simulation:[/blue] Win {reco.sim_win_pct:.0%} | Cover {reco.sim_cover_pct:.0%} | Margin {reco.sim_avg_margin:+.1f}")
        console.print(f"[magenta]Stats:[/magenta] {pick.underdog.abbreviation} Net {pick.underdog_context.net_rating:+.1f} vs {pick.favorite.abbreviation} Net {pick.favorite_context.net_rating:+.1f}")
        console.print(f"[green]Edge factors:[/green] {', '.join(reco.edge_factors)}")
        console.print(f"[red]Risk factors:[/red] {', '.join(reco.risk_factors)}")
        console.print(f"[white]Reasoning:[/white] {reco.reasoning}\n")


if __name__ == "__main__":
    asyncio.run(main())
