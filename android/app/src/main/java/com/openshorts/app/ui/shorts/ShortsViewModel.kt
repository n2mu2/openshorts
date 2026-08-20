package com.openshorts.app.ui.shorts

import android.app.Application
import androidx.lifecycle.AndroidViewModel
import androidx.lifecycle.viewModelScope
import com.google.gson.JsonElement
import com.openshorts.app.OpenShortsApp
import com.openshorts.app.core.model.AnalyzeRequest
import com.openshorts.app.core.model.GenerateRequest
import com.openshorts.app.core.model.SaasPostRequest
import com.openshorts.app.core.model.VoiceOption
import com.openshorts.app.data.ApiException
import com.openshorts.app.data.OpenShortsRepository
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

enum class ShortsStep { INPUT, ANALYZING, SCRIPTS, GENERATING, DONE, FAILED }

data class ScriptItem(
    val index: Int,
    val title: String,
    val preview: String,
    val raw: JsonElement,
)

data class ShortsUiState(
    val step: ShortsStep = ShortsStep.INPUT,
    val description: String = "",
    val url: String = "",
    val style: String = "ugc",
    val language: String = "en",
    val actorGender: String = "female",
    val numScripts: Int = 3,
    val actorDescription: String = "",
    val videoMode: String = "lowcost",
    val voiceId: String = "",
    val voices: List<VoiceOption> = emptyList(),
    val loadingVoices: Boolean = false,
    val busy: Boolean = false,
    val scripts: List<ScriptItem> = emptyList(),
    val selectedScript: Int? = null,
    val jobId: String? = null,
    val status: String? = null,
    val logs: List<String> = emptyList(),
    val videoUrl: String? = null,
    val scriptSummary: String? = null,
    val error: String? = null,
    val publishMessage: String? = null,
    val publishing: Boolean = false,
)

class ShortsViewModel(app: Application) : AndroidViewModel(app) {

    private val _state = MutableStateFlow(ShortsUiState())
    val state: StateFlow<ShortsUiState> = _state.asStateFlow()

    private var pollJob: Job? = null

    private fun repo(): OpenShortsRepository =
        OpenShortsRepository((getApplication<OpenShortsApp>()).settings.value)

    fun setDescription(v: String) = _state.update { it.copy(description = v) }
    fun setUrl(v: String) = _state.update { it.copy(url = v) }
    fun setStyle(v: String) = _state.update { it.copy(style = v) }
    fun setLanguage(v: String) = _state.update { it.copy(language = v) }
    fun setGender(v: String) = _state.update { it.copy(actorGender = v) }
    fun setNumScripts(v: Int) = _state.update { it.copy(numScripts = v) }
    fun setActorDescription(v: String) = _state.update { it.copy(actorDescription = v) }
    fun setVideoMode(v: String) = _state.update { it.copy(videoMode = v) }
    fun setVoiceId(v: String) = _state.update { it.copy(voiceId = v) }
    fun selectScript(i: Int) = _state.update { it.copy(selectedScript = i) }

    fun backToInput() = _state.update {
        it.copy(step = ShortsStep.INPUT, scripts = emptyList(), selectedScript = null, error = null)
    }

    fun loadVoices() {
        _state.update { it.copy(loadingVoices = true) }
        viewModelScope.launch {
            try {
                val voices = repo().voices().voices.orEmpty()
                _state.update { it.copy(voices = voices, loadingVoices = false) }
            } catch (e: Exception) {
                _state.update { it.copy(loadingVoices = false, error = (e as? ApiException)?.message ?: e.message) }
            }
        }
    }

    /** Step 1: description/URL -> viral scripts via Gemini. */
    fun analyze() {
        val s = _state.value
        if (s.busy) return
        if (s.description.isBlank() && s.url.isBlank()) {
            _state.update { it.copy(error = "Write a description or paste a URL first.") }
            return
        }
        _state.update { it.copy(step = ShortsStep.ANALYZING, busy = true, error = null) }
        viewModelScope.launch {
            try {
                val r = repo()
                val response = r.analyze(
                    AnalyzeRequest(
                        url = s.url.trim().ifBlank { null },
                        description = s.description.trim().ifBlank { null },
                        num_scripts = s.numScripts,
                        style = s.style,
                        language = s.language,
                        actor_gender = s.actorGender,
                    )
                )
                val items = response.scripts.orEmpty().mapIndexed { i, raw ->
                    ScriptItem(
                        index = i,
                        title = raw.field("title") ?: "Script ${i + 1}",
                        preview = raw.field("caption")
                            ?: raw.field("full_narration")
                            ?: raw.field("hook")
                            ?: "",
                        raw = raw,
                    )
                }
                if (items.isEmpty()) {
                    _state.update { it.copy(step = ShortsStep.FAILED, busy = false, error = "The server returned no scripts. Try a different description.") }
                } else {
                    _state.update { it.copy(step = ShortsStep.SCRIPTS, busy = false, scripts = items, selectedScript = 0) }
                }
            } catch (e: Exception) {
                _state.update {
                    it.copy(
                        step = ShortsStep.FAILED,
                        busy = false,
                        error = (e as? ApiException)?.message ?: "Unexpected error: ${e.message}",
                    )
                }
            }
        }
    }

    /** Step 2: chosen script -> AI actor reel (fal.ai + ElevenLabs). */
    fun generate() {
        val s = _state.value
        val script = s.selectedScript?.let { s.scripts.getOrNull(it)?.raw } ?: run {
            _state.update { it.copy(error = "Pick a script first.") }
            return
        }
        _state.update { it.copy(step = ShortsStep.GENERATING, busy = true, error = null, logs = emptyList()) }
        viewModelScope.launch {
            try {
                val r = repo()
                val response = r.generate(
                    GenerateRequest(
                        script = script,
                        voice_id = s.voiceId.trim().ifBlank { null },
                        actor_description = s.actorDescription.trim().ifBlank { null },
                        video_mode = s.videoMode,
                        share_to_gallery = false,
                    )
                )
                val jobId = response.jobId ?: throw ApiException("Server did not return a job id.")
                r.recordJob(jobId, "shorts", s.scripts[s.selectedScript!!].title.take(60))
                _state.update { it.copy(jobId = jobId, status = "processing") }
                watch(jobId)
            } catch (e: Exception) {
                _state.update {
                    it.copy(
                        step = ShortsStep.FAILED,
                        busy = false,
                        error = (e as? ApiException)?.message ?: "Unexpected error: ${e.message}",
                    )
                }
            }
        }
    }

    /** Resume watching an existing AI Shorts job. */
    fun resume(jobId: String) {
        _state.update { it.copy(step = ShortsStep.GENERATING, jobId = jobId, status = "processing", error = null, logs = emptyList()) }
        watch(jobId)
    }

    private fun watch(jobId: String) {
        pollJob?.cancel()
        pollJob = viewModelScope.launch {
            while (true) {
                val r = repo()
                try {
                    val status = r.saasJobStatus(jobId)
                    _state.update {
                        it.copy(
                            status = status.status,
                            logs = status.logs ?: it.logs,
                            videoUrl = status.result?.videoUrl ?: it.videoUrl,
                            scriptSummary = status.result?.script?.field("title") ?: it.scriptSummary,
                            step = when (status.status) {
                                "completed" -> ShortsStep.DONE
                                "failed" -> ShortsStep.FAILED
                                else -> it.step
                            },
                            busy = false,
                        )
                    }
                    r.updateJobStatus(jobId, status.status ?: "unknown")
                    if (status.status == "completed" || status.status == "failed") {
                        if (status.status == "failed") {
                            _state.update { it.copy(error = "Generation failed — check the job log above.") }
                        }
                        break
                    }
                } catch (e: Exception) {
                    _state.update { it.copy(busy = false, error = "Status poll failed: ${e.message}") }
                    break
                }
                delay(10_000)
            }
        }
    }

    fun absoluteUrl(url: String?): String? = repo().absoluteUrl(url)

    fun publish(
        title: String?,
        description: String?,
        platforms: List<String>,
        scheduledDate: String?,
        timezone: String?,
    ) {
        val jobId = _state.value.jobId ?: run {
            _state.update { it.copy(publishMessage = "No video to publish.") }
            return
        }
        _state.update { it.copy(publishing = true, publishMessage = null) }
        viewModelScope.launch {
            try {
                val r = repo()
                val (upKey, upUser) = r.publishDefaults()
                val result = r.postSaasToSocial(
                    SaasPostRequest(
                        jobId = jobId,
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

    private fun JsonElement.field(name: String): String? =
        (this as? com.google.gson.JsonObject)?.get(name)?.takeIf { !it.isJsonNull }?.asString?.takeIf { it.isNotBlank() }
}
