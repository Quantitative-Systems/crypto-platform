# Institutional Proof of Work Samples (`examples/`)

This directory provides executable, verifiable, end-to-end demonstration scripts showcasing the core capabilities of the Quantitative Crypto Trading Platform.

---

## Available Proof Samples

### 1. Multi-Timeframe Alpha Proof of Work
**Script**: [`examples/run_alpha_proof_sample.py`](run_alpha_proof_sample.py)

Demonstrates the verified institutional Alpha Champion discovering profitable edge across 8.5+ years of continuous Binance market history:
- **3-Timeframe Dataset Alignment**: HTF (4h) structural bias $\rightarrow$ MTF (1h) Point of Interest (OB/FVG/Liquidity) $\rightarrow$ LTF (15m) Market Structure Shift (MSS/CHOCH) entry trigger.
- **Asymmetric Target Geometry**: Strict minimum $R \ge 4.0\text{R}$ reward:risk requirement.
- **Realistic Friction**: 5.0 bps taker fee + 2.0 bps slippage accounted on every leg.
- **Walk-Forward Invariant**: Displays DEV, VAL, and Out-of-Sample (OOS) performance splits.

#### How to Run:
```bash
# Platform Champion (Ethereum - ETH/USDT)
py -3.14 examples/run_alpha_proof_sample.py

# Bitcoin Champion (BTC/USDT)
py -3.14 examples/run_alpha_proof_sample.py --btc

# Solana Champion (SOL/USDT)
py -3.14 examples/run_alpha_proof_sample.py --sol
```

#### Expected Key Metrics:
- **Ethereum**: 298 trades, **63.4% Win Rate**, **4.35 Profit Factor**, **+320.61R Net Alpha**, +1.076R Expectancy.
- **Bitcoin**: 301 trades, **60.8% Win Rate**, **5.78 Profit Factor**, **+411.50R Net Alpha**, +1.367R Expectancy.

---

### 2. Autonomous 24/7 Paper Execution & Risk Firewall Proof
**Script**: [`examples/run_paper_execution_sample.py`](run_paper_execution_sample.py)

Demonstrates the real-time execution engine and safety governance loop operating under simulated live conditions ($0.00 real capital risk):
- **Deterministic Clock Fabric**: Causally validated tick processing.
- **Feed Health Monitoring**: Millisecond latency, tick gap, and feed status checking.
- **Autonomous Decision Engine**: Exhaustive deterministic No-Trade Taxonomy firewall (`NO_TRADE_SPREAD_TOO_HIGH`, `NO_TRADE_REGIME_UNFAVORABLE`, `NO_TRADE_EVENT_FREEZE`).
- **Portfolio Risk Governor**: Capital allocation, factor beta heat limits (max 3% total heat), and position haircutting.
- **Execution Simulator**: Realistic market orders with exchange latency modeling ($\ge 15$ ms) and spread crossing.
- **Immutable Decision Ledger**: Every decision (TRADE and NO_TRADE) logged into an audit trail with timestamped records.

#### How to Run:
```bash
py -3.14 examples/run_paper_execution_sample.py
```

---

## Verification & Architecture Compliance
Both samples adhere strictly to the platform invariants:
- **Zero Lookahead Bias**: Bar $t$ decisions are computed solely from data available at or before $t$.
- **Decoupled Architecture**: Strategy logic is isolated from the frozen Market Model ($HOW, WHERE, WHAT$).
- **Deterministic Reproducibility**: Fixed seed and exact causal replay yield byte-identical results.
