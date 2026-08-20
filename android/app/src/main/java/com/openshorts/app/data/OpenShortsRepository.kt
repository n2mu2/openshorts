package com.openshorts.app.data

import android.content.ContentResolver
import android.content.Context
import android.net.Uri
import android.provider.OpenableColumns
import com.openshorts.app.core.model.AnalyzeRequest
import com.openshorts.app.core.model.AnalyzeResponse
import com.openshorts.app.core.model.Clip
import com.openshorts.app.core.model.ConfigResponse
import com.openshorts.app.core.model.GenerateRequest
import com.openshorts.app.core.model.JobStatusResponse
import com.openshorts.app.core.model.JobSubmitResponse
import com.openshorts.app.core.model.ProcessRequest
import com.openshorts.app.core.model.SaasPostRequest
import com.openshorts.app.core.model.SocialPostRequest
import com.openshorts.app.core.model.UploadPostProfilesResponse
import com.openshorts.app.core.model.VoicesResponse
import com.openshorts.app.core.network.ApiFactory
import com.openshorts.app.core.network.OpenShortsApi
import com.openshorts.app.core.prefs.AppSettings
import com.openshorts.app.core.prefs.SettingsStore
import com.openshorts.app.core.prefs.StoredJob
import com.google.gson.JsonElement
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.RequestBody
import okhttp3.RequestBody.Companion.toRequestBody
import okio.BufferedSink
import java.io.IOException

/** Thrown when the server answered with a 4xx/5xx or the request failed. */
class ApiException(message: String, val code: Int? = null) : Exception(message)

class OpenShortsRepository(private val settings: AppSettings) {

    private val api: OpenShortsApi = ApiFactory.api(settings)

    private fun nullIfBlank(s: String?): String? = s?.takeIf { it.isNotBlank() }

    private fun geminiHeader(): String? = nullIfBlank(settings.geminiKey)

    // ---------------------------------------------------------------- health
    suspend fun health(): Boolean = runCatching { api.health().status == "ok" }.getOrDefault(false)

    suspend fun config(): ConfigResponse = wrap { api.config() }

    // ------------------------------------------------------------- clip jobs
    suspend fun submitUrl(request: ProcessRequest): JobSubmitResponse =
        wrap { api.processUrl(request, geminiHeader()) }

    suspend fun submitFile(context: Context, uri: Uri, request: ProcessRequest): JobSubmitResponse {
        val resolver = context.contentResolver
        val name = resolver.queryName(uri) ?: "upload.mp4"
        val type = resolver.getType(uri) ?: "video/mp4"
        val body = object : RequestBody() {
            override fun contentType() = type.toMediaTypeOrNull()
            override fun contentLength(): Long {
                var size = 0L
                resolver.query(uri, arrayOf(OpenableColumns.SIZE), null, null, null)?.use { c ->
                    if (c.moveToFirst()) size = c.getLong(0)
                }
                return if (size > 0) size else -1
            }

            override fun writeTo(sink: BufferedSink) {
                resolver.openInputStream(uri)?.use { input ->
                    val buffer = ByteArray(64 * 1024)
                    var read = input.read(buffer)
                    while (read != -1) {
                        sink.write(buffer, 0, read)
                        read = input.read(buffer)
                    }
                }
            }
        }
        val filePart = MultipartBody.Part.createFormData("file", name, body)
        return wrap {
            api.processFile(
                file = filePart,
                acknowledged = "true".toRequestBody("text/plain".toMediaTypeOrNull()),
                outputFormat = nullIfBlank(request.output_format)?.toRequestBody("text/plain".toMediaTypeOrNull()),
                layouts = request.layouts?.joinToString(",")?.takeIf { it.isNotBlank() }?.toRequestBody("text/plain".toMediaTypeOrNull()),
                targetClips = request.target_clips?.toString()?.toRequestBody("text/plain".toMediaTypeOrNull()),
                clipMinSeconds = request.clip_min_seconds?.toString()?.toRequestBody("text/plain".toMediaTypeOrNull()),
                clipMaxSeconds = request.clip_max_seconds?.toString()?.toRequestBody("text/plain".toMediaTypeOrNull()),
                autoHook = request.auto_hook?.toString()?.toRequestBody("text/plain".toMediaTypeOrNull()),
                geminiKey = geminiHeader(),
            )
        }
    }

    suspend fun jobStatus(jobId: String): JobStatusResponse = wrap { api.jobStatus(jobId) }

    suspend fun postClipToSocial(body: SocialPostRequest): JsonElement = wrap { api.postClipToSocial(body) }

    // ------------------------------------------------------------- AI shorts
    suspend fun analyze(request: AnalyzeRequest): AnalyzeResponse =
        wrap { api.analyze(request, geminiHeader()) }

    suspend fun generate(request: GenerateRequest): JobSubmitResponse =
        wrap { api.generate(request, nullIfBlank(settings.falKey), nullIfBlank(settings.elevenLabsKey)) }

    suspend fun saasJobStatus(jobId: String): JobStatusResponse =
        wrap { api.saasJobStatus(jobId) }

    suspend fun voices(): VoicesResponse = wrap { api.voices(nullIfBlank(settings.elevenLabsKey)) }

    suspend fun postSaasToSocial(body: SaasPostRequest): JsonElement = wrap { api.postSaasToSocial(body) }

    // ---------------------------------------------------------------- social
    suspend fun socialProfiles(): UploadPostProfilesResponse =
        wrap { api.socialUser(nullIfBlank(settings.uploadPostKey)) }

    // ------------------------------------------------------------------ util
    fun absoluteUrl(url: String?): String? = ApiFactory.absoluteUrl(settings, url)

    fun clipAbsoluteUrl(clip: Clip): String? = absoluteUrl(clip.videoUrl)

    suspend fun recordJob(id: String, kind: String, label: String) {
        SettingsStore.recordJob(
            StoredJob(id = id, kind = kind, label = label, createdAt = System.currentTimeMillis())
        )
    }

    suspend fun updateJobStatus(id: String, status: String) {
        SettingsStore.updateJobStatus(id, status)
    }

    /** Fill BYOK fields in publish bodies (ignored server-side for hosted). */
    fun publishDefaults(): Pair<String?, String?> =
        nullIfBlank(settings.uploadPostKey) to nullIfBlank(settings.uploadPostUser)

    // -------------------------------------------------------------- errors
    private suspend inline fun <T> wrap(crossinline block: suspend () -> T): T = try {
        block()
    } catch (e: IOException) {
        throw ApiException(
            "Could not reach ${settings.serverUrl}. Check the server URL in Settings " +
                "and that your OpenShorts instance is running. (${e.message})"
        )
    } catch (e: retrofit2.HttpException) {
        val msg = try {
            val body = e.response()?.errorBody()?.string()
            if (!body.isNullOrBlank()) {
                val detail = runCatching {
                    com.google.gson.JsonParser.parseString(body)
                        .asJsonObject.get("detail")?.asString
                }.getOrNull()
                detail ?: body.take(300)
            } else null
        } catch (_: Exception) {
            null
        }
        throw ApiException(
            msg ?: humanHttpMessage(e.code()),
            e.code(),
        )
    }

    private fun humanHttpMessage(code: Int): String = when (code) {
        401 -> "Unauthorized — check your API key in Settings."
        402 -> "This feature needs a paid plan on the hosted cloud, or self-host with your own keys."
        404 -> "Not found on the server."
        413 -> "File too large for the server."
        429 -> "Rate limited — slow down and retry shortly."
        else -> "Server error (HTTP $code)."
    }

    private fun ContentResolver.queryName(uri: Uri): String? {
        query(uri, arrayOf(OpenableColumns.DISPLAY_NAME), null, null, null)?.use { c ->
            if (c.moveToFirst()) return c.getString(0)
        }
        return null
    }
}
