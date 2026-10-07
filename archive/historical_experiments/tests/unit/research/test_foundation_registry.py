"""
Unit tests for the QCP Foundation Registry (HTF Bias -> MTF Setup -> LTF Entry).

These tests defend the FOUNDATION invariants:
  1. One canonical 6-Set ladder, derived from a single source of truth.
  2. Every registered family is classified (no silent drift).
  3. Risk policy matches the enforcing code (1% risk, 1:4 planned RR floor).
  4. News blackout matches the live NewsProvider window and covers only fast-LTF sets.
  5. Performance targets are declared as UNPROVEN and are arithmetically consistent.
"""

import json

import pytest

from config.timeframe_sets import CANONICAL_6_TIMEFRAME_SETS, get_canonical_timeframe_set
from research.foundation_registry import (
    LAYER_HTF_BIAS,
    LAYER_HTF_TARGET,
    LAYER_LTF_ENTRY,
    LAYER_LTF_STOP,
    LAYER_MTF_SETUP,
    LAYER_MTF_TRAILING,
    build_foundation_inventory,
    build_news_policy,
    build_performance_targets,
    build_risk_policy,
    build_timeframe_sets,
    emit_foundation_manifest,
    news_affected_set_ids,
)
from research.replayer.timeframe_aligner import (
    CANONICAL_TIMEFRAME_SETS,
    TIMEFRAME_DURATIONS_SEC,
    TimeframeAligner,
)
from strategy_engine.news.news_provider import MemoryNewsProvider, NewsEvent, NewsImpact


# The operator directive, stated literally. If this fails, the ladder has been changed.
DIRECTIVE_LADDER = {
    "SET_1": ("1M", "1W", "1D"),
    "SET_2": ("1W", "1D", "4H"),
    "SET_3": ("1D", "4H", "1H"),
    "SET_4": ("4H", "1H", "15M"),
    "SET_5": ("1H", "15M", "5M"),
    "SET_6": ("15M", "5M", "1m"),
}


def test_foundation_defines_exactly_six_timeframe_sets():
    assert len(CANONICAL_6_TIMEFRAME_SETS) == 6
    assert len(build_timeframe_sets()) == 6
    assert len(CANONICAL_TIMEFRAME_SETS) == 6


def test_six_set_ladder_matches_operator_directive():
    for set_id, (htf, mtf, ltf) in DIRECTIVE_LADDER.items():
        cfg = get_canonical_timeframe_set(set_id)
        assert (cfg.htf, cfg.mtf, cfg.ltf) == (htf, mtf, ltf), f"{set_id} ladder drift"


def test_timeframe_aligner_derives_from_config_not_a_duplicate_literal():
    """The replayer must consume the single source of truth, never a second hard-coded copy."""
    for set_id, cfg in CANONICAL_6_TIMEFRAME_SETS.items():
        aligner_set = TimeframeAligner.get_set(set_id)
        assert (aligner_set.htf, aligner_set.mtf, aligner_set.ltf) == (cfg.htf, cfg.mtf, cfg.ltf)
        assert cfg.style_name in aligner_set.description


def test_ladder_is_strictly_hierarchical_on_every_set():
    for tf in build_timeframe_sets():
        htf_sec = TIMEFRAME_DURATIONS_SEC[tf["htf"]]
        mtf_sec = TIMEFRAME_DURATIONS_SEC[tf["mtf"]]
        ltf_sec = TIMEFRAME_DURATIONS_SEC[tf["ltf"]]
        assert htf_sec > mtf_sec > ltf_sec, f"{tf['set_id']} is not strictly hierarchical"


def test_invalid_set_id_fails_closed():
    with pytest.raises(ValueError):
        get_canonical_timeframe_set("SET_7")


def test_every_registered_family_is_classified():
    inventory = build_foundation_inventory()
    assert inventory["unclassified_families"] == []
    assert inventory["classification_complete"] is True


def test_pipeline_layers_are_populated_with_correct_component_kinds():
    families = build_foundation_inventory()["families"]
    expected = {
        LAYER_HTF_BIAS: "AbstractBias",
        LAYER_MTF_SETUP: "AbstractSetup",
        LAYER_LTF_ENTRY: "AbstractEntry",
        LAYER_LTF_STOP: "AbstractStopLoss",
        LAYER_HTF_TARGET: "AbstractTakeProfit",
        LAYER_MTF_TRAILING: "AbstractTrailing",
    }
    for layer, kind in expected.items():
        records = families[layer]
        assert len(records) > 0, f"{layer} is empty"
        assert {r["component_kind"] for r in records} == {kind}


def test_family_aliases_are_explicitly_flagged():
    """Aliases must be reported, never silently double-counted as unique mechanisms."""
    inventory = build_foundation_inventory()
    for layer, counts in inventory["family_counts"].items():
        records = inventory["families"][layer]
        assert counts["registered_ids"] == len(records)
        assert counts["registry_aliases"] == sum(1 for r in records if r["is_registry_alias"])
        assert counts["unique_classes"] == len({r["component_class"] for r in records})


def test_risk_policy_enforces_one_percent_and_four_r_and_structural_anchors():
    risk = build_risk_policy()
    assert risk["max_risk_per_trade_fraction"] == 0.01
    assert risk["max_risk_per_trade_pct"] == 1.0
    assert risk["min_planned_rr_floor"] == 4.0
    assert risk["rr_cap"] is None
    # LTF stop -> HTF target -> MTF trail (the canonical risk-management chain)
    assert risk["stop_anchor"] == "LTF_STRUCTURAL"
    assert risk["target_anchor"] == "HTF_STRUCTURAL"
    assert risk["trailing_anchor"] == "MTF_STRUCTURAL"
    assert risk["position_sizing_formula"].startswith("units = (equity * max_risk_fraction)")


def test_risk_policy_matches_live_risk_engine_constants():
    from risk_engine.contracts.risk_config import RiskConfig
    from risk_engine.sizing.position_sizer import PositionSizer
    from risk_engine.validators.drawdown_validator import DrawdownValidator
    from risk_engine.validators.exposure_validator import ExposureValidator

    risk = build_risk_policy()
    cfg = RiskConfig()
    assert risk["min_planned_rr_floor"] == cfg.min_rr_floor
    assert risk["max_risk_per_trade_fraction"] == min(
        cfg.max_risk_fraction, PositionSizer.MAX_RISK_FRACTION
    )
    assert risk["circuit_breakers"]["daily_drawdown_pct"] == (
        DrawdownValidator.MAX_DAILY_DRAWDOWN_PCT * 100.0
    )
    assert risk["circuit_breakers"]["weekly_drawdown_pct"] == (
        DrawdownValidator.MAX_WEEKLY_DRAWDOWN_PCT * 100.0
    )
    assert risk["circuit_breakers"]["systemic_peak_to_trough_pct"] == (
        DrawdownValidator.MAX_SYSTEMIC_DRAWDOWN_PCT * 100.0
    )
    assert risk["exposure_limits"]["max_open_positions"] == ExposureValidator.MAX_OPEN_POSITIONS


def test_news_blackout_applies_only_to_fast_ltf_sets():
    """Sets 4-6 (LTF <= 15m) are news-sensitive; Sets 1-3 are structural and unaffected."""
    policy = build_news_policy()
    assert news_affected_set_ids() == ["SET_4", "SET_5", "SET_6"]
    assert policy["unaffected_timeframe_sets"] == ["SET_1", "SET_2", "SET_3"]
    assert policy["missing_historical_news_data"] == "FAIL_CLOSED"
    assert policy["lookahead"] == "FORBIDDEN"


def test_declared_blackout_window_matches_live_news_provider_behaviour():
    """The registry's declared window must match what MemoryNewsProvider actually enforces."""
    policy = build_news_policy()
    before = policy["blackout_seconds_before"]
    after = policy["blackout_seconds_after"]

    provider = MemoryNewsProvider()
    event_ts = 1_700_000_000
    provider.add_event(NewsEvent(
        event_id="evt-1",
        timestamp=event_ts,
        event_name="TEST_HIGH_IMPACT",
        impact=NewsImpact.HIGH,
        affected_symbols=["BTC/USDT"],
    ))

    # Inside the window on both sides
    assert provider.is_news_blackout("BTC/USDT", event_ts)[0] is True
    assert provider.is_news_blackout("BTC/USDT", event_ts - before)[0] is True
    assert provider.is_news_blackout("BTC/USDT", event_ts + after)[0] is True

    # Just outside the window on both sides
    assert provider.is_news_blackout("BTC/USDT", event_ts - before - 1)[0] is False
    assert provider.is_news_blackout("BTC/USDT", event_ts + after + 1)[0] is False


def test_performance_targets_are_declared_unproven_never_as_results():
    targets = build_performance_targets()
    assert targets["claim_status"] == "UNPROVEN_TARGET_ONLY"
    assert targets["validated_alpha_strategies"] == 0
    assert "not performance claims" in targets["integrity_note"]
    assert targets["evaluation_scope"] == "UNTOUCHED_OUT_OF_SAMPLE_PARTITION"


def test_performance_target_arithmetic_is_consistent():
    targets = build_performance_targets()
    min_rr = targets["min_planned_rr"]

    # Breakeven win rate at the mandatory RR floor
    assert targets["breakeven_win_rate_at_min_rr"] == round(1.0 / (1.0 + min_rr), 4)
    assert targets["breakeven_win_rate_at_min_rr"] == 0.20

    # Declared bands and hard floors must agree
    assert targets["win_rate_target_band"] == [0.60, 0.80]
    assert targets["win_rate_hard_floor"] == targets["win_rate_target_band"][0]
    assert targets["profit_factor_target_band"] == [2.0, 3.0]
    assert targets["profit_factor_hard_floor"] == targets["profit_factor_target_band"][0]

    # Implied expectancy must be the honest consequence of the declared win rate + RR
    assert targets["implied_expectancy_r_at_60pct_win"] == round(0.60 * min_rr - 0.40, 4)
    assert targets["implied_expectancy_r_at_80pct_win"] == round(0.80 * min_rr - 0.20, 4)
    # ...and must be honestly far above the platform's existing promotion bar
    assert targets["implied_expectancy_r_at_60pct_win"] > (
        targets["platform_promotion_bar"]["min_expectancy_r"] * 5
    )


def test_manifest_emits_valid_json_and_round_trips(tmp_path):
    target = tmp_path / "FOUNDATION_MANIFEST.json"
    written = emit_foundation_manifest(target)
    assert written == target
    assert written.exists()

    payload = json.loads(written.read_text(encoding="utf-8"))
    assert payload["foundation"] == "HTF_BIAS__MTF_SETUP__LTF_ENTRY"
    assert len(payload["timeframe_sets"]) == 6
    assert payload["classification_complete"] is True
    assert payload["pipeline"] == [LAYER_HTF_BIAS, LAYER_MTF_SETUP, LAYER_LTF_ENTRY]
    assert payload["post_entry_management"] == [
        LAYER_LTF_STOP, LAYER_HTF_TARGET, LAYER_MTF_TRAILING
    ]


def test_strategy_grammar_scales_agree_with_the_canonical_ladder():
    """
    `research/strategy_grammar.TimeframeSet` stores (htf_scale, mtf_scale) relative to the
    base LTF. Those scales must reproduce the canonical ladder durations exactly, otherwise
    the grammar and the ladder would describe two different market resolutions.
    """
    from research.strategy_grammar import TimeframeSet as GrammarSet, get_scales_for_set

    grammar_to_set_id = {
        GrammarSet.SET_1_MACRO: "SET_1",
        GrammarSet.SET_2_CORE: "SET_2",
        GrammarSet.SET_3_SWING: "SET_3",
        GrammarSet.SET_4_INTRADAY: "SET_4",
        GrammarSet.SET_5_ACTIVE: "SET_5",
        GrammarSet.SET_6_SCALP: "SET_6",
    }
    assert len(list(GrammarSet)) == 6

    for grammar_set, set_id in grammar_to_set_id.items():
        htf_scale, mtf_scale = get_scales_for_set(grammar_set)
        cfg = CANONICAL_6_TIMEFRAME_SETS[set_id]
        ltf_sec = TIMEFRAME_DURATIONS_SEC[cfg.ltf]
        assert htf_scale * ltf_sec == TIMEFRAME_DURATIONS_SEC[cfg.htf], (
            f"{set_id}: HTF scale {htf_scale} does not reproduce {cfg.htf}"
        )
        assert mtf_scale * ltf_sec == TIMEFRAME_DURATIONS_SEC[cfg.mtf], (
            f"{set_id}: MTF scale {mtf_scale} does not reproduce {cfg.mtf}"
        )