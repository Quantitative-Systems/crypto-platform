# Authentication Durability and Session Security

## 1. Overview

The Crypto Platform authentication subsystem (`core.auth.auth_service.AuthService`) provides durable, restart-safe identity and session management backed by SQLite WAL persistence with repository isolation ready for PostgreSQL migration.

---

## 2. Security Invariants & Guarantees

### Zero Plaintext Secrets
1. **Passwords**:
   - Stored in the `users` table as `password_hash` with unique per-user cryptographically random salts (`secrets.token_hex(16)`).
   - Hashed using PBKDF2-HMAC-SHA256 with 100,000 iterations (`hashlib.pbkdf2_hmac("sha256", password, salt, 100000)`).
   - Passwords in plaintext are never written to disk, databases, checkpoints, or log files.
2. **Session Tokens**:
   - Issued to authenticated clients as high-entropy 256-bit hexadecimal bearer tokens (`secrets.token_hex(32)`).
   - Persisted in the `sessions` table strictly in SHA-256 hashed form (`token_hash = sha256(raw_token)`).
   - Even in the event of a database compromise or backup leak, raw session tokens cannot be recovered or used to impersonate users.
3. **Exchange Credentials**:
   - Exchange credentials are not persisted in plaintext. Live trading is hard-disabled fail-closed (`HARD_DISABLED_FAIL_CLOSED`), and authorized real capital remains `$0.00`.

---

## 3. Lifecycle & Behaviors

### Registration (`register_user`)
- Enforces email formatting and normalization (`strip().lower()`).
- Enforces minimum 8-character password policy.
- Validates password confirmation matching when provided.
- Duplicate email checks prevent collisions; existing emails raise `ValueError("An account with email '{email}' already exists.")`.
- Automatically provisions dedicated multi-tenant isolation IDs (`tenant_id = f"tnt_{user_id}"`).

### Login & Authentication (`authenticate`)
- Retrieves user record by normalized email.
- Verifies password hash using constant-time comparison (`hmac.compare_digest`).
- Upon success, generates a raw token, hashes it with SHA-256, and inserts a session record:
  ```sql
  INSERT INTO sessions (session_id, user_id, token_hash, created_at_ts, expires_at_ts, revoked)
  VALUES (?, ?, ?, ?, ?, 0);
  ```
- Returns `SessionToken` with client token and safe `User` record.

### Session Validation (`validate_session`)
- Hashes incoming bearer token and queries the `sessions` table.
- Enforces:
  1. Token hash existence.
  2. Non-revocation (`revoked == 0`).
  3. Expiration threshold (`time.time() <= expires_at_ts`).
  4. Active user status (`is_active == 1`).
- If expired, marks `revoked = 1` transactionally and rejects authentication.

### Logout & Revocation (`logout` / `revoke_session`)
- Atomically marks `revoked = 1` for the specified token hash.
- Repeated logout calls return `False` safely without side effects.
- Once revoked, the session is rejected immediately across all concurrent workers.

---

## 4. Multi-Tenant Tenancy Isolation

- Every user belongs to a tenant boundary (`tenant_id`).
- Watchlists and user preferences are scoped per user and tenant (`user_watchlists`, `user_preferences`).
- Cascade deletions ensure that tenant deletions wipe corresponding user assets without orphans.
