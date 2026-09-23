"""Unit tests for ComplianceEngine and ObservabilityCollector."""
import pytest
from crypto_platform.core.domain import ExecutionOrder, OrderIntent, OrderSide, OrderStatus, OrderType, TimeInForce
from crypto_platform.observability import ObservabilityCollector
from crypto_platform.security.compliance import ComplianceEngine, NonCustodialSecurityError


def test_compliance_non_custodial_permission_audit():
    engine = ComplianceEngine()

    # Valid permissions
    engine.verify_non_custodial_permissions({"read": True, "trade": True, "withdraw": False})

    # Withdrawal permissions must raise error immediately
    with pytest.raises(NonCustodialSecurityError, match="Withdrawal permissions enabled"):
        engine.verify_non_custodial_permissions({"read": True, "trade": True, "withdraw": True})

    # Transfer permissions must raise error immediately
    with pytest.raises(NonCustodialSecurityError, match="Transfer permissions enabled"):
        engine.verify_non_custodial_permissions({"read": True, "trade": True, "transfer": True})


def test_compliance_jurisdiction_check():
    engine = ComplianceEngine(restricted_jurisdictions={"KP", "SY", "IR"})
    assert engine.check_jurisdiction("US") is True
    assert engine.check_jurisdiction("DE") is True
    assert engine.check_jurisdiction("KP") is False


def test_compliance_wash_trading_detection():
    engine = ComplianceEngine()

    # Resting Buy order at $60,000 for tenant t_01
    resting_order = ExecutionOrder(
        order_id="o_resting",
        client_order_id="c_resting",
        tenant_id="t_01",
        account_id="acct_01",
        venue="binance",
        symbol="BTCUSDT",
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        time_in_force=TimeInForce.GTC,
        quantity=0.1,
        price=60000.0,
        status=OrderStatus.ACKNOWLEDGED,
    )

    # Intent from same tenant to Sell at $59,900 (would cross resting buy!)
    crossing_sell_intent = OrderIntent(
        intent_id="i_crossing",
        strategy_id="s_01",
        tenant_id="t_01",
        account_id="acct_01",
        symbol="BTCUSDT",
        direction=-1,
        target_size=0.1,
        limit_price=59900.0,
    )

    is_wash, reason = engine.check_wash_trading(crossing_sell_intent, [resting_order])
    assert is_wash is True
    assert "Wash-trading risk" in reason

    # Non-crossing sell at $60,100 passes
    safe_sell_intent = OrderIntent(
        intent_id="i_safe",
        strategy_id="s_01",
        tenant_id="t_01",
        account_id="acct_01",
        symbol="BTCUSDT",
        direction=-1,
        target_size=0.1,
        limit_price=60100.0,
    )
    is_wash, _ = engine.check_wash_trading(safe_sell_intent, [resting_order])
    assert is_wash is False


def test_observability_collector():
    collector = ObservabilityCollector()
    collector.set_subsystem_health("market_data", "HEALTHY", "All feeds streaming")
    collector.set_subsystem_health("risk_engine", "HEALTHY", "All 22 boundaries nominal")

    collector.inc_counter("ticks_processed", 150)
    collector.set_gauge("current_equity", 102500.0)
    collector.record_latency("order_routing", 1.25)
    collector.record_latency("order_routing", 1.85)

    collector.trigger_alert("WARNING", "RECONCILER", "Minor sequence gap detected and healed")

    health = collector.get_system_health()
    assert health["overall_status"] == "HEALTHY"
    assert health["counters"]["ticks_processed"] == 150
    assert health["gauges"]["current_equity"] == 102500.0
    assert "order_routing" in health["latencies"]
    assert len(health["recent_alerts"]) == 1
