# STRATA — Mobile Architecture & Safety Specification

## 1. Overview
The STRATA Mobile client provides a touch-first interface for real-time monitoring and emergency intervention on Android devices.
- **Packaging**: Android Native WebView / Capacitor shell (`mobile/android/`).
- **Core Role**: Operational oversight (equity, risk heat, KING status, open positions, broker status, emergency halt). Research, backtesting, and code authoring remain web-first workflows.

---

## 2. Security & Zero-Secret Storage Invariant
- **Strict Prohibition**: Android local storage, SQLite, or SharedPreferences must **never** store exchange API keys, private keys, or broker secrets.
- **Session Authentication**: Mobile communication uses ephemeral JWT / bearer tokens issued via the authenticated `/api/auth/login` endpoint.
- **Network Security**:
  - `usesCleartextTraffic="false"` explicitly enforced in `AndroidManifest.xml`.
  - All communications route through TLS 1.3 / HTTPS.

---

## 3. Architecture Topology

```text
               ┌──────────────────────────────────────┐
               │         STRATA ANDROID CLIENT        │
               │   (AndroidManifest.xml + WebView)    │
               └──────────────────┬───────────────────┘
                                  │ HTTPS (Bearer Token)
                                  ▼
               ┌──────────────────────────────────────┐
               │         STRATA PLATFORM API          │
               │            (web/server.py)           │
               └──────────────────┬───────────────────┘
                                  │
         ┌────────────────────────┼────────────────────────┐
         ▼                        ▼                        ▼
  /api/health              /api/king/overview       /api/agent/pause
(Heartbeat & Env)       (Protected Market State)     (Emergency Stop)
```

---

## 4. Operational Controls & Emergency Protocols
- **Emergency Stop Button**: Top navigation bar includes a persistent `HALT` button.
- **Two-Step Confirmation**: Touching the halt button prompts a confirmation modal to avoid accidental touches.
- **Fail-Safe Response**: Dispatching `/api/agent/pause` immediately stops trade generation, halts order routing, and freezes current open positions under protective stop losses.
