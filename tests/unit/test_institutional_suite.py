"""Unit and Integration Test Suite for Institutional Platform Upgrade Suite.

Tests the 3 institutional pillars:
1. CustodyRiskFirewall (Off-exchange cold vault, non-custodial API, solvency sentinel)
2. SmartExecutionGateway (Maker rebate optimization, TWAP slicing, spread firewall)
3. ForwardCanaryRunner (Full causal forward paper lifecycle and immutable track record auditing)
"""
from __future__ import annotations

import json
import unittest
from pathlib import Path
import numpy as np

from execution.risk.custody_risk_firewall import (
    CounterpartySolvencyState,
    CustodyProviderType,
    CustodyRiskFirewall,
)
from execution.adapters.smart_execution_gateway import (
    OrderExecutionType,
    SmartExecutionGateway,
)
from execution.shadow.forward_canary_runner import ForwardCanaryRunner


class TestInstitutionalSuite(unittest.TestCase):
    """Rigorous verification of the institutional upgrades."""

    def setUp(self):
        self.firewall = CustodyRiskFirewall(
            total_fund_equity_usd=100_000.0,
            max_hot_collateral_pct=0.20,
        )
        self.gateway = SmartExecutionGateway(
            max_order_size_single_slice_usd=25_000.0,
            maker_fee_bps=-0.5,
            taker_fee_bps=5.0,
            max_allowed_spread_bps=8.0,
        )
        self.runner = ForwardCanaryRunner(
            total_fund_equity_usd=100_000.0,
            max_hot_collateral_pct=0.20,
        )

    # =========================================================================
    # PILLAR 1: CUSTODY RISK FIREWALL TESTS
    # =========================================================================
    def test_custody_firewall_initial_allocation(self):
        """Verifies 80% cold vault and 20% hot collateral initial invariant."""
        self.assertEqual(self.firewall.cold_vault_equity_usd, 80_000.0)
        self.assertEqual(self.firewall.venues["BINANCE"].allocated_margin_usd, 20_000.0)

    def test_non_custodial_api_permission_enforcement(self):
        """Rejects API keys with withdrawal or transfer permissions."""
        # Forbidden key
        forbidden_key = {"enableReading": True, "enableSpotAndMarginTrading": True, "enableWithdrawals": True}
        allowed, msg = self.firewall.verify_api_key_permissions(forbidden_key)
        self.assertFalse(allowed)
        self.assertIn("SECURITY BREACH", msg)

        # Valid non-custodial key
        valid_key = {"enableReading": True, "enableSpotAndMarginTrading": True, "enableWithdrawals": False}
        allowed, msg = self.firewall.verify_api_key_permissions(valid_key)
        self.assertTrue(allowed)

    def test_counterparty_solvency_sentinel(self):
        """Verifies that an exchange withdrawal halt locks all fund trading."""
        state = self.firewall.update_venue_health("BINANCE", latency_ms=50.0, spread_bps=1.0, withdrawals_active=False)
        self.assertEqual(state, CounterpartySolvencyState.WITHDRAWAL_HALT_DETECTED)
        self.assertTrue(self.firewall.is_emergency_quarantined)

        # Pre-trade check must fail closed
        allowed, msg = self.firewall.check_pre_trade_collateral("BINANCE", requested_margin_usd=1_000.0)
        self.assertFalse(allowed)
        self.assertIn("EMERGENCY_QUARANTINE", msg)

    # =========================================================================
    # PILLAR 2: SMART ORDER ROUTER & EXECUTION GATEWAY TESTS
    # =========================================================================
    def test_spread_firewall_blocks_toxic_liquidity(self):
        """Rejects routing when bid-ask spread exceeds maximum threshold."""
        # Spread = (105 - 100) / 102.5 = 4.87% = 487 bps > 8 bps
        intent, msg = self.gateway.route_order(
            symbol="BTCUSDT",
            direction=1,
            size_usd=5_000.0,
            best_bid=100.0,
            best_ask=105.0,
            stop_price=95.0,
            target_price=120.0,
        )
        self.assertIsNone(intent)
        self.assertIn("REJECTED: Spread", msg)

    def test_passive_maker_order_routing(self):
        """Verifies limit post-only order routing to capture maker rebates."""
        intent, msg = self.gateway.route_order(
            symbol="BTCUSDT",
            direction=1,
            size_usd=10_000.0,
            best_bid=50_000.0,
            best_ask=50_001.0,
            stop_price=49_000.0,
            target_price=54_000.0,
            prefer_maker=True,
        )
        self.assertIsNotNone(intent)
        self.assertEqual(intent.execution_type, OrderExecutionType.POST_ONLY_MAKER)
        self.assertEqual(intent.limit_price, 50_000.0)

        # Simulate institutional fill
        fill = self.gateway.simulate_institutional_fill(
            intent=intent,
            arrival_price=50_000.5,
            best_bid=50_000.0,
            best_ask=50_001.0,
        )
        self.assertTrue(fill.is_maker)
        self.assertEqual(fill.fee_bps, -0.5)  # Maker rebate
        self.assertEqual(fill.slippage_bps, 0.0)

    def test_adaptive_twap_order_slicing(self):
        """Automatically slices large institutional orders into multiple child slices."""
        large_size = 75_000.0  # Exceeds $25,000 threshold
        intent, msg = self.gateway.route_order(
            symbol="ETHUSDT",
            direction=1,
            size_usd=large_size,
            best_bid=3_000.0,
            best_ask=3_000.2,
            stop_price=2_900.0,
            target_price=3_400.0,
        )
        self.assertIsNotNone(intent)
        self.assertEqual(intent.execution_type, OrderExecutionType.TWAP_SLICED)
        self.assertEqual(intent.slice_count, 3)

    # =========================================================================
    # PILLAR 3: FORWARD CANARY RUNNER LIFECYCLE TESTS
    # =========================================================================
    def test_forward_canary_break_even_and_exit_lifecycle(self):
        """Simulates position opening, +1.5R break-even lock, and take profit exit."""
        pos_id = "TEST-CANARY-1"
        from execution.shadow.forward_canary_runner import CanaryLivePosition

        pos = CanaryLivePosition(
            position_id=pos_id,
            symbol="BTCUSDT",
            timeframe_set="SET_2",
            direction=1,
            entry_price=50_000.0,
            current_stop_price=49_000.0,
            initial_stop_price=49_000.0,  # Risk dist = $1,000
            target_price=54_000.0,        # Target = +4.0R ($4,000)
            size_usd=10_000.0,
            entry_ts_ms=1700000000000,
        )
        self.runner.open_positions[pos_id] = pos

        # Update 1: Price rallies to $51,600 (+1.6R MFE) -> Must trigger Break-Even
        self.runner.update_open_positions(
            symbol="BTCUSDT",
            current_high=51_600.0,
            current_low=50_500.0,
            current_close=51_500.0,
        )
        self.assertTrue(pos.is_break_even)
        self.assertGreaterEqual(pos.current_stop_price, 50_100.0)  # Entry + 0.1R fee buffer
        self.assertEqual(len(self.runner.open_positions), 1)

        # Update 2: Price hits target $54,000 -> Must exit on TAKE_PROFIT
        self.runner.update_open_positions(
            symbol="BTCUSDT",
            current_high=54_100.0,
            current_low=52_000.0,
            current_close=54_050.0,
        )
        self.assertEqual(len(self.runner.open_positions), 0)
        self.assertEqual(len(self.runner.closed_positions), 1)

        closed = self.runner.closed_positions[0]
        self.assertEqual(closed.exit_reason, "TAKE_PROFIT")
        self.assertAlmostEqual(closed.realized_r, 4.0, places=1)

        # Verify Track Record Persistence
        summary = self.runner.persist_track_record_summary()
        self.assertEqual(summary["performance_metrics"]["total_closed_trades"], 1)
        self.assertEqual(summary["performance_metrics"]["win_rate_pct"], 100.0)
        self.assertGreater(summary["performance_metrics"]["net_realized_r"], 3.5)
        self.assertTrue(summary["custody_architecture"]["is_within_budget"])


if __name__ == "__main__":
    unittest.main()
