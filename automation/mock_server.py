#!/usr/bin/env python3
"""Tiny local test double for the OpenShorts API (AI Shorts subset).

Usage:
    python3 mock_server.py [port]        # default 8099
    OPENSHORTS_API_URL=http://127.0.0.1:8099 FAL_API_KEY=x ELEVENLABS_API_KEY=x \\
        python3 reels_bot.py --slot 1 --force

Lets you verify the whole bot pipeline end-to-end without a real OpenShorts
server or API keys. Stdlib only.
"""

import json
import sys
import time
import uuid
from http.server import BaseHTTPRequestHandler, HTTPServer

JOBS = {}          # job_id -> {"polls": int, "status": str}
SCRIPTS = [
    {
        "title": "The 40-second explainer",
        "hook": "Stop scrolling. Support and resistance, in plain words.",
        "caption": "Follow for one chart concept every day. Comment LEVELS for the free cheat sheet.",
        "full_narration": " ".join(["support and resistance explained simply."] * 40),
        "hashtags": ["#PriceAction"],
    },
    {
        "title": "The myth-buster",
        "hook": "Forget everything you heard about support and resistance. Start here.",
        "caption": "Save this before your next chart session.",
        "full_narration": " ".join(["the real story of support and resistance."] * 30),
    },
    {
        "title": "Bad advice script (should be rejected)",
        "hook": "Buy this stock now!",
        "caption": "Buy this stock, guaranteed profit, target price 500.",
        "full_narration": "buy this sell this recommendation guaranteed profit " * 30,
    },
]


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
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
        if self.path == "/api/saasshorts/analyze":
            return self._send(200, {"analysis": {}, "scripts": SCRIPTS, "web_research": None})
        if self.path == "/api/saasshorts/generate":
            job_id = str(uuid.uuid4())
            JOBS[job_id] = {"polls": 0, "status": "processing"}
            return self._send(200, {"job_id": job_id, "status": "processing"})
        if self.path == "/api/saasshorts/post":
            print(f"[mock] POST to platforms {body.get('platforms')}: {body.get('title')}", flush=True)
            return self._send(200, {"success": True, "message": "queued (mock)"})
        return self._send(404, {"detail": "not found"})


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8099
    server = HTTPServer(("127.0.0.1", port), Handler)
    print(f"mock OpenShorts API on http://127.0.0.1:{port}", flush=True)
    server.serve_forever()
