"""
Product 06 — 24/7/365 Live Execution Gateway
Contracts for Orders, Fills, Positions, and Exchange Operations.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Dict, Any


class OrderType(Enum):
    LIMIT = "LIMIT"
    MARKET = "MARKET"
    STOP_MARKET = "STOP_MARKET"
    POST_ONLY = "POST_ONLY"


class OrderSide(Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderStatus(Enum):
    NEW = "NEW"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELED = "CANCELED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class PositionSide(Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    FLAT = "FLAT"


@dataclass
class LiveOrder:
    order_id: str
    client_order_id: str
    symbol: str
    side: OrderSide
    order_type: OrderType
    price: float
    quantity: float
    filled_quantity: float = 0.0
    average_fill_price: float = 0.0
    status: OrderStatus = OrderStatus.NEW
    created_timestamp_ms: int = 0
    updated_timestamp_ms: int = 0
    stop_price: Optional[float] = None
    reduce_only: bool = False
    post_only: bool = False
    raw_response: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ExecutionFill:
    fill_id: str
    order_id: str
    client_order_id: str
    symbol: str
    side: OrderSide
    fill_price: float
    fill_quantity: float
    fee_usd: float
    is_maker: bool
    timestamp_ms: int


@dataclass
class PositionRecord:
    symbol: str
    side: PositionSide
    quantity: float
    entry_price: float
    current_price: float
    unrealized_pnl_usd: float = 0.0
    realized_pnl_usd: float = 0.0
    stop_loss_price: Optional[float] = None
    take_profit_price: Optional[float] = None
    active_sl_order_id: Optional[str] = None
    peak_favorable_price: float = 0.0
    is_profit_locked: bool = False
    last_updated_timestamp_ms: int = 0
