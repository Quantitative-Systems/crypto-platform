#!/bin/bash
# Kill any stuck processes and run the LEGACY batch
pkill -9 -f run_canonical_replay_engine 2>/dev/null
pkill -9 -f run_legacy_batch 2>/dev/null
pkill -9 -f run_f_series_batch 2>/dev/null
sleep 2
echo "Processes killed"
# Now run the batch
cd /home/mrcn2/crypto-platform
python3 scratch/run_legacy_v3.py > scratch/legacy_batch_v3_stdout.log 2>&1
echo "Batch complete"
