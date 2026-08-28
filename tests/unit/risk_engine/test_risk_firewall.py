import pytest
from strategy_engine.contracts.trade_plan import TradePlanPayload
from risk_engine.contracts.account_state import AccountState
from risk_engine.contracts.risk_config import RiskConfig
from risk_engine.risk_coordinator import RiskCoordinator
from risk_engine.contracts.risk_plan import RiskApprovedPlan
from risk_engine.contracts.risk_rejection import RiskRejectionPayload, RiskRejectionReason

@pytest.fixture
def base_account():
    return AccountState(
        current_equity=10000.0,
        peak_equity=10000.0,
        daily_pnl=0.0,
        weekly_pnl=0.0,
        open_position_count=0,
        active_assets={}
    )

@pytest.fixture
def base_config():
    return RiskConfig(
        max_risk_fraction=0.01,
        min_rr_floor=0.0,
        enable_circuit_breakers=False,
        enable_exposure_limits=False,
        enable_news_filter=False,
        max_leverage=10.0,
        min_stop_distance_pct=0.001
    )

def create_plan(entry: float, stop: float, target: float, is_long: bool) -> TradePlanPayload:
    return TradePlanPayload(
        trade_plan_id="plan_1",
        hypothesis_id="UNIFIED_STRATEGY",
        symbol="BTCUSDT",
        setup_timestamp=1000000,
        directional_permission="PERMIT_LONG" if is_long else "PERMIT_SHORT",
        entry_price=entry,
        stop_invalidation_price=stop,
        target_price=target,
        raw_rr=abs(target - entry) / abs(entry - stop) if abs(entry - stop) > 0 else 0,
        structural_provenance={},
        status="ENTERED"
    )

def test_01_normal_stop_distance_approval(base_account, base_config):
    # 5% stop distance
    plan = create_plan(entry=10000.0, stop=9500.0, target=12000.0, is_long=True)
    result = RiskCoordinator.evaluate(plan, base_account, base_config)
    assert isinstance(result, RiskApprovedPlan)
    assert result.dollar_risk == 100.0
    assert result.position_units == 100.0 / 500.0  # 0.2 units

def test_02_extremely_small_stop_distance(base_account, base_config):
    # 0.05% stop distance, below the 0.1% minimum limit
    plan = create_plan(entry=10000.0, stop=9995.0, target=10020.0, is_long=True)
    result = RiskCoordinator.evaluate(plan, base_account, base_config)
    assert isinstance(result, RiskRejectionPayload)
    assert result.reason == RiskRejectionReason.REJECT_MIN_STOP_DISTANCE_VIOLATION

def test_03_zero_stop_distance(base_account, base_config):
    plan = create_plan(entry=10000.0, stop=10000.0, target=10100.0, is_long=True)
    result = RiskCoordinator.evaluate(plan, base_account, base_config)
    assert isinstance(result, RiskRejectionPayload)
    assert result.reason == RiskRejectionReason.REJECT_ZERO_STOP_DISTANCE

def test_04_negative_stop_distance(base_account, base_config):
    # Long trade with stop above entry
    plan = create_plan(entry=10000.0, stop=10500.0, target=11000.0, is_long=True)
    result = RiskCoordinator.evaluate(plan, base_account, base_config)
    assert isinstance(result, RiskRejectionPayload)
    assert result.reason == RiskRejectionReason.REJECT_NEGATIVE_STOP_DISTANCE

def test_05_max_notional_breach_and_leverage(base_account, base_config):
    # Stop is exactly at the limit of 0.1% so it doesn't fail the distance test
    # Entry: 10000. Stop: 9990. Dist = 10. Qty = 100 / 10 = 10 units. Notional = 100,000
    # Equity = 10k, max_leverage = 10.0 -> max notional = 100k
    
    cfg = RiskConfig(
        max_risk_fraction=0.01,
        min_rr_floor=0.0,
        enable_circuit_breakers=False,
        enable_exposure_limits=False,
        enable_news_filter=False,
        max_leverage=10.0,
        min_stop_distance_pct=0.0001  # Lower this so it passes distance check
    )
    
    # Let's make it just over 100k to breach max_leverage
    plan = create_plan(entry=10000.0, stop=9991.0, target=10100.0, is_long=True)
    # Dist = 9, Qty = 11.11. Notional = 111k.
    result = RiskCoordinator.evaluate(plan, base_account, cfg)
    assert isinstance(result, RiskRejectionPayload)
    assert result.reason == RiskRejectionReason.REJECT_MAX_LEVERAGE_VIOLATION

def test_06_friction_adjusted_loss(base_account, base_config):
    # Increase max_leverage so we don't hit that limit, but friction blows out intended risk
    cfg = RiskConfig(
        max_risk_fraction=0.01,
        min_rr_floor=4.0,
        enable_circuit_breakers=False,
        enable_exposure_limits=False,
        enable_news_filter=False,
        max_leverage=200.0,
        min_stop_distance_pct=0.0001
    )
    # Entry 10000, Stop 9999. Dist = 1. Qty = 100 units. Notional = 1M.
    # Estimated slippage (5bps) = 500. Estimated fees (5bps) = 500.
    # Friction = 1000. Intended risk = 100. Friction exceeds intended risk by far!
    plan = create_plan(entry=10000.0, stop=9999.0, target=10100.0, is_long=True)
    result = RiskCoordinator.evaluate(plan, base_account, cfg)
    assert isinstance(result, RiskRejectionPayload)
    assert result.reason == RiskRejectionReason.REJECT_FRICTION_ADJUSTED_RISK_VIOLATION

def test_07_insufficient_equity(base_account, base_config):
    account = AccountState(
        current_equity=0.0,
        peak_equity=10000.0,
        daily_pnl=0.0,
        weekly_pnl=0.0,
        open_position_count=0,
        active_assets={}
    )
    plan = create_plan(entry=10000.0, stop=9500.0, target=12000.0, is_long=True)
    result = RiskCoordinator.evaluate(plan, account, base_config)
    assert isinstance(result, RiskRejectionPayload)
    assert result.reason == RiskRejectionReason.REJECT_INSUFFICIENT_EQUITY

def test_08_short_trade_normal_approval(base_account, base_config):
    plan = create_plan(entry=10000.0, stop=10500.0, target=8000.0, is_long=False)
    result = RiskCoordinator.evaluate(plan, base_account, base_config)
    assert isinstance(result, RiskApprovedPlan)
    assert result.dollar_risk == 100.0

def test_09_short_trade_negative_stop_distance(base_account, base_config):
    # Short trade with stop below entry
    plan = create_plan(entry=10000.0, stop=9500.0, target=8000.0, is_long=False)
    result = RiskCoordinator.evaluate(plan, base_account, base_config)
    assert isinstance(result, RiskRejectionPayload)
    assert result.reason == RiskRejectionReason.REJECT_NEGATIVE_STOP_DISTANCE

def test_10_invalid_exchange_quantity(base_account, base_config):
    # Set max_quantity to 0.05. Even if other rules pass, this rejects it.
    cfg = RiskConfig(
        max_risk_fraction=0.01,
        min_rr_floor=0.0,
        enable_circuit_breakers=False,
        enable_exposure_limits=False,
        enable_news_filter=False,
        max_leverage=10.0,
        min_stop_distance_pct=0.001,
        max_quantity=0.05
    )
    # Entry 10000, Stop 9500. Dist = 500. Qty = 100 / 500 = 0.2. 
    # Qty 0.2 > max_quantity 0.05
    plan = create_plan(entry=10000.0, stop=9500.0, target=12000.0, is_long=True)
    result = RiskCoordinator.evaluate(plan, base_account, cfg)
    assert isinstance(result, RiskRejectionPayload)
    assert result.reason == RiskRejectionReason.REJECT_QUANTITY_STEP_VIOLATION
