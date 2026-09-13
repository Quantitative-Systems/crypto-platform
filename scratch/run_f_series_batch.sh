#!/bin/bash
# F-series experiment batch (Development partition only)
cd /home/mrcn2/crypto-platform
E=python3
echo "=== BATCH START $(date -u) ==="
echo "--- RECERT EXP_TARGET_STRUCTURAL_01 ---"
$E research/experiments/run_canonical_replay_engine.py --treatment EXP_TARGET_STRUCTURAL_01 --output scratch/recert_target_structural_01_dev_results.json --workers 12 || echo "RECERT FAILED"
echo "--- EXP_F1_TGT_STRUCT_MILESTONE_01 ---"
$E research/experiments/run_canonical_replay_engine.py --treatment EXP_F1_TGT_STRUCT_MILESTONE_01 --output scratch/f1_tgt_struct_milestone_01_dev_results.json --workers 12 || echo "F1 FAILED"
echo "--- EXP_F2_TGT_STRUCT_KZFRESH_7D ---"
$E research/experiments/run_canonical_replay_engine.py --treatment EXP_F2_TGT_STRUCT_KZFRESH_7D --output scratch/f2_tgt_struct_kzfresh_7d_dev_results.json --workers 12 || echo "F2 FAILED"
echo "--- EXP_F2B_TGT_STRUCT_KZFRESH_30D ---"
$E research/experiments/run_canonical_replay_engine.py --treatment EXP_F2B_TGT_STRUCT_KZFRESH_30D --output scratch/f2b_tgt_struct_kzfresh_30d_dev_results.json --workers 12 || echo "F2B FAILED"
echo "--- EXP_F3_TGT_STRUCT_MAJORMTF_01 ---"
$E research/experiments/run_canonical_replay_engine.py --treatment EXP_F3_TGT_STRUCT_MAJORMTF_01 --output scratch/f3_tgt_struct_majormtf_01_dev_results.json --workers 12 || echo "F3 FAILED"
echo "=== BATCH END $(date -u) ==="
