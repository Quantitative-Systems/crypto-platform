# Crypto Platform — Cloud Hosting Evaluation & Architecture Decision

## 1. Executive Summary & Core Decision

| Layer / Responsibility | Selected Architecture | Selected Provider | Plan / Tier | Monthly Cost | Rationale |
| :--- | :--- | :--- | :--- | :---: | :--- |
| **Web Frontend Workstation** | Static HTML5/JS Web Terminal | **Vercel** | Hobby (Free) | **$0.00** | Global Edge CDN distribution, instant cold-starts, zero asset latency. |
| **Backend API Gateway** | Python 3.12 Docker Container | **Render** | Free Web Service | **$0.00** | Automated git deploy (`render.yaml`), HTTPS termination, health probes. |
| **Persistent Quantitative Worker** | Asyncio Supervisor Loop | **Render** (Staging) / **VPS** (Prod) | Free (Staging) | **$0.00** | Co-located in API container for staging; dedicated persistent process. |
| **Durable Storage / DB** | SQLite WAL on Mountable Disk | **Local / Persistent Disk** | Free Tier | **$0.00** | Zero external DB cost; low latency read/write for single-node platform. |
| **CI/CD & Android Builds** | Automated GitHub Actions | **GitHub** | Free Tier | **$0.00** | 2,000 monthly Ubuntu runner minutes; builds APKs autonomously. |
| **Total Immediate Spend** | | | | **$0.00** | Strict zero-capital policy maintained. |

---

## 2. In-Depth Provider Evaluation & Technical Constraints

### 1. Vercel (Hobby Tier)
- **Strengths:** Excellent edge network, zero config for static assets, seamless Git integration, custom domains with free TLS.
- **Critical Limitations:**
  - Serverless function timeout: **10 seconds** (Hobby) / 60 seconds (Pro).
  - WebSockets: Serverless functions **cannot maintain persistent WebSockets** or background streaming loops.
  - Ephemeral Memory: Functions terminate between requests; zero in-memory state retention.
- **Architectural Decision:** **Vercel is strictly restricted to static frontend hosting and reverse-proxy rewrite rules (`vercel.json`). Under NO circumstances is the quantitative engine run inside Vercel Serverless Functions.**

### 2. Render (Free Web Service)
- **Strengths:** Native Docker container runtime, automated build on Git push, free SSL, native WebSocket support, custom environment variables.
- **Critical Free-Tier Limitations (Verified from Render Documentation):**
  - **Inactivity Sleep:** Spins down after **15 minutes of inactivity**.
  - **Cold-Start Latency:** Initial request after sleep takes **30–50 seconds** to boot the container.
  - **Compute Limits:** 512 MB RAM, 0.1 shared CPU. (Our backend consumes ~145 MB RAM).
  - **Free Usage Cap:** 750 free instance hours per calendar month across all free services.
  - **Persistent Disks:** Render Free tier **does NOT support persistent disk mounts**; container filesystem resets on redeployment.
- **Architectural Decision:** **Suitable for on-demand Staging verification, manual review, and Android API integration testing. NOT suitable for uninterrupted 24/7/365 production forward testing on the free tier alone.**

### 3. Alternative Free/Low-Cost Providers Analyzed
- **Google Cloud Run:**
  - *Free Tier:* 2 million requests/month, 360,000 GB-seconds memory.
  - *Limitation:* Request-driven; instances scale to 0 when idle unless `min-instances: 1` is configured (which incurs costs beyond free credits).
- **Railway:**
  - *Free Tier:* $5.00 trial credit (one-time), then requires paid usage. Not a permanent free tier.
- **Fly.io:**
  - *Free Allowance:* Replaced by pay-as-you-go with credit card required.

---

## 3. Four-Tier Operational Roadmap

```
+-------------------------------------------------------------------------+
| LOCAL DEV        STAGING (FREE)         FORWARD-TESTING     PRODUCTION  |
| 127.0.0.1:8080   Render (Free Web)      Render Starter      Dedicated   |
| Dev Laptop       Sleeps after 15m       No sleep ($7/mo)    VPS ($4/mo) |
| Simulated Paper  Binance Testnet WSS    24/7 Persistent     Hard Locked |
| Capital: $0.00   Capital: $0.00         Capital: $0.00      Cap: $0.00  |
+-------------------------------------------------------------------------+
```

1. **Local Development (Current):** Developer laptop running `main.py` directly or via Docker for rapid development.
2. **Staging (Current Target):** Render Free Web Service + Vercel Edge. Zero cost. Verified for API contract compatibility and Android connectivity. Accepts cold-start wakeup delay.
3. **Continuous Forward Testing (Future Low-Cost Option):** Upgrading Render to the **Starter Plan ($7.00/month)** or deploying on a dedicated **Hetzner Cloud VPS ($4.50/month)** when 24/7 uninterrupted candle history is required without cold-start interruptions.
4. **Production:** Reserved for future live execution (strictly disabled today; capital = $0.00).

> [!CAUTION]
> In compliance with user instructions, no paid upgrades have been or will be purchased autonomously. The staging platform operates entirely within the verified free tier.
