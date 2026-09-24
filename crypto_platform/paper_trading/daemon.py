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
    Position,
    RiskDecision,
    RiskState,
)
from crypto_platform.core.events import CandleEvent, TickerEvent
from crypto_platform.core.interfaces import IStrategy
from crypto_platform.order_management.oms import OrderManagementSystem
from crypto_platform.risk_engine.firewall import RiskFirewall
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
    ):
        self.tenant_id = tenant_id
        self.account_id = account_id
        self.initial_equity = initial_equity
        self.current_equity = initial_equity
        self.peak_equity = initial_equity

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

        # Telemetry & Observability
        self.market_events_count = 0
        self.signals_generated_count = 0
        self.signals_rejected_count = 0
        self.orders_simulated_count = 0
        self.risk_decisions: List[RiskDecision] = []
        self.latencies_ms: List[float] = []

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

    def register_strategy(self, strategy: IStrategy) -> None:
        self.strategies[strategy.strategy_id] = strategy

    def connect_market_data(self, ws_client: Any) -> None:
        """Wire this daemon to a PublicWebSocketClient instance."""
        ws_client.subscribe("ticker", self.on_ticker)
        ws_client.subscribe("candle", self.on_candle)

    def disconnect_market_data(self, ws_client: Any) -> None:
        """Unwire this daemon from a PublicWebSocketClient instance."""
        if hasattr(ws_client, "unsubscribe"):
            ws_client.unsubscribe("ticker", self.on_ticker)
            ws_client.unsubscribe("candle", self.on_candle)

    def on_ticker(self, ticker: TickerEvent) -> List[Fill]:
        """Update market price, check resting limit orders, and update unrealized PnL."""
        t_start = time.perf_counter()
        self.market_events_count += 1
        self.latest_tickers[ticker.symbol] = ticker
        executed_fills: List[Fill] = []

        # Check working orders for this symbol
        open_orders = self.oms.get_open_orders(self.account_id)
        for order in open_orders:
            if order.symbol == ticker.symbol:
                fill = self.simulator.process_order(order, ticker)
                if fill is not None:
                    self.oms.register_fill(fill, self.account_id)
                    self.fills_history.append(fill)
                    executed_fills.append(fill)

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
        t_start = time.perf_counter()
        self.market_events_count += 1
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

        for strat in self.strategies.values():
            intents = strat.on_candle(candle)
            for intent in intents:
                self.signals_generated_count += 1

                # 1. Evaluate intent through independent Fail-Closed Risk Firewall
                decision = self.risk_firewall.evaluate_order_intent(
                    intent=intent,
                    current_positions=positions,
                    balances=self.balances,
                    risk_state=risk_state,
                    latest_ticker=ticker,
                )
                self.risk_decisions.append(decision)

                if decision.approved:
                    # 2. OMS creates and routes order
                    order = self.oms.create_order_from_intent(intent, decision, venue=candle.venue)
                    generated_orders.append(order)
                    self.orders_simulated_count += 1

                    if self.ledger:
                        self.ledger.save_order(order, self.account_id)

                    # 3. Microstructure simulator attempts fill
                    fill = self.simulator.process_order(order, ticker)
                    if fill is not None:
                        self.oms.register_fill(fill, self.account_id)
                        self.fills_history.append(fill)
                        strat.on_fill(fill)

                        if self.ledger:
                            self.ledger.save_order(order, self.account_id)
                            self.ledger.record_fill(fill, self.account_id)
                            pos = self.oms.get_positions(self.account_id).get(fill.symbol)
                            if pos:
                                self.ledger.save_position(pos, self.account_id)
                else:
                    self.signals_rejected_count += 1
                    if self.ledger:
                        self.ledger.log_audit_event(
                            account_id=self.account_id,
                            event_type="RISK_REJECTION",
                            severity="WARNING",
                            message=f"Order intent {intent.intent_id} rejected: {decision.reason}",
                            details={"rule_code": decision.rule_code, "symbol": intent.symbol},
                        )

        latency_ms = (time.perf_counter() - t_start) * 1000.0
        self.latencies_ms.append(latency_ms)
        return generated_orders

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

            elapsed = 0.0
            step = 5.0
            while elapsed < duration_seconds:
                sleep_chunk = min(step, duration_seconds - elapsed)
                await asyncio.sleep(sleep_chunk)
                elapsed += sleep_chunk
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
            "open_positions": {
                sym: dict(direction=p.direction, size=p.size, entry=p.entry_price, pnl=round(p.unrealized_pnl, 2))
                for sym, p in positions.items()
            },
        }
