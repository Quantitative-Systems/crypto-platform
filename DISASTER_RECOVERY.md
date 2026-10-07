# STRATA Digital Trading Platform — Disaster Recovery Runbook

## 1. Failure Scenarios & Standard Operating Procedures (SOP)

### Scenario A: Unscheduled Process Crash / Machine Restart
- **Behavior:** The operating system terminates the process or restarts the host.
- **Recovery Protocol:**
  1. Systemd / Docker automatically triggers container restart with `restart: unless-stopped`.
  2. At boot, `RecoveryWatchdog` runs **Startup Reconciliation**.
  3. Internal position table is cross-referenced with broker REST API (`GET /api/v3/openOrders`, `GET /api/v3/positionRisk`).
  4. If an orphan position is discovered:
     - System immediately fails-closed into `SAFE_MODE`.
     - Alert router sends emergency dispatch to registered webhooks/Telegram.
     - Human operator audits position before manual clearance.

### Scenario B: Market Data WebSocket Outage / Clock Drift
- **Behavior:** Binance or Bybit WebSocket disconnects, drops frames, or system clock skews > 1,500ms.
- **Recovery Protocol:**
  1. Exponential backoff reconnection loop executes with jitter (1.0s -> 2.0s -> 4.0s ... 30.0s).
  2. `BinanceRealtimeWSClient` identifies candle gap `open_ts > last_closed_open_ts + step_ms`.
  3. Gap callbacks fire and trigger REST kline backfill to recover missing OHLCV candles.
  4. Real-time feed status flags `DATA_DEGRADED` during recovery, temporarily pausing new signal generation until continuous feed is re-certified.

### Scenario C: Corrupted State Checkpoint
- **Behavior:** Sudden power cut during disk write causes partial or corrupted JSON checkpoint.
- **Recovery Protocol:**
  1. `RecoveryWatchdog.load_and_verify_checkpoint()` detects SHA-256 integrity mismatch.
  2. Corrupted file is rejected; system refuses blind resume.
  3. System fails-closed into `SAFE_MODE` and alerts operator.
  4. System falls back to previous verified atomic checkpoint (`*.tmp` atomic rename prevents partial write overwrites).

---

## 2. Disaster Recovery Escalation Matrix

| Severity | Condition | Action | Notification Channel |
| :--- | :--- | :--- | :--- |
| **P3 - Warning** | Intermittent WS drop (<10s) | Auto-reconnect with backoff | System log |
| **P2 - Degraded** | Clock drift > 1.5s or candle gap | REST backfill + pause entries | Slack / Webhook |
| **P1 - Critical** | Broker balance / order mismatch | Halt new trades + Safe Mode | Telegram + SMS / Webhook |
| **P0 - Emergency** | Orphan live position or unmanaged loss | Instant flatten (if configured) or hard halt | All channels + Multi-operator alert |
