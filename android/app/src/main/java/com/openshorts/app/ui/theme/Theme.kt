package com.openshorts.app.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

// Lumen Night Foundry — the OpenShorts design system palette.
val Ink = Color(0xFF0E0B14)          // dark violet canvas
val InkSurface = Color(0xFF17121F)   // raised surface
val InkSurface2 = Color(0xFF201928)  // hover / chip
val Hairline = Color(0xFF2A2233)     // hairline borders
val Brass = Color(0xFFD4A24A)        // molten-brass accent
val BrassSoft = Color(0xFFF0D9A8)    // brass tint for text emphasis
val TextPrimary = Color(0xFFEFE9F7)
val TextSecondary = Color(0xFFA79EB3)
val Danger = Color(0xFFE5484D)
val Success = Color(0xFF46A758)

private val LumenNightColors = darkColorScheme(
    primary = Brass,
    onPrimary = Ink,
    primaryContainer = Color(0xFF3A2E1A),
    onPrimaryContainer = BrassSoft,
    secondary = BrassSoft,
    onSecondary = Ink,
    background = Ink,
    onBackground = TextPrimary,
    surface = InkSurface,
    onSurface = TextPrimary,
    surfaceVariant = InkSurface2,
    onSurfaceVariant = TextSecondary,
    outline = Hairline,
    error = Danger,
    onError = Color.White,
    errorContainer = Color(0xFF3A1517),
    onErrorContainer = Color(0xFFFFDAD6),
)

@Composable
fun OpenShortsTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = LumenNightColors,
        typography = MaterialTheme.typography,
        content = content,
    )
}
