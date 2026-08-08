# APEX Quantitative Crypto Platform
> **Institutional-Grade Autonomous Cryptocurrency Trading Platform for Market Intelligence, Risk Management, and Deterministic Strategy Execution.**

![Python Version](https://img.shields.io/badge/python-3.12-blue.svg)
![Build Status](https://img.shields.io/badge/build-67%2F67%20passing-brightgreen.svg)
![Architecture](https://img.shields.io/badge/architecture-event--driven--causal-orange.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

---

## 🏛 System Architecture Overview

The APEX Platform is an event-driven, multi-timeframe quantitative trading engine built on strict **Fractal Market Invariance**. Every timeframe ($1\text{M}, 1\text{W}, 1\text{D}, 4\text{H}, 1\text{H}, 15\text{M}$) independently evaluates market language primitives to construct a standardized `MarketStatePayload`:

$$\text{MarketState}_T = \{ \text{Trend}, \text{Structure}, \text{Keyzones}, \text{Liquidity}, \text{Phase} \}$$

                       RAW OHLCV MARKET DATA
                                 │
                                 ▼
  ┌─────────────────────────────────────────────────────────────┐
  │             PRODUCT 01: MARKET LANGUAGE ENGINE              │
  │                                                             │
  │  ┌──────────────────┐  ┌──────────────────┐  ┌───────────┐  │
  │  │ Engine 1: Raw    │  │ Engine 2: Causal │  │ Engine 3: │  │
  │  │ Swing Extrema    │─►│ Structure        │─►│ Liquidity │  │
  │  │ (Zero-Lookahead) │  │ State Machine    │  │ Pools     │  │
  │  └──────────────────┘  └──────────────────┘  └───────────┘  │
  │                             │                               │
  │  ┌──────────────────┐  ┌────┴─────────────┐  ┌───────────┐  │
  │  │ Engine 6: Trend  │◄─│ Engine 5: Phase  │◄─│ Engine 4: │  │
  │  │ Classification   │  │ Classifier       │  │ Keyzones  │  │
  │  └──────────────────┘  └──────────────────┘  └───────────┘  │
  └──────────────────────────────┬──────────────────────────────┘
                                 │
                       MarketStatePayload
                                 │
        ┌────────────────────────┼────────────────────────┐
        ▼                        ▼                        ▼
 HTF Context Bias        MTF Setup Engine         LTF Trigger Engine
  (1D / 4H / 1W)          (4H / 1H / 1D)            (1H / 15M / 1M)
        │                        │                        │
        └────────────────────────┼────────────────────────┘
                                 │
                                 ▼
                  ┌─────────────────────────────┐
                  │    RISK & RR GATEWAY        │
                  │  • Hard Per-Trade Ceiling   │
                  │  • Risk/Reward Floor        │
                  └──────────────┬──────────────┘
                                 │
                                 ▼
                  ┌─────────────────────────────┐
                  │   DYNAMIC MTF TRAILING      │
                  │   • Structural Lock-In      │
                  └──────────────┬──────────────┘
                                 │
                                 ▼
                    REALISTIC REPLAY & EXECUTION

---

## 🔒 Product 01: Market Language Sub-Systems

The platform decouples market observation from trading decisions. Downstream strategy modules consume raw state payloads without modifying upstream market language logic.

### 1. Engine 1: Raw Swing Engine (`raw_swing_engine.py`)
* **Zero-Lookahead Confirmation**: Explicitly separates extreme detection index ($i$) from confirmation index ($i + N_{\text{right}}$).
* **Strict Geometric Bounds**: Rejects flat-top and flat-bottom extrema to avoid arbitrary pivot selections.

### 2. Engine 2: Stateful Market Structure Engine (`structure_builder_engine.py`)
* **Hierarchical Leg Scopes**: Differentiates macro external structural legs from nested internal retracements.
* **Causal Protected/Weak Roles**: Links protected swings directly to the causal origin of new structural expansions.
* **Stateful Event Ledger**: Emits deduplicated structural state transitions (`EXTERNAL_BOS`, `EXTERNAL_CHOCH`, `INTERNAL_BOS`, `INTERNAL_CHOCH`, `MSS`, `FAILED_BOS`).
* **Active Dealing Range**: Computes dynamic equilibrium bounds ($P_{\text{eq}} = P_{\text{low}} + \frac{P_{\text{high}} - P_{\text{low}}}{2}$) independently of protected level state.

---

## 📁 Repository Map

crypto-platform/
├── market_intelligence/       # Product 01: Market Language Engine
│   ├── primitives.py          # Shared immutable domain contracts
│   ├── raw_swing_engine.py    # Engine 1: Zero-lookahead swing extrema
│   └── structure_builder.py  # Engine 2: Stateful market structure builder
├── strategy/                  # HTF / MTF / LTF Orchestration Layer
├── risk/                      # Account equity gates & RR Floor verification
├── trade_management/          # MTF structural trailing engines
├── backtesting/               # Friction-aware historical replay engine
├── config/                    # Timeframe hierarchy sets & asset specs
└── tests/
└── unit/                  # Comprehensive unit & regression test suites


---

## 🧪 Verification & Test Suite

The platform enforces a 100% test-pass gate prior to freezing any architectural sub-system.

```bash
# Execute full repository regression discovery suite
python3 -m unittest discover -s tests -p "test*.py" -v
Plaintext
Ran 67 tests in 0.023s

OK
🛡 License
Distributed under the MIT License. See LICENSE for details.
