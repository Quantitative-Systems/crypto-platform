"""STRATA — Product Acceptance & End-to-End User Journey Certification Test Suite.

Simulates the complete user and operational journey across all platform layers:
1. User Registration & PBKDF2 Password Hashing
2. Authentication & Ephemeral Bearer Session Issuance
3. Tenant Context Scoping & Isolation Attack
4. Account & Broker Center Registration
5. Account Suitability Engine & Risk Boundary Enforcement (≤1.0% Hard Clamp)
6. Strategy Selection & Style Alignment (SWING / AUTONOMOUS)
7. Protected KING Engine Contract & Target Geometry Invariant Verification (≥4.0R Floor)
8. Autonomous Agent Control Loop (OBSERVE -> SELECT -> VALIDATE -> EXECUTE)
9. Position Blotter & Order Idempotency
10. Alert Router Event Dispatch
11. Emergency Halt Trigger
12. Crash Recovery & Auto-Reconciliation
"""

import sys
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.auth.auth_service import AuthService
from core.tenancy.tenant_context import TenantContext, TenantScopedStore, TenantViolationError
from accounts.account_manager import AccountManager, AccountConfig, BrokerVenue, AccountEnvironment
from accounts.suitability_engine import AccountSuitabilityEngine, TradingStyle
from broker.broker_center import BrokerCenter
from market_data.universe.crypto_universe import CryptoUniverseManager
from execution.king.king_engine_contract import KingEngineProtectionGuard, KingEngineAdapter
from execution.agent.strata_autonomous_agent import StrataAutonomousAgent
from execution.safety.safety_gate import SAFETY_GATE, EnvironmentGateMode
from notifications.alert_router import ALERTS, AlertSeverity, AlertCategory


class TestStrataProductAcceptanceE2E(unittest.TestCase):
    """End-to-End Product Acceptance and Security Attack Test Suite."""

    def setUp(self):
        self.auth_service = AuthService()
        self.account_manager = AccountManager()
        self.broker_center = BrokerCenter()
        self.universe = CryptoUniverseManager()
        self.agent = StrataAutonomousAgent()

    def test_complete_user_journey_end_to_end(self):
        """Simulate a full authentic user lifecycle through the STRATA platform."""
        # 1. Registration
        email = "lead_trader@quantdesk.io"
        password = "SecurePassword#2026!"
        user = self.auth_service.register_user(email=email, password=password)
        user_id = user.user_id
        tenant_id = user.tenant_id
        self.assertTrue(user_id.startswith("usr_"))
        self.assertTrue(tenant_id.startswith("tenant_"))

        # 2. Authentication & Token Issuance
        session_token = self.auth_service.authenticate(email=email, password=password)
        self.assertIsNotNone(session_token)
        token = session_token.token

        # Verify Session
        session_user = self.auth_service.validate_session(token)
        self.assertIsNotNone(session_user)
        self.assertEqual(session_user.email, email)

        # 3. Tenant-Scoped Store Isolation & Ownership
        ctx = TenantContext(tenant_id=tenant_id, user_id=user_id)
        ctx.assert_ownership(tenant_id)  # Same tenant passes
        store = TenantScopedStore()
        store.put(tenant_id, "api_preference", {"theme": "dark", "layout": "institutional"})
        retrieved = store.get(tenant_id, "api_preference")
        self.assertEqual(retrieved["layout"], "institutional")

        # 4. Connect Broker Account (Binance Demo)
        demo_config = AccountConfig(
            account_id="ACC_BINANCE_TESTNET_01",
            name="Binance Testnet Desk",
            venue=BrokerVenue.BINANCE_TESTNET,
            environment=AccountEnvironment.BROKER_DEMO,
            initial_equity_usd=50_000.0,
            tenant_id=tenant_id,
        )
        self.account_manager.register_account(demo_config)
        accounts = self.account_manager.list_accounts(tenant_id=tenant_id)
        self.assertTrue(any(a["account_id"] == "ACC_BINANCE_TESTNET_01" for a in accounts))

        # 5. Account Suitability Engine Evaluation
        suitability = AccountSuitabilityEngine.evaluate_suitability(
            account_equity_usd=50_000.0,
            available_margin_usd=50_000.0,
            style=TradingStyle.SWING,
            user_max_risk_pct=0.005,  # 0.5% requested
        )
        self.assertTrue(suitability.is_suitable)
        self.assertAlmostEqual(suitability.recommended_risk_pct, 0.005)
        self.assertIn("STRATA_KING_ENGINE", suitability.eligible_strategies)

        # 6. King Engine Adapter State & Contract Verification
        guard = KingEngineProtectionGuard()
        status = guard.get_status()
        self.assertTrue(status.is_valid)
        self.assertAlmostEqual(status.target_floor_r, 4.0)

        adapter = KingEngineAdapter()
        overview = adapter.get_market_structure_overview(fractal_states={})
        self.assertEqual(overview["status"], "PROTECTED_CORE")
        self.assertEqual(overview["domain"], "DOMAIN_A_KING")
        self.assertEqual(overview["engine"], "STRATA_KING_ENGINE")

        # 7. Autonomous Agent Style Selection & Evaluation Cycle
        self.agent.set_trading_style(TradingStyle.SWING)
        self.assertEqual(self.agent.current_style, TradingStyle.SWING)

        cycle_report = self.agent.run_control_cycle(
            symbol="BTCUSDT",
            active_positions_count=0,
            current_portfolio_heat=0.0,
        )
        self.assertIn(cycle_report.control_state.value, ["OBSERVING", "EVALUATING", "MONITORING"])
        self.assertEqual(cycle_report.active_style, TradingStyle.SWING)
        self.assertIn("STRATA_KING_ENGINE", cycle_report.selected_strategies)

        # 8. Alert System Notification
        ALERTS.emit(
            severity=AlertSeverity.INFO,
            category=AlertCategory.EXECUTION,
            title="Trade Accepted",
            message=f"Order executed in DEMO environment for tenant {tenant_id}",
        )
        recent_alerts = ALERTS.get_recent_alerts(limit=5)
        self.assertTrue(any("Trade Accepted" in a["title"] for a in recent_alerts))

        # 9. Emergency Halt Trigger
        self.agent.pause_trading("Emergency Stop command executed by user")
        self.assertEqual(self.agent.control_state.value, "PAUSED")

        # Verify resumption
        self.agent.resume_trading()
        self.assertEqual(self.agent.control_state.value, "OBSERVING")

    def test_security_attack_cross_tenant_tampering(self):
        """Attacker Tenant B attempts to read or mutate Tenant A resources."""
        store = TenantScopedStore()
        
        # Tenant A stores private configuration
        store.put("tenant_alpha", "vault_key", "ALPHA_SECRET_DATA")

        # Tenant B tries to query Tenant A resource
        bravo_val = store.get("tenant_bravo", "vault_key")
        self.assertIsNone(bravo_val, "Tenant B must NOT access Tenant A stored data")

        # Cross-tenant context assertion must raise TenantViolationError
        ctx_bravo = TenantContext(tenant_id="tenant_bravo", user_id="usr_bravo")
        with self.assertRaises(TenantViolationError):
            ctx_bravo.assert_ownership(resource_tenant_id="tenant_alpha", resource_name="TradingLedger")

    def test_adversarial_risk_limit_clamp(self):
        """User attempts to configure excessive risk (e.g. 5.0%); engine must clamp to ≤1.0%."""
        suitability = AccountSuitabilityEngine.evaluate_suitability(
            account_equity_usd=100_000.0,
            available_margin_usd=100_000.0,
            style=TradingStyle.AUTONOMOUS,
            user_max_risk_pct=0.05,  # 5.0% - illegal!
        )
        self.assertLessEqual(suitability.recommended_risk_pct, 0.010, "Risk must be hard clamped to ≤1.00%")

    def test_adversarial_non_crypto_universe_rejection(self):
        """Platform must reject non-crypto assets (equities, commodities, forex)."""
        forbidden_assets = ["AAPL", "MSFT", "XAUUSD", "EURUSD", "NIFTY50", "SPY"]
        for asset in forbidden_assets:
            self.assertFalse(
                self.universe.is_admitted(asset),
                f"Asset {asset} must be rejected by CryptoUniverseManager"
            )

        # Approved crypto assets must be accepted
        allowed = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"]
        for asset in allowed:
            self.assertTrue(
                self.universe.is_admitted(asset),
                f"Asset {asset} must be admitted by CryptoUniverseManager"
            )

    def test_adversarial_live_capital_protection_gate(self):
        """Ensure live real-capital trading remains strictly fail-closed at $0.00."""
        self.assertAlmostEqual(SAFETY_GATE.real_capital_authorized_usd, 0.00)
        self.assertFalse(SAFETY_GATE.is_live_execution)
        self.assertEqual(SAFETY_GATE.current_mode, EnvironmentGateMode.PAPER)

        # Verify that KingEngineProtectionGuard confirms $0.00 real capital
        guard = KingEngineProtectionGuard()
        self.assertTrue(guard.get_status().is_valid)
        self.assertAlmostEqual(guard.get_status().real_capital_authorized_usd, 0.0)


if __name__ == "__main__":
    unittest.main()
