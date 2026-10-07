"""Unit test suite for 24/7 Autonomous Shadow Trading Architecture."""
import time
from pathlib import Path

from execution.decision.decision_engine import (
    AutonomousDecisionEngine,
    NoTradeReason,
)
from execution.decision.decision_ledger import LiveDecisionLedger
from execution.position.position_lifecycle import (
    Position,
    PositionLifecycleMonitor,
    PositionState,
)
from execution.portfolio.factor_engine import PortfolioFactorEngine
from execution.shadow.shadow_trader import ShadowTrader
from execution.simulator.execution_simulator import (
    ExecutionSimulator,
    OrderSide,
    OrderStatus,
    OrderType,
    SimulatedOrder,
)
from instrument.instrument_contract import build_instrument
from instrument.instrument_health import HealthStatus, InstrumentHealth
from instrument.instrument_registry import InstrumentRegistry
from market_data.clock_fabric import (
    CanonicalEvent,
    DataQuality,
    DataType,
    DeterministicClock,
    create_canonical_event,
)


class TestShadowSystemArchitecture:
    """Test suite verifying Phase M autonomous trading infrastructure."""

    def test_deterministic_clock_causal_invariant(self):
        clock = DeterministicClock(initial_time=1000.0)
        assert clock.current_time == 1000.0

        evt_past = create_canonical_event(
            event_time=950.0,
            received_time=960.0,
            source="BINANCE",
            symbol="BTC/USDT",
            data_type=DataType.OHLCV,
            payload={"close": 65000.0},
        )
        evt_future = create_canonical_event(
            event_time=1020.0,
            received_time=1025.0,
            source="BINANCE",
            symbol="BTC/USDT",
            data_type=DataType.OHLCV,
            payload={"close": 66000.0},
        )

        assert clock.is_causally_visible(evt_past) is True
        assert clock.is_causally_visible(evt_future) is False

        filtered = clock.filter_visible_events([evt_past, evt_future])
        assert len(filtered) == 1
        assert filtered[0].event_id == evt_past.event_id

        # Advance clock and check causal visibility
        clock.advance_by(50.0)  # current_time = 1050.0
        assert clock.is_causally_visible(evt_future) is True

    def test_portfolio_factor_engine_limits(self):
        engine = PortfolioFactorEngine(
            max_total_portfolio_heat_pct=0.03,  # 3.0%
            max_single_trade_risk_pct=0.01,     # 1.0%
            max_single_asset_risk_pct=0.015,    # 1.5%
        )

        btc_usd = build_instrument("BTC/USD")
        eth_usd = build_instrument("ETH/USD")
        btc_xau = build_instrument("BTC/XAU")

        # Decompose BTC/XAU: Base is crypto, Quote is gold
        decomp = engine.decompose_position(btc_xau, direction=1, risk_pct=0.01)
        assert decomp.crypto_beta_exposure > 0.0
        assert decomp.gold_factor_exposure < 0.0  # Long BTC/XAU is short gold factor
        assert decomp.usd_factor_exposure == 0.0   # No USD exposure!

        # 1. Approve initial 1.0% trade in BTC
        approved, risk, reason = engine.evaluate_capital_approval(btc_usd, direction=1, requested_risk_pct=0.01, active_positions=[])
        assert approved is True
        assert risk == 0.01

        # 2. Portfolio has 1.0% in BTC and 1.0% in ETH (total 2.0% heat)
        active = [
            (btc_usd, 1, 0.01),
            (eth_usd, 1, 0.01),
        ]
        # Requesting another 1.5% exceeds 3.0% total heat -> should haircut or reject
        approved_3rd, risk_3rd, reason_3rd = engine.evaluate_capital_approval(btc_usd, direction=1, requested_risk_pct=0.015, active_positions=active)
        # Cap is 1.0% per trade, remaining headroom is 1.0% (3.0% - 2.0% = 1.0%), but BTC asset concentration allows max 0.5% (1.5% - 1.0% = 0.5%)
        assert approved_3rd is True
        assert risk_3rd == 0.005  # Haircut to 0.5% due to BTC concentration limit!

        # 3. Request when portfolio already at 3.0% heat -> REJECT
        full_active = [
            (btc_usd, 1, 0.01),
            (eth_usd, 1, 0.01),
            (build_instrument("SOL/USD"), 1, 0.01),
        ]
        app_full, risk_full, reason_full = engine.evaluate_capital_approval(btc_usd, direction=1, requested_risk_pct=0.01, active_positions=full_active)
        assert app_full is False
        assert "PORTFOLIO_HEAT_LIMIT" in reason_full

    def test_decision_engine_no_trade_taxonomy(self):
        engine = AutonomousDecisionEngine()
        btc_usd = build_instrument("BTC/USD")
        eur_usd = build_instrument("EUR/USD")  # Ineligible non-crypto base
        health = InstrumentHealth(symbol="BTC/USD")

        base_market = {
            "structure": "BULLISH_TREND",
            "zone": "DEMAND_ZONE",
            "phase": "CONTINUATION",
            "htf_bias": "BULLISH",
            "mtf_valid": True,
            "ltf_valid": True,
            "destination_r": 4.5,
            "spread_bps": 2.5,
            "entry_price": 65000.0,
            "stop_price": 64000.0,
            "target_price": 69500.0,
        }
        base_env = {
            "regime": "EXPANSION_STABLE",
            "in_event_window": False,
            "macro_state": "BENIGN",
        }
        base_gov = {
            "unknown_state_active": False,
            "drawdown_circuit_breaker": False,
            "reactivation_multiplier": 1.0,
        }

        # 1. Ineligible instrument check (EUR/USD)
        out = engine.evaluate_cycle(eur_usd, health, base_market, base_env, base_gov, [])
        assert out.decision == "NO_TRADE"
        assert out.no_trade_code == NoTradeReason.NO_TRADE_INELIGIBLE_INSTRUMENT

        # 2. Data Health failure check
        bad_health = InstrumentHealth(symbol="BTC/USD", feed_alive=False)
        bad_health.last_tick_time = 0.0
        out = engine.evaluate_cycle(btc_usd, bad_health, base_market, base_env, base_gov, [])
        assert out.decision == "NO_TRADE"
        assert out.no_trade_code == NoTradeReason.NO_TRADE_DATA_UNHEALTHY

        # 3. Unknown state check
        gov_unk = dict(base_gov, unknown_state_active=True)
        out = engine.evaluate_cycle(btc_usd, health, base_market, base_env, gov_unk, [])
        assert out.decision == "NO_TRADE"
        assert out.no_trade_code == NoTradeReason.NO_TRADE_UNKNOWN_STATE

        # 4. Drawdown circuit breaker check
        gov_dd = dict(base_gov, drawdown_circuit_breaker=True)
        out = engine.evaluate_cycle(btc_usd, health, base_market, base_env, gov_dd, [])
        assert out.decision == "NO_TRADE"
        assert out.no_trade_code == NoTradeReason.NO_TRADE_DRAWDOWN_GOVERNOR

        # 5. Reactivation cooloff check
        gov_react = dict(base_gov, reactivation_multiplier=0.0)
        out = engine.evaluate_cycle(btc_usd, health, base_market, base_env, gov_react, [])
        assert out.decision == "NO_TRADE"
        assert out.no_trade_code == NoTradeReason.NO_TRADE_REACTIVATION

        # 6. Event freeze check
        env_evt = dict(base_env, in_event_window=True)
        out = engine.evaluate_cycle(btc_usd, health, base_market, env_evt, base_gov, [])
        assert out.decision == "NO_TRADE"
        assert out.no_trade_code == NoTradeReason.NO_TRADE_EVENT_FREEZE

        # 7. Spread too wide check
        mkt_spread = dict(base_market, spread_bps=25.0)  # max is 15.0
        out = engine.evaluate_cycle(btc_usd, health, mkt_spread, base_env, base_gov, [])
        assert out.decision == "NO_TRADE"
        assert out.no_trade_code == NoTradeReason.NO_TRADE_SPREAD_TOO_HIGH

        # 8. Unfavorable regime check
        env_reg = dict(base_env, regime="CRISIS_TURMOIL")
        out = engine.evaluate_cycle(btc_usd, health, base_market, env_reg, base_gov, [])
        assert out.decision == "NO_TRADE"
        assert out.no_trade_code == NoTradeReason.NO_TRADE_REGIME_UNFAVORABLE

        # 9. HTF bias unclear check
        mkt_bias = dict(base_market, htf_bias="NEUTRAL")
        out = engine.evaluate_cycle(btc_usd, health, mkt_bias, base_env, base_gov, [])
        assert out.decision == "NO_TRADE"
        assert out.no_trade_code == NoTradeReason.NO_TRADE_HTF_UNCLEAR

        # 10. Phase invalid check
        mkt_phase = dict(base_market, phase="RANGING_CHOP")
        out = engine.evaluate_cycle(btc_usd, health, mkt_phase, base_env, base_gov, [])
        assert out.decision == "NO_TRADE"
        assert out.no_trade_code == NoTradeReason.NO_TRADE_PHASE_INVALID

        # 11. MTF setup missing check
        mkt_mtf = dict(base_market, mtf_valid=False)
        out = engine.evaluate_cycle(btc_usd, health, mkt_mtf, base_env, base_gov, [])
        assert out.decision == "NO_TRADE"
        assert out.no_trade_code == NoTradeReason.NO_TRADE_MTF_NOT_CONFIRMED

        # 12. LTF trigger missing check
        mkt_ltf = dict(base_market, ltf_valid=False)
        out = engine.evaluate_cycle(btc_usd, health, mkt_ltf, base_env, base_gov, [])
        assert out.decision == "NO_TRADE"
        assert out.no_trade_code == NoTradeReason.NO_TRADE_LTF_NOT_CONFIRMED

        # 13. Destination < 4.0R floor check
        mkt_dest = dict(base_market, destination_r=3.2)  # 3.2R < 4.0R
        out = engine.evaluate_cycle(btc_usd, health, mkt_dest, base_env, base_gov, [])
        assert out.decision == "NO_TRADE"
        assert out.no_trade_code == NoTradeReason.NO_TRADE_DESTINATION_LT_4R

        # 14. ALL GATES PASS -> CLEAN TRADE DECISION!
        out_trade = engine.evaluate_cycle(btc_usd, health, base_market, base_env, base_gov, [])
        assert out_trade.decision == "TRADE"
        assert out_trade.direction == "LONG"
        assert out_trade.destination_r == 4.5
        assert out_trade.risk_approved == 0.01
        assert out_trade.position_size > 0

    def test_position_lifecycle_progression_and_emergency(self):
        monitor = PositionLifecycleMonitor(protect_at_r=1.5, trail_at_r=2.5)
        pos = Position(
            position_id="POS-001",
            symbol="BTC/USD",
            direction=1,
            entry_price=100.0,
            initial_stop_price=90.0,  # 1R = 10.0
            current_stop_price=90.0,
            target_price=150.0,       # 5.0R target
            size=1.0,
            allocated_risk_pct=0.01,
            state=PositionState.PENDING,
        )

        health = InstrumentHealth(symbol="BTC/USD")

        # 1. Initial tick at 100.0 -> ENTERED
        monitor.update_position(pos, current_price=100.0, health=health)
        assert pos.state == PositionState.ENTERED

        # 2. Price reaches 110.0 (+1.0R) -> CONFIRMED
        monitor.update_position(pos, current_price=110.0, health=health)
        assert pos.state == PositionState.CONFIRMED

        # 3. Price reaches 116.0 (+1.6R) -> PROTECTED, Stop moves to Breakeven (100.0)
        monitor.update_position(pos, current_price=116.0, health=health)
        assert pos.state == PositionState.PROTECTED
        assert pos.current_stop_price == 100.0

        # 4. Price reaches 126.0 (+2.6R) -> TRAILING, stop ratchets to MTF level (115.0)
        monitor.update_position(pos, current_price=126.0, mtf_structural_stop=115.0, health=health)
        assert pos.state == PositionState.TRAILING
        assert pos.current_stop_price == 115.0

        # 5. Price reaches 145.0 (90% to 150.0 target) -> DESTINATION_APPROACH
        monitor.update_position(pos, current_price=145.0, health=health)
        assert pos.state == PositionState.DESTINATION_APPROACH

        # 6. Price reaches target 150.0 -> CLOSED_TARGET
        monitor.update_position(pos, current_price=150.0, health=health)
        assert pos.state == PositionState.CLOSED_TARGET
        assert pos.realized_r == 5.0
        assert pos.exit_reason == "HTF_DESTINATION_TARGET_REACHED"

        # Emergency branch test: data corruption forces CLOSED_EMERGENCY
        pos_emergency = Position(
            position_id="POS-002",
            symbol="BTC/USD",
            direction=1,
            entry_price=100.0,
            initial_stop_price=90.0,
            current_stop_price=90.0,
            target_price=150.0,
            size=1.0,
            allocated_risk_pct=0.01,
            state=PositionState.TRAILING,
        )
        bad_health = InstrumentHealth(symbol="BTC/USD", orderbook_valid=False)
        bad_health.evaluate()
        monitor.update_position(pos_emergency, current_price=120.0, health=bad_health)
        assert pos_emergency.state == PositionState.CLOSED_EMERGENCY
        assert "EMERGENCY_DATA_CORRUPTION" in pos_emergency.exit_reason

    def test_execution_simulator_microstructure(self):
        sim = ExecutionSimulator(base_latency_ms=50.0, taker_fee_bps=4.0, random_seed=123)
        btc_usd = build_instrument("BTC/USD")

        order = SimulatedOrder(
            order_id="ORD-001",
            symbol="BTC/USD",
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            quantity=0.5,
        )

        res = sim.execute_market_order(
            order=order,
            reference_price=60000.0,
            instrument=btc_usd,
            observed_spread_bps=3.0,
        )

        assert res.status == OrderStatus.FILLED
        assert res.filled_qty == 0.5
        assert res.latency_ms >= 15.0
        assert res.average_fill_price > 60000.0  # Paid half spread + slippage
        assert res.total_fee_usd > 0.0

    def test_shadow_trader_full_loop(self):
        trader = ShadowTrader(account_equity_usd=100_000.0)
        btc_usd = build_instrument("BTC/USD")
        trader.registry.register(btc_usd)
        health = InstrumentHealth(symbol="BTC/USD")

        market_signal = {
            "structure": "BULLISH_TREND",
            "zone": "DEMAND_ZONE",
            "phase": "CONTINUATION",
            "htf_bias": "BULLISH",
            "mtf_valid": True,
            "ltf_valid": True,
            "destination_r": 4.8,
            "spread_bps": 2.5,
            "entry_price": 60000.0,
            "stop_price": 59000.0,
            "target_price": 64800.0,
        }
        env = {"regime": "EXPANSION_STABLE", "in_event_window": False}
        gov = {"unknown_state_active": False, "drawdown_circuit_breaker": False, "reactivation_multiplier": 1.0}

        # 1. Process entry cycle -> generates TRADE and fills shadow position
        out = trader.process_cycle(btc_usd, health, 60000.0, market_signal, env, gov)
        assert out.decision == "TRADE"
        assert len(trader.active_positions) == 1
        assert len(trader.ledger.records) == 1

        # 2. Advance price toward target 64800.0 (setup completed, no new entry trigger)
        market_at_target = dict(market_signal, ltf_valid=False)
        trader.process_cycle(btc_usd, health, 65000.0, market_at_target, env, gov)
        assert len(trader.active_positions) == 0  # Position cleanly exited at target!
        assert len(trader.completed_trades) == 1

        metrics = trader.get_shadow_performance_metrics()
        assert metrics["total_trades"] == 1
        assert metrics["target_exits"] == 1
        assert metrics["net_r"] > 0
        assert metrics["avg_latency_ms"] > 0
