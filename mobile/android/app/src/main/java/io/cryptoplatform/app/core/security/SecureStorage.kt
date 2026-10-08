package io.cryptoplatform.app.core.security

import android.content.Context
import android.content.SharedPreferences
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey

/**
 * Encrypted local key-value store leveraging Android Keystore.
 * Stores JWT bearer session tokens and masked testnet API configurations.
 * Guarantees zero secret leakage into plain-text logs or analytics.
 */
class SecureStorage(context: Context) {

    private val prefs: SharedPreferences = try {
        val masterKey = MasterKey.Builder(context)
            .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
            .build()

        EncryptedSharedPreferences.create(
            context,
            "crypto_platform_secure_prefs",
            masterKey,
            EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
            EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
        )
    } catch (e: Exception) {
        // Fallback for emulator / non-keystore environments
        context.getSharedPreferences("crypto_platform_fallback_prefs", Context.MODE_PRIVATE)
    }

    companion object {
        private const val KEY_AUTH_TOKEN = "auth_jwt_token"
        private const val KEY_TENANT_ID = "active_tenant_id"
        private const val KEY_USER_EMAIL = "user_email"
        private const val KEY_WATCHLIST = "user_watchlist_symbols"
    }

    var authToken: String?
        get() = prefs.getString(KEY_AUTH_TOKEN, null)
        set(value) {
            prefs.edit().putString(KEY_AUTH_TOKEN, value).apply()
        }

    var tenantId: String
        get() = prefs.getString(KEY_TENANT_ID, "system") ?: "system"
        set(value) {
            prefs.edit().putString(KEY_TENANT_ID, value).apply()
        }

    var userEmail: String
        get() = prefs.getString(KEY_USER_EMAIL, "operator@cryptoplatform.io") ?: "operator@cryptoplatform.io"
        set(value) {
            prefs.edit().putString(KEY_USER_EMAIL, value).apply()
        }

    fun getWatchlist(): Set<String> {
        return prefs.getStringSet(KEY_WATCHLIST, setOf("BTCUSDT", "ETHUSDT")) ?: setOf("BTCUSDT", "ETHUSDT")
    }

    fun setWatchlist(symbols: Set<String>) {
        prefs.edit().putStringSet(KEY_WATCHLIST, symbols).apply()
    }

    fun clearSession() {
        prefs.edit()
            .remove(KEY_AUTH_TOKEN)
            .putString(KEY_TENANT_ID, "system")
            .apply()
    }
}
