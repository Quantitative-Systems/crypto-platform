#!/usr/bin/env python3
"""Run LEGACY F-Series batch experiments."""
import subprocess
import os
import sys
from datetime import datetime, timezone

os.chdir("/home/mrcn2/crypto-platform")

TREATMENTS = [
    ("EXP_BASE_TGTSTRUCT_LEGACY_STOP_01", "exp_base_tgtstruct_legacy_stop_01"),
    ("EXP_F1L_TGT_STRUCT_MILESTONE_01", "exp_f1l_tgt_struct_milestone_01"),
    ("EXP_F2L_TGT_STRUCT_KZFRESH_7D", "exp_f2l_tgt_struct_kzfresh_7d"),
    ("EXP_F2BL_TGT_STRUCT_KZFRESH_30D", "exp_f2bl_tgt_struct_kzfresh_30d"),
    ("EXP_F4L_TGT_STRUCT_RETESTFRESH_12H", "exp_f4l_tgt_struct_retestfresh_12h"),
    ("STRESS_FEES_TGTSTRUCT_LEGACY", "stress_fees_tgtstruct_legacy"),
    ("STRESS_SLIPPAGE_TGTSTRUCT_LEGACY", "stress_slippage_tgtstruct_legacy"),
]

LOGFILE = "scratch/legacy_batch_v3.log"

def log(msg):
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(LOGFILE, "a") as f:
        f.write(line + "\n")

log("=== LEGACY F-Series Batch V3 Start ===")

for treatment, fname in TREATMENTS:
    output = f"scratch/{fname}_dev_results.json"
    log(f"START {treatment}")
    try:
        result = subprocess.run(
            ["python3", "research/experiments/run_canonical_replay_engine.py",
             "--treatment", treatment, "--output", output, "--workers", "12"],
            capture_output=True, text=True, timeout=1800
        )
        log(f"COMPLETE {treatment} rc={result.returncode}")
        if result.returncode != 0:
            log(f"ERROR {treatment}: {result.stderr[-500:]}")
    except subprocess.TimeoutExpired:
        log(f"TIMEOUT {treatment}")
    except Exception as e:
        log(f"EXCEPTION {treatment}: {e}")

log("=== LEGACY F-Series Batch V3 Complete ===")
