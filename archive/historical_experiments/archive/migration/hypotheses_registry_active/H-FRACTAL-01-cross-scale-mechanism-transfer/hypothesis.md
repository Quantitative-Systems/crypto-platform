# Hypothesis ID: H-FRACTAL-01

## Title
Cross-Scale Mechanism Transfer

## Status
FORMALIZED

## Date Created
2026-09-19

## Owner
QCP Research

---

## Origin / Observation

Financial markets exhibit multi-scale structure. Price-action geometry, momentum behavior,
trend behavior, volatility behavior, and indicator-derived structures have been observed to
recur at different temporal resolutions. This multi-scale organization is sometimes described
using the concept of fractal or self-similar market structure.

The canonical QCP research program has established development-partition evidence of certain
mechanism families at specific temporal scales. A standing open question is whether a mechanism
that shows measurable behavior at one scale retains meaningful behavior when applied — without
modification — to a different temporal scale or a related asset.

This question cannot be answered by assumption. It must be answered empirically.

## Research Question

If a trading mechanism produces evidence of positive economic expectancy at one timeframe scale,
does the same underlying mechanism retain measurable and economically meaningful behavior when
applied to other timeframe scales and/or related assets?

## Hypothesis Statement

We hypothesize that a valid market mechanism may exhibit partial or meaningful transfer across
timeframe scales and assets, but that transferability must be demonstrated empirically and cannot
be assumed from the existence of fractal or multi-scale market structure.

The degree of transfer — if any — is an empirical question. The research must remain open to:
- strong cross-scale transfer
- partial cross-scale transfer (e.g. adjacent scales only)
- asset-specific transfer (mechanism works across assets but not across all scales)
- timeframe-specific behavior (mechanism works only at one or few scales)
- regime-specific behavior
- complete absence of transfer
- invalidation of the original apparent edge

## Null Hypothesis

Performance of a mechanism at one timeframe scale provides no reliable evidence that the same
mechanism will produce positive economic expectancy at another timeframe scale or asset.

Formally: the cross-scale performance correlation is not statistically distinguishable from
zero when evaluated across the pre-registered Development partition with the pre-registered
metrics and falsification thresholds.

## Falsification Criteria

**Pre-registered. Must not be modified after Development testing begins.**

The following outcomes would SUPPORT the null hypothesis (and therefore REJECT H-FRACTAL-01
in its generalized form):

- A mechanism that shows Development-partition evidence at one timeframe scale shows
  no positive expectancy (net expectancy ≤ 0.0R) at ANY other tested scale.
- Performance at SET_N does not predict performance at SET_N±1 above random chance.
- After fees and slippage, no timeframe set combination produces profit factor > 1.0
  across the pre-registered asset universe.

However, H-FRACTAL-01 is designed to permit ALL of the following as valid research outcomes
(none of which "falsifies" the research program — they merely classify the finding):

**A. STRONG_TRANSFER** — Mechanism survives across multiple scales and assets.
**B. PARTIAL_TRANSFER** — Mechanism survives only across adjacent scales.
**C. ASSET_TRANSFER** — Mechanism transfers across assets but not all scales.
**D. SCALE_SPECIFIC** — Mechanism works only at one or a small number of scales.
**E. ASSET_SPECIFIC** — Mechanism works only for particular assets.
**F. REGIME_SPECIFIC** — Mechanism works only under certain market regimes.
**G. NO_TRANSFER** — Mechanism fails outside the original research environment.
**H. INVALIDATED** — The apparent original edge disappears after corrected execution
   semantics, costs, causality, or other research corrections.

All eight outcomes are valid, complete, and reportable research outcomes.

The hypothesis is **rejected** only if the research process itself is abandoned or if
outcome H (INVALIDATED) is confirmed and there is no residual measurable effect anywhere.

---

## Supporting Evidence

- QCP Phase C/D research has demonstrated mechanism families with structured behavior
  at SET_3 (1D/4H/1H) and SET_4 (4H/1H/15m) scales.
- The existence of six canonical timeframe sets (SET_1..SET_6) in the QCP research
  infrastructure suggests the platform was designed to investigate multi-scale behavior.
- Forensic analysis of the canonical control (`HTF_TREND_CONTINUATION_V1`) showed that
  mechanism failures had characteristic signatures that may be scale-dependent.

_No Development-partition results are cited here because none exist yet for H-FRACTAL-01._

## Counter-Evidence

- Market microstructure differs substantially across scales. Mechanisms that exploit
  structural price-action at the daily scale may encounter pure noise at the 1-minute scale.
- Fee and slippage as a fraction of expected return scale adversely at lower timeframes:
  a mechanism viable at SET_1 may be fee-dominated at SET_6.
- Liquidity depth and participant composition differ across scales, which may break
  mechanisms that depend on specific order-flow dynamics.
- The canonical control (`HTF_TREND_CONTINUATION_V1`, -0.5998R expectancy, PF 0.38) shows
  that even the foundational trend-continuation mechanism does not universally work.

---

## Mechanism

The proposed mechanism family is: any mechanism that relies on directional structure
(trend, momentum, breakout, pullback, mean reversion, reversal, volatility expansion/contraction,
time-series momentum, channel/range, or structural price-action).

The core question is not which specific mechanism but whether **mechanism families** exhibit
transfer across scale. The research factory must support:
- trend
- momentum
- breakout
- pullback
- mean reversion
- reversal
- volatility expansion
- volatility contraction
- time-series momentum
- channel/range mechanisms
- structural price-action mechanisms

Do not treat internet strategy names as equivalent to mechanisms. Mechanisms are defined by
their economic rationale (e.g. trend-following monetizes autocorrelation of returns),
not by their indicator implementation.

## Expected Behavior

**If H-FRACTAL-01 result = STRONG_TRANSFER:**
- Performance matrix shows positive expectancy across SET_1..SET_6 for at least one mechanism family.
- Cross-scale correlation of expectancy is statistically positive.

**If H-FRACTAL-01 result = PARTIAL_TRANSFER:**
- Mechanism works at SET_2, SET_3, SET_4 but not SET_1 or SET_5/SET_6.
- Cross-scale performance degrades monotonically with scale distance.

**If H-FRACTAL-01 result = NO_TRANSFER:**
- Only the scale at which the mechanism was originally observed shows positive expectancy.
- All other scales produce net negative expectancy after fees.

**If H-FRACTAL-01 result = INVALIDATED:**
- After applying correct causality, fees, slippage, and collision semantics, even the
  original scale produces negative expectancy.

---

## Required Data

### Timeframe Sets
All six canonical QCP timeframe sets are in scope, referenced by ID:
- SET_1: 1M / 1W / 1D
- SET_2: 1W / 1D / 4H
- SET_3: 1D / 4H / 1H
- SET_4: 4H / 1H / 15m
- SET_5: 1H / 15m / 5m
- SET_6: 15m / 5m / 1m

**Important**: Set labels (e.g. "Macro Investing", "Micro Scalping") are informational metadata
in `research/timeframe_sets.py`. They are NOT research conclusions.
- SET_1 is NOT assumed to be "investing" in any meaningful or economically distinct sense.
- SET_6 is NOT assumed to be "scalping" in any meaningful or economically distinct sense.
The sets represent temporal scales. The research must discover which mechanisms work at each scale.

### Asset Universe
Initial: 5 assets (configurable — do not hard-code).
Extensible to 10 assets, then larger universes subject to data quality.
Asset list is specified in the experiment plan, not in this hypothesis document.

### Bar Horizon
Support all normalized holding horizons:
- 1–3 bars
- 4–10 bars
- 11–30 bars
- 31–100 bars

Exact horizon is configurable per experiment run.
Do not relabel a 3-month position on monthly candles as "scalping" merely because it uses 3 bars.

---

## Partitions

### Development Partition
- Period: 2021-01-01 to 2022-12-31
- Role: Hypothesis refinement and mechanism exploration
- Status: ASSIGNED (not yet accessed for H-FRACTAL-01 testing)

### Validation Partition
- Period: 2023-01-01 to 2023-12-31
- Role: FROZEN — Institutional validation gate
- Status: NOT_STARTED — Do NOT access until VALIDATION stage is formally authorized.

### OOS Partition
- Period: 2024-01-01 to 2026-06-30
- Role: UNTOUCHED — Blind out-of-sample quarantine
- Status: UNTOUCHED — Do NOT access under any circumstances before QUALIFIED status.

---

## Execution Assumptions

### Fees
To be specified in experiment plan. Must cover round-trip at each timeframe set.
Fee model must be conservative (taker rates unless maker execution is verified).

### Slippage
To be specified in experiment plan. Must scale appropriately with timeframe set.

### Collision Semantics
To be specified in experiment plan. Same-asset collision handling must be explicit.

### Re-entry Semantics
To be specified in experiment plan. Re-entry after stop-out conditions must be explicit.

---

## Risk Assumptions
- Risk per trade: 1% fixed fractional (default QCP standard)
- Maximum concurrent exposure: per QCP risk firewall (not overridden by this hypothesis)
- Risk model version: QCP canonical (research.risk_engine)
- No regime-conditional risk scaling unless explicitly justified

---

## Experimental Design

### EXPERIMENT A — Cross-Scale Mechanism Transfer (THIS DOCUMENT)

**Question**: Does the same mechanism survive across temporal scales?

**Design**: Sweep mechanism family × timeframe set × asset × bar horizon across the
Development partition. Measure performance independently per cell. Assess cross-scale
performance correlation.

**This experiment does NOT ask**: "Does combining HTF + MTF + LTF information improve returns?"
That is Experiment B (H-FRACTAL-02 placeholder).

### EXPERIMENT B — Multi-Timeframe Confirmation (PLACEHOLDER — NOT IMPLEMENTED)

**Question**: Does combining HTF + MTF + LTF information from *different scales* produce
incremental economic value beyond using a single-scale mechanism?

**Status**: Placeholder only. Will be registered as a separate hypothesis (H-FRACTAL-02
or equivalent) in a future research command.

**Do NOT conflate Experiment A and Experiment B. They test different causal structures.**

### Controls
- Risk model: constant (1% fixed fractional)
- Fee model: constant (pre-specified in experiment plan)
- Slippage model: constant (pre-specified in experiment plan)
- Data partition: Development only (2021–2022)
- Causality: zero lookahead enforced
- Execution semantics: QCP canonical replayer

### Independent Variables (Axes)

**Axis A — Timeframe Set**: SET_1, SET_2, SET_3, SET_4, SET_5, SET_6
**Axis B — Asset**: Configurable (initial: 5 assets)
**Axis C — Mechanism Family**: All mechanism families listed in the Mechanism section
**Axis D — Bar Horizon**: 1–3, 4–10, 11–30, 31–100 bars

### Dependent Variables
Performance measured per (mechanism × timeframe set × asset × bar horizon) cell.

---

## Metrics

**Required — do not rank by win rate alone:**

- `trade_count` — must meet minimum per cell before interpreting results
- `gross_r` — gross R before friction
- `net_r` — net R after all friction
- `expectancy_r` — net R / trade count
- `profit_factor` — gross winners / gross losers
- `win_rate_pct`
- `max_drawdown_r` — maximum drawdown in R units
- `avg_trade_r` — average trade outcome in R
- `exposure_pct` — proportion of time with open positions
- `fees_r` — total fee drag in R
- `slippage_r` — total slippage drag in R
- `turnover` — number of round-trips per unit time
- `outcome_concentration` — % of total R from top-N trades (concentration risk)
- `performance_by_asset` — per-asset breakdown
- `performance_by_timeframe_set` — per-set breakdown
- `performance_by_period` — sub-period breakdown within Development partition
- `performance_by_regime` — where regime data available (QCP regime engine)

---

## Confounders
- Insufficient trade count per cell (must flag cells below minimum sample size)
- Survivorship bias in asset universe selection
- Regime overlap between sub-periods of Development partition
- Fee model error (verify taker/maker assumptions)
- Structural breaks between 2021 and 2022 (bull → bear transition)
- Lookahead contamination (must be audited per the QCP causality enforcement standard)
- Correlation between assets (reduces effective sample size)

## Known Risks
- Strong Development-partition transfer finding that fails in the Validation partition
  due to regime shift or data snooping across cells.
- Cell count proliferation (6 sets × N assets × M mechanisms × 4 horizons) creating
  multiple hypothesis testing problem — must apply Bonferroni or equivalent correction.
- Fee dominance at SET_5 and SET_6: mechanisms that appear viable at SET_3 may be
  fee-dominated at higher-frequency sets.

---

## Implementation Requirements
- `run_hypothesis_factory.py` or equivalent research runner supporting all four axes
- Configurable asset universe (not hard-coded)
- Configurable bar horizon
- Per-cell metrics capture
- Cross-scale correlation analysis
- Results stored in `research/lifecycle/experiment_ledger.py` with hypothesis_id = "H-FRACTAL-01"

---

## Reproducibility Information

### Repository Commit
*To be recorded at time of first experiment run.*

### Experiment IDs
*None yet — testing has not begun.*

### Data Version
*To be recorded at time of first experiment run.*

### Configuration Hash
*To be recorded at time of first experiment run.*

### Random Seed
Not applicable to deterministic replayer. Record if any stochastic component is introduced.

---

## Results
*Not yet available. Testing has not begun. This section must not be filled speculatively.*

## Interpretation
*Not yet available.*

## Decision
*Not yet available.*

---

## Related Experiments
*(None yet — to be linked when experiments are registered in the experiment ledger.)*

## Related Hypotheses
- **H-FRACTAL-02** (placeholder): Multi-timeframe confirmation — Experiment B.
  "Does combining HTF + MTF + LTF information produce incremental economic value?"
  This is a separate research question from H-FRACTAL-01 and must not be combined with it.

---

## Changelog

| Date (UTC) | State | Change | Author |
|---|---|---|---|
| 2026-09-19 | FORMALIZED | Initial registration — hypothesis documented, experimental axes defined, no testing begun | QCP Research |
