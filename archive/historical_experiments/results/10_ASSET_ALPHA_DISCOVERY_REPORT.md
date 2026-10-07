# 10-ASSET ALPHA DISCOVERY REPORT
## EABG-002: Falsification-First Empirical Discovery

**Report Date**: 2026-09-17T14:47:42+00:00

### 1. Asset Certification Matrix
- BTC/USDT: 1D, 4H, 1H, 15m (Certified)
- ETH/USDT: 1D, 4H, 1H, 15m (Certified)
- SOL/USDT: 1D, 4H, 1H, 15m (Certified)
- BNB/USDT: 1D, 4H, 1H, 15m (Certified)
- XRP/USDT: 1D, 4H, 1H, 15m (Certified)
- ADA/USDT: 1D, 4H, 1H, 15m (Certified)
- DOGE/USDT: 1D, 4H, 1H, 15m (Certified)
- AVAX/USDT: 1D, 4H, 1H, 15m (Certified)
- LINK/USDT: 1D, 4H, 1H, 15m (Certified)
- LTC/USDT: 1D, 4H, 1H, 15m (Certified)

### 2. Datasets Used
- Binance Spot 1D, 4H, 1H, 15m historical candles.
- Partitions: DEV (2021-2022), VAL (2023), OOS (2024-2026).

### 3. Strategies Evaluated
- TrendStrategy
- BreakoutStrategy
- VolatilityStrategy
- MeanReversionStrategy
- RelativeValueStrategy
- MomentumStrategy

### 4. Number of Hypotheses Tested
- **240** (10 assets * 4 timeframes * 6 strategy families)

### 5. Number Falsified
- **240** total falsified.
  - 229 at Phase 1 (Baseline)
  - 3 at Phase 2 (Adversarial Friction)
  - 8 at Phase 3 (Locked OOS)

### 6. Number Surviving
- **0**

### 7. Net Performance
- All surviving candidates from Phase 2 exhibited **negative net edge** in the Locked OOS period, failing to produce positive net expectancy.

### 8. Friction Assumptions
- Baseline: 5 bps slippage, taker fees.
- Adversarial: 2x friction (15 bps taker, 6 bps slippage, 2 bps spread) applied in Phase 2.

### 9. Adversarial Results
- 3 out of 11 positive baselines failed to survive adversarial friction.

### 10. OOS Results
- The 8 remaining robust candidates failed to generate positive net edge in the 2024-2026 OOS dataset. 

### 11. Cross-Asset Results
- Edge decayed across all assets out-of-sample. No single asset yielded a robust survivor across regimes.

### 12. Regime Results
- N/A. All strategies failed prior to formal regime stratification.

### 13. Drawdowns
- Out-of-sample performance experienced terminal drawdowns failing capital preservation minimums.

### 14. Portfolio Concentration
- 0% (No capital allocated due to zero survivors).

### 15. Evidence Lifecycle State
- Falsified.

### 16. Reasons for Rejection
- Lack of genuine positive net expectancy in OOS environments. Strategies were overfit to DEV/VAL regimes and could not overcome institutional transaction costs out-of-sample.

### 17. Data Limitations
- Occasional missing 15m/1H data points, but robust enough for the 10-asset universe evaluation. 

### 18. Unresolved Problems
- The canonical strategy models lack sufficient predictive power or structural target reachability to overcome realistic market friction over time.

### 19. Forward-Paper Status
- Active and pending verification. `production/forward_paper_daemon.py` must be maintained and verified for future robust candidates.

## ZERO SURVIVORS

All tested hypotheses failed the rigorous multi-stage falsification pipeline. The system correctly preserved capital by not adopting fragile strategies. **Research outcome is considered successful.**