"""
Tests for Executable Funding Arbitrage Research Engine.
Verifies deployable capital economics, friction deductions, margin financing,
and research qualification pipeline verdicts.
"""

import pytest
from research.arbitrage.executable_funding_research import (
    ExecutableFundingResearchEngine,
    DeployableCapitalConfig,
    ExecutableCostConfig,
    FundingPaymentRecord,
)


def test_deployable_capital_config():
    cfg = DeployableCapitalConfig(
        total_deployable_capital_usd=10000.0,
        spot_allocation_pct=50.0,
        perp_margin_pct=25.0,
        liquidation_buffer_pct=25.0,
    )
    assert cfg.spot_notional_usd == 5000.0
    assert cfg.perp_notional_usd == 5000.0
    assert cfg.capital_utilization_pct == 75.0


def test_executable_cost_config():
    costs = ExecutableCostConfig(
        spot_taker_fee_bps=5.0,
        perp_taker_fee_bps=5.0,
        spot_slippage_bps=3.0,
        perp_slippage_bps=3.0,
    )
    assert costs.total_entry_friction_bps == 16.0
    assert costs.total_roundtrip_friction_bps == 32.0


def test_audit_empty_records():
    engine = ExecutableFundingResearchEngine()
    report = engine.audit_executable_arbitrage("SOLUSDT", [])
    assert report.total_funding_intervals == 0
    assert report.research_qualification_verdict == "INSUFFICIENT_DATA"


def test_deployable_capital_haircut_math():
    """
    Verifies that APY calculated on deployable capital ($10k) is exactly half
    the APY on theoretical spot notional ($5k) before borrow adjustments.
    """
    engine = ExecutableFundingResearchEngine(
        capital_config=DeployableCapitalConfig(
            total_deployable_capital_usd=10000.0,
            spot_allocation_pct=50.0,
            perp_margin_pct=25.0,
            liquidation_buffer_pct=25.0,
        ),
        cost_config=ExecutableCostConfig(
            borrow_apr_pct=0.0,  # 0 borrow to isolate capital haircut
            spot_taker_fee_bps=0.0,
            perp_taker_fee_bps=0.0,
            spot_slippage_bps=0.0,
            perp_slippage_bps=0.0,
        ),
    )

    # 1095 intervals of 8h = 365 days (1 year)
    # Rate of 0.0001 (10 bps per 8h) = 0.0003/day = 10.95% annual on notional
    intervals = [
        FundingPaymentRecord(
            timestamp=i * 28800,
            funding_rate_8h=0.0001,
            mark_price=100.0,
            is_positive=True,
            annualized_rate_pct=10.95,
        )
        for i in range(1095)
    ]

    report = engine.audit_executable_arbitrage("SOLUSDT", intervals)
    assert pytest.approx(report.theoretical_position_net_apy_pct, rel=1e-2) == 10.95
    # Deployable capital net APY should be half (5.475%) because notional ($5k) is 50% of capital ($10k)
    assert pytest.approx(report.deployable_capital_net_apy_pct, rel=1e-2) == 5.475
    assert report.capital_haircut_drag_pct > 5.0


def test_negative_funding_and_friction_impact():
    """
    Verifies that adverse funding and 32 bps round-trip friction are deducted correctly.
    """
    engine = ExecutableFundingResearchEngine(
        capital_config=DeployableCapitalConfig(total_deployable_capital_usd=10000.0),
        cost_config=ExecutableCostConfig(borrow_apr_pct=6.0),
    )

    # 30 days of intervals (90 intervals)
    # 50% negative funding
    intervals = []
    for i in range(90):
        rate = 0.0001 if i % 2 == 0 else -0.0001
        intervals.append(
            FundingPaymentRecord(
                timestamp=i * 28800,
                funding_rate_8h=rate,
                mark_price=100.0,
                is_positive=(rate > 0),
                annualized_rate_pct=rate * 3 * 365 * 100,
            )
        )

    report = engine.audit_executable_arbitrage("ETHUSDT", intervals)
    assert report.negative_funding_ratio_pct == 50.0
    # Net profit should be negative because gross funding is 0, while borrow & friction > 0
    assert report.net_profit_usd < 0
    assert report.research_qualification_verdict == "RESEARCH_FAIL_NET_NEGATIVE"
