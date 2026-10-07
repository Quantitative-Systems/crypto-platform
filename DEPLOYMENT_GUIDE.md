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
