"""Crypto Trading Platform — Forward Real-Time Paper Trading Daemon.

Consumes real-time market data (via WebSocket or synthetic stream), generates strategy signals,
evaluates them through the independent Risk Firewall, simulates fills via the
Microstructure Paper Simulator, updates OMS positions, tracks real-time virtual equity and PnL,
and commits state to durable SQLite storage for seamless crash recovery.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from typing import Any, Dict, List, Optional

from crypto_platform.core.domain import (
    AccountBalance,
    ExecutionOrder,
    Fill,
    OperatingMode,
    OrderIntent,
    OrderSide,
    OrderStatus,
    OrderType,
    Position,
    RiskDecision,
    RiskState,
    TimeInForce,
)
from crypto_platform.core.events import CandleEvent, FundingRateEvent, TickerEvent
from crypto_platform.core.interfaces import IStrategy
from crypto_platform.order_management.oms import OrderManagementSystem
from crypto_platform.risk_engine.firewall import RiskFirewall
from .funnel import ExecutionFunnel
from .persistence import SQLitePaperLedger
from .simulator import MicrostructurePaperSimulator

logger = logging.getLogger("crypto_platform.paper_trading.daemon")


class ForwardPaperTradingDaemon:
    """Orchestrates forward paper trading with complete execution fidelity and durability."""

    def __init__(
        self,
        tenant_id: str = "t_default",
        account_id: str = "acct_paper_01",
        initial_equity: float = 100_000.0,
        risk_firewall: Optional[RiskFirewall] = None,
        simulator: Optional[MicrostructurePaperSimulator] = None,
        ledger: Optional[SQLitePaperLedger] = None,
        db_path: Optional[str] = None,
        order_ttl_ms: int = 3_600_000,
    ):
        self.tenant_id = tenant_id
        self.account_id = account_id
        self.initial_equity = initial_equity
        self.current_equity = initial_equity
        self.peak_equity = initial_equity
        self.order_ttl_ms = order_ttl_ms
        self._processed_candle_keys: set[str] = set()

        self.risk_firewall = risk_firewall or RiskFirewall()
        self.simulator = simulator or MicrostructurePaperSimulator()
        self.oms = OrderManagementSystem()

        # Durable ledger
        if ledger is not None:
            self.ledger = ledger
        elif db_path is not None:
            self.ledger = SQLitePaperLedger(db_path=db_path)
        else:
            self.ledger = None

        self.strategies: Dict[str, IStrategy] = {}
        self.latest_tickers: Dict[str, TickerEvent] = {}
        self.balances: Dict[str, AccountBalance] = {
            "USDT": AccountBalance(
                asset="USDT", free=initial_equity, locked=0.0, total=initial_equity
            )
        }
        self.fills_history: List[Fill] = []
        self.equity_curve: List[tuple[int, float]] = [(int(time.time() * 1000), initial_equity)]

        # Telemetry & Observability Funnel
        self.funnel = ExecutionFunnel()
        self.market_events_count = 0
        self.signals_generated_count = 0
        self.signals_rejected_count = 0
        self.orders_simulated_count = 0
        self.risk_decisions: List[RiskDecision] = []
        self.latencies_ms: List[float] = []
        self.trade_audit_trail: List[Dict[str, Any]] = []

        # Rehydrate from ledger if available
        self._recover_state()

    def _recover_state(self) -> None:
        """Restores positions, fills, and equity state from SQLite ledger if present."""
        if not self.ledger:
            return

        recovered_positions = self.ledger.load_positions(self.account_id)
        acct_pos = self.oms._positions.setdefault(self.account_id, {})
        for sym, pos in recovered_positions.items():
            acct_pos[sym] = pos

        recovered_fills = self.ledger.load_fills(self.account_id)
        if recovered_fills:
            self.fills_history.extend(recovered_fills)

        latest_eq = self.ledger.load_latest_equity(self.account_id)
        if latest_eq:
            self.current_equity = latest_eq["equity"]
            self.peak_equity = latest_eq["peak_equity"]
            logger.info(
                f"Recovered paper account {self.account_id}: "
                f"Equity=${self.current_equity:,.2f}, Positions={len(recovered_positions)}"
            )

    def warm_up(self, cache_dir: str = "market_data/cache", bars: int = 60) -> Dict[str, int]:
        """Pre-warms registered strategies with historical certified closed bars.
        
        Guarantees strategy lookbacks (e.g. 21 bars for trend, 20 bars for MR, 6 rates for carry)
        are fulfilled before live session execution, eliminating cold-start starvation
        without modifying any frozen strategy parameters.
        """
        loaded_counts: Dict[str, int] = {}
        tf_map = {
            "INTRADAY": "15m",
            "SWING": "1h",
            "POSITION": "4h",
            "INVEST": "1d",
            "CARRY": "1d",
        }

        for strat_id, strat in self.strategies.items():
            loaded_counts[strat_id] = 0
            horizon = getattr(strat, "horizon", "INTRADAY")
            target_tf = tf_map.get(horizon, "15m")

            # 1. Pre-warm closed candles
            for sym in getattr(strat, "supported_symbols", []):
                cache_file = os.path.join(cache_dir, f"binance_{sym}_{target_tf}.json")
                if not os.path.exists(cache_file):
                    continue
                try:
                    with open(cache_file, "r") as f:
                        raw = json.load(f)
                    if isinstance(raw, list) and raw:
                        tail = raw[-bars:]
                        candle_list = []
                        for row in tail:
                            c = CandleEvent(
                                venue="binance",
                                symbol=sym,
                                timeframe=target_tf,
                                open_ts=int(row[0]),
                                close_ts=int(row[6]),
                                open=float(row[1]),
                                high=float(row[2]),
                                low=float(row[3]),
                                close=float(row[4]),
                                volume=float(row[5]),
                                is_closed=True,
                            )
                            candle_list.append(c)
                            self._processed_candle_keys.add(f"binance_{sym}_{target_tf}_{c.close_ts}")
                        strat.recent_candles[sym] = candle_list
                        loaded_counts[strat_id] += len(candle_list)
                except Exception as e:
                    logger.warning(f"Error pre-warming {sym} {target_tf} for {strat_id}: {e}")

            # 2. Pre-warm funding rates for carry strategies
            if hasattr(strat, "_funding_rates"):
                for sym in getattr(strat, "supported_symbols", []):
                    f_file = os.path.join(cache_dir, f"binance_funding_{sym}.json")
                    if os.path.exists(f_file):
                        try:
                            with open(f_file, "r") as f:
                                f_raw = json.load(f)
                            if isinstance(f_raw, list) and f_raw:
                                rates = []
                                for row in f_raw[-bars:]:
                                    if isinstance(row, dict):
                                        rates.append(float(row.get("fundingRate", 0.0)))
                                    elif isinstance(row, (list, tuple)):
                                        rates.append(float(row[1]))
                                    else:
                                        rates.append(float(row))
                                strat._funding_rates[sym] = rates
                                loaded_counts[strat_id] += len(rates)
                        except Exception as e:
                            logger.warning(f"Error pre-warming funding rates for {sym}: {e}")

        logger.info(f"Pre-warmed strategies with historical lookbacks: {loaded_counts}")
        return loaded_counts

    def register_strategy(self, strategy: IStrategy) -> None:
        self.strategies[strategy.strategy_id] = strategy

    def connect_market_data(self, ws_client: Any) -> None:
        """Wire this daemon to a PublicWebSocketClient instance."""
        ws_client.subscribe("ticker", self.on_ticker)
        ws_client.subscribe("candle", self.on_candle)
        if hasattr(self, "on_funding_rate"):
            ws_client.subscribe("funding_rate", self.on_funding_rate)

    def disconnect_market_data(self, ws_client: Any) -> None:
        """Unwire this daemon from a PublicWebSocketClient instance."""
        if hasattr(ws_client, "unsubscribe"):
            ws_client.unsubscribe("ticker", self.on_ticker)
            ws_client.unsubscribe("candle", self.on_candle)
            if hasattr(self, "on_funding_rate"):
                ws_client.unsubscribe("funding_rate", self.on_funding_rate)

    def on_ticker(self, ticker: TickerEvent) -> List[Fill]:
        """Update market price, check resting limit orders, and update unrealized PnL."""
        t_start = time.perf_counter()
        self.market_events_count += 1
        self.funnel.market_events += 1
        self.latest_tickers[ticker.symbol] = ticker
        executed_fills: List[Fill] = []
        now_ms = ticker.timestamp_ms

        # Check working orders for this symbol
        open_orders = self.oms.get_open_orders(self.account_id)
        for order in open_orders:
            if order.symbol == ticker.symbol:
                # Check order TTL expiration
                if order.created_at_ms > 0 and (now_ms - order.created_at_ms) > self.order_ttl_ms:
                    self.oms.update_order_status(
                        self.account_id,
                        order.order_id,
                        OrderStatus.EXPIRED,
                        message=f"Order TTL expired ({self.order_ttl_ms}ms)",
                    )
                    self.funnel.expired_orders += 1
                    self.funnel.record_rejection("ORDER_EXPIRED")
                    if self.ledger:
                        self.ledger.save_order(order, self.account_id)
                    continue

                fill = self.simulator.process_order(order, ticker)
                if fill is not None:
                    self.oms.register_fill(fill, self.account_id)
                    self.fills_history.append(fill)
                    executed_fills.append(fill)

                    if order.status == OrderStatus.FILLED:
                        self.funnel.full_fills += 1
                    else:
                        self.funnel.partial_fills += 1

                    if self.ledger:
                        self.ledger.save_order(order, self.account_id)
                        self.ledger.record_fill(fill, self.account_id)

                    for s in self.strategies.values():
                        s.on_fill(fill)

        # Update position mark prices and unrealized PnL
        positions = self.oms.get_positions(self.account_id)
        total_unrealized_pnl = 0.0
        for p in positions.values():
            if p.symbol == ticker.symbol:
                p.mark_price = ticker.last_price
                p.unrealized_pnl = (p.mark_price - p.entry_price) * p.size * p.direction
                if self.ledger:
                    self.ledger.save_position(p, self.account_id)
            total_unrealized_pnl += p.unrealized_pnl

        # Calculate current equity
        realized_pnl = sum(p.realized_pnl for p in positions.values())
        fees_paid = sum(f.fee for f in self.fills_history)
        self.current_equity = self.initial_equity + realized_pnl + total_unrealized_pnl - fees_paid
        if self.current_equity > self.peak_equity:
            self.peak_equity = self.current_equity

        self.equity_curve.append((ticker.timestamp_ms, round(self.current_equity, 2)))

        if self.ledger:
            dd_pct = (self.peak_equity - self.current_equity) / self.peak_equity if self.peak_equity > 0 else 0.0
            self.ledger.record_equity_snapshot(
                account_id=self.account_id,
                timestamp_ms=ticker.timestamp_ms,
                equity=self.current_equity,
                peak_equity=self.peak_equity,
                drawdown_pct=dd_pct,
                realized_pnl=realized_pnl,
                total_fees=fees_paid,
            )

        latency_ms = (time.perf_counter() - t_start) * 1000.0
        self.latencies_ms.append(latency_ms)
        return executed_fills

    def on_candle(self, candle: CandleEvent) -> List[ExecutionOrder]:
        """Dispatch closed candles to strategies, evaluate intents through Risk, and route orders."""
        self.market_events_count += 1
        self.funnel.market_events += 1

        if not candle.is_closed:
            self.funnel.unclosed_candles += 1
            self.funnel.record_rejection("UNCLOSED_CANDLE")
            return []

        candle_key = f"{candle.venue}_{candle.symbol}_{candle.timeframe}_{candle.close_ts}"
        if candle_key in self._processed_candle_keys:
            self.funnel.duplicate_candles += 1
            self.funnel.record_rejection("DUPLICATE_CANDLE")
            return []
        self._processed_candle_keys.add(candle_key)
        if len(self._processed_candle_keys) > 50000:
            self._processed_candle_keys.clear()
            self._processed_candle_keys.add(candle_key)

        self.funnel.closed_candles += 1
        t_start = time.perf_counter()
        generated_orders: List[ExecutionOrder] = []

        ticker = self.latest_tickers.get(candle.symbol)
        if ticker is None:
            ticker = TickerEvent(
                venue=candle.venue,
                symbol=candle.symbol,
                timestamp_ms=candle.close_ts,
                bid=candle.close * 0.9998,
                ask=candle.close * 1.0002,
                last_price=candle.close,
            )
            self.latest_tickers[candle.symbol] = ticker

        positions = self.oms.get_positions(self.account_id)
        risk_state = RiskState(
            equity=self.current_equity,
            peak_equity=self.peak_equity,
            drawdown_pct=(self.peak_equity - self.current_equity) / self.peak_equity if self.peak_equity > 0 else 0.0,
        )

        tf_map = {
            "INTRADAY": "15m",
            "SWING": "1h",
            "POSITION": "4h",
            "INVEST": "1d",
            "CARRY": "1d",
        }

        for strat in self.strategies.values():
            if hasattr(strat, "supported_symbols") and strat.supported_symbols:
                if candle.symbol not in strat.supported_symbols:
                    continue

            self.funnel.strategy_evaluations += 1
            self.funnel.record_strategy_metric(strat.strategy_id, "evaluations", 1)

            history = getattr(strat, "recent_candles", {}).get(candle.symbol, [])
            lookback_req = getattr(strat, "lookback", getattr(strat, "period", 20)) + 1
            history_len_before = len(history)

            intents = strat.on_candle(candle)

            if not intents:
                if history_len_before < lookback_req:
                    self.funnel.record_rejection("INSUFFICIENT_LOOKBACK")
                    self.funnel.record_strategy_metric(strat.strategy_id, "insufficient_lookback", 1)
                else:
                    self.funnel.record_rejection("NO_SIGNAL")
                    self.funnel.record_strategy_metric(strat.strategy_id, "no_signal", 1)
                continue

            for intent in intents:
                self.signals_generated_count += 1
                self.funnel.signals += 1
                self.funnel.order_intents += 1
                self.funnel.record_strategy_metric(strat.strategy_id, "signals", 1)

                # 1. Evaluate intent through independent Fail-Closed Risk Firewall
                decision = self.risk_firewall.evaluate_order_intent(
                    intent=intent,
                    current_positions=positions,
                    balances=self.balances,
                    risk_state=risk_state,
                    latest_ticker=ticker,
                )
                self.risk_decisions.append(decision)

                if not decision.approved:
                    self.signals_rejected_count += 1
                    self.funnel.risk_rejections += 1
                    rule_code = decision.rule_code or "RISK_LIMIT"
                    self.funnel.record_rejection(rule_code)
                    self.funnel.record_strategy_metric(strat.strategy_id, f"rejected_{rule_code}", 1)
                    self._record_audit_trail(
                        strategy_id=strat.strategy_id,
                        horizon=getattr(strat, "horizon", "INTRADAY"),
                        intent=intent,
                        ticker=ticker,
                        decision=decision,
                        latency_ms=(time.perf_counter() - t_start) * 1000.0,
                        rejection_reason=rule_code,
                    )
                    if self.ledger:
                        self.ledger.log_audit_event(
                            account_id=self.account_id,
                            event_type="RISK_REJECTION",
                            severity="WARNING",
                            message=f"Order intent {intent.intent_id} rejected: {decision.reason}",
                            details={"rule_code": decision.rule_code, "symbol": intent.symbol},
                        )
                    continue

                # 2. Portfolio Allocation Gating (leverage & concentration caps)
                current_exposure = sum(abs(p.size * p.entry_price) for p in positions.values())
                order_px = intent.limit_price or ticker.last_price
                new_notional = intent.target_size * order_px
                if (current_exposure + new_notional) > self.current_equity * 2.0:
                    self.funnel.allocation_rejections += 1
                    self.funnel.record_rejection("PORTFOLIO_LIMIT")
                    self.funnel.record_strategy_metric(strat.strategy_id, "rejected_portfolio_limit", 1)
                    self._record_audit_trail(
                        strategy_id=strat.strategy_id,
                        horizon=getattr(strat, "horizon", "INTRADAY"),
                        intent=intent,
                        ticker=ticker,
                        decision=decision,
                        latency_ms=(time.perf_counter() - t_start) * 1000.0,
                        rejection_reason="PORTFOLIO_LIMIT",
                    )
                    continue

                # 3. OMS creates and routes order
                order = self.oms.create_order_from_intent(intent, decision, venue=candle.venue)
                generated_orders.append(order)
                self.orders_simulated_count += 1
                self.funnel.oms_acceptances += 1
                self.funnel.simulator_submissions += 1
                self.funnel.record_strategy_metric(strat.strategy_id, "orders_submitted", 1)

                if self.ledger:
                    self.ledger.save_order(order, self.account_id)

                # 4. Microstructure simulator attempts fill
                fill = self.simulator.process_order(order, ticker)
                if fill is not None:
                    self.oms.register_fill(fill, self.account_id)
                    self.fills_history.append(fill)
                    strat.on_fill(fill)

                    if order.status == OrderStatus.FILLED:
                        self.funnel.full_fills += 1
                        self.funnel.record_strategy_metric(strat.strategy_id, "full_fills", 1)
                    else:
                        self.funnel.partial_fills += 1
                        self.funnel.resting_orders += 1
                        self.funnel.record_strategy_metric(strat.strategy_id, "partial_fills", 1)

                    self._record_audit_trail(
                        strategy_id=strat.strategy_id,
                        horizon=getattr(strat, "horizon", "INTRADAY"),
                        intent=intent,
                        ticker=ticker,
                        decision=decision,
                        order=order,
                        fill=fill,
                        latency_ms=(time.perf_counter() - t_start) * 1000.0,
                    )

                    if self.ledger:
                        self.ledger.save_order(order, self.account_id)
                        self.ledger.record_fill(fill, self.account_id)
                        pos = self.oms.get_positions(self.account_id).get(fill.symbol)
                        if pos:
                            self.ledger.save_position(pos, self.account_id)
                else:
                    # IOC or Market orders cannot sit resting
                    if order.time_in_force == TimeInForce.IOC or order.order_type == OrderType.MARKET:
                        self.oms.update_order_status(
                            self.account_id,
                            order.order_id,
                            OrderStatus.CANCELLED,
                            message="IOC / Market order expired: no immediate fill",
                        )
                        self.funnel.cancelled_orders += 1
                        self.funnel.record_rejection("IOC_CANCELLED")
                        self.funnel.record_strategy_metric(strat.strategy_id, "ioc_cancelled", 1)
                        self._record_audit_trail(
                            strategy_id=strat.strategy_id,
                            horizon=getattr(strat, "horizon", "INTRADAY"),
                            intent=intent,
                            ticker=ticker,
                            decision=decision,
                            order=order,
                            latency_ms=(time.perf_counter() - t_start) * 1000.0,
                            rejection_reason="IOC_CANCELLED",
                        )
                        if self.ledger:
                            self.ledger.save_order(order, self.account_id)
                    else:
                        self.funnel.resting_orders += 1
                        self.funnel.record_strategy_metric(strat.strategy_id, "resting_orders", 1)
                        if order.order_type == OrderType.POST_ONLY and (
                            (order.side == OrderSide.BUY and order.price is not None and order.price >= ticker.ask)
                            or (order.side == OrderSide.SELL and order.price is not None and order.price <= ticker.bid)
                        ):
                            self.funnel.record_rejection("POST_ONLY_CROSS")
                            rej_r = "POST_ONLY_CROSS"
                        elif ticker.last_price == order.price:
                            self.funnel.record_rejection("QUEUE_NOT_CLEARED")
                            rej_r = "QUEUE_NOT_CLEARED"
                        else:
                            self.funnel.record_rejection("RESTING_AWAY_FROM_MARKET")
                            rej_r = "RESTING_AWAY_FROM_MARKET"
                        self._record_audit_trail(
                            strategy_id=strat.strategy_id,
                            horizon=getattr(strat, "horizon", "INTRADAY"),
                            intent=intent,
                            ticker=ticker,
                            decision=decision,
                            order=order,
                            latency_ms=(time.perf_counter() - t_start) * 1000.0,
                            rejection_reason=rej_r,
                        )

        latency_ms = (time.perf_counter() - t_start) * 1000.0
        self.latencies_ms.append(latency_ms)
        return generated_orders

    def on_funding_rate(self, event: FundingRateEvent) -> List[ExecutionOrder]:
        """Dispatch funding rate updates to carry strategies."""
        self.market_events_count += 1
        self.funnel.market_events += 1
        t_start = time.perf_counter()
        generated_orders: List[ExecutionOrder] = []

        ticker = self.latest_tickers.get(event.symbol)
        if ticker is None:
            ticker = TickerEvent(
                venue=event.venue,
                symbol=event.symbol,
                timestamp_ms=event.timestamp_ms,
                bid=event.mark_price * 0.9999,
                ask=event.mark_price * 1.0001,
                last_price=event.mark_price,
            )
            self.latest_tickers[event.symbol] = ticker

        positions = self.oms.get_positions(self.account_id)
        risk_state = RiskState(
            equity=self.current_equity,
            peak_equity=self.peak_equity,
            drawdown_pct=(self.peak_equity - self.current_equity) / self.peak_equity if self.peak_equity > 0 else 0.0,
        )

        for strat in self.strategies.values():
            if not hasattr(strat, "on_funding_rate"):
                continue
            if event.symbol not in getattr(strat, "supported_symbols", []):
                continue

            self.funnel.strategy_evaluations += 1
            self.funnel.record_strategy_metric(strat.strategy_id, "evaluations", 1)

            intents = strat.on_funding_rate(event)
            if not intents:
                rates_len = len(getattr(strat, "_funding_rates", {}).get(event.symbol, []))
                if rates_len < 6:
                    self.funnel.record_rejection("INSUFFICIENT_LOOKBACK")
                    self.funnel.record_strategy_metric(strat.strategy_id, "insufficient_lookback", 1)
                else:
                    self.funnel.record_rejection("NO_SIGNAL")
                    self.funnel.record_strategy_metric(strat.strategy_id, "no_signal", 1)
                continue

            for intent in intents:
                self.signals_generated_count += 1
                self.funnel.signals += 1
                self.funnel.order_intents += 1
                self.funnel.record_strategy_metric(strat.strategy_id, "signals", 1)

                decision = self.risk_firewall.evaluate_order_intent(
                    intent=intent,
                    current_positions=positions,
                    balances=self.balances,
                    risk_state=risk_state,
                    latest_ticker=ticker,
                )
                self.risk_decisions.append(decision)

                if decision.approved:
                    order = self.oms.create_order_from_intent(intent, decision, venue=event.venue)
                    generated_orders.append(order)
                    self.orders_simulated_count += 1
                    self.funnel.oms_acceptances += 1
                    self.funnel.simulator_submissions += 1
                    self.funnel.record_strategy_metric(strat.strategy_id, "orders_submitted", 1)

                    if self.ledger:
                        self.ledger.save_order(order, self.account_id)

                    fill = self.simulator.process_order(order, ticker)
                    if fill is not None:
                        self.oms.register_fill(fill, self.account_id)
                        self.fills_history.append(fill)
                        strat.on_fill(fill)
                        self.funnel.full_fills += 1
                        self.funnel.record_strategy_metric(strat.strategy_id, "full_fills", 1)

                        self._record_audit_trail(
                            strategy_id=strat.strategy_id,
                            horizon=getattr(strat, "horizon", "CARRY"),
                            intent=intent,
                            ticker=ticker,
                            decision=decision,
                            order=order,
                            fill=fill,
                            latency_ms=(time.perf_counter() - t_start) * 1000.0,
                        )

                        if self.ledger:
                            self.ledger.save_order(order, self.account_id)
                            self.ledger.record_fill(fill, self.account_id)
                    else:
                        self.funnel.resting_orders += 1
                        self.funnel.record_strategy_metric(strat.strategy_id, "resting_orders", 1)
                        self._record_audit_trail(
                            strategy_id=strat.strategy_id,
                            horizon=getattr(strat, "horizon", "CARRY"),
                            intent=intent,
                            ticker=ticker,
                            decision=decision,
                            order=order,
                            latency_ms=(time.perf_counter() - t_start) * 1000.0,
                            rejection_reason="RESTING_AWAY_FROM_MARKET",
                        )
                else:
                    self.signals_rejected_count += 1
                    self.funnel.risk_rejections += 1
                    rej = decision.rule_code or "RISK_LIMIT"
                    self.funnel.record_rejection(rej)
                    self.funnel.record_strategy_metric(strat.strategy_id, f"rejected_{rej}", 1)
                    self._record_audit_trail(
                        strategy_id=strat.strategy_id,
                        horizon=getattr(strat, "horizon", "CARRY"),
                        intent=intent,
                        ticker=ticker,
                        decision=decision,
                        latency_ms=(time.perf_counter() - t_start) * 1000.0,
                        rejection_reason=rej,
                    )

        latency_ms = (time.perf_counter() - t_start) * 1000.0
        self.latencies_ms.append(latency_ms)
        return generated_orders

    def _record_audit_trail(
        self,
        strategy_id: str,
        horizon: str,
        intent: OrderIntent,
        ticker: Optional[TickerEvent],
        decision: Optional[RiskDecision] = None,
        order: Optional[ExecutionOrder] = None,
        fill: Optional[Fill] = None,
        latency_ms: float = 0.0,
        rejection_reason: Optional[str] = None,
    ) -> None:
        """Record structured machine-readable order and fill telemetry."""
        spread = round(abs(ticker.ask - ticker.bid), 6) if ticker else 0.0
        bid_px = ticker.bid if ticker else 0.0
        ask_px = ticker.ask if ticker else 0.0
        record = {
            "intent_id": intent.intent_id,
            "strategy_id": strategy_id,
            "symbol": intent.symbol,
            "timeframe": horizon,
            "side": "BUY" if intent.direction > 0 else "SELL",
            "order_type": order.order_type.value if order else "LIMIT",
            "requested_quantity": intent.target_size,
            "filled_quantity": fill.quantity if fill else 0.0,
            "fill_price": fill.price if fill else None,
            "limit_price": intent.limit_price,
            "bid_at_decision": bid_px,
            "ask_at_decision": ask_px,
            "spread": spread,
            "signal_timestamp_ms": intent.created_at_ms,
            "order_timestamp_ms": order.created_at_ms if order else None,
            "fill_timestamp_ms": fill.timestamp_ms if fill else None,
            "fee": fill.fee if fill else 0.0,
            "slippage": getattr(fill, "slippage", 0.0) if fill else 0.0,
            "latency_ms": round(latency_ms, 3),
            "realized_pnl": getattr(fill, "realized_pnl", 0.0) if fill else 0.0,
            "status": order.status.value if order else "REJECTED",
            "reason": rejection_reason or (decision.rule_code if decision and not decision.approved else ("FILLED" if fill else "UNFILLED")),
        }
        self.trade_audit_trail.append(record)

    def poll_funding_rates(self, symbols: List[str]) -> List[FundingRateEvent]:
        """Fetch authentic live funding rates from Binance public endpoint and dispatch to carry strategies."""
        import urllib.request
        target_set = set(symbols)
        events: List[FundingRateEvent] = []
        try:
            url = "https://fapi.binance.com/fapi/v1/premiumIndex"
            req = urllib.request.Request(url, headers={"User-Agent": "CryptoPlatform/1.0"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode())
            for item in data:
                sym = item.get("symbol")
                if sym in target_set:
                    ts = int(item.get("time", time.time() * 1000))
                    funding_rate = float(item.get("lastFundingRate", 0.0) or 0.0)
                    mark_px = float(item.get("markPrice", 0.0) or 0.0)
                    index_px = float(item.get("indexPrice", mark_px) or mark_px)
                    next_funding_time = int(item.get("nextFundingTime", 0) or 0)
                    ev = FundingRateEvent(
                        venue="binance",
                        symbol=sym,
                        timestamp_ms=ts,
                        funding_rate=funding_rate,
                        mark_price=mark_px,
                        index_price=index_px,
                        next_funding_time_ms=next_funding_time,
                    )
                    events.append(ev)
                    self.on_funding_rate(ev)
            logger.info(f"Dispatched {len(events)} live funding rate events to carry strategies.")
        except Exception as e:
            logger.warning(f"Failed to poll public funding rates: {e}")
        return events

    async def run_forward_session(
        self,
        duration_seconds: float = 10.0,
        symbols: Optional[List[str]] = None,
        ws_client: Optional[Any] = None,
        summary_out_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Runs an asynchronous controlled forward paper trading session."""
        target_symbols = symbols or ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
        start_ts = time.time()
        logger.info(f"Starting controlled paper session for {duration_seconds}s on {target_symbols}...")

        def _save_snapshot(elapsed_sec: float) -> None:
            if not summary_out_path:
                return
            snap = self.get_summary()
            avg_lat = sum(self.latencies_ms) / len(self.latencies_ms) if self.latencies_ms else 0.0
            snap.update({
                "elapsed_seconds": round(elapsed_sec, 2),
                "target_duration_seconds": duration_seconds,
                "market_events_processed": self.market_events_count,
                "signals_generated": self.signals_generated_count,
                "signals_rejected": self.signals_rejected_count,
                "orders_simulated": self.orders_simulated_count,
                "average_latency_ms": round(avg_lat, 3),
                "reconnect_count": ws_client.reconnect_count if ws_client else 0,
                "dropped_messages": ws_client.dropped_messages if ws_client else 0,
            })
            os.makedirs(os.path.dirname(summary_out_path), exist_ok=True)
            with open(summary_out_path, "w") as f:
                json.dump(snap, f, indent=2)

        try:
            if ws_client is not None:
                self.connect_market_data(ws_client)
                for s in target_symbols:
                    await ws_client.add_symbol_stream(s)
                ws_client.start()

            # Poll live funding rates for carry strategies immediately on startup
            last_funding_poll = 0.0
            if any(hasattr(s, "on_funding_rate") for s in self.strategies.values()):
                self.poll_funding_rates(target_symbols)
                last_funding_poll = time.time()

            elapsed = 0.0
            step = 5.0
            while elapsed < duration_seconds:
                sleep_chunk = min(step, duration_seconds - elapsed)
                await asyncio.sleep(sleep_chunk)
                elapsed += sleep_chunk

                # Periodic funding poll every 60 seconds
                if time.time() - last_funding_poll >= 60.0:
                    if any(hasattr(s, "on_funding_rate") for s in self.strategies.values()):
                        self.poll_funding_rates(target_symbols)
                        last_funding_poll = time.time()

                _save_snapshot(elapsed)
        finally:
            if ws_client is not None:
                self.disconnect_market_data(ws_client)
                await ws_client.stop()

        elapsed = time.time() - start_ts
        avg_latency = sum(self.latencies_ms) / len(self.latencies_ms) if self.latencies_ms else 0.0

        summary = self.get_summary()
        summary.update({
            "elapsed_seconds": round(elapsed, 2),
            "market_events_processed": self.market_events_count,
            "signals_generated": self.signals_generated_count,
            "signals_rejected": self.signals_rejected_count,
            "orders_simulated": self.orders_simulated_count,
            "average_latency_ms": round(avg_latency, 3),
            "reconnect_count": ws_client.reconnect_count if ws_client else 0,
            "dropped_messages": ws_client.dropped_messages if ws_client else 0,
        })
        if summary_out_path:
            os.makedirs(os.path.dirname(summary_out_path), exist_ok=True)
            with open(summary_out_path, "w") as f:
                json.dump(summary, f, indent=2)

        logger.info(f"Forward paper session complete: {summary}")
        return summary

    def get_summary(self) -> Dict[str, Any]:
        positions = self.oms.get_positions(self.account_id)
        return {
            "account_id": self.account_id,
            "mode": OperatingMode.PAPER.value,
            "initial_equity": self.initial_equity,
            "current_equity": round(self.current_equity, 2),
            "peak_equity": round(self.peak_equity, 2),
            "total_pnl": round(self.current_equity - self.initial_equity, 2),
            "return_pct": round((self.current_equity / self.initial_equity - 1.0) * 100, 2),
            "total_fills": len(self.fills_history),
            "funnel": self.funnel.to_dict(),
            "open_positions": {
                sym: dict(direction=p.direction, size=p.size, entry=p.entry_price, pnl=round(p.unrealized_pnl, 2))
                for sym, p in positions.items()
            },
            "trade_records": self.trade_audit_trail[-50:],
            "total_trade_records": len(self.trade_audit_trail),
        }
