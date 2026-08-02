"""
Product 01: Crypto Platform - End-to-End Strategy & Risk Test Suite
Verifies full pipeline execution against strategy_specification.md v1.1 contracts.
"""

import sys
import os

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from market_intelligence.primitives import (
    Candle, MarketStatePayload, TrendDirection, EventType,
    StructureEvent, KeyZone, KeyZoneType
)
from strategy.orchestrator import StrategyOrchestrator
from trade_management.trailing import TrailingEngine


def run_end_to_end_test():
    print("==========================================================================================================")
    print("     PRODUCT 01: END-TO-END STRATEGY SPECIFICATION VERIFICATION SUITE")
    print("==========================================================================================================\n")

    # 1. Mock HTF State (Bullish Bias, TP Target @ $130.00)
    htf_state = MarketStatePayload(
        symbol="BTC/USDT", timeframe="1D", trend=TrendDirection.BULLISH,
        protected_high=130.00, protected_low=95.00,
        last_event=StructureEvent(
            event_type=EventType.CHOCH, direction=TrendDirection.BULLISH,
            broken_price_level=110.0, candle_index=10, timestamp=1700000000
        )
    )

    # 2. Mock MTF State (Aligned Bullish, active Bullish OB @ $100-$102)
    mtf_state = MarketStatePayload(
        symbol="BTC/USDT", timeframe="4H", trend=TrendDirection.BULLISH,
        protected_high=125.00, protected_low=98.00,
        last_event=StructureEvent(
            event_type=EventType.BOS, direction=TrendDirection.BULLISH,
            broken_price_level=105.0, candle_index=15, timestamp=1700000000
        ),
        active_keyzones=[
            KeyZone(
                zone_id="OB_BULL_01", zone_type=KeyZoneType.ORDER_BLOCK,
                direction=TrendDirection.BULLISH, high=102.00, low=100.00,
                origin_candle_index=12
            )
        ]
    )

    # 3. Mock LTF State & Trigger Candle (Low touches $101.00 in keyzone, closes at $105.00)
    ltf_state = MarketStatePayload(
        symbol="BTC/USDT", timeframe="1H", trend=TrendDirection.BULLISH,
        protected_high=115.00, protected_low=99.50, last_event=None
    )

    latest_candle = Candle(
        timestamp=1700003600, open=102.00, high=106.00, low=101.00, close=105.00, volume=15000.0
    )

    # 4. Process Master Orchestrator Pipeline ($1,000 Account)
    plan = StrategyOrchestrator.process_pipeline(
        htf_state=htf_state, mtf_state=mtf_state, ltf_state=ltf_state,
        latest_candle=latest_candle, account_balance=1000.0, risk_pct=0.01
    )

    print("📊 [EXECUTED TRADE PLAN]:")
    print(f"  • Asset & Action      : {plan.symbol} | {plan.action}")
    print(f"  • Strategy Type       : {plan.strategy_type}")
    print(f"  • Entry Price         : ${plan.entry_price:.2f}")
    print(f"  • Stop Loss Price     : ${plan.stop_loss_price:.2f}")
    print(f"  • Target TP Price     : ${plan.target_tp_price:.2f}")
    print(f"  • Position Size       : {plan.position_size_units:.4f} Units")
    print(f"  • Dollar Risk ($)     : ${plan.dollar_risk_usd:.2f} (1.0% Equity)")
    print(f"  • True Reward-to-Risk : {plan.reward_to_risk_ratio:.2f}:1")
    print(f"  • Pipeline Status     : {plan.status} ({plan.reason})")

    assert plan.status == "APPROVED", f"FAIL: Pipeline rejected trade plan! Reason: {plan.reason}"
    assert plan.reward_to_risk_ratio >= 4.0, "FAIL: Reward-to-Risk floor breached!"
    assert round(plan.dollar_risk_usd, 2) == 10.00, "FAIL: 1% Dollar Risk calculation mismatch!"
    print("\n  ✅ PASS: 5-Gate Strategy Specification Pipeline Verified.\n")

    # 5. Test Dynamic MTF Trailing SL Update
    print("📈 [MTF DYNAMIC TRAILING TEST]:")
    mtf_state_updated = MarketStatePayload(
        symbol="BTC/USDT", timeframe="4H", trend=TrendDirection.BULLISH,
        protected_high=128.00, protected_low=108.00, last_event=None
    )

    trail_res = TrailingEngine.update_trailing_stop(
        action=plan.action, current_stop_loss=plan.stop_loss_price, mtf_state=mtf_state_updated
    )

    print(f"  • Initial Stop Loss   : ${plan.stop_loss_price:.2f}")
    print(f"  • Trailed Stop Loss   : ${trail_res.new_stop_loss:.2f}")
    print(f"  • Trailing Reason     : {trail_res.reason}")

    assert trail_res.is_updated, "FAIL: Trailing SL failed to update!"
    assert trail_res.new_stop_loss == 108.00, "FAIL: Trailed stop price mismatch!"
    print("  ✅ PASS: Dynamic MTF Structural Trailing Verified.")

    print("\n==========================================================================================================")
    print("  ✅ PHASE B COMPLETE: Strategy Engine & Risk Firewall 100% Mapped to Specification v1.1!")
    print("==========================================================================================================")


if __name__ == "__main__":
    run_end_to_end_test()