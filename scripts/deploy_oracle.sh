#!/usr/bin/env bash
set -euo pipefail

# ==============================================================================
# Crypto Engine — Oracle Host Safe Container Deployment & Automated Rollback
# ==============================================================================
# Invariants:
# 1. Image is pre-built in CI outside Oracle
# 2. Paper/Shadow mode only; Real Capital Authorized = $0.00
# 3. Port 8080 bound strictly to loopback (127.0.0.1:8080)
# 4. Persistent SQLite and checkpoints preserved via named Docker volumes
# 5. Automated health check with instant rollback on failure
# ==============================================================================

# Determine script location and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Always execute with working directory set to project root
cd "${PROJECT_ROOT}"

IMAGE_NAME="${1:-ghcr.io/quantitative-systems/crypto-platform:latest}"
export IMAGE_NAME
CONTAINER_NAME="crypto-engine"
ROLLBACK_NAME="crypto-engine-prev"

# If COMPOSE_FILE is not provided, default to deploy/docker-compose.oracle.yml
COMPOSE_FILE="${COMPOSE_FILE:-deploy/docker-compose.oracle.yml}"
# If COMPOSE_FILE is relative, make it absolute anchored at PROJECT_ROOT
if [[ "${COMPOSE_FILE}" != /* ]] && [[ "${COMPOSE_FILE}" != [a-zA-Z]:/* ]] && [[ "${COMPOSE_FILE}" != [a-zA-Z]:\\* ]]; then
    COMPOSE_FILE="${PROJECT_ROOT}/${COMPOSE_FILE}"
fi

# Probe Timing Configurations (Overridable for fast test suites)
HEALTH_ATTEMPTS="${HEALTH_ATTEMPTS:-15}"
HEALTH_SLEEP="${HEALTH_SLEEP:-2}"
ROLLBACK_ATTEMPTS="${ROLLBACK_ATTEMPTS:-15}"
ROLLBACK_SLEEP="${ROLLBACK_SLEEP:-2}"

# Optional command overrides for test harnesses
if [ -n "${DOCKER_BIN:-}" ]; then
    docker() { "${DOCKER_BIN}" "$@"; }
fi
if [ -n "${CURL_BIN:-}" ]; then
    curl() { "${CURL_BIN}" "$@"; }
fi

# ------------------------------------------------------------------------------
# Robust JSON Health Validator
# Strict: Rejects UNHEALTHY, DEGRADED, malformed, empty, or real_capital != 0.0
# ------------------------------------------------------------------------------
validate_health_json() {
    local raw_json="${1:-}"
    python3 -c "
import sys, json
try:
    raw = sys.argv[1].strip()
    if not raw:
        sys.exit(1)
    data = json.loads(raw)
    status = data.get('status')
    if status != 'HEALTHY':
        sys.exit(1)
    cap = float(data.get('real_capital_authorized', -1))
    if abs(cap - 0.0) > 1e-6:
        sys.exit(1)
    sys.exit(0)
except Exception:
    sys.exit(1)
" "$raw_json" 2>/dev/null
}

echo "======================================================================"
echo "CRYPTO ENGINE — DEPLOYMENT TO ORACLE HOST"
echo "Target Image: ${IMAGE_NAME}"
echo "Project Root: ${PROJECT_ROOT}"
echo "Compose File: ${COMPOSE_FILE}"
echo "======================================================================"

# Step 0: Pre-flight validation of Compose file and Docker config
# Invariant: Must fail closed BEFORE stopping or renaming the running container!
echo "[0/5] Pre-flight validation of Compose file and Docker environment..."
if [ ! -f "${COMPOSE_FILE}" ]; then
    echo "FATAL: Deployment compose file does not exist: ${COMPOSE_FILE}" >&2
    exit 1
fi

if ! IMAGE_NAME="${IMAGE_NAME}" docker compose -f "${COMPOSE_FILE}" config >/dev/null 2>&1; then
    echo "FATAL: Docker Compose configuration validation failed for ${COMPOSE_FILE}!" >&2
    IMAGE_NAME="${IMAGE_NAME}" docker compose -f "${COMPOSE_FILE}" config >&2 || true
    exit 1
fi

# Step 1: Pull updated image (fails closed before touching running containers)
echo "[1/5] Pulling verified container image from registry..."
docker pull "${IMAGE_NAME}"

# Step 2: Prepare rollback container snapshot
echo "[2/5] Creating rollback backup snapshot..."
HAD_PREV_CONTAINER=false
if [ "$(docker ps -q -f name=^/${CONTAINER_NAME}$)" ]; then
    echo "Stopping existing ${CONTAINER_NAME} and preserving as ${ROLLBACK_NAME}..."
    docker stop "${CONTAINER_NAME}" || true
    docker rename "${CONTAINER_NAME}" "${ROLLBACK_NAME}" 2>/dev/null || true
    HAD_PREV_CONTAINER=true
elif [ "$(docker ps -aq -f name=^/${CONTAINER_NAME}$)" ]; then
    echo "Existing ${CONTAINER_NAME} found in stopped state. Preserving as ${ROLLBACK_NAME}..."
    docker rename "${CONTAINER_NAME}" "${ROLLBACK_NAME}" 2>/dev/null || true
    HAD_PREV_CONTAINER=true
fi

# Step 3: Launch new container using docker-compose
# Note: Caught in conditional so set -e cannot abort script before rollback
echo "[3/5] Launching new Crypto Engine instance..."
NEW_CONTAINER_STARTED=false
if IMAGE_NAME="${IMAGE_NAME}" docker compose -f "${COMPOSE_FILE}" up -d; then
    NEW_CONTAINER_STARTED=true
    echo "New container launched successfully. Proceeding to health verification."
else
    echo "ERROR: Failed to launch new container via docker compose!"
fi

# Step 4: Health check loop (verify localhost loopback and fail-closed invariants)
HEALTHY=false
if [ "${NEW_CONTAINER_STARTED}" = true ]; then
    echo "[4/5] Running health verification probes against http://127.0.0.1:8080/api/health..."
    for attempt in $(seq 1 "${HEALTH_ATTEMPTS}"); do
        HEALTH_OUTPUT=$(curl -fsS --max-time 5 http://127.0.0.1:8080/api/health 2>/dev/null || true)
        if [ -n "${HEALTH_OUTPUT}" ] && validate_health_json "${HEALTH_OUTPUT}"; then
            echo "Health check attempt ${attempt}: PASS (Status=HEALTHY & Real Capital=$0.00)"
            HEALTHY=true
            break
        fi
        echo "Health check attempt ${attempt}: waiting for engine startup (sleeping ${HEALTH_SLEEP}s)..."
        sleep "${HEALTH_SLEEP}"
    done
else
    echo "[4/5] Skipping health probes: new container failed startup."
fi

# Step 5: Verification verdict & conditional rollback
if [ "${HEALTHY}" = true ]; then
    echo "[5/5] Deployment SUCCESSFUL. Purging temporary rollback container..."
    if [ "$(docker ps -aq -f name=^/${ROLLBACK_NAME}$)" ]; then
        docker rm -f "${ROLLBACK_NAME}" 2>/dev/null || true
    fi
    echo "======================================================================"
    echo "CRYPTO ENGINE IS LIVE & HEALTHY ON 127.0.0.1:8080"
    echo "Execution Mode: PAPER | Real Capital: $0.00 | Research Daemon: DISABLED"
    echo "======================================================================"
    exit 0
else
    echo "======================================================================"
    echo "CRITICAL WARNING: Health check failed or invariants breached!"
    echo "Initiating automatic rollback to previous container..."
    echo "======================================================================"
    # Tear down failed new container (without touching named volumes)
    IMAGE_NAME="${IMAGE_NAME}" docker compose -f "${COMPOSE_FILE}" down 2>/dev/null || true
    docker rm -f "${CONTAINER_NAME}" 2>/dev/null || true
    
    if [ "${HAD_PREV_CONTAINER}" = true ] && [ "$(docker ps -aq -f name=^/${ROLLBACK_NAME}$)" ]; then
        echo "Restoring ${ROLLBACK_NAME} -> ${CONTAINER_NAME}..."
        docker rename "${ROLLBACK_NAME}" "${CONTAINER_NAME}" 2>/dev/null || true
        docker start "${CONTAINER_NAME}"
        
        # Verify restored container status
        CONTAINER_STATUS=$(docker inspect --format '{{.State.Status}}' "${CONTAINER_NAME}" 2>/dev/null || echo "unknown")
        echo "Restored container status: ${CONTAINER_STATUS}"

        # Verify port binding
        PORT_BINDING=$(docker port "${CONTAINER_NAME}" 2>/dev/null || echo "none")
        echo "Restored container port binding: ${PORT_BINDING}"

        # Verify restored container health
        echo "Verifying health of restored rollback container..."
        ROLLBACK_HEALTHY=false
        for attempt in $(seq 1 "${ROLLBACK_ATTEMPTS}"); do
            RESTORED_HEALTH=$(curl -fsS --max-time 5 http://127.0.0.1:8080/api/health 2>/dev/null || true)
            if [ -n "${RESTORED_HEALTH}" ] && validate_health_json "${RESTORED_HEALTH}"; then
                echo "Rollback verification attempt ${attempt}: PASS (Restored container healthy & Real Capital=\$0.00)"
                ROLLBACK_HEALTHY=true
                break
            fi
            echo "Rollback health check attempt ${attempt}: waiting for container (sleeping ${ROLLBACK_SLEEP}s)..."
            sleep "${ROLLBACK_SLEEP}"
        done
        
        if [ "${ROLLBACK_HEALTHY}" = true ]; then
            echo "Rollback successfully restored previous working container."
            echo "WARNING: Deployment failed, but previous version is confirmed healthy."
        else
            echo "CRITICAL: Rollback failed! Restored container did not pass health check within window."
            echo "--- Restored Container Logs (last 50 lines) ---"
            docker logs --tail 50 "${CONTAINER_NAME}" 2>&1 || true
            echo "-----------------------------------------------"
        fi
    else
        echo "No prior running container was available to rollback."
    fi
    exit 1
fi
