"""Generate reproducible SVG research visualizations for Crypto Platform.

Uses exact, audited research figures from:
- research/results/PHASE_Q_FRACTAL_VALIDATION/phase_q2_trade_lineage_summary.json
- research/results/PHASE_Q_FRACTAL_VALIDATION/phase_q2_incremental_attribution.json
- research/reports/PHASE_Q2_INCREMENTAL_VALUE_AND_SHADOW_VALIDATION.md
"""
from pathlib import Path

OUT_DIR = Path(__file__).resolve().parent

def generate_cohort_comparison_svg():
    """Generates cohort comparison chart (Expectancy R and Profit Factor)."""
    svg = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 520" width="100%" height="100%">
    <defs>
        <linearGradient id="bgGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="#0f172a"/>
            <stop offset="100%" stop-color="#090d16"/>
        </linearGradient>
        <linearGradient id="barExp" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stop-color="#0284c7"/>
            <stop offset="100%" stop-color="#38bdf8"/>
        </linearGradient>
        <linearGradient id="barPf" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stop-color="#059669"/>
            <stop offset="100%" stop-color="#34d399"/>
        </linearGradient>
        <linearGradient id="barOos" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stop-color="#7c3aed"/>
            <stop offset="100%" stop-color="#a78bfa"/>
        </linearGradient>
    </defs>
    <rect width="960" height="520" rx="12" fill="url(#bgGrad)" stroke="#1e293b" stroke-width="1.5"/>
    
    <!-- Title and Subtitle -->
    <text x="40" y="44" fill="#f8fafc" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif" font-size="20" font-weight="700">Crypto Platform — Research Cohort Expectancy &amp; Profit Factor</text>
    <text x="40" y="68" fill="#94a3b8" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif" font-size="13">Empirical Phase Q.2 Attribution across 9,608 candidate records (4-Asset Universe: BTC, ETH, SOL, BNB)</text>
    
    <!-- Legend -->
    <rect x="620" y="32" width="14" height="14" rx="3" fill="url(#barExp)"/>
    <text x="642" y="44" fill="#cbd5e1" font-family="monospace" font-size="12">Expectancy (R)</text>
    <rect x="780" y="32" width="14" height="14" rx="3" fill="url(#barPf)"/>
    <text x="802" y="44" fill="#cbd5e1" font-family="monospace" font-size="12">Profit Factor</text>

    <!-- Grid Lines -->
    <line x1="320" y1="95" x2="900" y2="95" stroke="#1e293b" stroke-width="1"/>
    <line x1="320" y1="165" x2="900" y2="165" stroke="#1e293b" stroke-width="1"/>
    <line x1="320" y1="235" x2="900" y2="235" stroke="#1e293b" stroke-width="1"/>
    <line x1="320" y1="305" x2="900" y2="305" stroke="#1e293b" stroke-width="1"/>
    <line x1="320" y1="375" x2="900" y2="375" stroke="#1e293b" stroke-width="1"/>
    <line x1="320" y1="445" x2="900" y2="445" stroke="#1e293b" stroke-width="1"/>

    <!-- Row 1: Model A Baseline -->
    <text x="40" y="125" fill="#f1f5f9" font-family="monospace" font-size="13" font-weight="600">Model A: Baseline (All Sets)</text>
    <text x="40" y="143" fill="#64748b" font-family="monospace" font-size="11">N=9,608 | WinRate: 49.3% | MaxDD: 33.8R</text>
    <rect x="320" y="115" width="231" height="14" rx="3" fill="url(#barExp)"/>
    <text x="560" y="127" fill="#38bdf8" font-family="monospace" font-size="12" font-weight="700">+0.5781R</text>
    <rect x="320" y="133" width="188" height="14" rx="3" fill="url(#barPf)"/>
    <text x="518" y="145" fill="#34d399" font-family="monospace" font-size="12" font-weight="700">PF 2.352</text>

    <!-- Row 2: Model B1: Conf >= 0.50 -->
    <text x="40" y="195" fill="#f1f5f9" font-family="monospace" font-size="13" font-weight="600">Model B1: Conf &gt;= 0.50</text>
    <text x="40" y="213" fill="#64748b" font-family="monospace" font-size="11">N=3,531 | WinRate: 65.5% | MaxDD: 15.0R</text>
    <rect x="320" y="185" width="336" height="14" rx="3" fill="url(#barExp)"/>
    <text x="666" y="197" fill="#38bdf8" font-family="monospace" font-size="12" font-weight="700">+0.8414R</text>
    <rect x="320" y="203" width="355" height="14" rx="3" fill="url(#barPf)"/>
    <text x="685" y="215" fill="#34d399" font-family="monospace" font-size="12" font-weight="700">PF 4.440</text>

    <!-- Row 3: Model B2: Conf >= 0.60 -->
    <text x="40" y="265" fill="#f1f5f9" font-family="monospace" font-size="13" font-weight="600">Model B2: Conf &gt;= 0.60 (Standard)</text>
    <text x="40" y="283" fill="#64748b" font-family="monospace" font-size="11">N=2,942 | WinRate: 67.2% | MaxDD: 10.9R</text>
    <rect x="320" y="255" width="355" height="14" rx="3" fill="url(#barExp)"/>
    <text x="685" y="267" fill="#38bdf8" font-family="monospace" font-size="12" font-weight="700">+0.8885R</text>
    <rect x="320" y="273" width="393" height="14" rx="3" fill="url(#barPf)"/>
    <text x="723" y="285" fill="#34d399" font-family="monospace" font-size="12" font-weight="700">PF 4.918</text>

    <!-- Row 4: Model B3: Conf >= 0.75 -->
    <text x="40" y="335" fill="#f1f5f9" font-family="monospace" font-size="13" font-weight="600">Model B3: Conf &gt;= 0.75 (Strict)</text>
    <text x="40" y="353" fill="#64748b" font-family="monospace" font-size="11">N=1,547 | WinRate: 70.1% | MaxDD: 7.75R</text>
    <rect x="320" y="325" width="387" height="14" rx="3" fill="url(#barExp)"/>
    <text x="717" y="337" fill="#38bdf8" font-family="monospace" font-size="12" font-weight="700">+0.9679R</text>
    <rect x="320" y="343" width="476" height="14" rx="3" fill="url(#barPf)"/>
    <text x="806" y="355" fill="#34d399" font-family="monospace" font-size="12" font-weight="700">PF 5.955</text>

    <!-- Row 5: Model C: Production Sets 2-4 -->
    <text x="40" y="405" fill="#f1f5f9" font-family="monospace" font-size="13" font-weight="600">Model C: Prod Sets 2–4 (Conf &gt;= 0.50)</text>
    <text x="40" y="423" fill="#64748b" font-family="monospace" font-size="11">N=3,306 | WinRate: 66.0% | Calmar: 189.3</text>
    <rect x="320" y="395" width="343" height="14" rx="3" fill="url(#barExp)"/>
    <text x="673" y="407" fill="#38bdf8" font-family="monospace" font-size="12" font-weight="700">+0.8584R</text>
    <rect x="320" y="413" width="365" height="14" rx="3" fill="url(#barPf)"/>
    <text x="695" y="425" fill="#34d399" font-family="monospace" font-size="12" font-weight="700">PF 4.570</text>

    <!-- Row 6: Model D: Strict OOS -->
    <text x="40" y="475" fill="#f1f5f9" font-family="monospace" font-size="13" font-weight="600">Model D: Strictly Out-of-Sample</text>
    <text x="40" y="493" fill="#a78bfa" font-family="monospace" font-size="11">N=1,665 (July 2024–Pres) | WinRate: 63.6%</text>
    <rect x="320" y="465" width="324" height="14" rx="3" fill="url(#barOos)"/>
    <text x="654" y="477" fill="#a78bfa" font-family="monospace" font-size="12" font-weight="700">+0.8097R</text>
    <rect x="320" y="483" width="322" height="14" rx="3" fill="url(#barPf)"/>
    <text x="652" y="495" fill="#34d399" font-family="monospace" font-size="12" font-weight="700">PF 4.024</text>
</svg>"""
    (OUT_DIR / "research-cohort-expectancy-and-profit-factor.svg").write_text(svg, encoding="utf-8")
    print("Created research-cohort-expectancy-and-profit-factor.svg")

def generate_timeframe_distribution_svg():
    """Generates distribution by Timeframe Set and Asset Allocation."""
    svg = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 480" width="100%" height="100%">
    <defs>
        <linearGradient id="bgGrad2" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="#0f172a"/>
            <stop offset="100%" stop-color="#090d16"/>
        </linearGradient>
    </defs>
    <rect width="960" height="480" rx="12" fill="url(#bgGrad2)" stroke="#1e293b" stroke-width="1.5"/>
    
    <text x="40" y="44" fill="#f8fafc" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif" font-size="20" font-weight="700">Crypto Platform — Opportunity Distribution across 5 Timeframe Sets</text>
    <text x="40" y="68" fill="#94a3b8" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif" font-size="13">Breakdown of 9,608 mapped candidate records across overlapping observation windows &amp; assets</text>

    <!-- Set Breakdown (Left) -->
    <text x="40" y="110" fill="#38bdf8" font-family="monospace" font-size="14" font-weight="700">BY TIMEFRAME SET (LADDER WINDOW)</text>
    
    <!-- SET 1 -->
    <text x="40" y="145" fill="#e2e8f0" font-family="monospace" font-size="12">SET 1: 1M → 1W → 1D (Macro Anchor)</text>
    <rect x="40" y="155" width="15" height="12" rx="2" fill="#38bdf8"/>
    <text x="65" y="165" fill="#94a3b8" font-family="monospace" font-size="11">192 records (2.0%)</text>
    
    <!-- SET 2 -->
    <text x="40" y="200" fill="#e2e8f0" font-family="monospace" font-size="12">SET 2: 1W → 1D → 4H (Macro Swing)</text>
    <rect x="40" y="210" width="125" height="12" rx="2" fill="#0ea5e9"/>
    <text x="175" y="220" fill="#94a3b8" font-family="monospace" font-size="11">1,553 records (16.2%)</text>

    <!-- SET 3 -->
    <text x="40" y="255" fill="#e2e8f0" font-family="monospace" font-size="12">SET 3: 1D → 4H → 1H (Intermediate Intraday)</text>
    <rect x="40" y="265" width="446" height="12" rx="2" fill="#0284c7"/>
    <text x="496" y="275" fill="#38bdf8" font-family="monospace" font-size="11" font-weight="700">5,582 records (58.1%)</text>

    <!-- SET 4 -->
    <text x="40" y="310" fill="#e2e8f0" font-family="monospace" font-size="12">SET 4: 4H → 1H → 15M (Lower Intraday)</text>
    <rect x="40" y="320" width="151" height="12" rx="2" fill="#0369a1"/>
    <text x="201" y="330" fill="#94a3b8" font-family="monospace" font-size="11">1,893 records (19.7%)</text>

    <!-- SET 5 -->
    <text x="40" y="365" fill="#e2e8f0" font-family="monospace" font-size="12">SET 5: 1H → 15M → 3M (Micro Execution)</text>
    <rect x="40" y="375" width="31" height="12" rx="2" fill="#075985"/>
    <text x="81" y="385" fill="#94a3b8" font-family="monospace" font-size="11">388 records (4.0%)</text>

    <!-- Asset Allocation Box (Right) -->
    <rect x="580" y="100" width="340" height="340" rx="8" fill="#131d33" stroke="#1e293b"/>
    <text x="605" y="135" fill="#34d399" font-family="monospace" font-size="14" font-weight="700">UNIVERSE ASSET COVERAGE</text>
    
    <text x="605" y="175" fill="#f8fafc" font-family="monospace" font-size="13">ETHUSDT: 3,538 (36.8%)</text>
    <rect x="605" y="185" width="220" height="10" rx="2" fill="#10b981"/>
    
    <text x="605" y="235" fill="#f8fafc" font-family="monospace" font-size="13">BTCUSDT: 2,908 (30.3%)</text>
    <rect x="605" y="245" width="180" height="10" rx="2" fill="#059669"/>

    <text x="605" y="295" fill="#f8fafc" font-family="monospace" font-size="13">SOLUSDT: 2,672 (27.8%)</text>
    <rect x="605" y="305" width="165" height="10" rx="2" fill="#047857"/>

    <text x="605" y="355" fill="#f8fafc" font-family="monospace" font-size="13">BNBUSDT: 490 (5.1%)</text>
    <rect x="605" y="365" width="30" height="10" rx="2" fill="#065f46"/>

    <text x="605" y="415" fill="#94a3b8" font-family="monospace" font-size="11">Total: 9,608 Mapped Records across 4 Assets</text>
</svg>"""
    (OUT_DIR / "research-timeframe-sets-distribution.svg").write_text(svg, encoding="utf-8")
    print("Created research-timeframe-sets-distribution.svg")

def generate_pruning_filter_svg():
    """Generates mechanistic false-positive pruning visualization."""
    svg = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 440" width="100%" height="100%">
    <defs>
        <linearGradient id="bgGrad3" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="#0f172a"/>
            <stop offset="100%" stop-color="#090d16"/>
        </linearGradient>
    </defs>
    <rect width="960" height="440" rx="12" fill="url(#bgGrad3)" stroke="#1e293b" stroke-width="1.5"/>
    
    <text x="40" y="44" fill="#f8fafc" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif" font-size="20" font-weight="700">Mechanistic Attribution: False-Positive Loss Pruning</text>
    <text x="40" y="68" fill="#94a3b8" font-family="-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif" font-size="13">The Fractal State Engine acts as an institutional noise filter, eliminating 80.2% of baseline losses</text>

    <!-- Losses Box -->
    <rect x="40" y="105" width="420" height="290" rx="8" fill="#131d33" stroke="#f43f5e" stroke-width="1"/>
    <text x="65" y="140" fill="#fb7185" font-family="monospace" font-size="15" font-weight="700">BASELINE LOSSES: 4,873 Trades</text>
    
    <rect x="65" y="170" width="370" height="50" rx="4" fill="#4c0519"/>
    <text x="80" y="195" fill="#fecdd3" font-family="monospace" font-size="13" font-weight="700">Pruned by Fractal Engine: 3,907 Losses</text>
    <text x="80" y="212" fill="#fda4af" font-family="monospace" font-size="11">80.2% of baseline losses eliminated (Avg return: -0.8806R)</text>

    <rect x="65" y="240" width="100" height="50" rx="4" fill="#27272a"/>
    <text x="80" y="265" fill="#e4e4e7" font-family="monospace" font-size="13" font-weight="700">Retained: 966</text>
    <text x="80" y="282" fill="#a1a1aa" font-family="monospace" font-size="11">19.8% retained</text>

    <text x="65" y="340" fill="#94a3b8" font-family="monospace" font-size="12">Result: Prevents destructive whipsaws during HTF</text>
    <text x="65" y="360" fill="#94a3b8" font-family="monospace" font-size="12">consolidation and counter-trend exhaustion moves.</text>

    <!-- Wins Box -->
    <rect x="500" y="105" width="420" height="290" rx="8" fill="#131d33" stroke="#10b981" stroke-width="1"/>
    <text x="525" y="140" fill="#34d399" font-family="monospace" font-size="15" font-weight="700">BASELINE WINS: 4,735 Trades</text>

    <rect x="525" y="170" width="220" height="50" rx="4" fill="#064e3b"/>
    <text x="540" y="195" fill="#a7f3d0" font-family="monospace" font-size="13" font-weight="700">Preserved Wins: 1,976 Trades</text>
    <text x="540" y="212" fill="#6ee7b7" font-family="monospace" font-size="11">High-confluence multi-scale directional wins</text>

    <rect x="525" y="240" width="160" height="50" rx="4" fill="#27272a"/>
    <text x="540" y="265" fill="#e4e4e7" font-family="monospace" font-size="13" font-weight="700">Filtered: 2,759 Wins</text>
    <text x="540" y="282" fill="#a1a1aa" font-family="monospace" font-size="11">Lower RR / unaligned</text>

    <text x="525" y="340" fill="#34d399" font-family="monospace" font-size="12" font-weight="700">Win Rate Surges from 49.3% → 67.2%</text>
    <text x="525" y="360" fill="#34d399" font-family="monospace" font-size="12" font-weight="700">Profit Factor Expands from 2.352 → 4.918</text>
</svg>"""
    (OUT_DIR / "research-false-positive-pruning.svg").write_text(svg, encoding="utf-8")
    print("Created research-false-positive-pruning.svg")

if __name__ == "__main__":
    generate_cohort_comparison_svg()
    generate_timeframe_distribution_svg()
    generate_pruning_filter_svg()
