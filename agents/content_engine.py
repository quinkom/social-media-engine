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


# ── Color Utilities ──────────────────────────────────────

def _hex_to_rgb(color: str) -> tuple:
    """Convert hex color string to (R, G, B) tuple."""
    c = color.lstrip("#")
    return tuple(int(c[i:i+2], 16) for i in (0, 2, 4))


def _lighten(hex_color: str, amount: float = 0.15) -> str:
    """Lighten a hex color by blending toward white."""
    r, g, b = _hex_to_rgb(hex_color)
    r = int(r + (255 - r) * amount)
    g = int(g + (255 - g) * amount)
    b = int(b + (255 - b) * amount)
    return f"#{r:02X}{g:02X}{b:02X}"


def _darken(hex_color: str, amount: float = 0.15) -> str:
    """Darken a hex color by blending toward black."""
    r, g, b = _hex_to_rgb(hex_color)
    r = int(r * (1 - amount))
    g = int(g * (1 - amount))
    b = int(b * (1 - amount))
    return f"#{r:02X}{g:02X}{b:02X}"


def _is_dark(hex_color: str) -> bool:
    """Return True if the color is perceptually dark."""
    r, g, b = _hex_to_rgb(hex_color)
    luminance = 0.299 * r + 0.587 * g + 0.114 * b
    return luminance < 128


# ── Dynamic Palette Builder ──────────────────────────────

def _build_palettes() -> dict:
    """
    Build a set of visual palettes from BRAND_COLORS.

    Returns three named palettes:
      - "light"   : light background, dark text (default content slides)
      - "dark"    : dark background, light text (hook/CTA slides)
      - "accent"  : accent-colored background (special emphasis slides)
    Plus one per brand pillar, cycling through variants.
    """
    bg_light   = BRAND_COLORS.get("background", "#F5F5F5")
    bg_dark    = BRAND_COLORS.get("primary", "#1A1A2E")
    accent     = BRAND_COLORS.get("accent", "#E94560")
    accent2    = _lighten(accent, 0.2)
    text_light = BRAND_COLORS.get("text_light", "#FFFFFF")
    text_dark  = BRAND_COLORS.get("text_dark", "#1A1A2E")
    secondary  = BRAND_COLORS.get("secondary", "#16213E")
    surface    = _lighten(bg_light, 0.05) if _is_dark(bg_light) else _darken(bg_light, 0.04)
    muted      = _lighten(bg_dark, 0.35) if _is_dark(bg_dark) else _darken(bg_dark, 0.35)

    base = {
        "light": {
            "bg": bg_light, "bg_dark": bg_dark, "accent": accent, "accent2": accent2,
            "text": text_dark, "text_light": text_light, "muted": muted, "surface": surface,
        },
        "dark": {
            "bg": bg_dark, "bg_dark": bg_dark, "accent": accent, "accent2": accent2,
            "text": text_light, "text_light": text_light, "muted": muted, "surface": secondary,
        },
        "accent_bg": {
            "bg": accent, "bg_dark": _darken(accent, 0.2), "accent": bg_dark, "accent2": secondary,
            "text": text_light, "text_light": text_light, "muted": _lighten(accent, 0.4), "surface": accent2,
        },
        # Legacy fallback (used if pillar not mapped)
        "warning": {
            "bg": bg_dark, "bg_dark": bg_dark, "accent": "#E04040", "accent2": "#FF6B6B",
            "text": text_light, "text_light": text_light, "muted": muted, "surface": secondary,
        },
    }

    # Map each brand pillar to a palette variant, cycling through light/dark/accent
    variants = ["dark", "light", "accent_bg"]
    for i, pillar in enumerate(BRAND_PILLARS):
        base[pillar] = base[variants[i % len(variants)]]

    return base


PALETTES = _build_palettes()


def _get_palette(pillar: str) -> dict:
    """Get the right palette for a pillar, with fallback."""
    return PALETTES.get(pillar, PALETTES.get("dark", list(PALETTES.values())[0]))


# ── Font Utilities ───────────────────────────────────────

def _font(size: int, bold: bool = False, light: bool = False):
    """Load a font, trying Windows → Linux paths → default."""
    if light:
        paths = [
            "C:/Windows/Fonts/segoeuil.ttf",
            "C:/Windows/Fonts/arial.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        ]
    elif bold:
        paths = [
            "C:/Windows/Fonts/segoeuib.ttf",
            "C:/Windows/Fonts/arialbd.ttf",
            "C:/Windows/Fonts/calibrib.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        ]
    else:
        paths = [
            "C:/Windows/Fonts/segoeui.ttf",
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/calibri.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]
    for p in paths:
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            continue
    return ImageFont.load_default()


def _wrap(text: str, font, max_w: int, draw) -> list:
    """Word-wrap text to fit within max_w pixels."""
    words = text.split()
    lines, cur = [], ""
    for word in words:
        test = f"{cur} {word}".strip()
        if draw.textbbox((0, 0), test, font=font)[2] > max_w and cur:
            lines.append(cur)
            cur = word
        else:
            cur = test
    if cur:
        lines.append(cur)
    return lines


# ── Drawing Helpers ──────────────────────────────────────

def _grain(img, bg_hex: str, density: int = 6000):
    """Add a subtle film-grain texture overlay."""
    r0, g0, b0 = _hex_to_rgb(bg_hex)
    W, H = img.size
    for _ in range(density):
        x, y = random.randint(0, W - 1), random.randint(0, H - 1)
        n = random.randint(-6, 6)
        img.putpixel((x, y), (
            max(0, min(255, r0 + n)),
            max(0, min(255, g0 + n)),
            max(0, min(255, b0 + n)),
        ))


def _draw_rounded_rect(draw, xy: tuple, radius: int, fill):
    """Draw a filled rounded rectangle."""
    x0, y0, x1, y1 = xy
    r = min(radius, (x1 - x0) // 2, (y1 - y0) // 2)
    draw.rectangle([x0 + r, y0, x1 - r, y1], fill=fill)
    draw.rectangle([x0, y0 + r, x1, y1 - r], fill=fill)
    draw.pieslice([x0, y0, x0 + 2*r, y0 + 2*r], 180, 270, fill=fill)
    draw.pieslice([x1 - 2*r, y0, x1, y0 + 2*r], 270, 360, fill=fill)
    draw.pieslice([x0, y1 - 2*r, x0 + 2*r, y1], 90, 180, fill=fill)
    draw.pieslice([x1 - 2*r, y1 - 2*r, x1, y1], 0, 90, fill=fill)


# ── Carousel Slides ──────────────────────────────────────

def create_carousel_slides(content_piece: dict, output_dir: str = "content") -> list:
    """
    Generate premium carousel slides (1080x1350 portrait).
    Hook slide → content slides → CTA slide.
    Brand colors and handle are loaded from brand_config.json.
    """
    if not HAS_PIL:
        print("  [content_engine] PIL not installed — skipping image generation.")
        return []

    Path(output_dir).mkdir(exist_ok=True)
    slides_text = content_piece.get("slides", [])
    if not slides_text:
        return []

    pillar = content_piece.get("pillar", BRAND_PILLARS[0] if BRAND_PILLARS else "default")
    pal = _get_palette(pillar)
    pid = content_piece.get("piece_id", "unknown")
    total = len(slides_text)
    generated = []

    for idx, text in enumerate(slides_text):
        W, H = 1080, 1350
        is_first = idx == 0
        is_last = idx == total - 1

        # Alternate light/dark for visual rhythm; hook + every 3rd = dark
        use_dark = is_first or (idx % 3 == 0)
        bg     = pal["bg_dark"] if use_dark else pal["bg"]
        fg     = pal["text_light"] if use_dark else pal["text"]
        muted  = pal["muted"]
        accent = pal["accent"]

        img = Image.new("RGB", (W, H), bg)
        draw = ImageDraw.Draw(img)
        _grain(img, bg)

        if is_first:
            # ── HOOK SLIDE ──────────────────────────
            draw.rectangle([80, 120, 280, 124], fill=accent)

            pillar_label = pillar.replace("_", " ").upper()
            draw.text((80, 140), pillar_label, fill=muted, font=_font(16, light=True))

            hook = content_piece.get("hook", text)
            title_font = _font(54, bold=True)
            lines = _wrap(hook, title_font, W - 160, draw)
            line_h = 68
            block_h = len(lines) * line_h
            y = max(220, (H - block_h) // 2 - 60)
            for line in lines[:7]:
                draw.text((80, y), line, fill=fg, font=title_font)
                y += line_h

            draw.text((W - 160, H - 120), "SWIPE →", fill=accent, font=_font(14, bold=True))
            draw.text((80, H - 120), BRAND_HANDLE, fill=muted, font=_font(16))
            draw.text((W - 130, H - 80), f"1/{total}", fill=muted, font=_font(14))

        elif is_last:
            # ── CTA SLIDE ───────────────────────────
            cta = content_piece.get("cta", text) or text
            cta_font = _font(40, bold=True)
            lines = _wrap(cta, cta_font, W - 200, draw)
            line_h = 54
            block_h = len(lines) * line_h
            y = (H - block_h) // 2 - 30
            for line in lines[:5]:
                bx = draw.textbbox((0, 0), line, font=cta_font)
                lw = bx[2] - bx[0]
                draw.text(((W - lw) // 2, y), line, fill=fg, font=cta_font)
                y += line_h

            draw.rectangle([(W // 2 - 40), y + 20, (W // 2 + 40), y + 24], fill=accent)

            brand_font = _font(18)
            bx = draw.textbbox((0, 0), BRAND_HANDLE, font=brand_font)
            draw.text(((W - (bx[2] - bx[0])) // 2, y + 60), BRAND_HANDLE, fill=accent, font=brand_font)
            draw.text((W - 130, H - 80), f"{idx+1}/{total}", fill=muted, font=_font(14))

        else:
            # ── CONTENT SLIDE ────────────────────────
            # Split "Header: body text" or "Header\nbody"
            if ":" in text and text.index(":") < 60:
                header, body = text.split(":", 1)
                header, body = header.strip(), body.strip()
            elif "\n" in text:
                parts = text.split("\n", 1)
                header = parts[0].strip()
                body = parts[1].strip() if len(parts) > 1 else ""
            else:
                header, body = "", text

            y = 120

            # Large slide number in accent color
            num_font = _font(72, bold=True)
            draw.text((80, y), str(idx + 1), fill=accent, font=num_font)
            y += 100

            if header:
                h_font = _font(34, bold=True)
                h_lines = _wrap(header, h_font, W - 160, draw)
                for line in h_lines[:3]:
                    draw.text((80, y), line, fill=fg, font=h_font)
                    y += 46
                y += 16
                draw.rectangle([80, y, 300, y + 2], fill=accent)
                y += 28

            if body:
                b_font = _font(26)
                body_parts = body.split("•")
                if len(body_parts) > 1:
                    # Bulleted list
                    for part in body_parts:
                        part = part.strip()
                        if not part:
                            continue
                        draw.ellipse([88, y + 10, 98, y + 20], fill=accent)
                        b_lines = _wrap(part, b_font, W - 200, draw)
                        for line in b_lines[:3]:
                            draw.text((114, y), line, fill=fg, font=b_font)
                            y += 38
                        y += 12
                else:
                    b_lines = _wrap(body, b_font, W - 160, draw)
                    for line in b_lines[:18]:
                        draw.text((80, y), line, fill=fg, font=b_font)
                        y += 38

            draw.text((80, H - 80), BRAND_HANDLE, fill=muted, font=_font(14))
            draw.text((W - 130, H - 80), f"{idx+1}/{total}", fill=muted, font=_font(14))

        fname = f"{pid}_slide_{idx+1}.png"
        fpath = os.path.join(output_dir, fname)
        img.save(fpath, "PNG", quality=95)
        generated.append(fpath)

    return generated


# ── Single Image Post ────────────────────────────────────

def create_single_image(content_piece: dict, output_dir: str = "content") -> str | None:
    """Generate a single square image post (1080x1080)."""
    if not HAS_PIL:
        return None
    Path(output_dir).mkdir(exist_ok=True)

    pillar = content_piece.get("pillar", BRAND_PILLARS[0] if BRAND_PILLARS else "default")
    pal = _get_palette(pillar)
    pid = content_piece.get("piece_id", "unknown")

    W, H = 1080, 1080
    img = Image.new("RGB", (W, H), pal["bg_dark"])
    draw = ImageDraw.Draw(img)
    _grain(img, pal["bg_dark"])

    draw.rectangle([80, 200, 280, 204], fill=pal["accent"])

    hook = content_piece.get("hook", content_piece.get("title", ""))
    tf = _font(46, bold=True)
    lines = _wrap(hook, tf, W - 160, draw)
    y = 260
    for line in lines[:6]:
        draw.text((80, y), line, fill=pal["text_light"], font=tf)
        y += 62

    draw.text((80, H - 80), BRAND_HANDLE, fill=pal["muted"], font=_font(16))

    fpath = os.path.join(output_dir, f"{pid}_image.png")
    img.save(fpath, "PNG", quality=95)
    return fpath


# ── Pinterest Pin ────────────────────────────────────────

def create_pinterest_pin(content_piece: dict, output_dir: str = "content") -> str | None:
    """Generate a Pinterest-optimized pin (1000x1500)."""
    if not HAS_PIL:
        return None
    Path(output_dir).mkdir(exist_ok=True)

    pillar = content_piece.get("pillar", BRAND_PILLARS[0] if BRAND_PILLARS else "default")
    pal = _get_palette(pillar)
    pid = content_piece.get("piece_id", "unknown")

    W, H = 1000, 1500
    img = Image.new("RGB", (W, H), pal["bg_dark"])
    draw = ImageDraw.Draw(img)
    _grain(img, pal["bg_dark"], density=4000)

    # Accent header block
    draw.rectangle([0, 0, W, 360], fill=pal["accent"])

    hook = content_piece.get("hook", "")
    tf = _font(42, bold=True)
    lines = _wrap(hook, tf, W - 140, draw)
    y = 80
    for line in lines[:5]:
        draw.text((70, y), line, fill=pal["text_light"], font=tf)
        y += 56

    body = content_piece.get("body", "")
    if body:
        bf = _font(28)
        blines = _wrap(body[:350], bf, W - 140, draw)
        y = 420
        for line in blines[:12]:
            draw.text((70, y), line, fill=pal["text_light"], font=bf)
            y += 42

    # CTA bar at bottom
    cta = content_piece.get("cta", "Save for later")
    draw.rectangle([0, H - 80, W, H], fill=pal["accent"])
    cf = _font(22, bold=True)
    draw.text((70, H - 55), cta, fill=pal["text_light"], font=cf)
    draw.text((W - 220, H - 55), BRAND_HANDLE, fill=pal["text_light"], font=_font(18))

    fpath = os.path.join(output_dir, f"{pid}_pin.png")
    img.save(fpath, "PNG", quality=95)
    return fpath


# ── DALL-E Image Generation ──────────────────────────────

def generate_dalle_image(prompt: str, piece_id: str, output_dir: str = "content", openai_key: str = "") -> str | None:
    """Generate an image via DALL-E 3. Style is adapted to the brand's niche."""
    if not openai_key:
        return None
    try:
        from openai import OpenAI
        import requests as req
        client = OpenAI(api_key=openai_key)

        # Style prompt adapts to niche rather than hardcoding "food/fitness"
        style = f"Editorial photography for {BRAND_NICHE} content. Clean, minimal composition. Natural lighting. No text overlays."
        full_prompt = f"{prompt}. {style}"

        resp = client.images.generate(
            model="dall-e-3",
            prompt=full_prompt,
            size="1024x1024",
            quality="standard",
            n=1,
        )
        url = resp.data[0].url
        r = req.get(url, timeout=30)
        if r.status_code == 200:
            Path(output_dir).mkdir(exist_ok=True)
            fp = os.path.join(output_dir, f"{piece_id}_dalle.png")
            with open(fp, "wb") as f:
                f.write(r.content)
            return fp
    except Exception as e:
        print(f"  [DALL-E] Error: {e}")
    return None


# ── Video Processing ─────────────────────────────────────

def process_video_clip(clip_path: str, piece_id: str, caption_text: str = "", output_dir: str = "content") -> str | None:
    """Copy a raw clip to the output dir and save caption metadata."""
    import shutil
    Path(output_dir).mkdir(exist_ok=True)
    if not os.path.exists(clip_path):
        return None
    ext = os.path.splitext(clip_path)[1]
    out = os.path.join(output_dir, f"{piece_id}_video{ext}")
    shutil.copy2(clip_path, out)
    meta = {
        "video": out,
        "caption": caption_text,
        "brand_handle": BRAND_HANDLE,
        "created": datetime.now().isoformat(),
    }
    with open(os.path.join(output_dir, f"{piece_id}_captions.json"), "w") as f:
        json.dump(meta, f, indent=2)
    return out


# ── Master Builder ───────────────────────────────────────

def build_all_content(plan_data: dict, clips_dir: str = "clips", output_dir: str = "content", openai_key: str = "") -> dict:
    """
    Iterate over a content plan and generate all assets.
    Returns a dict keyed by piece_id with file paths and metadata.
    """
    pieces = plan_data.get("content_pieces", [])
    results = {}

    for piece in pieces:
        pid = piece.get("piece_id", "unknown")
        fmt = piece.get("format", "")
        print(f"  Building: {piece.get('title', pid)[:50]}")
        files = []

        if fmt == "carousel":
            slides = create_carousel_slides(piece, output_dir)
            files.extend(slides)
            if slides:
                print(f"    ✓ {len(slides)} carousel slides")

        elif fmt in ("single_image", "image"):
            img = create_single_image(piece, output_dir)
            if img:
                files.append(img)
                print("    ✓ Single image")

        elif fmt in ("short_video", "reel", "video", "short"):
            clip_id = piece.get("requires_clip", "")
            if clip_id and os.path.exists(clips_dir):
                matched = False
                for fn in os.listdir(clips_dir):
                    if clip_id.lower() in fn.lower():
                        v = process_video_clip(os.path.join(clips_dir, fn), pid, piece.get("body", ""), output_dir)
                        if v:
                            files.append(v)
                            print(f"    ✓ Clip processed")
                        matched = True
                        break
                if not matched:
                    print(f"    ⏳ Waiting for clip: {clip_id}")
            else:
                print("    ℹ No clip required")

        elif fmt == "pin":
            pin = create_pinterest_pin(piece, output_dir)
            if pin:
                files.append(pin)
                print("    ✓ Pinterest pin")

        elif fmt in ("text", "text_post", "thread"):
            print("    ✓ Text post (no image needed)")

        # DALL-E fallback for high-priority posts without images
        if piece.get("quality_priority") == "high" and openai_key and not files and fmt not in ("text", "text_post", "thread"):
            topic = piece.get("title", piece.get("hook", BRAND_NICHE))
            di = generate_dalle_image(f"Editorial photo for: {topic}", pid, output_dir, openai_key)
            if di:
                files.append(di)
                print("    ✓ DALL-E image generated")

        results[pid] = {
            "piece_id": pid,
            "title": piece.get("title", ""),
            "files": files,
            "caption": piece.get("body", ""),
            "hashtags": piece.get("hashtags", []),
            "platform": piece.get("platform", ""),
            "format": fmt,
            "status": "ready" if (files or fmt in ("text", "text_post", "thread")) else "waiting_for_clip",
        }

    return results
