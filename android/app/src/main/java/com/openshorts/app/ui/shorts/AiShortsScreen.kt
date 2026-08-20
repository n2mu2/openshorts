package com.openshorts.app.ui.shorts

import androidx.compose.foundation.background
import androidx.compose.foundation.border
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
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.PlayArrow
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Star
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
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.openshorts.app.ui.components.BrassButton
import com.openshorts.app.ui.components.ChipRow
import com.openshorts.app.ui.components.ErrorBanner
import com.openshorts.app.ui.components.LabeledField
import com.openshorts.app.ui.components.LoadingRow
import com.openshorts.app.ui.components.LogTail
import com.openshorts.app.ui.components.Notice
import com.openshorts.app.ui.components.OkBanner
import com.openshorts.app.ui.components.ScreenTitle
import com.openshorts.app.ui.components.SectionCard
import com.openshorts.app.ui.components.VideoPlayer
import com.openshorts.app.ui.publish.PublishSheet
import com.openshorts.app.ui.theme.Brass
import com.openshorts.app.ui.theme.Hairline
import com.openshorts.app.ui.theme.InkSurface
import com.openshorts.app.ui.theme.TextSecondary

private val STYLES = listOf("ugc", "educational", "shock", "story", "comparison")

@Composable
fun AiShortsScreen(
    jobId: String? = null,
    vm: ShortsViewModel = viewModel(),
) {
    val state by vm.state.collectAsStateWithLifecycle()
    var showPublish by remember { mutableStateOf(false) }

    if (jobId != null && vm.state.value.jobId != jobId && vm.state.value.step == ShortsStep.INPUT) {
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
        ScreenTitle("AI Shorts")

        when (state.step) {
            ShortsStep.INPUT -> InputStep(state, vm)
            ShortsStep.ANALYZING -> {
                SectionCard(title = "Writing scripts") {
                    LoadingRow("Gemini is researching and writing viral scripts…")
                    Spacer(Modifier.height(8.dp))
                    Text(
                        "This usually takes 20–60 seconds.",
                        style = MaterialTheme.typography.bodySmall,
                        color = TextSecondary,
                    )
                }
            }

            ShortsStep.SCRIPTS -> ScriptsStep(state, vm)
            ShortsStep.GENERATING -> GeneratingStep(state)
            ShortsStep.DONE -> DoneStep(state, vm) { showPublish = true }
            ShortsStep.FAILED -> FailedStep(state, vm)
        }

        Spacer(Modifier.height(24.dp))
    }

    if (showPublish) {
        PublishSheet(
            title = "Publish reel to Instagram & more",
            defaultDescription = state.scriptSummary,
            publishing = state.publishing,
            onDismiss = { showPublish = false },
            onPublish = { title, desc, platforms, scheduled, tz ->
                vm.publish(title, desc, platforms, scheduled, tz)
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

@Composable
private fun InputStep(state: ShortsUiState, vm: ShortsViewModel) {
    SectionCard(title = "1 · Describe the reel") {
        LabeledField(
            label = "Content description",
            value = state.description,
            onValueChange = vm::setDescription,
            singleLine = false,
            placeholder = "e.g. 45-second reel explaining candlestick patterns to beginners, energetic tone, CTA to follow for daily market tips",
        )
        Spacer(Modifier.height(10.dp))
        LabeledField(
            label = "Or paste a URL (web research)",
            value = state.url,
            onValueChange = vm::setUrl,
            placeholder = "https://…",
        )
    }

    SectionCard(title = "2 · Style") {
        Text("Script style", style = MaterialTheme.typography.labelMedium, color = TextSecondary)
        Spacer(Modifier.height(8.dp))
        ChipRow(
            options = STYLES,
            selected = setOf(state.style),
            onToggle = { vm.setStyle(it) },
        )
        Spacer(Modifier.height(14.dp))
        Text("Language", style = MaterialTheme.typography.labelMedium, color = TextSecondary)
        Spacer(Modifier.height(8.dp))
        ChipRow(
            options = listOf("en", "es"),
            selected = setOf(state.language),
            onToggle = { vm.setLanguage(it) },
        )
        Spacer(Modifier.height(14.dp))
        Text("Actor gender", style = MaterialTheme.typography.labelMedium, color = TextSecondary)
        Spacer(Modifier.height(8.dp))
        ChipRow(
            options = listOf("female", "male"),
            selected = setOf(state.actorGender),
            onToggle = { vm.setGender(it) },
        )
    }

    SectionCard(title = "3 · Generation options") {
        Text(
            "Scripts to write: ${state.numScripts}",
            style = MaterialTheme.typography.bodyMedium,
            color = TextSecondary,
        )
        Spacer(Modifier.height(8.dp))
        Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            listOf(1, 2, 3, 5).forEach { n ->
                val selected = state.numScripts == n
                Text(
                    text = "$n",
                    style = MaterialTheme.typography.labelLarge,
                    color = if (selected) Brass else TextSecondary,
                    modifier = Modifier
                        .background(if (selected) InkSurface else InkSurface, RoundedCornerShape(8.dp))
                        .border1(selected)
                        .clickable { vm.setNumScripts(n) }
                        .padding(horizontal = 16.dp, vertical = 10.dp),
                )
            }
        }
        Spacer(Modifier.height(14.dp))
        Text("Video mode", style = MaterialTheme.typography.labelMedium, color = TextSecondary)
        Spacer(Modifier.height(8.dp))
        ChipRow(
            options = listOf("lowcost", "premium"),
            selected = setOf(state.videoMode),
            onToggle = { vm.setVideoMode(it) },
        )
        Spacer(Modifier.height(14.dp))
        LabeledField(
            label = "Actor description (optional)",
            value = state.actorDescription,
            onValueChange = vm::setActorDescription,
            placeholder = "e.g. Indian woman in her 30s, professional yet friendly",
        )
        Spacer(Modifier.height(10.dp))
        Row(verticalAlignment = Alignment.CenterVertically) {
            LabeledField(
                label = "ElevenLabs voice ID (optional)",
                value = state.voiceId,
                onValueChange = vm::setVoiceId,
                placeholder = "e.g. 21m00Tcm4TlvDq8ikWAM",
                modifier = Modifier.weight(1f),
            )
            TextButton(onClick = { vm.loadVoices() }, enabled = !state.loadingVoices) {
                if (state.loadingVoices) {
                    LoadingRow("")
                } else {
                    Text("Load voices", color = Brass)
                }
            }
        }
        if (state.voices.isNotEmpty()) {
            Spacer(Modifier.height(6.dp))
            ChipRow(
                options = state.voices.take(8).map { it.name ?: it.voiceId ?: "voice" },
                selected = emptySet(),
                onToggle = { label ->
                    val v = state.voices.firstOrNull { it.name == label }
                    v?.voiceId?.let { vm.setVoiceId(it) }
                },
            )
        }
    }

    state.error?.let { ErrorBanner(it) }

    BrassButton(
        text = "Write scripts with Gemini",
        icon = Icons.Default.Star,
        loading = state.busy,
        onClick = { vm.analyze() },
        modifier = Modifier.fillMaxWidth(),
    )

    Notice(
        "Costs: analyze is free-tier Gemini; generating the reel uses fal.ai + ElevenLabs " +
            "(~$0.65 lowcost / ~$2 premium per video, via your keys or the hosted plan). " +
            "Always review AI-written financial content before publishing."
    )
}

@Composable
private fun ScriptsStep(state: ShortsUiState, vm: ShortsViewModel) {
    SectionCard(title = "Pick a script") {
        state.scripts.forEach { script ->
            val selected = state.selectedScript == script.index
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .background(if (selected) InkSurface else androidx.compose.ui.graphics.Color.Transparent, RoundedCornerShape(10.dp))
                    .clickable { vm.selectScript(script.index) }
                    .padding(12.dp)
                    .border1(selected),
            ) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text(
                        "${script.index + 1}. ${script.title}",
                        style = MaterialTheme.typography.bodyLarge,
                        fontWeight = FontWeight.SemiBold,
                        modifier = Modifier.weight(1f),
                    )
                    if (selected) Text("✓ SELECTED", color = Brass, style = MaterialTheme.typography.labelSmall)
                }
                if (script.preview.isNotBlank()) {
                    Spacer(Modifier.height(6.dp))
                    Text(
                        script.preview.take(220) + if (script.preview.length > 220) "…" else "",
                        style = MaterialTheme.typography.bodySmall,
                        color = TextSecondary,
                    )
                }
            }
            Spacer(Modifier.height(8.dp))
        }
    }

    state.error?.let { ErrorBanner(it) }

    Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
        TextButton(onClick = { vm.backToInput() }) {
            Text("← Back", color = TextSecondary)
        }
        BrassButton(
            text = "Generate reel",
            icon = Icons.Default.PlayArrow,
            loading = state.busy,
            onClick = { vm.generate() },
            modifier = Modifier.weight(1f),
        )
    }
}

@Composable
private fun GeneratingStep(state: ShortsUiState) {
    SectionCard(title = "Generating your reel") {
        LoadingRow("fal.ai actor → ElevenLabs voice → lip-sync → b-roll → composite")
        Spacer(Modifier.height(12.dp))
        Text(
            "This can take a few minutes. The job keeps running on the server — you can leave this screen.",
            style = MaterialTheme.typography.bodySmall,
            color = TextSecondary,
        )
        Spacer(Modifier.height(12.dp))
        LogTail(state.logs)
    }
}

@Composable
private fun DoneStep(state: ShortsUiState, vm: ShortsViewModel, onPublishClick: () -> Unit) {
    OkBanner("Reel ready! ${state.scriptSummary?.let { "— $it" } ?: ""}")
    state.videoUrl?.let { url ->
        vm.absoluteUrl(url)?.let { absolute ->
            SectionCard(title = "Preview") {
                VideoPlayer(url = absolute, modifier = Modifier.fillMaxWidth().height(420.dp))
            }
        }
    }
    BrassButton(
        text = "Publish to Instagram",
        icon = Icons.Default.Star,
        onClick = onPublishClick,
        modifier = Modifier.fillMaxWidth(),
    )
    TextButton(onClick = { vm.backToInput() }, modifier = Modifier.fillMaxWidth()) {
        Text("← Make another reel", color = TextSecondary)
    }
}

@Composable
private fun FailedStep(state: ShortsUiState, vm: ShortsViewModel) {
    state.error?.let { ErrorBanner(it) }
    if (!state.logs.isNullOrEmpty()) LogTail(state.logs)
    Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
        TextButton(onClick = { vm.backToInput() }) {
            Text("← Start over", color = TextSecondary)
        }
        BrassButton(
            text = "Retry",
            icon = Icons.Default.Refresh,
            onClick = {
                if (state.scripts.isEmpty()) vm.analyze() else vm.generate()
            },
            modifier = Modifier.weight(1f),
        )
    }
}

private fun Modifier.border1(selected: Boolean): Modifier =
    this.border(
        1.dp,
        if (selected) Brass else Hairline,
        RoundedCornerShape(10.dp),
    )
