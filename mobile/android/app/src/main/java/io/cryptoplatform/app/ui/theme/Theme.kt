package io.cryptoplatform.app.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

val BgPage = Color(0xFFF8FAFC)
val BgSurface = Color(0xFFFFFFFF)
val BgSubtle = Color(0xFFF1F5F9)
val TextPrimary = Color(0xFF0F172A)
val TextSecondary = Color(0xFF334155)
val TextMuted = Color(0xFF64748B)

val BrandBlue = Color(0xFF2563EB)
val BrandSky = Color(0xFF0284C7)
val PositiveEmerald = Color(0xFF059669)
val AlertRed = Color(0xFFDC2626)
val WarningAmber = Color(0xFFD97706)
val BorderLight = Color(0xFFE2E8F0)

private val LightColorScheme = lightColorScheme(
    primary = BrandBlue,
    onPrimary = Color.White,
    secondary = BrandSky,
    onSecondary = Color.White,
    tertiary = PositiveEmerald,
    background = BgPage,
    onBackground = TextPrimary,
    surface = BgSurface,
    onSurface = TextPrimary,
    surfaceVariant = BgSubtle,
    onSurfaceVariant = TextSecondary,
    outline = BorderLight,
    error = AlertRed,
    onError = Color.White
)

@Composable
fun CryptoPlatformTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = LightColorScheme,
        content = content
    )
}
