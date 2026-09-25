"""Crypto Trading Platform — canonical domain entities and enums.

Defines the core data models used across all planes: market data, strategy,
portfolio, risk engine, order management, execution, and reconciliation.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional
import time


class OperatingMode(str, Enum):
    PAPER = "PAPER"              # Forward paper simulation on live data
    DEMO = "DEMO"                # Exchange native sandbox/testnet
    LIVE_CANARY = "LIVE-CANARY"  # Real capital micro-canary deployment
    LIVE = "LIVE"                # Full real capital deployment (strictly locked)


class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    LIMIT = "LIMIT"
    MARKET = "MARKET"
    POST_ONLY = "POST_ONLY"
    STOP_LOSS = "STOP_LOSS"
    TAKE_PROFIT = "TAKE_PROFIT"


class TimeInForce(str, Enum):
    GTC = "GTC"   # Good 'Til Cancelled
    IOC = "IOC"   # Immediate or Cancel
    FOK = "FOK"   # Fill or Kill
    PO = "PO"     # Post-Only


class ExecutionUrgency(str, Enum):
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    EMERGENCY = "EMERGENCY"


class OrderStatus(str, Enum):
    CREATED = "CREATED"
    RISK_CHECKED = "RISK_CHECKED"
    SUBMITTED = "SUBMITTED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"    # Requires reconciliation; cannot assume failed


@dataclass
class Tenant:
    tenant_id: str
    name: str
    created_at_ms: int = field(default_factory=lambda: int(time.time() * 1000))
    is_active: bool = True
    settings: Dict[str, any] = field(default_factory=dict)


@dataclass
class TradingAccount:
    account_id: str
    tenant_id: str
    venue: str               # e.g., "binance", "bybit", "coinbase"
    environment: OperatingMode = OperatingMode.PAPER
    is_active: bool = True
    permissions: List[str] = field(default_factory=lambda: ["read", "trade"])
    created_at_ms: int = field(default_factory=lambda: int(time.time() * 1000))


@dataclass
class AccountBalance:
    asset: str
    free: float
    locked: float
    total: float
    updated_at_ms: int = field(default_factory=lambda: int(time.time() * 1000))


@dataclass
class Position:
    symbol: str
    direction: int          # +1 long, -1 short
    size: float
    entry_price: float
    mark_price: float
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    liquidation_price: Optional[float] = None
    leverage: float = 1.0
    margin: float = 0.0
    updated_at_ms: int = field(default_factory=lambda: int(time.time() * 1000))


@dataclass
class OrderIntent:
    """Emitted by Strategy Engine.

    Strategies never generate real orders or hold venue credentials. They emit
    OrderIntents that are evaluated and sized by Portfolio and Risk Engines.
    """
    intent_id: str
    strategy_id: str
    tenant_id: str
    account_id: str
    symbol: str
    direction: int          # +1 long, -1 short
    target_size: float
    urgency: ExecutionUrgency = ExecutionUrgency.NORMAL
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None
    target_price: Optional[float] = None
    horizon: str = "INTRADAY"
    created_at_ms: int = field(default_factory=lambda: int(time.time() * 1000))
    signal_reason: str = ""
    meta: Dict[str, any] = field(default_factory=dict)


@dataclass
class RiskDecision:
    """Evaluation result emitted by the independent Risk Firewall."""
    approved: bool
    reason: str
    rule_code: str = "PASS"
    adjusted_size: Optional[float] = None
    timestamp_ms: int = field(default_factory=lambda: int(time.time() * 1000))


@dataclass
class ExecutionOrder:
    """Order managed by OMS and routed to Exchange Adapters."""
    order_id: str
    client_order_id: str
    tenant_id: str
    account_id: str
    venue: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    time_in_force: TimeInForce
    quantity: float
    price: Optional[float]
    status: OrderStatus = OrderStatus.CREATED
    filled_quantity: float = 0.0
    average_fill_price: float = 0.0
    created_at_ms: int = field(default_factory=lambda: int(time.time() * 1000))
    updated_at_ms: int = field(default_factory=lambda: int(time.time() * 1000))
    rejection_reason: Optional[str] = None


@dataclass
class Fill:
    fill_id: str
    order_id: str
    client_order_id: str
    symbol: str
    side: OrderSide
    price: float
    quantity: float
    fee: float
    fee_asset: str
    is_maker: bool
    timestamp_ms: int = field(default_factory=lambda: int(time.time() * 1000))


@dataclass
class RiskState:
    equity: float
    peak_equity: float
    daily_loss_pct: float = 0.0
    drawdown_pct: float = 0.0
    gross_leverage: float = 0.0
    net_exposure: float = 0.0
    open_risk_pct: float = 0.0
    is_tripped: bool = False
    trip_reason: str = ""
    updated_at_ms: int = field(default_factory=lambda: int(time.time() * 1000))
