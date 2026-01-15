"""Telegram bot notifications."""

import httpx
from datetime import datetime
from typing import Optional

from src.models.schemas import BetRecommendation


class TelegramNotifier:
    """Send notifications via Telegram bot."""

    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
        self._client = httpx.Client(timeout=10.0)

    @property
    def is_configured(self) -> bool:
        """Check if Telegram is properly configured."""
        return bool(self.bot_token and self.chat_id)

    def close(self):
        """Close HTTP client."""
        self._client.close()

    def send_pick(self, reco: BetRecommendation) -> bool:
        """Send a pick notification to Telegram."""
        if not self.is_configured:
            return False

        message = self._format_message(reco)
        return self._send_message(message)

    def _format_message(self, reco: BetRecommendation) -> str:
        """Format pick as Telegram message with HTML."""
        pick = reco.pick
        conf = reco.confidence.value.upper()

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

        # Confidence emoji
        conf_emoji = {"HIGH": "🟢", "MEDIUM": "🟡", "LOW": "🔴"}.get(conf, "⚪")

        message = f"""
<b>🏀 NBA UNDERDOG ALERT</b>

<b>{pick.underdog.name}</b> ({position} {pick.bet_type.value.upper()})

📊 <b>Matchup:</b> {pick.game.away_team.abbreviation} @ {pick.game.home_team.abbreviation}
📈 <b>Line:</b> {line_str} | <b>Odds:</b> {odds_str}
{conf_emoji} <b>Confidence:</b> {conf}
💰 <b>Kelly Bet:</b> {bet_str}
📉 <b>EV:</b> ${reco.expected_value:+.2f}

<b>Edge:</b> {', '.join(reco.edge_factors) or 'None'}
<b>Risk:</b> {', '.join(reco.risk_factors) or 'None'}

<i>{reco.reasoning[:300]}...</i>

<code>NBA Underdog Bet v0.4.0</code>
"""
        return message.strip()

    def _send_message(self, text: str) -> bool:
        """Send a message to Telegram."""
        if not self.is_configured:
            return False

        url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }

        try:
            response = self._client.post(url, json=payload)
            return response.status_code == 200
        except Exception as e:
            print(f"Telegram notification failed: {e}")
            return False

    def send_test(self) -> bool:
        """Send a test notification."""
        if not self.is_configured:
            return False

        message = f"""
<b>🧪 TEST NOTIFICATION</b>

If you see this, Telegram notifications are working correctly!

<code>Sent at {datetime.now().strftime('%Y-%m-%d %H:%M')}</code>
"""
        return self._send_message(message.strip())
