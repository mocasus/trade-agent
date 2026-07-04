"""invinoveritas pre-trade verification risk-profile plugin.

Optional, opt-in (you must set `risk_profile: invinoveritas` in config.yaml — the shipped
default stays `moderate`). Wraps an existing risk profile unchanged for position sizing /
stop-loss / take-profit; adds exactly ONE extra check inside check_risk_rules(): after the
wrapped profile's own rules already allow the trade, POST the proposed decision to
invinoveritas (https://api.babyblueviper.com/review) — an independent, third-party
pre-trade verification service — and see what an outside check makes of it.

Advisory by default: a "reject" verdict is logged as a warning but does NOT block the
trade unless you set `enforce: true`. Fails OPEN on any network error, timeout, missing/
invalid api_key, or payment-required (free-call quota used up): the base profile's rules
always apply unchanged in that case, so an unreachable third-party check can never freeze
or silently block live trading.

Get a free API key (3 free calls, no funding needed): POST https://api.babyblueviper.com/register
Live contract verified directly against the API before writing this file (2026-07-02):
POST {"artifact": <str>, "artifact_type": "trade"} -> {"verdict": "approve"|"approve_with_concerns"|"reject", "summary": <str>, ...}
"""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from trade_agent.interfaces import RiskProfileInterface
from trade_agent.models import MarketContext
from trade_agent.plugins.risk_profile.aggressive import AggressiveProfile
from trade_agent.plugins.risk_profile.conservative import ConservativeProfile
from trade_agent.plugins.risk_profile.moderate import ModerateProfile

logger = logging.getLogger("trade-agent.risk_profile.invinoveritas")

_BASE_PROFILES = {
    "conservative": ConservativeProfile,
    "moderate": ModerateProfile,
    "aggressive": AggressiveProfile,
}

_DEFAULT_ENDPOINT = "https://api.babyblueviper.com/review"


class InvinoveritasProfile(RiskProfileInterface):
    def __init__(self):
        self._base = ModerateProfile()
        self._endpoint = _DEFAULT_ENDPOINT
        self._api_key = ""
        self._timeout_s = 8.0
        self._enforce = False
        self._warned_no_key = False

    def init(self, config: dict[str, Any]) -> None:
        base_name = config.get("base_profile", "moderate")
        base_cls = _BASE_PROFILES.get(base_name)
        if base_cls is None:
            logger.warning(
                "invinoveritas: unknown base_profile %r, falling back to 'moderate' "
                "(valid options: %s)", base_name, ", ".join(sorted(_BASE_PROFILES)),
            )
            base_cls = ModerateProfile
        self._base = base_cls()
        self._base.init(config)

        iv = config.get("invinoveritas") or {}
        self._endpoint = iv.get("endpoint", _DEFAULT_ENDPOINT)
        self._api_key = iv.get("api_key", "")
        self._timeout_s = float(iv.get("timeout_s", 8.0))
        self._enforce = bool(iv.get("enforce", False))

    def calculate_position_size(self, available_capital: float, confidence: int) -> float:
        return self._base.calculate_position_size(available_capital, confidence)

    def calculate_stop_loss(self, entry_price: float, context: MarketContext) -> float:
        return self._base.calculate_stop_loss(entry_price, context)

    def calculate_take_profit(self, entry_price: float, stop_loss: float) -> float:
        return self._base.calculate_take_profit(entry_price, stop_loss)

    def check_risk_rules(self, positions, decision, daily_pnl_pct) -> bool:
        # The wrapped profile's own rules run first and unchanged — invinoveritas only
        # ever adds an EXTRA check on top, never loosens an existing one.
        if not self._base.check_risk_rules(positions, decision, daily_pnl_pct):
            return False
        if decision.action.value == "HOLD":
            return True
        if not self._api_key:
            if not self._warned_no_key:
                logger.warning(
                    "invinoveritas risk_profile has no api_key configured — every check "
                    "fails open (base profile rules apply unchanged, no external "
                    "verification runs). Get a free key: "
                    "POST https://api.babyblueviper.com/register"
                )
                self._warned_no_key = True
            return True

        verdict, summary = self._review(positions, decision, daily_pnl_pct)
        if verdict is None:
            return True  # unavailable / error — fail open, already logged in _review()
        if verdict == "reject":
            logger.warning(
                "invinoveritas REJECTED %s %s (confidence %s, enforce=%s): %s",
                decision.action.value, decision.symbol, decision.confidence,
                self._enforce, summary,
            )
            return not self._enforce
        if verdict == "approve_with_concerns":
            logger.info(
                "invinoveritas approved %s %s WITH CONCERNS: %s",
                decision.action.value, decision.symbol, summary,
            )
        return True

    def _review(self, positions, decision, daily_pnl_pct) -> tuple[str | None, str]:
        """POST the proposed decision to /review. Returns (verdict, summary) or
        (None, reason) on any failure — callers treat None as fail-open."""
        artifact = json.dumps({
            "action": decision.action.value,
            "symbol": decision.symbol,
            "amount_pct": decision.amount_pct,
            "confidence": decision.confidence,
            "reasoning": decision.reasoning,
            "indicators_used": decision.indicators_used,
            "news_factors": decision.news_factors,
            "open_positions": len(positions),
            "daily_pnl_pct": daily_pnl_pct,
        })
        try:
            resp = httpx.post(
                self._endpoint,
                headers={"Authorization": f"Bearer {self._api_key}"},
                json={
                    "artifact": artifact,
                    "artifact_type": "trade",
                    "context": "trade-agent pre-trade check",
                },
                timeout=self._timeout_s,
            )
        except httpx.RequestError as exc:
            logger.warning(
                "invinoveritas /review unreachable (%s) — failing open, base profile "
                "rules apply unchanged", type(exc).__name__,
            )
            return None, ""
        if resp.status_code == 402:
            logger.info(
                "invinoveritas /review: free-call quota used up or account unfunded "
                "(402) — failing open. Fund at https://api.babyblueviper.com/topup"
            )
            return None, ""
        if resp.status_code != 200:
            logger.warning(
                "invinoveritas /review returned HTTP %s — failing open, base profile "
                "rules apply unchanged", resp.status_code,
            )
            return None, ""
        try:
            body = resp.json()
            return body.get("verdict"), body.get("summary", "")
        except Exception as exc:
            logger.warning(
                "invinoveritas /review response unparseable (%s) — failing open",
                type(exc).__name__,
            )
            return None, ""


def register():
    return {
        "name": "invinoveritas",
        "class": InvinoveritasProfile,
        "description": (
            "Wraps another risk profile and adds an independent third-party pre-trade "
            "verification check (invinoveritas /review) on top — advisory by default, "
            "opt-in enforce mode to actually veto a rejected trade"
        ),
    }
