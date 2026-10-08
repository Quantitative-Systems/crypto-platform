package io.cryptoplatform.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import io.cryptoplatform.app.ui.navigation.CryptoPlatformAppRoot
import io.cryptoplatform.app.ui.theme.CryptoPlatformTheme

/**
 * Main Activity for Crypto Platform Native Android Application.
 * Boots Jetpack Compose unidirectional reactive navigation and state architecture.
 */
class MainActivity : ComponentActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            CryptoPlatformTheme {
                CryptoPlatformAppRoot()
            }
        }
    }
}
