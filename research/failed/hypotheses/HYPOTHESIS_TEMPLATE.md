# Hypothesis ID: [FILL: H-FAMILY-NN]

## Title
<!-- One sentence describing the mechanism under investigation -->

## Status
<!-- PROPOSED | FORMALIZED | IMPLEMENTATION_READY | DEVELOPMENT_TEST | FORENSIC_REVIEW | VALIDATION_CANDIDATE | VALIDATION | OOS | QUALIFIED | REJECTED | INVALIDATED | ARCHIVED -->

## Date Created
<!-- YYYY-MM-DD (UTC) -->

## Owner
<!-- Researcher or team responsible -->

---

## Origin / Observation
<!-- What was observed in the data, forensic analysis, or literature that motivated this hypothesis?
     Be specific. Reference experiment IDs, data periods, assets, and timeframe sets where applicable. -->

## Research Question
<!-- The precise empirical question being investigated.
     Must be answerable with data. Must not assume the answer. -->

## Hypothesis Statement
<!-- The affirmative claim: "We hypothesize that [mechanism X] produces [measurable effect Y]
     under conditions [Z], as measured by [metric M]." -->

## Null Hypothesis
<!-- The default assumption to be overturned.
     Example: "The mechanism produces no reliable positive economic expectancy
     that distinguishes it from noise at the tested temporal scales and assets." -->

## Falsification Criteria
<!-- PRE-REGISTER these before any testing begins. Do not modify after testing starts.
     What results would definitively REJECT this hypothesis?
     Be specific: metric names, threshold values, sample size requirements.

     Example:
     - Net expectancy < 0.0R across all timeframe sets in Development partition
     - Win rate < 25% with fewer than 30 trades per timeframe set
     - Performance degrades monotonically vs. random entry baseline
     
     ⚠️ A hypothesis with no falsification criterion is not a hypothesis. -->

---

## Supporting Evidence
<!-- Evidence that motivated the hypothesis BEFORE testing.
     Do not add post-hoc evidence here. Reference experiment IDs and dates. -->

## Counter-Evidence
<!-- Known evidence that argues against the hypothesis.
     Must be documented honestly before testing begins. -->

---

## Mechanism
<!-- The proposed market mechanism. Why would this produce positive expectancy?
     Describe in terms of: order flow, participant behavior, structural asymmetry,
     information asymmetry, or market microstructure. 
     Do NOT describe in terms of indicator patterns alone. -->

## Expected Behavior
<!-- Concrete predictions: what would the performance matrix look like if the hypothesis is TRUE?
     What would it look like if FALSE? What would PARTIAL support look like? -->

---

## Required Data

### Timeframe Sets
<!-- Which SET_1..SET_6 are in scope? Or ALL? -->
<!-- Do NOT assign fixed trading-style interpretations to sets. -->

### Asset Universe
<!-- Which assets? Start small (5), scale to larger universes if data quality permits.
     Do not hard-code a fixed list. -->

### Bar Horizon
<!-- Normalized holding horizons: 1-3 bars | 4-10 bars | 11-30 bars | 31-100 bars -->

---

## Partitions

### Development Partition
<!-- Date range. Assets. Purpose: hypothesis refinement only. -->

### Validation Partition
<!-- Date range. FROZEN. Do not touch until Validation stage is formally authorized. -->

### OOS Partition
<!-- Date range. UNTOUCHED. Reserved for final blind evaluation only. -->

---

## Execution Assumptions

### Fees
<!-- Exact fee model: maker/taker rates, round-trip cost in R at typical position sizes -->

### Slippage
<!-- Slippage model: none / fixed / ATR-proportional / market-impact model -->

### Collision Semantics
<!-- How concurrent signals in same asset/direction are handled -->

### Re-entry Semantics
<!-- Whether re-entry after stop-out is permitted and under what conditions -->

---

## Risk Assumptions
<!-- Risk per trade (e.g. 1% fixed fractional).
     Maximum concurrent exposure.
     Any regime-conditional risk adjustments.
     Risk model version. -->

---

## Experimental Design

### Controls
<!-- What is held constant across all test conditions?
     E.g., risk model, fee model, data partition, execution semantics -->

### Independent Variables
<!-- Axes being varied:
     - Axis A: Timeframe Set (SET_1..SET_6)
     - Axis B: Asset
     - Axis C: Mechanism variant
     - Axis D: Bar horizon -->

### Dependent Variables
<!-- What is being measured.
     Must include at minimum: net expectancy R, profit factor, win rate, trade count -->

---

## Metrics

<!-- Required metrics — do not rank by win rate alone:
- trade_count
- gross_r
- net_r
- expectancy_r
- profit_factor
- win_rate_pct
- max_drawdown_r
- avg_trade_r
- exposure_pct
- fees_r
- slippage_r
- turnover
- outcome_concentration  (e.g. % of R from top N trades)
- performance_by_asset
- performance_by_timeframe_set
- performance_by_period
- performance_by_regime (where regime data available) -->

---

## Confounders
<!-- Known factors that could contaminate the result:
     - Survivorship bias
     - Look-ahead in data
     - Regime overlap between partitions
     - Insufficient trade count per cell
     - Structural breaks in the data
     - Fee/slippage model errors -->

## Known Risks
<!-- What could go wrong with this research program?
     What would cause a false positive that passes Development but fails OOS? -->

---

## Implementation Requirements
<!-- What code changes or new components are required to test this hypothesis?
     Reference existing modules where possible. Note any new data requirements. -->

---

## Reproducibility Information

### Repository Commit
<!-- Git commit hash at time of experiment run -->

### Experiment IDs
<!-- List of all experiment IDs linked to this hypothesis -->

### Data Version
<!-- Data manifest version or hash -->

### Configuration Hash
<!-- Hash of the configuration used for the experiment run -->

### Random Seed
<!-- If applicable -->

---

## Results
<!-- DO NOT FILL before testing.
     Record exact metrics from each experiment run.
     Never modify pre-registered falsification criteria after seeing results.
     Reference experiment IDs, not raw numbers from memory. -->

## Interpretation
<!-- After results are available: what do they mean?
     Which outcome class applies?
     A: Strong Transfer | B: Partial Transfer | C: Asset Transfer |
     D: Scale-Specific | E: Asset-Specific | F: Regime-Specific |
     G: No Transfer | H: Invalidated -->

## Decision
<!-- QUALIFIED | REJECTED | INVALIDATED | REQUIRES_FURTHER_RESEARCH
     Decision must follow directly from results vs. pre-registered falsification criteria.
     No discretionary overrides. -->

---

## Related Experiments
<!-- Experiment IDs from research/experiments/ or research/lifecycle/experiment_ledger.py -->

## Related Hypotheses
<!-- Other hypothesis IDs that are related, parent, or child hypotheses -->

---

## Changelog

| Date (UTC) | State | Change | Author |
|---|---|---|---|
| YYYY-MM-DD | PROPOSED | Initial registration | - |
