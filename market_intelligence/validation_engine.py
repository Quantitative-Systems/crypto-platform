"""
APEX Quantitative Systems Platform
Product 01 — Market Language | Engine 7 — Validation Engine

PURPOSE
-------
Evaluates raw outputs from Engines 1–6 to determine the quantitative quality
of the market structure setup. 

SEMANTIC CONTRACT
-----------------
1. Pure validation function.
2. Generates qualitative reason codes and a quantitative score.
3. Does not modify underlying structures.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List

from market_intelligence.primitives import Candle, RawSwing, StructureState, KeyZone


class ValidationStatus(Enum):
    VALID = "VALID"
    INVALID = "INVALID"


@dataclass(frozen=True)
class ValidationResult:
    status: ValidationStatus
    score: float
    reason_codes: List[str] = field(default_factory=list)


class ValidationEngine:
    """
    Evaluates body-to-wick ratios, displacement velocity, ATR thresholds,
    BOS distance, and KeyZone mitigation quality.
    """

    def evaluate(
        self,
        candles: List[Candle],
        swings: List[RawSwing],
        structure_state: StructureState,
        keyzones: List[KeyZone],
    ) -> ValidationResult:
        reasons = []
        passed_flags = 0
        total_flags = 5

        # 1. Body-to-wick ratio (using the latest candle)
        if candles:
            latest = candles[-1]
            body = abs(latest.close - latest.open)
            total = latest.high - latest.low
            if total > 0 and (body / total) > 0.5:
                passed_flags += 1
                reasons.append("BODY_RATIO_SUFFICIENT")
            else:
                reasons.append("INSUFFICIENT_BODY_RATIO")
        else:
            reasons.append("NO_CANDLES_PROVIDED")

        # 2. Displacement velocity
        if len(candles) >= 2:
            prev = candles[-2]
            latest = candles[-1]
            move = abs(latest.close - prev.close)
            
            # Use basic threshold: moving at least 0.1% for demonstration
            ref_price = prev.close if prev.close > 0 else 1.0
            if (move / ref_price) > 0.001:
                passed_flags += 1
                reasons.append("DISPLACEMENT_CONFIRMED")
            else:
                reasons.append("INSUFFICIENT_DISPLACEMENT")
        else:
            reasons.append("INSUFFICIENT_DISPLACEMENT_DATA")

        # 3. ATR threshold
        if len(candles) >= 14:
            tr_sum = sum(c.high - c.low for c in candles[-14:])
            atr = tr_sum / 14
            
            # Require ATR to be more than 0.05% of price
            latest = candles[-1]
            ref_price = latest.close if latest.close > 0 else 1.0
            if (atr / ref_price) > 0.0005:
                passed_flags += 1
                reasons.append("ATR_THRESHOLD_MET")
            else:
                reasons.append("ATR_TOO_LOW")
        else:
            reasons.append("INSUFFICIENT_ATR_DATA")

        # 4. BOS distance
        if hasattr(structure_state, 'events') and structure_state.events and "BOS" in str(structure_state.events[-1].event_type):
            passed_flags += 1
            reasons.append("BOS_CONFIRMED")
        elif hasattr(structure_state, 'last_event') and structure_state.last_event and "BOS" in str(structure_state.last_event.event_type):
            passed_flags += 1
            reasons.append("BOS_CONFIRMED")
        else:
            reasons.append("NO_RECENT_BOS")

        # 5. KeyZone mitigation quality
        mitigated = [kz for kz in keyzones if getattr(kz, 'is_mitigated', False) or (hasattr(kz, 'status') and 'MITIGATED' in str(getattr(kz, 'status')))]
        if mitigated:
            passed_flags += 1
            reasons.append("KEYZONE_MITIGATION_VALID")
        else:
            reasons.append("NO_MITIGATED_KEYZONE")

        score = passed_flags / total_flags
        status = ValidationStatus.VALID if score == 1.0 else ValidationStatus.INVALID

        return ValidationResult(
            status=status,
            score=score,
            reason_codes=reasons,
        )
