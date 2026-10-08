# Proguard rules for Crypto Platform Android Application

-keepattributes *Annotation*
-dontwarn okhttp3.**
-dontwarn okio.**
-keep class io.cryptoplatform.app.domain.model.** { *; }
