"""Unit Test Suite for STRATA Fractal Event Graph and Canonical Event Contracts."""
from __future__ import annotations

import pytest

from market_model.fractal_event_graph import (
    CanonicalFractalEvent,
    EventType,
    FractalEventGraph,
    InvalidationCondition,
    create_order_block_event,
    create_swing_event,
)


class TestFractalEventGraph:

    def test_causal_invariant_lookahead_rejection(self):
        """Verify that any event with available_time < event_time is strictly rejected."""
        with pytest.raises(ValueError, match="Causal lookahead violation"):
            CanonicalFractalEvent(
                event_id="TEST_LOOKAHEAD",
                event_type=EventType.SWING_HIGH,
                symbol="BTCUSDT",
                timeframe="1d",
                direction=-1,
                event_time=2000,
                available_time=1000,  # Lookahead! Available before it happened
                anchor_price=50000.0,
                boundary_high=50500.0,
                boundary_low=49500.0,
                source_candle_index=10,
                confirmation_candle_index=9,
                source_candle_count=1,
                invalidation_rule=InvalidationCondition.OPPOSITE_STRUCTURAL_BREAK,
                invalidation_price=50000.0,
            )

    def test_swing_event_creation_and_causal_availability(self):
        """Verify swing high is only visible after its confirmation timestamp."""
        graph = FractalEventGraph()

        # Pivot candle occurs at t=1000, confirmed at t=1060 (after 2 confirmation bars)
        swing = create_swing_event(
            symbol="BTCUSDT",
            timeframe="1h",
            swing_type="HIGH",
            pivot_price=60000.0,
            pivot_ts=1000,
            confirmation_ts=1060,
            pivot_idx=50,
            confirmation_idx=52,
        )
        graph.register_event(swing)

        # At t=1030 (before confirmation), event must NOT be visible
        visible_early = graph.get_events_visible_at("BTCUSDT", current_time_ms=1030)
        assert len(visible_early) == 0

        # At t=1060 (at confirmation), event becomes visible
        visible_on_time = graph.get_events_visible_at("BTCUSDT", current_time_ms=1060)
        assert len(visible_on_time) == 1
        assert visible_on_time[0].event_id == swing.event_id

    def test_parent_child_cross_timeframe_lineage(self):
        """Verify hierarchical linking from HTF swing down to MTF Order Block."""
        graph = FractalEventGraph()

        htf_swing = create_swing_event(
            symbol="ETHUSDT",
            timeframe="1d",
            swing_type="LOW",
            pivot_price=2500.0,
            pivot_ts=10000,
            confirmation_ts=10200,
            pivot_idx=100,
            confirmation_idx=102,
        )
        graph.register_event(htf_swing)

        mtf_ob = create_order_block_event(
            symbol="ETHUSDT",
            timeframe="4h",
            ob_type="DEMAND",
            high_price=2520.0,
            low_price=2490.0,
            creation_ts=10050,
            confirmation_ts=10100,
            candle_idx=200,
            parent_swing_id=htf_swing.event_id,
        )
        graph.register_event(mtf_ob)

        # Verify child registration in parent
        parent = graph.events[htf_swing.event_id]
        assert mtf_ob.event_id in parent.child_event_ids

        # Verify shared root event
        shared_root = graph.find_shared_root_event(htf_swing.event_id, mtf_ob.event_id)
        assert shared_root == htf_swing.event_id

    def test_duplicate_portfolio_exposure_prevention(self):
        """Verify that candidate signals originating from the same root market event are flagged."""
        graph = FractalEventGraph()

        root_id = "SWG_BTC_1d_1000_H"
        cand_set2 = {
            "symbol": "BTCUSDT",
            "set_id": "SET_2",
            "direction": -1,
            "root_event_id": root_id,
            "entry_price": 60000.0,
        }
        cand_set3 = {
            "symbol": "BTCUSDT",
            "set_id": "SET_3",
            "direction": -1,
            "root_event_id": root_id,
            "entry_price": 59900.0,
        }
        cand_independent = {
            "symbol": "BTCUSDT",
            "set_id": "SET_1",
            "direction": 1,
            "root_event_id": "SWG_BTC_1M_500_L",
            "entry_price": 40000.0,
        }

        candidates = [cand_set2, cand_set3, cand_independent]
        conflicts = graph.detect_overlapping_exposure(candidates)

        # cand_set3 should be flagged as overlapping with cand_set2 because both share root_id
        assert len(conflicts) == 1
        conflicted_trade, conflict_root = conflicts[0]
        assert conflicted_trade["set_id"] == "SET_3"
        assert conflict_root == root_id
