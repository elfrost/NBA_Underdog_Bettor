"""Main notifier that handles all notification channels."""

from typing import Optional

from config import get_settings
from src.models.schemas import BetRecommendation

from .discord import DiscordNotifier
from .telegram import TelegramNotifier


class Notifier:
    """Unified notifier for all channels."""

    def __init__(self):
        self.settings = get_settings()
        self._discord: Optional[DiscordNotifier] = None
        self._telegram: Optional[TelegramNotifier] = None

        # Initialize Discord if configured
        if self.settings.discord_webhook_url:
            self._discord = DiscordNotifier(self.settings.discord_webhook_url)

        # Initialize Telegram if configured
        if self.settings.telegram_bot_token and self.settings.telegram_chat_id:
            self._telegram = TelegramNotifier(
                self.settings.telegram_bot_token,
                self.settings.telegram_chat_id,
            )

    @property
    def is_enabled(self) -> bool:
        """Check if notifications are enabled."""
        return self.settings.notifications_enabled

    @property
    def has_channels(self) -> bool:
        """Check if any notification channel is configured."""
        return self._discord is not None or (
            self._telegram is not None and self._telegram.is_configured
        )

    def close(self):
        """Close all notifier clients."""
        if self._discord:
            self._discord.close()
        if self._telegram:
            self._telegram.close()

    def should_notify(self, reco: BetRecommendation) -> bool:
        """Check if this pick should trigger a notification."""
        if not self.is_enabled:
            return False

        if not self.has_channels:
            return False

        # Check confidence filter
        if self.settings.notify_high_only:
            return reco.confidence.value == "high"

        # Notify for HIGH and MEDIUM
        return reco.confidence.value in ("high", "medium")

    def send_pick(self, reco: BetRecommendation) -> dict:
        """Send pick notification to all configured channels."""
        results = {"discord": False, "telegram": False}

        if not self.should_notify(reco):
            return results

        if self._discord:
            results["discord"] = self._discord.send_pick(reco)

        if self._telegram and self._telegram.is_configured:
            results["telegram"] = self._telegram.send_pick(reco)

        return results

    def send_test(self) -> dict:
        """Send test notification to all channels."""
        results = {"discord": False, "telegram": False}

        if self._discord:
            results["discord"] = self._discord.send_test()

        if self._telegram and self._telegram.is_configured:
            results["telegram"] = self._telegram.send_test()

        return results


# Singleton instance
_notifier: Optional[Notifier] = None


def get_notifier() -> Notifier:
    """Get notifier instance (singleton)."""
    global _notifier
    if _notifier is None:
        _notifier = Notifier()
    return _notifier


def send_pick_notification(reco: BetRecommendation) -> dict:
    """Convenience function to send a pick notification."""
    notifier = get_notifier()
    return notifier.send_pick(reco)
