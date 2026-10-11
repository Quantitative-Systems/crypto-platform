# Crypto Platform — Cloud Cost & Limits Analysis

## 1. Zero-Cost Infrastructure Architecture

To comply with the operating rule requiring **zero unexpected costs and zero unauthorized purchases**, the staging environment is deployed exclusively on verified free-tier infrastructure.

### Cost Summary Table

| Provider | Service Role | Tier / Plan | Monthly Cost | Authorized Resource Limits |
| :--- | :--- | :--- | :--- | :--- |
| **Render** | Backend Container & Worker | Free Tier | **$0.00** | 512 MB RAM, 0.1 CPU, 750 free instance hrs/mo |
| **Vercel** | Web Terminal & Reverse Proxy | Hobby Tier | **$0.00** | 100 GB bandwidth, unlimited SSL, edge routing |
| **GitHub Actions** | CI/CD & Android APK Builds | Standard Free | **$0.00** | 2,000 free runner minutes/mo (Ubuntu) |
| **Binance** | Testnet Market Data Streams | Public Testnet | **$0.00** | Public WebSocket streams (no account fees) |
| **Total Staging Spend** | | | **$0.00 / mo** | Real Capital at Risk: **$0.00** |

---

## 2. Provider Quotas, Throttles & Technical Limits

### Render (Free Web Service)
- **Memory Limit:** 512 MB RAM (strictly monitored; our lightweight Python aiohttp engine runs at ~145 MB).
- **CPU:** Shared vCPU.
- **Inactivity Sleep:** Free tier web services spin down after 15 minutes of inactivity.
  - *Wakeup Time:* Initial HTTP request takes 30–50 seconds to cold-start.
  - *Mitigation:* GitHub Actions staging probe ping loop (`staging-deploy.yml`) handles cold-start gracefully.
  - *Keep-Alive:* A lightweight 10-minute cron ping or persistent mobile WebSocket maintains continuous uptime.

### Vercel (Hobby Tier)
- **Bandwidth:** 100 GB / month (our static web terminal assets consume <150 KB per visit).
- **Execution Limits:** Serverless function timeouts are 10 seconds.
  - *Architectural Decision:* **No trading logic runs in Vercel serverless functions**. Vercel only serves static assets and performs reverse-proxy routing to Render.

### GitHub Actions
- **Storage for Artifacts:** 500 MB free (Android APKs are ~17 MB each; configured with 14-day retention).
- **Concurrency:** Up to 20 concurrent jobs on Ubuntu runners.
- **Execution Time:** Full CI pipeline (Python tests + regression + Android test + assemble) completes in ~3 minutes 30 seconds.

---

## 3. Production & Scaling Low-Cost Roadmap

If transitioning from Staging to 24/7/365 production forward-testing without cold-starts:

| Tier | Provider | Specification | Estimated Cost | Rationale |
| :--- | :--- | :--- | :--- | :--- |
| **Staging (Current)** | Render + Vercel + GitHub | Free Tiers | **$0.00** | Staging validation, paper testing, CI builds |
| **Continuous Forward** | Render Starter | 512 MB, Always-On Persistent | **$7.00 / mo** | Eliminates cold start; 24/7 uninterrupted WebSocket feed |
| **Dedicated VPS** | Hetzner Cloud / DigitalOcean | 2 GB RAM, 2 vCPU, NVMe | **$4.50 / mo** | Full persistent volume, isolated SQLite, zero throttles |

> [!NOTE]
> Moving to a paid tier requires explicit human authorization. The current deployment remains 100% within the free tier.
