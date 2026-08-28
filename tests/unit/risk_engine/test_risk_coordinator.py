import pytest
from strategy_engine.contracts.trade_plan import TradePlanPayload
from strategy_engine.contracts.strategy_state import CandidateState
from risk_engine.contracts.account_state import AccountState
from risk_engine.contracts.risk_plan import RiskApprovedPlan
from risk_engine.contracts.risk_rejection import RiskRejectionPayload, RiskRejectionReason
from risk_engine.risk_coordinator import RiskCoordinator

def get_base_trade_plan() -> TradePlanPayload:
    return TradePlanPayload(
        trade_plan_id="t1",
        hypothesis_id="HYP_A",
        symbol="BTC",
        directional_permission="PERMIT_LONG",
        setup_timestamp=1234567890,
        entry_price=100.0,
        stop_invalidation_price=90.0,
        target_price=150.0,
        raw_rr=5.0,  # Valid RR
        status=CandidateState.ENTERED.value
    )

def get_base_account_state() -> AccountState:
    return AccountState(
        current_equity=10000.0,
        peak_equity=10000.0,
        daily_pnl=0.0,
        weekly_pnl=0.0,
        open_position_count=0,
        active_assets={}
    )

def test_risk_coordinator_approves_valid_trade():
    plan = get_base_trade_plan()
    account = get_base_account_state()
    
    result = RiskCoordinator.evaluate(plan, account)
    
    assert isinstance(result, RiskApprovedPlan)
    assert result.dollar_risk == 100.0  # 1% of 10000
    assert result.position_units == 10.0  # 100 / (100-90)

def test_risk_coordinator_rejects_low_rr():
    plan = get_base_trade_plan()
    plan.raw_rr = 3.9
    account = get_base_account_state()
    
    result = RiskCoordinator.evaluate(plan, account)
    
    assert isinstance(result, RiskRejectionPayload)
    assert result.reason == RiskRejectionReason.REJECT_RR_BELOW_FLOOR

def test_risk_coordinator_rejects_systemic_dd():
    plan = get_base_trade_plan()
    account = get_base_account_state()
    account.peak_equity = 10000.0
    account.current_equity = 8900.0  # 11% drawdown
    
    result = RiskCoordinator.evaluate(plan, account)
    
    assert isinstance(result, RiskRejectionPayload)
    assert result.reason == RiskRejectionReason.REJECT_SYSTEMIC_CIRCUIT_BREAKER

def test_risk_coordinator_rejects_max_open_positions():
    plan = get_base_trade_plan()
    account = get_base_account_state()
    account.open_position_count = 5
    
    result = RiskCoordinator.evaluate(plan, account)
    
    assert isinstance(result, RiskRejectionPayload)
    assert result.reason == RiskRejectionReason.REJECT_MAX_OPEN_POSITIONS

def test_risk_coordinator_rejects_zero_stop_distance():
    plan = get_base_trade_plan()
    plan.stop_invalidation_price = 100.0  # Same as entry
    account = get_base_account_state()
    
    result = RiskCoordinator.evaluate(plan, account)
    
    assert isinstance(result, RiskRejectionPayload)
    assert result.reason in [RiskRejectionReason.REJECT_ZERO_STOP_DISTANCE, RiskRejectionReason.REJECT_INVALID_STOP]
