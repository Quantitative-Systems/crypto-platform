import json

with open("scratch/composite_interaction_results.json") as f:
    data = json.load(f)

print("| Trade # | Stream | Dir | Baseline R | Polarity Status | Pol Acct R | BE Status | BE Acct R | Comp Status | Comp Realized R | Delta P | Delta BE | Delta C | Interaction I_i |")
print("| :---: | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |")

for r in data["opportunity_matrix"]:
    idx = f"#{r['index']:02d}"
    stream = r['stream_id']
    direction = "LONG" if "LONG" in r['direction'] else "SHORT"
    base_r = f"{r['b_realized_r']:+.4f}R"
    pol_s = r['pol_status']
    pol_r = f"{r['pol_accounting_r']:+.4f}R"
    be_s = r['be_status']
    be_r = f"{r['be_accounting_r']:+.4f}R"
    comp_s = r['comp_status']
    comp_r = f"{r['comp_accounting_r']:+.4f}R"
    dp = f"{r['delta_p']:+.4f}R"
    dbe = f"{r['delta_be']:+.4f}R"
    dc = f"{r['delta_c']:+.4f}R"
    ii = f"{r['interaction_i']:+.4f}R"
    print(f"| {idx} | {stream} | {direction} | {base_r} | {pol_s} | {pol_r} | {be_s} | {be_r} | {comp_s} | {comp_r} | {dp} | {dbe} | {dc} | {ii} |")

print("\n--- SUMMARY TOTALS ---")
acct = data["interaction_accounting"]
print(f"Total Delta P : {acct['total_delta_p_r']:+.4f}R")
print(f"Total Delta BE: {acct['total_delta_be_r']:+.4f}R")
print(f"Linear Sum    : {acct['linear_sum_deltas_r']:+.4f}R")
print(f"Total Delta C : {acct['total_delta_c_r']:+.4f}R")
print(f"Total I       : {acct['total_interaction_r']:+.4f}R [{acct['interaction_type']}]")
