# STRATA — Multi-Tenant Account & Broker Architecture

## 1. Overview
STRATA provides an institutional multi-tenant account and broker management architecture capable of managing unlimited user accounts across supported cryptocurrency exchanges.

---

## 2. Multi-Tenancy Isolation (`core/tenancy/`)

### 2.1 Context Isolation
Every incoming request must bind an authenticated tenant context:
```python
from core.tenancy.tenant_context import TenantContext

with TenantContext(tenant_id="usr_prod_001"):
    # All store access within this block is strictly scoped to usr_prod_001
    user_accounts = account_store.list()
```

### 2.2 Invariant Enforcement
- `TenantScopedStore` enforces that keys, database records, and cache items are prefixed by the active `tenant_id`.
- Any attempt to query, update, or delete records belonging to another tenant immediately raises `TenantViolationError` and emits a `CRITICAL` security audit alert.

---

## 3. Account Management (`accounts/account_manager.py`)

### 3.1 Account Attributes
Each registered trading account maintains:
- `account_id`: Globally unique identifier.
- `tenant_id`: Owner identifier.
- `broker_type`: Exchange connector (`BINANCE`, `BYBIT`, `METATRADER_5`).
- `environment`: Execution tier (`PAPER`, `DEMO`, `MICRO_LIVE`, `LIVE`).
- `balance` & `equity`: Real-time margin and capital tracking.
- `risk_profile`: User-selected risk limits (strictly capped at $\le 1.00\%$).
- `connection_status`: Heartbeat health of exchange API keys/sessions.

---

## 4. Broker Center (`broker/broker_center.py`)

### 4.1 Normalized Broker Adapter Interface
All broker integrations implement `BaseBrokerAdapter`:
- `AccountAdapter`: Queries balances, margins, and currency positions.
- `MarketDataAdapter`: Subscribes to level-1/level-2 order books and closed ticker candles.
- `ExecutionAdapter`: Places limit/market orders, manages stop losses, and handles cancellation.
- `ReconciliationAdapter`: Queries live exchange order/position states to verify synchronization with local ledger state.

### 4.2 Supported Integrations
| Exchange / Broker | Protocol | Key Features | Default Environment |
|:---|:---|:---|:---|
| **Binance** | REST + WebSocket | USDT-M Perpetual Futures, Spot | DEMO (Testnet) / PAPER |
| **Bybit** | REST + WebSocket | USDT Perpetuals, Inverse Futures | DEMO (Testnet) / PAPER |
| **MetaTrader 5 (MT5)** | IPC / REST Gateway | Multi-asset crypto CFD routing | DEMO / PAPER |

---

## 5. Account Suitability Engine (`accounts/suitability_engine.py`)
Before the Autonomous Agent allocates any strategy to an account, the `AccountSuitabilityEngine` evaluates:
1. **Capital Adequacy**: Verifies account equity meets minimum margin for 1R position sizing.
2. **Trading Style Alignment**: Validates strategy frequency matches account tier (e.g., high-frequency scalping requires low fee tiers).
3. **Venue Liquidity & Spread**: Ensures symbol tick/lot constraints align with strategy requirements.
4. **Hard Risk Ceiling**: Automatically overrides any user attempt to set trade risk $> 1.00\%$ down to $1.00\%$.
