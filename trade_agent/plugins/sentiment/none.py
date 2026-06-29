"""Disabled sentiment plugin — returns None."""
from __future__ import annotations

from typing import Any

from ...interfaces import SentimentInterface
from ...models import SentimentScore


class NoneSentiment(SentimentInterface):
    def __init__(self):
        pass

    def init(self, config: dict[str, Any]) -> None:
        pass

    def get_sentiment(self, symbol: str) -> SentimentScore | None:
        return None

    def shutdown(self) -> None:
        pass


def register():
    return {"name": "none", "class": NoneSentiment, "description": "Disable sentiment (returns None)"}
