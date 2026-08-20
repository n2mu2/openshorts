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
GitHub cron — 6 slots/day, every 4 hours (08:30 · 12:30 · 16:30 · 20:30 · 00:30 · 04:30 IST)
        │
        ├─ SLOT 1 (08:30 IST): WORLD-NEWS MORNING BRIEF — overnight US/Asia/oil/gold/dollar
        │      + domestic stories → unique bullet points, each mapped to an Indian SECTOR
        └─ SLOTS 2-6: evergreen bank reels (10 topics × 1,000 reels each)
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

## 4. The 08:30 IST world-news morning brief (bullet points × sectors)

The morning slot assembles a **multi-story brief** — everything that happened
overnight, in India and around the world, that can move Indian markets — from
these sources (editable in `automation/content/news_sources.json`):

| Source | What it catches |
|---|---|
| **Google News — Global Markets Overnight** | Wall Street, Nasdaq, Dow, US Fed (12h) |
| **Google News — Oil Gold Dollar** | Crude oil, gold price, dollar index, rupee (12h) |
| **Google News — Asia Markets** | Nikkei, Hang Seng, Shanghai, China (12h) |
| **Google News — Indian Markets** | NIFTY/SENSEX/stock-market headlines (1d) |
| **Google News — Economy & Policy** | RBI, SEBI, Budget, inflation, GST |
| **Google News — Hindi Markets / Schemes** | Hindi market + yojana/subsidy headlines |
| **Sarkari KYP** (`sarkarikyp.com/feed/`) | Hindi govt schemes, yojana, subsidy, pension, EPF/PPF updates |
| **Moneycontrol / Economic Times / Livemint** | Market wraps & macro |

**The reel format (mandatory, enforced by the verifier):**
- **Unique bullet points** — 3-4 bullets, each covering a *different* news
  story; no story appears twice, no story is ever reused across days
  (`news_used` dedup).
- **Sector mapping** — every bullet ends with `-> Sector: <sector>`, chosen
  from a 25-sector Indian taxonomy (Banking, IT Services, Pharma, Auto,
  Metals, Oil & Gas, Realty & Infra, Telecom, Defence, Agri, Tourism…).
- **No stocks, ever** — sectors only; company names are banned in the brief,
  the script prompt, and the verification checklist.
- **Only source facts** — no invented numbers (verifier checks every bullet
  against the source items).
- Attribution ("news reports say" / "khabaron ke mutabik"), bilingual flip,
  mid-roll question and comment CTA stay as in every reel. The micro-story
  rule is waived for this format (bullets replace it) — the verifier knows.

If no fresh story matches, the bot falls back to the evergreen bank instead
of stalling.

---

## 4b. The 100 AI influencers (the channel's faces)

`automation/content/influencers.json` defines **100 realistic Indian personas** —
**10 topics × 10 influencers each** (5 men + 5 women, ages **25 / 30 / 35 / 40 / 45**,
one man and one woman per age per topic). Every persona has:

- a **unique name, handle, city, profession and catchphrase** (e.g. *Kusum Lata,
  45, retired school principal, Patna — "Bachchon ko maths sikha chuki hoon…"*)
- a **face sheet** (skin tone, hair, features, glasses, facial hair) + an exact
  **outfit** matching an age-appropriate dress code (25: trendy smart-casual →
  45: senior professional) — all composed into a photorealistic fal.ai prompt
  with "smartphone photo, natural light, real skin texture, no AI-gloss" realism
  instructions, so they **look like real people, not renders**
- a **voice** (ElevenLabs premade, multilingual v2 — swap any `voice_id`)
- an optional **`avatar_url`**: paste an OpenShorts gallery image URL to pin the
  persona to ONE consistent face across all its reels (otherwise each reel
  generates a fresh face from the same description)

Rotation is deterministic: each topic's roster rotates 1→10 in order, so a page
posting daily cycles 100 distinct faces and voices; news reels draw a stable
persona per story from the whole pool. Posted history records `persona_id` +
`persona_name`, and captions credit the persona with their handle — the
"influencer identity" builds recognition over time.

## 4c. Engagement format (built into every script)

Each reel is scripted to hook → engage → convert, per the style of the
reference videos (realistic AI influencer + monetization):

1. **Punchy hook** (0–4s) — persona's catchphrase or the bank's hook line.
2. **Problem + mid-roll question** (4–8s) — the persona asks the viewer
   directly: *"Aapke saath aisa hua hai?" / "Has this happened to you?"*
3. **Solution opened by a micro-story or example** (8–15s) — *"Meri ek dost…" /
   "A friend of mine…"* — a 2-line, first-person everyday situation (from the
   content bank's story/example material, or a realistic invented one).
4. **Demo/example beat** (15–19s) — b-roll visual with a concrete illustration.
5. **CTA with a comment-inviting question** (19–21s) — *"Comment YES if this
   helped"* — plus follow/save/share.

The Gemini verifier audits these engagement elements (questions, story/example,
conversational tone) alongside facts and compliance; the bot also logs soft
warnings if any element is missing.

## 4d. Growth & revenue playbook (goal: India's top finance page)

**Posting muscle**: 2 reels/day (news 08:30 IST + evergreen 19:00 IST) = 60+/mo.
Consistency beats virality: the algorithm rewards daily posting from day 1.

**Virality levers baked in**: bilingual (Hindi+English flips double the
addressable audience), questions → comments (the #1 ranking signal on Reels),
micro-stories → watch-time, saveable content (checklists/rules) → saves/shares,
hashtags + keyword-rich captions → search discovery.

**Scale knobs**: `POSTS_PER_DAY=3+` when you add more slots; the content bank
holds 10,000+ unique reels before repetition.

**Monetization ladder (realistic order)**:
1. **Grow first** (0–10k): nothing to sell; optimize hooks + comments.
2. **Brand sponsorships** (10k+): brokers/AMCs/fintechs pay ₹5k–₹50k+ per reel
   at scale — educational "explainer" sponsorships fit the channel without
   advice (always disclose as promo).
3. **Affiliate**: broker/app referral links with disclosure (educational
   framing only — no recommendations).
4. **Cross-post to YouTube Shorts** (via `PLATFORMS=youtube`): finance is the
   highest-RPM niche on YouTube — the same reels earn ad money there.
5. **Own products later** (course/e-book): note — paid investment *advice* in
   India requires SEBI registration; keep paid products educational.

**Watch-outs**: never post unverified claims (the gate enforces it), never
promise returns, and review IG Insights weekly — double down on whatever
subtopic × persona cells get the most saves and shares.

---

## 4e. Launch batch — 10 reels to Google Drive (one-time starter pack)

The first 10 reels are **fully drafted** in `automation/content/launch_batch.json`:
one per topic, each with a distinct influencer (10 different faces/voices, Hindi⇄English
flips, mid-roll questions, micro-stories, comment CTAs). They are verified by the
Gemini gate, generated by OpenShorts, and uploaded to your shared Google Drive
folder — **without posting to Instagram**, so you can review them first.

**One-time setup for Drive:**

1. Create a **service account**: Google Cloud Console → IAM & Admin → Service
   Accounts → Create → then Keys → Add key → **JSON** (download it).
2. Open your shared Drive folder → **Share** → paste the service account
   **email** (looks like `reels-bot@project-123.iam.gserviceaccount.com`) with
   Editor access.
3. Repo → Settings → Secrets → add the whole JSON file content as
   `DRIVE_SA_JSON`. (Optional: add `DRIVE_FOLDER_ID` as a variable — the
   workflow already defaults to your shared folder `150v_l6VkcaB_Fo4WtgKPZfar1yKu1KMe`.)

**Run it:** Actions → **Reels Launch Batch** → Run workflow (delivery = `drive`).
~10 reels × ~2-4 min each ≈ 30-45 min; fal.ai cost ≈ $6.5 total. Results land
in your Drive folder as `L01-T1 - … .mp4`, and `state/state.json` records each
`drive_file_id` + link. Re-running is safe — `state["launch_done"]` prevents a
second batch.

---

## 4f. Sample reel (no keys needed — download from Actions)

A demo reel in the exact production format is prebuilt and rebuildable anytime:

- `automation/sample_reel.py` composites committed assets
  (`assets/sample_actor.png` = photorealistic AI influencer portrait from the
  persona sheet, `assets/sample_voice.mp3` = bilingual TTS voiceover,
  `assets/fonts/` = Mukta Bold (Devanagari+Latin) + Anton) into a 1080×1920
  reel: English hook → Hindi flip, **cross-language subtitles** (English speech
  → Hindi subs, Hindi speech → English subs), hook overlay, handle, disclaimer
  strip, slow push-in zoom.
- **Actions → "Sample Reel" → Run workflow** → when it finishes green, click
  the run → **Artifacts** → download `sample-reel-L01-NIFTY`. Runs entirely on
  the runner with apt ffmpeg — zero API keys, zero cost.
- Local: `SAMPLE_FFMPEG=/path/to/ffmpeg python3 automation/sample_reel.py`
  (needs an ffmpeg with drawtext; `pip install mutagen imageio-ffmpeg`).

---

## 5. Schedule — 6 reels/day, every 4 hours

| Cron (UTC) | IST | Slot | Content |
|---|---|---|---|
| `0 3 * * *` | **08:30** | 1 | 🌍 **World-news morning brief** — everything that happened overnight/globally that can move Indian markets, as unique bullet points mapped to **sectors** (never stocks) |
| `0 7 * * *` | 12:30 | 2 | Evergreen bank reel |
| `0 11 * * *` | 16:30 | 3 | Evergreen bank reel |
| `0 15 * * *` | 20:30 | 4 | Evergreen bank reel (post-market) |
| `0 19 * * *` | 00:30 | 5 | Evergreen bank reel |
| `0 23 * * *` | 04:30 | 6 | Evergreen bank reel |

`POSTS_PER_DAY` defaults to **6** (set it lower to trim slots from the end).
The morning brief pulls **multiple stories** (up to 6, max 2 per source) from
global feeds — US Fed/Wall Street, oil & gold & dollar, Asian markets — plus
Indian sources (Google News IN, sarkarikyp.com, Moneycontrol, ET, Livemint),
deduped forever via `news_used`. Every bullet in the reel is a distinct story,
ends with `-> Sector: <sector>` (from a 25-sector Indian taxonomy), and the
verifier enforces: bullets traceable to the source items, sectors only,
**no stock names**.

Notes:
- GitHub scheduled runs are **best-effort** — usually on time, occasionally
  delayed. The bot assigns each run to its 4-hour grid window, so a delayed
  run never posts two reels back-to-back out of schedule. If GitHub's
  best-effort timing matters for you, run `automation/run.sh` from a server
  cron for exact timing.
- Scheduled workflows are paused after 60 days of repo inactivity — the bot's
  own state commits keep the repo active.
- Manual runs: **Actions → Reels Bot → Run workflow** (dry-run / slot 1-6 /
  force).

### Alternative: your own server cron

```cron
30 8  * * *  cd /path/to/openshorts/automation && ./run.sh --slot 1 >> /var/log/reels-bot.log 2>&1
30 12 * * *  cd /path/to/openshorts/automation && ./run.sh --slot 2 >> /var/log/reels-bot.log 2>&1
30 16 * * *  cd /path/to/openshorts/automation && ./run.sh --slot 3 >> /var/log/reels-bot.log 2>&1
30 20 * * *  cd /path/to/openshorts/automation && ./run.sh --slot 4 >> /var/log/reels-bot.log 2>&1
30 0  * * *  cd /path/to/openshorts/automation && ./run.sh --slot 5 >> /var/log/reels-bot.log 2>&1
30 4  * * *  cd /path/to/openshorts/automation && ./run.sh --slot 6 >> /var/log/reels-bot.log 2>&1
```

---

## 6. Costs at 6 reels/day (self-check before you switch it on)

| Item | Approx. | Notes |
|---|---|---|
| fal.ai generation | **~$3.90/day ≈ $117/mo** (`lowcost`) | The dominant cost at 6/day. `premium` ≈ $2/reel (3×). |
| OpenShorts hosted plan | $12+/mo + minutes | 6×21s ≈ 2.1 min/day ≈ 65 min/mo — pick a plan covering that |
| ElevenLabs | **Creator plan (~$22/mo)** | 6 reels × ~30s voice ≈ 90 min/mo — free tier (10 min) is NOT enough |
| Gemini | Free tier | 2 calls/reel × 6/day — free tier covers this volume |
| Upload-Post | Paid tier | 180 posts/mo needs a paid tier; free = 10/mo |
| GitHub Actions | Free tier (2000 min/mo) | 6 runs/day × ~5-10 min ≈ 90-180 min/mo — fine, but watch it |

**Total ≈ $150-160/mo at 6/day** — that's the honest operating cost of this
cadence. Start at 6/day only when the page earns it; `POSTS_PER_DAY=2` costs
≈ $50/mo. Dry-run is free (Actions → Reels Bot → Run workflow → dry_run).

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
