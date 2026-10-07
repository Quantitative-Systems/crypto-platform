"""
Unit tests for QCP Alpha Universe Extensible Research Contracts.
"""

import pytest
from research.alpha_universe.contracts import (
    AlphaFamilyType,
    AlphaSignal,
    ArbitrageEconomicModel,
    MLBaselineComparison,
    HFTSimulationContract,
)


def test_arbitrage_economic_model():
    # Model 1: High gross spread (30 bps) that easily survives 23 bps total friction
    arb_profitable = ArbitrageEconomicModel(
        venue_a="Binance",
        venue_b="Coinbase",
        gross_spread_bps=30.0,
        taker_fee_a_bps=5.0,
        taker_fee_b_bps=5.0,
        half_spread_a_bps=2.0,
        half_spread_b_bps=2.0,
        expected_slippage_bps=4.0,
        transfer_cost_usd=1.0,
        funding_drag_bps=1.0,
    )
    res = arb_profitable.calculate_net_spread_bps(notional_usd=10000.0)
    assert res["gross_spread_bps"] == 30.0
    assert res["is_actionable"] is True
    assert res["net_spread_bps"] > 5.0

    # Model 2: Illusory arbitrage (10 bps gross spread) that gets wiped out by 19 bps friction
    arb_illusory = ArbitrageEconomicModel(
        venue_a="Binance",
        venue_b="Kraken",
        gross_spread_bps=10.0,
        taker_fee_a_bps=5.0,
        taker_fee_b_bps=5.0,
        half_spread_a_bps=2.0,
        half_spread_b_bps=2.0,
        expected_slippage_bps=4.0,
        transfer_cost_usd=1.0,
    )
    res_illusory = arb_illusory.calculate_net_spread_bps(notional_usd=10000.0)
    assert res_illusory["net_spread_bps"] < 0.0
    assert res_illusory["is_actionable"] is False


def test_ml_baseline_comparison():
    # ML model with strong excess edge over rules and linear models
    ml_qualified = MLBaselineComparison(
        model_name="XGBoost_Regime_Predictor",
        ml_test_expectancy_r=0.45,
        linear_baseline_expectancy_r=0.25,
        rule_baseline_expectancy_r=0.20,
        random_control_expectancy_r=0.00,
    )
    passed, msg = ml_qualified.passes_qualification(min_excess_edge_r=0.05)
    assert passed is True

    # ML model that overfit and fails to beat simple rule baseline
    ml_unqualified = MLBaselineComparison(
        model_name="Deep_Neural_Net_Overfit",
        ml_test_expectancy_r=0.22,
        linear_baseline_expectancy_r=0.20,
        rule_baseline_expectancy_r=0.21,
        random_control_expectancy_r=0.00,
    )
    passed, msg = ml_unqualified.passes_qualification(min_excess_edge_r=0.05)
    assert passed is False
    assert "does not beat rule baseline" in msg


def test_hft_simulation_contract():
    # Bar-level setup masquerading as HFT fails eligibility validation
    hft_invalid = HFTSimulationContract(
        tick_level_data_available=False,
        order_book_depth_levels=0,
        queue_position_model_enabled=False,
    )
    eligible, reasons = hft_invalid.validate_hft_eligibility()
    assert eligible is False
    assert len(reasons) >= 3

    # Institutional HFT environment with L2 order-book reconstruction passes
    hft_valid = HFTSimulationContract(
        tick_level_data_available=True,
        order_book_depth_levels=20,
        queue_position_model_enabled=True,
    )
    eligible, reasons = hft_valid.validate_hft_eligibility()
    assert eligible is True
    assert len(reasons) == 0
