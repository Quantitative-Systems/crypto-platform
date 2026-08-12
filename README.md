# Crypto Quantitative Systems Platform

> **A research-first quantitative trading systems platform for deterministic cryptocurrency market intelligence, multi-timeframe strategy research, risk-controlled capital allocation, and automated execution.**

**Repository:** `crypto-platform`  
**Domain:** Cryptocurrency Markets  
**Initial Assets:** BTC/USDT · ETH/USDT · SOL/USDT  
**Architecture:** Event-driven · causal · stateful · modular  
**Primary Objective:** Research, validate, risk-control, and eventually automate systematic cryptocurrency trading strategies.

---

## 01 — Platform Overview

The Crypto Quantitative Systems Platform is a modular research and execution infrastructure for systematic cryptocurrency trading.

The platform converts raw OHLCV market data into deterministic market-state information, evaluates explicit multi-timeframe trading hypotheses, constructs structural trade plans, applies independent capital-risk controls, and provides the foundation for historical research, execution simulation, and eventual automated deployment.

The current implementation is purpose-built for cryptocurrency markets. Its internal contracts and domain boundaries are designed for extensibility, but no non-crypto market support is claimed at this stage.

It does **not** claim profitability, predictive certainty, or production readiness.

Its purpose is to establish a rigorous engineering and research environment in which those claims can be tested rather than assumed.

---

## 02 — Core Trading Architecture

The primary strategy architecture is:

```text
                CRYPTO MARKET DATA
                       │
                       ▼
              MARKET INTELLIGENCE
                       │
                       ▼
                  HTF BIAS
                       │
                       ▼
                  MTF SETUP
                       │
                       ▼
                  MTF RETEST
                       │
                       ▼
                  LTF ENTRY
                       │
                       ▼
               LTF INVALIDATION
                       │
                       ▼
                  HTF TARGET
                       │
                       ▼
              MTF STRUCTURAL TRAIL
                       │
                       ▼
                 RISK CONTROL
                       │
                       ▼
              RESEARCH / REPLAY
```

The strategy operates on three coordinated horizons:

* **HTF — Higher Timeframe:** establishes directional bias and structural destination.
* **MTF — Middle Timeframe:** identifies setup formation, structural realignment, KeyZones, retests, and manages the open trade.
* **LTF — Lower Timeframe:** provides the execution trigger and initial structural invalidation.

The system therefore follows:

> **HTF Bias → MTF Setup → MTF Retest → LTF Entry → LTF Invalidation → HTF Target → MTF Structural Trailing**

---

## 03 — Strategy Hypotheses

The platform currently researches two independent hypotheses.

### Hypothesis A — Pullback Riding

The HTF establishes directional bias through market structure.

Price subsequently retraces toward an HTF structural KeyZone.

The MTF may temporarily move counter to the HTF direction during the retracement.

The system waits for MTF structural/trend realignment toward the HTF bias, identifies a new MTF setup and KeyZone, waits for the MTF retest, and then searches for an LTF execution model.

```text
HTF BOS / Directional Bias
        ↓
HTF Pullback
        ↓
HTF KeyZone Interaction
        ↓
MTF Countertrend Retracement
        ↓
MTF Structural Realignment
        ↓
MTF KeyZone / FVG / OB
        ↓
MTF Retest
        ↓
LTF Entry Model
        ↓
LTF Structural Invalidation
        ↓
HTF Structural Target
        ↓
MTF Structural Trailing
```

### Hypothesis B — Continuation Riding

The HTF has already interacted with the relevant structural zone and continuation is expected.

The system waits for MTF structural/trend alignment with the HTF bias, establishes the MTF setup, waits for its retest, and then searches for an LTF execution trigger.

```text
HTF Directional Bias
        ↓
HTF Continuation Context
        ↓
MTF Setup
        ↓
MTF Structural Realignment
        ↓
MTF KeyZone / FVG / OB
        ↓
MTF Retest
        ↓
LTF Structural Alignment
        ↓
LTF Entry Model
        ↓
LTF Structural Invalidation
        ↓
HTF Structural Target
        ↓
MTF Structural Trailing
```

The two hypotheses remain independently testable and attributable.

---

## 04 — Multi-Timeframe Strategy Configurations

The same strategy hypotheses are evaluated across four independent
timeframe configurations.

| Set | HTF | MTF | LTF | Trading Horizon |
|---|---|---|---|---|
| Set 1 | 1M | 1W | 1D | Macro / Position |
| Set 2 | 1W | 1D | 4H | Position / Swing |
| Set 3 | 1D | 4H | 1H | Swing / Intraday |
| Set 4 | 4H | 1H | 15M | Intraday |

Each configuration is treated as a separate research population.

The system does not assume that performance on one timeframe configuration
transfers automatically to another.

---

## 05 — Market Intelligence

Product 01 transforms cryptocurrency OHLCV data into a deterministic,
causal market-state representation.

The intelligence layer models:

- Market Structure
- External and Internal Structure
- BOS / CHOCH / MSS
- Protected Highs and Lows
- Liquidity Pools
- Liquidity Sweeps
- Inducement
- Order Blocks
- Fair Value Gaps
- KeyZone Mitigation
- Market Phase
- Trend State
- Structural Validation

The output is exposed through a controlled:

`MarketStatePayload`

Product 02 consumes this contract rather than independently recreating
market intelligence.

---

## 06 — Core Engineering Laws

These principles govern every product.

### LAW 01 — Temporal Causality

At timestamp `T`, no component may consume information that was unavailable at `T`.

Historical future information must never leak into a historical decision.

### LAW 02 — Deterministic Reproducibility

For identical input data and configuration:

```text
P(D, Config) Run A
        ≡
P(D, Config) Run B
```

### LAW 03 — Domain Isolation

Higher-level systems may consume lower-level contracts. Lower-level systems must never depend on higher-level decisions.

### LAW 04 — State Provenance

Every important decision must be traceable to its originating market events.

### LAW 05 — Fail Closed

When information is ambiguous, incomplete or invalid, `NO_TRADE` is preferable to an unsupported assumption.

### LAW 06 — Rejected Information Is Still Research Data

Rejected setups are not discarded. These observations become research telemetry.

### LAW 07 — Hypotheses Must Remain Isolated

A strategy hypothesis must be independently measurable. No hidden cross-contamination of rules, parameters or outcome attribution.

### LAW 08 — No Optimization Before Evidence

The platform does not add indicators, filters or parameters simply because a backtest looks weak.

---

## 07 — Platform Product Architecture

```text
P01 — MARKET INTELLIGENCE
      ↓
      MarketStatePayload
      ↓
P02 — STRATEGY ENGINE
      ↓
      TradePlanPayload
      ↓
P03 — RISK FIREWALL
      ↓
      RiskApprovedPlan
      ↓
P04 — RESEARCH & BACKTESTING
      ↓
      Validated Research Evidence
      ↓
P05 — PORTFOLIO CONTROL
      ↓
      Portfolio Decision
      ↓
P06 — EXECUTION
      ↓
      Live Orders / Fills
      ↓
P07 — PRODUCTION OPERATIONS
      ↓
      Monitoring / Reconciliation / Kill Switch
```

Each product owns a distinct responsibility and communicates through
explicit contracts.

---

## 08 — Product Verification State

```text
==============================================================
            CRYPTO QUANTITATIVE SYSTEMS PLATFORM
==============================================================

PRODUCT 01 — MARKET INTELLIGENCE
    Regression                  131 / 131
    Independent Acceptance      100 / 100
    Status                      🔒 LOCKED

PRODUCT 02 — STRATEGY ENGINE
    Platform Regression         Included
    Lifecycle Architecture      Implemented
    Hypothesis Isolation        Verified
    Causality                   Verified
    Acceptance                  6 / 6 PASS
    Status                      🔒 ACCEPTED

PRODUCT 03 — RISK FIREWALL
    Risk Engine                 Implemented
    Integration                 Verified
    Full Regression             145 / 145
    Independent Acceptance      NEXT
    Status                      🟢 IMPLEMENTED / AWAITING ACCEPTANCE

PRODUCT 04 — RESEARCH LAB
    Status                      ⏳ NEXT

==============================================================
FULL REPOSITORY REGRESSION
                    145 / 145 PASSING
==============================================================
```

---

## 09 — Product 04: Research & Backtesting Laboratory

**Next major development target.**

The research pipeline:

```text
                    HISTORICAL DATA
                          │
                          ▼
                  MARKET REPLAY
                          │
                          ▼
                 PRODUCT 01
                          │
                          ▼
                 PRODUCT 02
                          │
                          ▼
                 PRODUCT 03
                          │
                          ▼
              SIMULATED EXECUTION
                          │
                          ▼
                    TRADE LEDGER
                          │
                          ▼
              PERFORMANCE ATTRIBUTION
                          │
              ┌───────────┴───────────┐
              ▼                       ▼
        IN-SAMPLE                 OUT-OF-SAMPLE
              │                       │
              └───────────┬───────────┘
                          ▼
                  WALK-FORWARD
                          │
                          ▼
                    ROBUSTNESS
                          │
                          ▼
                 PAPER TRADING
```

---

## 10 — Research Matrix

Initial baseline:

```text
2 Strategies
×
4 Timeframe Sets
×
3 Assets
=
24 configurations
```

The first objective is to discover:

```text
Does the canonical architecture
produce positive expectancy after
realistic trading friction?
```

Only then should optimization begin.

---

## 11 — Repository Architecture

```text
crypto-platform/
│
├── config/
├── market_intelligence/
├── strategy_engine/
├── risk_engine/
├── research/
├── portfolio/
├── execution/
├── operations/
├── market_data/
├── logs/
├── tests/
├── README.md
└── LICENSE
```

---

## Engineering Principle

> **The platform does not assume an edge.**
>
> It formalizes trading hypotheses, subjects them to deterministic
> historical research, measures their failure modes, constrains capital
> risk, and only permits automation after sufficient evidence has been
> established.

**Crypto Quantitative Systems Platform**

*Research before optimization.*  
*Risk before execution.*  
*Evidence before automation.*
