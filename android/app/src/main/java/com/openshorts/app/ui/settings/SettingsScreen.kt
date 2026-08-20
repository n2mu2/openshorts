package com.openshorts.app.ui.settings

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
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.openshorts.app.core.prefs.AppSettings
import com.openshorts.app.ui.components.BrassButton
import com.openshorts.app.ui.components.ErrorBanner
import com.openshorts.app.ui.components.LabeledField
import com.openshorts.app.ui.components.Notice
import com.openshorts.app.ui.components.OkBanner
import com.openshorts.app.ui.components.ScreenTitle
import com.openshorts.app.ui.components.SectionCard
import com.openshorts.app.ui.theme.Brass
import com.openshorts.app.ui.theme.TextSecondary

@Composable
fun SettingsScreen(vm: SettingsViewModel = viewModel()) {
    val state by vm.state.collectAsStateWithLifecycle()
    val s = state.settings

    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(horizontal = 16.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        Spacer(Modifier.height(8.dp))
        ScreenTitle("Settings")

        SectionCard(title = "OpenShorts server") {
            LabeledField(
                label = "Server URL",
                value = s.serverUrl,
                onValueChange = { v -> vm.update { it.copy(serverUrl = v) } },
                placeholder = AppSettings.DEFAULT_SERVER,
                keyboard = KeyboardType.Uri,
            )
            LabeledField(
                label = "Hosted API key (osk_…, optional)",
                value = s.apiKey,
                onValueChange = { v -> vm.update { it.copy(apiKey = v) } },
                secret = true,
            )
            Text(
                "Self-hosted: leave the API key blank and fill the BYOK keys below.\n" +
                    "Hosted cloud (openshorts.app): only the API key is needed.",
                style = MaterialTheme.typography.bodySmall,
                color = TextSecondary,
            )
        }

        SectionCard(title = "BYOK keys (self-hosted only)") {
            LabeledField(
                label = "Gemini API key",
                value = s.geminiKey,
                onValueChange = { v -> vm.update { it.copy(geminiKey = v) } },
                secret = true,
            )
            Spacer(Modifier.height(8.dp))
            LabeledField(
                label = "fal.ai API key",
                value = s.falKey,
                onValueChange = { v -> vm.update { it.copy(falKey = v) } },
                secret = true,
            )
            Spacer(Modifier.height(8.dp))
            LabeledField(
                label = "ElevenLabs API key",
                value = s.elevenLabsKey,
                onValueChange = { v -> vm.update { it.copy(elevenLabsKey = v) } },
                secret = true,
            )
            Spacer(Modifier.height(8.dp))
            LabeledField(
                label = "Upload-Post API key",
                value = s.uploadPostKey,
                onValueChange = { v -> vm.update { it.copy(uploadPostKey = v) } },
                secret = true,
            )
            Spacer(Modifier.height(8.dp))
            LabeledField(
                label = "Upload-Post profile (username)",
                value = s.uploadPostUser,
                onValueChange = { v -> vm.update { it.copy(uploadPostUser = v) } },
            )
        }

        Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            BrassButton(
                text = "Save",
                loading = state.saving,
                onClick = { vm.save() },
                modifier = Modifier.weight(1f),
            )
            TextButton(onClick = { vm.testConnection() }, modifier = Modifier.weight(1f)) {
                Text(
                    if (state.testing) "Testing…" else "Test connection",
                    color = Brass,
                )
            }
        }

        if (state.saved) {
            OkBanner("Settings saved — they apply on the next request.")
        }
        state.testResult?.let { result ->
            if (state.testOk == false) {
                ErrorBanner(result)
            } else {
                OkBanner(result)
            }
        }

        SectionCard(title = "Data") {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(
                    "Recently watched jobs are stored only on this device.",
                    style = MaterialTheme.typography.bodySmall,
                    color = TextSecondary,
                    modifier = Modifier.weight(1f),
                )
                TextButton(onClick = { vm.clearJobs() }) {
                    Text("Clear history", color = Brass)
                }
            }
        }

        Notice(
            "API keys are stored in the app's private DataStore on this device only. " +
                "For production you may prefer Android Keystore-backed encryption — " +
                "see the README (android/README.md)."
        )

        Spacer(Modifier.height(24.dp))
    }
}
