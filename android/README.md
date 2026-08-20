# OpenShorts — Android App

Native Android client for the [OpenShorts](https://github.com/n2mu2/openshorts) API.
Create trading/market reels from a **text prompt** (AI Shorts) or from **long videos**
(Clip Generator), then **publish to Instagram Reels** (plus TikTok / YouTube Shorts)
straight from the phone — through the same pipeline the web dashboard uses.

Built with Kotlin, Jetpack Compose (Material 3), Retrofit, ExoPlayer and DataStore.
No backend of its own: the app is a remote control for your OpenShorts server.

---

## What it does

| Screen | Feature |
|---|---|
| **Home** | Server + Instagram connectivity status, recent jobs, quick actions |
| **AI Shorts** | Prompt/URL → Gemini writes viral scripts → pick one → fal.ai + ElevenLabs generate the AI-actor reel → preview → publish |
| **Clips** | YouTube URL *or* a video picked from the phone → viral-moment detection → 9:16 clips with captions → preview → publish |
| **Social** | Upload-Post profiles, which platforms are connected (Instagram ✓/✗) |
| **Settings** | Server URL, hosted API key, BYOK keys (Gemini / fal.ai / ElevenLabs / Upload-Post), connection test |

Both flows let you **schedule** the post (date, time, IANA timezone) or publish
immediately. Jobs keep running on the server if you close the app; reopening a
job from Home resumes the live status polling.

---

## Architecture

```
app/src/main/java/com/openshorts/app/
├── core/
│   ├── network/OpenShortsApi.kt      Retrofit interface — 1:1 mirror of the REST API
│   ├── network/ApiFactory.kt         OkHttp + bearer token interceptor
│   ├── model/Models.kt               Gson DTOs (requests & responses)
│   └── prefs/SettingsStore.kt        DataStore (settings + job history)
├── data/OpenShortsRepository.kt      business logic, error mapping, file upload
└── ui/
    ├── nav/AppNav.kt                 bottom nav (Home / AI Shorts / Clips / Social / Settings)
    ├── home/ shorts/ clips/ social/ settings/   one screen + ViewModel each
    ├── publish/PublishSheet.kt       shared platform/caption/schedule sheet
    └── components/                   shared cards, chips, log tail, ExoPlayer wrapper
```

### API endpoints used (verified against the backend source)

| Action | Endpoint |
|---|---|
| Submit clip job (URL) | `POST /api/process` (JSON: `url`, `acknowledged`, `layouts`, `target_clips`, …) |
| Submit clip job (file) | `POST /api/process` (multipart `file` + form fields) |
| Clip job status | `GET /api/status/{job_id}` → `{status, logs, result.clips[]}` |
| AI scripts | `POST /api/saasshorts/analyze` `{description|url, num_scripts, style, language, actor_gender}` |
| Generate AI reel | `POST /api/saasshorts/generate` `{script, voice_id, actor_description, video_mode}` + `X-Fal-Key`, `X-ElevenLabs-Key` headers |
| AI reel status | `GET /api/saasshorts/status/{job_id}` |
| Publish a clip | `POST /api/social/post` `{job_id, clip_index, platforms[], title, description, scheduled_date, timezone}` |
| Publish an AI reel | `POST /api/saasshorts/post` (same minus `clip_index`) |
| Social accounts | `GET /api/social/user` (profiles + connected platforms) |
| Health / config | `GET /health`, `GET /api/config` |

**Auth model**
- *Hosted* (`openshorts.app`): only the `osk_...` API key → sent as `Authorization: Bearer`.
- *Self-hosted*: no auth header; BYOK keys travel as `X-Gemini-Key` / `X-Fal-Key` /
  `X-ElevenLabs-Key` headers, and the Upload-Post key + profile go in the publish body
  (ignored server-side when hosted).

---

## Build it

Requirements: **Android Studio** (Koala or newer) or JDK 17 + Android SDK 34.

```bash
cd android
./gradlew :app:assembleDebug
# APK: app/build/outputs/apk/debug/app-debug.apk
```

Or open the `android/` folder in Android Studio and press Run.

- minSdk 26 (Android 8.0), targetSdk 34
- Kotlin 2.0.21 · AGP 8.5.2 · Gradle 8.7 · Compose BOM 2024.09.03 · Media3 1.4.1

CI builds the app on every push (`.github/workflows/android.yml`).

---

## Point it at your server

1. **Hosted cloud** — Settings → Server URL `https://api.openshorts.app`, paste your
   `osk_...` API key (created in your account page). Everything else is managed
   server-side. AI Shorts needs a paid plan; clip generation works on the free tier.
2. **Self-hosted** — Settings → Server URL to your machine, e.g.
   `http://192.168.1.10:8000` (LAN IP, port 8000 — the FastAPI backend; the Vite
   dashboard on 5175 is only the web UI). Leave the API key blank and fill the BYOK
   keys. Note: the app allows cleartext `http://` exactly for this LAN case.

### Instagram posting

Publishing goes **through OpenShorts → Upload-Post** — the same path the dashboard
uses. In Upload-Post, connect an Instagram **Business/Creator** account and copy:

- the Upload-Post **API key** → Settings → *Upload-Post API key*
- the profile **username** → Settings → *Upload-Post profile*

Then use *Social* → verify, or Settings → *Test connection* — you should see
`Instagram connected ✓`. The free Upload-Post tier covers 10 posts/month.

### Cost reality check (self-hosted)

- Clip Generator: ~free (Gemini free tier; CPU render time 5–8 min per video).
- AI Shorts: fal.ai pay-per-use — lowcost ~$0.65/video, premium ~$2/video
  (+ ElevenLabs free tier for the voiceover).

---

## Security notes

- API keys live in the app-private DataStore (no logs, no backups).
- Self-hosted instances are usually **unauthenticated** — do not expose port 8000
  to the public internet; LAN or VPN only.
- Production hardening ideas: Keystore-backed encryption for keys, certificate
  pinning, and an API-gateway auth layer in front of the self-hosted server.
- Financial content compliance: review every AI-written reel before publishing;
  TikTok/IG/YouTube restrict investment advice, and SEBI rules apply in India.

---

## License

MIT — same as the OpenShorts platform. See the repository `LICENSE`.
