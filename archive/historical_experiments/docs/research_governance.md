# Scientific Research Governance & Experimentation Protocol

---

## 1. Foundational Governance Principles

The Quantitative Systems Platform operates under strict scientific research governance designed to eliminate confirmation bias, p-hacking, multiple-testing inflation, and lookahead leakage.

```
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                SCIENTIFIC HYPOTHESIS LIFE CYCLE                                        │
├────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│ 1. FROZEN CONTROL ($H_1$)      : Immutable baseline. Never modified to fit empirical losses.          │
│ 2. ONE-VARIABLE EXPERIMENTATION : Child hypotheses ($H_{1.x}$) isolate exactly ONE structural change.  │
│ 3. CAUSALITY FIRST             : Point-in-time candle availability strictly enforced before entry.     │
│ 4. REALISTIC FRICTION          : Maker/taker fee modeling, market slippage, adverse-first collisions.  │
│ 5. STATISTICAL FALSIFICATION   : Block bootstrap resampling, Holm-Bonferroni trial penalties.          │
│ 6. CAPITAL BARRIER GATEWAY     : 10-dimension risk governor prevents uncertified live deployment.      │
└────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Frozen Baseline Control Policy

1. **Immutability of Control Benchmarks:**
   - The baseline strategy hypothesis ($H_1$: `HTF_TREND_CONTINUATION_V1`) is permanently frozen as the reference control.
   - Under no circumstances may $H_1$'s core logic, parameters, or thresholds be tuned, optimized, or patched in response to negative backtest expectancy.
   - Falsification is a valid scientific result: a losing baseline provides the exact empirical counterfactual against which all child variants are evaluated.

2. **Isolated Child Hypothesis Lineage:**
   - Every experimental variant must be registered as an independent child hypothesis in `HypothesisRegistry` with:
     * Unique Hypothesis Identifier (e.g., `H1.1_EARLY_MTF_ALIGNMENT_ENTRY`)
     * Explicit Parent Lineage (e.g., `parent_id = "HTF_TREND_CONTINUATION_V1"`)
     * Trial ID ($K \in \mathbb{N}$) for Multiple Hypothesis Testing (MHT) accounting
     * Single Isolated Variable Modification Description
     * Formal Economic / Market Microstructure Rationale

---

## 3. One-Variable-at-a-Time Experimentation Rule

To ensure strict causal attribution, experiments must isolate **exactly one degree of freedom**:

```
                       H1 CONTROL (FROZEN)
                                │
       ┌────────────────────────┼────────────────────────┐
       ▼                        ▼                        ▼
H1.1 ENTRY TIMING        H1.2 SL ANCHOR           H1.3 TARGET REFRESH
(Only Trigger Bar)       (Only Invalidation SL)   (Only Destination TP)
```

* **Prohibition on Composite Modifications:** Child hypotheses must never combine multiple simultaneous changes (e.g., changing entry timing AND stop loss distance AND trailing rules). Combining modifications destroys attribution and leads to curve-fitted illusions of edge.
* **Sequential Attribution:** Composite strategies may only be formulated from child components that have independently survived statistical falsification and out-of-sample stress testing.

---

## 4. Zero-Lookahead & Causal Boundary Requirements

All research replays, backtests, and simulations must strictly adhere to the following point-in-time constraints:

1. **Candle-Close Availability Axiom:**
   - Higher timeframe (HTF) and middle timeframe (MTF) bars remain strictly invisible to the strategy state machine until their exact period close timestamp:
     $$t_{\text{close}} \le t_{\text{LTF}}$$
   - A 4-hour candle spanning `12:00` to `16:00` cannot be accessed by a 1-hour bar at `14:00`. At `14:00`, only the 4-hour bar closing at `12:00` is causally available.

2. **Swing Confirmation Latency:**
   - Macro/micro swing pivots require multi-candle confirmation ($N \ge 2$ subsequent bars). Unconfirmed pivots cannot be read or used as structural anchors at the trigger bar.

3. **Execution Fill Timing:**
   - Limit orders fill at the limit price only if subsequent candle price breaches the limit level.
   - Market orders fill at the next candle open or with explicit slippage penalties.
   - **Adverse-First Intrabar Collision Rule:** If both stop loss and take profit price levels are touched within the same candle, the simulation must execute the stop loss first.

---

## 5. Transaction-Cost & Friction Standards

All empirical evaluations must incorporate realistic trading friction:
* **Maker Fee:** 0.0 bps ($0.00\%$) on limit entries and limit take profits.
* **Taker Fee:** 5.0 bps ($0.05\%$) on market fills and market stop losses.
* **Slippage Penalty:** 5.0 bps ($0.05\%$) adverse execution drag on all market stop invalidations.
* **Friction Stress Testing:** Strategies must be evaluated under cost shocks ($1.2\times, 1.5\times, 2.0\times, 3.0\times$ base fees) to ensure edge survival under illiquid regimes.

---

## 6. Statistical Falsification & Validation Standards

No hypothesis may claim statistical edge or viability based solely on sample mean return:

1. **Sample Size Floor:**
   - Minimum sample size for statistical inference: $N \ge 30$ independent trades (institutional standard: $N \ge 100$).

2. **Block Bootstrap Resampling:**
   - All trade ledgers must be resampled via stationary block bootstrap ($B = 1,000$ iterations, block size $= 4$ trades) to compute the empirical 95% Confidence Interval:
     $$\text{CI}_{95\%} = \left[Q_{0.05},\; Q_{0.95}\right]$$
   - A strategy is considered to have **zero statistical edge** if the lower bound $Q_{0.05} \le 0.0\text{R}$.

3. **Multiple Hypothesis Testing (MHT) Correction:**
   - As multiple child hypotheses ($K$) are evaluated, raw p-values must be adjusted via the Holm-Bonferroni method:
     $$p_{\text{adj}} = p_{\text{raw}} \times (K - i + 1)$$
   - Prevents declaring a lucky variant as profitable after running multiple trials.

---

## 7. Promotion Criteria (Capital Barrier Governance)

A child hypothesis is **NEVER** promoted to a new baseline or live capital merely because of a positive backtest curve. Promotion follows the 5-tier Capital Barrier hierarchy:

```
REJECTED_RESEARCH_ONLY
         ↓ (Requires: E[R] > 0, N >= 30, Bootstrap 95% CI > 0)
RESEARCH_VALIDATED
         ↓ (Requires: Out-of-sample generalization ratio >= 0.70, 2.0x cost shock survival)
PAPER_ELIGIBLE
         ↓ (Requires: 60-day real-time paper execution without telemetry desync)
MICRO_LIVE_ELIGIBLE
         ↓ (Requires: Max 0.25% equity risk, live exchange fill reconciliation)
PRODUCTION_ELIGIBLE
```

Any hypothesis failing any tier is immediately quarantined in `REJECTED_RESEARCH_ONLY`.
