package io.cryptoplatform.app

import android.app.Application
import android.util.Log
import io.cryptoplatform.app.core.security.CapitalSafetyGate
import io.cryptoplatform.app.core.security.SecureStorage

/**
 * Root Android Application for Crypto Platform.
 * Enforces hardware and software safety invariants at launch.
 */
class CryptoPlatformApp : Application() {

    companion object {
        lateinit var instance: CryptoPlatformApp
            private set
    }

    lateinit var secureStorage: SecureStorage
        private set

    override fun onCreate() {
        super.onCreate()
        instance = this
        
        // Initialize encrypted security storage
        secureStorage = SecureStorage(this)

        // Enforce fail-closed capital invariants at application launch
        CapitalSafetyGate.verifyLaunchInvariants()
        Log.i("CryptoPlatformApp", "Application initialized with REAL_CAPITAL = $0.00 (LOCKED)")
    }
}
