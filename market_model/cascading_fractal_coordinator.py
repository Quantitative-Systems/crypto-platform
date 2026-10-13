"""Cascading Fractal Strategy Coordinator.

Unifies all 5 timeframe sets into a single, correlated, top-down cascading
decision and execution engine:

    Set 1: 1M (HTF) -> 1w (MTF) -> 1d (LTF)
    Set 2: 1w (HTF) -> 1d (MTF) -> 4h (LTF)
    Set 3: 1d (HTF) -> 4h (MTF) -> 1h (LTF)
    Set 4: 4h (HTF) -> 1h (MTF) -> 15m (LTF)
    Set 5: 1h (HTF) -> 15m (MTF) -> 3m (LTF)

The 5 sets are NOT independent strategies; they are fractally coupled gears:
1. Macro Dealing Range (1M / 1w): Determines whether price is in Premium (>50%)
   or Discount (<50%) relative to the dealing range.
   - Deep Premium (>70%): Authorizes Macro PULLBACK phase (hunt shorts into discount).
   - Deep Discount (<30%): Authorizes Macro CONTINUATION or PULLBACK-BUY phase.
2. The Baton Transmission:
   - Macro Phase sets the Directional Authorization Baton.
   - Intermediate sets (1w, 1d, 4h) confirm the structural shift (CHoCH / BOS).
   - Micro sets (1h, 15m, 3m) are STRICTLY PERMISSION-LOCKED. They cannot take
     counter-trend noise trades. They only fire precision entries in alignment
     with the macro baton.
3. Asymmetric 3-Tier Execution:
   - Initial Stop Loss: Local LTF structural swing / invalidation level.
   - Trailing Stop: Ratchets monotonically behind confirmed MTF structural swings.
   - Target Objective: Macro HTF destination liquidity / opposing key zone (>= 4.0R).
   - Position Sizing: 1.0% account risk dynamically sized to the LTF stop distance.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from market_model.contracts import (
    MarketPhaseType,
    MarketState,
    StructuralBreakType,
    TrendDirection,
)
from market_model.state_generator import MarketStateGenerator


class MacroPhaseBaton(str, Enum):
    BULLISH_EXPANSION = "BULLISH_EXPANSION"     # Trending long in discount/equilibrium
    BEARISH_PULLBACK = "BEARISH_PULLBACK"       # In premium, hunting pullback short to demand
    BEARISH_EXPANSION = "BEARISH_EXPANSION"     # Trending short in premium/equilibrium
    BULLISH_PULLBACK = "BULLISH_PULLBACK"       # In discount, hunting pullback long to supply
    NEUTRAL_CONSOLIDATION = "NEUTRAL"           # Awaiting clear structural break


@dataclass
class CascadingSignalCandidate:
    bar_index: int
    timestamp_ms: int
    symbol: str
    origin_set: str
    direction: int                              # 1 = Long, -1 = Short
    entry_price: float
    stop_price: float
    target_price: float
    target_r: float
    macro_baton: MacroPhaseBaton
    risk_dist: float
    reward_dist: float
    position_size_usd: float = 0.0              # Dynamic 1% risk position size
    meta: Dict[str, Any] = field(default_factory=dict)


class CascadingFractalCoordinator:
    """Universal Top-Down Multi-Timeframe State Machine."""

    TIMEFRAME_SETS = {
        "SET_1": {"htf": "1M", "mtf": "1w", "ltf": "1d"},
        "SET_2": {"htf": "1w", "mtf": "1d", "ltf": "4h"},
        "SET_3": {"htf": "1d", "mtf": "4h", "ltf": "1h"},
        "SET_4": {"htf": "4h", "mtf": "1h", "ltf": "15m"},
        "SET_5": {"htf": "1h", "mtf": "15m", "ltf": "3m"},
    }

    def __init__(
        self,
        min_target_r: float = 4.0,
        risk_per_trade_pct: float = 0.01,       # 1.0% account risk
        account_equity_usd: float = 100_000.0,
        deep_premium_threshold: float = 0.65,   # Above 65% dealing range = Premium
        deep_discount_threshold: float = 0.35,  # Below 35% dealing range = Discount
    ):
        self.min_target_r = min_target_r
        self.risk_per_trade_pct = risk_per_trade_pct
        self.account_equity_usd = account_equity_usd
        self.deep_premium_threshold = deep_premium_threshold
        self.deep_discount_threshold = deep_discount_threshold

        # Dedicated generators per timeframe
        self.generators = {
            tf: MarketStateGenerator(timeframe=tf)
            for tf in ["1M", "1w", "1d", "4h", "1h", "15m", "3m"]
        }
        self._macro_cache: Dict[Tuple[str, str, int], Tuple[MacroPhaseBaton, Optional[float], Optional[float]]] = {}

    def evaluate_macro_baton(
        self,
        symbol: str,
        current_ts: int,
        all_data: Dict[str, Dict[str, np.ndarray]],
    ) -> Tuple[MacroPhaseBaton, Optional[float], Optional[float]]:
        """Evaluate 1M and 1W macro dealing range to determine the directional baton.
        
        Returns:
            baton: Active macro authorization phase.
            macro_demand_target: HTF demand level (for pullbacks/continuations).
            macro_supply_target: HTF supply level (for pullbacks/continuations).
        """
        # 1. Evaluate 1M if available, else fallback to 1W
        macro_tf = "1M" if "1M" in all_data and len(all_data["1M"]["c"]) >= 10 else "1w"
        if macro_tf not in all_data or len(all_data[macro_tf]["c"]) < 10:
            return MacroPhaseBaton.NEUTRAL_CONSOLIDATION, None, None

        m_data = all_data[macro_tf]
        m_idx = np.searchsorted(m_data["close_ts"], current_ts, side="right") - 1
        if m_idx < 5:
            return MacroPhaseBaton.NEUTRAL_CONSOLIDATION, None, None

        cache_key = (symbol, macro_tf, m_idx)
        if cache_key in self._macro_cache:
            return self._macro_cache[cache_key]

        m_start = max(0, m_idx - 100)
        m_state = self.generators[macro_tf].generate(
            symbol=symbol,
            opens=m_data["o"][m_start : m_idx + 1],
            highs=m_data["h"][m_start : m_idx + 1],
            lows=m_data["l"][m_start : m_idx + 1],
            closes=m_data["c"][m_start : m_idx + 1],
            volumes=m_data["v"][m_start : m_idx + 1],
            timestamps=m_data["ts"][m_start : m_idx + 1],
        )

        curr_px = float(m_data["c"][m_idx])
        sw_hi = m_state.structure.last_major_high.price if m_state.structure.last_major_high else float(np.max(m_data["h"][m_start : m_idx + 1]))
        sw_lo = m_state.structure.last_major_low.price if m_state.structure.last_major_low else float(np.min(m_data["l"][m_start : m_idx + 1]))

        dealing_range = sw_hi - sw_lo
        if dealing_range <= 0:
            return MacroPhaseBaton.NEUTRAL_CONSOLIDATION, None, None

        relative_pos = (curr_px - sw_lo) / dealing_range
        trend = m_state.structure.external_trend

        # Macro Targets:
        demand_target = sw_lo + 0.3 * dealing_range  # Discount demand pocket
        supply_target = sw_hi                       # External liquidity high

        # Baton Logic:
        if trend == TrendDirection.BULLISH:
            if relative_pos >= self.deep_premium_threshold:
                # Bullish market expanded deep into Premium -> Expect Pullback to Discount Demand
                res = (MacroPhaseBaton.BEARISH_PULLBACK, demand_target, supply_target)
            else:
                # Bullish market in Discount or Equilibrium -> Expect Bullish Expansion
                res = (MacroPhaseBaton.BULLISH_EXPANSION, demand_target, supply_target)
        elif trend == TrendDirection.BEARISH:
            if relative_pos <= self.deep_discount_threshold:
                # Bearish market sold off into Discount -> Expect Pullback to Premium Supply
                res = (MacroPhaseBaton.BULLISH_PULLBACK, demand_target, supply_target)
            else:
                # Bearish market in Premium or Equilibrium -> Expect Bearish Expansion
                res = (MacroPhaseBaton.BEARISH_EXPANSION, demand_target, supply_target)
        else:
            res = (MacroPhaseBaton.NEUTRAL_CONSOLIDATION, demand_target, supply_target)

        self._macro_cache[cache_key] = res
        return res

    def scan_cascading_candidates(
        self,
        symbol: str,
        target_set: str,
        all_data: Dict[str, Dict[str, np.ndarray]],
        only_latest_bar: bool = False,
    ) -> Tuple[List[Dict[str, Any]], Dict[int, float]]:
        """Scan candidate signals for a specific set, causally conditioned on the macro baton.
        
        If target_set is Set 4 or Set 5, entries are gated by the macro baton.
        Returns:
            candidates: Fully qualified trade candidates.
            trailing_map: Causal MTF trailing stop mapping.
        """
        cfg = self.TIMEFRAME_SETS[target_set]
        htf_tf = cfg["htf"]
        mtf_tf = cfg["mtf"]
        ltf_tf = cfg["ltf"]

        if htf_tf not in all_data or mtf_tf not in all_data or ltf_tf not in all_data:
            return [], {}

        htf_data = all_data[htf_tf]
        mtf_data = all_data[mtf_tf]
        ltf_data = all_data[ltf_tf]

        ltf_closes = ltf_data["c"]
        ltf_ts = ltf_data["ts"]
        n_ltf = len(ltf_closes)

        htf_close_ts = htf_data["close_ts"]
        mtf_close_ts = mtf_data["close_ts"]

        candidates: List[Dict[str, Any]] = []
        trailing_map: Dict[int, float] = {}

        last_htf_idx = -1
        last_htf_state = None
        last_mtf_idx = -1
        last_mtf_state = None

        risk_budget_usd = self.account_equity_usd * self.risk_per_trade_pct

        start_i = max(25, n_ltf - 1) if only_latest_bar else 25
        for i in range(start_i, n_ltf):
            t_curr = int(ltf_ts[i])
            curr_px = float(ltf_closes[i])

            # 1. Determine Macro Baton at this timestamp
            baton, demand_tgt, supply_tgt = self.evaluate_macro_baton(symbol, t_curr, all_data)

            # Determine authorized direction from macro baton
            if baton in (MacroPhaseBaton.BULLISH_EXPANSION, MacroPhaseBaton.BULLISH_PULLBACK):
                authorized_dir = 1
            elif baton in (MacroPhaseBaton.BEARISH_EXPANSION, MacroPhaseBaton.BEARISH_PULLBACK):
                authorized_dir = -1
            else:
                authorized_dir = 0

            # Sets 4 & 5 MUST have an active macro baton; unaligned trades are rejected
            if target_set in ("SET_4", "SET_5") and authorized_dir == 0:
                continue

            # 2. Identify last closed HTF bar
            htf_idx = np.searchsorted(htf_close_ts, t_curr, side="right") - 1
            if htf_idx < 10:
                continue

            if htf_idx != last_htf_idx:
                htf_start = max(0, htf_idx - 150)
                last_htf_state = self.generators[htf_tf].generate(
                    symbol=symbol,
                    opens=htf_data["o"][htf_start : htf_idx + 1],
                    highs=htf_data["h"][htf_start : htf_idx + 1],
                    lows=htf_data["l"][htf_start : htf_idx + 1],
                    closes=htf_data["c"][htf_start : htf_idx + 1],
                    volumes=htf_data["v"][htf_start : htf_idx + 1],
                    timestamps=htf_data["ts"][htf_start : htf_idx + 1],
                )
                last_htf_idx = htf_idx

            htf_state = last_htf_state
            if htf_state is None:
                continue

            # 3. Identify last closed MTF bar
            mtf_idx = np.searchsorted(mtf_close_ts, t_curr, side="right") - 1
            if mtf_idx < 15:
                continue

            if mtf_idx != last_mtf_idx:
                mtf_start = max(0, mtf_idx - 200)
                last_mtf_state = self.generators[mtf_tf].generate(
                    symbol=symbol,
                    opens=mtf_data["o"][mtf_start : mtf_idx + 1],
                    highs=mtf_data["h"][mtf_start : mtf_idx + 1],
                    lows=mtf_data["l"][mtf_start : mtf_idx + 1],
                    closes=mtf_data["c"][mtf_start : mtf_idx + 1],
                    volumes=mtf_data["v"][mtf_start : mtf_idx + 1],
                    timestamps=mtf_data["ts"][mtf_start : mtf_idx + 1],
                )
                last_mtf_idx = mtf_idx

            mtf_state = last_mtf_state
            if mtf_state is None:
                continue

            # 4. Trailing stop registration (MTF structural swings: Major & Minor swing points)
            if authorized_dir == 1:
                trail_cands = []
                if mtf_state.structure.last_major_low and mtf_state.structure.last_major_low.price < curr_px:
                    trail_cands.append(mtf_state.structure.last_major_low.price)
                if mtf_state.structure.last_minor_low and mtf_state.structure.last_minor_low.price < curr_px:
                    trail_cands.append(mtf_state.structure.last_minor_low.price)
                if trail_cands:
                    trailing_map[t_curr] = max(trail_cands)
            elif authorized_dir == -1:
                trail_cands = []
                if mtf_state.structure.last_major_high and mtf_state.structure.last_major_high.price > curr_px:
                    trail_cands.append(mtf_state.structure.last_major_high.price)
                if mtf_state.structure.last_minor_high and mtf_state.structure.last_minor_high.price > curr_px:
                    trail_cands.append(mtf_state.structure.last_minor_high.price)
                if trail_cands:
                    trailing_map[t_curr] = min(trail_cands)

            # 4b. MTF Dealing Range & Zone Check (Must be in Discount for Long, Premium for Short)
            mtf_pd = mtf_state.zones.premium_discount_zone
            mtf_valid = False
            if authorized_dir == 1:
                if mtf_pd == "DISCOUNT" or len(mtf_state.zones.fair_value_gaps) > 0 or len(mtf_state.zones.order_blocks) > 0:
                    mtf_valid = True
            elif authorized_dir == -1:
                if mtf_pd == "PREMIUM" or len(mtf_state.zones.fair_value_gaps) > 0 or len(mtf_state.zones.order_blocks) > 0:
                    mtf_valid = True

            # For micro sets (Sets 4 & 5), require active MTF KeyZone (Order Block or FVG)
            if target_set in ("SET_4", "SET_5"):
                has_ob = len(mtf_state.zones.order_blocks) > 0
                has_fvg = len(mtf_state.zones.fair_value_gaps) > 0
                if not (has_ob or has_fvg):
                    continue

            # 5. Check LTF structural break
            ltf_start = max(0, i - 40)
            ltf_state = self.generators[ltf_tf].generate(
                symbol=symbol,
                opens=ltf_data["o"][ltf_start : i + 1],
                highs=ltf_data["h"][ltf_start : i + 1],
                lows=ltf_data["l"][ltf_start : i + 1],
                closes=ltf_data["c"][ltf_start : i + 1],
                volumes=ltf_data["v"][ltf_start : i + 1],
                timestamps=ltf_data["ts"][ltf_start : i + 1],
            )

            ltf_breaks = ltf_state.structure.recent_breaks
            if not ltf_breaks:
                continue

            last_break = ltf_breaks[-1]
            break_dir = 0
            if last_break.break_type in (StructuralBreakType.BOS_BULLISH, StructuralBreakType.CHOCH_BULLISH):
                break_dir = 1
            elif last_break.break_type in (StructuralBreakType.BOS_BEARISH, StructuralBreakType.CHOCH_BEARISH):
                break_dir = -1

            # ENFORCE THE BATON LAW: LTF break must match authorized macro baton direction
            if break_dir == 0 or break_dir != authorized_dir:
                continue

            # 6. Establish Initial SL and Destination Target
            if break_dir == 1:
                sl_ref = ltf_state.structure.last_minor_low or ltf_state.structure.last_major_low
                if sl_ref and sl_ref.price < curr_px:
                    initial_sl = sl_ref.price * 0.999
                else:
                    initial_sl = curr_px - ltf_state.measurements.atr * 2.0

                # Apply Volatility Stop Floor for micro sets (Sets 4 & 5)
                if target_set in ("SET_4", "SET_5"):
                    min_stop_dist = max(ltf_state.measurements.atr * 1.5, curr_px * 0.005)
                    initial_sl = min(initial_sl, curr_px - min_stop_dist)

                # Destination target: Supply pool or minimum 4R
                if supply_tgt and supply_tgt > curr_px:
                    target_px = supply_tgt
                elif htf_state.structure.weak_high and htf_state.structure.weak_high > curr_px:
                    target_px = htf_state.structure.weak_high
                else:
                    target_px = curr_px + 4.5 * abs(curr_px - initial_sl)

                risk_dist = curr_px - initial_sl
                reward_dist = target_px - curr_px

            else:  # break_dir == -1
                sl_ref = ltf_state.structure.last_minor_high or ltf_state.structure.last_major_high
                if sl_ref and sl_ref.price > curr_px:
                    initial_sl = sl_ref.price * 1.001
                else:
                    initial_sl = curr_px + ltf_state.measurements.atr * 2.0

                # Apply Volatility Stop Floor for micro sets (Sets 4 & 5)
                if target_set in ("SET_4", "SET_5"):
                    min_stop_dist = max(ltf_state.measurements.atr * 1.5, curr_px * 0.005)
                    initial_sl = max(initial_sl, curr_px + min_stop_dist)

                # Destination target: Demand pool or minimum 4R
                if demand_tgt and demand_tgt < curr_px:
                    target_px = demand_tgt
                elif htf_state.structure.weak_low and htf_state.structure.weak_low < curr_px:
                    target_px = htf_state.structure.weak_low
                else:
                    target_px = curr_px - 4.5 * abs(initial_sl - curr_px)

                risk_dist = initial_sl - curr_px
                reward_dist = curr_px - target_px

            if risk_dist <= 0 or reward_dist <= 0:
                continue

            target_r = reward_dist / risk_dist
            if target_r < self.min_target_r - 1e-4:
                continue

            # Dynamic 1% risk position sizing
            pos_size_usd = risk_budget_usd / (risk_dist / curr_px)

            candidates.append({
                "bar_index": i,
                "timestamp_ms": t_curr,
                "symbol": symbol,
                "origin_set": target_set,
                "direction": break_dir,
                "entry_price": curr_px,
                "stop_price": initial_sl,
                "target_price": target_px,
                "target_r": target_r,
                "macro_baton": baton.value,
                "risk_dist": risk_dist,
                "reward_dist": reward_dist,
                "position_size_usd": pos_size_usd,
                "meta": {
                    "break_type": last_break.break_type.value,
                    "target_set": target_set,
                    "macro_baton": baton.value,
                },
            })

        return candidates, trailing_map
