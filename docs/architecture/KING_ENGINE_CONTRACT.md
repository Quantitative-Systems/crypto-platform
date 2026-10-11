# STRATA — KING ENGINE CONTRACT

## Contract Specification: Domain A Protected Intelligence

### 1. Identity & Primacy
- **Engine Name:** STRATA King Engine (`STRATA_KING_ENGINE`)
- **Domain:** `DOMAIN_A_KING` (Highest Platform Priority)
- **Scientific Heritage:** Phase Q.2 Unified Fractal State Engine + Phase R Continuous Decision Pipeline
- **Immutable Contract Hash:** `8fbc923a104e7688c3a9f0e4b8592c30dfb0b9a67a84511d5e49f8721c432098`

---

## 2. Protected Non-Negotiable Invariants

1. **Frozen Market Model:**
   - 3 Top-Level Domains: `STRUCTURE_TREND`, `KEY_ZONES_LEVELS`, `PHASE`.
   - 2 Phases: `PULLBACK`, `CONTINUATION`.
   - Continuous 7-Timeframe Hierarchy: $1M \to 1w \to 1d \to 4h \to 1h \to 15m \to 3m$.
   - 5 Overlapping Triad Sets (Sets 1 to 5).
   - Fixed confidence scoring formula:
     $$\text{Confidence} = 0.35 \times \text{CrossSet} + 0.25 \times \text{Set2Alignment} + 0.20 \times \text{Set3Alignment} + 0.15 \times \text{Set4Alignment} + 0.05 \times \text{MicroConfirm}$$

2. **Reward-to-Risk Floor:**
   - Minimum Target Floor: **$\ge 4.0\text{R}$**.
   - Any opportunity with target geometry $< 4.0\text{R}$ is strictly rejected.

3. **Risk Governors:**
   - Single-Trade Risk Limit: $\le 1.0\%$.
   - Single Base-Asset Exposure Limit: $\le 1.0\%$.
   - Maximum Aggregate Portfolio Heat: $\le 3.0\%$.

4. **Zero-Capital Lock:**
   - Real Capital Allocation: **$\$0.00$** locked fail-closed.
   - Operating Environment: `SHADOW` / `PAPER` until explicit multi-signature authorization.

5. **Causal Execution Guarantee:**
   - Only confirmed **closed candles** (`is_closed=True`) trigger downstream evaluations.
   - Zero lookahead, zero synthetic data interpolation.

---

## 3. Stable Integration Interface

External subsystems (Autonomous Agent, Strategy Lab, Web Terminal, Mobile Client) interact with King Engine solely through [`KingEngineAdapter`](file:///c:/Users/nares/Workspace/crypto-platform/execution/king/king_engine_contract.py).

```python
from execution.king.king_engine_contract import KingEngineAdapter

adapter = KingEngineAdapter()
card = adapter.evaluate(
    symbol="BTCUSDT",
    price=64000.0,
    candle_open_ts=1728345600000,
    fractal_states=states,
    account_equity=100000.0,
)
```

Direct mutation of King Engine parameters or state weights is cryptographically prohibited by `KingEngineProtectionGuard`.
