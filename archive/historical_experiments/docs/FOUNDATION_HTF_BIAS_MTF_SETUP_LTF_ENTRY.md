# FOUNDATION SPECIFICATION
## HTF BIAS → MTF SETUP → LTF ENTRY

**Status:** Canonical foundation reference
**Scope:** Asset-class agnostic (initial universe: BTC/USDT, ETH/USDT, SOL/USDT)
**Machine-readable twin:** `research/foundation_registry.py` → `research/results/FOUNDATION_MANIFEST.json`
**Verified by:** `tests/unit/research/test_foundation_registry.py`

---

## 0. What this document is (and is not)

This is the **foundation** — the single architectural spine every trade in the platform depends on:

```text
HTF BIAS  →  MTF SETUP  →  LTF ENTRY
then, after entry:
LTF STRUCTURAL SL  →  HTF STRUCTURAL TARGET  →  MTF STRUCTURAL TRAILING
```

The foundation is deliberately **not** one strategy. It is a *grammar*: a fixed
direction → setup → trigger → risk chain, with a **library of interchangeable families** at
every layer. Different market behaviour selects different families. Nothing here is
hard-coded to a single indicator or a single SMC concept.

> **This document does not claim profitability.** It specifies the architecture, the
> family inventory, the risk contract, and the acceptance gates a hypothesis must clear
> before it may be believed. See §8.

---

## 1. The foundation invariant

Three structural rules are non-negotiable. They come from the platform's engineering laws
(`docs/architecture.md`).

1. **Direction is never taken from the entry timeframe.** Bias is an HTF output only.
2. **A timeframe layer is never flattened into another.** HTF structure ≠ MTF structure ≠
   LTF structure. LTF price action may never redefine the HTF bias.
3. **Rejection is a valid output.** `NO_TRADE` is preferred to an unsupported assumption
   (fail closed).

The chain is evaluated strictly in order. A failure at any layer terminates the candidate:

```text
HTF bias + HTF target        (permission + destination)
        ↓
MTF setup + MTF keyzone      (alignment + navigation)
        ↓
LTF entry trigger            (execution + invalidation)
        ↓
Risk firewall                (1% max risk, ≥1:4 planned RR)
        ↓
Management                   (LTF SL → HTF target → MTF trail)
```

---

## 2. The six timeframe sets

Six independent strategy instances. Each set maintains its own market structure, bias,
zones, setup, entry, stop, target, trailing state, ledger, and statistics.

| Set | Style | HTF (bias / target) | MTF (setup / trail) | LTF (entry / stop) |
| :--- | :--- | :--- | :--- | :--- |
| **SET_1** | Investing / Macro | 1 Month | 1 Week | 1 Day |
| **SET_2** | Position Trading | 1 Week | 1 Day | 4 Hours |
| **SET_3** | Swing Trading | 1 Day | 4 Hours | 1 Hour |
| **SET_4** | Intraday | 4 Hours | 1 Hour | 15 Minutes |
| **SET_5** | Short-Term Intraday | 1 Hour | 15 Minutes | 5 Minutes |
| **SET_6** | Scalping | 15 Minutes | 5 Minutes | 1 Minute |

Per-set architecture (shown for SET_5):

```text
1H bias
→ 15M setup
→ 5M entry
→ 5M structural SL
→ 1H structural target
→ 15M structural trailing
```

**Layer roles (never interchangeable):**

| Layer | Role | Owns |
| :--- | :--- | :--- |
| **HTF** | Destination & Permission | bias, expected phase, take-profit, invalidation of context |
| **MTF** | Navigation & Trailing | setup, realignment, keyzone, trailing stop |
| **LTF** | Execution & Invalidation | liquidity sweep, trigger, initial structural stop |

**Single source of truth:** `config/timeframe_sets.py::CANONICAL_6_TIMEFRAME_SETS`.
`research/replayer/timeframe_aligner.py` derives its ladder from that mapping, and
`research/strategy_grammar.py` expresses the same ladder as `(htf_scale, mtf_scale)`
multiples of the base timeframe. A test asserts all three agree — see §9.
---

## 3. Layer 1 — HTF BIAS families

The HTF layer answers one question only: **which direction is permitted, and where is the
structural destination?**

Registered bias families (22 registry ids / 21 unique classes):

| Category | Family id | Mechanism |
| :--- | :--- | :--- |
| BASELINE | `CANONICAL_SUPERTREND_STOCHASTIC` | Supertrend regime direction |
| TREND | `TREND_MA_ALIGNMENT` | Moving-average stack alignment |
| TREND | `BIAS_ICHIMOKU` | Ichimoku cloud position |
| TREND_STRENGTH | `BIAS_ADX_DIRECTIONAL` | Directional index dominance |
| MOMENTUM | `MOM_RSI_REGIME` | RSI regime state |
| MOMENTUM | `BIAS_MACD_REGIME` | MACD regime state |
| MOMENTUM | `BIAS_STOCHASTIC_REGIME` | Stochastic regime state |
| MOMENTUM | `BIAS_MOMENTUM_SLOPE` | Momentum slope sign |
| MARKET_STRUCTURE | `STRUCT_HH_HL` | Higher-high / higher-low sequence |
| MARKET_STRUCTURE | `BIAS_BOS` | Break of structure |
| MARKET_STRUCTURE | `BIAS_CHOCH` | Change of character |
| SMC_ZONE | `BIAS_ORDER_BLOCK` | Order-block origin direction |
| SMC_ZONE | `BIAS_FVG_DIRECTION` | Fair-value-gap direction |
| SMC_ZONE | `BIAS_PREMIUM_DISCOUNT` | Premium/discount dealing range |
| VALUE | `BIAS_VWAP_POSITION` | Position relative to VWAP |
| VOLATILITY | `BIAS_SQUEEZE_DIRECTION` | Compression-release direction |
| REGIME | `REGIME_TREND` | Trend regime active |
| REGIME | `REGIME_RANGE` | Range regime active |
| REGIME | `REGIME_ANY` | Any regime active |
| REGIME | `REGIME` *(registry alias → `REGIME_ANY`)* | Any regime active |
| REGIME | `BIAS_REGIME_COMPRESSION` | Compression regime active |
| NULL_CONTROL | `NEUTRAL` | Explicit no-bias control |

**Rule:** a bias family is selected by **market behaviour / regime**, not by preference.
Multiple bias families may be composed into one hypothesis; the composition is a research
hypothesis, not a default. `NEUTRAL` exists so a hypothesis can be falsified against a
no-signal control.

---

## 4. Layer 2 — MTF SETUP families

The MTF layer answers: **has price realigned with the HTF bias, and where is the zone?**

Registered setup families (24 registry ids / 20 unique classes):

| Category | Family id | Mechanism |
| :--- | :--- | :--- |
| BASELINE | `CANONICAL_SUPERTREND_STOCHASTIC_SETUP` | Baseline pullback |
| CONTINUATION | `PULLBACK` | Pullback into trend |
| CONTINUATION | `SETUP_MA_PULLBACK` | MA pullback |
| CONTINUATION | `SETUP_FLAG_PENNANT` | Flag / pennant consolidation |
| BREAKOUT | `BREAKOUT` | Range/level breakout |
| BREAKOUT | `SETUP_BREAKOUT_RETEST` | Breakout then retest |
| MARKET_STRUCTURE | `SETUP_CHOCH_BOS_RETEST` | CHOCH/BOS then retest |
| SMC_ZONE | `SETUP_ORDER_BLOCK_RETEST` | Order-block retest |
| SMC_ZONE | `SETUP_FVG_TAP` | Fair-value-gap tap |
| LIQUIDITY | `SETUP_LIQUIDITY_SWEEP` | Liquidity sweep |
| LIQUIDITY | `SETUP_LIQUIDITY_GRAB_REVERSAL` | Liquidity grab reversal |
| RETRACEMENT | `SETUP_FIBONACCI_RETRACEMENT` | Fibonacci retracement |
| MEAN_REVERSION | `SETUP_VWAP_MEAN_REVERSION` | VWAP mean reversion |
| REVERSAL | `SETUP_SR_FLIP` | Support/resistance flip |
| VOLATILITY | `SETUP_SQUEEZE` | Volatility squeeze |
| COMPRESSION | `SETUP_INSIDE_BAR` | Inside-bar compression |
| OSCILLATOR | `SETUP_STOCHASTIC_CROSS` | Stochastic cross |
| OSCILLATOR | `SETUP_MACD_HISTOGRAM_REVERSAL` | MACD histogram reversal |
| DIVERGENCE | `SETUP_RSI_DIVERGENCE` | RSI divergence |
| VOLUME | `SETUP_VOLUME_CLIMAX` | Volume climax |

Short registry aliases exist for the commonly reused setups
(`FVG_TAP`, `LIQUIDITY_SWEEP`, `BREAKOUT_RETEST`, `CHOCH_BOS_RETEST`). They are aliases of
the same class, **not** additional mechanisms — the registry reports them explicitly so
they are never double-counted in research statistics.

**Rule:** the setup must be the *MTF* manifestation of the HTF phase. A bullish HTF bias
with a bearish MTF setup is not a setup — it is a contradiction, and the candidate is
rejected. It must never be inverted into a counter-trend trade.

---

## 5. Layer 3 — LTF ENTRY families

The LTF layer answers: **is there a causal trigger right now, and where is the invalidation?**

Registered entry families (15 registry ids / 9 unique classes):

| Category | Family id | Mechanism |
| :--- | :--- | :--- |
| BASELINE | `CANONICAL_SUPERTREND_STOCHASTIC_ENTRY` | Baseline trigger |
| CANDLE_PATTERN | `ENGULFING` | Engulfing close |
| CANDLE_PATTERN | `REJECTION_CLOSE` | Rejection / pin close |
| OSCILLATOR | `MACD_CROSSOVER` | MACD crossover |
| BREAKOUT | `BREAKOUT_CLOSE` | Close beyond the level |
| MARKET_STRUCTURE | `CHOCH_CONFIRMATION` | CHOCH confirmed on the LTF |
| LIQUIDITY | `SWEEP_RECLAIM` | Sweep then reclaim |
| SMC_ZONE | `FVG_REJECTION` | Rejection out of an FVG |
| DISPLACEMENT | `DISPLACEMENT_CONFIRMATION` | Displacement candle confirmation |

Aliases (`ENTRY_*` prefixes) map to the same classes and are reported as aliases.

**Rule:** the entry must be *causally* after the MTF retest. A liquidity sweep that
occurred *before* the setup retest is not a valid trigger — this is enforced explicitly
because it was previously a source of lookahead contamination
(see `docs/AUTONOMOUS_QUANTITATIVE_RESEARCH_REPORT.md`).

---

## 6. Post-entry: stop, target, trailing

After entry the position is managed by a three-layer chain. The stop is never widened and
the target is never moved outward to manufacture a ratio.

### 6.1 LTF structural stop — 8 registry ids / 5 classes

| Category | Family id | Anchor |
| :--- | :--- | :--- |
| STRUCTURAL_LTF | `SL_LTF_SWING` *(alias `STRUCTURAL_SL`)* | LTF swing pivot |
| SETUP_GEOMETRY | `SL_SETUP_INVALIDATION` | Setup invalidation point |
| MARKET_STRUCTURE | `SL_BOS_INVALIDATION` | Break-of-structure invalidation |
| SMC_ZONE | `SL_FVG_INVALIDATION` *(alias `FVG_INVALIDATION_SL`)* | FVG invalidation |
| VOLATILITY | `SL_ATR` *(alias `SL_ATR_REFERENCE`)* | ATR multiple (research reference) |

The canonical anchor is **structural** (`SL_LTF_SWING`). ATR stops exist as research
references and must not silently replace the structural stop.

### 6.2 HTF structural target — 8 registry ids / 5 classes

| Category | Family id | Anchor |
| :--- | :--- | :--- |
| STRUCTURAL_HTF | `TP_HTF_STRUCTURAL` *(alias `TP_HTF_STRUCTURE`)* | HTF structural destination |
| STRUCTURAL_SWING | `TP_STRUCTURAL_SWING` *(alias `STRUCTURAL_TP`)* | Structural swing |
| LIQUIDITY | `TP_LTF_LIQUIDITY` | LTF liquidity pool |
| LIQUIDITY | `TP_LIQUIDITY_TARGET` | Liquidity target |
| R_MULTIPLE | `TP_DYNAMIC_R` / `TP_FIXED_R` | Fixed R multiple (reference) |

The canonical target is the **HTF structural destination**. The target is determined
first; the ratio is then *measured*, never engineered.

### 6.3 MTF structural trailing — 6 registry ids / 5 classes

| Category | Family id | Anchor |
| :--- | :--- | :--- |
| STRUCTURAL_MTF | `TRAIL_MTF_STRUCTURAL` | MTF structural swing |
| MARKET_STRUCTURE | `TRAIL_BOS` | Trailing on MTF BOS |
| STRUCTURAL_LTF | `TRAIL_LTF_STRUCTURE` | LTF structure |
| VOLATILITY | `TRAIL_CHANDELIER` *(alias `TRAIL_ATR`)* | Chandelier / ATR |
| NONE | `TRAIL_NONE` | No trailing (control) |

The canonical trailing mechanism is **MTF structural** (`TRAIL_MTF_STRUCTURAL`), which is
itself a testable hypothesis — not an assumption.

### 6.4 Exit hierarchy

Exactly one exit reason is attributed per trade, in this precedence:

```text
1. LTF structural SL breached        → LTF_INVALIDATION_EXIT
2. MTF trailing stop breached        → MTF_TRAIL_EXIT
3. HTF structural target reached     → HTF_TARGET_REACHED
4. Risk kill switch / blackout       → RISK_EXIT
```

When two levels collide inside the same bar, the **adverse** outcome takes precedence.

---

## 7. Risk management contract

Risk management is **downstream** of the strategy. The risk engine has no awareness of
market phases or hypotheses; it only enforces invariants. All values below are read from
the enforcing code, never from prose.

| Rule | Value | Enforced by |
| :--- | :--- | :--- |
| Max risk per trade | **1.0%** of account equity | `PositionSizer.MAX_RISK_FRACTION`, `RiskConfig.max_risk_fraction` |
| Minimum planned RR | **1 : 4** | `RiskConfig.min_rr_floor` |
| Maximum planned RR | uncapped | — |
| Stop anchor | LTF structural | `SL_LTF_SWING` |
| Target anchor | HTF structural | `TP_HTF_STRUCTURAL` |
| Trailing anchor | MTF structural | `TRAIL_MTF_STRUCTURAL` |
| Max leverage | 1.0 (no leverage) | `RiskConfig.max_leverage` |
| Min stop distance | 0.1% of entry | `RiskConfig.min_stop_distance_pct` |
| Friction ceiling | worst-case loss ≤ 1.2× intended risk | `PositionSizer` |
| Friction model | taker 5 bps + slippage 5 bps | `PositionSizer` |

**Sizing formula**

```text
units = (equity × 0.01) / abs(entry − LTF_structural_stop)
```

This works at any account size ($10, $100, $10,000) with no leverage bypass.

**Portfolio circuit breakers**

| Limit | Value |
| :--- | :--- |
| Daily drawdown | −3.0% |
| Weekly drawdown | −6.0% |
| Systemic (peak-to-trough) | −10.0% |
| Max simultaneous positions | 5 |
| Max exposure per asset | 3.0% |

**Ratio rule:** the HTF structural destination is determined **first**; the ratio is then
*measured* as `target_distance / stop_distance`. If the measured ratio is below 4.0 the
trade is rejected. The target must **never** be pushed outward to manufacture 4R, and the
stop must **never** be tightened below the structural invalidation to inflate the ratio.
The 1:4 floor is an *entry qualification gate*, not a forced exit — realized R is measured
after the trade closes.

---

## 8. News avoidance

Where reliable point-in-time scheduled-event data exists, no **new** position may be
initiated inside the blackout window:

```text
30 minutes before a HIGH-impact event  →  30 minutes after the event
```

| Rule | Value |
| :--- | :--- |
| Blackout before | 1800 s (30 min) |
| Blackout after | 1800 s (30 min) |
| Qualifying impact | `HIGH` |
| Applies to layer | LTF entry |
| Affected sets | **SET_4, SET_5, SET_6** (LTF ≤ 15 min) |
| Unaffected sets | SET_1, SET_2, SET_3 (structural horizons) |
| Positions already open | managed, not cancelled |
| Missing historical news data | fail closed |
| Lookahead | forbidden |

The affected-set list is **derived from the ladder** (any set whose LTF is 15 minutes or
faster), not hard-coded, so it cannot drift if the ladder changes. Interface:
`strategy_engine/news/news_provider.py` (`NewsProvider`, `MemoryNewsProvider`,
`NullNewsProvider`).
---

## 9. Performance targets — and the honest arithmetic

The operator directive for this foundation is:

| Metric | Target |
| :--- | :--- |
| Win rate | 60% – 80% |
| Profit factor | 2.0 – 3.0 (higher acceptable, not lower) |
| Minimum planned RR | 1 : 4 |
| Max risk per trade | 1% of account |

These are recorded in code as **acceptance gates**, in
`research/foundation_registry.py::build_performance_targets()`, with
`claim_status = "UNPROVEN_TARGET_ONLY"`.

### The arithmetic must be understood before the target is chased

At a mandatory **1:4** planned RR, the **breakeven** win rate is exactly:

```text
1 / (1 + 4) = 20%
```

So the target is not "a bit above breakeven". A 60% win rate at 4R implies:

```text
expectancy = 0.60 × 4R − 0.40 × 1R = +2.00R per trade
```

and an 80% win rate at 4R implies:

```text
expectancy = 0.80 × 4R − 0.20 × 1R = +3.00R per trade
```

For context, the platform's own documented promotion bar
(`docs/ECONOMIC_PURPOSE_SPECIFICATION.md`) is **+0.20R expectancy, t-stat > 2.0,
net Sharpe > 1.2**. The 60–80% / 4R target therefore implies an expectancy roughly
**10×–15× that bar**.

### Integrity position

This target is treated as a **hypothesis to be falsified**, not as an expected outcome:

- Current validated alpha strategies in the platform: **0** (see `README.md`).
- A target may only be reported as achieved after **multi-partition out-of-sample** and
  **adversarial falsification**.
- Reporting a target as achieved without that evidence is a governance violation and is
  prohibited by `CONTRIBUTING.md` and the platform's research-integrity rules.

If the target cannot be met, the correct platform output is the honest one:
`NO_NEW_ECONOMIC_EDGE_VALIDATED`. Refusing to fabricate a win rate **is** the platform
working correctly.

---

## 10. Verification

The foundation is enforced by tests, not by documentation:

```bash
python3 -m pytest tests/unit/research/test_foundation_registry.py -v
python3 -m pytest tests/unit/research/test_timeframe_aligner.py -v
python3 -m pytest tests/unit/strategy_engine/test_strategy_ontology.py -v
```

Guarantees asserted:

| # | Guarantee |
| :--- | :--- |
| 1 | Exactly six sets, matching this document verbatim (fails if the ladder drifts) |
| 2 | `config` and the replayer agree on every set (single source of truth) |
| 3 | The grammar enum's scales reproduce the ladder durations exactly |
| 4 | Every set is strictly hierarchical (HTF > MTF > LTF), fail-closed on unknown ids |
| 5 | Every registered family is classified; a new unclassified family fails the build |
| 6 | Aliases are reported, never double-counted as unique mechanisms |
| 7 | Risk policy matches the live `risk_engine` constants (1% / 1:4 / −3% / −6% / −10%) |
| 8 | The declared news window matches live `NewsProvider` behaviour at the boundary |
| 9 | Targets are marked `UNPROVEN_TARGET_ONLY` and their arithmetic is consistent |
| 10 | The JSON manifest emits and round-trips |

Regenerate the machine-readable manifest:

```bash
python3 -m research.foundation_registry
```

---

## 11. Source map

| Concern | File |
| :--- | :--- |
| Ladder single source of truth | `config/timeframe_sets.py` |
| Replayer ladder (derived) | `research/replayer/timeframe_aligner.py` |
| Grammar scales | `research/strategy_grammar.py` |
| Machine-readable inventory | `research/foundation_registry.py` |
| Generated manifest | `research/results/FOUNDATION_MANIFEST.json` |
| Bias families | `research/bias_families.py` |
| Setup families | `research/setup_families.py` |
| Entry families | `research/entry_families.py` |
| Stop / target / trailing families | `research/sl_families.py`, `research/tp_families.py`, `research/trailing_families.py` |
| Component interfaces + registry | `research/grammar_components.py` |
| Event assembly (bias→entry) | `strategy/orchestrator.py` |
| Risk firewall | `risk_engine/`, `docs/risk-model.md` |
| News filter | `strategy_engine/news/news_provider.py` |
| Canonical strategy spec | `docs/CANONICAL_STRATEGY_SPECIFICATION.md` §29–§30 |