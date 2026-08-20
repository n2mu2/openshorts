package com.openshorts.app.ui.social

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.openshorts.app.ui.components.ChipTone
import com.openshorts.app.ui.components.ErrorBanner
import com.openshorts.app.ui.components.HairlineDivider
import com.openshorts.app.ui.components.LoadingRow
import com.openshorts.app.ui.components.Notice
import com.openshorts.app.ui.components.ScreenTitle
import com.openshorts.app.ui.components.SectionCard
import com.openshorts.app.ui.components.StatusChip
import com.openshorts.app.ui.theme.TextSecondary

@Composable
fun SocialScreen(vm: SocialViewModel = viewModel()) {
    val state by vm.state.collectAsStateWithLifecycle()

    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(horizontal = 16.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        Spacer(Modifier.height(8.dp))
        Row(verticalAlignment = Alignment.CenterVertically) {
            ScreenTitle("Social", modifier = Modifier.weight(1f))
            IconButton(onClick = { vm.refresh() }) {
                Icon(Icons.Default.Refresh, contentDescription = "Refresh", tint = MaterialTheme.colorScheme.primary)
            }
        }

        state.error?.let { ErrorBanner(it) }

        if (state.loading) {
            LoadingRow("Checking Upload-Post profiles…")
        } else if (state.profiles.isEmpty()) {
            Notice(
                "No Upload-Post profiles returned. Add your Upload-Post API key in Settings, " +
                    "then connect your Instagram account on upload-post.com (the server needs it to post)."
            )
        } else {
            SectionCard(title = "Upload-Post profiles") {
                state.profiles.forEachIndexed { i, profile ->
                    Column(modifier = Modifier.padding(vertical = 6.dp)) {
                        Text(
                            profile.username ?: "unknown",
                            style = MaterialTheme.typography.bodyLarge,
                            fontWeight = FontWeight.SemiBold,
                            fontFamily = FontFamily.Monospace,
                        )
                        Spacer(Modifier.height(6.dp))
                        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            listOf("instagram", "tiktok", "youtube").forEach { platform ->
                                val connected = profile.connected?.contains(platform) == true
                                StatusChip(
                                    text = if (connected) "$platform ✓" else "$platform ✗",
                                    tone = if (connected) ChipTone.OK else ChipTone.NEUTRAL,
                                )
                            }
                        }
                    }
                    if (i < state.profiles.lastIndex) {
                        HairlineDivider(Modifier.padding(vertical = 6.dp))
                    }
                }
            }
        }

        SectionCard(title = "How publishing works") {
            Text(
                "1 · Create a reel (AI Shorts) or clips (Clip Generator).\n" +
                    "2 · Tap “Publish to Instagram” on the finished video.\n" +
                    "3 · Pick platforms, caption, and optionally a schedule.\n" +
                    "4 · OpenShorts sends it through Upload-Post to your connected Instagram Reels.",
                style = MaterialTheme.typography.bodyMedium,
                color = TextSecondary,
            )
        }

        Notice(
            "Instagram requires a Business or Creator account linked in Upload-Post. " +
                "The free Upload-Post tier includes 10 posts/month to all networks."
        )

        Spacer(Modifier.height(24.dp))
    }
}
