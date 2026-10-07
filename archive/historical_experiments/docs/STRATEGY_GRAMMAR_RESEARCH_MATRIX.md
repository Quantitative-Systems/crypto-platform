# QCP Strategy Grammar Research Matrix

This matrix tracks the hypothesis testing of specific HTF/MTF/LTF combinations.

## 1. Trend Families

| Family ID | HTF Bias | MTF Setup | LTF Entry | Primary Asset | Status | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **TRND-01** | EMA Alignment (50/200) | Pullback to fast EMA | Engulfing / Displacement | BTC, ETH | **Pending Audit** | The canonical trend continuation baseline. |
| **TRND-02** | SMC Market Structure | FVG Tap | Shift in Market Structure | SOL, AVAX | **In Development** | Relies on fractal high/low mapping. |
| **TRND-03** | MACD Momentum | Oscillator Reset | Momentum Hook | BNB | **Planned** | Standard momentum-trend alignment. |

## 2. Volatility / Breakout Families

| Family ID | HTF Bias | MTF Setup | LTF Entry | Primary Asset | Status | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **VOL-01** | Range Contraction (ATR) | Bollinger Squeeze | Vol Expansion Breakout | SOL, LINK | **Pending Audit** | Best for Set 3 / Set 4. |
| **VOL-02** | High Vol Regime | Opening Range Break | Volume Confirmation | DOGE, XRP | **Planned** | Highly sensitive to taker fees. |

## 3. Mean Reversion Families

| Family ID | HTF Bias | MTF Setup | LTF Entry | Primary Asset | Status | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **REV-01** | Over-extended (RSI > 80) | Structural Divergence | Rejection Pinbar | ADA | **Planned** | Requires strict stop-loss logic; low win-rate, high R:R. |
| **REV-02** | Bollinger Band Excursion | V-Shape Reversal | Engulfing | BTC | **Planned** | Often fails in crypto during macro trends. |

## 4. Relative Value / Arbitrage Families

| Family ID | HTF Bias | MTF Setup | LTF Entry | Primary Asset | Status | Notes |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **RV-01** | Cointegration / Z-Score | Z-Score > 2.0 | Mean Reversion | ETH/BTC | **Pending Audit** | Statistical arbitrage. Requires accurate simultaneous quotes. |
| **RV-02** | Spot / Perp Basis | Premium > threshold | Convergence | BTC | **BLOCKED** | Missing historical funding rate data. |

---

### Research Lifecycle Stages

1. **Ideation**: Defined in the grammar, awaiting coding.
2. **In Development**: Signal math is being written.
3. **Pending Audit**: Runs through DEV, but needs Walk-Forward OOS confirmation.
4. **Quarantined**: Failed OOS validation. Kept for historical reference to prevent re-testing.
5. **Promoted**: Survived OOS, eligible for paper trading / production allocation.
