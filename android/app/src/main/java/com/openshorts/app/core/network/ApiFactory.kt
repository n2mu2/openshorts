package com.openshorts.app.core.network

import com.openshorts.app.core.prefs.AppSettings
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.util.concurrent.TimeUnit

/**
 * Builds a Retrofit client for a given settings snapshot.
 *
 * The client is rebuilt when the settings change (cheap and stateless);
 * ViewModels fetch the current settings per operation, so an edited server
 * URL or API key takes effect on the next call without an app restart.
 */
object ApiFactory {

    @Volatile
    private var cached: Pair<AppSettings, OpenShortsApi>? = null

    fun api(settings: AppSettings): OpenShortsApi {
        cached?.let { (cachedSettings, api) ->
            if (cachedSettings == settings) return api
        }
        val client = OkHttpClient.Builder()
            .connectTimeout(30, TimeUnit.SECONDS)
            .readTimeout(30, TimeUnit.SECONDS)
            .writeTimeout(30, TimeUnit.MINUTES) // big video uploads
            .callTimeout(35, TimeUnit.MINUTES)
            .addInterceptor { chain ->
                val request = chain.request().newBuilder()
                if (settings.apiKey.isNotBlank()) {
                    request.header("Authorization", "Bearer ${settings.apiKey}")
                }
                chain.proceed(request.build())
            }
            .addInterceptor(
                HttpLoggingInterceptor().apply {
                    level = HttpLoggingInterceptor.Level.BASIC
                }
            )
            .build()

        val baseUrl = settings.serverUrl.trim()
            .ifBlank { AppSettings.DEFAULT_SERVER }
            .let { if (it.endsWith("/")) it else "$it/" }

        val retrofit = Retrofit.Builder()
            .baseUrl(baseUrl)
            .client(client)
            .addConverterFactory(GsonConverterFactory.create())
            .build()

        val api = retrofit.create(OpenShortsApi::class.java)
        cached = settings to api
        return api
    }

    /** Turns a possibly-relative server URL (/videos/...) into an absolute one. */
    fun absoluteUrl(settings: AppSettings, url: String?): String? {
        if (url.isNullOrBlank()) return null
        if (url.startsWith("http://") || url.startsWith("https://")) return url
        val base = settings.serverUrl.trim().ifBlank { AppSettings.DEFAULT_SERVER }.trimEnd('/')
        return "$base${if (url.startsWith("/")) url else "/$url"}"
    }
}
