# STRATA Digital Trading Platform — Production Deployment Guide

## 1. Architectural Architecture & Environments

STRATA operates under strict multi-environment isolation:

```
SHADOW (Passive Data Ingestion) 
  → PAPER (Zero-Capital Forward Simulation) 
    → BROKER DEMO (Testnet API Key Execution) 
      → MICRO-LIVE ($0.00 Default, Requires Signed Authorization) 
        → CONTROLLED-LIVE (Hard-Capped Max Exposure)
```

> **CRITICAL INVARIANT:** By default, all deployments initialize with `PLATFORM_LIVE_CAPITAL_USD=0.0`. Live adapters remain hard-disabled and fail-closed until multi-signature human authorization is explicitly mounted.

---

## 2. Prerequisites & System Requirements

- **Operating System:** Linux (Ubuntu 22.04 LTS / Debian 12 recommended) or Windows Server
- **Python Runtime:** Python 3.12+ (isolated venv or Docker container)
- **Memory:** Minimum 4GB RAM (8GB recommended for multi-timeframe caching)
- **Disk:** Fast NVMe SSD with minimum 20GB free space
- **Network:** Low-latency connection to Binance / Bybit public and authenticated endpoints (<50ms recommended)

---

## 3. Containerized Deployment (Docker & Docker Compose)

### 3.1 Environment Configuration
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Ensure that no live credentials or withdrawal keys are stored in `.env`.

### 3.2 Building and Launching Services
To build and launch the forward-paper execution service and institutional web dashboard:
```bash
docker compose -f deploy/docker-compose.yml up -d forward-paper web-dashboard
```

### 3.3 Verifying Service Health
Inspect container status and internal health checks:
```bash
docker compose -f deploy/docker-compose.yml ps
docker compose -f deploy/docker-compose.yml logs -f forward-paper
```

Test HTTP API health probe:
```bash
curl -f http://localhost:8080/api/health
```

---

## 4. Bare-Metal / Systemd Service Deployment

### 4.1 Systemd Service Installation
Copy the unit file to systemd directory:
```bash
sudo cp deploy/crypto-platform.service /etc/systemd/system/strata.service
sudo systemctl daemon-reload
```

### 4.2 Start and Enable Service
```bash
sudo systemctl enable --now strata.service
sudo systemctl status strata.service
```

### 4.3 Log Streaming
```bash
journalctl -u strata.service -f
```

---

## 5. Pre-Flight Verification Checklist

Before leaving the platform running in production:

1. [ ] Run unit tests: `pytest` (192/192 passing)
2. [ ] Run replay regression: `python -m research.experiments.run_phase_r_replay_regression` (9,608/9,608 opportunities 100% matched)
3. [ ] Run CLI contract verification: `python cli.py verify-contract`
4. [ ] Run CLI health check: `python cli.py health`
5. [ ] Verify live capital status: Confirm `PLATFORM_LIVE_CAPITAL_USD == 0.0`
6. [ ] Confirm broker keys have ZERO withdrawal privileges enabled.

---

## 6. 24/7 Production Operational Runbook

### 6.1 START (Clean Cold Boot)
```bash
# 1. Run pre-flight configuration and security validation
python cli.py validate-preflight

# 2. Verify immutable KING engine contract hash
python cli.py verify-contract

# 3. Start supervisor daemon in background or via docker-compose
docker compose up -d strata-platform

# 4. Probe readiness
curl -f http://127.0.0.1:8080/api/ready
```

### 6.2 STOP (Graceful Drain & Halt)
```bash
# 1. Issue operator pause to halt new order intent creation
curl -X POST http://127.0.0.1:8080/api/agent/pause

# 2. Send SIGTERM to process (allows current candle evaluation and checkpoint flush to finish)
docker compose stop -t 30 strata-platform

# 3. Verify zero orphan processes remain
ps aux | grep strata
```

### 6.3 RESTART (State Preserving Cycling)
```bash
# Graceful cycling with automated checkpoint restoration
docker compose restart -t 30 strata-platform

# Verify post-restart state reconciliation
python cli.py reconcile
```

### 6.4 RECOVER (Crash & Outage Recovery)
When an unexpected crash, kernel panic, or cloud VM restart occurs:
```bash
# 1. Inspect watchdog and checkpoint integrity
python -c "from execution.safety.watchdog import RecoveryWatchdog; wd = RecoveryWatchdog(); print(wd.load_and_verify_checkpoint())"

# 2. Execute reconciliation audit against connected broker exchanges
python cli.py reconcile

# 3. If zero orphan positions are confirmed, clear safe mode and restart
docker compose up -d strata-platform
```

### 6.5 ROLLBACK (Software Version Reversion)
If a software defect is detected post-deployment:
```bash
# 1. Stop current container
docker compose down

# 2. Revert code to certified release tag
git checkout v1.0.0-phase-r-baseline

# 3. Verify contract and regression tests
python cli.py verify-contract
python -m research.experiments.run_phase_r_replay_regression

# 4. Restart stable baseline
docker compose up -d --build strata-platform
```

### 6.6 DISASTER RECOVERY (Host Catastrophe / Complete Failover)
In the event of total server hardware loss:
```bash
# 1. Provision new server instance from standard image
# 2. Clone repository and restore encrypted database & checkpoints volume from off-site backup
rsync -avz backup-server:/backups/strata/data/ ./data/

# 3. Validate checkpoint checksums
python cli.py reconcile

# 4. Spin up containerized cluster
docker compose up -d strata-platform strata-gateway
```

