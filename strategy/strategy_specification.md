
# PRODUCT 01: MASTER STRATEGY SPECIFICATION CONTRACT v1.1

**Product ID:** `APEX-PRODUCT-CRYPTO` (Product 01)  
**Parent Platform:** APEX Quant Platform (`Quantitative-Systems`)  
**Specification Standard:** v1.1-MASTER-LOCKED  

---

## PART A: PRODUCT DEFINITION & SCOPE

### 1. Mission Statement
The objective of Product 01 is to engineer a self-improving, autonomous capital asset whose decisions derive from a fixed market ontology, gated by a Market Suitability Engine, validated through evidence-driven research, protected by unbreakable mathematical risk firewalls, and executed across decoupled Live and Research engines.

### 2. Primary Asset Universe
Trading execution is restricted to Tier-1 high-liquidity crypto majors:

$$\text{Primary Asset Universe} = \{\text{BTC/USDT}, \text{ETH/USDT}, \text{SOL/USDT}\}$$

### 3. Execution Scales (Timeframe Sets)
The market model is fractal. The exact same 3-timeframe strategy logic runs across four operational execution scales:

| Timeframe Set | Trading Horizon | HTF (Destination & TP) | MTF (Navigation & Trail) | LTF (Execution & SL) |
| :--- | :--- | :--- | :--- | :--- |
| **SET 1** | Investing Horizon | 1 Month (1M) | 1 Week (1W) | 1 Day (1D) |
| **SET 2** | Position Trading Horizon | 1 Week (1W) | 1 Day (1D) | 4 Hour (4H) |
| **SET 3** | Swing Trading Horizon | 1 Day (1D) | 4 Hour (4H) | 1 Hour (1H) |
| **SET 4** | Intraday Scaling Horizon | 4 Hour (4H) | 1 Hour (1H) | 15 Minute (15M) |

---

## PART B: UNIVERSAL MARKET ONTOLOGY

Every single timeframe ($1\text{M}, 1\text{W}, 1\text{D}, 4\text{H}, 1\text{H}, 15\text{M}$) processes price action through an identical price action language:

$$\text{Market State}_T = \{ \text{Trend}, \text{Structure}, \text{Key Levels}, \text{Key Zones}, \text{Liquidity}, \text{Pullback}, \text{Continuation}, \text{Expansion}, \text{Reversal} \}$$

1. **Trend Direction:** Evaluates to `BULLISH` (Higher Highs / Higher Lows), `BEARISH` (Lower Highs / Lower Lows), or `RANGING` (horizontally bound).
2. **Break of Structure (BOS):** Candlestick body close beyond the previous structural swing high (bullish BOS) or swing low (bearish BOS), confirming trend extension.
3. **Change of Character (CHOCH):** Candlestick body close beyond the opposing structural swing low (Bullish to Bearish) or swing high (Bearish to Bullish), confirming trend reversal.
4. **Key Levels:** Horizontal Equal Highs (`EQH`) and Equal Lows (`EQL`) representing concentrated retail stop liquidity.
5. **Key Zones:** Order Blocks (`OB`) and Fair Value Gaps (`FVG`) representing institutional supply and demand footprints.
6. **Liquidity Sweeps:** Price wick piercing a mapped Key Level (`EQH`/`EQL`), sweeping stop liquidity, followed by an immediate candle body close back inside the structural boundary.

---

## PART C: 3-TIMEFRAME RESPONSIBILITY ALLOCATION

```text
  HTF (Higher Timeframe) ──► DESTINATION & PERMISSION
  • Determines Directional Bias (BULLISH / BEARISH).
  • Sets Expected Market Phase (PULLBACK / CONTINUATION).
  • Maps Structural Target Objective (TP = Protected Swing High/Low).
  • Verifies price interaction with an unmitigated HTF KeyZone.
  • NEVER executes orders; NEVER calculates stop losses.

  MTF (Middle Timeframe) ──► NAVIGATION & TRAILING
  • Confirms MTF Trend Alignment with HTF Bias.
  • Confirms MTF Structural Realignment (CHOCH/BOS) following HTF KeyZone touch.
  • Identifies active, unmitigated MTF Keyzones (Order Blocks & FVGs).
  • Manages dynamic structural trailing stop loss during active trade lifecycle.

  LTF (Lower Timeframe) ──► EXECUTION & INVALIDATION
  • Confirms micro execution trigger: Liquidity Sweep + Displacement Candle close.
  • Calculates Invalidation Stop Loss (SL = Structural KeyZone boundary).
  • NEVER determines market bias; NEVER sets macro targets.

```

---

## PART D: FORMAL DEFINITION OF MTF SETUP

An **MTF Setup** is officially valid if and only if all four conditions are satisfied:

1. **HTF KeyZone Mitigation:** HTF price action has penetrated into an active, unmitigated HTF KeyZone (`OB` or `FVG`).
2. **Trend Realignment:** MTF Trend Direction matches HTF Directional Bias (`BULLISH` == `BULLISH` or `BEARISH` == `BEARISH`).
3. **Structural Realignment:** MTF has printed a structural event (`CHOCH` or `BOS`) aligning with HTF Bias following HTF KeyZone interaction.
4. **Active KeyZone Availability:** An unmitigated MTF Order Block (`OB`) or Fair Value Gap (`FVG`) exists in the direction of HTF Bias.

---

## PART E: FORMAL DEFINITION OF LTF ENTRY MODEL

An **LTF Entry Trigger** is officially valid if and only if all four conditions occur sequentially:

1. **MTF KeyZone Interaction:** LTF price penetrates into the active MTF KeyZone range.
2. **Micro Liquidity Sweep:** LTF price sweeps an internal micro-swing high/low or `EQH`/`EQL` pool within the MTF KeyZone.
3. **Displacement Candle Close:** LTF prints a high-volume displacement candle whose body closes strongly in the direction of HTF Bias.
4. **Invalidation SL Placement:** Stop Loss (`SL`) is placed strictly at the structural invalidation boundary (the extreme wick low of a Bullish KeyZone or extreme wick high of a Bearish KeyZone).

---

## PART F: CORE STRATEGY FAMILY

### Strategy A: Pullback Riding

* **HTF State:** HTF confirms a major structure break (`BOS`). HTF Expected Phase is set to `PULLBACK`.
* **MTF Setup:** MTF trend initially opposes HTF bias during retracement. System waits for price to hit the HTF Keyzone and print an MTF `CHOCH` back into alignment, forming an MTF Keyzone.
* **LTF Execution:** LTF executes a liquidity sweep inside the MTF Keyzone followed by a displacement candle.

### Strategy B: Continuation Riding

* **HTF State:** HTF pullback is complete at an HTF Keyzone. HTF Expected Phase is set to `CONTINUATION`.
* **MTF Setup:** MTF trend is already aligned with HTF bias, printing sequential continuation `BOS` and active MTF Keyzones.
* **LTF Execution:** LTF executes a liquidity sweep inside the MTF Keyzone followed by a displacement candle as trend expansion resumes.

---

## PART G: MATH-ONLY RISK FIREWALL & POSITION SIZING

### Dynamic 1.0% Equity Risk Sizing

Risk per trade is capped at exactly $1.0\%$ of current account equity, calculated dynamically regardless of account size:

$$\text{Dollar Risk (\$)} = \text{Account Balance} \times 0.01$$

$$\text{Position Size (Lots/Units)} = \frac{\text{Dollar Risk}}{\lvert \text{Entry Price} - \text{Stop Loss Price} \rvert}$$

### Mandatory Reward-to-Risk Floor ($\ge 1:4$ R:R)

The distance between Entry Price and HTF Target Objective (`TP`) divided by the distance between Entry Price and LTF Invalidation (`SL`) must meet or exceed $4.0$:

$$\text{True Reward-to-Risk} = \frac{\lvert \text{HTF Target TP} - \text{Entry Price} \rvert}{\lvert \text{Entry Price} - \text{LTF Stop Loss} \rvert} \ge 4.0$$

$$\text{If True R:R} < 4.0 \longrightarrow \text{REJECT TRADE (Code: RISK\_RR\_BELOW\_4)}$$

---

## PART H: DYNAMIC TRADE MANAGEMENT & TRAILING STOP

1. **Initial Stop Loss:** Placed at structural keyzone invalidation boundary on LTF.
2. **Take Profit Target:** Fixed at HTF Protected High (for Longs) or HTF Protected Low (for Shorts).
3. **Dynamic MTF Trailing SL:** As price advances, the stop loss trails dynamically behind newly formed MTF protected swing lows (for Longs) or MTF protected swing highs (for Shorts).

```

