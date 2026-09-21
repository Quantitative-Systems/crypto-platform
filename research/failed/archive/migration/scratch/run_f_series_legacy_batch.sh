#!/bin/bash
# Legacy-stop base F-series batch (Development partition only)
cd /home/mrcn2/crypto-platform
E=python3
echo "=== LEGACY F BATCH START $(date -u) ==="
echo "--- EXP_F1L_TGT_STRUCT_MILESTONE_01 ---"
$E research/experiments/run_canonical_replay_engine.py --treatment EXP_F1L_TGT_STRUCT_MILESTONE_01 --output scratch/f1l_tgt_struct_milestone_01_dev_results.json --workers 12 || echo "F1L FAILED"
echo "--- EXP_F2L_TGT_STRUCT_KZFRESH_7D ---"
$E research/experiments/run_canonical_replay_engine.py --treatment EXP_F2L_TGT_STRUCT_KZFRESH_7D --output scratch/f2l_tgt_struct_kzfresh_7d_dev_results.json --workers 12 || echo "F2L FAILED"
echo "--- EXP_F2BL_TGT_STRUCT_KZFRESH_30D ---"
$E research/experiments/run_canonical_replay_engine.py --treatment EXP_F2BL_TGT_STRUCT_KZFRESH_30D --output scratch/f2bl_tgt_struct_kzfresh_30d_dev_results.json --workers 12 || echo "F2BL FAILED"
echo "--- EXP_F4L_TGT_STRUCT_RETESTFRESH_12H ---"
$E research/experiments/run_canonical_replay_engine.py --treatment EXP_F4L_TGT_STRUCT_RETESTFRESH_12H --output scratch/f4l_tgt_struct_retestfresh_12h_dev_results.json --workers 12 || echo "F4L FAILED"
echo "=== LEGACY F BATCH END $(date -u) ==="