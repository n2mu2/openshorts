package com.openshorts.app.core.network

import com.google.gson.JsonElement
import com.openshorts.app.core.model.AnalyzeRequest
import com.openshorts.app.core.model.AnalyzeResponse
import com.openshorts.app.core.model.ConfigResponse
import com.openshorts.app.core.model.GenerateRequest
import com.openshorts.app.core.model.HealthResponse
import com.openshorts.app.core.model.JobStatusResponse
import com.openshorts.app.core.model.JobSubmitResponse
import com.openshorts.app.core.model.ProcessRequest
import com.openshorts.app.core.model.SaasPostRequest
import com.openshorts.app.core.model.SocialPostRequest
import com.openshorts.app.core.model.UploadPostProfilesResponse
import com.openshorts.app.core.model.VoicesResponse
import okhttp3.MultipartBody
import okhttp3.RequestBody
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.Header
import retrofit2.http.Multipart
import retrofit2.http.POST
import retrofit2.http.Part
import retrofit2.http.Path

/**
 * Retrofit mirror of the OpenShorts REST API.
 *
 * Auth model:
 *  - Hosted (openshorts.app): the OkHttp interceptor adds
 *    `Authorization: Bearer osk_...`; BYOK headers are ignored server-side.
 *  - Self-hosted: no auth header; BYOK keys travel in the X-* headers
 *    (Gemini / fal.ai / ElevenLabs) and the Upload-Post key goes in the
 *    publish request body.
 */
interface OpenShortsApi {

    // ------------------------------------------------------------ liveness
    @GET("health")
    suspend fun health(): HealthResponse

    @GET("api/config")
    suspend fun config(): ConfigResponse

    // -------------------------------------------------------- clip generator
    @POST("api/process")
    suspend fun processUrl(
        @Body body: ProcessRequest,
        @Header("X-Gemini-Key") geminiKey: String?,
    ): JobSubmitResponse

    @Multipart
    @POST("api/process")
    suspend fun processFile(
        @Part file: MultipartBody.Part,
        @Part("acknowledged") acknowledged: RequestBody,
        @Part("output_format") outputFormat: RequestBody?,
        @Part("layouts") layouts: RequestBody?,
        @Part("target_clips") targetClips: RequestBody?,
        @Part("clip_min_seconds") clipMinSeconds: RequestBody?,
        @Part("clip_max_seconds") clipMaxSeconds: RequestBody?,
        @Part("auto_hook") autoHook: RequestBody?,
        @Header("X-Gemini-Key") geminiKey: String?,
    ): JobSubmitResponse

    @GET("api/status/{jobId}")
    suspend fun jobStatus(@Path("jobId") jobId: String): JobStatusResponse

    @POST("api/social/post")
    suspend fun postClipToSocial(@Body body: SocialPostRequest): JsonElement

    // ------------------------------------------------------------- AI shorts
    @POST("api/saasshorts/analyze")
    suspend fun analyze(
        @Body body: AnalyzeRequest,
        @Header("X-Gemini-Key") geminiKey: String?,
    ): AnalyzeResponse

    @POST("api/saasshorts/generate")
    suspend fun generate(
        @Body body: GenerateRequest,
        @Header("X-Fal-Key") falKey: String?,
        @Header("X-ElevenLabs-Key") elevenLabsKey: String?,
    ): JobSubmitResponse

    @GET("api/saasshorts/status/{jobId}")
    suspend fun saasJobStatus(@Path("jobId") jobId: String): JobStatusResponse

    @GET("api/saasshorts/voices")
    suspend fun voices(
        @Header("X-ElevenLabs-Key") elevenLabsKey: String?,
    ): VoicesResponse

    @POST("api/saasshorts/post")
    suspend fun postSaasToSocial(@Body body: SaasPostRequest): JsonElement

    // ---------------------------------------------------------------- social
    @GET("api/social/user")
    suspend fun socialUser(
        @Header("X-Upload-Post-Key") uploadPostKey: String?,
    ): UploadPostProfilesResponse
}
