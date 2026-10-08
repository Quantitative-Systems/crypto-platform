# STRATA Android Mobile Architecture & Safety Guide

## Overview
The **STRATA Mobile Client** provides a hardened, cross-platform Android mobile interface targeting high-priority operational workflows:
- Portfolio equity & available capital monitoring
- Open positions & active risk blotter
- Protected **KING Engine** state & opportunities
- Broker connection health & heartbeat
- System alerts (CRITICAL / EMERGENCY)
- Multi-factor authenticated emergency intervention (PAUSE / EMERGENCY STOP)

Advanced quantitative research, fractal state modeling, and backtesting remain web-first workflows.

---

## Architecture Principles

### 1. Cross-Platform Native Webview / Capacitor Pattern
- The mobile application is packaged using modern Android tooling (`AndroidManifest.xml`, Gradle) loading hardened, responsive web assets (`assets/www/index.html`).
- Zero duplicate backend trading logic: mobile clients consume the identical authenticated REST/WebSocket endpoints (`/api/auth/*`, `/api/king/*`, `/api/positions`, `/api/agent/*`).

### 2. Zero Secret Persistence Invariant (Rule 32)
- **NEVER** store broker API secrets or private keys in Android local storage, SQLite, or SharedPreferences.
- All broker API credentials reside securely on the backend in tenant-scoped, encrypted credential vaults.
- Mobile authentication relies exclusively on ephemeral bearer session tokens issued via `/api/auth/login`.
- Session tokens are stored in Android `EncryptedSharedPreferences` / KeyStore backed secure storage.

### 3. Fail-Closed Emergency Control Protocol
- The mobile Emergency Stop control triggers `/api/agent/emergency-stop`.
- Emergency actions require explicit two-step user confirmation dialogs to prevent accidental touch trigger.
- Capital allocation remains strictly $0.00 until explicit, multi-factor authenticated live capital activation.

---

## Directory Structure
```
mobile/
├── android/
│   ├── AndroidManifest.xml       # Permissions (INTERNET, ACCESS_NETWORK_STATE) & Secure App Manifest
│   ├── app/
│   │   └── build.gradle          # Android Gradle packaging & dependency specification
│   └── assets/
│       └── www/
│           └── index.html        # Responsive touch-optimized STRATA Mobile Terminal UI
└── README.md                     # Architecture & security specifications
```
