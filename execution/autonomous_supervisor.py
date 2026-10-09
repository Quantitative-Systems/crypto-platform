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
from execution.state.state_persistence import (
    PersistenceError,
    PersistenceMode,
    StatePersistenceManager,
)
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
        state_persistence: Optional[StatePersistenceManager] = None,
        db_path: Optional[Union[str, Path]] = None,
        state_dir: Optional[Path] = None,
    ):
        self.symbols = [s.upper() for s in (symbols or ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"])]
        self.simulated_equity = simulated_equity
        self.peak_equity = simulated_equity
        self.min_confidence = min_confidence
        if ledger_path is not None:
            self.ledger_path = Path(ledger_path)
        elif os.environ.get("PYTEST_CURRENT_TEST"):
            import tempfile
            self.ledger_path = Path(tempfile.gettempdir()) / f"pytest_ledger_{os.getpid()}.jsonl"
            if self.ledger_path.exists():
                try:
                    self.ledger_path.unlink()
                except OSError:
                    pass
        else:
            self.ledger_path = LEDGER_FILE

        # 1. Assert capital safety and frozen research contract
        FROZEN_GUARD.assert_capital_safety(
            real_capital_authorized=SAFETY_GATE.real_capital_authorized_usd,
            live_trading_enabled=SAFETY_GATE.is_live_execution,
        )

        # 2. Account & Execution Infrastructure
        self.account_manager = AccountManager()
        self.execution_gateway = ExecutionGateway()
        self.circuit_breakers = CompositeCircuitBreakerManager()
        if state_persistence is not None:
            self.state_persistence = state_persistence
        elif db_path is not None or state_dir is not None:
            self.state_persistence = StatePersistenceManager(state_dir=state_dir, db_path=db_path)
        else:
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

        # Candle processing semantics
        self.last_received_candle: Dict[str, Dict[str, int]] = {s: {} for s in self.symbols}
        self.last_closed_candle: Dict[str, Dict[str, int]] = {s: {} for s in self.symbols}
        self.last_processed_candle: Dict[str, Dict[str, int]] = {s: {} for s in self.symbols}
        self.last_evaluated_decision_ts: Dict[str, int] = {s: 0 for s in self.symbols}

        self._running = False
        self._persistence_barrier_tripped = False
        self.system_status = "INITIALIZING"
        self._last_checkpoint_ts = 0

        self._setup_bindings()
        self._attempt_restart_recovery()

    @property
    def open_positions(self) -> Dict[str, Position]:
        """Alias for active_positions providing uniform property access."""
        return self.active_positions

    @open_positions.setter
    def open_positions(self, val: Dict[str, Position]) -> None:
        self.active_positions = val

    @property
    def equity_usd(self) -> float:
        """Alias for simulated_equity providing uniform property access."""
        return self.simulated_equity

    @equity_usd.setter
    def equity_usd(self, val: float) -> None:
        self.simulated_equity = val

    @property
    def peak_equity_usd(self) -> float:
        """Alias for peak_equity providing uniform property access."""
        return self.peak_equity

    @peak_equity_usd.setter
    def peak_equity_usd(self, val: float) -> None:
        self.peak_equity = val

    def is_persistence_blocked(self) -> bool:
        """Determines if the persistence safety barrier is active."""
        if self.state_persistence.mode == PersistenceMode.REQUIRED_DURABLE:
            if getattr(self, "_persistence_barrier_tripped", False) or self.system_status in ("PERSISTENCE_DEGRADED", "RECOVERY_FAILED_HALTED"):
                return True
            health = self.state_persistence.get_persistence_health()
            if health.get("status") != "HEALTHY" or not health.get("database_connected", False):
                return True
        return False

    def _trip_persistence_gate(self, reason: str) -> None:
        """Enforces hard persistence barrier when durable persistence fails."""
        self._persistence_barrier_tripped = True
        self.system_status = "PERSISTENCE_DEGRADED"
        logger.critical(f"PERSISTENCE SAFETY GATE TRIPPED: {reason}. All trading decisions and order execution halted.")
        ALERTS.emit(
            severity=AlertSeverity.CRITICAL,
            category=AlertCategory.SYSTEM,
            title="Persistence Safety Barrier Tripped",
            message=f"Mandatory persistence failed: {reason}. Trading execution blocked fail-closed.",
            metadata={"reason": reason, "mode": self.state_persistence.mode.value},
        )

    def recover_persistence_and_reconcile(self) -> bool:
        """Attempts recovery from degraded persistence state, verifies durable DB write, and reconciles ledger."""
        logger.info("Attempting recovery and reconciliation from degraded persistence...")
        try:
            save_ok = self._save_state_checkpoint()
            if not save_ok or not self.state_persistence.get_persistence_health().get("database_connected", False):
                logger.error("Persistence recovery failed: Database unresponsive or checkpoint save failed.")
                return False
        except Exception as ex:
            logger.error(f"Persistence recovery failed during checkpoint save: {ex}")
            return False

        recon_report = self.run_reconciliation()
        if not recon_report.is_reconciled and len(recon_report.discrepancies) > 0:
            logger.critical(f"Persistence recovery reconciliation failed: {recon_report.discrepancies}")
            self.system_status = "RECOVERY_FAILED_HALTED"
            return False

        self._persistence_barrier_tripped = False
        self.system_status = f"RUNNING_{SAFETY_GATE.current_mode.value}_24_7" if self._running else "RECOVERED_HEALTHY"
        logger.info("Persistence recovery and reconciliation successful. Normal execution restored.")
        ALERTS.emit(
            severity=AlertSeverity.INFO,
            category=AlertCategory.SYSTEM,
            title="Persistence Barrier Cleared",
            message="Persistence recovery and ledger reconciliation succeeded. Resumed normal operations.",
            metadata={"status": self.system_status},
        )
        return True

    def _setup_bindings(self) -> None:
        """Wire event callbacks from market data to candle engine and decision pipeline."""
        self.ws_client.add_candle_listener(self._on_raw_candle_received)
        self.candle_engine.add_closed_candle_listener(self._on_closed_candle_formed)

    def _abort_recovery(self, reason: str) -> None:
        """Fails closed upon unrecoverable checkpoint state."""
        self.system_status = "RECOVERY_FAILED_HALTED"
        self._persistence_barrier_tripped = True
        self._running = False
        logger.critical(f"FATAL: Restart recovery aborted: {reason}. System halted fail-closed.")
        ALERTS.emit(
            severity=AlertSeverity.CRITICAL,
            category=AlertCategory.SYSTEM,
            title="Restart Recovery Aborted",
            message=f"System failed-closed on startup: {reason}",
            metadata={"reason": reason},
        )

    def _attempt_restart_recovery(self) -> None:
        """Attempt to restore state from persistent checkpoint on boot with validation and reconciliation."""
        try:
            checkpoint = self.state_persistence.load_checkpoint()
        except Exception as e:
            self._abort_recovery(f"Fatal error loading checkpoint: {e}")
            return

        if not checkpoint:
            logger.info("No prior checkpoint found. Initializing pristine supervisor state.")
            self.system_status = "INITIALIZED_PRISTINE"
            return

        # 1. Validate Schema and Timestamp
        schema_ver = checkpoint.get("schema_version", 1)
        if schema_ver < 1 or schema_ver > 4:
            self._abort_recovery(f"Incompatible schema version: {schema_ver}")
            return

        # 2. Equity & Peak Equity Validation
        eq = checkpoint.get("equity_usd")
        peak_eq = checkpoint.get("peak_equity_usd")
        if eq is None or eq <= 0:
            self._abort_recovery(f"Invalid equity in checkpoint: {eq}")
            return
        if peak_eq is None or peak_eq <= 0:
            self._abort_recovery(f"Invalid peak equity in checkpoint: {peak_eq}")
            return
        self.simulated_equity = float(eq)
        self.peak_equity = max(float(peak_eq), float(eq))

        # 3. Check Stale Checkpoint Against Authoritative Decision Ledger
        if self.ledger_path.exists():
            max_ledger_ts = 0
            ledger_trade_count = 0
            ledger_records: List[PhaseRDecisionRecord] = []
            try:
                with open(self.ledger_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            rec_dict = json.loads(line)
                            ts = rec_dict.get("timestamp_ms", 0)
                            if ts > max_ledger_ts:
                                max_ledger_ts = ts
                            if rec_dict.get("decision") == "TRADE":
                                ledger_trade_count += 1
                            try:
                                ledger_records.append(PhaseRDecisionRecord.from_dict(rec_dict))
                            except Exception:
                                pass
            except Exception as ex:
                logger.warning(f"Error inspecting decision ledger: {ex}")

            ckpt_ts = checkpoint.get("timestamp_ms", 0)
            if max_ledger_ts > 0 and ckpt_ts < max_ledger_ts - 5000:
                self._abort_recovery(
                    f"Stale checkpoint rejected: checkpoint timestamp ({ckpt_ts}) is older than "
                    f"authoritative decision ledger ({max_ledger_ts}). Never resume from stale state."
                )
                return

            saved_orders = checkpoint.get("orders_history", [])
            if ledger_trade_count > len(saved_orders):
                self._abort_recovery(
                    f"Stale checkpoint rejected: ledger contains {ledger_trade_count} TRADE decisions "
                    f"but checkpoint only contains {len(saved_orders)} orders."
                )
                return

            self.decisions_history = ledger_records

        # 4. Restore and Validate Active Positions
        raw_positions = checkpoint.get("active_positions") or checkpoint.get("open_positions") or []
        for p_dict in raw_positions:
            try:
                pid = p_dict.get("position_id")
                sym = p_dict.get("symbol", "").upper()
                entry_px = float(p_dict.get("entry_price", 0.0))
                size = float(p_dict.get("size", 0.0))
                direction = int(p_dict.get("direction", 0))
                init_stop = float(p_dict.get("initial_stop", p_dict.get("initial_stop_price", 0.0)))
                tgt_px = float(p_dict.get("target_price", 0.0))

                if not pid or not sym or sym not in self.symbols:
                    self._abort_recovery(f"Invalid position in checkpoint: id={pid}, sym={sym}")
                    return
                if entry_px <= 0 or size <= 0 or direction not in (1, -1):
                    self._abort_recovery(f"Invalid position parameters for {pid}: entry={entry_px}, size={size}, dir={direction}")
                    return
                if init_stop <= 0 or tgt_px <= 0:
                    self._abort_recovery(f"Invalid stop/target parameters for {pid}: stop={init_stop}, target={tgt_px}")
                    return

                # Geometry check: stop < entry < target for long; stop > entry > target for short
                if direction == 1 and not (init_stop < entry_px < tgt_px):
                    self._abort_recovery(f"Inverted geometry for long position {pid}: stop={init_stop}, entry={entry_px}, target={tgt_px}")
                    return
                elif direction == -1 and not (init_stop > entry_px > tgt_px):
                    self._abort_recovery(f"Inverted geometry for short position {pid}: stop={init_stop}, entry={entry_px}, target={tgt_px}")
                    return

                pos = Position.from_dict(p_dict)
                self.active_positions[pos.position_id] = pos
            except Exception as pos_err:
                self._abort_recovery(f"Failed to deserialize position from checkpoint: {pos_err}")
                return

        # 5. Restore Closed Positions & Trade History
        if "closed_positions" in checkpoint:
            self.closed_positions = list(checkpoint["closed_positions"])

        # 6. Restore Orders and Fills History
        if "orders_history" in checkpoint:
            self.orders_history = [
                OrderIntent(**o) if isinstance(o, dict) else o
                for o in checkpoint["orders_history"]
            ]
        if "fills_history" in checkpoint:
            self.fills_history = [
                SimulatedFill(**f) if isinstance(f, dict) else f
                for f in checkpoint["fills_history"]
            ]

        # 7. Restore Circuit Breaker Tripped States
        breaker_states = checkpoint.get("circuit_breakers_state", {})
        if breaker_states:
            self.circuit_breakers.restore_states(breaker_states)

        # 8. Restore Idempotency Keys (Prevent Duplicate Orders across restarts)
        recovered_keys = checkpoint.get("idempotency_keys", [])
        if recovered_keys:
            self.idempotency_guard.restore_keys(recovered_keys)

        # 9. Restore Candle Processing Timestamps
        if "last_received_candle" in checkpoint:
            self.last_received_candle = checkpoint["last_received_candle"]
        if "last_closed_candle" in checkpoint:
            self.last_closed_candle = checkpoint["last_closed_candle"]
        if "last_processed_candle" in checkpoint:
            self.last_processed_candle = checkpoint["last_processed_candle"]
        elif "candle_sync_timestamps" in checkpoint:
            c_sync = checkpoint["candle_sync_timestamps"]
            for k, ts in c_sync.items():
                if ":" in k:
                    s, tf = k.split(":", 1)
                    self.last_processed_candle.setdefault(s, {})[tf] = int(ts)
                else:
                    self.last_processed_candle.setdefault(k, {})["15m"] = int(ts)

        if "last_evaluated_decision_ts" in checkpoint:
            self.last_evaluated_decision_ts = checkpoint["last_evaluated_decision_ts"]

        # 10. Reconcile Restored State with Authoritative Ledger
        recon_report = self.run_reconciliation()
        if not recon_report.is_reconciled and len(recon_report.discrepancies) > 0:
            logger.critical(
                f"RESTART RECOVERY RECONCILIATION FAILED: {len(recon_report.discrepancies)} discrepancies detected: "
                f"{recon_report.discrepancies}"
            )
            self._abort_recovery(f"Reconciliation discrepancy after recovery: {recon_report.discrepancies}")
            return

        self.system_status = "RECOVERED_HEALTHY"
        logger.info(
            f"RESTART RECOVERY COMPLETE: Equity: ${self.simulated_equity:.2f}, "
            f"Peak: ${self.peak_equity:.2f}, "
            f"Active Positions: {len(self.active_positions)}, "
            f"Idempotency Keys Restored: {len(recovered_keys)}, "
            f"Reconciliation: RECONCILED"
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
        sym = raw_kline["symbol"].upper()
        tf = raw_kline.get("timeframe", "15m")
        open_ts = int(raw_kline.get("open_ts", 0))
        close_ts = int(raw_kline.get("close_ts", open_ts))

        # Track actual candle timestamps
        if sym not in self.last_received_candle:
            self.last_received_candle[sym] = {}
        self.last_received_candle[sym][tf] = open_ts

        if raw_kline.get("is_closed", True):
            if sym not in self.last_closed_candle:
                self.last_closed_candle[sym] = {}
            self.last_closed_candle[sym][tf] = close_ts

        rec = CandleRecord(
            symbol=sym,
            timeframe=tf,
            open_ts=open_ts,
            close_ts=close_ts,
            open=float(raw_kline["open"]),
            high=float(raw_kline["high"]),
            low=float(raw_kline["low"]),
            close=float(raw_kline["close"]),
            volume=float(raw_kline["volume"]),
            is_closed=True,
            source=raw_kline.get("source", "WS"),
            ingestion_ts=int(raw_kline.get("ingestion_ts", time.time() * 1000)),
        )
        self.candle_engine.ingest_closed_candle(rec)

    def _on_closed_candle_formed(self, candle: CandleRecord) -> None:
        """Triggered causally whenever a candle officially closes."""
        sym = candle.symbol.upper()
        tf = candle.timeframe
        if sym not in self.decision_engines:
            return

        # 1. Reject duplicate or out-of-order closed candles causally
        last_proc = self.last_processed_candle.get(sym, {}).get(tf, 0)
        if candle.close_ts <= last_proc:
            logger.debug(
                f"Duplicate or out-of-order closed candle ignored: {sym} {tf} "
                f"close_ts={candle.close_ts} <= last_processed={last_proc}"
            )
            return

        # 2. Hard persistence barrier check at main decision-processing boundary
        if self.is_persistence_blocked():
            logger.warning(
                f"Persistence barrier active ({self.system_status}). "
                f"Bypassing decision processing for {candle.symbol}."
            )
            return

        engine = self.decision_engines[sym]
        all_tf_data = self.candle_engine.get_all_timeframe_data(sym)
        data_health = self.ws_client.get_feed_health(sym)

        # 3. Evaluate Circuit Breakers before processing orders
        breaker_ctx = {
            "current_equity_usd": self.simulated_equity,
            "peak_equity_usd": self.peak_equity,
            "consecutive_losses": sum(1 for p in self.closed_positions[-3:] if p.get("realized_r", 0) < 0),
            "last_tick_timestamp_ms": candle.ingestion_ts,
            "reconciliation_discrepancy_count": len(self.reconciliation_engine.last_report.discrepancies)
            if self.reconciliation_engine.last_report else 0,
        }
        all_safe, failed_breakers, breaker_states = self.circuit_breakers.evaluate_all(breaker_ctx)

        # 4. Evaluate across the 3 execution sets (SET_2, SET_3, SET_4) and 2 phases
        for set_name in ["SET_2", "SET_3", "SET_4"]:
            for hyp in ["CONTINUATION", "PULLBACK"]:
                decision_card = engine.evaluate_opportunity(
                    set_name=set_name,
                    hypothesis_type=hyp,
                    all_timeframe_data=all_tf_data,
                    data_health=data_health,
                    eval_timestamp_ms=candle.close_ts,
                )

                # Record decision evaluation timestamp
                self.last_evaluated_decision_ts[sym] = max(
                    self.last_evaluated_decision_ts.get(sym, 0),
                    candle.close_ts,
                )

                # If circuit breakers tripped or persistence blocked, demote TRADE to NO_TRADE
                if self.is_persistence_blocked() and decision_card.decision == DecisionType.TRADE:
                    decision_card.decision = DecisionType.NO_TRADE
                    decision_card.reason_codes.append("PERSISTENCE_SAFETY_BARRIER")
                elif not all_safe and decision_card.decision == DecisionType.TRADE:
                    decision_card.decision = DecisionType.NO_TRADE
                    decision_card.reason_codes.extend(failed_breakers)

                self.decisions_history.append(decision_card)
                self._persist_decision_to_ledger(decision_card)

                if decision_card.decision == DecisionType.TRADE:
                    self._execute_order(decision_card)

        # 5. Check existing positions for stop/target/trailing hits
        self._manage_open_positions(sym, candle.close, candle.close_ts)

        # 6. Mark candle as successfully processed causally
        if sym not in self.last_processed_candle:
            self.last_processed_candle[sym] = {}
        self.last_processed_candle[sym][tf] = candle.close_ts

        # 7. Periodically save state checkpoint (every 60s)
        now_ts = int(time.time())
        if now_ts - self._last_checkpoint_ts >= 60:
            self._save_state_checkpoint()
            self._last_checkpoint_ts = now_ts

    def _execute_order(self, d: PhaseRDecisionRecord) -> None:
        """Executes an order through ExecutionGateway and initializes position."""
        # 0. Persistence safety gate check immediately before order intent creation
        if self.is_persistence_blocked():
            logger.critical(
                f"SAFETY GATE ENFORCED: Blocked order intent execution for {d.asset} {d.decision_id} "
                f"because persistence is degraded."
            )
            ALERTS.emit(
                severity=AlertSeverity.CRITICAL,
                category=AlertCategory.EXECUTION,
                title="Order Submission Blocked by Persistence Gate",
                message=f"Blocked order intent for {d.asset} {d.decision_id} due to degraded durable persistence.",
                metadata={"asset": d.asset, "decision_id": d.decision_id, "status": self.system_status},
            )
            return

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

        # Persist checkpoint immediately upon order fill
        self._save_state_checkpoint()

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

        if closed_ids:
            self._save_state_checkpoint()

    def _save_state_checkpoint(self) -> bool:
        """Saves atomic platform checkpoint to disk and database."""
        active_pos_list = [p.to_dict() for p in self.active_positions.values()]
        metrics = {
            "total_trades": len(self.closed_positions),
            "win_rate": sum(1 for p in self.closed_positions if p.get("realized_r", 0) > 0) / max(len(self.closed_positions), 1),
            "net_r": sum(p.get("realized_r", 0) for p in self.closed_positions),
        }
        candle_sync = {
            f"{s}:{tf}": ts
            for s, tfs in self.last_processed_candle.items()
            for tf, ts in tfs.items()
        }
        _, _, breaker_states = self.circuit_breakers.evaluate_all({"current_equity_usd": self.simulated_equity})
        orders_payload = [asdict(o) if hasattr(o, "__dataclass_fields__") else dict(o) for o in self.orders_history]
        fills_payload = [asdict(f) if hasattr(f, "__dataclass_fields__") else dict(f) for f in self.fills_history]

        try:
            success = self.state_persistence.save_checkpoint(
                equity_usd=self.simulated_equity,
                peak_equity_usd=self.peak_equity,
                active_positions=active_pos_list,
                closed_trades_count=len(self.closed_positions),
                metrics=metrics,
                candle_sync_timestamps=candle_sync,
                circuit_breakers_state=breaker_states,
                idempotency_keys=self.idempotency_guard.get_keys(),
                closed_positions=self.closed_positions,
                orders_history=orders_payload,
                fills_history=fills_payload,
                last_received_candle=self.last_received_candle,
                last_closed_candle=self.last_closed_candle,
                last_processed_candle=self.last_processed_candle,
                last_evaluated_decision_ts=self.last_evaluated_decision_ts,
            )
            if not success and self.state_persistence.mode == PersistenceMode.REQUIRED_DURABLE:
                self._trip_persistence_gate("Checkpoint save returned false in REQUIRED_DURABLE mode")
                return False
            return success
        except Exception as e:
            logger.critical(f"Exception saving checkpoint: {e}")
            if self.state_persistence.mode == PersistenceMode.REQUIRED_DURABLE:
                self._trip_persistence_gate(str(e))
            return False

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
            orders=[asdict(o) if hasattr(o, "__dataclass_fields__") else o for o in self.orders_history],
            fills=[asdict(f) if hasattr(f, "__dataclass_fields__") else f for f in self.fills_history],
            active_positions=[p.to_dict() for p in self.active_positions.values()],
            closed_positions=self.closed_positions,
            ledger_count=ledger_lines,
        )

    def get_system_telemetry(self) -> Dict[str, Any]:
        """Provides full operational telemetry for the web dashboard."""
        recon = self.reconciliation_engine.last_report
        drift = self.drift_monitor.evaluate_drift()
        safety_status = SAFETY_GATE.get_status_report()
        pers_health = self.state_persistence.get_persistence_health()

        return {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "product_name": "Crypto Platform",
            "execution_mode": SAFETY_GATE.current_mode.value,
            "real_capital_authorized": SAFETY_GATE.real_capital_authorized_usd,
            "live_trading_status": "ENABLED" if SAFETY_GATE.is_live_execution else "DISABLED_FAIL_CLOSED",
            "system_health": "HEALTHY" if (not recon or recon.is_reconciled) and pers_health.get("status") == "HEALTHY" else "DEGRADED",
            "simulated_equity_usd": self.simulated_equity,
            "peak_equity_usd": self.peak_equity,
            "portfolio_heat_pct": sum(1.0 for _ in self.active_positions),
            "current_drawdown_pct": round(max(0.0, (self.peak_equity - self.simulated_equity) / max(self.peak_equity, 1.0) * 100.0), 2),
            "active_positions_count": len(self.active_positions),
            "total_decisions_logged": len(self.decisions_history),
            "total_trades_executed": len(self.fills_history),
            "total_positions_closed": len(self.closed_positions),
            "safety_barrier": safety_status,
            "persistence_health": pers_health,
            "feed_metrics": self.ws_client.get_metrics_snapshot(),
            "reconciliation": recon.to_dict() if recon else {"status": "INITIALIZED"},
            "drift_status": drift.to_dict(),
            "accounts": self.account_manager.list_accounts(),
            "universe": UNIVERSE_MANAGER.get_all_specs(),
        }

    async def start(self) -> None:
        """Starts the autonomous 24/7 background organism."""
        if self.system_status in ("RECOVERY_FAILED_HALTED", "PERSISTENCE_DEGRADED") or self.is_persistence_blocked():
            logger.critical(f"Cannot start autonomous supervisor: system is in {self.system_status} state.")
            raise RuntimeError(f"Autonomous supervisor startup aborted: system is in {self.system_status} state.")

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

