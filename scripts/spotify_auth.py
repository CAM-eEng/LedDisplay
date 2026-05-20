#!/usr/bin/env python3
"""One-time host-side OAuth helper for the Spotify currently-playing scope.

Usage:
    python3 scripts/spotify_auth.py --client-id <id> --client-secret <secret>

Steps:
  1. Spins up a one-shot HTTP server on http://127.0.0.1:8080/callback.
  2. Opens the Spotify authorize URL in the user's browser.
  3. Captures the redirect's code, exchanges it for a refresh_token.
  4. Prints settings.toml lines to paste into the project's settings.toml.

The Spotify Developer app must have http://127.0.0.1:8080/callback registered
as a redirect URI (exact match — Spotify rejects the hostname "localhost").
"""
import argparse
import http.server
import json
import secrets
import sys
import urllib.parse
import urllib.request
import webbrowser


REDIRECT_URI = "http://127.0.0.1:8080/callback"
SCOPE = "user-read-currently-playing"
HOST = "127.0.0.1"
PORT = 8080

_captured = {"code": None, "state": None, "error": None}


class _CallbackHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path != "/callback":
            self.send_response(404)
            self.end_headers()
            return
        q = urllib.parse.parse_qs(parsed.query)
        _captured["code"] = q.get("code", [None])[0]
        _captured["state"] = q.get("state", [None])[0]
        _captured["error"] = q.get("error", [None])[0]
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        if _captured["error"]:
            msg = "Spotify denied authorization: " + _captured["error"]
        else:
            msg = "Authorization captured. You can close this tab."
        self.wfile.write(
            ("<html><body><h2>" + msg + "</h2></body></html>").encode()
        )

    def log_message(self, fmt, *args):
        return  # silence default access log


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--client-id", required=True)
    p.add_argument("--client-secret", required=True)
    args = p.parse_args()

    state = secrets.token_urlsafe(16)
    authorize_url = "https://accounts.spotify.com/authorize?" + urllib.parse.urlencode(
        {
            "client_id": args.client_id,
            "response_type": "code",
            "redirect_uri": REDIRECT_URI,
            "scope": SCOPE,
            "state": state,
        }
    )

    print("Opening browser for Spotify authorization...")
    print("If it doesn't open, paste this URL into your browser:")
    print("  " + authorize_url)
    webbrowser.open(authorize_url)

    server = http.server.HTTPServer((HOST, PORT), _CallbackHandler)
    print("Waiting for the redirect on " + REDIRECT_URI + " ...")
    server.handle_request()
    server.server_close()

    if _captured["error"]:
        print("Spotify returned error:", _captured["error"], file=sys.stderr)
        sys.exit(1)
    if _captured["state"] != state:
        print("State mismatch — possible CSRF; aborting.", file=sys.stderr)
        sys.exit(1)
    if not _captured["code"]:
        print("No authorization code received.", file=sys.stderr)
        sys.exit(1)

    token_req = urllib.request.Request(
        "https://accounts.spotify.com/api/token",
        data=urllib.parse.urlencode(
            {
                "grant_type": "authorization_code",
                "code": _captured["code"],
                "redirect_uri": REDIRECT_URI,
                "client_id": args.client_id,
                "client_secret": args.client_secret,
            }
        ).encode(),
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        with urllib.request.urlopen(token_req, timeout=10) as resp:
            token_data = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        print("Token exchange failed:", e.code, e.read().decode(), file=sys.stderr)
        sys.exit(1)

    refresh = token_data.get("refresh_token")
    if not refresh:
        print("Spotify did not return a refresh_token:", token_data, file=sys.stderr)
        sys.exit(1)

    print()
    print("=== Success! ===")
    print("Add these lines to settings.toml (the file is gitignored):")
    print()
    print('SPOTIFY_CLIENT_ID = "{}"'.format(args.client_id))
    print('SPOTIFY_CLIENT_SECRET = "{}"'.format(args.client_secret))
    print('SPOTIFY_REFRESH_TOKEN = "{}"'.format(refresh))
    print('SPOTIFY_REFRESH_SEC = "10"')
    print()


if __name__ == "__main__":
    main()
