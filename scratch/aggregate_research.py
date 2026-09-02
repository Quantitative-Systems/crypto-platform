import os
import json
import glob
from collections import defaultdict

RESULTS_DIR = "/home/mrcn2/crypto-platform/research/results"

def analyze_all():
    files = glob.glob(os.path.join(RESULTS_DIR, "BASELINE_001_*.json"))
    
    # Keep latest file per stream_key
    stream_files = {}
    for f in files:
        basename = os.path.basename(f)
        # format: BASELINE_001_{asset}_{set}_{hyp}_{date}_{hash}.json
        parts = basename.split("_")
        # reconstruct stream name
        asset = parts[2]
        set_id = f"{parts[3]}_{parts[4]}"
        hyp = f"{parts[5]}_{parts[6]}_{parts[7]}"
        stream_key = f"{asset}_{set_id}_{hyp}"
        if stream_key not in stream_files or f > stream_files[stream_key]:
            stream_files[stream_key] = f

    print("=========================================================================================================")
    print("                      BASELINE 001 MULTI-ASSET & MULTI-TIMEFRAME RESULTS")
    print("=========================================================================================================")
    print(f"{'Stream':<32} | {'Trades':<6} | {'Win Rate':<9} | {'Net PnL ($)':<12} | {'PF':<6} | {'Avg R':<8} | {'Max DD':<8}")
    print("-" * 105)

    tot_trades = 0
    tot_wins = 0
    tot_losses = 0
    tot_net_pnl = 0.0
    tot_friction = 0.0

    for stream_key in sorted(stream_files.keys()):
        filepath = stream_files[stream_key]
        with open(filepath, "r") as fp:
            data = json.load(fp)
        m = data.get("metrics", {})
        trades = m.get("total_trades", 0)
        wr = m.get("win_rate", 0.0)
        net_pnl = m.get("net_profit_usd", 0.0)
        pf = m.get("profit_factor", "N/A")
        avg_r = m.get("average_r", "N/A")
        max_dd = m.get("max_drawdown_pct", 0.0)
        fric = m.get("total_friction_usd", 0.0)

        tot_trades += trades
        tot_wins += m.get("win_count", 0)
        tot_losses += m.get("loss_count", 0)
        tot_net_pnl += net_pnl
        tot_friction += fric

        pf_str = f"{pf:.2f}" if isinstance(pf, (int, float)) else str(pf)[:6]
        avg_r_str = f"{avg_r:.2f}" if isinstance(avg_r, (int, float)) else str(avg_r)[:6]
        max_dd_str = f"{max_dd*100:.1f}%" if isinstance(max_dd, (int, float)) else str(max_dd)

        print(f"{stream_key:<32} | {trades:<6} | {wr*100:<8.1f}% | ${net_pnl:<11.2f} | {pf_str:<6} | {avg_r_str:<8} | {max_dd_str:<8}")

    print("=" * 105)
    print(f"TOTAL TRADES: {tot_trades} | WINS: {tot_wins} | LOSSES: {tot_losses} | WIN RATE: {(tot_wins/tot_trades*100) if tot_trades else 0:.1f}%")
    print(f"PORTFOLIO NET PNL: ${tot_net_pnl:.2f} | TOTAL FRICTION: ${tot_friction:.2f}")

    # Now Trailing AB Experiments
    ab_files = glob.glob(os.path.join(RESULTS_DIR, "TRAILING_AB_EXPERIMENT_*.json"))
    stream_ab = {}
    for f in ab_files:
        basename = os.path.basename(f)
        parts = basename.split("_")
        asset = parts[3]
        set_id = f"{parts[4]}_{parts[5]}"
        key = f"{asset}_{set_id}"
        if key not in stream_ab or f > stream_ab[key]:
            stream_ab[key] = f

    print("\n=========================================================================================================")
    print("                 TRAILING A/B EXPERIMENT COMPARISON (NO TRAIL vs MTF TRAIL)")
    print("=========================================================================================================")
    print(f"{'Stream':<15} | {'A Trades':<8} | {'A WR%':<8} | {'A Net PnL':<10} | {'B Trades':<8} | {'B WR%':<8} | {'B Net PnL':<10} | {'PnL Delta':<10}")
    print("-" * 105)

    for key in sorted(stream_ab.keys()):
        filepath = stream_ab[key]
        with open(filepath, "r") as fp:
            data = json.load(fp)
        m = data.get("metrics", {})
        ma = m.get("baseline_a", {})
        mb = m.get("baseline_b", {})
        d = m.get("deltas", {})
        
        print(f"{key:<15} | {ma.get('total_trades', 0):<8} | {ma.get('win_rate', 0)*100:<7.1f}% | ${ma.get('net_profit_usd', 0):<9.2f} | {mb.get('total_trades', 0):<8} | {mb.get('win_rate', 0)*100:<7.1f}% | ${mb.get('net_profit_usd', 0):<9.2f} | ${d.get('net_profit_delta_usd', 0):<9.2f}")
    print("=" * 105)

if __name__ == "__main__":
    analyze_all()
