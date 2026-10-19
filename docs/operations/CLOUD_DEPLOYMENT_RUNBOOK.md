# Crypto Platform — Cloud Deployment Runbook

## 1. Production Architecture Overview

The primary production environment for **Crypto Platform** runs on an **Oracle Cloud VPS** (Ubuntu 24.04, 1 GB RAM) utilizing Docker Compose, persistent volumes, and an automated GitHub Actions CI/CD deployment pipeline.

```
                      GITHUB ACTIONS CI/CD
                                │
        ┌───────────────────────┴───────────────────────┐
        ▼                                               ▼
   RUNNER BUILD                               RUNNER PRE-DEPLOY TEST
  - Multi-stage Docker Build                 - Run Container in Runner Sandbox
  - Push image to GitHub Packages (GHCR)     - Pull GHCR Image via Auth Token
  - Tag: ghcr.io/.../crypto-platform:<sha>    - Probe /health & /ready in Sandbox
        │                                               │
        └───────────────────────┬───────────────────────┘
                                ▼
                       SSH TO ORACLE HOST
  - Acquire Deployment Mutex Lock via flock: /var/lock/crypto-engine-deploy.lock
  - Pull pre-built GHCR image directly on host (No on-host compilation)
  - Tag existing running container image as rollback candidate: crypto-engine-prev
  - Zero-downtime swap via: docker compose -f deploy/docker-compose.oracle.yml up -d
  - Strict JSON Health Validation: /health (status=HEALTHY, real_capital=0.0)
  - Strict JSON Readiness Validation: /ready (status=READY, supervisor=true, reconciliation=true)
  - Automated Instant Rollback to .last_known_good_image if probes fail
  - Persistent Volumes Preserved: crypto_platform_data, crypto_platform_research
```

---

## 2. Production Safety Invariants

Every production deployment strictly enforces the following core safety parameters:
- `ENVIRONMENT=production`
- `REAL_CAPITAL_AUTHORIZED_USD=0.00` (Hardware and software fail-closed limit)
- `LIVE_TRADING_ENABLED=false` (Hard locked)
- `HOST=0.0.0.0` inside container, bound strictly to `127.0.0.1:8080` on host loopback.
- **Persistent Data Preservation:** Docker volumes `crypto_platform_data` and `crypto_platform_research` are never pruned or recreated (`docker compose down -v` is strictly forbidden).

> [!CAUTION]
> **FAIL-CLOSED LIVE TRADING LOCK**: Setting `REAL_CAPITAL_AUTHORIZED_USD > 0.00` or `LIVE_TRADING_ENABLED=true` triggers an instant, unrecoverable `RuntimeError` during startup validation. The system will fail to start and immediately roll back.

---

## 3. Automated Oracle Deployment Pipeline (GitHub Actions)

### Workflow File: `.github/workflows/deploy-oracle.yml`
Deployments to the Oracle production VPS are triggered automatically upon merging PRs into deployment branches or manually via `workflow_dispatch`.

```yaml
name: Deploy Crypto Engine to Oracle Cloud VPS

on:
  workflow_dispatch:
    inputs:
      target_branch:
        description: 'Branch or commit SHA to deploy'
        required: true
        default: 'feature/crypto-platform-cloud-deployment'
```

### Steps Executed by the Pipeline:
1. **Runner Image Build**: Builds `Dockerfile` on GitHub-hosted Ubuntu runners (avoiding RAM exhaustion on the 1 GB VPS).
2. **GHCR Publishing**: Authenticates with `GITHUB_TOKEN` and pushes to `ghcr.io/quantitative-systems/crypto-platform:<sha>`.
3. **Runner Sandbox Pre-flight**: Launches container on the GitHub runner, pulls from GHCR, and verifies `/health` and `/ready` endpoints before touching the VPS.
4. **Target Host Execution**:
   - Establishes secure SSH connection using repository secret `ORACLE_SSH_KEY` to `ORACLE_HOST`.
   - Runs `scripts/deploy_oracle.sh <image_tag>`.
   - Verifies container health against `http://127.0.0.1:8080/health`.

---

## 4. Host Deployment Script (`scripts/deploy_oracle.sh`)

The deployment script executes with comprehensive resilience protections:

1. **Host Mutex Locking:**
   Acquires `/var/lock/crypto-engine-deploy.lock` via `flock` to prevent concurrent deploy operations.
2. **Pre-built Image Pull:**
   Pulls the image from GHCR with exponential backoff retries.
3. **Rollback Marker Tagging:**
   Inspects current running container image and records it to `/opt/crypto-platform/.last_known_good_image` and tags it as `crypto-engine-prev`.
4. **Compose Execution:**
   Runs `docker compose -f deploy/docker-compose.oracle.yml up -d --remove-orphans`.
5. **Strict JSON Health Probes:**
   Polls `http://127.0.0.1:8080/health` (requires `status == "HEALTHY"` and `real_capital_authorized == 0.0`) and `http://127.0.0.1:8080/ready` (requires `status == "READY"`, `supervisor_running == true`, `reconciliation_intact == true`).
6. **Instant Rollback on Failure:**
   If health checks do not pass within the timeout window, the script automatically rolls back to the previously tagged image (`crypto-engine-prev`), re-verifies health, and exits with a non-zero exit code to alert CI.

---

## 5. Docker Compose Configuration (`deploy/docker-compose.oracle.yml`)

```yaml
services:
  crypto-engine:
    image: ${IMAGE_NAME:-ghcr.io/quantitative-systems/crypto-platform:latest}
    container_name: crypto-engine
    restart: unless-stopped
    command: ["--mode", "PAPER", "--host", "0.0.0.0", "--port", "8080", "--no-research"]
    ports:
      # Strictly bound to loopback to prevent unauthorized external access
      - "127.0.0.1:8080:8080"
    environment:
      - ENVIRONMENT=production
      - REAL_CAPITAL_AUTHORIZED_USD=0.00
      - LIVE_TRADING_ENABLED=false
      - LOG_LEVEL=INFO
      - HOST=0.0.0.0
      - PORT=8080
    deploy:
      resources:
        limits:
          cpus: "1.0"
          memory: 512M
        reservations:
          cpus: "0.2"
          memory: 128M
    volumes:
      - crypto_platform_data:/app/data
      - crypto_platform_research:/app/research/results
    healthcheck:
      test: ["CMD-SHELL", "python3 cli.py health || exit 1"]
      interval: 20s
      timeout: 5s
      retries: 3
      start_period: 15s

volumes:
  crypto_platform_data:
    driver: local
  crypto_platform_research:
    driver: local
```

---

## 6. Manual Host Inspection & Health Verification

To inspect the running production instance via SSH tunnel:

```bash
# Open secure local tunnel to VPS loopback
ssh -i ~/.ssh/oracle_vps.key -L 8080:127.0.0.1:8080 ubuntu@129.225.72.92

# In a local terminal, verify health:
curl -fsS http://127.0.0.1:8080/health | jq .
curl -fsS http://127.0.0.1:8080/ready | jq .
curl -fsS http://127.0.0.1:8080/version | jq .

# Inspect container status and resource usage:
docker ps --filter "name=crypto-engine"
docker stats crypto-engine --no-stream

# View container logs:
docker logs --tail 100 crypto-engine
```

---

## 7. Emergency Incident Response & Manual Rollback

If anomalous behavior, degraded health, or persistent failure is observed on the production host:

### 1. Manual Rollback to Last Known Good Image
```bash
# On the Oracle VPS:
cd /opt/crypto-platform
LAST_IMAGE=$(cat .last_known_good_image 2>/dev/null || echo "crypto-engine-prev")
IMAGE_NAME="${LAST_IMAGE}" docker compose -f deploy/docker-compose.oracle.yml up -d
curl -fsS http://127.0.0.1:8080/health
```

### 2. Emergency Agent Pause / System Halt
Send authenticated halt command:
```bash
TOKEN=$(curl -s -X POST http://127.0.0.1:8080/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com", "password": "..."}' | jq -r .token)

curl -X POST http://127.0.0.1:8080/api/system/halt \
  -H "Authorization: Bearer ${TOKEN}"
```

### 3. State Integrity & Reconciliation Check
```bash
docker exec -it crypto-engine python3 cli.py health
docker exec -it crypto-engine python3 cli.py verify-contract
docker exec -it crypto-engine python3 cli.py reconcile
```

---

## 8. Secondary Staging Environments (Render & Vercel)

For ephemeral developer preview and staging testing:
- **Render Staging**: Configured via `render.yaml` for automatic container staging builds at `https://crypto-platform-staging.onrender.com`.
- **Vercel Edge Proxy**: Configured via `vercel.json` to proxy static assets to the staging backend.
