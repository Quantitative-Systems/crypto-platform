"""
Comprehensive Test Suite: Low Latency Event Bus, Binary Schemas & Security/Multi-Tenancy.
Validates:
- FastEventBus ring buffer pub/sub and latency tracking
- BinarySchemaCodec serialization / deserialization
- RBACManager roles and permissions
- TenantManager isolation
"""

import time
import pytest
from low_latency.event_bus import FastEventBus, TimestampedEvent
from low_latency.binary_serializer import BinaryTick, BinarySchemaCodec
from security.rbac_manager import RBACManager, UserRole, Permission
from multi_tenancy.tenant_manager import TenantManager


def test_fast_event_bus_ring_buffer():
    bus = FastEventBus(capacity=100)
    received = []

    def on_tick(evt: TimestampedEvent):
        received.append(evt.payload)

    bus.subscribe("TICK", on_tick)
    for i in range(10):
        bus.publish("TICK", f"tick_{i}")

    processed = bus.dispatch_batch(max_batch_size=50)
    assert processed == 10
    assert len(received) == 10
    stats = bus.get_latency_stats_us()
    assert stats["samples"] == 10
    assert stats["p50_us"] >= 0.0


def test_binary_tick_codec():
    tick = BinaryTick(
        timestamp_ns=time.perf_counter_ns(),
        price=60000.50,
        quantity=1.25,
        sequence_id=987654,
        is_buy=True,
        is_snapshot=False,
    )
    raw = tick.serialize()
    assert len(raw) == 34

    decoded = BinaryTick.deserialize(raw)
    assert decoded.price == tick.price
    assert decoded.quantity == tick.quantity
    assert decoded.sequence_id == tick.sequence_id
    assert decoded.is_buy is True


def test_rbac_manager_permissions():
    rbac = RBACManager()
    user_id = "test-user-quant"
    rbac.assign_role(user_id, UserRole.QUANT_ENGINEER)

    assert rbac.check_permission(user_id, Permission.VIEW_PORTFOLIO) is True
    assert rbac.check_permission(user_id, Permission.EXECUTE_BACKTEST) is True
    assert rbac.check_permission(user_id, Permission.TRIGGER_KILL_SWITCH) is False
    assert rbac.check_permission(user_id, Permission.MANAGE_TENANTS) is False

    admin_id = "test-admin"
    rbac.assign_role(admin_id, UserRole.SUPER_ADMIN)
    assert rbac.check_permission(admin_id, Permission.TRIGGER_KILL_SWITCH) is True
    assert rbac.check_permission(admin_id, Permission.MANAGE_TENANTS) is True



def test_tenant_manager_isolation():
    tm = TenantManager()
    t1 = tm.create_tenant("Fund Alpha", tier="ENTERPRISE")
    t2 = tm.create_tenant("Prop Beta", tier="STANDARD")

    assert t1.tenant_id != t2.tenant_id

    # Create account in t1
    acc1 = tm.create_account(t1.tenant_id, "Main Account", initial_capital_usd=50_000.0)

    # Validate isolation: t2 cannot view or access acc1
    t2_accounts = tm.list_accounts(t2.tenant_id)
    assert not any(a["account_id"] == acc1["account_id"] for a in t2_accounts)
