"""Discord webhook notifications."""

import httpx
from datetime import datetime
from typing import Optional

from src.models.schemas import BetRecommendation


class DiscordNotifier:
    """Send notifications via Discord webhook."""

    # Embed colors
    COLOR_HIGH = 0x00FF00  # Green
    COLOR_MEDIUM = 0xFFFF00  # Yellow
    COLOR_LOW = 0xFF0000  # Red

    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url
        self._client = httpx.Client(timeout=10.0)

    def close(self):
        """Close HTTP client."""
        self._client.close()

    def send_pick(self, reco: BetRecommendation) -> bool:
        """Send a pick notification to Discord."""
        if not self.webhook_url:
            return False

        pick = reco.pick
        embed = self._build_embed(reco)

        payload = {
            "username": "NBA Underdog Bot",
            "avatar_url": "https://cdn-icons-png.flaticon.com/512/889/889442.png",
            "embeds": [embed],
        }

        try:
            response = self._client.post(self.webhook_url, json=payload)
            return response.status_code in (200, 204)
        except Exception as e:
            print(f"Discord notification failed: {e}")
            return False

    def _build_embed(self, reco: BetRecommendation) -> dict:
        """Build Discord embed for a pick."""
        pick = reco.pick
        conf = reco.confidence.value.upper()

        # Color based on confidence
        color = {
            "HIGH": self.COLOR_HIGH,
            "MEDIUM": self.COLOR_MEDIUM,
            "LOW": self.COLOR_LOW,
        }.get(conf, self.COLOR_LOW)

        # Format line with sign
        line_str = f"{'+' if pick.line > 0 else ''}{pick.line}"
        odds_str = f"{'+' if pick.odds > 0 else ''}{pick.odds}"

        # Position
        position = "Home" if pick.game.home_team.id == pick.underdog.id else "Road"

        # Bet recommendation
        if reco.should_bet:
            bet_str = f"${reco.bet_amount:.0f} ({reco.bankroll_pct:.1f}%)"
        else:
            bet_str = "PASS"

        embed = {
            "title": f"NBA Underdog Alert",
            "description": f"**{pick.underdog.name}** ({position} {pick.bet_type.value.upper()})",
            "color": color,
            "fields": [
                {
                    "name": "Matchup",
                    "value": f"{pick.game.away_team.abbreviation} @ {pick.game.home_team.abbreviation}",
                    "inline": True,
                },
                {
                    "name": "Line",
                    "value": line_str,
                    "inline": True,
                },
                {
                    "name": "Odds",
                    "value": odds_str,
                    "inline": True,
                },
                {
                    "name": "Confidence",
                    "value": conf,
                    "inline": True,
                },
                {
                    "name": "Sim Win/Cover",
                    "value": f"{reco.sim_win_pct:.0%} / {reco.sim_cover_pct:.0%}",
                    "inline": True,
                },
                {
                    "name": "Sim Margin",
                    "value": f"{reco.sim_avg_margin:+.1f}",
                    "inline": True,
                },
                {
                    "name": "Kelly Bet",
                    "value": bet_str,
                    "inline": True,
                },
                {
                    "name": "EV",
                    "value": f"${reco.expected_value:+.2f}",
                    "inline": True,
                },
                {
                    "name": "Edge Factors",
                    "value": ", ".join(reco.edge_factors) or "None",
                    "inline": False,
                },
                {
                    "name": "Risk Factors",
                    "value": ", ".join(reco.risk_factors) or "None",
                    "inline": False,
                },
                {
                    "name": "Analysis",
                    "value": reco.reasoning[:500] if reco.reasoning else "No reasoning provided",
                    "inline": False,
                },
            ],
            "footer": {
                "text": f"NBA Underdog Bet v0.7.0 | {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            },
        }

        return embed

    def send_test(self) -> bool:
        """Send a test notification."""
        if not self.webhook_url:
            return False

        payload = {
            "username": "NBA Underdog Bot",
            "content": "Test notification from NBA Underdog Bet system.",
            "embeds": [{
                "title": "Test Alert",
                "description": "If you see this, notifications are working correctly!",
                "color": self.COLOR_HIGH,
                "footer": {"text": f"Test sent at {datetime.now().strftime('%Y-%m-%d %H:%M')}"},
            }],
        }

        try:
            response = self._client.post(self.webhook_url, json=payload)
            return response.status_code in (200, 204)
        except Exception as e:
            print(f"Discord test failed: {e}")
            return False
