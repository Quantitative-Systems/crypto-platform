"""
Seeds the StrategyRegistry with Candidate #001 and initial discovery hypotheses,
then generates the initial CEO Dashboard.
"""

import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from research.discovery_lab.strategy_registry import StrategyRegistry, StrategyStatus
from research.discovery_lab.hypothesis_engine import HypothesisEngine
from research.discovery_lab.ceo_dashboard import export_ceo_dashboard


def seed():
    registry = StrategyRegistry()

    # 1. Candidate #001
    h1 = HypothesisEngine.create_candidate_001_hypothesis()
    dev_results_001 = {
        "total_trades": 25,
        "win_count": 11,
        "loss_count": 14,
        "win_rate": 0.4400,
        "net_r": 35.79,
        "expectancy_r": 1.43,
        "profit_factor_r": 3.94,
        "max_drawdown_r": 2.91,
        "average_r": 1.43,
        "median_r": -0.26,
        "net_pnl_usd": 3697.10,
        "sample_confidence": "INSUFFICIENT_DATA",
    }
    registry.register_candidate(
        strategy_id="CANDIDATE-001",
        version="1.0.0-FROZEN",
        hypothesis=h1.to_dict(),
        rules={
            "supertrend": {"atr_period": 6, "multiplier": 5.0},
            "stochastic": {"k_period": 25, "k_smooth": 5, "d_smooth": 3, "oversold": 25, "overbought": 75},
            "min_tp3_r": 6.0,
            "timeframe_hierarchy": "HTF_BIAS -> MTF_SETUP -> LTF_ENTRY",
            "trailing_stop": "3_PHASE_STRUCTURAL",
        },
        assets=["BTC/USDT", "ETH/USDT", "SOL/USDT"],
        timeframes=["Set 1", "Set 2", "Set 3", "Set 4", "Set 5", "Set 6"],
        risk_model={"max_risk_pct": 0.01, "friction_adjusted": True},
        status=StrategyStatus.RESEARCH,
        development_results=dev_results_001,
        notes="Frozen benchmark. Opportunity starved (25 trades total across 18 sets, 10 sets with 0 trades).",
    )

    # 2. Pre-register Hypothesis H-001A (Geometry Rationalization)
    h_1a = HypothesisEngine.create_geometry_rationalization_hypothesis()
    registry.register_candidate(
        strategy_id="EXP-001A-GEOM",
        version="0.1.0-DRAFT",
        hypothesis=h_1a.to_dict(),
        rules={
            "supertrend": {"atr_period": 6, "multiplier": 5.0},
            "stochastic": {"k_period": 25, "k_smooth": 5, "d_smooth": 3, "oversold": 25, "overbought": 75},
            "min_tp3_r": 3.0,
            "timeframe_hierarchy": "HTF_BIAS -> MTF_SETUP -> LTF_ENTRY",
            "trailing_stop": "3_PHASE_STRUCTURAL",
        },
        assets=["BTC/USDT", "ETH/USDT", "SOL/USDT"],
        timeframes=["Set 3", "Set 4"],
        risk_model={"max_risk_pct": 0.01, "friction_adjusted": True},
        status=StrategyStatus.RESEARCH,
        notes="Pre-registered hypothesis for Discovery Lab: test reducing 6R hurdle to 3R to unlock viable setups.",
    )

    # 3. Pre-register Hypothesis H-001B (Stochastic Hierarchy)
    h_1b = HypothesisEngine.create_hierarchical_stochastic_hypothesis()
    registry.register_candidate(
        strategy_id="EXP-001B-STOCH",
        version="0.1.0-DRAFT",
        hypothesis=h_1b.to_dict(),
        rules={
            "supertrend": {"atr_period": 6, "multiplier": 5.0},
            "htf_stoch_floor": 35.0,
            "mtf_stoch_oversold": 25.0,
            "ltf_stoch_oversold": 25.0,
            "min_tp3_r": 3.0,
            "timeframe_hierarchy": "HTF_TREND -> MTF_PULLBACK -> LTF_TRIGGER",
            "trailing_stop": "3_PHASE_STRUCTURAL",
        },
        assets=["BTC/USDT", "ETH/USDT", "SOL/USDT"],
        timeframes=["Set 3", "Set 4"],
        risk_model={"max_risk_pct": 0.01, "friction_adjusted": True},
        status=StrategyStatus.RESEARCH,
        notes="Pre-registered hypothesis: decouple HTF from deep oversold condition, allowing trend persistence.",
    )

    print("Registry seeded successfully.")
    export_ceo_dashboard()


if __name__ == "__main__":
    seed()
