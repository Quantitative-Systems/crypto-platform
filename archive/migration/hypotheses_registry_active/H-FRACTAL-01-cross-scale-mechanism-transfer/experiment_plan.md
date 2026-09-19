# H-FRACTAL-01 Experiment Plan — Cross-Scale Mechanism Transfer

**Hypothesis ID**: H-FRACTAL-01
**Experiment**: A — Cross-Scale Mechanism Transfer
**Status**: IMPLEMENTATION_READY (pending)
**Date Created**: 2026-09-19

---

## Separation from Experiment B

This document covers **Experiment A** only.

**Experiment A (this document)**: Does the same mechanism survive across temporal scales?

**Experiment B (not implemented)**: Does combining HTF + MTF + LTF information from different
scales produce incremental economic value? This will be registered separately as H-FRACTAL-02
or equivalent. Do not combine the two experiments.

---

## Research Axes

### AXIS A — Timeframe Set

All six QCP canonical timeframe sets are in scope:

| Set | Frames (HTF / MTF / LTF) |
|---|---|
| SET_1 | 1M / 1W / 1D |
| SET_2 | 1W / 1D / 4H |
| SET_3 | 1D / 4H / 1H |
| SET_4 | 4H / 1H / 15m |
| SET_5 | 1H / 15m / 5m |
| SET_6 | 15m / 5m / 1m |

**Important note**: The names "Macro Investing", "Swing Trading", etc. from `research/timeframe_sets.py`
are informational metadata that describe typical holding durations. They are NOT research classifications
and must not be used to pre-determine which mechanism families to apply to which sets.
The research must remain agnostic about which mechanisms are appropriate at which scales.

### AXIS B — Asset

Initial universe: **5 assets** (configurable — exact list specified at experiment execution time).

Expandable to:
- 10 assets (if data quality passes certification)
- Larger universes (subject to governance approval)

Do not hard-code asset lists into the experiment runner. Use a configurable asset registry.

Candidate initial universe (not binding — to be confirmed at execution time):
- BTC/USDT, ETH/USDT, SOL/USDT, BNB/USDT, XRP/USDT

### AXIS C — Mechanism Family

The experiment runner must support (at minimum) the following mechanism families:

| Family | Economic Rationale |
|---|---|
| `trend` | Monetizes autocorrelation of directional price movement |
| `momentum` | Monetizes persistence of returns over a lookback window |
| `breakout` | Monetizes expansion from consolidation/range |
| `pullback` | Monetizes continuation after counter-trend retrace |
| `mean_reversion` | Monetizes mean-reversion after extreme extension |
| `reversal` | Monetizes structural directional change signals |
| `volatility_expansion` | Monetizes post-compression expansion in range |
| `volatility_contraction` | Monetizes decay of volatility toward mean |
| `time_series_momentum` | Monetizes sign persistence in rolling return series |
| `channel_range` | Monetizes bounded oscillation within established range |
| `structural_price_action` | Monetizes recognized structural price-action configurations |

Do not treat internet strategy names as mechanism names. Each mechanism must be defined
by its economic rationale.

### AXIS D — Bar Horizon

| Horizon | Description |
|---|---|
| `H1` | 1–3 bars |
| `H2` | 4–10 bars |
| `H3` | 11–30 bars |
| `H4` | 31–100 bars |

Do not assign trading-style names to horizons based on absolute calendar duration alone.
A 3-bar position on monthly candles spans approximately 3 months, which is not "scalping".

---

## Data Partition

**Development only.** Validation and OOS partitions must not be accessed.

- Period: 2021-01-01 to 2022-12-31
- Partition boundary: enforced by the QCP temporal partitioner (`research/experiments/temporal_partitioner.py`)

---

## Controls (Fixed Across All Cells)

| Parameter | Value |
|---|---|
| Risk per trade | 1% fixed fractional |
| Fee model | Conservative (taker rates unless maker verified) |
| Slippage model | Pre-specified in runner config |
| Causality | Zero lookahead (QCP replayer standard) |
| Collision semantics | Pre-specified in runner config |
| Re-entry semantics | Pre-specified in runner config |

---

## Required Metrics Per Cell

Each (mechanism × timeframe set × asset × bar horizon) cell must record:

```
trade_count
gross_r
net_r
expectancy_r
profit_factor
win_rate_pct
max_drawdown_r
avg_trade_r
exposure_pct
fees_r
slippage_r
turnover
outcome_concentration  # % of R from top-3 trades
```

Additionally, aggregate cross-cell analysis:
```
cross_scale_expectancy_correlation  # Pearson correlation of expectancy across sets
cross_asset_expectancy_correlation  # Pearson correlation of expectancy across assets
regime_conditional_breakdown        # Where regime data available
```

---

## Reproducibility Requirements

Every experiment run must record:

```yaml
hypothesis_id: H-FRACTAL-01
experiment_id: <assigned at run time>
repository_commit: <git rev-parse HEAD>
data_version: <data manifest hash>
data_partition: development_2021_2022
asset_universe: <exact list>
timeframe_sets: [SET_1, SET_2, SET_3, SET_4, SET_5, SET_6]
bar_horizon: <exact value>
fees_model: <version>
slippage_model: <version>
collision_semantics: <exact policy>
re_entry_semantics: <exact policy>
risk_model: <version>
random_seed: null  # deterministic replayer
configuration_hash: <hash of full config dict>
```

Results must be registered in `research/lifecycle/experiment_ledger.py` with
`hypothesis_id = "H-FRACTAL-01"` and linked in `hypotheses/registry.yaml` under
`H-FRACTAL-01.related_experiments`.

---

## Multiple Hypothesis Testing

The full experiment matrix has a very large number of cells:
6 sets × N assets × M mechanisms × 4 horizons

This creates a multiple-testing problem. Before interpreting any cell result as significant:

1. Apply Bonferroni correction: α_per_cell = 0.05 / total_cells_tested
2. Or use Benjamini-Hochberg FDR correction for the full matrix
3. Flag cells with trade count below minimum threshold as UNDERPOWERED (not interpretable)
4. Report the full matrix — do not select favorable cells post-hoc

The `research/experiments/hypothesis_registry.py` `get_multiple_testing_penalty()` method
tracks the Bonferroni trial multiplier. Use it.

---

## Minimum Sample Requirements

| Timeframe Set | Minimum Trades Per Cell |
|---|---|
| SET_1 | 15 |
| SET_2 | 20 |
| SET_3 | 20 |
| SET_4 | 30 |
| SET_5 | 40 |
| SET_6 | 60 |

Cells with trade count below minimum are UNDERPOWERED. Report them but mark as
`sample_status: INSUFFICIENT`. Do not use underpowered cells to support conclusions.

---

## Decision Criteria

After Development results are complete:

| Outcome | Condition |
|---|---|
| STRONG_TRANSFER | ≥4 of 6 sets positive expectancy, ≥3 mechanism families, cross-scale correlation > 0.5 |
| PARTIAL_TRANSFER | ≥3 adjacent sets positive, ≥1 mechanism family |
| ASSET_TRANSFER | ≥3 assets positive but <3 sets; mechanism family specific |
| SCALE_SPECIFIC | 1–2 sets positive; fails to generalize |
| ASSET_SPECIFIC | Individual assets show positive but aggregate does not |
| REGIME_SPECIFIC | Positive conditional on regime classification |
| NO_TRANSFER | No cell positive after fee/slippage correction at the required significance level |
| INVALIDATED | Original apparent edge disappears under corrected execution semantics |

**None of these outcomes trigger Validation-partition access automatically.**
Validation requires separate governance authorization.

---

## Experiment B Placeholder

When the research program is ready to address multi-timeframe confirmation, the following
new hypothesis will be registered:

**H-FRACTAL-02** (not yet implemented):
> "Does the inclusion of information from a higher timeframe scale, combined with a
> lower timeframe mechanism signal, produce statistically significant incremental economic
> value relative to using the mechanism signal at the lower timeframe alone?"

This is a fundamentally different causal question from H-FRACTAL-01 and requires its own
experimental design, null hypothesis, and falsification criteria.

---

## Pre-Execution Checklist

Before beginning Development testing:

- [ ] Exact asset universe confirmed and logged
- [ ] Fee model version confirmed
- [ ] Slippage model version confirmed
- [ ] Collision and re-entry semantics confirmed
- [ ] Configuration hash computed and stored
- [ ] Repository commit recorded
- [ ] Data manifest version confirmed
- [ ] Causality audit completed on mechanism implementations
- [ ] Experiment ID assigned and registered in experiment_ledger
- [ ] H-FRACTAL-01 status.yaml updated to DEVELOPMENT_TEST
- [ ] hypothesis_governance.py validates H-FRACTAL-01 at DEVELOPMENT_TEST state

---

*This document is part of the H-FRACTAL-01 hypothesis directory.*
*Status: IMPLEMENTATION_READY (pending execution authorization)*
*Last updated: 2026-09-19*
