#!/usr/bin/env python3
"""Loopback-only signed-session validator; never serve this directly to the Internet."""
import base64
import hashlib
import hmac
import http.server
import json
import time
from http.cookies import SimpleCookie

with open("/etc/nginx/.stremio-session-key", "rb") as secret_file:
    SECRET = secret_file.read().strip()
TTL = 43200
NAME = "stremio_proxy_session"

def enc(value):
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode()

def dec(value):
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))

def sig(value):
    return enc(hmac.new(SECRET, value.encode(), hashlib.sha256).digest())

class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass

    def respond(self, status, headers=None):
        self.send_response(status)
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        if self.path == "/check":
            try:
                cookies = SimpleCookie()
                cookies.load(self.headers.get("Cookie", ""))
                payload, mac = cookies[NAME].value.rsplit(".", 1)
                obj = json.loads(dec(payload))
                now = time.time()
                if hmac.compare_digest(mac, sig(payload)) and now < obj["exp"] <= now + TTL + 60:
                    self.respond(204)
                    return
            except (KeyError, ValueError, TypeError, IndexError):
                pass
            self.respond(401)
        elif self.path == "/issue":
            user = self.headers.get("X-Authenticated-User", "")
            if not user or len(user) > 128:
                self.respond(403)
                return
            payload = enc(json.dumps(
                {"u": user, "exp": int(time.time()) + TTL},
                separators=(",", ":")).encode())
            token = payload + "." + sig(payload)
            self.respond(302, {
                "Set-Cookie": NAME + "=" + token +
                "; Path=/; Max-Age=" + str(TTL) +
                "; Secure; HttpOnly; SameSite=None",
                "Location": "/",
            })
        else:
            self.respond(404)

http.server.ThreadingHTTPServer(("127.0.0.1", 18765), Handler).serve_forever()
