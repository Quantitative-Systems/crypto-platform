# Crypto Trading Platform — Exchange Support & Capability Matrix

**Version:** 1.0.0  
**Verification Date:** 2026-09-23  
**Audit Scope:** Public market data feeds, private execution endpoints, sandbox environments, and non-custodial permission enforcements.

---

## 1. Verified Capability Matrix

| Exchange / Venue | Market Data (REST) | Market Data (WebSocket) | Account Data | Order Submission | Order Cancellation | Position Data | Auto Reconnect | Rate Limiting | Paper Support | Live Support | Status |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **Binance (Futures)** | `VERIFIED` | `VERIFIED` | `VERIFIED` (Mock/REST) | `VERIFIED` (Paper/REST) | `VERIFIED` (Paper/REST) | `VERIFIED` (Paper/REST) | `VERIFIED` | `VERIFIED` (1200 req/min) | `SUPPORTED` | `READY_FOR_AUTH` | `SUPPORTED` |
| **Binance (Spot)** | `VERIFIED` | `VERIFIED` | `VERIFIED` (Mock/REST) | `VERIFIED` (Paper/REST) | `VERIFIED` (Paper/REST) | `VERIFIED` (Paper/REST) | `VERIFIED` | `VERIFIED` (1200 req/min) | `SUPPORTED` | `READY_FOR_AUTH` | `SUPPORTED` |
| **Bybit (Linear/Perp)** | `VERIFIED` | `VERIFIED` | `VERIFIED` (UTA Mock) | `VERIFIED` (Paper/REST) | `VERIFIED` (Paper/REST) | `VERIFIED` (Paper/REST) | `VERIFIED` | `VERIFIED` (600 req/min) | `SUPPORTED` | `READY_FOR_AUTH` | `SUPPORTED` |
| **CCXT Generic (Kraken, Coinbase, OKX)** | `VERIFIED` (REST) | `PARTIAL` | `VERIFIED` (Mock) | `VERIFIED` (Paper) | `VERIFIED` (Paper) | `VERIFIED` (Paper) | `N/A` | `VERIFIED` | `SUPPORTED` | `PLANNED` | `EXPERIMENTAL` |

---

## 2. Non-Custodial Security & Permission Gates

To guarantee that customer funds can never be exfiltrated:

1. **Permission Audit on Connect:**
   Whenever an API key is connected or refreshed, the exchange adapter immediately calls the permission inspection endpoint (`/sapi/v1/account/apiRestrictions` on Binance or `/v5/user/query-api` on Bybit).
   * **Required Permissions:** `read`, `trade` (Spot/Margin/Futures).
   * **Forbidden Permissions:** `withdraw` (Enable Withdrawals), `transfer` (Internal/Universal Transfer).
   * **Security Rule:** If `withdraw == True` or any transfer permission is detected, the adapter **immediately aborts connection**, raises `PermissionSecurityError`, and locks the account.

2. **Zero Storage of Raw Plaintext Secrets:**
   All API keys and secrets are envelope-encrypted using `AES-256-GCM` with tenant-isolated salt and PBKDF2 HMAC-SHA256 key derivation.
   Secrets are decrypted strictly in memory at the point of request signing and zeroed out immediately after.

3. **HMAC-SHA256 Request Signing:**
   All private REST requests are signed with strict millisecond timestamps and a mandatory 5000ms `recvWindow` to prevent replay attacks.

---

## 3. Real-Time Market Data Stream Verification

Public market data feeds are verified continuously with automated health checks:
* **Heartbeat & Liveness:** Ping/pong checks every 20 seconds. If no message or pong is received within 25 seconds, the socket disconnects and triggers immediate reconnection.
* **Exponential Backoff Reconnection:** Initial retry starts at 1.0s with randomized jitter (0.1s–0.5s), doubling up to a 30.0s ceiling.
* **Timestamp Monotonicity:** Any incoming tick or bar with a timestamp earlier than the latest received timestamp is flagged as an out-of-order sequence inversion and rejected.
* **Stale Data Alarm:** If no tick is received for a subscribed active symbol within 5000ms, the Risk Firewall rejects new orders for that instrument (`STALE_MARKET_DATA`).
