#!/bin/bash
# LEGACY F-Series Batch — EXHAUSTIVE_STRUCTURAL stop anchoring
# These treatments use the same stop mode as the certified positive result
# (EXP_TARGET_STRUCTURAL_01: N=20, +3.83R, PF=1.66)
#
# All non-LEGACY variants (F1-F4) came back strongly negative due to
# LOCAL_SWING micro-stops. The LEGACY variants restore the certified
# stop geometry and add controlled augmentations.

set -euo pipefail

cd /home/mrcn2/crypto-platform

LOGFILE="scratch/legacy_batch_run.log"
echo "=== LEGACY F-Series Batch Start $(date -u) ===" | tee "$LOGFILE"

# Legacy baseline — EXHAUSTIVE_STRUCTURAL stops, no mitigation check
echo "[START] EXP_BASE_TGTSTRUCT_LEGACY_STOP_01 $(date -u)" | tee -a "$LOGFILE"
python3 research/experiments/run_canonical_replay_engine.py \
    --treatment EXP_BASE_TGTSTRUCT_LEGACY_STOP_01 \
    --output scratch/exp_base_tgtstruct_legacy_stop_01_dev_results.json 2>&1 | tail -5 | tee -a "$LOGFILE"
echo "[COMPLETE] EXP_BASE_TGTSTRUCT_LEGACY_STOP_01 $(date -u)" | tee -a "$LOGFILE"

# F1L: Legacy + milestone 2.5R
echo "[START] EXP_F1L_TGT_STRUCT_MILESTONE_01 $(date -u)" | tee -a "$LOGFILE"
python3 research/experiments/run_canonical_replay_engine.py \
    --treatment EXP_F1L_TGT_STRUCT_MILESTONE_01 \
    --output scratch/exp_f1l_tgt_struct_milestone_01_dev_results.json 2>&1 | tail -5 | tee -a "$LOGFILE"
echo "[COMPLETE] EXP_F1L_TGT_STRUCT_MILESTONE_01 $(date -u)" | tee -a "$LOGFILE"

# F2L: Legacy + 7d keyzone freshness
echo "[START] EXP_F2L_TGT_STRUCT_KZFRESH_7D $(date -u)" | tee -a "$LOGFILE"
python3 research/experiments/run_canonical_replay_engine.py \
    --treatment EXP_F2L_TGT_STRUCT_KZFRESH_7D \
    --output scratch/exp_f2l_tgt_struct_kzfresh_7d_dev_results.json 2>&1 | tail -5 | tee -a "$LOGFILE"
echo "[COMPLETE] EXP_F2L_TGT_STRUCT_KZFRESH_7D $(date -u)" | tee -a "$LOGFILE"

# F2BL: Legacy + 30d keyzone freshness
echo "[START] EXP_F2BL_TGT_STRUCT_KZFRESH_30D $(date -u)" | tee -a "$LOGFILE"
python3 research/experiments/run_canonical_replay_engine.py \
    --treatment EXP_F2BL_TGT_STRUCT_KZFRESH_30D \
    --output scratch/exp_f2bl_tgt_struct_kzfresh_30d_dev_results.json 2>&1 | tail -5 | tee -a "$LOGFILE"
echo "[COMPLETE] EXP_F2BL_TGT_STRUCT_KZFRESH_30D $(date -u)" | tee -a "$LOGFILE"

# F4L: Legacy + retest latency 12h
echo "[START] EXP_F4L_TGT_STRUCT_RETESTFRESH_12H $(date -u)" | tee -a "$LOGFILE"
python3 research/experiments/run_canonical_replay_engine.py \
    --treatment EXP_F4L_TGT_STRUCT_RETESTFRESH_12H \
    --output scratch/exp_f4l_tgt_struct_retestfresh_12h_dev_results.json 2>&1 | tail -5 | tee -a "$LOGFILE"
echo "[COMPLETE] EXP_F4L_TGT_STRUCT_RETESTFRESH_12H $(date -u)" | tee -a "$LOGFILE"

# Stress tests on LEGACY base
echo "[START] STRESS_FEES_TGTSTRUCT_LEGACY $(date -u)" | tee -a "$LOGFILE"
python3 research/experiments/run_canonical_replay_engine.py \
    --treatment STRESS_FEES_TGTSTRUCT_LEGACY \
    --output scratch/stress_fees_tgtstruct_legacy_dev_results.json 2>&1 | tail -5 | tee -a "$LOGFILE"
echo "[COMPLETE] STRESS_FEES_TGTSTRUCT_LEGACY $(date -u)" | tee -a "$LOGFILE"

echo "[START] STRESS_SLIPPAGE_TGTSTRUCT_LEGACY $(date -u)" | tee -a "$LOGFILE"
python3 research/experiments/run_canonical_replay_engine.py \
    --treatment STRESS_SLIPPAGE_TGTSTRUCT_LEGACY \
    --output scratch/stress_slippage_tgtstruct_legacy_dev_results.json 2>&1 | tail -5 | tee -a "$LOGFILE"
echo "[COMPLETE] STRESS_SLIPPAGE_TGTSTRUCT_LEGACY $(date -u)" | tee -a "$LOGFILE"

echo "=== LEGACY F-Series Batch Complete $(date -u) ===" | tee -a "$LOGFILE"
