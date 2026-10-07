# Public Repository Security & Open-Source Boundary Policy

**Platform:** Crypto Quantitative Trading Platform  
**Document Version:** 1.0.0  
**Status:** Canonical Security & Architecture Governance  
**Date:** 2026-09-25  
**Repository State:** Public Open-Source Baseline (`v0.4.0`)  

---

## 1. Executive Summary

This repository is maintained as a **public open-source quantitative trading engineering framework**. This document defines the formal boundaries governing what is permitted in this public repository versus what must remain strictly private or isolated within external secret management systems.

> [!CAUTION]
> ### FUNDAMENTAL SECURITY RULE: VISIBILITY IS NOT SECURITY
> **GitHub repository visibility (Public vs. Private) must NEVER be treated as a security boundary.**
> Even in a private repository, credentials, private API keys, and sensitive financial secrets must **NEVER** be committed to Git. Code repositories store history immutably; any credential committed to version control must be treated as permanently compromised. Secrets belong exclusively in operating system environment variables, encrypted vault files (outside Git), or managed key-vault services (e.g. AWS Secrets Manager, HashiCorp Vault, GCP Secret Manager).

---

## 2. Public vs. Private Architectural Classification Matrix

| Category | Boundary Classification | Architectural & Risk Rationale | Current Repository Status |
|---|---|---|---|
| **Core Source Code** | `PUBLIC CORE` | Execution engines, order lifecycle, risk firewall, portfolio state, reconciliation, domain models. Provides the transparent engineering foundation. | **PUBLIC** (Tracked in Git, 0 secrets) |
| **Strategy Engines (Reference)** | `PUBLIC CORE` | Reference implementations of Trend Breakout, Mean Reversion, Systematic DCA, Volatility Expansion. Standard quantitative benchmarks. | **PUBLIC** (Tracked in `crypto_platform/strategy/`) |
| **Proprietary Alpha & Signals** | `PRIVATE PROPRIETARY` | Advanced proprietary alpha signals, trained ML weight tensors, custom feature transformations, parameter sets with commercial edge. | **EXCLUDED** (None present in public repository) |
| **Research Artifacts** | `PUBLIC CORE / AUDIT` | Historical validation reports, bias checklists, walk-forward OOS summaries, stress test logs. Proves methodology integrity. | **PUBLIC** (Tracked in `research/results/` & `docs/`) |
| **Historical Failed Research** | `OPTIONAL PUBLIC` | Archive of failed hypotheses and legacy exploration runs (`research/failed/`). Transparent evidence of research honesty. | **PUBLIC** (Tracked in `research/failed/`) |
| **Market Data Datasets** | `PUBLIC CORE (BENCHMARK ONLY)` | Minimal 9-file OHLCV benchmark fixture files in `market_data/cache/` (~500KB–15MB). Essential for deterministic unit test execution. | **PUBLIC** (9 benchmark files tracked; 400MB+ bulk cache ignored) |
| **Bulk Historical Datasets** | `PRIVATE / EXTERNAL` | Multi-gigabyte tick, orderbook depth, and trade-by-trade archives. High storage footprint and exchange redistribution licensing restrictions. | **GITIGNORED** (`market_data/cache/*.json`, `data/`, `datasets/`) |
| **Environment Files (`.env`)** | `STRICTLY PRIVATE` | Local environment variable configurations containing actual operational variables. | **GITIGNORED** (`.env`, `.env.*`; only `.env.example` template tracked) |
| **Configuration Templates** | `PUBLIC CORE` | Sanitized templates (`.env.example`, `pyproject.toml`, `docker-compose.yml`) containing empty dummy placeholders only. | **PUBLIC** (Tracked, verified zero live values) |
| **Broker API Credentials** | `STRICTLY PRIVATE` | Production/Testnet API keys, API secrets, subaccount IDs, passphrases, IP whitelist tokens. | **EXCLUDED** (Verified 0 credentials in worktree and Git history) |
| **Private Keys & Certificates** | `STRICTLY PRIVATE` | SSH keys, TLS certificates, P12/PFX bundles, GPG keys, Fernet/AES vault keys. | **GITIGNORED** (`*.pem`, `*.key`, `*.crt`, `*.p12`, `*.pfx`, `id_rsa*`) |
| **Process Logs** | `STRICTLY PRIVATE` | Runtime standard output, error dumps, audit trails, and execution logs that may record runtime parameters. | **GITIGNORED** (`*.log`, `logs/`, `nohup.out`) |
| **State & Trade Databases** | `STRICTLY PRIVATE` | SQLite databases (`*.db`, `*.sqlite3`) recording active accounts, orders, positions, and equity histories. | **GITIGNORED** (`*.db`, `*.db-*`, `**/*.db*`, `*.sqlite3`) |
| **Container & Daemon Configs** | `PUBLIC CORE` | Generic `Dockerfile`, `docker-compose.yml`, and `crypto-platform.service` systemd unit files using environment variable injection. | **PUBLIC** (Tracked, no hardcoded secrets) |
| **REST & WebSocket API** | `PUBLIC CORE` | Web API routers, telemetry endpoints, emergency kill switch, and WebSocket streaming handlers. | **PUBLIC** (Tracked in `crypto_platform/api/`) |
| **Web Dashboard** | `PUBLIC CORE` | Vanilla JavaScript/CSS single-page institutional operations interface. | **PUBLIC** (Tracked in `crypto_platform/web/`) |
| **Test Suite** | `PUBLIC CORE` | Unit, integration, and safety contract test suites (212 tests). Ensures code correctness for public contributors. | **PUBLIC** (Tracked in `tests/`) |
| **PAPER Trading Plane** | `PUBLIC CORE` | Synthetic execution simulator and public live WebSocket forward paper trading harness. | **PUBLIC** (Tracked, uses only public feeds) |
| **DEMO / MOCK Plane** | `PUBLIC CORE` | Deterministic mock adapter and pre-flight state reconciliation harness for simulated brokers. | **PUBLIC** (Tracked, uses dummy credentials) |
| **LIVE-CANARY Safety Layer** | `PUBLIC CORE` | 14-step broker pre-flight auditor, capital ceiling enforcement, and non-custodial permission verification engine. | **PUBLIC** (Tracked; state defaults to `DISARMED`) |
| **LIVE Trading Plane** | `HARD-LOCKED` | Real-money production trading plane. | **PUBLIC CODE / HARD-LOCKED** (Capital = $0.00, permanently locked in code) |
| **Cloud Deployment Manifests** | `PRIVATE OPERATIONAL` | Terraform state files, cloud provider IAM role ARNs, private VPC configs, production DNS records. | **EXCLUDED** (Cloud deployment has not been performed) |

---

## 3. The Recommended Two-Repository Model

For future phases transitioning into real-money production and proprietary trading, the platform architecture recommends a strict **Two-Repository Boundary**:

```
                              THE QUANTITATIVE TRADING BUSINESS
                                              │
                     ┌────────────────────────┴────────────────────────┐
                     │                                                 │
          OPEN-SOURCE CORE REPOSITORY                     PRIVATE OPERATIONS REPOSITORY
         "crypto-platform" (Public)                    "crypto-platform-private" (Private)
                     │                                                 │
      ├─ Canonical Data Architecture                    ├─ Proprietary Alpha Signals & Features
      ├─ Historical Replay & Backtest Engine            ├─ Calibrated ML Weights & Hyperparameters
      ├─ Risk Firewall & Circuit Breakers               ├─ Production Deployment Manifests (Terraform)
      ├─ Execution & Order State Machine                ├─ Real Broker Credential Vault
      ├─ Binance, Bybit & CCXT Adapters                 ├─ Live Capital Allocation & Sizing Models
      ├─ REST & WebSocket Streaming API                 ├─ Production Monitoring & Alerting Webhooks
      ├─ Web Operations Dashboard                       ├─ Proprietary High-Frequency Routing
      ├─ PAPER & DEMO Trading Engines                   └─ Private Trading Audit History & Tax P&L
      └─ LIVE-CANARY 14-Step Safety Engine
```

### Advantages of this Separation:
1. **Open-Source Showcase:** Demonstrates institutional-grade software engineering, rigorous quantitative methodologies, safety architectures, and clean testing without revealing commercial alpha.
2. **Zero Blast Radius:** Public contributors, automated bots, and web indexers can never access live trading credentials, private production infrastructure, or proprietary strategy edges.
3. **Clean Upstream Flow:** Infrastructure enhancements, adapter bug fixes, and data quality improvements made in the open-source repo can be merged downstream into the private repository via Git remotes or private submodules.

---

## 4. Worktree & Git History Audit Findings

A complete, exhaustive forensic audit of both the current working tree and all 211 historical commits was executed:

| Audit Parameter | Verification Command | Result | Findings / Actions |
|---|---|---|---|
| **Worktree Secret Scan** | `git grep -i -E "(api_key|api_secret|private_key|...)"` | **CLEAN** | Only dummy placeholders (`demo_binance_testnet_key`, `<your_production_api_key>`) found in docs/tests. |
| **Private Key Scan** | `git grep -i "BEGIN.*PRIVATE KEY"` | **CLEAN** | Zero PEM/SSH/RSA/EC private keys detected. |
| **Cloud Token Patterns** | Regex search for `AKIA*`, `ghp_*`, `AIza*`, `xox*` | **CLEAN** | Zero AWS, GitHub, Google Cloud, or Slack tokens found. |
| **Git History Secrets** | `git log --all -G"..."` across 211 commits | **CLEAN** | Only commit `6597f29` matched, introducing testnet dummy mock strings. No history rewrite needed. |
| **Active/Historical DBs** | `git ls-files | grep '\.db$'` | **CLEAN** | Zero SQLite databases tracked in Git. Local `.db` files are strictly gitignored. |
| **Runtime Logs** | `git ls-files | grep '\.log$'` | **CLEAN** | Zero runtime log files tracked in Git. All logs are strictly gitignored. |
| **Live Account Data** | Database query across all local SQLite tables | **CLEAN** | Exactly 0 real account balances, 0 real positions, and 0 real orders found. |

---

## 5. Security & Contribution Rules for Maintainers

1. **Never Commit Secrets:** Any developer or agent submitting code must ensure no `.env` files, API keys, or private tokens are staged.
2. **Pre-Commit Verification:** Run `git diff --staged` and search for credential patterns before running `git commit`.
3. **Mandatory Non-Custodial Enforcement:** Any API keys connected to DEMO or LIVE-CANARY must have withdrawal permissions explicitly disabled at the exchange. The platform's 14-step pre-flight will reject keys with withdrawal permissions.
4. **Permanent LIVE Lock:** The production trading lock (`LIVE_CAPITAL_USD=0.00` and `LIVE` rejection) must remain permanently intact in the public repository.
