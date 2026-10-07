# STRATA Digital Trading Platform — Rollback Guide

## 1. Rollback Principles

In financial trading infrastructure, rollbacks must prioritize **capital preservation** and **state determinism** over system uptime:

1. **Safety First:** If an upgraded component exhibits unexpected behavior, immediately revert to the certified engineering baseline (`strata-v1.0.0-engineering-baseline`).
2. **Never Abandon State:** Internal trade ledgers and execution journals must be preserved during software rollbacks.
3. **No Unmanaged Positions:** If broker orders or open positions exist, verify them via `RecoveryWatchdog.verify_startup_reconciliation` before resuming execution.

---

## 2. Emergency Instant Rollback (Zero Downtime)

### Step 1: Halt New Trade Dispatch
Trigger safe mode via CLI:
```bash
python cli.py emergency-stop
```
Or stop the systemd service / docker container:
```bash
sudo systemctl stop strata.service
# Or for Docker:
docker compose -f deploy/docker-compose.yml stop forward-paper
```

### Step 2: Checkout Certified Git Baseline
To revert code back to the certified engineering baseline:
```bash
git fetch origin --tags
git checkout strata-v1.0.0-engineering-baseline
```

### Step 3: Run Baseline Verification
Verify that the baseline code is completely intact:
```bash
pytest
python -m research.experiments.run_phase_r_replay_regression
python cli.py health
```
Expected result:
- 172/172 tests PASS
- 9,608 / 9,608 opportunities 100% match

### Step 4: Resume Platform Under Baseline
```bash
sudo systemctl start strata.service
# Or for Docker:
docker compose -f deploy/docker-compose.yml up -d forward-paper
```

---

## 3. Post-Rollback State Audit

After rolling back:
1. Run `python cli.py reconcile` to confirm internal ledger matches broker balance.
2. Check `data/checkpoints/` for state snapshot consistency.
3. Review system logs in `logs/` for root cause investigation.
