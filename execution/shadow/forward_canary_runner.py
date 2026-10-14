"""Institutional Forward Paper & Canary Soak Validation Runner.

Deploys the complete top-tier institutional trading organism:
1. FRACTAL ENGINE CORE:
   - Continuously evaluates the 3 Universal Pillars (Structure, KeyZones, Phases).
   - Enforces top-down causal transmission (HTF Bias -> MTF Setup -> LTF Entry).
2. PRIME CUSTODY FIREWALL:
   - Restricts exchange hot collateral to <= 20% (80% non-custodial cold vault).
   - Monitors exchange counterparty solvency.
3. SMART EXECUTION GATEWAY:
   - Maker-rebate optimization (-0.5 bps) and adaptive TWAP order slicing.
   - Real-time spread firewall and latency auditing.
4. DURABLE IMMUTABLE AUDITING:
   - Real-time writes to FORWARD_CANARY_TRACK_RECORD.json and .jsonl.
   - Live Sharpe, Realized R, Maximum Favorable Excursion, and fee breakdown.
"""
from __future__ import annotations

import json
import logging
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from execution.adapters.smart_execution_gateway import (
    ExecutionFillReport,
    OrderExecutionType,
    RoutedOrderIntent,
    SmartExecutionGateway,
)
from execution.risk.custody_risk_firewall import (
    CounterpartySolvencyState,
    CustodyRiskFirewall,
    CustodyProviderType,
)
from market_model.cascading_fractal_coordinator import (
    CascadingFractalCoordinator,
    MacroPhaseBaton,
)
from research.experiments.run_phase_p_fractal_discovery import load_series_arrays

RESULTS_DIR = WORKSPACE_ROOT / "research" / "results" / "FORWARD_CANARY"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger("ForwardCanaryRunner")


@dataclass
class CanaryLivePosition:
    position_id: str
    symbol: str
    timeframe_set: str
    direction: int                      # 1 = Long, -1 = Short
    entry_price: float
    current_stop_price: float
    initial_stop_price: float
    target_price: float
    size_usd: float
    entry_ts_ms: int
    is_break_even: bool = False
    mfe_r: float = 0.0
    mae_r: float = 0.0
    realized_r: Optional[float] = None
    exit_price: Optional[float] = None
    exit_ts_ms: Optional[int] = None
    exit_reason: Optional[str] = None


class ForwardCanaryRunner:
    """Master Institutional Forward Validation Runner."""

    def __init__(
        self,
        symbols: Optional[List[str]] = None,
        total_fund_equity_usd: float = 100_000.0,
        risk_per_trade_pct: float = 0.01,
        max_portfolio_heat_pct: float = 0.03,
        min_target_r: float = 4.0,
        max_hot_collateral_pct: float = 0.20,
    ):
        self.symbols = [s.upper() for s in (symbols or [
            "BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT",
            "ARBUSDT", "RENDERUSDT", "INJUSDT", "NEARUSDT"
        ])]
        self.total_fund_equity_usd = total_fund_equity_usd
        self.risk_per_trade_pct = risk_per_trade_pct
        self.max_portfolio_heat_pct = max_portfolio_heat_pct
        self.min_target_r = min_target_r

        # Pillar 1: Custody Firewall
        self.custody_firewall = CustodyRiskFirewall(
            total_fund_equity_usd=total_fund_equity_usd,
            max_hot_collateral_pct=max_hot_collateral_pct,
            custody_provider=CustodyProviderType.SIMULATED_INSTITUTIONAL,
        )

        # Pillar 2: Smart Execution Router
        self.router = SmartExecutionGateway(
            default_venue="BINANCE",
            maker_fee_bps=-0.5,
            taker_fee_bps=5.0,
        )

        # Pillar 3: Fractal Engine Coordinator
        self.coordinator = CascadingFractalCoordinator(
            min_target_r=min_target_r,
            risk_per_trade_pct=risk_per_trade_pct,
            account_equity_usd=total_fund_equity_usd,
        )

        self.open_positions: Dict[str, CanaryLivePosition] = {}
        self.closed_positions: List[CanaryLivePosition] = []
        self.track_record_file = RESULTS_DIR / "FORWARD_CANARY_TRACK_RECORD.json"
        self.ledger_file = RESULTS_DIR / "FORWARD_CANARY_LEDGER.jsonl"
        self._pos_counter = 0

    def evaluate_live_market_tick(
        self,
        symbol: str,
        target_set: str,
        all_data: Dict[str, Dict[str, np.ndarray]],
        current_bid: float,
        current_ask: float,
    ) -> Optional[CanaryLivePosition]:
        """Evaluates live market state and executes causal forward canary paper trades."""
        # 1. Check portfolio heat limit
        open_risk_usd = sum(p.size_usd * (self.risk_per_trade_pct) for p in self.open_positions.values())
        open_heat_pct = open_risk_usd / max(self.total_fund_equity_usd, 1.0)
        if open_heat_pct >= self.max_portfolio_heat_pct:
            return None

        # 2. Check Custody Firewall
        trade_risk_budget_usd = self.total_fund_equity_usd * self.risk_per_trade_pct
        allowed, reason = self.custody_firewall.check_pre_trade_collateral("BINANCE", trade_risk_budget_usd)
        if not allowed:
            return None

        # 3. Generate Fractal Candidates
        candidates, trailing_map = self.coordinator.scan_cascading_candidates(
            symbol=symbol,
            target_set=target_set,
            all_data=all_data,
            only_latest_bar=True,
        )

        if not candidates:
            return None

        cand = candidates[-1]
        direction = cand["direction"]
        sl = cand["stop_price"]
        tp = cand["target_price"]
        size_usd = cand.get("position_size_usd", trade_risk_budget_usd * 10.0)

        # 4. Route through Smart Execution Gateway
        intent, route_msg = self.router.route_order(
            symbol=symbol,
            direction=direction,
            size_usd=size_usd,
            best_bid=current_bid,
            best_ask=current_ask,
            stop_price=sl,
            target_price=tp,
            prefer_maker=True,
        )

        if not intent:
            return None

        # 5. Simulate institutional fill
        fill = self.router.simulate_institutional_fill(
            intent=intent,
            arrival_price=(current_bid + current_ask) / 2.0,
            best_bid=current_bid,
            best_ask=current_ask,
        )

        self._pos_counter += 1
        pos_id = f"CANARY-{symbol}-{target_set}-{self._pos_counter}"
        pos = CanaryLivePosition(
            position_id=pos_id,
            symbol=symbol,
            timeframe_set=target_set,
            direction=direction,
            entry_price=fill.filled_price,
            current_stop_price=sl,
            initial_stop_price=sl,
            target_price=tp,
            size_usd=size_usd,
            entry_ts_ms=fill.timestamp_ms,
        )

        self.open_positions[pos_id] = pos
        self._append_ledger_event("POSITION_OPENED", {
            "position_id": pos_id,
            "symbol": symbol,
            "set": target_set,
            "direction": direction,
            "entry_price": fill.filled_price,
            "stop_price": sl,
            "target_price": tp,
            "size_usd": size_usd,
            "is_maker": fill.is_maker,
            "fee_usd": fill.fee_usd,
        })

        return pos

    def update_open_positions(self, symbol: str, current_high: float, current_low: float, current_close: float):
        """Updates trailing stops, checks break-even locks, and evaluates exits."""
        now_ms = int(time.time() * 1000)
        to_close = []

        for pos_id, pos in self.open_positions.items():
            if pos.symbol != symbol:
                continue

            risk_dist = abs(pos.entry_price - pos.initial_stop_price)
            if risk_dist <= 0:
                continue

            if pos.direction == 1:
                favorable_dist = current_high - pos.entry_price
                adverse_dist = pos.entry_price - current_low
                curr_r = (current_close - pos.entry_price) / risk_dist

                pos.mfe_r = max(pos.mfe_r, favorable_dist / risk_dist)
                pos.mae_r = max(pos.mae_r, adverse_dist / risk_dist)

                # +1.5R Break-Even Lock
                if pos.mfe_r >= 1.5 and not pos.is_break_even:
                    pos.current_stop_price = max(pos.current_stop_price, pos.entry_price + (risk_dist * 0.1))
                    pos.is_break_even = True
                    self._append_ledger_event("BREAK_EVEN_RATCHET", {"position_id": pos_id, "new_sl": pos.current_stop_price})

                # Check Stop Loss exit
                if current_low <= pos.current_stop_price:
                    pos.exit_price = pos.current_stop_price
                    pos.exit_reason = "STOP_LOSS" if not pos.is_break_even else "BREAK_EVEN"
                    pos.realized_r = (pos.exit_price - pos.entry_price) / risk_dist
                    pos.exit_ts_ms = now_ms
                    to_close.append(pos_id)
                # Check Take Profit exit
                elif current_high >= pos.target_price:
                    pos.exit_price = pos.target_price
                    pos.exit_reason = "TAKE_PROFIT"
                    pos.realized_r = (pos.exit_price - pos.entry_price) / risk_dist
                    pos.exit_ts_ms = now_ms
                    to_close.append(pos_id)

            else:  # Short
                favorable_dist = pos.entry_price - current_low
                adverse_dist = current_high - pos.entry_price
                curr_r = (pos.entry_price - current_close) / risk_dist

                pos.mfe_r = max(pos.mfe_r, favorable_dist / risk_dist)
                pos.mae_r = max(pos.mae_r, adverse_dist / risk_dist)

                # +1.5R Break-Even Lock
                if pos.mfe_r >= 1.5 and not pos.is_break_even:
                    pos.current_stop_price = min(pos.current_stop_price, pos.entry_price - (risk_dist * 0.1))
                    pos.is_break_even = True
                    self._append_ledger_event("BREAK_EVEN_RATCHET", {"position_id": pos_id, "new_sl": pos.current_stop_price})

                # Check Stop Loss exit
                if current_high >= pos.current_stop_price:
                    pos.exit_price = pos.current_stop_price
                    pos.exit_reason = "STOP_LOSS" if not pos.is_break_even else "BREAK_EVEN"
                    pos.realized_r = (pos.entry_price - pos.exit_price) / risk_dist
                    pos.exit_ts_ms = now_ms
                    to_close.append(pos_id)
                # Check Take Profit exit
                elif current_low <= pos.target_price:
                    pos.exit_price = pos.target_price
                    pos.exit_reason = "TAKE_PROFIT"
                    pos.realized_r = (pos.entry_price - pos.exit_price) / risk_dist
                    pos.exit_ts_ms = now_ms
                    to_close.append(pos_id)

        for pid in to_close:
            closed = self.open_positions.pop(pid)
            self.closed_positions.append(closed)
            self._append_ledger_event("POSITION_CLOSED", {
                "position_id": closed.position_id,
                "symbol": closed.symbol,
                "realized_r": round(closed.realized_r or 0.0, 2),
                "exit_reason": closed.exit_reason,
                "mfe_r": round(closed.mfe_r, 2),
            })

    def _append_ledger_event(self, event_type: str, data: Dict[str, Any]):
        entry = {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "data": data,
        }
        with open(self.ledger_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

    def persist_track_record_summary(self) -> Dict[str, Any]:
        """Generates comprehensive forward canary performance audit summary."""
        total_closed = len(self.closed_positions)
        wins = [p for p in self.closed_positions if (p.realized_r or 0.0) > 0]
        losses = [p for p in self.closed_positions if (p.realized_r or 0.0) <= 0]

        total_r = sum(p.realized_r or 0.0 for p in self.closed_positions)
        gross_win = sum(p.realized_r or 0.0 for p in wins)
        gross_loss = abs(sum(p.realized_r or 0.0 for p in losses))

        win_rate = (len(wins) / max(total_closed, 1)) * 100
        pf = gross_win / max(gross_loss, 0.001)

        custody_report = self.custody_firewall.generate_custody_report()

        summary = {
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "fund_equity_usd": self.total_fund_equity_usd,
            "custody_architecture": {
                "provider": self.custody_firewall.custody_provider.value,
                "cold_vault_usd": custody_report.cold_vault_equity_usd,
                "hot_exchange_usd": custody_report.hot_exchange_equity_usd,
                "hot_exchange_pct": custody_report.hot_exchange_pct,
                "is_within_budget": custody_report.is_within_custody_budget,
            },
            "performance_metrics": {
                "total_closed_trades": total_closed,
                "active_open_trades": len(self.open_positions),
                "win_rate_pct": round(win_rate, 2),
                "net_realized_r": round(total_r, 2),
                "profit_factor": round(pf, 2),
                "expectancy_r": round(total_r / max(total_closed, 1), 3),
            },
            "smart_execution_metrics": {
                "total_routed_orders": len(self.router.execution_ledger),
                "maker_orders_count": sum(1 for f in self.router.execution_ledger if f.is_maker),
                "total_fees_usd": round(sum(f.fee_usd for f in self.router.execution_ledger), 2),
                "avg_slippage_bps": round(np.mean([f.slippage_bps for f in self.router.execution_ledger]) if self.router.execution_ledger else 0.0, 2),
            },
        }

        with open(self.track_record_file, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)

        return summary
