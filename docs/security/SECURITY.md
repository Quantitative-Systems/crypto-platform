# Crypto Trading Platform — Security, Non-Custodial Safeguards & Compliance

**Document Version:** 1.0.0  
**Classification:** Institutional Non-Custodial SaaS Security Standard  

---

## 1. Non-Custodial Architecture Principles

The platform is strictly engineered so that **customer capital remains in the customer's own broker/exchange account at all times**:

1. **Zero Fund Custody:** The platform does not hold, pool, stake, or custody customer fiat or cryptocurrency balances.
2. **Forbidden Permissions:** All exchange adapters reject API keys that possess `withdraw` or `transfer` capabilities.
3. **Automated Permission Auditing:** When an account is registered or reconnected, the platform calls exchange permission endpoints (e.g. `/sapi/v1/account/apiRestrictions` on Binance or `/v5/user/query-api` on Bybit).
   * If `withdraw == True` or `transfer == True`, the connection is immediately aborted, the keys are wiped, and a `NonCustodialSecurityError` is raised.

---

## 2. Cryptographic Secret Management & Envelope Encryption

To ensure secrets cannot be leaked via database exfiltration, log dumps, or core dumps:

```
[ Master Password / KMS Key ]
             │
             ▼ PBKDF2 HMAC-SHA256 (390,000 rounds + Tenant Salt)
[ Derived Key Encryption Key (KEK) ]
             │
             ▼ AES-256-GCM Envelope Encryption
[ Encrypted API Secret + 96-bit IV + 128-bit Auth Tag ]
```

* **Cipher:** `AES-256-GCM` (Galois/Counter Mode) authenticated encryption.
* **Tamper Proofing:** Any bit alteration in the ciphertext or tag causes instant decryption failure (`ValueError: Decryption failed or ciphertext corrupted`).
* **Zero Plaintext Logging:** API secrets are masked (`*****`) in all logs, audit trails, and exception traces.
* **Tenant Isolation:** Every tenant uses a cryptographically distinct salt to prevent cross-tenant key derivation.

---

## 3. Market Integrity & Wash Trading Safeguards

The platform includes active safeguards against manipulative market behavior:

* **Self-Crossing Order Prevention:** The `ComplianceEngine` scans working orders for the same tenant. If a new sell limit order is submitted at or below a working buy order (or vice-versa), the intent is rejected for wash-trading risk.
* **Rate-Limit Throttling:** Strict token-bucket rate limits and runaway order loop detectors protect against quote-stuffing or unintentional DoS of exchange matching engines.

---

## 4. Emergency Kill Switches

Hierarchical, instant trading shutdowns are accessible via API, CLI, and automated monitoring agents:

| Scope | Trigger Target | Operational Effect |
|---|---|---|
| **GLOBAL** | Platform-wide (`*`) | Halts all order generation and routing across all accounts |
| **TENANT** | Tenant ID (`t_...`) | Halts trading for a specific customer organization |
| **ACCOUNT** | Account ID (`acct_...`) | Halts trading on a specific connected exchange account |
| **VENUE** | Venue Name (`BINANCE`) | Halts all orders targeted at an exchange experiencing outages |
| **STRATEGY** | Strategy ID (`strat_...`) | Freezes order generation for a specific strategy algorithm |
| **INSTRUMENT** | Symbol (`BTCUSDT`) | Freezes trading on a specific de-pegged or halted coin |
