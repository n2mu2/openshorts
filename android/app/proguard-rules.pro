# OpenShorts Android — ProGuard rules (release build).
# Retrofit / Gson models are kept by default in debug; for release:
-keepattributes Signature, InnerClasses, EnclosingMethod, *Annotation*
-keep class com.openshorts.app.core.model.** { *; }
-keep interface com.openshorts.app.core.network.OpenShortsApi { *; }
-dontwarn okhttp3.**
-dontwarn okio.**
-dontwarn javax.annotation.**
-dontwarn org.conscrypt.**
-dontwarn org.bouncycastle.**
-dontwarn org.openjsse.**
