# STRATA — Public Brand Simplification & Visual Rebuild Report

**Document Date:** 2026-10-08  
**Project:** STRATA / crypto-platform  
**Mission:** Commercial SaaS Brand Simplification & Public Website Redesign  
**Core Brand Message:** **Think. Build. Automate.**  
**Status:** Certified & Verified (`FORWARD_VALIDATION_READY` / `PRODUCT_ACCEPTANCE_READY`)  

---

## 1. Executive Summary: Before vs. After Philosophy

| Dimension | Before (Prototype & Technical Clutter) | After (Simplified Commercial Fintech SaaS) |
|:---|:---|:---|
| **Primary Mental Model** | Looked like an internal technical audit report and AI dashboard. Exposed frozen contracts, 7-TF matrices, and internal jargon on the homepage. | Modern, clean algorithmic-trading SaaS inspired by top fintech platforms. Simple enough for any trader to understand in 10 seconds. |
| **Core Message** | Technical thesis on causal fractal alignment and research contracts. | **"Think. Build. Automate."** — Turn your trading ideas into automated crypto strategies. |
| **Top Navigation** | 12 technical links competing for attention: *How It Works, Markets, KING Core, Strategies, Strategy Lab, Forward Val, Security, Pricing, FAQ, Sign In, Get Started, Terminal*. | 5 clean commercial links: `Home`, `About`, `What's New`, `Strategies`, `Pricing` + `Contact`, `Sign In`, and dominant `Get Started` CTA. |
| **Hero Composition** | Center-weighted or overly dense, featuring contract hashes, $\ge 4\text{R}$ formulas, and terminal screens. | High-impact left-aligned headline with STRATA blue emphasis, 2-line clear value proposition, and crisp tilted product card on right. |
| **Color System** | Heavy dark navy backgrounds, blue glowing neon borders, and floating particles. | Crisp white/off-white background, near-black typography, STRATA royal blue primary accent, sky-blue secondary highlights, and controlled red accents. |
| **Public vs. Terminal** | Attempted to reproduce the Bloomberg-style terminal on the public landing page. | Strict architectural decoupling: Public site is light, commercial, and editorial; Terminal (`/app`) remains dark, dense, and institutional. |

---

## 2. Brand Architecture & Visual System

### 2.1 The Three Pillars: "Think. Build. Automate."
- **THINK:** "Turn your market idea into clear trading rules." Formulate explicit entries, invalidations, and target objectives without emotional bias.
- **BUILD:** "Create and test systematic strategies without unnecessary complexity." Structure rules into verifiable models across crypto markets.
- **AUTOMATE:** "Validate your strategy and move toward automated execution." Deploy into zero-capital paper simulation and demo venue execution.

### 2.2 Color Palette
- **Background:** Pure White (`#ffffff`) and Soft Off-White (`#f8fafc`).
- **Typography:** Near-Black (`#09090b` headings, `#475569` body text).
- **Primary Brand Accent:** STRATA Royal Blue (`#2563eb`, hover `#1d4ed8`, tint `#eff6ff`).
- **Secondary Accent:** Sky Blue (`#0284c7` / `#38bdf8`).
- **Risk & Alert Accent:** Controlled Red (`#dc2626` / `#fef2f2`).
- **Success Accent:** Emerald (`#059669` / `#ecfdf5`).

---

## 3. Simplified Section-by-Section Structure

1. **Header:** Clean commercial bar with STRATA logo, 5 navigation links (`Home`, `About`, `What's New`, `Strategies`, `Pricing`), and action buttons (`Contact`, `Sign In`, `Get Started`).
2. **Hero:**
   - Left: Eyebrow badge *"Digital Asset Automation Platform"*, subhead *"THINK. BUILD. AUTOMATE."*, headline *"Turn Your Trading Ideas into Automated Crypto Strategies"*, concise 2-sentence value description, primary CTA *"Get Started Free →"*, secondary CTA *"Learn More →"*.
   - Right: Sparse, elegant product preview card tilted in perspective showcasing portfolio equity ($100k Paper), live crypto tickers (`BTCUSDT`, `ETHUSDT`, `SOLUSDT`, `BNBUSDT`), and active trend model.
3. **Core Philosophy Section:** Three clean editorial blocks defining *Think*, *Build*, and *Automate*.
4. **Step-by-Step Systematic Flow:** Horizontal 5-stage progression: `Idea` $\to$ `Build` $\to$ `Backtest` $\to$ `Validate` $\to$ `Automate`.
5. **Editorial Trading Lifestyle Section:** High-contrast visual section with headline *"Don't Spend Your Life Watching Charts."* demonstrating automated discipline over screen fatigue.
6. **Platform Capabilities ("Everything You Need"):** 6 clean cards: *Research*, *Build*, *Backtest*, *Validate*, *Automate*, *Monitor*.
7. **Trading Styles:** Minimalist taxonomy pills highlighting *Swing, Intraday, Position, Scalping, Investing, Hedging, Arbitrage, and Autonomous*.
8. **Strategy Lab Featurette:** *"Have an Idea? Build It With STRATA."* inviting users to test ideas with honest research disclosures.
9. **Proof & Quantitative Discipline:** Discreet quantitative credibility strip displaying 9,608 historical replay trades, $\ge 4.0\text{R}$ target floor, $\le 1.0\%$ risk cap, and $0.00 capital lock.
10. **Risk & Safety Notice:** Plain English explanation that automation does not remove market risk, reinforcing the $0.00 fail-closed capital gate.
11. **Pricing:** Clear launch period message: **$0.00 / First-Year Launch Access** with transparent mention of planned post-launch tiers.
12. **FAQ:** Short, transparent answers covering strategy creation, profit disclaimers, and zero-risk simulation.
13. **Footer:** Clean multi-column layout with Product, Company, Resources, and Legal links.

---

## 4. User Journey & Functional Authentication Flow

- **"Get Started"** opens an elegant, lightweight modal allowing new users to register with Full Name, Email, Password, and Password Confirmation.
- Form inputs validate client-side before dispatching to `/api/auth/register`.
- On successful registration, tokens are persisted and users seamlessly enter the `/app` institutional terminal.
- **"Sign In"** allows returning users to log in directly to their dedicated tenant workspace.
- **"Open STRATA Terminal"** provides direct access to `/app`.

---

## 5. Verification, Tests & Regressions

All automated tests, contract hashes, and historical replay regressions passed with 100% exact parity:

### 5.1 Automated Test Suite
```
======================= 244 passed, 3 warnings in 7.33s =======================
```
- **Total Tests:** 244 passed, 0 failed.
- Targeted web endpoint & programmatic journey tests passed cleanly.

### 5.2 Research Contract Integrity
```
Verifying Phase Q.2 Frozen Research Contract...
 [PASS] Frozen Contract Hash: 8fbc923a104e7688c3a9f0e4b8592c30dfb0b9a67a84511d5e49f8721c432098
 [PASS] Real Capital Authorized: $0.00
 [PASS] Live Adapter Status: HARD_DISABLED_FAIL_CLOSED
 [PASS] Target Floor: >=4.0R
 [PASS] Risk Per Trade: <=1.0%

FROZEN CONTRACT INTEGRITY 100% VERIFIED.
```

### 5.3 Historical Replay Regression
```
PHASE R — HISTORICAL REPLAY REGRESSION TEST:
Total Candidate Count:          9608 / 9608 [PASS]
Production Candidates (>=0.50): 3306 / 3306 [PASS]
High Confidence Candidates:     2942 / 2942 [PASS]
Strict Confidence Candidates:   1547 / 1547 [PASS]
Strict OOS Candidates:          1665 / 1665 [PASS]
REPLAY REGRESSION VERDICT:      PASS
```

### 5.4 Preflight, Health & Reconciliation
- `cli.py validate-preflight` $\to$ **PASS** (Environment: `PAPER`, Invariants intact)
- `cli.py health` $\to$ **ALL PLATFORM HEALTH CHECKS PASSED**
- `cli.py reconcile` $\to$ **STATUS: RECONCILED (0 Discrepancies)**

---

## 6. Strict Separation Rule Certified

- **Public Marketing Website (`/`):** Simple, light, commercial, editorial, easy to understand.
- **Institutional Trading Terminal (`/app`):** Dense, dark, quantitative, multi-timeframe, data-heavy, frozen KING Core.
- **Live Capital Safety Gate:** Permanently locked at **$0.00** fail-closed.
