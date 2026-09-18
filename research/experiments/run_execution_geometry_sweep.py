"""
QCP Phase D — H_STRUCT_01 Forensic Execution + Geometry Sensitivity Study.

Directive (Phase D):
  - DO NOT modify the underlying H_STRUCT_01 logic (FVG_TAP / BREAKOUT_CLOSE /
    SL_LTF_SWING / TP_STRUCTURAL_SWING / TRAIL_NONE).
  - DO NOT declare any configuration "the winner".
  - DO NOT optimize toward PF > 2 or WR > 60%.

The study has four sub-experiments:

  D-0  Control Reproduction
       H_STRUCT_01 at Taker fill / 4R target — must match Phase C report
       (confirms no regression in the v2.1 engine).

  D-1  Geometry Sensitivity (Taker fill, vary target_r_multiple)
       1.5R, 2R, 2.5R, 3R, 4R — firewall held at 4.0 throughout.
       Note: targets below 4R will be rejected by the firewall for all trades
       that require >= 4R planned R:R.  That is expected and must be reported.

  D-2  Execution Friction Decomposition (fixed 4R geometry, vary fill model)
       TAKER / MAKER_TOUCH / MAKER_CONSERVATIVE
       Each model changes entry_fill -> recomputes risk_per_unit and planned R:R.

  D-3  Combined Matrix (geometry x fill model) — full forensic surface
       Every (R-multiple x fill-model) combination for H_STRUCT_01.

Population: BTC/USDT, ETH/USDT, SOL/USDT * SET_2(4h), SET_3(1h), SET_4(15m)
            DEV partition (2021-01-01 - 2022-12-31).
"""

import os
import sys
import json
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd

REPO_ROOT = os.path.realpath(os.path.join(os.path.dirname(__file__), "..", ".."))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from research.grammar_components import ComponentRegistry
import research.bias_families as bf
import research.setup_families as sf
import research.entry_families as ef
import research.sl_families as slf
import research.tp_families as tpf
import research.trailing_families as trf

from research.strategy_grammar import HypothesisBuilder, TimeframeSet
from research.economic_evaluation_engine import (
    EconomicEvaluationEngine, BacktestConfig, CausalTripleBarrierBacktester,
)
from backtesting.friction_model import (
    FrictionModel,
    FILL_MODEL_TAKER, FILL_MODEL_MAKER_TOUCH, FILL_MODEL_MAKER_CONSERVATIVE,
)
from platform_core.alpha_genome import AlphaGenome

# Register all components
bf.register_all_biases(ComponentRegistry)
sf.register_all_setups(ComponentRegistry)
ef.register_all_entries(ComponentRegistry)
slf.register_all_stop_losses(ComponentRegistry)
tpf.register_all_take_profits(ComponentRegistry)
trf.register_all_trailings(ComponentRegistry)

# ─────────────────────────────────────────────────────────────────────────────
# Research population (identical to Phase C)
# ─────────────────────────────────────────────────────────────────────────────
ASSETS = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]
TF_SETS = {
    "SET_2": (TimeframeSet.SET_2_CORE, "4h"),
    "SET_3": (TimeframeSet.SET_3_SWING, "1h"),
    "SET_4": (TimeframeSet.SET_4_INTRADAY, "15m"),
}
DEV_PARTITIONS = [("DEV", "2021-01-01", "2022-12-31")]

# ─────────────────────────────────────────────────────────────────────────────
# H_STRUCT_01 — immutable canonical specification (DO NOT ALTER)
# ─────────────────────────────────────────────────────────────────────────────
H_STRUCT_01 = {
    "description": "FVG Tap + Breakout Close + Structural SL + Structural TP + Trail None",
    "bias_id": "REGIME_TREND",
    "setup_id": "SETUP_FVG_TAP",
    "entry_id": "ENTRY_BREAKOUT_CLOSE",
    "sl_id": "SL_LTF_SWING",
    "tp_id": "TP_STRUCTURAL_SWING",
    "trailing_id": "TRAIL_NONE",
}

# ─────────────────────────────────────────────────────────────────────────────
# Phase D experiment axes
# ─────────────────────────────────────────────────────────────────────────────
GEOMETRY_TARGETS = [1.5, 2.0, 2.5, 3.0, 4.0]
FILL_MODELS: Dict[str, FrictionModel] = {
    FILL_MODEL_TAKER: FrictionModel.taker(),
    FILL_MODEL_MAKER_TOUCH: FrictionModel.maker_touch(),
    FILL_MODEL_MAKER_CONSERVATIVE: FrictionModel.maker_conservative(),
}
CANONICAL_FIREWALL = 4.0
CANONICAL_TARGET_R = 4.0


def _build_stream_id(suffix: str, asset: str, set_id: str, tf_str: str) -> str:
    return f"H_STRUCT_01_{suffix}_{asset.replace('/', '')}_{set_id}_{tf_str}"


def _build_engine(fill_model: FrictionModel, target_r: float) -> EconomicEvaluationEngine:
    """Construct a correctly configured engine for one (fill_model x target_r) cell."""
    config = BacktestConfig(
        min_rr_firewall=CANONICAL_FIREWALL,
        stop_atr_multiple=2.0,
        target_r_multiple=target_r,
        apply_borrow_financing=True,
    )
    backtester = CausalTripleBarrierBacktester(friction=fill_model, config=config)
    return EconomicEvaluationEngine(min_trades_per_partition=1, backtester=backtester)


def _aggregate_stream_results(records: List[Dict]) -> Dict[str, Any]:
    """Aggregate per-stream records into a single summary dict."""
    all_net_r = []
    all_gross_r = []
    total_trades = 0
    total_obs = total_regime = total_setup = total_entry = 0
    total_geom = total_firewall_rej = 0
    total_fee_r = 0.0
    total_borrow_r = 0.0
    exit_reasons: Counter = Counter()
    trades_by_asset: Counter = Counter()
    trades_by_tf: Counter = Counter()

    for rec in records:
        n = rec["trade_count"]
        total_trades += n
        if n > 0:
            all_net_r.extend(rec.get("net_r_list", []))
            all_gross_r.extend(rec.get("gross_r_list", []))
            total_fee_r += rec.get("total_fee_r", 0.0)
            total_borrow_r += rec.get("total_borrow_r", 0.0)
            exit_reasons.update(rec.get("exit_reasons", {}))
            trades_by_asset[rec["asset"]] += n
            trades_by_tf[rec["timeframe"]] += n

        funnel = rec.get("funnel", {})
        total_obs += funnel.get("observations", 0)
        total_regime += funnel.get("regime_valid", 0)
        total_setup += funnel.get("setup_valid", 0)
        total_entry += funnel.get("entry_valid", 0)
        total_geom += funnel.get("geometry_valid", 0)
        total_firewall_rej += funnel.get("firewall_rejections", 0)

    net_arr = np.array(all_net_r) if all_net_r else np.array([])
    gross_arr = np.array(all_gross_r) if all_gross_r else np.array([])

    if total_trades > 0 and len(net_arr) > 0:
        wins = net_arr[net_arr > 0]
        losses = net_arr[net_arr < 0]
        win_rate = len(wins) / total_trades * 100.0
        gross_profit = float(wins.sum()) if len(wins) > 0 else 0.0
        gross_loss = float(abs(losses.sum())) if len(losses) > 0 else 0.0
        pf = min(999.0, gross_profit / max(1e-6, gross_loss))
        total_net_r = float(net_arr.sum())
        total_gross_r_val = float(gross_arr.sum())
        expectancy = float(net_arr.mean())
        friction_r = total_gross_r_val - total_net_r
        friction_pct = (friction_r / max(1e-6, abs(total_gross_r_val))) * 100.0
        cum = np.cumsum(net_arr)
        peak = np.maximum.accumulate(cum)
        max_dd = float(np.max(peak - cum))
    else:
        win_rate = pf = total_net_r = total_gross_r_val = expectancy = 0.0
        friction_r = friction_pct = max_dd = 0.0
        gross_profit = gross_loss = 0.0

    return {
        "total_trades": total_trades,
        "total_net_r": round(total_net_r, 4),
        "total_gross_r": round(total_gross_r_val, 4),
        "expectancy_net_r": round(expectancy, 6),
        "win_rate": round(win_rate, 2),
        "profit_factor": round(pf, 4),
        "max_drawdown_r": round(max_dd, 4),
        "total_fee_r": round(total_fee_r, 4),
        "total_borrow_r": round(total_borrow_r, 4),
        "total_friction_r": round(friction_r, 4),
        "friction_drag_pct": round(friction_pct, 2),
        "exit_reasons": dict(exit_reasons),
        "trades_by_asset": dict(trades_by_asset),
        "trades_by_tf": dict(trades_by_tf),
        "funnel": {
            "observations": total_obs,
            "regime_valid": total_regime,
            "setup_valid": total_setup,
            "entry_valid": total_entry,
            "geometry_valid": total_geom,
            "firewall_rejections": total_firewall_rej,
            "executed": total_trades,
        },
    }


def run_cell(
    fill_model: FrictionModel,
    target_r: float,
    cell_label: str,
    verbose: bool = True,
) -> Tuple[List[Dict], Dict]:
    """Execute all streams for one (fill_model x target_r) cell."""
    engine = _build_engine(fill_model, target_r)
    stream_records: List[Dict] = []

    spec = H_STRUCT_01
    for set_id, (tf_set, tf_str) in TF_SETS.items():
        for asset in ASSETS:
            stream_id = _build_stream_id(cell_label, asset, set_id, tf_str)
            if verbose:
                print(f"    {stream_id} ...", end=" ", flush=True)

            genome = AlphaGenome(
                alpha_id=stream_id,
                family="STRUCTURAL_REGIME",
                version="D.1.0",
                asset_universe=[asset],
                venues=["Binance"],
                instruments=["SPOT"],
                timeframe=tf_str,
                expected_holding_period_hours=24.0,
                economic_rationale=spec["description"],
                features=[spec["bias_id"], spec["setup_id"], spec["entry_id"]],
                entry_mechanism=spec["entry_id"],
                exit_mechanism=f"{spec['sl_id']}+{spec['tp_id']}+{spec['trailing_id']}",
            )

            signal_fn = HypothesisBuilder.build_signal(
                hypothesis_id="H_STRUCT_01",
                bias_id=spec["bias_id"],
                setup_id=spec["setup_id"],
                entry_id=spec["entry_id"],
                sl_id=spec["sl_id"],
                tp_id=spec["tp_id"],
                trailing_id=spec["trailing_id"],
                tf_set=tf_set,
            )

            try:
                res = engine.evaluate(
                    genome=genome,
                    signal_fn=signal_fn,
                    symbol=asset,
                    timeframe=tf_str,
                    partitions=DEV_PARTITIONS,
                )
                n = len(res.trades)
                net_r_list = [t.net_r for t in res.trades]
                gross_r_list = [t.gross_r for t in res.trades]
                fee_r_list = list(getattr(engine.backtester, "last_fee_r", []))
                borrow_r_list = list(getattr(engine.backtester, "last_borrow_r", []))
                exit_reasons = Counter(t.exit_reason for t in res.trades)

                rec = {
                    "cell_label": cell_label,
                    "fill_model": fill_model.fill_model,
                    "target_r": target_r,
                    "asset": asset,
                    "timeframe_set": set_id,
                    "timeframe": tf_str,
                    "status": res.status,
                    "trade_count": n,
                    "net_r_list": net_r_list,
                    "gross_r_list": gross_r_list,
                    "total_fee_r": sum(fee_r_list),
                    "total_borrow_r": sum(borrow_r_list),
                    "exit_reasons": dict(exit_reasons),
                    "funnel": res.telemetry.get("funnel", {}),
                }
                stream_records.append(rec)
                if verbose:
                    total_net = sum(net_r_list)
                    print(f"trades={n}, total_net={total_net:+.2f}R, status={res.status}")

            except Exception as exc:
                if verbose:
                    print(f"ERROR: {exc}")
                stream_records.append({
                    "cell_label": cell_label,
                    "fill_model": fill_model.fill_model,
                    "target_r": target_r,
                    "asset": asset,
                    "timeframe_set": set_id,
                    "timeframe": tf_str,
                    "status": f"ERROR: {exc}",
                    "trade_count": 0,
                    "net_r_list": [],
                    "gross_r_list": [],
                    "total_fee_r": 0.0,
                    "total_borrow_r": 0.0,
                    "exit_reasons": {},
                    "funnel": {},
                })

    summary = _aggregate_stream_results(stream_records)
    return stream_records, summary


def run_experiment() -> Dict[str, Any]:
    print("=" * 80)
    print("QCP PHASE D: H_STRUCT_01 FORENSIC EXECUTION + GEOMETRY SENSITIVITY STUDY")
    print("=" * 80)
    print(f"Time       : {datetime.now(timezone.utc).isoformat()} UTC")
    print(f"Hypothesis : H_STRUCT_01 -- {H_STRUCT_01['description']}")
    print(f"Assets     : {', '.join(ASSETS)}")
    print(f"TF Sets    : {', '.join(TF_SETS.keys())}")
    print(f"Partition  : DEV (2021-01-01 to 2022-12-31)")
    print(f"Firewall   : min_rr = {CANONICAL_FIREWALL}R (BINDING -- not relaxed)")
    print("-" * 80)

    all_cell_summaries: Dict[str, Any] = {}
    all_cell_records: Dict[str, List[Dict]] = {}

    # D-0 Control Reproduction
    print("\n[D-0] CONTROL REPRODUCTION -- Taker fill / 4R target")
    recs_d0, summary_d0 = run_cell(
        fill_model=FrictionModel.taker(),
        target_r=CANONICAL_TARGET_R,
        cell_label="D0_CTRL",
    )
    all_cell_summaries["D0_CTRL"] = {"fill_model": FILL_MODEL_TAKER, "target_r": 4.0, **summary_d0}
    all_cell_records["D0_CTRL"] = recs_d0

    # D-1 Geometry Sensitivity
    print("\n[D-1] GEOMETRY SENSITIVITY -- Taker fill, vary target R-multiple")
    for tr in GEOMETRY_TARGETS:
        label = f"D1_TAKER_{str(tr).replace('.', 'p')}R"
        print(f"\n  target_r = {tr}R -> cell={label}")
        recs, summary = run_cell(
            fill_model=FrictionModel.taker(),
            target_r=tr,
            cell_label=label,
        )
        all_cell_summaries[label] = {"fill_model": FILL_MODEL_TAKER, "target_r": tr, **summary}
        all_cell_records[label] = recs

    # D-2 Execution Friction Decomposition
    print("\n[D-2] EXECUTION FRICTION DECOMPOSITION -- fixed 4R geometry, vary fill model")
    for fm_id, fm in FILL_MODELS.items():
        label = f"D2_{fm_id}_4R"
        print(f"\n  fill_model={fm_id} -> cell={label}")
        recs, summary = run_cell(
            fill_model=fm,
            target_r=CANONICAL_TARGET_R,
            cell_label=label,
        )
        all_cell_summaries[label] = {"fill_model": fm_id, "target_r": 4.0, **summary}
        all_cell_records[label] = recs

    # D-3 Combined Matrix
    print("\n[D-3] COMBINED MATRIX -- geometry x fill model")
    for fm_id, fm in FILL_MODELS.items():
        for tr in GEOMETRY_TARGETS:
            label = f"D3_{fm_id}_{str(tr).replace('.', 'p')}R"
            recs, summary = run_cell(
                fill_model=fm,
                target_r=tr,
                cell_label=label,
                verbose=False,
            )
            all_cell_summaries[label] = {"fill_model": fm_id, "target_r": tr, **summary}
            all_cell_records[label] = recs
            print(
                f"  {label:<45} trades={summary['total_trades']:3d} "
                f"net={summary['total_net_r']:+.2f}R "
                f"WR={summary['win_rate']:.1f}% "
                f"PF={summary['profit_factor']:.3f} "
                f"frict={summary['total_friction_r']:+.4f}R ({summary['friction_drag_pct']:.1f}%)"
            )

    return {
        "experiment_id": "PHASE_D_H_STRUCT_01_FORENSIC",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "hypothesis": H_STRUCT_01,
        "population": {"assets": ASSETS, "tf_sets": list(TF_SETS.keys()), "partition": "DEV"},
        "canonical_firewall": CANONICAL_FIREWALL,
        "cell_summaries": all_cell_summaries,
        "cell_records": all_cell_records,
    }


def generate_report(results: Dict[str, Any]) -> str:
    """Generate EXECUTION_GEOMETRY_SWEEP_REPORT.md content."""
    lines: List[str] = []

    def h(level, text):
        lines.append("#" * level + " " + text)

    def p(text=""):
        lines.append(text)

    h(1, "QCP Phase D -- H_STRUCT_01 Forensic Execution + Geometry Sensitivity Report")
    p()
    p(f"**Generated**: {results['generated_at_utc']}")
    p(f"**Hypothesis**: H_STRUCT_01 -- {results['hypothesis']['description']}")
    p(f"**Population**: {', '.join(results['population']['assets'])} x "
      f"{', '.join(results['population']['tf_sets'])} x DEV partition (2021-2022)")
    p(f"**Binding Research Firewall**: min_rr >= {results['canonical_firewall']}R (not relaxed)")
    p()
    p("> GOVERNANCE: No result in this report is declared profitable or superior. "
      "All findings are forensic observations for continued research scoping.")
    p()

    # D-0 Control
    h(2, "D-0 -- Control Reproduction (Taker / 4R)")
    p()
    ctrl = results["cell_summaries"].get("D0_CTRL", {})
    p(f"| Metric | Value |")
    p(f"|--------|-------|")
    p(f"| Total Trades | {ctrl.get('total_trades', 0)} |")
    p(f"| Total Gross R | {ctrl.get('total_gross_r', 0.0):+.4f}R |")
    p(f"| Total Net R | {ctrl.get('total_net_r', 0.0):+.4f}R |")
    p(f"| Expectancy | {ctrl.get('expectancy_net_r', 0.0):+.6f}R/trade |")
    p(f"| Win Rate | {ctrl.get('win_rate', 0.0):.2f}% |")
    p(f"| Profit Factor | {ctrl.get('profit_factor', 0.0):.4f} |")
    p(f"| Max Drawdown | {ctrl.get('max_drawdown_r', 0.0):.4f}R |")
    p(f"| Total Friction | {ctrl.get('total_friction_r', 0.0):+.4f}R ({ctrl.get('friction_drag_pct', 0.0):.1f}% of gross) |")
    p(f"| Fee R | {ctrl.get('total_fee_r', 0.0):+.4f}R |")
    p(f"| Borrow R | {ctrl.get('total_borrow_r', 0.0):+.4f}R |")
    p()
    funnel = ctrl.get("funnel", {})
    p("**Funnel:**")
    p("| Stage | Count |")
    p("|-------|-------|")
    for k, v in funnel.items():
        p(f"| {k.replace('_', ' ').title()} | {v} |")
    p()
    er = ctrl.get("exit_reasons", {})
    if er:
        p("**Exit Reasons:**")
        p("| Reason | Count |")
        p("|--------|-------|")
        for k, v in sorted(er.items(), key=lambda x: -x[1]):
            p(f"| {k} | {v} |")
    p()

    # D-1 Geometry Sensitivity
    h(2, "D-1 -- Geometry Sensitivity (Taker Fill, Varying Target R)")
    p()
    p("Firewall fixed at 4.0R. Targets below 4R pass when structural geometry already exceeds firewall.")
    p()
    p("| Target R | Trades | Gross R | Net R | Expectancy | WR% | PF | MaxDD | Friction R | Friction% |")
    p("|----------|--------|---------|-------|------------|-----|----|-------|------------|-----------|")
    for tr in GEOMETRY_TARGETS:
        label = f"D1_TAKER_{str(tr).replace('.', 'p')}R"
        c = results["cell_summaries"].get(label, {})
        p(f"| {tr}R | {c.get('total_trades',0)} "
          f"| {c.get('total_gross_r',0.0):+.4f} "
          f"| {c.get('total_net_r',0.0):+.4f} "
          f"| {c.get('expectancy_net_r',0.0):+.6f} "
          f"| {c.get('win_rate',0.0):.1f}% "
          f"| {c.get('profit_factor',0.0):.3f} "
          f"| {c.get('max_drawdown_r',0.0):.4f} "
          f"| {c.get('total_friction_r',0.0):+.4f} "
          f"| {c.get('friction_drag_pct',0.0):.1f}% |")
    p()

    # D-2 Friction Decomposition
    h(2, "D-2 -- Execution Friction Decomposition (Fixed 4R, Varying Fill Model)")
    p()
    p("| Fill Model | Trades | Gross R | Net R | Expectancy | WR% | PF | Fee R | Borrow R | Friction R | Friction% |")
    p("|------------|--------|---------|-------|------------|-----|----|-------|----------|------------|-----------|")
    for fm_id in [FILL_MODEL_TAKER, FILL_MODEL_MAKER_TOUCH, FILL_MODEL_MAKER_CONSERVATIVE]:
        label = f"D2_{fm_id}_4R"
        c = results["cell_summaries"].get(label, {})
        p(f"| {fm_id} | {c.get('total_trades',0)} "
          f"| {c.get('total_gross_r',0.0):+.4f} "
          f"| {c.get('total_net_r',0.0):+.4f} "
          f"| {c.get('expectancy_net_r',0.0):+.6f} "
          f"| {c.get('win_rate',0.0):.1f}% "
          f"| {c.get('profit_factor',0.0):.3f} "
          f"| {c.get('total_fee_r',0.0):+.4f} "
          f"| {c.get('total_borrow_r',0.0):+.4f} "
          f"| {c.get('total_friction_r',0.0):+.4f} "
          f"| {c.get('friction_drag_pct',0.0):.1f}% |")
    p()
    p("**Causal note**: Changing entry fill model changes `entry_fill` => recomputes "
      "`risk_per_unit = |entry_fill - stop|` => recomputes planned R:R => firewall may "
      "accept/reject different trades. Gross R differences between models reflect "
      "both fill-price improvement AND different trade populations passing the firewall.")
    p()

    # D-3 Combined Matrix
    h(2, "D-3 -- Combined Matrix (Geometry x Fill Model)")
    p()
    p("| Fill Model | Target | Trades | Net R | WR% | PF | Friction R | Friction% |")
    p("|------------|--------|--------|-------|-----|----|------------|-----------|")
    for fm_id in [FILL_MODEL_TAKER, FILL_MODEL_MAKER_TOUCH, FILL_MODEL_MAKER_CONSERVATIVE]:
        for tr in GEOMETRY_TARGETS:
            label = f"D3_{fm_id}_{str(tr).replace('.', 'p')}R"
            c = results["cell_summaries"].get(label, {})
            p(f"| {fm_id} | {tr}R "
              f"| {c.get('total_trades',0)} "
              f"| {c.get('total_net_r',0.0):+.4f} "
              f"| {c.get('win_rate',0.0):.1f}% "
              f"| {c.get('profit_factor',0.0):.3f} "
              f"| {c.get('total_friction_r',0.0):+.4f} "
              f"| {c.get('friction_drag_pct',0.0):.1f}% |")
    p()

    # Forensic Interpretation
    h(2, "Forensic Interpretation")
    p()
    h(3, "1. Control Reproduction Verdict")
    p()
    d0 = results["cell_summaries"].get("D0_CTRL", {})
    d0_trades = d0.get("total_trades", 0)
    d0_net = d0.get("total_net_r", 0.0)
    p(f"D-0 executed **{d0_trades} trades** with total net R = **{d0_net:+.4f}R**. "
      f"Compare against Phase C STRUCTURAL_REGIME_RESEARCH_REPORT.md H_STRUCT_01 row.")
    p()
    h(3, "2. Gross Edge Characterisation")
    p()
    d0_gross = d0.get("total_gross_r", 0.0)
    d0_friction = d0.get("total_friction_r", 0.0)
    if d0_trades > 0:
        p(f"- Gross R pool: **{d0_gross:+.4f}R** across {d0_trades} trades")
        p(f"- Friction consumed: **{d0_friction:+.4f}R** ({d0.get('friction_drag_pct', 0.0):.1f}% of gross abs)")
        p(f"- Net R remaining: **{d0_net:+.4f}R**")
        if abs(d0_gross) > 1e-6:
            consumed_pct = abs(d0_friction) / abs(d0_gross) * 100.0
            if consumed_pct > 50.0:
                p(f"- WARNING: Friction consumed > 50% of gross -- edge is friction-sensitive.")
            elif consumed_pct > 25.0:
                p(f"- Friction consumed {consumed_pct:.1f}% of gross -- moderate sensitivity.")
            else:
                p(f"- Friction consumed {consumed_pct:.1f}% of gross -- low sensitivity.")
    else:
        p("- No trades executed in control -- no gross edge to characterise.")
    p()
    h(3, "3. Geometry Sensitivity Observation")
    p()
    p("If trade count is approximately constant across D-1 target levels (1.5R-4R), "
      "structural geometry is the binding constraint -- almost all candidates exceed even "
      "the lowest target. If trade count drops sharply as target increases, target proximity "
      "is limiting -- few setups offer enough room for higher targets.")
    p()
    h(3, "4. Execution Model Sensitivity")
    p()
    p("From D-2: if Net R differs meaningfully between fill models beyond what fee "
      "arithmetic alone predicts, fill-price changes are shifting trades in/out of the "
      "firewall -- the entry price is influencing the population of valid trades, not "
      "just the net P&L of the same trade set.")
    p()
    h(3, "5. Research Governance Statement")
    p()
    p("> This Phase D forensic study does NOT declare any configuration a winner. "
      "Results are forensic inputs to the Research Governor for scoping H_STRUCT_01 "
      "further research: (a) refinement into a distinct hypothesis, (b) dismissal as "
      "insufficient gross edge, or (c) continuation into VAL/OOS partitions.")
    p()

    return "\n".join(lines)


if __name__ == "__main__":
    t0 = time.time()
    results = run_experiment()
    elapsed = time.time() - t0

    print(f"\n{'=' * 80}")
    print(f"Experiment complete in {elapsed:.1f}s")
    print("=" * 80)

    results_dir = os.path.join(REPO_ROOT, "research", "results")
    os.makedirs(results_dir, exist_ok=True)

    # Save JSON (summaries only — skip large per-trade lists)
    json_payload = {k: v for k, v in results.items() if k != "cell_records"}
    json_path = os.path.join(results_dir, "execution_geometry_sweep_raw.json")
    with open(json_path, "w") as fh:
        json.dump(json_payload, fh, indent=2, default=str)
    print(f"Raw JSON : {json_path}")

    # Generate and save markdown report
    report_md = generate_report(results)
    report_path = os.path.join(results_dir, "EXECUTION_GEOMETRY_SWEEP_REPORT.md")
    with open(report_path, "w") as fh:
        fh.write(report_md)
    print(f"Report   : {report_path}")

    # Console Summary
    print("\n" + "=" * 80)
    print("PHASE D SUMMARY -- All Cells")
    print("=" * 80)
    print(f"{'Cell':<45} {'Trades':>6} {'Net R':>10} {'WR%':>6} {'PF':>7} {'Frict%':>7}")
    print("-" * 80)
    for cell_id, c in results["cell_summaries"].items():
        print(
            f"{cell_id:<45} {c.get('total_trades', 0):>6} "
            f"{c.get('total_net_r', 0.0):>+10.4f} "
            f"{c.get('win_rate', 0.0):>6.1f}% "
            f"{c.get('profit_factor', 0.0):>7.3f} "
            f"{c.get('friction_drag_pct', 0.0):>6.1f}%"
        )
    print("=" * 80)
    print("\nPhase D complete. No configuration declared winner.")
