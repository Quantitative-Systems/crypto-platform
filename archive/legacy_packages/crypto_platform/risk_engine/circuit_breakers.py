"""Crypto Trading Platform — Circuit Breakers and Account Drawdown State Machine.

Enforces multi-tier account defense:
- Normal: Full operational limits.
- De-Risk: Triggered by moderate daily drawdown (e.g. -3%). Position sizes throttled by 50%.
- Circuit Trip: Triggered by severe daily drawdown (e.g. -5%). All new orders halted.
- Safe Mode: Triggered on systemic error or catastrophic drawdown (-12% from peak).
  Requires explicit manual intervention to reset.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import time


class CircuitState(str, Enum):
    NORMAL = "NORMAL"
    DE_RISK = "DE_RISK"
    CIRCUIT_TRIP = "CIRCUIT_TRIP"
    SAFE_MODE = "SAFE_MODE"


@dataclass
class CircuitBreakerConfig:
    daily_derisk_pct: float = 0.03       # -3% daily loss -> DE_RISK
    daily_halt_pct: float = 0.05         # -5% daily loss -> CIRCUIT_TRIP
    max_hwm_drawdown_pct: float = 0.12   # -12% all-time HWM drawdown -> SAFE_MODE
    derisk_size_multiplier: float = 0.50 # halve position sizing in DE_RISK


class AccountCircuitBreaker:
    """Manages the real-time health and circuit state of an account."""

    def __init__(self, initial_equity: float, config: CircuitBreakerConfig | None = None):
        self.config = config or CircuitBreakerConfig()
        self.initial_equity = float(initial_equity)
        self.current_equity = float(initial_equity)
        self.peak_equity = float(initial_equity)
        self.day_start_equity = float(initial_equity)
        self.state = CircuitState.NORMAL
        self.trip_reason = ""
        self.state_updated_at_ms = int(time.time() * 1000)

    def start_new_day(self, current_equity: float) -> None:
        """Reset daily baseline at 00:00 UTC."""
        self.current_equity = current_equity
        self.day_start_equity = current_equity
        if self.state in (CircuitState.DE_RISK, CircuitState.CIRCUIT_TRIP):
            self.state = CircuitState.NORMAL
            self.trip_reason = ""
            self.state_updated_at_ms = int(time.time() * 1000)

    def update_equity(self, current_equity: float) -> CircuitState:
        """Update equity and evaluate circuit thresholds."""
        self.current_equity = float(current_equity)
        if self.current_equity > self.peak_equity:
            self.peak_equity = self.current_equity

        # If already locked in SAFE_MODE, remain until manual reset
        if self.state == CircuitState.SAFE_MODE:
            return self.state

        # Calculate drawdowns
        daily_loss_pct = (
            (self.day_start_equity - self.current_equity) / self.day_start_equity
            if self.day_start_equity > 0
            else 0.0
        )
        hwm_drawdown_pct = (
            (self.peak_equity - self.current_equity) / self.peak_equity
            if self.peak_equity > 0
            else 0.0
        )

        # 1. Catastrophic HWM Drawdown -> SAFE_MODE
        if hwm_drawdown_pct >= self.config.max_hwm_drawdown_pct:
            self.state = CircuitState.SAFE_MODE
            self.trip_reason = f"Catastrophic HWM Drawdown: {hwm_drawdown_pct*100:.1f}% >= {self.config.max_hwm_drawdown_pct*100:.1f}%"
            self.state_updated_at_ms = int(time.time() * 1000)
            return self.state

        # 2. Daily Loss Limit -> CIRCUIT_TRIP
        if daily_loss_pct >= self.config.daily_halt_pct:
            self.state = CircuitState.CIRCUIT_TRIP
            self.trip_reason = f"Daily Loss Limit Tripped: {daily_loss_pct*100:.1f}% >= {self.config.daily_halt_pct*100:.1f}%"
            self.state_updated_at_ms = int(time.time() * 1000)
            return self.state

        # 3. Moderate Daily Loss -> DE_RISK
        if daily_loss_pct >= self.config.daily_derisk_pct:
            self.state = CircuitState.DE_RISK
            self.trip_reason = f"Daily De-Risk Threshold Tripped: {daily_loss_pct*100:.1f}% >= {self.config.daily_derisk_pct*100:.1f}%"
            self.state_updated_at_ms = int(time.time() * 1000)
            return self.state

        self.state = CircuitState.NORMAL
        self.trip_reason = ""
        return self.state

    def get_sizing_multiplier(self) -> float:
        """Returns the capital sizing multiplier allowed in current state."""
        if self.state in (CircuitState.CIRCUIT_TRIP, CircuitState.SAFE_MODE):
            return 0.0
        if self.state == CircuitState.DE_RISK:
            return self.config.derisk_size_multiplier
        return 1.0

    def manual_reset(self, authorized_by: str) -> None:
        """Explicit human/admin override to reset from SAFE_MODE or CIRCUIT_TRIP."""
        self.state = CircuitState.NORMAL
        self.trip_reason = f"Manually reset by {authorized_by}"
        self.day_start_equity = self.current_equity
        self.peak_equity = self.current_equity
        self.state_updated_at_ms = int(time.time() * 1000)
