# 🤖 OpenShorts Reels Bot — verified, bilingual, news-aware finance reels for Instagram

A cron-driven pipeline that runs in **GitHub Actions**: every day it picks the
next reel — the **latest market news** (sarkarikyp.com, Google News, Moneycontrol,
ET, Livemint…) or an **evergreen topic** from the expert-curated bank — writes a
**bilingual Hindi↔English script**, passes it through a **mandatory Gemini
verification gate** (fact-check + legal/compliance), generates the AI-actor reel
through OpenShorts, and publishes it to **Instagram Reels** (optionally TikTok /
YouTube Shorts too). **Nothing is ever posted without Gemini verification.**
State and logs are committed back to this repo, so every decision — including
rejections — is auditable in git.

```
GitHub cron (08:30 & 19:00 IST)
        │
        ├─ NEWS (slot 1): sarkarikyp.com · Google News · Moneycontrol · ET · Livemint
        └─ BANK (slot 2): automation/content/topics.json (10 topics × 1,000 reels)
        │
        ▼
automation/reels_bot.py
        │
        ├─ 1. Gemini WRITES the script  (bilingual: Hindi⇄English flip mid-reel,
        │      every segment carries subtitle_text in the OPPOSITE language)
        ├─ 2. Gemini VERIFIES the script (correctness + authenticity + compliance)
        │      → approve: continue · fix: correct & re-verify · reject: NEVER post
        ├─ 3. OpenShorts generates (fal.ai actor + ElevenLabs multilingual voice)
        └─ 4. Publish to Instagram via Upload-Post
        │
        ▼
state/state.json + state/log.jsonl committed back to the repo
```

---

## 1. One-time setup (you only need to add secrets)

Go to **repo → Settings → Secrets and variables → Actions** and add:

| Secret name | Required | What it is / where to get it |
|---|---|---|
| `GEMINI_API_KEY` | **Yes — all modes** | Free key from [aistudio.google.com](https://aistudio.google.com/app/apikey). The bot uses Gemini directly to **write AND verify every script** — it refuses to run without it. |
| `OPENSHORTS_API_KEY` | Hosted mode | `osk_...` key from your [openshorts.app](https://openshorts.app) account page. Needs a **paid plan** for AI Shorts. Leave blank if self-hosting. |
| `FAL_API_KEY` | **Yes** | [fal.ai](https://fal.ai) dashboard key — powers the AI actor/video. ~$0.65 per reel in `lowcost` mode. |
| `ELEVENLABS_API_KEY` | **Yes** | [elevenlabs.io](https://elevenlabs.io) key — the voiceover. Free tier is enough. |
| `UPLOAD_POST_API_KEY` | Self-host only | [upload-post.com](https://upload-post.com) API key — **this is your "Instagram access"**: Instagram is connected inside Upload-Post. On hosted paid plans the server manages this. |
| `UPLOAD_POST_USER` | Self-host only | Your Upload-Post profile username that has Instagram connected. |

Optional **Variables** (repo → Settings → Variables → Actions):

| Variable | Default | Meaning |
|---|---|---|
| `PLATFORMS` | `instagram` | Comma list: `instagram,tiktok,youtube` |
| `POSTS_PER_DAY` | `1` | `1` = morning only, `2` = morning + evening |
| `MAX_MONTHLY_POSTS` | `30` | Budget cap. **Set `10` if you are on Upload-Post's free tier.** |
| `NEWS_ENABLED` | `true` | Whether the news slot runs |
| `NEWS_SLOT` | `1` | Which slot posts news (1=morning, 2=evening, 0=never) |
| `BILINGUAL` | `true` | Hindi⇄English flip reels (see below) |
| `BILINGUAL_VOICE_ID` | `9BWtsMINqrJLrRacOk9x` | ElevenLabs voice for bilingual reels (default: "Sarah", multilingual v2 — Hindi-capable, usable on any account) |
| `GEMINI_MODEL` | `gemini-2.5-flash` | Any Gemini model that supports JSON output |
| `OPENSHORTS_API_URL` | `https://api.openshorts.app` | Point at your self-hosted instance instead, e.g. `http://your-server:8000` |

### The "Instagram credentials" question

The app/bot never logs into Instagram directly — publishing goes through
**Upload-Post** (the same path the OpenShorts dashboard uses), which is the
only route that stays within Instagram's rules for API posting:

1. Create an account at [upload-post.com](https://upload-post.com).
2. Connect your **Instagram Business or Creator account** there (their OAuth).
3. Grab the **API key** and your **profile username** → put them in the
   secrets above (self-host) — or, on the hosted openshorts.app paid plan,
   connect the account once in the OpenShorts dashboard and skip both secrets.

---

## 2. The Gemini verification gate (every reel, no exceptions)

Before anything reaches the OpenShorts generation API, the freshly written
script goes through a mandatory audit. Gemini checks:

1. **Facts** — every numeric/factual claim must be in the ground-truth text
   (the news source text, or the content bank's fact sheet) or universally
   known public financial knowledge. Invented numbers = reject.
2. **Legal / compliance** — no buy/sell/hold advice, no stock names as picks,
   no price targets, no guaranteed/promised returns, no "sure-shot" claims,
   no solicitation of funds (SEBI finfluencer norms).
3. **Good faith** — no fear-mongering, no defamation, no misleading urgency,
   no plagiarised verbatim article text, honest tone.
4. **Bilingual fidelity** — each segment is genuinely in its assigned
   language, and every subtitle is a faithful translation (no meaning drift).
5. **Schema** — 5 valid segments with b-roll prompts and sane timings.

Verdicts: **approve** → publish · **fix** → Gemini's corrected script is
re-verified (max 2 attempts) · **reject** → the reel is **never posted**,
recorded in state with the reason. If Gemini itself is unreachable, the run
**fails loudly** — a broken gate means no posting, ever.

Reels are always made in **good faith**: educational framing, verified facts,
attributed news, mandatory bilingual disclaimer on every caption.

---

## 3. Bilingual reels (Hindi ⇄ English flip)

Default behaviour: the reel **randomly starts in Hindi or English** and, halfway
through, **flips to the other language** — while the on-screen subtitles always
run in the **opposite language** of the speech (English speech → Hindi
subtitles, Hindi speech → English subtitles).

- Spoken part: ElevenLabs `eleven_multilingual_v2` with the default voice
  **Sarah** (`9BWtsMINqrJLrRacOk9x`) — a premade multilingual voice that speaks
  Hindi + English naturally and works on every account. Override with
  `BILINGUAL_VOICE_ID` if you prefer a different multilingual voice.
- Subtitles: this **fork's `saasshorts.py` patch** supports
  `use_script_subtitles=true`, burning the script's per-segment
  `subtitle_text` (with DejaVu Sans, which renders Devanagari + Latin).
  → **Self-hosting from this fork gives the full cross-language experience.**
  → On the hosted cloud (upstream code), the flag is ignored gracefully and
    subtitles follow the spoken language of each half — speech is still
    fully bilingual.
- `BILINGUAL=false` switches to plain English reels (subtitles via the
  server's normal Whisper path).

---

## 4. News reels (latest news, attributed)

The **morning slot (08:30 IST)** posts a reel built from the freshest
market-relevant story across these sources (editable in
`automation/content/news_sources.json`):

| Source | What it catches |
|---|---|
| **Sarkari KYP** (`sarkarikyp.com/feed/`) | Hindi govt schemes, yojana, subsidy, pension, EPF/PPF updates |
| **Google News — Indian Markets** | NIFTY/SENSEX/stock-market headlines, 1 day |
| **Google News — Economy & Policy** | RBI, SEBI, Budget, inflation, GST |
| **Google News — Hindi Markets** | Hindi stock-market headlines |
| **Google News — Schemes & Subsidies** | Yojana/subsidy/pension (Hindi) |
| **Moneycontrol / Economic Times / Livemint** | Market wraps & macro |

Rules baked in: the script may **only use facts present in the source text**
(the verifier enforces this), the reel **attributes the source** ("news reports
say" / "khabaron ke mutabik"), the caption carries the source name + link, and
no invented numbers are allowed. Stories already used are never repeated
(tracked in state). If no fresh story matches, the bot falls back to the
evergreen bank instead of stalling.

---

## 5. Schedule

| Cron (UTC) | IST | Slot |
|---|---|---|
| `0 3 * * *` | 08:30 | Morning — **news reel** (fresh headlines) |
| `30 13 * * *` | 19:00 | Evening — **evergreen bank reel** (active when `POSTS_PER_DAY=2`) |

Notes:
- GitHub scheduled runs are **best-effort** — usually on time, occasionally
  delayed ~15–60 min under load. For hard-exact timing, run `automation/run.sh`
  from a server cron instead (`.env` file, git-ignored).
- Scheduled workflows are paused after 60 days of repo inactivity — the bot's
  own state commits keep the repo active.
- Manual runs: **Actions → Reels Bot → Run workflow** (dry-run / slot / force).

### Alternative: your own server cron

```cron
30 8  * * *  cd /path/to/openshorts/automation && ./run.sh >> /var/log/reels-bot.log 2>&1
0 19  * * *  cd /path/to/openshorts/automation && ./run.sh >> /var/log/reels-bot.log 2>&1
```

---

## 6. Costs (self-check before you switch it on)

| Item | Approx. | Notes |
|---|---|---|
| OpenShorts hosted plan | $12+/mo | Paid tier unlocks AI Shorts + API keys + managed Upload-Post |
| fal.ai generation | **~$0.65/reel** (`lowcost`) | The real per-post cost. 1/day ≈ $20/mo. `premium` ≈ $2/reel. |
| ElevenLabs | Free tier | Enough for 1–2 reels/day; Sarah multilingual voice is a free premade voice |
| Google Gemini | Free tier | Script writing + verification ≈ 2 calls per reel; free tier covers ~1,000+ reels/day of this volume |
| Upload-Post | Free 10 posts/mo → paid tiers | Set `MAX_MONTHLY_POSTS=10` if staying free |
| GitHub Actions | Free tier is plenty | ~15 min/run, 30–60 runs/mo |

Dry-run is free: **Actions → Reels Bot → Run workflow → dry_run = true** prints
the exact plan (news item, language order, brief, caption) without any API spend.

---

## 7. Guardrails & compliance

- **Education only**: no stock names, no buy/sell/hold calls, no price targets,
  no profit promises — enforced by both the prompt and the verification gate.
- **Verified facts**: news scripts may only use source facts; bank scripts may
  only use the fact sheet (SEBI trader-loss studies, SIP maths, LTCG rules…).
- **Attribution**: every news caption names the source with a link.
- **Bilingual disclaimer** on every post.
- **Audit trail**: every run commits its decision + result + verification
  verdict to `automation/state/`.
- **Fails loudly**: any API or verification failure exits non-zero → the
  Actions run turns red (enable watch notifications on the repo if you want
  emails).
- Recommendation: check the first 2–3 posted reels after enabling, then let it
  fly on autopilot.

## 8. Local testing

```bash
# plan only (no API calls, no keys)
python3 automation/reels_bot.py --dry-run --date 2026-08-22 --slot 1

# full pipeline against a fake server (no keys, no cost) — includes
# mock Gemini (script + verification) and a mock news feed:
python3 automation/mock_server.py 8099 &
OPENSHORTS_API_URL=http://127.0.0.1:8099 GEMINI_API_URL=http://127.0.0.1:8099 \
GEMINI_API_KEY=test FAL_API_KEY=x ELEVENLABS_API_KEY=x \
NEWS_SOURCE_URLS=http://127.0.0.1:8099/news/rss.xml \
POSTS_PER_DAY=2 python3 automation/reels_bot.py --slot 1 --force
```

## 9. Troubleshooting

| Symptom | Likely cause |
|---|---|
| Run red, `GEMINI_API_KEY is missing` | The gate is mandatory — add the secret. Nothing will post without it. |
| Run red, `HTTP 402` | Hosted plan quota/minutes exhausted → top up or lower `POSTS_PER_DAY` |
| Run red, `Missing fal.ai API Key` | `FAL_API_KEY` secret missing |
| Post fails, `Missing Upload-Post API key` | Self-hosted: add `UPLOAD_POST_API_KEY` + `UPLOAD_POST_USER`; or IG not connected in Upload-Post |
| "verification: REJECTED" in log | The gate caught an unsafe/unfactual script — check `state/log.jsonl` for the issues, then let the next slot run |
| Hindi subtitles missing (self-host) | You're not running this fork's image, or the container predates the `saasshorts.py` patch — rebuild with `docker compose up --build` |
| Hindi voice sounds off | Try another multilingual voice via `BILINGUAL_VOICE_ID` (list yours at ElevenLabs → Voices) |
| "slot is disabled" every evening | `POSTS_PER_DAY` is `1` — expected |
| "monthly budget reached" | `MAX_MONTHLY_POSTS` cap — expected; raise it (and check Upload-Post tier) |
| Nothing runs at all | Check the workflow is on the **default branch** and Actions is enabled |
