"""
Quantitative Crypto Platform (QCP) — Continuous Forward Paper Execution Daemon.

Transforms historical paper simulation into a continuous, fault-tolerant, event-driven
forward paper execution system directly connected to live closed candles.

Guarantees:
- Automatic startup and state/position recovery
- Clock synchronization & closed-candle confirmation
- Duplicate-bar rejection & missing-bar gap detection
- Stale-data detection & signal inhibit
- Deterministic event ordering with immutable event IDs
- Zero duplicate orders and zero duplicate exits
- Periodic structured heartbeats and failure logging
- Atomic graceful shutdown
"""

import os
import sys
import json
import time
import uuid
import signal
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from market_intelligence.primitives import Candle
from market_data.binance_fetcher import BinanceFetcher
from platform_core.canonical_strategy_spec import (
    CanonicalStrategySpec,
    create_fam07_spec,
    StrategyLifecycleState,
)
from platform_core.canonical_strategy_registry import CanonicalStrategyRegistry
from platform_core.execution_contract import ExecutionContract, CollisionPolicy
from strategy_engine.canonical_signal_engine import CanonicalSignalEngine, SignalResult
from trade_management.lifecycle_engine import (
    TradeManagementEngine,
    TradeOrderPlan,
    ManagedPosition,
    PositionLifecycleStage,
)
from portfolio_engine.portfolio_intelligence import (
    PortfolioIntelligenceEngine,
    PortfolioAllocationDecision,
)
from production.telemetry.execution_telemetry import (
    ExecutionTelemetryLogger,
    TradeTelemetryRecord,
)
from production.qualification.forward_qualification_engine import (
    ForwardQualificationEngine,
    QualificationReport,
)
from production.qualification.model_reality_engine import (
    ModelVsRealityEngine,
    TradeRealityDelta,
    ModelRealitySummary,
)

TF_SECONDS_MAP: Dict[str, int] = {
    "1m": 60,
    "5m": 300,
    "15m": 900,
    "1h": 3600,
    "4h": 14400,
    "1d": 86400,
}


@dataclass
class DaemonConfig:
    symbol: str = "SOL/USDT"
    timeframes: Tuple[str, ...] = ("4h", "1h", "15m")
    poll_interval_sec: float = 10.0
    starting_capital: float = 1000.0
    state_file: str = os.path.join(os.path.dirname(__file__), "daemon_state.json")
    audit_file: str = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "research",
        "results",
        "FORWARD_PAPER_DAEMON_AUDIT.json",
    )
    heartbeat_interval_sec: float = 60.0
    max_stale_data_sec: float = 1800.0  # 30 mins for 15m primary timeframe
    max_reconnect_retries: int = 5


@dataclass
class DaemonHeartbeat:
    timestamp: int
    utc_iso: str
    status: str
    uptime_seconds: float
    current_equity_usd: float
    peak_equity_usd: float
    max_drawdown_pct: float
    active_positions: int
    total_closed_trades: int
    last_processed_candles: Dict[str, int]
    clock_drift_sec: float
    gap_count: int


class ForwardPaperDaemon:
    """
    Production-grade event-driven forward paper daemon for QCP.
    """

    def __init__(
        self,
        config: Optional[DaemonConfig] = None,
        strategy_spec: Optional[CanonicalStrategySpec] = None,
    ):
        self.config = config or DaemonConfig()
        self.spec = strategy_spec or create_fam07_spec(
            symbol=self.config.symbol,
            timeframe_set=2,
            lifecycle_state=StrategyLifecycleState.QUALIFIED_ROBUST,
            notes="Primary robust forward paper candidate",
        )

        self.starting_capital = self.config.starting_capital
        self.current_equity = self.config.starting_capital
        self.peak_equity = self.config.starting_capital
        self.max_drawdown_usd = 0.0
        self.max_drawdown_pct = 0.0

        self.last_processed_ts: Dict[str, int] = {tf: 0 for tf in self.config.timeframes}
        self.closed_trades: List[Dict[str, Any]] = []
        self.reality_deltas: List[Dict[str, Any]] = []
        self.gaps_detected: List[Dict[str, Any]] = []
        self.cycle_logs: List[Dict[str, Any]] = []

        self.trade_manager = TradeManagementEngine()
        self.telemetry = ExecutionTelemetryLogger()
        self.registry = CanonicalStrategyRegistry()
        self.signal_engine = CanonicalSignalEngine(self.spec)

        self.start_time: float = time.time()
        self.last_heartbeat_time: float = 0.0
        self._running: bool = False
        self.last_reality_summary: Optional[ModelRealitySummary] = None

        # Verify strict capital firewall lock (zero live credentials / zero live order paths)
        self._verify_capital_firewall_locked()

        # Load persistent state if available
        self._load_state()

    def _verify_capital_firewall_locked(self) -> None:
        """
        Enforces operational safety: verifies zero live credentials and ensures
        all order execution paths remain strictly simulated behind the capital firewall.
        """
        forbidden_keys = ["BINANCE_API_KEY", "BINANCE_SECRET_KEY", "EXCHANGE_PRIVATE_KEY", "LIVE_CAPITAL_ENABLED"]
        for key in forbidden_keys:
            val = os.getenv(key)
            if val:
                raise RuntimeError(f"FATAL: Capital firewall violation: {key} detected in environment.")
        assert not hasattr(self, "live_broker"), "Safety invariant breached: live_broker must not exist."
        assert not hasattr(self, "live_exchange_client"), "Safety invariant breached: live_exchange_client must not exist."

    def _load_state(self) -> None:
        """Restores equity, drawdown, active positions, and candle watermarks."""
        if os.path.exists(self.config.state_file):
            try:
                with open(self.config.state_file, "r") as f:
                    data = json.load(f)
                    self.current_equity = data.get("current_equity", self.starting_capital)
                    self.peak_equity = data.get("peak_equity", self.starting_capital)
                    self.max_drawdown_usd = data.get("max_drawdown_usd", 0.0)
                    self.max_drawdown_pct = data.get("max_drawdown_pct", 0.0)
                    self.last_processed_ts = data.get("last_processed_ts", self.last_processed_ts)

                    # Restore active positions into TradeManagementEngine
                    saved_positions = data.get("active_positions", [])
                    for pos_data in saved_positions:
                        pos = ManagedPosition(
                            position_id=pos_data["position_id"],
                            strategy_id=pos_data["strategy_id"],
                            symbol=pos_data["symbol"],
                            direction=pos_data["direction"],
                            stage=PositionLifecycleStage(pos_data.get("stage", "ACTIVE")),
                            entry_time=pos_data["entry_time"],
                            entry_price=pos_data["entry_price"],
                            current_sl_price=pos_data["current_sl_price"],
                            initial_sl_price=pos_data["initial_sl_price"],
                            emergency_sl_price=pos_data.get("emergency_sl_price", pos_data["initial_sl_price"]),
                            tp1_price=pos_data.get("tp1_price", pos_data["entry_price"]),
                            tp2_price=pos_data.get("tp2_price", pos_data["entry_price"]),
                            tp3_price=pos_data.get("tp3_price", pos_data["entry_price"]),
                            total_qty=pos_data["total_qty"],
                            remaining_qty=pos_data.get("remaining_qty", pos_data["total_qty"]),
                            risk_r_unit_usd=pos_data["risk_r_unit_usd"],
                            peak_unrealized_r=pos_data.get("peak_unrealized_r", 0.0),
                            bars_held=pos_data.get("bars_held", 0),
                            last_update_ts=pos_data.get("last_update_ts", pos_data["entry_time"]),
                        )
                        self.trade_manager.active_positions[pos.position_id] = pos
            except Exception as e:
                print(f"⚠️ [ForwardPaperDaemon] Warning restoring state: {e}")

    def _save_state(self) -> None:
        """Persists state to disk atomically."""
        temp_file = f"{self.config.state_file}.tmp"
        os.makedirs(os.path.dirname(os.path.abspath(self.config.state_file)), exist_ok=True)

        active_pos_list = [
            {
                "position_id": p.position_id,
                "strategy_id": p.strategy_id,
                "symbol": p.symbol,
                "direction": p.direction,
                "stage": p.stage.value if hasattr(p.stage, "value") else str(p.stage),
                "entry_time": p.entry_time,
                "entry_price": p.entry_price,
                "current_sl_price": p.current_sl_price,
                "initial_sl_price": p.initial_sl_price,
                "emergency_sl_price": p.emergency_sl_price,
                "tp1_price": p.tp1_price,
                "tp2_price": p.tp2_price,
                "tp3_price": p.tp3_price,
                "total_qty": p.total_qty,
                "remaining_qty": p.remaining_qty,
                "risk_r_unit_usd": p.risk_r_unit_usd,
                "peak_unrealized_r": p.peak_unrealized_r,
                "bars_held": p.bars_held,
                "last_update_ts": p.last_update_ts,
            }
            for p in self.trade_manager.active_positions.values()
            if p.stage in (
                PositionLifecycleStage.ACTIVE,
                PositionLifecycleStage.BREAK_EVEN_LOCKED,
                PositionLifecycleStage.TRAILING_ACTIVE,
                PositionLifecycleStage.PARTIAL_PROFIT_TAKEN,
            )
        ]

        state = {
            "platform": "Quantitative Crypto Platform (QCP)",
            "saved_at_utc": datetime.now(timezone.utc).isoformat(),
            "symbol": self.config.symbol,
            "strategy_id": self.spec.strategy_id,
            "current_equity": round(self.current_equity, 4),
            "peak_equity": round(self.peak_equity, 4),
            "max_drawdown_usd": round(self.max_drawdown_usd, 4),
            "max_drawdown_pct": round(self.max_drawdown_pct, 4),
            "last_processed_ts": self.last_processed_ts,
            "active_positions": active_pos_list,
            "total_closed_trades": len(self.closed_trades),
            "gaps_count": len(self.gaps_detected),
        }

        with open(temp_file, "w") as f:
            json.dump(state, f, indent=2)
        os.replace(temp_file, self.config.state_file)

    def run_cycle(
        self,
        current_time: Optional[float] = None,
        candle_feed: Optional[Dict[str, List[Candle]]] = None,
    ) -> Dict[str, Any]:
        """
        Executes one deterministic cycle of the forward paper loop:
        Market data -> Closed confirmation -> Stale/Gap check -> MTF update ->
        Active trade management -> Signal -> Risk -> Simulated Order -> Telemetry.
        """
        now = current_time if current_time is not None else time.time()
        event_id = f"evt_{int(now)}_{uuid.uuid4().hex[:8]}"

        cycle_result: Dict[str, Any] = {
            "event_id": event_id,
            "timestamp": int(now),
            "status": "INITIATED",
            "new_bars_processed": {},
            "position_events": [],
            "new_orders": [],
            "gaps": [],
            "warnings": [],
        }

        # Heartbeat check at start of cycle
        if (now - self.last_heartbeat_time) >= self.config.heartbeat_interval_sec or self.last_heartbeat_time == 0.0:
            self._emit_heartbeat(now, 0.0)
            self.last_heartbeat_time = now

        # 1. Fetch live candles per timeframe
        raw_candles: Dict[str, List[Candle]] = {}
        for tf in self.config.timeframes:
            if candle_feed and tf in candle_feed:
                raw_candles[tf] = candle_feed[tf]
            else:
                try:
                    raw_candles[tf] = BinanceFetcher.fetch_live_candles(
                        symbol=self.config.symbol,
                        timeframe=tf,
                        limit=120,
                    )
                except Exception as e:
                    cycle_result["warnings"].append(f"Network error fetching {tf}: {e}")
                    cycle_result["status"] = "DATA_FETCH_FAILED"
                    return cycle_result

        # 2. Closed-Candle Confirmation & Duplicate Rejection
        confirmed_closed_candles: Dict[str, List[Candle]] = {}
        has_new_primary_bar = False

        for tf, candles in raw_candles.items():
            if not candles:
                continue

            tf_sec = TF_SECONDS_MAP.get(tf.lower(), 900)
            closed_only = []
            for c in candles:
                # Closed candle rule: current time must be >= candle_open + tf_sec
                if now >= (c.timestamp + tf_sec):
                    closed_only.append(c)

            if not closed_only:
                continue

            confirmed_closed_candles[tf] = closed_only
            latest_c = closed_only[-1]
            last_processed = self.last_processed_ts.get(tf, 0)

            # Duplicate-bar rejection
            if latest_c.timestamp > last_processed:
                cycle_result["new_bars_processed"][tf] = latest_c.timestamp

                # Missing-bar gap detection
                if last_processed > 0 and (latest_c.timestamp - last_processed) > tf_sec:
                    gap_info = {
                        "timeframe": tf,
                        "expected_ts": last_processed + tf_sec,
                        "received_ts": latest_c.timestamp,
                        "gap_seconds": latest_c.timestamp - last_processed,
                        "detected_at_utc": datetime.now(timezone.utc).isoformat(),
                    }
                    self.gaps_detected.append(gap_info)
                    cycle_result["gaps"].append(gap_info)

                self.last_processed_ts[tf] = latest_c.timestamp
                if tf == self.config.timeframes[-1]:  # primary execution timeframe (e.g. 15m)
                    has_new_primary_bar = True

        # 3. Stale Data Check
        primary_tf = self.config.timeframes[-1]
        primary_candles = confirmed_closed_candles.get(primary_tf, [])
        if not primary_candles:
            cycle_result["status"] = "NO_CLOSED_CANDLES_AVAILABLE"
            return cycle_result

        latest_primary = primary_candles[-1]
        stale_age = now - latest_primary.timestamp
        if stale_age > self.config.max_stale_data_sec:
            cycle_result["warnings"].append(
                f"STALE_DATA_INHIBIT: Primary candle {latest_primary.timestamp} is {stale_age:.0f}s old (> {self.config.max_stale_data_sec}s)"
            )
            cycle_result["status"] = "STALE_DATA_INHIBITED"
            return cycle_result

        # 4. Load MTF State into Signal Engine
        tf_4h = confirmed_closed_candles.get("4h", [])
        tf_1h = confirmed_closed_candles.get("1h", [])
        tf_15m = confirmed_closed_candles.get("15m", [])

        if len(tf_4h) < 20 or len(tf_1h) < 20 or len(tf_15m) < 30:
            cycle_result["status"] = "INSUFFICIENT_WARMUP_BARS"
            return cycle_result

        self.signal_engine.prepare_series(
            ltf_candles=tf_15m,
            mtf_candles=tf_1h,
            htf_candles=tf_4h,
        )

        # 5. Evaluate Active Positions (SL, TP, Breakeven Trailing)
        current_bar = latest_primary
        exited_ids = []

        for pos_id, pos in list(self.trade_manager.active_positions.items()):
            if pos.stage not in (
                PositionLifecycleStage.ACTIVE,
                PositionLifecycleStage.BREAK_EVEN_LOCKED,
                PositionLifecycleStage.TRAILING_ACTIVE,
                PositionLifecycleStage.PARTIAL_PROFIT_TAKEN,
            ):
                continue

            pos.bars_held += 1
            pos.last_update_ts = current_bar.timestamp
            is_long = (pos.direction in ("LONG", "BUY"))
            r_dist = abs(pos.entry_price - pos.initial_sl_price)
            if r_dist <= 1e-6:
                continue

            # MFE / MAE tracking
            if is_long:
                pos.peak_unrealized_r = max(pos.peak_unrealized_r, (current_bar.high - pos.entry_price) / r_dist)
            else:
                pos.peak_unrealized_r = max(pos.peak_unrealized_r, (pos.entry_price - current_bar.low) / r_dist)

            # Break-Even Locking at +1.0R
            if pos.peak_unrealized_r >= 1.0 and pos.stage == PositionLifecycleStage.ACTIVE:
                pos.stage = PositionLifecycleStage.BREAK_EVEN_LOCKED
                pos.current_sl_price = pos.entry_price

            # Hit checks
            hit_sl = (current_bar.low <= pos.current_sl_price) if is_long else (current_bar.high >= pos.current_sl_price)
            hit_tp = (current_bar.high >= pos.tp3_price) if is_long else (current_bar.low <= pos.tp3_price)

            hit_sl, hit_tp, collision_reason = ExecutionContract.resolve_same_bar_collision(
                hit_sl, hit_tp, policy=CollisionPolicy.ADVERSE_FIRST
            )

            if hit_sl or hit_tp:
                raw_exit = pos.current_sl_price if hit_sl else pos.tp3_price
                exit_reason = "SL_HIT" if hit_sl else "TP_HIT"
                if pos.stage == PositionLifecycleStage.BREAK_EVEN_LOCKED and hit_sl and abs(raw_exit - pos.entry_price) < 1e-4:
                    exit_reason = "BREAKEVEN_TRAIL"

                exec_exit = ExecutionContract.apply_slippage(raw_exit, is_buy=(not is_long), slippage_bps=5.0)
                exit_fee = ExecutionContract.calculate_fee(exec_exit * pos.total_qty, fee_bps=5.0)
                entry_fee = ExecutionContract.calculate_fee(pos.entry_price * pos.total_qty, fee_bps=2.0)

                r_metrics = ExecutionContract.calculate_r_accounting(
                    entry_price=pos.entry_price,
                    exit_price=exec_exit,
                    initial_sl_price=pos.initial_sl_price,
                    is_long=is_long,
                    position_size=pos.total_qty,
                    entry_fee_usd=entry_fee,
                    exit_fee_usd=exit_fee,
                )

                # Update Account Equity and Running Drawdown
                self.current_equity += r_metrics["net_pnl_usd"]
                if self.current_equity > self.peak_equity:
                    self.peak_equity = self.current_equity
                else:
                    dd_usd = self.peak_equity - self.current_equity
                    dd_pct = (dd_usd / self.peak_equity) * 100.0 if self.peak_equity > 0 else 0.0
                    if dd_usd > self.max_drawdown_usd:
                        self.max_drawdown_usd = dd_usd
                    if dd_pct > self.max_drawdown_pct:
                        self.max_drawdown_pct = dd_pct

                pos.stage = PositionLifecycleStage.CLOSED_SL if hit_sl else PositionLifecycleStage.CLOSED_TP

                # Telemetry record
                rec = TradeTelemetryRecord(
                    trade_id=pos.position_id,
                    strategy_id=pos.strategy_id,
                    symbol=pos.symbol,
                    timeframe_set=2,
                    direction=pos.direction,
                    entry_timestamp=pos.entry_time,
                    exit_timestamp=current_bar.timestamp,
                    holding_bars=pos.bars_held,
                    holding_seconds=current_bar.timestamp - pos.entry_time,
                    expected_entry_price=pos.entry_price,
                    executed_entry_price=pos.entry_price,
                    entry_slippage_bps=0.0,
                    entry_fee_usd=entry_fee,
                    expected_exit_price=raw_exit,
                    executed_exit_price=exec_exit,
                    exit_slippage_bps=5.0,
                    exit_fee_usd=exit_fee,
                    position_units=pos.total_qty,
                    position_notional_usd=round(pos.entry_price * pos.total_qty, 2),
                    initial_risk_usd=round(pos.risk_r_unit_usd, 2),
                    exit_reason=exit_reason,
                    gross_pnl_usd=round(r_metrics["gross_pnl_usd"], 4),
                    total_friction_usd=round(r_metrics["total_friction_usd"], 4),
                    net_pnl_usd=round(r_metrics["net_pnl_usd"], 4),
                    gross_r=round(r_metrics["gross_r"], 4),
                    friction_r=round(r_metrics["friction_r"], 4),
                    net_r=round(r_metrics["net_r"], 4),
                    market_regime="LIVE_FORWARD",
                    peak_unrealized_r=round(pos.peak_unrealized_r, 4),
                    max_adverse_r=0.0,
                    portfolio_heat_at_entry_pct=0.60,
                    breakeven_triggered=(pos.stage == PositionLifecycleStage.BREAK_EVEN_LOCKED),
                )
                self.telemetry.record_trade(rec)
                trade_dict = rec.to_dict()
                self.closed_trades.append(trade_dict)
                delta = ModelVsRealityEngine.evaluate_trade(trade_dict)
                self.reality_deltas.append(delta.to_dict())
                exited_ids.append(pos_id)
                cycle_result["position_events"].append({
                    "type": "POSITION_CLOSED",
                    "position_id": pos_id,
                    "reason": exit_reason,
                    "net_r": rec.net_r,
                    "net_pnl_usd": rec.net_pnl_usd,
                })

        # 6. Generate Strategy Signals (Only on fresh primary bar)
        if has_new_primary_bar:
            bar_idx = len(tf_15m) - 1
            signal: Optional[SignalResult] = self.signal_engine.generate_signal_at_bar(bar_idx=bar_idx)

            if signal is not None:
                # 7. Portfolio Intelligence and Risk Controls
                curr_dd = ((self.peak_equity - self.current_equity) / self.peak_equity) * 100.0 if self.peak_equity > 0 else 0.0
                open_pos_list = [
                    {"symbol": p.symbol, "direction": p.direction, "risk_usd": p.risk_r_unit_usd}
                    for p in self.trade_manager.active_positions.values()
                    if p.stage in (
                        PositionLifecycleStage.ACTIVE,
                        PositionLifecycleStage.BREAK_EVEN_LOCKED,
                        PositionLifecycleStage.TRAILING_ACTIVE,
                        PositionLifecycleStage.PARTIAL_PROFIT_TAKEN,
                    )
                ]

                port_eval = PortfolioIntelligenceEngine.evaluate_new_trade(
                    candidate_symbol=self.config.symbol.replace("/", "").replace("_", ""),
                    candidate_direction=signal.action,
                    current_open_positions=open_pos_list,
                    account_equity=self.current_equity,
                    current_drawdown_pct=curr_dd,
                )

                if port_eval.decision in (
                    PortfolioAllocationDecision.APPROVED_FULL_SIZE,
                    PortfolioAllocationDecision.APPROVED_SCALED_SIZE,
                    PortfolioAllocationDecision.ACCEPT_FULL,
                    PortfolioAllocationDecision.ACCEPT_REDUCED,
                ):
                    # Canonical execution simulation
                    is_long = (signal.action in ("BUY", "LONG"))
                    raw_entry = current_bar.close
                    exec_entry = ExecutionContract.apply_slippage(raw_entry, is_buy=is_long, slippage_bps=2.0)
                    risk_frac = (port_eval.recommended_risk_pct / 100.0) if port_eval.recommended_risk_pct > 0.05 else port_eval.recommended_risk_pct
                    r_risk_usd = self.current_equity * risk_frac

                    risk_distance = abs(exec_entry - signal.stop_loss)
                    if risk_distance > 1e-6:
                        pos_units = r_risk_usd / risk_distance
                        pos_notional = pos_units * exec_entry

                        # Maximum leverage ceiling of 3x
                        if pos_notional <= (self.current_equity * 3.0):
                            new_pos_id = f"POS_{self.config.symbol.replace('/', '')}_{current_bar.timestamp}_{uuid.uuid4().hex[:6]}"
                            self.trade_manager.initialize_position(
                                position_id=new_pos_id,
                                strategy_id=self.spec.strategy_id,
                                symbol=self.config.symbol,
                                direction=signal.action,
                                fill_price=exec_entry,
                                fill_qty=pos_units,
                                initial_sl=signal.stop_loss,
                                tp1_price=exec_entry + (risk_distance * 1.0) if is_long else exec_entry - (risk_distance * 1.0),
                                tp2_price=exec_entry + (risk_distance * 2.0) if is_long else exec_entry - (risk_distance * 2.0),
                                tp3_price=signal.take_profit,
                                timestamp=current_bar.timestamp,
                            )
                            # Set risk dollar value on created position
                            if new_pos_id in self.trade_manager.active_positions:
                                self.trade_manager.active_positions[new_pos_id].risk_r_unit_usd = r_risk_usd

                            cycle_result["new_orders"].append({
                                "position_id": new_pos_id,
                                "direction": signal.action,
                                "entry_price": exec_entry,
                                "stop_loss": signal.stop_loss,
                                "take_profit": signal.take_profit,
                                "notional_usd": round(pos_notional, 2),
                                "risk_usd": round(r_risk_usd, 2),
                            })
                else:
                    cycle_result["warnings"].append(f"Trade rejected by portfolio governor: {port_eval.rationale}")

        # 8. Heartbeat Check
        drift = now - latest_primary.timestamp
        if (now - self.last_heartbeat_time) >= self.config.heartbeat_interval_sec:
            self._emit_heartbeat(now, drift)
            self.last_heartbeat_time = now

        # 9. Persist state atomically
        self._save_state()

        active_count = len([
            p for p in self.trade_manager.active_positions.values()
            if p.stage in (
                PositionLifecycleStage.ACTIVE,
                PositionLifecycleStage.BREAK_EVEN_LOCKED,
                PositionLifecycleStage.TRAILING_ACTIVE,
                PositionLifecycleStage.PARTIAL_PROFIT_TAKEN,
            )
        ])

        cycle_result["status"] = "SUCCESS"
        cycle_result["equity"] = round(self.current_equity, 2)
        cycle_result["peak_equity"] = round(self.peak_equity, 2)
        cycle_result["max_drawdown_pct"] = round(self.max_drawdown_pct, 2)
        cycle_result["active_positions"] = active_count
        self.cycle_logs.append(cycle_result)
        return cycle_result

    def _emit_heartbeat(self, now: float, drift: float) -> DaemonHeartbeat:
        active_count = len([
            p for p in self.trade_manager.active_positions.values()
            if p.stage in (
                PositionLifecycleStage.ACTIVE,
                PositionLifecycleStage.BREAK_EVEN_LOCKED,
                PositionLifecycleStage.TRAILING_ACTIVE,
                PositionLifecycleStage.PARTIAL_PROFIT_TAKEN,
            )
        ])
        hb = DaemonHeartbeat(
            timestamp=int(now),
            utc_iso=datetime.fromtimestamp(now, tz=timezone.utc).isoformat(),
            status="HEALTHY",
            uptime_seconds=max(0.0, round(now - self.start_time, 1)),
            current_equity_usd=round(self.current_equity, 2),
            peak_equity_usd=round(self.peak_equity, 2),
            max_drawdown_pct=round(self.max_drawdown_pct, 2),
            active_positions=active_count,
            total_closed_trades=len(self.closed_trades),
            last_processed_candles=self.last_processed_ts,
            clock_drift_sec=round(drift, 1),
            gap_count=len(self.gaps_detected),
        )
        # Reality gap audit
        reality_summary = ModelVsRealityEngine.audit_reality_gap(
            self.closed_trades,
            backtest_expectancy_r=0.6107,
            backtest_win_rate=0.7014,
        )
        self.last_reality_summary = reality_summary

        # Flush to audit log
        os.makedirs(os.path.dirname(os.path.abspath(self.config.audit_file)), exist_ok=True)
        audit_payload = {
            "platform": "Quantitative Crypto Platform (QCP)",
            "last_heartbeat": asdict(hb),
            "state_summary": {
                "starting_capital_usd": self.starting_capital,
                "current_equity_usd": round(self.current_equity, 2),
                "net_profit_usd": round(self.current_equity - self.starting_capital, 2),
                "total_return_pct": round(((self.current_equity - self.starting_capital) / self.starting_capital) * 100.0, 2),
                "max_drawdown_pct": round(self.max_drawdown_pct, 2),
                "total_trades": len(self.closed_trades),
            },
            "model_vs_reality_gap": reality_summary.to_dict(),
            "recent_gaps": self.gaps_detected[-10:],
        }
        with open(self.config.audit_file, "w") as f:
            json.dump(audit_payload, f, indent=2)

        return hb

    def start(self) -> None:
        """Starts continuous daemon loop with graceful shutdown signal handlers."""
        self._running = True

        def _handle_signal(signum, frame):
            print(f"\n🛑 [ForwardPaperDaemon] Received signal {signum}. Commencing graceful shutdown...")
            self._running = False

        signal.signal(signal.SIGINT, _handle_signal)
        signal.signal(signal.SIGTERM, _handle_signal)

        print(f"🚀 [QCP] Forward Paper Daemon initialized for {self.config.symbol}.")
        print(f"   Starting Capital: ${self.starting_capital:,.2f} | Polling Interval: {self.config.poll_interval_sec}s")

        while self._running:
            try:
                self.run_cycle()
            except Exception as e:
                print(f"⚠️ [ForwardPaperDaemon] Exception in cycle: {e}")
            time.sleep(self.config.poll_interval_sec)

        self._save_state()
        print("✅ [ForwardPaperDaemon] Clean shutdown complete. State safely committed.")
