"""The Odds API client for live betting odds."""

from datetime import datetime
import httpx

from src.models.schemas import Odds


class OddsAPIClient:
    """Client for The Odds API."""

    SPORT = "basketball_nba"
    REGIONS = "us"
    MARKETS = "spreads,h2h"  # spreads and moneyline

    def __init__(self, api_key: str, base_url: str = "https://api.the-odds-api.com/v4"):
        self.api_key = api_key
        self.base_url = base_url
        self._client = httpx.AsyncClient(
            base_url=base_url,
            timeout=30.0,
        )
        self._remaining_requests: int | None = None

    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()

    @property
    def remaining_requests(self) -> int | None:
        """Return remaining API requests for the month."""
        return self._remaining_requests

    async def get_odds(self) -> list[dict]:
        """Fetch current NBA odds from all available bookmakers."""
        params = {
            "apiKey": self.api_key,
            "regions": self.REGIONS,
            "markets": self.MARKETS,
            "oddsFormat": "american",
        }

        response = await self._client.get(f"/sports/{self.SPORT}/odds", params=params)
        response.raise_for_status()

        # Track remaining requests
        self._remaining_requests = int(response.headers.get("x-requests-remaining", 0))

        return response.json()

    def parse_odds_for_game(self, game_data: dict, preferred_book: str = "fanduel") -> Odds | None:
        """Parse odds data for a single game, preferring specified bookmaker."""
        bookmakers = game_data.get("bookmakers", [])
        if not bookmakers:
            return None

        # Find preferred bookmaker or use first available
        book = next(
            (b for b in bookmakers if b["key"] == preferred_book),
            bookmakers[0]
        )

        markets = {m["key"]: m for m in book.get("markets", [])}

        spreads = markets.get("spreads", {}).get("outcomes", [])
        h2h = markets.get("h2h", {}).get("outcomes", [])

        if not spreads or not h2h:
            return None

        # Parse spreads
        home_spread_data = next((o for o in spreads if o["name"] == game_data["home_team"]), None)
        away_spread_data = next((o for o in spreads if o["name"] == game_data["away_team"]), None)

        # Parse moneyline
        home_ml_data = next((o for o in h2h if o["name"] == game_data["home_team"]), None)
        away_ml_data = next((o for o in h2h if o["name"] == game_data["away_team"]), None)

        if not all([home_spread_data, away_spread_data, home_ml_data, away_ml_data]):
            return None

        return Odds(
            game_id=hash(game_data["id"]) % (10**8),  # Create numeric ID from string
            bookmaker=book["key"],
            home_spread=home_spread_data["point"],
            away_spread=away_spread_data["point"],
            home_spread_odds=home_spread_data["price"],
            away_spread_odds=away_spread_data["price"],
            home_ml=home_ml_data["price"],
            away_ml=away_ml_data["price"],
            timestamp=datetime.now(),
        )

    def identify_underdog(self, odds: Odds) -> tuple[str, str]:
        """
        Identify which team is the underdog based on spread.
        Returns (underdog_position, favorite_position) as ('home'|'away', 'home'|'away').
        """
        # Positive spread = underdog
        if odds.home_spread > 0:
            return ("home", "away")
        return ("away", "home")
