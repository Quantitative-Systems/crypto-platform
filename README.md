# Crypto Trading Platform

> **Professional systematic trading infrastructure** for cryptocurrency markets — from certified market data and strategy research through backtesting, validation, portfolio construction, risk management, paper trading, and exchange-connected execution.

[![Tests](https://img.shields.io/badge/tests-145%20passing-green)](#testing)
[![Live Capital](https://img.shields.io/badge/live%20capital-%240.00-red)]
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

> **This platform places no live orders and holds no funds. All strategies are research artifacts. Nothing here is a profitability claim.**

---

## Overview

This repository contains a modular, research-driven cryptocurrency trading platform with two complementary layers:

1. **`crypto_platform/` — the production-grade infrastructure layer** — market data websockets, strategy engines, portfolio allocation, risk engine, order management, exchange adapters, paper trading persistence, and observability.
2. **`qcp_platform/` — the research and validation layer** — walk-forward backtesting, G1–G7 governance gates, cost-shock analysis, portfolio construction, and paper-trading eligibility.

Every strategy candidate is measured through the same rigorous pipeline: certified market data, causal feature engineering, walk-forward backtesting with full fee/slippage/spread modeling, out-of-sample validation, cost-shock survival testing, and portfolio-level marginal-contribution gates. Only books that survive all governance gates are promoted to **paper trading**. Everything else is archived with its rejection reason.

**No live capital is deployed. Promotion means paper-trading eligibility only.**

---

## Current Capabilities

### Implemented (CURRENT)

| Area | Status | Where |
|---|---|---|
| Market data (Binance USDⓈ-M klines + funding, quality gates, websocket streaming) | Implemented | `market_data/`, `crypto_platform/market_data/` |
| Strategy research across 6 horizons / 10 assets | Implemented | `qcp_platform/strategies.py`, `allocations.py` |
| Strategy engine (momentum, trend, mean reversion, volatility, statistical arbitrage, funding carry, investing) | Implemented | `crypto_platform/strategy_engine/` |
| Walk-forward backtesting (60/20/20 DEV/VAL/OOS) | Implemented | `qcp_platform/walkforward.py`, `engine.py` |
| Validation, cost-shock and robustness gates (G1–G7) | Implemented | `qcp_platform/evaluate.py` |
| Portfolio construction + governed paper simulation | Implemented | `qcp_platform/portfolio.py`, `governor.py` |
| Risk engine (firewall, circuit breakers, kill switches, drawdown control) | Implemented | `crypto_platform/risk_engine/` |
| Order management (router, state machine, reconciliation) | Implemented | `crypto_platform/order_management/`, `reconciliation/` |
| Exchange adapters (Binance, Bybit, CCXT) | Implemented (paper/testnet oriented) | `crypto_platform/exchange_adapters/` |
| Paper trading (simulator, persistence, daemon, soak runner) | Implemented | `crypto_platform/paper_trading/` |
| Statistical arbitrage / relative-value discovery | Implemented | `crypto_platform/discovery/`, `research_engine/comparison_engine.py` |
| Funding carry parameter sweep + compression stress | Implemented | `qcp_platform/carry_sweep.py`, `crypto_platform/research_engine/carry_stress.py` |
| Champion/challenger self-improvement loop | Implemented | `qcp_platform/improve.py` |
| Reporting (markdown + JSON artifacts) | Implemented | `qcp_platform/report.py`, `crypto_platform/research_engine/` |
| Architecture blueprint (product → production) | Documented | `docs/` |
| Historical research archive | Preserved | `research/failed/` |

### Planned (PLANNED — not implemented)

Live order placement with real capital, multi-tenant user accounts, web dashboards, database-backed state beyond paper-trading persistence, and options/derivatives beyond perpetual funding. See the
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

---

## Architecture

The current research engine is a modular monolith of 13+ packages under
`qcp_platform/`, described in
[`qcp_platform/README.md`](qcp_platform/README.md):

```
costs → horizons → indicators → data → regimes → strategies → allocations
     → engine → walkforward → evaluate → runner → portfolio → governor
     → improve → report
```

The broader infrastructure layer under `crypto_platform/` extends this into a
complete trading stack:

```
market data (websocket) → strategy engine → portfolio engine
                    → risk engine → order management → exchange adapters
                    → paper trading (simulator + persistence + daemon)
                    → discovery (stat arb) → observability
```

The full product architecture — connectivity, research, portfolio, risk,
execution, operations, security, and the build-phase sequence — is specified
in [`docs/CRYPTO_TRADING_PLATFORM_ARCHITECTURE.md`](docs/CRYPTO_TRADING_PLATFORM_ARCHITECTURE.md).
It clearly distinguishes what is implemented today from what is planned.

---

## Repository Structure

| Path | Purpose |
|---|---|
| `crypto_platform/` | Production-grade trading infrastructure: strategy engine, risk engine, order management, exchange adapters, paper trading, market data websocket, discovery, observability |
| `qcp_platform/` | Research engine: walk-forward backtesting, G1–G7 governance gates, portfolio construction, paper-trading eligibility |
| `market_data/` | Binance kline/funding cache, ingestion, quality & lineage pipeline |
| `config/` | Asset universe and canonical timeframe sets |
| `research/results/qcp_platform/` | Current measured results: REPORT.md, verdicts, economic screen, baselines |
| `research/results/crypto_platform/` | Forward paper, soak test, carry stress, stat arb, and comparison results |
| `research/failed/` | Historical research archive — superseded and rejected work, preserved verbatim |
| `tests/` | Governance, data-quality, and infrastructure tests (145 tests) |
| `docs/` | Product architecture, operations, security, risk, and methodology documentation |

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

## CLI Reference

### `crypto_platform` — Primary Infrastructure Layer

```bash
python3 -m crypto_platform.cli screen      # pre-trade cost economics per horizon
python3 -m crypto_platform.cli sweep       # full walk-forward sweep + G1–G7 gates
python3 -m crypto_platform.cli report      # rebuild the markdown report
python3 -m crypto_platform.cli improve     # champion/challenger self-improvement pass
python3 -m crypto_platform.cli paper       # paper-trade the promoted book set
python3 -m crypto_platform.cli carry-stress # funding carry compression stress audit
python3 -m crypto_platform.cli forward-paper # controlled forward paper session (SQLite ledger)
python3 -m crypto_platform.cli compare     # backtest vs OOS vs forward paper comparison
python3 -m crypto_platform.cli soak        # websocket forward paper soak session
python3 -m crypto_platform.cli discover-arb # relative-value / stat arb discovery
python3 -m crypto_platform.cli status      # current platform status and promoted books
```

### `qcp_platform` — Legacy Research Layer

```bash
python3 -m qcp_platform.cli screen         # pre-trade cost economics per horizon
python3 -m qcp_platform.cli sweep          # full walk-forward sweep + gates
python3 -m qcp_platform.cli report         # rebuild the markdown report
python3 -m qcp_platform.cli improve        # champion/challenger pass
python3 -m qcp_platform.cli paper          # paper-trade the promoted set
python3 -m qcp_platform.cli status         # current platform beliefs
python3 -m qcp_platform.cli carry_sweep    # funding carry parameter sweep
```

Both CLIs write artifacts to `research/results/` so results are auditable and
reproducible. **No subcommand ever places a live order: this platform
promotes to PAPER only, deliberately.**

---

## Paper Trading

`python3 -m crypto_platform.cli paper` simulates the promoted book set through
the risk governor on the out-of-sample window: per-horizon capital weights,
volatility scaling, drawdown tiers (10%/20%/25%), daily/weekly loss caps,
consecutive-loss cooldown, and a hard kill switch. Every skipped trade is
logged with its reason. Paper fills are simulated with the same cost model
as backtests — they are not live fills.

For longer-running validation, `python3 -m crypto_platform.cli soak` runs a
public WebSocket forward-paper soak session with restart verification, while
`python3 -m crypto_platform.cli forward-paper` runs a controlled session backed
by a SQLite ledger.

---

## Exchange Connectivity

The first research venue is **Binance USDⓈ-M** (klines, funding rates).
Implemented adapters, behind a normalized exchange-neutral interface:

| Venue | Data | Execution | Priority |
|---|---|---|---|
| Binance USDⓈ-M | Implemented (cache + websocket) | Paper only | Current |
| Bybit | Implemented (adapter) | Paper only | Current |
| Generic CCXT adapter | Implemented (adapter) | Paper only | Current |

Planned venues and capabilities: OKX, Kraken, real-time multi-venue data, and
live execution semantics. Any venue whose API cannot support the platform's
execution semantics (next-bar-open, adverse-first stops, full cost accounting)
is excluded rather than approximated.

---

## Testing

```bash
python3 -m pytest tests -q
```

**145 tests** cover the data-quality/lineage pipeline, research engine
governance invariants, strategy engine behavior, risk boundaries, exchange
adapters, paper-trading persistence, websocket soak verification, market data,
statistical arbitrage discovery, and cross-layer reconciliation.

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
4. Expand the WebSocket soak and forward-paper verification suite.

Medium-term (product):

5. Exchange-connected paper broker adapter.
6. Real-time market data streaming across multiple venues.
7. Multi-venue data and execution adapters.
8. Database-backed state and operational tooling.

Long-term (planned, not started):

9. Live execution with governed capital and user controls.
10. Multi-broker, multi-tenant product layer.

The full sequence, including contingency planning, is defined in the
[architecture document](docs/CRYPTO_TRADING_PLATFORM_ARCHITECTURE.md).

---

## Limitations

- Single primary data venue (Binance USDⓈ-M); single cache.
- Results are historical simulations on cached data — subject to regime
  decay, cost drift, and every failure mode the gates test for.
- The research kernel is batch-oriented (CLI sweeps), not streaming.
- No user accounts, no API server, no frontend, no database-backed state
  beyond paper-trading persistence.
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
pip install -e ".[dev]"                # optional: editable + dev extras

# Run the research pipeline
PYTHONPATH=. python3 -m crypto_platform.cli screen
PYTHONPATH=. python3 -m crypto_platform.cli sweep
PYTHONPATH=. python3 -m crypto_platform.cli paper

# Run the legacy research layer
PYTHONPATH=. python3 -m qcp_platform.cli screen
PYTHONPATH=. python3 -m qcp_platform.cli sweep

# Tests
python3 -m pytest tests -q
```

`market_data/cache/` holds the local Binance kline/funding archives used by
the pipeline (excluded from git; regenerate with the tools in
`market_data/`). Artifacts land in `research/results/` — both under
`research/results/qcp_platform/` and `research/results/crypto_platform/`.

---

## License

[MIT](LICENSE)
