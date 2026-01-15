"""Test script for v0.5.0 Advanced Stats + Simulator."""

from datetime import datetime, timedelta
from src.models.schemas import Team, Game
from src.stats.ratings import TeamRatings, calculate_team_ratings, get_matchup_analysis
from src.stats.simulator import MonteCarloSimulator, SimulationResult


def test_ratings_calculation():
    """Test team ratings calculation."""
    print("\n=== Testing Team Ratings ===")

    # Create test team and games
    team = Team(id=1, name="Test Team", abbreviation="TST")
    opp = Team(id=2, name="Opponent", abbreviation="OPP")

    now = datetime.now()
    games = [
        Game(
            id=i,
            date=now - timedelta(days=i),
            home_team=team if i % 2 == 0 else opp,
            away_team=opp if i % 2 == 0 else team,
            status="Final",
            home_score=110 + i * 2,
            away_score=105 + i,
        )
        for i in range(1, 6)
    ]

    ratings = calculate_team_ratings(team, games)

    print(f"Team: {ratings.team}")
    print(f"Games played: {ratings.games_played}")
    print(f"Points per game: {ratings.points_per_game:.1f}")
    print(f"Offensive rating: {ratings.offensive_rating:.1f}")
    print(f"Defensive rating: {ratings.defensive_rating:.1f}")
    print(f"Net rating: {ratings.net_rating:+.1f}")
    print(f"Pace: {ratings.pace:.1f}")

    assert ratings.games_played == 5, "Should have 5 games"
    assert ratings.points_per_game > 0, "PPG should be positive"
    print("[OK] Ratings calculation PASSED")


def test_matchup_analysis():
    """Test matchup analysis."""
    print("\n=== Testing Matchup Analysis ===")

    underdog = TeamRatings(
        team="PHX",
        games_played=5,
        points_per_game=108.0,
        offensive_rating=112.5,
        defensive_rating=115.0,
        net_rating=-2.5,
        pace=100.0,
    )

    favorite = TeamRatings(
        team="BOS",
        games_played=5,
        points_per_game=118.0,
        offensive_rating=120.0,
        defensive_rating=108.0,
        net_rating=12.0,
        pace=102.0,
    )

    # Underdog at home
    matchup = get_matchup_analysis(underdog, favorite, is_underdog_home=True)

    print(f"Expected pace: {matchup['expected_pace']:.1f}")
    print(f"Underdog expected score: {matchup['underdog_expected_score']:.1f}")
    print(f"Favorite expected score: {matchup['favorite_expected_score']:.1f}")
    print(f"Expected margin: {matchup['expected_margin']:+.1f}")

    assert matchup['expected_margin'] > 0, "Favorite should be expected to win"
    assert matchup['underdog_expected_score'] > 100, "Scores should be realistic"
    print("[OK] Matchup analysis PASSED")


def test_monte_carlo_simulation():
    """Test Monte Carlo simulation."""
    print("\n=== Testing Monte Carlo Simulator ===")

    underdog = TeamRatings(
        team="PHX",
        games_played=5,
        points_per_game=108.0,
        offensive_rating=112.5,
        defensive_rating=115.0,
        net_rating=-2.5,
        pace=100.0,
    )

    favorite = TeamRatings(
        team="BOS",
        games_played=5,
        points_per_game=118.0,
        offensive_rating=120.0,
        defensive_rating=108.0,
        net_rating=12.0,
        pace=102.0,
    )

    simulator = MonteCarloSimulator(simulations=1000)

    # Test with spread +5.5
    result = simulator.simulate_game(
        underdog_ratings=underdog,
        favorite_ratings=favorite,
        spread=5.5,
        is_underdog_home=False,
    )

    print(f"Simulations: {result.simulations}")
    print(f"Underdog win: {result.underdog_win_pct:.1%}")
    print(f"Cover spread: {result.underdog_cover_pct:.1%}")
    print(f"Average margin: {result.avg_margin:+.1f}")
    print(f"Margin std: {result.margin_std:.1f}")
    print(f"10th percentile: {result.margin_10th:+.1f}")
    print(f"90th percentile: {result.margin_90th:+.1f}")

    # Validate results
    assert 0 <= result.underdog_win_pct <= 1, "Win pct should be 0-1"
    assert 0 <= result.underdog_cover_pct <= 1, "Cover pct should be 0-1"
    assert result.margin_std > 0, "Margin std should be positive"

    print(f"\nFormatted for prompt:")
    print(result.format_for_prompt())

    print("[OK] Monte Carlo simulation PASSED")


def test_expected_value():
    """Test EV calculation."""
    print("\n=== Testing Expected Value ===")

    underdog = TeamRatings(team="PHX", offensive_rating=112.0, defensive_rating=115.0, net_rating=-3.0, pace=100.0)
    favorite = TeamRatings(team="BOS", offensive_rating=118.0, defensive_rating=108.0, net_rating=10.0, pace=102.0)

    simulator = MonteCarloSimulator(simulations=1000)
    result = simulator.simulate_game(underdog, favorite, spread=5.5, is_underdog_home=True)

    # Calculate EV for a $100 bet at +110 odds
    ev = simulator.calculate_ev(result, spread=5.5, odds=110, bet_amount=100)

    print(f"Cover pct: {result.underdog_cover_pct:.1%}")
    print(f"Odds: +110")
    print(f"Bet amount: $100")
    print(f"Expected value: ${ev:+.2f}")

    print("[OK] Expected value calculation PASSED")


if __name__ == "__main__":
    print("=" * 50)
    print("NBA Underdog Bet v0.5.0 Test Suite")
    print("=" * 50)

    test_ratings_calculation()
    test_matchup_analysis()
    test_monte_carlo_simulation()
    test_expected_value()

    print("\n" + "=" * 50)
    print("All tests PASSED!")
    print("=" * 50)
