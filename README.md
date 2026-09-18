# QCP — Quantitative Crypto Platform

[![Tests](https://img.shields.io/badge/tests-604%20passed%2C%202%20failed%2C%2014%20errors-orange)](#5-testing)
[![Live Capital](https://img.shields.io/badge/live%20capital-$0.00-red)](#4-current-research)
[![Alpha Status](https://img.shields.io/badge/validated%20alpha-NONE-orange)](#4-current-research)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

> **Scientific integrity first.** QCP exists to discover economically real,
> statistically defensible, executable, scalable, and independent crypto
> return sources — or to honestly report that none exist.

QCP is a **quantitative research and trading-infrastructure system**: a causal
backtesting laboratory with a modular strategy grammar, a binding risk
firewall, decomposed friction modelling, adversarial falsification, and full
negative-result preservation. It is **not** a profitable trading bot. No
strategy here has cleared validation, no capital is deployed, and no
profitability is claimed.

---

## Table of Contents

- [1. Project Overview](#1-project-overview)
- [2. Current Architecture](#2-current-architecture)
- [3. Research Philosophy](#3-research-philosophy)
- [4. Current Research](#4-current-research)
- [5. Testing](#5-testing)
- [6. Research Results](#6-research-results)
- [7. Repository Structure](#7-repository-structure)
- [8. Current Limitations](#8-current-limitations)
- [9. Roadmap](#9-roadmap)
- [Getting Started](#getting-started)
- [Safety Guarantees](#safety-guarantees)
- [Governance](#governance)
- [Contributing](#contributing)
- [License](#license)

---

## 1. Project Overview

**What QCP is.** A reproducible platform for one honest question: *does this
hypothesis survive causal execution, real friction, and out-of-sample
validation?* It provides a certified data layer, a strategy grammar
(HTF bias -> MTF setup -> LTF entry -> structural SL/TP/trailing), causal
backtesting across DEV (2021-2022) / VAL (2023) / OOS (2024-2026) partitions,
friction-aware evaluation, adversarial falsification, and a fail-closed
production gate (live capital `$0.00`, order submission `DISABLED`).

**What problem it solves.** Retail backtests manufacture edge via lookahead
leakage, ignored costs, cherry-picked windows, and deleted failures. QCP makes
each failure mode structurally difficult: causality in code, costs before
claims, chronological partitions, preserved negatives.

**What QCP is not:**

| Refused | Done instead |
|---|---|
| Manufacture profitable backtests | Report `NO_NEW_ECONOMIC_EDGE_VALIDATED` |
| Simulate missing market data | Block with `BLOCKED_EXTERNAL_DATA` |
| Treat paper trading as validation | Hard `$0.00` capital gate |
| Approve after a single pass | Require OOS + adversarial battery |
| Skip friction | Fees + spread + slippage + financing |

---
## 2. Current Architecture

Implemented flow (every box exists in code; aspirations are labelled PLANNED
in section 9):

```text
Data (market_data/: loader, certifier, universe, manifests)
  -> Market Intelligence (market_intelligence/: regimes, opportunity detector)
  -> Research / Alpha (governor, factory, discovery lab, falsification)
  -> Strategy Grammar (research/*_families.py + strategy_grammar.py)
  -> Risk (risk_engine/: 1% sizer, 4R firewall, breakers, veto)
  -> Execution (SIMULATED ONLY: research/simulation/ + friction_model.py)
  -> Backtesting (research/replayer/: causal replayer + aligner)
  -> Economic Evaluation (economic_evaluation_engine.py + evidence ledger)
  -> Telemetry (research/results/telemetry/: audit ledger, telemetry)
  -> Research Feedback (opportunity_memory, hypothesis registry, reports)
```

Live order routing is NOT in this path. `execution_gateway/` lives only under
`quarantine/` (prototype, not importable as a top-level package). Anything
importing it fails at collection — see section 5 and 8.

| Subsystem | Location | Status |
|---|---|---|
| Data layer | `market_data/` | IMPLEMENTED |
| Regime engines | `research/regime_engine.py`, `research/market_regime.py` | IMPLEMENTED |
| Strategy grammar | `research/strategy_grammar.py`, `research/*_families.py` | IMPLEMENTED |
| Foundation registry | `research/foundation_registry.py` | IMPLEMENTED |
| Causal replayer | `research/replayer/`, `research/simulation/` | IMPLEMENTED |
| Friction model | `backtesting/friction_model.py` (3 fill models) | IMPLEMENTED |
| Economic evaluation | `research/economic_evaluation_engine.py` | IMPLEMENTED |
| Discovery lab | `research/discovery_lab/` | PARTIALLY (known regression, sec 5) |
| Falsification engine | `research/adversarial_falsification_engine.py` | IMPLEMENTED |
| Governor + factory | `research/autonomous_research_*.py` | IMPLEMENTED (gap noted, sec 5) |
| Risk engine | `risk_engine/` | IMPLEMENTED |
| Production gate | `production/` (capital locked) | IMPLEMENTED |
| Platform core | `platform_core/` | IMPLEMENTED |

Full IMPLEMENTED / PARTIAL / PLANNED / NOT verdicts:
`research/results/DAY_48_REPOSITORY_CLOSEOUT.md`.

---

## 3. Research Philosophy

1. **Evidence before claims.** Hypotheses are words until measured from
   checksummed data. The factory ships zeroed metrics by contract.
2. **Reproducibility.** Same data + config = same result. Hashes, configs,
   lineages frozen in manifests and evidence records.
3. **Causal backtesting.** Closed-bar signals fill at the NEXT bar open.
   Same-bar fills impossible; stop/target collisions resolve adverse-first.
4. **Friction-aware evaluation.** Fees, spread, slippage, borrow deducted
   before any claim; 2x cost shock required.
5. **Negative-result preservation.** Failures are committed artifacts, never
   deleted.
6. **Research governance.** One-variable experiments, frozen controls,
   Bonferroni correction, strict DEV / VAL / untouched-OOS separation.

---
## 4. Current Research

### Phase C — structural + regime edge (DEV 2021-2022, BTC/ETH/SOL x SET_2/3/4)

Five hypotheses under the binding 4R firewall. All failed or inconclusive.
Preserved, not hidden.

| Hypothesis | Trades | Net R | Verdict |
|---|---|---|---|
| H_STRUCT_01 (FVG Tap + Breakout Close) | 77 | -22.64R | FAIL |
| H_STRUCT_02 (FVG + Displacement) | 14 | -6.68R | INCONCLUSIVE (n<15) |
| H_STRUCT_03 (Sweep + Reclaim) | 11053 | -3624.04R | FAIL |
| H_STRUCT_04 (Sweep + CHoCH + BOS trail) | 31 | -7.41R | FAIL |
| H_STRUCT_05 (Breakout Retest) | 65 | -24.45R | FAIL |

Report: `research/results/STRUCTURAL_REGIME_RESEARCH_REPORT.md`.

### Phase D — H_STRUCT_01 forensics (frozen, no tuning)

- **D-0 control:** 77 trades, **+1.64R gross / -22.64R net**, PF 0.713,
  WR 24.7%. Friction 24.28R = **1478% of gross**.
- **D-1 geometry sweep:** target-R sweep (1.5R-4R) **inoperative** — identical
  populations at every level; structural TP already exceeded the firewall.
- **D-2 fill models:** TAKER / MAKER_TOUCH / MAKER_CONSERVATIVE gave 77 / 84 /
  93 trades (net -22.64R / -9.48R / -5.42R). Different populations, because
  entry fill recomputes risk-per-unit and firewall pass/fail. All negative.
- Nothing declared profitable or a winner.

Reports: `research/results/EXECUTION_GEOMETRY_SWEEP_REPORT.md` and
`research/results/execution_geometry_sweep_raw.json`.

### Discovery verdict

Canonical verdict: **`NO_NEW_ECONOMIC_EDGE_VALIDATED`** (148 evaluated, 116
falsified, 32 blocked on missing data, 0 survivors).
See `research/results/QCP_ALPHA_DISCOVERY_REPORT.md`.

### Next task (NOT started)

**HISTORICAL_POSITIVE_RECONCILIATION** — which historical positives survive
the corrected engine. Not implemented, not attempted in this freeze.

---
## 5. Testing

Full run **2026-09-18**:
`PYTHONPATH=. python3 -m pytest tests/ -p no:cacheprovider
--continue-on-collection-errors -q` (~140 s):

| Outcome | Count |
|---|---|
| Passed | **604** |
| Failed | **2** |
| Collection errors | **14** |
| Total collected | 620 |

Failures documented, not silently fixed (freeze operation):

1. `test_alpha_discovery_pipeline_end_to_end` — discovery engine calls
   `simulate(df, signal, bar_hours)` but the signature requires
   `(df, signal, planned_sl, planned_tp, bar_hours)`.
2. `test_autonomous_research_forensic_pipeline` — blueprint genomes carry
   empty `failure_modes`, violating the genome-integrity assertion.
3. 14 collection errors — all `No module named 'execution_gateway'` (plus
   `derivatives_engine`, `low_latency`): live-gateway code lives under
   `quarantine/` while tests import it top-level. Boundary intentional;
   paths never migrated.

New grammar/foundation causality tests (30 tests) all pass.

```bash
PYTHONPATH=. python3 -m pytest tests/ -p no:cacheprovider --continue-on-collection-errors -q
PYTHONPATH=. python3 -m pytest tests/test_bias_causality.py tests/test_market_regime.py tests/test_regime_engine.py tests/test_structural_components.py tests/unit/research/test_foundation_registry.py -q
```

---

## 6. Research Results

Negative results included — that is the point:

- [Phase D sweep](research/results/EXECUTION_GEOMETRY_SWEEP_REPORT.md) /
  [raw JSON](research/results/execution_geometry_sweep_raw.json)
- [Phase C structural regime](research/results/STRUCTURAL_REGIME_RESEARCH_REPORT.md)
- [Discovery matrix](research/results/DISCOVERY_MATRIX_REPORT.md)
- [Discovery report](research/results/QCP_ALPHA_DISCOVERY_REPORT.md)
- [Foundation manifest](research/results/FOUNDATION_MANIFEST.json)
- [Closeout: audit + test record](research/results/DAY_48_REPOSITORY_CLOSEOUT.md)
- Full ledger: `research/results/` (198 JSON + 20 MD) and `docs/` (46 docs).

---
## 7. Repository Structure

```text
crypto-platform/
├── backtesting/              # Replay engine, friction model, analytics
├── capital_intelligence/     # Capacity / feasibility intelligence
├── config/                   # Canonical 6-set ladder (single source of truth)
├── docs/                     # 46 documents: specs, audits, methodology
├── market_data/              # Loader, certifier, universe engine (+ local cache)
├── market_intelligence/      # Regime engines, opportunity detector
├── platform_core/            # State store, audit bus, provenance, secrets
├── portfolio_engine/         # Sizing, allocation, exposure graph
├── production/               # Production gate, audits, paper daemon (locked)
├── quarantine/               # NOT importable: gateway, derivatives, MM prototypes
├── research/
│   ├── *_families.py         # bias / setup / entry / SL / TP / trailing
│   ├── strategy_grammar.py + grammar_components.py
│   ├── regime_engine.py + market_regime.py + timeframe_sets.py
│   ├── foundation_registry.py
│   ├── economic_evaluation_engine.py + falsification engine
│   ├── autonomous_research_governor.py + factory
│   ├── discovery_lab/        # Discovery engine
│   ├── replayer/ + simulation/
│   ├── experiments/          # 45 run_*.py harnesses (incl. Phase C/D)
│   └── results/              # 198 JSON + 20 MD (positives AND negatives)
├── risk_engine/              # Canonical risk (risk/ is legacy)
├── strategy/ + strategy_engine/
├── tests/                    # 142 files: unit / integration / comprehensive
├── CAPABILITY_REGISTRY.json / CHANGELOG.md / CONTRIBUTING.md
├── SECURITY.md / LICENSE (MIT)
└── pyproject.toml / requirements.txt  # numpy + pandas; pytest dev
```

---

## 8. Current Limitations

- **No validated edge.** 0 strategies cleared falsification + OOS.
  Capital `$0.00`, orders `DISABLED`.
- **Small samples.** H_STRUCT_01 = 77 DEV trades; H_STRUCT_02 = 14.
- **DEV-only for Phase C/D.** VAL/OOS continuation is future work.
- **Simulated execution.** Two fee schedules coexist
  (7.5/2 bps vs 0/5 bps maker/taker) — documented, not averaged.
- **Data gaps.** Funding, L2, liquidations unwarehoused; dependents BLOCKED,
  never synthesised. Cache: 90 local files, 9 tracked samples.
- **Known test failures (sec 5).** 2 failed + 14 errors. Frozen, not patched.
- **Legacy duplication.** `risk/` vs `risk_engine/`; two regime lineages;
  dual timeframe definitions (canonical: `config/timeframe_sets.py`).
- **Unfinished.** Live gateway, funding research, H_STRUCT_01B, fractal
  program: NOT IMPLEMENTED (see sec 9).

---

## 9. Roadmap

### CURRENT (frozen tonight)

Research freeze: H_STRUCT_01 logic, 4R firewall, friction, execution models
unchanged. Audit, closeout, README/docs, clean commit, push.

### NEXT (tomorrow, in order)

1. **HISTORICAL_POSITIVE_RECONCILIATION** — survivors of corrected engine.
2. VAL/OOS continuation for any survivors.
3. Reconcile fee schedules; resolve `quarantine/` import boundary; fix the
   two integration failures as research tasks, not drive-by patches.

### FUTURE (hypotheses only — NOT implemented)

- **Fractal discovery:** per timeframe set (SET_1 = 1M/1W/1D ... SET_6 =
  15M/5M/1M), independently test scalping/intraday/swing/position/macro,
  trend/momentum/mean-reversion/volatility/liquidity/statistical/flow/
  relative-value/event-driven. Never pre-assign style to timeframe.
- **Composite confirmation:** HTF signal -> MTF confirm -> LTF confirm ->
  composite entry. Separate research.
- H_STRUCT_01B, live gateway, funding/microstructure warehousing.

---
## Getting Started

Prerequisites: Python 3.12+, Linux/macOS.

```bash
git clone https://github.com/Quantitative-Systems/crypto-platform.git
cd crypto-platform
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Runtime is minimal (`numpy`, `pandas`); `pytest` for tests; `ccxt` only for
optional quarantined gateway prototypes.

```bash
PYTHONPATH=. python3 -m pytest tests/ -p no:cacheprovider --continue-on-collection-errors -q
PYTHONPATH=. python3 -m research.autonomous_research_governor
PYTHONPATH=. python3 -m research.discovery_lab.empirical_alpha_discovery_engine
PYTHONPATH=. python3 -m research.foundation_registry
```

Reports land in `research/results/QCP_ALPHA_DISCOVERY_REPORT.{json,md}`.

---

## Safety Guarantees

| Guarantee | Enforcement |
|---|---|
| No live fills without validated alpha | Code-locked gate; `$0.00`; `DISABLED` |
| No synthetic data | Uncertified streams blocked |
| No lookahead | Next-bar fills; adverse-first; falsification battery |
| No multiple-testing inflation | Bonferroni correction |
| No fabricated P&L | Decomposed friction; slippage never zero |
| No secret leakage | Fail-closed `SecretsManager`; secrets gitignored |

---

## Governance

Governed by `research/autonomous_research_governor.py`: evidence-scored
priorities, hypothesis lifecycle (open -> test -> falsified -> closed),
audit trails. See `docs/research_governance.md`. No backtest alone promotes.

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Do not submit code that manufactures
results, weakens gates, removes friction, bypasses the capital gate, or
deletes negative results. Such PRs will be rejected.

---

## License

MIT — see [LICENSE](LICENSE).

---

*QCP reports scientific truth. If no alpha exists, QCP says so.*
