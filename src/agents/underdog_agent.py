"""Pydantic AI agent for underdog betting analysis."""

from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider

from src.models.schemas import (
    BetRecommendation,
    BetType,
    Odds,
    UnderdogPick,
)
from config import get_settings


class UnderdogAgent:
    """AI agent that analyzes underdog betting opportunities."""

    SYSTEM_PROMPT = """You are an expert NBA betting analyst specializing in underdog value plays.
Your job is to analyze matchups and identify high-value underdog bets on spreads and moneylines.

Key principles:
1. Contrarian approach - fade public heavy favorites when data supports it
2. Focus on situational advantages: B2B fatigue, rest advantages, injuries to key players
3. Value road underdogs in the +3.5 to +7.5 spread range
4. Moneyline underdogs +150 to +300 offer best risk/reward
5. Be conservative - only recommend bets with clear edges

Analyze the provided game context and output a structured recommendation.
Be specific about WHY this underdog has value, citing concrete factors."""

    def __init__(self):
        settings = get_settings()
        self.model = OpenAIChatModel(
            settings.openrouter_model,
            provider=OpenAIProvider(
                base_url="https://openrouter.ai/api/v1",
                api_key=settings.openrouter_api_key,
            ),
        )
        self.agent = Agent(
            model=self.model,
            system_prompt=self.SYSTEM_PROMPT,
            output_type=BetRecommendation,
        )
        self.settings = settings

    def _format_context(self, pick: UnderdogPick) -> str:
        """Format pick context for AI analysis."""
        uc = pick.underdog_context
        fc = pick.favorite_context

        return f"""
GAME: {pick.game.away_team.name} @ {pick.game.home_team.name}
DATE: {pick.game.date.strftime("%Y-%m-%d %H:%M")}

UNDERDOG: {pick.underdog.name}
- Position: {'Home' if pick.game.home_team.id == pick.underdog.id else 'Road'}
- Line: {'+' if pick.line > 0 else ''}{pick.line} ({pick.bet_type.value})
- Odds: {'+' if pick.odds > 0 else ''}{pick.odds}
- Rest days: {uc.days_rest}
- Back-to-back: {'YES' if uc.is_back_to_back else 'No'}
- Recent form: {uc.recent_record}
- Key injuries: {', '.join(uc.injuries) if uc.injuries else 'None reported'}

FAVORITE: {pick.favorite.name}
- Rest days: {fc.days_rest}
- Back-to-back: {'YES' if fc.is_back_to_back else 'No'}
- Recent form: {fc.recent_record}
- Key injuries: {', '.join(fc.injuries) if fc.injuries else 'None reported'}

BET TYPE: {pick.bet_type.value.upper()}
Analyze this underdog opportunity and provide your recommendation.
"""

    async def analyze_pick(self, pick: UnderdogPick) -> BetRecommendation:
        """Analyze an underdog pick and generate recommendation."""
        context = self._format_context(pick)
        result = await self.agent.run(context)
        return result.output

    def filter_underdog(self, odds: Odds, bet_type: BetType) -> bool:
        """Check if underdog meets filter criteria."""
        if bet_type == BetType.SPREAD:
            # Check if away spread is in target range (road underdog)
            spread = abs(odds.away_spread) if odds.away_spread > 0 else abs(odds.home_spread)
            return self.settings.min_spread <= spread <= self.settings.max_spread
        else:
            # Check ML odds in target range
            ml = odds.away_ml if odds.away_ml > 0 else odds.home_ml
            return self.settings.min_ml_odds <= ml <= self.settings.max_ml_odds
