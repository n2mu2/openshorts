#!/usr/bin/env python3
"""Tiny local test double for the OpenShorts API + Gemini + a news RSS feed.

Usage:
    python3 mock_server.py [port]        # default 8099
    OPENSHORTS_API_URL=http://127.0.0.1:8099 GEMINI_API_URL=http://127.0.0.1:8099 \\
    GEMINI_API_KEY=test FAL_API_KEY=x ELEVENLABS_API_KEY=x \\
    NEWS_SOURCE_URLS=http://127.0.0.1:8099/news/rss.xml \\
        python3 reels_bot.py --slot 1 --force

Lets you verify the whole pipeline (news fetch, bilingual script, verification
gate, generation, publish) without real services or costs. Stdlib only.
"""

import json
import sys
import uuid
from http.server import BaseHTTPRequestHandler, HTTPServer

JOBS = {}  # job_id -> {"polls": int, "status": str}

BILINGUAL_SCRIPT = {
    "title": "NIFTY explained — bilingual demo",
    "style": "educational",
    "duration_seconds": 21,
    "target_platform": "instagram",
    "hook_text": "NIFTY samajh lo",
    "segments": [
        {"type": "hook", "start": 0, "end": 4,
         "narration": "रुको! क्या आपको पता है NIFTY असल में क्या है?",
         "visual": "actor_talking", "broll_prompt": None, "emotion": "excited",
         "subtitle_text": "Wait! Do you actually know what NIFTY is?"},
        {"type": "problem", "start": 4, "end": 8,
         "narration": "ज़्यादातर लोग इसे सिर्फ एक नंबर समझते हैं, और यहीं गलती होती है।",
         "visual": "broll", "broll_prompt": "Indian stock exchange screen with falling numbers, confused young investor",
         "emotion": "concerned",
         "subtitle_text": "Most people see it as just a number — and that is the mistake."},
        {"type": "solution", "start": 8, "end": 15,
         "narration": "NIFTY is simply a scoreboard of India's 50 biggest companies.",
         "visual": "actor_talking", "broll_prompt": None, "emotion": "confident",
         "subtitle_text": "NIFTY बस भारत की 50 सबसे बड़ी कंपनियों का स्कोरबोर्ड है।"},
        {"type": "demo", "start": 15, "end": 19,
         "narration": "When those companies do well, the scoreboard rises. That's it.",
         "visual": "broll", "broll_prompt": "Rising green candlestick chart on a clean dashboard",
         "emotion": "excited",
         "subtitle_text": "जब ये कंपनियां अच्छा करती हैं, स्कोरबोर्ड ऊपर जाता है। बस इतना ही।"},
        {"type": "cta", "start": 19, "end": 21,
         "narration": "Follow for one market concept every day. Save this!",
         "visual": "actor_talking", "broll_prompt": None, "emotion": "friendly",
         "subtitle_text": "रोज़ एक मार्केट कॉन्सेप्ट के लिए फॉलो करें!"},
    ],
    "full_narration": "रुको! क्या आपको पता है NIFTY असल में क्या है? ज़्यादातर लोग इसे सिर्फ एक नंबर समझते हैं, और यहीं गलती होती है। NIFTY is simply a scoreboard of India's 50 biggest companies. When those companies do well, the scoreboard rises. That's it. Follow for one market concept every day. Save this!",
    "actor_description": "Indian woman in her early 30s, friendly and trustworthy, casual modern clothing",
    "hashtags": ["#Nifty", "#StockMarketBasics"],
    "caption": "NIFTY explained in 21 seconds.\nNIFTY को 21 सेकंड में समझें।",
}

VERIFY_APPROVE = {"approved": True, "verdict": "approve", "issues": [], "fixed_script": None}
VERIFY_FIX_ONCE = {"approved": False, "verdict": "fix", "issues": ["minor wording"], "fixed_script": BILINGUAL_SCRIPT}

RSS_XML = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel>
<title>Mock News</title><link>http://127.0.0.1:8099</link><description>test feed</description>
<item>
 <title>NIFTY ne banaya naya record, Sensex 200 points up</title>
 <link>http://mock.test/nifty-record</link>
 <pubDate>Thu, 21 Aug 2026 09:00:00 +0530</pubDate>
 <description>Stock markets closed at a fresh high today with NIFTY gaining 0.5% led by banking stocks.</description>
</item>
<item>
 <title>UPSC EPFO APFC Recruitment 2026: 80 पदों के लिए ऑनलाइन आवेदन शुरू</title>
 <link>http://mock.test/upsc-jobs</link>
 <pubDate>Thu, 21 Aug 2026 08:30:00 +0530</pubDate>
 <description>Jobs notification details for government recruitment.</description>
</item>
<item>
 <title>RBI keeps repo rate unchanged at 6.5%</title>
 <link>http://mock.test/rbi-rate</link>
 <pubDate>Thu, 21 Aug 2026 07:00:00 +0530</pubDate>
 <description>The central bank held the policy rate steady for the third straight meeting.</description>
</item>
</channel></rss>"""


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, obj, raw=None):
        if raw is not None:
            body = raw.encode()
        else:
            body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json" if raw is None else "application/rss+xml")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read(self):
        length = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(length) or b"{}")

    def log_message(self, fmt, *args):  # quieter
        pass

    def do_GET(self):
        if self.path == "/health":
            return self._send(200, {"status": "ok"})
        if self.path.startswith("/news/rss.xml"):
            return self._send(200, {}, raw=RSS_XML)
        if self.path.startswith("/api/saasshorts/status/"):
            job_id = self.path.rsplit("/", 1)[-1]
            job = JOBS.get(job_id)
            if not job:
                return self._send(404, {"detail": "job not found"})
            job["polls"] += 1
            if job["polls"] >= 2:
                job["status"] = "completed"
            return self._send(200, {
                "status": job["status"],
                "logs": [f"poll {job['polls']}", "rendering…", "compositing…"],
                "result": {
                    "video_url": f"/videos/saas_{job_id}/demo_final.mp4",
                    "script": {"title": "Demo reel"},
                } if job["status"] == "completed" else None,
            })
        return self._send(404, {"detail": "not found"})

    def do_POST(self):
        body = self._read()
        # Gemini generateContent (script writing + verification gate)
        if "generateContent" in self.path:
            text = ""
            try:
                text = body["contents"][0]["parts"][0]["text"]
                if body.get("systemInstruction"):
                    text += " " + body["systemInstruction"]["parts"][0]["text"]
            except (KeyError, IndexError, TypeError):
                pass
            if "TASK: SCRIPT" in text:
                return self._send(200, {"candidates": [{"content": {"parts": [{"text": json.dumps(BILINGUAL_SCRIPT, ensure_ascii=False)}]}}]})
            if "TASK: VERIFY" in text:
                if "FORCE_REJECT" in text:
                    return self._send(200, {"candidates": [{"content": {"parts": [{"text": json.dumps({"approved": False, "verdict": "reject", "issues": ["contains buy/sell advice"], "fixed_script": None})}]}}]})
                return self._send(200, {"candidates": [{"content": {"parts": [{"text": json.dumps(VERIFY_APPROVE)}]}}]})
            return self._send(200, {"candidates": [{"content": {"parts": [{"text": "{}"}]}}]})
        if self.path == "/api/saasshorts/analyze":
            return self._send(200, {"analysis": {}, "scripts": [BILINGUAL_SCRIPT], "web_research": None})
        if self.path == "/api/saasshorts/generate":
            job_id = str(uuid.uuid4())
            JOBS[job_id] = {"polls": 0, "status": "processing"}
            print(f"[mock] generate: script={str(body.get('script', {}).get('title'))[:50]} voice={body.get('voice_id')}", flush=True)
            return self._send(200, {"job_id": job_id, "status": "processing"})
        if self.path == "/api/saasshorts/post":
            print(f"[mock] POST to {body.get('platforms')}: {str(body.get('title'))[:60]}", flush=True)
            return self._send(200, {"success": True, "message": "queued (mock)"})
        return self._send(404, {"detail": "not found"})


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8099
    server = HTTPServer(("127.0.0.1", port), Handler)
    print(f"mock OpenShorts+Gemini+News API on http://127.0.0.1:{port}", flush=True)
    server.serve_forever()
