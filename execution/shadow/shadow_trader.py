"""24/7 Shadow Trader Orchestrator.

Operates the complete autonomous organism in SHADOW MODE:
- Observes real-time market data fabric and instrument health
- Runs the deterministic Candidate V1 decision engine
- Generates institutional TRADE / NO_TRADE outcomes
- Records every decision into the Live Decision Ledger
- When TRADE triggered: DOES NOT send real capital orders
- Submits order to ExecutionSimulator (latency, spread crossing, slippage)
- Initializes and tracks position via PositionLifecycleMonitor (MTF structural trail, HTF target >= 4R)
- Compares predicted entry vs actual fill and logs execution drag
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from execution.decision.decision_engine import AutonomousDecisionEngine, AutonomousDecisionOutcome
from execution.decision.decision_ledger import LiveDecisionLedger
from execution.position.position_lifecycle import Position, PositionLifecycleMonitor, PositionState
from execution.portfolio.factor_engine import PortfolioFactorEngine
from execution.simulator.execution_simulator import (
    ExecutionSimulator,
    OrderSide,
    OrderStatus,
    OrderType,
    SimulatedOrder,
)
from instrument.instrument_contract import CryptoBaseInstrument
from instrument.instrument_health import InstrumentHealth
from instrument.instrument_registry import InstrumentRegistry


@dataclass
class ShadowTradeAuditRecord:
    """Detailed reconciliation comparing research signal vs simulated execution."""
    trade_id: str
    symbol: str
    decision_id: str
    direction: str
    predicted_entry: float
    simulated_fill_price: float
    slippage_bps: float
    spread_cost_bps: float
    execution_latency_ms: float
    fee_usd: float
    initial_stop_price: float
    target_price: float
    destination_r: float
    realized_r: float = 0.0
    exit_state: str = "OPEN"
    exit_price: Optional[float] = None
    exit_reason: Optional[str] = None
    opened_at: float = field(default_factory=time.time)
    closed_at: Optional[float] = None


class ShadowTrader:
    """Institutional shadow trading orchestrator."""

    def __init__(
        self,
        registry: Optional[InstrumentRegistry] = None,
        factor_engine: Optional[PortfolioFactorEngine] = None,
        simulator: Optional[ExecutionSimulator] = None,
        ledger_path: Optional[Path] = None,
        account_equity_usd: float = 100_000.0,
    ):
        self.registry = registry or InstrumentRegistry()
        self.factor_engine = factor_engine or PortfolioFactorEngine()
        self.decision_engine = AutonomousDecisionEngine(self.factor_engine)
        self.simulator = simulator or ExecutionSimulator()
        self.position_monitor = PositionLifecycleMonitor()
        self.ledger = LiveDecisionLedger(ledger_path)
        self.account_equity_usd = account_equity_usd

        # State tracking
        self.active_positions: Dict[str, Position] = {}
        self.completed_trades: List[ShadowTradeAuditRecord] = []
        self.shadow_audits: Dict[str, ShadowTradeAuditRecord] = {}

    def get_active_portfolio_tuples(self) -> List[Tuple[CryptoBaseInstrument, int, float]]:
        """Return active positions formatted for factor engine evaluation."""
        tuples = []
        for pos_id, pos in self.active_positions.items():
            inst = self.registry.get_instrument(pos.symbol)
            if inst:
                tuples.append((inst, pos.direction, pos.allocated_risk_pct))
        return tuples

    def process_cycle(
        self,
        instrument: CryptoBaseInstrument,
        health: InstrumentHealth,
        current_market_price: float,
        market_model_state: Dict[str, Any],
        environment_state: Dict[str, Any],
        governor_state: Dict[str, Any],
        mtf_structural_stop: Optional[float] = None,
        current_time: Optional[float] = None,
    ) -> Optional[AutonomousDecisionOutcome]:
        """Execute one complete autonomous shadow evaluation cycle."""
        now = current_time if current_time is not None else time.time()

        # =================================================================
        # 1. UPDATE EXISTING OPEN POSITIONS FOR THIS INSTRUMENT
        # =================================================================
        for pos_id in list(self.active_positions.keys()):
            pos = self.active_positions[pos_id]
            if pos.symbol == instrument.symbol:
                new_state = self.position_monitor.update_position(
                    pos=pos,
                    current_price=current_market_price,
                    mtf_structural_stop=mtf_structural_stop,
                    health=health,
                    systemic_risk_active=governor_state.get("systemic_risk_active", False),
                    now=now,
                )

                if new_state in (PositionState.CLOSED_TARGET, PositionState.CLOSED_STOP, PositionState.CLOSED_EMERGENCY):
                    # Trade closed: finalize shadow audit record
                    audit = self.shadow_audits.get(pos_id)
                    if audit:
                        audit.realized_r = round(pos.realized_r, 2)
                        audit.exit_state = new_state.value
                        audit.exit_price = current_market_price
                        audit.exit_reason = pos.exit_reason
                        audit.closed_at = now
                        self.completed_trades.append(audit)
                    del self.active_positions[pos_id]

        # =================================================================
        # 2. RUN DECISION ENGINE
        # =================================================================
        active_tuples = self.get_active_portfolio_tuples()
        outcome = self.decision_engine.evaluate_cycle(
            instrument=instrument,
            health=health,
            market_model_state=market_model_state,
            environment_state=environment_state,
            governor_state=governor_state,
            active_positions=active_tuples,
            account_equity_usd=self.account_equity_usd,
            current_time=now,
        )

        # Record to immutable Live Decision Ledger
        self.ledger.record(outcome)

        # =================================================================
        # 3. IF TRADE SIGNAL GENERATED -> SIMULATE EXECUTION
        # =================================================================
        if outcome.decision == "TRADE" and outcome.position_size > 0:
            order_side = OrderSide.BUY if outcome.direction == "LONG" else OrderSide.SELL
            order = SimulatedOrder(
                order_id=f"ORD-{uuid.uuid4().hex[:8].upper()}",
                symbol=instrument.symbol,
                side=order_side,
                order_type=OrderType.MARKET,
                quantity=outcome.position_size,
                price=outcome.entry_price,
                submitted_at=now,
            )

            # Microstructure execution simulation
            exec_res = self.simulator.execute_market_order(
                order=order,
                reference_price=current_market_price,
                instrument=instrument,
                observed_spread_bps=float(market_model_state.get("spread_bps", 3.0)),
            )

            if exec_res.status in (OrderStatus.FILLED, OrderStatus.PARTIALLY_FILLED):
                pos_id = f"POS-{uuid.uuid4().hex[:8].upper()}"
                pos_direction = 1 if outcome.direction == "LONG" else -1

                # Spawn tracked position
                new_pos = Position(
                    position_id=pos_id,
                    symbol=instrument.symbol,
                    direction=pos_direction,
                    entry_price=exec_res.average_fill_price,
                    initial_stop_price=outcome.stop_price or current_market_price * 0.98,
                    current_stop_price=outcome.stop_price or current_market_price * 0.98,
                    target_price=outcome.target_price or current_market_price * 1.08,
                    size=exec_res.filled_qty,
                    allocated_risk_pct=outcome.risk_approved,
                    state=PositionState.ENTERED,
                    entry_time=now,
                )
                self.active_positions[pos_id] = new_pos

                # Log shadow audit reconciliation
                audit = ShadowTradeAuditRecord(
                    trade_id=pos_id,
                    symbol=instrument.symbol,
                    decision_id=outcome.decision_id,
                    direction=outcome.direction or "LONG",
                    predicted_entry=outcome.entry_price or current_market_price,
                    simulated_fill_price=exec_res.average_fill_price,
                    slippage_bps=exec_res.total_slippage_bps,
                    spread_cost_bps=exec_res.fills[0].spread_cost_bps if exec_res.fills else 1.5,
                    execution_latency_ms=exec_res.latency_ms,
                    fee_usd=exec_res.total_fee_usd,
                    initial_stop_price=new_pos.initial_stop_price,
                    target_price=new_pos.target_price,
                    destination_r=outcome.destination_r,
                    opened_at=now,
                )
                self.shadow_audits[pos_id] = audit

        return outcome

    def get_shadow_performance_metrics(self) -> Dict[str, Any]:
        """Compute performance metrics of completed shadow trades."""
        total_trades = len(self.completed_trades)
        if total_trades == 0:
            return {
                "total_trades": 0,
                "net_r": 0.0,
                "win_rate": 0.0,
                "avg_slippage_bps": 0.0,
                "avg_latency_ms": 0.0,
                "target_exits": 0,
                "stop_exits": 0,
                "emergency_exits": 0,
            }

        wins = sum(1 for t in self.completed_trades if t.realized_r > 0)
        net_r = sum(t.realized_r for t in self.completed_trades)
        target_exits = sum(1 for t in self.completed_trades if t.exit_state == PositionState.CLOSED_TARGET.value)
        stop_exits = sum(1 for t in self.completed_trades if t.exit_state == PositionState.CLOSED_STOP.value)
        emergency_exits = sum(1 for t in self.completed_trades if t.exit_state == PositionState.CLOSED_EMERGENCY.value)

        avg_slippage = sum(t.slippage_bps for t in self.completed_trades) / total_trades
        avg_latency = sum(t.execution_latency_ms for t in self.completed_trades) / total_trades

        return {
            "total_trades": total_trades,
            "net_r": round(net_r, 2),
            "win_rate": round(wins / total_trades, 4),
            "avg_slippage_bps": round(avg_slippage, 2),
            "avg_latency_ms": round(avg_latency, 2),
            "target_exits": target_exits,
            "stop_exits": stop_exits,
            "emergency_exits": emergency_exits,
        }
