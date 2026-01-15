"""BallDon'tLie API client for NBA data."""

from datetime import datetime, timedelta
import httpx

from src.models.schemas import Team, Game, TeamContext


class BallDontLieClient:
    """Client for BallDon'tLie API (All-Star tier)."""

    def __init__(self, api_key: str, base_url: str = "https://api.balldontlie.io/v1"):
        self.api_key = api_key
        self.base_url = base_url
        self._client = httpx.AsyncClient(
            base_url=base_url,
            headers={"Authorization": api_key},
            timeout=30.0,
        )

    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()

    async def get_teams(self) -> list[Team]:
        """Fetch all NBA teams."""
        response = await self._client.get("/teams")
        response.raise_for_status()
        data = response.json()
        return [
            Team(
                id=t["id"],
                name=t["full_name"],
                abbreviation=t["abbreviation"],
                conference=t.get("conference"),
                division=t.get("division"),
            )
            for t in data["data"]
        ]

    async def get_games(self, date: datetime | None = None) -> list[Game]:
        """Fetch games for a specific date (defaults to today)."""
        if date is None:
            date = datetime.now()

        params = {"dates[]": date.strftime("%Y-%m-%d")}
        response = await self._client.get("/games", params=params)
        response.raise_for_status()
        data = response.json()

        games = []
        for g in data["data"]:
            home = Team(
                id=g["home_team"]["id"],
                name=g["home_team"]["full_name"],
                abbreviation=g["home_team"]["abbreviation"],
            )
            away = Team(
                id=g["visitor_team"]["id"],
                name=g["visitor_team"]["full_name"],
                abbreviation=g["visitor_team"]["abbreviation"],
            )
            games.append(Game(
                id=g["id"],
                date=datetime.fromisoformat(g["date"].replace("Z", "+00:00")),
                home_team=home,
                away_team=away,
                status=g["status"],
                home_score=g.get("home_team_score"),
                away_score=g.get("visitor_team_score"),
            ))
        return games

    async def get_team_recent_games(self, team_id: int, days: int = 7) -> list[Game]:
        """Fetch recent games for a team to check B2B and form."""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        params = {
            "team_ids[]": team_id,
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d"),
        }
        response = await self._client.get("/games", params=params)
        response.raise_for_status()
        data = response.json()

        games = []
        for g in data["data"]:
            home = Team(
                id=g["home_team"]["id"],
                name=g["home_team"]["full_name"],
                abbreviation=g["home_team"]["abbreviation"],
            )
            away = Team(
                id=g["visitor_team"]["id"],
                name=g["visitor_team"]["full_name"],
                abbreviation=g["visitor_team"]["abbreviation"],
            )
            games.append(Game(
                id=g["id"],
                date=datetime.fromisoformat(g["date"].replace("Z", "+00:00")),
                home_team=home,
                away_team=away,
                status=g["status"],
                home_score=g.get("home_team_score"),
                away_score=g.get("visitor_team_score"),
            ))
        return sorted(games, key=lambda x: x.date, reverse=True)

    async def get_player_injuries(self) -> list[dict]:
        """Fetch current player injuries."""
        response = await self._client.get("/player_injuries")
        response.raise_for_status()
        data = response.json()
        return data.get("data", [])

    async def build_team_context(self, team: Team, game_date: datetime) -> TeamContext:
        """Build context for a team including B2B, rest days, injuries."""
        recent_games = await self.get_team_recent_games(team.id, days=7)
        injuries_data = await self.get_player_injuries()

        # Check for B2B
        yesterday = game_date - timedelta(days=1)
        is_b2b = any(
            g.date.date() == yesterday.date()
            for g in recent_games
        )

        # Calculate days rest
        days_rest = 3  # default
        for g in recent_games:
            if g.date.date() < game_date.date():
                days_rest = (game_date.date() - g.date.date()).days
                break

        # Recent record (last 5)
        completed = [g for g in recent_games if g.status == "Final"][:5]
        wins = sum(
            1 for g in completed
            if (g.home_team.id == team.id and (g.home_score or 0) > (g.away_score or 0))
            or (g.away_team.id == team.id and (g.away_score or 0) > (g.home_score or 0))
        )
        recent_record = f"{wins}-{len(completed)-wins} L{len(completed)}"

        # Team injuries
        team_injuries = [
            f"{inj['player']['first_name']} {inj['player']['last_name']} ({inj['status']})"
            for inj in injuries_data
            if inj.get("player", {}).get("team", {}).get("id") == team.id
        ]

        return TeamContext(
            team=team,
            is_back_to_back=is_b2b,
            days_rest=days_rest,
            recent_record=recent_record,
            injuries=team_injuries[:5],  # Limit to top 5
        )
