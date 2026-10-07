"""Unit tests for Phase L Independent Robustness & Statistical Stress Testing."""
import pytest
from execution.backtest.engine import TradeRecord
from validation.robustness.contracts import (
    AssetTransferResult,
    CostStressResult,
    CrisisBlindEpisodeResult,
    MasterPhaseLReport,
    MonteCarloResampleResult,
    ParameterPerturbationResult,
    ReactivationIsolationResult,
    TimeframeTransferResult,
)
from validation.robustness.stress_tester import RobustnessStressTester


def _build_dummy_trades(r_multipliers):
    trades = []
    base_ts = 1600000000000
    for i, r in enumerate(r_multipliers):
        trades.append(
            TradeRecord(
                symbol="BTCUSDT",
                stream_id=f"S_{i}",
                direction=1,
                entry_ts=base_ts + i * 14400000,
                exit_ts=base_ts + (i + 1) * 14400000,
                entry_px=50000.0,
                exit_px=50000.0 * (1.0 + r * 0.02),
                initial_sl=49000.0,
                target_px=54000.0,
                initial_risk_dist=1000.0,
                target_r=4.0,
                realized_r=r,
                exit_reason="HTF_TP" if r > 0 else "LTF_SL",
                bars_held=5,
                fee_bps=10.0,
                slippage_bps=5.0,
            )
        )
    return trades


def test_cost_stress_degradation():
    tester = RobustnessStressTester(rng_seed=42)
    # Series with +4R, -1R, +4R, -1R, +4R (Net +10R)
    trades = _build_dummy_trades([4.0, -1.0, 4.0, -1.0, 4.0])
    results = tester.run_cost_stress_test(trades, base_friction_r=0.06)

    assert len(results) == 5
    assert results[0].multiplier == 1.0
    assert results[0].net_r == 10.0
    assert results[0].is_positive_expectancy is True

    # Check monotonic degradation with higher friction
    for i in range(1, len(results)):
        assert results[i].net_r < results[i - 1].net_r
        assert results[i].expectancy_r < results[i - 1].expectancy_r


def test_parameter_perturbation_plateau():
    tester = RobustnessStressTester(rng_seed=42)
    test_vals = [3.5, 4.0, 4.5, 5.0]
    trades_dict = {
        3.5: _build_dummy_trades([3.5, -1.0, 3.5]),
        4.0: _build_dummy_trades([4.0, -1.0, 4.0]),
        4.5: _build_dummy_trades([4.5, -1.0, 4.5]),
        5.0: _build_dummy_trades([5.0, -1.0, 5.0]),
    }

    res = tester.run_parameter_perturbation(
        parameter_name="min_r_multiple",
        baseline_val=4.0,
        test_values=test_vals,
        trades_by_param=trades_dict,
    )

    assert res.parameter_name == "min_r_multiple"
    assert res.baseline_value == 4.0
    assert len(res.expectancies_r) == 4
    assert res.plateau_stability_index > 0.60
    assert res.is_fragile is False


def test_monte_carlo_resampling_statistics():
    tester = RobustnessStressTester(rng_seed=42)
    # Resilient series
    trades = _build_dummy_trades([4.0, -1.0, 4.0, -1.0, 4.0, -1.0, 4.0, -1.0, 4.0, -1.0])
    res = tester.run_monte_carlo_resampling(trades, n_iterations=200, ruin_threshold_r=25.0)

    assert res.iterations == 200
    assert res.original_trade_count == 10
    assert res.original_net_r == 15.0
    assert res.p50_net_r > 0
    assert res.ruin_probability == 0.0
    assert res.is_resilient is True
    assert res.longest_losing_streak_p95 >= 1


def test_contracts_to_dict():
    c_res = CostStressResult(
        multiplier=2.0,
        effective_friction_per_trade_r=0.12,
        trade_count=10,
        net_r=8.0,
        expectancy_r=0.8,
        win_rate=60.0,
        profit_factor=3.0,
        max_drawdown_pct=2.0,
        is_positive_expectancy=True,
    )
    d = c_res.to_dict()
    assert d["multiplier"] == 2.0
    assert d["is_positive_expectancy"] is True

    m_rep = MasterPhaseLReport(
        timestamp_utc="2026-10-06T15:00:00Z",
        cost_stress_breakeven_multiplier=4.5,
        parameter_plateau_passed=True,
        asset_transfer_pass_rate=83.3,
        timeframe_transfer_pass_rate=75.0,
        monte_carlo_resilient=True,
        crisis_blind_protection_rate=100.0,
        reactivation_incremental_finding="Validated isolated post-crisis value",
    )
    m_dict = m_rep.to_dict()
    assert m_dict["cost_stress_breakeven_multiplier"] == 4.5
