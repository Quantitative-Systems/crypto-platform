# Crypto Platform — Cloud Deployment Runbook

## 1. Quick Start & Prerequisites

The backend is packaged as a non-root Docker container configured via `Dockerfile` and `render.yaml`. It can be deployed to any modern container hosting platform (Render, Railway, Fly.io, or GCP Cloud Run).

### Environment Checklist
Ensure the following environment variables are configured in your staging service:
- `ENVIRONMENT=STAGING`
- `PLATFORM_ENV=staging`
- `REAL_CAPITAL_AUTHORIZED_USD=0.00`
- `LIVE_TRADING_ENABLED=false`
- `PORT=8080`
- `HOST=0.0.0.0`
- `CORS_ALLOWED_ORIGINS=*`

> [!CAUTION]
> Under NO circumstances should `REAL_CAPITAL_AUTHORIZED_USD` be set above `0.00` or `LIVE_TRADING_ENABLED` be set to `true`. The platform will enter `HARD_FAIL_CLOSED` emergency lock if these invariants are violated without cryptographic passkeys.

---

## 2. Zero-Cost Staging Deployment (Render Blueprint)

### Option A: Automatic Blueprint via GitHub (Recommended)
1. Push branch `feature/crypto-platform-cloud-deployment` to GitHub:
   ```bash
   git push origin feature/crypto-platform-cloud-deployment
   ```
2. Navigate to [dashboard.render.com](https://dashboard.render.com) > **Blueprints** > **New Blueprint Instance**.
3. Connect repository `Quantitative-Systems/crypto-platform` and select `render.yaml`.
4. Click **Apply**. Render will:
   - Build the container from `Dockerfile`.
   - Start the service binding to `0.0.0.0:$PORT`.
   - Register the `/health` endpoint for continuous health checking.
5. Service will be live at: `https://crypto-platform-staging.onrender.com`.

### Option B: Docker Run / Self-Hosted VPS
```bash
# Build production image locally or on staging server
docker build -t crypto-platform:staging .

# Run container with resource limits and restart policy
docker run -d \
  --name crypto-platform-staging \
  -p 8080:8080 \
  -e ENVIRONMENT=STAGING \
  -e REAL_CAPITAL_AUTHORIZED_USD=0.00 \
  -e LIVE_TRADING_ENABLED=false \
  --restart unless-stopped \
  crypto-platform:staging
```

---

## 3. Vercel Frontend Edge Deployment

For hosting the web administration terminal:
1. Connect repository to [Vercel](https://vercel.com).
2. Set Root Directory to `./`.
3. Vercel automatically detects `vercel.json` and serves the static terminal while proxying `/api/*` and `/health` requests to `https://crypto-platform-staging.onrender.com`.
4. Verify deployment:
   ```bash
   curl -I https://<your-vercel-domain>/terminal
   curl -I https://<your-vercel-domain>/health
   ```

---

## 4. Post-Deployment Verification Procedure

Execute the automated verification sequence against the staging deployment:

```bash
# 1. Check Root Health Probe
curl -fsS https://crypto-platform-staging.onrender.com/health

# Expected response:
# {"status": "HEALTHY", "real_capital_authorized": 0.0, "live_trading_status": "DISABLED_FAIL_CLOSED", ...}

# 2. Check Readiness Probe
curl -fsS https://crypto-platform-staging.onrender.com/ready

# 3. Check Platform Version & Frozen Contract Hash
curl -fsS https://crypto-platform-staging.onrender.com/version

# Expected contract hash:
# "8fbc923a104e7688c3a9f0e4b8592c30dfb0b9a67a84511d5e49f8721c432098"

# 4. Run Automated Smoke Test Suite
pytest tests/integration/test_cloud_staging_smoke.py -v
```

---

## 5. Rollback & Emergency Incident Procedures

If degraded health or anomalous behavior is detected in staging:
1. **Immediate Service Pause:**
   Send halt trigger to API:
   ```bash
   curl -X POST https://crypto-platform-staging.onrender.com/api/system/halt
   ```
2. **Revert Deployment:**
   In Render or Cloud Run dashboard, select the previous successful build and click **Rollback**.
3. **State Integrity Verification:**
   Run CLI state reconciliation:
   ```bash
   python cli.py reconcile
   python cli.py verify-contract
   ```
