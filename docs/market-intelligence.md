# Product 01: Market Intelligence

Product 01 converts raw OHLCV market data into a deterministic, causality-preserved Market Ontology. This layer is mathematically isolated; it produces state payloads but possesses no knowledge of trading setups, entry triggers, or capital risk.

## Pipeline Architecture
`OHLCV → Raw Swings → Market Structure → Liquidity → KeyZones → Market Phase → Trend → Validation → Market State Payload`

### 1. Raw Swing Engine
Identifies causal market extremes (Swing Highs, Swing Lows) utilizing chronological confirmation constraints. It guarantees that an extreme is only recognized *after* the requisite confirmation candles have printed, enforcing temporal causality.

### 2. Market Structure Engine
Consumes raw swings to map the underlying structural lattice. 
Identifies structural events: `EXTERNAL_BOS`, `EXTERNAL_CHOCH`, `INTERNAL_BOS`, `INTERNAL_CHOCH`, `MSS`, and `FAILED_BOS`.
Maintains the dealing range (Protected Highs / Protected Lows).

### 3. Liquidity Engine
Maps explicit structural liquidity pools (BSL, SSL, EQH, EQL, Internal, External).
Models the complete lifecycle of a liquidity pool: `ACTIVE → SWEPT → CONSUMED`.

### 4. KeyZone Engine
Detects and manages Order Blocks (OB) and Fair Value Gaps (FVG).
Enforces KeyZone lifecycle: `UNMITIGATED → MITIGATED → INVALIDATED`.
KeyZones are fundamentally linked to structural causation (e.g., the exact block that initiated a structural BOS).

### 5. Phase Engine
Classifies the current state of market delivery based on structural events and KeyZone mitigation states. 
Regimes identified: `ACCUMULATION, EXPANSION, PULLBACK, CONTINUATION, DISTRIBUTION, REVERSAL, COMPRESSION`.

### 6. Trend Engine
Derives a standardized directional bias (`BULLISH, BEARISH, RANGING`) based on structural precedence and phase combinations.

### 7. Validation Engine
Provides final geometric and chronological sanity checks on structural displacement to filter out noisy wicks that lack genuine structural significance.

### 8. Aggregation Contract: `MarketStatePayload`
The culmination of Product 01 is an immutable snapshot payload that explicitly defines the market's ontology at `Timestamp T`. This is the exclusive contract passed to Product 02.
