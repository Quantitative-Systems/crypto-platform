# QCP — Quantitative Crypto Platform

[![Tests](https://img.shields.io/badge/tests-556%20passing-brightgreen)](#testing)
[![Live Capital](https://img.shields.io/badge/live%20capital-$0.00-red)](#production-gate)
[![Alpha Status](https://img.shields.io/badge/validated%20alpha-NONE-orange)](#alpha-discovery)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

> **Scientific integrity first.** QCP exists to discover economically real, statistically defensible, executable, scalable, and independent crypto return sources — or to honestly report that none exist.

---

## Table of Contents

- [What QCP Is](#what-qcp-is)
- [What QCP Is Not](#what-qcp-is-not)
- [Current Status](#current-status)
- [Architecture](#architecture)
- [Production Gate](#production-gate)
- [Alpha Discovery](#alpha-discovery)
- [Repository Layout](#repository-layout)
- [Getting Started](#getting-started)
- [Testing](#testing)
- [Safety Guarantees](#safety-guarantees)
- [Governance](#governance)
- [Contributing](#contributing)

---

## What QCP Is

QCP is a self-auditing quantitative research and execution system for crypto markets built around four non-negotiable principles:

1. **Empirical truth** — every claim is backed by independently verifiable data and code.
2. **Adversarial falsification** — every strategy is actively attacked before it is promoted.
3. **Causal evaluation** — backtests are partitioned into development, validation, and untouched out-of-sample windows; results are never cherry-picked.
4. **Fail-closed safety** — when data quality is uncertain or a risk gate fires, the system stops. It does not simulate, interpolate, or manufacture.

---

## What QCP Is Not

| ❌ What QCP Refuses To Do | ✅ What QCP Does Instead |
|---|---|
| Manufacture profitable backtest results | Report `NO_NEW_ECONOMIC_EDGE_VALIDATED` when none exists |
| Simulate unavailable market data | Block live execution; require real warehouse data |
| Treat paper trading as live validation | Maintain hard `$0.00` live capital gate |
| Auto-approve strategies after a single pass | Require multi-partition OOS + adversarial battery |
| Skip friction modelling | Apply maker/taker fees, bid-ask spread, execution slippage, borrow financing |

---

## Current Status

| Dimension | State |
|---|---|
| **Live capital deployed** | `$0.00` — production gate not yet cleared |
| **Validated alpha strategies** | `0` — no edge has cleared adversarial falsification |
| **Discovery phase** | Active — empirical alpha search in progress |
| **Test suite** | 556 / 556 passing |
| **Data warehouse** | 24 certified datasets with SHA-256 lineage hashes |
| **Blocked data streams** | Funding rates, L2 order books, liquidation cascades (not yet warehoused — no synthetic substitution) |

> **This is honest reporting, not a limitation.** The system is working exactly as designed: it refuses to report alpha where none has been found.

---

## Architecture

QCP is organized as a layered system of autonomous, self-auditing subsystems:

```
┌─────────────────────────────────────────────────────────────────────┐
│                     AUTONOMOUS RESEARCH LOOP                        │
│  EmpiricalAlphaDiscoveryEngine → AutonomousResearchGovernor         │
│  CertifiedResearchUniverseEngine → OpportunityDetector              │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     BACKTESTING LAYER                               │
│  DEV window (2021-2022) → VAL window (2023) → OOS window (2024-26)  │
│  Adversarial battery: lookahead, 2x friction, windfall, latency     │
│  Bonferroni-corrected multiple-testing control                      │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     EXECUTION GATEWAY                               │
│  Pre-trade risk check → Position sizing → Order routing             │
│  Circuit breakers → Drawdown limits → VaR / CVaR enforcement        │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     PRODUCTION GATE                                 │
│  Evidence registry → Canonical audits → Capital authorization       │
│  Status: LOCKED ($0.00 live) until gate cleared by empirical proof  │
└─────────────────────────────────────────────────────────────────────┘
```

### Key Subsystems

| Subsystem | Location | Purpose |
|---|---|---|
| **Alpha Discovery Engine** | `research/discovery_lab/` | Causal multi-partition backtesting and adversarial falsification |
| **Certified Universe Engine** | `market_data/certified_research_universe.py` | SHA-256 dataset lineage audit and data-stream gating |
| **Research Governor** | `research/autonomous_research_governor.py` | Evidence-based research priority scoring and scheduling |
| **Opportunity Detector** | `market_intelligence/opportunity_detector.py` | Structural anomaly scanning across certified assets |
| **Opportunity Memory** | `research/opportunity_memory.py` | Regime-aware hypothesis lifecycle management |
| **Execution Gateway** | `execution_gateway/` | Pre-trade risk enforcement and order routing |
| **Risk Engine** | `risk_engine/` | Real-time VaR, CVaR, drawdown, and correlation monitoring |
| **Portfolio Engine** | `portfolio_engine/` | Position sizing, allocation, and rebalancing |
| **Production Gate** | `production/` | Autonomous production-readiness gate with evidence registry |
| **Platform Core** | `platform_core/` | Unified state store, audit bus, and evidence provenance layer |

---

## Production Gate

The production gate enforces **six canonical audits** before any live capital can be deployed:

1. **Data Integrity Audit** — All input data must have SHA-256 verified lineage
2. **Strategy Conformance Audit** — Strategy logic must match registered specification
3. **Risk Gate Audit** — All risk limits must be binding and non-bypassable
4. **Execution Fidelity Audit** — Fills must be real; no fabricated P&L
5. **Research Integrity Audit** — No lookahead, no data-mining bias, no multiple-testing inflation
6. **Capital Authorization Audit** — Explicit empirical evidence required for every dollar deployed

**Current gate status: `LOCKED`**

No capital will be deployed until all six audits pass independently. This is enforced in code, not just policy.

---

## Alpha Discovery

### Process

Every candidate strategy must survive the following pipeline before being considered validated:

```
Hypothesis Generation
       │
       ▼
DEV Backtest (2021–2022)
  ├─ Full friction model (maker/taker + spread + slippage + financing)
  └─ Statistical significance (Sharpe > 0, p < 0.05)
       │
       ▼
VAL Backtest (2023)
  ├─ Independent confirmation (Sharpe > 0.5)
  └─ Drawdown within tolerance
       │
       ▼
Adversarial Falsification Battery
  ├─ Lookahead contamination test
  ├─ 2× friction shock (does edge survive doubled costs?)
  ├─ Windfall removal (strip outlier days)
  └─ Latency delay injection
       │
       ▼
OOS Backtest (2024–2026) — UNTOUCHED until adversarial battery passed
       │
       ▼
Multiple-Testing Control (Bonferroni-corrected hurdle)
       │
       ▼
Research Governor Promotion Decision
       │
       ▼ (only if ALL above cleared)
Production Gate Review → Capital Authorization
```

### Canonical Discovery Reports

Every research cycle emits two machine-readable reports:

- **`QCP_ALPHA_DISCOVERY_REPORT.json`** — full structured evidence record
- **`QCP_ALPHA_DISCOVERY_REPORT.md`** — human-readable summary

Latest finding: **`NO_NEW_ECONOMIC_EDGE_VALIDATED`**

This is the correct and expected output when no strategy has cleared adversarial falsification. It is not a failure — it is the system working honestly.

---

## Repository Layout

```
crypto-platform/
├── backtesting/              # Backtest engine and partition management
├── capital_intelligence/     # Capital allocation intelligence
├── config/                   # System and risk configuration
├── docs/                     # Extended documentation
├── execution_gateway/        # Order routing and pre-trade risk
├── market_data/              # Data pipeline and certified universe engine
├── market_intelligence/      # Opportunity detection and regime analysis
├── platform_core/            # State store, audit bus, evidence provenance
├── portfolio_engine/         # Position sizing and portfolio management
├── production/               # Production gate and canonical audits
├── research/
│   ├── autonomous_research_governor.py
│   ├── discovery_lab/        # Alpha discovery engine (core research)
│   ├── opportunity_memory.py
│   └── ...
├── risk/                     # Risk models and analytics
├── risk_engine/              # Real-time risk enforcement
├── strategy/                 # Strategy registry and base classes
├── strategy_engine/          # Strategy lifecycle management
├── tests/
│   ├── unit/                 # 500+ unit tests
│   └── integration/          # End-to-end pipeline tests
├── trade_management/         # Order and trade lifecycle
├── CAPABILITY_REGISTRY.json  # Machine-readable capability evidence
├── CHANGELOG.md              # Detailed change history
├── CONTRIBUTING.md           # Contribution guidelines
├── RESEARCH_INTEGRITY_AUDIT.md
├── SECURITY.md
└── pyproject.toml
```

---

## Getting Started

### Prerequisites

- Python 3.11+
- Unix-like environment (Linux / macOS)

### Installation

```bash
git clone https://github.com/Quantitative-Systems/crypto-platform.git
cd crypto-platform
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Run the Test Suite

```bash
python3 -m pytest tests/ -v
```

### Run the Research Governor

```bash
python3 -m research.autonomous_research_governor
```

### Run Alpha Discovery

```bash
python3 -m research.discovery_lab.empirical_alpha_discovery_engine
```

Discovery reports will be written to:
- `QCP_ALPHA_DISCOVERY_REPORT.json`
- `QCP_ALPHA_DISCOVERY_REPORT.md`

---

## Testing

QCP maintains a comprehensive test suite with strict coverage requirements:

| Category | Tests | Status |
|---|---|---|
| Unit — Research | 80+ | ✅ Passing |
| Unit — Risk Engine | 60+ | ✅ Passing |
| Unit — Execution | 50+ | ✅ Passing |
| Unit — Data / Universe | 40+ | ✅ Passing |
| Unit — Platform Core | 60+ | ✅ Passing |
| Unit — Strategy Engine | 80+ | ✅ Passing |
| Integration — Alpha Discovery Pipeline | 20+ | ✅ Passing |
| Integration — Production Gate | 30+ | ✅ Passing |
| **Total** | **556** | **✅ All passing** |

Tests are organized under `tests/unit/` and `tests/integration/`. All tests are deterministic and run without network access or live exchange connections.

---

## Safety Guarantees

QCP enforces the following safety properties in code (not just documentation):

| Guarantee | Enforcement |
|---|---|
| No live fills without validated alpha | Production gate code-lock |
| No synthetic data substitution for missing streams | `CertifiedResearchUniverseEngine` blocks unwarehoused streams |
| No lookahead contamination | Adversarial falsification battery (required, not optional) |
| No multiple-testing inflation | Bonferroni correction applied to all hypothesis batches |
| No fabricated P&L | All backtests use decomposed friction models; slippage is not zero |
| Live capital: $0.00 until independently authorized | Hard gate enforced by `production/` subsystem |

---

## Governance

QCP is self-governed by the **Autonomous Research Governor** (`research/autonomous_research_governor.py`), which:

- Scores research opportunities by data readiness, signal quality, and statistical confidence
- Enforces research priority based on evidence — not preference
- Manages hypothesis lifecycle (open → under test → falsified → closed)
- Emits canonical audit trails for every decision

All governance decisions are logged to the platform audit bus and are independently verifiable.

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidelines.

**Key rule:** do not submit code that manufactures positive results, weakens safety gates, removes friction from backtests, or bypasses the production capital gate. Such PRs will be rejected.

---

## License

MIT — see [LICENSE](LICENSE).

---

*QCP reports scientific truth. If no alpha exists, QCP says so.*
