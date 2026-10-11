# Crypto Platform — Android Release Runbook

## 1. Overview & Build Types

The **Crypto Platform Android Application** is written in Kotlin with Jetpack Compose and Material 3 design tokens. It provides an intuitive, high-performance mobile interface for quantitative market analysis, fractal visualization, paper execution, and risk telemetry.

### Build Type Matrix

| Build Type | Application ID | Default API Endpoint | Logging | Package Suffix |
| :--- | :--- | :--- | :--- | :--- |
| **`debug`** | `io.cryptoplatform.app` | `http://10.0.2.2:8080` (Local Host) | Enabled | None |
| **`staging`** | `io.cryptoplatform.app.staging` | `https://crypto-platform-staging.onrender.com` | Enabled | `.staging` |
| **`release`** | `io.cryptoplatform.app` | `https://api.cryptoplatform.io` | Minified / ProGuard | None |

---

## 2. Dynamic Endpoint Configuration

The Android application dynamically resolves its backend API endpoint without needing recompilation:
1. **Compile-Time Default:** Configured in `app/build.gradle` via `buildConfigField "String", "BASE_URL", ...`.
2. **Runtime Custom Endpoint:** In the **Account / Settings** screen, users can specify an alternate backend endpoint (e.g., self-hosted staging or LAN IP).
   - Validated for valid HTTPS/HTTP protocol format.
   - Encrypted at rest in hardware-backed Android Keystore via `EncryptedSharedPreferences` (`SecureStorage.kt`).
   - Reverts immediately to `BuildConfig.BASE_URL` if cleared.

---

## 3. APK Artifact Retrieval from GitHub Actions

Developers do NOT need Android Studio or a local Android SDK installed on their machines.

1. Navigate to the GitHub repository: **Actions** tab.
2. Select the latest run of **Crypto Platform CI** or **Dedicated Android Release & Staging Build**.
3. Under the **Artifacts** section at the bottom of the page:
   - Download `crypto-platform-staging-apk` (`app-staging.apk`)
   - Download `crypto-platform-debug-apk` (`app-debug.apk`)
4. Unzip the artifact to obtain the installable `.apk` file.

---

## 4. Installation on Physical Android Devices

### Method A: Direct Sideloading (Over-the-Air)
1. Send the downloaded `app-staging.apk` to your Android device via Google Drive, Telegram, email, or direct USB transfer.
2. Open the file on the Android device and select **Install**.
3. If prompted, toggle **Allow from this source** (standard for sideloaded testnet APKs).

### Method B: ADB Command Line
```bash
# Connect device via USB with USB Debugging enabled
adb devices

# Install staging APK with reinstall flag
adb install -r app-staging.apk
```

---

## 5. Physical Device Testing Boundary

Per Phase 15 of the deployment specification:
- CI/CD build, compile, unit tests, and APK artifact generation operate **100% autonomously in the cloud**.
- When no physical Android phone is connected to the build machine or runner, the physical hardware verification is classified as:
  `PHYSICAL_DEVICE_TEST_PENDING`
- This boundary does **NOT** block the cloud backend or CI pipeline.

### Manual Physical Checklist (When Device is Connected):
- [ ] APK installs successfully without package signature conflicts.
- [ ] App launches into Splash screen and transitions cleanly to Home.
- [ ] Connects to `https://crypto-platform-staging.onrender.com/health` over cellular/Wi-Fi.
- [ ] 7-timeframe ladder renders smoothly with hardware acceleration.
- [ ] Live candle prices update on Markets screen.
- [ ] Emergency Halt button is responsive.
- [ ] Live real-money trading is verified permanently locked ($0.00 capital).

---

## 6. Release Signing Configuration (Production Boundary)

For security, production release keystores are **NEVER committed to git**.

To produce signed production release builds in CI:
1. Generate keystore locally:
   ```bash
   keytool -genkey -v -keystore crypto-platform-release.keystore -alias cryptoplatform -keyalg RSA -keysize 2048 -validity 10000
   ```
2. Convert keystore to base64:
   ```bash
   base64 -w 0 crypto-platform-release.keystore > keystore.base64
   ```
3. Add GitHub Secrets:
   - `KEYSTORE_BASE64`: contents of `keystore.base64`
   - `KEYSTORE_PASSWORD`: keystore password
   - `KEY_ALIAS`: `cryptoplatform`
   - `KEY_PASSWORD`: alias password
4. When secrets are provided, CI generates signed releases; otherwise it produces `app-release-unsigned.apk`.
