"""
Clean Population Analytics Engine (N=23 Unique Opportunities)
Computes all metrics for Phases 2 through 10 of the Day 40 Governance Directive.
"""

import json
import numpy as np
from collections import defaultdict

def main():
    with open('scratch/canonical_35_trade_audit_ledger.json') as f:
        all_35_trades = json.load(f)

    # Filter to 23 unique genuine opportunities (first occurrence of each trade_id)
    seen = set()
    clean_23 = []
    for t in all_35_trades:
        if t['trade_id'] not in seen:
            seen.add(t['trade_id'])
            clean_23.append(t)

    assert len(clean_23) == 23, f"Expected 23 unique opportunities, got {len(clean_23)}"
    print(f"Loaded {len(clean_23)} clean unique trade opportunities.")

    # -------------------------------------------------------------
    # PHASE 2 — CLEAN POPULATION RECONCILIATION
    # -------------------------------------------------------------
    total_opps = len(clean_23) # Denominator = 23
    wins = [t for t in clean_23 if t['realized_R'] > 0]
    losses = [t for t in clean_23 if t['realized_R'] < 0]
    initial_sl_exits = [t for t in clean_23 if t['exit_reason'] == 'INITIAL_LTF_SL']
    mtf_exits = [t for t in clean_23 if 'TRAIL' in t['exit_reason']]
    target_exits = [t for t in clean_23 if t['exit_reason'] == 'HTF_TP']
    htf_target_hits = [t for t in clean_23 if t['target_hit']]

    # Under H1.1 (+1.0R ratchet to Entry + 0.10R):
    protected_exits = [t for t in clean_23 if t['MFE_R'] >= 1.0 and t['realized_R'] < 0]

    print("\n=== PHASE 2: CLEAN POPULATION RECONCILIATION ===")
    print(f"Total Opportunities (N): {total_opps}")
    print(f"Wins: {len(wins)} / {total_opps} ({len(wins)/total_opps*100:.2f}%)")
    print(f"Losses: {len(losses)} / {total_opps} ({len(losses)/total_opps*100:.2f}%)")
    print(f"Protected Exits (H1.1): {len(protected_exits)} / {total_opps} ({len(protected_exits)/total_opps*100:.2f}%) [or {len(protected_exits)} / {len(losses)} losses ({len(protected_exits)/len(losses)*100:.2f}%)]")
    print(f"Initial-SL Exits: {len(initial_sl_exits)} / {total_opps} ({len(initial_sl_exits)/total_opps*100:.2f}%)")
    print(f"MTF Trailing Exits: {len(mtf_exits)} / {total_opps} ({len(mtf_exits)/total_opps*100:.2f}%)")
    print(f"Target Exits: {len(target_exits)} / {total_opps} ({len(target_exits)/total_opps*100:.2f}%)")
    print(f"HTF Target Hits: {len(htf_target_hits)} / {total_opps} ({len(htf_target_hits)/total_opps*100:.2f}%)")

    # -------------------------------------------------------------
    # PHASE 3 — CLEAN MFE / MAE FORENSICS
    # -------------------------------------------------------------
    group_a = [t for t in clean_23 if t['MFE_R'] < 0.5]
    group_b = [t for t in clean_23 if 0.5 <= t['MFE_R'] < 1.0]
    group_c = [t for t in clean_23 if 1.0 <= t['MFE_R'] < 2.0]
    group_d = [t for t in clean_23 if 2.0 <= t['MFE_R'] < 4.0]
    group_e = [t for t in clean_23 if t['MFE_R'] >= 4.0]

    groups = [
        ("GROUP A (MFE < 0.5R)", group_a),
        ("GROUP B (0.5R <= MFE < 1.0R)", group_b),
        ("GROUP C (1.0R <= MFE < 2.0R)", group_c),
        ("GROUP D (2.0R <= MFE < 4.0R)", group_d),
        ("GROUP E (MFE >= 4.0R)", group_e)
    ]

    print("\n=== PHASE 3: CLEAN MFE / MAE FORENSICS ===")
    for gname, gtrades in groups:
        cnt = len(gtrades)
        pct = (cnt / total_opps) * 100.0
        if cnt > 0:
            mfes = [t['MFE_R'] for t in gtrades]
            maes = [t['MAE_R'] for t in gtrades]
            r_vals = [t['realized_R'] for t in gtrades]
            exits = defaultdict(int)
            for t in gtrades:
                exits[t['exit_reason']] += 1
            exit_str = ", ".join(f"{k}: {v}" for k, v in exits.items())
            print(f"\n{gname}:")
            print(f"  Count: {cnt} / {total_opps} ({pct:.2f}%)")
            print(f"  Mean MFE: {np.mean(mfes):.4f} R | Median MFE: {np.median(mfes):.4f} R")
            print(f"  Mean MAE: {np.mean(maes):.4f} R | Median MAE: {np.median(maes):.4f} R")
            print(f"  Mean Realized R: {np.mean(r_vals):.4f} R | Median Realized R: {np.median(r_vals):.4f} R")
            print(f"  Exit Distribution: {exit_str}")
        else:
            print(f"\n{gname}: Count: 0 / {total_opps} (0.00%)")

    # -------------------------------------------------------------
    # PHASE 4 — ENTRY FAILURE FORENSICS (GROUP A)
    # -------------------------------------------------------------
    print("\n=== PHASE 4: ENTRY FAILURE FORENSICS (GROUP A: MFE < 0.5R) ===")
    print(f"Total Group A Trades: {len(group_a)} / {total_opps} ({len(group_a)/total_opps*100:.2f}%)")
    for i, t in enumerate(group_a):
        print(f"  [{i+1:02d}] {t['trade_id']} | {t['asset']} {t['timeframe_set']} {t['direction']} | entry={t['entry_price']} | SL={t['initial_SL']} | MFE={t['MFE_R']:.2f}R | MAE={t['MAE_R']:.2f}R | Realized={t['realized_R']:.2f}R | Exit={t['exit_reason']}")

    # -------------------------------------------------------------
    # PHASE 5 — TARGET REALITY FORENSICS
    # -------------------------------------------------------------
    print("\n=== PHASE 5: TARGET REALITY FORENSICS ===")
    ratios = []
    for t in clean_23:
        target_dist = t['planned_RR'] # In R
        mfe_r = t['MFE_R']
        ratio = (mfe_r / target_dist) if target_dist > 0 else 0.0
        ratios.append(ratio)

    print(f"Mean MFE / Planned Target Ratio: {np.mean(ratios)*100:.2f}%")
    print(f"Median MFE / Planned Target Ratio: {np.median(ratios)*100:.2f}%")
    print(f"Max MFE / Planned Target Ratio: {np.max(ratios)*100:.2f}%")

    ge_3r = sum(1 for t in clean_23 if t['MFE_R'] >= 3.0)
    ge_4r = sum(1 for t in clean_23 if t['MFE_R'] >= 4.0)
    ge_5r = sum(1 for t in clean_23 if t['MFE_R'] >= 5.0)
    ge_6r = sum(1 for t in clean_23 if t['MFE_R'] >= 6.0)

    print(f"Excursion Reachability:")
    print(f"  MFE >= 3.0R: {ge_3r} / {total_opps} ({ge_3r/total_opps*100:.2f}%)")
    print(f"  MFE >= 4.0R: {ge_4r} / {total_opps} ({ge_4r/total_opps*100:.2f}%)")
    print(f"  MFE >= 5.0R: {ge_5r} / {total_opps} ({ge_5r/total_opps*100:.2f}%)")
    print(f"  MFE >= 6.0R: {ge_6r} / {total_opps} ({ge_6r/total_opps*100:.2f}%)")
    print(f"  Target Hit Before Exit: {len(htf_target_hits)} / {total_opps} (0.00%)")

    # Counterfactual Fixed-Exit Diagnostic at 3R, 4R, 5R, 6R
    # If a trade reaches XR MFE, it could counterfactually exit at XR (net of taker/maker fees ~0.05R = (X - 0.05)R)
    # Otherwise it takes its baseline loss!
    for fix_r in [3.0, 4.0, 5.0, 6.0]:
        sim_r = []
        hits = 0
        for t in clean_23:
            if t['MFE_R'] >= fix_r:
                hits += 1
                sim_r.append(fix_r - 0.05) # Fixed exit realized net R
            else:
                sim_r.append(t['realized_R'])
        net_sim_r = sum(sim_r)
        exp_sim_r = np.mean(sim_r)
        print(f"  Fixed {fix_r:.0f}R Diagnostic: Hits={hits}/{total_opps} ({hits/total_opps*100:.1f}%) | Net R={net_sim_r:+.4f}R | Exp={exp_sim_r:+.4f}R")

    # -------------------------------------------------------------
    # PHASE 6 — MANAGEMENT VS ENTRY LEAKAGE
    # -------------------------------------------------------------
    print("\n=== PHASE 6: MANAGEMENT VS ENTRY LEAKAGE ===")
    imm_fail = [t for t in clean_23 if t['MFE_R'] < 0.5]
    pos_then_loss = [t for t in clean_23 if t['MFE_R'] >= 0.5 and t['realized_R'] < 0]
    profit_exits = [t for t in clean_23 if t['realized_R'] > 0]

    imm_loss_r = sum(t['realized_R'] for t in imm_fail)
    pos_loss_r = sum(t['realized_R'] for t in pos_then_loss)
    win_r = sum(t['realized_R'] for t in profit_exits)
    total_net_r = sum(t['realized_R'] for t in clean_23)

    print(f"Total Net Realized R (Clean N=23): {total_net_r:+.4f} R (Expectancy: {np.mean([t['realized_R'] for t in clean_23]):+.4f} R)")
    print(f"1. Immediate Failure (MFE < 0.5R): N={len(imm_fail)} / {total_opps} ({len(imm_fail)/total_opps*100:.1f}%) | Total Loss = {imm_loss_r:+.4f} R ({abs(imm_loss_r)/abs(total_net_r)*100:.1f}% of net loss)")
    print(f"2. Excursion Bleed (MFE >= 0.5R, Realized < 0): N={len(pos_then_loss)} / {total_opps} ({len(pos_then_loss)/total_opps*100:.1f}%) | Total Loss = {pos_loss_r:+.4f} R ({abs(pos_loss_r)/abs(total_net_r)*100:.1f}% of net loss)")
    print(f"3. Profitable Exits: N={len(profit_exits)} / {total_opps} ({len(profit_exits)/total_opps*100:.1f}%) | Total Profit = {win_r:+.4f} R")

    # Counterfactual Effect of HYP_MGT_LOCAL_TRAIL_01 on Clean N=23
    h1_1_r = []
    for t in clean_23:
        if t['realized_R'] > 0:
            h1_1_r.append(t['realized_R']) # Winner kept intact
        elif t['MFE_R'] >= 1.0:
            h1_1_r.append(0.0482) # Loss protected
        else:
            h1_1_r.append(t['realized_R'])
    print(f"Counterfactual H1.1 on Clean N=23: Baseline Net R={total_net_r:+.4f}R -> Treatment Net R={sum(h1_1_r):+.4f}R (Delta: {sum(h1_1_r) - total_net_r:+.4f}R, Exp={np.mean(h1_1_r):+.4f}R)")

    # -------------------------------------------------------------
    # PHASE 7 — ASSET / TIMEFRAME / REGIME STRATIFICATION
    # -------------------------------------------------------------
    print("\n=== PHASE 7: STRATIFICATION (CLEAN N=23) ===")
    for asset in ["BTC", "ETH", "SOL"]:
        at = [t for t in clean_23 if t['asset'] == asset]
        r_list = [t['realized_R'] for t in at]
        wins_cnt = sum(1 for r in r_list if r > 0)
        net_r = sum(r_list)
        exp = np.mean(r_list) if r_list else 0.0
        print(f"Asset {asset:4s}: N={len(at):2d} ({len(at)/total_opps*100:4.1f}%) | Wins={wins_cnt} | Net R={net_r:+7.4f}R | Exp={exp:+7.4f}R | Mean MFE={np.mean([t['MFE_R'] for t in at]):.2f}R")

    print("")
    for tf in ["SET_1", "SET_2", "SET_3", "SET_4", "SET_5"]:
        tft = [t for t in clean_23 if t['timeframe_set'] == tf]
        r_list = [t['realized_R'] for t in tft]
        wins_cnt = sum(1 for r in r_list if r > 0)
        net_r = sum(r_list)
        exp = np.mean(r_list) if r_list else 0.0
        print(f"Timeframe {tf:5s}: N={len(tft):2d} ({len(tft)/total_opps*100:4.1f}%) | Wins={wins_cnt} | Net R={net_r:+7.4f}R | Exp={exp:+7.4f}R")

    # -------------------------------------------------------------
    # PHASE 8 — DEPENDENCY & CLUSTERING
    # -------------------------------------------------------------
    print("\n=== PHASE 8: DEPENDENCY & CLUSTERING ===")
    # Count trades with overlapping timestamps
    sorted_trades = sorted(clean_23, key=lambda x: x['entry_timestamp'])
    clusters = []
    current_cluster = [sorted_trades[0]]
    current_end = sorted_trades[0]['exit_timestamp']

    for t in sorted_trades[1:]:
        if t['entry_timestamp'] < current_end:
            current_cluster.append(t)
            current_end = max(current_end, t['exit_timestamp'])
        else:
            clusters.append(current_cluster)
            current_cluster = [t]
            current_end = t['exit_timestamp']
    if current_cluster:
        clusters.append(current_cluster)

    overlapping_trades = sum(len(c) for c in clusters if len(c) > 1)
    print(f"Raw Trades: {len(clean_23)}")
    print(f"Independent Event Clusters: {len(clusters)}")
    print(f"Overlapping Trades in Multi-Trade Clusters: {overlapping_trades} / {total_opps} ({overlapping_trades/total_opps*100:.1f}%)")

    # -------------------------------------------------------------
    # PHASE 9 — COST ROBUSTNESS
    # -------------------------------------------------------------
    print("\n=== PHASE 9: COST SENSITIVITY ===")
    # Base friction = fees + slippage
    base_gross_r = sum(t['realized_R'] + t['fees'] + t['slippage'] for t in clean_23)
    base_friction_r = sum(t['fees'] + t['slippage'] for t in clean_23)
    print(f"Gross R: {base_gross_r:+.4f} R | Base Friction: {base_friction_r:.4f} R")

    for mult_label, mult in [("BASE", 1.0), ("+25%", 1.25), ("+50%", 1.50), ("+100%", 2.0), ("+200%", 3.0)]:
        fric = base_friction_r * mult
        net_r = base_gross_r - fric
        exp_r = net_r / total_opps
        # PF calculation
        pos_sum = sum(t['realized_R'] for t in clean_23 if t['realized_R'] > 0)
        neg_sum = abs(sum(t['realized_R'] for t in clean_23 if t['realized_R'] < 0)) + (fric - base_friction_r)
        pf = pos_sum / neg_sum if neg_sum > 0 else 0.0
        print(f"Cost {mult_label:5s}: Friction={fric:.4f}R | Net R={net_r:+.4f}R | Exp={exp_r:+.4f}R | PF={pf:.4f}")

if __name__ == '__main__':
    main()
