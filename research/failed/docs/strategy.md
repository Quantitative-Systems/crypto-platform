# Strategy Lifecycle & Hypotheses

The platform executes strategy logic as a stateful, chronological cascade across multiple timeframes.

## Canonical Architecture Cascade

```text
                  HTF BIAS
                       │
                       ▼
                  MTF SETUP
                       │
                       ▼
                  MTF RETEST
                       │
                       ▼
                  LTF ENTRY
                       │
                       ▼
               LTF INVALIDATION
                       │
                       ▼
                  HTF TARGET
                       │
                       ▼
              MTF STRUCTURAL TRAIL
```

## Multi-Timeframe Configurations
The system evaluates hypotheses independently across isolated structural combinations.

| Set | HTF | MTF | LTF | Trading Horizon |
|---|---|---|---|---|
| Set 1 | 1M | 1W | 1D | Macro / Position |
| Set 2 | 1W | 1D | 4H | Position / Swing |
| Set 3 | 1D | 4H | 1H | Swing / Intraday |
| Set 4 | 4H | 1H | 15M | Intraday |

## Hypothesis A: Pullback Riding
This hypothesis tests the scenario where the HTF establishes a clear trend, pulls back to an HTF structural KeyZone, forces the MTF to counter-trend, and then re-aligns. We look to enter on the MTF's subsequent structural realignment and retest.

**Chronological Flow:**
`HTF Trend → HTF Pullback → HTF KeyZone Interaction → MTF Countertrend → MTF Realignment → MTF KeyZone Setup → MTF Retest → LTF Execution → LTF Stop Loss → HTF Target → MTF Trail`

## Hypothesis B: Continuation Riding
This hypothesis tests environments where the HTF has already interacted with its structural origin, and the prevailing trend is simply continuing. We look for the MTF to build a setup in alignment with the HTF and execute upon its retest.

**Chronological Flow:**
`HTF Continuation Context → MTF Setup → MTF Structural Realignment → MTF KeyZone Setup → MTF Retest → LTF Execution → LTF Stop Loss → HTF Target → MTF Trail`

## State Tracking
The `CandidateTracker` operates as a state machine. Rather than evaluating a single snapshot in time, candidates transition through statuses such as `WAIT_MTF_ALIGNMENT`, `WAIT_LTF_TRIGGER`, `RISK_GATE`, and `ENTERED`. If conditions invalidate at any step (e.g. HTF bias changes before LTF trigger), the candidate is cleanly terminated and recorded.
