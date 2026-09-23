# Crypto Trading Platform

[![Tests](https://img.shields.io/badge/tests-43%20passing-green)](#testing)
[![Live Capital](https://img.shields.io/badge/live%20capital-%240.00-red)]
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

A research-driven cryptocurrency trading platform for market-data
infrastructure, strategy research, historical backtesting, validation,
portfolio construction, risk management, paper trading, and eventual
exchange-connected automated execution.

> **The platform places no live orders and holds no funds. All strategies are
> research artifacts. Nothing here is a profitability claim.**

---

## Overview

This repository contains a cost-aware, self-improving strategy research
engine covering six trading horizons — scalping, intraday, swing, position,
investing, and market-neutral carry — across ten liquid crypto assets. Every
strategy candidate is measured through the same pipeline: walk-forward
backtesting with full fee/slippage/spread modeling, out-of-sample validation,
a +50% cost-shock survival test, and a portfolio-level marginal-contribution
gate. Only books that survive all seven governance gates are promoted to
**paper trading**. Everything else is archived, with its rejection reason.

**No live capital is deployed. Promotion means paper-trading eligibility.**

---

## Project Goals

1. **Honest measurement.** Every strategy verdict is produced by one
   deterministic pipeline: next-bar-open fills, adverse-first stop
   resolution, costs charged on both sides, R-multiple accounting.
2. **No lookahead.** Parameters are selected on a development window,
   confirmed on a validation window, and reported on a held-out
   out-of-sample window that is never used for selection.
3. **Economic realism.** A horizon whose stop cannot pay its roundtrip cost
   is flagged `NOT_ECONOMIC` instead of being force-fit.
4. **Governed risk.** Volatility targeting, drawdown tiers, daily/weekly loss
   caps, consecutive-loss cooldown, and a hard kill switch.
5. **Preserved negative evidence.** Failed and superseded experiments are
   archived verbatim — they are part of the research record.

## Current Capabilities

### Implemented (CURRENT)

| Area | Status | Where |
|---|---|---|
| Market data (Binance USDⓈ-M klines + funding, quality gates) | Implemented | `market_data/`, `qcp_platform/data.py` |
| Strategy research across 6 horizons / 10 assets | Implemented | `qcp_platform/strategies.py`, `allocations.py` |
| Walk-forward backtesting (60/20/20 DEV/VAL/OOS) | Implemented | `qcp_platform/walkforward.py`, `engine.py` |
| Validation, cost-shock and robustness gates (G1–G6) | Implemented | `qcp_platform/evaluate.py` |
| Portfolio construction + governed paper simulation | Implemented | `qcp_platform/portfolio.py`, `governor.py` |
| Champion/challenger self-improvement loop | Implemented | `qcp_platform/improve.py` |
| Funding-carry parameter sweep | Implemented | `qcp_platform/carry_sweep.py` |
| Reporting (markdown + JSON artifacts) | Implemented | `qcp_platform/report.py` |
| Architecture blueprint (product → production) | Documented | `docs/` |
| Historical research archive | Preserved | `research/failed/` |

### Planned (PLANNED — not implemented)

Live exchange connectivity & order routing, multi-broker adapters beyond
Binance, real-time streaming execution, user accounts / multi-tenant SaaS,
web dashboards, database-backed state, and options/derivatives beyond
perpetual funding. See the
[architecture document](docs/CRYPTO_TRADING_PLATFORM_ARCHITECTURE.md) for
the full blueprint and build-phase sequence.

---

## Research & Backtesting

The engine sweeps every (horizon, family, asset) combination through a
walk-forward protocol with three temporal partitions:

```
DEV (60%)  — parameter selection happens here, only here
VAL (20%)  — the DEV winner must still work here, untouched
OOS (20%)  — reported once, never used for any decision
```

Six horizon books run from one risk governor: **SCALP, INTRADAY, SWING,
POSITION, INVEST, CARRY** (funding harvest, market-neutral). Ten assets, one
causal engine: next-bar-open fills, adverse-first stops, full costs on every
trade, R-multiple accounting.

Seven governance gates decide each book:

1. **G1 — Data** — trade counts, development span, cache integrity
2. **G2 — Alpha** — positive expectancy in DEV, VAL and OOS
3. **G3 — Statistics** — bootstrap probability, t-statistic
4. **G4 — Walk-forward** — DEV→OOS decay bound, sign stability
5. **G5 — Costs** — survival under a +50% cost shock
6. **G6 — Risk** — drawdown bound, no single trade dominating total R
7. **G7 — Portfolio** — marginal Sharpe contribution to the governed book set

Verdicts are explicit: `PROMOTABLE_PAPER_ONLY`, `MEASURED`, or
`REJECTED_<gate>`. Rejections are reported with the gate that killed them —
they are findings, not failures.

---

## Research Integrity

- **OOS is never tuned.** The held-out window is reported once.
- **Costs are always on.** Fee, slippage, and half-spread are charged both
  sides on every simulated trade, including the carry book (4 fills + basis).
- **Refusal is a valid output.** A horizon whose economics cannot pay its
  costs is flagged, not force-fit.
- **Every number is reproducible** from the local cache. The report
  deliberately leads with rejections.
- **No strategy is assumed profitable.** Strategies must earn promotion
  through reproducible research evidence. OOS results in this repository are
  historical simulation measurements, not forecasts.

## Architecture

The current research engine is a modular monolith of 13+ packages under
`qcp_platform/`, described in
[`qcp_platform/README.md`](qcp_platform/README.md):

```
costs → horizons → indicators → data → regimes → strategies → allocations
     → engine → walkforward → evaluate → runner → portfolio → governor
     → improve → report
```

The full product architecture — connectivity, research, portfolio, risk,
execution, operations, security, and the build-phase sequence — is specified
in [`docs/CRYPTO_TRADING_PLATFORM_ARCHITECTURE.md`](docs/CRYPTO_TRADING_PLATFORM_ARCHITECTURE.md).
It clearly distinguishes what is implemented today from what is planned.

---

## Repository Structure

| Path | Purpose |
|---|---|
| `qcp_platform/` | The deployable research engine (13+ modules, one command sweep) |
| `market_data/` | Binance kline/funding cache, ingestion, quality & lineage pipeline |
| `config/` | Asset universe and canonical timeframe sets |
| `research/results/qcp_platform/` | Current measured results: REPORT.md, verdicts, economic screen, baselines |
| `research/failed/` | Historical research archive — superseded and rejected work, preserved verbatim |
| `tests/` | Governance and data-layer tests for the current platform |
| `docs/` | Product architecture blueprint |

---

## Current Research Status

The authoritative, generated report is
[`research/results/qcp_platform/REPORT.md`](research/results/qcp_platform/REPORT.md).
It records how many books were measured, how many passed all gates, which
gate killed each rejected book, and the governed OOS portfolio simulation.

Summary of the most recent research run (see the report for details):

- 104 books measured across all horizons and assets with full costs.
- 10 books promoted to paper-trading eligibility across CARRY, INTRADAY,
  POSITION and SWING.
- Most single-asset books decay out-of-sample; the platform reports that
  rather than hiding it. Scalping is flagged **cost-impossible** with taker
  fills (costs exceed stop distance) and is only permitted in maker mode.
- CARRY is a market-neutral funding-harvest book measured against perpetual
  funding yield, not price direction.

These are historical simulation measurements on cached data. They are not
live performance, not a forecast, and not a profitability guarantee.

## Historical Research Archive

[`research/failed/`](research/failed/) preserves the complete record of the
earlier research program: superseded implementations, rejected hypotheses,
forensic investigations, and negative results — kept verbatim.

- **Failed ≠ deleted.** Archived code and results remain reproducible.
- **Failed ≠ useless.** Negative results are the reason the current engine
  looks the way it does.
- The archive is **not installed, not imported by the current engine, and not
  part of the test suite.**

See [`research/failed/README.md`](research/failed/README.md) for the archive
inventory and conventions.

---

## Testing

```bash
python3 -m pytest tests -q
```

43 tests cover the data-quality/lineage pipeline and the research engine's
governance invariants: causal HTF alignment, next-open entries, adverse-first
resolution, always-on costs, horizon economics, governor tiers,
funding-carry neutrality, and rotation without look-ahead.

---

## Security

See [SECURITY.md](SECURITY.md). Key points:

- This software does not claim profitability and is **not production-ready**.
- Never connect exchange API keys with withdrawal permissions.
- Run execution strictly in testnet or simulated paper-trading environments
  until you have independently verified robustness.
- `.gitignore` excludes `.env*`, key material, credential files, logs, and
  local databases.

---

## Development Roadmap

Near-term (research):

1. Broaden the measured book universe (more families, more timeframes).
2. Deepen out-of-sample and cost-shock validation.
3. Extend the champion/challenger improvement loop.

Medium-term (product):

4. Exchange-connected paper broker adapter.
5. Real-time market data streaming.
6. Multi-venue data and execution adapters.

Long-term (planned, not started):

7. Live execution with governed capital and user controls.
8. Multi-broker, multi-tenant product layer.

The full sequence, including contingency planning, is defined in the
[architecture document](docs/CRYPTO_TRADING_PLATFORM_ARCHITECTURE.md).

## Planned Exchange Connectivity

The first research venue is **Binance USDⓈ-M** (klines, funding rates).
Planned adapters, behind a normalized exchange-neutral interface:

| Venue | Data | Execution | Priority |
|---|---|---|---|
| Binance USDⓈ-M | Implemented (cache) | Paper only | Current |
| Bybit / OKX / Kraken | Planned | Planned | Phase 4+ |
| Generic CCXT adapter | Planned | Planned | Phase 4+ |

Any venue whose API cannot support the platform's execution semantics
(next-bar-open, adverse-first stops, full cost accounting) is excluded
rather than approximated.

---

## Paper Trading

`python3 -m qcp_platform.cli paper` simulates the promoted book set through
the risk governor on the out-of-sample window: per-horizon capital weights,
volatility scaling, drawdown tiers (10%/20%/25%), daily/weekly loss caps,
consecutive-loss cooldown, and a hard kill switch. Every skipped trade is
logged with its reason. Paper fills are simulated with the same cost model
as backtests — they are not live fills.

---

## Future Live Execution

**Not implemented.** Live trading is disabled by construction. Before any
live consideration the platform requires: a validated forward burn-in on
paper, exchange-connected execution with reconciliation, per-user capital
isolation, and the full safety architecture described in the blueprint.
This repository currently contains none of that, and says so.

---

## Limitations

- Single data venue (Binance USDⓈ-M); single cache.
- Results are historical simulations on cached data — subject to regime
  decay, cost drift, and every failure mode the gates test for.
- The research kernel is batch-oriented (CLI sweeps), not streaming.
- No user accounts, no API server, no frontend, no database-backed state.
- The historical archive (`research/failed/`) contains earlier-generation
  code and experiments retained for the record; it is not installed and is
  not part of the test suite.

---

## Disclaimer

This software is provided for research and educational purposes. Nothing in
this repository is financial advice, and nothing here guarantees or implies
profitability. Cryptocurrency trading involves substantial risk of loss.
Any performance data in this repository is a historical simulation produced
by the research pipeline — not live trading results, and not indicative of
future returns. Use at your own risk.

---

## Installation

```bash
# Python >= 3.12
git clone https://github.com/Quantitative-Systems/crypto-platform.git
cd crypto-platform
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt        # numpy, pandas, pytest

# Run the research pipeline
PYTHONPATH=. python3 -m qcp_platform.cli screen        # cost economics per horizon
PYTHONPATH=. python3 -m qcp_platform.cli sweep         # full walk-forward sweep + gates
PYTHONPATH=. python3 -m qcp_platform.cli improve       # champion/challenger pass
PYTHONPATH=. python3 -m qcp_platform.cli paper         # governed paper simulation
PYTHONPATH=. python3 -m qcp_platform.cli status        # current platform beliefs

# Tests
python3 -m pytest tests -q
```

`market_data/cache/` holds the local Binance kline/funding archives used by
the pipeline (excluded from git; regenerate with the tools in
`market_data/`). Artifacts land in `research/results/qcp_platform/`.

---

## License

[MIT](LICENSE)
