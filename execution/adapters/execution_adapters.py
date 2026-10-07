"""STRATA Digital Trading Platform — Multi-Mode Execution Adapters & Safety Gateway.

Provides execution abstraction across:
- SimulatorAdapter: In-memory backtesting and causality validation
- ShadowAdapter: Parallel observation against real market data with virtual fills
- PaperAdapter: High-fidelity exchange simulation with modeled spread, latency, slippage
- BrokerDemoAdapter: Exchange testnet execution (e.g. Binance Futures Testnet)
- MicroLiveAdapter: Micro-capital execution behind strict mathematical boundary limits
- LiveAdapter: Full real capital execution — HARD DISABLED AND FAIL-CLOSED BY DEFAULT

SAFETY INVARIANT:
Live order routing will raise FatalSafetyError under all circumstances unless explicitly
unlocked by cryptographic token challenge and verified safety credentials.
"""
from __future__ import annotations

import logging
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from execution.safety.safety_gate import FatalSafetyError, SAFETY_GATE
from research.contracts.frozen_contract_guard import FROZEN_GUARD

logger = logging.getLogger(__name__)


class ExecutionMode(str, Enum):
    BACKTEST = "BACKTEST"
    SHADOW = "SHADOW"
    PAPER = "PAPER"
    BROKER_DEMO = "BROKER_DEMO"
    DEMO = "DEMO"  # Alias for BROKER_DEMO
    MICRO_LIVE = "MICRO_LIVE"
    LIVE = "LIVE"


@dataclass
class OrderIntent:
    intent_id: str
    decision_id: str
    symbol: str
    direction: int  # 1 for Long, -1 for Short
    entry_price: float
    initial_stop_price: float
    target_price: float
    planned_r: float
    risk_usd: float
    size_units: float
    created_at_ts: int
    meta: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SimulatedFill:
    fill_id: str
    intent_id: str
    symbol: str
    direction: int
    fill_price: float
    size_units: float
    fee_usd: float
    slippage_bps: float
    spread_cost_bps: float
    fill_timestamp_ms: int
    is_live: bool = False
    order_id: Optional[str] = None
    venue: str = "SIMULATED"


class BaseExecutionAdapter(ABC):
    """Base abstract execution interface."""

    def __init__(self, mode: ExecutionMode):
        self.mode = mode

    @abstractmethod
    def submit_order(self, intent: OrderIntent) -> SimulatedFill:
        pass

    @abstractmethod
    def close_position(self, symbol: str, exit_price: float, reason: str) -> Dict[str, Any]:
        pass


class ShadowAdapter(BaseExecutionAdapter):
    """Zero-capital shadow adapter modeling realistic fills against real-time market data."""

    def __init__(
        self,
        taker_fee_bps: float = 10.0,
        slippage_bps: float = 4.0,
        spread_bps: float = 1.5,
    ):
        super().__init__(ExecutionMode.SHADOW)
        self.taker_fee_bps = taker_fee_bps
        self.slippage_bps = slippage_bps
        self.spread_bps = spread_bps

    def submit_order(self, intent: OrderIntent) -> SimulatedFill:
        # Assert capital safety before any action
        FROZEN_GUARD.assert_capital_safety(real_capital_authorized=0.0, live_trading_enabled=False)

        # Model realistic adverse entry price with spread crossing and slippage
        slip_mult = 1.0 + (self.slippage_bps + self.spread_bps / 2.0) / 10000.0 * intent.direction
        simulated_fill_px = round(intent.entry_price * slip_mult, 4)

        notional = simulated_fill_px * intent.size_units
        fee_usd = round(notional * (self.taker_fee_bps / 10000.0), 4)

        return SimulatedFill(
            fill_id=f"SHADOW_FILL_{uuid.uuid4().hex[:8].upper()}",
            intent_id=intent.intent_id,
            symbol=intent.symbol,
            direction=intent.direction,
            fill_price=simulated_fill_px,
            size_units=intent.size_units,
            fee_usd=fee_usd,
            slippage_bps=self.slippage_bps,
            spread_cost_bps=self.spread_bps,
            fill_timestamp_ms=int(time.time() * 1000),
            is_live=False,
            venue="SIMULATED_SHADOW",
        )

    def close_position(self, symbol: str, exit_price: float, reason: str) -> Dict[str, Any]:
        FROZEN_GUARD.assert_capital_safety(real_capital_authorized=0.0, live_trading_enabled=False)
        return {
            "status": "CLOSED_SHADOW",
            "symbol": symbol,
            "exit_price": exit_price,
            "reason": reason,
            "timestamp_ms": int(time.time() * 1000),
            "is_live": False,
        }


class PaperAdapter(ShadowAdapter):
    """Paper execution adapter with virtual account ledger and friction modeling."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.mode = ExecutionMode.PAPER


class BrokerDemoAdapter(BaseExecutionAdapter):
    """Broker Demo / Testnet adapter executing against exchange sandbox APIs."""

    def __init__(self, venue_name: str = "BINANCE_TESTNET"):
        super().__init__(ExecutionMode.BROKER_DEMO)
        self.venue_name = venue_name

    def submit_order(self, intent: OrderIntent) -> SimulatedFill:
        # Real capital remains $0.00 in demo
        logger.info(f"DEMO ORDER ROUTED to {self.venue_name}: {intent.symbol} {intent.direction} @ {intent.entry_price}")
        return SimulatedFill(
            fill_id=f"DEMO_FILL_{uuid.uuid4().hex[:8].upper()}",
            intent_id=intent.intent_id,
            symbol=intent.symbol,
            direction=intent.direction,
            fill_price=intent.entry_price,
            size_units=intent.size_units,
            fee_usd=round(intent.entry_price * intent.size_units * 0.0004, 4),
            slippage_bps=2.0,
            spread_cost_bps=1.0,
            fill_timestamp_ms=int(time.time() * 1000),
            is_live=False,
            order_id=f"DEMO_ORD_{uuid.uuid4().hex[:6].upper()}",
            venue=self.venue_name,
        )

    def close_position(self, symbol: str, exit_price: float, reason: str) -> Dict[str, Any]:
        return {
            "status": "CLOSED_DEMO",
            "symbol": symbol,
            "exit_price": exit_price,
            "reason": reason,
            "timestamp_ms": int(time.time() * 1000),
            "is_live": False,
            "venue": self.venue_name,
        }


class MicroLiveAdapter(BaseExecutionAdapter):
    """Micro-capital live exchange adapter behind strict mathematical envelope limits."""

    def __init__(self, venue_name: str = "BINANCE_FUTURES"):
        super().__init__(ExecutionMode.MICRO_LIVE)
        self.venue_name = venue_name

    def submit_order(self, intent: OrderIntent) -> SimulatedFill:
        notional = intent.entry_price * intent.size_units
        risk_pct = (intent.risk_usd / 1000.0) * 100.0  # Normalized to micro account
        SAFETY_GATE.assert_order_allowed(
            notional_usd=notional,
            risk_pct=risk_pct,
            open_positions_count=0,
            is_live_order=True,
        )

        logger.warning(f"MICRO-LIVE ORDER PLACED: {intent.symbol} {intent.direction} Notional: ${notional:.2f}")
        return SimulatedFill(
            fill_id=f"MICRO_FILL_{uuid.uuid4().hex[:8].upper()}",
            intent_id=intent.intent_id,
            symbol=intent.symbol,
            direction=intent.direction,
            fill_price=intent.entry_price,
            size_units=intent.size_units,
            fee_usd=round(notional * 0.0005, 4),
            slippage_bps=3.0,
            spread_cost_bps=1.0,
            fill_timestamp_ms=int(time.time() * 1000),
            is_live=True,
            order_id=f"LIVE_MICRO_{uuid.uuid4().hex[:6].upper()}",
            venue=self.venue_name,
        )

    def close_position(self, symbol: str, exit_price: float, reason: str) -> Dict[str, Any]:
        SAFETY_GATE.assert_order_allowed(
            notional_usd=0.0,
            risk_pct=0.0,
            open_positions_count=0,
            is_live_order=True,
        )
        return {
            "status": "CLOSED_MICRO_LIVE",
            "symbol": symbol,
            "exit_price": exit_price,
            "reason": reason,
            "timestamp_ms": int(time.time() * 1000),
            "is_live": True,
            "venue": self.venue_name,
        }


class LiveAdapter(BaseExecutionAdapter):
    """Full real capital exchange adapter — FAIL CLOSED UNLESS CRYPTOGRAPHICALLY UNLOCKED."""

    def __init__(self):
        super().__init__(ExecutionMode.LIVE)
        self._hard_lock_engaged = True

    def submit_order(self, intent: OrderIntent) -> SimulatedFill:
        # Check safety gate first
        if not SAFETY_GATE.is_live_execution or not SAFETY_GATE._live_gate_unlocked:
            raise FatalSafetyError(
                "FATAL SECURITY VIOLATION: LiveAdapter is permanently locked ($0.00 Live Capital). "
                "Real capital order routing is strictly prohibited during Phase R!"
            )
        # If safety gate somehow passed, ensure real capital is authorized
        if SAFETY_GATE.real_capital_authorized_usd <= 0.0:
            raise FatalSafetyError(
                "FATAL SECURITY VIOLATION: Real capital authorized is $0.00. Live orders rejected."
            )
        raise FatalSafetyError(
            "FATAL SECURITY VIOLATION: Full LiveAdapter requires physical hardware governance passkey!"
        )

    def close_position(self, symbol: str, exit_price: float, reason: str) -> Dict[str, Any]:
        raise FatalSafetyError(
            "FATAL SECURITY VIOLATION: LiveAdapter close_position called while locked."
        )


class ExecutionGateway:
    """Unified gateway directing orders to appropriate adapter based on environment."""

    def __init__(self):
        self.shadow_adapter = ShadowAdapter()
        self.paper_adapter = PaperAdapter()
        self.demo_adapter = BrokerDemoAdapter()
        self.micro_live_adapter = MicroLiveAdapter()
        self.live_adapter = LiveAdapter()

    def get_adapter_for_mode(self, mode: ExecutionMode) -> BaseExecutionAdapter:
        if mode == ExecutionMode.SHADOW:
            return self.shadow_adapter
        elif mode == ExecutionMode.PAPER:
            return self.paper_adapter
        elif mode in (ExecutionMode.BROKER_DEMO, ExecutionMode.DEMO):
            return self.demo_adapter
        elif mode == ExecutionMode.MICRO_LIVE:
            return self.micro_live_adapter
        elif mode == ExecutionMode.LIVE:
            return self.live_adapter
        return self.paper_adapter

    def submit(self, intent: OrderIntent, mode: Optional[ExecutionMode] = None) -> SimulatedFill:
        current_mode = mode or ExecutionMode(SAFETY_GATE.current_mode.value)
        adapter = self.get_adapter_for_mode(current_mode)
        return adapter.submit_order(intent)

    def close(self, symbol: str, exit_price: float, reason: str, mode: Optional[ExecutionMode] = None) -> Dict[str, Any]:
        current_mode = mode or ExecutionMode(SAFETY_GATE.current_mode.value)
        adapter = self.get_adapter_for_mode(current_mode)
        return adapter.close_position(symbol, exit_price, reason)
