# Open-Source Research Notes: Freqtrade & FreqAI

## 1. Executive Summary
- **Repository:** [`freqtrade/freqtrade`](https://github.com/freqtrade/freqtrade)
- **License:** GPL-3.0 (Copyleft)
- **Core Paradigm:** Event-loop execution engine with vectorized pandas/numpy strategy evaluation and a dedicated machine learning subsystem (FreqAI).
- **Relevance to Crypto-Platform:** Exemplary patterns in incremental data downloading, background ML retraining workers, zero-leakage z-scoring/scaling, and outlier-based regime shift detection.

---

## 2. Key Architectural Components

### A. Data Layer & Ingestion Pipeline
- **Fetcher Mechanism:** Wraps CCXT REST endpoints (`fetch_ohlcv`) with automatic pagination, exponential backoff, and local rate-limit compliance.
- **Storage:** Stores raw 1m/5m/1h candles in compressed Feather/HDF5 or JSON files with metadata headers.
- **Gap Detection:** Detects missing timestamp sequences and handles candle gaps explicitly (either forward-fill or drop).
- **Informative Pairs / Timeframes:** Allows a strategy to request auxiliary timeframes (e.g. 1h, 1d) or benchmark assets (e.g. BTC/USDT) which are resampled and merged onto the base dataframe.

### B. FreqAI (Machine Learning Subsystem)
FreqAI is split into three decoupled objects:
1. `IFreqaiModel`: Persistent abstraction managing data collection, feature engineering, model training, and inferencing across Scikit-Learn, LightGBM, XGBoost, CatBoost, and PyTorch.
2. `FreqaiDataKitchen`: Non-persistent, pair-specific worker that computes technical indicators, scales features using in-sample statistics only (preventing lookahead), and splits chronologically into train/test sets.
3. `FreqaiDataDrawer`: Persistent coordinator that serializes trained models, metadata, and historical predictions to disk.

### C. Dissimilarity / Outlier Detection (Regime Protection)
FreqAI introduces a critical concept for crypto regimes:
- **PCA / Distance Metric:** Evaluates the Euclidean or Mahalanobis distance between current incoming market features and the training feature distribution.
- **Do-Not-Trade Boundary:** If incoming market volatility or feature distributions exceed a predefined distance threshold (indicating an unfamiliar regime such as a flash crash or extreme expansion), the model emits `DI_VALUES > DI_THRESHOLD` and suppresses entries.

---

## 3. License & Intellectual Property Governance
> [!CAUTION]
> Freqtrade is licensed under **GPL-3.0**. Under no circumstances should source code, files, or direct functions from Freqtrade be copied into the `crypto-platform` repository. All architectural inspirations must be clean-room reimplemented in original Python code.

---

## 4. Architectural Lessons for Crypto-Platform
1. **Separation of Feature Extraction from Decision Logic:**
   - In Freqtrade, `populate_indicators` is strictly separated from `populate_entry_trend`.
   - In our platform, this translates directly to the **Observation Registry** pattern: `MarketState -> Observations -> StrategyHypothesis`.
2. **Leakage-Safe Scaling:**
   - Any mathematical normalization (e.g. rolling z-scores or volatility normalization) must fit parameters on in-sample bars only and transform out-of-sample bars causally.
3. **Regime Distance Filter:**
   - We can register a `VolatilityRegimeObservation` that flags extreme outlier volatility to conditionally inhibit entries without altering the core Market Model.
