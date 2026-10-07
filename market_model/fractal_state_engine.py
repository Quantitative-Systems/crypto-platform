"""Fractal State Engine — Universal Cross-Timeframe Causal State Machine.

Implements the core insight from Phase P empirical discovery: all 5 timeframe sets
are overlapping views of a single 7-timeframe ladder (1M → 1W → 1D → 4H → 1H → 15M → 3M).
One set's LTF is another set's HTF. This engine formalizes the fractal identity:
each physical market movement has a unique causal identity across the ladder.

Architecture:
    FractalStateEngine
    ├── TimeframeLadder (1M → 1W → 1D → 4H → 1H → 15M → 3M)
    ├── FractalStateGraph (directed edges: parent-TF → child-TF causal transitions)
    ├── ConditionalHypothesisEngine (HTF+MTF context → LTF expectancy)
    └── CrossSetCoherence (ensures no double-counting across overlapping sets)

Invariants (Frozen):
    - MarketState contract (structure + zones + phase + measurements) is CANONICAL
    - No lookahead: state at bar[i] uses only data from bars [0..i]
    - Minimum 4R target floor
    - 1% max risk per trade
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np

from market_model.contracts import (
    MarketPhaseType,
    MarketState,
    StructuralBreakType,
    TrendDirection,
)
from market_model.state_generator import MarketStateGenerator


# ============================================================
# 1. TIMEFRAME LADDER — The Universal 7-Level Hierarchy
# ============================================================

class TimeframeRank(int, Enum):
    """Canonical rank in the fractal hierarchy. Higher = slower timeframe."""
    TF_1M = 7    # Monthly
    TF_1W = 6    # Weekly
    TF_1D = 5    # Daily
    TF_4H = 4    # 4-Hour
    TF_1H = 3    # 1-Hour
    TF_15M = 2   # 15-Minute
    TF_3M = 1    # 3-Minute


TIMEFRAME_LABEL_TO_RANK: Dict[str, TimeframeRank] = {
    "1M": TimeframeRank.TF_1M,
    "1w": TimeframeRank.TF_1W,
    "1d": TimeframeRank.TF_1D,
    "4h": TimeframeRank.TF_4H,
    "1h": TimeframeRank.TF_1H,
    "15m": TimeframeRank.TF_15M,
    "3m": TimeframeRank.TF_3M,
}

RANK_TO_LABEL: Dict[TimeframeRank, str] = {v: k for k, v in TIMEFRAME_LABEL_TO_RANK.items()}


# Overlapping timeframe sets as views into the 7-level ladder
TIMEFRAME_SETS = {
    "SET_1": {"htf": "1M", "mtf": "1w", "ltf": "1d"},
    "SET_2": {"htf": "1w", "mtf": "1d", "ltf": "4h"},
    "SET_3": {"htf": "1d", "mtf": "4h", "ltf": "1h"},
    "SET_4": {"htf": "4h", "mtf": "1h", "ltf": "15m"},
    "SET_5": {"htf": "1h", "mtf": "15m", "ltf": "3m"},
}


class FractalBias(str, Enum):
    """Directional bias derived from HTF context."""
    STRONG_BULLISH = "STRONG_BULLISH"
    BULLISH = "BULLISH"
    WEAK_BULLISH = "WEAK_BULLISH"
    NEUTRAL = "NEUTRAL"
    WEAK_BEARISH = "WEAK_BEARISH"
    BEARISH = "BEARISH"
    STRONG_BEARISH = "STRONG_BEARISH"


class FractalAlignment(str, Enum):
    """Cross-timeframe alignment state."""
    FULLY_ALIGNED = "FULLY_ALIGNED"         # All 3 timeframes agree
    HTF_MTF_ALIGNED = "HTF_MTF_ALIGNED"     # HTF + MTF agree, LTF diverges
    MTF_LTF_ALIGNED = "MTF_LTF_ALIGNED"     # MTF + LTF agree, HTF diverges
    CONFLICTING = "CONFLICTING"             # No agreement
    TRANSITIONAL = "TRANSITIONAL"           # One or more in RANGE/TRANSITIONAL


@dataclass
class TimeframeState:
    """Canonical state snapshot for a single timeframe at a point in time."""
    label: str
    rank: TimeframeRank
    state: Optional[MarketState] = None
    last_computed_ts: int = 0
    last_bar_idx: int = -1

    @property
    def trend(self) -> TrendDirection:
        if self.state is None:
            return TrendDirection.NEUTRAL
        return self.state.structure.external_trend

    @property
    def phase(self) -> MarketPhaseType:
        if self.state is None:
            return MarketPhaseType.UNCERTAIN
        return self.state.phase.current_phase

    @property
    def is_bullish(self) -> bool:
        return self.trend == TrendDirection.BULLISH

    @property
    def is_bearish(self) -> bool:
        return self.trend == TrendDirection.BEARISH

    @property
    def is_directional(self) -> bool:
        return self.trend in (TrendDirection.BULLISH, TrendDirection.BEARISH)


# ============================================================
# 2. FRACTAL STATE GRAPH — Cross-Timeframe Transition Tracker
# ============================================================

@dataclass
class FractalTransition:
    """Records a causal state transition event on the fractal ladder."""
    source_tf: str                          # Timeframe where transition occurred
    source_rank: int
    timestamp_ms: int
    previous_trend: TrendDirection
    new_trend: TrendDirection
    break_type: Optional[StructuralBreakType] = None
    meta: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FractalStateNode:
    """A node in the fractal graph representing the state of all timeframes at a given moment."""
    timestamp_ms: int
    states: Dict[str, TimeframeState] = field(default_factory=dict)
    transitions: List[FractalTransition] = field(default_factory=list)
    alignment: FractalAlignment = FractalAlignment.CONFLICTING
    fractal_bias: FractalBias = FractalBias.NEUTRAL
    active_sets: List[str] = field(default_factory=list)  # Which sets have valid signals

    def get_alignment_for_set(self, set_name: str) -> FractalAlignment:
        """Compute alignment specifically for a 3-timeframe set."""
        cfg = TIMEFRAME_SETS.get(set_name)
        if not cfg:
            return FractalAlignment.CONFLICTING

        htf_state = self.states.get(cfg["htf"])
        mtf_state = self.states.get(cfg["mtf"])
        ltf_state = self.states.get(cfg["ltf"])

        if not htf_state or not mtf_state or not ltf_state:
            return FractalAlignment.CONFLICTING

        htf_dir = htf_state.trend
        mtf_dir = mtf_state.trend
        ltf_dir = ltf_state.trend

        # Check for RANGE/TRANSITIONAL on any timeframe
        non_directional = {TrendDirection.RANGE, TrendDirection.NEUTRAL, TrendDirection.TRANSITIONAL}
        if htf_dir in non_directional or mtf_dir in non_directional or ltf_dir in non_directional:
            return FractalAlignment.TRANSITIONAL

        # Check alignment
        if htf_dir == mtf_dir == ltf_dir:
            return FractalAlignment.FULLY_ALIGNED
        elif htf_dir == mtf_dir:
            return FractalAlignment.HTF_MTF_ALIGNED
        elif mtf_dir == ltf_dir:
            return FractalAlignment.MTF_LTF_ALIGNED
        else:
            return FractalAlignment.CONFLICTING


# ============================================================
# 3. CONDITIONAL HYPOTHESIS ENGINE
# ============================================================

@dataclass
class FractalHypothesis:
    """A trade hypothesis derived from fractal cross-timeframe analysis."""
    hypothesis_id: str
    set_name: str
    htf_bias: TrendDirection
    mtf_context: str                    # "DISCOUNT", "PREMIUM", "EQUILIBRIUM"
    ltf_confirmation: str               # Break type string
    expected_direction: int             # +1 or -1
    target_destination: str             # HTF structural target
    alignment: FractalAlignment
    cross_set_support: int              # Number of other sets supporting this direction
    confidence_score: float             # 0.0 to 1.0
    meta: Dict[str, Any] = field(default_factory=dict)


class ConditionalHypothesisEngine:
    """Maps HTF State + MTF Context + LTF Confirmation → Expectancy-weighted hypothesis.

    The engine exploits the fractal insight: if SET 2 shows a bullish HTF (1W), then
    SET 3's HTF (1D) is SET 2's MTF — so SET 3's direction corroborates SET 2.
    """

    # Phase P empirical weights (derived from 9,118 trades)
    SET_WEIGHTS = {
        "SET_1": 0.08,   # Macro, low frequency (147 trades, ExpR=0.76)
        "SET_2": 0.25,   # Strongest edge (1470 trades, ExpR=1.05)
        "SET_3": 0.35,   # Most traded (5424 trades, ExpR=0.56)
        "SET_4": 0.22,   # Intraday (1785 trades, ExpR=0.36)
        "SET_5": 0.10,   # Marginal (292 trades, ExpR=0.10)
    }

    # Break type modifier (CHOCH outperforms BOS empirically)
    BREAK_MODIFIERS = {
        "CHOCH_BULLISH": 1.15,
        "CHOCH_BEARISH": 1.15,
        "BOS_BULLISH": 1.00,
        "BOS_BEARISH": 1.00,
        "MSS_BULLISH": 1.05,
        "MSS_BEARISH": 1.05,
        "FAILED_BREAK": 0.60,
    }

    def __init__(self):
        self._hypothesis_counter = 0

    def evaluate_hypothesis(
        self,
        fractal_node: FractalStateNode,
        set_name: str,
        hypothesis_type: str,  # "PULLBACK" or "CONTINUATION"
    ) -> Optional[FractalHypothesis]:
        """Evaluate whether the current fractal state supports a tradeable hypothesis."""
        cfg = TIMEFRAME_SETS.get(set_name)
        if not cfg:
            return None

        htf_state = fractal_node.states.get(cfg["htf"])
        mtf_state = fractal_node.states.get(cfg["mtf"])
        ltf_state = fractal_node.states.get(cfg["ltf"])

        if not htf_state or not mtf_state or not ltf_state:
            return None
        if not htf_state.state or not mtf_state.state or not ltf_state.state:
            return None

        # 1. HTF Bias
        htf_trend = htf_state.trend
        if not htf_state.is_directional:
            return None

        # 2. Expected direction based on hypothesis type
        if hypothesis_type == "CONTINUATION":
            expected_dir = 1 if htf_trend == TrendDirection.BULLISH else -1
        elif hypothesis_type == "PULLBACK":
            expected_dir = -1 if htf_trend == TrendDirection.BULLISH else 1
        else:
            return None

        # 3. MTF Context validation
        mtf_pd = mtf_state.state.zones.premium_discount_zone
        mtf_valid = False
        if expected_dir == 1 and mtf_pd in ("DISCOUNT", "EQUILIBRIUM"):
            mtf_valid = True
        elif expected_dir == -1 and mtf_pd in ("PREMIUM", "EQUILIBRIUM"):
            mtf_valid = True
        if not mtf_valid and len(mtf_state.state.zones.fair_value_gaps) > 0:
            mtf_valid = True
        if not mtf_valid:
            return None

        # 4. LTF Confirmation check
        ltf_breaks = ltf_state.state.structure.recent_breaks
        if not ltf_breaks:
            return None

        last_break = ltf_breaks[-1]
        is_confirmed = False
        if expected_dir == 1 and last_break.break_type in (
            StructuralBreakType.BOS_BULLISH,
            StructuralBreakType.CHOCH_BULLISH,
        ):
            is_confirmed = True
        elif expected_dir == -1 and last_break.break_type in (
            StructuralBreakType.BOS_BEARISH,
            StructuralBreakType.CHOCH_BEARISH,
        ):
            is_confirmed = True
        if not is_confirmed:
            return None

        # 5. Cross-set support calculation
        cross_support = self._count_cross_set_support(fractal_node, set_name, expected_dir)

        # 6. Alignment
        alignment = fractal_node.get_alignment_for_set(set_name)

        # 7. Confidence scoring
        set_weight = self.SET_WEIGHTS.get(set_name, 0.1)
        break_mod = self.BREAK_MODIFIERS.get(last_break.break_type.value, 1.0)

        alignment_bonus = {
            FractalAlignment.FULLY_ALIGNED: 0.25,
            FractalAlignment.HTF_MTF_ALIGNED: 0.15,
            FractalAlignment.MTF_LTF_ALIGNED: 0.05,
            FractalAlignment.CONFLICTING: -0.10,
            FractalAlignment.TRANSITIONAL: 0.0,
        }.get(alignment, 0.0)

        cross_set_bonus = min(cross_support * 0.08, 0.32)

        confidence = min(1.0, max(0.0,
            0.40                     # Base confidence from HTF+MTF+LTF confirmation
            + set_weight * 0.5       # Set strength contribution
            + alignment_bonus        # Alignment bonus
            + cross_set_bonus        # Cross-set corroboration
            + (break_mod - 1.0)      # Break type adjustment
        ))

        # 8. Target destination
        htf_ms = htf_state.state
        if expected_dir == 1:
            target_dest = "HTF_WEAK_HIGH" if htf_ms.structure.weak_high else "HTF_PREV_HIGH"
        else:
            target_dest = "HTF_WEAK_LOW" if htf_ms.structure.weak_low else "HTF_PREV_LOW"

        self._hypothesis_counter += 1

        return FractalHypothesis(
            hypothesis_id=f"FRAC_{self._hypothesis_counter:06d}",
            set_name=set_name,
            htf_bias=htf_trend,
            mtf_context=mtf_pd,
            ltf_confirmation=last_break.break_type.value,
            expected_direction=expected_dir,
            target_destination=target_dest,
            alignment=alignment,
            cross_set_support=cross_support,
            confidence_score=round(confidence, 4),
            meta={
                "hypothesis_type": hypothesis_type,
                "htf_phase": htf_ms.phase.current_phase.value,
                "mtf_trend": mtf_state.trend.value,
                "ltf_trend": ltf_state.trend.value,
                "set_weight": set_weight,
                "break_modifier": break_mod,
            },
        )

    def _count_cross_set_support(
        self,
        node: FractalStateNode,
        primary_set: str,
        expected_dir: int,
    ) -> int:
        """Count how many other sets corroborate the expected direction.

        Exploits the fractal overlap: SET 2's LTF (4h) = SET 3's MTF (4h),
        so SET 3's HTF (1d) = SET 2's MTF (1d). If SET 2 says bullish and
        SET 3's HTF also says bullish, that's cross-set support.
        """
        support_count = 0
        for other_set, other_cfg in TIMEFRAME_SETS.items():
            if other_set == primary_set:
                continue
            other_htf = node.states.get(other_cfg["htf"])
            if other_htf and other_htf.is_directional:
                if expected_dir == 1 and other_htf.is_bullish:
                    support_count += 1
                elif expected_dir == -1 and other_htf.is_bearish:
                    support_count += 1
        return support_count


# ============================================================
# 4. CROSS-SET COHERENCE — Unique Causal Identity
# ============================================================

class CrossSetCoherenceTracker:
    """Ensures each physical market movement has a unique causal identity.

    When a structural break on 4H fires a signal in SET 2 (as LTF) and
    simultaneously serves as an MTF event in SET 3, the tracker prevents
    double-counting by assigning a unique causal ID to the physical event
    and tracking which sets have consumed it.
    """

    def __init__(self):
        self._consumed_events: Dict[str, Set[str]] = {}
        # Key = "tf_timestamp_breaktype", Value = set of set_names that consumed it

    def register_event(self, timeframe: str, timestamp_ms: int, break_type: str, set_name: str) -> bool:
        """Register a structural event. Returns True if this is a new event for this set."""
        event_id = f"{timeframe}_{timestamp_ms}_{break_type}"
        if event_id not in self._consumed_events:
            self._consumed_events[event_id] = set()

        if set_name in self._consumed_events[event_id]:
            return False  # Already consumed by this set

        self._consumed_events[event_id].add(set_name)
        return True

    def is_duplicate_for_set(self, timeframe: str, timestamp_ms: int, break_type: str, set_name: str) -> bool:
        """Check if this event has already been consumed by this set."""
        event_id = f"{timeframe}_{timestamp_ms}_{break_type}"
        return set_name in self._consumed_events.get(event_id, set())

    def get_cross_set_consumers(self, timeframe: str, timestamp_ms: int, break_type: str) -> Set[str]:
        """Get all sets that have consumed this event."""
        event_id = f"{timeframe}_{timestamp_ms}_{break_type}"
        return self._consumed_events.get(event_id, set()).copy()

    def reset(self):
        self._consumed_events.clear()


# ============================================================
# 5. FRACTAL STATE ENGINE — Main Entry Point
# ============================================================

class FractalStateEngine:
    """Universal Cross-Timeframe Causal State Machine.

    Computes all 7 timeframe states independently and causally, then evaluates
    fractal hypotheses across all 5 overlapping sets. Each timeframe state is
    derived solely from its own candle data up to the evaluation point (zero lookahead).

    Usage:
        engine = FractalStateEngine(symbol="BTCUSDT")
        engine.load_data(timeframe_data)
        node = engine.evaluate_at(timestamp_ms)
        hypotheses = engine.scan_hypotheses(node)
    """

    def __init__(self, symbol: str):
        self.symbol = symbol
        self.hypothesis_engine = ConditionalHypothesisEngine()
        self.coherence = CrossSetCoherenceTracker()

        # One MarketStateGenerator per timeframe level
        self._generators: Dict[str, MarketStateGenerator] = {}
        self._data: Dict[str, Dict[str, np.ndarray]] = {}
        self._tf_states: Dict[str, TimeframeState] = {}
        self._state_cache: Dict[Tuple[str, int], MarketState] = {}
        self._node_cache: Dict[int, FractalStateNode] = {}

        for label, rank in TIMEFRAME_LABEL_TO_RANK.items():
            self._generators[label] = MarketStateGenerator(timeframe=label)
            self._tf_states[label] = TimeframeState(label=label, rank=rank)

    def load_data(self, timeframe_data: Dict[str, Dict[str, np.ndarray]]):
        """Load OHLCV data for all available timeframes.

        Args:
            timeframe_data: Dict keyed by timeframe label (e.g., "1d"),
                values are dicts with keys: "o", "h", "l", "c", "v", "ts", "close_ts"
        """
        self._data = {}
        self._state_cache.clear()
        self._node_cache.clear()
        for label, data in timeframe_data.items():
            if label in TIMEFRAME_LABEL_TO_RANK:
                self._data[label] = data

    def compute_state_at(
        self,
        tf_label: str,
        eval_ts: int,
        lookback: int = 250,
    ) -> Optional[MarketState]:
        """Compute MarketState for a single timeframe at a given evaluation timestamp.

        Only uses bars with close_ts <= eval_ts (strict no-lookahead).
        """
        data = self._data.get(tf_label)
        if data is None:
            return None

        close_ts = data["close_ts"]
        # Find the last bar that is fully closed before eval_ts
        idx = int(np.searchsorted(close_ts, eval_ts, side="right")) - 1
        if idx < 25:
            return None

        cache_key = (tf_label, idx)
        tf_state = self._tf_states.get(tf_label)
        if cache_key in self._state_cache:
            state = self._state_cache[cache_key]
            if tf_state:
                tf_state.state = state
                tf_state.last_computed_ts = eval_ts
                tf_state.last_bar_idx = idx
            return state

        start = max(0, idx - lookback)
        state = self._generators[tf_label].generate(
            symbol=self.symbol,
            opens=data["o"][start:idx + 1],
            highs=data["h"][start:idx + 1],
            lows=data["l"][start:idx + 1],
            closes=data["c"][start:idx + 1],
            volumes=data["v"][start:idx + 1],
            timestamps=data["ts"][start:idx + 1],
        )

        self._state_cache[cache_key] = state
        if tf_state:
            tf_state.state = state
            tf_state.last_computed_ts = eval_ts
            tf_state.last_bar_idx = idx

        return state

    def evaluate_at(
        self, eval_ts: int, target_tfs: Optional[Set[str]] = None
    ) -> FractalStateNode:
        """Compute fractal state across requested (or all) available timeframes at eval_ts.

        Returns a FractalStateNode containing the state of each timeframe and
        the computed alignment/bias.
        """
        cache_key = (eval_ts, tuple(sorted(target_tfs))) if target_tfs is not None else eval_ts
        if cache_key in self._node_cache:
            return self._node_cache[cache_key]

        node = FractalStateNode(timestamp_ms=eval_ts)

        # Compute state for each requested (or all) available timeframe
        tfs_to_compute = target_tfs if target_tfs is not None else self._data.keys()
        for tf_label in tfs_to_compute:
            if tf_label in self._data:
                state = self.compute_state_at(tf_label, eval_ts)
                if state is not None:
                    tf_state = TimeframeState(
                        label=tf_label,
                        rank=TIMEFRAME_LABEL_TO_RANK[tf_label],
                        state=state,
                        last_computed_ts=eval_ts,
                    )
                    node.states[tf_label] = tf_state

        # Compute fractal bias from the highest available timeframe downward
        node.fractal_bias = self._compute_fractal_bias(node)
        node.alignment = self._compute_global_alignment(node)
        node.active_sets = self._identify_active_sets(node)

        self._node_cache[cache_key] = node
        return node

    def scan_hypotheses(
        self,
        node: FractalStateNode,
        sets: Optional[List[str]] = None,
        hypothesis_types: Optional[List[str]] = None,
    ) -> List[FractalHypothesis]:
        """Scan all viable hypotheses across specified sets and hypothesis types."""
        target_sets = sets or list(TIMEFRAME_SETS.keys())
        target_types = hypothesis_types or ["PULLBACK", "CONTINUATION"]

        hypotheses = []
        for set_name in target_sets:
            if set_name not in node.active_sets:
                continue
            for hyp_type in target_types:
                hyp = self.hypothesis_engine.evaluate_hypothesis(node, set_name, hyp_type)
                if hyp is not None:
                    hypotheses.append(hyp)

        # Sort by confidence descending
        hypotheses.sort(key=lambda h: h.confidence_score, reverse=True)
        return hypotheses

    def _compute_fractal_bias(self, node: FractalStateNode) -> FractalBias:
        """Compute net directional bias from all available timeframes, weighted by rank."""
        bullish_weight = 0.0
        bearish_weight = 0.0
        total_weight = 0.0

        rank_weights = {
            TimeframeRank.TF_1M: 3.0,
            TimeframeRank.TF_1W: 2.5,
            TimeframeRank.TF_1D: 2.0,
            TimeframeRank.TF_4H: 1.5,
            TimeframeRank.TF_1H: 1.0,
            TimeframeRank.TF_15M: 0.5,
            TimeframeRank.TF_3M: 0.25,
        }

        for tf_label, tf_state in node.states.items():
            w = rank_weights.get(tf_state.rank, 1.0)
            total_weight += w
            if tf_state.is_bullish:
                bullish_weight += w
            elif tf_state.is_bearish:
                bearish_weight += w

        if total_weight == 0:
            return FractalBias.NEUTRAL

        net_score = (bullish_weight - bearish_weight) / total_weight

        if net_score >= 0.7:
            return FractalBias.STRONG_BULLISH
        elif net_score >= 0.4:
            return FractalBias.BULLISH
        elif net_score >= 0.15:
            return FractalBias.WEAK_BULLISH
        elif net_score <= -0.7:
            return FractalBias.STRONG_BEARISH
        elif net_score <= -0.4:
            return FractalBias.BEARISH
        elif net_score <= -0.15:
            return FractalBias.WEAK_BEARISH
        else:
            return FractalBias.NEUTRAL

    def _compute_global_alignment(self, node: FractalStateNode) -> FractalAlignment:
        """Compute alignment across the dominant SET (SET 2 or SET 3 based on data availability)."""
        # Prefer SET 2 (strongest edge), fall back to SET 3
        for preferred in ["SET_2", "SET_3", "SET_1"]:
            alignment = node.get_alignment_for_set(preferred)
            if alignment != FractalAlignment.CONFLICTING:
                return alignment
        return FractalAlignment.CONFLICTING

    def _identify_active_sets(self, node: FractalStateNode) -> List[str]:
        """Identify which timeframe sets have sufficient data for hypothesis evaluation."""
        active = []
        for set_name, cfg in TIMEFRAME_SETS.items():
            htf_ok = cfg["htf"] in node.states and node.states[cfg["htf"]].state is not None
            mtf_ok = cfg["mtf"] in node.states and node.states[cfg["mtf"]].state is not None
            ltf_ok = cfg["ltf"] in node.states and node.states[cfg["ltf"]].state is not None
            if htf_ok and mtf_ok and ltf_ok:
                active.append(set_name)
        return active

    def get_fractal_summary(self, node: FractalStateNode) -> Dict[str, Any]:
        """Produce a serializable summary of the fractal state for logging/analysis."""
        tf_summary = {}
        for label, tf_state in node.states.items():
            tf_summary[label] = {
                "rank": tf_state.rank.value,
                "trend": tf_state.trend.value,
                "phase": tf_state.phase.value,
                "is_directional": tf_state.is_directional,
            }

        set_alignments = {}
        for set_name in TIMEFRAME_SETS:
            set_alignments[set_name] = node.get_alignment_for_set(set_name).value

        return {
            "timestamp_ms": node.timestamp_ms,
            "fractal_bias": node.fractal_bias.value,
            "global_alignment": node.alignment.value,
            "active_sets": node.active_sets,
            "timeframe_states": tf_summary,
            "set_alignments": set_alignments,
            "transition_count": len(node.transitions),
        }
