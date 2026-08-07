"""
Product 01: Sub-Engine 02 - Sequence Engine
Transforms independent raw swings into a structured SequenceState container.
"""

from typing import List
from market_intelligence.primitives import (
    RawSwing, SwingType, SequenceSwing, SequenceLabel, SequenceState
)

class SequenceEngine:

    @staticmethod
    def assign_sequences(raw_swings: List[RawSwing]) -> SequenceState:
        """
        Single O(n) pass returning SequenceState with terminal high/low accessors.
        """
        if not raw_swings:
            return SequenceState(sequence_swings=[], total_swings=0)

        sequence_swings: List[SequenceSwing] = []
        last_high = None
        last_low = None
        last_hh = None
        last_hl = None

        for raw in raw_swings:
            if raw.swing_type == SwingType.SWING_HIGH:
                if last_high is None:
                    label = SequenceLabel.UNKNOWN
                elif raw.price > last_high.price:
                    label = SequenceLabel.HH
                elif raw.price < last_high.price:
                    label = SequenceLabel.LH
                else:
                    label = SequenceLabel.EQH
                
                seq_swing = SequenceSwing(raw_swing=raw, label=label)
                if label == SequenceLabel.HH:
                    last_hh = seq_swing
                last_high = seq_swing

            else:  # SWING_LOW
                if last_low is None:
                    label = SequenceLabel.UNKNOWN
                elif raw.price > last_low.price:
                    label = SequenceLabel.HL
                elif raw.price < last_low.price:
                    label = SequenceLabel.LL
                else:
                    label = SequenceLabel.EQL
                
                seq_swing = SequenceSwing(raw_swing=raw, label=label)
                if label == SequenceLabel.HL:
                    last_hl = seq_swing
                last_low = seq_swing

            sequence_swings.append(seq_swing)

        return SequenceState(
            sequence_swings=sequence_swings,
            latest_high=last_high,
            latest_low=last_low,
            latest_higher_high=last_hh,
            latest_higher_low=last_hl,
            total_swings=len(sequence_swings)
        )