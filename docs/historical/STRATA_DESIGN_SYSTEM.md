# STRATA — Product Design System Specification

## 1. Design Philosophy & Aesthetic Principles
The STRATA user experience reflects the discipline, clarity, and precision of institutional quantitative finance:
- **Tone**: Calm, authoritative, technical, and restrained.
- **Avoidance**: No casino aesthetics, no neon saturation, no cartoon mascots, no pseudo-futuristic fake AI holograms.
- **Density Balance**:
  - **Public / Marketing**: Spatially open, clean typographic hierarchy, interactive 3D fractal particle visualizations for product storytelling.
  - **Trading / Terminal**: Dense, tabular, 2D data-focused interfaces with instant visual scannability and minimal DOM overhead.

---

## 2. Color Palette & Theming Tokens

### 2.1 Core Dark Mode Palette (Default)
```css
:root {
  /* Surfaces */
  --bg-main: #060913;          /* Deep space slate background */
  --bg-card: #0d1527;          /* Card and blotter surface */
  --bg-hover: #131e36;         /* Row highlight and interactive surface */
  --border: #1a2742;           /* Subtle structural separator */
  --border-focus: #2563eb;     /* Focused active element border */

  /* Typography */
  --text-main: #f8fafc;        /* High-contrast primary text */
  --text-muted: #8492a6;       /* De-emphasized labels and metadata */
  --text-dim: #475569;         /* Tertiary timestamps and subtle hints */

  /* Accents & Financial Semantics */
  --cyan: #0ea5e9;             /* Primary brand accent / Telemetry */
  --emerald: #10b981;          /* Positive returns, filled orders, healthy state */
  --rose: #f43f5e;             /* Negative returns, canceled orders, halt trigger */
  --amber: #f59e0b;            /* Warning alerts, degraded strategies, quarantine */
  --purple: #8b5cf6;           /* Research, AI compiler, experimental tier */
}
```

---

## 3. Typography Hierarchy
- **Primary Interface**: Inter / Roboto / System Sans (`-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif`).
- **Tabular & Financial Data**: JetBrains Mono (`"JetBrains Mono", Menlo, Consolas, monospace`).
  - Monospace formatting is mandatory for order prices, notional amounts, R-multiples, timestamps, and hashes to prevent visual shifting.

---

## 4. Component Standards

### 4.1 Navigation & Layout
- Fixed left sidebar navigation with high-contrast icon badges and active indicators.
- Top status header displaying:
  - System Mode (`PAPER` / `SHADOW` / `LIVE`)
  - Portfolio Equity and Open Risk Heat
  - Watchdog Heartbeat pulse (Emerald / Rose)
  - Emergency Halt button

### 4.2 Financial Blotters & Tables
- Sticky table headers with compact row heights (`padding: 0.65rem 0.85rem`).
- Strict column alignment: text left-aligned, numeric data right-aligned.
- Status badges:
  - Filled / Healthy: Emerald pill (`background: rgba(16, 185, 129, 0.15)`)
  - Degraded / Quarantined: Amber pill (`background: rgba(245, 158, 11, 0.15)`)
  - Error / Halted: Rose pill (`background: rgba(244, 63, 94, 0.15)`)

### 4.3 Strategy Lab Natural Language Input
- Monospace-styled prompt input container with syntax hints.
- Real-time specification compilation summary cards displaying parsed asset universes, entry triggers, stop invalidations, and minimum target floors ($\ge 4\text{R}$).

### 4.4 Mobile Touch Interface
- Bottom fixed tab bar with tap targets $\ge 48\text{px}$.
- High-contrast visual warnings and double-confirmation dialogs for operational controls.
