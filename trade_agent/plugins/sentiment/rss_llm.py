"""RSS + LLM sentiment analysis plugin."""
from __future__ import annotations

import hashlib
import json
import logging
import re
import time
from typing import Any

import httpx
from openai import OpenAI

from trade_agent.interfaces import SentimentInterface
from trade_agent.models import SentimentScore

logger = logging.getLogger("trade-agent.sentiment.rss_llm")


class RSSLLMSentiment(SentimentInterface):
    def __init__(self):
        self._feeds: list[dict] = []
        self._max_items: int = 10
        self._cache_hours: int = 2
        self._cache: dict[str, tuple[float, SentimentScore]] = {}
        self._client: OpenAI | None = None
        self._model: str = "gpt-4o-mini"
        self._symbol_filter: bool = True
        self._prompt: str = "brief"

    def init(self, config: dict[str, Any]) -> None:
        self._feeds = config.get("feeds", [])
        self._max_items = config.get("max_items", 10)
        self._cache_hours = config.get("cache_hours", 2)
        self._symbol_filter = config.get("symbol_filter", True)

        ai = config.get("ai", {})
        if ai:
            self._client = OpenAI(
                base_url=ai.get("base_url", "https://api.openai.com/v1"),
                api_key=ai.get("api_key", ""),
            )
            self._model = ai.get("model", "gpt-4o-mini")

        # Use strategy AI config as fallback
        strategy_ai = config.get("strategy", {}).get("ai", {})
        if not self._client and strategy_ai:
            self._client = OpenAI(
                base_url=strategy_ai.get("base_url", "https://api.openai.com/v1"),
                api_key=strategy_ai.get("api_key", ""),
            )
            self._model = strategy_ai.get("sentiment_model_override", strategy_ai.get("model", "gpt-4o-mini"))

    def get_sentiment(self, symbol: str) -> SentimentScore | None:
        # Check cache
        cache_key = symbol
        if cache_key in self._cache:
            ts, cached = self._cache[cache_key]
            if time.time() - ts < self._cache_hours * 3600:
                return cached

        # Fetch news
        items = self._fetch_news(symbol)
        if not items:
            return SentimentScore(symbol=symbol, score=0.0, summary="No recent news", sources=[])

        # LLM sentiment scoring
        if not self._client:
            # Simple keyword-based scoring if no LLM
            return self._keyword_sentiment(symbol, items)

        return self._llm_sentiment(symbol, items)

    def _fetch_news(self, symbol: str) -> list[str]:
        items = []
        for feed_cfg in self._feeds:
            url = feed_cfg.get("url", "")
            if not url:
                continue
            try:
                resp = httpx.get(url, timeout=15, follow_redirects=True)
                if resp.status_code != 200:
                    continue
                # Simple RSS parsing: extract title/description from <item> tags
                raw_items = re.findall(r"<item>.*?</item>", resp.text, re.DOTALL)
                for item_xml in raw_items[:self._max_items]:
                    title = re.search(r"<title>.*?</title>", item_xml)
                    desc = re.search(r"<description>.*?</description>", item_xml)
                    text = ""
                    if title:
                        text += re.sub(r"<[^>]+>", "", title.group()).strip()
                    if desc:
                        text += " " + re.sub(r"<[^>]+>", "", desc.group()).strip()
                    if self._symbol_filter:
                        base = symbol.replace("USDT", "").replace("USD", "")
                        if base.lower() not in text.lower():
                            continue
                    items.append(text)
            except Exception:
                logger.debug("Failed to fetch %s", url)
        return items[:self._max_items]

    def _keyword_sentiment(self, symbol: str, items: list[str]) -> SentimentScore:
        bullish_words = ["surge", "rally", "gain", "bullish", "breakthrough", "approval", "adoption", "upgrade"]
        bearish_words = ["crash", "drop", "loss", "bearish", "ban", "regulation", "hack", "scam", "decline"]
        score = 0.0
        for text in items:
            for w in bullish_words:
                if w in text.lower():
                    score += 0.1
            for w in bearish_words:
                if w in text.lower():
                    score -= 0.1
        score = max(-1.0, min(1.0, score))
        return SentimentScore(symbol=symbol, score=score, summary=f"Keyword analysis: {len(items)} items", sources=["rss"])

    def _llm_sentiment(self, symbol: str, items: list[str]) -> SentimentScore:
        news_text = "\n".join(f"- {item}" for item in items)
        prompt = 'Analyze sentiment for %s based on these news items. Score from -1.0 (bearish) to 1.0 (bullish).\n\n%s\n\nRespond as JSON: {"score": 0.5, "summary": "brief explanation"}' % (symbol, news_text)

        try:
            resp = self._client.chat.completions.create(
                model=self._model, temperature=0.2, max_tokens=200,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = resp.choices[0].message.content.strip()
            json_match = re.search(r"\{[^{}]*\}", raw)
            if json_match:
                data = json.loads(json_match.group())
                score = float(data.get("score", 0))
                summary = data.get("summary", "")
                result = SentimentScore(symbol=symbol, score=score, summary=summary, sources=["rss", "llm"])
                self._cache[symbol] = (time.time(), result)
                return result
        except Exception as e:
            logger.error("LLM sentiment failed: %s", e)

        return self._keyword_sentiment(symbol, items)

    def shutdown(self) -> None:
        pass


def register():
    return {"name": "rss_llm", "class": RSSLLMSentiment, "description": "RSS + LLM sentiment analysis"}
