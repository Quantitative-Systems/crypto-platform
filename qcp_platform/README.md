# QCP Platform — All-Horizon, Cost-Aware, Self-Improving Trading System

One platform, six books (scalping → investing + market-neutral carry), 10
assets, every verdict produced by the same walk-forward, cost-included,
out-of-sample-untouched pipeline. **Nothing here is tradable with real money:
promotion means "paper-trade next", never "wire funds".**

## Commands

```bash
PYTHONPATH=. python3 -m qcp_platform.cli screen    # cost economics per horizon
PYTHONPATH=. python3 -m qcp_platform.cli sweep     # full walk-forward + G7 portfolio
PYTHONPATH=. python3 -m qcp_platform.cli report    # rebuild report from sweep.json
PYTHONPATH=. python3 -m qcp_platform.cli improve   # champion/challenger pass
PYTHONPATH=. python3 -m qcp_platform.cli paper     # governed paper simulation
PYTHONPATH=. python3 -m qcp_platform.cli status    # current platform beliefs
```

## Architecture

| Module | Role |
|---|---|
| `costs.py` | Single source of truth for fees/slippage/spread/basis. Cost-to-stop arithmetic decides what is even attemptable. |
| `horizons.py` | The six books: SCALP, INTRADAY, SWING, POSITION, INVEST, CARRY — each with its own clock, stop width, risk budget and maker/taker mode. |
| `indicators.py` | Vectorized causal indicators (EMA/RMA/ATR/RSI/ADX/Donchian/vol/efficiency). |
| `data.py` | Local-cache OHLCV/funding loaders, causal HTF alignment, merged cross-asset panels. |
| `regimes.py` | Trend/range/stress classification + cross-asset breadth. |
| `strategies.py` | Directional families: breakout, pullback rider, mean reversion, grid-range, micro-scalp. |
| `allocations.py` | Rotation (cross-sectional momentum), DCA accumulation, pairs, funding carry. |
| `engine.py` | THE trade resolver: next-open fills, adverse-first SL/TP ties, costs both sides, R accounting. |
| `walkforward.py` | 60/20/20 DEV/VAL/OOS splits, per-window slices. |
| `evaluate.py` | Gate chain G1–G6 per book + G7 portfolio marginal-contribution upgrade. |
| `runner.py` | Sweep orchestration across every (horizon, family, asset). |
| `portfolio.py` | Governed portfolio simulation: vol targeting, DD tiers, daily/weekly loss caps, exposure caps. |
| `governor.py` | The risk governor — scaling/blocking rules, kill switch. |
| `improve.py` | Baseline beliefs + challenger promotion (VAL must confirm, OOS sign must agree). |
| `report.py` | Honest markdown/JSON reporting, rejections included. |

## Non-negotiable rules

1. **Causality** — every decision at bar *i* uses only bars that closed at or
   before bar *i*'s close. HTF context enters exclusively through
   `data.align_causal`.
2. **Costs always on** — taker/maker fee + slippage + half-spread both sides;
   carry pays 4 fills + explicit basis.
3. **OOS is never tuned** — parameters are selected on DEV, confirmed on VAL,
   reported on OOS; the +50% cost shock runs on OOS.
4. **Refusal is a valid output** — a horizon whose stop can't pay its roundtrip
   cost is flagged NOT_ECONOMIC (today: SCALP) instead of being force-fit.
5. **Risk is governed, not requested** — 0.5x/1.0x/1.5x vol scaling, DD tiers
   at 10/20/25%, 3% daily / 7% weekly loss caps, 8-loss cooldown, per-symbol
   and per-horizon exposure caps, hard kill switch.

## Verdicts

`REJECTED_DATA / REJECTED_G1..G7 / MEASURED / PROMOTABLE_PAPER_ONLY`.

A book is promoted only if it passes data sufficiency, positive DEV *and* OOS
expectancy, minimum trade count, DEV→OOS decay bound, the +50% cost shock, and
adds marginal Sharpe to the governed portfolio. Everything else is reported
with its rejection reason — rejections are findings, not failures.

## Tests

```bash
PYTHONPATH=. python3 -m pytest tests/unit/research/test_qcp_platform_governance.py -q
```

18 tests pin the invariants: causal HTF alignment, next-open entries,
adverse-first resolution, always-on costs, horizon economics, governor tiers,
funding-carry neutrality, rotation without look-ahead.
