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
    OPEN = "OPEN"
    CLOSED = "CLOSED"


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
    initial_stop_price: float = 0.0
    current_stop_price: float = 0.0
    target_price: float = 0.0         # HTF Destination >= 4R
    size: float = 0.0                 # Base units
    allocated_risk_pct: float = 0.01
    state: PositionState = PositionState.PENDING
    realized_pnl_usd: float = 0.0
    realized_r: float = 0.0
    entry_time: float = field(default_factory=time.time)
    exit_time: Optional[float] = None
    state_history: List[StateTransition] = field(default_factory=list)
    exit_reason: Optional[str] = None
    initial_risk_dollars: float = 0.0
    opened_at_timestamp: Optional[float] = None
    closed_at_timestamp: Optional[float] = None

    def __init__(
        self,
        position_id: str,
        symbol: str,
        direction: int,
        entry_price: float,
        target_price: float,
        size: float,
        initial_stop_price: Optional[float] = None,
        current_stop_price: Optional[float] = None,
        initial_stop: Optional[float] = None,
        current_stop: Optional[float] = None,
        allocated_risk_pct: float = 0.01,
        initial_risk_dollars: float = 0.0,
        opened_at_timestamp: Optional[float] = None,
        closed_at_timestamp: Optional[float] = None,
        entry_time: Optional[float] = None,
        exit_time: Optional[float] = None,
        state: Union[PositionState, str] = PositionState.PENDING,
        realized_pnl_usd: float = 0.0,
        realized_r: float = 0.0,
        state_history: Optional[List[StateTransition]] = None,
        exit_reason: Optional[str] = None,
    ):
        self.position_id = position_id
        self.symbol = symbol.upper()
        self.direction = int(direction)
        self.entry_price = float(entry_price)
        self.target_price = float(target_price)
        self.size = float(size)

        resolved_stop = initial_stop if initial_stop is not None else (initial_stop_price if initial_stop_price is not None else 0.0)
        self.initial_stop_price = float(resolved_stop)
        resolved_curr_stop = current_stop if current_stop is not None else (current_stop_price if current_stop_price is not None else self.initial_stop_price)
        self.current_stop_price = float(resolved_curr_stop)

        self.allocated_risk_pct = float(allocated_risk_pct)
        self.initial_risk_dollars = float(initial_risk_dollars)
        self.entry_time = float(entry_time) if entry_time is not None else (float(opened_at_timestamp) if opened_at_timestamp is not None else time.time())
        self.opened_at_timestamp = float(opened_at_timestamp) if opened_at_timestamp is not None else self.entry_time
        self.exit_time = float(exit_time) if exit_time is not None else (float(closed_at_timestamp) if closed_at_timestamp is not None else None)
        self.closed_at_timestamp = self.exit_time

        if isinstance(state, str):
            try:
                self.state = PositionState(state)
            except ValueError:
                self.state = PositionState.OPEN if state in ("OPEN", "ENTERED") else PositionState.CLOSED
        else:
            self.state = state

        self.realized_pnl_usd = float(realized_pnl_usd)
        self.realized_r = float(realized_r)
        self.state_history = list(state_history or [])
        self.exit_reason = exit_reason

    @property
    def initial_stop(self) -> float:
        return self.initial_stop_price

    @initial_stop.setter
    def initial_stop(self, val: float) -> None:
        self.initial_stop_price = val

    @property
    def current_stop(self) -> float:
        return self.current_stop_price

    @current_stop.setter
    def current_stop(self, val: float) -> None:
        self.current_stop_price = val

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

    def to_dict(self) -> Dict[str, Any]:
        """Serialize position to dictionary."""
        return {
            "position_id": self.position_id,
            "symbol": self.symbol,
            "direction": self.direction,
            "entry_price": self.entry_price,
            "initial_stop": self.initial_stop,
            "current_stop": self.current_stop,
            "initial_stop_price": self.initial_stop_price,
            "current_stop_price": self.current_stop_price,
            "target_price": self.target_price,
            "size": self.size,
            "initial_risk_dollars": self.initial_risk_dollars,
            "allocated_risk_pct": self.allocated_risk_pct,
            "opened_at_timestamp": self.opened_at_timestamp,
            "closed_at_timestamp": self.closed_at_timestamp,
            "entry_time": self.entry_time,
            "exit_time": self.exit_time,
            "state": self.state.value if isinstance(self.state, PositionState) else str(self.state),
            "realized_pnl_usd": self.realized_pnl_usd,
            "realized_r": self.realized_r,
            "exit_reason": self.exit_reason,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Position:
        """Construct position instance from serialized dictionary."""
        init_stop = data.get("initial_stop", data.get("initial_stop_price", 0.0))
        curr_stop = data.get("current_stop", data.get("current_stop_price", init_stop))
        st = data.get("state", PositionState.ENTERED)
        return cls(
            position_id=data["position_id"],
            symbol=data["symbol"],
            direction=int(data["direction"]),
            entry_price=float(data["entry_price"]),
            target_price=float(data["target_price"]),
            size=float(data["size"]),
            initial_stop=float(init_stop),
            current_stop=float(curr_stop),
            initial_risk_dollars=float(data.get("initial_risk_dollars", 0.0)),
            allocated_risk_pct=float(data.get("allocated_risk_pct", 0.01)),
            opened_at_timestamp=data.get("opened_at_timestamp", data.get("entry_time")),
            closed_at_timestamp=data.get("closed_at_timestamp", data.get("exit_time")),
            state=st,
            realized_pnl_usd=float(data.get("realized_pnl_usd", 0.0)),
            realized_r=float(data.get("realized_r", 0.0)),
            exit_reason=data.get("exit_reason"),
        )



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
