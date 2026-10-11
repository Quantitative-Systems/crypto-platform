# Crypto Platform — Production Containerfile
# Multi-stage container build with non-root security & fail-closed invariants

FROM python:3.12-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt pyproject.toml ./
RUN pip install --no-cache-dir --user -r requirements.txt

# --- Final Runner Stage ---
FROM python:3.12-slim AS runner

WORKDIR /app

# Unprivileged system user
RUN groupadd -r cryptoplatform && useradd -r -g cryptoplatform -u 1001 -m cryptoplatform

# Copy python dependencies from builder
COPY --from=builder /root/.local /home/cryptoplatform/.local
ENV PATH=/home/cryptoplatform/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app
ENV ENVIRONMENT=STAGING
ENV PLATFORM_ENV=staging
ENV REAL_CAPITAL_AUTHORIZED_USD=0.00
ENV LIVE_TRADING_ENABLED=false
ENV HOST=0.0.0.0
ENV PORT=8080

# Copy source repository
COPY --chown=cryptoplatform:cryptoplatform . /app

# Create persistent state directories
RUN mkdir -p /app/data/checkpoints /app/data/db /app/data/logs /app/research/results \
    && chown -R cryptoplatform:cryptoplatform /app/data /app/research/results

USER cryptoplatform

# Readiness & Liveness Probes
HEALTHCHECK --interval=20s --timeout=5s --start-period=10s --retries=3 \
    CMD python3 cli.py health || exit 1

EXPOSE 8080

ENTRYPOINT ["python3", "main.py"]
CMD ["--host", "0.0.0.0", "--port", "8080"]
