#!/usr/bin/env python3
"""
GrowthStacker - One-Time OAuth Setup
Run this ONCE locally to get your Google refresh token for Blogger API.

Requirements:
  pip install requests

Usage:
  python3 scripts/setup_oauth.py

What this does:
  1. Opens Google OAuth consent page in your browser
  2. You log in and approve
  3. Saves refresh token to .env.local (NOT committed to git)
  4. Prints instructions for adding to GitHub Secrets

SECURITY: .env.local is in .gitignore — never commit it.
"""

import os
import sys
import json
import webbrowser
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread

try:
    import requests
except ImportError:
    print("Install requests: pip install requests")
    sys.exit(1)

# ── Google OAuth config ───────────────────────────────────────────────────────
# These are PUBLIC values — safe to hardcode for installed apps
# You must create your own at: https://console.cloud.google.com/apis/credentials
# Create OAuth 2.0 Client ID → Desktop App

REDIRECT_URI  = "http://localhost:8765/callback"
SCOPES        = "https://www.googleapis.com/auth/blogger"

TOKEN_URL     = "https://oauth2.googleapis.com/token"
AUTH_URL      = "https://accounts.google.com/o/oauth2/v2/auth"

# ── Local callback server ─────────────────────────────────────────────────────
received_code = None


class CallbackHandler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass  # Suppress server logs

    def do_GET(self):
        global received_code
        parsed = urllib.parse.urlparse(self.path)
        params = dict(urllib.parse.parse_qsl(parsed.query))

        if "code" in params:
            received_code = params["code"]
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"""
<html><body style="font-family:sans-serif;text-align:center;padding:60px">
<h2 style="color:#1a73e8">Authorization successful!</h2>
<p>You can close this window and return to your terminal.</p>
</body></html>
""")
        else:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Authorization failed")


def run_server():
    server = HTTPServer(("localhost", 8765), CallbackHandler)
    server.handle_request()  # Handle exactly one request


# ── Main setup flow ───────────────────────────────────────────────────────────

def main():
    print("\n" + "="*60)
    print("  GrowthStacker — Blogger OAuth Setup")
    print("="*60)
    print()

    # Check for existing .env.local
    if os.path.exists(".env.local"):
        print("[!] .env.local already exists. Delete it to re-run setup.")
        sys.exit(0)

    print("You need a Google Cloud project with Blogger API enabled.")
    print("Create credentials at: https://console.cloud.google.com/apis/credentials")
    print("Choose: OAuth 2.0 Client ID → Desktop application\n")

    client_id = input("Enter your Google Client ID: ").strip()
    if not client_id:
        print("[ERROR] Client ID is required")
        sys.exit(1)

    client_secret = input("Enter your Google Client Secret: ").strip()
    if not client_secret:
        print("[ERROR] Client Secret is required")
        sys.exit(1)

    blogger_blog_id = input("Enter your Blogger Blog ID (from blogspot URL): ").strip()

    gemini_key = input("Enter your Gemini API Key (from Google AI Studio): ").strip()

    # Build auth URL
    auth_params = {
        "client_id":     client_id,
        "redirect_uri":  REDIRECT_URI,
        "response_type": "code",
        "scope":         SCOPES,
        "access_type":   "offline",
        "prompt":        "consent",
    }
    auth_link = AUTH_URL + "?" + urllib.parse.urlencode(auth_params)

    # Start local server in background thread
    t = Thread(target=run_server, daemon=True)
    t.start()

    print(f"\n[INFO] Opening browser for Google authorization...")
    print(f"[INFO] If browser does not open, visit:\n{auth_link}\n")
    webbrowser.open(auth_link)

    # Wait for callback
    t.join(timeout=120)

    if not received_code:
        print("[ERROR] No authorization code received (timeout or error)")
        sys.exit(1)

    # Exchange code for tokens
    print("\n[INFO] Exchanging code for refresh token...")
    resp = requests.post(TOKEN_URL, data={
        "code":          received_code,
        "client_id":     client_id,
        "client_secret": client_secret,
        "redirect_uri":  REDIRECT_URI,
        "grant_type":    "authorization_code",
    }, timeout=15)
    resp.raise_for_status()
    tokens = resp.json()

    refresh_token = tokens.get("refresh_token")
    if not refresh_token:
        print(f"[ERROR] No refresh token in response: {tokens}")
        sys.exit(1)

    # Save to .env.local
    env_content = f"""# GrowthStacker local env — DO NOT COMMIT THIS FILE
GOOGLE_CLIENT_ID={client_id}
GOOGLE_CLIENT_SECRET={client_secret}
GOOGLE_REFRESH_TOKEN={refresh_token}
BLOGGER_BLOG_ID={blogger_blog_id}
GEMINI_API_KEY={gemini_key}
"""
    with open(".env.local", "w") as f:
        f.write(env_content)

    print("\n" + "="*60)
    print("  ✓ Setup Complete!")
    print("="*60)
    print()
    print("Saved to: .env.local (gitignored — NEVER commit this file)\n")
    print("Now add these to GitHub Secrets:")
    print("  Settings → Secrets and variables → Actions → New repository secret\n")
    print(f"  GOOGLE_CLIENT_ID     = {client_id}")
    print(f"  GOOGLE_CLIENT_SECRET = {client_secret}")
    print(f"  GOOGLE_REFRESH_TOKEN = {refresh_token}")
    print(f"  BLOGGER_BLOG_ID      = {blogger_blog_id}")
    print(f"  GEMINI_API_KEY       = {gemini_key}")
    print()
    print("After adding secrets, push this repo to GitHub.")
    print("The workflow will run daily at 09:00 UTC automatically.\n")


if __name__ == "__main__":
    main()
