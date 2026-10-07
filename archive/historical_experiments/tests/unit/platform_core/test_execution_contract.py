"""
Unit tests for QCP Canonical Execution Contract.
"""

import pytest
from platform_core.execution_contract import (
    ExecutionContract,
    CollisionPolicy,
    ExecutionConfig,
)


def test_adverse_first_collision_resolution():
    # Scenario 1: Only SL hit
    hit_sl, hit_tp, reason = ExecutionContract.resolve_same_bar_collision(
        hit_sl=True, hit_tp=False, policy=CollisionPolicy.ADVERSE_FIRST
    )
    assert hit_sl is True
    assert hit_tp is False
    assert reason == "SL_HIT"

    # Scenario 2: Only TP hit
    hit_sl, hit_tp, reason = ExecutionContract.resolve_same_bar_collision(
        hit_sl=False, hit_tp=True, policy=CollisionPolicy.ADVERSE_FIRST
    )
    assert hit_sl is False
    assert hit_tp is True
    assert reason == "TP_HIT"

    # Scenario 3: Same-bar collision (both touched). Adverse-first MUST award SL
    hit_sl, hit_tp, reason = ExecutionContract.resolve_same_bar_collision(
        hit_sl=True, hit_tp=True, policy=CollisionPolicy.ADVERSE_FIRST
    )
    assert hit_sl is True
    assert hit_tp is False
    assert reason == "SL_HIT_ADVERSE_FIRST_COLLISION"

    # Scenario 4: Deprecated optimistic policy (for adversarial testing only)
    hit_sl, hit_tp, reason = ExecutionContract.resolve_same_bar_collision(
        hit_sl=True, hit_tp=True, policy=CollisionPolicy.OPTIMISTIC_FIRST
    )
    assert hit_sl is False
    assert hit_tp is True
    assert reason == "TP_HIT_OPTIMISTIC_COLLISION"


def test_slippage_and_fee_math():
    # Base price 100.0, 5 bps slippage (0.05%)
    buy_fill = ExecutionContract.apply_slippage(100.0, is_buy=True, slippage_bps=5.0)
    assert pytest.approx(buy_fill, 1e-6) == 100.05

    sell_fill = ExecutionContract.apply_slippage(100.0, is_buy=False, slippage_bps=5.0)
    assert pytest.approx(sell_fill, 1e-6) == 99.95

    # Fee math: $10,000 notional at 5 bps (0.05%) = $5.00
    fee = ExecutionContract.calculate_fee(10000.0, fee_bps=5.0)
    assert pytest.approx(fee, 1e-6) == 5.00


def test_canonical_r_accounting():
    # Long trade: Entry 100, Stop 90 (risk = 10), Size = 1.0 unit (risk $10)
    # Exit at TP 125 (+2.5R gross), Entry fee $0.20, Exit fee $0.25 (total friction $0.45 = 0.045R)
    res = ExecutionContract.calculate_r_accounting(
        entry_price=100.0,
        exit_price=125.0,
        initial_sl_price=90.0,
        is_long=True,
        position_size=1.0,
        entry_fee_usd=0.20,
        exit_fee_usd=0.25,
    )
    assert res["initial_risk_usd"] == 10.0
    assert res["gross_pnl_usd"] == 25.0
    assert res["total_friction_usd"] == 0.45
    assert res["net_pnl_usd"] == 24.55
    assert res["gross_r"] == 2.5
    assert res["friction_r"] == 0.045
    assert res["net_r"] == 2.455
