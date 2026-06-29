"""LLM-based strategy plugin."""
from __future__ import annotations

import json
import logging
import re
from typing import Any

from openai import OpenAI

from ...interfaces import StrategyInterface
from ...models import Action, Decision, MarketContext

logger = logging.getLogger("trade-agent.strategy.llm")

_DEFAULT_SYSTEM = "You are a disciplined trading analyst. Analyze market data and make decisions based on technical indicators and news sentiment. Always respond with valid JSON."

_DEFAULT_PROMPT = """Analyze the following market data and make a decision.

## Market: {symbol} ({timeframe} timeframe)
Current price: ${{price}}
24h change: {{change_24h}}%
Volume: {{volume_24h}}

## Indicators
{{indicators}}

## Recent News
{{news}}

## Portfolio
Available capital: ${{available}}
Open positions: {{positions}}
Today P&L: {{daily_pnl}}%

## Risk
Max position: {{max_pos_pct}}% of capital
Stop-loss method: {{sl_method}}
Daily loss limit: {{daily_loss_pct}}%

Respond ONLY as JSON:
{{"action": "BUY" | "SELL" | "HOLD" | "CLOSE_ALL", "symbol": "{symbol}", "amount_pct": 5, "confidence": 75, "reasoning": "Brief explanation", "indicators_used": ["rsi", "macd"], "news_factors": ["factor1"]}}"""


class LLMStrategy(StrategyInterface):
    def __init__(self):
        self._client: OpenAI | None = None
        self._model: str = "gpt-4o-mini"
        self._temperature: float = 0.3
        self._max_tokens: int = 500
        self._timeout: int = 30
        self._system_prompt: str = _DEFAULT_SYSTEM
        self._prompt_template: str = _DEFAULT_PROMPT

    def init(self, config: dict[str, Any]) -> None:
        ai = config.get("ai", {})
        self._client = OpenAI(
            base_url=ai.get("base_url", "https://api.openai.com/v1"),
            api_key=ai.get("api_key", ""),
        )
        self._model = ai.get("model", self._model)
        self._temperature = ai.get("temperature", self._temperature)
        self._max_tokens = ai.get("max_tokens", self._max_tokens)
        self._timeout = ai.get("timeout_seconds", self._timeout)

        prompt_cfg = config.get("prompt", {})
        self._system_prompt = prompt_cfg.get("system_prompt", self._system_prompt)
        if prompt_cfg.get("custom_template"):
            template_path = Path(prompt_cfg["custom_template"]).expanduser()
            if template_path.exists():
                self._prompt_template = template_path.read_text()

    def analyze(self, context: MarketContext) -> Decision:
        prompt = self._build_prompt(context)
        try:
            resp = self._client.chat.completions.create(
                model=self._model,
                temperature=self._temperature,
                max_tokens=self._max_tokens,
                timeout=self._timeout,
                messages=[
                    {"role": "system", "content": self._system_prompt},
                    {"role": "user", "content": prompt},
                ],
            )
            raw = resp.choices[0].message.content.strip()
            return self._parse_decision(raw, context.symbol)
        except Exception as e:
            logger.error("LLM call failed: %s", e)
            return Decision(action=Action.HOLD, symbol=context.symbol, confidence=0, reasoning=f"LLM error: {e}")

    def _build_prompt(self, ctx: MarketContext) -> str:
        indicators_str = ""
        if ctx.indicators:
            d = ctx.indicators.to_dict()
            indicators_str = "\n".join(f"{k}: {v}" for k, v in d.items())

        news_str = ""
        if ctx.sentiment and ctx.sentiment.summary:
            news_str = f"Sentiment score: {ctx.sentiment.score:.2f}\n{ctx.sentiment.summary}"

        positions_str = f"{len(ctx.positions)} open"
        if ctx.positions:
            positions_str += " (" + ", ".join(f"{p.symbol} {p.unrealized_pnl_pct:.1f}%" for p in ctx.positions) + ")"

        return self._prompt_template.format(
            symbol=ctx.symbol, timeframe=ctx.timeframe,
            price=ctx.ticker.last_price,
            change_24h=ctx.ticker.change_pct_24h,
            volume_24h=ctx.ticker.volume_24h,
            indicators=indicators_str,
            news=news_str,
            available=ctx.balance.available_usd if ctx.balance else 0,
            positions=positions_str,
            daily_pnl=ctx.daily_pnl_pct,
            max_pos_pct=ctx.config.get("risk", {}).get("position_sizing", {}).get("max_pct", 8),
            sl_method=ctx.config.get("risk", {}).get("stop_loss", {}).get("method", "atr"),
            daily_loss_pct=ctx.config.get("risk", {}).get("daily_limits", {}).get("max_loss_pct", 5),
        )

    def _parse_decision(self, raw: str, symbol: str) -> Decision:
        # Extract JSON from response (may have markdown wrapping)
        json_match = re.search(r"\{[^{}]*\}", raw, re.DOTALL)
        if not json_match:
            return Decision(action=Action.HOLD, symbol=symbol, confidence=0, reasoning=raw)

        try:
            data = json.loads(json_match.group())
            action_str = data.get("action", "HOLD").upper()
            try:
                action = Action(action_str)
            except ValueError:
                action = Action.HOLD

            return Decision(
                action=action,
                symbol=data.get("symbol", symbol),
                amount_pct=float(data.get("amount_pct", 0)),
                confidence=int(data.get("confidence", 0)),
                reasoning=data.get("reasoning", ""),
                indicators_used=data.get("indicators_used", []),
                news_factors=data.get("news_factors", []),
            )
        except json.JSONDecodeError:
            return Decision(action=Action.HOLD, symbol=symbol, confidence=0, reasoning=raw)

    def shutdown(self) -> None:
        pass


def register():
    return {"name": "llm", "class": LLMStrategy, "description": "LLM-based trading strategy"}
