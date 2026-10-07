"""
Module: research.hypotheses.hypothesis_registry
Implements PHASE 2 — GENERATE HYPOTHESES, NOT INDICATOR PILES
Enforces strict scientific protocol:
- Every experiment must have hypothesis ID, parent, exact economic rationale, ONE structural modification,
  affected component, parameter chosen BEFORE seeing validation results, datasets, expected failure mechanism,
  acceptance criteria, and rejection criteria.
- Never combine multiple modifications in one experiment.
- Only hypotheses supported by Phase 1 forensic evidence.
"""

import json
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional

ROOT_DIR = Path("/home/mrcn2/crypto-platform")


@dataclass
class HypothesisRecord:
    hypothesis_id: str
    parent_hypothesis: str
    exact_economic_rationale: str
    one_structural_modification: str
    affected_component: str
    pre_registered_parameter: Dict[str, Any]
    development_dataset: Dict[str, str]
    validation_dataset: Dict[str, str]
    untouched_oos_dataset: Dict[str, str]
    expected_failure_mechanism: str
    acceptance_criteria: Dict[str, Any]
    rejection_criteria: Dict[str, Any]
    status: str = "REGISTERED_QUEUED"
    created_at_utc: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    verdict: Optional[str] = None
    verdict_notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class HypothesisRegistry:
    """
    Formal, immutable registry for systematic trading hypotheses.
    """

    def __init__(self, registry_file: Optional[Path] = None):
        self.registry_file = registry_file or (ROOT_DIR / "research/hypotheses/hypothesis_registry.json")
        self.hypotheses: Dict[str, HypothesisRecord] = {}
        self.load()

    def register(self, record: HypothesisRecord) -> None:
        """Registers a new hypothesis if not already present."""
        if record.hypothesis_id in self.hypotheses:
            print(f"[Registry] Updating existing hypothesis: {record.hypothesis_id}")
        else:
            print(f"[Registry] Registering new hypothesis: {record.hypothesis_id}")
        self.hypotheses[record.hypothesis_id] = record
        self.save()

    def save(self) -> None:
        self.registry_file.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "metadata": {
                "title": "SCIENTIFIC HYPOTHESIS REGISTRY",
                "last_updated_utc": datetime.now(timezone.utc).isoformat(),
                "total_hypotheses": len(self.hypotheses),
                "governance_standard": "Anti-Overfitting Single-Variable Modification Protocol"
            },
            "hypotheses": {k: v.to_dict() for k, v in self.hypotheses.items()}
        }
        with open(self.registry_file, "w") as f:
            json.dump(payload, f, indent=2)

    def load(self) -> None:
        if self.registry_file.exists():
            try:
                with open(self.registry_file, "r") as f:
                    data = json.load(f)
                for hid, hdata in data.get("hypotheses", {}).items():
                    self.hypotheses[hid] = HypothesisRecord(**hdata)
            except Exception as e:
                print(f"Warning loading registry: {e}")

    def export_markdown(self, md_path: Optional[Path] = None) -> Path:
        out_path = md_path or (ROOT_DIR / "docs/hypothesis_registry.md")
        out_path.parent.mkdir(parents=True, exist_ok=True)

        lines = []
        lines.append("# Formal Research Hypothesis Registry")
        lines.append("## Institutional Single-Variable Scientific Experiments")
        lines.append("")
        lines.append(f"**Last Updated**: `{datetime.now(timezone.utc).isoformat()}`  ")
        lines.append("**Governing Standard**: Anti-Curve-Fitting / Single Structural Modification  ")
        lines.append("**Control Baseline**: `HTF_TREND_CONTINUATION_V1` ($N=128$, $-76.77\\text{R}$, $E[R]=-0.5998\\text{R}$)  ")
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append("| Hypothesis ID | Parent | Affected Component | Structural Modification | Pre-Registered Parameter | Status |")
        lines.append("|---|---|---|---|---|:---:|")

        for hid, h in self.hypotheses.items():
            param_str = ", ".join(f"`{k}={v}`" for k, v in h.pre_registered_parameter.items())
            lines.append(f"| **{h.hypothesis_id}** | `{h.parent_hypothesis}` | `{h.affected_component}` | {h.one_structural_modification} | {param_str} | `{h.status}` |")

        lines.append("")
        lines.append("---")
        lines.append("")

        for hid, h in self.hypotheses.items():
            lines.append(f"### {h.hypothesis_id}")
            lines.append(f"- **Parent Hypothesis**: `{h.parent_hypothesis}`")
            lines.append(f"- **Status**: **`{h.status}`**")
            lines.append(f"- **Economic / Microstructure Rationale**: {h.exact_economic_rationale}")
            lines.append(f"- **Single Structural Modification**: {h.one_structural_modification}")
            lines.append(f"- **Affected Subsystem**: `{h.affected_component}`")
            lines.append(f"- **Pre-Registered Parameters**: `{h.pre_registered_parameter}`")
            lines.append(f"- **Expected Failure Mode**: {h.expected_failure_mechanism}")
            lines.append(f"- **Acceptance Thresholds**: `{h.acceptance_criteria}`")
            lines.append(f"- **Rejection Thresholds**: `{h.rejection_criteria}`")
            lines.append(f"- **Partition Scopes**:")
            lines.append(f"  - Development: `{h.development_dataset['period']}` (`{h.development_dataset['symbols']}`)")
            lines.append(f"  - Validation: `{h.validation_dataset['period']}` (FROZEN)")
            lines.append(f"  - Out-of-Sample: `{h.untouched_oos_dataset['period']}` (UNTOUCHED)")
            if h.verdict:
                lines.append(f"- **Empirical Verdict**: **`{h.verdict}`** — {h.verdict_notes}")
            lines.append("")

        out_path.write_text("\n".join(lines))
        return out_path


def initialize_canonical_hypothesis_registry() -> HypothesisRegistry:
    """Populates the registry with the 7 forensically grounded hypotheses from Phase 1."""
    registry = HypothesisRegistry()

    dev_ds = {
        "period": "2021-01-01 to 2022-12-31",
        "symbols": "BTC/USDT, ETH/USDT, SOL/USDT",
        "timeframe_sets": "SET_1, SET_2, SET_3, SET_4, SET_5",
        "role": "Development & Hypothesis Refinement"
    }
    val_ds = {
        "period": "2023-01-01 to 2023-12-31",
        "symbols": "BTC/USDT, ETH/USDT, SOL/USDT",
        "role": "Frozen Institutional Validation Gate"
    }
    oos_ds = {
        "period": "2024-01-01 to 2026-06-30",
        "symbols": "BTC/USDT, ETH/USDT, SOL/USDT",
        "role": "Blind Out-of-Sample Quarantine"
    }

    # H1.0 Control Benchmark
    h0 = HypothesisRecord(
        hypothesis_id="HTF_TREND_CONTINUATION_V1",
        parent_hypothesis="NONE_ROOT_CONTROL",
        exact_economic_rationale="Canonical institutional trend-following baseline trading in direction of HTF structure.",
        one_structural_modification="None (Frozen negative control benchmark).",
        affected_component="SystemRoot",
        pre_registered_parameter={"min_rr": 4.0, "risk_fraction": 0.01},
        development_dataset=dev_ds,
        validation_dataset=val_ds,
        untouched_oos_dataset=oos_ds,
        expected_failure_mechanism="Extreme target unreachability, stale zone decay, and micro-stop noise liquidation.",
        acceptance_criteria={"expectancy_r": "> 0.0R", "profit_factor": "> 1.0"},
        rejection_criteria={"expectancy_r": "<= 0.0R"},
        status="REJECTED_RESEARCH_ONLY",
        verdict="REJECTED_RESEARCH_ONLY",
        verdict_notes="Empirical control result: N=128, E[R]=-0.5998R, Net Realized Return=-76.77R, PF=0.38, 95% CI=[-0.7137R, -0.4683R]."
    )
    registry.register(h0)

    # H1.1 Earlier MTF Entry
    h1_1 = HypothesisRecord(
        hypothesis_id="H1.1_EARLIER_MTF_ENTRY",
        parent_hypothesis="HTF_TREND_CONTINUATION_V1",
        exact_economic_rationale="Forensic Phase 1 demonstrated that trades delayed > 1h lose -0.8699R (59.5% of losses). Entering on immediate close of the MTF realignment/retest bar captures initial impulse momentum before local exhaustion.",
        one_structural_modification="Trigger entry on immediate MTF confirmation bar close, eliminating secondary delayed LTF consolidation lag.",
        affected_component="StrategyCoordinator / LTFTriggerEngine",
        pre_registered_parameter={"mtf_entry_trigger": "IMMEDIATE_MTF_CONFIRMATION", "max_ltf_lag_bars": 0},
        development_dataset=dev_ds,
        validation_dataset=val_ds,
        untouched_oos_dataset=oos_ds,
        expected_failure_mechanism="Potential increase in false breakouts without secondary micro-sweep confirmation.",
        acceptance_criteria={"dev_expectancy_r": "> 0.0R", "profit_factor": "> 1.0", "cost_stress_1_5x_e_r": "> 0.0R"},
        rejection_criteria={"dev_expectancy_r": "<= -0.20R", "win_rate_pct": "< 25.0%"}
    )
    registry.register(h1_1)

    # H1.2 Alternative Structural SL Anchor
    h1_2 = HypothesisRecord(
        hypothesis_id="H1.2_MTF_STRUCTURAL_SL_ANCHOR",
        parent_hypothesis="HTF_TREND_CONTINUATION_V1",
        exact_economic_rationale="Forensic Phase 1 revealed that 41.8% of losses stem from sub-0.5% micro-stops swept by high-frequency spread/noise. Anchoring stop to confirmed MTF swing extreme places invalidation outside noise bands, while position sizing inversely scales to hold dollar risk constant at 1%.",
        one_structural_modification="Anchor initial structural stop loss to confirmed MTF Swing Extreme instead of micro LTF wick.",
        affected_component="RiskEngine / PositionSizer",
        pre_registered_parameter={"sl_anchor_timeframe": "MTF", "buffer_atr_mult": 0.10},
        development_dataset=dev_ds,
        validation_dataset=val_ds,
        untouched_oos_dataset=oos_ds,
        expected_failure_mechanism="Wider stops reduce trade reward-to-risk ratio, requiring higher win rate to maintain profitability.",
        acceptance_criteria={"dev_expectancy_r": "> 0.0R", "win_rate_pct": "> 35.0%", "profit_factor": "> 1.0"},
        rejection_criteria={"dev_net_r": "< -36.70R", "dev_expectancy_r": "< -0.40R"}
    )
    registry.register(h1_2)

    # H1.3 Dynamic Target Propagation
    h1_3 = HypothesisRecord(
        hypothesis_id="H1.3_DYNAMIC_STRUCTURAL_TARGET",
        parent_hypothesis="HTF_TREND_CONTINUATION_V1",
        exact_economic_rationale="Forensic Phase 1 proved that 52.4% of loss velocity was target unreachability drag: 0/128 trades reached fixed 4.0R, but 44.5% reached +0.5R to +2.58R before reversing. Anchoring target dynamically to nearest opposing MTF liquidity pool (min 1.5R) monetizes real market moves.",
        one_structural_modification="Set structural profit target to nearest opposing MTF swing pivot (min 1.5R) rather than rigid 4.0R macro extreme.",
        affected_component="HTFDestinationEngine / TradePlan",
        pre_registered_parameter={"target_mode": "NEAREST_OPPOSING_MTF_SWING", "min_rr_floor": 1.50},
        development_dataset=dev_ds,
        validation_dataset=val_ds,
        untouched_oos_dataset=oos_ds,
        expected_failure_mechanism="Reduced payoff ratio per winning trade may fail to outpace round-trip fees if win rate does not increase.",
        acceptance_criteria={"dev_expectancy_r": "> 0.0R", "target_reach_rate_pct": "> 20.0%", "profit_factor": "> 1.10"},
        rejection_criteria={"dev_expectancy_r": "<= 0.0R", "profit_factor": "< 1.0"}
    )
    registry.register(h1_3)

    # H1.4 Dynamic Trade Management Rule
    h1_4 = HypothesisRecord(
        hypothesis_id="H1.4_DYNAMIC_PROFIT_LOCK_0_75R",
        parent_hypothesis="HTF_TREND_CONTINUATION_V1",
        exact_economic_rationale="Forensic Phase 1 showed trades reaching +0.5R to +0.9R had 38.6% failure rate because baseline trailing only engaged at +1.0R. Engaging break-even lock at +0.75R MFE protects +0.5R moves from collapsing into full losses.",
        one_structural_modification="Activate break-even stop ratchet at +0.75R MFE with +0.05R buffer for fees.",
        affected_component="ExecutionSimulator / TradeManagement",
        pre_registered_parameter={"profit_lock_trigger_r": 0.75, "profit_lock_stop_r": 0.05},
        development_dataset=dev_ds,
        validation_dataset=val_ds,
        untouched_oos_dataset=oos_ds,
        expected_failure_mechanism="Premature break-even stop-outs on natural counter-trend wicks, truncating larger multi-R continuation runs.",
        acceptance_criteria={"dev_net_r_delta": ">= +10.0R", "dev_expectancy_r": "> 0.0R", "profit_factor": "> 1.0"},
        rejection_criteria={"winner_retention_pct": "< 70.0%", "dev_net_r_delta": "< 0.0R"}
    )
    registry.register(h1_4)

    # H1.5 HTF Zone Freshness
    h1_5 = HypothesisRecord(
        hypothesis_id="H1.5_HTF_KEYZONE_FRESHNESS_7D",
        parent_hypothesis="HTF_TREND_CONTINUATION_V1",
        exact_economic_rationale="Forensic Phase 1 proved that KeyZones > 7 days old generated 0 winners and accounted for -18.6R in losses. Older zones represent re-auctioned retail inventory rather than fresh institutional liquidity.",
        one_structural_modification="Quarantine candidate qualification to HTF KeyZones where (interaction_time - creation_time) <= 7 days.",
        affected_component="KeyZoneEngine / CandidateTracker",
        pre_registered_parameter={"max_keyzone_age_days": 7.0},
        development_dataset=dev_ds,
        validation_dataset=val_ds,
        untouched_oos_dataset=oos_ds,
        expected_failure_mechanism="Throughput compression from rejecting valid structural levels.",
        acceptance_criteria={"winner_retention_pct": "100.0%", "loss_removal_count": ">= 20", "dev_net_r_delta": ">= +15.0R"},
        rejection_criteria={"winner_retention_pct": "< 100.0%", "dev_net_r_delta": "< +5.0R"}
    )
    registry.register(h1_5)

    # H1.6 Volatility-Aware Entry Qualification
    h1_6 = HypothesisRecord(
        hypothesis_id="H1.6_VOLATILITY_EXPANSION_QUALIFICATION",
        parent_hypothesis="HTF_TREND_CONTINUATION_V1",
        exact_economic_rationale="Forensic Phase 1 demonstrated compression regimes produce frequent false breakouts. Requiring MTF ATR > 50-period SMA(ATR) filters out dead-market chop.",
        one_structural_modification="Require MTF ATR_14 > SMA_50(ATR_14) at entry qualification.",
        affected_component="MarketIntelligenceCoordinator",
        pre_registered_parameter={"volatility_metric": "ATR_14", "volatility_threshold": "SMA_50_ATR"},
        development_dataset=dev_ds,
        validation_dataset=val_ds,
        untouched_oos_dataset=oos_ds,
        expected_failure_mechanism="Entering at the tail end of volatility expansion cycles, buying local top of volatility.",
        acceptance_criteria={"dev_expectancy_r": "> 0.0R", "profit_factor": "> 1.0"},
        rejection_criteria={"dev_expectancy_r": "<= 0.0R", "throughput_retention_pct": "< 40.0%"}
    )
    registry.register(h1_6)

    # H1.7 Fast MTF Retest Qualification
    h1_7 = HypothesisRecord(
        hypothesis_id="H1.7_FAST_MTF_RETEST_24H",
        parent_hypothesis="HTF_TREND_CONTINUATION_V1",
        exact_economic_rationale="Forensic Phase 1 showed fast retests (<=4h) produced +0.4377R expectancy (PF 1.65), whereas slow grinds (>24h) produced 0% win rate (-1.06R avg, 41.7% of losses). Filtering out stale retests eliminates exhausted setups.",
        one_structural_modification="Reject setups where MTF retest occurs > 24 hours after MTF alignment event.",
        affected_component="MTFAlignmentEngine / CandidateTracker",
        pre_registered_parameter={"max_retest_delay_hours": 24.0},
        development_dataset=dev_ds,
        validation_dataset=val_ds,
        untouched_oos_dataset=oos_ds,
        expected_failure_mechanism="Missing multi-day accumulator pullbacks in high-timeframe trends.",
        acceptance_criteria={"loss_removal_count": ">= 15", "dev_expectancy_r": "> 0.0R", "profit_factor": "> 1.0"},
        rejection_criteria={"winner_retention_pct": "< 80.0%", "dev_net_r_delta": "< +5.0R"}
    )
    registry.register(h1_7)

    registry.save()
    registry.export_markdown()
    print(f"[Registry] Initialized {len(registry.hypotheses)} canonical hypotheses.")
    return registry


if __name__ == "__main__":
    initialize_canonical_hypothesis_registry()
