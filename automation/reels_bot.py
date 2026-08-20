#!/usr/bin/env python3
"""OpenShorts Reels Bot — automated daily trading/finance reels for Instagram.

Talks to the OpenShorts API (hosted cloud or self-hosted), generates an
AI-actor reel from the expert-curated content bank in content/topics.json
and publishes it to Instagram via the same Upload-Post path the OpenShorts
dashboard uses.

Designed to run from GitHub Actions on a cron schedule (or from any machine
with Python 3.9+ — stdlib only, no pip installs).

State lives in state/state.json and is committed back by CI, so every run is
idempotent (a slot that already posted today will not post again) and the
full history is auditable in git.

Exit codes: 0 = success or intentionally skipped; 1 = failure.
"""

import argparse
import json
import os
import random
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONTENT_FILE = os.path.join(BASE_DIR, "content", "topics.json")
STATE_FILE = os.path.join(BASE_DIR, "state", "state.json")
LOG_FILE = os.path.join(BASE_DIR, "state", "log.jsonl")

IST = ZoneInfo("Asia/Kolkata")
UTC = ZoneInfo("UTC")

# ------------------------------------------------------------------ config
def env(name: str, default: str = "") -> str:
    return os.environ.get(name, "").strip() or default

API_URL = env("OPENSHORTS_API_URL", "https://api.openshorts.app").rstrip("/")
API_KEY = env("OPENSHORTS_API_KEY")                  # osk_... for hosted
GEMINI_KEY = env("GEMINI_API_KEY")                   # self-host BYOK only
FAL_KEY = env("FAL_API_KEY")                         # needed for AI Shorts
ELEVENLABS_KEY = env("ELEVENLABS_API_KEY")           # needed for AI Shorts
UP_KEY = env("UPLOAD_POST_API_KEY")                  # self-host BYOK only
UP_USER = env("UPLOAD_POST_USER")                    # self-host profile
PLATFORMS = [p.strip() for p in env("PLATFORMS", "instagram").split(",") if p.strip()]
POSTS_PER_DAY = max(1, int(env("POSTS_PER_DAY", "1") or 1))
MAX_MONTHLY_POSTS = max(1, int(env("MAX_MONTHLY_POSTS", "30") or 30))
MAX_WAIT_MINUTES = max(5, int(env("MAX_WAIT_MINUTES", "55") or 55))
VIDEO_MODE = env("VIDEO_MODE", "lowcost") or "lowcost"   # lowcost | premium
FORCE = env("FORCE_RERUN", "false").lower() in ("1", "true", "yes")

LOG_LIMIT = 500
HISTORY_LIMIT = 300

# ------------------------------------------------------------------ logging
def log(msg: str, level: str = "INFO", **extra):
    ts = datetime.now(IST).isoformat(timespec="seconds")
    print(f"[{ts}] [{level}] {msg}", flush=True)
    entry = {"ts": ts, "level": level, "msg": msg}
    entry.update(extra)
    try:
        os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
        with open(LOG_FILE, "a") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        with open(LOG_FILE) as f:
            lines = f.readlines()
        if len(lines) > LOG_LIMIT:
            with open(LOG_FILE, "w") as f:
                f.writelines(lines[-LOG_LIMIT:])
    except OSError as e:
        print(f"[WARN] could not write log: {e}", flush=True)


def load_state() -> dict:
    try:
        with open(STATE_FILE) as f:
            st = json.load(f)
        if not isinstance(st, dict):
            st = {}
    except (OSError, ValueError):
        st = {}
    st.setdefault("history", [])
    st.setdefault("counters", {})
    return st


def save_state(st: dict):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(st, f, indent=2, ensure_ascii=False)


# ------------------------------------------------------------------ http
class HttpError(Exception):
    def __init__(self, code: int, body: str):
        self.code = code
        self.body = body
        super().__init__(f"HTTP {code}: {body[:200]}")


def http(method: str, path: str, body=None, headers=None, timeout: int = 300, retries: int = 2):
    """HTTP call against the OpenShorts API with retries on transient errors."""
    url = API_URL + path
    hdrs = {"Accept": "application/json", "User-Agent": "openshorts-reels-bot/1.0"}
    if API_KEY:
        hdrs["Authorization"] = f"Bearer {API_KEY}"
    if headers:
        hdrs.update(headers)
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        hdrs["Content-Type"] = "application/json"

    last_err: Exception = HttpError(0, "no response")
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, data=data, headers=hdrs, method=method)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read().decode() or "{}"
                try:
                    return resp.status, json.loads(raw)
                except ValueError:
                    return resp.status, raw
        except urllib.error.HTTPError as e:
            try:
                raw = e.read().decode()
            except Exception:
                raw = ""
            if e.code in (400, 401, 402, 403, 404, 413):
                raise HttpError(e.code, raw)
            last_err = HttpError(e.code, raw)  # 429 / 5xx -> retry
        except Exception as e:
            last_err = e
        if attempt < retries:
            time.sleep(5 * (attempt + 1))
    if isinstance(last_err, HttpError):
        raise last_err
    raise HttpError(0, str(last_err))


# ------------------------------------------------------------------ content
def load_content() -> dict:
    with open(CONTENT_FILE, encoding="utf-8") as f:
        return json.load(f)


def seasonal_weight(topic: dict, month: int) -> float:
    w = float(topic.get("weight", 1.0))
    if topic["id"] == "T10" and month in (1, 2, 3):   # tax season
        w *= 2.0
    if topic["id"] == "T9" and month == 2:            # Budget month
        w *= 1.5
    if topic["id"] == "T8" and month in (10, 11, 12): # IPO season
        w *= 1.4
    return w


def choose_topic(rng: random.Random, topics: list, history: list, month: int) -> dict:
    recent = [h["reel_id"].split("-")[0] for h in history[-2:] if h.get("status") == "posted"]
    pool = [t for t in topics if t["id"] not in recent] or topics
    weights = [seasonal_weight(t, month) for t in pool]
    total = sum(weights)
    r = rng.random() * total
    for t, w in zip(pool, weights):
        r -= w
        if r <= 0:
            return t
    return pool[-1]


def build_reel_spec(content: dict, state: dict, date_str: str, slot: int) -> dict:
    """Deterministically pick the next reel. Counters advance only after a
    successful post, so a failed slot retries the same reel on a manual rerun."""
    topics = content["topics"]
    month = int(date_str[5:7])
    seed = int(date_str.replace("-", "")) * 10 + slot
    rng = random.Random(seed)

    topic = choose_topic(rng, topics, state["history"], month)
    tid = topic["id"]
    # First appearance of each topic starts at a different point in its
    # 1,000-reel space, so early posts vary across topics immediately.
    topic_offset = (topics.index(topic) * 111) % 1000
    counter = int(state["counters"].get(tid, topic_offset))

    subtopics = topic["subtopics"]
    hooks = content["hooks"] + topic.get("extra_hooks", [])
    n_angles = len(content["angles"])

    # Coprime strides: every post advances subtopic, hook AND angle at once,
    # while cycling each list completely. Combined cycle = 10 × len(hooks) × 10
    # posts per topic before any (subtopic, hook, angle) triple repeats.
    subtopic_idx = counter % len(subtopics)
    hook_idx = (counter * 7) % len(hooks)
    angle_idx = (counter * 3) % n_angles
    angle_id = str(angle_idx + 1)
    angle = content["angles"][angle_id]

    subtopic = subtopics[subtopic_idx]
    hook_tpl = hooks[hook_idx]

    def rot(lst, stride):
        if not lst:
            return ""
        return lst[(counter * stride) % len(lst)]

    material = {
        "myth": rot(topic.get("myths", []), 2),
        "mistake": rot(topic.get("mistakes", []), 1),
        "stat": rot(topic.get("stats", []), 2),
        "example": rot(topic.get("examples", []), 1),
        "story": rot(topic.get("stories", []), 1),
        "timely": rot(topic.get("timely", []), 1),
        "challenge": rot(topic.get("challenges", []), 1),
        "spot": rot(topic.get("spots", []), 1),
        "compare": topic.get("comparisons", [{}])[counter % max(1, len(topic.get("comparisons", [])))],
    }
    cta = topic["cta"][counter % len(topic["cta"])]
    actor = content["actors"][seed % len(content["actors"])]
    duration = topic.get("duration", content["defaults"]["duration_seconds"])

    def fill(s: str) -> str:
        subtopic_spoken = subtopic.replace(":", ",")
        return (s.replace("{subtopic}", subtopic_spoken)
                 .replace("{Subtopic}", subtopic_spoken[:1].upper() + subtopic_spoken[1:])
                 .replace("{duration}", str(duration))
                 .replace("{myth}", material["myth"])
                 .replace("{mistake}", material["mistake"])
                 .replace("{stat}", material["stat"])
                 .replace("{example}", material["example"])
                 .replace("{story}", material["story"])
                 .replace("{timely}", material["timely"])
                 .replace("{challenge}", material["challenge"])
                 .replace("{spot}", material["spot"])
                 .replace("{compare_a}", material["compare"].get("a", ""))
                 .replace("{compare_b}", material["compare"].get("b", "")))

    hook_filled = fill(hook_tpl)
    angle_filled = fill(angle["template"])

    reel_id = f"{tid}-S{subtopic_idx + 1:02d}-H{hook_idx + 1:02d}-A{angle_id}"

    flavor_line = ""
    if topic.get("flavor") == "hinglish":
        flavor_line = (" Sprinkle at most one or two natural Hindi phrases like 'samajh lo' or 'dekho' "
                       "for an Indian audience. Keep the narration 90% English.")

    description = (
        f"Create a {duration}-second educational reel for Indian retail investors. "
        f"Topic: {topic['name']}. Subtopic: {subtopic}. "
        f"Angle: {angle['name']}. {angle_filled} "
        f"Open with this hook, word for word: \"{hook_filled}\" "
        f"Explain in simple English with no jargon, no stock names, no buy/sell advice, "
        f"no profit promises, no specific price targets.{flavor_line} "
        f"Tone: energetic but trustworthy, like a friend who knows the market. "
        f"End with this call to action, word for word: \"{cta}\" "
        f"Include a one-line disclaimer: \"Educational content, not investment advice.\""
    )

    hashtags = " ".join(topic.get("hashtags", []))
    caption = (
        f"{hook_filled}\n\n"
        f"{topic['tagline']}\n"
        f"\U0001F4BE Save this before your next trade.\n"
        f"{hashtags}\n\n"
        f"\u26A0\uFE0F Educational content. Not investment advice. Markets are subject to risks."
    )
    title = f"{subtopic[:1].upper() + subtopic[1:]} — {angle['name']} | {topic['short']}"[:80]

    return {
        "reel_id": reel_id,
        "topic_id": tid,
        "topic": topic["name"],
        "subtopic": subtopic,
        "hook": hook_filled,
        "angle": angle["name"],
        "description": description,
        "caption": caption,
        "title": title,
        "actor": actor,
        "style": topic.get("style", content["defaults"]["style"]),
        "language": content["defaults"]["language"],
        "gender": actor["gender"],
        "counter": counter,
        "duration": duration,
    }


# ------------------------------------------------------------------ helpers
def score_script(script: dict) -> int:
    """Heuristic to pick the most reel-worthy of the Gemini scripts,
    and to down-rank anything that smells like investment advice."""
    s = 0
    caption = (script.get("caption") or "").lower()
    hook = (script.get("hook") or "").lower()
    narration = (script.get("full_narration") or script.get("narration") or "").lower()
    for word in ("follow", "comment", "save", "share"):
        if word in caption or word in hook:
            s += 1
    if hook:
        s += 2
    words = len(narration.split())
    if 100 <= words <= 260:
        s += 2
    elif words > 340:
        s -= 1
    for bad in ("buy this", "sell this", "recommendation", "target price", "guaranteed profit"):
        if bad in narration or bad in caption:
            s -= 3
    return s


def pick_script(scripts: list):
    if not scripts:
        raise HttpError(0, "analyze returned no scripts")
    return sorted(scripts, key=score_script, reverse=True)[0]


def resolve_slot(args, state: dict, today: str) -> int:
    if args.slot:
        return args.slot
    override = env("SLOT_OVERRIDE")
    if override:
        return int(override)
    hour = datetime.now(UTC).hour
    if 1 <= hour <= 6:          # 03:00 UTC cron -> morning slot (08:30 IST)
        return 1
    if 12 <= hour <= 16:        # 13:30 UTC cron -> evening slot (19:00 IST)
        return 2
    posted = {(h["date"], h["slot"]) for h in state["history"] if h.get("status") in ("posted", "skipped")}
    for s in range(1, POSTS_PER_DAY + 1):
        if (today, s) not in posted:
            return s
    return 1


# ------------------------------------------------------------------ pipeline
def run_once(content: dict, state: dict, args) -> int:
    today = args.date or datetime.now(IST).strftime("%Y-%m-%d")
    month_key = today[:7]
    slot = resolve_slot(args, state, today)

    log(f"=== reels bot run start: date={today} slot={slot} platforms={PLATFORMS} ===")

    if slot > POSTS_PER_DAY:
        log(f"slot {slot} is disabled (POSTS_PER_DAY={POSTS_PER_DAY}). Nothing to do.", "SKIP")
        return 0

    posted_this_month = sum(
        1 for h in state["history"]
        if h.get("date", "").startswith(month_key) and h.get("status") == "posted"
    )
    if posted_this_month >= MAX_MONTHLY_POSTS:
        log(f"monthly budget reached ({posted_this_month}/{MAX_MONTHLY_POSTS}). Nothing to do.", "SKIP")
        return 0

    if not FORCE and any(
        h.get("date") == today and h.get("slot") == slot and h.get("status") in ("posted", "skipped")
        for h in state["history"]
    ):
        log(f"slot {slot} on {today} already handled. Nothing to do.", "SKIP")
        return 0

    spec = build_reel_spec(content, state, today, slot)
    log(f"planned reel {spec['reel_id']} — {spec['topic']} / {spec['subtopic']} / {spec['angle']}",
        reel_id=spec["reel_id"], topic_id=spec["topic_id"], slot=slot, date=today)
    log(f"hook: {spec['hook']}")

    if args.dry_run:
        print("\n----- DRY RUN — nothing was generated or posted -----")
        print("description -> analyze:")
        print(spec["description"])
        print("\ncaption -> post:")
        print(spec["caption"])
        print("-----------------------------------------------------\n")
        return 0

    # 1. Gemini writes scripts
    analyze_body = {
        "description": spec["description"],
        "num_scripts": 3,
        "style": spec["style"],
        "language": spec["language"],
        "actor_gender": spec["gender"],
    }
    headers = {"X-Gemini-Key": GEMINI_KEY} if GEMINI_KEY else {}
    log("step 1/4: writing scripts (analyze)…")
    try:
        _, analyze = http("POST", "/api/saasshorts/analyze", analyze_body, headers=headers, timeout=600)
    except HttpError as e:
        log(f"analyze failed ({e}); retrying once in 30s…", "WARN")
        time.sleep(30)
        _, analyze = http("POST", "/api/saasshorts/analyze", analyze_body, headers=headers, timeout=600)
    scripts = analyze.get("scripts") or []
    script = pick_script(scripts)
    log(f"picked script (score {score_script(script)}): {str(script.get('title') or script.get('hook'))[:100]}")

    # 2. Generate the AI-actor reel
    generate_body = {
        "script": script,
        "voice_id": spec["actor"].get("voice_id") or None,
        "actor_description": spec["actor"].get("desc") or None,
        "video_mode": VIDEO_MODE,
        "share_to_gallery": False,
    }
    gen_headers = {}
    if FAL_KEY:
        gen_headers["X-Fal-Key"] = FAL_KEY
    if ELEVENLABS_KEY:
        gen_headers["X-ElevenLabs-Key"] = ELEVENLABS_KEY
    log(f"step 2/4: generating reel (mode={VIDEO_MODE}, actor={spec['actor']['name']})…")
    _, generated = http("POST", "/api/saasshorts/generate", generate_body, headers=gen_headers, timeout=600)
    job_id = generated.get("job_id")
    if not job_id:
        raise HttpError(0, f"generate returned no job_id: {str(generated)[:200]}")
    log(f"generate job started: {job_id}", job_id=job_id)

    # 3. Poll until done
    log("step 3/4: waiting for render…")
    deadline = time.time() + MAX_WAIT_MINUTES * 60
    result = None
    while time.time() < deadline:
        _, status = http("GET", f"/api/saasshorts/status/{job_id}")
        state_status = status.get("status")
        result = status.get("result") or {}
        if state_status == "completed":
            log(f"render completed: {str(result.get('video_url'))[:100]}", job_id=job_id)
            break
        if state_status == "failed":
            raise HttpError(0, f"generation failed. last logs: {str((status.get('logs') or [])[-3:])[:300]}")
        last_log = (status.get("logs") or [""])[-1]
        log(f"…{state_status}: {last_log[:100]}", level="STATUS")
        time.sleep(60)
    else:
        raise HttpError(0, f"timed out after {MAX_WAIT_MINUTES} min waiting for {job_id}")

    # 4. Publish to Instagram (and any other configured platforms)
    post_body = {
        "job_id": job_id,
        "platforms": PLATFORMS,
        "title": spec["title"],
        "description": spec["caption"],
        "timezone": "Asia/Kolkata",
    }
    if UP_KEY:
        post_body["api_key"] = UP_KEY
    if UP_USER:
        post_body["user_id"] = UP_USER
    log(f"step 4/4: publishing to {PLATFORMS}…", job_id=job_id)
    try:
        _, posted = http("POST", "/api/saasshorts/post", post_body, timeout=300)
    except HttpError as e:
        log(f"publish failed ({e}); retrying once in 60s…", "WARN")
        time.sleep(60)
        _, posted = http("POST", "/api/saasshorts/post", post_body, timeout=300)
    log(f"publish response: {str(posted)[:200]}", job_id=job_id)

    state["counters"][spec["topic_id"]] = spec["counter"] + 1
    state["history"].append({
        "date": today,
        "slot": slot,
        "reel_id": spec["reel_id"],
        "topic_id": spec["topic_id"],
        "topic": spec["topic"],
        "subtopic": spec["subtopic"],
        "title": spec["title"],
        "job_id": job_id,
        "video_url": result.get("video_url"),
        "platforms": PLATFORMS,
        "status": "posted",
        "ts": datetime.now(IST).isoformat(timespec="seconds"),
    })
    state["history"] = state["history"][-HISTORY_LIMIT:]
    save_state(state)
    log(f"=== posted reel {spec['reel_id']} to {PLATFORMS} — done. ===", status="posted", reel_id=spec["reel_id"])
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="plan only, no API calls")
    parser.add_argument("--slot", type=int, choices=[1, 2], help="slot override (1=morning, 2=evening)")
    parser.add_argument("--date", help="override today's date as YYYY-MM-DD (testing)")
    parser.add_argument("--force", action="store_true", help="rerun even if the slot already posted")
    args = parser.parse_args()

    content = load_content()
    state = load_state()
    try:
        return run_once(content, state, args)
    except HttpError as e:
        log(f"HTTP error: {e}", "ERROR")
        return 1
    except Exception as e:
        log(f"unexpected error: {e!r}", "ERROR")
        return 1


if __name__ == "__main__":
    sys.exit(main())
