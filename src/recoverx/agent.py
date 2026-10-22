"""Opt-in, short-lived read-only report bridge. No paths or disk operations accepted remotely."""

import argparse
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import secrets
import time
from urllib.parse import parse_qs, urlsplit

from .store import Store


def make_server(db_path, scan_id, origin, token, port=0, ttl=600):
    parsed = urlsplit(origin)
    if parsed.scheme != "https" or parsed.path or parsed.query or parsed.fragment or not parsed.netloc:
        raise ValueError("Pair one exact HTTPS origin without a trailing slash")
    if len(token) < 32 or not 1 <= ttl <= 600:
        raise ValueError("Invalid pairing token or lifetime")
    expires = time.monotonic() + ttl

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass  # Headers, tokens, paths and filenames are never logged.

        def setup(self):
            super().setup()
            self.connection.settimeout(5)

        def respond(self, status, body):
            data = json.dumps(body).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            if self.headers.get("Origin") == origin:
                self.send_header("Access-Control-Allow-Origin", origin)
                self.send_header("Vary", "Origin")
            self.end_headers()
            self.wfile.write(data)

        def valid_context(self):
            return (
                self.headers.get("Host") == f"127.0.0.1:{self.server.server_port}"
                and self.headers.get("Origin") == origin
                and time.monotonic() < expires
            )

        def do_OPTIONS(self):
            if not self.valid_context():
                return self.respond(403, {"error": "Origin or host rejected"})
            self.send_response(204)
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Access-Control-Allow-Methods", "GET")
            self.send_header("Access-Control-Allow-Headers", "Authorization")
            self.send_header("Vary", "Origin")
            self.end_headers()

        def do_GET(self):
            if not self.valid_context():
                return self.respond(403, {"error": "Pairing context rejected or expired"})
            if not secrets.compare_digest(self.headers.get("Authorization", ""), f"Bearer {token}"):
                return self.respond(401, {"error": "Pairing required"})
            path = urlsplit(self.path)
            if path.path == "/health":
                return self.respond(
                    200,
                    {
                        "version": "0.1.0",
                        "scope": "one scan, read-only",
                        "expires_in": max(0, int(expires - time.monotonic())),
                    },
                )
            if path.path != f"/api/v1/scans/{scan_id}/results":
                return self.respond(404, {"error": "Endpoint unavailable"})
            try:
                offset = int(parse_qs(path.query).get("offset", ["0"])[0])
                if not 0 <= offset <= 10_000_000:
                    raise ValueError("Invalid offset")
            except ValueError:
                return self.respond(400, {"error": "Invalid pagination"})
            store = Store(db_path)
            try:
                report = [c.to_dict() for c in store.results(scan_id, offset, 100)]
                for c in report:
                    c.pop("original_path", None)
                self.respond(200, {"candidates": report, "offset": offset, "total": store.count(scan_id)})
            finally:
                store.close()

    server = HTTPServer(("127.0.0.1", port), Handler)
    server.timeout = 1
    server.expires = expires
    return server


def main():
    parser = argparse.ArgumentParser(description="Explicitly pair a read-only report bridge for 10 minutes")
    parser.add_argument("db")
    parser.add_argument("scan_id")
    parser.add_argument("--origin", required=True)
    parser.add_argument("--consent", action="store_true", required=True)
    args = parser.parse_args()
    store = Store(args.db)
    store.get(args.scan_id)
    store.close()
    token = secrets.token_urlsafe(32)
    server = make_server(args.db, args.scan_id, args.origin, token)
    print(f"Read-only pairing at http://127.0.0.1:{server.server_port}")
    print(f"Pairing token (valid 10 minutes): {token}")
    print(
        "Ctrl+C disconnects immediately. Browser localhost policy may block this bridge; report import is the default."
    )
    try:
        while time.monotonic() < server.expires:
            server.handle_request()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
