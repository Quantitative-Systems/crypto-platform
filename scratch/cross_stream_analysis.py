import json
from collections import defaultdict

def analyze_cross_stream(file_path, label):
    with open(file_path) as f:
        d = json.load(f)

    print("=" * 80)
    print(f"CROSS-STREAM ANALYSIS: {label}")
    print("=" * 80)

    trades = d.get("all_trades", [])
    stream_results = d.get("stream_results", [])

    # Map trades by stream
    stream_trades = defaultdict(list)
    for t in trades:
        s_id = t.get("stream_id")
        stream_trades[s_id].append(t)

    total_net_r = d.get("aggregate_performance", {}).get("net_r", 0.0)

    print(f"{'Stream ID':12s} | {'Asset':5s} | {'Set':6s} | {'Trades':6s} | {'Wins':4s} | {'Losses':6s} | {'WR (%)':6s} | {'Net R':9s} | {'Exp (R)':8s} | {'Contrib %':9s} | {'Status':20s}")
    print("-" * 115)

    all_stream_ids = [
        "BTC_SET_1", "BTC_SET_2", "BTC_SET_3", "BTC_SET_4", "BTC_SET_5",
        "ETH_SET_1", "ETH_SET_2", "ETH_SET_3", "ETH_SET_4", "ETH_SET_5",
        "SOL_SET_1", "SOL_SET_2", "SOL_SET_3", "SOL_SET_4", "SOL_SET_5",
    ]

    # Map status from stream_results
    sr_status = {}
    for s in stream_results:
        sr_status[s.get("stream_id")] = s.get("status", "OK")

    for sid in all_stream_ids:
        t_list = stream_trades[sid]
        parts = sid.split("_")
        asset = parts[0]
        tf_set = f"{parts[1]}_{parts[2]}"
        n = len(t_list)
        wins = sum(1 for t in t_list if t.get("net_r", 0.0) > 0.05)
        losses = sum(1 for t in t_list if t.get("net_r", 0.0) < -0.05)
        net_r = sum(t.get("net_r", 0.0) for t in t_list)
        exp = net_r / n if n > 0 else 0.0
        wr = wins / n * 100 if n > 0 else 0.0
        contrib = (net_r / total_net_r * 100) if (total_net_r != 0 and net_r != 0) else 0.0
        status = sr_status.get(sid, "OK")

        print(f"{sid:12s} | {asset:5s} | {tf_set:6s} | {n:6d} | {wins:4d} | {losses:6d} | {wr:6.1f} | {net_r:+9.4f} | {exp:+8.4f} | {contrib:+8.1f}% | {status:20s}")

    # Set rollups
    print("\n--- TIMEFRAME SET ROLLUP ---")
    for s_num in ["SET_1", "SET_2", "SET_3", "SET_4", "SET_5"]:
        s_trades = [t for t in trades if s_num in t.get("stream_id", "")]
        n = len(s_trades)
        net_r = sum(t.get("net_r", 0.0) for t in s_trades)
        wins = sum(1 for t in s_trades if t.get("net_r", 0.0) > 0.05)
        wr = wins / n * 100 if n > 0 else 0.0
        exp = net_r / n if n > 0 else 0.0
        print(f"  {s_num:6s}: N={n:2d} | Wins={wins:2d} | WR={wr:5.1f}% | Net R={net_r:+8.4f}R | Exp={exp:+7.4f}R")

    # Asset rollups
    print("\n--- ASSET ROLLUP ---")
    for a in ["BTC", "ETH", "SOL"]:
        a_trades = [t for t in trades if a in t.get("symbol", "")]
        n = len(a_trades)
        net_r = sum(t.get("net_r", 0.0) for t in a_trades)
        wins = sum(1 for t in a_trades if t.get("net_r", 0.0) > 0.05)
        wr = wins / n * 100 if n > 0 else 0.0
        exp = net_r / n if n > 0 else 0.0
        print(f"  {a:6s}: N={n:2d} | Wins={wins:2d} | WR={wr:5.1f}% | Net R={net_r:+8.4f}R | Exp={exp:+7.4f}R")

if __name__ == "__main__":
    analyze_cross_stream("scratch/exp_base_tgtstruct_legacy_stop_01_dev_results.json", "EXP_BASE_TGTSTRUCT_LEGACY_STOP_01 (Baseline)")
    analyze_cross_stream("scratch/exp_f1l_tgt_struct_milestone_01_dev_results.json", "EXP_F1L_TGT_STRUCT_MILESTONE_01 (Milestone 2.5R)")
    analyze_cross_stream("scratch/exp_f4l_tgt_struct_retestfresh_12h_dev_results.json", "EXP_F4L_TGT_STRUCT_RETESTFRESH_12H (Retest Freshness <=12h)")
