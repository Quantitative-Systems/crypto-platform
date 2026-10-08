# Crypto Platform — Android Manual Device Acceptance Test Checklist

This checklist contains **ONLY** the tests that genuinely require physical human interaction on an Android device. All other toolchain, build, static safety, unit tests, and repository regressions are verified autonomously.

---

## Prerequisites (When Connecting Physical Hardware)

1. **Connect Device:**
   Connect an Android device (API 26+) via USB cable.
2. **Enable USB Debugging:**
   In Developer Options on device, toggle **USB debugging** to **ON**.
3. **Accept Host Key Prompt:**
   When the RSA fingerprint dialog appears on the device screen, tap **Allow**.
4. **Verify Connectivity:**
   ```powershell
   adb devices
   ```
   Device must show as `device` (not `unauthorized` or `offline`).

---

## Automated Install & Port Reverse Command

Once connected, execute:
```powershell
# Set up reverse port mapping for backend connectivity
adb reverse tcp:8000 tcp:8000

# Install the built APK
adb install -r C:\Users\nares\Workspace\crypto-platform\mobile\android\app\build\outputs\apk\debug\app-debug.apk

# Launch Crypto Platform
adb shell am start -n io.cryptoplatform.app.debug/io.cryptoplatform.app.MainActivity
```

---

## Manual Acceptance Checklist

| Test ID | Procedure | Expected Physical Behavior | Verdict |
| :--- | :--- | :--- | :--- |
| **MA-01** | **Cold App Launch** | Launch app from device launcher. Verify splash transition to Home screen with dark institutional theme. | [ ] PASS |
| **MA-02** | **Touch Responsive Navigation** | Tap bottom navigation items: **Markets**, **Strategies**, **Backtest**, **Trading**, **Account**. Verify smooth 60fps Compose navigation. | [ ] PASS |
| **MA-03** | **Emergency Stop Control** | On Trading or Account screen, locate the red **Emergency Stop** button and tap it. Verify confirmation dialog appears and prevents accidental triggering. | [ ] PASS |
| **MA-04** | **Capital Safety Gate Display** | Navigate to Account & Risk tabs. Verify **Real Capital Authorized** displays strictly `$0.00` and **Live Trading Status** displays `LOCKED / DISABLED`. | [ ] PASS |
| **MA-05** | **Orientation & Resize** | Rotate device to landscape and back to portrait. Verify layout re-adapts cleanly without state loss or crashing. | [ ] PASS |
| **MA-06** | **Haptic Feedback** | Tap action buttons (e.g., Quick Order intent or Run Backtest). Verify tactile haptic vibration triggers via Android vibrator. | [ ] PASS |
