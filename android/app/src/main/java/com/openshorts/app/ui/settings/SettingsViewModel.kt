package com.openshorts.app.ui.settings

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.openshorts.app.OpenShortsApp
import com.openshorts.app.core.prefs.AppSettings
import com.openshorts.app.core.prefs.SettingsStore
import com.openshorts.app.data.ApiException
import com.openshorts.app.data.OpenShortsRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.firstOrNull
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class SettingsUiState(
    val settings: AppSettings = AppSettings(),
    val loaded: Boolean = false,
    val saving: Boolean = false,
    val saved: Boolean = false,
    val testing: Boolean = false,
    val testResult: String? = null,
    val testOk: Boolean? = null,
)

class SettingsViewModel(app: Application) : AndroidViewModel(app) {

    private val _state = MutableStateFlow(SettingsUiState())
    val state: StateFlow<SettingsUiState> = _state.asStateFlow()

    init {
        viewModelScope.launch {
            val loaded = SettingsStore.settings.firstOrNull()
            if (loaded != null) _state.update { it.copy(settings = loaded, loaded = true) }
        }
    }

    fun update(transform: (AppSettings) -> AppSettings) =
        _state.update { it.copy(settings = transform(it.settings), saved = false) }

    fun save() {
        val settings = _state.value.settings
        _state.update { it.copy(saving = true, saved = false) }
        viewModelScope.launch {
            SettingsStore.save(settings)
            _state.update { it.copy(saving = false, saved = true) }
        }
    }

    fun testConnection() {
        _state.update { it.copy(testing = true, testResult = null, testOk = null) }
        viewModelScope.launch {
            val repo = OpenShortsRepository(_state.value.settings)
            val healthOk = runCatching { repo.health() }.getOrDefault(false)
            if (!healthOk) {
                _state.update { it.copy(testing = false, testOk = false, testResult = "Server unreachable. Check the URL and that OpenShorts is running.") }
                return@launch
            }
            val profiles = runCatching { repo.socialProfiles().profiles.orEmpty() }.getOrNull()
            val ig = profiles?.any { p -> p.connected?.contains("instagram") == true } == true
            val msg = buildString {
                append("Server reachable ✓")
                if (profiles != null) {
                    append("\nUpload-Post profiles: ")
                    append(profiles.joinToString(", ") { it.username ?: "?" })
                    append(if (ig) "\nInstagram connected ✓" else "\nInstagram NOT connected — check the Upload-Post key/profile.")
                } else {
                    append("\nUpload-Post check skipped (needs a key).")
                }
            }
            _state.update { it.copy(testing = false, testOk = healthOk && (profiles == null || ig), testResult = msg) }
        }
    }

    fun clearJobs() {
        viewModelScope.launch { SettingsStore.clearJobs() }
    }
}
