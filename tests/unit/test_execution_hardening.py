"""Unit tests for STRATA Execution Precision & Idempotency Hardening."""
import pytest
from execution.precision_engine import (
    DuplicateOrderIntentError,
    IdempotencyExecutionGuard,
    generate_deterministic_order_id,
    round_to_step_size,
    round_to_tick_size,
)


def test_round_to_step_size():
    assert round_to_step_size(1.23456, 0.001) == 1.234
    assert round_to_step_size(0.0987, 0.01) == 0.09
    assert round_to_step_size(15.75, 1.0) == 15.0


def test_round_to_tick_size():
    assert round_to_tick_size(65432.18, 0.1) == 65432.2
    assert round_to_tick_size(0.04567, 0.0001) == 0.0457


def test_deterministic_order_id_generation():
    id1 = generate_deterministic_order_id("BTCUSDT", "DEC_001", 1700000000000)
    id2 = generate_deterministic_order_id("BTCUSDT", "DEC_001", 1700000000000)
    assert id1 == id2
    assert id1.startswith("STRATA_BTCUSDT_")

    id3 = generate_deterministic_order_id("ETHUSDT", "DEC_001", 1700000000000)
    assert id1 != id3


def test_idempotency_guard_blocks_duplicates():
    guard = IdempotencyExecutionGuard()
    # First submission -> allowed
    guard.assert_idempotent("BTCUSDT", "DEC_100", 1700000000000)

    # Second submission of identical decision -> REJECTED
    with pytest.raises(DuplicateOrderIntentError, match="DUPLICATE ORDER INTENT REJECTED"):
        guard.assert_idempotent("BTCUSDT", "DEC_100", 1700000000000)

    # Different candle timestamp -> allowed
    guard.assert_idempotent("BTCUSDT", "DEC_100", 1700000060000)
