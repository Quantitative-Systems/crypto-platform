package io.cryptoplatform.app;

import android.content.Context;
import android.os.VibrationEffect;
import android.os.Vibrator;
import android.webkit.JavascriptInterface;
import android.widget.Toast;

/**
 * Android JavaScript Interface bridge for Crypto Platform.
 * Exposes device-level security assertions, haptic feedback, and emergency stops.
 */
public class WebAppInterface {
    private final Context context;

    public WebAppInterface(Context context) {
        this.context = context;
    }

    @JavascriptInterface
    public void emergencyHalt() {
        triggerHapticFeedback();
        Toast.makeText(context, "EMERGENCY STOP TRIGGERED: Fail-closed mode active.", Toast.LENGTH_LONG).show();
    }

    @JavascriptInterface
    public void triggerHapticFeedback() {
        try {
            Vibrator v = (Vibrator) context.getSystemService(Context.VIBRATOR_SERVICE);
            if (v != null && v.hasVibrator()) {
                v.vibrate(VibrationEffect.createOneShot(100, VibrationEffect.DEFAULT_AMPLITUDE));
            }
        } catch (Exception ignored) {
        }
    }

    @JavascriptInterface
    public String getAppEnvironment() {
        return "{\"platform\":\"Android\",\"version\":\"1.0.0\",\"real_capital_authorized\":0.00,\"live_trading_status\":\"LOCKED\"}";
    }

    @JavascriptInterface
    public boolean isLiveTradingLocked() {
        return true;
    }

    @JavascriptInterface
    public void showToast(String message) {
        Toast.makeText(context, message, Toast.LENGTH_SHORT).show();
    }
}
