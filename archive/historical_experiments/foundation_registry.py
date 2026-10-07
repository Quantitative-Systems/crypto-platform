"""
QCP Foundation Registry — HTF Bias -> MTF Setup -> LTF Entry.

Machine-readable, single-source-of-truth inventory of the canonical trading foundation:

    HTF BIAS  ->  MTF SETUP  ->  LTF ENTRY
    then after entry:
    LTF STRUCTURAL SL  ->  HTF STRUCTURAL TARGET  ->  MTF STRUCTURAL TRAILING

The inventory is READ LIVE from `ComponentRegistry` after the family modules register
themselves. It therefore cannot drift from executable code: adding a new bias / setup /
entry / stop / target / trailing family and forgetting to classify it causes
`build_foundation_inventory()` to report `UNCLASSIFIED` and the accompanying test to fail.

Structural discipline (inherited from the platform's engineering laws):
  * Bias families are HTF-only. Setup families are MTF-only. Entry families are LTF-only.
  * A timeframe layer is never flattened into another layer.
  * The registry enumerates OPTIONS. It does not assert that any combination is profitable,
    nor that any edge exists. `claim_status` is reported explicitly.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from config.timeframe_sets import CANONICAL_6_TIMEFRAME_SETS
from research.grammar_components import ComponentRegistry
from research.replayer.timeframe_aligner import TIMEFRAME_DURATIONS_SEC
from risk_engine.contracts.risk_config import RiskConfig
from risk_engine.sizing.position_sizer import PositionSizer
from risk_engine.validators.drawdown_validator import DrawdownValidator
from risk_engine.validators.exposure_validator import ExposureValidator

import research.bias_families as bias_families
import research.setup_families as setup_families
import research.entry_families as entry_families
import research.sl_families as sl_families
import research.tp_families as tp_families
import research.trailing_families as trailing_families


FOUNDATION_ID = "HTF_BIAS__MTF_SETUP__LTF_ENTRY"
FOUNDATION_VERSION = "1.0.0"

# Layer identifiers
LAYER_HTF_BIAS = "HTF_BIAS"
LAYER_MTF_SETUP = "MTF_SETUP"
LAYER_LTF_ENTRY = "LTF_ENTRY"
LAYER_LTF_STOP = "LTF_STRUCTURAL_SL"
LAYER_HTF_TARGET = "HTF_STRUCTURAL_TARGET"
LAYER_MTF_TRAILING = "MTF_STRUCTURAL_TRAILING"

_LINEAR_SEQUENCE = ["SET_1", "SET_2", "SET_3", "SET_4", "SET_5", "SET_6"]


# =============================================================================
# Family taxonomy — component CLASS name -> category.
#
# Keyed on class name (never registry id) so deliberate registry aliases inherit the
# correct category automatically and cannot be silently left unclassified.
# =============================================================================

BIAS_CATEGORY_BY_CLASS: Dict[str, str] = {
    "CanonicalSupertrendStochasticBias": "BASELINE",
    "TrendMAAlignmentBias": "TREND",
    "IchimokuCloudBias": "TREND",
    "ADXDirectionalBias": "TREND_STRENGTH",
    "MomRSIRegimeBias": "MOMENTUM",
    "MACDRegimeBias": "MOMENTUM",
    "StochasticRegimeBias": "MOMENTUM",
    "MomentumSlopeBias": "MOMENTUM",
    "StructHHHLBias": "MARKET_STRUCTURE",
    "BreakOfStructureBias": "MARKET_STRUCTURE",
    "ChangeOfCharacterBias": "MARKET_STRUCTURE",
    "OrderBlockBias": "SMC_ZONE",
    "FVGDirectionalBias": "SMC_ZONE",
    "PremiumDiscountZoneBias": "SMC_ZONE",
    "VWAPPositionBias": "VALUE",
    "SqueezeDirectionBias": "VOLATILITY",
    "RegimeTrendBias": "REGIME",
    "RegimeRangeBias": "REGIME",
    "RegimeAnyBias": "REGIME",
    "RegimeCompressionBias": "REGIME",
    "NeutralBias": "NULL_CONTROL",
}

SETUP_CATEGORY_BY_CLASS: Dict[str, str] = {
    "CanonicalSupertrendStochasticSetup": "BASELINE",
    "PullbackSetup": "CONTINUATION",
    "SetupMAPullback": "CONTINUATION",
    "SetupFlagPennant": "CONTINUATION",
    "BreakoutSetup": "BREAKOUT",
    "SetupBreakoutRetest": "BREAKOUT",
    "SetupChochBosRetest": "MARKET_STRUCTURE",
    "SetupOrderBlockRetest": "SMC_ZONE",
    "SetupFVGTap": "SMC_ZONE",
    "SetupLiquiditySweep": "LIQUIDITY",
    "SetupLiquidityGrabReversal": "LIQUIDITY",
    "SetupFibonacciRetracement": "RETRACEMENT",
    "SetupVWAPMeanReversion": "MEAN_REVERSION",
    "SetupSRFlip": "REVERSAL",
    "SetupSqueeze": "VOLATILITY",
    "SetupInsideBar": "COMPRESSION",
    "SetupStochasticCross": "OSCILLATOR",
    "SetupMACDHistogramReversal": "OSCILLATOR",
    "SetupRSIDivergence": "DIVERGENCE",
    "SetupVolumeClimax": "VOLUME",
}

ENTRY_CATEGORY_BY_CLASS: Dict[str, str] = {
    "CanonicalSupertrendStochasticEntry": "BASELINE",
    "EngulfingEntry": "CANDLE_PATTERN",
    "EntryRejectionClose": "CANDLE_PATTERN",
    "MACDCrossoverEntry": "OSCILLATOR",
    "EntryBreakoutClose": "BREAKOUT",
    "EntryChochConfirmation": "MARKET_STRUCTURE",
    "EntrySweepReclaim": "LIQUIDITY",
    "EntryFVGRejection": "SMC_ZONE",
    "EntryDisplacementConfirmation": "DISPLACEMENT",
}

SL_CATEGORY_BY_CLASS: Dict[str, str] = {
    "SLATR": "VOLATILITY",
    "SLLTFSwing": "STRUCTURAL_LTF",
    "SLSetupInvalidation": "SETUP_GEOMETRY",
    "SLFVGInvalidation": "SMC_ZONE",
    "SLBOSInvalidation": "MARKET_STRUCTURE",
}

TP_CATEGORY_BY_CLASS: Dict[str, str] = {
    "TPDynamicR": "R_MULTIPLE",
    "TPHTFStructural": "STRUCTURAL_HTF",
    "TPStructuralSwing": "STRUCTURAL_SWING",
    "TPLTFLiquidity": "LIQUIDITY",
    "TPLiquidityTarget": "LIQUIDITY",
}

TRAILING_CATEGORY_BY_CLASS: Dict[str, str] = {
    "TrailNone": "NONE",
    "TrailChandelier": "VOLATILITY",
    "TrailMTFStructural": "STRUCTURAL_MTF",
    "TrailBOS": "MARKET_STRUCTURE",
    "TrailLTFStructure": "STRUCTURAL_LTF",
}


# =============================================================================
# Risk policy — read from the enforcing code, never from prose.
# =============================================================================

def build_risk_policy() -> Dict[str, Any]:
    """Risk policy as actually enforced by `risk_engine` (source of truth: code)."""
    cfg = RiskConfig()
    max_risk = min(cfg.max_risk_fraction, PositionSizer.MAX_RISK_FRACTION)
    return {
        "max_risk_per_trade_fraction": max_risk,
        "max_risk_per_trade_pct": max_risk * 100.0,
        "min_planned_rr_floor": cfg.min_rr_floor,
        "rr_cap": None,
        "stop_anchor": "LTF_STRUCTURAL",
        "target_anchor": "HTF_STRUCTURAL",
        "trailing_anchor": "MTF_STRUCTURAL",
        "max_leverage": cfg.max_leverage,
        "min_stop_distance_pct": cfg.min_stop_distance_pct,
        "friction_limit_multiple_of_risk": 1.2,
        "friction_model": {
            "taker_fee_rate": 0.0005,
            "slippage_bps": 5.0,
        },
        "circuit_breakers": {
            "daily_drawdown_pct": DrawdownValidator.MAX_DAILY_DRAWDOWN_PCT * 100.0,
            "weekly_drawdown_pct": DrawdownValidator.MAX_WEEKLY_DRAWDOWN_PCT * 100.0,
            "systemic_peak_to_trough_pct": DrawdownValidator.MAX_SYSTEMIC_DRAWDOWN_PCT * 100.0,
        },
        "exposure_limits": {
            "max_open_positions": ExposureValidator.MAX_OPEN_POSITIONS,
            "max_asset_exposure_pct": ExposureValidator.MAX_ASSET_EXPOSURE_PCT * 100.0,
        },
        "position_sizing_formula": (
            "units = (equity * max_risk_fraction) / abs(entry - ltf_structural_stop)"
        ),
    }


# =============================================================================
# News policy — blackout scope is DERIVED from the ladder, never hard-coded.
# =============================================================================

NEWS_BLACKOUT_SECONDS = 1800  # +/- 30 minutes, matching NewsProvider defaults
NEWS_BLACKOUT_LTF_MAX_SECONDS = 15 * 60  # applies to sets whose LTF is 15m or faster


def news_affected_set_ids() -> List[str]:
    """Returns the set ids whose LTF resolution is 15 minutes or faster."""
    affected: List[str] = []
    for set_id in _LINEAR_SEQUENCE:
        cfg = CANONICAL_6_TIMEFRAME_SETS[set_id]
        duration = TIMEFRAME_DURATIONS_SEC.get(cfg.ltf)
        if duration is not None and duration <= NEWS_BLACKOUT_LTF_MAX_SECONDS:
            affected.append(set_id)
    return affected


def build_news_policy() -> Dict[str, Any]:
    affected = news_affected_set_ids()
    return {
        "rule": "No NEW position may be initiated inside the blackout window.",
        "blackout_seconds_before": NEWS_BLACKOUT_SECONDS,
        "blackout_seconds_after": NEWS_BLACKOUT_SECONDS,
        "qualifying_impact": "HIGH",
        "applies_to_layer": LAYER_LTF_ENTRY,
        "affected_timeframe_sets": affected,
        "unaffected_timeframe_sets": [s for s in _LINEAR_SEQUENCE if s not in affected],
        "open_positions_on_blackout": "MANAGED_NOT_CANCELLED",
        "missing_historical_news_data": "FAIL_CLOSED",
        "lookahead": "FORBIDDEN",
    }


# =============================================================================
# Performance targets — declared intent, explicitly NOT a measured result.
# =============================================================================

def build_performance_targets() -> Dict[str, Any]:
    """
    Operator-declared acceptance gates for promotion.

    INTEGRITY NOTE (do not remove): these numbers are a *target to be falsified*, not a
    result. At the mandatory 1:4 planned-RR floor the breakeven win rate is exactly 20%.
    A 60-80% win rate at >= 4R implies an expectancy of +2.0R to +3.0R per trade, roughly
    10x-15x the platform's existing documented promotion bar (+0.20R expectancy,
    t-stat > 2.0, net Sharpe > 1.2). The target is a hypothesis requiring out-of-sample
    evidence and must never be reported as achieved without surviving the adversarial
    falsification battery.
    """
    min_rr = RiskConfig().min_rr_floor
    breakeven = 1.0 / (1.0 + min_rr)
    return {
        "declared_by": "OPERATOR_DIRECTIVE",
        "claim_status": "UNPROVEN_TARGET_ONLY",
        "validated_alpha_strategies": 0,
        "min_planned_rr": min_rr,
        "breakeven_win_rate_at_min_rr": round(breakeven, 4),
        "win_rate_target_band": [0.60, 0.80],
        "win_rate_hard_floor": 0.60,
        "profit_factor_target_band": [2.0, 3.0],
        "profit_factor_hard_floor": 2.0,
        "implied_expectancy_r_at_60pct_win": round(0.60 * min_rr - 0.40 * 1.0, 4),
        "implied_expectancy_r_at_80pct_win": round(0.80 * min_rr - 0.20 * 1.0, 4),
        "platform_promotion_bar": {
            "min_expectancy_r": 0.20,
            "min_t_stat": 2.0,
            "min_net_sharpe": 1.2,
            "requires_multi_partition_oos": True,
            "requires_cross_asset_confirmation": 2,
        },
        "evaluation_scope": "UNTOUCHED_OUT_OF_SAMPLE_PARTITION",
        "integrity_note": (
            "Targets are acceptance gates, not performance claims. Reporting a target as "
            "achieved before multi-partition OOS + adversarial falsification is a governance "
            "violation (see README 'What QCP Refuses To Do')."
        ),
    }


# =============================================================================
# Inventory assembly
# =============================================================================

DEFAULT_MANIFEST_PATH = Path(__file__).resolve().parent / "results" / "FOUNDATION_MANIFEST.json"


def ensure_all_families_registered() -> None:
    """Idempotently registers every family module into the ComponentRegistry."""
    bias_families.register_all_biases(ComponentRegistry)
    setup_families.register_all_setups(ComponentRegistry)
    entry_families.register_all_entries(ComponentRegistry)
    sl_families.register_all_stop_losses(ComponentRegistry)
    tp_families.register_all_take_profits(ComponentRegistry)
    trailing_families.register_all_trailings(ComponentRegistry)


def _layer_records(
    registry_map: Dict[str, Any],
    category_by_class: Dict[str, str],
    layer: str,
    component_kind: str,
) -> List[Dict[str, Any]]:
    """Builds classified family records for one architectural layer."""
    ids_by_class: Dict[str, List[str]] = {}
    for family_id, component in registry_map.items():
        ids_by_class.setdefault(type(component).__name__, []).append(family_id)

    records: List[Dict[str, Any]] = []
    for family_id in sorted(registry_map):
        component = registry_map[family_id]
        class_name = type(component).__name__
        canonical_id = sorted(ids_by_class[class_name])[0]
        records.append({
            "family_id": family_id,
            "component_class": class_name,
            "component_kind": component_kind,
            "layer": layer,
            "category": category_by_class.get(class_name, "UNCLASSIFIED"),
            "is_registry_alias": family_id != canonical_id,
            "canonical_id_for_class": canonical_id,
            "description": getattr(component, "description", ""),
        })
    return records


def build_timeframe_sets() -> List[Dict[str, Any]]:
    """The canonical 6-Set ladder with layer roles, trace, and duration arithmetic."""
    sets: List[Dict[str, Any]] = []
    for set_id in _LINEAR_SEQUENCE:
        cfg = CANONICAL_6_TIMEFRAME_SETS[set_id]
        sets.append({
            "set_id": set_id,
            "style_name": cfg.style_name,
            "htf": cfg.htf,
            "mtf": cfg.mtf,
            "ltf": cfg.ltf,
            "htf_role": "DESTINATION_AND_PERMISSION",
            "mtf_role": "NAVIGATION_AND_TRAILING",
            "ltf_role": "EXECUTION_AND_INVALIDATION",
            "setup_trace": f"{cfg.htf} bias -> {cfg.mtf} setup -> {cfg.ltf} entry",
            "management_trace": f"{cfg.ltf} SL -> {cfg.htf} target -> {cfg.mtf} trailing",
            "htf_duration_sec": TIMEFRAME_DURATIONS_SEC.get(cfg.htf),
            "mtf_duration_sec": TIMEFRAME_DURATIONS_SEC.get(cfg.mtf),
            "ltf_duration_sec": TIMEFRAME_DURATIONS_SEC.get(cfg.ltf),
        })
    return sets


def build_foundation_inventory() -> Dict[str, Any]:
    """
    Builds the complete, machine-readable foundation inventory.

    `classification_complete` is False whenever a newly registered family has no taxonomy
    entry — that is a hard signal, not a warning, and is asserted by the test suite.
    """
    ensure_all_families_registered()

    families: Dict[str, List[Dict[str, Any]]] = {
        LAYER_HTF_BIAS: _layer_records(
            ComponentRegistry._biases, BIAS_CATEGORY_BY_CLASS, LAYER_HTF_BIAS, "AbstractBias"),
        LAYER_MTF_SETUP: _layer_records(
            ComponentRegistry._setups, SETUP_CATEGORY_BY_CLASS, LAYER_MTF_SETUP, "AbstractSetup"),
        LAYER_LTF_ENTRY: _layer_records(
            ComponentRegistry._entries, ENTRY_CATEGORY_BY_CLASS, LAYER_LTF_ENTRY, "AbstractEntry"),
        LAYER_LTF_STOP: _layer_records(
            ComponentRegistry._stop_losses, SL_CATEGORY_BY_CLASS, LAYER_LTF_STOP, "AbstractStopLoss"),
        LAYER_HTF_TARGET: _layer_records(
            ComponentRegistry._take_profits, TP_CATEGORY_BY_CLASS, LAYER_HTF_TARGET, "AbstractTakeProfit"),
        LAYER_MTF_TRAILING: _layer_records(
            ComponentRegistry._trailings, TRAILING_CATEGORY_BY_CLASS, LAYER_MTF_TRAILING, "AbstractTrailing"),
    }

    family_counts = {
        layer: {
            "registered_ids": len(records),
            "unique_classes": len({r["component_class"] for r in records}),
            "registry_aliases": sum(1 for r in records if r["is_registry_alias"]),
        }
        for layer, records in families.items()
    }

    unclassified = [
        f"{layer}::{record['family_id']}"
        for layer, records in families.items()
        for record in records
        if record["category"] == "UNCLASSIFIED"
    ]

    return {
        "foundation": FOUNDATION_ID,
        "version": FOUNDATION_VERSION,
        "pipeline": [LAYER_HTF_BIAS, LAYER_MTF_SETUP, LAYER_LTF_ENTRY],
        "post_entry_management": [LAYER_LTF_STOP, LAYER_HTF_TARGET, LAYER_MTF_TRAILING],
        "timeframe_sets": build_timeframe_sets(),
        "families": families,
        "family_counts": family_counts,
        "unclassified_families": unclassified,
        "classification_complete": len(unclassified) == 0,
        "risk_policy": build_risk_policy(),
        "news_policy": build_news_policy(),
        "performance_targets": build_performance_targets(),
    }
def emit_foundation_manifest(path: Optional[Path] = None) -> Path:
    """Writes the foundation inventory as JSON and returns the written path."""
    import json

    target = Path(path) if path is not None else DEFAULT_MANIFEST_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(build_foundation_inventory(), indent=2) + "\n",
        encoding="utf-8",
    )
    return target


def _main() -> int:
    inventory = build_foundation_inventory()
    print("=" * 78)
    print("QCP FOUNDATION REGISTRY — HTF BIAS -> MTF SETUP -> LTF ENTRY")
    print("=" * 78)

    print("\n[6-SET LADDER]")
    for tf in inventory["timeframe_sets"]:
        print(f"  {tf['set_id']}  {tf['style_name']:<22} "
              f"{tf['htf']:>3} bias -> {tf['mtf']:>3} setup -> {tf['ltf']:>3} entry")

    print("\n[FAMILY COUNTS]")
    for layer, counts in inventory["family_counts"].items():
        print(f"  {layer:<24} ids={counts['registered_ids']:<3} "
              f"classes={counts['unique_classes']:<3} aliases={counts['registry_aliases']}")

    print("\n[RISK POLICY]")
    risk = inventory["risk_policy"]
    print(f"  max risk per trade    : {risk['max_risk_per_trade_pct']:.1f}%")
    print(f"  min planned RR        : 1:{risk['min_planned_rr_floor']:.0f}")
    print(f"  SL / TP / trail anchor: {risk['stop_anchor']} / "
          f"{risk['target_anchor']} / {risk['trailing_anchor']}")

    print("\n[NEWS POLICY]")
    news = inventory["news_policy"]
    print(f"  blackout              : +/- {news['blackout_seconds_before'] // 60} min")
    print(f"  affected sets         : {news['affected_timeframe_sets']}")
    print(f"  unaffected sets       : {news['unaffected_timeframe_sets']}")

    print("\n[PERFORMANCE TARGETS]")
    targets = inventory["performance_targets"]
    print(f"  status                : {targets['claim_status']}")
    print(f"  win rate target band  : {targets['win_rate_target_band']}")
    print(f"  profit factor band    : {targets['profit_factor_target_band']}")
    print(f"  breakeven WR @ 1:{targets['min_planned_rr']:.0f}   : "
          f"{targets['breakeven_win_rate_at_min_rr']:.0%}")

    print(f"\nclassification_complete: {inventory['classification_complete']}")
    if inventory["unclassified_families"]:
        print(f"UNCLASSIFIED           : {inventory['unclassified_families']}")

    written = emit_foundation_manifest()
    print(f"\nManifest written to: {written}")
    return 0 if inventory["classification_complete"] else 1


if __name__ == "__main__":
    raise SystemExit(_main())