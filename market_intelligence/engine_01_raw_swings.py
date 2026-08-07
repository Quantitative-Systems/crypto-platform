"""
Product 01: Sub-Engine 01 - Raw Swing Detection Engine (V4.3 Production)
Detects Confirmed & Candidate Swings, links Prev/Next Swing UUIDs, computes
Displacement & Quality Scores, and clusters multi-member EQH/EQL liquidity pools.
"""

from typing import List
from market_intelligence.primitives import Candle, RawSwing, SwingType, SwingStatus


class RawSwingEngine:

    def __init__(self, swing_lookback: int = 2, eq_tolerance_pct: float = 0.001):
        if swing_lookback < 1:
            raise ValueError("swing_lookback must be at least 1.")
        self.swing_lookback = swing_lookback
        self.eq_tolerance_pct = eq_tolerance_pct

    def detect_raw_swings(self, candles: List[Candle], timeframe: str = "1D") -> List[RawSwing]:
        """
        Detects Raw Swings with UUIDs, Prev/Next links, Displacement, Quality Scores,
        and multi-member EQH/EQL clusters.
        """
        n = len(candles)
        if n < (self.swing_lookback + 1):
            return []

        swings: List[RawSwing] = []

        # 1. Detection Phase
        for i in range(self.swing_lookback, n):
            current = candles[i]
            left = candles[i - self.swing_lookback:i]
            right = candles[i + 1:min(i + 1 + self.swing_lookback, n)]

            check_high = all(current.high >= c.high for c in left)
            check_low = all(current.low <= c.low for c in left)

            # Swing High Evaluation
            if check_high and len(right) > 0:
                if all(current.high > c.high for c in right):
                    is_fully_confirmed = (i + self.swing_lookback) < n
                    status = SwingStatus.CONFIRMED if is_fully_confirmed else SwingStatus.CANDIDATE
                    conf_index = (i + self.swing_lookback) if is_fully_confirmed else (n - 1)

                    right_min = min((c.low for c in right), default=current.low)
                    disp_pct = ((current.high - right_min) / current.high) * 100.0

                    wick_ratio = current.body_range / current.range if current.range > 0 else 0.5
                    quality = min(100.0, max(20.0, (disp_pct * 20.0) + (wick_ratio * 40.0) + 40.0))

                    s_id = f"SW_HIGH_{i}_{current.high:.2f}"

                    swings.append(RawSwing(
                        swing_id=s_id,
                        timestamp=current.timestamp,
                        price=current.high,
                        swing_type=SwingType.SWING_HIGH,
                        candle_index=i,
                        timeframe=timeframe,
                        status=status,
                        displacement_pct=round(disp_pct, 4),
                        quality_score=round(quality, 2),
                        confidence_score=95.0 if status == SwingStatus.CONFIRMED else 60.0,
                        fractal_strength=float(self.swing_lookback),
                        confirmation_candle_index=conf_index
                    ))

            # Swing Low Evaluation
            if check_low and len(right) > 0:
                if all(current.low < c.low for c in right):
                    is_fully_confirmed = (i + self.swing_lookback) < n
                    status = SwingStatus.CONFIRMED if is_fully_confirmed else SwingStatus.CANDIDATE
                    conf_index = (i + self.swing_lookback) if is_fully_confirmed else (n - 1)

                    right_max = max((c.high for c in right), default=current.high)
                    disp_pct = ((right_max - current.low) / current.low) * 100.0

                    wick_ratio = current.body_range / current.range if current.range > 0 else 0.5
                    quality = min(100.0, max(20.0, (disp_pct * 20.0) + (wick_ratio * 40.0) + 40.0))

                    s_id = f"SW_LOW_{i}_{current.low:.2f}"

                    swings.append(RawSwing(
                        swing_id=s_id,
                        timestamp=current.timestamp,
                        price=current.low,
                        swing_type=SwingType.SWING_LOW,
                        candle_index=i,
                        timeframe=timeframe,
                        status=status,
                        displacement_pct=round(disp_pct, 4),
                        quality_score=round(quality, 2),
                        confidence_score=95.0 if status == SwingStatus.CONFIRMED else 60.0,
                        fractal_strength=float(self.swing_lookback),
                        confirmation_candle_index=conf_index
                    ))

        # 2. Relational Linkage Phase (Prev / Next Swing UUIDs)
        for idx in range(len(swings)):
            if idx > 0:
                swings[idx].prev_swing_id = swings[idx - 1].swing_id
            if idx < len(swings) - 1:
                swings[idx].next_swing_id = swings[idx + 1].swing_id

        # 3. EQH / EQL Multi-Member Clustering Phase
        self._assign_clusters(swings)

        return swings

    def _assign_clusters(self, swings: List[RawSwing]):
        """Groups swings with near-identical prices into multi-member liquidity clusters."""
        highs = [s for s in swings if s.swing_type == SwingType.SWING_HIGH]
        lows = [s for s in swings if s.swing_type == SwingType.SWING_LOW]

        for s_list, prefix in [(highs, "CLUST_EQH"), (lows, "CLUST_EQL")]:
            visited = set()
            for i in range(len(s_list)):
                if s_list[i].swing_id in visited:
                    continue

                cluster_group = [s_list[i]]
                for j in range(i + 1, len(s_list)):
                    price_diff_pct = abs(s_list[i].price - s_list[j].price) / s_list[i].price
                    if price_diff_pct <= self.eq_tolerance_pct:
                        cluster_group.append(s_list[j])

                if len(cluster_group) > 1:
                    cluster_id = f"{prefix}_{s_list[i].candle_index}"
                    count = len(cluster_group)
                    for member in cluster_group:
                        member.is_equal_extreme = True
                        member.cluster_id = cluster_id
                        member.cluster_member_count = count
                        visited.add(member.swing_id)