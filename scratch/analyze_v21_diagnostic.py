import json
from collections import Counter

with open("scratch/v21_diagnostic_results.json") as f:
    d = json.load(f)

total_trades = 0
total_candidates = 0
total_signals = 0
gross_r = 0.0
net_r = 0.0
wins = 0
losses = 0
breakevens = 0
mdd = 0.0
running_r = 0.0
max_r = 0.0

for s in d.get("stream_results", []):
    trades = s.get("trades", [])
    total_trades += len(trades)
    
    # We might not have all_candidates in this JSON, let's check
    cands = s.get("all_candidates", [])
    total_candidates += len(cands)
    
    # Let's see if we have signals
    signals = s.get("all_signals", [])
    total_signals += len(signals)
    
    for t in trades:
        gr = t.get("gross_r", 0.0)
        nr = t.get("net_r", 0.0)
        gross_r += gr
        net_r += nr
        if nr > 0: wins += 1
        elif nr < 0: losses += 1
        else: breakevens += 1
        
        running_r += nr
        if running_r > max_r:
            max_r = running_r
        drawdown = max_r - running_r
        if drawdown > mdd:
            mdd = drawdown

win_rate = wins / total_trades if total_trades > 0 else 0
gross_loss = abs(sum(t.get("gross_r", 0.0) for s in d.get("stream_results", []) for t in s.get("trades", []) if t.get("gross_r", 0.0) < 0))
gross_profit = sum(t.get("gross_r", 0.0) for s in d.get("stream_results", []) for t in s.get("trades", []) if t.get("gross_r", 0.0) > 0)
pf = gross_profit / gross_loss if gross_loss > 0 else float("inf")

print(f"Total Candidates: {total_candidates}")
print(f"Total Signals: {total_signals}")
print(f"Total Trades Evaluated: {total_trades}")
print(f"Gross R: {gross_r:.2f}R")
print(f"Net R: {net_r:.2f}R")
print(f"Win Rate: {win_rate*100:.1f}%")
print(f"Profit Factor: {pf:.2f}")
print(f"Max Drawdown: {mdd:.2f}R")
