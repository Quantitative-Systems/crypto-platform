"""Autonomous Shadow/Paper Champion Engine & Demotion Governor.

Operationalizes the 24/7/365 production paper validation pipeline:
1. Instrument Discovery & Health Check
2. Causal Market State Generation (HTF -> MTF -> LTF)
3. Champion Signal Evaluation (from validated Champion Registry)
4. Strict Directional Geometry & 4R Floor Enforcement
5. Portfolio Risk Governor (1% per trade, 1% per asset, 3% portfolio heat)
6. Execution Simulation & Decision Ledger Auditing (Zero Real Capital)
7. MTF Structural Trailing Stop Management
8. Auto-Degradation & Auto-Demotion Trigger
"""
from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from execution.decision_ledger import DecisionLedger, DecisionType
from execution.portfolio.risk_governor import (
    PortfolioOpportunity,
    PortfolioRiskGovernor,
)
from execution.position.position_lifecycle import Position, PositionLifecycleMonitor, PositionState
from execution.simulator.execution_simulator import (
    ExecutionSimulator,
    OrderSide,
    OrderStatus,
    OrderType,
    SimulatedOrder,
)
from instrument.instrument_contract import CryptoBaseInstrument
from instrument.instrument_health import HealthStatus, InstrumentHealth
from instrument.instrument_registry import InstrumentRegistry


@dataclass
class PaperTradeAudit:
    decision_id: str
    symbol: str
    timeframe_set: str
    champion_id: str
    direction: int
    entry_ts: int
    predicted_entry: float
    simulated_fill: float
    initial_sl: float
    target_px: float
    target_r: float
    slippage_bps: float
    fee_bps: float
    exit_ts: Optional[int] = None
    exit_px: Optional[float] = None
    exit_reason: Optional[str] = None
    realized_r: Optional[float] = None
    status: str = "OPEN"
    ledger_hash: Optional[str] = None


@dataclass
class ChampionHealthState:
    champion_id: str
    slot_key: str
    status: str  # ACTIVE_PAPER, DEMOTED_DRIFT, DEMOTED_COST, PAUSED
    total_paper_trades: int = 0
    paper_expectancy_r: float = 0.0
    rolling_trades_r: List[float] = field(default_factory=list)
    cumulative_drag_bps: float = 0.0
    demotion_reason: Optional[str] = None


class PaperChampionEngine:
    """Production candidate paper trading engine with autonomous drift demotion."""

    def __init__(
        self,
        registry_path: Optional[Path] = None,
        ledger_path: Optional[Path] = None,
        account_equity_usd: float = 100_000.0,
        taker_fee_bps: float = 5.0,
        slippage_bps: float = 2.0,
    ):
        self.workspace_root = Path(__file__).resolve().parent.parent.parent
        self.risk_governor = PortfolioRiskGovernor(
            max_total_portfolio_risk_pct=0.03,
            max_single_trade_risk_pct=0.01,
        )
        self.simulator = ExecutionSimulator(taker_fee_bps=taker_fee_bps)
        self.position_monitor = PositionLifecycleMonitor()
        self.ledger = DecisionLedger(ledger_path or (self.workspace_root / "execution" / "shadow" / "PAPER_DECISION_LEDGER.json"))

        self.account_equity_usd = account_equity_usd
        self.taker_fee_bps = taker_fee_bps
        self.slippage_bps = slippage_bps

        # Champions state
        self.champions: Dict[str, ChampionHealthState] = {}
        self.active_paper_trades: Dict[str, PaperTradeAudit] = {}
        self.completed_paper_trades: List[PaperTradeAudit] = []

        self._load_promoted_champions(registry_path)

    def _load_promoted_champions(self, path: Optional[Path]):
        """Loads promoted champions from registry."""
        reg_file = path or (self.workspace_root / "research" / "results" / "discovery_engine" / "CHAMPION_CHALLENGER_REGISTRY.json")
        if not reg_file.exists():
            return

        try:
            with open(reg_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            for slot_key, champ in data.items():
                c_id = champ.get("candidate_id", slot_key)
                self.champions[c_id] = ChampionHealthState(
                    champion_id=c_id,
                    slot_key=slot_key,
                    status="ACTIVE_PAPER",
                )
        except Exception as e:
            print(f"[WARN] Failed to load champion registry: {e}")

    def evaluate_opportunity(
        self,
        champion_id: str,
        symbol: str,
        timeframe_set: str,
        direction: int,
        entry_price: float,
        stop_price: float,
        target_price: float,
        timestamp_ms: int,
        market_state_snapshot: Optional[Dict[str, Any]] = None,
    ) -> Optional[PaperTradeAudit]:
        """Evaluates an incoming signal through strict risk, geometry, and demotion gates."""
        # 1. Check Champion status
        champ = self.champions.get(champion_id)
        if champ and champ.status != "ACTIVE_PAPER":
            return None

        # 2. Strict Directional Geometry Invariant
        if direction == 1:
            if stop_price >= entry_price or target_price <= entry_price:
                return None  # Long geometry violation: Target > Entry > Stop
            risk_dist = entry_price - stop_price
            reward_dist = target_price - entry_price
        elif direction == -1:
            if stop_price <= entry_price or target_price >= entry_price:
                return None  # Short geometry violation: Target < Entry < Stop
            risk_dist = stop_price - entry_price
            reward_dist = entry_price - target_price
        else:
            return None

        if risk_dist <= 0 or reward_dist <= 0:
            return None

        # 3. Minimum 4R Floor Invariant
        target_r = reward_dist / risk_dist
        if target_r < 3.999:
            return None

        # 4. Portfolio Risk Governor Check
        opp = PortfolioOpportunity(
            symbol=symbol,
            direction=direction,
            expected_edge_r=0.80,
            destination_r=target_r,
            base_risk_pct=0.01,
        )
        allocated = self.risk_governor.allocate_portfolio_risk([opp])
        if not allocated or allocated[0].approved_risk_pct <= 0:
            return None
        approved_risk_pct = allocated[0].approved_risk_pct

        # 5. Execution Simulation (Taker fees + slippage)
        slip_frac = (self.slippage_bps / 1e4)
        sim_fill = entry_price * (1.0 + direction * slip_frac)

        decision_id = f"DEC_{uuid.uuid4().hex[:12]}"
        audit = PaperTradeAudit(
            decision_id=decision_id,
            symbol=symbol,
            timeframe_set=timeframe_set,
            champion_id=champion_id,
            direction=direction,
            entry_ts=timestamp_ms,
            predicted_entry=entry_price,
            simulated_fill=sim_fill,
            initial_sl=stop_price,
            target_px=target_price,
            target_r=round(target_r, 2),
            slippage_bps=self.slippage_bps,
            fee_bps=self.taker_fee_bps * 2.0,
            status="OPEN",
        )

        # Log decision into immutable ledger
        self.ledger.record_decision(
            timestamp_ms=timestamp_ms,
            symbol=symbol,
            timeframe_set=timeframe_set,
            decision=DecisionType.TRADE,
            primary_reason=f"Champion {champion_id} passed risk and geometry gates (Target R={target_r:.2f})",
            direction="LONG" if direction == 1 else "SHORT",
            htf_destination_r=target_r,
            risk_allocated_pct=approved_risk_pct,
            entry_price=entry_price,
            stop_price=stop_price,
            target_price=target_price,
            meta={
                "champion_id": champion_id,
                "fill_price": sim_fill,
                "market_state": market_state_snapshot or {},
            },
        )

        self.active_paper_trades[decision_id] = audit
        return audit

    def update_open_trades(
        self,
        current_low: float,
        current_high: float,
        current_close: float,
        timestamp_ms: int,
        mtf_trailing_level: Optional[float] = None,
    ) -> List[PaperTradeAudit]:
        """Manages active paper positions with adverse-first collision and MTF trailing stop."""
        closed_this_bar: List[PaperTradeAudit] = []

        for dec_id, trade in list(self.active_paper_trades.items()):
            direction = trade.direction
            current_sl = trade.initial_sl
            target_px = trade.target_px
            risk_dist = abs(trade.predicted_entry - trade.initial_sl)

            # Monotonic MTF Trailing SL update
            if mtf_trailing_level is not None:
                if direction == 1 and mtf_trailing_level > current_sl:
                    current_sl = min(mtf_trailing_level, target_px)
                elif direction == -1 and mtf_trailing_level < current_sl:
                    current_sl = max(mtf_trailing_level, target_px)

            exit_px = None
            exit_reason = None

            # Adverse-first collision resolution
            if direction == 1:
                if current_low <= current_sl:
                    exit_px = current_sl
                    exit_reason = "LTF_SL" if current_sl == trade.initial_sl else "MTF_TRAIL"
                elif current_high >= target_px:
                    exit_px = target_px
                    exit_reason = "HTF_TP"
            else:
                if current_high >= current_sl:
                    exit_px = current_sl
                    exit_reason = "LTF_SL" if current_sl == trade.initial_sl else "MTF_TRAIL"
                elif current_low <= target_px:
                    exit_px = target_px
                    exit_reason = "HTF_TP"

            if exit_px is not None:
                trade.exit_ts = timestamp_ms
                trade.exit_px = exit_px
                trade.exit_reason = exit_reason
                trade.status = "CLOSED"

                # Calculate realized P/L and R
                slip_frac = (self.slippage_bps / 1e4)
                fill_exit = exit_px * (1.0 - direction * slip_frac)
                rt_fee_bps = self.taker_fee_bps * 2.0
                gross_pnl_bps = ((fill_exit - trade.simulated_fill) / trade.simulated_fill) * 1e4 * direction
                net_pnl_bps = gross_pnl_bps - rt_fee_bps
                realized_r = (net_pnl_bps / 1e4 * trade.simulated_fill) / risk_dist

                trade.realized_r = round(realized_r, 4)

                self.completed_paper_trades.append(trade)
                del self.active_paper_trades[dec_id]
                closed_this_bar.append(trade)

                # Feed outcome to drift & demotion governor
                self._update_champion_drift(trade.champion_id, realized_r)

        return closed_this_bar

    def _update_champion_drift(self, champion_id: str, realized_r: float):
        """Monitors rolling performance and triggers autonomous demotion on degradation."""
        champ = self.champions.get(champion_id)
        if not champ:
            return

        champ.total_paper_trades += 1
        champ.rolling_trades_r.append(realized_r)
        if len(champ.rolling_trades_r) > 30:
            champ.rolling_trades_r.pop(0)

        # Autonomous Demotion Rule:
        # If N >= 15 and rolling expectancy <= -0.10R -> DEMOTE_DRIFT
        if len(champ.rolling_trades_r) >= 15:
            rolling_exp = float(np.mean(champ.rolling_trades_r))
            champ.paper_expectancy_r = rolling_exp
            if rolling_exp < -0.10:
                champ.status = "DEMOTED_DRIFT"
                champ.demotion_reason = f"Rolling paper expectancy collapsed to {rolling_exp:.3f}R (N={len(champ.rolling_trades_r)})"
                print(f"[DEMOTION GOVERNOR] Champion {champion_id} automatically demoted: {champ.demotion_reason}")

    def summary_status(self) -> Dict[str, Any]:
        """Returns complete operational status."""
        return {
            "total_champions": len(self.champions),
            "active_paper_champions": sum(1 for c in self.champions.values() if c.status == "ACTIVE_PAPER"),
            "demoted_champions": sum(1 for c in self.champions.values() if c.status.startswith("DEMOTED")),
            "active_open_trades": len(self.active_paper_trades),
            "completed_paper_trades": len(self.completed_paper_trades),
            "champions_status": {c_id: asdict(c) for c_id, c in self.champions.items()},
        }
