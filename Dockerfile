# Multi-stage production Dockerfile for Crypto Platform
# Enforces non-root execution, minimal attack surface, and health check probes

FROM python:3.12-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt pyproject.toml ./
RUN pip install --no-cache-dir --user -r requirements.txt

FROM python:3.12-slim AS runner

WORKDIR /app

# Create unprivileged application user
RUN groupadd -r platform && useradd -r -g platform -u 1000 -m platform

# Copy installed python wheels from builder
COPY --from=builder /root/.local /home/platform/.local
ENV PATH=/home/platform/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app

# Copy application source code
COPY --chown=platform:platform . /app

# Ensure directories for persistence exist with proper permissions
RUN mkdir -p /app/research/results /app/market_data/cache \
    && chown -R platform:platform /app/research /app/market_data

USER platform

# Platform health check probe
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python3 -m crypto_platform.cli health || exit 1

ENTRYPOINT ["python3", "-m", "crypto_platform.cli"]
CMD ["status"]
