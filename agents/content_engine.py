"""
Content Creation Engine — Brand-configurable carousel, image & pin generation.
Reads brand colors and handle from brand_config.json via config.py.
Modern minimal aesthetic: clean typography, subtle texture, strong hierarchy.
"""

import json
import os
import random
from datetime import datetime
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

# ── Brand Config ─────────────────────────────────────────
# Import brand-specific values from config (which loads brand_config.json)
try:
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from config import BRAND_HANDLE, BRAND_COLORS, BRAND_PILLARS, BRAND_NICHE
except Exception:
    BRAND_HANDLE = "@yourbrand"
    BRAND_COLORS = {
        "primary": "#1A1A2E", "secondary": "#16213E", "accent": "#E94560",
        "background": "#F5F5F5", "text_light": "#FFFFFF", "text_dark": "#1A1A2E",
    }
    BRAND_PILLARS = ["content", "community", "education"]
    BRAND_NICHE = "general"
