# Phase R — Production Deployment & Operations Runbook

**Execution Mode:** `SHADOW_PAPER`  
**Capital Authorization:** `$0.00` (Strictly Zero Live Orders)

---

## 1. Quick-Start Commands

### A. Start Autonomous Trading Application (Shadow Mode)
```bash
# Starts 24/7 background shadow trading and boots web terminal on port 8080
python main.py --symbols BTCUSDT,ETHUSDT,SOLUSDT,BNBUSDT --port 8080
```
* Or via CLI:
```bash
python cli.py shadow
```

### B. Verify Frozen Research Contract
```bash
python cli.py verify-contract
```

### C. Run Full Test Suite
```bash
pytest tests/unit/ tests/integration/ -v
```

### D. Run Historical Replay Regression Test
```bash
python research/experiments/run_phase_r_replay_regression.py
```

### E. Run Automated Real-Time Dry-Run
```bash
python main.py --dry-run-seconds 10
```

---

## 2. Health Check & Telemetry Inspection

### A. API Endpoints
* **System Health Probe:**
  ```bash
  curl http://127.0.0.1:8080/api/health
  ```
* **Full Telemetry Snapshot:**
  ```bash
  curl http://127.0.0.1:8080/api/telemetry
  ```
* **Recent Closed-Candle Decisions:**
  ```bash
  curl http://127.0.0.1:8080/api/decisions
  ```
* **Audit Reconciliation:**
  ```bash
  curl http://127.0.0.1:8080/api/reconciliation
  ```
* **Drift & Regime Telemetry:**
  ```bash
  curl http://127.0.0.1:8080/api/drift
  ```

### B. Interactive Dashboard
Open a browser to:
```text
http://127.0.0.1:8080/dashboard
```

---

## 3. Graceful Shutdown & Disaster Recovery

* **Graceful Termination:** Send `SIGINT` (Ctrl+C) or `SIGTERM`. The supervisor closes WebSocket streams, flushes the immutable decision ledger to disk, and cleanly terminates.
* **Restart Recovery:** On startup, `AutonomousTradingSupervisor` automatically seeds the continuous 7-timeframe candle engine from the on-disk cache (`market_data/cache/`), and executes state reconciliation across past ledger rows.
