"""
Social Media Content Engine — Configuration Loader
====================================================
Loads brand configuration from brand_config.json and API keys from .env.

To configure for your brand:
  1. Copy brand_config.example.json → brand_config.json
  2. Fill in your brand details, platforms, and content types
  3. Copy .env.example → .env and add your API keys
  4. Run: python engine.py
"""

import os
import json
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ── Paths ────────────────────────────────────────────────
BASE_DIR = Path(os.path.dirname(os.path.abspath(__file__)))
LOGS_DIR = BASE_DIR / "logs"
DATA_DIR = BASE_DIR / "data"
CONTENT_DIR = BASE_DIR / "content"
CLIPS_DIR = BASE_DIR / "clips"
TEMPLATES_DIR = BASE_DIR / "templates"
DASHBOARD_DIR = BASE_DIR / "dashboard"

for d in [LOGS_DIR, DATA_DIR, CONTENT_DIR, CLIPS_DIR, TEMPLATES_DIR, DASHBOARD_DIR]:
    d.mkdir(exist_ok=True)


# ── Load Brand Config ────────────────────────────────────
_config_path = BASE_DIR / "brand_config.json"
_example_path = BASE_DIR / "brand_config.example.json"

if not _config_path.exists():
    print(
        "\n[ERROR] brand_config.json not found.\n"
        f"Copy the example file and fill in your brand details:\n"
        f"  cp brand_config.example.json brand_config.json\n"
        f"Then edit brand_config.json with your brand name, pillars, voice, and platform handles.\n"
    )
    sys.exit(1)

with open(_config_path, "r", encoding="utf-8") as f:
    _cfg = json.load(f)


def _get(path: str, default=None):
    """Dot-path accessor for nested config values. e.g. _get('brand.voice.tone')"""
    keys = path.split(".")
    node = _cfg
    for key in keys:
        if not isinstance(node, dict) or key not in node:
            return default
        node = node[key]
    return node


# ── Brand Identity ───────────────────────────────────────
BRAND_NAME        = _get("brand.name", "My Brand")
BRAND_HANDLE      = _get("brand.handle", "@mybrand")
BRAND_TAGLINE     = _get("brand.tagline", "")
BRAND_DESCRIPTION = _get("brand.description", "")
BRAND_NICHE       = _get("brand.niche", "general")
BRAND_PILLARS     = _get("brand.pillars", ["content", "community", "education"])
BRAND_VOICE       = _get("brand.voice", {
    "tone": "Conversational and authentic.",
    "personality": "Helpful and direct.",
    "avoid": ["Generic filler", "Unverified claims"],
    "embrace": ["Specific information", "Personality"],
    "influences": [],
})
BRAND_COLORS = _get("brand.color_palette", {
    "primary":     "#1A1A2E",
    "secondary":   "#16213E",
    "accent":      "#E94560",
    "background":  "#F5F5F5",
    "text_light":  "#FFFFFF",
    "text_dark":   "#1A1A2E",
})


# ── Platform Constraints (fixed by platform, not user-configurable) ──────────
_PLATFORM_CONSTRAINTS = {
    "instagram": {
        "priority": 1,
        "post_types": ["carousel", "reel", "story", "single_image"],
        "max_hashtags": 30,
        "caption_max_chars": 2200,
    },
    "tiktok": {
        "priority": 2,
        "post_types": ["short_video", "photo_carousel"],
        "max_hashtags": 5,
        "caption_max_chars": 4000,
    },
    "youtube_shorts": {
        "priority": 3,
        "post_types": ["short"],
        "max_hashtags": 15,
        "description_max_chars": 5000,
    },
    "twitter": {
        "priority": 4,
        "post_types": ["text", "thread", "image"],
        "max_chars": 280,
    },
    "pinterest": {
        "priority": 5,
        "post_types": ["pin"],
        "description_max_chars": 500,
    },
}

# ── Platforms (merged: user config + platform constraints) ───────────────────
_user_platforms = _get("platforms", {})

PLATFORMS = {}
for platform_name, constraints in _PLATFORM_CONSTRAINTS.items():
    user_cfg = _user_platforms.get(platform_name, {})
    if not user_cfg.get("enabled", True):
        continue  # Skip disabled platforms
    PLATFORMS[platform_name] = {
        **constraints,
        "handle":       user_cfg.get("handle", ""),
        "daily_target": user_cfg.get("daily_target", 1),
        "optimal_times": user_cfg.get("optimal_times", ["09:00", "18:00"]),
    }

# If user hasn't configured any platforms, default to instagram + tiktok
if not PLATFORMS:
    for name in ("instagram", "tiktok"):
        PLATFORMS[name] = {**_PLATFORM_CONSTRAINTS[name], "handle": "", "daily_target": 1, "optimal_times": ["09:00"]}


# ── Content Types ────────────────────────────────────────
# Loaded from brand_config.json so users can define formats that fit their niche.
# Falls back to generic defaults if not configured.
_DEFAULT_CONTENT_TYPES = {
    "reaction": {
        "description": "React to something trending in your niche",
        "format": "short_video",
        "requires_face": True,
        "engagement_multiplier": 1.5,
    },
    "comparison": {
        "description": "Compare two things — good vs bad, before vs after",
        "format": "carousel",
        "requires_face": False,
        "engagement_multiplier": 1.3,
    },
    "showcase": {
        "description": "Show something you made, do, or use",
        "format": "single_image_or_reel",
        "requires_face": True,
        "engagement_multiplier": 1.0,
    },
    "myth_bust": {
        "description": "Correct a common misconception",
        "format": "carousel",
        "requires_face": False,
        "engagement_multiplier": 1.4,
    },
    "tutorial": {
        "description": "Quick how-to or skill demo",
        "format": "short_video",
        "requires_face": True,
        "engagement_multiplier": 1.2,
    },
    "deep_dive": {
        "description": "Educational carousel or thread on a niche topic",
        "format": "carousel_or_thread",
        "requires_face": False,
        "engagement_multiplier": 1.1,
    },
    "hot_take": {
        "description": "Strong, specific opinion on a trending topic",
        "format": "text_or_short_video",
        "requires_face": True,
        "engagement_multiplier": 1.6,
    },
    "recommendation": {
        "description": "Genuine product or resource recommendation",
        "format": "short_video_or_carousel",
        "requires_face": True,
        "engagement_multiplier": 0.9,
        "monetization": "affiliate",
    },
}

_user_content_types = _get("content_types", {})
# Remove internal comment keys before merging
CONTENT_TYPES = {
    k: v for k, v in {**_DEFAULT_CONTENT_TYPES, **_user_content_types}.items()
    if not k.startswith("_")
}


# ── ML Model Config ──────────────────────────────────────
_ml_cfg = _get("ml", {})
ML_CONFIG = {
    "min_training_samples": _ml_cfg.get("min_training_samples", 50),
    "retrain_interval_days": _ml_cfg.get("retrain_interval_days", 7),
    "target_variable": "engagement_composite",
    "engagement_weights": _ml_cfg.get("engagement_weights", {
        "views": 0.1,
        "likes": 0.3,
        "comments": 0.5,
        "shares": 1.5,
        "saves": 1.0,
        "clicks": 2.0,
        "affiliate_revenue": 5.0,
        "follows_gained": 3.0,
    }),
    "features": [
        "content_type", "pillar", "format", "has_face",
        "caption_length", "hook_type", "cta_type",
        "posting_hour", "posting_day", "trend_score",
        "competitor_coverage", "platform",
    ],
}


# ── API Keys ─────────────────────────────────────────────
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
OPENAI_API_KEY    = os.getenv("OPENAI_API_KEY", "")
SERPER_API_KEY    = os.getenv("SERPER_API_KEY", "")

if not ANTHROPIC_API_KEY:
    print("[WARNING] ANTHROPIC_API_KEY not set in .env — strategy agent will not work.")
if not SERPER_API_KEY:
    print("[WARNING] SERPER_API_KEY not set in .env — trend agent will not work.")


# ── Analytics Schema ─────────────────────────────────────
# Reference schema — every content record is tracked with these fields.
ANALYTICS_SCHEMA = {
    # Content metadata
    "content_id":           "unique identifier",
    "created_at":           "timestamp",
    "posted_at":            "timestamp per platform",
    "content_type":         "from CONTENT_TYPES",
    "pillar":               "from BRAND_PILLARS",
    "topic":                "specific topic string",
    "format":               "carousel | reel | single_image | text | thread | pin",
    "has_face":             "bool — did this include face-on-camera",
    "caption_length":       "int",
    "hashtags":             "list",
    "hook_type":            "question | statement | shock | story | statistic",
    "cta_type":             "none | follow | save | share | link | comment",
    "monetization":         "none | affiliate | product | brand",
    # Platform metrics
    "platform":             "instagram | tiktok | youtube_shorts | twitter | pinterest",
    "impressions":          "int",
    "views":                "int (video)",
    "likes":                "int",
    "comments":             "int",
    "shares":               "int",
    "saves":                "int",
    "clicks":               "int (link clicks)",
    "follows_gained":       "int",
    "watch_time_avg":       "float (seconds, video only)",
    "engagement_rate":      "float (calculated)",
    # Revenue
    "affiliate_clicks":     "int",
    "affiliate_revenue":    "float",
    "product_sales":        "int",
    "product_revenue":      "float",
    "estimated_creator_fund": "float",
    # ML features (derived)
    "posting_hour":         "int 0-23",
    "posting_day":          "int 0-6 (Monday=0)",
    "trend_score":          "float — how trending was the topic when posted",
    "competitor_coverage":  "int — how many competitors posted on this topic recently",
    "content_quality_score": "float — self-assessed quality 1-10",
}
