"""
PROJECT TOP1 — Phase 5 Hypothesis Generation & Controlled Experimentation Engine.

Enforces structured, economically grounded hypothesis generation across the 8 strategy families:
1. Trend Following
2. Trend + Pullback
3. Breakout
4. Momentum
5. Mean Reversion
6. Volatility Expansion
7. Multi-Timeframe Continuation
8. Regime-Adaptive Systems

Every hypothesis requires:
- Economic rationale
- Exact entry, exit, stop, target conditions
- Asset and timeframe scope
- Expected market regime
- Risk model (<=1% per trade)
- Strict falsification criteria
"""

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import List, Dict, Any, Optional


class StrategyFamily(str, Enum):
    TREND_FOLLOWING = "TREND_FOLLOWING"
    TREND_PULLBACK = "TREND_PULLBACK"
    BREAKOUT = "BREAKOUT"
    MOMENTUM = "MOMENTUM"
    MEAN_REVERSION = "MEAN_REVERSION"
    VOLATILITY_EXPANSION = "VOLATILITY_EXPANSION"
    MTF_CONTINUATION = "MTF_CONTINUATION"
    REGIME_ADAPTIVE = "REGIME_ADAPTIVE"


@dataclass
class FalsificationCriteria:
    """Quantitative hurdles that automatically reject or quarantine a candidate."""
    min_trades: int = 30
    min_expectancy_r: float = 0.20
    max_drawdown_r: float = 8.0
    min_profit_factor: float = 1.30
    min_win_rate: float = 0.30
    max_consecutive_losses: int = 7
    allow_oos_degradation_pct: float = 0.40  # Max 40% performance drop from In-Sample to OOS


@dataclass
class Hypothesis:
    hypothesis_id: str
    name: str
    family: StrategyFamily
    parent_candidate_id: Optional[str] = None
    economic_rationale: str = ""
    entry_condition: str = ""
    exit_condition: str = ""
    stop_condition: str = ""
    target_condition: str = ""
    asset_scope: List[str] = field(default_factory=lambda: ["BTC/USDT", "ETH/USDT", "SOL/USDT"])
    timeframe_scope: List[str] = field(default_factory=lambda: ["Set 3", "Set 4"])
    expected_regime: str = "TRENDING_OR_EXPANDING"
    risk_model: Dict[str, Any] = field(default_factory=lambda: {"max_risk_pct": 0.01, "friction_adjusted": True})
    falsification: FalsificationCriteria = field(default_factory=FalsificationCriteria)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["family"] = self.family.value
        d["falsification"] = asdict(self.falsification)
        return d


class HypothesisEngine:
    """Generates and registers disciplined quantitative hypotheses."""

    @staticmethod
    def create_candidate_001_hypothesis() -> Hypothesis:
        """Baseline frozen candidate hypothesis."""
        return Hypothesis(
            hypothesis_id="CANDIDATE-001",
            name="Supertrend + Stochastic MTF Triple Alignment (6.0R)",
            family=StrategyFamily.MTF_CONTINUATION,
            parent_candidate_id=None,
            economic_rationale=(
                "Captures large macro trend continuation by requiring higher timeframe trend alignment (Supertrend), "
                "intermediate pullback into deep oversold/overbought conditions (Stochastic K<=25), and lower timeframe "
                "momentum confirmation on candle close, with asymmetric 6R geometric expansion."
            ),
            entry_condition="HTF Supertrend green/red AND HTF, MTF, LTF Stochastics all <= 25 (>=75) with confirmed K/D cross",
            exit_condition="Initial structural SL OR 3-phase structural trailing stop OR TP3 (HTF opposing swing)",
            stop_condition="LTF structural swing extreme at entry, trailed via LTF/MTF/HTF Supertrend/swings",
            target_condition="HTF opposing liquidity / structural swing pivot (minimum 6.0R required at entry)",
            asset_scope=["BTC/USDT", "ETH/USDT", "SOL/USDT"],
            timeframe_scope=["Set 1", "Set 2", "Set 3", "Set 4", "Set 5", "Set 6"],
            expected_regime="STRONG_TREND_WITH_SHARP_PULLBACKS",
            falsification=FalsificationCriteria(min_trades=30, min_expectancy_r=0.25, max_drawdown_r=6.0),
        )

    @staticmethod
    def create_geometry_rationalization_hypothesis() -> Hypothesis:
        """Experiment 001-A: Rationalize target geometry from 6R to 3R."""
        return Hypothesis(
            hypothesis_id="EXP-001A-GEOM",
            name="Supertrend + Stochastic MTF with 3.0R Rational Geometry",
            family=StrategyFamily.MTF_CONTINUATION,
            parent_candidate_id="CANDIDATE-001",
            economic_rationale=(
                "Candidate #001 suffered 29 aborted setups due to the extreme 6.0R hurdle. "
                "Crypto market intraday swings regularly offer 3.0R to 4.5R before standard mean-reversion pullbacks occur. "
                "Lowering the entry qualification hurdle to 3.0R increases statistical opportunity while maintaining positive expectancy."
            ),
            entry_condition="Same as CANDIDATE-001 but minimum TP3 reward-to-risk reduced to >= 3.0R",
            exit_condition="Same as CANDIDATE-001 (Trailing stop + TP3)",
            stop_condition="Same as CANDIDATE-001 (LTF structural swing)",
            target_condition="HTF opposing structural swing >= 3.0R",
            asset_scope=["BTC/USDT", "ETH/USDT", "SOL/USDT"],
            timeframe_scope=["Set 3", "Set 4"],
            expected_regime="TREND_CONTINUATION",
            falsification=FalsificationCriteria(min_trades=30, min_expectancy_r=0.20, max_drawdown_r=8.0),
        )

    @staticmethod
    def create_hierarchical_stochastic_hypothesis() -> Hypothesis:
        """Experiment 001-B: Decouple HTF oscillator from oversold requirement."""
        return Hypothesis(
            hypothesis_id="EXP-001B-STOCH-HIERARCHY",
            name="Decoupled HTF Trend / MTF Pullback Oscillator",
            family=StrategyFamily.TREND_PULLBACK,
            parent_candidate_id="CANDIDATE-001",
            economic_rationale=(
                "In strong trends, the HTF Stochastic rarely drops to K<=25; it typically finds support near K~40-50. "
                "Requiring K<=25 on HTF filters out the best trending moves. "
                "Allowing HTF to simply hold Supertrend direction + Stochastic K>35 while MTF/LTF execute the oversold pullback "
                "aligns with institutional trend-pullback dynamics."
            ),
            entry_condition="HTF: Supertrend green + Stoch K > 35. MTF: Stoch <= 25 with K/D cross. LTF: Stoch <= 25 with K/D cross",
            exit_condition="Trailing stop + TP3 (>= 3.0R)",
            stop_condition="LTF structural swing",
            target_condition="HTF opposing swing target >= 3.0R",
            asset_scope=["BTC/USDT", "ETH/USDT", "SOL/USDT"],
            timeframe_scope=["Set 3", "Set 4"],
            expected_regime="BULL_AND_BEAR_TRENDS",
            falsification=FalsificationCriteria(min_trades=40, min_expectancy_r=0.25, max_drawdown_r=7.0),
        )
