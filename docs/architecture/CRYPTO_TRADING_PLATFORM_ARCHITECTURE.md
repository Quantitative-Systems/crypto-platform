# Crypto Trading Platform — Complete Architecture & Build Plan

**Document type:** North-star architecture and implementation blueprint
**Product:** Multi-tenant automated crypto trading platform (web app + backend + optional mobile client)
**Status:** Approved target architecture. Build proceeds through vertical slices defined in Section 25.

---

## 0. How to Read This Document

- Sections 1–4 define the **product**: what it is, what it honestly is not, and what the customer experiences.
- Sections 5–14 define the **trading machine**: connectivity, data, strategies, research, portfolio, risk, execution, reconciliation.
- Sections 15–24 define the **operating shell**: operations, security, backup/recovery, AI, billing, compliance, testing.
- Sections 25–29 define the **build plan**: phases, fallbacks, repository model, success criteria.

Every section is binding unless explicitly marked *future*. Nothing in this document
is a promise of profitability. See Section 2 first.

---

## 1. Product Definition

### 1.1 What the Product Is

A multi-tenant SaaS platform where customers:

1. Create an account (web first, mobile later).
2. **Connect their own crypto broker/exchange accounts** — any supported venue, not one.
3. Deposit funds into **their own** broker account (the platform does not custody trading funds in the baseline model).
4. Choose an operating mode: **Demo (Paper)** or **Live**.
5. Select from platform-provided strategies that have passed the platform's own research gates.
6. Configure risk within platform-enforced safety bounds.
7. Enable automation — the platform generates signals, passes them through an independent risk engine, and executes orders in the customer's connected account **24/7/365**.
8. Monitor everything, and pause/stop/emergency-stop at any time.

Core value proposition: *institutional-grade systematic trading infrastructure, previously available only to funds, delivered as a consumer product while the customer keeps custody of their own funds.*

### 1.2 What the Product Is NOT (Permanent Honesty Rules)

The platform **cannot and must not** be marketed as:

- A guaranteed-profit or "money printing" machine.
- A system that never loses money or never has drawdowns.
- Immune to exchange outages, market gaps, or software defects.

**What it can honestly promise:** systematic, continuously monitored, risk-controlled,
auditable automated trading infrastructure where catastrophic loss is made *difficult,
detected early, bounded, and capable of automatic shutdown*.

Two rules follow and are frozen:

- **No profitability guarantee is ever made to users, in any copy, UI, or marketing.**
- **No strategy is offered to customers until it passes the platform's own research promotion gates (Section 8.4).** A strategy that has not survived the internal laboratory is never sold.

### 1.3 Operating Modes

| Mode | Funds | Execution | Market Data | Purpose |
|---|---|---|---|---|
| **Demo / Paper** | Virtual (or venue sandbox where available) | Simulated fills with fees/spread/slippage modelling | Live | Customer evaluates strategies with zero risk |
| **Shadow** | None | Signals recorded, no orders | Live | Observe live behavior before activation |
| **Live** | Customer's own funds in customer's own account | Real orders via venue adapter | Live | Automated trading |

These modes must be **technically separated** (different execution backends, different credentials, different state stores), not merely labeled differently in the UI.

Demo mode is a first-class product surface, not a demo of the demo:

- Provider-native sandbox is used **when the venue offers one** (e.g., Binance Spot/Futures Testnet, Bybit Demo).
- Otherwise the platform's own paper execution simulator is used against live market data, modelling fees, spread, slippage, latency, partial fills, and funding.
- The UI must never represent a simulated fill as a real broker fill.

### 1.4 North-Star Customer Journey

```
DISCOVER → CREATE ACCOUNT → CONNECT BROKER/EXCHANGE → DEMO/PAPER
        → SELECT STRATEGY → SET RISK → OBSERVE → LIVE ACTIVATION (explicit)
        → AUTOMATED 24/7 TRADING → MONITOR → ADAPT / PAUSE / STOP
```

The customer experience should be simple. The complexity lives underneath: data,
strategies, portfolio, risk, execution, reconciliation, monitoring, recovery,
security, backups, audit, tenancy isolation.

---

## 2. Non-Negotiable Reality Checks (Read Before Building Anything)

### 2.1 The Edge Problem

The platform is the **vehicle**. It is not the **engine**. A flawless architecture
executing unproven strategies produces flawless losses at scale.

Frozen rule: **commercial Live mode opens only when at least one strategy has
completed the full promotion chain** (Section 8.4: development → validation →
out-of-sample → robustness → shadow → canary). Until then, the product ships
Demo/Paper mode — which is itself a complete, sellable product (Section 21.5).

This converts the biggest current risk — *selling automated trading before
possessing validated edge* — into a build-order constraint.

### 2.2 The Regulatory Problem

Automatically trading **other people's money** is a regulated activity in most
jurisdictions (portfolio/investment management, securities and derivatives rules,
consumer protection, AML/KYC). Section 21 is a first-class workstream, not an
afterthought. The architecture is deliberately shaped to keep the *least-regulated
viable* footprint (non-custodial, user-selected, user-configured strategies)
while remaining extensible to regulated managed models later.

### 2.3 "Never Blow the Account" Is a Design Principle, Not a Promise

Implemented as layered, independent, fail-closed controls (Section 10). Losses are
bounded by design; zero-loss is not a claim the platform ever makes.

### 2.4 Venue Terms-of-Service Constraints

- Many exchanges permit API trading; some **brokers prohibit third-party automation**. The adapter layer records and enforces per-venue automation permissions.
- API keys must be scoped to minimum permissions: read + trade. **Withdrawal permissions are never requested** where the venue supports scoping.
- Rate limits, WebSocket lifetimes, ping/pong requirements, and user-data stream semantics differ per venue and are adapter responsibilities (Section 5.6).

---

## 3. High-Level System Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                        CUSTOMER LAYER                            │
│   Web App | (Mobile later) | Notifications | Reports | Billing   │
└───────────────────────────────┬──────────────────────────────────┘
                                ↓
┌──────────────────────────────────────────────────────────────────┐
│                 IDENTITY & ACCOUNT CONTROL                       │
│   Auth | MFA | Sessions | Roles | Permissions | Tenant Isolation │
└───────────────────────────────┬──────────────────────────────────┘
                                ↓
┌──────────────────────────────────────────────────────────────────┐
│              CUSTOMER TRADING ACCOUNTS                           │
│   Connected Broker/Exchange Accounts | Demo | Paper | Live       │
└───────────────────────────────┬──────────────────────────────────┘
                                ↓
┌──────────────────────────────────────────────────────────────────┐
│                    PLATFORM CONTROL PLANE                        │
│   Strategy Registry | Policies | Config | Lifecycle | Flags      │
└───────────────────────────────┬──────────────────────────────────┘
                                ↓
┌────────────────────────────┐  ┌──────────────────────────────────┐
│        DATA PLANE          │  │      RESEARCH PLANE (isolated)   │
│ Market | Book | Trades |   │  │ Hypotheses | Backtests | Evidence│
│ Funding | OI | On-chain    │  │ NO live credentials. EVER.       │
└─────────────┬──────────────┘  └──────────────────────────────────┘
              ↓
┌──────────────────────────────────────────────────────────────────┐
│                  STRATEGY ENGINE (many families)                 │
└───────────────────────────────┬──────────────────────────────────┘
                                ↓  (Order Intents only — never orders)
┌──────────────────────────────────────────────────────────────────┐
│              PORTFOLIO / ALLOCATION ENGINE                       │
└───────────────────────────────┬──────────────────────────────────┘
                                ↓
┌──────────────────────────────────────────────────────────────────┐
│                RISK FIREWALL (fail-closed)                       │
│  Account | Strategy | Portfolio | Venue | System | Kill Switch   │
└───────────────────────────────┬──────────────────────────────────┘
                                ↓
┌──────────────────────────────────────────────────────────────────┐
│             OMS / EXECUTION LAYER                                │
│   Order Intent | Routing | Orders | Fills | Reconciliation       │
└───────────────────────────────┬──────────────────────────────────┘
                                ↓
┌──────────────────────────────────────────────────────────────────┐
│                VENUE ADAPTER LAYER                               │
│   Exchange A | B | C | D | ... (CCXT or native per Section 5.5)  │
└───────────────────────────────┬──────────────────────────────────┘
                                ↓
                   Customer's own broker/exchange accounts

Around everything: SECURITY · AUDIT · BACKUP · RECOVERY · OBSERVABILITY · GOVERNANCE
```

The single most important structural rule:

> **A strategy generates Order Intents. It never holds venue credentials, never
> calls a venue API, and cannot move capital except through the risk firewall.**

---

## 4. Customer Application Layer

### 4.1 Application Architecture

```
Browser/Mobile → CDN/WAF → API Gateway → Application Services → Domain Services → Trading Core
```

- Web frontend: modern SPA (React/Next.js). The browser never holds or processes exchange secrets.
- API Gateway: authentication, rate limiting, tenant isolation, request validation, audit logging.
- Backend: start as a **modular monolith** with hard logical module boundaries; split into services only when scale, isolation, or team size demands it (Section 22).

### 4.2 Identity, Tenancy, Roles

- Every customer is a **tenant**. `tenant_id` is enforced server-side in every query, cache key, event, log, and object-storage path. Never trust client-supplied tenant scope.
- Auth: email + password (or passwordless), **MFA mandatory before Live mode**, session management, device history, recovery, suspicious-login detection.
- Roles: Owner, Admin, Viewer, Support, Internal Admin — with explicit permission matrices.

### 4.3 Dashboard Requirements

The customer must always be able to answer, at a glance:

- Is this DEMO or LIVE? (permanent, unmissable visual state)
- Which venue/account is connected, and its health?
- Which strategies are active, with what allocation?
- Current positions, orders, PnL, drawdown, risk state?
- Why did the system stop (if it stopped)?
- How do I stop it right now? (one-tap emergency stop, always reachable)

### 4.4 Customer Controls

Start / Pause / Stop / Reduce allocation / Disable strategy / Disconnect account / Emergency stop. Customer STOP behavior is explicit:

1. Stop new order intents.
2. Handle pending orders per stated policy (cancel).
3. Reconcile.
4. Mark automation stopped.
5. Whether open positions are flattened is a **separate, explicit, user-facing choice** — never an ambiguous default.

### 4.5 User-Safe Defaults

- Trading disabled after account connection.
- No strategy auto-activated.
- No leverage by default.
- Conservative initial limits.
- Explicit live confirmation flow (Section 14.2).
- Alerts enabled by default.

---

## 5. Broker & Exchange Connectivity

### 5.1 Adapter Architecture

The platform is never written around one exchange. Every venue implements one
canonical adapter interface:

```
connect/authenticate · get_account() · get_balances() · get_positions()
get_open_orders() · get_instruments() · subscribe_market_data()
subscribe_user_data() · submit_order() · cancel_order() · replace_order()
get_order() · get_fills() · get_funding() · reconcile() · health_check()
```

Adding a venue = implementing an adapter. Nothing upstream changes.

### 5.2 Venue Data Model

```
TradingAccount
 ├── provider_id · account_id · account_type
 ├── environment: DEMO | PAPER | LIVE
 ├── permissions (scoped, verified at connect time)
 ├── supported_assets · supported_products (SPOT / MARGIN / PERPS / FUTURES)
 ├── automation_allowed (venue ToS flag — hard gate)
 ├── connection_status · sync_status · health_status
```

### 5.3 Connection Methods & Permission Scoping

- API key/secret (most exchanges), OAuth/delegated authorization where offered, read-only connections for visibility-only mode.
- **Minimum permissions only**: read account + trade. Withdrawal permissions are never requested. The connect flow verifies the key's actual scopes and refuses trading-enabled connections that exceed policy.
- Credentials flow: Browser → secure upload flow → backend secret manager (encrypted, rotation-capable, audited). Secrets never touch Git, logs, or the browser after submission.

### 5.4 Initial Venue Support Matrix

| Venue | Spot | Perps/Futures | Native Testnet/Demo | Notes |
|---|---|---|---|---|
| Binance | ✔ | ✔ | ✔ (Spot + Futures Testnet) | Highest liquidity; deep API docs; 24h WS lifetime handling required |
| Bybit | ✔ | ✔ | ✔ (Demo trading) | Strong perps |
| OKX | ✔ | ✔ | ✔ (Demo trading) | |
| Kraken | ✔ | ✔ | ✔ (Demo environments) | |
| Coinbase (Advanced) | ✔ | ✔ | ✔ (Sandbox) | REST/WS split; monitor platform migration notices |
| KuCoin | ✔ | ✔ | ✔ (Simulation) | |
| Bitget | ✔ | ✔ | ✔ (Demo) | |
| Others | via generic CCXT adapter rollout | | | Gated by demand + liquidity |

Broker-type venues (e.g., traditional fintech brokers offering crypto) are added
only after their automation ToS is verified (Section 2.4).

### 5.5 CCXT vs Native Adapters (Decision)

- **Rule:** use [CCXT](https://github.com/ccxt/ccxt) as the default implementation substrate for exchange adapters (100+ venues, unified schema, active maintenance).
- **Native adapter** only when a venue requires behavior CCXT cannot express (special auth, order types, user-data semantics) — native adapter wraps/implements the same interface.
- **Fallback:** if a venue has no CCXT support at all, implement a minimal native adapter (REST + WS) before considering dropping the venue. Venue coverage never drives core redesign.

### 5.6 Connectivity Engineering Requirements

- REST + WebSocket per venue; WS reconnection with exponential backoff, heartbeat/ping handling, sequence-gap detection, and full **resync/reconcile after reconnect** before any new order submission.
- Rate-limit budgets per venue, per key, per endpoint class; token-bucket enforcement in the adapter layer.
- Idempotent client order IDs (deterministic, tenant-scoped) to prevent duplicate submissions on retry.
- Per-venue health circuit breaker: repeated auth failures → auto-disable trading for that connection + customer alert.


---

## 6. Data Plane

### 6.1 Data Classes

| Class | Examples |
|---|---|
| Market | candles (OHLCV), trades, tickers, quotes, order book depth, spreads, volume |
| Derivatives | funding rates, open interest, liquidations, mark/index price, basis, futures curves |
| On-chain | transactions, exchange flows, stablecoin flows, active addresses, supply changes, token unlocks |
| Fundamental | protocol revenue, fees, TVL, token economics, governance events |
| Information | news, announcements, exchange maintenance notices, macro events, sentiment |

The data layer separates: **acquisition → normalization → validation → storage →
distribution → feature generation**.

### 6.2 Canonical Event Model

No strategy or engine component ever consumes venue-specific JSON directly.
All providers normalize into internal events:

```
MarketEvent · TradeEvent · QuoteEvent · OrderBookEvent · CandleEvent
FundingEvent · OpenInterestEvent · LiquidationEvent · NewsEvent · OnChainEvent
AccountEvent · OrderEvent · FillEvent · PositionEvent · RiskEvent · SystemEvent
```

Why: venues change their APIs constantly (REST/WS reorganizations, migrations,
sandbox changes). Normalization isolates that churn inside adapters.

### 6.3 Data Quality Gates

Every dataset carries: source, provider, instrument, event timestamp, ingestion
timestamp, schema version, completeness, duplicate status, gap report, outlier
report, quality status. Data states:

```
UNKNOWN → INGESTED → CHECKED → VALID → RESEARCH_ELIGIBLE
```

Contaminated or gapped data is quarantined, never silently patched. (The existing
`market_data/` quality pipeline in this repository is the seed of this subsystem.)

### 6.4 Dynamic Asset Universe

No hard-coded asset count. The universe is computed at runtime:

```
All discovered instruments
   → data quality → liquidity → spread → product availability
   → fees → execution quality → risk eligibility → strategy compatibility
   → ELIGIBLE UNIVERSE
```

Instruments are rejected for: insufficient history, bad data, low liquidity,
excessive spread, abnormal volatility, execution infeasibility, or policy
restrictions. The platform is **asset-agnostic; deployments are universe-bounded
by evidence, liquidity, infrastructure, and risk constraints**. Customers may
further restrict (exclude assets, venues, products) within platform bounds.

### 6.5 Storage Architecture

| Store | Technology (initial) | Purpose | Scale-up path |
|---|---|---|---|
| Relational | PostgreSQL | tenants, users, accounts, strategies, config, billing, permissions, orders, fills | managed Postgres, read replicas |
| Time-series | PostgreSQL + TimescaleDB | candles, metrics, features, performance | ClickHouse for heavy analytics |
| Cache / hot state | Redis | live quotes, rate-limit tokens, session data, leader locks | Redis Cluster |
| Object storage | S3-compatible | raw data archives, datasets, experiment artifacts, reports, backups | — |
| Streams | Redis Streams initially | event bus (Section 18) | Kafka/NATS at scale |

Research jobs must never compete with live-trading I/O for these resources
(Section 15.5).

---

## 7. Strategy Architecture

### 7.1 Strategy Families (Plugin Catalog)

| Family | Contents |
|---|---|
| Trend / Momentum | MA systems, breakouts, channel systems, time-series momentum, multi-timeframe momentum |
| Mean Reversion | z-score, band-based, statistical reversal, cross-sectional reversal |
| Structural / Price Action | breakouts, structural retests, displacement, FVG/liquidity mechanisms |
| Statistical Arbitrage | pairs, cointegration, spread trading, relative value |
| Cross-Venue Arbitrage | price dislocations, triangular relationships (latency-sensitive; late phase) |
| Funding / Basis | funding capture, spot-perp basis, cash-and-carry |
| Market Making | spread capture, inventory-aware quoting (separate microstructure stack; late phase) |
| Order Flow / Microstructure | book imbalance, aggressive flow, absorption (late phase) |
| Volatility | realized vol, regime models, options strategies where supported |
| Fundamental / On-Chain | network activity, flows, supply/unlock events, protocol metrics |
| Event / News | event reaction, announcement impact, sentiment shocks |
| Machine Learning | classification, regression, ranking, regime models, meta-labeling, ensembles |

No family is presumed profitable. The research engine (Section 8) decides.

### 7.2 Trading Styles Are Configurations, Not Platforms

Scalping, intraday, swing, position, and investing are **metadata and configuration
of the same strategy contract** — differing in data requirements, holding period,
latency tolerance, and cost sensitivity. One platform hosts all styles; the
compatibility matrix (Section 7.4) gates which strategies can run where.

### 7.3 Universal Strategy Contract

Every strategy declares:

```
strategy_id · version · family · style
supported_assets · supported_venues · required_data
time_horizon · entry_logic · exit_logic · position_model · risk_model
execution_model · expected_holding_period · capacity
regime_profile · known_failure_modes
research_lineage · validation_status · live_status
```

The engine needs no special-casing per style: it hosts contracts.

### 7.4 Signal → Order Intent

A strategy outputs **Order Intents** — never venue calls:

```
strategy_id · strategy_version · instrument · direction · target_exposure
urgency · execution_constraints · signal_timestamp · signal_reason
```

An Order Intent flows: Strategy → Portfolio Engine → Risk Engine → Approved
(resized/rejected) → Execution. Nothing else.


---

## 8. Research Laboratory (Internal, Isolated From Live)

The research plane is the platform's truth machine. It operates on **development
and validation data partitions only** and holds **no live trading credentials**.

### 8.1 Research Lifecycle

```
IDEA → HYPOTHESIS → FORMAL SPEC → CANDIDATE → DEVELOPMENT TEST
     → FORENSIC REVIEW → VALIDATION → OUT-OF-SAMPLE → STRESS/ROBUSTNESS
     → SHADOW → PAPER → CANARY → QUALIFIED LIVE → MONITOR
     → RE-QUALIFY / RETIRE
```

No stage implies the next. No shortcut exists. A candidate can be retired at any stage.

### 8.2 Backtest Fidelity Levels

| Level | Simulation includes |
|---|---|
| 1 — Research | OHLCV, deterministic replay |
| 2 — Execution-aware | + fees, spread, slippage, latency, funding |
| 3 — Event-driven | + intrabar sequencing, order lifecycle, partial fills, collision semantics |
| 4 — Microstructure | + order book, depth, queue assumptions, impact |
| 5 — Replay | + full recorded venue event replay |

Minimum fidelity for any commercial claim: **Level 3**. The existing deterministic
replay engine and forensic funnel audits in this repository are Level 1–3 seeds.

### 8.3 Forensic Engine (Automatic)

Every experiment is automatically screened for: lookahead, leakage, timestamp
errors, duplicate events, phantom re-entry, incorrect collision semantics, cache
truncation, invalid fills, missing fees/slippage, data snooping, overfitting,
weak sample size, regime dependence, and result concentration. Positive results
that fail forensics are recorded as negative evidence — never deleted.

### 8.4 Promotion Gates (Strategy → Customer-Visible)

```
RESEARCH → VALIDATED → OOS (never tuned on) → ROBUSTNESS/STRESS
        → SHADOW (live conditions, no capital) → PAPER → CANARY (tiny live allocation)
        → QUALIFIED LIVE
```

Qualification metrics (all required, none sufficient alone): net expectancy after
full friction, profit factor, drawdown, OOS stability, regime robustness, capacity,
correlation to existing live strategies, execution feasibility.

### 8.5 Mapping to the Existing Repository

| Existing asset | Becomes |
|---|---|
| `qcp_platform/` deterministic sweep + governance gates | Research harness behind Section 8.1 lifecycle |
| `market_data/` cache + quality pipeline | Data plane quality gates (6.3) |
| Hypothesis/candidate/evidence registry | Research governance layer (8.1–8.4) |
| `research/failed/` archive | Evidence library including negative evidence |
| Forensic funnel audits | Forensic engine (8.3) |

The research engine does not move; the platform grows around it.

---

## 9. Portfolio & Capital Allocation

Ten independently profitable-looking strategies may be one crowded crypto-beta
factor. The portfolio engine therefore models, per tenant:

- strategy correlation, asset/factor exposure, net & gross exposure, leverage
- volatility contribution, liquidity, capacity, concentration, tail exposure

Allocation methods (configurable, independently testable): fixed risk budget,
volatility targeting, equal risk contribution, correlation-aware, drawdown-aware,
regime-aware, signal-confidence weighted.

Portfolio constraints: max total leverage, max asset/strategy/venue/correlated
concentration, liquidity constraints, **capital reserve** (margin buffer, fee
buffer, volatility shock, emergency reduction — never 100% allocated).

Portfolio safety takes priority over individual strategy signals.

---

## 10. Risk Engine (The Firewall)

### 10.1 Structure

Independent service. Fail-closed. No strategy, tenant action, or billing event can
bypass, weaken, or disable it.

```
Order Intent → Portfolio Engine → RISK ENGINE → approved / resized / rejected → Execution
```

### 10.2 Six Risk Levels

| Level | Checks |
|---|---|
| 1 — Order | size, price sanity vs market, duplicate ID, stale signal, stale data, notional/leverage/margin limits |
| 2 — Strategy | max position, max loss, max concurrent trades, turnover, strategy drawdown, kill switch |
| 3 — Portfolio | gross/net exposure, asset & correlation concentration, leverage, liquidation buffer |
| 4 — Account | daily/weekly loss, total drawdown, margin utilization, available equity |
| 5 — Venue | API health, data health, latency anomalies, order-status mismatch, outage |
| 6 — System | corrupted state, DB failure, clock failure, duplicated processes, runaway loops, bad deploy |

### 10.3 Fail-Closed Policy

If the platform cannot establish that a trade is safe — stale data, unknown order
state, missing account info, risk engine unavailable, position mismatch, clock
failure, DB inconsistency — **no new order**. Refusal is a valid output.

### 10.4 Kill Switches

Scoped: Global · Customer · Trading account · Venue · Strategy · Instrument ·
Portfolio · Execution (block submits, keep monitoring) · Emergency. Every switch
activation is auditable and reversible only through explicit, logged action.

### 10.5 Catastrophic Loss Protection (Layered)

```
Position limits → Leverage limits → Margin buffer → Stop/exit policies
→ Portfolio risk → Account drawdown → Systemic drawdown → Circuit breaker
→ Emergency state (cancel all + predefined position handling) → SAFE MODE
```

Derivatives accounts additionally monitor maintenance margin, liquidation distance,
and funding drag; approach of policy thresholds triggers deterministic
Reduce → Restrict → Halt sequences.


---

## 11. OMS & Execution

### 11.1 Order State Machine (owned by OMS)

```
CREATED → RISK_CHECKED → SUBMITTED → ACKNOWLEDGED → PARTIALLY_FILLED → FILLED
                       ↘ REJECTED · CANCELLED · EXPIRED · FAILED · UNKNOWN
```

**UNKNOWN ≠ FAILED.** Unknown state mandates reconciliation before any new order
for that account (Section 12).

### 11.2 Execution Engine Responsibilities

Routing, submission, cancellation, replacement, partial-fill handling, retry
policy with idempotency, execution-quality metrics (slippage vs arrival,
fill rate, latency), and per-venue constraint handling — all hidden from strategies.

Strategies request *exposure* ("long BTC"); the portfolio/risk/execution stack
decides *how* that is actually achieved.

### 11.3 Smart Routing (later phase)

Where supported: price, liquidity, spread, fees, expected slippage, latency, venue
health, balances. Never routes to a venue the risk layer has disabled.

---

## 12. Reconciliation Engine (Non-Negotiable for Live)

Continuously compares **expected platform state vs actual venue state**:
balances, positions, open orders, fills, fees, margin, PnL.

Mandatory reconciliation after: restart, reconnect, network outage, process crash,
venue maintenance, any UNKNOWN order state, any mismatch detected.

```
Mismatch found → halt new orders (account scope) → classify → repair or SAFE MODE → audit
```

---

## 13. Multi-Tenant Execution Architecture

This is the part single-bot designs ignore and this product cannot.

### 13.1 Signal Fan-Out

One strategy × N tenants = N order intents for the same instruments. Handling:

- **Per-tenant sizing**: intents are sized per tenant's allocation and risk policy; minimum order sizes per venue apply.
- **Minimum account guidance**: venues impose minimum notional/lot sizes; the product defines a minimum viable allocation per strategy (documented per strategy, enforced at activation).
- **Rate-limit stewardship**: per-venue budgets are shared; tenant orders are scheduled through a fair, per-venue execution queue. When limits bind, lower-urgency orders wait — staleness checks then cancel expired intents rather than executing stale signals.
- **Herding monitor**: aggregate platform exposure per instrument is tracked; if fan-out creates outsized aggregate footprint, the universe/strategy caps adapt (protects customers and execution quality).
- **Partial-fill fairness**: fills are attributed per tenant order; partial fills do not reorder the queue unfairly.

### 13.2 Isolation Boundaries

- Shared: market data, feature computation, strategy logic, research infrastructure.
- Per-tenant: credentials, balances, positions, orders, configuration, strategy instance state, risk state.
- A fault in one tenant's execution loop must never block another tenant's safety path.

---

## 14. Account & Deployment State Machines

### 14.1 Connection Lifecycle

```
DISCONNECTED → CONNECTED → SYNCING → HEALTHY → READY → ARMED → TRADING
TRADING → PAUSED → SAFE (user stop or degradation)
TRADING → RISK HALT → CANCEL NEW ORDERS → RECONCILE → SAFE MODE
EMERGENCY → CANCEL OPEN ORDERS → EMERGENCY POSITION HANDLING → RECONCILE → SAFE MODE
```

### 14.2 Live Activation Checklist (all mandatory, all automated)

venue supported · connection healthy · key permissions verified (no withdrawal scope) ·
account synced · instruments compatible · market data healthy · risk policy loaded ·
risk engine healthy · execution engine healthy · reconciliation clean ·
strategy qualified for live · **explicit customer confirmation with mode-acknowledgment UI**.

Failure of any check blocks activation. Live state cannot be reached accidentally.

### 14.3 Disconnection Behavior

Customer disconnects (or revokes keys at the venue): stop new order authority →
cancel/handle pending orders per policy → reconcile → mark inactive → notify.
The platform never silently keeps trading after access is revoked.


---

## 15. 24/7 Operations & Reliability

### 15.1 Health Domains

Market data · Strategy runtime · Portfolio · Risk · Execution · Venue connections ·
Database · Event bus · Storage · Hosts · **Clock**. Each reports
`HEALTHY / DEGRADED / FAILED` with heartbeats; missing heartbeats are failures.

### 15.2 Process Supervision

Detect → Restart → Restore state from durable store → **Reconcile** → Resume only
if safe. The system never blindly resumes order submission after restart.

### 15.3 Time Synchronization

Host, application, and venue timestamps are continuously compared. Severe clock
drift disables time-sensitive trading until corrected.

### 15.4 Alerting Levels

| Level | Examples |
|---|---|
| INFO | trade executed, strategy started |
| WARNING | data delay, elevated slippage, drawdown approaching limit |
| CRITICAL | venue mismatch, repeated order rejection, risk degradation |
| EMERGENCY | unexplained position mismatch, uncontrolled order generation, systemic corruption |

### 15.5 Resource Isolation

Live execution ≠ research compute. Live risk ≠ experimental AI. Research/training
jobs run on separate resources/queues so a heavy backtest can never starve live
safety paths.

### 15.6 Incident Management

Detect → Classify → **Contain (protect capital first)** → Reconcile → Investigate →
Communicate (customer comms templates prepared in advance) → Resolve → Postmortem
→ New automated test/governance rule. Every serious incident makes the platform
permanently harder to break.

---

## 16. Security Architecture

### 16.1 Boundary Map

```
Internet → CDN/WAF → API Gateway → AuthN/AuthZ → Application Services
        → Trading Control Plane → Risk Firewall → Execution → Venue Adapters → Venues
```

Research network is separated from live trading network where practical.
Research services hold no live credentials — enforced by infrastructure, not policy documents.

### 16.2 Secrets

Exchange API keys: encrypted at rest in a dedicated secret store (e.g., cloud KMS /
Vault), rotation supported, access audited, decryptable only by the scoped execution
service. Never in Git, logs, config files, or browser storage. A breach-response
playbook with customer key-rotation instructions is pre-written.

### 16.3 Application Security

MFA (mandatory for Live), session security, per-endpoint authorization, request
validation, idempotency, replay protection on sensitive flows, abuse detection,
rate limiting. Customer API keys are never returned to any client after storage
(write-only from the user's perspective). Full audit log of every financially
material action, immutable, tenant-scoped.

---

## 17. Backup & Disaster Recovery

### 17.1 What Is Backed Up (by failure class)

| Asset | Mechanism | Cadence |
|---|---|---|
| Source code | Git + independent mirror (second remote) | every push |
| Configuration & policies | versioned in Git; encrypted where sensitive | every change |
| Research (manifests, results, evidence) | Git + object storage archive | every experiment |
| Raw market data | immutable archive + independent copy | continuous |
| Operational DB | snapshots + point-in-time recovery (WAL) | continuous + daily |
| Trading state (orders, fills, positions, strategy/risk state) | durable event log + snapshots | continuous |

### 17.2 Recovery Levels

- **Hot:** standby ready (post-scale).
- **Warm:** infrastructure ready with recent state restored.
- **Cold:** full rebuild from Code + Config + DB backup + Event log + State snapshot.

Target property: **the platform is rebuildable from durable evidence and depends
on no single machine or provider.**

### 17.3 Restore Drills

Backups are proven by scheduled restore drills (documented RTO/RPO per component).
An untested backup is treated as no backup.


---

## 18. Event Bus & Event Sourcing

All financially material actions are events on a versioned bus:

```
MARKET_DATA_RECEIVED · SIGNAL_GENERATED · ORDER_INTENT_CREATED
RISK_APPROVED · RISK_REJECTED · ORDER_SUBMITTED · ORDER_ACKNOWLEDGED
FILL_RECEIVED · POSITION_CHANGED · RISK_STATE_CHANGED
STRATEGY_PAUSED · STRATEGY_QUARANTINED · SYSTEM_DEGRADED · SYSTEM_RECOVERED
```

Consumers (strategy engine, features, risk, portfolio, monitoring, audit,
research recorder) subscribe; idempotent where required. The durable event log
enables: replay, debugging, audit, recovery, incident reconstruction, and
deterministic research on live behavior.

---

## 19. AI Layer (Governed)

AI agents multiply research and operations capability; they do not hold capital
authority in this architecture.

| Agent | Role |
|---|---|
| Opportunity Scout | propose research ideas |
| Data Scientist | find relationships/anomalies |
| Researcher | formulate falsifiable hypotheses |
| Coding Agent | implement candidate experiments |
| Forensic Agent | hunt leakage, defects, regime dependence |
| Risk Analyst | detect concentration, drift, anomalies |
| Portfolio Analyst | compare allocation approaches |
| Ops Agent | diagnose failures |
| Research Librarian | maintain experiment lineage and evidence |

Control model (frozen):

```
AI PROPOSES → SYSTEM FORMALIZES → TEST → FORENSIC → RISK → GOVERNANCE → DEPLOY
```

Not: AI decides → AI trades. ML strategies additionally require time-ordered
splits, walk-forward evaluation, feature/model versioning, drift monitoring, and
calibration checks — accuracy alone never qualifies anything.

---

## 20. Billing & SaaS Model

- Tiers: free demo → subscription tiers → advanced analytics/professional plans; usage-based options later. Performance-linked pricing only where legally appropriate (it interacts with Section 21).
- For non-custodial performance-fee models, fees are computed from reconciled live PnL per tenant per strategy, settled by invoice/charge — **never** by the platform moving customer funds.
- **Billing is isolated from trading safety:** an expired subscription stops *new* strategy activations; existing positions are handled per explicit policy — never abruptly abandoned because of a billing event.
- Product analytics (signups, connections, retention, uptime) are tracked separately from trading performance and never used to obscure trading results.


---

## 21. Compliance & Legal Workstream (First-Class)

### 21.1 Why This Is Structural

Automatically trading customer funds at connected venues can constitute
portfolio/investment management or dealing in financial instruments depending on
jurisdiction, product, and discretion level. The architecture must therefore make
the compliance surface **configurable**, not accidental.

### 21.2 Regulatory Design Levers (Least-Regulated-Viable Posture)

| Lever | Effect |
|---|---|
| **Non-custodial** (funds stay at customer's venue) | Avoids money-transmission/custody licensing in most regimes |
| **User selects strategies & sets risk explicitly** | Discretion stays with the user (tool-provision posture) — legal analysis required per jurisdiction |
| **No personalized investment advice** | Avoids investment-adviser triggers |
| **Honest performance presentation** | Consumer-protection compliance |
| **KYC/AML via providers** | Required on Live in most jurisdictions |

### 21.3 Workstream Items (before public Live launch)

Legal opinion per launch jurisdiction on the operating model · entity & licensing
decisions (e.g., EU MiCA/CASP implications, US analysis, UAE VARA, Singapore MAS —
jurisdictions chosen with counsel, not by convenience) · KYC/AML provider
integration · Terms of Service, Risk Disclosures (drawdowns, fees, no guarantees),
Privacy Policy, data-retention compliance · marketing/claims review process ·
per-venue contractual review (third-party API trading permission) · geo-restriction
capability in the API (not just the frontend).

### 21.4 Geo/Jurisdiction Strategy

The API supports per-jurisdiction feature gating from day one: Paper-only
jurisdictions, Live jurisdictions, restricted jurisdictions — driven by config,
audited.

### 21.5 Commercial Sequencing Consequence

Demo/Paper mode has a far lighter regulatory surface than Live and is fully
valuable as a product (research-grade simulation, education, strategy evaluation).
**Ship Paper first; open Live only after Section 8.4 (validated strategy) and
Section 21.3 (legal clearance) both complete.** This is the correct order, not
the cautious order.

---

## 22. Technology Stack & Decision Matrix

| Concern | Initial choice | Rationale | Fallback if it fails |
|---|---|---|---|
| Backend language | Python (matches existing engine) | reuse `qcp_platform`, `market_data` | Rust/C++ for hot paths only (adapters keep interface) |
| API framework | FastAPI | async, typed, OpenAPI | — |
| Web frontend | Next.js/React SPA | ecosystem, SSR marketing pages | — |
| Databases | PostgreSQL + TimescaleDB | transactions + time-series in one ops surface | ClickHouse for heavy analytics |
| Cache/queues | Redis (+ Redis Streams) | simple, fast, singleton locks | NATS → Kafka at scale |
| Exchange connectivity | CCXT (+ native where needed) | 100+ venues, unified schema | native REST/WS adapters |
| Deployment | Docker Compose → single cloud VPS (early) → Kubernetes (scale) | cost discipline early | managed K8s / multi-region |
| Secrets | Cloud KMS or Vault | audited, rotating | — |
| Monitoring | Prometheus + Grafana + Alertmanager; logs → Loki | standard, cheap | SaaS APM if budget allows |
| CI/CD | GitHub Actions | repo-native | — |

Modular monolith first; extract services (risk, execution, market data) only when
isolation or scale genuinely demands it.


---

## 23. Contingency Matrix ("If this fails → then this")

| If… | Then… |
|---|---|
| No strategy passes research gates by the launch target | Ship Demo/Paper product; continue research; Live stays gated. Never lower gates to hit a date. |
| A venue has no sandbox/demo | Use the platform paper simulator against its live market data |
| CCXT can't express a venue behavior | Write a native adapter implementing the same interface |
| A venue ToS forbids third-party automation | Venue stays unsupported for Live; Paper-only at most |
| PostgreSQL strains under time-series load | Move analytics tables to ClickHouse; keep OLTP in Postgres |
| Redis Streams saturate | Move event bus to NATS, then Kafka — event schema unchanged |
| Single server can't sustain live load | Split: market-data, execution, risk services on separate hosts; then Kubernetes |
| Python latency insufficient for a strategy family | Rewrite only that strategy's hot path (Rust/Cython) behind the same contract; never loosen risk checks for speed |
| Live execution diverges from backtest expectations | Freeze new capital to that strategy; re-forecast costs (slippage/latency); re-run the promotion chain with measured execution data |
| Regulatory blocker in a target market | Geo-gate to Paper mode there; revisit with counsel |
| Payment/billing provider fails | Trading safety unaffected; new activations pause; comms template used |
| Research compute too slow | Rent burst compute for research only; live plane untouched |
| Exchange API outage | Circuit breaker → stop new orders for that venue → reconcile on recovery → resume under policy |
| Platform state corrupted | Rebuild from event log + snapshots (17.1); reconcile all accounts before returning to TRADING |
| Key/secret compromise suspected | Force-disable affected connections, notify customers with rotation playbook, rotate platform secrets, postmortem |
| A qualified strategy degrades live | Strategy health ladder (Section 24.3): WATCH → RESTRICTED → QUARANTINED → RETIRED; capital follows automatically |


---

## 24. Testing, Safety Invariants & Health Ladders

### 24.1 Test Pyramid

| Layer | What it proves |
|---|---|
| Unit | domain logic (sizing, risk math, indicators) |
| Contract | adapter & strategy interfaces against fakes + venue sandboxes |
| Integration | data → strategy → portfolio → risk → execution paths |
| Replay | deterministic historical behavior, byte-stable results |
| Property | safety invariants hold under generated inputs |
| Fault injection | connection loss, DB failure, duplicate process, stale data, unknown order state, venue outage |
| End-to-end | Demo/Paper customer loop; live-simulation loop |

### 24.2 Permanent Safety Invariants (enforced by tests, forever)

1. A strategy cannot bypass the risk engine.
2. A rejected order can never execute.
3. A stale signal cannot execute.
4. Unknown order state requires reconciliation before new orders.
5. A disabled/quarantined strategy cannot submit order intents or receive capital.
6. A disabled venue cannot receive orders.
7. A failed risk engine authorizes nothing.
8. Duplicate order submission is impossible (idempotent IDs).
9. Research services cannot access live trading credentials.
10. A tenant cannot access another tenant's data.
11. Paper fills cannot mutate live account state.
12. Demo mode cannot send real orders.
13. Live mode requires explicit activation (checklist 14.2).
14. Disconnecting an account immediately ends its order authority.
15. No subsystem may silently change strategy permissions, risk limits, or live status.

### 24.3 Strategy & Portfolio Health Ladders

Strategy: `HEALTHY → WATCH → RESTRICTED → QUARANTINED → RETIRED`
Portfolio: `HEALTHY → DEGRADED → RISK_REDUCED → HALTED → SAFE_MODE`

Inputs: performance drift, drawdown, regime mismatch, execution degradation,
feature drift, data quality, correlation shift, operational errors. Capital
transitions follow the ladder automatically; requalification requires research,
not hope.

---

## 25. Build Phases (Vertical Slices)

Each phase ends with a *working, tested slice* — never a half-built layer.

| Phase | Deliverable | Key contents |
|---|---|---|
| **1 — Core foundation** | Skeleton that compiles, tests, deploys | identity, tenancy, account model, canonical events, strategy & order-intent & risk contracts, audit, core persistence |
| **2 — Research vertical slice** | One strategy measured honestly end-to-end | market data → candidate → backtest → forensics → risk simulation → evidence (reuses existing repo assets) |
| **3 — Demo/Paper product** | First sellable product | virtual accounts, simulated execution (fees/spread/slippage), customer dashboard, strategy controls, alerts |
| **4 — First live connector** | One venue, fully safe | adapter, account sync, OMS, reconciliation, live risk checks, monitoring, emergency controls |
| **5 — Multi-strategy** | Catalog grows via contracts | several genuinely different families promoted through Section 8.4 |
| **6 — Portfolio system** | Capital allocation engine | allocation, correlation, capacity, portfolio risk |
| **7 — Multi-venue** | More adapters | additional exchanges per demand matrix (5.4) |
| **8 — Advanced data** | Richer inputs | order book, funding, OI, liquidations, on-chain, news |
| **9 — AI research layer** | Governed agents | Section 19 roles, still zero capital authority |
| **10 — Advanced execution** | Competitive execution | smart routing, microstructure, market making, arbitrage families |
| **11 — Scale** | Production hardening | HA, multi-region, DR drills, larger customer base |

Gates between phases: full test suite green · restore drill passed (from Phase 4)
· no open EMERGENCY-class incidents · compliance checklist current.


---

## 26. What NOT to Build First

Explicitly deferred until the corresponding phase (avoiding architecture-as-procrastination):

- Every strategy family and every exchange
- Options infrastructure, market-making infrastructure, HFT latency engineering
- Autonomous AI trading (AI never holds capital authority in any phase)
- Mobile app, enterprise billing, global multi-region deployment
- Customer-uploaded strategy code (if ever built: strict WASM/container sandbox, no tenant/secrets/network access — a separately designed product)

The first complete slice that proves the machine:

```
User → Connect Demo/Paper → Market Data → One Qualified Strategy → Signal
     → Order Intent → Risk Check → Simulated Order → Fill → Position → PnL
     → Monitoring → Audit
```

Then the same interfaces, reused for a real-money path:

```
User → Connect Live Venue → Permission Verify → Sync → Strategy → Intent
     → Portfolio → Risk → Execution → Venue → Fill → Reconciliation
     → Position → PnL → Monitoring
```

---

## 27. Target Repository Model

```
platform/
├── apps/web/                    # Next.js frontend
├── services/                    # extracted when justified (start: modular monolith)
│   ├── identity/  accounts/  billing/  market_data/
│   ├── research/  strategies/  portfolio/  risk/
│   ├── oms/  execution/  reconciliation/
│   └── notifications/  audit/
├── core/
│   ├── domain/  contracts/  events/  state/
├── adapters/
│   ├── venues/  data_sources/  notifications/
├── research/
│   ├── hypotheses/  experiments/  datasets/  evidence/
├── strategies/                  # one package per family (Section 7.1)
├── infrastructure/
│   ├── deployment/  observability/  recovery/  backups/  security/
└── tests/  docs/
```

This is a **target** logical model. The existing research repository is not thrown
away — it becomes the `research/` and engine seed. No big-bang refactor; structure
converges as phases demand.

---

## 28. Success Criteria for the Complete Platform

The platform is mature when it can reliably:

1. Onboard customers and enforce tenant isolation.
2. Connect supported broker/exchange accounts with verified scoped permissions.
3. Support Demo/Paper/Live as technically separated modes.
4. Ingest and validate market data into canonical events.
5. Run multiple strategy families through one contract.
6. Enforce an independent, fail-closed risk firewall over every order.
7. Execute through multiple venues with idempotent, reconciled order flows.
8. Operate 24/7 with heartbeats, alerting, supervision, and safe recovery.
9. Preserve immutable audit evidence and pass restore drills.
10. Add strategies as plugins, venues as adapters, assets as configuration — without core rewrites.
11. Promote strategies only through the research gates (8.4).
12. Present performance honestly: backtest vs paper vs live, with costs and drawdowns.

---

## 29. Frozen Architecture Decisions

1. Multi-tenant SaaS; web-first; optional mobile later.
2. Demo/Paper/Live are distinct technical modes, not UI labels.
3. Customer funds remain in customer-controlled venue accounts (non-custodial baseline).
4. Strategy never bypasses risk; never talks to a venue; outputs Order Intents only.
5. Risk engine is independent and fails closed. Refusal is a valid output.
6. Venue-specific logic lives only in adapters.
7. Research and live execution are isolated (credentials, networks, resources).
8. Fail-closed + reconcile-unknown-state are permanent rules.
9. Negative research evidence is retained forever; development results never equal qualification.
10. No fixed business maximum on assets or strategy families — bounded only by evidence, liquidity, resources, and risk policy.
11. New strategies = plugins; new venues = adapters; new assets = universe configuration.
12. Live mode requires the full activation checklist and explicit customer confirmation.
13. Every capital-bearing action is audited; production deployment is reversible.
14. No profitability guarantee is ever made to users.
15. No customer-facing Live strategy exists until it passes Section 8.4 gates.

---

## 30. Glossary

| Term | Meaning |
|---|---|
| Order Intent | A strategy's request for exposure; the only thing a strategy may emit |
| Qualified Live | A strategy that completed the full promotion chain (8.4) |
| Paper / Demo | Simulated execution on live data / venue sandbox or simulator, zero real funds |
| Shadow | Signals recorded against live conditions with no orders |
| Canary | Tiny live allocation proving execution reality before scaled capital |
| Fail-closed | On any safety ambiguity: no new orders |
| Reconciliation | Comparing platform-expected vs venue-actual state; mandatory after any anomaly |
| Safe Mode | State where monitoring continues but new order authority is suspended |
| Fan-out | One strategy signal multiplied across N tenant accounts |
| Capacity | The capital size at which a strategy's edge survives its own market impact |

---

## Final Statement

The target product is not a single bot. It is a **multi-tenant automated
quantitative trading platform**: customer application + broker/exchange
connectivity + Demo/Paper/Live execution + dynamic multi-asset universe +
multi-strategy engine + research laboratory + portfolio construction + independent
risk firewall + OMS/execution + venue adapters + 24/7 monitoring + reconciliation +
security + backups + disaster recovery + governed AI + audit — built in vertical
slices, with the research laboratory (already standing in this repository) as the
truth machine that decides what the platform is ever allowed to offer.

The platform continuously answers four questions:

1. Where is there a measurable, honestly-measured opportunity?
2. Does it survive realistic costs, risk, and out-of-sample data?
3. Can it be combined safely with existing strategies?
4. Can it be executed and monitored reliably with customer-authorized capital?

*End of document.*
