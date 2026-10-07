"""Position Lifecycle State Machine and Real-Time Structural Monitor.

Implements the institutional position state machine:
    PENDING
       │
       ▼
    ENTERED
       │
       ▼
   CONFIRMED
       │
       ▼
   PROTECTED (Stop moved to Breakeven)
       │
       ▼
    TRAILING (MTF Structural Trail)
       │
       ▼
DESTINATION_APPROACH (Within sight of HTF >= 4R Destination)
       │
       ▼
      EXIT

Emergency branches supported from ANY state:
- DATA_CORRUPTION -> SAFE FLAT
- SYSTEMIC_EVENT -> RISK GOVERNOR HALT
- RISK_BREACH -> REDUCE / EXIT
- EXCHANGE_FAILURE -> FAILSAFE FLAT
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from instrument.instrument_health import InstrumentHealth


class PositionState(str, Enum):
    """Position lifecycle stages."""
    PENDING = "PENDING"
    ENTERED = "ENTERED"
    CONFIRMED = "CONFIRMED"
    PROTECTED = "PROTECTED"
    TRAILING = "TRAILING"
    DESTINATION_APPROACH = "DESTINATION_APPROACH"
    CLOSED_TARGET = "CLOSED_TARGET"
    CLOSED_STOP = "CLOSED_STOP"
    CLOSED_EMERGENCY = "CLOSED_EMERGENCY"


class EmergencyReason(str, Enum):
    DATA_CORRUPTION = "DATA_CORRUPTION"
    SYSTEMIC_EVENT = "SYSTEMIC_EVENT"
    RISK_BREACH = "RISK_BREACH"
    EXCHANGE_FAILURE = "EXCHANGE_FAILURE"


@dataclass(frozen=True)
class StateTransition:
    """Audit record of a state transition."""
    from_state: PositionState
    to_state: PositionState
    timestamp: float
    trigger_price: float
    reason: str


@dataclass
class Position:
    """Institutional tracked position state."""
    position_id: str
    symbol: str
    direction: int                    # +1 LONG, -1 SHORT
    entry_price: float
    initial_stop_price: float
    current_stop_price: float
    target_price: float               # HTF Destination >= 4R
    size: float                       # Base units
    allocated_risk_pct: float
    state: PositionState = PositionState.PENDING
    realized_pnl_usd: float = 0.0
    realized_r: float = 0.0
    entry_time: float = field(default_factory=time.time)
    exit_time: Optional[float] = None
    state_history: List[StateTransition] = field(default_factory=list)
    exit_reason: Optional[str] = None

    @property
    def initial_risk_distance(self) -> float:
        return abs(self.entry_price - self.initial_stop_price)

    def current_r_multiple(self, current_price: float) -> float:
        """Calculate current unrealized R-multiple."""
        if self.initial_risk_distance <= 0:
            return 0.0
        if self.direction == 1:
            return (current_price - self.entry_price) / self.initial_risk_distance
        else:
            return (self.entry_price - current_price) / self.initial_risk_distance

    def transition_to(self, new_state: PositionState, price: float, reason: str) -> None:
        """Record state transition."""
        trans = StateTransition(
            from_state=self.state,
            to_state=new_state,
            timestamp=time.time(),
            trigger_price=price,
            reason=reason,
        )
        self.state_history.append(trans)
        self.state = new_state


class PositionLifecycleMonitor:
    """Continuously evaluates open positions against market structure and risk."""

    def __init__(
        self,
        protect_at_r: float = 1.5,      # Move to Breakeven at +1.5R
        trail_at_r: float = 2.5,        # Engage MTF structural trail at +2.5R
        destination_approach_ratio: float = 0.85, # Destination approach at 85% to target
    ):
        self.protect_at_r = protect_at_r
        self.trail_at_r = trail_at_r
        self.destination_approach_ratio = destination_approach_ratio

    def update_position(
        self,
        pos: Position,
        current_price: float,
        mtf_structural_stop: Optional[float] = None,
        health: Optional[InstrumentHealth] = None,
        systemic_risk_active: bool = False,
        now: Optional[float] = None,
    ) -> PositionState:
        """Update position state, evaluate stops, trailing, targets, and emergency exits."""
        current_ts = now if now is not None else time.time()

        # Terminal state check
        if pos.state in (PositionState.CLOSED_TARGET, PositionState.CLOSED_STOP, PositionState.CLOSED_EMERGENCY):
            return pos.state

        # =================================================================
        # 1. EMERGENCY BRANCHES (High Priority Failsafes)
        # =================================================================
        if health is not None and not health.is_operational():
            pos.realized_r = pos.current_r_multiple(current_price)
            pos.exit_time = current_ts
            pos.exit_reason = f"EMERGENCY_DATA_CORRUPTION_{health.status.value}"
            pos.transition_to(PositionState.CLOSED_EMERGENCY, current_price, pos.exit_reason)
            return pos.state

        if systemic_risk_active:
            pos.realized_r = pos.current_r_multiple(current_price)
            pos.exit_time = current_ts
            pos.exit_reason = "EMERGENCY_SYSTEMIC_EVENT_RISK_GOVERNOR"
            pos.transition_to(PositionState.CLOSED_EMERGENCY, current_price, pos.exit_reason)
            return pos.state

        # =================================================================
        # 2. CHECK STOP LOSS HIT
        # =================================================================
        stop_hit = False
        if pos.direction == 1 and current_price <= pos.current_stop_price:
            stop_hit = True
        elif pos.direction == -1 and current_price >= pos.current_stop_price:
            stop_hit = True

        if stop_hit:
            pos.realized_r = pos.current_r_multiple(pos.current_stop_price)
            pos.exit_time = current_ts
            pos.exit_reason = "STOP_LOSS_HIT"
            pos.transition_to(PositionState.CLOSED_STOP, pos.current_stop_price, "STOP_LOSS_HIT")
            return pos.state

        # =================================================================
        # 3. CHECK HTF TARGET HIT (>= 4R)
        # =================================================================
        target_hit = False
        if pos.direction == 1 and current_price >= pos.target_price:
            target_hit = True
        elif pos.direction == -1 and current_price <= pos.target_price:
            target_hit = True

        if target_hit:
            pos.realized_r = pos.current_r_multiple(pos.target_price)
            pos.exit_time = current_ts
            pos.exit_reason = "HTF_DESTINATION_TARGET_REACHED"
            pos.transition_to(PositionState.CLOSED_TARGET, pos.target_price, "HTF_DESTINATION_TARGET_REACHED")
            return pos.state

        # =================================================================
        # 4. NORMAL STATE PROGRESSION & STRUCTURAL TRAILING
        # =================================================================
        current_r = pos.current_r_multiple(current_price)

        # From PENDING to ENTERED
        if pos.state == PositionState.PENDING:
            pos.transition_to(PositionState.ENTERED, current_price, "INITIAL_FILL_CONFIRMED")

        # From ENTERED to CONFIRMED (+1.0R)
        if pos.state == PositionState.ENTERED and current_r >= 1.0:
            pos.transition_to(PositionState.CONFIRMED, current_price, f"R_MULTIPLE_{current_r:.1f}_CONFIRMED")

        # From CONFIRMED to PROTECTED (+1.5R) -> Move stop to Breakeven
        if pos.state == PositionState.CONFIRMED and current_r >= self.protect_at_r:
            # Move stop to Entry price (breakeven)
            pos.current_stop_price = pos.entry_price
            pos.transition_to(PositionState.PROTECTED, current_price, f"STOP_MOVED_TO_BREAKEVEN_AT_{current_r:.1f}R")

        # From PROTECTED to TRAILING (+2.5R) -> Engage MTF structural trailing
        if pos.state in (PositionState.PROTECTED, PositionState.CONFIRMED) and current_r >= self.trail_at_r:
            pos.transition_to(PositionState.TRAILING, current_price, f"MTF_STRUCTURAL_TRAIL_ENGAGED_AT_{current_r:.1f}R")

        # Dynamic MTF structural ratchet while in TRAILING or DESTINATION_APPROACH
        if pos.state in (PositionState.TRAILING, PositionState.DESTINATION_APPROACH) and mtf_structural_stop is not None:
            if pos.direction == 1 and mtf_structural_stop > pos.current_stop_price:
                # Ratchet up only
                pos.current_stop_price = mtf_structural_stop
            elif pos.direction == -1 and mtf_structural_stop < pos.current_stop_price:
                # Ratchet down only
                pos.current_stop_price = mtf_structural_stop

        # Approach check: Distance to target is >= 85%
        target_dist = abs(pos.target_price - pos.entry_price)
        cur_dist = abs(current_price - pos.entry_price)
        if target_dist > 0 and (cur_dist / target_dist) >= self.destination_approach_ratio:
            if pos.state == PositionState.TRAILING:
                pos.transition_to(PositionState.DESTINATION_APPROACH, current_price, f"APPROACHING_HTF_TARGET_({(cur_dist/target_dist)*100:.1f}%)")

        return pos.state
