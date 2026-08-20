package com.openshorts.app.core.prefs

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStoreFile
import androidx.datastore.preferences.core.PreferenceDataStoreFactory
import com.google.gson.Gson
import com.google.gson.reflect.TypeToken
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.catch
import kotlinx.coroutines.flow.firstOrNull
import kotlinx.coroutines.flow.map
import java.io.IOException

/**
 * All connection settings the app needs to drive an OpenShorts instance.
 *
 * Hosted cloud (openshorts.app): only [apiKey] is required (osk_...).
 * Self-hosted: leave [apiKey] blank and fill the BYOK fields instead —
 *   [geminiKey]        -> X-Gemini-Key header (clip generation + scripts)
 *   [falKey]           -> X-Fal-Key header (AI Shorts actor/video generation)
 *   [elevenLabsKey]    -> X-ElevenLabs-Key header (voiceovers)
 *   [uploadPostKey]    -> Upload-Post API key (Instagram/TikTok/YouTube posting)
 *   [uploadPostUser]   -> Upload-Post profile username to post as
 */
data class AppSettings(
    val serverUrl: String = DEFAULT_SERVER,
    val apiKey: String = "",
    val geminiKey: String = "",
    val falKey: String = "",
    val elevenLabsKey: String = "",
    val uploadPostKey: String = "",
    val uploadPostUser: String = "",
) {
    companion object {
        const val DEFAULT_SERVER = "https://api.openshorts.app"
    }

    val isHosted: Boolean get() = apiKey.isNotBlank()
}

/** A locally remembered job so the user can resume watching its status. */
data class StoredJob(
    val id: String,
    val kind: String,          // "clips" | "shorts"
    val label: String,
    val createdAt: Long,
    val lastStatus: String? = null,
)

object SettingsStore {

    private const val FILE = "openshorts"

    private val KEY_SERVER = stringPreferencesKey("server_url")
    private val KEY_API = stringPreferencesKey("api_key")
    private val KEY_GEMINI = stringPreferencesKey("gemini_key")
    private val KEY_FAL = stringPreferencesKey("fal_key")
    private val KEY_ELEVEN = stringPreferencesKey("eleven_key")
    private val KEY_UP = stringPreferencesKey("uploadpost_key")
    private val KEY_UP_USER = stringPreferencesKey("uploadpost_user")
    private val KEY_JOBS = stringPreferencesKey("jobs_json")

    @Volatile
    private var store: DataStore<Preferences>? = null

    private val gson = Gson()

    fun init(context: Context) {
        if (store == null) {
            synchronized(this) {
                if (store == null) {
                    store = PreferenceDataStoreFactory.create(
                        produceFile = { context.applicationContext.preferencesDataStoreFile(FILE) }
                    )
                }
            }
        }
    }

    private fun ds(): DataStore<Preferences> = checkNotNull(store) {
        "SettingsStore.init() must be called in Application.onCreate()"
    }

    private val prefs: Flow<Preferences> = ds().data.catch { e ->
        if (e is IOException) emit(androidx.datastore.preferences.core.emptyPreferences())
        else throw e
    }

    val settings: Flow<AppSettings> = prefs.map { p ->
        AppSettings(
            serverUrl = p[KEY_SERVER] ?: AppSettings.DEFAULT_SERVER,
            apiKey = p[KEY_API] ?: "",
            geminiKey = p[KEY_GEMINI] ?: "",
            falKey = p[KEY_FAL] ?: "",
            elevenLabsKey = p[KEY_ELEVEN] ?: "",
            uploadPostKey = p[KEY_UP] ?: "",
            uploadPostUser = p[KEY_UP_USER] ?: "",
        )
    }

    suspend fun save(settings: AppSettings) {
        ds().edit { p ->
            p[KEY_SERVER] = settings.serverUrl.trim().ifBlank { AppSettings.DEFAULT_SERVER }
            p[KEY_API] = settings.apiKey.trim()
            p[KEY_GEMINI] = settings.geminiKey.trim()
            p[KEY_FAL] = settings.falKey.trim()
            p[KEY_ELEVEN] = settings.elevenLabsKey.trim()
            p[KEY_UP] = settings.uploadPostKey.trim()
            p[KEY_UP_USER] = settings.uploadPostUser.trim()
        }
    }

    // ------------------------------------------------------------------ jobs

    val jobs: Flow<List<StoredJob>> = prefs.map { p ->
        val raw = p[KEY_JOBS] ?: "[]"
        runCatching {
            val type = object : TypeToken<List<StoredJob>>() {}.type
            gson.fromJson<List<StoredJob>>(raw, type) ?: emptyList()
        }.getOrDefault(emptyList())
    }

    /** Upsert a job (newest first, capped at 100). */
    suspend fun recordJob(job: StoredJob) {
        val list = jobs.firstOrNull().orEmpty()
        val updated = listOf(job) + list.filterNot { it.id == job.id }
        ds().edit { p -> p[KEY_JOBS] = gson.toJson(updated.take(100)) }
    }

    suspend fun updateJobStatus(id: String, status: String) {
        val list = jobs.firstOrNull().orEmpty()
        val updated = list.map { if (it.id == id) it.copy(lastStatus = status) else it }
        ds().edit { p -> p[KEY_JOBS] = gson.toJson(updated) }
    }

    suspend fun clearJobs() {
        ds().edit { p -> p[KEY_JOBS] = "[]" }
    }

    suspend fun firstOrNull(): List<StoredJob>? = jobs.firstOrNull()
}
