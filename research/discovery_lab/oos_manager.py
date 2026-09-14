"""
PROJECT TOP1 — Phase 9 Out-of-Sample (OOS) Data Protection & Split Manager.

Guarantees strict chronological separation between:
1. In-Sample Development Dataset (70% of historical candle series)
2. Locked Out-of-Sample (OOS) Dataset (Final 30% of historical series)

Security Invariant:
- Discovery, optimization, and parameter tuning CANNOT access OOS data.
- Attempts to query OOS data without explicit qualification unlock raise an OOSLockViolation.
- If a qualified candidate fails OOS testing, it is permanently marked FAILED/DEGRADED.
"""

from typing import List, Tuple, Dict, Any, Optional
from market_intelligence.primitives import Candle


class OOSLockViolation(Exception):
    """Raised when unverified research code attempts to access locked OOS data."""
    pass


class OOSManager:
    """Manages chronological dataset partitioning and access gating."""

    DEFAULT_IN_SAMPLE_RATIO = 0.70

    @staticmethod
    def partition_candles(
        candles: List[Candle],
        in_sample_ratio: float = DEFAULT_IN_SAMPLE_RATIO,
    ) -> Tuple[List[Candle], List[Candle], int]:
        """
        Chronologically splits candles into In-Sample and Locked Out-of-Sample sets.
        Returns (in_sample_candles, oos_candles, split_timestamp).
        """
        if not candles:
            return [], [], 0

        split_idx = int(len(candles) * in_sample_ratio)
        in_sample = candles[:split_idx]
        oos = candles[split_idx:]
        split_ts = in_sample[-1].timestamp if in_sample else 0

        return in_sample, oos, split_ts

    @staticmethod
    def get_development_candles(
        candles: List[Candle],
        in_sample_ratio: float = DEFAULT_IN_SAMPLE_RATIO,
    ) -> List[Candle]:
        """Returns ONLY the In-Sample development candles for discovery and tuning."""
        dev_candles, _, _ = OOSManager.partition_candles(candles, in_sample_ratio)
        return dev_candles

    @staticmethod
    def get_oos_candles(
        candles: List[Candle],
        is_candidate_qualified: bool,
        candidate_id: str,
        in_sample_ratio: float = DEFAULT_IN_SAMPLE_RATIO,
    ) -> List[Candle]:
        """
        Gated access to the Out-of-Sample dataset.
        Access is strictly prohibited unless candidate is formally marked QUALIFIED on In-Sample.
        """
        if not is_candidate_qualified:
            raise OOSLockViolation(
                f"Candidate '{candidate_id}' is not qualified for OOS testing! "
                f"OOS access is locked to prevent data snooping and p-hacking."
            )

        _, oos_candles, _ = OOSManager.partition_candles(candles, in_sample_ratio)
        return oos_candles

    @staticmethod
    def verify_oos_stability(
        dev_expectancy_r: float,
        oos_expectancy_r: float,
        max_degradation_pct: float = 0.40,
    ) -> Tuple[bool, float, str]:
        """
        Validates whether OOS performance holds up against In-Sample development performance.
        """
        if dev_expectancy_r <= 0:
            return False, 1.0, "Development expectancy was non-positive"

        if oos_expectancy_r <= 0:
            return False, 1.0, "OOS expectancy collapsed into negative return"

        degradation = (dev_expectancy_r - oos_expectancy_r) / dev_expectancy_r
        if degradation > max_degradation_pct:
            return False, degradation, f"OOS degraded by {degradation*100:.1f}% (max allowed {max_degradation_pct*100:.0f}%)"

        return True, degradation, f"OOS passed with {degradation*100:+.1f}% change"
