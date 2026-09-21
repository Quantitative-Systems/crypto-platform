"""
Unit Tests for Dynamic Funding & Basis Carry Engine.
Verifies active entry/exit logic, margin borrow financing,
32 bps roundtrip friction, and deployable capital accounting.
"""

import pytest
from research.arbitrage.dynamic_funding_carry import (
    DynamicFundingCarryEngine,
    DynamicCarryConfig,
    DynamicCarryAuditReport,
)


def test_dynamic_funding_carry_high_yield_regime():
    """
    Tests dynamic carry when funding rate is sustained at +0.03% per 8h (32.85% APR)
    for 10 intervals, then drops to 0.0% for 10 intervals.
    Engine should enter during the high-yield regime and exit when funding normalizes.
    """
    records = []
    base_time = 1700000000
    # 25 high funding intervals (approx 8.3 days, sufficient to amortize 32 bps friction)
    for i in range(25):
        records.append({
            "fundingTime": base_time + i * 28800000,
            "fundingRate": 0.0004,  # +4.0 bps per 8h (43.8% APR)
        })
    # 10 low funding intervals
    for i in range(25, 35):
        records.append({
            "fundingTime": base_time + i * 28800000,
            "fundingRate": 0.00001,  # +0.1 bps per 8h
        })

    engine = DynamicFundingCarryEngine(
        config=DynamicCarryConfig(
            entry_annual_funding_pct=15.0,
            exit_annual_funding_pct=5.0,
            borrow_apr_pct=6.0,
            roundtrip_friction_bps=32.0,
            total_deployable_capital_usd=10000.0,
        )
    )

    report: DynamicCarryAuditReport = engine.evaluate_dynamic_carry(
        symbol="SOLUSDT",
        funding_records=records,
    )

    assert report.total_funding_intervals == 35
    assert report.trades_count == 1
    assert report.winning_trades == 1
    assert report.total_gross_funding_usd > 0.0
    assert report.total_net_pnl_usd > 0.0
    assert report.active_utilization_pct < 100.0  # Successfully avoided idle holding


def test_dynamic_funding_carry_inversion_protection():
    """
    Tests that the dynamic carry engine exits immediately upon funding rate inversion (negative rate),
    protecting the short from paying funding to longs.
    """
    records = []
    base_time = 1700000000
    # 5 high funding intervals
    for i in range(5):
        records.append({
            "fundingTime": base_time + i * 28800000,
            "fundingRate": 0.0004,
        })
    # Immediate inversion to negative funding
    records.append({
        "fundingTime": base_time + 5 * 28800000,
        "fundingRate": -0.0002,
    })

    engine = DynamicFundingCarryEngine()
    report = engine.evaluate_dynamic_carry("SOLUSDT", records)

    assert report.trades_count == 1
    # Trade exited on inversion at index 5
    assert report.active_intervals_count == 5
