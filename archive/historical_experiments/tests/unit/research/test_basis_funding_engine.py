"""
Unit tests for QCP Market-Neutral Basis & Funding Arbitrage Engine.
Tests cash-and-carry simulation, friction accounting, funding accumulation,
borrow financing deduction, and net APY yield reporting.
"""

import pytest
from research.arbitrage.basis_funding_engine import (
    BasisFundingArbitrageEngine,
    ArbitrageCostModel,
    FundingIntervalRecord,
    ArbitrageSimulationReport,
)


def test_arbitrage_empty_series():
    engine = BasisFundingArbitrageEngine()
    rep = engine.simulate_cash_and_carry("SOL/USDT", [])
    assert rep.total_trades == 0
    assert rep.ending_equity_usd == 10000.0
    assert rep.net_profit_usd == 0.0


def test_friction_accounting():
    costs = ArbitrageCostModel(
        spot_taker_fee_bps=5.0,
        perp_taker_fee_bps=5.0,
        spot_slippage_bps=3.0,
        perp_slippage_bps=3.0,
    )
    engine = BasisFundingArbitrageEngine(cost_model=costs)
    notional = 10000.0

    # Total friction per side = 5 + 5 + 3 + 3 = 16 bps = 0.16%
    entry_fric = engine.calculate_entry_friction(notional)
    assert abs(entry_fric - 16.0) < 1e-4

    exit_fric = engine.calculate_exit_friction(notional)
    assert abs(exit_fric - 16.0) < 1e-4


def test_cash_and_carry_profitable_cycle():
    """
    Simulate 30 intervals (10 days) of high funding rate in a bull market:
    - Spot = 100.0
    - Perp = 100.50 (50 bps basis)
    - Funding = 0.0004 (40 bps per 8h, ~43.8% annualized!)
    - Basis compresses to 100.01 at interval 15.
    """
    costs = ArbitrageCostModel(
        spot_taker_fee_bps=5.0,
        perp_taker_fee_bps=5.0,
        spot_slippage_bps=3.0,
        perp_slippage_bps=3.0,
        borrow_apr_pct=6.0,
        exit_basis_threshold_pct=0.02,
    )
    engine = BasisFundingArbitrageEngine(cost_model=costs)

    start_ts = 1704067200
    intervals = []
    for i in range(30):
        ts = start_ts + i * 28800  # 8h intervals
        spot = 100.0
        # Basis premium starts at 0.50 and decays to 0.01
        perp = 100.50 - (0.49 * (i / 15.0)) if i <= 15 else 100.01
        funding = 0.0004 if i <= 15 else 0.0001
        intervals.append(FundingIntervalRecord(ts, spot, perp, funding))

    rep = engine.simulate_cash_and_carry("SOL/USDT", intervals, capital_usd=10000.0)

    assert rep.total_trades >= 1
    trade = rep.trades[0]
    assert trade.gross_funding_usd > 0
    assert trade.borrow_cost_usd > 0
    assert trade.total_friction_usd > 0
    # Net profit should be positive after high funding harvest
    assert trade.net_pnl_usd > 0
    assert rep.net_profit_usd > 0
    assert rep.annualized_net_apy_pct > 0.0


def test_arbitrage_unwind_on_inversion():
    """
    Simulate funding inversion to negative (perp trades below spot, longs pay shorts):
    Engine should exit position safely to avoid paying negative funding.
    """
    costs = ArbitrageCostModel(exit_basis_threshold_pct=0.01)
    engine = BasisFundingArbitrageEngine(cost_model=costs)

    start_ts = 1704067200
    intervals = [
        FundingIntervalRecord(start_ts, 100.0, 100.40, 0.0003),
        FundingIntervalRecord(start_ts + 28800, 100.0, 100.35, 0.0003),
        FundingIntervalRecord(start_ts + 57600, 100.0, 100.30, 0.0003),
        FundingIntervalRecord(start_ts + 86400, 100.0, 100.25, 0.0003),
        FundingIntervalRecord(start_ts + 115200, 100.0, 99.50, -0.0005),  # Inversion!
        FundingIntervalRecord(start_ts + 144000, 100.0, 99.40, -0.0005),
    ]

    rep = engine.simulate_cash_and_carry("BTC/USDT", intervals, capital_usd=10000.0)
    assert rep.total_trades == 1
    trade = rep.trades[0]
    assert trade.exit_timestamp == start_ts + 115200
