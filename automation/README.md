# 🤖 OpenShorts Reels Bot — fully automated finance reels for Instagram

A cron-driven pipeline that runs in **GitHub Actions**: every day it picks the
next reel from an expert-curated bank of the most-searched trading/finance
topics in India, generates an AI-actor reel through OpenShorts, and publishes
it to **Instagram Reels** (optionally TikTok / YouTube Shorts too) — with no
human in the loop. State and logs are committed back to this repo, so the
entire history is auditable in git.

```
GitHub cron (08:30 & 19:00 IST)
        │
        ▼
automation/reels_bot.py ── picks next reel (deterministic, no repeats)
        │
        ├─ 1. POST /api/saasshorts/analyze      Gemini writes 3 scripts
        ├─ 2. POST /api/saasshorts/generate     fal.ai actor + ElevenLabs voice → reel
        ├─ 3. GET  /api/saasshorts/status/{id}  poll until rendered
        └─ 4. POST /api/saasshorts/post         → Instagram via Upload-Post
        │
        ▼
state/state.json + state/log.jsonl committed back to the repo
```

---

## 1. One-time setup (you only need to add secrets)

Go to **repo → Settings → Secrets and variables → Actions** and add:

| Secret name | Required | What it is / where to get it |
|---|---|---|
| `OPENSHORTS_API_KEY` | Hosted mode | `osk_...` key from your [openshorts.app](https://openshorts.app) account page. Needs a **paid plan** for AI Shorts. Leave blank if self-hosting. |
| `FAL_API_KEY` | **Yes** | [fal.ai](https://fal.ai) dashboard key — powers the AI actor/video. ~$0.65 per reel in `lowcost` mode. |
| `ELEVENLABS_API_KEY` | **Yes** | [elevenlabs.io](https://elevenlabs.io) key — the voiceover. Free tier is enough. |
| `UPLOAD_POST_API_KEY` | Self-host only | [upload-post.com](https://upload-post.com) API key — **this is your "Instagram access"**: Instagram is connected inside Upload-Post. On hosted paid plans the server manages this. |
| `UPLOAD_POST_USER` | Self-host only | Your Upload-Post profile username that has Instagram connected. |
| `GEMINI_API_KEY` | Self-host only | From [aistudio.google.com](https://aistudio.google.com/app/apikey) (free). Hosted ignores it. |

Optional **Variables** (repo → Settings → Variables → Actions):

| Variable | Default | Meaning |
|---|---|---|
| `PLATFORMS` | `instagram` | Comma list: `instagram,tiktok,youtube` |
| `POSTS_PER_DAY` | `1` | `1` = morning only, `2` = morning + evening |
| `MAX_MONTHLY_POSTS` | `30` | Budget cap. **Set `10` if you are on Upload-Post's free tier.** |
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

## 2. What content gets posted (chosen for Indian demand)

The bank in [`content/topics.json`](content/topics.json) encodes the topics
Indian retail investors search most, weighted by demand (see
`REELS_CONTENT_PLAN.md` for the research):

| Topic | Weight | Why it's in the rotation |
|---|---|---|
| Candlesticks & chart patterns | 1.0 | Most-searched "how-to" in trading |
| Stock market basics (NIFTY/SENSEX/demat) | 1.0 | Largest beginner pool |
| SIPs, mutual funds, compounding | 1.0 | Highest-value micro-niche |
| Intraday discipline & risk | 1.0 | Huge search volume; SEBI-loss-stats hooks |
| Trading psychology & mistakes | 1.0 | Highest comments/shares |
| Technical indicators (RSI/MACD…) | 0.9 | Evergreen tool explainers |
| F&O / options explained | 0.8 | Massive curiosity, biggest education gap |
| Market news decoded (RBI/Budget/FII) | 0.6 | Boosted to 1.5× in Budget month |
| Taxes for traders (STCG/advance tax) | 0.6 | Boosted to 2× in Jan–Mar tax season |
| IPOs & listing gains | 0.4 | Boosted in Oct–Dec IPO season |

Every topic carries 10 subtopics, 10+ hooks, and 10 angle formulas (myth-bust,
mistake-spotlight, number-shock, quiz, micro-story…), with per-topic myths,
real stats (SEBI trader-loss studies, SIP compounding maths), everyday
analogies, CTAs and hashtags. The picker is **deterministic and no-repeat**:
subtopic/hook/angle counters only advance after a successful post, so a failed
slot retries the same reel. Mixing 10 topics × 10 subtopics × 10 hooks × 10
angles = **1,000 unique reels per topic** before anything repeats.

Actor and voice rotate daily (6 Indian actors × 6 ElevenLabs voices).
Every caption carries a mandatory disclaimer; scripts are scored to
**reject anything that smells like buy/sell advice**.

---

## 3. Schedule

| Cron (UTC) | IST | Slot |
|---|---|---|
| `0 3 * * *` | 08:30 | Morning (pre-market) — always on |
| `30 13 * * *` | 19:00 | Evening (post-market) — active when `POSTS_PER_DAY=2` |

Notes:
- GitHub scheduled runs are **best-effort** — usually on time, occasionally
  delayed ~15–60 min under load. For hard-exact timing, run `automation/run.sh`
  from a server cron (see below) instead.
- Scheduled workflows are **paused by GitHub after 60 days of repo inactivity**.
  Any commit (e.g. a state commit) resets that clock — the bot itself keeps
  the repo active, so this only matters if posting stops for two months.
- Manual runs: **Actions → Reels Bot → Run workflow** (has dry-run / slot /
  force toggles).

### Alternative: your own server cron (exact timing, no Actions minutes)

```cron
# /etc/crontab or crontab -e
30 8  * * *  cd /path/to/openshorts/automation && ./run.sh >> /var/log/reels-bot.log 2>&1
0 19  * * *  cd /path/to/openshorts/automation && ./run.sh >> /var/log/reels-bot.log 2>&1
```
Put keys in `automation/.env` (git-ignored).

---

## 4. Costs (self-check before you switch it on)

| Item | Approx. | Notes |
|---|---|---|
| OpenShorts hosted plan | $12+/mo | Paid tier unlocks AI Shorts + API keys + managed Upload-Post |
| fal.ai generation | **~$0.65/reel** (`lowcost`) | The real per-post cost. 1/day ≈ $20/mo. `premium` ≈ $2/reel. |
| ElevenLabs | Free tier | Enough for 1–2 reels/day |
| Upload-Post | Free 10 posts/mo → paid tiers | Set `MAX_MONTHLY_POSTS=10` if staying free |
| GitHub Actions | Free tier is plenty | ~15 min/run, 30–60 runs/mo |

Dry-run is free: **Actions → Reels Bot → Run workflow → dry_run = true** prints
the exact reel plan (script prompt + caption) without any API spend.

---

## 5. Guardrails & compliance

- **Education only**: the content bank contains no stock names, no buy/sell/
  hold calls, no price targets, no profit promises. Scripts that say "buy
  this" are auto-rejected by the scorer.
- **Real stats only**: SEBI trader-loss study figures, SIP compounding maths,
  LTCG rules — no made-up numbers.
- **Disclaimer on every post**: "Educational content. Not investment advice."
- **Audit trail**: every run commits its decision + result to `automation/state/`.
- **Fails loudly**: any API failure exits non-zero → the Actions run turns red,
  so you can see problems in the Actions tab (enable watch notifications on
  the repo for failed runs if you want emails).
- Strong recommendation: check the first 2–3 posted reels after enabling, then
  let it fly on autopilot.

## 6. Local testing

```bash
# plan only (no API calls, no keys)
python3 automation/reels_bot.py --dry-run --date 2026-08-22 --slot 1

# full pipeline against a fake server (no keys, no cost)
python3 automation/mock_server.py 8099 &
OPENSHORTS_API_URL=http://127.0.0.1:8099 FAL_API_KEY=x ELEVENLABS_API_KEY=x \
  python3 automation/reels_bot.py --slot 1 --force
```

## 7. Troubleshooting

| Symptom | Likely cause |
|---|---|
| Run is red, `HTTP 402` | Hosted plan quota/minutes exhausted → top up or lower `POSTS_PER_DAY` |
| Run is red, `Missing fal.ai API Key` | `FAL_API_KEY` secret missing |
| Post fails, `Missing Upload-Post API key` | Self-hosted: add `UPLOAD_POST_API_KEY` + `UPLOAD_POST_USER`; or IG not connected in Upload-Post |
| "slot is disabled" every evening | `POSTS_PER_DAY` is `1` — expected |
| "monthly budget reached" | `MAX_MONTHLY_POSTS` cap — expected; raise it (and check Upload-Post tier) |
| Nothing runs at all | Check the workflow is on the **default branch** and Actions is enabled |
