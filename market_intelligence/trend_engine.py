"""
APEX Quantitative Systems Platform
Product 01 — Market Language | Engine 6 — Trend Engine

PURPOSE
-------
Evaluates the directional trend state and health based on structural events
and market phase context.

SEMANTIC CONTRACT
-----------------
1. Pure function that derives TrendState deterministically.
2. Relies solely on StructureState and PhaseState.
3. Zero trading signals, only market ontology.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List

from market_intelligence.primitives import StructureState, TrendDirection
from market_intelligence.phase_engine import PhaseState, MarketPhase


class TrendHealth(Enum):
    STRONG = "STRONG"
    WEAKENING = "WEAKENING"
    EXHAUSTED = "EXHAUSTED"


@dataclass(frozen=True)
class TrendState:
    direction: TrendDirection
    health: TrendHealth
    causal_evidence: List[str] = field(default_factory=list)


class TrendEngine:
    """
    Deterministic Trend Evaluator.
    Combines StructureState (Engine 2) and PhaseState (Engine 5) to emit TrendState.
    """

    def evaluate(
        self, structure_state: StructureState, phase_state: PhaseState
    ) -> TrendState:
        # 1. Base direction comes directly from StructureState's external trend
        direction = structure_state.external_trend

        # 2. Derive causal evidence from structure
        evidence = []
        if hasattr(structure_state, 'broken_protected_swing_id') and getattr(structure_state, 'broken_protected_swing_id'):
            evidence.append(structure_state.broken_protected_swing_id)
            
        if hasattr(structure_state, 'events') and structure_state.events:
            for event in reversed(structure_state.events):
                if "CHOCH" in str(event.event_type):
                    if hasattr(event, 'broken_swing_id'):
                        evidence.append(event.broken_swing_id)
                    break

        
        # Add anchors to evidence
        if direction == TrendDirection.BULLISH and structure_state.protected_low:
            evidence.append(structure_state.protected_low.raw_swing.swing_id)
        elif direction == TrendDirection.BEARISH and structure_state.protected_high:
            evidence.append(structure_state.protected_high.raw_swing.swing_id)

        # 3. Assess Health based on swings and phases
        health = TrendHealth.STRONG

        if direction == TrendDirection.BULLISH:
            if phase_state.current_phase in (MarketPhase.PULLBACK, MarketPhase.COMPRESSION):
                health = TrendHealth.WEAKENING
            elif phase_state.current_phase in (MarketPhase.DISTRIBUTION, MarketPhase.REVERSAL):
                health = TrendHealth.EXHAUSTED
            elif structure_state.protected_low and not structure_state.protected_low.is_strong:
                health = TrendHealth.WEAKENING
        
        elif direction == TrendDirection.BEARISH:
            if phase_state.current_phase in (MarketPhase.PULLBACK, MarketPhase.COMPRESSION):
                health = TrendHealth.WEAKENING
            elif phase_state.current_phase in (MarketPhase.ACCUMULATION, MarketPhase.REVERSAL):
                health = TrendHealth.EXHAUSTED
            elif structure_state.protected_high and not structure_state.protected_high.is_strong:
                health = TrendHealth.WEAKENING
        else:
            # RANGING or NEUTRAL
            direction = TrendDirection.RANGING
            if phase_state.current_phase in (MarketPhase.ACCUMULATION, MarketPhase.DISTRIBUTION):
                health = TrendHealth.EXHAUSTED
            else:
                health = TrendHealth.WEAKENING

        return TrendState(
            direction=direction,
            health=health,
            causal_evidence=evidence
        )
