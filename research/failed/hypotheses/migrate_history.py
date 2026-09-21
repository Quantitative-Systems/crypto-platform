"""Migrate historical research artifacts into the QCP lab (hypotheses/).

AUDIT -> CLASSIFY -> DESIGN -> MIGRATE -> VERIFY phase.
No engine code is modified. Original artifacts stay in place; each test
record carries full provenance pointing back to the original path.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .governance_ops_a import create_candidate, create_hypothesis
from .governance_ops_b import create_test, record_test_result
from .index_gen import generate_indexes
from .seed_fractal01 import ensure as ensure_fractal01
from .verify_lab import verify_lab

LAB = Path(__file__).resolve().parent
REPO = LAB.parent.parent

DATA_VERSION = ("Certified DEV partition 2021-01-01..2022-12-31 "
                "(277,908 candles, 15 streams, BTC/ETH/SOL x SET_1..SET_5)")
EXEC = ("causal replayer, adverse-first intrabar collision, exited plans "
        "terminal (no-reentry invariant, replayer fix 6382061)")
TF = "SET_1..SET_5 multi-scale (15 streams)"
ASSETS = "BTC/USDT, ETH/USDT, SOL/USDT"
CFG = {"asset": ASSETS, "timeframe": TF, "fees": "2/5 bps",
       "slippage": "5 bps", "data_partition": "DEV 2021-2022",
       "execution_assumptions": EXEC}


def prov(hid, cid, tid, orig, exp_id, commit, version, cls, defect=None):
    p = {"original_path": orig, "experiment_id": exp_id,
         "hypothesis_id": hid, "candidate_id": cid, "test_id": tid,
         "strategy_mechanism_version": version, "data_version": DATA_VERSION,
         "code_commit": commit, "timeframe": TF, "asset": ASSETS,
         "execution_assumptions": EXEC, "fees": "maker 2 bps / taker 5 bps",
         "slippage": "5 bps adverse",
         "collision_reentry_semantics": "ADVERSE_FIRST + terminal-plan no-reentry",
         "result_classification": cls}
    if defect:
        p["known_engine_defect_note"] = defect
    return p


def m(n, net, pf, exp=None, note=""):
    d = {"total_trades": n, "net_r": net, "profit_factor": pf}
    if exp is not None:
        d["expectancy_r"] = exp
    if note:
        d["note"] = note
    return d


def run() -> dict:
    log = {"hypotheses": [], "candidates": 0, "tests": 0,
           "duplicates_removed": [], "errors": []}
    C, CD, T, R = (create_hypothesis, create_candidate, create_test,
                   record_test_result)
    # ---------------- H-TGTGEO-01: macro structural target selection --------
    hid = "H-TGTGEO-01"
    C(hid, "Macro Structural Target Selection",
      "Does prioritizing macro structural targets (STRUCTURAL_OBJECTIVE) "
      "over closest-objective ranking improve trade monetization?",
      status="NOT_SUPPORTED",
      null_hypothesis="Target ranking has no effect on net expectancy.",
      falsification="Treatment net expectancy < control (pre-registered B3).",
      mechanism="Target ranking rule isolated; all else frozen vs H0.",
      decision="REJECTED (B3 NEGATIVE). Preserved as negative evidence.")
    CD(hid, "C-TGTGEO-01", ASSETS, TF,
       "STRUCTURAL_OBJECTIVE hierarchical target ranking (weak swing > "
       "liquidity pool > opposing keyzone)", status="REJECTED")
    T(hid, "C-TGTGEO-01", "T-TGTGEO-01-T01", ASSETS, TF,
      config=dict(CFG, control="CLOSEST_OBJECTIVE canonical H0",
                  experiment_id="EXP_TARGET_STRUCTURAL_01"))
    R(hid, "C-TGTGEO-01", "T-TGTGEO-01-T01",
      m(41, -27.66, 0.1905, -0.6746,
        "vs control N=29 net -15.52R PF 0.3871; reach 6.90%->2.44%; "
        "winner truncation -4.13R on trade 20"),
      prov(hid, "C-TGTGEO-01", "T-TGTGEO-01-T01",
           "docs/TARGET_GEOMETRY_EXPERIMENT_AUDIT.md; "
           "scratch/exp_base_tgtstruct_legacy_stop_01_dev_results.json",
           "EXP_TARGET_STRUCTURAL_01",
           "unrecorded (pre-registry artifact, milestone branch lineage)",
           "v1.0.0-causal-adverse-first + STRUCTURAL_OBJECTIVE ranking",
           "NEGATIVE_SIGNAL"), "NEGATIVE_SIGNAL")
    log["hypotheses"].append(hid); log["candidates"] += 1; log["tests"] += 1

    # ---------------- H-TRDMGT-01: post-entry trade management -------------
    hid = "H-TRDMGT-01"
    C(hid, "Post-Entry Trade Management Monetization",
      "Do post-entry lifecycle mechanisms (milestone exits, breakeven "
      "ratchets, profit locks, composition) monetize the documented >=2R "
      "favorable excursions that trailing latency gives back?",
      status="PARTIALLY_SUPPORTED",
      null_hypothesis="Lifecycle overlays do not change net expectancy.",
      falsification="Overlay family with net expectancy <= 0 on DEV.",
      mechanism="Overlays isolated against certified ANCHOR_2 baseline.",
      decision="PARTIAL: milestone 2.5R and polarity+breakeven composite "
               "show positive DEV signals (N=11-13). DEV ONLY - no "
               "promotion to VAL/OOS/capital. Profit lock rejected.")
    log["hypotheses"].append(hid)
    # C-TRDMGT-01 milestone 2.5R
    CD(hid, "C-TRDMGT-01", ASSETS, TF,
       "+2.5R pre-registered milestone limit exit on MTF structural trail",
       status="PROMISING")
    T(hid, "C-TRDMGT-01", "T-TRDMGT-01-T01", ASSETS, TF,
      config=dict(CFG, baseline="COMPOSITE_01 N=13 +0.9615R",
                  experiment_id="HYP_TARGET_MILESTONE_01"))
    R(hid, "C-TRDMGT-01", "T-TRDMGT-01-T01",
      m(13, 1.4403, 1.3869, 0.1108,
        "RESULT_B_INFORMATIVE_MECHANISM; 0/13 structural target hits; "
        "convexity truncation prevents promotion"),
      prov(hid, "C-TRDMGT-01", "T-TRDMGT-01-T01",
           "scratch/milestone_2_5r_dev_results.json; "
           "docs/HYP_TARGET_MILESTONE_01_AUDIT_2021_2022.md",
           "CANONICAL_MILESTONE_2_5R_DEV_2021_2022",
           "8f570207d03d1822f9f6ab9289e8bd9a507fc394",
           "v1.0.0-causal-adverse-first + MILESTONE_2.5R exit",
           "POSITIVE_SIGNAL",
           defect="DEV sample only; positive result != winner; VAL/OOS "
                  "locked"), "POSITIVE_SIGNAL")
    T(hid, "C-TRDMGT-01", "T-TRDMGT-01-T02", ASSETS, TF,
      config=dict(CFG, baseline="LEGACY_STOP F-series",
                  execution_assumptions=EXEC +
                  " + EXHAUSTIVE_STRUCTURAL legacy stop anchor",
                  experiment_id="F1L_tgt_struct_milestone_01"),
      status="PLANNED")
    # C-TRDMGT-02 breakeven ratchet
    CD(hid, "C-TRDMGT-02", ASSETS, TF,
       "+1.0R -> +0.10R breakeven stop ratchet", status="PROMISING")
    T(hid, "C-TRDMGT-02", "T-TRDMGT-02-T01", ASSETS, TF,
      config=dict(CFG, baseline="ANCHOR_2 N=23 -4.1741R",
                  experiment_id="HYP_MGT_BREAKEVEN_1R_01"))
    R(hid, "C-TRDMGT-02", "T-TRDMGT-02-T01",
      m(23, -1.1462, None, None,
        "improvement vs baseline -4.1741R (+3.03R) but net expectancy "
        "still negative -> MIXED"),
      prov(hid, "C-TRDMGT-02", "T-TRDMGT-02-T01",
           "docs/HYP_COMPOSITE_POLARITY_BREAKEVEN_01_AUDIT_2021_2022.md; "
           "scratch/breakeven_1r_dev_results.json",
           "HYP_MGT_BREAKEVEN_1R_01",
           "unrecorded (branch feat/exp-composite-polarity-breakeven)",
           "v1.0.0-causal-adverse-first + breakeven 1R ratchet",
           "MIXED"), "MIXED")
    # C-TRDMGT-03 displacement polarity entry gate
    CD(hid, "C-TRDMGT-03", ASSETS, TF,
       "Entry displacement polarity filter (close vs open at trigger)",
       status="PROMISING")
    T(hid, "C-TRDMGT-03", "T-TRDMGT-03-T01", ASSETS, TF,
      config=dict(CFG, baseline="ANCHOR_2 N=23 -4.1741R",
                  experiment_id="HYP_ENTRY_DISPLACEMENT_POLARITY_01"))
    R(hid, "C-TRDMGT-03", "T-TRDMGT-03-T01",
      m(12, -0.0685, None, None,
        "N=12/13 retained; near-breakeven but entry-quality gate composes "
        "cleanly; enables the positive composite"),
      prov(hid, "C-TRDMGT-03", "T-TRDMGT-03-T01",
           "docs/HYP_COMPOSITE_POLARITY_BREAKEVEN_01_AUDIT_2021_2022.md",
           "HYP_ENTRY_DISPLACEMENT_POLARITY_01",
           "unrecorded (branch feat/exp-composite-polarity-breakeven)",
           "v1.0.0-causal-adverse-first + displacement polarity gate",
           "INCONCLUSIVE"), "INCONCLUSIVE")
    log["candidates"] += 3; log["tests"] += 4
    # C-TRDMGT-04 composite polarity + breakeven
    CD(hid, "C-TRDMGT-04", ASSETS, TF,
       "Composite: displacement polarity gate + breakeven 1R ratchet",
       status="PROMISING")
    T(hid, "C-TRDMGT-04", "T-TRDMGT-04-T01", ASSETS, TF,
      config=dict(CFG, baseline="ANCHOR_2 N=23 -4.1741R",
                  experiment_id="CANONICAL_COMPOSITE_01_DEV_2021_2022"))
    R(hid, "C-TRDMGT-04", "T-TRDMGT-04-T01",
      m(11, 1.4145, 1.4326, 0.1286,
        "repaired terminal replay; interaction I_total subadditive "
        "(redundant) but net positive on DEV"),
      prov(hid, "C-TRDMGT-04", "T-TRDMGT-04-T01",
           "scratch/composite_01_dev_results_repaired_terminal.json",
           "CANONICAL_COMPOSITE_01_DEV_2021_2022",
           "2e0cd3383aa080b89240dc9b252ebbeac3793696",
           "v1.0.0-causal-adverse-first + polarity + breakeven composite",
           "POSITIVE_SIGNAL", defect="DEV sample only; no promotion"),
      "POSITIVE_SIGNAL")
    T(hid, "C-TRDMGT-04", "T-TRDMGT-04-T02", ASSETS, TF,
      config=dict(CFG, baseline="ANCHOR_2 N=23 -4.1741R",
                  experiment_id="HYP_COMPOSITE_POLARITY_BREAKEVEN_01"))
    R(hid, "C-TRDMGT-04", "T-TRDMGT-04-T02",
      m(13, 0.9615, 1.2583, 0.0740,
        "audited composite: trade #14 recovered after the 1,000-bar cache "
        "truncation defect in binance_ETHUSDT_1h.json was repaired"),
      prov(hid, "C-TRDMGT-04", "T-TRDMGT-04-T02",
           "docs/HYP_COMPOSITE_POLARITY_BREAKEVEN_01_AUDIT_2021_2022.md",
           "HYP_COMPOSITE_POLARITY_BREAKEVEN_01",
           "unrecorded (branch feat/exp-composite-polarity-breakeven)",
           "v1.0.0-causal-adverse-first + polarity + breakeven composite",
           "POSITIVE_SIGNAL",
           defect="historical 1,000-bar cache truncation in "
                  "binance_ETHUSDT_1h.json affected the Cycle-1 record; "
                  "repaired before certification"), "POSITIVE_SIGNAL")
    # C-TRDMGT-05 profit lock 0.5R/0.25R (NEGATIVE - preserved)
    CD(hid, "C-TRDMGT-05", ASSETS, TF,
       "Profit lock ladder 0.5R / 0.25R", status="REJECTED")
    T(hid, "C-TRDMGT-05", "T-TRDMGT-05-T01", ASSETS, TF,
      config=dict(CFG, baseline="canonical H0 N=8 -5.1331R",
                  experiment_id="CANONICAL_PROFIT_LOCK_0.5R_0.25R_DEV_2021_2022"))
    R(hid, "C-TRDMGT-05", "T-TRDMGT-05-T01",
      m(8, -0.6025, 0.5642, -0.0753,
        "win rate 62.5% but premature exits destroy convexity; PF 0.5642"),
      prov(hid, "C-TRDMGT-05", "T-TRDMGT-05-T01",
           "scratch/canonical_profit_lock_0.5r_0.25r_dev_results.json",
           "CANONICAL_PROFIT_LOCK_0.5R_0.25R_DEV_2021_2022",
           "8ef0c931a87084096334a45bf81564232b42255b",
           "v1.0.0-causal-adverse-first + profit lock 0.5R/0.25R",
           "NEGATIVE_SIGNAL"), "NEGATIVE_SIGNAL")
    log["candidates"] += 2; log["tests"] += 3
    # ---------------- H-BASECTL-01: canonical entry baseline viability -----
    hid = "H-BASECTL-01"
    C(hid, "Canonical Entry Baseline Economic Viability (H0 / ANCHOR_2)",
      "Does the canonical HTF/MTF/LTF entry model with structural targets "
      "produce positive net expectancy on the DEV partition?",
      status="NOT_SUPPORTED",
      null_hypothesis="Baseline expectancy <= 0.",
      falsification="Net expectancy <= 0 after replayer repair.",
      mechanism="HTF BOS/CHOCH bias + keyzone, MTF MSS + causal retest, "
                "LTF sweep + displacement, structural SL, RR>=4 firewall.",
      decision="NOT SUPPORTED: H0 -5.13R (N=8), ANCHOR_2 -4.17R (N=23). "
               "ANCHOR_2 improves on H0 (+0.96R) but remains negative.")
    CD(hid, "C-BASECTL-01", ASSETS, TF,
       "Canonical H0 control (CLOSEST_OBJECTIVE targets)", status="REJECTED")
    T(hid, "C-BASECTL-01", "T-BASECTL-01-T01", ASSETS, TF,
      config=dict(CFG, experiment_id="CANONICAL_H0_DEV_2021_2022"))
    R(hid, "C-BASECTL-01", "T-BASECTL-01-T01",
      m(8, -5.1331, 0.0, -0.6416, "0 wins / 8 losses; certified control"),
      prov(hid, "C-BASECTL-01", "T-BASECTL-01-T01",
           "scratch/canonical_h0_dev_results.json; "
           "docs/CERTIFIED_DEVELOPMENT_BASELINE_AUDIT.md",
           "CANONICAL_H0_DEV_2021_2022",
           "8ef0c931a87084096334a45bf81564232b42255b",
           "v1.0.0-causal-adverse-first (post replayer repair 6382061)",
           "NEGATIVE_SIGNAL",
           defect="pre-repair replays contained 12 phantom re-entries "
                  "from the replayer loop defect; certified ledger is "
                  "post-repair"), "NEGATIVE_SIGNAL")
    CD(hid, "C-BASECTL-02", ASSETS, TF,
       "ANCHOR_2 structural target resolution expansion", status="REJECTED")
    T(hid, "C-BASECTL-02", "T-BASECTL-02-T01", ASSETS, TF,
      config=dict(CFG, experiment_id="ANCHOR_2_TREATMENT_DEV_2021_2022"))
    R(hid, "C-BASECTL-02", "T-BASECTL-02-T01",
      m(23, -4.1741, 0.5712, -0.1815,
        "3 multi-R winners (+2.80R, +1.69R, +1.06R); net negative"),
      prov(hid, "C-BASECTL-02", "T-BASECTL-02-T01",
           "docs/CERTIFIED_DEVELOPMENT_BASELINE_AUDIT.md",
           "ANCHOR_2_TREATMENT_DEV_2021_2022",
           "6382061 (replayer fix) merged via ada37f7",
           "v1.0.0-causal-adverse-first + ANCHOR_2 expansion",
           "MIXED"), "MIXED")
    log["hypotheses"].append(hid); log["candidates"] += 2; log["tests"] += 2
    # ---------------- H-REPRO-01: certified baseline reproducibility -------
    hid = "H-REPRO-01"
    C(hid, "Certified Baseline Reproducibility / Engine Drift",
      "Can the stored certified EXP_TARGET_STRUCTURAL_01 result be "
      "reproduced bit-comparably on the current working tree?",
      status="INVALIDATED",
      null_hypothesis="Certified results are reproducible on current tree.",
      falsification="Material deviation from stored certified metrics.",
      mechanism="Recompute composite base + STRUCTURAL_OBJECTIVE on the "
                "current tree and diff vs stored certified file.",
      decision="DRIFT DETECTED (-16.54R N=79 vs stored certified). "
               "Invalidated as evidence of engine drift; negative "
               "evidence preserved; blocks promotion of dependent "
               "legacy results.")
    CD(hid, "C-REPRO-01", ASSETS, TF,
       "Recomputation of certified composite base on current tree",
       status="INVALIDATED")
    T(hid, "C-REPRO-01", "T-REPRO-01-T01", ASSETS, TF,
      config=dict(CFG, baseline="stored certified EXP_TARGET_STRUCTURAL_01",
                  experiment_id="F_SERIES_RECERT"))
    R(hid, "C-REPRO-01", "T-REPRO-01-T01",
      m(79, -16.54, 0.568, -0.209,
        "DRIFT DETECTED vs stored certified result; N also differs"),
      prov(hid, "C-REPRO-01", "T-REPRO-01-T01",
           "docs/F_SERIES_EXPERIMENT_LEDGER.md",
           "F_SERIES_RECERT", "unrecorded (F-series working tree)",
           "current working tree (drifted) vs stored certified",
           "INVALIDATED",
           defect="engine drift invalidates comparability of legacy "
                  "certified artifacts with current-tree replays"),
      "INVALIDATED")
    log["hypotheses"].append(hid); log["candidates"] += 1; log["tests"] += 1

    # ---------------- H-MOM-01: momentum treatment -------------------------
    hid = "H-MOM-01"
    C(hid, "Momentum Treatment (H_MOM_01)",
      "Does the momentum-based treatment variant produce positive net "
      "expectancy on the DEV partition?",
      status="NOT_SUPPORTED",
      null_hypothesis="Momentum treatment expectancy <= 0.",
      falsification="Net expectancy <= 0 on DEV.",
      mechanism="Canonical engine + momentum treatment overlay.",
      decision="NOT SUPPORTED: N=18, net -3.61R, PF 0.63.")
    CD(hid, "C-MOM-01", ASSETS, TF,
       "H_MOM_01 momentum treatment", status="REJECTED")
    T(hid, "C-MOM-01", "T-MOM-01-T01", ASSETS, TF,
      config=dict(CFG, experiment_id="CANONICAL_H_MOM_01_DEV_2021_2022"))
    R(hid, "C-MOM-01", "T-MOM-01-T01",
      m(18, -3.6141, 0.6314, -0.2008,
        "27.8% win rate; 5 max consecutive losses"),
      prov(hid, "C-MOM-01", "T-MOM-01-T01",
           "scratch/canonical_h_mom_01_dev_results.json",
           "CANONICAL_H_MOM_01_DEV_2021_2022",
           "c75c00ca1c5d255b62f3b934e185a10097d4cd0e",
           "v1.0.0-causal-adverse-first + momentum treatment",
           "NEGATIVE_SIGNAL"), "NEGATIVE_SIGNAL")
    log["hypotheses"].append(hid); log["candidates"] += 1; log["tests"] += 1

    # ---------------- H-FRACTAL-01: new hypothesis (infrastructure only) ---
    ensure_fractal01()
    log["hypotheses"].append("H-FRACTAL-01")
    # ---------------- duplicate removal (sha256-verified) -------------------
    dups = [
        ("scratch/exp_base_tgtstruct_legacy_stop_01_dev_results.json",
         "scratch/legacystop_tgtstruct_01_dev_results.json"),
        ("scratch/exp_f1l_tgt_struct_milestone_01_dev_results.json",
         "scratch/f1l_tgt_struct_milestone_01_dev_results.json"),
        ("research/results/CAPABILITY_REGISTRY.json",
         "research/results/QCP_CAPABILITY_REGISTRY.json"),
        ("research/results/INSTITUTIONAL_PORTFOLIO.json",
         "research/results/SYSTEMATIC_ALPHA_PORTFOLIO.json"),
    ]
    for keep, dup in dups:
        kp, dp = REPO / keep, REPO / dup
        if kp.exists() and dp.exists():
            hk = hashlib.sha256(kp.read_bytes()).hexdigest()
            hd = hashlib.sha256(dp.read_bytes()).hexdigest()
            if hk == hd:
                dp.unlink()
                log["duplicates_removed"].append(dup)

    # ---------------- migration log ----------------------------------------
    (LAB / "MIGRATION_LOG.md").write_text(
        "# Historical Research Migration Log\n\n"
        "Generated by `hypotheses/migrate_history.py`. Original "
        "artifacts preserved in place; each test record carries full "
        "provenance (original path, experiment ID, commit, friction, "
        "collision semantics, classification).\n\n"
        "## Registered hypotheses\n\n"
        "| hypothesis | status | candidates | tests |\n"
        "|---|---|---|---|\n"
        "| H-TGTGEO-01 | NOT_SUPPORTED | 1 | 1 |\n"
        "| H-TRDMGT-01 | PARTIALLY_SUPPORTED | 5 | 7 |\n"
        "| H-BASECTL-01 | NOT_SUPPORTED | 2 | 2 |\n"
        "| H-REPRO-01 | INVALIDATED | 1 | 1 |\n"
        "| H-MOM-01 | NOT_SUPPORTED | 1 | 1 |\n"
        "| H-FRACTAL-01 | UNDER_RESEARCH | 0 | 0 (DO NOT TEST) |\n\n"
        "## Engine defects affecting historical artifacts\n\n"
        "- Replayer loop defect: exited trade plans re-entered the risk "
        "firewall (12 phantom trades). Fixed in commit 6382061; certified "
        "ledgers are post-repair.\n"
        "- 1,000-bar cache truncation in `binance_ETHUSDT_1h.json` hid "
        "composite trade #14 from the Cycle-1 record; repaired before "
        "baseline certification.\n"
        "- F-series RECERT drift: the current tree cannot reproduce the "
        "stored certified EXP_TARGET_STRUCTURAL_01 result (H-REPRO-01).\n\n"
        "## Duplicates removed (sha256-verified identical)\n\n"
        + "".join("- `%s` (identical to `%s`)\n" % (d, k)
                  for k, d in dups) +
        "\n## Preservation rules\n\n"
        "- Negative/mixed/invalidated evidence preserved as tests with "
        "NEGATIVE_SIGNAL / MIXED / INVALIDATED classification.\n"
        "- Positive DEV signals recorded as POSITIVE_SIGNAL tests; the "
        "governance layer structurally forbids automatic promotion to "
        "VALIDATION_CANDIDATE / VALIDATED from DEV evidence.\n"
        "- A/B separation: cross-scale transfer lives under H-FRACTAL-01 "
        "only; multi-timeframe confirmation/confluence is a distinct "
        "hypothesis family and must NOT be merged into H-FRACTAL-01 "
        "tests.\n",
        encoding="utf-8")

    # ---------------- indexes + verification -------------------------------
    generate_indexes(LAB)
    errs = verify_lab(LAB)
    log["errors"] = errs
    return log


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))

