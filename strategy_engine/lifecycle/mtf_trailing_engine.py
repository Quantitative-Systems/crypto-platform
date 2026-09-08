"""
Product 02 — Strategy Engine: Causal MTF Structural Trailing Engine
Monitors active positions against causal MTF structure evolution:
1. Ratchets stop monotonically behind newly confirmed MTF swing lows (Longs) or swing highs (Shorts).
2. Includes both external protected swings and internal sequence swings to prevent stop-freezing.
3. Exits immediately on confirmed adverse MTF Change of Character (CHOCH).
4. Strictly eliminates arbitrary +1R profit locks and fixed breakeven ratchets.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple
from market_intelligence.primitives import MarketStatePayload, TrendDirection, SwingType
from strategy_engine.contracts.trade_plan import TradePlanPayload, DirectionalPermission
from strategy_engine.contracts.strategy_state import PositionState


@dataclass(frozen=True)
class TrailingDecision:
    should_update_stop: bool
    new_stop_price: Optional[float]
    should_exit_structural: bool
    exit_reason: Optional[str]
    rationale: str


class MTFStructuralTrailingEngine:
    """
    Independently testable MTF structural trailing model.
    """

    @staticmethod
    def evaluate(
        plan: TradePlanPayload,
        mtf_payload: MarketStatePayload,
        ltf_payload: Optional[MarketStatePayload] = None
    ) -> TrailingDecision:
        is_long = plan.directional_permission == DirectionalPermission.PERMIT_LONG.value
        current_sl = plan.stop_invalidation_price
        setup_ts = getattr(plan, 'setup_timestamp', 0)
        struct = mtf_payload.structure_state

        if not struct:
            return TrailingDecision(False, None, False, None, "NO_MTF_STRUCTURE_AVAILABLE")

        # -----------------------------------------------------------------
        # 1. Check MTF Structural Deterioration (Adverse CHOCH Exit)
        # -----------------------------------------------------------------
        mtf_events = getattr(struct, 'events', None) or mtf_payload.events or []
        for ev in reversed(mtf_events):
            ev_ts = getattr(ev, 'timestamp', 0)
            if ev_ts <= setup_ts:
                break
            ev_type = str(getattr(ev, 'event_type', ''))
            ev_dir = str(getattr(ev, 'direction', None) or (ev.metadata.get('direction', '') if hasattr(ev, 'metadata') else ''))

            if "CHOCH" in ev_type:
                # Adverse event: Bearish CHOCH during Long, or Bullish CHOCH during Short
                if is_long and "BEARISH" in ev_dir:
                    return TrailingDecision(
                        should_update_stop=False,
                        new_stop_price=None,
                        should_exit_structural=True,
                        exit_reason="MTF_ADVERSE_CHOCH_BEARISH_EXIT",
                        rationale=f"Exit triggered by causal MTF Bearish CHOCH at {ev_ts}"
                    )
                elif not is_long and "BULLISH" in ev_dir:
                    return TrailingDecision(
                        should_update_stop=False,
                        new_stop_price=None,
                        should_exit_structural=True,
                        exit_reason="MTF_ADVERSE_CHOCH_BULLISH_EXIT",
                        rationale=f"Exit triggered by causal MTF Bullish CHOCH at {ev_ts}"
                    )

        # -----------------------------------------------------------------
        # 2. Structural Ratchet behind Confirmed MTF Swings
        # -----------------------------------------------------------------
        new_sl_candidate = current_sl
        updated = False
        update_reason = "SL_MAINTAINED"

        # Check macro protected swing first
        prot_low = getattr(struct, 'protected_low', None)
        prot_high = getattr(struct, 'protected_high', None)
        if is_long and prot_low and getattr(prot_low, 'raw_swing', None):
            prot_low_p = prot_low.raw_swing.price
            if prot_low_p > new_sl_candidate:
                new_sl_candidate = prot_low_p
                updated = True
                update_reason = f"TRAILED_BEHIND_MTF_PROTECTED_LOW_{prot_low_p:.2f}"
        elif (not is_long) and prot_high and getattr(prot_high, 'raw_swing', None):
            prot_high_p = prot_high.raw_swing.price
            if prot_high_p < new_sl_candidate:
                new_sl_candidate = prot_high_p
                updated = True
                update_reason = f"TRAILED_BEHIND_MTF_PROTECTED_HIGH_{prot_high_p:.2f}"

        # Check all confirmed sequence swings (including internal pivots) to prevent freezing
        seq_swings = getattr(struct, 'sequence_swings', None) or []
        for seq in seq_swings:
            raw = getattr(seq, 'raw_swing', None)
            if not raw:
                continue
            conf_ts = getattr(raw, 'confirmation_timestamp', None) or raw.timestamp
            # Causality filter: swing confirmation must occur at or after trade setup
            if conf_ts < setup_ts:
                continue

            st = str(raw.swing_type)
            if is_long and ("LOW" in st):
                # New confirmed higher low
                if raw.price > new_sl_candidate and raw.price < (ltf_payload.current_price if ltf_payload else raw.price + 1.0):
                    new_sl_candidate = raw.price
                    updated = True
                    update_reason = f"TRAILED_BEHIND_MTF_SWING_LOW_{raw.price:.2f}"
            elif (not is_long) and ("HIGH" in st):
                # New confirmed lower high
                if raw.price < new_sl_candidate and raw.price > (ltf_payload.current_price if ltf_payload else raw.price - 1.0):
                    new_sl_candidate = raw.price
                    updated = True
                    update_reason = f"TRAILED_BEHIND_MTF_SWING_HIGH_{raw.price:.2f}"

        return TrailingDecision(
            should_update_stop=updated,
            new_stop_price=new_sl_candidate if updated else None,
            should_exit_structural=False,
            exit_reason=None,
            rationale=update_reason
        )
