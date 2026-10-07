"""QCP Edge Lab causal backtester (single stream).

Contract: signals on CLOSED bars only; fill NEXT bar open + costs.
Adverse-first SL/TP collision. Costs before any edge claim.
One position at a time per stream.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List
import numpy as np
from .config import RISK_PCT, TAKER_FEE_PCT, SLIPPAGE_PCT, SPREAD_PCT


@dataclass
class StreamResult:
    n: int = 0
    net_r: float = 0.0
    expectancy_r: float = 0.0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    max_dd_r: float = 0.0
    avg_win_r: float = 0.0
    avg_loss_r: float = 0.0
    realized: np.ndarray = field(default_factory=lambda: np.array([]))
    entry_idx: np.ndarray = field(default_factory=lambda: np.array([], dtype=int))
    exit_idx: np.ndarray = field(default_factory=lambda: np.array([], dtype=int))
    exit_reason: List[str] = field(default_factory=list)
    mfe_r: np.ndarray = field(default_factory=lambda: np.array([]))
    mae_r: np.ndarray = field(default_factory=lambda: np.array([]))
