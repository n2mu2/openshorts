package com.openshorts.app.ui.clips

import android.app.Application
import android.content.Context
import android.net.Uri
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.openshorts.app.OpenShortsApp
import com.openshorts.app.core.model.Clip
import com.openshorts.app.core.model.ProcessRequest
import com.openshorts.app.core.model.SocialPostRequest
import com.openshorts.app.data.ApiException
import com.openshorts.app.data.OpenShortsRepository
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class ClipUiState(
    val urlInput: String = "",
    val fileName: String? = null,
    val fileUri: Uri? = null,
    val layouts: Set<String> = setOf("auto"),
    val targetClips: String = "",
    val minSeconds: String = "",
    val maxSeconds: String = "",
    val autoHook: Boolean = false,
    val submitting: Boolean = false,
    val jobId: String? = null,
    val status: String? = null,
    val logs: List<String> = emptyList(),
    val clips: List<Clip> = emptyList(),
    val error: String? = null,
    val publishMessage: String? = null,
    val publishing: Boolean = false,
    val watching: Boolean = false,
)

class ClipViewModel(app: Application) : AndroidViewModel(app) {

    private val _state = MutableStateFlow(ClipUiState())
    val state: StateFlow<ClipUiState> = _state.asStateFlow()

    private var pollJob: Job? = null

    private fun repo(): OpenShortsRepository =
        OpenShortsRepository((getApplication<OpenShortsApp>()).settings.value)

    fun setUrl(url: String) = _state.update { it.copy(urlInput = url) }

    fun setFile(context: Context, uri: Uri) {
        val name = runCatching {
            context.contentResolver.query(uri, arrayOf(android.provider.OpenableColumns.DISPLAY_NAME), null, null, null)?.use { c ->
                if (c.moveToFirst()) c.getString(0) else null
            }
        }.getOrNull()
        _state.update { it.copy(fileUri = uri, fileName = name ?: "video") }
    }

    fun clearFile() = _state.update { it.copy(fileUri = null, fileName = null) }

    fun toggleLayout(layout: String) = _state.update {
        val next = if (layout in it.layouts) it.layouts - layout else it.layouts + layout
        it.copy(layouts = next)
    }

    fun setTargetClips(v: String) = _state.update { it.copy(targetClips = v.filter(Char::isDigit).take(2)) }
    fun setMinSeconds(v: String) = _state.update { it.copy(minSeconds = v.filter(Char::isDigit).take(3)) }
    fun setMaxSeconds(v: String) = _state.update { it.copy(maxSeconds = v.filter(Char::isDigit).take(3)) }
    fun setAutoHook(v: Boolean) = _state.update { it.copy(autoHook = v) }

    fun submit(context: Context) {
        val s = _state.value
        if (s.submitting) return
        _state.update { it.copy(submitting = true, error = null, clips = emptyList(), logs = emptyList(), publishMessage = null) }
        viewModelScope.launch {
            try {
                val request = ProcessRequest(
                    url = s.urlInput.trim().ifBlank { null },
                    acknowledged = true,
                    layouts = s.layouts.toList(),
                    target_clips = s.targetClips.toIntOrNull(),
                    clip_min_seconds = s.minSeconds.toIntOrNull(),
                    clip_max_seconds = s.maxSeconds.toIntOrNull(),
                    auto_hook = s.autoHook,
                )
                val r = repo()
                val response = if (s.fileUri != null) {
                    r.submitFile(context, s.fileUri!!, request)
                } else {
                    r.submitUrl(request)
                }
                val jobId = response.jobId ?: throw ApiException("Server did not return a job id.")
                r.recordJob(jobId, "clips", s.fileName ?: s.urlInput.trim().take(60).ifBlank { "video" })
                _state.update { it.copy(jobId = jobId, status = "queued", submitting = false) }
                watch(jobId)
            } catch (e: Exception) {
                _state.update { it.copy(submitting = false, error = (e as? ApiException)?.message ?: "Unexpected error: ${e.message}") }
            }
        }
    }

    /** Resume watching an existing job (e.g. opened from the home screen). */
    fun resume(jobId: String) {
        _state.update { it.copy(jobId = jobId, status = "queued", clips = emptyList(), error = null) }
        watch(jobId)
    }

    private fun watch(jobId: String) {
        pollJob?.cancel()
        _state.update { it.copy(watching = true) }
        pollJob = viewModelScope.launch {
            while (true) {
                val r = repo()
                try {
                    val status = r.jobStatus(jobId)
                    _state.update {
                        it.copy(
                            status = status.status,
                            logs = status.logs ?: it.logs,
                            clips = status.result?.clips ?: it.clips,
                        )
                    }
                    r.updateJobStatus(jobId, status.status ?: "unknown")
                    if (status.status == "completed" || status.status == "failed") break
                } catch (e: Exception) {
                    _state.update { it.copy(error = "Status poll failed: ${e.message}", watching = false) }
                    break
                }
                delay(10_000)
            }
            _state.update { it.copy(watching = false) }
        }
    }

    fun absoluteUrl(url: String?): String? = repo().absoluteUrl(url)

    fun publish(
        clipIndex: Int,
        title: String?,
        description: String?,
        platforms: List<String>,
        scheduledDate: String?,
        timezone: String?,
    ) {
        val jobId = _state.value.jobId ?: run {
            _state.update { it.copy(publishMessage = "No job to publish.") }
            return
        }
        _state.update { it.copy(publishing = true, publishMessage = null) }
        viewModelScope.launch {
            try {
                val r = repo()
                val (upKey, upUser) = r.publishDefaults()
                val result = r.postClipToSocial(
                    SocialPostRequest(
                        jobId = jobId,
                        clipIndex = clipIndex,
                        apiKey = upKey,
                        userId = upUser,
                        platforms = platforms,
                        title = title?.takeIf { it.isNotBlank() },
                        description = description?.takeIf { it.isNotBlank() },
                        scheduledDate = scheduledDate,
                        timezone = timezone,
                    )
                )
                _state.update { it.copy(publishing = false, publishMessage = "Publish accepted: $result") }
            } catch (e: Exception) {
                _state.update {
                    it.copy(
                        publishing = false,
                        publishMessage = "Publish failed: ${(e as? ApiException)?.message ?: e.message}",
                    )
                }
            }
        }
    }

    fun dismissPublishMessage() = _state.update { it.copy(publishMessage = null) }
}
