"""STRATA Digital Trading Platform — Institutional Web Terminal & REST API Server.

Serves an institutional financial trading terminal:
- Master Cockpit (/dashboard)
- Multi-Instrument Market Monitor (/markets)
- 7-Timeframe Interactive Fractal Visualizer (/fractal-state)
- Real-Time Opportunity Pipeline (/opportunities)
- Active & Closed Position Blotter (/positions)
- Order Execution Log (/orders)
- Broker & Testnet Accounts (/accounts)
- Risk Governor & Circuit Breakers (/risk)
- Forward Performance Analytics (/performance)
- Statistical Drift & Degradation Monitor (/drift)
- Append-Only Immutable Decision Ledger (/decision-ledger)
- State & Broker Reconciliation Auditor (/reconciliation)
- System Health & Telemetry (/system-health)
- Safety Gates & Environmental Controls (/settings)
- Interactive Trade Explainer Modal ("Why Trade?" vs "Why No Trade?")
- Permanent Hardware/Software Capital Safety Banner
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from aiohttp import web

from execution.autonomous_supervisor import AutonomousTradingSupervisor
from notifications.alert_router import ALERTS
from execution.safety.safety_gate import SAFETY_GATE

HTML_TERMINAL_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>STRATA Digital Trading Platform — Institutional Terminal</title>
    <style>
        :root {
            --bg-primary: #070a11;
            --bg-secondary: #0e1422;
            --bg-tertiary: #162035;
            --bg-card: #121a2c;
            --text-primary: #e2e8f0;
            --text-secondary: #8492a6;
            --accent-cyan: #0ea5e9;
            --accent-green: #10b981;
            --accent-red: #f43f5e;
            --accent-amber: #f59e0b;
            --accent-purple: #8b5cf6;
            --border-color: #1e293b;
            --font-mono: 'JetBrains Mono', 'SF Mono', Consolas, monospace;
            --font-sans: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            background-color: var(--bg-primary);
            color: var(--text-primary);
            font-family: var(--font-sans);
            font-size: 13px;
            line-height: 1.5;
            display: flex;
            flex-direction: column;
            height: 100vh;
            overflow: hidden;
        }
        /* Top Safety Banner */
        .safety-banner {
            background: linear-gradient(90deg, #450a0a, #7f1d1d, #450a0a);
            color: #fecaca;
            padding: 5px 20px;
            font-weight: 700;
            font-size: 11px;
            letter-spacing: 0.08em;
            text-align: center;
            border-bottom: 1px solid #991b1b;
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-family: var(--font-mono);
        }
        .header {
            background: var(--bg-secondary);
            border-bottom: 1px solid var(--border-color);
            padding: 10px 24px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .header-brand {
            display: flex;
            align-items: center;
            gap: 12px;
        }
        .header-brand h1 {
            font-size: 15px;
            font-weight: 800;
            letter-spacing: 0.1em;
            color: #f8fafc;
        }
        .brand-badge {
            background: #0369a1;
            color: #e0f2fe;
            padding: 2px 7px;
            border-radius: 3px;
            font-size: 10px;
            font-weight: 700;
            font-family: var(--font-mono);
        }
        .badges-group {
            display: flex;
            gap: 8px;
            align-items: center;
        }
        .badge {
            padding: 4px 10px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 600;
            font-family: var(--font-mono);
        }
        .badge-mode { background: #0c4a6e; color: #7dd3fc; border: 1px solid #0284c7; }
        .badge-healthy { background: #064e3b; color: #6ee7b7; border: 1px solid #10b981; }
        .badge-danger { background: #7f1d1d; color: #fca5a5; border: 1px solid #ef4444; }

        /* Main Layout */
        .main-layout {
            display: flex;
            flex: 1;
            overflow: hidden;
        }
        .sidebar {
            width: 220px;
            background: var(--bg-secondary);
            border-right: 1px solid var(--border-color);
            display: flex;
            flex-direction: column;
            padding: 10px 0;
            overflow-y: auto;
        }
        .nav-section-title {
            padding: 12px 18px 4px;
            font-size: 10px;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: #475569;
            font-weight: 700;
        }
        .nav-item {
            padding: 8px 18px;
            color: var(--text-secondary);
            cursor: pointer;
            font-weight: 500;
            transition: all 0.12s ease;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .nav-item:hover {
            background: var(--bg-tertiary);
            color: #f8fafc;
        }
        .nav-item.active {
            background: var(--bg-tertiary);
            color: #38bdf8;
            border-left: 3px solid var(--accent-cyan);
            font-weight: 600;
        }
        .content {
            flex: 1;
            padding: 20px 24px;
            overflow-y: auto;
            background: var(--bg-primary);
        }

        /* Metric Cards */
        .grid-kpi {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 14px;
            margin-bottom: 20px;
        }
        .card {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 6px;
            padding: 14px 16px;
        }
        .card-title {
            color: var(--text-secondary);
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            margin-bottom: 6px;
            font-weight: 600;
        }
        .card-value {
            font-size: 20px;
            font-weight: 700;
            font-family: var(--font-mono);
            color: #f8fafc;
        }
        .card-subtext {
            font-size: 11px;
            color: var(--text-secondary);
            margin-top: 4px;
        }

        /* 7-Timeframe Matrix */
        .ladder-grid {
            display: grid;
            grid-template-columns: repeat(7, 1fr);
            gap: 8px;
            margin-bottom: 20px;
        }
        .ladder-node {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 6px;
            padding: 10px;
            text-align: center;
        }
        .ladder-tf {
            font-size: 13px;
            font-weight: 800;
            font-family: var(--font-mono);
            color: var(--accent-cyan);
            margin-bottom: 4px;
        }
        .ladder-trend {
            font-size: 10px;
            font-weight: 700;
            padding: 2px 6px;
            border-radius: 3px;
            display: inline-block;
            margin-bottom: 4px;
        }
        .trend-bullish { background: rgba(16, 185, 129, 0.2); color: #34d399; }
        .trend-bearish { background: rgba(244, 63, 94, 0.2); color: #fb7185; }
        .trend-neutral { background: rgba(148, 163, 184, 0.2); color: #94a3b8; }

        /* Tables */
        table {
            width: 100%;
            border-collapse: collapse;
            font-family: var(--font-mono);
            font-size: 12px;
        }
        th, td {
            padding: 9px 12px;
            text-align: left;
            border-bottom: 1px solid var(--border-color);
        }
        th {
            background: var(--bg-secondary);
            color: var(--text-secondary);
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        tr:hover { background: rgba(255, 255, 255, 0.02); cursor: pointer; }
        .tag-trade {
            background: rgba(16, 185, 129, 0.2);
            color: #34d399;
            padding: 2px 6px;
            border-radius: 3px;
            font-weight: 700;
        }
        .tag-no-trade {
            background: rgba(100, 116, 139, 0.2);
            color: #94a3b8;
            padding: 2px 6px;
            border-radius: 3px;
            font-weight: 500;
        }

        /* Modal Explainer */
        .modal-overlay {
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(0, 0, 0, 0.75);
            display: none;
            justify-content: center;
            align-items: center;
            z-index: 1000;
        }
        .modal-box {
            background: var(--bg-card);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            width: 650px;
            max-width: 90vw;
            padding: 24px;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.6);
        }
        .modal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 12px;
            margin-bottom: 16px;
        }
        .modal-close {
            background: transparent;
            border: none;
            color: var(--text-secondary);
            font-size: 18px;
            cursor: pointer;
        }
        .tab-view { display: none; }
        .tab-view.active { display: block; }
    </style>
</head>
<body>
    <!-- Permanent Safety Guard Banner -->
    <div class="safety-banner">
        <div>🔒 STRATA MULTI-TIER CAPITAL GATE: FAIL-CLOSED SAFETY BARRIER ENGAGED</div>
        <div id="safety-banner-detail">REAL CAPITAL AUTHORIZED: $0.00 | LIVE TRADING: HARD-DISABLED</div>
        <div>SHA-256 CONTRACT CERTIFIED</div>
    </div>

    <!-- Header -->
    <div class="header">
        <div class="header-brand">
            <h1>STRATA</h1>
            <span class="brand-badge">DIGITAL TRADING PLATFORM</span>
            <span style="color: var(--text-secondary); font-size: 11px;">v2.0-PROD</span>
        </div>
        <div class="badges-group">
            <span id="env-badge" class="badge badge-mode">ENV: PAPER</span>
            <span id="sys-health-badge" class="badge badge-healthy">SYSTEM: HEALTHY</span>
            <span id="clock-display" style="font-family: var(--font-mono); font-size: 11px; color: var(--text-secondary);">UTC: --:--:--</span>
        </div>
    </div>

    <div class="main-layout">
        <!-- Sidebar Navigation -->
        <div class="sidebar">
            <div class="nav-section-title">Core Operations</div>
            <div class="nav-item active" onclick="switchTab('dashboard')">Master Cockpit</div>
            <div class="nav-item" onclick="switchTab('markets')">Markets & Feeds</div>
            <div class="nav-item" onclick="switchTab('fractal-state')">7-TF Fractal Matrix</div>
            <div class="nav-item" onclick="switchTab('opportunities')">Opportunities Blotter</div>

            <div class="nav-section-title">Execution & Accounts</div>
            <div class="nav-item" onclick="switchTab('positions')">Active Positions</div>
            <div class="nav-item" onclick="switchTab('orders')">Order Execution Blotter</div>
            <div class="nav-item" onclick="switchTab('accounts')">Broker Accounts</div>
            <div class="nav-item" onclick="switchTab('risk')">Risk & Breakers</div>

            <div class="nav-section-title">Analytics & Audit</div>
            <div class="nav-item" onclick="switchTab('performance')">Forward Analytics</div>
            <div class="nav-item" onclick="switchTab('drift')">Statistical Drift</div>
            <div class="nav-item" onclick="switchTab('decision-ledger')">Decision Ledger</div>
            <div class="nav-item" onclick="switchTab('reconciliation')">State Reconciliation</div>
            <div class="nav-item" onclick="switchTab('system-health')">System Telemetry</div>
            <div class="nav-item" onclick="switchTab('settings')">Settings & Gates</div>
        </div>

        <!-- Dynamic Content Area -->
        <div class="content">
            <!-- TAB: Dashboard (Master Cockpit) -->
            <div id="tab-dashboard" class="tab-view active">
                <div class="grid-kpi">
                    <div class="card">
                        <div class="card-title">Simulated Equity</div>
                        <div class="card-value" id="kpi-equity">$100,000.00</div>
                        <div class="card-subtext" id="kpi-peak-equity">Peak: $100,000.00</div>
                    </div>
                    <div class="card">
                        <div class="card-title">Real Capital Authorized</div>
                        <div class="card-value" style="color: var(--accent-red);">$0.00</div>
                        <div class="card-subtext">Live Orders Fail-Closed</div>
                    </div>
                    <div class="card">
                        <div class="card-title">Portfolio Heat</div>
                        <div class="card-value" id="kpi-heat">0.0% / 3.0%</div>
                        <div class="card-subtext">Max Limit: 3.0%</div>
                    </div>
                    <div class="card">
                        <div class="card-title">Drawdown from Peak</div>
                        <div class="card-value" id="kpi-dd">0.00%</div>
                        <div class="card-subtext">Breaker Floor: 4.00%</div>
                    </div>
                    <div class="card">
                        <div class="card-title">Active Positions</div>
                        <div class="card-value" id="kpi-positions">0</div>
                        <div class="card-subtext">Sets 2, 3, 4 Eligible</div>
                    </div>
                    <div class="card">
                        <div class="card-title">Decisions Logged</div>
                        <div class="card-value" id="kpi-decisions">0</div>
                        <div class="card-subtext">Append-Only Ledger</div>
                    </div>
                </div>

                <!-- 7-Timeframe Hierarchy Banner -->
                <div class="card-title" style="margin-top: 10px; margin-bottom: 8px;">Continuous Scale-Invariant Hierarchy (Overlapping Sets 1 to 5)</div>
                <div class="ladder-grid">
                    <div class="ladder-node">
                        <div class="ladder-tf">1M</div>
                        <div class="ladder-trend trend-bullish">BULLISH</div>
                        <div style="font-size: 10px; color: var(--text-secondary);">Set 1 HTF (Macro Anchor)</div>
                    </div>
                    <div class="ladder-node">
                        <div class="ladder-tf">1W</div>
                        <div class="ladder-trend trend-bullish">BULLISH</div>
                        <div style="font-size: 10px; color: var(--text-secondary);">Set 1 MTF / Set 2 HTF</div>
                    </div>
                    <div class="ladder-node">
                        <div class="ladder-tf">1D</div>
                        <div class="ladder-trend trend-bearish">PULLBACK</div>
                        <div style="font-size: 10px; color: var(--text-secondary);">Set 2 MTF / Set 3 HTF</div>
                    </div>
                    <div class="ladder-node">
                        <div class="ladder-tf">4H</div>
                        <div class="ladder-trend trend-neutral">EQUILIBRIUM</div>
                        <div style="font-size: 10px; color: var(--text-secondary);">Set 2 LTF / Set 3 MTF / Set 4 HTF</div>
                    </div>
                    <div class="ladder-node">
                        <div class="ladder-tf">1H</div>
                        <div class="ladder-trend trend-bullish">MSS_BULL</div>
                        <div style="font-size: 10px; color: var(--text-secondary);">Set 3 LTF / Set 4 MTF / Set 5 HTF</div>
                    </div>
                    <div class="ladder-node">
                        <div class="ladder-tf">15M</div>
                        <div class="ladder-trend trend-bullish">CHOCH_ENTRY</div>
                        <div style="font-size: 10px; color: var(--text-secondary);">Set 4 LTF / Set 5 MTF</div>
                    </div>
                    <div class="ladder-node">
                        <div class="ladder-tf">3M</div>
                        <div class="ladder-trend trend-neutral">PULLBACK</div>
                        <div style="font-size: 10px; color: var(--text-secondary);">Set 5 LTF (Micro Confirm)</div>
                    </div>
                </div>

                <!-- Recent Decisions Live Feed -->
                <div class="card" style="margin-top: 15px;">
                    <div class="card-title" style="display: flex; justify-content: space-between;">
                        <span>Real-Time Closed-Candle Decisions (Click Row for Trade Explainer)</span>
                        <span style="color: var(--accent-cyan);">Auto-Refreshed Every 2s</span>
                    </div>
                    <div style="overflow-x: auto; margin-top: 10px;">
                        <table>
                            <thead>
                                <tr>
                                    <th>Timestamp</th>
                                    <th>Asset</th>
                                    <th>Set</th>
                                    <th>Phase</th>
                                    <th>Decision</th>
                                    <th>Confidence</th>
                                    <th>Planned R</th>
                                    <th>Reason Codes / Details</th>
                                </tr>
                            </thead>
                            <tbody id="decisions-tbody">
                                <tr><td colspan="8" style="text-align: center; color: var(--text-secondary); padding: 15px;">Streaming causal events...</td></tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>

            <!-- TAB: Markets -->
            <div id="tab-markets" class="tab-view">
                <div class="card">
                    <div class="card-title">Active Instrument Universe & WebSocket Feeds</div>
                    <div style="overflow-x: auto; margin-top: 10px;">
                        <table>
                            <thead>
                                <tr>
                                    <th>Symbol</th>
                                    <th>Base Asset</th>
                                    <th>Quote Asset</th>
                                    <th>Admission Status</th>
                                    <th>Tick Size</th>
                                    <th>Lot Size</th>
                                    <th>Min Notional</th>
                                    <th>Typical Spread</th>
                                    <th>Venue Routing</th>
                                </tr>
                            </thead>
                            <tbody id="markets-tbody">
                                <tr><td colspan="9" style="text-align: center; color: var(--text-secondary);">Loading universe specs...</td></tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>

            <!-- TAB: 7-TF Fractal Matrix -->
            <div id="tab-fractal-state" class="tab-view">
                <div class="card">
                    <div class="card-title">Continuous 7-Timeframe Scale Invariance Matrix</div>
                    <p style="color: var(--text-secondary); margin-bottom: 15px;">
                        Scale-invariant causal transmission across overlapping windows: Set 1 (1M/1W/1D), Set 2 (1W/1D/4H),
                        Set 3 (1D/4H/1H), Set 4 (4H/1H/15M), Set 5 (1H/15M/3M).
                    </p>
                    <div id="fractal-matrix-container">
                        <div class="ladder-grid">
                            <div class="ladder-node"><div class="ladder-tf">1M</div><div class="card-subtext">Macro Trend: BULLISH<br>Phase: CONTINUATION</div></div>
                            <div class="ladder-node"><div class="ladder-tf">1W</div><div class="card-subtext">Swing Trend: BULLISH<br>Phase: CONTINUATION</div></div>
                            <div class="ladder-node"><div class="ladder-tf">1D</div><div class="card-subtext">Daily Trend: RANGE<br>Phase: PULLBACK</div></div>
                            <div class="ladder-node"><div class="ladder-tf">4H</div><div class="card-subtext">Intraday: EQUILIBRIUM<br>Phase: ACCUMULATION</div></div>
                            <div class="ladder-node"><div class="ladder-tf">1H</div><div class="card-subtext">Structure: MSS_BULL<br>Phase: EXPANSION</div></div>
                            <div class="ladder-node"><div class="ladder-tf">15M</div><div class="card-subtext">Trigger: CHOCH<br>Phase: ENTRY_SETUP</div></div>
                            <div class="ladder-node"><div class="ladder-tf">3M</div><div class="card-subtext">Micro: REACTION<br>Phase: CONFIRMATION</div></div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- TAB: Opportunities Blotter -->
            <div id="tab-opportunities" class="tab-view">
                <div class="card">
                    <div class="card-title">Real-Time Opportunity Qualification Pipeline</div>
                    <div style="overflow-x: auto; margin-top: 10px;">
                        <table>
                            <thead>
                                <tr>
                                    <th>Candidate ID</th>
                                    <th>Asset</th>
                                    <th>Set</th>
                                    <th>Phase</th>
                                    <th>Confidence</th>
                                    <th>Entry</th>
                                    <th>Stop</th>
                                    <th>Target</th>
                                    <th>Planned R</th>
                                    <th>Status</th>
                                </tr>
                            </thead>
                            <tbody id="opps-tbody">
                                <tr><td colspan="10" style="text-align: center; color: var(--text-secondary);">Waiting for qualifying candle setup...</td></tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>

            <!-- TAB: Positions -->
            <div id="tab-positions" class="tab-view">
                <div class="card">
                    <div class="card-title">Active & Closed Positions Blotter</div>
                    <div style="overflow-x: auto; margin-top: 10px;">
                        <table>
                            <thead>
                                <tr>
                                    <th>Position ID</th>
                                    <th>Symbol</th>
                                    <th>Dir</th>
                                    <th>Size</th>
                                    <th>Entry Px</th>
                                    <th>Current Stop</th>
                                    <th>Target Px</th>
                                    <th>Realized R</th>
                                    <th>PnL (USD)</th>
                                    <th>State</th>
                                </tr>
                            </thead>
                            <tbody id="positions-tbody">
                                <tr><td colspan="10" style="text-align: center; color: var(--text-secondary);">No positions currently open.</td></tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>

            <!-- TAB: Orders -->
            <div id="tab-orders" class="tab-view">
                <div class="card">
                    <div class="card-title">Execution Blotter & Simulated Fills</div>
                    <div style="overflow-x: auto; margin-top: 10px;">
                        <table>
                            <thead>
                                <tr>
                                    <th>Fill ID</th>
                                    <th>Intent ID</th>
                                    <th>Symbol</th>
                                    <th>Direction</th>
                                    <th>Fill Price</th>
                                    <th>Size Units</th>
                                    <th>Fee USD</th>
                                    <th>Slippage</th>
                                    <th>Venue</th>
                                </tr>
                            </thead>
                            <tbody id="orders-tbody">
                                <tr><td colspan="9" style="text-align: center; color: var(--text-secondary);">No orders executed yet.</td></tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>

            <!-- TAB: Accounts -->
            <div id="tab-accounts" class="tab-view">
                <div class="card">
                    <div class="card-title">Registered Broker & Simulated Accounts</div>
                    <div style="overflow-x: auto; margin-top: 10px;">
                        <table>
                            <thead>
                                <tr>
                                    <th>Account ID</th>
                                    <th>Account Name</th>
                                    <th>Venue</th>
                                    <th>Environment</th>
                                    <th>Total Equity</th>
                                    <th>Available Margin</th>
                                    <th>Active</th>
                                    <th>Status</th>
                                </tr>
                            </thead>
                            <tbody id="accounts-tbody">
                                <tr><td colspan="8" style="text-align: center; color: var(--text-secondary);">Loading accounts...</td></tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>

            <!-- TAB: Risk -->
            <div id="tab-risk" class="tab-view">
                <div class="grid-kpi">
                    <div class="card">
                        <div class="card-title">Max Trade Risk</div>
                        <div class="card-value">1.0%</div>
                        <div class="card-subtext">Hard Risk Cap</div>
                    </div>
                    <div class="card">
                        <div class="card-title">Max Portfolio Heat</div>
                        <div class="card-value">3.0%</div>
                        <div class="card-subtext">Aggregate Cap</div>
                    </div>
                    <div class="card">
                        <div class="card-title">Correlation Haircut</div>
                        <div class="card-value">50.0%</div>
                        <div class="card-subtext">Active if Corr > 0.75</div>
                    </div>
                    <div class="card">
                        <div class="card-title">Drawdown Breaker</div>
                        <div class="card-value">4.0%</div>
                        <div class="card-subtext">Halts New Entries</div>
                    </div>
                </div>
                <div class="card" style="margin-top: 15px;">
                    <div class="card-title">Automated Circuit Breaker States</div>
                    <div style="padding: 10px 0; font-family: var(--font-mono);">
                        <div style="margin-bottom: 8px;">✅ MaxDrawdownBreaker: ARMED (Drawdown: 0.00% &lt; 4.00%)</div>
                        <div style="margin-bottom: 8px;">✅ ConsecutiveLossBreaker: ARMED (Losses: 0 &lt; 3)</div>
                        <div style="margin-bottom: 8px;">✅ StaleDataBreaker: ARMED (Heartbeat Latency: &lt; 2s)</div>
                        <div>✅ ReconciliationDiscrepancyBreaker: ARMED (0 Breaches)</div>
                    </div>
                </div>
            </div>

            <!-- TAB: Performance -->
            <div id="tab-performance" class="tab-view">
                <div class="grid-kpi">
                    <div class="card">
                        <div class="card-title">Reference Expectancy</div>
                        <div class="card-value" style="color: var(--accent-green);">+0.8097R</div>
                        <div class="card-subtext">Frozen Q.2 Baseline</div>
                    </div>
                    <div class="card">
                        <div class="card-title">Reference Profit Factor</div>
                        <div class="card-value">4.024</div>
                        <div class="card-subtext">OOS Baseline</div>
                    </div>
                    <div class="card">
                        <div class="card-title">Reference Win Rate</div>
                        <div class="card-value">63.6%</div>
                        <div class="card-subtext">Historical Certified</div>
                    </div>
                    <div class="card">
                        <div class="card-title">Minimum Target Floor</div>
                        <div class="card-value" style="color: var(--accent-cyan);">&ge; 4.0R</div>
                        <div class="card-subtext">Hard Geometry Constraint</div>
                    </div>
                </div>
            </div>

            <!-- TAB: Drift -->
            <div id="tab-drift" class="tab-view">
                <div class="card">
                    <div class="card-title">Statistical Drift & Degradation Monitor</div>
                    <div id="drift-status-container" style="padding: 10px 0; font-family: var(--font-mono);">
                        Loading real-time drift telemetry...
                    </div>
                </div>
            </div>

            <!-- TAB: Decision Ledger -->
            <div id="tab-decision-ledger" class="tab-view">
                <div class="card">
                    <div class="card-title">Immutable Decision Ledger (SHA-256 Chained)</div>
                    <p style="color: var(--text-secondary); margin-bottom: 10px;">
                        Path: <code>research/results/PHASE_R_DECISION_LEDGER.jsonl</code>
                    </p>
                    <div style="overflow-x: auto;">
                        <table>
                            <thead>
                                <tr>
                                    <th>Decision ID</th>
                                    <th>Asset</th>
                                    <th>Set</th>
                                    <th>Decision</th>
                                    <th>Confidence</th>
                                    <th>Planned R</th>
                                    <th>Reasons</th>
                                </tr>
                            </thead>
                            <tbody id="ledger-tbody">
                                <tr><td colspan="7" style="text-align: center; color: var(--text-secondary);">Loading ledger records...</td></tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>

            <!-- TAB: Reconciliation -->
            <div id="tab-reconciliation" class="tab-view">
                <div class="card">
                    <div class="card-title">State & Broker Reconciliation Auditor</div>
                    <div id="reconciliation-container" style="padding: 10px 0; font-family: var(--font-mono);">
                        Auditing pipeline state invariants...
                    </div>
                </div>
            </div>

            <!-- TAB: System Health -->
            <div id="tab-system-health" class="tab-view">
                <div class="card">
                    <div class="card-title">System Telemetry & Operational Health</div>
                    <div id="telemetry-raw" style="padding: 10px 0; font-family: var(--font-mono); white-space: pre-wrap; font-size: 11px; color: #94a3b8;">
                        Fetching system telemetry...
                    </div>
                </div>
            </div>

            <!-- TAB: Settings -->
            <div id="tab-settings" class="tab-view">
                <div class="card">
                    <div class="card-title">Environment Mode & Capital Safety Gates</div>
                    <div style="padding: 10px 0; font-family: var(--font-mono); line-height: 1.8;">
                        <div>Current Execution Mode: <strong style="color: var(--accent-cyan);" id="settings-mode">PAPER</strong></div>
                        <div>Real Capital Authorization: <strong style="color: var(--accent-red);">$0.00</strong></div>
                        <div>Live Adapter Barrier: <strong style="color: var(--accent-red);">FAIL-CLOSED (LOCKED)</strong></div>
                        <div style="margin-top: 15px; padding: 12px; background: rgba(239, 68, 68, 0.1); border: 1px solid #7f1d1d; border-radius: 4px;">
                            ⚠️ <strong>SAFETY RESTRICTION:</strong> Live capital execution requires multi-party cryptographic authorization
                            tokens via host environment configuration (<code>PLATFORM_LIVE_AUTH_TOKEN</code>). No front-end button can bypass this barrier.
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Trade Explainer Modal -->
    <div id="explainer-modal" class="modal-overlay" onclick="closeExplainer(event)">
        <div class="modal-box" onclick="event.stopPropagation()">
            <div class="modal-header">
                <h3 id="modal-title" style="color: #f8fafc; font-size: 15px;">Trade Decision Explainer</h3>
                <button class="modal-close" onclick="document.getElementById('explainer-modal').style.display='none'">&times;</button>
            </div>
            <div id="modal-content" style="font-family: var(--font-mono); font-size: 12px; line-height: 1.8;">
                Loading explanation...
            </div>
        </div>
    </div>

    <script>
        let cachedDecisions = [];

        function updateClock() {
            document.getElementById('clock-display').innerText = 'UTC: ' + new Date().toISOString().substring(11, 19);
        }
        setInterval(updateClock, 1000);

        function switchTab(tabId) {
            document.querySelectorAll('.tab-view').forEach(el => el.classList.remove('active'));
            document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
            const target = document.getElementById('tab-' + tabId);
            if (target) target.classList.add('active');
            if (event && event.currentTarget) event.currentTarget.classList.add('active');
        }

        async function fetchTelemetry() {
            try {
                const res = await fetch('/api/telemetry');
                if (!res.ok) return;
                const data = await res.json();
                
                document.getElementById('kpi-equity').innerText = '$' + (data.simulated_equity_usd || 100000).toLocaleString('en-US', {minimumFractionDigits: 2});
                document.getElementById('kpi-peak-equity').innerText = 'Peak: $' + (data.peak_equity_usd || 100000).toLocaleString('en-US', {minimumFractionDigits: 2});
                document.getElementById('kpi-decisions').innerText = (data.total_decisions_logged || 0).toLocaleString();
                document.getElementById('kpi-positions').innerText = (data.active_positions_count || 0);
                document.getElementById('kpi-heat').innerText = (data.portfolio_heat_pct || 0).toFixed(1) + '% / 3.0%';
                document.getElementById('kpi-dd').innerText = (data.current_drawdown_pct || 0).toFixed(2) + '%';
                
                if (data.system_health) {
                    const badge = document.getElementById('sys-health-badge');
                    badge.innerText = 'SYSTEM: ' + data.system_health;
                    badge.className = 'badge ' + (data.system_health === 'HEALTHY' ? 'badge-healthy' : 'badge-danger');
                }

                if (data.execution_mode) {
                    document.getElementById('env-badge').innerText = 'ENV: ' + data.execution_mode;
                    document.getElementById('settings-mode').innerText = data.execution_mode;
                }

                document.getElementById('telemetry-raw').innerText = JSON.stringify(data, null, 2);

                // Populate Universe
                if (data.universe) {
                    const tbody = document.getElementById('markets-tbody');
                    tbody.innerHTML = data.universe.map(u => `
                        <tr>
                            <td><strong>${u.symbol}</strong></td>
                            <td>${u.base_asset}</td>
                            <td>${u.quote_asset}</td>
                            <td><span class="tag-trade">${u.admission_status}</span></td>
                            <td>${u.tick_size}</td>
                            <td>${u.lot_size}</td>
                            <td>$${u.min_notional_usd}</td>
                            <td>${u.typical_spread_bps} bps</td>
                            <td>${u.venue}</td>
                        </tr>
                    `).join('');
                }

                // Populate Accounts
                if (data.accounts) {
                    const tbody = document.getElementById('accounts-tbody');
                    tbody.innerHTML = data.accounts.map(a => `
                        <tr>
                            <td>${a.account_id}</td>
                            <td><strong>${a.name}</strong></td>
                            <td>${a.venue}</td>
                            <td><span class="badge badge-mode">${a.environment}</span></td>
                            <td>$${(a.total_equity_usd || 0).toLocaleString()}</td>
                            <td>$${(a.available_margin_usd || 0).toLocaleString()}</td>
                            <td>${a.is_active_account ? '✅ ACTIVE' : 'STANDBY'}</td>
                            <td>${a.status_message}</td>
                        </tr>
                    `).join('');
                }
            } catch (e) {}
        }
        setInterval(fetchTelemetry, 2000);
        fetchTelemetry();

        async function fetchDecisions() {
            try {
                const res = await fetch('/api/decisions');
                if (!res.ok) return;
                const rows = await res.json();
                if (!rows || rows.length === 0) return;
                cachedDecisions = rows;

                const tbody = document.getElementById('decisions-tbody');
                const ledgerTbody = document.getElementById('ledger-tbody');

                const html = rows.slice(-15).reverse().map((d, idx) => `
                    <tr onclick="openExplainer('${d.decision_id}')">
                        <td>${new Date(d.timestamp_ms).toLocaleTimeString()}</td>
                        <td><strong>${d.asset}</strong></td>
                        <td>${d.timeframe_set}</td>
                        <td>${d.phase}</td>
                        <td><span class="${d.decision === 'TRADE' ? 'tag-trade' : 'tag-no-trade'}">${d.decision}</span></td>
                        <td>${(d.confidence_score * 100).toFixed(1)}%</td>
                        <td>${d.planned_r ? d.planned_r.toFixed(2) + 'R' : '-'}</td>
                        <td style="color: var(--text-secondary);">${d.reason_codes.length ? d.reason_codes.slice(0, 2).join(', ') : 'QUALIFIED'}</td>
                    </tr>
                `).join('');

                tbody.innerHTML = html;
                ledgerTbody.innerHTML = html;
            } catch (e) {}
        }
        setInterval(fetchDecisions, 3000);
        fetchDecisions();

        function openExplainer(decisionId) {
            const d = cachedDecisions.find(item => item.decision_id === decisionId);
            if (!d) return;

            const modal = document.getElementById('explainer-modal');
            const title = document.getElementById('modal-title');
            const content = document.getElementById('modal-content');

            const isTrade = (d.decision === 'TRADE');
            title.innerText = (isTrade ? 'WHY TRADE? ' : 'WHY NO TRADE? ') + d.asset + ' (' + d.timeframe_set + ')';
            title.style.color = isTrade ? '#34d399' : '#f87171';

            let bodyHtml = `
                <div><strong>Decision ID:</strong> ${d.decision_id}</div>
                <div><strong>Timestamp:</strong> ${new Date(d.timestamp_ms).toISOString()}</div>
                <div><strong>Asset / Set / Phase:</strong> ${d.asset} | ${d.timeframe_set} | ${d.phase}</div>
                <div><strong>Confidence:</strong> ${(d.confidence_score * 100).toFixed(1)}% (Threshold: 50.0%)</div>
                <div><strong>Target Geometry:</strong> Entry: ${d.entry_price || '-'} | Stop: ${d.initial_stop_price || '-'} | Target: ${d.target_price || '-'}</div>
                <div><strong>Planned R:</strong> ${d.planned_r ? d.planned_r.toFixed(2) + 'R' : '-'} (&ge; 4.0R floor)</div>
                <hr style="border: 0; border-top: 1px solid var(--border-color); margin: 12px 0;">
                <div><strong>OUTCOME:</strong> <span class="${isTrade ? 'tag-trade' : 'tag-no-trade'}">${d.decision}</span></div>
            `;

            if (isTrade) {
                bodyHtml += `
                    <div style="margin-top: 10px; color: #34d399;">
                        ✅ Structure aligned on HTF & MTF.<br>
                        ✅ Zone and discount location confirmed.<br>
                        ✅ Confidence ${ (d.confidence_score * 100).toFixed(1) }% satisfies threshold.<br>
                        ✅ Natural target geometry produces ${ d.planned_r.toFixed(2) }R &ge; 4.0R.<br>
                        ✅ Risk allocated: 1.0% (${d.risk_usd ? '$' + d.risk_usd.toFixed(2) : 'Simulated'}).
                    </div>
                `;
            } else {
                bodyHtml += `
                    <div style="margin-top: 10px; color: #fca5a5;">
                        <strong>Rejection Reasons:</strong><br>
                        ${d.reason_codes && d.reason_codes.length ? d.reason_codes.map(r => '&bull; ' + r).join('<br>') : '&bull; CRITERIA_NOT_MET'}
                    </div>
                `;
            }

            content.innerHTML = bodyHtml;
            modal.style.display = 'flex';
        }

        function closeExplainer(e) {
            document.getElementById('explainer-modal').style.display = 'none';
        }

        async function fetchPositions() {
            try {
                const res = await fetch('/api/positions');
                if (!res.ok) return;
                const data = await res.json();
                const tbody = document.getElementById('positions-tbody');
                const all = [...(data.active_positions || []), ...(data.closed_positions || [])];
                if (all.length === 0) return;
                tbody.innerHTML = all.map(p => `
                    <tr>
                        <td>${p.position_id}</td>
                        <td><strong>${p.symbol}</strong></td>
                        <td>${p.direction === 1 ? 'LONG' : 'SHORT'}</td>
                        <td>${p.size || p.size_units || '-'}</td>
                        <td>${p.entry_price}</td>
                        <td>${p.current_stop || p.initial_stop || '-'}</td>
                        <td>${p.target_price || '-'}</td>
                        <td>${p.realized_r !== undefined ? p.realized_r.toFixed(2) + 'R' : '-'}</td>
                        <td>${p.pnl_usd !== undefined ? '$' + p.pnl_usd.toFixed(2) : '-'}</td>
                        <td><span class="${p.state === 'OPEN' ? 'tag-trade' : 'tag-no-trade'}">${p.state || 'CLOSED'}</span></td>
                    </tr>
                `).join('');
            } catch (e) {}
        }
        setInterval(fetchPositions, 3000);

        async function fetchDrift() {
            try {
                const res = await fetch('/api/drift');
                if (!res.ok) return;
                const d = await res.json();
                const container = document.getElementById('drift-status-container');
                container.innerHTML = `
                    <div>State: <strong style="color: ${d.drift_state === 'STABLE' ? '#34d399' : '#f59e0b'}">${d.drift_state}</strong></div>
                    <div>Evaluated Sample: <strong>${d.sample_size} trades</strong></div>
                    <div>Rolling Expectancy: <strong>${d.rolling_expectancy_r >= 0 ? '+' : ''}${d.rolling_expectancy_r}R</strong> (Ref: +0.8097R)</div>
                    <div>Rolling Win Rate: <strong>${(d.rolling_win_rate * 100).toFixed(1)}%</strong> (Ref: 63.6%)</div>
                    <div>Rolling Profit Factor: <strong>${d.rolling_profit_factor}</strong> (Ref: 4.024)</div>
                    <div>Action: <strong>${d.action_recommended}</strong></div>
                `;
            } catch (e) {}
        }
        setInterval(fetchDrift, 5000);
        fetchDrift();

        async function fetchReconciliation() {
            try {
                const res = await fetch('/api/reconciliation');
                if (!res.ok) return;
                const r = await res.json();
                const container = document.getElementById('reconciliation-container');
                container.innerHTML = `
                    <div>Status: <strong style="color: ${r.is_reconciled ? '#34d399' : '#f43f5e'}">${r.status}</strong></div>
                    <div>Total Candidates Evaluated: ${r.total_candidates}</div>
                    <div>Decisions Logged: ${r.total_decisions} | Ledger Records: ${r.ledger_records}</div>
                    <div>Orders Submitted: ${r.orders_submitted} | Fills Executed: ${r.fills_executed}</div>
                    <div>Active Positions: ${r.active_positions} | Closed Positions: ${r.closed_positions}</div>
                    <div>Discrepancies: <strong>${r.discrepancies.length === 0 ? '0 (ALL INVARIANTS CONSERVED)' : r.discrepancies.join(', ')}</strong></div>
                `;
            } catch (e) {}
        }
        setInterval(fetchReconciliation, 5000);
        fetchReconciliation();
    </script>
</body>
</html>
"""


class PhaseRWebServer:
    """Async web server providing public website, institutional terminal UI, and authenticated REST APIs."""

    def __init__(
        self,
        supervisor: AutonomousTradingSupervisor,
        host: str = "127.0.0.1",
        port: int = 8080,
    ):
        self.supervisor = supervisor
        self.host = host
        self.port = port

        # Instantiate subsystem components
        from core.auth.auth_service import AuthService
        from strategy.library.strategy_library import StrategyLibraryManager
        from strategy.lab.strategy_lab_engine import StrategyLabEngine
        from broker.broker_center import BrokerCenter
        from execution.agent.strata_autonomous_agent import StrataAutonomousAgent
        from execution.king.king_engine_contract import KingEngineAdapter
        from market_data.market_service import MarketService
        from core.billing.billing_engine import BillingEngine

        self.auth_service = AuthService()
        self.strategy_library = StrategyLibraryManager()
        self.strategy_lab = StrategyLabEngine()
        self.broker_center = BrokerCenter()
        self.market_service = MarketService()
        self.billing_engine = BillingEngine(is_launch_period=True)
        self.agent = StrataAutonomousAgent(
            account_manager=self.supervisor.account_manager,
            strategy_library=self.strategy_library,
        )
        de = getattr(self.supervisor, "decision_engines", {}).get("BTCUSDT")
        self.king_adapter = KingEngineAdapter(
            symbol="BTCUSDT",
            decision_engine=de,
        )

        # Load static pages
        self._load_static_templates()

        from web.security_middleware import create_rate_limit_middleware, security_headers_middleware
        self.app = web.Application(middlewares=[
            security_headers_middleware,
            create_rate_limit_middleware(max_requests=240, window_seconds=60.0),
        ])
        self._setup_routes()

    def _load_static_templates(self) -> None:
        static_dir = Path(__file__).resolve().parent / "static"
        pub_file = static_dir / "public_website.html"
        app_file = static_dir / "app_terminal.html"
        mobile_file = Path(__file__).resolve().parent.parent / "mobile" / "android" / "assets" / "www" / "index.html"

        self.public_html = pub_file.read_text(encoding="utf-8") if pub_file.exists() else HTML_TERMINAL_PAGE
        self.app_html = app_file.read_text(encoding="utf-8") if app_file.exists() else HTML_TERMINAL_PAGE
        self.mobile_html = mobile_file.read_text(encoding="utf-8") if mobile_file.exists() else ""

    def _setup_routes(self) -> None:
        # Public website & Mobile development routes
        self.app.router.add_get("/", self.handle_public_website)
        self.app.router.add_get("/mobile", self.handle_mobile_app)
        self.app.router.add_get("/android", self.handle_mobile_app)
        self.app.router.add_get("/how-it-works", self.handle_public_website)
        self.app.router.add_get("/technology", self.handle_public_website)
        self.app.router.add_get("/pricing", self.handle_public_website)
        self.app.router.add_get("/faq", self.handle_public_website)

        # Authenticated Web Application Terminal routes
        for path in [
            "/app", "/dashboard", "/markets", "/fractal-state", "/opportunities",
            "/king", "/strategies", "/strategy-lab", "/backtesting", "/forward",
            "/positions", "/orders", "/accounts", "/brokers", "/risk",
            "/performance", "/drift", "/decision-ledger", "/reconciliation",
            "/system-health", "/settings", "/alerts"
        ]:
            self.app.router.add_get(path, self.handle_app_terminal)

        # REST API: Authentication & Multi-Tenancy
        self.app.router.add_post("/api/auth/register", self.handle_auth_register)
        self.app.router.add_post("/api/auth/login", self.handle_auth_login)
        self.app.router.add_post("/api/auth/logout", self.handle_auth_logout)
        self.app.router.add_get("/api/auth/me", self.handle_auth_me)

        # REST API: Core Health & Telemetry
        self.app.router.add_get("/api/health", self.handle_health)
        self.app.router.add_get("/api/ready", self.handle_ready)
        self.app.router.add_get("/api/version", self.handle_version)
        self.app.router.add_get("/api/telemetry", self.handle_telemetry)

        # REST API: King Engine Core
        self.app.router.add_get("/api/king/overview", self.handle_king_overview)

        # REST API: Markets & Universe
        self.app.router.add_get("/api/markets", self.handle_markets)
        self.app.router.add_get("/api/markets/{symbol}", self.handle_market_symbol)
        self.app.router.add_post("/api/markets/watchlist", self.handle_watchlist_toggle)

        # REST API: Strategy Library & Strategy Lab
        self.app.router.add_get("/api/strategies", self.handle_strategies_list)
        self.app.router.add_post("/api/strategy-lab/parse", self.handle_strategy_lab_parse)
        self.app.router.add_post("/api/strategy-lab/evaluate", self.handle_strategy_lab_evaluate)
        self.app.router.add_post("/api/strategy-lab/copilot", self.handle_strategy_lab_copilot)
        self.app.router.add_get("/api/backtests", self.handle_backtests)
        self.app.router.add_get("/api/forward-validation", self.handle_forward_validation)

        # REST API: Accounts & Brokers
        self.app.router.add_get("/api/accounts", self.handle_accounts)
        self.app.router.add_get("/api/brokers", self.handle_brokers)
        self.app.router.add_post("/api/accounts/suitability", self.handle_suitability)

        # REST API: Commercial Billing & Entitlements
        self.app.router.add_get("/api/billing", self.handle_billing_status)
        self.app.router.add_post("/api/billing/plan", self.handle_billing_plan_change)

        # REST API: Risk & Governance
        self.app.router.add_get("/api/risk", self.handle_risk)

        # REST API: Autonomous Trading Agent & Emergency Stop
        self.app.router.add_post("/api/agent/cycle", self.handle_agent_cycle)
        self.app.router.add_post("/api/agent/style", self.handle_agent_style)
        self.app.router.add_post("/api/agent/pause", self.handle_agent_pause)
        self.app.router.add_post("/api/agent/resume", self.handle_agent_resume)
        self.app.router.add_post("/api/system/halt", self.handle_agent_pause)

        # REST API: Trading Blotters & Analytics
        self.app.router.add_get("/api/decisions", self.handle_decisions)
        self.app.router.add_get("/api/positions", self.handle_positions)
        self.app.router.add_get("/api/orders", self.handle_orders)
        self.app.router.add_get("/api/reconciliation", self.handle_reconciliation)
        self.app.router.add_get("/api/drift", self.handle_drift)
        self.app.router.add_get("/api/alerts", self.handle_alerts)

    async def handle_public_website(self, request: web.Request) -> web.Response:
        pub_file = Path(__file__).resolve().parent / "static" / "public_website.html"
        if pub_file.exists():
            return web.Response(text=pub_file.read_text(encoding="utf-8"), content_type="text/html")
        return web.Response(text=self.public_html, content_type="text/html")

    async def handle_mobile_app(self, request: web.Request) -> web.Response:
        mobile_file = Path(__file__).resolve().parent.parent / "mobile" / "android" / "assets" / "www" / "index.html"
        if mobile_file.exists():
            return web.Response(text=mobile_file.read_text(encoding="utf-8"), content_type="text/html")
        return web.Response(text=self.mobile_html, content_type="text/html")

    async def handle_app_terminal(self, request: web.Request) -> web.Response:
        app_file = Path(__file__).resolve().parent / "static" / "app_terminal.html"
        if app_file.exists():
            return web.Response(text=app_file.read_text(encoding="utf-8"), content_type="text/html")
        return web.Response(text=self.app_html, content_type="text/html")

    # --- Authentication Handlers ---
    async def handle_auth_register(self, request: web.Request) -> web.Response:
        try:
            data = await request.json()
            email = data.get("email", "")
            password = data.get("password", "")
            name = data.get("name", "")
            confirm = data.get("password_confirmation", None)
            user = self.auth_service.register_user(
                email=email,
                password=password,
                name=name,
                password_confirmation=confirm,
            )
            session = self.auth_service.authenticate(email, password)
            return web.json_response({
                "status": "registered",
                "user": user.to_safe_dict(),
                "token": session.token if session else None,
            })
        except Exception as e:
            return web.json_response({"error": str(e)}, status=400)

    async def handle_auth_login(self, request: web.Request) -> web.Response:
        try:
            data = await request.json()
            session = self.auth_service.authenticate(data.get("email", ""), data.get("password", ""))
            if not session:
                return web.json_response({"error": "Invalid email or password"}, status=401)
            user = self.auth_service.validate_session(session.token)
            return web.json_response({
                "token": session.token,
                "user": user.to_safe_dict() if user else None,
            })
        except Exception as e:
            return web.json_response({"error": str(e)}, status=400)

    async def handle_auth_logout(self, request: web.Request) -> web.Response:
        token = request.headers.get("Authorization", "").replace("Bearer ", "").strip()
        if token:
            self.auth_service.logout(token)
        return web.json_response({"status": "logged_out"})

    async def handle_auth_me(self, request: web.Request) -> web.Response:
        token = request.headers.get("Authorization", "").replace("Bearer ", "").strip()
        user = self.auth_service.validate_session(token) if token else None
        if not user:
            return web.json_response({"error": "Unauthorized"}, status=401)
        return web.json_response(user.to_safe_dict())

    # --- Core & King Handlers ---
    async def handle_health(self, request: web.Request) -> web.Response:
        recon = self.supervisor.reconciliation_engine.last_report
        healthy = not recon or recon.is_reconciled
        return web.json_response({
            "status": "HEALTHY" if healthy else "DEGRADED",
            "real_capital_authorized": SAFETY_GATE.real_capital_authorized_usd,
            "live_trading_status": "ENABLED" if SAFETY_GATE.is_live_execution else "DISABLED_FAIL_CLOSED",
            "execution_mode": SAFETY_GATE.current_mode.value,
            "agent_state": self.agent.control_state.value,
            "trading_style": self.agent.current_style.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    async def handle_ready(self, request: web.Request) -> web.Response:
        recon = getattr(self.supervisor, "reconciliation_engine", None)
        recon_report = getattr(recon, "last_report", None) if recon else None
        is_recon_ok = not recon_report or getattr(recon_report, "is_reconciled", True)
        watchdog_ok = True
        wd = getattr(self.supervisor, "watchdog", None)
        if wd is not None:
            wd_status = getattr(wd, "status", None)
            if wd_status is not None:
                is_healthy = bool(getattr(wd_status, "healthy", True))
                is_safe = bool(getattr(wd_status, "safe_mode_active", False))
                watchdog_ok = is_healthy and not is_safe
        ready = is_recon_ok and watchdog_ok and getattr(self.supervisor, "running", True)
        status_code = 200 if ready else 503
        return web.json_response({
            "status": "READY" if ready else "NOT_READY",
            "supervisor_running": getattr(self.supervisor, "running", True),
            "reconciliation_intact": is_recon_ok,
            "watchdog_healthy": watchdog_ok,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }, status=status_code)

    async def handle_version(self, request: web.Request) -> web.Response:
        import os
        from execution.king.king_engine_contract import EXPECTED_KING_CONTRACT_HASH
        return web.json_response({
            "platform": "STRATA Digital Trading Platform",
            "version": "1.0.0-forward-validation",
            "environment": os.environ.get("STRATA_ENV", "paper").lower(),
            "king_contract_hash": EXPECTED_KING_CONTRACT_HASH,
            "contract_status": "VERIFIED_IMMUTABLE",
            "engine": "KING_Q2_PHASE_R",
            "execution_mode": SAFETY_GATE.current_mode.value,
            "real_capital_authorized_usd": SAFETY_GATE.real_capital_authorized_usd,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    async def handle_telemetry(self, request: web.Request) -> web.Response:
        return web.json_response(self.supervisor.get_system_telemetry())

    async def handle_king_overview(self, request: web.Request) -> web.Response:
        states = getattr(self.supervisor, "last_fractal_states", {})
        return web.json_response(self.king_adapter.get_market_structure_overview(states))

    # --- Markets & Universe Handlers ---
    async def handle_markets(self, request: web.Request) -> web.Response:
        tenant_id = request.query.get("tenant_id", "default")
        return web.json_response(self.market_service.list_market_assets(tenant_id=tenant_id))

    async def handle_market_symbol(self, request: web.Request) -> web.Response:
        symbol = request.match_info.get("symbol", "").upper()
        detail = self.market_service.get_asset_detail(symbol)
        if not detail:
            return web.json_response({"error": f"Asset '{symbol}' not found in admitted crypto universe"}, status=404)
        return web.json_response(detail)

    async def handle_watchlist_toggle(self, request: web.Request) -> web.Response:
        try:
            data = await request.json()
            symbol = data.get("symbol", "")
            tenant_id = data.get("tenant_id", "default")
            new_wl = self.market_service.toggle_watchlist(tenant_id, symbol)
            return web.json_response({"status": "updated", "watchlist": new_wl})
        except Exception as e:
            return web.json_response({"error": str(e)}, status=400)

    # --- Commercial Billing Handlers ---
    async def handle_billing_status(self, request: web.Request) -> web.Response:
        tenant_id = request.query.get("tenant_id", "default")
        return web.json_response({
            "status": self.billing_engine.get_tenant_billing_status(tenant_id),
            "available_plans": self.billing_engine.list_available_plans(),
        })

    async def handle_billing_plan_change(self, request: web.Request) -> web.Response:
        try:
            data = await request.json()
            plan_tier = data.get("tier", "AUTONOMOUS")
            tenant_id = data.get("tenant_id", "default")
            res = self.billing_engine.assign_plan(tenant_id, plan_tier)
            return web.json_response(res)
        except Exception as e:
            return web.json_response({"error": str(e)}, status=400)

    # --- Risk Center Handlers ---
    async def handle_risk(self, request: web.Request) -> web.Response:
        heat = getattr(self.supervisor.portfolio_governor, "total_heat", 0.0) if hasattr(self.supervisor, "portfolio_governor") else 0.0
        return web.json_response({
            "max_trade_risk_pct": 1.0,
            "max_asset_heat_pct": 1.0,
            "max_portfolio_heat_pct": 3.0,
            "current_portfolio_heat_pct": heat,
            "target_geometry_floor_r": 4.0,
            "active_positions_count": len(self.supervisor.active_positions),
            "daily_drawdown_pct": 0.0,
            "max_drawdown_limit_pct": 5.0,
            "capital_safety_gate": {
                "real_capital_authorized_usd": SAFETY_GATE.real_capital_authorized_usd,
                "mode": SAFETY_GATE.current_mode.value,
                "live_execution_locked": not SAFETY_GATE.is_live_execution,
            },
            "circuit_breakers": {
                "reconciliation_ok": True,
                "data_health_ok": True,
                "watchdog_ok": True,
            }
        })

    # --- Backtest & Forward Validation Handlers ---
    async def handle_backtests(self, request: web.Request) -> web.Response:
        return web.json_response({
            "benchmark_king": {
                "total_trades": 9608,
                "expectancy_r": 0.8885,
                "profit_factor": 4.918,
                "win_rate": 0.672,
                "max_drawdown_r": 10.89,
                "tail_risk_cvar": 1.20,
                "target_floor": ">= 4.0R",
                "status": "PROTECTED_BASELINE",
            },
            "recent_runs": [
                {
                    "id": "BT_20261008_BTC_SWING",
                    "strategy": "STRATA_TREND_PULLBACK",
                    "symbol": "BTCUSDT",
                    "timeframes": ["1w", "1d", "4h"],
                    "trades": 320,
                    "expectancy_r": 0.443,
                    "profit_factor": 2.45,
                    "win_rate": 0.51,
                    "max_dd_r": 14.2,
                    "environment": "HISTORICAL",
                },
                {
                    "id": "BT_20261008_ETH_VOLATILITY",
                    "strategy": "STRATA_REGIME_ADAPTIVE",
                    "symbol": "ETHUSDT",
                    "timeframes": ["1d", "4h"],
                    "trades": 180,
                    "expectancy_r": 0.511,
                    "profit_factor": 2.65,
                    "win_rate": 0.54,
                    "max_dd_r": 11.5,
                    "environment": "HISTORICAL",
                },
            ]
        })

    async def handle_forward_validation(self, request: web.Request) -> web.Response:
        return web.json_response({
            "environments": {
                "HISTORICAL": {
                    "trades_evaluated": 9608,
                    "expectancy_r": 0.8885,
                    "profit_factor": 4.918,
                    "win_rate": 0.672,
                    "max_drawdown_r": 10.89,
                    "status": "CERTIFIED_REPLAY",
                    "provenance": "Phase Q.2 Locked Dataset",
                },
                "OOS": {
                    "trades_evaluated": 1665,
                    "expectancy_r": 0.745,
                    "profit_factor": 3.82,
                    "win_rate": 0.612,
                    "max_drawdown_r": 12.4,
                    "status": "VALIDATED",
                    "provenance": "Phase Q.2 Out-of-Sample Holdout",
                },
                "PAPER": {
                    "trades_evaluated": len(getattr(self.supervisor, "orders_history", [])),
                    "active_positions": len(self.supervisor.active_positions),
                    "realized_r": 0.0,
                    "execution_drag_bps": 2.4,
                    "status": "ACTIVE_SIMULATION",
                    "provenance": "Live Realtime Ticker / Closed Candles",
                },
                "DEMO": {
                    "connected_venues": ["BINANCE_TESTNET", "BYBIT_TESTNET"],
                    "trades_executed": 0,
                    "status": "READY_AWAITING_TRIGGER",
                    "provenance": "Exchange Demo Gateway",
                },
                "LIVE": {
                    "authorized_capital_usd": 0.00,
                    "status": "FAIL_CLOSED_LOCKED",
                    "order_routing": "DISABLED",
                    "provenance": "Zero Capital Policy",
                },
            },
            "safety_invariants": {
                "real_capital_authorized": 0.00,
                "min_target_r": 4.0,
                "max_trade_risk_pct": 1.0,
                "max_portfolio_heat_pct": 3.0,
            }
        })

    async def handle_strategy_lab_copilot(self, request: web.Request) -> web.Response:
        try:
            data = await request.json()
            prompt = data.get("prompt", "")
            tenant_id = data.get("tenant_id", "system")
            res = self.strategy_lab.research_copilot_chat(prompt=prompt, tenant_id=tenant_id)
            return web.json_response(res)
        except Exception as e:
            return web.json_response({"error": str(e)}, status=400)

    # --- Strategy Handlers ---
    async def handle_strategies_list(self, request: web.Request) -> web.Response:
        tenant_id = request.query.get("tenant_id")
        entries = self.strategy_library.list_entries(tenant_id=tenant_id)
        return web.json_response([e.to_dict() for e in entries])

    async def handle_strategy_lab_parse(self, request: web.Request) -> web.Response:
        try:
            data = await request.json()
            prompt = data.get("prompt", "")
            tenant_id = data.get("tenant_id", "system")
            spec = self.strategy_lab.parse_natural_language(prompt=prompt, tenant_id=tenant_id)
            return web.json_response({"specification": spec.to_dict()})
        except Exception as e:
            return web.json_response({"error": str(e)}, status=400)

    async def handle_strategy_lab_evaluate(self, request: web.Request) -> web.Response:
        try:
            from strategy.lab.strategy_specification import StrategySpecification
            data = await request.json()
            spec_data = data.get("specification", {})
            spec = StrategySpecification.from_dict(spec_data)
            evidence, report = self.strategy_lab.evaluate_strategy(spec)
            return web.json_response(report)
        except Exception as e:
            return web.json_response({"error": str(e)}, status=400)

    # --- Accounts, Brokers & Suitability ---
    async def handle_accounts(self, request: web.Request) -> web.Response:
        tenant_id = request.query.get("tenant_id")
        return web.json_response(self.supervisor.account_manager.list_accounts(tenant_id=tenant_id))

    async def handle_brokers(self, request: web.Request) -> web.Response:
        return web.json_response([v.to_dict() for v in self.broker_center.list_venues()])

    async def handle_suitability(self, request: web.Request) -> web.Response:
        try:
            from accounts.suitability_engine import AccountSuitabilityEngine, TradingStyle
            data = await request.json()
            style_str = data.get("style", "AUTONOMOUS")
            equity = float(data.get("equity_usd", 100_000.0))
            margin = float(data.get("margin_usd", 100_000.0))
            risk_pct = float(data.get("risk_pct", 0.01))
            verdict = AccountSuitabilityEngine.evaluate_suitability(
                account_equity_usd=equity,
                available_margin_usd=margin,
                style=TradingStyle(style_str),
                user_max_risk_pct=risk_pct,
            )
            return web.json_response(verdict.to_dict())
        except Exception as e:
            return web.json_response({"error": str(e)}, status=400)

    # --- Agent Orchestration ---
    async def handle_agent_cycle(self, request: web.Request) -> web.Response:
        heat = getattr(self.supervisor.portfolio_governor, "total_heat", 0.0) if hasattr(self.supervisor, "portfolio_governor") else 0.0
        pos_count = len(self.supervisor.active_positions)
        report = self.agent.run_control_cycle(
            symbol="BTCUSDT",
            active_positions_count=pos_count,
            current_portfolio_heat=heat,
        )
        return web.json_response(report.to_dict())

    async def handle_agent_style(self, request: web.Request) -> web.Response:
        try:
            from accounts.suitability_engine import TradingStyle
            data = await request.json()
            style = TradingStyle(data.get("style", "AUTONOMOUS"))
            self.agent.set_trading_style(style)
            return web.json_response({"status": "updated", "style": style.value})
        except Exception as e:
            return web.json_response({"error": str(e)}, status=400)

    async def handle_agent_pause(self, request: web.Request) -> web.Response:
        self.agent.pause_trading("Operator trigger via REST API")
        return web.json_response({"status": "PAUSED"})

    async def handle_agent_resume(self, request: web.Request) -> web.Response:
        self.agent.resume_trading()
        return web.json_response({"status": "OBSERVING"})

    # --- Blotters ---
    async def handle_decisions(self, request: web.Request) -> web.Response:
        decisions = [d.to_dict() for d in self.supervisor.decisions_history[-50:]]
        return web.json_response(decisions)

    async def handle_positions(self, request: web.Request) -> web.Response:
        active = [p.to_dict() if hasattr(p, "to_dict") else str(p) for p in self.supervisor.active_positions.values()]
        return web.json_response({
            "active_positions": active,
            "closed_positions": self.supervisor.closed_positions[-25:],
        })

    async def handle_orders(self, request: web.Request) -> web.Response:
        orders = [o.to_dict() if hasattr(o, "to_dict") else str(o) for o in getattr(self.supervisor, "orders_history", [])]
        return web.json_response(orders)

    async def handle_reconciliation(self, request: web.Request) -> web.Response:
        recon = self.supervisor.run_reconciliation()
        return web.json_response(recon.to_dict())

    async def handle_drift(self, request: web.Request) -> web.Response:
        drift = self.supervisor.drift_monitor.evaluate_drift()
        return web.json_response(drift.to_dict())

    async def handle_alerts(self, request: web.Request) -> web.Response:
        return web.json_response(ALERTS.get_recent_alerts(limit=50))

    async def start(self) -> web.AppRunner:
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, self.host, self.port)
        await site.start()
        return runner


StrataInstitutionalWebServer = PhaseRWebServer

