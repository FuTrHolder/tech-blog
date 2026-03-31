#!/usr/bin/env python3
"""
GrowthStacker - Local Test Runner
Run before pushing to GitHub to verify the pipeline works.

Usage:
  python3 scripts/test_local.py

Loads credentials from .env.local (never from env vars directly).
Does NOT publish to Blogger by default (dry run).
"""

import os
import sys
import json
from pathlib import Path

# Load .env.local
env_file = Path(".env.local")
if not env_file.exists():
    print("[ERROR] .env.local not found. Run setup_oauth.py first.")
    sys.exit(1)

for line in env_file.read_text().splitlines():
    line = line.strip()
    if line and not line.startswith("#") and "=" in line:
        key, val = line.split("=", 1)
        os.environ[key.strip()] = val.strip()

print("✓ Loaded .env.local\n")

# Import after env is set
sys.path.insert(0, str(Path(__file__).parent))
from generate_post import (
    load_state, pick_topic, build_keyword,
    build_prompt, call_gemini, wrap_html, save_local
)
import json

CONFIG_PATH = Path(__file__).parent.parent / "config" / "topics.json"
with open(CONFIG_PATH) as f:
    config = json.load(f)

state = load_state()
rotation = config["rotation"]
niche_key = rotation[state["rotation_index"] % len(rotation)]
niche_cfg = config["niches"][niche_key]

used = state.get("used_topics", {}).get(niche_key, [])
topic   = pick_topic(niche_key, niche_cfg, used)
keyword = build_keyword(topic, niche_cfg)

print(f"Niche   : {niche_cfg['label']}")
print(f"Topic   : {topic}")
print(f"Keyword : {keyword}\n")

test_only = input("Test API call? (y/n, default=y): ").strip().lower()
if test_only == "n":
    print("[SKIP] Skipping API call.")
    sys.exit(0)

print("\nCalling Gemini API...")
try:
    prompt   = build_prompt(keyword, niche_cfg["content_type"], niche_cfg["label"])
    raw_html = call_gemini(prompt)
    print(f"✓ Generated {len(raw_html)} characters\n")

    post = wrap_html(raw_html, keyword, niche_key)
    print(f"Title   : {post['title']}")
    print(f"Labels  : {post['labels']}")
    print(f"Meta    : {post['meta_description'][:80]}...")
    print(f"Thumb   : {post['thumbnail_prompt'][:80]}...")

    save_local(post, niche_key)
    print("\n✓ Local backup saved to logs/")
    print("\n[DRY RUN] Not publishing to Blogger.")
    print("To publish, set BLOGGER_ACCESS_TOKEN and BLOGGER_BLOG_ID and run generate_post.py")

except Exception as e:
    print(f"[ERROR] {e}")
    sys.exit(1)
