/**
 * Institutional Crypto Platform — Web Application Client Logic
 * Real-time WebSocket streaming, broker management, strategy toggles, and emergency kill controls.
 */

// Application State
const state = {
  status: {},
  portfolio: {},
  funnel: {},
  strategies: [],
  accounts: [],
  ws: null,
};

// DOM Elements
const el = {
  systemStatusText: document.getElementById('txt-system-status'),
  systemStatusPill: document.getElementById('pill-system-status'),
  planeText: document.getElementById('txt-plane'),
  netEquity: document.getElementById('val-net-equity'),
  dailyPnl: document.getElementById('val-daily-pnl'),
  drawdown: document.getElementById('val-drawdown'),
  leverage: document.getElementById('val-leverage'),
  tbodyPositions: document.getElementById('tbody-positions'),
  tbodyFills: document.getElementById('tbody-fills'),
  positionCountBadge: document.getElementById('badge-position-count'),
  fillsCountBadge: document.getElementById('badge-fills-count'),
  funnelTicks: document.getElementById('funnel-val-ticks'),
  funnelClosedBars: document.getElementById('funnel-val-closed-bars'),
  funnelEvals: document.getElementById('funnel-val-evals'),
  funnelSignals: document.getElementById('funnel-val-signals'),
  funnelRiskPassed: document.getElementById('funnel-val-risk-passed'),
  funnelOrders: document.getElementById('funnel-val-orders'),
  funnelFills: document.getElementById('funnel-val-fills'),
  strategiesGrid: document.getElementById('strategies-grid'),
  accountsList: document.getElementById('accounts-list'),
  terminalLog: document.getElementById('terminal-log'),
  brokerModal: document.getElementById('broker-modal'),
  btnOpenBrokerModal: document.getElementById('btn-open-broker-modal'),
  btnCloseBrokerModal: document.getElementById('btn-close-broker-modal'),
  btnCancelModal: document.getElementById('btn-cancel-modal'),
  formConnectBroker: document.getElementById('form-connect-broker'),
  btnEmergencyKill: document.getElementById('btn-emergency-kill'),
  btnRefreshPortfolio: document.getElementById('btn-refresh-portfolio'),
  btnClearLogs: document.getElementById('btn-clear-logs'),
};

// Log Message Helper
function appendLog(message, type = 'info') {
  const line = document.createElement('div');
  line.className = `log-line log-${type}`;
  const timestamp = new Date().toLocaleTimeString();
  line.textContent = `[${timestamp}] ${message}`;
  el.terminalLog.appendChild(line);
  el.terminalLog.scrollTop = el.terminalLog.scrollHeight;
}

// Fetch Initial Data
async function loadPlatformData() {
  try {
    const [statusRes, portRes, funnelRes, stratRes, accRes, canaryRes] = await Promise.all([
      fetch('/api/status').then(r => r.json()),
      fetch('/api/portfolio').then(r => r.json()),
      fetch('/api/funnel').then(r => r.json()),
      fetch('/api/strategies').then(r => r.json()),
      fetch('/api/accounts').then(r => r.json()),
      fetch('/api/canary/status').then(r => r.json()).catch(() => ({})),
    ]);

    state.status = statusRes;
    state.portfolio = portRes;
    state.funnel = funnelRes;
    state.strategies = stratRes.strategies || [];
    state.accounts = accRes.accounts || [];
    state.canary = canaryRes || {};

    renderUI();
  } catch (err) {
    appendLog(`Failed to fetch initial telemetry: ${err.message}`, 'error');
  }
}

// Render Dashboard UI
function renderUI() {
  // System Status
  const isHalted = state.status.status === 'EMERGENCY_HALTED' || state.status.emergency_kill_active;
  if (isHalted) {
    el.systemStatusText.textContent = 'EMERGENCY HALTED';
    el.systemStatusPill.className = 'status-pill status-locked';
  } else {
    el.systemStatusText.textContent = 'OPERATIONAL';
    el.systemStatusPill.className = 'status-pill status-healthy';
  }

  // Toggle Reset Kill button
  const btnResetKill = document.getElementById('btn-reset-kill');
  if (btnResetKill) {
    btnResetKill.style.display = isHalted ? 'inline-flex' : 'none';
  }

  const isCanary = (state.status.environment || '').toUpperCase().includes('CANARY');
  if (isCanary) {
    el.planeText.textContent = 'OPERATING PLANE: LIVE-CANARY';
    el.planeText.parentElement.className = 'status-pill status-canary';
    const lockTxt = document.getElementById('txt-capital-lock');
    if (lockTxt) {
      lockTxt.textContent = `CANARY CAPITAL: $${Number(state.status.canary_capital_limit_usd || 0).toFixed(2)} (${state.status.canary_state || 'DISARMED'})`;
      lockTxt.parentElement.className = (state.status.canary_state === 'ACTIVE') ? 'status-pill status-canary' : 'status-pill status-locked';
    }
  } else {
    el.planeText.textContent = `OPERATING PLANE: ${state.status.environment || 'PAPER'}`;
    el.planeText.parentElement.className = 'status-pill status-plane';
    const lockTxt = document.getElementById('txt-capital-lock');
    if (lockTxt) {
      lockTxt.textContent = 'LIVE CAPITAL: $0.00 (LOCKED)';
      lockTxt.parentElement.className = 'status-pill status-locked';
    }
  }

  // LIVE-CANARY HUD Panel
  if (state.canary && Object.keys(state.canary).length > 0) {
    const c = state.canary;
    const badgeState = document.getElementById('badge-canary-state');
    if (badgeState) {
      badgeState.textContent = `STATE: ${c.state || 'DISARMED'}`;
      badgeState.style.background = c.state === 'ACTIVE' ? 'var(--color-green)' : (c.state === 'ARMED' ? 'var(--color-amber)' : 'rgba(255,255,255,0.1)');
    }
    const setVal = (id, val) => { const elem = document.getElementById(id); if (elem) elem.textContent = val; };
    setVal('canary-val-plane', c.operating_plane || 'LIVE-CANARY');
    setVal('canary-val-real-capital', `$${Number(c.canary_capital_limit_usd || 0).toFixed(2)}`);
    setVal('canary-val-allocation', `$${Number(c.canary_capital_limit_usd || 0).toFixed(2)}`);
    setVal('canary-val-equity', `$${Number(c.current_equity_usd || 0).toFixed(2)}`);
    setVal('canary-val-peak', `Peak: $${Number(c.peak_equity_usd || 0).toFixed(2)}`);
    setVal('canary-val-realized-pnl', `$${Number(c.realized_pnl_usd || 0).toFixed(2)}`);
    setVal('canary-val-unrealized-pnl', `$${Number(c.unrealized_pnl_usd || 0).toFixed(2)}`);
    setVal('canary-val-drawdown', `${Number(c.drawdown_pct || 0).toFixed(2)}%`);
    setVal('canary-val-exposure', `$${Number(c.canary_max_position_size || 500).toFixed(2)} limit`);
    setVal('canary-val-leverage', `${Number(c.canary_max_leverage || 1.5).toFixed(2)}x max`);
    setVal('canary-val-positions', `${c.open_positions_count || 0}`);
    setVal('canary-val-orders', `${c.total_orders || 0} / ${c.total_fills || 0}`);
    setVal('canary-val-fees', `$${Number(c.total_fees_usd || 0).toFixed(4)}`);
    setVal('canary-val-funding', `$${Number(c.funding_accrued_usd || 0).toFixed(4)}`);
    setVal('canary-val-broker', c.broker_connected ? 'CONNECTED' : (c.broker_venue ? `${c.broker_venue.toUpperCase()} (STANDBY)` : 'STANDBY'));
    setVal('canary-val-risk', c.state === 'HALTED' ? 'BLOCKED' : 'ENFORCED');
    setVal('canary-val-kill-status', c.emergency_kill_active ? 'TRIPPED / HALTED' : 'STANDBY (READY)');
  }

  // Metrics
  if (state.portfolio) {
    el.netEquity.textContent = `$${Number(state.portfolio.current_equity_usd || 100000).toLocaleString('en-US', { minimumFractionDigits: 2 })}`;
    const pnl = Number(state.portfolio.unrealized_pnl_usd || 0);
    el.dailyPnl.textContent = `${pnl >= 0 ? '+' : ''}$${pnl.toFixed(2)} (${state.portfolio.daily_return_bps || 0.0} bps) Today`;
    el.drawdown.textContent = `${(state.portfolio.max_drawdown_pct || 0).toFixed(2)}%`;
    el.leverage.textContent = `${(state.portfolio.portfolio_leverage || 0).toFixed(3)}x`;

    // Positions Table
    const positions = state.portfolio.open_positions || [];
    el.positionCountBadge.textContent = `${positions.length} Active`;
    if (positions.length > 0) {
      el.tbodyPositions.innerHTML = positions.map(pos => `
        <tr>
          <td class="cell-symbol">${pos.symbol}</td>
          <td><span class="tag ${pos.side === 'LONG' ? 'tag-long' : 'tag-short'}">${pos.side}</span></td>
          <td>${Number(pos.quantity).toLocaleString()}</td>
          <td>$${Number(pos.entry_price).toFixed(4)}</td>
          <td>$${Number(pos.mark_price).toFixed(4)}</td>
          <td class="${pos.unrealized_pnl_usd >= 0 ? 'positive' : 'negative'}">
            ${pos.unrealized_pnl_usd >= 0 ? '+' : ''}$${Number(pos.unrealized_pnl_usd).toFixed(2)}
          </td>
          <td class="cell-muted">${pos.strategy_id}</td>
        </tr>
      `).join('');
    } else {
      el.tbodyPositions.innerHTML = '<tr><td colspan="7" class="cell-muted" style="text-align: center;">No active open positions</td></tr>';
    }

    // Recent Fills Table
    const fills = state.portfolio.recent_fills || [];
    el.fillsCountBadge.textContent = `${fills.length} Fill${fills.length === 1 ? '' : 's'}`;
    if (fills.length > 0) {
      el.tbodyFills.innerHTML = fills.map(f => `
        <tr>
          <td>${new Date(f.timestamp_ms || Date.now()).toLocaleTimeString()}</td>
          <td class="cell-symbol">${f.symbol}</td>
          <td><span class="tag ${f.side === 'BUY' ? 'tag-long' : 'tag-short'}">${f.side}</span></td>
          <td>$${Number(f.price).toFixed(4)}</td>
          <td>${Number(f.quantity).toLocaleString()}</td>
          <td>$${Number(f.fee_usd || 0).toFixed(4)}</td>
          <td>${f.slippage_bps || 0.0} bps</td>
        </tr>
      `).join('');
    } else {
      el.tbodyFills.innerHTML = '<tr><td colspan="7" class="cell-muted" style="text-align: center;">No recent executions</td></tr>';
    }
  }

  // Funnel Telemetry
  if (state.funnel) {
    el.funnelTicks.textContent = Number(state.funnel.market_events || 0).toLocaleString();
    el.funnelClosedBars.textContent = Number(state.funnel.closed_candles || 0).toLocaleString();
    el.funnelEvals.textContent = Number(state.funnel.strategy_evaluations || 0).toLocaleString();
    el.funnelSignals.textContent = Number(state.funnel.signals || 0).toLocaleString();
    el.funnelRiskPassed.textContent = `${state.funnel.risk_accepted || 0} (${state.funnel.risk_rejections || 0} Gated)`;
    el.funnelOrders.textContent = Number(state.funnel.oms_acceptances || 0).toLocaleString();
    el.funnelFills.textContent = `${state.funnel.total_fills || 0} (Partial Fill)`;

    // Dynamically render failure codes in Funnel
    const rejContainer = document.getElementById('rejection-tags');
    if (rejContainer && state.funnel.rejection_reasons) {
      const keys = Object.keys(state.funnel.rejection_reasons);
      if (keys.length > 0) {
        rejContainer.innerHTML = keys.map(k => `
          <span class="rej-badge">${k}: ${Number(state.funnel.rejection_reasons[k]).toLocaleString()}</span>
        `).join('');
      } else {
        rejContainer.innerHTML = '<span class="cell-muted" style="font-size: 11px;">Zero risk rejections recorded</span>';
      }
    }
  }

  // Strategies Grid
  if (state.strategies) {
    el.strategiesGrid.innerHTML = state.strategies.map(s => `
      <div class="strategy-card ${s.active ? 'active' : 'paused'}" id="card-${s.id}">
        <div class="strat-header">
          <div>
            <div class="strat-id">${s.id}</div>
            <div class="strat-family">${s.family}</div>
          </div>
          <label class="toggle-switch">
            <input type="checkbox" ${s.active ? 'checked' : ''} onchange="toggleStrategy('${s.id}')">
            <span class="slider"></span>
          </label>
        </div>
        <div class="strat-details">
          <span>Horizon: <strong>${s.horizon}</strong></span>
          <span>Risk: <strong>${s.risk_budget_pct}%</strong></span>
        </div>
        <div class="strat-symbols cell-muted">
          Symbols: ${s.symbols.join(', ')}
        </div>
      </div>
    `).join('');
  }

  // Accounts List
  if (state.accounts) {
    el.accountsList.innerHTML = state.accounts.map(acc => `
      <div class="account-item">
        <div>
          <div class="acc-venue">${acc.venue.toUpperCase()}</div>
          <div class="acc-key">Key: ${acc.api_key_masked} | Account: ${acc.account_id}</div>
        </div>
        <span class="acc-status tag ${acc.mode === 'LIVE' ? 'tag-short' : 'tag-long'}">${acc.mode}</span>
      </div>
    `).join('');
  }
}

// Toggle Strategy
async function toggleStrategy(strategyId) {
  try {
    const res = await fetch(`/api/strategies/${strategyId}/toggle`, { method: 'POST' });
    const data = await res.json();
    appendLog(data.message, 'success');
    const strat = state.strategies.find(s => s.id === strategyId);
    if (strat) {
      strat.active = data.active;
      const card = document.getElementById(`card-${strategyId}`);
      if (card) {
        card.className = `strategy-card ${data.active ? 'active' : 'paused'}`;
      }
    }
  } catch (err) {
    appendLog(`Failed to toggle strategy ${strategyId}: ${err.message}`, 'error');
  }
}

// Emergency Kill Switch
async function triggerEmergencyKill() {
  if (!confirm('CONFIRM EMERGENCY KILL: This will halt all active strategy books and cancel pending orders!')) {
    return;
  }
  try {
    const res = await fetch('/api/emergency_kill', { method: 'POST' });
    const data = await res.json();
    appendLog(`[CIRCUIT BREAKER] ${data.message}`, 'error');
    state.status.status = 'EMERGENCY_HALTED';
    state.strategies.forEach(s => s.active = false);
    renderUI();
  } catch (err) {
    appendLog(`Emergency kill failed: ${err.message}`, 'error');
  }
}

// Connect Broker Account Form
async function handleBrokerSubmit(e) {
  e.preventDefault();
  const venue = document.getElementById('select-venue').value;
  const mode = document.getElementById('select-mode').value;
  const apiKey = document.getElementById('input-api-key').value;
  const apiSecret = document.getElementById('input-api-secret').value;

  appendLog(`Verifying credentials and non-custodial permissions for ${venue}...`, 'info');

  try {
    const res = await fetch('/api/accounts', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ venue, mode, api_key: apiKey, api_secret: apiSecret }),
    });

    const data = await res.json();
    if (!res.ok) {
      appendLog(`Connection Rejected: ${data.error}`, 'error');
      alert(`Connection Rejected: ${data.error}`);
      return;
    }

    appendLog(`Broker account successfully connected: ${data.account_id} (${data.venue})`, 'success');
    alert(`Success: ${data.message}`);
    el.brokerModal.classList.remove('open');
    el.formConnectBroker.reset();
    await loadPlatformData();
  } catch (err) {
    appendLog(`Network error connecting broker: ${err.message}`, 'error');
  }
}

// Real-Time WebSocket Streaming
function initWebSocket() {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsUrl = `${protocol}//${window.location.host}/ws/stream`;

  state.ws = new WebSocket(wsUrl);

  state.ws.onopen = () => {
    appendLog('Real-time WebSocket telemetry stream established.', 'success');
  };

  state.ws.onmessage = async (event) => {
    try {
      const data = JSON.parse(event.data);
      if (data.event === 'STRATEGY_TOGGLED') {
        const strat = state.strategies.find(s => s.id === data.strategy_id);
        if (strat) {
          strat.active = data.active;
          renderUI();
        }
      } else if (data.event === 'EMERGENCY_KILL_ACTIVATED') {
        state.status.status = 'EMERGENCY_HALTED';
        state.status.emergency_kill_active = true;
        state.strategies.forEach(s => s.active = false);
        renderUI();
      } else if (data.event === 'EMERGENCY_KILL_RESET') {
        state.status.status = 'HEALTHY';
        state.status.emergency_kill_active = false;
        await loadPlatformData();
      } else if (data.event === 'CANARY_STATE_CHANGED') {
        await loadPlatformData();
      }
    } catch (e) {
      // Non-JSON ping/pong or raw message
    }
  };

  state.ws.onclose = () => {
    appendLog('WebSocket disconnected. Reconnecting in 3s...', 'warn');
    setTimeout(initWebSocket, 3000);
  };
}

// Event Listeners
el.btnOpenBrokerModal.addEventListener('click', () => el.brokerModal.classList.add('open'));
el.btnCloseBrokerModal.addEventListener('click', () => el.brokerModal.classList.remove('open'));
el.btnCancelModal.addEventListener('click', () => el.brokerModal.classList.remove('open'));
el.formConnectBroker.addEventListener('submit', handleBrokerSubmit);
el.btnEmergencyKill.addEventListener('click', triggerEmergencyKill);

// Portfolio Refresh Listener
if (el.btnRefreshPortfolio) {
  el.btnRefreshPortfolio.addEventListener('click', async () => {
    appendLog('Refreshing portfolio and execution telemetry...', 'info');
    await loadPlatformData();
    appendLog('Portfolio metrics refreshed.', 'success');
  });
}

// Clear Terminal Logs Listener
if (el.btnClearLogs) {
  el.btnClearLogs.addEventListener('click', () => {
    el.terminalLog.innerHTML = '<div class="log-line log-info">[AUDIT] Terminal log cleared by operator.</div>';
  });
}

// Reset Emergency Halt Listener
const btnResetKill = document.getElementById('btn-reset-kill');
if (btnResetKill) {
  btnResetKill.addEventListener('click', async () => {
    if (!confirm('CONFIRM RESET: Restore normal operations and unhalt risk firewall?')) return;
    try {
      const res = await fetch('/api/emergency_kill/reset', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ authorized_by: 'OPERATOR' }),
      });
      const data = await res.json();
      appendLog(data.message, 'success');
      await loadPlatformData();
    } catch (err) {
      appendLog(`Failed to reset emergency kill: ${err.message}`, 'error');
    }
  });
}

// LIVE-CANARY Action Handlers
const btnCanaryVerify = document.getElementById('btn-canary-verify');
const btnToggleVerif = document.getElementById('btn-toggle-verification-details');
const listVerif = document.getElementById('canary-checks-detail-list');

if (btnToggleVerif && listVerif) {
  btnToggleVerif.addEventListener('click', () => {
    const isHidden = listVerif.style.display === 'none';
    listVerif.style.display = isHidden ? 'block' : 'none';
    btnToggleVerif.textContent = isHidden ? 'Hide Forensic Breakdown' : 'Show Forensic Breakdown';
  });
}

if (btnCanaryVerify) {
  btnCanaryVerify.addEventListener('click', async () => {
    appendLog('Starting 14-Step LIVE-CANARY Broker Pre-Flight Audit...', 'info');
    try {
      const res = await fetch('/api/canary/verify', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ symbol: 'BTCUSDT' }) });
      const report = await res.json();
      const txtVerif = document.getElementById('txt-verification-status');
      if (txtVerif) {
        txtVerif.textContent = report.passed ? 'ALL 14 CHECKS PASSED (READY TO ARM)' : `FAILED: ${report.failure_reason}`;
        txtVerif.style.color = report.passed ? 'var(--color-green)' : 'var(--color-red)';
      }

      if (listVerif && report.checks) {
        listVerif.innerHTML = report.checks.map(chk => `
          <div style="display: flex; justify-content: space-between; align-items: center; padding: 4px 0; border-bottom: 1px dotted rgba(255,255,255,0.08); font-size: 11px;">
            <span>Step ${chk.step}: <strong>${chk.name}</strong></span>
            <span style="color: ${chk.passed ? 'var(--color-green)' : 'var(--color-red)'}; font-weight: 600;">
              ${chk.passed ? '✓ PASSED' : '✗ FAILED'}
            </span>
          </div>
          <div style="font-size: 10px; color: var(--text-muted); margin-bottom: 4px; padding-left: 8px;">
            ${chk.message}
          </div>
        `).join('');
        listVerif.style.display = 'block';
        if (btnToggleVerif) btnToggleVerif.textContent = 'Hide Forensic Breakdown';
      }

      appendLog(`14-Step Audit complete: ${report.passed ? 'ALL 14 CHECKS PASSED' : report.failure_reason}`, report.passed ? 'success' : 'error');
    } catch (err) {
      appendLog(`Verification error: ${err.message}`, 'error');
    }
  });
}

const btnCanaryArm = document.getElementById('btn-canary-arm');
if (btnCanaryArm) {
  btnCanaryArm.addEventListener('click', async () => {
    if (!confirm('ATTENTION: Arm LIVE-CANARY operating plane? Requires pre-flight pass and explicit operator authorization.')) return;
    appendLog('Arming LIVE-CANARY...', 'warn');
    try {
      const res = await fetch('/api/canary/arm', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ authorized_by: 'OPERATOR' }) });
      const data = await res.json();
      appendLog(`Arm response: ${data.message}`, data.success ? 'success' : 'error');
      await loadPlatformData();
    } catch (err) {
      appendLog(`Arm error: ${err.message}`, 'error');
    }
  });
}

const btnCanaryActivate = document.getElementById('btn-canary-activate');
if (btnCanaryActivate) {
  btnCanaryActivate.addEventListener('click', async () => {
    if (!confirm('CRITICAL SAFETY CONFIRMATION: You are about to ACTIVATE real-money LIVE-CANARY trading. Proceed?')) return;
    appendLog('Activating LIVE-CANARY trading...', 'warn');
    try {
      const res = await fetch('/api/canary/activate', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ authorized_by: 'OPERATOR' }) });
      const data = await res.json();
      appendLog(`Activate response: ${data.message}`, data.success ? 'warn' : 'error');
      await loadPlatformData();
    } catch (err) {
      appendLog(`Activate error: ${err.message}`, 'error');
    }
  });
}

const btnCanaryDisarm = document.getElementById('btn-canary-disarm');
if (btnCanaryDisarm) {
  btnCanaryDisarm.addEventListener('click', async () => {
    appendLog('Disarming LIVE-CANARY...', 'info');
    try {
      const res = await fetch('/api/canary/disarm', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ reason: 'Operator manual disarm' }) });
      const data = await res.json();
      appendLog(data.message, 'info');
      await loadPlatformData();
    } catch (err) {
      appendLog(`Disarm error: ${err.message}`, 'error');
    }
  });
}

// Modal Dismiss UX (Escape Key & Outside Click)
window.addEventListener('keydown', (e) => {
  if (e.key === 'Escape' && el.brokerModal.classList.contains('open')) {
    el.brokerModal.classList.remove('open');
  }
});
el.brokerModal.addEventListener('click', (e) => {
  if (e.target === el.brokerModal) {
    el.brokerModal.classList.remove('open');
  }
});

// Initialize on Load
window.addEventListener('DOMContentLoaded', () => {
  loadPlatformData();
  initWebSocket();
});
