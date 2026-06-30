"""Backtesting engine — run any strategy on historical data."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from .config import Config
from .models import Action, Balance, MarketContext, Position, Ticker
from .plugin_loader import PluginLoader

_BUILTIN_PLUGINS = Path(__file__).parent / "plugins"
logger = logging.getLogger("trade-agent.backtest")


def run_backtest(config: Config) -> dict[str, Any]:
    """Run a backtest based on config.backtest section.

    Returns results dict with performance metrics.
    """
    bt_cfg = config.section("backtest")
    loader = PluginLoader(_BUILTIN_PLUGINS)

    # Load strategy
    strategy_name = bt_cfg.get("strategy", "llm")
    strategy_cfg = config.section("strategy")
    strategy = loader.load("strategy", strategy_name, strategy_cfg)

    # Load indicators
    indicators = loader.load("indicators", config.get("plugins.indicators", "ta"), {})

    # Load paper exchange for simulation
    exchange = loader.load("exchange", "paper", bt_cfg)

    # Load data source
    data_source_name = bt_cfg.get("data_source", "ccxt")
    ds_cfg = config.section("data_source")
    data_source = loader.load("data_source", data_source_name, ds_cfg)

    # Initialize
    data_source.init(ds_cfg)
    strategy.init(strategy_cfg)
    exchange.init(bt_cfg)

    symbols = bt_cfg.get("symbols", ["BTCUSDT"])
    timeframe = bt_cfg.get("timeframe", "15m")
    initial_capital = float(bt_cfg.get("initial_capital", 10000))

    capital = initial_capital
    positions: list[Position] = []
    trades: list[dict] = []
    equity_curve: list[float] = [initial_capital]

    for symbol in symbols:
        candles = data_source.get_candles(symbol, timeframe, limit=2000)
        if not candles:
            logger.warning("No candles for %s", symbol)
            continue

        indicator_set = config.get(
            "strategy.prompt.indicator_set", ["rsi", "macd", "ema_20", "ema_50", "bb"]
        )
        batch_size = 200

        for i in range(batch_size, len(candles)):
            batch = candles[i - batch_size : i]
            last = batch[-1]

            # Compute indicators
            ind = indicators.compute(batch, indicator_set)

            # Build context
            ticker = Ticker(
                symbol=symbol,
                last_price=last.close,
                bid=last.close,
                ask=last.close,
                volume_24h=sum(c.volume for c in batch[-24:] if len(batch) >= 24),
                change_pct_24h=0,
            )

            balance = Balance(total_usd=capital, available_usd=capital)
            context = MarketContext(
                symbol=symbol,
                timeframe=timeframe,
                candles=batch,
                ticker=ticker,
                indicators=ind,
                balance=balance,
                positions=positions,
                daily_pnl_pct=0,
                config=config.data,
            )

            # Get decision
            decision = strategy.analyze(context)

            # Simulate execution
            if decision.action != Action.HOLD and decision.confidence >= 65:
                price = last.close
                amount = capital * decision.amount_pct / 100 / price

                if decision.action == Action.BUY and amount > 0:
                    cost = amount * price
                    fee = cost * 0.001
                    if cost + fee <= capital:
                        capital -= cost + fee
                        positions.append(
                            Position(
                                symbol=symbol,
                                side="long",
                                entry_price=price,
                                amount=amount,
                                current_price=price,
                            )
                        )
                        trades.append(
                            {
                                "timestamp": last.timestamp,
                                "action": "BUY",
                                "price": price,
                                "amount": amount,
                                "fee": fee,
                                "confidence": decision.confidence,
                            }
                        )
                elif decision.action == Action.SELL:
                    for j, pos in enumerate(positions):
                        if pos.symbol == symbol:
                            proceeds = pos.amount * price
                            fee = proceeds * 0.001
                            pnl = (price - pos.entry_price) * pos.amount - fee
                            capital += proceeds - fee
                            positions.pop(j)
                            trades.append(
                                {
                                    "timestamp": last.timestamp,
                                    "action": "SELL",
                                    "price": price,
                                    "amount": pos.amount,
                                    "pnl": pnl,
                                    "fee": fee,
                                }
                            )
                            break

            equity_curve.append(
                capital + sum(p.amount * p.current_price for p in positions)
            )

    # Calculate metrics
    metrics = _calculate_metrics(trades, equity_curve, initial_capital)

    # Output
    output_path = Path(
        bt_cfg.get("output_path", "~/.trade-agent/backtest-results/")
    ).expanduser()
    output_path.mkdir(parents=True, exist_ok=True)

    result_file = (
        output_path / f"backtest_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    )
    with result_file.open("w") as f:
        json.dump(
            {"metrics": metrics, "trades": trades, "config": bt_cfg},
            f,
            indent=2,
            default=str,
        )

    logger.info(
        "Backtest complete — %d trades, %.1f%% return",
        len(trades),
        metrics["total_return_pct"],
    )

    # Cleanup
    data_source.shutdown()
    exchange.shutdown()

    return metrics


def _calculate_metrics(
    trades: list[dict], equity_curve: list[float], initial_capital: float
) -> dict[str, Any]:
    final_equity = equity_curve[-1] if equity_curve else initial_capital
    total_return = final_equity - initial_capital
    total_return_pct = total_return / initial_capital * 100

    sell_trades = [t for t in trades if t.get("action") == "SELL"]
    winning = sum(1 for t in sell_trades if t.get("pnl", 0) > 0)
    total_sell = len(sell_trades)
    win_rate = winning / max(total_sell, 1) * 100
    total_pnl = sum(t.get("pnl", 0) for t in sell_trades)

    # Max drawdown
    peak = initial_capital
    max_dd = 0.0
    max_dd_pct = 0.0
    for eq in equity_curve:
        if eq > peak:
            peak = eq
        dd = peak - eq
        dd_pct = dd / peak * 100
        if dd_pct > max_dd_pct:
            max_dd_pct = dd_pct
            max_dd = dd

    # Sharpe ratio (simplified)
    if len(equity_curve) > 1:
        returns = [
            (equity_curve[i] - equity_curve[i - 1]) / equity_curve[i - 1]
            for i in range(1, len(equity_curve))
        ]
        avg_return = sum(returns) / len(returns)
        std_return = (sum((r - avg_return) ** 2 for r in returns) / len(returns)) ** 0.5
        sharpe = avg_return / std_return if std_return > 0 else 0
    else:
        sharpe = 0

    return {
        "total_return": total_return,
        "total_return_pct": total_return_pct,
        "final_equity": final_equity,
        "total_trades": len(trades),
        "sell_trades": total_sell,
        "winning_trades": winning,
        "win_rate": win_rate,
        "total_pnl": total_pnl,
        "max_drawdown": max_dd,
        "max_drawdown_pct": max_dd_pct,
        "sharpe_ratio": sharpe,
    }
