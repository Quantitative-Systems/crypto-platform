"""Unit tests for Portfolio Risk Governor and Decision Ledger."""
from execution.decision_ledger import DecisionLedger, DecisionType
from execution.portfolio.risk_governor import (
    PortfolioOpportunity,
    PortfolioRiskGovernor,
)


def test_portfolio_risk_governor_correlation_haircut():
    governor = PortfolioRiskGovernor(
        max_total_portfolio_risk_pct=0.03, # 3.0%
        max_single_trade_risk_pct=0.01,    # 1.0%
        high_correlation_threshold=0.75,
        correlation_haircut_factor=0.50,   # 50% haircut
    )

    opp_btc = PortfolioOpportunity(
        symbol="BTCUSDT",
        direction=1,
        expected_edge_r=1.50,
        destination_r=5.5,
        confidence_score=1.0,
        btc_correlation=1.0,
        base_risk_pct=0.01,
    )

    opp_eth = PortfolioOpportunity(
        symbol="ETHUSDT",
        direction=1,
        expected_edge_r=1.20,
        destination_r=5.0,
        confidence_score=1.0,
        btc_correlation=0.90, # Highly correlated with BTC
        base_risk_pct=0.01,
    )

    opp_sol = PortfolioOpportunity(
        symbol="SOLUSDT",
        direction=1,
        expected_edge_r=1.80, # Highest score!
        destination_r=6.5,
        confidence_score=1.1,
        btc_correlation=0.65, # Lower correlation (< 0.75)
        base_risk_pct=0.01,
    )

    allocated = governor.allocate_portfolio_risk([opp_btc, opp_eth, opp_sol])

    # SOL has highest composite score -> allocated 1.0% full risk
    sol_res = next(o for o in allocated if o.symbol == "SOLUSDT")
    assert sol_res.approved_risk_pct == 0.01
    assert sol_res.allocation_action == "ALLOCATED"

    # BTC is second highest -> allocated 1.0% full risk
    btc_res = next(o for o in allocated if o.symbol == "BTCUSDT")
    assert btc_res.approved_risk_pct == 0.01
    assert btc_res.allocation_action == "ALLOCATED"

    # ETH is highly correlated with BTC (0.90 >= 0.75) -> haircut by 50% to 0.50%
    eth_res = next(o for o in allocated if o.symbol == "ETHUSDT")
    assert eth_res.approved_risk_pct == 0.005 # 50 bps
    assert eth_res.allocation_action == "HAIRCUT"

    # Total allocated risk: 1.0% + 1.0% + 0.5% = 2.5% <= 3.0% max budget
    total_allocated = sum(o.approved_risk_pct for o in allocated)
    assert abs(total_allocated - 0.025) < 1e-4


def test_portfolio_governor_destination_floor_enforcement():
    governor = PortfolioRiskGovernor()
    sub_floor_opp = PortfolioOpportunity(
        symbol="BNBUSDT",
        direction=1,
        expected_edge_r=1.5,
        destination_r=2.8, # Under 4.0R floor!
        base_risk_pct=0.01,
    )
    allocated = governor.allocate_portfolio_risk([sub_floor_opp])
    assert allocated[0].approved_risk_pct == 0.0
    assert allocated[0].allocation_action == "SUPPRESSED"
    assert "below mandatory 4.0R floor" in allocated[0].allocation_reason


def test_decision_ledger_records_and_formatting():
    ledger = DecisionLedger()

    # Record a NO-TRADE decision
    rec_flat = ledger.record_decision(
        timestamp_ms=1_700_000_000_000,
        symbol="BTCUSDT",
        timeframe_set="SET_2",
        decision=DecisionType.NO_TRADE,
        primary_reason="Event freeze window: CPI in 12 minutes",
        htf_context="BULLISH",
        mtf_context="PULLBACK",
        blockers=["Event freeze window: CPI in 12 minutes", "HTF destination 3.1R < 4R"],
    )

    assert rec_flat.decision == DecisionType.NO_TRADE
    assert len(rec_flat.blockers) == 2

    card = rec_flat.format_human_card()
    assert "DECISION: NO_TRADE" in card
    assert "BLOCKERS:" in card

    # Record a TRADE decision
    rec_trade = ledger.record_decision(
        timestamp_ms=1_700_000_000_000,
        symbol="BTCUSDT",
        timeframe_set="SET_2",
        decision=DecisionType.TRADE,
        primary_reason="Full Causal Alignment",
        direction="LONG",
        htf_context="BULLISH CONTINUATION",
        mtf_context="DISCOUNT OB RETEST",
        ltf_context="CHOCH + MSS CONFIRMED",
        htf_destination_r=5.2,
        expected_edge_r=1.35,
        risk_allocated_pct=0.01,
        entry_price=64200.0,
        stop_price=63800.0,
        target_price=66280.0,
    )

    stats = ledger.get_summary_statistics()
    assert stats["total_decisions"] == 2
    assert stats["trade_decisions"] == 1
    assert stats["no_trade_decisions"] == 1
