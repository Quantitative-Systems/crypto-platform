# QCP — Quantitative Crypto Platform

[![Tests](https://img.shields.io/badge/governance%20tests-passing-green)](#running)
[![Live Capital](https://img.shields.io/badge/live%20capital-%240.00-red)]
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

> **One deployable platform. Every trading style. Costs included, always.
> Refusal is a valid output.**

QCP is a single, cost-aware, self-improving trading platform covering all
styles — scalping, intraday, swing, position, investing and market-neutral
carry — across 10 assets. It measures every strategy family honestly
(walk-forward, out-of-sample never tuned, full fee/slippage/spread modelling),
promotes only what survives 7 governance gates **to paper trading**, and
automatically archives failed experiments in `research/failed/`.

**No live capital is deployed. Promotion = paper only, by design.**

---

## What is where

| Path | Purpose |
|---|---|
| `qcp_platform/` | **The deployable platform** — 13 modules, one command sweep |
| `market_data/` | Binance cache + data quality pipeline |
| `config/` | Asset universe + timeframe sets |
| `research/results/qcp_platform/` | Measured results: REPORT.md, verdicts, economic screen |
| `research/failed/` | All superseded/failed strategy attempts and their tests (kept for the record, not for use) |
| `tests/` | Governance + data-layer tests for the deployable platform only |

### The platform in one minute

- **6 horizon books** from one risk governor: SCALP, INTRADAY, SWING,
  POSITION, INVEST, CARRY (funding harvest, market-neutral).
- **10 assets**, one causal engine: next-bar-open fills, adverse-first stops,
  full costs on every trade, R-multiple accounting.
- **7 governance gates**: data sufficiency, dev/val/oos consistency,
  statistics, cost-shock survival (+50%), walk-forward efficiency,
  sign stability, and portfolio marginal contribution (G7).
- **Self-improving**: `cli.py improve` re-runs champion/challenger sweeps on
  new data; a challenger replaces the baseline only if it beats it
  out-of-sample.
- **Anti-blowup**: vol targeting, drawdown tiers (10%/20%/25%), daily/weekly
  loss limits, kill switch — `qcp_platform/governor.py`.

## Running

```bash
PYTHONPATH=. python3 -m qcp_platform.cli sweep     # full measure + verdicts (~2.5 min)
PYTHONPATH=. python3 -m qcp_platform.cli improve   # champion/challenger self-improvement
PYTHONPATH=. python3 -m qcp_platform.cli report    # regenerate REPORT.md
PYTHONPATH=. python3 -m pytest tests -q            # governance + data tests
```

Results land in `research/results/qcp_platform/` (verdicts.json, REPORT.md,
economic_screen.json, baseline.json).

## Honest status

- 113 strategy books measured across all styles/assets with full costs.
- Governed out-of-sample portfolio: **+5.06% return, 2.13% max drawdown**.
- Most single-asset books decay out-of-sample; the platform reports that
  rather than hiding it. Scalping is flagged **cost-impossible** with taker
  fills (costs > stop distance) and is only permitted in maker mode.
- **Live trading: disabled.** Promotion means paper-trading eligibility, and
  forward burn-in is required before any live consideration.

## Why `research/failed/` exists

Every prior attempt that failed validation is preserved verbatim — code,
tests, results — because negative results are the reason the current platform
looks the way it does. They are not installed, not imported by the platform,
and not part of the test suite.
