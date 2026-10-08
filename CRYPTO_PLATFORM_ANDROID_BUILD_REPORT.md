# Crypto Platform — Android Build & Environment Forensic Report

**Date / Timestamp:** 2026-10-08T20:34:00+05:30  
**Repository:** `C:\Users\nares\Workspace\crypto-platform`  
**Git Branch:** `feature/crypto-platform-android-complete`  
**Final Classification:** `ANDROID_BUILD_VERIFIED` (`PHYSICAL DEVICE ACTION REQUIRED` for on-device execution)  

---

## 1. Executive Summary

The Windows development environment required to build, test, and package the native **Crypto Platform** Android application has been autonomously established without manual intervention. The complete Java 17 toolchain, Android SDK command-line tools, API 34 platforms, build-tools, and project Gradle wrapper were configured. 

The application successfully compiled, passed all unit tests (including `CapitalSafetyTest`), and produced the verified debug APK artifact. The research core remains 100% protected and verified: the frozen contract hash is intact and deterministic replay regression passed with 9,608 / 9,608 identical opportunities.

Because the Windows host machine has hardware virtualization firmware disabled in BIOS (`VirtualizationFirmwareEnabled: False`), hardware-accelerated local Android emulators cannot be spawned on this host. Testing on hardware requires connecting an Android device with USB debugging enabled.

---

## 2. Environment Forensics & Toolchain Discovery

| Component | Status | Location / Details |
| :--- | :--- | :--- |
| **Operating System** | Detected | Windows 11 (NT 10.0.26100.0, 64-bit AMD64) |
| **Available RAM / Disk** | Verified | 16 GB RAM (~7.4 GB free), Drive C: ~1.07 TB free |
| **Hardware Virtualization** | Inspected | `VirtualizationFirmwareEnabled: False` (Disabled in host BIOS) |
| **Java / JDK** | Auto-Installed | Microsoft Build of OpenJDK 17.0.20.1+1 LTS (`C:\Program Files\Microsoft\jdk-17.0.20.101-hotspot`) |
| **Android SDK** | Auto-Installed | `C:\Users\nares\AppData\Local\Android\Sdk` |
| **SDK Command-Line Tools**| Auto-Installed | Google `cmdline-tools` 12.0 (`latest`) |
| **SDK Platforms** | Auto-Installed | `platforms;android-34` (Android 14 API level 34) |
| **SDK Build-Tools** | Auto-Installed | `build-tools;34.0.0` |
| **SDK Platform-Tools** | Auto-Installed | Google `platform-tools` v37.0.1 (`adb.exe`, `fastboot.exe`) |
| **Gradle** | Auto-Configured| Official Gradle 8.5 with project wrapper (`gradlew.bat`) |
| **Kotlin / AGP** | Configured | Kotlin 1.9.22, Compose Compiler 1.5.8, AGP 8.2.2 |

---

## 3. Build & Artifact Verification

| Step | Command | Result |
| :--- | :--- | :--- |
| **Clean** | `.\gradlew.bat clean` | **BUILD SUCCESSFUL** |
| **Unit Tests** | `.\gradlew.bat test` | **BUILD SUCCESSFUL** (46 tasks executed, 100% pass) |
| **Assemble Debug** | `.\gradlew.bat assembleDebug` | **BUILD SUCCESSFUL** |

### Output APK Details
- **Exact Path:** `C:\Users\nares\Workspace\crypto-platform\mobile\android\app\build\outputs\apk\debug\app-debug.apk`
- **File Size:** `17,410,860` bytes (~17.4 MB)
- **Package Name:** `io.cryptoplatform.app` (Application ID: `io.cryptoplatform.app.debug`)
- **Min SDK:** 26 (Android 8.0 Oreo)
- **Compile / Target SDK:** 34 (Android 14)
- **Signing:** Android Debug Keystore verified

---

## 4. Android Static Safety Audit

A recursive AST and pattern scan of all files in `mobile/android` verified zero compliance violations:

- **API Keys & Secrets:** Zero exchange credentials or private keys in source code.
- **Real Capital Authorization:** Strictly locked to `$0.00` via `CapitalSafetyGate.REAL_CAPITAL_AUTHORIZED_USD`.
- **Live Order Routing:** Permanently locked fail-closed (`IS_LIVE_TRADING_LOCKED = true`).
- **Target Invariant:** Target floor enforced $\ge 4.0\text{R}$ (`MINIMUM_TARGET_FLOOR_R = 4.0`).
- **Risk Invariant:** Trade risk enforced $\le 1.0\%$ (`MAX_TRADE_RISK_PERCENT = 1.0`).
- **Portfolio Heat Invariant:** Portfolio heat enforced $\le 3.0\%$ (`MAX_PORTFOLIO_HEAT_PERCENT = 3.0`).

---

## 5. Device Detection & Hardware Constraints

```
> adb devices -l
List of devices attached: <empty>

> Get-CimInstance Win32_Processor | Select-Object VirtualizationFirmwareEnabled
VirtualizationFirmwareEnabled: False
```

- **Physical Android Device:** None currently attached via USB debugging.
- **Virtualization Support:** Host BIOS has hardware virtualization (Intel VT-x / AMD-V) disabled.
- **Status:** **`PHYSICAL DEVICE ACTION REQUIRED`**
  *(To validate on hardware, attach an Android device with USB debugging enabled, or enable virtualization in Windows BIOS to launch an AVD).*

---

## 6. Backend Connectivity Specification

- **Host LAN Address:** `192.168.31.149` (Wireless LAN)
- **Default Endpoint:** `http://10.0.2.2:8080` (Emulator loopback) or `http://192.168.31.149:8000/api` (LAN)
- **USB Reverse Tethering (Recommended):**
  ```powershell
  adb reverse tcp:8000 tcp:8000
  ```
  Allows the physical phone to reach `http://localhost:8000/api` directly over USB without firewall adjustments.
- **Network Security Config:** `res/xml/network_security_config.xml` permits cleartext traffic strictly for local development endpoints (`10.0.2.2`, `127.0.0.1`, `localhost`, `192.168.31.149`) while enforcing TLS globally for all external production networks.

---

## 7. Full Repository Regression & Quantitative Invariants

All quantitative research logic and contracts were executed and verified against the frozen baselines:

| Test / Audit Command | Result | Details |
| :--- | :--- | :--- |
| `pytest -q` | **PASS** | 246 passed, 0 failed in 31.17s |
| `python cli.py verify-contract` | **PASS** | Contract hash: `8fbc923a104e7688c3a9f0e4b8592c30dfb0b9a67a84511d5e49f8721c432098` |
| `python cli.py validate-preflight` | **PASS** | 5 safety gates verified; real capital = $0.00 |
| `python cli.py health` | **PASS** | 11 canonical strategy families & observations verified |
| `python cli.py reconcile` | **PASS** | 0 discrepancies, system fully reconciled |
| `python -m research.experiments.run_phase_r_replay_regression` | **PASS** | **9,608 / 9,608** candidate replay identical |

---

## 8. Summary Table of Quantitative Invariants

| Invariant | Requirement | Status |
| :--- | :--- | :--- |
| **Research Contract Hash** | `8fbc923a104e7688c3a9f0e4b8592c30dfb0b9a67a84511d5e49f8721c432098` | **VERIFIED** |
| **Deterministic Replay** | 9,608 / 9,608 opportunities identical | **VERIFIED** |
| **Real Capital Authorized** | `$0.00` | **VERIFIED** |
| **Live Order Submission** | Hard-disabled / Fail-closed | **VERIFIED** |
| **Minimum Target Floor** | $\ge 4.0\text{R}$ | **VERIFIED** |
| **Max Trade Risk** | $\le 1.0\%$ | **VERIFIED** |
| **Max Portfolio Heat** | $\le 3.0\%$ | **VERIFIED** |
