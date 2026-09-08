# UNIVERSAL MULTI-TIMEFRAME STRUCTURAL TRADING SYSTEM

## Canonical Strategy & Architecture Specification

**Document Purpose:**
Define the canonical trading concept, strategy logic, market-structure architecture, risk framework, execution architecture, and research requirements for a systematic multi-timeframe trading platform.

**Primary Initial Asset Class:** Cryptocurrency

**Future Asset Classes:** Forex, indices, commodities, equities, futures, and other sufficiently liquid markets.

The core strategy must remain **asset-class agnostic**.

Asset-specific behaviour must be implemented through configuration, adapters, and execution/data modules rather than by changing the fundamental strategy.

---

# 1. CORE TRADING CONCEPT

The fundamental strategy architecture is:

> **HTF BIAS → MTF SETUP → LTF ENTRY MODEL**

After entry:

> **LTF STRUCTURAL SL → HTF STRUCTURAL TARGET → MTF STRUCTURAL TRAILING**

This is the central concept.

The system uses three hierarchical timeframes:

* **HTF — Higher Time Frame:** establishes directional bias and broader market context.
* **MTF — Middle Time Frame:** develops the trade setup and confirms structural alignment with the HTF.
* **LTF — Lower Time Frame:** provides the precise entry model and initial structural invalidation.

The MTF subsequently manages the open position through structural trailing.

The system therefore separates:

**Direction → Setup → Entry → Initial Risk → Destination → Position Management**

rather than attempting to generate an entry from one timeframe.

---

# 2. UNIVERSAL MARKET-STRUCTURE MODEL

Every timeframe is treated as an independent market environment.

Each timeframe can contain its own:

* market structure
* trend
* BOS
* CHOCH
* swing highs
* swing lows
* strong swings
* weak swings
* liquidity
* keyzones
* keylevels
* FVGs
* order blocks
* supply
* demand
* imbalance
* premium/discount context
* pullback phases
* continuation phases
* expansion
* contraction
* structural invalidation

The system must preserve the distinction between timeframe layers.

HTF structure must not be flattened into MTF structure.

MTF structure must not be flattened into LTF structure.

LTF structure must not be used to redefine the HTF bias.

---

# 3. ONE CORE STRATEGY

The system contains **one core strategy architecture**.

The concepts sometimes described as:

* pullback riding
* continuation riding

must NOT become two unrelated strategy engines.

They are different **market contexts/phases within the same strategy**.

The universal strategy trades in the direction established by the HTF.

The HTF may currently be:

* continuing
* pulling back
* reacting from a keyzone
* approaching a destination
* developing new structure

Regardless of the phase, the execution hierarchy remains:

**HTF → MTF → LTF**

---

# 4. HTF — DIRECTIONAL BIAS ENGINE

The HTF establishes the directional bias.

The HTF structural engine identifies the most recent meaningful market structure using objectively defined rules.

Potential structural information includes:

* BOS
* CHOCH
* swing hierarchy
* higher highs
* higher lows
* lower highs
* lower lows
* strong swings
* weak swings
* liquidity
* structural displacement

Example:

```text
HTF structure = BULLISH
HTF bias = LONG
```

The system therefore looks only for long opportunities.

Example:

```text
HTF structure = BEARISH
HTF bias = SHORT
```

The system therefore looks only for short opportunities.

The HTF bias is **direction**, not an immediate entry signal.

---

# 5. HTF KEYZONES AND KEYLEVELS

After identifying HTF structure, the system identifies relevant HTF reaction areas.

Potential keyzones/keylevels include objectively defined:

* order blocks
* fair value gaps
* supply zones
* demand zones
* imbalances
* liquidity pools
* structural swing areas
* premium/discount zones
* other validated structural reaction areas

The system must maintain a lifecycle for every zone:

```text
CREATED
→ ACTIVE
→ TESTED
→ MITIGATED
→ INVALIDATED
→ EXPIRED
```

Zones must have timestamps and provenance.

A zone must never be treated as permanently valid.

---

# 6. HTF PHASE

The HTF must identify the current structural phase/context.

Possible contexts include:

* continuation
* pullback
* expansion
* consolidation
* transition
* reversal risk

Example:

```text
HTF structure = BULLISH
Price = approaching HTF demand
Context = PULLBACK
Bias = LONG
```

This does NOT mean immediately buying.

It means:

> The broader directional expectation remains bullish while price is currently moving through a pullback/context phase.

Another example:

```text
HTF structure = BULLISH
Price = reacted from HTF demand
Context = CONTINUATION
Bias = LONG
```

The strategy still waits for the MTF setup and LTF entry.

---

# 7. HTF TARGET / DESTINATION

The HTF determines the structural destination of the trade.

For LONG positions, the destination may be:

* HTF weak swing
* HTF liquidity
* opposing structural level
* structural continuation destination
* other objectively defined HTF target

For SHORT positions, the inverse applies.

The target is structural.

It is not an arbitrary percentage.

It is not automatically a fixed number of ATRs.

It is not automatically a fixed R multiple.

---

# 8. MINIMUM PLANNED RR

Every trade must have:

> **Minimum planned RR = 1:4**

There is no maximum.

A trade may have:

* 1:4
* 1:5
* 1:6
* 1:8
* 1:10
* 1:12
* 1:15
* 1:20
* etc.

The system calculates:

```text
Planned RR =
HTF target distance
/
LTF structural SL distance
```

If:

```text
Planned RR < 4.0
```

the trade is rejected.

The system must NOT move the target artificially simply to achieve 4R.

The HTF structural destination must be determined first.

RR is then calculated.

---

# 9. MTF — SETUP ENGINE

The MTF is the most important bridge between HTF direction and LTF entry.

The MTF does not have to initially agree with the HTF.

This is especially important during HTF pullbacks.

Example:

```text
HTF = BULLISH

MTF = BEARISH
```

This is not a valid short trade.

The MTF bearish structure may represent the pullback occurring inside the bullish HTF environment.

The system waits for the MTF to structurally transition toward the HTF direction.

Example:

```text
MTF bearish
→ structural shift
→ CHOCH/BOS
→ bullish structure
→ MTF aligns with bullish HTF
```

Now the MTF setup is developing.

For bearish HTF:

```text
MTF bullish
→ structural shift
→ CHOCH/BOS
→ bearish structure
→ MTF aligns with bearish HTF
```

---

# 10. MTF STRUCTURAL ALIGNMENT

MTF alignment is not simply:

```text
HTF bullish
AND
MTF bullish
```

The system must know **how the MTF became bullish**.

The alignment event must have structural provenance.

Record:

* previous MTF direction
* previous structural swing
* structural break
* CHOCH/BOS
* confirmation timestamp
* confirmation candle
* new structural direction
* HTF direction
* alignment timestamp

The transition is important:

```text
MTF counter-direction
→ structural shift
→ HTF-aligned MTF direction
```

---

# 11. MTF STRUCTURE AFTER ALIGNMENT

After the MTF aligns with the HTF, the MTF creates a new structural environment.

That environment has its own:

* swings
* strong swings
* weak swings
* BOS
* CHOCH
* FVG
* OB
* liquidity
* keyzones
* keylevels
* pullback areas

This post-alignment structure becomes the setup framework for the LTF.

---

# 12. MTF KEYZONE CREATION

Once MTF structural alignment is confirmed, identify the relevant newly formed MTF setup zone.

Potential zones:

* MTF FVG
* MTF OB
* MTF supply/demand
* MTF imbalance
* MTF liquidity level
* MTF structural keylevel

The system does NOT automatically enter immediately after MTF alignment.

The intended sequence is:

```text
MTF structural shift
→ MTF alignment
→ new MTF structure
→ MTF keyzone
→ price retracement/retest
→ LTF activation
```

---

# 13. MTF PULLBACK / RETEST

After MTF alignment and keyzone creation, price may retrace into the newly formed MTF zone.

The system waits for that interaction.

This creates the setup location for the LTF.

The MTF pullback is therefore part of the strategy architecture.

The strategy does not simply chase the first MTF BOS candle.

---

# 14. LTF — ENTRY MODEL

Once price reaches the relevant MTF setup zone, the LTF becomes active.

The LTF has its own:

* market structure
* trend
* BOS
* CHOCH
* swings
* liquidity
* FVG
* OB
* displacement
* entry zones

The LTF must produce an entry model aligned with:

1. HTF direction
2. MTF structure
3. MTF setup location

The ideal state is:

```text
HTF = ALIGNED
MTF = ALIGNED
LTF = ALIGNED
```

This is the three-timeframe confirmation state.

---

# 15. LTF ENTRY MODEL

The entry model may use objectively defined SMC/ICT-style concepts.

Potential components include:

* liquidity sweep
* liquidity grab
* CHOCH
* BOS
* displacement
* FVG
* order block
* mitigation
* rejection
* structural retest
* imbalance

A typical long sequence could be:

```text
Price reaches MTF bullish keyzone
↓
LTF liquidity sweep
↓
LTF bullish CHOCH/BOS
↓
LTF displacement
↓
LTF FVG/OB
↓
Entry
```

The exact entry model must be deterministic and backtestable.

---

# 16. THREE-TIMEFRAME CONFIRMATION

A trade becomes eligible only when the hierarchy is satisfied:

```text
HTF directional bias
        ↓
MTF structural alignment
        ↓
MTF setup/keyzone
        ↓
MTF pullback/retest
        ↓
LTF entry confirmation
```

The system must not skip required structural stages unless a separately validated hypothesis explicitly proves that a stage can be safely removed.

---

# 17. INITIAL LTF STOP

The initial SL is structural.

For LONG:

```text
SL = LTF strong structural reversal/invalidation point
```

For SHORT:

```text
SL = LTF strong structural reversal/invalidation point
```

The reasoning:

The LTF entry is valid because LTF structure aligned with MTF and HTF.

If the relevant LTF structural reversal point is violated:

```text
LTF alignment failed
→ initial trade thesis invalidated
→ exit
```

The system must not arbitrarily tighten structural stops to improve historical statistics.

---

# 18. POSITION RISK

Maximum account risk per trade:

> **1% of current account equity**

Risk may be lower.

Risk may never exceed 1%.

Position sizing must be automatic.

Formula:

```text
Allowed monetary risk
=
Account equity × risk percentage
```

Then:

```text
Position size
=
Allowed monetary risk
/
structural stop distance
```

The system must account for:

* tick size
* lot size
* contract specifications
* minimum order quantity
* exchange precision
* leverage constraints
* fees
* expected slippage

The system must fail closed if the calculated position would exceed the maximum permitted risk.

---

# 19. MTF STRUCTURAL TRAILING

MTF structural trailing is a **core component of the strategy**, not a cosmetic exit optimization.

After entry:

```text
Initial protection = LTF structural SL
```

The trade is then managed by the MTF structure.

For LONG:

```text
MTF creates valid higher-low structure
→ trailing stop advances beneath confirmed structural point
```

For SHORT:

```text
MTF creates valid lower-high structure
→ trailing stop advances above confirmed structural point
```

The trail moves only from causally confirmed MTF structural information.

No future swing confirmation may be used retrospectively.

---

# 20. PURPOSE OF MTF TRAILING

The HTF target may be very far away.

Example:

```text
Planned RR = 1:10
```

Price may reach:

```text
+1R
+2R
+3R
```

and then reverse.

A fixed HTF target could give back most of that favorable movement.

The MTF structural trail attempts to preserve part of the move.

Therefore a trade can exit at:

```text
+1R
+2R
+3R
+5R
+10R
```

depending on whether:

* MTF structure continues
* MTF structure deteriorates
* HTF target is reached

---

# 21. MTF TRAIL EXIT

While MTF structure remains aligned with HTF:

```text
HOLD
```

If MTF structural alignment deteriorates:

```text
MTF structural reversal
→ MTF trailing stop
→ EXIT
```

The strategy does not wait for the HTF itself to reverse.

The MTF is deliberately used as the intermediate position-management timeframe.

---

# 22. EXIT HIERARCHY

A position can terminate through:

### Exit 1 — Initial LTF Structural SL

The original LTF structural thesis failed.

### Exit 2 — MTF Structural Trail

The higher-level continuation structure deteriorated.

### Exit 3 — HTF Target

The structural destination was reached.

### Exit 4 — Emergency Risk Exit

Operational or portfolio risk requires immediate closure.

Every exit must have an explicit reason code.

---

# 23. TRADE OUTCOME TYPES

The system must distinguish:

```text
INITIAL_SL
MTF_TRAIL_PROFIT
MTF_TRAIL_BREAKEVEN
MTF_TRAIL_LOSS
HTF_TARGET
EMERGENCY_EXIT
```

Do not classify every non-SL trade as an HTF-target winner.

This is critical for evaluating the MTF trailing thesis.

---

# 24. PLANNED RR VS REALIZED R

The system must maintain both:

**Planned RR**

and

**Realized R**

Example:

```text
Entry = 100
SL = 98
HTF target = 120

Risk = 2
Target distance = 20

Planned RR = 10R
```

The trade could realize:

```text
-1R
+1R
+2R
+3R
+5R
+10R
```

depending on the exit mechanism.

Therefore:

> Planned RR >= 4R does not mean every realized trade must produce >=4R.

---

# 25. MARKET REGIME LAYER

A separate market-regime layer should classify the market environment.

Possible regimes:

* strong trend
* weak trend
* range
* high volatility
* low volatility
* volatility expansion
* volatility contraction
* momentum expansion
* momentum exhaustion
* abnormal conditions
* degraded liquidity

Potential measurements:

* ATR
* realized volatility
* ADX
* volatility percentile
* trend persistence
* range statistics
* volume
* spread
* funding
* open interest
* basis
* market depth

Indicators are allowed but not mandatory.

They must solve a demonstrated problem.

---

# 26. REGIME ADAPTATION

The system may adapt risk/trade qualification according to market regime.

However:

> **The core strategy must not change.**

The core remains:

```text
HTF bias
→ MTF setup
→ LTF entry
→ LTF SL
→ HTF target
→ MTF trailing
```

Regime information may modify:

* whether a trade is allowed
* position risk
* execution requirements
* liquidity requirements
* portfolio exposure
* risk reduction

It must not secretly transform the strategy into another trading system.

---

# 27. INDICATOR POLICY

Indicators may be introduced when evidence shows they improve robustness.

Examples:

ATR:
volatility normalization.

ADX:
trend-strength classification.

Volume:
participation confirmation.

Funding:
derivatives positioning.

Open interest:
positioning context.

The rule is:

```text
Observed failure
→ hypothesis
→ indicator proposal
→ pre-registration
→ development test
→ validation
→ OOS
→ stress test
```

Never add indicators simply because they improve one backtest.

---

# 28. NEWS FILTER

Where reliable point-in-time scheduled-event data exists:

Do not initiate a new position:

```text
30 minutes before high-impact event
through
30 minutes after event
```

The system must only use information that was actually available at the decision timestamp.

No lookahead.

If reliable historical news data cannot be established, production eligibility must fail closed rather than fabricate event information.

---

# 29. TIMEFRAME SYSTEMS

The universal strategy supports five timeframe sets.

## SET 1 — LONG-TERM

```text
HTF = 1 Month
MTF = 1 Week
LTF = 1 Day
```

Architecture:

```text
1M bias
→ 1W setup
→ 1D entry
→ 1D SL
→ 1M target
→ 1W trail
```

---

## SET 2 — POSITIONAL

```text
HTF = 1 Week
MTF = 1 Day
LTF = 4 Hours
```

Architecture:

```text
1W bias
→ 1D setup
→ 4H entry
→ 4H SL
→ 1W target
→ 1D trail
```

---

## SET 3 — SWING

```text
HTF = 1 Day
MTF = 4 Hours
LTF = 1 Hour
```

Architecture:

```text
1D bias
→ 4H setup
→ 1H entry
→ 1H SL
→ 1D target
→ 4H trail
```

---

## SET 4 — INTRADAY

```text
HTF = 4 Hours
MTF = 1 Hour
LTF = 15 Minutes
```

Architecture:

```text
4H bias
→ 1H setup
→ 15m entry
→ 15m SL
→ 4H target
→ 1H trail
```

---

## SET 5 — SCALPING

```text
HTF = 15 Minutes
MTF = 5 Minutes
LTF = 1 Minute
```

Architecture:

```text
15m bias
→ 5m setup
→ 1m entry
→ 1m SL
→ 15m target
→ 5m trail
```

---

# 30. TIMEFRAME SET INDEPENDENCE

Every timeframe set is an independent strategy instance.

Each instance maintains its own:

* market structure
* bias
* zones
* setup
* entry
* SL
* target
* trailing state
* trade ledger
* statistics

Example:

```text
BTC / SET 1
BTC / SET 2
BTC / SET 3
BTC / SET 4
BTC / SET 5
```

are separate state machines.

One cannot overwrite another.

---

# 31. ASSET-CLASS ABSTRACTION

The strategy itself must be asset-agnostic.

The initial implementation is cryptocurrency.

The architecture should later support:

```text
Crypto
Forex
Indices
Commodities
Equities
Futures
Other liquid markets
```

The universal strategy engine should consume normalized market data.

Asset-specific modules handle:

* trading hours
* tick size
* contract size
* leverage
* fees
* funding
* margin
* exchange/broker execution
* liquidity
* spread
* market microstructure

Therefore:

```text
Universal Strategy Engine
        ↓
Asset-Class Adapter
        ↓
Broker/Exchange Adapter
```

The strategy itself does not need to be rewritten when moving from crypto to forex.

---

# 32. INITIAL CRYPTO UNIVERSE

Initial crypto universe:

```text
BTC
ETH
SOL
```

Additional assets may be introduced only when justified by:

* liquidity
* historical data quality
* execution quality
* spread
* fees
* sample size
* correlation
* capacity
* robustness

Do not add assets merely to increase trade count.

---

# 33. MULTI-ASSET OPERATION

The system should eventually run:

```text
BTC × 5 timeframe sets
ETH × 5 timeframe sets
SOL × 5 timeframe sets
```

simultaneously.

Every instance must have independent structural state.

The combined system must have portfolio-level risk controls.

---

# 34. PORTFOLIO RISK

Individual trade risk:

```text
<= 1%
```

But simultaneous positions create aggregate exposure.

Therefore the portfolio layer must evaluate:

* total open risk
* same-direction exposure
* asset concentration
* timeframe concentration
* correlated positions
* exchange concentration
* daily drawdown
* rolling drawdown
* volatility shock
* liquidity deterioration

The portfolio layer may reduce or reject trades when aggregate risk becomes excessive.

---

# 35. EXECUTION ARCHITECTURE

Separate strategy from execution.

Strategy layer:

```text
Market Data
→ Structure
→ Bias
→ Setup
→ Entry
→ SL
→ Target
→ Trailing
→ Position Specification
```

Execution layer:

```text
Position Specification
→ Broker/Exchange
→ Order
→ Fill
→ Reconciliation
```

The strategy must not contain exchange-specific order logic.

The execution layer must support multiple brokers/exchanges.

---

# 36. AUTONOMOUS OPERATION

The final system is intended to operate:

> **24/7/365**

The production architecture must support:

* continuous market-data ingestion
* structural analysis
* candidate generation
* signal generation
* position sizing
* order execution
* stop management
* target management
* MTF trailing
* position reconciliation
* balance reconciliation
* restart recovery
* persistent state
* duplicate-order protection
* exchange reconnection
* operational alerts
* telemetry
* audit logs
* kill switches

---

# 37. EXECUTION SAFETY

Before live deployment, the platform must support:

* secure credentials
* minimum exchange permissions
* no withdrawal permissions
* order acknowledgement
* duplicate-order prevention
* idempotency
* position reconciliation
* balance reconciliation
* open-order reconciliation
* stale-data detection
* stale-signal prevention
* exchange failure handling
* network retry policies
* emergency shutdown
* maximum-position enforcement
* maximum-risk enforcement

If execution state is uncertain:

> **FAIL CLOSED.**

---

# 38. MARKET-DATA REQUIREMENTS

Data must be:

* timestamp accurate
* normalized
* gap checked
* OHLCV validated
* partitioned
* reproducible
* versioned
* checksum verified where applicable

Historical replay must use only information that would have existed at the decision time.

---

# 39. CAUSALITY REQUIREMENT

Strict point-in-time causality is mandatory.

At decision time `t`, the system may use only information available at `t`.

This applies to:

* structure
* BOS
* CHOCH
* swing confirmation
* strong/weak swing classification
* keyzones
* FVG
* OB
* liquidity
* MTF alignment
* LTF entry
* regime
* news
* trailing

Future information must never influence a historical trade.

---

# 40. STRUCTURAL PROVENANCE

Every structural event must be reconstructable.

For every event record:

```text
asset
timeframe
event type
timestamp
source candle
source swing
price
direction
previous structure
new structure
zone ID
parent structure
confirmation latency
```

---

# 41. COMPLETE TRADE TELEMETRY

Every trade must contain:

```text
Asset
Asset class
Timeframe set
HTF timeframe
MTF timeframe
LTF timeframe

HTF structure
HTF direction
HTF phase
HTF keyzone
HTF target

MTF previous structure
MTF structural shift
MTF alignment
MTF alignment timestamp
MTF structure
MTF keyzone
MTF pullback/retest

LTF structure
LTF liquidity event
LTF CHOCH/BOS
LTF displacement
LTF FVG/OB
LTF entry

Entry price
Initial SL
HTF target
Planned RR
Risk %
Position size

MTF trailing events
Trail levels
Trail timestamps

Exit price
Exit reason
Realized R
MFE
MAE

Fees
Slippage
Funding
Execution latency
```

---

# 42. RESEARCH METRICS

Do not optimize for win rate alone.

Measure:

* expectancy
* profit factor
* win rate
* average win
* average loss
* median R
* net R
* MFE
* MAE
* planned RR
* realized R
* target-hit rate
* MTF-trail exit rate
* initial-SL rate
* maximum drawdown
* recovery factor
* Sharpe
* Sortino
* Calmar
* consecutive losses
* turnover
* fees
* slippage
* funding
* time in market
* tail losses

---

# 43. CORE PROFITABILITY PRINCIPLE

The goal is:

> **Positive expectancy after realistic costs with statistical and out-of-sample robustness.**

Do not define success as:

> "The system must have 60% win rate."

A system could theoretically have:

```text
40% wins
Average winner = +5R
Average loser = -1R
```

and still have strong expectancy.

Conversely:

```text
70% wins
Average winner = +0.5R
Average loser = -2R
```

can lose money.

The MTF trailing hypothesis should therefore be evaluated on:

* realized expectancy
* profit factor
* drawdown
* MFE retention
* distribution of trail exits
* robustness

not merely win rate.

---

# 44. MTF TRAILING RESEARCH HYPOTHESIS

The central management hypothesis is:

> MTF structural trailing can convert a portion of trades that fail to reach the HTF target into profitable or reduced-loss exits while preserving enough upside participation to improve overall expectancy.

This hypothesis must be tested.

Measure:

```text
Without MTF trail
vs
With MTF structural trail
```

Compare:

* win rate
* expectancy
* PF
* drawdown
* MFE retention
* average realized R
* target-hit rate
* loss distribution
* tail behaviour

Do not assume the result.

---

# 45. RESEARCH DISCIPLINE

The platform must use controlled experimentation.

When a failure is discovered:

```text
Failure
→ hypothesis
→ pre-register
→ isolate
→ test
→ validate
→ OOS
→ stress
```

Do not simultaneously change:

* entry
* stop
* target
* trailing
* regime
* indicators
* risk

because attribution becomes impossible.

---

# 46. DEVELOPMENT / VALIDATION / OOS

Historical data must be divided temporally.

### Development

Used for hypothesis discovery.

### Validation

Used for testing generalization.

### OOS

Must remain untouched until the strategy is frozen.

Never repeatedly inspect OOS results and then modify the strategy.

---

# 47. COST STRESS

The strategy must survive realistic:

* trading fees
* spread
* slippage
* funding
* execution latency

Stress testing should include adverse execution scenarios such as increased transaction costs.

A strategy that is profitable only under perfect fills is not production-ready.

---

# 48. REGIME ROBUSTNESS

Evaluate performance across:

* bull markets
* bear markets
* sideways markets
* high volatility
* low volatility
* volatility expansion
* volatility contraction
* market shocks

Determine whether profitability is broad or dependent on one narrow historical environment.

---

# 49. CROSS-ASSET ROBUSTNESS

Evaluate independently:

```text
BTC
ETH
SOL
```

Then evaluate pooled performance.

Measure:

* expectancy
* PF
* drawdown
* correlation
* trade frequency
* execution quality

---

# 50. CROSS-TIMEFRAME ROBUSTNESS

Evaluate independently:

```text
SET 1
SET 2
SET 3
SET 4
SET 5
```

Then evaluate the combined portfolio.

Do not assume the strategy works identically across every timeframe.

---

# 51. NO-TRADE CONDITIONS

Reject a trade when required conditions are absent.

Examples:

* unclear HTF direction
* invalid HTF structure
* no valid HTF context
* MTF not aligned
* no MTF structural setup
* no valid MTF keyzone
* no MTF pullback/retest
* no valid LTF entry
* LTF not aligned
* invalid structural SL
* planned RR < 4R
* risk > 1%
* insufficient liquidity
* abnormal spread
* stale market data
* news restriction
* portfolio risk limit
* execution uncertainty
* system health failure

The system must prefer:

> **NO TRADE**

over low-quality trades.

---

# 52. ADAPTATION PRINCIPLE

The platform should adapt to changing market conditions.

However:

> **Adaptation must occur around the strategy, not by destroying the strategy.**

The core remains:

```text
HTF
↓
MTF
↓
LTF
↓
ENTRY
↓
LTF SL
↓
MTF TRAIL
↓
HTF TARGET
```

Adaptation may occur through:

* regime qualification
* volatility normalization
* risk adjustment
* liquidity filtering
* execution filtering
* portfolio allocation
* asset selection
* trade-frequency control

All such adaptations require evidence.

---

# 53. PRODUCTION LIFECYCLE

The system should progress through:

```text
RESEARCH_ONLY
↓
RESEARCH_VALIDATED
↓
PAPER_ELIGIBLE
↓
PAPER TRADING
↓
MICRO-LIVE ELIGIBLE
↓
MICRO-LIVE
↓
PRODUCTION ELIGIBLE
```

No stage may be skipped.

---

# 54. PAPER TRADING

Before real capital, validate the complete live pipeline:

* real-time data
* HTF structure
* MTF setup
* LTF entry
* SL
* target
* MTF trailing
* position sizing
* news filter
* regime filter
* execution simulation
* reconciliation
* restart recovery
* telemetry

---

# 55. MICRO-LIVE

Only after successful paper validation should small real capital be considered.

Compare:

```text
Backtest
vs
Paper
vs
Live
```

for:

* fills
* slippage
* fees
* latency
* win rate
* expectancy
* drawdown
* MFE
* MAE

If live behaviour materially diverges:

> STOP AND INVESTIGATE.

Do not automatically scale.

---

# 56. SELF-HEALTH / AUTONOMOUS SAFETY

The production system must continuously monitor:

* data freshness
* exchange connection
* broker connection
* order status
* position status
* account balance
* risk
* latency
* duplicate positions
* duplicate orders
* system heartbeat
* storage
* reconciliation
* execution errors

Critical failures must trigger:

> FAIL CLOSED.

---

# 57. KILL SWITCH

Emergency shutdown must exist.

Potential triggers:

* corrupted market data
* stale data
* exchange outage
* position mismatch
* unexpected balance
* unexpected execution
* excessive slippage
* repeated order failures
* risk-limit violation
* software integrity failure
* severe portfolio drawdown
* abnormal market conditions

Capital protection takes priority over trade generation.

---

# 58. ARCHITECTURAL LAYERS

The system should be separated into:

## Layer 1 — Market Data

Normalizes raw market information.

## Layer 2 — Market Structure

Determines:

* BOS
* CHOCH
* swings
* strong/weak swings
* trend

## Layer 3 — Keyzone Engine

Determines:

* OB
* FVG
* supply/demand
* liquidity
* imbalance
* keylevels

## Layer 4 — HTF Context Engine

Determines:

* HTF direction
* phase
* relevant zone
* structural destination

## Layer 5 — MTF Setup Engine

Determines:

* MTF counter-phase
* structural shift
* alignment
* new MTF structure
* MTF keyzone
* MTF pullback

## Layer 6 — LTF Entry Engine

Determines:

* liquidity
* LTF structural confirmation
* FVG/OB
* displacement
* entry

## Layer 7 — Risk Engine

Determines:

* structural SL
* position size
* maximum 1% risk
* portfolio risk

## Layer 8 — Trade Management

Controls:

* initial SL
* MTF structural trailing
* HTF target

## Layer 9 — Regime / Qualification

Controls:

* volatility
* liquidity
* market regime
* news

## Layer 10 — Portfolio Engine

Controls:

* aggregate risk
* correlation
* exposure
* drawdown

## Layer 11 — Execution

Handles:

* broker/exchange
* orders
* fills
* reconciliation

## Layer 12 — Research / Analytics

Measures:

* expectancy
* PF
* drawdown
* robustness
* statistical significance

## Layer 13 — Autonomous Operations

Handles:

* monitoring
* alerts
* recovery
* restart
* health
* kill switch

---

# 59. UNIVERSAL ASSET ARCHITECTURE

The system should conceptually be:

```text
                    UNIVERSAL STRATEGY
                           │
             ┌─────────────┴─────────────┐
             │                           │
        MARKET STRUCTURE             RISK ENGINE
             │                           │
      HTF → MTF → LTF              POSITION SIZE
             │                           │
        TRADE MANAGEMENT              <=1%
             │
        MTF TRAILING
             │
       HTF DESTINATION
             │
      ASSET-CLASS ADAPTER
             │
      ┌──────┼────────┐
      │      │        │
    CRYPTO FOREX   OTHER
      │      │        │
   EXCHANGE BROKER  VENUE
```

The core strategy remains unchanged.

Only asset-specific infrastructure changes.

---

# 60. INITIAL CRYPTO IMPLEMENTATION

The first implementation is cryptocurrency.

Initial universe:

```text
BTC
ETH
SOL
```

Initial five timeframe systems:

```text
1M / 1W / 1D
1W / 1D / 4H
1D / 4H / 1H
4H / 1H / 15m
15m / 5m / 1m
```

The system operates continuously because cryptocurrency markets operate continuously.

Later, the same strategy engine can be connected to other asset classes through appropriate adapters.

---

# 61. CANONICAL END-TO-END FLOW

The complete strategy is:

```text
MARK HTF MARKET STRUCTURE
        ↓
DETERMINE HTF TREND / DIRECTION
        ↓
MARK HTF KEYZONES / KEYLEVELS
        ↓
IDENTIFY HTF PHASE / CONTEXT
        ↓
IDENTIFY HTF STRUCTURAL DESTINATION
        ↓
WAIT FOR RELEVANT HTF CONTEXT
        ↓
ANALYSE MTF STRUCTURE
        ↓
ALLOW MTF COUNTER-TREND DEVELOPMENT
        ↓
WAIT FOR MTF STRUCTURAL SHIFT
        ↓
MTF ALIGNMENT WITH HTF
        ↓
FORM NEW MTF STRUCTURE
        ↓
MARK MTF KEYZONE / KEYLEVEL
        ↓
WAIT FOR MTF PULLBACK / RETEST
        ↓
ACTIVATE LTF
        ↓
LTF LIQUIDITY / ENTRY MODEL
        ↓
LTF STRUCTURAL ALIGNMENT
        ↓
LTF ENTRY
        ↓
LTF STRUCTURAL SL
        ↓
CALCULATE HTF TARGET
        ↓
CALCULATE PLANNED RR
        ↓
REJECT IF RR < 4R
        ↓
CALCULATE POSITION SIZE
        ↓
ENFORCE <=1% RISK
        ↓
EXECUTE
        ↓
MONITOR LTF INVALIDATION
        ↓
MTF STRUCTURAL TRAILING
        ↓
HOLD WHILE MTF REMAINS ALIGNED
        ↓
EXIT ON MTF STRUCTURAL DETERIORATION
        OR
HTF TARGET
        OR
LTF INITIAL INVALIDATION
        OR
EMERGENCY RISK EXIT
        ↓
RECONCILE
        ↓
RECORD COMPLETE TRADE TELEMETRY
        ↓
RETURN TO MARKET MONITORING
```

---

# 62. FUNDAMENTAL DESIGN PHILOSOPHY

The system must be:

**Structural**

because market structure establishes the hierarchy.

**Multi-timeframe**

because HTF, MTF and LTF perform different jobs.

**Risk-controlled**

because no individual trade may risk more than 1%.

**Asymmetric**

because planned RR must be at least 4R.

**Adaptive**

because market conditions change.

**Evidence-driven**

because additions must be proven.

**Execution-aware**

because backtest assumptions are not real execution.

**Autonomous**

because the eventual objective is 24/7 operation.

**Asset-agnostic**

because the core strategy should work across different asset classes.

**Research-governed**

because profitability must be demonstrated rather than assumed.

---

# 63. FINAL NON-NEGOTIABLES

The following are canonical:

1. HTF establishes directional bias.
2. HTF structure and keyzones are explicitly identified.
3. Every timeframe has independent structure.
4. MTF develops the setup.
5. MTF may initially be counter-direction during HTF pullback/context.
6. MTF must structurally realign toward HTF.
7. MTF creates its own post-alignment structure.
8. MTF creates its own setup keyzone.
9. Price must interact with/retest the MTF setup.
10. LTF provides the entry model.
11. LTF must align with HTF and MTF.
12. LTF structural reversal point is the initial SL.
13. HTF structural destination is the planned target.
14. Minimum planned RR is 4R.
15. There is no maximum planned RR.
16. Maximum individual trade risk is 1% of account equity.
17. MTF structural trailing is a core position-management mechanism.
18. MTF structural deterioration can trigger exit before HTF reversal.
19. HTF target and MTF trailing coexist.
20. Five timeframe sets are supported.
21. BTC, ETH and SOL are the initial crypto universe.
22. All timeframe sets operate independently.
23. The system is designed for eventual 24/7/365 autonomous operation.
24. The strategy core is asset-agnostic.
25. Crypto-specific infrastructure is isolated behind asset/execution adapters.
26. Indicators may be added only when evidence justifies them.
27. Market-regime intelligence may adapt qualification/risk but must not silently replace the strategy.
28. News restrictions must be point-in-time causal.
29. Execution must fail closed when state is uncertain.
30. Profitability must be demonstrated through rigorous research rather than assumed.

---

# 64. FINAL OBJECTIVE

The objective is to build a professional quantitative trading platform around one simple but deeply structured principle:

> **HTF determines where we want to trade.
> MTF determines whether the setup is developing in that direction.
> LTF determines when to enter.
> LTF determines the initial invalidation.
> HTF determines the structural destination.
> MTF determines whether the position should continue to be held.**

In compact form:

```text
HTF = DIRECTION
MTF = SETUP
LTF = ENTRY

LTF = INITIAL INVALIDATION
HTF = DESTINATION
MTF = TRAILING / POSITION MANAGEMENT
```

This same architecture must be reusable across asset classes.

For the initial implementation:

```text
ASSET CLASS = CRYPTO
ASSETS = BTC / ETH / SOL

SET 1 = 1M / 1W / 1D
SET 2 = 1W / 1D / 4H
SET 3 = 1D / 4H / 1H
SET 4 = 4H / 1H / 15m
SET 5 = 15m / 5m / 1m
```

The ultimate objective is not merely to produce a backtest.

It is to build a system capable of progressing from:

```text
Research
→ Validation
→ OOS
→ Paper
→ Micro-Live
→ Controlled Production
```

while preserving the canonical strategy architecture and continuously protecting capital.

The platform must never manufacture profitability.

If the architecture produces a durable edge:

**prove it.**

If it does not:

**identify why and improve it through controlled research.**

If no robust edge exists after disciplined research:

**NO VERIFIED EDGE.**
