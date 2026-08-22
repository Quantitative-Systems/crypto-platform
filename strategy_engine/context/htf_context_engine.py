"""
Product 02 — Strategy Engine: HTF Context Engine
Extracts macro structure, expected move (PULLBACK vs CONTINUATION), structural targets,
and keylevels from HTF MarketStatePayload.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Any

from market_intelligence.primitives import (
    MarketStatePayload,
    TrendDirection,
    MarketPhase,
    SequenceSwing,
    StructureEvent,
    EQHLiquidityPool,
    KeyZone
)
from strategy_engine.contracts.trade_plan import DirectionalPermission




@dataclass(frozen=True)
class HTFContext:
    """
    Explicit, structured representation of the HTF decision state.
    """
    context_id: str
    timestamp: int
    symbol: str
    timeframe: str
    
    # Direction & Phase
    macro_direction: TrendDirection
    market_phase: Optional[MarketPhase]
    protected_swing: Optional[SequenceSwing]
    weak_swing: Optional[SequenceSwing]
    target_anchor_price: Optional[float]
    
    # Valuation & Keylevels
    valuation_state: str  # PREMIUM, DISCOUNT, EQUILIBRIUM
    active_keyzones: List[KeyZone] = field(default_factory=list)
    liquidity_pools: List[EQHLiquidityPool] = field(default_factory=list)
    last_event: Optional[StructureEvent] = None
    structural_epoch: int = 0


class HTFContextEngine:
    """
    Analyzes HTF market state to classify whether the expected move is PULLBACK or CONTINUATION,
    and identifies structural targets and invalidation boundaries.
    """

    @staticmethod
    def evaluate(htf_payload: MarketStatePayload) -> HTFContext:
        trend = htf_payload.trend_state or TrendDirection.NEUTRAL
        phase = htf_payload.phase_state
        phase_str = str(phase) if phase is not None else ""
        valuation = htf_payload.valuation_state or "EQUILIBRIUM"
        symbol = htf_payload.symbol
        ts = htf_payload.timestamp
        context_id = f"htf_{symbol}_{ts}"

        struct = htf_payload.structure_state
        prot_swing = None
        weak_swing = None
        target_price = None
        # 1. BULLISH Macro Structure
        if trend == TrendDirection.BULLISH:
            prot_swing = struct.protected_low if struct else None
            weak_swing = struct.weak_high if struct else None
            if weak_swing and weak_swing.raw_swing:
                target_price = weak_swing.raw_swing.price

        # 2. BEARISH Macro Structure
        elif trend == TrendDirection.BEARISH:
            prot_swing = struct.protected_high if struct else None
            weak_swing = struct.weak_low if struct else None
            if weak_swing and weak_swing.raw_swing:
                target_price = weak_swing.raw_swing.price

        # Last structure event
        last_event = None
        if struct and struct.events:
            last_event = struct.events[-1]

        return HTFContext(
            context_id=context_id,
            timestamp=ts,
            symbol=symbol,
            timeframe=htf_payload.timeframe,
            macro_direction=trend,
            market_phase=phase,
            protected_swing=prot_swing,
            weak_swing=weak_swing,
            target_anchor_price=target_price,
            valuation_state=valuation,
            active_keyzones=list(htf_payload.keyzones or []),
            liquidity_pools=list(htf_payload.liquidity_pools or []),
            last_event=last_event,
            structural_epoch=getattr(struct, 'structural_epoch', 0) if struct else 0
        )
