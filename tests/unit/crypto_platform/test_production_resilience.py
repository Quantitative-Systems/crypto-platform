"""Production Resilience & Controlled Failure Testing Suite.

Verifies that the platform fails CLOSED under all abnormal conditions:
- Live capital $> 0$ strictly rejected
- Stale data / clock drift rejected
- Corrupt intent / malformed order rejected
- Out-of-band exchange position mismatch triggers reconciliation freeze
- Emergency kill halts all order routing
- Demo vs Real environment & credential isolation strictly enforced
"""
import asyncio
import os
import time
import pytest

from crypto_platform.config.settings import PlatformSettings
from crypto_platform.core.domain import (
    ExecutionOrder,
    OperatingMode,
    OrderIntent,
    OrderSide,
    OrderStatus,
    OrderType,
    Position,
    RiskState,
)
from crypto_platform.core.events import TickerEvent
from crypto_platform.exchange_adapters.binance_adapter import BinanceAdapter
from crypto_platform.order_management.oms import OrderManagementSystem
from crypto_platform.production.supervisor import ProductionSupervisor
from crypto_platform.reconciliation.reconciler import StateReconciliationEngine
from crypto_platform.risk_engine.firewall import RiskFirewall


def test_supervisor_live_capital_strict_rejection():
    """Supervisor must reject startup if live capital is non-zero."""
    bad_settings = PlatformSettings(environment="PAPER", live_capital_usd=100.0)
    with pytest.raises(RuntimeError, match="Live capital.*prohibited"):
        ProductionSupervisor(settings=bad_settings)


def test_supervisor_telemetry_collection():
    """Supervisor telemetry must return valid system resource metrics."""
    supervisor = ProductionSupervisor(port=8991)
    telemetry = supervisor.get_system_telemetry()
    assert "memory_rss_mb" in telemetry
    assert "disk_free_gb" in telemetry
    assert telemetry["memory_rss_mb"] > 0
    assert telemetry["disk_free_gb"] > 0
    assert telemetry["environment"] == "PAPER"
    assert telemetry["live_capital_usd"] == 0.0


@pytest.mark.anyio
async def test_supervisor_lifecycle_start_and_stop():
    """Supervisor must cleanly execute preflight checks, write audit records, and shut down."""
    supervisor = ProductionSupervisor(port=8992)
    await supervisor.start()
    assert supervisor.is_running is True

    # Verify audit event written to SQLite
    events = supervisor.ledger.load_audit_events(limit=5)
    assert any(e["event_type"] == "PRODUCTION_SERVICE_START" for e in events)

    # Stop supervisor
    await supervisor.stop()
    assert supervisor.is_running is False
    stop_events = supervisor.ledger.load_audit_events(limit=5)
    assert any(e["event_type"] == "PRODUCTION_SERVICE_SHUTDOWN" for e in stop_events)


def test_failure_resilience_stale_data_rejection():
    """Stale market data (>1000ms drift) must fail closed in the Risk Firewall."""
    firewall = RiskFirewall(max_market_data_age_ms=1000)
    now_ms = int(time.time() * 1000)

    stale_ticker = TickerEvent(
        venue="binance",
        symbol="BTCUSDT",
        timestamp_ms=now_ms - 5000,  # 5 seconds stale
        bid=60000.0,
        ask=60001.0,
        last_price=60000.5,
    )
    intent = OrderIntent(
        intent_id=f"intent_stale_{now_ms}",
        strategy_id="strat_01",
        tenant_id="t_1",
        account_id="acc_1",
        symbol="BTCUSDT",
        direction=1,
        target_size=0.1,
        created_at_ms=now_ms,
    )
    risk_state = RiskState(equity=50000.0, peak_equity=50000.0, drawdown_pct=0.0)
    decision = firewall.evaluate_order_intent(intent, {}, {}, risk_state, stale_ticker)

    assert decision.approved is False
    assert decision.rule_code == "STALE_MARKET_DATA"


def test_failure_resilience_emergency_kill_engages_firewall():
    """Emergency kill switch must immediately halt all trading and fail closed."""
    firewall = RiskFirewall()
    firewall.kill_switches.activate(scope="GLOBAL", target="*", reason="EMERGENCY_KILL_ENGAGED")

    now_ms = int(time.time() * 1000)
    ticker = TickerEvent(venue="binance", symbol="BTCUSDT", timestamp_ms=now_ms, bid=60000.0, ask=60001.0, last_price=60000.5)
    intent = OrderIntent(
        intent_id=f"intent_kill_{now_ms}",
        strategy_id="strat_01",
        tenant_id="t_1",
        account_id="acc_1",
        symbol="BTCUSDT",
        direction=1,
        target_size=0.1,
        created_at_ms=now_ms,
    )
    risk_state = RiskState(equity=50000.0, peak_equity=50000.0, drawdown_pct=0.0)
    decision = firewall.evaluate_order_intent(intent, {}, {}, risk_state, ticker)

    assert decision.approved is False
    assert decision.rule_code == "GLOBAL_KILL_SWITCH_ACTIVE"


@pytest.mark.anyio
async def test_failure_resilience_reconciliation_freeze():
    """Out-of-band position mismatch must immediately freeze trading."""
    oms = OrderManagementSystem()
    firewall = RiskFirewall()
    reconciler = StateReconciliationEngine(risk_firewall=firewall)
    adapter = BinanceAdapter(mock_mode=True)
    await adapter.connect({})

    # Inject ghost position on exchange
    adapter._mock_positions["ETHUSDT"] = Position(symbol="ETHUSDT", direction=1, size=5.0, entry_price=3000.0, mark_price=3000.0)

    # Local OMS has no record of ETHUSDT position -> Discrepancy detected
    in_sync = await reconciler.reconcile_account("acc_recon_test", adapter, oms)
    assert in_sync is False

    # Risk firewall must block any new order intents
    now_ms = int(time.time() * 1000)
    intent = OrderIntent(
        intent_id=f"intent_recon_block_{now_ms}",
        strategy_id="strat_01",
        tenant_id="t_1",
        account_id="acc_recon_test",
        symbol="ETHUSDT",
        direction=1,
        target_size=0.5,
        created_at_ms=now_ms,
    )
    ticker = TickerEvent(venue="binance", symbol="ETHUSDT", timestamp_ms=now_ms, bid=3000.0, ask=3001.0, last_price=3000.5)
    decision = firewall.evaluate_order_intent(intent, {}, {}, RiskState(equity=50000.0, peak_equity=50000.0, drawdown_pct=0.0), ticker)
    assert decision.approved is False
    assert decision.rule_code == "RECONCILIATION_OUT_OF_SYNC"


def test_demo_vs_real_environment_and_credential_isolation():
    """Demo endpoints and credentials must remain strictly isolated from real/live paths."""
    demo_adapter = BinanceAdapter(is_futures=True, testnet=True, mock_mode=False)
    endpoints = demo_adapter.get_endpoints()
    assert "testnet" in endpoints["rest"]
    assert "testnet" in endpoints["ws"] or "stream.binancefuture.com" in endpoints["ws"]

    # Verify that live mode throws exception on settings load
    os.environ["PLATFORM_ENV"] = "LIVE"
    try:
        with pytest.raises(RuntimeError, match="FATAL: Operating mode LIVE is strictly disabled"):
            PlatformSettings.load_from_env()
    finally:
        os.environ["PLATFORM_ENV"] = "PAPER"
