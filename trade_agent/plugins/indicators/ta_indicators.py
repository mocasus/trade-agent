"""Technical indicators plugin using pandas-ta."""

from __future__ import annotations

from typing import Any

import numpy as np

from trade_agent.interfaces import IndicatorPluginInterface
from trade_agent.models import Candle, Indicators


class TAIndicators(IndicatorPluginInterface):
    def __init__(self):
        self._enabled: set[str] = set()

    def init(self, config: dict[str, Any]) -> None:
        pass

    def compute(self, candles: list[Candle], indicator_set: list[str]) -> Indicators:
        if not candles:
            return Indicators()

        closes = np.array([c.close for c in candles])
        highs = np.array([c.high for c in candles])
        lows = np.array([c.low for c in candles])
        volumes = np.array([c.volume for c in candles])

        result = Indicators()
        wanted = set(indicator_set)

        try:
            import pandas as pd

            df = pd.DataFrame(
                {"close": closes, "high": highs, "low": lows, "volume": volumes}
            )

            if "rsi" in wanted:
                result.rsi = (
                    float(df.ta.rsi(length=14).iloc[-1])
                    if hasattr(df, "ta")
                    else self._rsi(closes)
                )

            if "macd" in wanted:
                macd_data = self._macd(closes)
                result.macd = macd_data[0]
                result.macd_signal = macd_data[1]
                result.macd_histogram = macd_data[2]

            if "ema_20" in wanted:
                result.ema_20 = self._ema(closes, 20)
            if "ema_50" in wanted:
                result.ema_50 = self._ema(closes, 50)
            if "ema_200" in wanted:
                result.ema_200 = self._ema(closes, 200)

            if "bb" in wanted or "bollinger" in wanted:
                bb = self._bollinger(closes)
                result.bb_upper = bb[0]
                result.bb_middle = bb[1]
                result.bb_lower = bb[2]

            if "atr" in wanted:
                result.atr = self._atr(highs, lows, closes, 14)

        except ImportError:
            # Fallback to manual calculations if pandas-ta not installed
            if "rsi" in wanted:
                result.rsi = self._rsi(closes)
            if "macd" in wanted:
                m = self._macd(closes)
                result.macd, result.macd_signal, result.macd_histogram = m
            if "ema_20" in wanted:
                result.ema_20 = self._ema(closes, 20)
            if "ema_50" in wanted:
                result.ema_50 = self._ema(closes, 50)
            if "ema_200" in wanted:
                result.ema_200 = self._ema(closes, 200)
            if "bb" in wanted or "bollinger" in wanted:
                bb = self._bollinger(closes)
                result.bb_upper, result.bb_middle, result.bb_lower = bb
            if "atr" in wanted:
                result.atr = self._atr(highs, lows, closes, 14)

        return result

    def _rsi(self, closes: np.ndarray, period: int = 14) -> float:
        if len(closes) < period + 1:
            return 50.0
        deltas = np.diff(closes)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])
        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return float(100 - (100 / (1 + rs)))

    def _ema(self, data: np.ndarray, period: int) -> float:
        if len(data) < period:
            return float(data[-1]) if len(data) > 0 else 0.0
        multiplier = 2 / (period + 1)
        ema = float(data[0])
        for val in data[1:]:
            ema = (float(val) - ema) * multiplier + ema
        return ema

    def _macd(
        self, closes: np.ndarray, fast: int = 12, slow: int = 26, signal: int = 9
    ) -> tuple:
        if len(closes) < slow + signal:
            return (0.0, 0.0, 0.0)
        ema_fast = self._ema(closes, fast)
        ema_slow = self._ema(closes, slow)
        macd_line = ema_fast - ema_slow
        # Simplified signal line
        macd_values = [
            self._ema(closes[: i + 1], fast) - self._ema(closes[: i + 1], slow)
            for i in range(slow, len(closes))
        ]
        signal_line = (
            self._ema(np.array(macd_values), signal)
            if len(macd_values) >= signal
            else macd_values[-1]
        )
        histogram = macd_line - float(signal_line)
        return (float(macd_line), float(signal_line), float(histogram))

    def _bollinger(
        self, closes: np.ndarray, period: int = 20, std_dev: float = 2.0
    ) -> tuple:
        if len(closes) < period:
            last = float(closes[-1]) if len(closes) > 0 else 0
            return (last, last, last)
        sma = np.mean(closes[-period:])
        std = np.std(closes[-period:])
        return (float(sma + std_dev * std), float(sma), float(sma - std_dev * std))

    def _atr(
        self, highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, period: int = 14
    ) -> float:
        if len(closes) < period + 1:
            return 0.0
        tr_values = []
        for i in range(1, len(closes)):
            tr = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i - 1]),
                abs(lows[i] - closes[i - 1]),
            )
            tr_values.append(tr)
        return float(np.mean(tr_values[-period:]))


def register():
    return {
        "name": "ta",
        "class": TAIndicators,
        "description": "Technical indicators (RSI, MACD, EMA, BB, ATR)",
    }
