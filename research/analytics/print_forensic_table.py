import json
import datetime

with open("/home/mrcn2/crypto-platform/scratch/forensic_candidate_ledger.json") as f:
    d = json.load(f)

print(f"{'#':2s} | {'Candidate ID':34s} | {'Dir':5s} | {'Created (UTC)':16s} | {'MTF Align':16s} | {'MTF Retest':16s} | {'Term State':10s} | {'Rejection Reason':36s}")
print("-" * 155)

for idx, c in enumerate(d["candidates_ledger"], 1):
    c_dt = datetime.datetime.fromtimestamp(c["creation_timestamp"], tz=datetime.timezone.utc).strftime("%Y-%m-%d %H:%M") if c["creation_timestamp"] else "None"
    a_dt = datetime.datetime.fromtimestamp(c["mtf_alignment_timestamp"], tz=datetime.timezone.utc).strftime("%Y-%m-%d %H:%M") if c["mtf_alignment_timestamp"] else "None"
    r_dt = datetime.datetime.fromtimestamp(c["mtf_retest_timestamp"], tz=datetime.timezone.utc).strftime("%Y-%m-%d %H:%M") if c["mtf_retest_timestamp"] else "None"
    
    print(f"{idx:2d} | {c['candidate_id']:34s} | {c['direction']:5s} | {c_dt:16s} | {a_dt:16s} | {r_dt:16s} | {str(c['terminal_state']):10s} | {str(c['exact_rejection_reason']):36s}")
