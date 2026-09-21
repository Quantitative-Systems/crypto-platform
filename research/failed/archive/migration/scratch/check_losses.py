import json

with open("scratch/anchor2_dev_certified_results.json", "r") as f:
    d = json.load(f)

trades = d["all_trades"]
print(f"Total trades: {len(trades)}")

wins = [t for t in trades if t["net_r"] > 0]
losses = [t for t in trades if t["net_r"] < 0]
be = [t for t in trades if t["net_r"] == 0]

print(f"Wins: {len(wins)}, Losses: {len(losses)}, Breakeven: {len(be)}")

net_r_total = sum(t["net_r"] for t in trades)
print(f"Net R total: {net_r_total:.4f}R")

mfe_lt_05 = [t for t in losses if t["mfe_r"] < 0.5]
mfe_05_to_10 = [t for t in losses if 0.5 <= t["mfe_r"] < 1.0]
mfe_ge_10 = [t for t in losses if t["mfe_r"] >= 1.0]

print(f"\n--- LOSSES WITH MFE < 0.5R ({len(mfe_lt_05)}/20) ---")
for t in mfe_lt_05:
    tid = t["trade_id"]
    mfe = t["mfe_r"]
    mae = t["mae_r"]
    pnl = t["net_r"]
    ex = t.get("exit_reason")
    print(f"  {tid} | MFE: {mfe:.4f}R | MAE: {mae:.4f}R | Net R: {pnl:.4f}R | Exit: {ex}")

print(f"\n--- LOSSES WITH 0.5R <= MFE < 1.0R ({len(mfe_05_to_10)}/20) ---")
for t in mfe_05_to_10:
    tid = t["trade_id"]
    mfe = t["mfe_r"]
    mae = t["mae_r"]
    pnl = t["net_r"]
    ex = t.get("exit_reason")
    print(f"  {tid} | MFE: {mfe:.4f}R | MAE: {mae:.4f}R | Net R: {pnl:.4f}R | Exit: {ex}")

print(f"\n--- LOSSES WITH MFE >= 1.0R ({len(mfe_ge_10)}/20) ---")
for t in mfe_ge_10:
    tid = t["trade_id"]
    mfe = t["mfe_r"]
    mae = t["mae_r"]
    pnl = t["net_r"]
    ex = t.get("exit_reason")
    print(f"  {tid} | MFE: {mfe:.4f}R | MAE: {mae:.4f}R | Net R: {pnl:.4f}R | Exit: {ex}")

print(f"\n--- WINS ({len(wins)}) ---")
for t in wins:
    tid = t["trade_id"]
    mfe = t["mfe_r"]
    mae = t["mae_r"]
    pnl = t["net_r"]
    ex = t.get("exit_reason")
    print(f"  {tid} | MFE: {mfe:.4f}R | MAE: {mae:.4f}R | Net R: {pnl:.4f}R | Exit: {ex}")
