"""Main agent loop: data → indicators → sentiment → strategy → risk → execute → notify → store."""
from __future__ import annotations

import argparse
import logging
import signal
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from .config import Config
from .models import Action, Balance, Candle, Decision, Event, MarketContext, Order, OrderResult, OrderSide, OrderType, Position, Report
from .plugin_loader import PluginLoader
from .storage import Storage

logger = logging.getLogger("trade-agent")

_BUILTIN_PLUGINS = Path(__file__).parent / "plugins"


class TradeAgent:
    """Orchestrates the full trading pipeline using plugins."""

    def __init__(self, config: Config):
        self.config = config
        self._running = False
        self._killed = False
        self._api_failures = 0

        # Load all plugins
        loader = PluginLoader(_BUILTIN_PLUGINS)
        self.plugins = loader.load_from_config(config.data)

        # Storage
        db_path = config.get("storage.db_path", "~/.trade-agent/trade-agent.db")
        self.storage = Storage(db_path)

        # Extract commonly used
        self.data_source = self.plugins.get("data_source")
        self.strategy = self.plugins.get("strategy")
        self.exchange = self.plugins.get("exchange")
        self.sentiment = self.plugins.get("sentiment")
        self.risk = self.plugins.get("risk_profile")
        self.indicators = self.plugins.get("indicators")
        self.notifiers = self.plugins.get("notifiers", [])

    def start(self) -> None:
        """Initialize all components and start the main loop."""
        self.storage.init()

        for notifier in self.notifiers:
            notifier.start_polling()

        interval = self.config.get("schedule.interval_minutes", 15)
        max_failures = self.config.get("safety.max_api_failures", 5)
        auto_stop = self.config.get("safety.auto_stop_on_error", True)

        self._running = True
        self._notify(Event(
            category="kill_switch" if self._killed else "trade",
            title="Agent Started",
            message=f"Trade Agent started. Paper mode: {self.config.get('trading.paper_mode', True)}. Interval: {interval}min.",
        ))

        while self._running and not self._killed:
            try:
                self._run_cycle()
                self._api_failures = 0
            except Exception as e:
                self._api_failures += 1
                logger.exception("Cycle failed")
                self._notify(Event(category="error", title="Cycle Error", message=str(e)))
                if auto_stop and self._api_failures >= max_failures:
                    logger.error("Max API failures (%d) reached — stopping", max_failures)
                    self._notify(Event(
                        category="error", title="Agent Stopped",
                        message=f"Stopped after {max_failures} consecutive failures.",
                    ))
                    break

            if self._running and not self._killed:
                sleep_secs = interval * 60
                logger.info("Sleeping %ds until next cycle...", sleep_secs)
                self._interruptible_sleep(sleep_secs)

        self._shutdown()

    def stop(self) -> None:
        """Kill switch — stop the agent."""
        self._killed = True
        self._running = False
        logger.info("Kill switch activated")

    def _interruptible_sleep(self, seconds: int) -> None:
        """Sleep that can be interrupted by kill switch."""
        end = time.time() + seconds
        while time.time() < end and not self._killed:
            time.sleep(min(1, end - time.time()))

    def _run_cycle(self) -> None:
        """Run one trading cycle for all configured symbols."""
        symbols = self._get_symbols()
        balance = self._get_balance()
        positions = self._get_positions()
        daily_pnl = self.storage.get_daily_pnl_pct()

        logger.info("Cycle start — %d symbols, daily P&L: %.2f%%", len(symbols), daily_pnl)

        for sym_cfg in symbols:
            if not sym_cfg.get("enabled", True):
                continue
            symbol = sym_cfg["symbol"]
            timeframe = sym_cfg.get("timeframe", "15m")

            try:
                self._process_symbol(symbol, timeframe, balance, positions, daily_pnl)
            except Exception as e:
                logger.exception("Error processing %s", symbol)
                self._notify(Event(
                    category="error", title=f"Error: {symbol}",
                    message=str(e),
                ))

        # Save portfolio state
        self.storage.save_portfolio(balance)

    def _process_symbol(
        self, symbol: str, timeframe: str,
        balance: Balance, positions: list[Position], daily_pnl: float,
    ) -> None:
        """Process a single symbol: gather data → analyze → decide → execute."""
        logger.info("Processing %s (%s)", symbol, timeframe)

        # 1. Gather market data
        candles = self.data_source.get_candles(symbol, timeframe, limit=200)
        ticker = self.data_source.get_ticker(symbol)

        # 2. Compute indicators
        indicator_set = self.config.get("strategy.prompt.indicator_set", ["rsi", "macd", "ema_20", "ema_50", "bb"])
        indicators = self.indicators.compute(candles, indicator_set) if self.indicators else None

        # 3. Get sentiment (optional)
        sentiment = None
        if self.sentiment:
            try:
                sentiment = self.sentiment.get_sentiment(symbol)
            except Exception:
                logger.debug("Sentiment fetch failed for %s", symbol)

        # 4. Build market context
        context = MarketContext(
            symbol=symbol, timeframe=timeframe, candles=candles,
            ticker=ticker, indicators=indicators or type(indicators)() if indicators else type("I", (), {"to_dict": lambda: {}})(),
            sentiment=sentiment, balance=balance, positions=positions,
            daily_pnl_pct=daily_pnl, config=self.config.data,
        )

        # 5. Strategy decision
        decision = self.strategy.analyze(context)
        logger.info("Decision: %s %s confidence=%d reasoning=%s",
                     decision.action.value, decision.symbol, decision.confidence, decision.reasoning[:100])

        # 6. Risk check
        if not self.risk.check_risk_rules(positions, decision, daily_pnl):
            logger.info("Risk check failed for %s — skipping", symbol)
            self.storage.log_decision(decision, executed=False)
            return

        # 7. Execute (or skip HOLD)
        if decision.action == Action.HOLD:
            self.storage.log_decision(decision, executed=False)
            return

        order_result = self._execute_decision(decision, balance, context)
        self.storage.log_decision(decision, executed=order_result.status != "error", order_id=order_result.order_id)

        if order_result.status != "error":
            self._notify(Event(
                category="trade", title=f"{decision.action.value} {symbol}",
                message=f"Price: ${order_result.price:.2f}\nAmount: {order_result.amount:.6f}\nConfidence: {decision.confidence}%\nReason: {decision.reasoning}",
                data={"order": order_result.order_id},
            ))

    def _execute_decision(self, decision: Decision, balance: Balance, context: MarketContext) -> OrderResult:
        """Execute a trade decision via the exchange plugin."""
        if decision.action == Action.CLOSE_ALL:
            # Close all positions for this symbol
            results = []
            for pos in context.positions:
                if pos.symbol == decision.symbol:
                    side = OrderSide.SELL if pos.side == "long" else OrderSide.BUY
                    order = Order(
                        symbol=decision.symbol, side=side, type=OrderType.MARKET,
                        amount=pos.amount,
                    )
                    result = self.exchange.place_order(order)
                    self.storage.log_trade(result)
                    if result.status != "error":
                        self.storage.close_position(decision.symbol, pos.side)
                    results.append(result)
            if results:
                return results[0]
            return OrderResult(order_id="", symbol=decision.symbol, side="none", type="none",
                               amount=0, price=0, status="error", error="No positions to close")

        # BUY or SELL
        side = OrderSide.BUY if decision.action == Action.BUY else OrderSide.SELL
        position_size = self.risk.calculate_position_size(
            balance.available_usd, decision.confidence,
        )
        price = context.ticker.last_price
        amount = position_size / price if price > 0 else 0

        if amount <= 0:
            return OrderResult(order_id="", symbol=decision.symbol, side=side.value,
                               type="market", amount=0, price=price, status="error",
                               error="Insufficient capital")

        # Calculate stop-loss and take-profit
        stop_loss = self.risk.calculate_stop_loss(price, context)
        take_profit = self.risk.calculate_take_profit(price, stop_loss)

        order = Order(
            symbol=decision.symbol, side=side, type=OrderType.MARKET,
            amount=amount, stop_loss=stop_loss, take_profit=take_profit,
        )

        result = self.exchange.place_order(order)
        self.storage.log_trade(result, stop_loss=stop_loss, take_profit=take_profit)

        if result.status != "error":
            position = Position(
                symbol=decision.symbol,
                side="long" if side == OrderSide.BUY else "short",
                entry_price=result.price, amount=result.amount,
                current_price=result.price, stop_loss=stop_loss, take_profit=take_profit,
            )
            self.storage.open_position(position)

        return result

    def _get_symbols(self) -> list[dict]:
        return self.config.get("trading.symbols", [])

    def _get_balance(self) -> Balance:
        try:
            return self.exchange.get_balance()
        except Exception:
            return Balance()

    def _get_positions(self) -> list[Position]:
        try:
            return self.exchange.get_positions()
        except Exception:
            return []

    def _notify(self, event: Event) -> None:
        for notifier in self.notifiers:
            try:
                notifier.send(event)
            except Exception:
                logger.debug("Notifier %s failed", type(notifier).__name__)

    def _shutdown(self) -> None:
        """Cleanup on shutdown."""
        logger.info("Shutting down...")
        self._notify(Event(
            category="kill_switch", title="Agent Stopped",
            message="Trade Agent has been stopped.",
        ))
        for notifier in self.notifiers:
            try:
                notifier.shutdown()
            except Exception:
                pass
        try:
            self.data_source.shutdown()
            self.exchange.shutdown()
            if self.sentiment:
                self.sentiment.shutdown()
        except Exception:
            pass
        self.storage.shutdown()


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Trade Agent — AI-powered trading bot")
    parser.add_argument("--config", "-c", default="config.yaml", help="Path to config.yaml")
    parser.add_argument("--log-level", default=None, help="Override log level (DEBUG/INFO/WARNING/ERROR)")
    args = parser.parse_args()

    config_path = Path(args.config)
    config = Config(config_path)

    log_level = args.log_level or config.get("agent.log_level", "INFO")
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    issues = config.validate()
    for issue in issues:
        logger.warning("Config issue: %s", issue)

    agent = TradeAgent(config)

    def _signal_handler(sig, frame):
        logger.info("Signal %d received — stopping", sig)
        agent.stop()

    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    agent.start()


if __name__ == "__main__":
    main()
