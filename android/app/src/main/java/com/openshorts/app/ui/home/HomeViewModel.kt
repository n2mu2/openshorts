package com.openshorts.app.ui.home

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.openshorts.app.OpenShortsApp
import com.openshorts.app.core.model.ConfigResponse
import com.openshorts.app.core.model.UploadPostProfile
import com.openshorts.app.core.prefs.SettingsStore
import com.openshorts.app.core.prefs.StoredJob
import com.openshorts.app.data.OpenShortsRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class HomeUiState(
    val serverUrl: String = "",
    val serverOk: Boolean? = null,
    val config: ConfigResponse? = null,
    val profiles: List<UploadPostProfile> = emptyList(),
    val jobs: List<StoredJob> = emptyList(),
    val checking: Boolean = false,
    val instagramConnected: Boolean? = null,
)

class HomeViewModel(app: Application) : AndroidViewModel(app) {

    private val _state = MutableStateFlow(HomeUiState())
    val state: StateFlow<HomeUiState> = _state.asStateFlow()

    init {
        val appState = (app as OpenShortsApp).settings
        _state.update { it.copy(serverUrl = appState.value.serverUrl) }
        viewModelScope.launch {
            appState.collect { s ->
                _state.update { it.copy(serverUrl = s.serverUrl) }
            }
        }
        viewModelScope.launch {
            SettingsStore.jobs.collect { jobs ->
                _state.update { it.copy(jobs = jobs) }
            }
        }
        refresh()
    }

    fun refresh() {
        _state.update { it.copy(checking = true) }
        viewModelScope.launch {
            val repo = OpenShortsRepository((getApplication<OpenShortsApp>()).settings.value)
            val ok = runCatching { repo.health() }.getOrDefault(false)
            val config = runCatching { repo.config() }.getOrNull()
            var profiles: List<UploadPostProfile> = emptyList()
            if (ok) {
                profiles = runCatching { repo.socialProfiles().profiles.orEmpty() }.getOrDefault(emptyList())
            }
            val igConnected = profiles.any { p -> p.connected?.contains("instagram") == true }
            _state.update {
                it.copy(
                    checking = false,
                    serverOk = ok,
                    config = config,
                    profiles = profiles,
                    instagramConnected = if (profiles.isEmpty()) null else igConnected,
                )
            }
        }
    }
}
