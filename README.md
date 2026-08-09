   APEX Quantitative Systems Platform

> **An institutional-grade, research-driven quantitative systems engineering platform for deterministic market intelligence, multi-horizon state parsing, risk-first portfolio control, and automated execution infrastructure.**

[![Build Status](https://img.shields.io/badge/build-99%2F99%20passing-brightgreen.svg)](#05--verification--regression-matrix)
[![Architecture](https://img.shields.io/badge/architecture-event--driven%20%7C%20causal%20%7C%20stateful-blue.svg)](#03--system-architecture--domain-separation)
[![Domain Isolation](https://img.shields.io/badge/domain-strict%20unidirectional%20decoupling-orange.svg)](#04--domain-boundary-rules)
[![Domain](https://img.shields.io/badge/domain-cryptocurrency%20markets-purple.svg)](#01--executive-summary)

---

## Technical Metadata

| Parameter | Platform Specification |
| :--- | :--- |
| **System Architecture** | Decoupled Event-Driven Multi-Timeframe State Machine |
| **Platform Name** | APEX Quantitative Systems Platform |
| **Repository Name** | `crypto-platform` |
| **Primary Production Domain** | Cryptocurrency Markets (`BTC/USDT`, `ETH/USDT`, `SOL/USDT`) |
| **Active Product** | **Product 01 — Market Language Engine** |
| **Verification Gate** | **99 / 99 Unit & Integration Tests Passing (100% Deterministic OK)** |
| **Locked Sub-Systems** | Engine 1 (Raw Swings), Engine 2 (Structure), Engine 3 (Liquidity), Engine 4 (KeyZones) |
| **Next Engine Target** | Engine 5 (Market Phase Classifier) |

---

## 01 — Executive Summary

The **APEX Quantitative Systems Platform** is a research and execution infrastructure designed to process financial market data streams into machine-readable market intelligence, statistically validated strategy hypotheses, risk-bounded execution models, and autonomous capital allocation systems.

While cryptocurrency markets serve as the initial liquid deployment domain, the platform architecture is strictly domain-agnostic, built to generalize across equities, foreign exchange, and derivative asset classes.

### The Quantitative Core Imperative
Retail trading scripts frequently fail due to **architectural contamination**—mixing market data parsing, technical indicators, signal generation, risk budgeting, and broker execution into tightly coupled procedural scripts. APEX enforces strict **Domain-Driven Design (DDD)** and **Unidirectional Dependency Trees**.

```text
               RAW OHLCV MARKET DATA STREAMS
                             │
                             ▼
 ┌───────────────────────────────────────────────────────┐
 │          PRODUCT 01: MARKET LANGUAGE ENGINE          │
 │  • Zero-Lookahead Extrema Detection                   │
 │  • Causal Market Structure State Machine              │
 │  • Liquidity Pool & Sweep Tracking                    │
 │  • Order Block & Fair Value Gap Location Mapping      │
 └───────────────────────────┬───────────────────────────┘
                             │
                     MarketStatePayload
                             │
                             ▼
 ┌───────────────────────────────────────────────────────┐
 │          PRODUCT 02: STRATEGY INTELLIGENCE            │
 │  • HTF Context & Directional Bias                     │
 │  • MTF Setup & Alignment Coordination                 │
 │  • LTF Trigger & Microstructure Invalidation          │
 └───────────────────────────┬───────────────────────────┘
                             │
                      Order Proposal
                             │
                             ▼
 ┌───────────────────────────────────────────────────────┐
 │            PRODUCT 03: RISK & CAPITAL GATE            │
 │  • Hard Equity Risk Ceiling (≤ 1.0% per trade)        │
 │  • Asymmetric Reward-to-Risk Floor Verification (≥ 1:4)│
 │  • Max Cumulative Drawdown Circuit Breakers           │
 └───────────────────────────┬───────────────────────────┘
                             │
                     Validated Intent
                             │
                             ▼
 ┌───────────────────────────────────────────────────────┐
 │       PRODUCT 04: EXECUTION & ROUTING ADAPTERS        │
 │  • Pluggable Broker Abstraction (Binance/Bybit/MT5)   │
 │  • Execution Drag & Slippage Accounting               │
 │  • Dynamic Structural Trailing Management             │
 └───────────────────────────────────────────────────────┘

```

---

## 02 — Formal System Invariants

Every engine, calculator, and pipeline within APEX adheres to five immutable engineering laws:

1. **Zero-Lookahead Temporal Isolation:**
Calculations at timestamp $T$ consume strictly historical data $t \le T$. Future candles or unconfirmed swing extrema are physically inaccessible to the evaluation loop.
2. **Deterministic Reproducibility:**
For any dataset $D$, executing state pipeline $P(D)$ produces identical payload outputs $S$:

$$P(D_t)_{\text{Run A}} \equiv P(D_t)_{\text{Run B}}$$


3. **Pure State Isolation:**
Market Intelligence sub-systems describe market state; they do not calculate lot sizing, access account equity, query exchange websocket balances, or construct execution orders.
4. **Causal Event Derivation:**
Events (`BOS`, `CHOCH`, `LIQUIDITY_SWEEP`, `KEYZONE_MITIGATED`) are derived strictly through verified geometric and price action state transitions, never through caller-asserted booleans or arbitrary heuristics.
5. **Fail-Safe Defensive Protection:**
Sitting in an unexposed state (`WAIT` / `NO_TRADE`) is treated as a first-class, high-value decision state that preserves risk capital during adverse volatility or illiquid market regimes.

---

## 03 — System Architecture & Domain Separation

The platform is partitioned into autonomous products. Higher layers consume contracts from lower layers. Lower layers remain oblivious to higher-level decision models.

```text
                         APEX PLATFORM
                               │
        ┌──────────────────────┼──────────────────────┐
        │                      │                      │
        ▼                      ▼                      ▼
   MARKET DATA         MARKET INTELLIGENCE        RESEARCH &
  INFRASTRUCTURE       (PRODUCT 01 ENGINE)       BACKTESTING
        │                      │                      │
        │                      ▼                      │
        │             MarketStatePayload              │
        │                      │                      │
        └──────────────────────┼──────────────────────┘
                               ▼
                     STRATEGY INTELLIGENCE
                          (PRODUCT 02)
                               │
                               ▼
                     RISK & CAPITAL GATES
                          (PRODUCT 03)
                               │
                               ▼
                     EXECUTION INFRASTRUCTURE
                          (PRODUCT 04)
                               │
                               ▼
                    PORTFOLIO TELEMETRY &
                    PERFORMANCE ATTRIBUTION

```

---

## 04 — Product 01: Market Language Engine

### Mission Statement

To convert raw OHLCV market streams into a deterministic, machine-readable market ontology. Product 01 provides the analytical foundation that eliminates visual subjectivity from technical price action analysis.

```text
                               RAW OHLCV
                                   │
                                   ▼
                         ┌───────────────────┐
                         │     ENGINE 1      │
                         │    RAW SWING      │
                         └─────────┬─────────┘
                                   │
                                   ▼
                         ┌───────────────────┐
                         │     ENGINE 2      │
                         │ MARKET STRUCTURE  │
                         └─────────┬─────────┘
                                   │
            ┌──────────────────────┼──────────────────────┐
            ▼                      ▼                      ▼
  ┌───────────────────┐  ┌───────────────────┐  ┌───────────────────┐
  │     ENGINE 3      │  │     ENGINE 4      │  │     ENGINE 6      │
  │    LIQUIDITY      │  │     KEYZONE       │  │      TREND        │
  └─────────┬─────────┘  └─────────┬─────────┘  └─────────┬─────────┘
            │                      │                      │
            └──────────────────────┼──────────────────────┘
                                   ▼
                         ┌───────────────────┐
                         │     ENGINE 5      │
                         │   MARKET PHASE    │
                         └─────────┬─────────┘
                                   │
                                   ▼
                         ┌───────────────────┐
                         │     ENGINE 7      │
                         │    VALIDATION     │
                         └─────────┬─────────┘
                                   │
                                   ▼
                         ┌───────────────────┐
                         │     ENGINE 8      │
                         │   MARKET STATE    │
                         └─────────┬─────────┘
                                   │
                                   ▼
                         ┌───────────────────┐
                         │     ENGINE 9      │
                         │    COORDINATOR    │
                         └─────────┬─────────┘
                                   │
                                   ▼
                           MarketStatePayload

```

---

### Sub-System Specifications & Status

#### Engine 1 — Raw Swing Engine (`raw_swing_engine.py`)

* **Responsibility:** Establishes confirmed structural extrema (Swing Highs and Swing Lows) from raw candlestick streams.
* **Formal Properties:**
* Explicit separation of Extreme Index ($i$) and Confirmation Index ($i + N_{\text{right}}$).
* Strict geometric bounds: Rejects flat-top and flat-bottom candles to eliminate arbitrary pivot assignments.
* Timeframe-preserving chronological execution.


* **Status:** 🔒 **LOCKED** (15 / 15 Unit Tests Passing)

#### Engine 2 — Stateful Market Structure Engine (`structure_builder_engine.py`)

* **Responsibility:** Constructs causal, stateful market structure from confirmed raw swings.
* **Formal Properties:**
* **Sequence Labelling:** `HH`, `HL`, `LH`, `LL`, `EQH`, `EQL`.
* **Scope Classification:** Separates macro External Structural Legs from nested Internal Retracements.
* **Role Linking:** Links Protected Swings directly to the causal origin of new structural expansions (`EXTERNAL_BOS`).
* **State Transitions:** Emits deduplicated events (`EXTERNAL_BOS`, `EXTERNAL_CHOCH`, `INTERNAL_BOS`, `INTERNAL_CHOCH`, `MSS`, `FAILED_BOS`).
* **Active Dealing Range:** Computes dynamic Equilibrium Bounds ($P_{\text{eq}} = P_{\text{low}} + \frac{P_{\text{high}} - P_{\text{low}}}{2}$).


* **Status:** 🔒 **LOCKED** (40 / 40 Unit Tests Passing)

#### Engine 3 — Liquidity Intelligence Engine (`liquidity_engine.py`)

* **Responsibility:** Detects retail liquidity concentrations and tracks multi-candle liquidity pool lifecycles.
* **Formal Properties:**
* **Pool Types:** Equal Highs (`EQH`), Equal Lows (`EQL`), Buy-Side Liquidity (`BSL`), Sell-Side Liquidity (`SSL`).
* **Scope:** Differentiates External Major Liquidity from Internal Minor Liquidity.
* **Candle Geometry Bounds:** Validates wick sweeps where $P_{\text{wick}} > \text{Boundary}$ while $\max(P_{\text{open}}, P_{\text{close}}) \le \text{Boundary}$.
* **Stateful Lifecycle:** Manages state transitions across:

$$\text{ACTIVE} \longrightarrow \text{SWEPT (Wick Rejection)} \longrightarrow \text{CONSUMED (Body Breakout)}$$


* **Inducement Classification:** Maps sweeps of internal liquidity aligned with macro structural trend as inducement.


* **Status:** 🔒 **LOCKED** (14 / 14 Unit Tests Passing)

#### Engine 4 — KeyZone Location Engine (`keyzone_engine.py`)

* **Responsibility:** Maps institutional supply/demand footprints and tracks price imbalance retests.
* **Formal Properties:**
* **Zone Types:** Bullish & Bearish Order Blocks (`OB`), Bullish & Bearish Fair Value Gaps (`FVG`).
* **Causal Alignment:** OB creation index maps to the confirming structural break index (`break_idx`); FVG creation index maps to the third confirming imbalance candle ($i$).
* **Lifecycle State Machine:**

$$\text{UNMITIGATED} \longrightarrow \text{MITIGATED (Price Retest)} \longrightarrow \text{INVALIDATED (Body Close Beyond)}$$


* **Liquidity-Enhanced Scoring:** Dynamically boosts zone probability score when origin candles align with Engine 3 sweep events.


* **Status:** 🔒 **LOCKED** (18 / 18 Unit Tests Passing)

#### Engine 5 — Market Phase Engine (`phase_engine.py`)

* **Responsibility:** Classifies market dynamics into canonical market regimes:

$$\text{ACCUMULATION} \to \text{EXPANSION} \to \text{PULLBACK} \to \text{CONTINUATION} \to \text{DISTRIBUTION} \to \text{REVERSAL} \to \text{COMPRESSION}$$


* **Status:** 🎯 **ACTIVE IMPLEMENTATION TARGET**

#### Engines 6–9 (Planned Foundation Modules)

* **Engine 6 (Trend Engine):** Standardized multi-timeframe trend state contract (`BULLISH`, `BEARISH`, `RANGING`).
* **Engine 7 (Validation Engine):** Quality-control verification gate analyzing displacement velocity, candle body metrics, and ATR ratios.
* **Engine 8 (Market State Engine):** Aggregator compiling Engines 1–7 outputs into a single immutable payload.
* **Engine 9 (Market Language Coordinator):** Interface adapter exposing standardized contracts to Product 02.

---

## 05 — Verification & Regression Matrix

APEX enforces strict **Test-Driven Development (TDD)**. No engine or component is merged or tagged without passing a 100% regression gate.

```text
========================================================================================
                      QUANTITATIVE SYSTEMS PLATFORM — CRYPTO PLATFORM
              Product 01: Market Language Engine | Component Scorecard
========================================================================================

  Engine 1: Raw Swing Engine        ████████████████████ 15/15 PASS  [🔒 LOCKED]
  Engine 2: Causal Structure Engine ████████████████████ 40/40 PASS  [🔒 LOCKED]
  Engine 3: Liquidity Engine        ████████████████████ 14/14 PASS  [🔒 LOCKED]
  Engine 4: KeyZone Engine          ████████████████████ 18/18 PASS  [🔒 LOCKED]
  Engine 5: Market Phase Engine     ░░░░░░░░░░░░░░░░░░░░ 00/00       [🎯 NEXT TARGET]
  Engine 6: Trend Engine            ░░░░░░░░░░░░░░░░░░░░ 00/00       [⏳ PLANNED]
  Engine 7: Validation Engine       ░░░░░░░░░░░░░░░░░░░░ 00/00       [⏳ PLANNED]
  Engine 8: Market State Engine     ░░░░░░░░░░░░░░░░░░░░ 00/00       [⏳ PLANNED]
  Engine 9: Language Coordinator    ░░░░░░░░░░░░░░░░░░░░ 00/00       [⏳ PLANNED]

----------------------------------------------------------------------------------------
  TOTAL REPOSITORY REGRESSION SUITE: 99 / 99 TESTS PASSING (100% OK)
========================================================================================

```

### Full Test Suite Execution Command

```bash
python3 -m unittest discover -s tests -p "test*.py" -v

```

```text
Ran 99 tests in 0.034s

OK

```

---

## 06 — Quantitative Research & Validation Lifecycle

APEX maintains a strict separation between **Software Verification** and **Financial Alpha Validation**.

```text
  SOFTWARE VERIFICATION          RESEARCH & REPLAY              PRODUCTION STAGING
 ┌──────────────────────┐      ┌──────────────────────┐      ┌──────────────────────┐
 │ • Unit Test Suite    │      │ • Historical Replay  │      │ • Paper Sandbox      │
 │ • Integration Suite  │ ───► │ • Out-of-Sample Test │ ───► │ • Friction Drag Audit│ ───► PRODUCTION
 │ • Causal Replay Gate │      │ • Walk-Forward Sweep │      │ • Micro-Capital Live │
 │ • Determinism Gate   │      │ • Monte Carlo Permut │      │ • Slippage Modeling  │
 └──────────────────────┘      └──────────────────────┘      └──────────────────────┘

```

1. **Software Verification:** Asserts that code behaves according to formal specification contracts (e.g., 99/99 unit tests).
2. **Historical Replay & Out-of-Sample (OOS):** Replays multi-year native datasets ($5\text{--}10\text{ years}$) with strict exchange friction injection:
* Taker Fee Drag: $0.075\%$
* Simulated Order Slippage: $0.02\%\text{--}0.05\%$
* Spread Widening during macro volatility events.


3. **Walk-Forward Matrix Analysis:** Validates strategy parameter stability across non-overlapping historical regimes to prevent over-fitting.
4. **Micro-Capital Production Staging:** Validates live exchange WebSocket latency, order fill latency, and real-world execution drag before scaling leverage.

---

## 07 — Strategy Architecture Target (Product 02)

When Product 01 reaches complete lockdown, Product 02 will consume `MarketStatePayload` objects to execute two primary multi-timeframe strategy models across parameterised Timeframe Horizons:

```text
               PULLBACK RIDING                         CONTINUATION RIDING
        (HTF BOS -> Retracement Phase)           (HTF KeyZone Retest Complete)
                      │                                        │
                      ▼                                        ▼
         MTF Counter-Trend Retracement            MTF Re-alignment with HTF Bias
                      │                                        │
                      ▼                                        ▼
          MTF Structural Alignment                 MTF KeyZone Setup Formed
                      │                                        │
                      └───────────────────┬────────────────────┘
                                          │
                                          ▼
                             LTF Execution Trigger
                       (Liquidity Sweep + Displacement)
                                          │
                                          ▼
                             Risk Firewall Gate
                     (Risk <= 1.0%, Reward-to-Risk >= 1:4)

```

### Timeframe Horizon Configurations

* **Set 1 (Macro / Position):** $1\text{M} \to 1\text{W} \to 1\text{D}$
* **Set 2 (Position / Swing):** $1\text{W} \to 1\text{D} \to 4\text{H}$
* **Set 3 (Swing / Intraday):** $1\text{D} \to 4\text{H} \to 1\text{H}$
* **Set 4 (Intraday Scaling):** $4\text{H} \to 1\text{H} \to 15\text{M}$

---

## 08 — Repository Structure

```text
crypto-platform/
│
├── config/                      # System parameters, timeframes & asset configs
├── market_intelligence/         # Product 01: Market Language Engine
│   ├── primitives.py            # Immutable domain primitives & dataclasses
│   ├── raw_swing_engine.py      # Engine 1: Zero-lookahead swing extrema
│   ├── structure_builder_engine.py # Engine 2: Stateful market structure builder
│   ├── liquidity_engine.py      # Engine 3: Liquidity pool & sweep engine
│   └── keyzone_engine.py        # Engine 4: Order Block & FVG location engine
│
├── strategy/                    # Product 02: HTF / MTF / LTF Strategy Orchestration
├── risk/                        # Product 03: Account equity gates & RR floor calculators
├── execution/                   # Product 04: Pluggable exchange/broker adapters
├── backtesting/                 # Historical replay, friction simulation & walk-forward
├── data/                        # Native candlestick database storage (.sqlite3)
├── logs/                        # System runtime audit logs
└── tests/                       # Complete regression test suite
    └── unit/                    # Unit tests for core market engines

```

---

## 09 — Git Version Control & Checkpoint History

The codebase progresses through immutable semantic checkpoint tags:

* `product-01-v0-baseline`: Initial repository chassis and data pipeline.
* `product-01-engine-1-green`: Locked Raw Swing Engine (15/15 tests).
* `product-01-engine-2-green`: Locked Market Structure Builder (40/40 tests).
* `product-01-engine-3-hardened-green`: Locked Liquidity Intelligence Engine (14/14 tests).
* `product-01-engine-4-green`: **Locked KeyZone Location Engine (18/18 tests, commit `ef2e184`).**

---

## 10 — Disclaimers & Maturity Model

1. **Development Maturity:** APEX is currently at **Level 2 (Unit & Repository Software Verification)** within its 7-stage engineering maturity lifecycle.
2. **No Alpha Guarantee:** Unit test passes certify software correctness against explicit contracts. They do not constitute a guarantee of future financial returns or trading alpha.
3. **Research First:** Live trading execution and capital allocation are strictly locked until out-of-sample forward research gates are satisfied.

---

> **APEX QUANTITATIVE SYSTEMS PLATFORM** > *Observe the market. Translate the market. Validate the hypothesis. Protect the capital. Automate only what has earned the right to be automated.*

