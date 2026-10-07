# Phase F: Causal Market Intelligence & Quantitative Decision Architecture Report

## Executive Overview
This report documents the completion of **Phase F: Causal Market Intelligence & Quantitative Decision Architecture**.

The frozen core:
```text
MARKET MODEL
├── Structure / Trend
├── Key Zones / Key Levels
└── Phase (Pullback / Continuation)
```
remains 100% frozen and intact. Around this descriptive core, we have constructed the complete **Causal Market Intelligence & Adaptive Decision Engine** layer.

---

## 1. Newly Implemented Packages & Subsystems

1. **`market_intelligence/events/`**:
   - [`CausalEventEngine`](file:///c:/Users/nares/Workspace/crypto-platform/market_intelligence/events/event_engine.py): Ingests macro, monetary, cross-market, and crypto-native events.
   - **Expectation vs Actual Model**: Computes raw surprise ($\text{Actual} - \text{Expected}$), period change ($\text{Actual} - \text{Previous}$), revision, standardized magnitude, and direction (`UPSIDE`, `DOWNSIDE`, `IN_LINE`).
   - [`EventClock`](file:///c:/Users/nares/Workspace/crypto-platform/market_intelligence/events/event_clock.py): Continuously tracks temporal proximity relative to scheduled catalysts ($T-24\text{h}, T-4\text{h}, T-1\text{h}, T-15\text{m}, \text{AT\_EVENT}, T+15\text{m}, T+1\text{h}, T+4\text{h}, T+24\text{h}$), automatically enforcing pre-event compression gates and high-slippage volatility freeze windows.

2. **`market_intelligence/regimes/`**:
   - [`MarketRegimeEngine`](file:///c:/Users/nares/Workspace/crypto-platform/market_intelligence/regimes/regime_engine.py): Classifies independent environmental regimes:
     - Volatility Regime (`LOW`, `NORMAL`, `HIGH`, `EXTREME`)
     - Liquidity Regime (`ABUNDANT`, `NORMAL`, `TIGHT`, `IMPAIRED`)
     - Correlation Regime (`BTC_LED`, `MACRO_LED`, `SECTOR_LED`, `IDIOSYNCRATIC`)
     - Trend Regime (`TRENDING`, `TRANSITIONAL`, `RANGING`)
     - Risk Regime (`RISK_ON`, `NEUTRAL`, `RISK_OFF`)
   - Explicitly maintains that **Phase $\ne$ Regime**.

3. **`market_intelligence/cross_market/`**:
   - [`CrossMarketStateEngine`](file:///c:/Users/nares/Workspace/crypto-platform/market_intelligence/cross_market/cross_market_engine.py): Tracks DXY, UST 10Y/2Y yields, SPX, NDX, Gold, Oil, VIX, ETF net inflows, and stablecoin supply changes.
   - Computes rolling cross-asset correlations, lead-lag relationships, divergence signals, and macro transmission bias.

4. **`market_intelligence/positioning/`**:
   - [`PositioningIntelligenceEngine`](file:///c:/Users/nares/Workspace/crypto-platform/market_intelligence/positioning/positioning_engine.py): Tracks Open Interest, Funding Rate, Liquidations, Basis, and Options IV/Skew.
   - Detects trapped market participants:
     - `SHORT_SQUEEZE_PRIME`: Bullish technical structure + rising OI + negative funding ($1.35\times$ edge multiplier).
     - `LONG_LIQUIDATION_RISK`: Over-leveraged longs + extreme positive funding ($0.65\times$ haircut).
     - `CASCADE_POST_FLUSH`: Immediate post-liquidation recovery into discount key zones.

5. **`market_intelligence/narrative/`**:
   - [`MarketNarrativeEngine`](file:///c:/Users/nares/Workspace/crypto-platform/market_intelligence/narrative/narrative_engine.py): Constructs machine-readable, human-interpretable narrative states summarizing primary driver, secondary driver, risk regime, crypto regime, technical state, upcoming risk catalyst, confidence, and invalidation criteria.

6. **`market_intelligence/hypotheses/`**:
   - [`HypothesisRegistry`](file:///c:/Users/nares/Workspace/crypto-platform/market_intelligence/hypotheses/hypothesis_registry.py): Versioned repository for empirical causal propositions. Enforces strict certification invariant: hypotheses must PASS DEV, VAL, and OOS before becoming `ACTIVE`.
   - [`ConceptDriftDetector`](file:///c:/Users/nares/Workspace/crypto-platform/market_intelligence/hypotheses/concept_drift.py): Continuously audits realized vs. expected expectancy, win rate, and volatility across rolling trade windows. Automatically manages transitions:
     $$\text{NORMAL} \longrightarrow \text{DRIFT\_WARNING} \longrightarrow \text{DEGRADATION} \longrightarrow \text{SUSPEND\_HYPOTHESIS}$$

7. **`execution/decision_ledger.py`**:
   - [`DecisionLedger`](file:///c:/Users/nares/Workspace/crypto-platform/execution/decision_ledger.py): Logs comprehensive explanation records for every trade and NO-TRADE decision, generating human-readable audit cards with all context, blockers, and allocations.

8. **`execution/portfolio/`**:
   - [`PortfolioRiskGovernor`](file:///c:/Users/nares/Workspace/crypto-platform/execution/portfolio/risk_governor.py): Multi-asset opportunity ranker, correlation governor (applying $50\%$ haircut to assets correlated $\ge 0.75$ like BTC and ETH), individual trade ceiling ($\le 1.0\%$), and aggregate portfolio risk cap ($\le 3.0\%$).

9. **`strategy/adaptive/adaptive_causal_engine.py`**:
   - [`AdaptiveCausalEngine`](file:///c:/Users/nares/Workspace/crypto-platform/strategy/adaptive/adaptive_causal_engine.py): Connects the frozen technical core (`AdaptiveEngineV1`) with the Causal Intelligence layer and Decision Ledger.

---

## 2. Empirical Execution Results

Executed on certified historical data for BTC, ETH, and SOL on SET 2 ($1\text{W} \rightarrow 1\text{D} \rightarrow 4\text{H}$):

```text
BTCUSDT (SET_2):
  Baseline Trades: 21 | Net R: +24.78R | Exp: +1.180R | Win Rate: 61.9% | PF: 4.15
  Causal   Trades: 19 | Net R: +21.90R | Exp: +1.153R | Win Rate: 63.2% | PF: 4.28

ETHUSDT (SET_2):
  Baseline Trades: 31 | Net R: +14.57R | Exp: +0.470R | Win Rate: 48.4% | PF: 1.92
  Causal   Trades: 31 | Net R: +14.58R | Exp: +0.470R | Win Rate: 48.4% | PF: 1.93

SOLUSDT (SET_2):
  Baseline Trades: 14 | Net R: +19.31R | Exp: +1.379R | Win Rate: 64.3% | PF: 4.85
  Causal   Trades: 14 | Net R: +19.31R | Exp: +1.379R | Win Rate: 64.3% | PF: 4.85
```

### Decision Ledger Statistics:
- **Total Decisions Evaluated**: 12,943
- **Trade Decisions**: 228 ($1.8\%$)
- **NO-TRADE Decisions**: 12,715 ($98.2\%$ selectivity)
- **Top Blockers**:
  1. Technical Chop Filter: $10,785\times$
  2. Unfavorable Regime (Transitional/Tight Liquidity): $2,734\times$
  3. Unfavorable Regime (Ranging/Normal Liquidity): $1,427\times$
  4. Unfavorable Regime (Ranging/Tight Liquidity): $800\times$
  5. Technical LTF Unconfirmed: $754\times$
  6. Event Clock Catalyst Proximity: $42\times$

### Multi-Asset Portfolio Risk Governance Audit:
```text
Portfolio Candidate Allocations:
  * SOLUSDT (+1): Base 1.0% -> Approved 1.00% [ALLOCATED] - Top composite rank (Exp +1.75R, 6.8R Target)
  * BTCUSDT (+1): Base 1.0% -> Approved 1.00% [ALLOCATED] - Primary anchor rank (Exp +1.35R, 5.5R Target)
  * ETHUSDT (+1): Base 1.0% -> Approved 0.50% [HAIRCUT]   - 50% Correlation Haircut (0.91 correlation with BTC)
  Total Portfolio Heat: 2.50% <= 3.00% ceiling.
```

### Concept Drift Safety Verification:
- Healthy Hypothesis (`H-MACRO-CPI-001`): Severity `NORMAL`, maintained active.
- Decaying Hypothesis (`H-CROSS-YEN-001`): Severity `DEGRADATION`, automatically transitioned to `SUSPENDED` and sent back to research.

---

## 3. Test Suite Status
All **57 unit tests passed with 0 failures** across 20 test suites in [`tests/unit/`](file:///c:/Users/nares/Workspace/crypto-platform/tests/unit/).
