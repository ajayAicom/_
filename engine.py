"""
MotionAI 30s Engine
Free local motion graphics video generator from reference photos.

This is not a paid API wrapper. It creates unlimited videos locally using
MoviePy + Pillow. Optional true image-to-video AI can be added later through
ComfyUI/Wan/CogVideoX if you have a GPU.
"""
from __future__ import annotations

import math
import os
import random
import tempfile
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps
from moviepy.editor import (
    AudioFileClip,
    CompositeVideoClip,
    ImageClip,
    concatenate_videoclips,
)
from moviepy.audio.fx.all import audio_loop
from moviepy.video.fx.all import fadein, fadeout


ASPECT_SIZES = {
    "1:1 Square": {"720p": (720, 720), "1080p": (1080, 1080)},
    "9:16 Reels/Shorts": {"720p": (720, 1280), "1080p": (1080, 1920)},
    "16:9 YouTube": {"720p": (1280, 720), "1080p": (1920, 1080)},
    "4:5 Instagram": {"720p": (720, 900), "1080p": (1080, 1350)},
}

STYLE_CONFIG = {
    "Cinematic": {
        "bg_blur": 22,
        "bg_dark": 0.45,
        "border": (255, 255, 255, 190),
        "text_bg": (0, 0, 0, 145),
        "text_fg": (255, 255, 255, 255),
        "accent": (255, 205, 120, 230),
    },
    "Product Premium": {
        "bg_blur": 30,
        "bg_dark": 0.25,
        "border": (255, 255, 255, 220),
        "text_bg": (255, 255, 255, 210),
        "text_fg": (20, 20, 20, 255),
        "accent": (255, 95, 80, 230),
    },
    "Birthday / Cake": {
        "bg_blur": 24,
        "bg_dark": 0.20,
        "border": (255, 240, 245, 225),
        "text_bg": (95, 20, 45, 160),
        "text_fg": (255, 255, 255, 255),
        "accent": (255, 180, 210, 235),
    },
    "Travel": {
        "bg_blur": 20,
        "bg_dark": 0.30,
        "border": (255, 255, 255, 200),
        "text_bg": (10, 45, 65, 155),
        "text_fg": (255, 255, 255, 255),
        "accent": (90, 210, 255, 230),
    },
    "Minimal Clean": {
        "bg_blur": 16,
        "bg_dark": 0.10,
        "border": (255, 255, 255, 185),
        "text_bg": (255, 255, 255, 190),
        "text_fg": (10, 10, 10, 255),
        "accent": (0, 0, 0, 180),
    },
}


def get_canvas_size(aspect: str, resolution: str) -> Tuple[int, int]:
    return ASPECT_SIZES.get(aspect, ASPECT_SIZES["9:16 Reels/Shorts"]).get(
        resolution, (720, 1280)
    )


def _safe_filename(name: str) -> str:
    allowed = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"
    clean = "".join(ch if ch in allowed else "_" for ch in name.strip())
    return clean[:64] or "motionai_video"


def _font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Bold.ttf" if bold else "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf",
        "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf",
        "/Library/Fonts/Arial Bold.ttf" if bold else "/Library/Fonts/Arial.ttf",
        "arialbd.ttf" if bold else "arial.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size=size)
        except Exception:
            continue
    return ImageFont.load_default()


def _cover_resize(img: Image.Image, size: Tuple[int, int]) -> Image.Image:
    return ImageOps.fit(img, size, method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))


def _contain_resize(img: Image.Image, max_size: Tuple[int, int]) -> Image.Image:
    im = img.copy()
    im.thumbnail(max_size, Image.Resampling.LANCZOS)
    return im


def _rounded_rect_mask(size: Tuple[int, int], radius: int) -> Image.Image:
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle((0, 0, size[0], size[1]), radius=radius, fill=255)
    return mask


def create_reference_canvas(
    image_path: str | Path,
    canvas_size: Tuple[int, int],
    style: str,
    index: int,
    total: int,
) -> str:
    """Build one polished still frame from a reference photo."""
    cfg = STYLE_CONFIG.get(style, STYLE_CONFIG["Cinematic"])
    w, h = canvas_size
    source = Image.open(image_path).convert("RGB")

    # blurred background from same reference photo
    bg = _cover_resize(source, canvas_size).filter(ImageFilter.GaussianBlur(cfg["bg_blur"]))
    dark_layer = Image.new("RGB", canvas_size, (0, 0, 0))
    bg = Image.blend(bg, dark_layer, cfg["bg_dark"])

    canvas = bg.convert("RGBA")

    # foreground photo with clean border and soft shadow
    margin_x = int(w * 0.075)
    margin_y = int(h * 0.12)
    fg = _contain_resize(source, (w - 2 * margin_x, h - 2 * margin_y)).convert("RGBA")
    radius = max(18, int(min(w, h) * 0.035))
    mask = _rounded_rect_mask(fg.size, radius)

    shadow_offset = max(8, int(min(w, h) * 0.018))
    shadow = Image.new("RGBA", fg.size, (0, 0, 0, 180))
    shadow.putalpha(mask.filter(ImageFilter.GaussianBlur(radius // 2)))

    x = (w - fg.width) // 2
    y = (h - fg.height) // 2
    canvas.alpha_composite(shadow, (x + shadow_offset, y + shadow_offset))

    fg.putalpha(mask)
    canvas.alpha_composite(fg, (x, y))

    # border
    draw = ImageDraw.Draw(canvas)
    border_width = max(2, int(min(w, h) * 0.004))
    for b in range(border_width):
        draw.rounded_rectangle(
            (x - b, y - b, x + fg.width + b, y + fg.height + b),
            radius=radius + b,
            outline=cfg["border"],
            width=1,
        )

    # small top progress dots / motion graphics touch
    dot_r = max(3, int(w * 0.006))
    gap = dot_r * 3
    start_x = w // 2 - ((total * dot_r * 2) + ((total - 1) * gap)) // 2
    top_y = int(h * 0.04)
    for i in range(total):
        color = cfg["accent"] if i == index else (255, 255, 255, 95)
        dx = start_x + i * (dot_r * 2 + gap)
        draw.ellipse((dx, top_y, dx + dot_r * 2, top_y + dot_r * 2), fill=color)

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    canvas.convert("RGB").save(tmp.name, quality=95)
    return tmp.name



def _normalize_instagram_handle(handle: Optional[str]) -> str:
    """Return a clean @handle string for watermark display."""
    value = (handle or "").strip()
    if not value:
        return ""
    value = value.replace("https://www.instagram.com/", "").replace("https://instagram.com/", "")
    value = value.strip().strip("/").split("?")[0]
    if not value.startswith("@"):
        value = f"@{value}"
    return value[:36]


def create_instagram_watermark_asset(
    handle: Optional[str],
    canvas_size: Tuple[int, int],
    opacity: float = 0.88,
) -> Optional[str]:
    """Create a transparent PNG watermark: Instagram-style icon + handle."""
    handle_text = _normalize_instagram_handle(handle)
    if not handle_text:
        return None

    w, h = canvas_size
    base = min(w, h)
    font_size = max(16, int(base * 0.035))
    icon_size = max(28, int(base * 0.060))
    pad_x = max(12, int(base * 0.022))
    pad_y = max(8, int(base * 0.014))
    gap = max(8, int(base * 0.014))
    font = _font(font_size, bold=True)

    dummy = Image.new("RGBA", (10, 10), (0, 0, 0, 0))
    d = ImageDraw.Draw(dummy)
    tb = d.textbbox((0, 0), handle_text, font=font)
    text_w = tb[2] - tb[0]
    text_h = tb[3] - tb[1]
    box_w = int(pad_x * 2 + icon_size + gap + text_w)
    box_h = int(max(icon_size, text_h) + pad_y * 2)

    img = Image.new("RGBA", (box_w, box_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    alpha_bg = int(120 * max(0.25, min(1.0, opacity)))
    alpha_fg = int(255 * max(0.25, min(1.0, opacity)))
    radius = box_h // 2
    draw.rounded_rectangle((0, 0, box_w - 1, box_h - 1), radius=radius, fill=(0, 0, 0, alpha_bg))

    ix = pad_x
    iy = (box_h - icon_size) // 2
    # Transparent Instagram-style camera icon (not an official asset file): outline, lens, small dot.
    outline_w = max(2, icon_size // 13)
    icon_outline = (255, 255, 255, alpha_fg)
    icon_accent = (255, 92, 142, alpha_fg)
    draw.rounded_rectangle(
        (ix, iy, ix + icon_size, iy + icon_size),
        radius=max(7, icon_size // 4),
        outline=icon_outline,
        width=outline_w,
    )
    lens_r = icon_size * 0.23
    cx = ix + icon_size * 0.50
    cy = iy + icon_size * 0.52
    draw.ellipse((cx - lens_r, cy - lens_r, cx + lens_r, cy + lens_r), outline=icon_outline, width=outline_w)
    dot_r = max(2, icon_size * 0.055)
    dot_cx = ix + icon_size * 0.73
    dot_cy = iy + icon_size * 0.28
    draw.ellipse((dot_cx - dot_r, dot_cy - dot_r, dot_cx + dot_r, dot_cy + dot_r), fill=icon_accent)

    tx = ix + icon_size + gap
    ty = (box_h - text_h) // 2 - max(0, int(font_size * 0.08))
    draw.text((tx, ty), handle_text, font=font, fill=(255, 255, 255, alpha_fg))

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    img.save(tmp.name)
    return tmp.name


def apply_instagram_watermark(
    canvas: Image.Image,
    handle: Optional[str],
    position: str = "Bottom Right",
) -> Image.Image:
    """Apply transparent Instagram-style watermark to a PIL canvas."""
    handle_text = _normalize_instagram_handle(handle)
    if not handle_text:
        return canvas
    rgba = canvas.convert("RGBA")
    wm_path = create_instagram_watermark_asset(handle_text, rgba.size)
    if not wm_path:
        return rgba
    try:
        wm = Image.open(wm_path).convert("RGBA")
        margin = max(14, int(min(rgba.size) * 0.030))
        pos = (position or "Bottom Right").lower()
        if "left" in pos:
            x = margin
        else:
            x = rgba.width - wm.width - margin
        if "top" in pos:
            y = margin
        else:
            y = rgba.height - wm.height - margin
        rgba.alpha_composite(wm, (max(0, x), max(0, y)))
        return rgba
    finally:
        try:
            os.remove(wm_path)
        except OSError:
            pass

def create_text_overlay(
    text: str,
    canvas_size: Tuple[int, int],
    style: str,
    placement: str = "bottom",
) -> Optional[str]:
    text = (text or "").strip()
    if not text:
        return None

    cfg = STYLE_CONFIG.get(style, STYLE_CONFIG["Cinematic"])
    w, h = canvas_size
    overlay = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    title_size = max(28, int(w * 0.055))
    subtitle_size = max(18, int(w * 0.032))
    title_font = _font(title_size, bold=True)
    sub_font = _font(subtitle_size, bold=False)

    parts = [p.strip() for p in text.replace("|", "\n").split("\n") if p.strip()]
    title = parts[0][:64]
    subtitle = "  •  ".join(parts[1:])[:120]

    pad_x = int(w * 0.055)
    pad_y = int(h * 0.018)
    max_box_w = int(w * 0.86)

    title_bbox = draw.textbbox((0, 0), title, font=title_font)
    title_w = min(title_bbox[2] - title_bbox[0], max_box_w)
    title_h = title_bbox[3] - title_bbox[1]
    sub_h = 0
    sub_w = 0
    if subtitle:
        sub_bbox = draw.textbbox((0, 0), subtitle, font=sub_font)
        sub_w = min(sub_bbox[2] - sub_bbox[0], max_box_w)
        sub_h = sub_bbox[3] - sub_bbox[1]

    box_w = min(max(title_w, sub_w) + 2 * pad_x, int(w * 0.92))
    box_h = title_h + sub_h + (pad_y * 3 if subtitle else pad_y * 2)

    box_x = (w - box_w) // 2
    if placement == "center":
        box_y = (h - box_h) // 2
    elif placement == "top":
        box_y = int(h * 0.08)
    else:
        box_y = h - box_h - int(h * 0.08)

    radius = max(14, int(min(w, h) * 0.025))
    shadow = Image.new("RGBA", (box_w, box_h), (0, 0, 0, 115))
    shadow_mask = _rounded_rect_mask((box_w, box_h), radius).filter(ImageFilter.GaussianBlur(10))
    shadow.putalpha(shadow_mask)
    overlay.alpha_composite(shadow, (box_x + 4, box_y + 5))

    draw.rounded_rectangle((box_x, box_y, box_x + box_w, box_y + box_h), radius=radius, fill=cfg["text_bg"])
    draw.rounded_rectangle((box_x, box_y, box_x + box_w, box_y + box_h), radius=radius, outline=cfg["accent"], width=max(2, int(w * 0.003)))

    tx = box_x + pad_x
    ty = box_y + pad_y
    draw.text((tx, ty), title, font=title_font, fill=cfg["text_fg"])
    if subtitle:
        draw.text((tx, ty + title_h + int(pad_y * 0.65)), subtitle, font=sub_font, fill=cfg["text_fg"])

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    overlay.save(tmp.name)
    return tmp.name


def _motion_clip(image_path: str, clip_duration: float, canvas_size: Tuple[int, int], motion: str) -> CompositeVideoClip:
    w, h = canvas_size
    base = ImageClip(image_path).set_duration(clip_duration)

    if motion == "zoom_out":
        def scale(t: float) -> float:
            return 1.10 - 0.08 * min(1, t / max(clip_duration, 0.01))
    elif motion == "pulse":
        def scale(t: float) -> float:
            return 1.035 + 0.018 * math.sin(t * math.pi * 2 / max(clip_duration, 0.01))
    else:
        def scale(t: float) -> float:
            return 1.00 + 0.085 * min(1, t / max(clip_duration, 0.01))

    moving = base.resize(scale).set_position(("center", "center"))
    return CompositeVideoClip([moving], size=canvas_size).set_duration(clip_duration)



def _wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int) -> List[str]:
    words = (text or "").split()
    if not words:
        return []
    lines: List[str] = []
    current = ""
    for word in words:
        test = word if not current else f"{current} {word}"
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] <= max_width or not current:
            current = test
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def build_story_captions(topic: str, language: str = "Hinglish", tone: str = "Promotional", count: int = 6) -> List[str]:
    """Create short scene captions when the user has no reference photo."""
    topic = (topic or "New Brand Story").strip()[:80]
    language = language or "Hinglish"
    tone = tone or "Promotional"
    count = max(3, min(8, int(count or 6)))

    if language == "Hindi":
        base = [
            f"{topic} | एक नई शुरुआत",
            "समस्या | लोगों को चाहिए तेज़ और आसान समाधान",
            "समाधान | स्मार्ट आइडिया, साफ़ डिज़ाइन",
            "फायदा | समय बचे, काम बेहतर बने",
            "भरोसा | साफ़ जानकारी और अच्छा अनुभव",
            "अभी शुरू करें | अपनी कहानी को वीडियो में बदलें",
            "नया अंदाज़ | प्रोफेशनल मोशन ग्राफिक्स",
            "धन्यवाद | शेयर करें और आगे बढ़ें",
        ]
    elif language == "English":
        base = [
            f"{topic} | A fresh beginning",
            "The problem | People need a faster, cleaner solution",
            "The idea | Smart story, polished motion, clear message",
            "The benefit | Save time and look more professional",
            "The trust | Simple visuals with strong presentation",
            "Start now | Turn your idea into a 30-second video",
            "Modern style | Motion graphics made easy",
            "Thank you | Share your story with the world",
        ]
    else:
        base = [
            f"{topic} | Ek fresh start",
            "Problem | Logon ko fast aur easy solution chahiye",
            "Idea | Smart story, clean design, premium motion",
            "Benefit | Time save, kaam better, look professional",
            "Trust | Clear visuals aur smooth experience",
            "Start now | Apni story ko 30 sec video me badlo",
            "Modern style | AI-style motion graphics easy way",
            "Thank you | Apni story duniya tak pahunchao",
        ]

    if tone == "Emotional":
        if language == "Hindi":
            base[1] = "भावना | हर कहानी में एक सपना छुपा होता है"
            base[3] = "कनेक्शन | दिल से जुड़ने वाला वीडियो"
        elif language == "English":
            base[1] = "Emotion | Every story carries a dream"
            base[3] = "Connection | A video that feels personal"
        else:
            base[1] = "Emotion | Har story me ek sapna hota hai"
            base[3] = "Connection | Dil se connect hone wala video"
    elif tone == "Informative":
        if language == "Hindi":
            base[1] = "जानकारी | मुख्य बात को आसान तरीके से समझाएँ"
            base[3] = "स्पष्टता | हर सीन में साफ़ मैसेज"
        elif language == "English":
            base[1] = "Information | Explain the main point clearly"
            base[3] = "Clarity | One clear message in every scene"
        else:
            base[1] = "Info | Main point simple tarike se samjhao"
            base[3] = "Clarity | Har scene me clear message"
    elif tone == "Cinematic":
        if language == "Hindi":
            base[1] = "विज़ुअल | गहराई, मूड और सिनेमैटिक एनर्जी"
            base[3] = "मोशन | स्मूथ कैमरा मूव और प्रीमियम लुक"
        elif language == "English":
            base[1] = "Visuals | Depth, mood, and cinematic energy"
            base[3] = "Motion | Smooth camera moves and premium pacing"
        else:
            base[1] = "Visuals | Depth, mood aur cinematic energy"
            base[3] = "Motion | Smooth camera move aur premium look"

    return base[:count]


def create_story_canvas(
    scene_text: str,
    canvas_size: Tuple[int, int],
    style: str,
    index: int,
    total: int,
    topic: str = "Story",
) -> str:
    """Create a generated scene when no reference photo is available."""
    cfg = STYLE_CONFIG.get(style, STYLE_CONFIG["Cinematic"])
    w, h = canvas_size
    rng = random.Random(f"{topic}-{scene_text}-{index}")
    palettes = [
        ((18, 24, 38), (120, 65, 255), (255, 196, 87)),
        ((13, 45, 63), (0, 190, 210), (255, 255, 255)),
        ((50, 18, 32), (255, 88, 120), (255, 210, 160)),
        ((20, 20, 20), (255, 255, 255), (255, 80, 80)),
        ((35, 28, 20), (255, 190, 90), (255, 255, 255)),
    ]
    bg1, bg2, accent = palettes[index % len(palettes)]
    canvas = Image.new("RGB", canvas_size, bg1)
    px = canvas.load()
    for y in range(h):
        blend = y / max(1, h - 1)
        for x in range(w):
            radial = ((x - w * 0.7) ** 2 + (y - h * 0.25) ** 2) ** 0.5 / max(w, h)
            b = min(1, max(0, blend * 0.62 + radial * 0.35))
            px[x, y] = tuple(int(bg1[i] * (1 - b) + bg2[i] * b) for i in range(3))
    canvas = canvas.filter(ImageFilter.GaussianBlur(0.2)).convert("RGBA")
    draw = ImageDraw.Draw(canvas)

    # Abstract motion shapes
    for _ in range(8):
        cx = rng.randint(-w // 8, w)
        cy = rng.randint(0, h)
        rr = rng.randint(max(18, w // 18), max(36, w // 6))
        color = (*accent, rng.randint(28, 80))
        draw.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), fill=color)

    # Main glass panel
    panel_w = int(w * 0.82)
    panel_h = int(h * 0.46)
    panel_x = (w - panel_w) // 2
    panel_y = int(h * 0.27)
    radius = max(24, int(min(w, h) * 0.04))
    shadow = Image.new("RGBA", (panel_w, panel_h), (0, 0, 0, 120))
    shadow.putalpha(_rounded_rect_mask((panel_w, panel_h), radius).filter(ImageFilter.GaussianBlur(18)))
    canvas.alpha_composite(shadow, (panel_x + 8, panel_y + 10))
    draw.rounded_rectangle((panel_x, panel_y, panel_x + panel_w, panel_y + panel_h), radius=radius, fill=(255, 255, 255, 42), outline=(255, 255, 255, 115), width=max(2, w // 320))

    parts = [p.strip() for p in scene_text.replace("|", "\n").split("\n") if p.strip()]
    title = parts[0] if parts else topic
    subtitle = " ".join(parts[1:]) if len(parts) > 1 else ""
    title_font = _font(max(34, int(w * 0.065)), bold=True)
    subtitle_font = _font(max(22, int(w * 0.038)), bold=False)
    small_font = _font(max(16, int(w * 0.026)), bold=False)

    max_text_w = int(panel_w * 0.82)
    title_lines = _wrap_text(draw, title, title_font, max_text_w)[:2]
    subtitle_lines = _wrap_text(draw, subtitle, subtitle_font, max_text_w)[:3]

    y_cursor = panel_y + int(panel_h * 0.23)
    for line in title_lines:
        bbox = draw.textbbox((0, 0), line, font=title_font)
        tx = panel_x + (panel_w - (bbox[2] - bbox[0])) // 2
        draw.text((tx, y_cursor), line, font=title_font, fill=(255, 255, 255, 255))
        y_cursor += (bbox[3] - bbox[1]) + int(h * 0.012)
    y_cursor += int(h * 0.008)
    for line in subtitle_lines:
        bbox = draw.textbbox((0, 0), line, font=subtitle_font)
        tx = panel_x + (panel_w - (bbox[2] - bbox[0])) // 2
        draw.text((tx, y_cursor), line, font=subtitle_font, fill=(255, 255, 255, 220))
        y_cursor += (bbox[3] - bbox[1]) + int(h * 0.008)

    # Scene counter dots
    dot_r = max(4, int(w * 0.007))
    gap = dot_r * 3
    start_x = w // 2 - ((total * dot_r * 2) + ((total - 1) * gap)) // 2
    top_y = int(h * 0.07)
    for i in range(total):
        color = (*accent, 235) if i == index else (255, 255, 255, 95)
        dx = start_x + i * (dot_r * 2 + gap)
        draw.ellipse((dx, top_y, dx + dot_r * 2, top_y + dot_r * 2), fill=color)

    footer = "Generated Story Mode"
    fb = draw.textbbox((0, 0), footer, font=small_font)
    draw.text(((w - (fb[2] - fb[0])) // 2, int(h * 0.88)), footer, font=small_font, fill=(255, 255, 255, 155))

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    canvas.convert("RGB").save(tmp.name, quality=95)
    return tmp.name


def create_story_assets(
    topic: str,
    language: str,
    tone: str,
    aspect: str,
    resolution: str,
    style: str,
    scene_count: int = 6,
) -> Tuple[List[str], List[str]]:
    """Return generated image paths and captions for no-photo mode."""
    captions = build_story_captions(topic, language=language, tone=tone, count=scene_count)
    canvas_size = get_canvas_size(aspect, resolution)
    image_paths = [
        create_story_canvas(text, canvas_size, style, idx, len(captions), topic=topic)
        for idx, text in enumerate(captions)
    ]
    return image_paths, captions

def generate_video(
    image_paths: Sequence[str | Path],
    output_name: str = "motionai_video",
    output_dir: str | Path = "outputs",
    duration: int = 30,
    aspect: str = "9:16 Reels/Shorts",
    resolution: str = "720p",
    style: str = "Cinematic",
    captions: Optional[Sequence[str]] = None,
    fps: int = 24,
    transition: float = 0.65,
    music_path: Optional[str | Path] = None,
    logo_path: Optional[str | Path] = None,
    watermark_handle: Optional[str] = None,
    watermark_position: str = "Bottom Right",
) -> str:
    """Generate a polished MP4 video from uploaded reference photos."""
    if not image_paths:
        raise ValueError("At least one image is required.")

    duration = int(max(5, min(30, duration)))
    fps = int(max(12, min(60, fps)))
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    canvas_size = get_canvas_size(aspect, resolution)
    watermark_path = create_instagram_watermark_asset(watermark_handle, canvas_size)
    if watermark_path:
        # keep the generated watermark file until render cleanup
        pass

    image_paths = [str(p) for p in image_paths]
    n = len(image_paths)
    transition = float(max(0, min(1.2, transition if n > 1 else 0)))
    clip_duration = (duration + transition * (n - 1)) / n

    captions = list(captions or [])
    clips = []
    temp_files: List[str] = []
    if watermark_path:
        temp_files.append(watermark_path)
    motions = ["zoom_in", "zoom_out", "pulse", "zoom_in"]

    for idx, path in enumerate(image_paths):
        canvas_path = create_reference_canvas(path, canvas_size, style, idx, n)
        temp_files.append(canvas_path)
        clip = _motion_clip(canvas_path, clip_duration, canvas_size, motions[idx % len(motions)])

        caption_text = captions[idx % len(captions)] if captions else ""
        text_path = create_text_overlay(caption_text, canvas_size, style, placement="bottom")
        overlays = [clip]
        if text_path:
            temp_files.append(text_path)
            text_clip = ImageClip(text_path).set_duration(clip_duration).fx(fadein, 0.25).fx(fadeout, 0.25)
            overlays.append(text_clip)

        if logo_path:
            try:
                logo = ImageClip(str(logo_path)).set_duration(clip_duration)
                logo_w = max(64, int(canvas_size[0] * 0.14))
                logo = logo.resize(width=logo_w).set_position((int(canvas_size[0] * 0.04), int(canvas_size[1] * 0.035))).set_opacity(0.92)
                overlays.append(logo)
            except Exception:
                pass

        if watermark_path:
            try:
                wm = ImageClip(str(watermark_path)).set_duration(clip_duration).set_opacity(0.96)
                margin = max(14, int(min(canvas_size) * 0.030))
                pos = (watermark_position or "Bottom Right").lower()
                x = margin if "left" in pos else canvas_size[0] - wm.w - margin
                y = margin if "top" in pos else canvas_size[1] - wm.h - margin
                wm = wm.set_position((x, y))
                overlays.append(wm)
            except Exception:
                pass

        final = CompositeVideoClip(overlays, size=canvas_size).set_duration(clip_duration)
        if idx > 0 and transition > 0:
            final = final.crossfadein(transition)
        clips.append(final)

    video = concatenate_videoclips(clips, method="compose", padding=-transition).set_duration(duration)

    if music_path:
        try:
            audio = AudioFileClip(str(music_path))
            audio = audio_loop(audio, duration=duration).volumex(0.35)
            video = video.set_audio(audio)
        except Exception:
            # Music is optional; video should still be generated.
            pass

    output_path = output_dir / f"{_safe_filename(output_name)}.mp4"
    video.write_videofile(
        str(output_path),
        fps=fps,
        codec="libx264",
        audio_codec="aac",
        preset="medium",
        threads=max(1, os.cpu_count() or 1),
        temp_audiofile=str(output_dir / "temp-audio.m4a"),
        remove_temp=True,
        logger=None,
    )

    # close resources
    video.close()
    for clip in clips:
        try:
            clip.close()
        except Exception:
            pass

    for file in temp_files:
        try:
            os.remove(file)
        except OSError:
            pass

    return str(output_path)

# -----------------------------
# Photo Generator / Resizer tools
# -----------------------------
PHOTO_PRESETS = {
    "1:1 Square": (1080, 1080),
    "400x400 Profile/Icon": (400, 400),
    "9:16 Story/Reel": (1080, 1920),
    "16:9 YouTube/Thumbnail": (1920, 1080),
    "4:5 Instagram Portrait": (1080, 1350),
    "A4 Portrait 300DPI": (2480, 3508),
    "A4 Landscape 300DPI": (3508, 2480),
    "Custom Size": None,
}


def get_photo_size(preset: str, custom_width: int = 1080, custom_height: int = 1080) -> Tuple[int, int]:
    """Return output image size for a selected preset."""
    if PHOTO_PRESETS.get(preset):
        return PHOTO_PRESETS[preset]  # type: ignore[index]
    custom_width = int(max(64, min(4096, custom_width or 1080)))
    custom_height = int(max(64, min(4096, custom_height or 1080)))
    return custom_width, custom_height


def _hex_to_rgb(hex_color: str, fallback: Tuple[int, int, int] = (255, 255, 255)) -> Tuple[int, int, int]:
    value = (hex_color or "").strip().lstrip("#")
    if len(value) == 3:
        value = "".join(ch * 2 for ch in value)
    if len(value) != 6:
        return fallback
    try:
        return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]
    except ValueError:
        return fallback


def _save_image_with_target(
    img: Image.Image,
    output_path: Path,
    output_format: str = "JPG",
    target_bytes: Optional[int] = None,
) -> None:
    """Save image. For JPG/WebP, binary-search quality to get close to target size."""
    fmt = output_format.upper().replace("JPEG", "JPG")
    if fmt == "JPG":
        pil_format = "JPEG"
        save_img = img.convert("RGB")
    elif fmt == "WEBP":
        pil_format = "WEBP"
        save_img = img.convert("RGB") if img.mode not in ("RGB", "RGBA") else img
    else:
        pil_format = "PNG"
        save_img = img.convert("RGBA") if img.mode == "RGBA" else img.convert("RGB")

    if pil_format == "PNG":
        save_img.save(output_path, format="PNG", optimize=True)
        return

    # No exact target requested: use high but balanced quality.
    if not target_bytes or target_bytes <= 0:
        save_img.save(output_path, format=pil_format, quality=88, optimize=True)
        return

    low, high = 10, 95
    best_data: Optional[bytes] = None
    best_diff: Optional[int] = None
    import io

    for _ in range(9):
        q = (low + high) // 2
        buf = io.BytesIO()
        save_img.save(buf, format=pil_format, quality=q, optimize=True)
        data = buf.getvalue()
        diff = abs(len(data) - target_bytes)
        if best_diff is None or diff < best_diff or len(data) <= target_bytes:
            best_data = data
            best_diff = diff
        if len(data) > target_bytes:
            high = q - 1
        else:
            low = q + 1

    if best_data is None:
        save_img.save(output_path, format=pil_format, quality=82, optimize=True)
    else:
        output_path.write_bytes(best_data)


def process_uploaded_photo(
    image_path: str | Path,
    output_name: str = "motionai_photo",
    output_dir: str | Path = "outputs",
    preset: str = "1:1 Square",
    custom_width: int = 1080,
    custom_height: int = 1080,
    fit_mode: str = "Smart Crop",
    background_color: str = "#FFFFFF",
    output_format: str = "JPG",
    target_size_value: Optional[float] = None,
    target_size_unit: str = "KB",
    watermark_handle: Optional[str] = None,
    watermark_position: str = "Bottom Right",
) -> str:
    """Resize/crop/contain an uploaded image and optionally compress near a KB/MB target."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    w, h = get_photo_size(preset, custom_width, custom_height)
    source = Image.open(image_path).convert("RGBA")

    fit_mode = fit_mode or "Smart Crop"
    bg_rgb = _hex_to_rgb(background_color)
    canvas = Image.new("RGBA", (w, h), (*bg_rgb, 255))

    if fit_mode == "Stretch":
        placed = source.resize((w, h), Image.Resampling.LANCZOS)
        canvas.alpha_composite(placed, (0, 0))
    elif fit_mode == "Fit / No Crop":
        placed = _contain_resize(source, (w, h)).convert("RGBA")
        canvas.alpha_composite(placed, ((w - placed.width) // 2, (h - placed.height) // 2))
    else:
        placed = ImageOps.fit(source, (w, h), method=Image.Resampling.LANCZOS, centering=(0.5, 0.5)).convert("RGBA")
        canvas.alpha_composite(placed, (0, 0))

    canvas = apply_instagram_watermark(canvas, watermark_handle, position=watermark_position)

    fmt = output_format.upper().replace("JPEG", "JPG")
    ext = {"JPG": "jpg", "WEBP": "webp", "PNG": "png"}.get(fmt, "jpg")
    output_path = output_dir / f"{_safe_filename(output_name)}.{ext}"

    target_bytes = None
    if target_size_value and target_size_value > 0:
        unit = (target_size_unit or "KB").upper()
        multiplier = 1024 * 1024 if unit == "MB" else 1024
        target_bytes = int(float(target_size_value) * multiplier)

    _save_image_with_target(canvas, output_path, fmt, target_bytes=target_bytes)
    return str(output_path)


def build_photo_prompt_lines(prompt: str, language: str = "Hinglish") -> Tuple[str, str, str]:
    prompt = (prompt or "New creative photo").strip()[:90]
    if language == "Hindi":
        return prompt, "प्रोफेशनल AI-स्टाइल डिज़ाइन", "Download • Resize • Share"
    if language == "English":
        return prompt, "Professional AI-style visual design", "Download • Resize • Share"
    return prompt, "Professional AI-style photo design", "Download • Resize • Share"


def generate_photo_canvas(
    prompt: str,
    language: str = "Hinglish",
    style: str = "Product Premium",
    output_name: str = "motionai_generated_photo",
    output_dir: str | Path = "outputs",
    preset: str = "1:1 Square",
    custom_width: int = 1080,
    custom_height: int = 1080,
    output_format: str = "JPG",
    target_size_value: Optional[float] = None,
    target_size_unit: str = "KB",
    watermark_handle: Optional[str] = None,
    watermark_position: str = "Bottom Right",
    show_brand_tag: bool = False,
) -> str:
    """Create a free local AI-style graphic/photo poster from a text prompt.

    This is a no-model generator. It makes polished prompt-based visuals with
    abstract background, typography and motion-graphics-style design. For real
    photorealistic image AI, connect Stable Diffusion/ComfyUI later.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    w, h = get_photo_size(preset, custom_width, custom_height)
    cfg = STYLE_CONFIG.get(style, STYLE_CONFIG["Product Premium"])
    rng = random.Random(f"{prompt}-{language}-{style}-{w}x{h}")

    # Style-aware palettes.
    palettes = {
        "Cinematic": [((8, 12, 24), (60, 54, 120), (255, 205, 120)), ((20, 24, 34), (80, 30, 50), (255, 120, 95))],
        "Product Premium": [((255, 248, 235), (255, 195, 160), (255, 80, 70)), ((18, 18, 18), (120, 65, 45), (255, 210, 150))],
        "Birthday / Cake": [((255, 235, 245), (255, 180, 210), (150, 35, 80)), ((255, 245, 225), (255, 190, 120), (255, 95, 120))],
        "Travel": [((12, 52, 76), (55, 185, 210), (255, 238, 180)), ((8, 80, 82), (100, 210, 170), (255, 255, 255))],
        "Minimal Clean": [((244, 246, 250), (220, 226, 238), (20, 20, 20)), ((15, 15, 16), (80, 80, 85), (255, 255, 255))],
    }
    bg1, bg2, accent = rng.choice(palettes.get(style, palettes["Product Premium"]))
    canvas = Image.new("RGB", (w, h), bg1)
    px = canvas.load()
    for y in range(h):
        yy = y / max(1, h - 1)
        for x in range(w):
            xx = x / max(1, w - 1)
            radial = ((xx - 0.72) ** 2 + (yy - 0.25) ** 2) ** 0.5
            b = min(1.0, max(0.0, yy * 0.48 + radial * 0.75))
            px[x, y] = tuple(int(bg1[i] * (1 - b) + bg2[i] * b) for i in range(3))
    canvas = canvas.filter(ImageFilter.GaussianBlur(0.15)).convert("RGBA")
    draw = ImageDraw.Draw(canvas)

    # Decorative AI-style shapes.
    for i in range(12):
        rr = rng.randint(max(18, min(w, h) // 22), max(36, min(w, h) // 5))
        cx = rng.randint(-rr, w + rr)
        cy = rng.randint(-rr, h + rr)
        alpha = rng.randint(25, 95)
        color = (*accent, alpha)
        if i % 3 == 0:
            draw.rounded_rectangle((cx - rr, cy - rr // 2, cx + rr, cy + rr // 2), radius=max(12, rr // 3), fill=color)
        else:
            draw.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), fill=color)

    # Main panel/card.
    panel_w = int(w * 0.80)
    panel_h = int(h * 0.48)
    panel_x = (w - panel_w) // 2
    panel_y = int(h * 0.25)
    radius = max(22, int(min(w, h) * 0.045))
    shadow = Image.new("RGBA", (panel_w, panel_h), (0, 0, 0, 110))
    shadow.putalpha(_rounded_rect_mask((panel_w, panel_h), radius).filter(ImageFilter.GaussianBlur(max(10, radius // 2))))
    canvas.alpha_composite(shadow, (panel_x + max(6, w // 120), panel_y + max(7, h // 120)))
    draw.rounded_rectangle((panel_x, panel_y, panel_x + panel_w, panel_y + panel_h), radius=radius, fill=(255, 255, 255, 52), outline=(255, 255, 255, 145), width=max(2, w // 350))

    title, subtitle, footer = build_photo_prompt_lines(prompt, language)
    title_font = _font(max(30, int(w * 0.065)), bold=True)
    sub_font = _font(max(18, int(w * 0.034)), bold=False)
    foot_font = _font(max(13, int(w * 0.022)), bold=False)
    max_text_w = int(panel_w * 0.82)
    title_lines = _wrap_text(draw, title, title_font, max_text_w)[:3]
    subtitle_lines = _wrap_text(draw, subtitle, sub_font, max_text_w)[:2]

    # Decide text color by background brightness.
    brightness = sum(bg1) / 3
    text_fill = (15, 15, 18, 255) if brightness > 170 and style != "Minimal Clean" else (255, 255, 255, 255)
    soft_fill = (*text_fill[:3], 210)

    y_cursor = panel_y + int(panel_h * 0.20)
    for line in title_lines:
        bbox = draw.textbbox((0, 0), line, font=title_font)
        draw.text((panel_x + (panel_w - (bbox[2] - bbox[0])) // 2, y_cursor), line, font=title_font, fill=text_fill)
        y_cursor += (bbox[3] - bbox[1]) + int(h * 0.012)
    y_cursor += int(h * 0.008)
    for line in subtitle_lines:
        bbox = draw.textbbox((0, 0), line, font=sub_font)
        draw.text((panel_x + (panel_w - (bbox[2] - bbox[0])) // 2, y_cursor), line, font=sub_font, fill=soft_fill)
        y_cursor += (bbox[3] - bbox[1]) + int(h * 0.008)

    # Optional brand tag. Default is off so exports can be truly no-watermark.
    if show_brand_tag:
        tag = "MotionAI Photo"
        tb = draw.textbbox((0, 0), tag, font=foot_font)
        tag_w = tb[2] - tb[0] + int(w * 0.05)
        tag_h = tb[3] - tb[1] + int(h * 0.024)
        tx = (w - tag_w) // 2
        ty = int(h * 0.88)
        draw.rounded_rectangle((tx, ty, tx + tag_w, ty + tag_h), radius=tag_h // 2, fill=(*accent, 190))
        draw.text((tx + (tag_w - (tb[2] - tb[0])) // 2, ty + (tag_h - (tb[3] - tb[1])) // 2 - 1), tag, font=foot_font, fill=(20, 20, 20, 255))

    canvas = apply_instagram_watermark(canvas, watermark_handle, position=watermark_position)

    fmt = output_format.upper().replace("JPEG", "JPG")
    ext = {"JPG": "jpg", "WEBP": "webp", "PNG": "png"}.get(fmt, "jpg")
    output_path = output_dir / f"{_safe_filename(output_name)}.{ext}"
    target_bytes = None
    if target_size_value and target_size_value > 0:
        unit = (target_size_unit or "KB").upper()
        target_bytes = int(float(target_size_value) * (1024 * 1024 if unit == "MB" else 1024))
    _save_image_with_target(canvas, output_path, fmt, target_bytes=target_bytes)
    return str(output_path)
