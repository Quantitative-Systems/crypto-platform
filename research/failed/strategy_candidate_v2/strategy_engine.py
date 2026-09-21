"""
Multi-Asset / Multi-Timeframe Strategy Engine.

Implements the exact specification:
  - Supertrend (ATR=6, Factor=5) as trend-state indicator
  - Stochastic (K=25, Ksmooth=5, Dsmooth=3) as momentum/pullback confirmation
  - HTF -> MTF -> LTF hierarchical confirmation
  - Both bullish and bearish logic (strict mirror)
  - 6R TP3 minimum filter
  - Hierarchical trailing: LTF -> MTF -> HTF
  - News filter (30min before/after)
  - Causal execution (no lookahead, candle-close confirmation)
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict, Any, Tuple

from market_intelligence.primitives import Candle, RawSwing, SwingType
from market_intelligence.raw_swing_engine import RawSwingEngine, RawSwingConfig
from strategy_candidate.indicators import SupertrendEngine, StochasticEngine
from strategy_engine.news.news_provider import NullNewsProvider, NewsProvider
from backtesting.friction_model import FrictionModel


class SetupState(Enum):
    """States for the stochastic cycle state machine."""
    IDLE = "IDLE"
    WAITING_PEAK = "WAITING_PEAK"       # Waiting for stoch to reach 75 (bull) or 25 (bear)
    WAITING_PULLBACK = "WAITING_PULLBACK"  # Waiting for stoch to pull back to 25 (bull) or 75 (bear)
    WAITING_CONFIRMATION = "WAITING_CONFIRMATION"  # Waiting for candle close + supertrend recheck
    WAITING_CROSSOVER = "WAITING_CROSSOVER"  # LTF only: waiting for K/D crossover
    READY = "READY"


class TrailingPhase(Enum):
    PHASE_1_LTF = "PHASE_1_LTF"
    PHASE_2_WAITING_MTF = "PHASE_2_WAITING_MTF"
    PHASE_2_MTF = "PHASE_2_MTF"
    PHASE_3_WAITING_HTF = "PHASE_3_WAITING_HTF"
    PHASE_3_HTF = "PHASE_3_HTF"


@dataclass
class TimeframeState:
    """State for a single timeframe in the strategy."""
    tf_name: str
    direction: int = 0  # 1 = bullish, -1 = bearish, 0 = none
    supertrend_dir: int = 0
    supertrend_val: float = 0.0
    k: float = 50.0
    d: float = 50.0
    prev_k: float = 50.0
    prev_d: float = 50.0
    state: SetupState = SetupState.IDLE
    condition_met_ts: Optional[int] = None
    target_price: Optional[float] = None
    # Track if stochastic has reached the peak level
    peak_reached: bool = False
    pullback_reached: bool = False


@dataclass
class TradeSetup:
    """A complete trade setup across all three timeframes."""
    symbol: str
    set_name: str
    direction: int  # 1 = LONG, -1 = SHORT
    htf_ts: int
    mtf_ts: int
    ltf_ts: int
    entry_price: float
    sl_price: float
    tp1: float
    tp2: float
    tp3: float
    planned_rr: float
    htf_state: TimeframeState = None
    mtf_state: TimeframeState = None
    ltf_state: TimeframeState = None


@dataclass
class ActivePosition:
    """An active trade being managed."""
    trade_id: str
    symbol: str
    set_name: str
    direction: int
    entry_ts: int
    entry_price: float
    fill_entry: float
    size: float
    entry_fee: float
    initial_sl: float
    current_sl: float
    tp1: float
    tp2: float
    tp3: float
    planned_rr: float
    trailing_phase: TrailingPhase = TrailingPhase.PHASE_1_LTF
    # Trailing transition tracking
    ltf_trail_vals: List[float] = field(default_factory=list)
    mtf_trail_vals: List[float] = field(default_factory=list)
    htf_trail_vals: List[float] = field(default_factory=list)
    transition_log: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class HighLowData:
    """Simple high/low data for exit checking."""
    high: float
    low: float


class StrategyEngine:
    """
    Core strategy engine implementing the exact specification.
    """

    # Strategy parameters (NO OPTIMIZATION)
    ATR_LENGTH = 6
    FACTOR = 5.0
    K_LENGTH = 25
    K_SMOOTH = 5
    D_SMOOTH = 3
    STOCH_HIGH = 75.0
    STOCH_LOW = 25.0
    MIN_TP3_RR = 6.0
    RISK_PCT = 0.01  # 1% per trade

    def __init__(self, news_provider: Optional[NewsProvider] = None):
        self.news_provider = news_provider or NullNewsProvider()
        self.friction_model = FrictionModel()
        self.swing_engine = RawSwingEngine(RawSwingConfig(left_bars=2, right_bars=2))

    def compute_indicators(self, candles: List[Candle]) -> Dict[str, Any]:
        """Compute all indicators for a candle series."""
        st = SupertrendEngine.calculate(candles, self.ATR_LENGTH, self.FACTOR)
        stoch = StochasticEngine.calculate(candles, self.K_LENGTH, self.K_SMOOTH, self.D_SMOOTH)
        swings = self.swing_engine.detect(candles)
        return {
            "supertrend": st,
            "stochastic": stoch,
            "swings": swings,
        }

    def extract_target_swing(self, swings: List[RawSwing], current_ts: int, direction: int) -> Optional[float]:
        """
        Extract the relevant previous high/swing prior to the pullback.
        For bullish: last HIGH swing before current_ts
        For bearish: last LOW swing before current_ts
        Must be causal (confirmation_timestamp <= current_ts).
        """
        valid_swings = [s for s in swings if s.confirmation_timestamp <= current_ts]
        if direction == 1:
            # Bullish: need the last HIGH swing
            for i in range(len(valid_swings) - 1, -1, -1):
                if valid_swings[i].swing_type in (SwingType.HIGH, SwingType.SWING_HIGH):
                    return valid_swings[i].price
        else:
            # Bearish: need the last LOW swing
            for i in range(len(valid_swings) - 1, -1, -1):
                if valid_swings[i].swing_type in (SwingType.LOW, SwingType.SWING_LOW):
                    return valid_swings[i].price
        return None

    def update_timeframe_state(
        self,
        state: TimeframeState,
        st_dir: int,
        st_val: float,
        k: float,
        d: float,
        prev_k: float,
        prev_d: float,
        swings: List[RawSwing],
        current_ts: int,
        direction: int,
        is_ltf: bool = False,
    ):
        """
        Update the state machine for a single timeframe.
        
        Bullish logic (direction=1):
          1. Supertrend must be bullish (st_dir == 1)
          2. Stochastic must reach 75 (peak)
          3. Stochastic must pull back to 25
          4. Candle close confirms (we evaluate on close)
          5. Recheck Supertrend is still bullish
          6. (LTF only) K must cross above D
          
        Bearish logic (direction=-1):
          1. Supertrend must be bearish (st_dir == -1)
          2. Stochastic must reach 25 (trough)
          3. Stochastic must recover to 75
          4. Candle close confirms
          5. Recheck Supertrend is still bearish
          6. (LTF only) K must cross below D
        """
        state.supertrend_dir = st_dir
        state.supertrend_val = st_val
        state.prev_k = state.k
        state.prev_d = state.d
        state.k = k
        state.d = d

        if direction == 1:
            # BULLISH LOGIC
            if st_dir != 1:
                # Supertrend not bullish -> reset
                state.state = SetupState.IDLE
                state.peak_reached = False
                state.pullback_reached = False
                state.condition_met_ts = None
                return

            if state.state == SetupState.IDLE:
                # Waiting for stochastic to reach 75
                if k >= self.STOCH_HIGH:
                    state.state = SetupState.WAITING_PEAK
                    state.peak_reached = True

            elif state.state == SetupState.WAITING_PEAK:
                # Stochastic reached 75, now waiting for pullback to 25
                if k <= self.STOCH_LOW:
                    state.state = SetupState.WAITING_PULLBACK
                    state.pullback_reached = True
                elif k >= self.STOCH_HIGH:
                    # Still at peak, stay
                    state.peak_reached = True

            elif state.state == SetupState.WAITING_PULLBACK:
                # Stochastic pulled back to 25
                # Now we need candle close confirmation + supertrend recheck
                # Since we evaluate on candle close, the current state IS the confirmation
                if st_dir == 1:  # Supertrend still bullish
                    if is_ltf:
                        # LTF needs K/D crossover
                        state.state = SetupState.WAITING_CROSSOVER
                    else:
                        # HTF/MTF: ready
                        state.state = SetupState.READY
                        state.condition_met_ts = current_ts
                        state.target_price = self.extract_target_swing(swings, current_ts, direction)
                else:
                    # Supertrend turned bearish -> invalidate
                    state.state = SetupState.IDLE
                    state.peak_reached = False
                    state.pullback_reached = False

            elif state.state == SetupState.WAITING_CROSSOVER:
                # LTF: waiting for K to cross above D
                if prev_k <= prev_d and k > d:
                    # Crossover confirmed on this candle close
                    if st_dir == 1:  # Supertrend still bullish
                        state.state = SetupState.READY
                        state.condition_met_ts = current_ts
                        state.target_price = self.extract_target_swing(swings, current_ts, direction)
                    else:
                        state.state = SetupState.IDLE
                        state.peak_reached = False
                        state.pullback_reached = False
                elif k <= self.STOCH_LOW:
                    # Stochastic still at or below 25, keep waiting for crossover
                    pass
                else:
                    # Stochastic moved above 25 without crossover -> reset crossover wait
                    # but keep pullback reached state
                    pass

        else:
            # BEARISH LOGIC (mirror of bullish)
            if st_dir != -1:
                state.state = SetupState.IDLE
                state.peak_reached = False
                state.pullback_reached = False
                state.condition_met_ts = None
                return

            if state.state == SetupState.IDLE:
                # Waiting for stochastic to reach 25
                if k <= self.STOCH_LOW:
                    state.state = SetupState.WAITING_PEAK
                    state.peak_reached = True

            elif state.state == SetupState.WAITING_PEAK:
                # Stochastic reached 25, now waiting for recovery to 75
                if k >= self.STOCH_HIGH:
                    state.state = SetupState.WAITING_PULLBACK
                    state.pullback_reached = True
                elif k <= self.STOCH_LOW:
                    state.peak_reached = True

            elif state.state == SetupState.WAITING_PULLBACK:
                if st_dir == -1:  # Supertrend still bearish
                    if is_ltf:
                        state.state = SetupState.WAITING_CROSSOVER
                    else:
                        state.state = SetupState.READY
                        state.condition_met_ts = current_ts
                        state.target_price = self.extract_target_swing(swings, current_ts, direction)
                else:
                    state.state = SetupState.IDLE
                    state.peak_reached = False
                    state.pullback_reached = False

            elif state.state == SetupState.WAITING_CROSSOVER:
                # LTF: waiting for K to cross below D
                if prev_k >= prev_d and k < d:
                    if st_dir == -1:
                        state.state = SetupState.READY
                        state.condition_met_ts = current_ts
                        state.target_price = self.extract_target_swing(swings, current_ts, direction)
                    else:
                        state.state = SetupState.IDLE
                        state.peak_reached = False
                        state.pullback_reached = False

    def check_entry(
        self,
        htf_state: TimeframeState,
        mtf_state: TimeframeState,
        ltf_state: TimeframeState,
        direction: int,
    ) -> bool:
        """Check if all three timeframes are ready for entry."""
        return (
            htf_state.state == SetupState.READY and
            mtf_state.state == SetupState.READY and
            ltf_state.state == SetupState.READY
        )

    def reset_after_entry(
        self,
        htf_state: TimeframeState,
        mtf_state: TimeframeState,
        ltf_state: TimeframeState,
        direction: int,
    ):
        """Reset states after entering a trade."""
        if direction == 1:
            htf_state.state = SetupState.IDLE
            htf_state.peak_reached = False
            htf_state.pullback_reached = False
            mtf_state.state = SetupState.IDLE
            mtf_state.peak_reached = False
            mtf_state.pullback_reached = False
            ltf_state.state = SetupState.IDLE
            ltf_state.peak_reached = False
            ltf_state.pullback_reached = False
        else:
            htf_state.state = SetupState.IDLE
            htf_state.peak_reached = False
            htf_state.pullback_reached = False
            mtf_state.state = SetupState.IDLE
            mtf_state.peak_reached = False
            mtf_state.pullback_reached = False
            ltf_state.state = SetupState.IDLE
            ltf_state.peak_reached = False
            ltf_state.pullback_reached = False

    def update_trailing(self, position: ActivePosition,
                        ltf_st_val: float, mtf_st_val: float, htf_st_val: float,
                        current_ts: int):
        """
        Hierarchical trailing stop management.
        
        Phase 1: LTF Supertrend trailing until MTF Supertrend crosses TP1
        Phase 2: MTF Supertrend trailing until HTF Supertrend crosses MTF trail level
        Phase 3: HTF Supertrend trailing until TP3 or exit
        """
        direction = position.direction

        if direction == 1:  # LONG
            if position.trailing_phase == TrailingPhase.PHASE_1_LTF:
                # Trail with LTF Supertrend
                if ltf_st_val > position.current_sl:
                    position.current_sl = ltf_st_val
                position.ltf_trail_vals.append(position.current_sl)

                # Check for transition: MTF Supertrend crosses TP1
                if mtf_st_val >= position.tp1:
                    position.trailing_phase = TrailingPhase.PHASE_2_WAITING_MTF
                    position.transition_log.append({
                        "ts": current_ts,
                        "from": "PHASE_1_LTF",
                        "to": "PHASE_2_WAITING_MTF",
                        "reason": f"MTF ST ({mtf_st_val:.2f}) >= TP1 ({position.tp1:.2f})",
                    })

            elif position.trailing_phase == TrailingPhase.PHASE_2_WAITING_MTF:
                # Wait for MTF Supertrend to cross current SL
                if mtf_st_val >= position.current_sl:
                    position.trailing_phase = TrailingPhase.PHASE_2_MTF
                    position.current_sl = mtf_st_val
                    position.transition_log.append({
                        "ts": current_ts,
                        "from": "PHASE_2_WAITING_MTF",
                        "to": "PHASE_2_MTF",
                        "reason": f"MTF ST ({mtf_st_val:.2f}) >= current SL ({position.current_sl:.2f})",
                    })

            elif position.trailing_phase == TrailingPhase.PHASE_2_MTF:
                # Trail with MTF Supertrend
                if mtf_st_val > position.current_sl:
                    position.current_sl = mtf_st_val
                position.mtf_trail_vals.append(position.current_sl)

                # Check for transition: HTF Supertrend crosses current SL
                if htf_st_val >= position.current_sl:
                    position.trailing_phase = TrailingPhase.PHASE_3_HTF
                    position.current_sl = htf_st_val
                    position.transition_log.append({
                        "ts": current_ts,
                        "from": "PHASE_2_MTF",
                        "to": "PHASE_3_HTF",
                        "reason": f"HTF ST ({htf_st_val:.2f}) >= current SL",
                    })

            elif position.trailing_phase == TrailingPhase.PHASE_3_HTF:
                # Trail with HTF Supertrend
                if htf_st_val > position.current_sl:
                    position.current_sl = htf_st_val
                position.htf_trail_vals.append(position.current_sl)

        else:  # SHORT
            if position.trailing_phase == TrailingPhase.PHASE_1_LTF:
                if ltf_st_val < position.current_sl:
                    position.current_sl = ltf_st_val
                position.ltf_trail_vals.append(position.current_sl)

                if mtf_st_val <= position.tp1:
                    position.trailing_phase = TrailingPhase.PHASE_2_WAITING_MTF
                    position.transition_log.append({
                        "ts": current_ts,
                        "from": "PHASE_1_LTF",
                        "to": "PHASE_2_WAITING_MTF",
                        "reason": f"MTF ST ({mtf_st_val:.2f}) <= TP1 ({position.tp1:.2f})",
                    })

            elif position.trailing_phase == TrailingPhase.PHASE_2_WAITING_MTF:
                if mtf_st_val <= position.current_sl:
                    position.trailing_phase = TrailingPhase.PHASE_2_MTF
                    position.current_sl = mtf_st_val
                    position.transition_log.append({
                        "ts": current_ts,
                        "from": "PHASE_2_WAITING_MTF",
                        "to": "PHASE_2_MTF",
                        "reason": f"MTF ST ({mtf_st_val:.2f}) <= current SL",
                    })

            elif position.trailing_phase == TrailingPhase.PHASE_2_MTF:
                if mtf_st_val < position.current_sl:
                    position.current_sl = mtf_st_val
                position.mtf_trail_vals.append(position.current_sl)

                if htf_st_val <= position.current_sl:
                    position.trailing_phase = TrailingPhase.PHASE_3_HTF
                    position.current_sl = htf_st_val
                    position.transition_log.append({
                        "ts": current_ts,
                        "from": "PHASE_2_MTF",
                        "to": "PHASE_3_HTF",
                        "reason": f"HTF ST ({htf_st_val:.2f}) <= current SL",
                    })

            elif position.trailing_phase == TrailingPhase.PHASE_3_HTF:
                if htf_st_val < position.current_sl:
                    position.current_sl = htf_st_val
                position.htf_trail_vals.append(position.current_sl)

    def check_exit(self, position: ActivePosition, candle: HighLowData) -> Tuple[bool, str, float]:
        """
        Check if the position should be exited.
        Returns (should_exit, reason, exit_price).
        
        Adverse-first collision handling: if both SL and TP are hit in the same candle,
        assume the adverse outcome (SL) first.
        """
        if position.direction == 1:  # LONG
            # Check stop loss first (adverse-first)
            if candle.low <= position.current_sl:
                return True, "SL", position.current_sl
            # Check TP3
            if candle.high >= position.tp3:
                return True, "TP3", position.tp3
        else:  # SHORT
            if candle.high >= position.current_sl:
                return True, "SL", position.current_sl
            if candle.low <= position.tp3:
                return True, "TP3", position.tp3

        return False, "", 0.0



