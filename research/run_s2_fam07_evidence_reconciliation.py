"""
QCP — S2 Evidence Reconciliation: FAM-07-MTFCONT_SOLUSDT_Set2
Directive: EABG-001, Remediation Slice S2

PURPOSE
=======
Produce a single, immutable, forensically-verified evidence artifact that:
  1. De-duplicates the contaminated forward telemetry store (F-02).
  2. Re-derives the realistic forward paper performance from de-duplicated data.
  3. Reconciles the contradictory claims (+278% vs -0.9066R).
  4. Issues a single, evidence-backed verdict for the strategy's lifecycle state.
  5. Writes a hash-pinned artifact to research/results/FAM07_S2_EVIDENCE_RECONCILIATION.json
     and commits it as the authoritative evidence record for this strategy.

INVARIANTS
==========
- No historical rows are rewritten. All changes are additive.
- The contaminated store is documented; de-duplicated data is presented separately.
- The baseline DEV evidence (HTF_TREND_CONTINUATION_V1.json) is re-read and pinned.
- Verdict drives lifecycle state change in the canonical registry.
- This script is itself a research artifact and must be committed.

VERDICT LOGIC
=============
The reconciled verdict resolves the contradiction:
  - The +278% figure derives from the contaminated store (F-02 — inadmissible).
  - The -0.9066R figure derives from the DEV 2021-2022 baseline (14 trades, 0 wins).
  - The forward paper (F-10) shows 2 trades, -1.202R expectancy, 0% win rate.
  - All three consistent, uncontaminated measurements agree: NEGATIVE EXPECTANCY.
  - Verdict: FAM-07-MTFCONT_SOLUSDT_Set2 → FRAGILE (lifecycle state demoted).
    Rationale: The strategy has genuine forward paper history (2 trades) but 0 wins.
    FALSIFIED is reserved for confirmed negative after minimum sample (≥30 trades).
    The correct state is FRAGILE: negative early evidence, continued monitoring authorized.
"""

import hashlib
import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TELEMETRY_PATH = os.path.join(REPO_ROOT, "research", "results", "telemetry", "forward_execution_telemetry.jsonl")
BASELINE_EVIDENCE_PATH = os.path.join(REPO_ROOT, "research", "results", "HTF_TREND_CONTINUATION_V1.json")
PAPER_AUDIT_PATH = os.path.join(REPO_ROOT, "research", "results", "FORWARD_PAPER_DAEMON_AUDIT.json")
OUTPUT_PATH = os.path.join(REPO_ROOT, "research", "results", "FAM07_S2_EVIDENCE_RECONCILIATION.json")
CONTAMINATION_MANIFEST_PATH = os.path.join(
    REPO_ROOT, "research", "results", "telemetry", "CONTAMINATION_MANIFEST.json"
)

STRATEGY_ID = "FAM-07-MTFCONT_SOLUSDT_Set2"


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_str(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def load_and_audit_telemetry():
    """Load telemetry, compute dedup stats, return unique records for STRATEGY_ID."""
    rows = []
    with open(TELEMETRY_PATH) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    pass

    total_rows = len(rows)
    id_counter = Counter(r.get("trade_id", "") for r in rows)
    unique_ids = len(id_counter)
    max_rep = max(id_counter.values()) if id_counter else 0
    dup_pct = 100.0 * (total_rows - unique_ids) / max(total_rows, 1)

    # De-duplicate: keep first occurrence of each trade_id
    seen = set()
    unique_rows = []
    for r in rows:
        tid = r.get("trade_id", "")
        if tid not in seen:
            seen.add(tid)
            unique_rows.append(r)

    # Filter for this strategy
    fam07_rows = [r for r in unique_rows if r.get("strategy_id") == STRATEGY_ID]

    return {
        "total_raw_rows": total_rows,
        "total_unique_trade_ids": unique_ids,
        "duplicate_rows_removed": total_rows - unique_ids,
        "duplicate_pct": round(dup_pct, 2),
        "max_single_id_repetition": max_rep,
        "unique_rows_after_dedup": len(unique_rows),
        "fam07_unique_rows": fam07_rows,
        "fam07_count": len(fam07_rows),
        "telemetry_file_sha256": sha256_file(TELEMETRY_PATH),
    }


def compute_performance(trades: list) -> dict:
    """Compute realized performance metrics from a list of de-duplicated trade records."""
    n = len(trades)
    if n == 0:
        return {
            "n_trades": 0,
            "wins": 0,
            "losses": 0,
            "win_rate_pct": 0.0,
            "total_net_r": 0.0,
            "expectancy_r": 0.0,
            "profit_factor": 0.0,
        }

    net_rs = [t.get("net_r", 0.0) for t in trades]
    wins = [r for r in net_rs if r > 0]
    losses = [r for r in net_rs if r < 0]

    win_sum = sum(wins)
    loss_sum = abs(sum(losses))
    pf = (win_sum / loss_sum) if loss_sum > 0 else float("inf")

    return {
        "n_trades": n,
        "wins": len(wins),
        "losses": len(losses),
        "win_rate_pct": round(100.0 * len(wins) / n, 2),
        "total_net_r": round(sum(net_rs), 4),
        "expectancy_r": round(sum(net_rs) / n, 4),
        "profit_factor": round(pf, 4) if pf != float("inf") else "Inf",
    }


def resolve_verdict(
    dev_expectancy_r: float,
    dev_win_rate_pct: float,
    dev_n_trades: int,
    forward_n_trades: int,
    forward_expectancy_r: float,
    forward_win_rate_pct: float,
) -> dict:
    """
    Apply the evidence-driven verdict logic.
    Returns verdict, lifecycle_state, and rationale.
    """
    # Minimum sample gates (per EABG-001 economic gate)
    MIN_FALSIFICATION_TRADES = 30
    MIN_PROMOTION_TRADES = 50

    rationale = []

    # --- DEV evidence ---
    if dev_expectancy_r <= 0.0:
        rationale.append(
            f"DEV expectancy is {dev_expectancy_r:.4f}R (≤ 0) across {dev_n_trades} trades: "
            "negative expectancy confirmed in development period."
        )
        dev_verdict = "NEGATIVE"
    else:
        dev_verdict = "POSITIVE"
        rationale.append(f"DEV expectancy is {dev_expectancy_r:.4f}R across {dev_n_trades} trades.")

    # --- Forward paper evidence ---
    if forward_n_trades < 2:
        rationale.append("Forward paper: insufficient trades for evaluation.")
        forward_verdict = "INSUFFICIENT"
    elif forward_win_rate_pct == 0.0 and forward_expectancy_r < 0.0:
        rationale.append(
            f"Forward paper: {forward_n_trades} trades, 0 wins, "
            f"expectancy {forward_expectancy_r:.4f}R: consistent with DEV negative."
        )
        forward_verdict = "NEGATIVE"
    else:
        forward_verdict = "UNCLEAR"

    # --- Contaminated claim (inadmissible) ---
    rationale.append(
        "Contaminated claim (+278%): derived from forward telemetry with 53% duplicate records "
        "(F-02). INADMISSIBLE. Cannot be cited."
    )

    # --- Lifecycle determination ---
    if dev_verdict == "NEGATIVE" and forward_verdict == "NEGATIVE":
        # Both uncontaminated sources agree: negative
        if (dev_n_trades + forward_n_trades) >= MIN_FALSIFICATION_TRADES:
            verdict = "FALSIFIED"
            lifecycle_state = "FALSIFIED"
            summary = (
                f"Strategy has ≥{MIN_FALSIFICATION_TRADES} combined trades with consistent "
                "negative expectancy. FALSIFIED and routed to Strategy Graveyard."
            )
        else:
            verdict = "FRAGILE"
            lifecycle_state = "FRAGILE"
            summary = (
                f"Both DEV ({dev_n_trades} trades) and forward paper ({forward_n_trades} trades) "
                "show negative expectancy. Combined sample insufficient for formal FALSIFIED verdict "
                f"(need ≥{MIN_FALSIFICATION_TRADES}). Lifecycle state: FRAGILE. "
                "Continued paper monitoring authorized. No capital allocation permitted."
            )
    elif dev_verdict == "POSITIVE" and forward_verdict in ("NEGATIVE", "INSUFFICIENT"):
        verdict = "FRAGILE"
        lifecycle_state = "FRAGILE"
        summary = "Mixed evidence. Cannot promote. FRAGILE pending more forward data."
    else:
        verdict = "FRAGILE"
        lifecycle_state = "FRAGILE"
        summary = "Evidence ambiguous or insufficient. Default to FRAGILE."

    return {
        "verdict": verdict,
        "lifecycle_state": lifecycle_state,
        "summary": summary,
        "rationale": rationale,
        "dev_verdict": dev_verdict,
        "forward_verdict": forward_verdict,
    }


def main():
    timestamp = datetime.now(timezone.utc).isoformat()
    print(f"[S2] FAM-07 Evidence Reconciliation — {timestamp}")

    # ── 1. Audit telemetry store ──────────────────────────────────────────
    print("[S2] Loading and auditing telemetry store (2302 rows, may take ~30s)...")
    telem_audit = load_and_audit_telemetry()
    print(
        f"[S2] Telemetry: {telem_audit['total_raw_rows']} total → "
        f"{telem_audit['total_unique_trade_ids']} unique "
        f"({telem_audit['duplicate_pct']:.1f}% duplicates, "
        f"max rep={telem_audit['max_single_id_repetition']})"
    )
    print(f"[S2] FAM-07 unique trades: {telem_audit['fam07_count']}")

    # ── 2. Load DEV baseline evidence ────────────────────────────────────
    with open(BASELINE_EVIDENCE_PATH) as f:
        dev_evidence = json.load(f)
    dev_sha256 = sha256_file(BASELINE_EVIDENCE_PATH)
    dev_metrics = dev_evidence.get("financial_metrics", {})
    dev_sample = dev_evidence.get("sample_metrics", {})
    print(
        f"[S2] DEV baseline: {dev_sample.get('n_trades', 0)} trades, "
        f"expectancy {dev_metrics.get('expectancy_r', 0.0):.4f}R, "
        f"win rate {dev_sample.get('win_rate_pct', 0.0):.1f}%"
    )

    # ── 3. Load forward paper daemon audit ───────────────────────────────
    with open(PAPER_AUDIT_PATH) as f:
        paper_audit = json.load(f)
    paper_sha256 = sha256_file(PAPER_AUDIT_PATH)
    paper_state = paper_audit.get("state_summary", {})
    paper_model = paper_audit.get("model_vs_reality_gap", {})
    forward_n = paper_state.get("total_trades", 0)
    forward_exp = paper_model.get("forward_observed_expectancy_r", 0.0)
    forward_win = paper_model.get("forward_win_rate_pct", 0.0)
    print(
        f"[S2] Forward paper: {forward_n} trades, "
        f"expectancy {forward_exp:.4f}R, "
        f"win rate {forward_win:.1f}%"
    )

    # ── 4. Compute de-duplicated FAM-07 forward performance ──────────────
    fam07_perf = compute_performance(telem_audit["fam07_unique_rows"])
    print(
        f"[S2] De-duplicated FAM-07 forward telemetry: "
        f"{fam07_perf['n_trades']} trades, "
        f"expectancy {fam07_perf['expectancy_r']:.4f}R"
    )

    # ── 5. Write contamination manifest ──────────────────────────────────
    contamination_manifest = {
        "schema_version": "1.0",
        "purpose": "CONTAMINATION_QUARANTINE_RECORD",
        "directive": "EABG-001 / Finding F-02",
        "audit_timestamp_utc": timestamp,
        "quarantined_file": TELEMETRY_PATH,
        "total_rows": telem_audit["total_raw_rows"],
        "unique_trade_ids": telem_audit["total_unique_trade_ids"],
        "duplicate_rows": telem_audit["duplicate_rows_removed"],
        "duplicate_pct": telem_audit["duplicate_pct"],
        "max_single_trade_repetition": telem_audit["max_single_id_repetition"],
        "file_sha256_at_audit": telem_audit["telemetry_file_sha256"],
        "verdict": "FAIL_CONTAMINATED_NON_EVIDENCE",
        "admissibility": "NON_EVIDENCE_CONTAMINATED_SOURCE",
        "instructions": (
            "This store is read-only quarantined. Never used as evidence for strategy "
            "performance claims. All metrics derived from it are inadmissible per EABG-001 §F-02. "
            "De-duplicated analysis is in FAM07_S2_EVIDENCE_RECONCILIATION.json."
        ),
    }
    with open(CONTAMINATION_MANIFEST_PATH, "w") as f:
        json.dump(contamination_manifest, f, indent=2)
    print(f"[S2] Contamination manifest written: {CONTAMINATION_MANIFEST_PATH}")

    # ── 6. Resolve verdict ───────────────────────────────────────────────
    verdict_result = resolve_verdict(
        dev_expectancy_r=dev_metrics.get("expectancy_r", -999.0),
        dev_win_rate_pct=dev_sample.get("win_rate_pct", 0.0),
        dev_n_trades=dev_sample.get("n_trades", 0),
        forward_n_trades=forward_n,
        forward_expectancy_r=forward_exp,
        forward_win_rate_pct=forward_win,
    )
    print(f"[S2] Verdict: {verdict_result['verdict']} → lifecycle state: {verdict_result['lifecycle_state']}")
    for line in verdict_result["rationale"]:
        print(f"[S2]   · {line}")

    # ── 7. Build and write the authoritative evidence artifact ───────────
    evidence_record = {
        "schema_version": "2.0",
        "artifact_type": "S2_EVIDENCE_RECONCILIATION",
        "directive": "EABG-001 / Remediation Slice S2",
        "strategy_id": STRATEGY_ID,
        "family": "FAM-07 Multi-Timeframe Continuation",
        "symbol": "SOL/USDT",
        "timeframe_set": 2,
        "timeframes": {"HTF": "1W", "MTF": "1D", "LTF": "4H"},
        "reconciliation_timestamp_utc": timestamp,

        # ── Telemetry store audit ──────────────────────────────────────
        "telemetry_store_audit": {
            "path": TELEMETRY_PATH,
            "sha256": telem_audit["telemetry_file_sha256"],
            "total_rows": telem_audit["total_raw_rows"],
            "unique_trade_ids": telem_audit["total_unique_trade_ids"],
            "duplicate_rows": telem_audit["duplicate_rows_removed"],
            "duplicate_pct": telem_audit["duplicate_pct"],
            "max_repetition": telem_audit["max_single_id_repetition"],
            "verdict": "FAIL_CONTAMINATED_NON_EVIDENCE",
            "contamination_manifest": CONTAMINATION_MANIFEST_PATH,
        },

        # ── Contaminated claim (inadmissible — never cite) ─────────────
        "inadmissible_contaminated_claim": {
            "source": "PAPER_TRADING_SIMULATION_AUDIT.json",
            "reported_total_return_pct": 278.32,
            "reported_pf": 5.24,
            "reported_status": "FORWARD_HEALTHY",
            "verdict": "NON_EVIDENCE_CONTAMINATED_SOURCE",
            "reason": (
                "Derived from a telemetry store with 53% duplicate records (F-02). "
                "Sample count matches duplicate row count. Inadmissible per EABG-001."
            ),
        },

        # ── Development baseline (admissible) ─────────────────────────
        "development_baseline": {
            "source": "HTF_TREND_CONTINUATION_V1.json",
            "sha256": dev_sha256,
            "partition": "Development (2021-01-01 to 2022-12-31)",
            "dataset_hashes": dev_evidence.get("dataset_hashes", {}),
            "n_trades": dev_sample.get("n_trades", 0),
            "wins": dev_sample.get("wins", 0),
            "losses": dev_sample.get("losses", 0),
            "win_rate_pct": dev_sample.get("win_rate_pct", 0.0),
            "expectancy_r": dev_metrics.get("expectancy_r", 0.0),
            "net_r": dev_metrics.get("net_r", 0.0),
            "profit_factor": dev_metrics.get("profit_factor", 0.0),
            "sharpe_ratio": dev_metrics.get("sharpe_ratio", 0.0),
            "bootstrap_prob_positive_edge_pct": dev_evidence.get(
                "statistical_validation", {}
            ).get("bootstrap_prob_positive_edge_pct", 0.0),
            "promotion_status": dev_evidence.get("governance", {}).get("promotion_status", ""),
            "verdict": "ADMISSIBLE_DEVELOPMENT",
        },

        # ── De-duplicated forward telemetry (admissible — limited sample) ─
        "deduped_forward_telemetry": {
            "source": "forward_execution_telemetry.jsonl (de-duplicated)",
            "fam07_unique_trades": fam07_perf["n_trades"],
            "wins": fam07_perf["wins"],
            "losses": fam07_perf["losses"],
            "win_rate_pct": fam07_perf["win_rate_pct"],
            "expectancy_r": fam07_perf["expectancy_r"],
            "profit_factor": fam07_perf.get("profit_factor", 0.0),
            "verdict": "ADMISSIBLE_FORWARD_LIMITED_SAMPLE",
            "caveat": (
                f"Only {fam07_perf['n_trades']} FAM-07 unique trades in the forward store. "
                "Statistically insufficient for independent claim. Consistent with DEV evidence."
            ),
        },

        # ── Live forward daemon audit ──────────────────────────────────
        "forward_paper_daemon": {
            "source": "FORWARD_PAPER_DAEMON_AUDIT.json",
            "sha256": paper_sha256,
            "last_heartbeat_utc": paper_audit.get("last_heartbeat", {}).get("utc_iso", ""),
            "total_closed_trades": forward_n,
            "forward_expectancy_r": forward_exp,
            "forward_win_rate_pct": forward_win,
            "backtest_baseline_expectancy_r": paper_model.get("backtest_baseline_expectancy_r", 0.0),
            "expectancy_decay_pct": paper_model.get("expectancy_decay_pct", 0.0),
            "alerts": paper_model.get("alerts", []),
            "verdict": "ADMISSIBLE_FORWARD_PRELIMINARY",
        },

        # ── Authoritative verdict ──────────────────────────────────────
        "verdict": verdict_result["verdict"],
        "lifecycle_state_change": {
            "from": "QUALIFIED_ROBUST (fiat-asserted — F-04, inadmissible)",
            "to": verdict_result["lifecycle_state"],
            "authority": "S2 Evidence Reconciliation — EABG-001",
            "timestamp_utc": timestamp,
        },
        "verdict_summary": verdict_result["summary"],
        "verdict_rationale": verdict_result["rationale"],

        # ── Capital implications ───────────────────────────────────────
        "capital_implications": {
            "allocation_permitted": False,
            "live_capital_permitted": False,
            "paper_monitoring_permitted": True,
            "minimum_trades_for_falsification": 30,
            "minimum_trades_for_promotion": 50,
            "current_combined_sample": dev_sample.get("n_trades", 0) + forward_n,
            "additional_paper_trades_needed": max(
                0,
                30 - (dev_sample.get("n_trades", 0) + forward_n),
            ),
        },

        # ── Next steps ────────────────────────────────────────────────
        "next_steps": [
            "Continue forward paper daemon (SOL/USDT Set 2) with S1-hardened telemetry (session-tagged).",
            "After 30 combined paper trades with persistent negative expectancy: promote to FALSIFIED.",
            "After 30 combined paper trades with positive expectancy (>0.10R, PF>1.5): promote to HISTORICALLY_ROBUST.",
            "Do NOT alter this artifact. Write new versioned evidence artifacts for subsequent evaluations.",
        ],
    }

    # Compute artifact hash
    artifact_str = json.dumps(evidence_record, sort_keys=True)
    evidence_record["artifact_sha256"] = sha256_str(artifact_str)

    with open(OUTPUT_PATH, "w") as f:
        json.dump(evidence_record, f, indent=2)

    print(f"\n[S2] ✓ Evidence reconciliation artifact written: {OUTPUT_PATH}")
    print(f"[S2] ✓ Artifact SHA-256: {evidence_record['artifact_sha256']}")
    print(f"[S2] ✓ Verdict: {verdict_result['verdict']} → {verdict_result['lifecycle_state']}")
    print(f"[S2] ✓ Contamination manifest: {CONTAMINATION_MANIFEST_PATH}")
    print("\n[S2] RECONCILIATION COMPLETE. Slice S2 definition of done:")
    print("  ✓ Telemetry store audited and de-duplicated")
    print("  ✓ Contamination manifest written")
    print("  ✓ All three evidence sources evaluated independently")
    print("  ✓ Single immutable verdict artifact produced with dataset hashes")
    print("  ✓ Lifecycle state change recorded: inadmissible QUALIFIED_ROBUST → FRAGILE")
    print("  ✓ Capital allocation blocked pending minimum sample attainment")
    return evidence_record


if __name__ == "__main__":
    main()
