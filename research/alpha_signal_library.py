"""
QCP Alpha Signal Library.
Causal signal constructors for the measurable alpha specifications.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

import numpy as np
import pandas as pd

from research.strategy_grammar import HypothesisBuilder, TimeframeSet
from research.grammar_components import ComponentRegistry
import research.bias_families as bf
import research.setup_families as sf
import research.entry_families as ef
import research.sl_families as slf
import research.tp_families as tpf
import research.trailing_families as trf

# Register all components
bf.register_all_biases(ComponentRegistry)
sf.register_all_setups(ComponentRegistry)
ef.register_all_entries(ComponentRegistry)
slf.register_all_stop_losses(ComponentRegistry)
tpf.register_all_take_profits(ComponentRegistry)
trf.register_all_trailings(ComponentRegistry)


@dataclass
class SignalSpec:
    alpha_id: str
    required_data: List[str]
    builder: Optional[Callable[[], Callable[[pd.DataFrame, pd.Series], pd.DataFrame]]] = None
    availability_reason: str = "AVAILABLE"
    economic_mechanism: str = ""

    @property
    def is_measurable(self) -> bool:
        return self.builder is not None


def build_signal_registry(reference_df: Optional[pd.DataFrame] = None) -> Dict[str, SignalSpec]:
    """Constructs the registry of measurable and explicitly unmeasurable alphas using modular components."""
    registry: Dict[str, SignalSpec] = {}
    
    # ---------------------------------------------------------
    # Canonical: CANONICAL_SUPERTREND_STOCHASTIC_MTF_V1
    # ---------------------------------------------------------
    registry["CANONICAL_SUPERTREND_STOCHASTIC_MTF_V1"] = SignalSpec(
        alpha_id="CANONICAL_SUPERTREND_STOCHASTIC_MTF_V1",
        required_data=["OHLCV_4h"], # Assume SET 2 base timeframe for test
        builder=lambda: HypothesisBuilder.build_signal(
            hypothesis_id="CANONICAL_SUPERTREND_STOCHASTIC_MTF_V1",
            bias_id="CANONICAL_SUPERTREND_STOCHASTIC",
            setup_id="CANONICAL_SUPERTREND_STOCHASTIC_SETUP",
            entry_id="CANONICAL_SUPERTREND_STOCHASTIC_ENTRY",
            sl_id="SL_LTF_SWING",
            tp_id="TP_DYNAMIC_R",
            trailing_id="TRAIL_CHANDELIER",
            tf_set=TimeframeSet.SET_2_CORE
        ),
        economic_mechanism="Canonical Baseline: Supertrend Bias, Stochastic Pullback.",
    )

    # ---------------------------------------------------------
    # Test Hypothesis: Trend + Breakout
    # ---------------------------------------------------------
    registry["TRND_BREAKOUT_SET3"] = SignalSpec(
        alpha_id="TRND_BREAKOUT_SET3",
        required_data=["OHLCV_1h"],
        builder=lambda: HypothesisBuilder.build_signal(
            hypothesis_id="TRND_BREAKOUT",
            bias_id="TREND_MA_ALIGNMENT",
            setup_id="BREAKOUT",
            entry_id="MACD_CROSSOVER",
            sl_id="SL_ATR",
            tp_id="TP_LTF_LIQUIDITY",
            trailing_id="TRAIL_NONE",
            tf_set=TimeframeSet.SET_3_SWING
        ),
        economic_mechanism="Set 3 Swing: MA Alignment -> Breakout Setup -> MACD Crossover.",
    )

    # ---------------------------------------------------------
    # UNAVAILABLE / UNMEASURABLE DATA
    # ---------------------------------------------------------
    registry["FAM-12-OFI_MOMENTUM_BTC_V1"] = SignalSpec(
        alpha_id="FAM-12-OFI_MOMENTUM_BTC_V1",
        required_data=["L2_ORDER_BOOK_DEPTH_TICK", "AGGRESSOR_FLOW"],
        builder=None,
        availability_reason=(
            "DATA_UNAVAILABLE: requires historical L2 book-depth and aggressor-flow "
            "ticks. QCP holds no such archive; the alpha cannot be measured and is "
            "not simulated."
        ),
        economic_mechanism="Order-flow imbalance pressure.",
    )
    
    registry["FAM-10-DYNAMIC_CARRY_SOL_V2"] = SignalSpec(
        alpha_id="FAM-10-DYNAMIC_CARRY_SOL_V2",
        required_data=["FUNDING_RATE_HISTORY", "SPOT_PERP_BASIS"],
        builder=None,
        availability_reason=(
            "DATA_UNAVAILABLE: requires historical funding-rate and spot/perp basis "
            "series. Not present in the warehouse; measured carry claims are therefore "
            "impossible today."
        ),
        economic_mechanism="Perpetual funding carry.",
    )

    return registry