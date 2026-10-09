"""STRATA Digital Trading Platform — Autonomous 24/7/365 Production Supervisor.

Master production orchestrator coordinating:
1. Real-time Market Data & Ingestion (Binance WebSocket Client)
2. 7-Timeframe Continuous Candle Engine (1M down to 3M)
3. Frozen Market Model & Fractal State Engine (Sets 1 to 5)
4. Phase R Decision Engine & Hard Target Geometry (>= 4.0R floor)
5. Multi-Tier Capital Safety Gate & Hardware/Software Barrier
6. Multi-Broker Account Manager & Execution Gateway (Paper, Demo, Micro-Live, Live)
7. Automated Circuit Breakers & Portfolio Risk Governors
8. Continuous Position Lifecycle & Autonomous Trailing Stops
9. Immutable SHA-256 Decision Ledger & Lineage Bridge
10. Continuous 3-Way State & Broker Reconciliation
11. Real-Time Statistical Drift Monitor & Research Candidate Pipeline
12. Multi-Channel Alert & Notification Router
13. State Checkpointing & 24/7 Restart Recovery
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import time
import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from accounts.account_manager import (
    AccountConfig,
    AccountEnvironment,
    AccountManager,
    AccountSnapshot,
)
from execution.adapters.execution_adapters import (
    ExecutionGateway,
    ExecutionMode,
    OrderIntent,
    SimulatedFill,
)
from execution.decision.decision_ledger import LiveDecisionLedger
from execution.decision.phase_r_decision_engine import (
    DecisionType,
    PhaseRDecisionEngine,
    PhaseRDecisionRecord,
)
from execution.position.position_lifecycle import (
    Position,
    PositionLifecycleMonitor,
    PositionState,
)
from execution.reconciliation_engine import (
    AutonomousReconciliationEngine,
    ReconciliationReport,
)
from execution.precision_engine import (
    DuplicateOrderIntentError,
    IdempotencyExecutionGuard,
    generate_deterministic_order_id,
    round_to_step_size,
    round_to_tick_size,
)
from execution.risk.circuit_breakers import CompositeCircuitBreakerManager
from execution.safety.safety_gate import EnvironmentGateMode, SAFETY_GATE
from execution.state.state_persistence import StatePersistenceManager
from instrument.universe_manager import UNIVERSE_MANAGER
from market_data.realtime.binance_ws_client import (
    BinanceRealtimeWSClient,
    DataHealthStatus,
)
from market_data.realtime.candle_engine import (
    CandleRecord,
    ContinuousCandleEngine,
)
from notifications.alert_router import ALERTS, AlertCategory, AlertSeverity
from research.contracts.frozen_contract_guard import FROZEN_GUARD
from validation.realtime_drift_monitor import (
    DriftState,
    DriftStatusReport,
    RealtimeDriftMonitor,
)
from validation.research_candidate_pipeline import RESEARCH_PIPELINE

logger = logging.getLogger(__name__)

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
LEDGER_FILE = WORKSPACE_ROOT / "research" / "results" / "PHASE_R_DECISION_LEDGER.jsonl"


class AutonomousTradingSupervisor:
    """Master production supervisor managing 24/7 trading operations."""

    def __init__(
        self,
        symbols: Optional[List[str]] = None,
        simulated_equity: float = 100_000.0,
        min_confidence: float = 0.50,
        ledger_path: Optional[Path] = None,
    ):
        self.symbols = [s.upper() for s in (symbols or ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"])]
        self.simulated_equity = simulated_equity
        self.peak_equity = simulated_equity
        self.min_confidence = min_confidence
        self.ledger_path = ledger_path or LEDGER_FILE

        # 1. Assert capital safety and frozen research contract
        FROZEN_GUARD.assert_capital_safety(
            real_capital_authorized=SAFETY_GATE.real_capital_authorized_usd,
            live_trading_enabled=SAFETY_GATE.is_live_execution,
        )

        # 2. Account & Execution Infrastructure
        self.account_manager = AccountManager()
        self.execution_gateway = ExecutionGateway()
        self.circuit_breakers = CompositeCircuitBreakerManager()
        self.state_persistence = StatePersistenceManager()
        self.idempotency_guard = IdempotencyExecutionGuard()

        # 3. Market Data & 7-Timeframe Candle Engine
        self.ws_client = BinanceRealtimeWSClient(symbols=self.symbols, base_timeframe="15m")
        self.candle_engine = ContinuousCandleEngine(symbols=self.symbols)

        # 4. Decision Engines (per symbol)
        self.decision_engines: Dict[str, PhaseRDecisionEngine] = {
            s: PhaseRDecisionEngine(
                symbol=s,
                initial_equity_usd=self.simulated_equity,
                min_confidence=self.min_confidence,
            )
            for s in self.symbols
        }

        # 5. Position & Ledger Management
        self.position_monitor = PositionLifecycleMonitor()
        self.decision_ledger = LiveDecisionLedger(self.ledger_path)

        # 6. Audit, Drift & Research Pipelines
        self.reconciliation_engine = AutonomousReconciliationEngine()
        self.drift_monitor = RealtimeDriftMonitor()
        self.research_pipeline = RESEARCH_PIPELINE

        # Operational telemetry state
        self.decisions_history: List[PhaseRDecisionRecord] = []
        self.orders_history: List[OrderIntent] = []
        self.fills_history: List[SimulatedFill] = []
        self.active_positions: Dict[str, Position] = {}
        self.closed_positions: List[Dict[str, Any]] = []

        self._running = False
        self.system_status = "INITIALIZING"
        self._last_checkpoint_ts = 0

        self._setup_bindings()
        self._attempt_restart_recovery()

    def _setup_bindings(self) -> None:
        """Wire event callbacks from market data to candle engine and decision pipeline."""
        self.ws_client.add_candle_listener(self._on_raw_candle_received)
        self.candle_engine.add_closed_candle_listener(self._on_closed_candle_formed)

    def _attempt_restart_recovery(self) -> None:
        """Attempt to restore state from disk checkpoint on boot."""
        checkpoint = self.state_persistence.load_checkpoint()
        if checkpoint:
            self.simulated_equity = checkpoint.get("equity_usd", self.simulated_equity)
            self.peak_equity = checkpoint.get("peak_equity_usd", self.peak_equity)
            recovered_keys = checkpoint.get("idempotency_keys", [])
            if recovered_keys:
                self.idempotency_guard.restore_keys(recovered_keys)
            logger.info(
                f"Restored equity from checkpoint: ${self.simulated_equity:.2f}, "
                f"{len(recovered_keys)} idempotency keys restored"
            )

    def seed_historical_state(self) -> Dict[str, int]:
        """Seeds continuous candle engine from existing disk cache."""
        counts = {}
        for sym in self.symbols:
            loaded = self.candle_engine.seed_from_disk_cache(sym)
            counts[sym] = loaded
        logger.info(f"Seeded historical cache across symbols: {counts}")
        self.system_status = "SEEDED_READY"
        return counts

    def _on_raw_candle_received(self, raw_kline: Dict[str, Any]) -> None:
        """Processes closed candles arriving from WebSocket stream."""
        rec = CandleRecord(
            symbol=raw_kline["symbol"],
            timeframe=raw_kline["timeframe"],
            open_ts=raw_kline["open_ts"],
            close_ts=raw_kline["close_ts"],
            open=raw_kline["open"],
            high=raw_kline["high"],
            low=raw_kline["low"],
            close=raw_kline["close"],
            volume=raw_kline["volume"],
            is_closed=True,
            source=raw_kline.get("source", "WS"),
            ingestion_ts=raw_kline.get("ingestion_ts", int(time.time() * 1000)),
        )
        self.candle_engine.ingest_closed_candle(rec)

    def _on_closed_candle_formed(self, candle: CandleRecord) -> None:
        """Triggered causally whenever a candle officially closes."""
        sym = candle.symbol.upper()
        if sym not in self.decision_engines:
            return

        engine = self.decision_engines[sym]
        all_tf_data = self.candle_engine.get_all_timeframe_data(sym)
        data_health = self.ws_client.get_feed_health(sym)

        # 1. Evaluate Circuit Breakers before processing orders
        breaker_ctx = {
            "current_equity_usd": self.simulated_equity,
            "peak_equity_usd": self.peak_equity,
            "consecutive_losses": sum(1 for p in self.closed_positions[-3:] if p.get("realized_r", 0) < 0),
            "last_tick_timestamp_ms": candle.ingestion_ts,
            "reconciliation_discrepancy_count": len(self.reconciliation_engine.last_report.discrepancies)
            if self.reconciliation_engine.last_report else 0,
        }
        all_safe, failed_breakers, breaker_states = self.circuit_breakers.evaluate_all(breaker_ctx)

        # 2. Evaluate across the 3 execution sets (SET_2, SET_3, SET_4) and 2 phases
        for set_name in ["SET_2", "SET_3", "SET_4"]:
            for hyp in ["CONTINUATION", "PULLBACK"]:
                decision_card = engine.evaluate_opportunity(
                    set_name=set_name,
                    hypothesis_type=hyp,
                    all_timeframe_data=all_tf_data,
                    data_health=data_health,
                    eval_timestamp_ms=candle.close_ts,
                )

                # If circuit breakers tripped, demote TRADE to NO_TRADE
                if not all_safe and decision_card.decision == DecisionType.TRADE:
                    decision_card.decision = DecisionType.NO_TRADE
                    decision_card.reason_codes.extend(failed_breakers)

                self.decisions_history.append(decision_card)
                self._persist_decision_to_ledger(decision_card)

                if decision_card.decision == DecisionType.TRADE:
                    self._execute_order(decision_card)

        # 3. Check existing positions for stop/target/trailing hits
        self._manage_open_positions(sym, candle.close, candle.close_ts)

        # 4. Periodically save state checkpoint (every 60s)
        now_ts = int(time.time())
        if now_ts - self._last_checkpoint_ts >= 60:
            self._save_state_checkpoint()
            self._last_checkpoint_ts = now_ts

    def _execute_order(self, d: PhaseRDecisionRecord) -> None:
        """Executes an order through ExecutionGateway and initializes position."""
        # 1. Assert idempotency to prevent duplicate entries
        try:
            self.idempotency_guard.assert_idempotent(d.asset, d.decision_id, d.timestamp_ms)
        except DuplicateOrderIntentError:
            logger.warning(f"Idempotency: Suppressed duplicate order execution for {d.asset} {d.decision_id}")
            return

        # 2. Risk sizing: 1% risk of simulated equity (or micro risk if micro-live)
        active_acc = self.account_manager.get_active_account()
        risk_pct = 0.001 if active_acc.environment == AccountEnvironment.MICRO_LIVE else 0.01
        risk_usd = self.simulated_equity * risk_pct
        risk_dist = abs(d.entry_price - d.initial_stop_price)
        raw_size = risk_usd / max(risk_dist, 1e-4)

        # 3. Precision rounding
        spec = UNIVERSE_MANAGER.get_instrument(d.asset)
        step_size = spec.lot_size if spec else 0.001
        size_units = round_to_step_size(raw_size, step_size)
        if size_units <= 0:
            logger.warning(f"Precision: Sizing resulted in 0 units for {d.asset}. Order suppressed.")
            return

        intent_id = generate_deterministic_order_id(d.asset, d.decision_id, d.timestamp_ms)
        intent = OrderIntent(
            intent_id=intent_id,
            decision_id=d.decision_id,
            symbol=d.asset,
            direction=d.direction,
            entry_price=d.entry_price,
            initial_stop_price=d.initial_stop_price,
            target_price=d.target_price,
            planned_r=d.planned_r,
            risk_usd=risk_usd,
            size_units=size_units,
            created_at_ts=d.timestamp_ms,
            meta={"set": d.timeframe_set, "phase": d.phase, "confidence": d.confidence_score, "account": active_acc.account_id},
        )
        self.orders_history.append(intent)

        # Route through Execution Gateway
        exec_mode = ExecutionMode(SAFETY_GATE.current_mode.value)
        fill = self.execution_gateway.submit(intent, mode=exec_mode)
        self.fills_history.append(fill)

        # Create position in monitor
        pos_id = f"POS_{uuid.uuid4().hex[:8].upper()}"
        pos = Position(
            position_id=pos_id,
            symbol=d.asset,
            direction=d.direction,
            size=size_units,
            entry_price=fill.fill_price,
            initial_stop=d.initial_stop_price,
            current_stop=d.initial_stop_price,
            target_price=d.target_price,
            initial_risk_dollars=risk_usd,
            opened_at_timestamp=fill.fill_timestamp_ms,
            state=PositionState.OPEN,
        )
        self.active_positions[pos_id] = pos

        ALERTS.emit(
            severity=AlertSeverity.INFO,
            category=AlertCategory.EXECUTION,
            title=f"Position Opened: {pos.symbol} ({d.timeframe_set})",
            message=f"Filled {pos.size} units @ {pos.entry_price:.2f}. Planned Target: {pos.target_price:.2f} ({d.planned_r:.1f}R).",
            metadata={"position_id": pos_id, "mode": exec_mode.value},
        )

    def _manage_open_positions(self, symbol: str, current_price: float, ts_now: int) -> None:
        """Audits open positions against trailing stop or >= 4R target completion."""
        closed_ids = []
        for pid, pos in self.active_positions.items():
            if pos.symbol != symbol:
                continue

            closed = False
            exit_px = current_price
            exit_reason = ""
            realized_r = 0.0

            risk_dist = abs(pos.entry_price - pos.initial_stop)

            # Long checks
            if pos.direction == 1:
                # Breakeven trailing stop at +2.0R
                if current_price >= pos.entry_price + (2.0 * risk_dist):
                    if pos.current_stop < pos.entry_price:
                        pos.current_stop = pos.entry_price  # Move to breakeven

                if current_price <= pos.current_stop:
                    closed = True
                    exit_px = pos.current_stop
                    exit_reason = "STOP_LOSS" if pos.current_stop < pos.entry_price else "BREAKEVEN"
                    realized_r = (exit_px - pos.entry_price) / max(risk_dist, 1e-4)
                elif current_price >= pos.target_price:
                    closed = True
                    exit_px = pos.target_price
                    exit_reason = "TARGET_4R"
                    realized_r = round(abs(pos.target_price - pos.entry_price) / max(risk_dist, 1e-4), 4)

            # Short checks
            elif pos.direction == -1:
                # Breakeven trailing stop at +2.0R
                if current_price <= pos.entry_price - (2.0 * risk_dist):
                    if pos.current_stop > pos.entry_price:
                        pos.current_stop = pos.entry_price  # Move to breakeven

                if current_price >= pos.current_stop:
                    closed = True
                    exit_px = pos.current_stop
                    exit_reason = "STOP_LOSS" if pos.current_stop > pos.entry_price else "BREAKEVEN"
                    realized_r = (pos.entry_price - exit_px) / max(risk_dist, 1e-4)
                elif current_price <= pos.target_price:
                    closed = True
                    exit_px = pos.target_price
                    exit_reason = "TARGET_4R"
                    realized_r = round(abs(pos.entry_price - pos.target_price) / max(risk_dist, 1e-4), 4)

            if closed:
                pos.state = PositionState.CLOSED
                pos.closed_at_timestamp = ts_now
                pnl_dollars = realized_r * pos.initial_risk_dollars
                self.simulated_equity += pnl_dollars
                self.peak_equity = max(self.peak_equity, self.simulated_equity)

                closed_rec = {
                    "position_id": pid,
                    "symbol": pos.symbol,
                    "direction": pos.direction,
                    "entry_price": pos.entry_price,
                    "exit_price": exit_px,
                    "exit_reason": exit_reason,
                    "realized_r": round(realized_r, 4),
                    "pnl_usd": round(pnl_dollars, 2),
                    "closed_at": ts_now,
                }
                self.closed_positions.append(closed_rec)
                self.drift_monitor.record_completed_trade(realized_r, 0.60)

                # Check drift degradation and emit research proposal if detected
                drift_rep = self.drift_monitor.evaluate_drift()
                self.research_pipeline.inspect_and_emit(drift_rep)

                closed_ids.append(pid)

                ALERTS.emit(
                    severity=AlertSeverity.INFO,
                    category=AlertCategory.TRADE,
                    title=f"Position Closed: {pos.symbol} [{exit_reason}]",
                    message=f"Realized {realized_r:+.2f}R (${pnl_dollars:+.2f}). Equity: ${self.simulated_equity:.2f}.",
                    metadata=closed_rec,
                )

        for cid in closed_ids:
            del self.active_positions[cid]

    def _save_state_checkpoint(self) -> None:
        """Saves atomic platform checkpoint to disk."""
        active_pos_list = [asdict(p) for p in self.active_positions.values()]
        metrics = {
            "total_trades": len(self.closed_positions),
            "win_rate": sum(1 for p in self.closed_positions if p.get("realized_r", 0) > 0) / max(len(self.closed_positions), 1),
            "net_r": sum(p.get("realized_r", 0) for p in self.closed_positions),
        }
        candle_sync = {s: int(time.time() * 1000) for s in self.symbols}
        _, _, breaker_states = self.circuit_breakers.evaluate_all({"current_equity_usd": self.simulated_equity})

        self.state_persistence.save_checkpoint(
            equity_usd=self.simulated_equity,
            peak_equity_usd=self.peak_equity,
            active_positions=active_pos_list,
            closed_trades_count=len(self.closed_positions),
            metrics=metrics,
            candle_sync_timestamps=candle_sync,
            circuit_breakers_state=breaker_states,
            idempotency_keys=self.idempotency_guard.get_keys(),
        )

    def _persist_decision_to_ledger(self, d: PhaseRDecisionRecord) -> None:
        """Appends the decision card to disk."""
        try:
            self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.ledger_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(d.to_dict()) + "\n")
        except Exception as ex:
            logger.error(f"Failed to append to decision ledger: {ex}")

    def run_reconciliation(self) -> ReconciliationReport:
        """Performs full end-to-end reconciliation audit."""
        ledger_lines = 0
        if self.ledger_path.exists():
            with open(self.ledger_path, "r", encoding="utf-8") as f:
                ledger_lines = len(f.readlines())

        return self.reconciliation_engine.reconcile(
            candidate_count=len(self.decisions_history),
            decisions=[d.to_dict() for d in self.decisions_history],
            orders=[asdict(o) for o in self.orders_history],
            fills=[asdict(f) for f in self.fills_history],
            active_positions=[asdict(p) for p in self.active_positions.values()],
            closed_positions=self.closed_positions,
            ledger_count=ledger_lines,
        )

    def get_system_telemetry(self) -> Dict[str, Any]:
        """Provides full operational telemetry for the web dashboard."""
        recon = self.reconciliation_engine.last_report
        drift = self.drift_monitor.evaluate_drift()
        safety_status = SAFETY_GATE.get_status_report()

        return {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "product_name": "STRATA Digital Trading Platform",
            "execution_mode": SAFETY_GATE.current_mode.value,
            "real_capital_authorized": SAFETY_GATE.real_capital_authorized_usd,
            "live_trading_status": "ENABLED" if SAFETY_GATE.is_live_execution else "DISABLED_FAIL_CLOSED",
            "system_health": "HEALTHY" if (not recon or recon.is_reconciled) else "DEGRADED",
            "simulated_equity_usd": self.simulated_equity,
            "peak_equity_usd": self.peak_equity,
            "portfolio_heat_pct": sum(1.0 for _ in self.active_positions),
            "current_drawdown_pct": round(max(0.0, (self.peak_equity - self.simulated_equity) / max(self.peak_equity, 1.0) * 100.0), 2),
            "active_positions_count": len(self.active_positions),
            "total_decisions_logged": len(self.decisions_history),
            "total_trades_executed": len(self.fills_history),
            "total_positions_closed": len(self.closed_positions),
            "safety_barrier": safety_status,
            "feed_metrics": self.ws_client.get_metrics_snapshot(),
            "reconciliation": recon.to_dict() if recon else {"status": "INITIALIZED"},
            "drift_status": drift.to_dict(),
            "accounts": self.account_manager.list_accounts(),
            "universe": UNIVERSE_MANAGER.get_all_specs(),
        }

    async def start(self) -> None:
        """Starts the autonomous 24/7 background organism."""
        self._running = True
        self.system_status = f"RUNNING_{SAFETY_GATE.current_mode.value}_24_7"
        await self.ws_client.start()
        logger.info(f"Autonomous Trading Supervisor started in {SAFETY_GATE.current_mode.value} mode.")

    async def stop(self) -> None:
        """Gracefully shuts down."""
        self._running = False
        self.system_status = "SHUTDOWN"
        self._save_state_checkpoint()
        await self.ws_client.stop()
        logger.info("Autonomous Trading Supervisor gracefully stopped.")
