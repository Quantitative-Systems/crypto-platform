import json

with open("scratch/anchor2_dev_certified_results.json", "r") as f:
    a2 = json.load(f)

with open("scratch/h0_dev_certified_results.json", "r") as f:
    h0 = json.load(f)

def analyze_candidates(data, name):
    print(f"\n==================== {name} WATERFALL ====================")
    total_bars = 0
    total_htf_qualified = 0
    total_mtf_aligned = 0
    total_mtf_retested = 0
    total_ltf_confirmed = 0
    total_entered = 0
    total_rejected = 0
    
    rejection_reasons = {}
    
    for s in data["stream_results"]:
        sid = s["stream_id"]
        total_bars += s.get("ltf_candles_count", 0)
        cands = s.get("all_candidates", [])
        trades = s.get("trades", [])
        
        entered_cands = [c for c in cands if c.get("state") == "ENTERED"]
        print(f"Stream {sid}: LTF Bars={s.get('ltf_candles_count')}, Candidates={len(cands)}, Entered={len(entered_cands)}, Fills={len(trades)}")
        
        for c in cands:
            st = c.get("state")
            if st == "ENTERED":
                total_entered += 1
            elif st == "REJECTED":
                total_rejected += 1
                reason = c.get("invalidation_reason", "UNKNOWN")
                rejection_reasons[reason] = rejection_reasons.get(reason, 0) + 1

    print(f"\nAggregate {name}:")
    print(f"  Total Market Bars: {total_bars}")
    print(f"  Total Candidate Setups Created: {total_entered + total_rejected}")
    print(f"  Total Entered: {total_entered}")
    print(f"  Total Rejected: {total_rejected}")
    print("  Rejection breakdown:")
    for r, count in sorted(rejection_reasons.items(), key=lambda x: x[1], reverse=True):
        print(f"    {r}: {count}")

analyze_candidates(h0, "H0 CONTROL")
analyze_candidates(a2, "ANCHOR_2 TREATMENT")
