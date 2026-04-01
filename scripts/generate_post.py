#!/usr/bin/env python3
"""
GrowthStacker Auto Blog - Content Generator
Uses Gemini 2.0 Flash (free tier) to generate SEO-optimized blog posts
All secrets loaded from environment variables (GitHub Secrets)
"""

import os
import json
import random
import re
import sys
import time
from datetime import datetime
from pathlib import Path

# ── Dependency check ────────────────────────────────────────────────────────
try:
    import requests
except ImportError:
    print("[ERROR] requests not installed. Run: pip install requests")
    sys.exit(1)

# ── Config ───────────────────────────────────────────────────────────────────
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
BLOGGER_TOKEN  = os.environ.get("BLOGGER_ACCESS_TOKEN", "")
BLOGGER_BLOG_ID = os.environ.get("BLOGGER_BLOG_ID", "")

CONFIG_DIR = Path(__file__).parent.parent / "config"
TOPICS_FILE = CONFIG_DIR / "topics.json"
STATE_FILE  = CONFIG_DIR / "rotation_state.json"

GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-2.0-flash:generateContent"
)

# ── Rotation state ───────────────────────────────────────────────────────────

def load_state() -> dict:
    """Load current rotation state (which niche is next, which topics used)."""
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return {"rotation_index": 0, "used_topics": {}}


def save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def pick_topic(niche_key: str, niche_cfg: dict, used: list) -> str:
    """Pick a seed topic not yet used, or reset if all used."""
    seeds = niche_cfg["seed_topics"]
    available = [t for t in seeds if t not in used]
    if not available:
        available = seeds  # reset cycle
    topic = random.choice(available)
    return topic


def build_keyword(topic: str, niche_cfg: dict) -> str:
    """Transform seed topic into search-intent keyword."""
    prefix = random.choice(niche_cfg["keyword_prefixes"])
    suffix = random.choice(niche_cfg["keyword_suffixes"])
    # If topic already starts with a verb, use it directly
    if any(topic.lower().startswith(v) for v in ["how", "best", "top", "review"]):
        return f"{topic} {suffix}"
    return f"{prefix} {topic} {suffix}"

# ── Prompt builder ────────────────────────────────────────────────────────────

SYSTEM_INSTRUCTION = """
You are an expert SEO blog writer for the site growthstacker.blogspot.com,
targeting US audiences for Google AdSense monetization.

WRITING RULES:
- Grade 6-8 reading level, natural human English
- Short paragraphs (2-4 lines max)
- Use bullet points only where genuinely helpful
- No keyword stuffing, no filler content
- Include ONE unique angle not found in typical AI blogs
- Every article must feel written by a real person who has tested the tools

SEO RULES:
- Primary keyword in: title, first 100 words, one H2, meta description
- LSI keywords woven naturally throughout
- Internal link anchors: suggest 2-3 related article topics at the end
- Target featured snippet with a direct answer in first 2 paragraphs

OUTPUT FORMAT: Return valid HTML only. No markdown. No code fences.
Structure:
<article>
  <h1>Title</h1>
  <p class="intro">Introduction paragraph...</p>
  [rest of article in HTML]
  <section class="faq">
    <h2>Frequently Asked Questions</h2>
    [3-5 FAQ items as <details><summary> pairs]
  </section>
  <p class="thumbnail-prompt">THUMBNAIL: [image prompt]</p>
</article>
"""


def build_prompt(keyword: str, content_type: str, niche_label: str) -> str:
    type_instructions = {
        "how_to": (
            "Write a complete how-to guide. Include numbered steps, "
            "real tool names, and at least one specific use case "
            "(e.g., a freelancer using this to earn extra income)."
        ),
        "review": (
            "Write an honest review. Include: quick verdict summary box, "
            "pros/cons, pricing info, who it's best for, "
            "and one honest limitation most reviewers skip."
        ),
        "tutorial": (
            "Write a beginner-friendly tutorial with exact steps. "
            "Include screenshots descriptions (e.g., 'Click the blue button labeled...'), "
            "common mistakes to avoid, and a quick-start checklist."
        ),
    }

    instruction = type_instructions.get(content_type, type_instructions["how_to"])

    return f"""
Target keyword: "{keyword}"
Niche: {niche_label}
Content type: {content_type}

{instruction}

MANDATORY STRUCTURE:
1. H1 title (SEO-optimized, curiosity-driven, includes keyword)
2. Hook intro: open with a surprising stat or relatable problem (2-3 sentences)
3. TL;DR summary (1 sentence — the direct answer for featured snippets)
4. Why it matters / context section
5. Main content (steps / review sections / tutorial)
6. Practical tips section (3-5 actionable tips not commonly mentioned)
7. Conclusion with clear takeaway
8. FAQ section (3-5 questions, each answer 40-80 words)
9. Related articles suggestions (2-3 topic ideas for internal linking)
10. THUMBNAIL prompt at the very end

Word count: 1,200–1,800 words.
Do NOT include generic AI disclaimers. Write as a knowledgeable human expert.
""".strip()

# ── Gemini API call ───────────────────────────────────────────────────────────

def call_gemini(prompt: str) -> str:
    """Call Gemini 2.0 Flash API and return generated text."""
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY environment variable is not set")

    payload = {
        "system_instruction": {"parts": [{"text": SYSTEM_INSTRUCTION}]},
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.82,
            "topP": 0.92,
            "maxOutputTokens": 4096,
        },
        "safetySettings": [
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_ONLY_HIGH"},
        ],
    }

    headers = {"Content-Type": "application/json"}
    params  = {"key": GEMINI_API_KEY}

    for attempt in range(3):
        try:
            resp = requests.post(
                GEMINI_URL, json=payload, headers=headers,
                params=params, timeout=60
            )
            resp.raise_for_status()
            data = resp.json()
            candidates = data.get("candidates", [])
            if not candidates:
                raise ValueError(f"No candidates in response: {data}")
            return candidates[0]["content"]["parts"][0]["text"]
        except requests.HTTPError as e:
            print(f"[WARN] Gemini attempt {attempt+1}/3 failed: {e}")
            if attempt < 2:
                time.sleep(5 * (attempt + 1))
            else:
                raise

# ── HTML post builder ─────────────────────────────────────────────────────────

def wrap_html(article_html: str, keyword: str, niche: str) -> dict:
    """
    Wrap raw Gemini HTML output into a complete Blogger-ready post object.
    Returns dict with title, content, labels, meta description.
    """
    # Extract title from H1
    title_match = re.search(r"<h1[^>]*>(.*?)</h1>", article_html, re.IGNORECASE | re.DOTALL)
    title = re.sub(r"<[^>]+>", "", title_match.group(1)).strip() if title_match else keyword

    # Extract thumbnail prompt (remove from body)
    thumb_match = re.search(r"<p[^>]*class=['\"]thumbnail-prompt['\"][^>]*>(.*?)</p>",
                             article_html, re.IGNORECASE | re.DOTALL)
    thumbnail_prompt = ""
    if thumb_match:
        thumbnail_prompt = thumb_match.group(1).replace("THUMBNAIL:", "").strip()
        article_html = article_html.replace(thumb_match.group(0), "")

    # Build AdSense-friendly wrapper with inline styles
    full_html = f"""
<div style="font-family: Georgia, serif; max-width: 780px; margin: 0 auto; color: #222; line-height: 1.75;">
  {article_html}
  <!-- Auto-generated by GrowthStacker Pipeline | {datetime.utcnow().strftime('%Y-%m-%d')} -->
</div>
""".strip()

    # Build meta description from intro
    intro_match = re.search(r"<p[^>]*class=['\"]intro['\"][^>]*>(.*?)</p>",
                             article_html, re.IGNORECASE | re.DOTALL)
    if intro_match:
        raw_intro = re.sub(r"<[^>]+>", "", intro_match.group(1)).strip()
        meta_desc = raw_intro[:155] + ("…" if len(raw_intro) > 155 else "")
    else:
        meta_desc = f"Discover {keyword} — practical tips, tools, and strategies to grow your income online."

    # Labels for Blogger (tags)
    label_map = {
        "ai_make_money":  ["AI Tools", "Make Money Online", "Passive Income", "Side Hustle"],
        "product_review": ["Product Reviews", "Tech Tools", "Software Reviews"],
        "tech_tutorial":  ["Tech Tutorials", "How To", "Beginner Guide", "SEO"],
    }
    labels = label_map.get(niche, ["Blog"])

    return {
        "title": title,
        "content": full_html,
        "labels": labels,
        "meta_description": meta_desc,
        "thumbnail_prompt": thumbnail_prompt,
        "keyword": keyword,
    }

# ── Blogger publish ───────────────────────────────────────────────────────────

def publish_to_blogger(post: dict) -> dict:
    """Publish post to Blogger via API v3."""
    if not BLOGGER_TOKEN or not BLOGGER_BLOG_ID:
        raise ValueError("BLOGGER_ACCESS_TOKEN or BLOGGER_BLOG_ID not set")

    url = f"https://www.googleapis.com/blogger/v3/blogs/{BLOGGER_BLOG_ID}/posts/"
    headers = {
        "Authorization": f"Bearer {BLOGGER_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "kind": "blogger#post",
        "blog": {"id": BLOGGER_BLOG_ID},
        "title": post["title"],
        "content": post["content"],
        "labels": post["labels"],
        "status": "LIVE",
    }

    resp = requests.post(url, json=payload, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.json()

# ── Save local backup ─────────────────────────────────────────────────────────

def save_local(post: dict, niche_key: str) -> None:
    date_str = datetime.utcnow().strftime("%Y-%m-%d")
    out_dir = Path(__file__).parent.parent / "logs"
    out_dir.mkdir(parents=True, exist_ok=True)
    fname = out_dir / f"{date_str}_{niche_key}.json"
    with open(fname, "w", encoding="utf-8") as f:
        json.dump({
            "date": date_str,
            "niche": niche_key,
            "title": post["title"],
            "keyword": post["keyword"],
            "meta_description": post["meta_description"],
            "thumbnail_prompt": post["thumbnail_prompt"],
            "labels": post["labels"],
            "content_length": len(post["content"]),
        }, f, indent=2, ensure_ascii=False)
    print(f"[INFO] Local backup saved: {fname}")

# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    print(f"\n{'='*60}")
    print(f"  GrowthStacker Auto-Blog | {datetime.utcnow().isoformat()}Z")
    print(f"{'='*60}\n")

    # Load config and state
    with open(TOPICS_FILE) as f:
        config = json.load(f)

    state = load_state()
    rotation = config["rotation"]

    niche_key = rotation[state["rotation_index"] % len(rotation)]
    niche_cfg = config["niches"][niche_key]

    used = state.setdefault("used_topics", {}).get(niche_key, [])

    topic   = pick_topic(niche_key, niche_cfg, used)
    keyword = build_keyword(topic, niche_cfg)

    print(f"[INFO] Niche      : {niche_cfg['label']}")
    print(f"[INFO] Seed topic : {topic}")
    print(f"[INFO] Keyword    : {keyword}")

    # Generate content
    print("[INFO] Calling Gemini 2.0 Flash...")
    prompt       = build_prompt(keyword, niche_cfg["content_type"], niche_cfg["label"])
    raw_html     = call_gemini(prompt)

    print(f"[INFO] Generated {len(raw_html)} chars")

    # Process
    post = wrap_html(raw_html, keyword, niche_key)
    print(f"[INFO] Title: {post['title']}")

    # Save local backup (always, even if publish fails)
    save_local(post, niche_key)

    # Publish to Blogger
    if BLOGGER_TOKEN and BLOGGER_BLOG_ID:
        print("[INFO] Publishing to Blogger...")
        result = publish_to_blogger(post)
        print(f"[SUCCESS] Published: {result.get('url', 'unknown URL')}")
    else:
        print("[WARN] BLOGGER credentials not set — skipping publish (dry run mode)")

    # Update state
    used.append(topic)
    state["used_topics"][niche_key] = used
    state["rotation_index"] = (state["rotation_index"] + 1) % len(rotation)
    save_state(state)

    print(f"\n[DONE] Next niche: {rotation[state['rotation_index'] % len(rotation)]}\n")


if __name__ == "__main__":
    main()
