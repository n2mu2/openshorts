package com.openshorts.app.ui.clips

import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.clickable
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
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material.icons.filled.Send
import androidx.compose.material3.Checkbox
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.openshorts.app.ui.components.BrassButton
import com.openshorts.app.ui.components.ChipRow
import com.openshorts.app.ui.components.ErrorBanner
import com.openshorts.app.ui.components.HairlineDivider
import com.openshorts.app.ui.components.LabeledField
import com.openshorts.app.ui.components.LoadingRow
import com.openshorts.app.ui.components.LogTail
import com.openshorts.app.ui.components.Notice
import com.openshorts.app.ui.components.OkBanner
import com.openshorts.app.ui.components.ScreenTitle
import com.openshorts.app.ui.components.SectionCard
import com.openshorts.app.ui.components.StatusChip
import com.openshorts.app.ui.components.ChipTone
import com.openshorts.app.ui.components.VideoPlayer
import com.openshorts.app.ui.publish.PublishSheet
import com.openshorts.app.ui.theme.Brass
import com.openshorts.app.ui.theme.TextSecondary

private val LAYOUTS = listOf("auto", "split", "screencast", "speaker_cut", "punch_in")

@Composable
fun ClipGeneratorScreen(
    jobId: String? = null,
    vm: ClipViewModel = viewModel(),
) {
    val state by vm.state.collectAsStateWithLifecycle()
    val context = LocalContext.current
    var showPublish by remember { mutableStateOf(false) }
    var publishClipIndex by remember { mutableStateOf(0) }

    val filePicker = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.GetContent()
    ) { uri: Uri? -> uri?.let { vm.setFile(context, it) } }

    if (jobId != null && vm.state.value.jobId != jobId && vm.state.value.status == null) {
        vm.resume(jobId)
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(horizontal = 16.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        Spacer(Modifier.height(8.dp))
        ScreenTitle("Clip Generator")

        // ------------------------------------------------------------ input
        SectionCard(title = "1 · Source video") {
            LabeledField(
                label = "YouTube / video URL",
                value = state.urlInput,
                onValueChange = vm::setUrl,
                placeholder = "https://youtube.com/watch?v=…",
            )
            Spacer(Modifier.height(10.dp))
            Row(verticalAlignment = Alignment.CenterVertically) {
                TextButton(onClick = { filePicker.launch("video/*") }) {
                    Text("Pick video from phone", color = Brass)
                }
                state.fileName?.let { name ->
                    Spacer(Modifier.height(0.dp))
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        StatusChip("$name ✓", ChipTone.OK)
                        Spacer(Modifier.height(0.dp))
                        TextButton(onClick = { vm.clearFile() }) {
                            Text("remove", color = TextSecondary, style = MaterialTheme.typography.labelMedium)
                        }
                    }
                }
            }
            Text(
                if (state.fileUri != null) "A local file is selected — it overrides the URL field."
                else "Either paste a URL or pick a file from your phone.",
                style = MaterialTheme.typography.bodySmall,
                color = TextSecondary,
            )
        }

        SectionCard(title = "2 · Options") {
            Text("Layouts the AI may apply", style = MaterialTheme.typography.labelMedium, color = TextSecondary)
            Spacer(Modifier.height(8.dp))
            ChipRow(
                options = LAYOUTS,
                selected = state.layouts,
                onToggle = vm::toggleLayout,
            )
            Spacer(Modifier.height(14.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                LabeledField(
                    label = "Target clips",
                    value = state.targetClips,
                    onValueChange = vm::setTargetClips,
                    placeholder = "e.g. 5",
                    modifier = Modifier.weight(1f),
                )
                LabeledField(
                    label = "Min sec",
                    value = state.minSeconds,
                    onValueChange = vm::setMinSeconds,
                    placeholder = "15",
                    modifier = Modifier.weight(1f),
                )
                LabeledField(
                    label = "Max sec",
                    value = state.maxSeconds,
                    onValueChange = vm::setMaxSeconds,
                    placeholder = "60",
                    modifier = Modifier.weight(1f),
                )
            }
            Spacer(Modifier.height(6.dp))
            Row(verticalAlignment = Alignment.CenterVertically) {
                Checkbox(checked = state.autoHook, onCheckedChange = vm::setAutoHook)
                Text("Auto-generate hook text overlays", style = MaterialTheme.typography.bodyMedium)
            }
        }

        state.error?.let { ErrorBanner(it) }

        if (state.jobId == null) {
            BrassButton(
                text = if (state.fileUri != null) "Upload video & find viral moments" else "Find viral moments",
                icon = Icons.Default.PlayArrow,
                loading = state.submitting,
                onClick = { vm.submit(context) },
                modifier = Modifier.fillMaxWidth(),
            )
            Notice(
                "Self-hosted on CPU, an 8-minute video takes ~5–8 minutes. " +
                    "The job keeps running on the server if you leave this screen."
            )
        }

        // ------------------------------------------------------------ status
        state.jobId?.let { id ->
            SectionCard(title = "Job ${id.take(8)}…") {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    StatusChip(statusLabel(state.status), toneFor(state.status))
                    if (state.watching) {
                        Spacer(Modifier.height(0.dp))
                        LoadingRow("polling…")
                    }
                }
                Spacer(Modifier.height(10.dp))
                LogTail(state.logs)
            }
        }

        // ------------------------------------------------------------- clips
        if (state.clips.isNotEmpty()) {
            SectionCard(title = "Clips (${state.clips.size})") {
                state.clips.forEachIndexed { index, clip ->
                    Column(modifier = Modifier.fillMaxWidth()) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Text(
                                "${index + 1}. ${clip.displayTitle.take(80)}",
                                style = MaterialTheme.typography.bodyMedium,
                                fontWeight = FontWeight.Medium,
                                modifier = Modifier.weight(1f),
                            )
                        }
                        clip.duration?.let { d ->
                            Text(
                                "${d.toInt()}s",
                                style = MaterialTheme.typography.labelSmall,
                                color = TextSecondary,
                            )
                        }
                        Spacer(Modifier.height(6.dp))
                        vm.absoluteUrl(clip.videoUrl)?.let { url ->
                            VideoPlayer(url = url, modifier = Modifier.fillMaxWidth().height(320.dp))
                        }
                        Spacer(Modifier.height(8.dp))
                        BrassButton(
                            text = "Publish to Instagram",
                            icon = Icons.Default.Send,
                            onClick = {
                                publishClipIndex = index
                                showPublish = true
                            },
                            modifier = Modifier.fillMaxWidth(),
                        )
                    }
                    if (index < state.clips.lastIndex) {
                        HairlineDivider(Modifier.padding(vertical = 12.dp))
                    }
                }
            }
        }

        Spacer(Modifier.height(24.dp))
    }

    if (showPublish) {
        PublishSheet(
            title = "Publish clip #${publishClipIndex + 1}",
            defaultDescription = state.clips.getOrNull(publishClipIndex)?.displayTitle,
            publishing = state.publishing,
            onDismiss = { showPublish = false },
            onPublish = { title, desc, platforms, scheduled, tz ->
                vm.publish(publishClipIndex, title, desc, platforms, scheduled, tz)
            },
        )
    }

    state.publishMessage?.let { msg ->
        androidx.compose.material3.AlertDialog(
            onDismissRequest = { vm.dismissPublishMessage() },
            confirmButton = {
                TextButton(onClick = { vm.dismissPublishMessage() }) { Text("OK") }
            },
            title = { Text("Publish result") },
            text = { Text(msg) },
        )
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
