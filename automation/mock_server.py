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
import os
import sys
import uuid
from http.server import BaseHTTPRequestHandler, HTTPServer

JOBS = {}  # job_id -> {"polls": int, "status": str}
FAST = os.environ.get("MOCK_FAST") == "1"
DUMMY_MP4 = b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 4096

BILINGUAL_SCRIPT = {
    "title": "NIFTY explained — long-format demo",
    "style": "educational",
    "duration_seconds": 75,
    "target_platform": "instagram",
    "hook_text": "NIFTY samajh lo",
    "segments": [
        {"type": "hook", "start": 0, "end": 6,
         "narration": "रुको! NIFTY कोई रहस्य नहीं है। Dekho, simple si baat hai... NIFTY सिर्फ एक स्कोरबोर्ड है, और आप इसे OVER-think कर रहे हो।",
         "visual": "actor_talking", "broll_prompt": None, "emotion": "excited",
         "subtitle_text": "Wait! NIFTY is not a mystery. See, it is simple... NIFTY is just a scoreboard, and you are OVER-thinking it."},
        {"type": "problem", "start": 6, "end": 18,
         "narration": "ज़्यादातर लोग NIFTY गिरता देख घबरा जाते हैं, जैसे पूरा बाज़ार डूब गया। जबकि असल में वह सिर्फ पचास कंपनियों का average score है। अब ईमानदारी से बताओ... आपके साथ भी ऐसा हुआ है?",
         "visual": "broll", "broll_prompt": "Indian street crowd staring up at a big red stock ticker screen, worried faces, evening city light",
         "emotion": "concerned",
         "subtitle_text": "Most people panic when NIFTY falls, as if the whole market drowned. Actually, it is just the average score of fifty companies. Now be honest... has it happened to you too?"},
        {"type": "solution", "start": 18, "end": 51,
         "narration": "Meri ek dost har subah NIFTY dekh kar panic ho jaati thi. Phir ek din maine use cricket ka example diya. NIFTY is simply a scoreboard of India's 50 biggest companies. Jab ye companies achha karti hain, score upar jaata hai... bilkul team ke total ki tarah. Ek player fail ho, toh bhi team jeet sakti hai. Samjhe point? Aur doosra example: petrol ke daam. Jab crude oil sasta hota hai, oil companies ka kharcha ghat-ta hai... aur unka profit badh sakta hai. Aise hi chhoti-chhoti cheezein NIFTY ka score banati hain. Koi jaadu nahi.",
         "visual": "actor_talking", "broll_prompt": None, "emotion": "confident",
         "subtitle_text": "A friend of mine used to panic every morning watching NIFTY. Then one day I gave her a cricket example. NIFTY is simply a scoreboard of India's 50 biggest companies. When these companies do well, the score rises... just like a team total. One player can fail and the team can still win. Got the point? And a second example: petrol prices. When crude oil gets cheaper, oil companies' costs fall... and their profit can rise. Small things like this make the NIFTY score. No magic."},
        {"type": "demo", "start": 51, "end": 66,
         "narration": "देखो, एक और आसान तरीका: scoreboard ki tarah socho. हर कंपनी का प्रदर्शन एक रन है, और NIFTY... टीम का टोटल। ऊपर-नीचे होना सामान्य है, डरना नहीं है।",
         "visual": "broll", "broll_prompt": "Cricket stadium scoreboard zooming into the team total, clean bright graphic, stadium lights",
         "emotion": "excited",
         "subtitle_text": "See, one more easy way: think of a scoreboard. Every company's performance is a run, and NIFTY... is the team total. Up and down is normal, not scary."},
        {"type": "cta", "start": 66, "end": 75,
         "narration": "अब कल से NIFTY को नई नज़र से देखोगे? Comment YES... aur follow karo daily market concepts ke liye. Share karna mat bhoolna, kisi dost ka panic bach jayega!",
         "visual": "actor_talking", "broll_prompt": None, "emotion": "friendly",
         "subtitle_text": "So will you see NIFTY differently from tomorrow? Comment YES... and follow for daily market concepts. Don't forget to share, you might save a friend's panic!"},
    ],
    "full_narration": "रुको! NIFTY कोई रहस्य नहीं है। Dekho, simple si baat hai... NIFTY सिर्फ एक स्कोरबोर्ड है, और आप इसे OVER-think कर रहे हो। ज़्यादातर लोग NIFTY गिरता देख घबरा जाते हैं, जैसे पूरा बाज़ार डूब गया। जबकि असल में वह सिर्फ पचास कंपनियों का average score है। अब ईमानदारी से बताओ... आपके साथ भी ऐसा हुआ है? Meri ek dost har subah NIFTY dekh kar panic ho jaati thi. Phir ek din maine use cricket ka example diya. NIFTY is simply a scoreboard of India's 50 biggest companies. Jab ye companies achha karti hain, score upar jaata hai... bilkul team ke total ki tarah. Ek player fail ho, toh bhi team jeet sakti hai. Samjhe point? Aur doosra example: petrol ke daam. Jab crude oil sasta hota hai, oil companies ka kharcha ghat-ta hai... aur unka profit badh sakta hai. Aise hi chhoti-chhoti cheezein NIFTY ka score banati hain. Koi jaadu nahi. देखो, एक और आसान तरीका: scoreboard ki tarah socho. हर कंपनी का प्रदर्शन एक रन है, और NIFTY... टीम का टोटल। ऊपर-नीचे होना सामान्य है, डरना नहीं है। अब कल से NIFTY को नई नज़र से देखोगे? Comment YES... aur follow karo daily market concepts ke liye. Share karna mat bhoolna, kisi dost ka panic bach jayega!",
    "actor_description": "Indian woman in her early 30s, friendly and trustworthy, casual modern clothing",
    "hashtags": ["#Nifty", "#StockMarketBasics"],
    "caption": "NIFTY explained in one minute.\nNIFTY को एक मिनट में समझें।",
}

VERIFY_APPROVE = {"approved": True, "verdict": "approve", "issues": [], "fixed_script": None}
VERIFY_FIX_ONCE = {"approved": False, "verdict": "fix", "issues": ["minor wording"], "fixed_script": BILINGUAL_SCRIPT}

RSS_XML = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel>
<title>Mock News</title><link>http://127.0.0.1:8099</link><description>test feed</description>
<item>
 <title>US Fed keeps rates steady, signals patient stance</title>
 <link>http://mock.test/fed-rates</link>
 <pubDate>Thu, 21 Aug 2026 05:30:00 +0530</pubDate>
 <description>The US Federal Reserve held interest rates steady overnight and signalled a patient approach.</description>
</item>
<item>
 <title>Wall Street ends lower as tech shares slide</title>
 <link>http://mock.test/wallstreet-tech</link>
 <pubDate>Thu, 21 Aug 2026 05:00:00 +0530</pubDate>
 <description>US stocks closed lower overnight with technology shares leading the decline.</description>
</item>
<item>
 <title>Crude oil prices rise on supply worries</title>
 <link>http://mock.test/crude-rise</link>
 <pubDate>Thu, 21 Aug 2026 04:30:00 +0530</pubDate>
 <description>Oil prices climbed as traders weighed supply concerns from key producers.</description>
</item>
<item>
 <title>Gold hits fresh record high, dollar steady</title>
 <link>http://mock.test/gold-record</link>
 <pubDate>Thu, 21 Aug 2026 04:00:00 +0530</pubDate>
 <description>Gold prices touched a new record while the dollar index held steady.</description>
</item>
<item>
 <title>Asian markets mixed as China data disappoints</title>
 <link>http://mock.test/asia-mixed</link>
 <pubDate>Thu, 21 Aug 2026 03:30:00 +0530</pubDate>
 <description>Asian equities traded mixed with Chinese economic data coming in below expectations.</description>
</item>
<item>
 <title>NIFTY ne banaya naya record, Sensex 200 points up</title>
 <link>http://mock.test/nifty-record</link>
 <pubDate>Thu, 21 Aug 2026 03:00:00 +0530</pubDate>
 <description>Stock markets closed at a fresh high today with NIFTY gaining led by banking stocks.</description>
</item>
<item>
 <title>UPSC EPFO APFC Recruitment 2026: 80 पदों के लिए ऑनलाइन आवेदन शुरू</title>
 <link>http://mock.test/upsc-jobs</link>
 <pubDate>Thu, 21 Aug 2026 02:30:00 +0530</pubDate>
 <description>Jobs notification details for government recruitment.</description>
</item>
<item>
 <title>RBI keeps repo rate unchanged at 6.5%</title>
 <link>http://mock.test/rbi-rate</link>
 <pubDate>Thu, 21 Aug 2026 02:00:00 +0530</pubDate>
 <description>The central bank held the policy rate steady for the third straight meeting.</description>
</item>
</channel></rss>"""


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, obj, raw=None, ctype=None):
        if raw is not None:
            body = raw.encode() if isinstance(raw, str) else raw
        else:
            body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype or ("application/json" if raw is None else "application/rss+xml"))
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
        if self.path.startswith("/videos/"):
            return self._send(200, {}, raw=DUMMY_MP4, ctype="video/mp4")
        if self.path.startswith("/api/saasshorts/status/"):
            job_id = self.path.rsplit("/", 1)[-1]
            job = JOBS.get(job_id)
            if not job:
                return self._send(404, {"detail": "job not found"})
            job["polls"] += 1
            if job["polls"] >= (1 if FAST else 2):
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
