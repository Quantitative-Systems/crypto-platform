"""Drawdown Governor: Dynamic Equity Curve Protection & Phased Recovery.

Enforces multi-tiered risk reduction and circuit breakers based on peak-to-trough
equity decline, preventing catastrophic drawdowns and tail risk ruin.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from execution.risk.contracts import DrawdownTier


@dataclass
class DrawdownStatus:
    current_equity_r: float
    peak_equity_r: float
    current_drawdown_pct: float
    current_drawdown_r: float
    max_drawdown_pct: float
    tier: DrawdownTier
    risk_multiplier: float                 # Multiplier applied to position sizing
    destination_r_floor: float             # Floor required for candidate target R
    time_underwater_bars: int
    is_halted: bool = False
    message: str = "Normal operating conditions."


class DrawdownGovernor:
    """Manages equity high-water mark, drawdown tiers, and recovery pacing."""

    def __init__(
        self,
        elevated_threshold_pct: float = 5.0,    # 5% DD -> 50% risk haircut
        severe_threshold_pct: float = 10.0,     # 10% DD -> 75% risk haircut & 5R floor
        critical_halt_pct: float = 15.0,        # 15% DD -> Circuit breaker trading halt
        initial_equity_usd: float = 100_000.0,
    ):
        self.elevated_threshold_pct = elevated_threshold_pct
        self.severe_threshold_pct = severe_threshold_pct
        self.critical_halt_pct = critical_halt_pct
        self.initial_equity_usd = initial_equity_usd

        # State tracking
        self.current_equity_r: float = 0.0
        self.peak_equity_r: float = 0.0
        self.current_equity_usd: float = initial_equity_usd
        self.peak_equity_usd: float = initial_equity_usd
        self.max_drawdown_pct: float = 0.0
        self.time_underwater_bars: int = 0
        self.consecutive_profitable_bars: int = 0
        self.history: List[Dict[str, Any]] = []

    def update_equity_r(self, delta_r: float, bar_index: int = 0) -> DrawdownStatus:
        """Update equity curve with realized R outcome."""
        self.current_equity_r += delta_r
        # Standard conversion: 1R = 1% of initial equity
        self.current_equity_usd += delta_r * (self.initial_equity_usd * 0.01)

        if self.current_equity_r > self.peak_equity_r:
            self.peak_equity_r = self.current_equity_r
            self.peak_equity_usd = self.current_equity_usd
            self.time_underwater_bars = 0
            self.consecutive_profitable_bars += 1
        else:
            self.time_underwater_bars += 1
            if delta_r <= 0:
                self.consecutive_profitable_bars = 0

        # Calculate peak-to-trough decline
        dd_r = self.peak_equity_r - self.current_equity_r
        dd_pct = ((self.peak_equity_usd - self.current_equity_usd) / self.peak_equity_usd * 100.0) if self.peak_equity_usd > 0 else 0.0
        dd_pct = max(0.0, dd_pct)
        self.max_drawdown_pct = max(self.max_drawdown_pct, dd_pct)

        status = self.evaluate_status()
        self.history.append({
            "bar_index": bar_index,
            "equity_r": round(self.current_equity_r, 2),
            "drawdown_pct": round(dd_pct, 2),
            "tier": status.tier.value,
            "risk_multiplier": status.risk_multiplier,
        })
        return status

    def record_trade_result(self, trade_r: float, timestamp_ms: int = 0, bar_index: int = 0) -> DrawdownStatus:
        """Alias for recording realized trade outcome."""
        return self.update_equity_r(delta_r=trade_r, bar_index=bar_index)

    def evaluate_status(self) -> DrawdownStatus:
        """Determine current drawdown tier and derived defense constraints."""
        dd_r = self.peak_equity_r - self.current_equity_r
        dd_pct = ((self.peak_equity_usd - self.current_equity_usd) / self.peak_equity_usd * 100.0) if self.peak_equity_usd > 0 else 0.0
        dd_pct = max(0.0, dd_pct)

        if dd_pct >= self.critical_halt_pct:
            tier = DrawdownTier.CRITICAL_HALT
            mult = 0.0
            floor = 10.0
            is_halted = True
            msg = f"CRITICAL DRAWDOWN ({dd_pct:.1f}% >= {self.critical_halt_pct}%): Trading circuit breaker tripped. Capital frozen."
        elif dd_pct >= self.severe_threshold_pct:
            tier = DrawdownTier.SEVERE
            mult = 0.25 # 75% risk haircut (0.25% risk per trade)
            floor = 5.0 # Elevated destination floor: only asymmetric >= 5R trades allowed
            is_halted = False
            msg = f"SEVERE DRAWDOWN ({dd_pct:.1f}%): Risk reduced to 0.25x; target floor elevated to 5.0R."
        elif dd_pct >= self.elevated_threshold_pct:
            tier = DrawdownTier.ELEVATED
            mult = 0.50 # 50% risk haircut (0.50% risk per trade)
            floor = 4.0
            is_halted = False
            msg = f"ELEVATED DRAWDOWN ({dd_pct:.1f}%): Risk reduced to 0.50x."
        else:
            tier = DrawdownTier.NORMAL
            mult = 1.00
            floor = 4.0
            is_halted = False
            msg = f"NORMAL OPERATION: Peak equity drawdown {dd_pct:.1f}% within baseline threshold."

        return DrawdownStatus(
            current_equity_r=round(self.current_equity_r, 2),
            peak_equity_r=round(self.peak_equity_r, 2),
            current_drawdown_pct=round(dd_pct, 2),
            current_drawdown_r=round(dd_r, 2),
            max_drawdown_pct=round(self.max_drawdown_pct, 2),
            tier=tier,
            risk_multiplier=mult,
            destination_r_floor=floor,
            time_underwater_bars=self.time_underwater_bars,
            is_halted=is_halted,
            message=msg,
        )
