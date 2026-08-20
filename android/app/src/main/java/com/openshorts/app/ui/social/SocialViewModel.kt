package com.openshorts.app.ui.social

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.openshorts.app.OpenShortsApp
import com.openshorts.app.core.model.UploadPostProfile
import com.openshorts.app.data.ApiException
import com.openshorts.app.data.OpenShortsRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class SocialUiState(
    val loading: Boolean = false,
    val profiles: List<UploadPostProfile> = emptyList(),
    val error: String? = null,
)

class SocialViewModel(app: Application) : AndroidViewModel(app) {

    private val _state = MutableStateFlow(SocialUiState())
    val state: StateFlow<SocialUiState> = _state.asStateFlow()

    init {
        refresh()
    }

    fun refresh() {
        _state.update { it.copy(loading = true, error = null) }
        viewModelScope.launch {
            try {
                val repo = OpenShortsRepository((getApplication<OpenShortsApp>()).settings.value)
                val profiles = repo.socialProfiles().profiles.orEmpty()
                _state.update { it.copy(loading = false, profiles = profiles) }
            } catch (e: Exception) {
                _state.update {
                    it.copy(
                        loading = false,
                        error = (e as? ApiException)?.message ?: e.message,
                    )
                }
            }
        }
    }
}
