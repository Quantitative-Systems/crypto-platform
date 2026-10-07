import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from research.discovery.independent_validator import IndependentValidator, StreamAuditCard
DISCOVERY_DIR = WORKSPACE_ROOT / "research" / "results" / "PHASE_P_FRACTAL_DISCOVERY"
OUTPUT_DIR = WORKSPACE_ROOT / "research" / "results" / "discovery_engine"


def run_master_audit():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    validator = IndependentValidator(n_resamples=1000, block_size=5)

    stream_files = sorted(DISCOVERY_DIR.glob("*.json"))
    stream_files = [f for f in stream_files if not f.name.startswith("master_")]

    print(f"Discovered {len(stream_files)} candidate stream files for independent audit...")

    cards: List[StreamAuditCard] = []
    total_hypotheses = len(stream_files)

    for idx, s_path in enumerate(stream_files, start=1):
        card = validator.audit_stream_file(s_path, total_hypotheses=total_hypotheses, rank_idx=idx)
        if card:
            cards.append(card)

    # Sort cards by classification priority and expectancy
    tier_order = {
        "ELITE": 0,
        "ROBUST": 1,
        "CONDITIONAL": 2,
        "RESEARCH ONLY": 3,
        "INSUFFICIENT_DATA": 4,
        "UNSTABLE": 5,
        "ECONOMICALLY_UNTRADABLE": 6,
        "FALSIFIED": 7,
    }
    cards.sort(key=lambda c: (tier_order.get(c.classification, 99), -c.bootstrap.exp_r_mean))

    print(f"\nAudit complete. Processed {len(cards)} streams.")

    # Write Master JSON
    audit_dict = {
        "total_streams_audited": len(cards),
        "total_hypotheses_considered": total_hypotheses,
        "tier_counts": {},
        "streams": {},
    }

    for c in cards:
        audit_dict["tier_counts"][c.classification] = audit_dict["tier_counts"].get(c.classification, 0) + 1
        audit_dict["streams"][c.stream_id] = {
            "stream_id": c.stream_id,
            "symbol": c.symbol,
            "timeframe_set": c.timeframe_set,
            "hypothesis": c.hypothesis,
            "total_trades": c.total_trades,
            "classification": c.classification,
            "justification": c.justification,
            "forensics": asdict(c.forensic),
            "bootstrap": asdict(c.bootstrap),
            "multiple_testing": asdict(c.multiple_testing),
            "cost_resilience": asdict(c.cost_resilience),
            "outlier_pruning": asdict(c.outlier_pruning),
        }

    json_path = OUTPUT_DIR / "INDEPENDENT_AUDIT_MASTER.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(audit_dict, f, indent=2)
    print(f"Saved master JSON to {json_path}")

    # Build Markdown Summary
    md_lines = [
        "# Independent Adversarial Validation & Multiple-Testing Audit Report",
        "",
        "**Status:** Certified Independent Quantitative Audit",
        f"**Streams Audited:** {len(cards)}",
        f"**Hypotheses Space:** {total_hypotheses}",
        "",
        "## 1. Classification Summary by Tier",
        "",
        "| Institutional Tier | Count | Description |",
        "|---|---|---|",
    ]

    tier_descriptions = {
        "ELITE": "High positive expectancy, confirmed OOS, high cost resilience, low concentration, statistical significance.",
        "ROBUST": "Positive expectancy, surviving bootstrap, FDR, OOS, and cost stress.",
        "CONDITIONAL": "Positive signal but wider confidence intervals or sensitive to multiple-testing penalty.",
        "RESEARCH ONLY": "Viable geometry but requires further regime conditioning.",
        "INSUFFICIENT_DATA": "Opportunity scarcity (N < 25), primarily macro Set 1.",
        "UNSTABLE": "Edge collapses when top winners are removed or fails OOS.",
        "ECONOMICALLY_UNTRADABLE": "Friction exceeds edge; break-even friction multiple < 1.0x (e.g. Set 5).",
        "FALSIFIED": "Negative sample expectancy or failed forensic geometry audit.",
    }

    for tier, count in sorted(audit_dict["tier_counts"].items(), key=lambda x: tier_order.get(x[0], 99)):
        desc = tier_descriptions.get(tier, "")
        md_lines.append(f"| **{tier}** | **{count}** | {desc} |")

    md_lines.extend([
        "",
        "## 2. Stream-by-Stream Independent Audit Scorecard",
        "",
        "| Stream ID | Set | Phase | Trades | Classification | Boot E[R] (95% CI) | Break-Even Friction | Ex-Top2 E[R] | Top 2 Conc % | Target Struct % |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ])

    for c in cards:
        ci_str = f"[{c.bootstrap.exp_r_ci_lower_95:+.2f}, {c.bootstrap.exp_r_ci_upper_95:+.2f}]"
        md_lines.append(
            f"| `{c.stream_id}` | {c.timeframe_set} | {c.hypothesis.replace('HYP_A_', '').replace('HYP_B_', '')} | "
            f"{c.total_trades} | **{c.classification}** | {c.bootstrap.exp_r_mean:+.4f}R {ci_str} | "
            f"{c.cost_resilience.breakeven_cost_multiple:.1f}x | {c.outlier_pruning.exp_ex_top2_r:+.4f}R | "
            f"{c.outlier_pruning.top2_concentration_pct:.1f}% | {c.forensic.structural_ratio_pct:.1f}% |"
        )

    md_path = OUTPUT_DIR / "INDEPENDENT_AUDIT_SUMMARY.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines) + "\n")
    print(f"Saved markdown summary to {md_path}")


if __name__ == "__main__":
    run_master_audit()
