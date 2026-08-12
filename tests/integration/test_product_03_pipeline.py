import pytest
from market_intelligence.primitives import MarketStatePayload, TrendDirection, RawSwing, SwingType, SequenceSwing, SequenceLabel, StructuralRole
from market_intelligence.phase_engine import MarketPhase
from market_intelligence.structure_builder_engine import StructureState
from strategy_engine.coordinator.strategy_coordinator import StrategyCoordinator
from risk_engine.risk_coordinator import RiskCoordinator
from risk_engine.contracts.account_state import AccountState
from risk_engine.contracts.risk_plan import RiskApprovedPlan

def create_high_rr_payload() -> MarketStatePayload:
    # Entry = 100, Stop = 95, Target = 130 => RR = 30 / 5 = 6.0
    
    pl = SequenceSwing(RawSwing("sw1", 12340, 95.0, SwingType.SWING_LOW, 1, 12345, 2), SequenceLabel.HL, StructuralRole.PROTECTED_LOW, True, True, False)
    ph = SequenceSwing(RawSwing("sw2", 12342, 110.0, SwingType.SWING_HIGH, 1, 12345, 2), SequenceLabel.HH, StructuralRole.PROTECTED_HIGH, True, True, False)
    wl = SequenceSwing(RawSwing("sw3", 12343, 98.0, SwingType.SWING_LOW, 1, 12345, 2), SequenceLabel.HL, StructuralRole.WEAK_LOW, False, False, True)
    wh = SequenceSwing(RawSwing("sw4", 12344, 130.0, SwingType.SWING_HIGH, 1, 12345, 2), SequenceLabel.HH, StructuralRole.WEAK_HIGH, False, False, True)
    
    return MarketStatePayload(
        symbol="BTCUSD",
        timeframe="1D",
        timestamp=1000,
        current_price=100.0,
        current_candle=None,
        events=[],
        swings=[],
        structure_state=StructureState(
            sequence_swings=[],
            external_trend=TrendDirection.NEUTRAL,
            internal_trend=TrendDirection.NEUTRAL,
            protected_low=pl,
            protected_high=ph,
            weak_low=wl,
            weak_high=wh,
            dealing_range=None,
            events=[]
        ),
        liquidity_pools=[],
        keyzones=[],
        phase_state=MarketPhase.EXPANSION,
        trend_state=TrendDirection.BULLISH
    )

def test_full_p01_to_p03_pipeline():
    # 1. Product 01 Output
    htf = create_high_rr_payload()
    mtf = create_high_rr_payload()
    ltf = create_high_rr_payload()
    
    # 2. Product 02 Strategy Engine
    strategy_coord = StrategyCoordinator()
    
    # Step 1: Initialize Candidate
    trade_plans = strategy_coord.evaluate(htf, mtf, ltf)
    assert len(trade_plans) == 0
    
    # Step 2: Manually push state to RISK_GATE to simulate setup formation over time
    from strategy_engine.contracts.strategy_state import CandidateState
    for candidate in strategy_coord.candidate_tracker.active_candidates.values():
        candidate.state = CandidateState.RISK_GATE
        
    # Step 3: Trigger Entry
    trade_plans = strategy_coord.evaluate(htf, mtf, ltf)
    
    # We should have 2 ENTERED plans (one for Pullback, one for Continuation since both mock states matched blindly)
    assert len(trade_plans) == 2
    for plan in trade_plans:
        if plan.status == "REJECTED":
            print(f"Plan rejected: {plan.rejection_reason}")
        assert plan.status == CandidateState.ENTERED.value
        assert plan.raw_rr == 6.0
        
    # 3. Product 03 Risk Firewall
    account_state = AccountState(
        current_equity=10000.0,
        peak_equity=10000.0,
        daily_pnl=0.0,
        weekly_pnl=0.0,
        open_position_count=0,
        active_assets={}
    )
    
    # Test first plan through the firewall
    plan_to_execute = trade_plans[0]
    result = RiskCoordinator.evaluate(plan_to_execute, account_state)
    
    # Assert Risk Firewall Approves
    assert isinstance(result, RiskApprovedPlan)
    assert result.position_units == 20.0  # $100 risk / (100 - 95 stop distance)
    assert result.dollar_risk == 100.0
