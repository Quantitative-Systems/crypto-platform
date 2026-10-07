"""
Quantitative Systems Platform (QSP) — Trade Management Package.
"""

from trade_management.lifecycle_engine import (
    TradeManagementEngine,
    ManagedPosition,
    PositionLifecycleStage,
    PreEntryCheckResult,
    TradeOrderPlan,
    OrderType,
)
from trade_management.trailing import MTFTrailingEngine, TrailingUpdate

__all__ = [
    "TradeManagementEngine",
    "ManagedPosition",
    "PositionLifecycleStage",
    "PreEntryCheckResult",
    "TradeOrderPlan",
    "OrderType",
    "MTFTrailingEngine",
    "TrailingUpdate",
]
