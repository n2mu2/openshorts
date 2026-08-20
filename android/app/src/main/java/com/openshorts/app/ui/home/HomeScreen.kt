package com.openshorts.app.ui.home

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Star
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
import com.openshorts.app.core.prefs.StoredJob
import com.openshorts.app.ui.components.BrassButton
import com.openshorts.app.ui.components.ChipTone
import com.openshorts.app.ui.components.HairlineDivider
import com.openshorts.app.ui.components.KeyValueRow
import com.openshorts.app.ui.components.ScreenTitle
import com.openshorts.app.ui.components.SectionCard
import com.openshorts.app.ui.components.StatusChip
import com.openshorts.app.ui.theme.Hairline
import com.openshorts.app.ui.theme.InkSurface
import com.openshorts.app.ui.theme.TextSecondary
import java.time.Instant
import java.time.ZoneId
import java.time.format.DateTimeFormatter

@Composable
fun HomeScreen(
    onNewShort: () -> Unit,
    onNewClip: () -> Unit,
    onOpenJob: (StoredJob) -> Unit,
    vm: HomeViewModel = viewModel(),
) {
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
            ScreenTitle("OpenShorts", modifier = Modifier.weight(1f))
            IconButton(onClick = { vm.refresh() }) {
                Icon(Icons.Default.Refresh, contentDescription = "Refresh", tint = MaterialTheme.colorScheme.primary)
            }
        }

        // ------------------------------------------------------- server card
        SectionCard(title = "Connection") {
            KeyValueRow("Server", state.serverUrl.ifBlank { "not set" })
            Row(verticalAlignment = Alignment.CenterVertically) {
                when (state.serverOk) {
                    null -> StatusChip("checking…", ChipTone.NEUTRAL)
                    true -> StatusChip("connected", ChipTone.OK)
                    false -> StatusChip("unreachable", ChipTone.BAD)
                }
                Spacer(Modifier.width(8.dp))
                if (state.serverOk == false) {
                    Text(
                        "Set the correct URL in Settings",
                        style = MaterialTheme.typography.bodySmall,
                        color = TextSecondary,
                    )
                }
            }
            if (state.config?.billingEnabled == true) {
                Spacer(Modifier.height(8.dp))
                StatusChip("hosted cloud mode", ChipTone.BRASS)
            }
            Spacer(Modifier.height(8.dp))
            Row(verticalAlignment = Alignment.CenterVertically) {
                when (state.instagramConnected) {
                    null -> StatusChip("Instagram: unknown", ChipTone.NEUTRAL)
                    true -> StatusChip("Instagram: connected", ChipTone.OK)
                    false -> StatusChip("Instagram: not connected", ChipTone.WARN)
                }
            }
        }

        // ---------------------------------------------------- quick actions
        Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            BrassButton(
                text = "New AI reel",
                icon = Icons.Default.Star,
                onClick = onNewShort,
                modifier = Modifier.weight(1f),
            )
            BrassButton(
                text = "New clip job",
                icon = Icons.Default.PlayArrow,
                onClick = onNewClip,
                modifier = Modifier.weight(1f),
            )
        }

        // ----------------------------------------------------------- jobs
        SectionCard(title = "Recent jobs") {
            if (state.jobs.isEmpty()) {
                Text(
                    "No jobs yet. Create an AI reel from a prompt, or send a long trading video through the Clip Generator.",
                    color = TextSecondary,
                    style = MaterialTheme.typography.bodyMedium,
                )
            } else {
                state.jobs.take(20).forEachIndexed { i, job ->
                    JobRow(job = job, onClick = { onOpenJob(job) })
                    if (i < state.jobs.take(20).lastIndex) HairlineDivider(Modifier.padding(vertical = 8.dp))
                }
            }
        }

        Spacer(Modifier.height(24.dp))
    }
}

@Composable
private fun JobRow(job: StoredJob, onClick: () -> Unit) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .background(InkSurface, RoundedCornerShape(8.dp))
            .clickable(onClick = onClick)
            .padding(10.dp),
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text(
                job.label.ifBlank { job.id.take(8) },
                style = MaterialTheme.typography.bodyMedium,
                fontWeight = FontWeight.Medium,
                modifier = Modifier.weight(1f),
            )
            StatusChip(
                job.kind.ifBlank { "job" },
                if (job.kind == "shorts") ChipTone.BRASS else ChipTone.NEUTRAL,
            )
        }
        Spacer(Modifier.height(6.dp))
        Row(verticalAlignment = Alignment.CenterVertically) {
            StatusChip(statusLabel(job.lastStatus), toneFor(job.lastStatus))
            Spacer(Modifier.width(10.dp))
            Text(
                formatTime(job.createdAt),
                style = MaterialTheme.typography.labelSmall,
                color = TextSecondary,
                fontFamily = FontFamily.Monospace,
            )
        }
    }
}

private fun statusLabel(status: String?): String = when (status) {
    null -> "queued"
    else -> status
}

private fun toneFor(status: String?): ChipTone = when (status) {
    "completed" -> ChipTone.OK
    "failed" -> ChipTone.BAD
    null, "queued", "processing" -> ChipTone.WARN
    else -> ChipTone.NEUTRAL
}

private fun formatTime(epochMillis: Long): String = runCatching {
    DateTimeFormatter.ofPattern("dd MMM HH:mm")
        .withZone(ZoneId.systemDefault())
        .format(Instant.ofEpochMilli(epochMillis))
}.getOrDefault("")
