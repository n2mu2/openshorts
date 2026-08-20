package com.openshorts.app.core.model

import com.google.gson.JsonElement
import com.google.gson.annotations.SerializedName

// ---------------------------------------------------------------- clip jobs

/** POST /api/process (JSON body). Either url OR a multipart file upload. */
data class ProcessRequest(
    val url: String? = null,
    val acknowledged: Boolean = true,
    val output_format: String? = null,          // "vertical" | "horizontal" | "square"
    val layouts: List<String>? = null,          // auto, split, screencast, speaker_cut, punch_in
    val target_clips: Int? = null,
    val clip_min_seconds: Int? = null,
    val clip_max_seconds: Int? = null,
    val auto_hook: Boolean? = null,
    val auto_hook_style: String? = null,
    val webhook_url: String? = null,
    val webhook_secret: String? = null,
)

data class JobSubmitResponse(
    @SerializedName("job_id") val jobId: String? = null,
    val status: String? = null,
)

/** GET /api/status/{job_id} and GET /api/saasshorts/status/{job_id} */
data class JobStatusResponse(
    val status: String? = null,
    val logs: List<String>? = null,
    val result: JobResult? = null,
)

data class JobResult(
    val clips: List<Clip>? = null,
    val cost_analysis: JsonElement? = null,
    // AI Shorts fields:
    @SerializedName("video_url") val videoUrl: String? = null,
    val script: JsonElement? = null,
)

data class Clip(
    val title: String? = null,
    @SerializedName("video_url") val videoUrl: String? = null,
    @SerializedName("video_title_for_youtube_short") val youtubeTitle: String? = null,
    val description: String? = null,
    val duration: Double? = null,
) {
    val displayTitle: String
        get() = title?.takeIf { it.isNotBlank() }
            ?: youtubeTitle?.takeIf { it.isNotBlank() }
            ?: "Clip"
}

// ---------------------------------------------------------------- AI shorts

/** POST /api/saasshorts/analyze */
data class AnalyzeRequest(
    val url: String? = null,
    val description: String? = null,
    val num_scripts: Int = 3,
    val style: String = "ugc",                  // ugc | educational | shock | story | comparison
    val language: String = "en",                // en | es
    val actor_gender: String = "female",        // female | male
)

data class AnalyzeResponse(
    val analysis: JsonElement? = null,
    val scripts: List<JsonElement>? = null,
    val web_research: JsonElement? = null,
)

/** POST /api/saasshorts/generate */
data class GenerateRequest(
    val script: JsonElement,
    val voice_id: String? = null,
    val actor_description: String? = null,
    val selected_actor_url: String? = null,
    val retry_job_id: String? = null,
    val video_mode: String = "lowcost",         // lowcost | premium
    val share_to_gallery: Boolean = false,
)

// ---------------------------------------------------------------- publishing

/** POST /api/social/post — publish one clip of a clip job. */
data class SocialPostRequest(
    @SerializedName("job_id") val jobId: String,
    @SerializedName("clip_index") val clipIndex: Int,
    @SerializedName("api_key") val apiKey: String? = null,
    @SerializedName("user_id") val userId: String? = null,
    val platforms: List<String>,                // tiktok | instagram | youtube
    val title: String? = null,
    val description: String? = null,
    @SerializedName("scheduled_date") val scheduledDate: String? = null, // ISO-8601
    val timezone: String? = "UTC",
)

/** POST /api/saasshorts/post — publish an AI Shorts video. */
data class SaasPostRequest(
    @SerializedName("job_id") val jobId: String,
    @SerializedName("api_key") val apiKey: String? = null,
    @SerializedName("user_id") val userId: String? = null,
    val platforms: List<String>,
    val title: String? = null,
    val description: String? = null,
    @SerializedName("scheduled_date") val scheduledDate: String? = null,
    val timezone: String? = "UTC",
)

/** GET /api/social/user — Upload-Post profiles and their connected networks. */
data class UploadPostProfilesResponse(
    val success: Boolean? = null,
    val profiles: List<UploadPostProfile>? = null,
    val detail: String? = null,
)

data class UploadPostProfile(
    val username: String? = null,
    val connected: List<String>? = null,
)

// ---------------------------------------------------------------- misc

data class HealthResponse(val status: String? = null)

data class ConfigResponse(
    @SerializedName("youtubeUrlEnabled") val youtubeUrlEnabled: Boolean? = null,
    @SerializedName("billingEnabled") val billingEnabled: Boolean? = null,
    @SerializedName("googleAuthEnabled") val googleAuthEnabled: Boolean? = null,
    @SerializedName("jobRetentionSeconds") val jobRetentionSeconds: Long? = null,
)

data class VoicesResponse(
    val voices: List<VoiceOption>? = null,
    val source: String? = null,
)

data class VoiceOption(
    @SerializedName("voice_id") val voiceId: String? = null,
    val name: String? = null,
    val category: String? = null,
)
