#!/usr/bin/env python3
"""OpenShorts Reels Bot — automated, verified, bilingual finance reels for Instagram.

Every reel passes through a mandatory Gemini gate before anything is published:

  1. NEWS or BANK pick — latest market news (sarkarikyp.com, Moneycontrol, ET,
     Livemint, …) or the evergreen content bank (content/topics.json).
  2. GEMINI WRITES the script — bilingual by default: the reel starts in Hindi
     or English (random) and flips mid-reel to the other language; every
     segment carries subtitle_text in the OPPOSITE language (cross-language
     subtitles, burned by the server when use_script_subtitles=true — supported
     by this fork's saasshorts.py patch).
  3. GEMINI VERIFIES the script (correctness + authenticity gate):
       • every factual/numeric claim is checked against the ground-truth text
         (news source text, or the content bank's fact sheet)
       • compliance: no buy/sell/target/guaranteed-returns advice, no stock
         names, mandatory disclaimer, good-faith tone, no defamation
       • translations are faithful, languages are genuine
     → approve: post · fix: apply correction and re-verify (max attempts) ·
       reject: do NOT post (recorded in state, loud log).
  4. GENERATE via OpenShorts (fal.ai actor + ElevenLabs multilingual voice).
  5. PUBLISH to Instagram (+ any other configured platforms) via Upload-Post.

State lives in state/state.json (committed back by CI) so runs are idempotent
and every decision — including rejections — is auditable in git.

Stdlib only. Exit codes: 0 = posted/skipped/rejected-safely; 1 = failure.
"""

import argparse
import hashlib
import html as html_lib
import json
import os
import random
import re
import sys
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
from email.utils import parsedate_to_datetime
from zoneinfo import ZoneInfo

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONTENT_FILE = os.path.join(BASE_DIR, "content", "topics.json")
NEWS_FILE = os.path.join(BASE_DIR, "content", "news_sources.json")
INFLUENCERS_FILE = os.path.join(BASE_DIR, "content", "influencers.json")
LAUNCH_FILE = os.path.join(BASE_DIR, "content", "launch_batch.json")
MEDIA_DIR = os.path.join(BASE_DIR, "media")
STATE_FILE = os.path.join(BASE_DIR, "state", "state.json")
LOG_FILE = os.path.join(BASE_DIR, "state", "log.jsonl")

IST = ZoneInfo("Asia/Kolkata")
UTC = ZoneInfo("UTC")

# ------------------------------------------------------------------ config
def env(name: str, default: str = "") -> str:
    return os.environ.get(name, "").strip() or default


API_URL = env("OPENSHORTS_API_URL", "https://api.openshorts.app").rstrip("/")
API_KEY = env("OPENSHORTS_API_KEY")                  # osk_... for hosted

# Gemini is the correctness/authenticity gate — REQUIRED in every mode.
GEMINI_API_KEY = env("GEMINI_API_KEY")
GEMINI_API_URL = env("GEMINI_API_URL", "https://generativelanguage.googleapis.com").rstrip("/")
GEMINI_MODEL = env("GEMINI_MODEL", "gemini-2.5-flash")

FAL_KEY = env("FAL_API_KEY")                         # self-host BYOK
ELEVENLABS_KEY = env("ELEVENLABS_API_KEY")           # self-host BYOK
UP_KEY = env("UPLOAD_POST_API_KEY")                  # self-host BYOK
UP_USER = env("UPLOAD_POST_USER")                    # self-host profile
PLATFORMS = [p.strip() for p in env("PLATFORMS", "instagram").split(",") if p.strip()]
POSTS_PER_DAY = max(1, int(env("POSTS_PER_DAY", "1") or 1))
MAX_MONTHLY_POSTS = max(1, int(env("MAX_MONTHLY_POSTS", "30") or 30))
MAX_WAIT_MINUTES = max(5, int(env("MAX_WAIT_MINUTES", "55") or 55))
VIDEO_MODE = env("VIDEO_MODE", "lowcost") or "lowcost"
FORCE = env("FORCE_RERUN", "false").lower() in ("1", "true", "yes")

# Bilingual + news knobs
BILINGUAL = env("BILINGUAL", "true").lower() not in ("0", "false", "no")
BILINGUAL_VOICE_ID = env("BILINGUAL_VOICE_ID", "9BWtsMINqrJLrRacOk9x")  # ElevenLabs "Sarah" (multilingual v2 — Hindi capable)
VOICE_ID = env("VOICE_ID", "21m00Tcm4TlvDq8ikWAM")                      # ElevenLabs "Rachel"
NEWS_ENABLED = env("NEWS_ENABLED", "true").lower() not in ("0", "false", "no")
NEWS_SLOT = max(0, min(2, int(env("NEWS_SLOT", "1") or 1)))             # which slot posts news; 0 = never
NEWS_SOURCE_URLS = env("NEWS_SOURCE_URLS")                              # optional override, comma-separated
VERIFY_MAX_ATTEMPTS = max(1, int(env("VERIFY_MAX_ATTEMPTS", "2") or 2))

# Launch batch + delivery knobs
LAUNCH = env("LAUNCH", "false").lower() in ("1", "true", "yes")         # run the 10-reel launch batch
DELIVERY_MODE = env("DELIVERY", "instagram")                            # instagram | drive | instagram,drive
DRIVE_FOLDER_ID = env("DRIVE_FOLDER_ID", "")                            # target shared folder
DRIVE_DRY_RUN = env("DRIVE_DRY_RUN", "false").lower() in ("1", "true", "yes")

LOG_LIMIT = 500
HISTORY_LIMIT = 300
NEWS_USED_LIMIT = 200

DISCLAIMER_BILINGUAL = (
    "\u26A0\uFE0F Educational content, not investment advice. Markets are subject to risks.\n"
    "\u0936\u0948\u0915\u094D\u0937\u093F\u0915 \u0938\u093E\u092E\u0917\u094D\u0930\u0940 \u2014 \u0928\u093F\u0935\u0947\u0936 \u0938\u0932\u093E\u0939 \u0928\u0939\u0940\u0902\u0964"
)

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
    st.setdefault("news_used", [])
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
    hdrs = {"Accept": "application/json", "User-Agent": "openshorts-reels-bot/2.0"}
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
            last_err = HttpError(e.code, raw)
        except Exception as e:
            last_err = e
        if attempt < retries:
            time.sleep(5 * (attempt + 1))
    if isinstance(last_err, HttpError):
        raise last_err
    raise HttpError(0, str(last_err))


def fetch_text(url: str, timeout: int = 15) -> str:
    """Simple GET for news sources. Returns '' on any failure."""
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36",
        "Accept": "*/*",
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception as e:
        log(f"news fetch failed for {url}: {e}", "WARN")
        return ""


# ------------------------------------------------------------------ gemini
GEMINI_SYSTEM = (
    "You are the content-safety and accuracy engine of an educational finance reels "
    "channel for Indian retail investors. You write in good faith, never invent facts, "
    "never give investment advice, and you are meticulous about compliance with "
    "Indian regulations (SEBI) and platform rules."
)


def gemini_json(prompt: str, system: str = "", temperature: float = 0.6, attempts: int = 2) -> dict:
    if not GEMINI_API_KEY:
        raise HttpError(0, "GEMINI_API_KEY is missing. Gemini is the mandatory correctness/authenticity gate for every reel — the bot refuses to produce or post without it.")
    url = f"{GEMINI_API_URL}/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json", "temperature": temperature},
    }
    if system:
        body["systemInstruction"] = {"parts": [{"text": system}]}
    last_err: Exception = HttpError(0, "no response")
    for attempt in range(attempts):
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(body).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=180) as resp:
                data = json.loads(resp.read().decode() or "{}")
            text = (data.get("candidates") or [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
            if not text:
                raise HttpError(0, f"Gemini returned empty text: {str(data)[:200]}")
            text = text.strip()
            if text.startswith("```"):
                text = re.sub(r"^```(json)?\s*", "", text)
                text = re.sub(r"\s*```$", "", text)
            return json.loads(text)
        except HttpError:
            raise
        except Exception as e:
            last_err = e
            if attempt < attempts - 1:
                time.sleep(3 * (attempt + 1))
    raise HttpError(0, f"Gemini call failed: {last_err}")


# ------------------------------------------------------------------ content
def load_content() -> dict:
    with open(CONTENT_FILE, encoding="utf-8") as f:
        return json.load(f)


def load_influencers() -> dict:
    with open(INFLUENCERS_FILE, encoding="utf-8") as f:
        return json.load(f)


def pick_influencer(spec: dict, influencers: list) -> dict:
    """Deterministic persona choice:
    - bank reels: round-robin through the topic's 10-persona roster
      (driven by the reel counter -> the same reel always gets the same face)
    - news reels: hash of the story -> any of the 100 personas, stable per story
    """
    if spec["kind"] == "bank":
        roster = [p for p in influencers if p["topic_id"] == spec["topic_id"]]
        if not roster:
            roster = influencers
        return roster[spec["counter"] % len(roster)]
    digest = int(spec["news"]["hash"], 16)
    return influencers[digest % len(influencers)]


def build_actor_description(persona: dict, data: dict) -> str:
    """Compose a photorealistic fal.ai actor prompt from the persona sheet."""
    style_table = data["style_table"]
    gender = persona["gender"]
    age_band = str(persona["age"])
    base_style = style_table[gender][age_band]
    return (
        f"{persona['face']}. Wearing a {base_style}: {persona['style_extra']}. "
        f"{data['camera_realism']}"
    )


def seasonal_weight(topic: dict, month: int) -> float:
    w = float(topic.get("weight", 1.0))
    if topic["id"] == "T10" and month in (1, 2, 3):
        w *= 2.0
    if topic["id"] == "T9" and month == 2:
        w *= 1.5
    if topic["id"] == "T8" and month in (10, 11, 12):
        w *= 1.4
    return w


def choose_topic(rng: random.Random, topics: list, history: list, month: int) -> dict:
    recent = [h["reel_id"].split("-")[0] for h in history[-2:] if h.get("status") == "posted" and h.get("reel_id", "").startswith("T")]
    pool = [t for t in topics if t["id"] not in recent] or topics
    weights = [seasonal_weight(t, month) for t in pool]
    total = sum(weights)
    r = rng.random() * total
    for t, w in zip(pool, weights):
        r -= w
        if r <= 0:
            return t
    return pool[-1]


def build_bank_spec(content: dict, state: dict, date_str: str, slot: int, rng: random.Random) -> dict:
    """Deterministically pick the next evergreen reel. Counters advance only
    after a successful post, so a failed slot retries the same reel."""
    topics = content["topics"]
    month = int(date_str[5:7])
    topic = choose_topic(rng, topics, state["history"], month)
    tid = topic["id"]
    topic_offset = (topics.index(topic) * 111) % 1000
    counter = int(state["counters"].get(tid, topic_offset))

    subtopics = topic["subtopics"]
    hooks = content["hooks"] + topic.get("extra_hooks", [])
    n_angles = len(content["angles"])

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
    actor = content["actors"][(seed := int(date_str.replace("-", "")) * 10 + slot) % len(content["actors"])]
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

    hook = fill(hook_tpl)
    angle_text = fill(angle["template"])
    lang_order = rng.choice(["hi-en", "en-hi"])

    reel_id = f"{tid}-S{subtopic_idx + 1:02d}-H{hook_idx + 1:02d}-A{angle_id}"

    fact_sheet = []
    for key, label in (("myth", "Myth to debunk"), ("stat", "True fact/stat to use"),
                       ("example", "Everyday analogy"), ("mistake", "Common mistake"),
                       ("timely", "Timely angle"), ("challenge", "Challenge"),
                       ("story", "Micro-story")) :
        if material.get(key):
            fact_sheet.append(f"- {label}: {material[key]}")
    fact_sheet.append(f"- Angle formula: {angle_text}")
    fact_sheet.append(f"- Hook (use word-for-word at the start): {hook}")
    fact_sheet.append(f"- CTA (end the reel with this): {cta}")

    brief = (
        f"TOPIC: {topic['name']}\nSUBTopic: {subtopic}\n\n"
        + "\n".join(fact_sheet) + "\n\n"
        "Only use the facts above plus universally known financial knowledge. "
        "Do not invent specific numbers beyond the fact sheet. "
        "Do not name any specific stock or company as a pick. Education only."
    )

    hashtags = topic.get("hashtags", [])
    return {
        "reel_id": reel_id,
        "kind": "bank",
        "topic_id": tid,
        "topic": topic["name"],
        "subtopic": subtopic,
        "hook": hook,
        "angle": angle["name"],
        "brief": brief,
        "ground_truth": "\n".join(fact_sheet),
        "caption_top": hook,
        "hashtags": hashtags,
        "actor": actor,
        "counter": counter,
        "lang_order": lang_order,
        "duration": 20,
    }


# ------------------------------------------------------------------ news
def load_news_config() -> dict:
    with open(NEWS_FILE, encoding="utf-8") as f:
        return json.load(f)


def parse_rss(text: str) -> list:
    items = []
    try:
        root = ET.fromstring(text)
        for it in root.findall(".//item"):
            items.append({
                "title": (it.findtext("title", "") or "").strip(),
                "desc": re.sub(r"<[^>]+>", " ", it.findtext("description", "") or "").strip(),
                "link": (it.findtext("link", "") or "").strip(),
                "date": (it.findtext("pubDate", "") or "").strip(),
            })
    except ET.ParseError:
        pass
    return items


def parse_html(text: str, base_url: str) -> list:
    items = []
    title_match = re.search(r"<title[^>]*>(.*?)</title>", text, re.I | re.S)
    site_title = html_lib.unescape(re.sub(r"<[^>]+>", "", title_match.group(1))).strip() if title_match else ""
    seen = set()
    for m in re.finditer(r'<h([1-4])[^>]*>\s*<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>', text, re.I | re.S):
        headline = html_lib.unescape(re.sub(r"<[^>]+>", "", m.group(3))).strip()
        if len(headline) < 12 or headline in seen:
            continue
        seen.add(headline)
        href = m.group(2)
        if href.startswith("/"):
            from urllib.parse import urlparse
            p = urlparse(base_url)
            href = f"{p.scheme}://{p.netloc}{href}"
        items.append({"title": headline, "desc": "", "link": href, "date": ""})
    if site_title and len(site_title) > 12:
        items.append({"title": site_title, "desc": "", "link": base_url, "date": ""})
    return items


def keyword_hits(text: str, keywords: list) -> int:
    low = text.lower()
    return sum(1 for kw in keywords if kw in low)


def news_date_score(item: dict, idx: int) -> float:
    try:
        dt = parsedate_to_datetime(item["date"])
        return dt.timestamp()
    except (TypeError, ValueError, KeyError):
        return time.time() - idx * 3600  # undated items: keep order, slight decay


def pick_news(state: dict) -> dict | None:
    cfg = load_news_config()
    keywords = [k.lower() for k in cfg.get("keywords", [])]
    sources = cfg.get("sources", [])
    if NEWS_SOURCE_URLS:
        sources = [{"name": f"custom-{i}", "url": u.strip(), "type": "auto"} for i, u in enumerate(NEWS_SOURCE_URLS.split(",")) if u.strip()]

    used = {u["hash"] for u in state["news_used"]}
    candidates = []
    for src in sources:
        text = fetch_text(src["url"])
        if not text:
            continue
        items = []
        if "<rss" in text[:2000] or "<feed" in text[:2000] or "<rdf" in text[:2000] or src.get("type") == "rss":
            items = parse_rss(text)
        else:
            items = parse_html(text, src["url"])
        for it in items:
            title = it["title"]
            if not title:
                continue
            blob = f"{title} {it['desc']}"
            hits = keyword_hits(blob, keywords)
            if hits == 0:
                continue
            digest = hashlib.md5((it["link"] or title).encode()).hexdigest()[:12]
            if digest in used:
                continue
            candidates.append({
                "source": src["name"],
                "title": title,
                "desc": it["desc"][:500],
                "link": it["link"],
                "date": it["date"],
                "hits": hits,
                "hash": digest,
                "score": news_date_score(it, len(candidates)) + hits * 3600 * 6,
            })
    if not candidates:
        return None
    candidates.sort(key=lambda c: -c["score"])
    last_source = state["history"][-1].get("source") if state["history"] else None
    best = candidates[0]
    if best["source"] == last_source and len(candidates) > 1:
        best = candidates[1]
    return best


def build_news_spec(item: dict, date_str: str, slot: int, rng: random.Random) -> dict:
    source_text = item["title"]
    if item["desc"]:
        source_text += "\n" + item["desc"]
    brief = (
        "You are turning this NEWS ITEM into an educational reel:\n"
        f"SOURCE: {item['source']}\nNEWS TEXT:\n{source_text}\n\n"
        "STRICT RULES:\n"
        "1. Use ONLY facts stated in the NEWS TEXT above. If it lacks numbers, do not invent any.\n"
        "2. Frame it educationally: what happened, and what it could mean for retail investors "
        "in simple terms. No predictions of guaranteed outcomes, no 'buy/sell', no stock picks.\n"
        "3. Attribute the news in the narration once, e.g. 'news reports say' / 'khabaron ke mutabik'.\n"
        "4. Keep it honest: if the news is about a scheme/rule change, explain who it affects.\n"
        "5. Never claim certainty about market direction.\n"
    )
    lang_order = rng.choice(["hi-en", "en-hi"])
    digest = item["hash"]
    return {
        "reel_id": f"N-{date_str.replace('-', '')}-{slot}-{digest[:6]}",
        "kind": "news",
        "topic_id": None,
        "topic": f"News: {item['source']}",
        "subtopic": item["title"][:60],
        "hook": item["title"][:90],
        "angle": "Timely explainer",
        "brief": brief,
        "ground_truth": f"SOURCE TEXT (only this may be used as fact):\n{source_text}",
        "caption_top": item["title"][:110],
        "hashtags": ["#StockMarketNews", "#NiftyToday", "#MarketUpdate", "#ShareMarketIndia"],
        "actor": {},  # filled below
        "counter": 0,
        "lang_order": lang_order,
        "duration": 20,
        "news": {"source": item["source"], "link": item["link"], "hash": item["hash"], "date": item["date"]},
    }


# ------------------------------------------------------------------ script
SCRIPT_SYSTEM = (
    "You are a viral short-form scriptwriter for Indian finance reels. You write "
    "bilingual (Hindi + English) scripts with cross-language subtitles. You always "
    "follow the exact JSON schema you are given. You write in good faith: educational, "
    "no investment advice, no invented numbers, no specific stock picks."
)

SEGMENT_TYPES = ["hook", "problem", "solution", "demo", "cta"]
REPAIR_TIMINGS = {"hook": (0, 4), "problem": (4, 8), "solution": (8, 15), "demo": (15, 19), "cta": (19, 21)}


def validate_script(script: dict) -> list:
    issues = []
    segs = script.get("segments")
    if not isinstance(segs, list) or len(segs) != 5:
        return ["segments must be a list of exactly 5"]
    types = [s.get("type") for s in segs]
    if types != SEGMENT_TYPES:
        issues.append(f"segment types must be {SEGMENT_TYPES}, got {types}")
    visuals = [s.get("visual") for s in segs]
    if visuals != ["actor_talking", "broll", "actor_talking", "broll", "actor_talking"]:
        issues.append("visual order must be actor/broll/actor/broll/actor")
    for i, s in enumerate(segs):
        if not (s.get("narration") or "").strip():
            issues.append(f"segment {i} narration empty")
        if BILINGUAL and not (s.get("subtitle_text") or "").strip():
            issues.append(f"segment {i} subtitle_text empty")
        if not isinstance(s.get("start"), (int, float)) or not isinstance(s.get("end"), (int, float)):
            issues.append(f"segment {i} missing start/end")
        if s.get("visual") == "broll" and not (s.get("broll_prompt") or "").strip():
            issues.append(f"segment {i} broll_prompt empty")
    total = float(script.get("duration_seconds", 0))
    if not (15 <= total <= 25):
        issues.append(f"duration_seconds {total} outside 15-25")
    return issues


def repair_script(script: dict) -> dict:
    """Normalize timings to the canonical 21-second layout so the server's
    composite step always gets monotonic, in-range segments."""
    segs = script.get("segments", [])
    if len(segs) != 5:
        return script
    for s in segs:
        if s.get("type") in REPAIR_TIMINGS:
            s["start"], s["end"] = REPAIR_TIMINGS[s["type"]]
    script["duration_seconds"] = 21
    return script


def engagement_warnings(script: dict) -> list:
    """Soft checks for the engagement elements (the Gemini verifier enforces
    these authoritatively; this just surfaces warnings in the log)."""
    warnings = []
    segs = script.get("segments") or []
    if len(segs) == 5:
        problem = segs[1].get("narration") or ""
        problem_sub = segs[1].get("subtitle_text") or ""
        solution = segs[2].get("narration") or ""
        cta = segs[4].get("narration") or ""
        cta_sub = segs[4].get("subtitle_text") or ""
        cta_blob = (cta + " " + cta_sub).lower()
        if "?" not in problem and "?" not in problem_sub:
            warnings.append("problem segment has no viewer question")
        if len(solution.split()) < 12:
            warnings.append("solution segment looks too short for a micro-story/example")
        comment_cues = ("?", "comment", "batao", "likho", "karo", "answer", "yes", "no")
        if not any(cue in cta_blob for cue in comment_cues):
            warnings.append("CTA segment has no comment-inviting question")
    return warnings


def build_script(spec: dict) -> dict:
    lang1, lang2 = spec["lang_order"].split("-")
    lang1_name = "Hindi" if lang1 == "hi" else "English"
    lang2_name = "Hindi" if lang2 == "hi" else "English"
    split_rule = (
        f"LANGUAGE FLIP: segments 1 and 2 (hook, problem) MUST be written in {lang1_name}. "
        f"Segments 3, 4 and 5 (solution, demo, cta) MUST be written in {lang2_name}. "
        f"For every segment, subtitle_text MUST be a faithful, short translation of that "
        f"segment's narration into the OTHER language ({lang2_name} for segments 1-2, "
        f"{lang1_name} for segments 3-5). Use natural Devanagari script for Hindi. "
        f"The narration must feel like one person switching languages naturally mid-video."
    ) if BILINGUAL else (
        "LANGUAGE: write all narration in simple English; subtitle_text mirrors the narration "
        "(short TikTok-style phrasing)."
    )

    persona = spec.get("persona") or {}
    persona_block = ""
    if persona:
        persona_block = (
            "PERSONA: You are {name}, a {age}-year-old {profession} from {city}, India. "
            "Speak in the first person, naturally, exactly like {name} would. "
            "Speaking style: {tone}. Your signature catchphrase is \"{catchphrase}\" - "
            "use it once, naturally, in the hook or CTA segment.\n"
        ).format(
            name=persona["name"], age=persona["age"], profession=persona["profession"],
            city=persona["city"], tone=persona["tone"], catchphrase=persona["catchphrase"],
        )

    engagement_rules = (
        "ENGAGEMENT RULES (mandatory):\n"
        "1. The problem segment MUST end with a direct question to the viewer, in that "
        "segment's language (e.g. 'Aapke saath aisa hua hai?' / 'Has this happened to you?').\n"
        "2. The solution segment MUST open with a very short micro-story or a real-life "
        "example (max 2 lines, first person - e.g. 'Meri ek dost ke saath...' / 'A friend "
        "of mine...'). Use the story/example material from the brief when given; otherwise "
        "invent a realistic everyday situation that fits the topic.\n"
        "3. The CTA segment MUST end with a question that invites comments (e.g. "
        "'Comment YES if this helped you' / 'Aap kya karte? Comment karo').\n"
        "4. Keep the whole reel conversational - like one person talking to a friend, "
        "not reading a textbook.\n"
    )

    actor_desc = spec.get("actor_desc", "Indian professional in their late 20s, friendly and trustworthy, casual modern clothing")

    prompt = f"""TASK: SCRIPT

{spec['brief']}

{persona_block}
{split_rule}
{engagement_rules}
Return ONLY JSON, exactly this schema:
{{
  "title": "short internal title",
  "style": "{'educational'}",
  "duration_seconds": 21,
  "target_platform": "instagram",
  "hook_text": "2-5 word on-screen hook (in {lang1_name})",
  "segments": [
    {{"type": "hook", "start": 0, "end": 4, "narration": "...({lang1_name}, punchy hook)", "visual": "actor_talking", "broll_prompt": null, "emotion": "excited", "subtitle_text": "...({lang2_name})"}},
    {{"type": "problem", "start": 4, "end": 8, "narration": "...({lang1_name}, ends with a QUESTION to the viewer)", "visual": "broll", "broll_prompt": "detailed English visual description (Indian setting)", "emotion": "concerned", "subtitle_text": "...({lang2_name})"}},
    {{"type": "solution", "start": 8, "end": 15, "narration": "...({lang2_name}, opens with a micro-story or example)", "visual": "actor_talking", "broll_prompt": null, "emotion": "confident", "subtitle_text": "...({lang1_name})"}},
    {{"type": "demo", "start": 15, "end": 19, "narration": "...({lang2_name})", "visual": "broll", "broll_prompt": "detailed English visual description (Indian setting)", "emotion": "excited", "subtitle_text": "...({lang1_name})"}},
    {{"type": "cta", "start": 19, "end": 21, "narration": "...({lang2_name}, CTA to follow/save/share + a comment-inviting question)", "visual": "actor_talking", "broll_prompt": null, "emotion": "friendly", "subtitle_text": "...({lang1_name})"}}
  ],
  "full_narration": "all narration joined with spaces",
  "actor_description": "{actor_desc}",
  "hashtags": ["#..."],
  "caption": "bilingual caption: 1 English line + 1 Hindi line (short)"
}}

RULES: exact schema · no markdown · durations must match start/end · broll_prompt in English ·
no stock names · no buy/sell/target prices · no profit guarantees · educational tone ·
narration totals ~55-70 words. If Hindi is used, it must be correct, natural Hindi
(Devanagari), not transliterated English."""
    return gemini_json(prompt, SCRIPT_SYSTEM, temperature=0.8)


# ------------------------------------------------------------------ verify
VERIFY_SYSTEM = (
    "You are the legal-and-accuracy auditor for an educational finance reels channel. "
    "Your verdict decides whether a reel may be published. You are strict but fair: "
    "minor wording issues get fixed; anything unsafe or unfactual gets rejected. "
    "You never let a reel through with unverified claims, investment advice, or bad-faith content."
)


def verify_script(script: dict, spec: dict) -> tuple:
    """Returns (verdict, script). verdict in approve|reject. Raises if Gemini fails."""
    for attempt in range(1, VERIFY_MAX_ATTEMPTS + 1):
        prompt = f"""TASK: VERIFY (attempt {attempt}/{VERIFY_MAX_ATTEMPTS})

You are reviewing a reel BEFORE it is published to Instagram. Decide approve / fix / reject.

GROUND TRUTH (facts the script is allowed to use):
{spec['ground_truth']}

THE SCRIPT (JSON):
{json.dumps(script, ensure_ascii=False, indent=1)}

AUDIT CHECKLIST — flag every violation:
1. FACTS: every numeric or factual claim in narration/subtitle_text/caption must be in the
   GROUND TRUTH or universally known public financial knowledge. Any invented number,
   wrong statistic, or claim contradicted by the ground truth = reject-level issue.
2. LEGAL/COMPLIANCE: no buy/sell/hold advice, no stock names as picks, no price targets,
   no guaranteed or promised returns, no "sure-shot" claims, no solicitation of funds.
3. GOOD FAITH: no fear-mongering, no defamation, no misleading urgency, no impersonation,
   no plagiarized verbatim article text (summaries must be in the reel's own words).
4. BILINGUAL: each segment's narration is genuinely in its assigned language; each
   subtitle_text is a faithful translation (no meaning drift, no invented content).
5. SCHEMA: 5 segments with the correct type order and both broll_prompt filled.
6. ENGAGEMENT: the problem segment ends with a direct question to the viewer; the
   solution segment opens with a micro-story or example; the CTA ends with a
   comment-inviting question; the tone is conversational, not textbook.
7. PERSONA: the narration is first-person and consistent with the influencer's stated
   age/profession/city; the catchphrase appears naturally once; no cringe or
   age-inappropriate slang for the persona's age.
8. CAPTION: includes a disclaimer line (the bot appends it automatically — do not flag
   it as missing), no clickbait.

Return ONLY JSON:
{{
  "approved": true/false,
  "verdict": "approve" | "fix" | "reject",
  "issues": ["human-readable issue strings"],
  "fixed_script": {{ ...full corrected script JSON if verdict is fix, else null }}
}}

If verdict is "fix", fixed_script must be the COMPLETE corrected script JSON.
Reject only when the content is unfactual, unsafe, or bad-faith beyond repair.
If the script is fine, verdict is "approve" and approved is true."""
        try:
            result = gemini_json(prompt, VERIFY_SYSTEM, temperature=0.2)
        except HttpError:
            raise  # verification infrastructure failure -> abort the run (never post unverified)
        verdict = str(result.get("verdict", "reject")).lower()
        if verdict == "approve":
            log(f"verification: APPROVED (attempt {attempt})")
            return "approve", script
        if verdict == "fix" and isinstance(result.get("fixed_script"), dict) and attempt < VERIFY_MAX_ATTEMPTS:
            log(f"verification: FIX requested (attempt {attempt}) — applying corrections: {result.get('issues')}", "WARN")
            script = result["fixed_script"]
            continue
        log(f"verification: REJECTED (attempt {attempt}) — {result.get('issues')}", "ERROR")
        return "reject", script
    return "reject", script


# ------------------------------------------------------------------ voices
def pick_voice(bilingual: bool) -> str:
    if bilingual:
        return BILINGUAL_VOICE_ID  # multilingual v2 premade voice — speaks Hindi + English
    return VOICE_ID


# ------------------------------------------------------------------ slots
def resolve_slot(args, state: dict, today: str) -> int:
    if args.slot:
        return args.slot
    override = env("SLOT_OVERRIDE")
    if override:
        return int(override)
    hour = datetime.now(UTC).hour
    if 1 <= hour <= 6:
        return 1
    if 12 <= hour <= 16:
        return 2
    posted = {(h["date"], h["slot"]) for h in state["history"] if h.get("status") in ("posted", "skipped", "rejected")}
    for s in range(1, POSTS_PER_DAY + 1):
        if (today, s) not in posted:
            return s
    return 1


# ------------------------------------------------------------------ pipeline
def run_once(content: dict, state: dict, args) -> int:
    today = args.date or datetime.now(IST).strftime("%Y-%m-%d")
    month_key = today[:7]
    slot = resolve_slot(args, state, today)
    seed = int(today.replace("-", "")) * 10 + slot
    rng = random.Random(seed)

    log(f"=== reels bot run start: date={today} slot={slot} platforms={PLATFORMS} bilingual={BILINGUAL} ===")

    if slot > POSTS_PER_DAY:
        log(f"slot {slot} is disabled (POSTS_PER_DAY={POSTS_PER_DAY}). Nothing to do.", "SKIP")
        return 0

    posted_this_month = sum(1 for h in state["history"] if h.get("date", "").startswith(month_key) and h.get("status") == "posted")
    if posted_this_month >= MAX_MONTHLY_POSTS:
        log(f"monthly budget reached ({posted_this_month}/{MAX_MONTHLY_POSTS}). Nothing to do.", "SKIP")
        return 0

    if not FORCE and any(
        h.get("date") == today and h.get("slot") == slot and h.get("status") in ("posted", "skipped", "rejected")
        for h in state["history"]
    ):
        log(f"slot {slot} on {today} already handled. Nothing to do.", "SKIP")
        return 0

    # ------------------------------------------------------- pick the content
    want_news = NEWS_ENABLED and NEWS_SLOT > 0 and slot == NEWS_SLOT
    news_item = None
    if want_news:
        news_item = pick_news(state)
        if news_item:
            log(f"news reel: [{news_item['source']}] {news_item['title'][:100]}", kind="news")
        else:
            log("no fresh market news found — falling back to the evergreen bank", "WARN")

    spec = build_news_spec(news_item, today, slot, rng) if news_item else build_bank_spec(content, state, today, slot, rng)

    # ------------------------------------------------- assign the influencer
    inf_data = load_influencers()
    influencers = inf_data["influencers"]
    persona = pick_influencer(spec, influencers)
    spec["persona"] = persona
    spec["actor_desc"] = build_actor_description(persona, inf_data)
    log(f"planned reel {spec['reel_id']} — {spec['topic']} / {spec['subtopic'][:60]} / {spec['angle']}",
        reel_id=spec["reel_id"], kind=spec["kind"], lang_order=spec["lang_order"], slot=slot, date=today)
    log(f"influencer: {persona['name']} ({persona['age']}, {persona['gender']}, {persona['city']}) — {persona['profession']} [{persona['id']}]",
        persona_id=persona["id"])
    log(f"language flip: {spec['lang_order']}")

    if args.dry_run:
        print("\n----- DRY RUN — nothing was generated, verified or posted -----")
        print("kind       :", spec["kind"], "| lang order:", spec["lang_order"])
        print("reel id    :", spec["reel_id"])
        print("influencer :", f"{persona['name']} · {persona['age']} · {persona['profession']} · {persona['city']} · {persona['handle']}")
        print("catchphrase:", persona["catchphrase"])
        print("actor desc :", spec["actor_desc"][:220], "…")
        if news_item:
            print("news source:", news_item["source"], "|", news_item["link"])
            print("news title :", news_item["title"])
        print("brief      :")
        print(spec["brief"][:700])
        print("\ncaption top:", spec["caption_top"])
        print("hashtags   :", " ".join(spec["hashtags"]))
        print("-----------------------------------------------------------------\n")
        return 0

    # ------------------------------------------------- 1. write (Gemini)
    log("step 1/5: Gemini writes the bilingual script…")
    script = build_script(spec)
    issues = validate_script(script)
    if issues:
        log(f"script schema issues: {issues} — repairing timings", "WARN")
        script = repair_script(script)
        issues = validate_script(script)
        if issues:
            raise HttpError(0, f"script failed schema validation after repair: {issues}")
    script["use_script_subtitles"] = True if BILINGUAL else False
    log(f"script: {str(script.get('title'))[:80]} | segments=5 | {spec['lang_order']}")
    for w in engagement_warnings(script):
        log(f"engagement warning: {w}", "WARN")

    # ------------------------------------------------- 2. verify (Gemini)
    log("step 2/5: Gemini verification gate (correctness + authenticity + compliance)…")
    verdict, script = verify_script(script, spec)
    if verdict != "approve":
        log(f"verification verdict: REJECT — NOT posting this reel. {spec['reel_id']}", "ERROR")
        state["history"].append({
            "date": today, "slot": slot, "reel_id": spec["reel_id"], "kind": spec["kind"],
            "topic": spec["topic"], "status": "rejected",
            "ts": datetime.now(IST).isoformat(timespec="seconds"),
        })
        state["history"] = state["history"][-HISTORY_LIMIT:]
        save_state(state)
        return 0

    # ------------------------------------------------- 3. generate
    voice_id = persona.get("voice_id") or pick_voice(BILINGUAL)
    generate_body = {
        "script": script,
        "voice_id": voice_id,
        "actor_description": spec.get("actor_desc") or None,
        "selected_actor_url": persona.get("avatar_url") or None,
        "video_mode": VIDEO_MODE,
        "share_to_gallery": False,
    }
    gen_headers = {}
    if FAL_KEY:
        gen_headers["X-Fal-Key"] = FAL_KEY
    if ELEVENLABS_KEY:
        gen_headers["X-ElevenLabs-Key"] = ELEVENLABS_KEY
    log(f"step 3/5: generating reel (mode={VIDEO_MODE}, influencer={persona['name']}, voice={voice_id}, avatar={'reused' if persona.get('avatar_url') else 'generated fresh'})…")
    _, generated = http("POST", "/api/saasshorts/generate", generate_body, headers=gen_headers, timeout=600)
    job_id = generated.get("job_id")
    if not job_id:
        raise HttpError(0, f"generate returned no job_id: {str(generated)[:200]}")
    log(f"generate job started: {job_id}", job_id=job_id)

    # ------------------------------------------------- 4. poll
    log("step 4/5: waiting for render…")
    deadline = time.time() + MAX_WAIT_MINUTES * 60
    result = None
    while time.time() < deadline:
        _, status = http("GET", f"/api/saasshorts/status/{job_id}")
        st = status.get("status")
        result = status.get("result") or {}
        if st == "completed":
            log(f"render completed: {str(result.get('video_url'))[:100]}", job_id=job_id)
            break
        if st == "failed":
            raise HttpError(0, f"generation failed. last logs: {str((status.get('logs') or [])[-3:])[:300]}")
        last_log = (status.get("logs") or [""])[-1]
        log(f"…{st}: {last_log[:100]}", level="STATUS")
        time.sleep(60)
    else:
        raise HttpError(0, f"timed out after {MAX_WAIT_MINUTES} min waiting for {job_id}")

    # ------------------------------------------------- 5. publish
    persona_credit = (
        f"With {persona['name']}, {persona['age']} - {persona['profession']}, {persona['city']}. "
        f"Follow {persona['handle']}"
    )
    caption_parts = [spec["caption_top"], script.get("caption") or "", persona_credit]
    if news_item:
        caption_parts.append(f"\U0001F4F0 Source: {news_item['source']} ({news_item['link']})")
    caption_parts.append(" ".join(spec["hashtags"]))
    caption_parts.append(DISCLAIMER_BILINGUAL)
    caption = "\n\n".join(p for p in caption_parts if p and p.strip())

    post_body = {
        "job_id": job_id,
        "platforms": PLATFORMS,
        "title": (spec["hook"] or spec["subtopic"])[:80],
        "description": caption,
        "timezone": "Asia/Kolkata",
    }
    if UP_KEY:
        post_body["api_key"] = UP_KEY
    if UP_USER:
        post_body["user_id"] = UP_USER
    log(f"step 5/5: publishing to {PLATFORMS}…", job_id=job_id)
    try:
        _, posted = http("POST", "/api/saasshorts/post", post_body, timeout=300)
    except HttpError as e:
        log(f"publish failed ({e}); retrying once in 60s…", "WARN")
        time.sleep(60)
        _, posted = http("POST", "/api/saasshorts/post", post_body, timeout=300)
    log(f"publish response: {str(posted)[:200]}", job_id=job_id)

    # ------------------------------------------------- bookkeeping
    if spec["kind"] == "bank":
        state["counters"][spec["topic_id"]] = spec["counter"] + 1
    if news_item:
        state["news_used"].append({"hash": news_item["hash"], "date": today})
        state["news_used"] = state["news_used"][-NEWS_USED_LIMIT:]
    state["history"].append({
        "date": today, "slot": slot, "reel_id": spec["reel_id"], "kind": spec["kind"],
        "topic_id": spec["topic_id"], "topic": spec["topic"],
        "subtopic": spec["subtopic"], "lang_order": spec["lang_order"],
        "persona_id": persona["id"], "persona_name": persona["name"],
        "source": news_item["source"] if news_item else None,
        "news_link": news_item["link"] if news_item else None,
        "job_id": job_id, "video_url": result.get("video_url"),
        "platforms": PLATFORMS, "status": "posted",
        "verified": True,
        "ts": datetime.now(IST).isoformat(timespec="seconds"),
    })
    state["history"] = state["history"][-HISTORY_LIMIT:]
    save_state(state)
    log(f"=== posted reel {spec['reel_id']} ({spec['lang_order']}) to {PLATFORMS} — done. ===",
        status="posted", reel_id=spec["reel_id"])
    return 0


# ------------------------------------------------------------------ drive
def absolutize(url: str) -> str:
    if url.startswith(("http://", "https://")):
        return url
    return API_URL + (url if url.startswith("/") else "/" + url)


def download_video(video_url: str, job_id: str = "") -> str:
    """Download the finished reel MP4 from the OpenShorts server."""
    os.makedirs(MEDIA_DIR, exist_ok=True)
    abs_url = absolutize(video_url)
    name = os.path.basename(video_url.split("?")[0]) or "reel.mp4"
    dest = os.path.join(MEDIA_DIR, f"{job_id}_{name}" if job_id else name)
    log(f"downloading reel: {abs_url[:120]}")
    req = urllib.request.Request(abs_url, headers={"User-Agent": "openshorts-reels-bot/2.0"})
    with urllib.request.urlopen(req, timeout=600) as resp:
        with open(dest, "wb") as f:
            while True:
                chunk = resp.read(1024 * 1024)
                if not chunk:
                    break
                f.write(chunk)
    size = os.path.getsize(dest)
    if size == 0:
        raise HttpError(0, f"downloaded empty file from {abs_url}")
    log(f"downloaded {size / 1e6:.1f} MB -> {dest}")
    return dest


def deliver_to_drive(local_path: str, drive_name: str) -> dict:
    """Upload the MP4 to the configured shared Drive folder."""
    if DRIVE_DRY_RUN:
        return {"file_id": f"sim-{abs(hash(drive_name))}", "name": drive_name,
                "webViewLink": "(dry run - DRIVE_DRY_RUN=1)"}
    if not DRIVE_FOLDER_ID:
        raise HttpError(0, "DRIVE_FOLDER_ID is missing - set the shared folder id")
    if not os.environ.get("DRIVE_SA_JSON"):
        raise HttpError(0, "DRIVE_SA_JSON is missing - add the service account key secret")
    cmd = [sys.executable, os.path.join(BASE_DIR, "drive_upload.py"), local_path, drive_name]
    import subprocess
    log(f"uploading to Drive folder {DRIVE_FOLDER_ID}: {drive_name}")
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=900, cwd=BASE_DIR)
    if proc.returncode != 0:
        raise HttpError(0, f"drive upload failed: {proc.stderr.strip()[:300]}")
    try:
        return json.loads(proc.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError) as e:
        raise HttpError(0, f"drive upload returned unexpected output: {e}")


def safe_drive_name(name: str) -> str:
    return re.sub(r"[^\w\s\-.,()\[\]\u0900-\u097F]", "", name)[:120].strip() or "reel.mp4"


# ------------------------------------------------------------------ launch
def load_launch_batch() -> dict:
    with open(LAUNCH_FILE, encoding="utf-8") as f:
        return json.load(f)


def launch_once(state: dict) -> int:
    """Generate the pre-drafted 10-reel batch (one per topic) and deliver it
    per DELIVERY_MODE (default: Google Drive only - no Instagram posting).
    Every pre-written script still passes through the Gemini verification gate."""
    batch = load_launch_batch()
    items = batch.get("items", [])
    log(f"=== LAUNCH BATCH: {len(items)} pre-drafted reels | delivery={DELIVERY_MODE} ===")
    inf_data = load_influencers()
    influencers = inf_data["influencers"]
    by_id = {p["id"]: p for p in influencers}
    results = []
    for idx, item in enumerate(items, 1):
        persona = by_id.get(item["persona_id"])
        if not persona:
            raise HttpError(0, f"launch item {item['reel_id']}: unknown persona {item['persona_id']}")
        spec = {
            "kind": "launch", "reel_id": item["reel_id"], "topic_id": item["topic_id"],
            "topic": f"Launch: {item['title']}", "subtopic": item["title"],
            "lang_order": item["lang_order"], "ground_truth": item["ground_truth"],
            "caption_top": item["caption_top"], "hashtags": item["hashtags"],
            "persona": persona, "angle": "Launch batch",
        }
        log(f"[{idx}/{len(items)}] {item['reel_id']} — {item['title']} | {persona['name']} ({persona['age']}) | {item['lang_order']}")

        script = item["script"]
        issues = validate_script(script)
        if issues:
            log(f"launch script schema issues: {issues} - repairing timings", "WARN")
            script = repair_script(script)
            issues = validate_script(script)
            if issues:
                raise HttpError(0, f"{item['reel_id']} failed schema validation after repair: {issues}")
        script["use_script_subtitles"] = True if BILINGUAL else False

        # verification gate (mandatory even for pre-drafted scripts)
        verdict, script = verify_script(script, spec)
        if verdict != "approve":
            log(f"launch reel {item['reel_id']} REJECTED by the gate - skipping. {spec['ground_truth'][:80]}", "ERROR")
            state["history"].append({
                "date": datetime.now(IST).strftime("%Y-%m-%d"), "slot": 0,
                "reel_id": item["reel_id"], "kind": "launch", "status": "rejected",
                "persona_id": persona["id"], "persona_name": persona["name"],
                "ts": datetime.now(IST).isoformat(timespec="seconds"),
            })
            continue

        # generate
        voice_id = persona.get("voice_id") or pick_voice(BILINGUAL)
        generate_body = {
            "script": script,
            "voice_id": voice_id,
            "actor_description": script.get("actor_description") or None,
            "selected_actor_url": persona.get("avatar_url") or None,
            "video_mode": VIDEO_MODE,
            "share_to_gallery": False,
        }
        gen_headers = {}
        if FAL_KEY:
            gen_headers["X-Fal-Key"] = FAL_KEY
        if ELEVENLABS_KEY:
            gen_headers["X-ElevenLabs-Key"] = ELEVENLABS_KEY
        _, generated = http("POST", "/api/saasshorts/generate", generate_body, headers=gen_headers, timeout=600)
        job_id = generated.get("job_id")
        if not job_id:
            raise HttpError(0, f"generate returned no job_id for {item['reel_id']}")
        log(f"  generate job {job_id} (voice={voice_id})", job_id=job_id)

        deadline = time.time() + MAX_WAIT_MINUTES * 60
        result = None
        while time.time() < deadline:
            _, status = http("GET", f"/api/saasshorts/status/{job_id}")
            st = status.get("status")
            result = status.get("result") or {}
            if st == "completed":
                break
            if st == "failed":
                raise HttpError(0, f"{item['reel_id']} generation failed: {str((status.get('logs') or [])[-3:])[:200]}")
            time.sleep(30)
        else:
            raise HttpError(0, f"timeout waiting for {item['reel_id']} ({job_id})")
        log(f"  render completed: {str(result.get('video_url'))[:90]}")

        entry = {
            "date": datetime.now(IST).strftime("%Y-%m-%d"), "slot": 0,
            "reel_id": item["reel_id"], "kind": "launch", "topic_id": item["topic_id"],
            "topic": item["title"], "lang_order": item["lang_order"],
            "persona_id": persona["id"], "persona_name": persona["name"],
            "job_id": job_id, "video_url": result.get("video_url"),
            "verified": True,
        }

        # delivery
        if "drive" in DELIVERY_MODE.split(","):
            local = download_video(result.get("video_url") or "", job_id=job_id)
            drive_name = safe_drive_name(f"{item['reel_id']} - {item['title']} - {persona['name']}.mp4")
            info = deliver_to_drive(local, drive_name)
            entry["drive_file_id"] = info.get("file_id")
            entry["drive_link"] = info.get("webViewLink")
            entry["status"] = "delivered"
            log(f"  -> Drive: {info.get('file_id')} ({info.get('webViewLink')})")
        if "instagram" in DELIVERY_MODE.split(","):
            caption_parts = [item["caption_top"], (script.get("caption") or ""),
                             f"With {persona['name']}, {persona['age']} - {persona['profession']}, {persona['city']}.",
                             " ".join(item["hashtags"]), DISCLAIMER_BILINGUAL]
            caption = "\n\n".join(p for p in caption_parts if p and p.strip())
            post_body = {"job_id": job_id, "platforms": PLATFORMS,
                         "title": item["title"][:80], "description": caption, "timezone": "Asia/Kolkata"}
            if UP_KEY:
                post_body["api_key"] = UP_KEY
            if UP_USER:
                post_body["user_id"] = UP_USER
            _, posted = http("POST", "/api/saasshorts/post", post_body, timeout=300)
            entry["status"] = "posted"
            log(f"  -> Instagram: {str(posted)[:120]}")
        if "status" not in entry:
            entry["status"] = "generated"

        entry["ts"] = datetime.now(IST).isoformat(timespec="seconds")
        state["history"].append(entry)
        results.append(entry)

    state["launch_done"] = datetime.now(IST).isoformat(timespec="seconds")
    state["history"] = state["history"][-HISTORY_LIMIT:]
    save_state(state)
    ok = sum(1 for e in results if e.get("status") in ("delivered", "posted"))
    log(f"=== LAUNCH BATCH done: {ok}/{len(items)} delivered, {len(items) - ok} skipped/rejected ===")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="plan only, no API calls")
    parser.add_argument("--slot", type=int, choices=[1, 2], help="slot override (1=morning, 2=evening)")
    parser.add_argument("--date", help="override today's date as YYYY-MM-DD (testing)")
    parser.add_argument("--force", action="store_true", help="rerun even if the slot already posted")
    parser.add_argument("--launch", action="store_true", help="run the 10-reel launch batch (delivery per DELIVERY env)")
    args = parser.parse_args()

    content = load_content()
    state = load_state()
    try:
        if args.launch or LAUNCH:
            return launch_once(state)
        return run_once(content, state, args)
    except HttpError as e:
        log(f"HTTP error: {e}", "ERROR")
        return 1
    except Exception as e:
        log(f"unexpected error: {e!r}", "ERROR")
        return 1


if __name__ == "__main__":
    sys.exit(main())
