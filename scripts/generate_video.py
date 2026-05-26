"""
Generate a 1080x1920 vertical short (TikTok / YouTube Shorts) from a post.

Features:
  - Per-card TTS voiceover. Uses ElevenLabs (Grace voice, V3 model) when
    ELEVENLABS_API_KEY is set in .env. Falls back to gTTS otherwise.
  - Card durations driven by TTS length (no awkward silent gaps)
  - Ken Burns slow zoom on every card + crossfade transitions
  - Optional music bed at -20dB if assets/audio/news-bed.mp3 exists

Usage:
    python3 scripts/generate_video.py revolut-scam-uk
    python3 scripts/generate_video.py royal-mail-text-scam-uk --no-music

Env vars (.env is loaded automatically):
    ELEVENLABS_API_KEY      required to use ElevenLabs
    ELEVENLABS_VOICE_ID     override the default Grace voice
    ELEVENLABS_MODEL_ID     override the default eleven_v3 model

Output:
    out/videos/{slug}.mp4
    out/videos/{slug}-frames/  per-scene PNGs for inspection
    out/videos/{slug}-audio/   per-card TTS MP3s

Music:
    Drop a royalty-free news theme MP3 at assets/audio/news-bed.mp3.
    Mixkit (https://mixkit.co/free-stock-music/tag/news/) is free with no
    account required. The track will be mixed at -20dB under the voiceover.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import shutil
import sys
from pathlib import Path
from typing import List, Optional, Tuple

from PIL import Image, ImageDraw, ImageFont
from moviepy import (
    ImageClip,
    AudioFileClip,
    CompositeVideoClip,
    CompositeAudioClip,
)
from moviepy.video.fx import CrossFadeIn

# Load .env so ELEVENLABS_API_KEY is available without an explicit export.
# Optional dep — the script still runs (with gTTS) if dotenv isn't installed.
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

try:
    from gtts import gTTS
    _GTTS_OK = True
except Exception:
    _GTTS_OK = False

try:
    from elevenlabs.client import ElevenLabs
    _ELEVEN_OK = True
except Exception:
    _ELEVEN_OK = False


# ─── TTS provider configuration ────────────────────────────────────────────
# Daniel — British male, deep newsreader timbre, premade voice in the
# ElevenLabs library. Pinned as the canonical Beat the Scam voice.
# Override via ELEVENLABS_VOICE_ID env var if you ever need a different one.
ELEVEN_VOICE_ID = os.environ.get("ELEVENLABS_VOICE_ID", "3WqHLnw80rOZqJzW9YRB")
ELEVEN_MODEL_ID = os.environ.get("ELEVENLABS_MODEL_ID", "eleven_v3")
ELEVEN_API_KEY  = os.environ.get("ELEVENLABS_API_KEY", "").strip()


# ─── Pronunciation overrides (TTS only — display text unchanged) ───────────
# Brand names that TTS engines commonly mispronounce. The key is the written
# form (whole-word, case-sensitive); the value is the phonetic respelling
# that produces a correct reading. Extend this dict whenever you spot an
# issue — it's cheap and dramatically improves perceived quality.
PHONETIC_OVERRIDES = {
    # Brand names that need respelling for natural pronunciation.
    "Revolut":   "Rev-uh-loot",
    "Evri":      "Ev-ree",

    # Acronyms: V3 generally handles common British acronyms (HMRC, DVLA,
    # NCSC, etc.) natively — the model knows they should be read letter-by-
    # letter. We only override here when we've confirmed V3 mispronounces
    # something with the bare form. Verified mispronunciations get added back.

    # Already pronounced as words — light respellings to fix vowel sounds.
    "UCAS":      "yoo-kass",
    "ASOS":      "ay-sos",
}


def for_speech(text: str) -> str:
    """Apply pronunciation overrides for the TTS path only."""
    out = text or ""
    for written, spoken in PHONETIC_OVERRIDES.items():
        out = re.sub(r"\b" + re.escape(written) + r"\b", spoken, out)
    return out


# ─── Brand constants (match the OG image generator in build.py) ────────────
W, H = 1080, 1920
BG          = (11, 18, 32)
PANEL       = (15, 24, 42)
ACCENT      = (58, 134, 255)
SECONDARY   = (140, 198, 255)
WHITE       = (255, 255, 255)
ALERT_RED   = (255, 92, 92)

FPS = 30

# Path defaults
ROOT           = Path(__file__).resolve().parents[1]
DEFAULT_MUSIC  = ROOT / "assets" / "audio" / "news-bed.mp3"
END_CARD_IMAGE = ROOT / "assets" / "video" / "end-card.png"


# ─── Fonts ─────────────────────────────────────────────────────────────────

def load_font(size: int) -> ImageFont.FreeTypeFont:
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/Library/Fonts/Arial Bold.ttf",
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            continue
    return ImageFont.load_default()


def wrap(draw: ImageDraw.ImageDraw, text: str, font, max_width: int) -> List[str]:
    words = text.split()
    lines, current = [], []
    for w in words:
        trial = " ".join(current + [w])
        bbox = draw.textbbox((0, 0), trial, font=font)
        if (bbox[2] - bbox[0]) <= max_width:
            current.append(w)
        else:
            if current:
                lines.append(" ".join(current))
            current = [w]
    if current:
        lines.append(" ".join(current))
    return lines


# ─── Card rendering ────────────────────────────────────────────────────────

def draw_chrome(draw: ImageDraw.ImageDraw, alert: bool = False):
    bar_colour = ALERT_RED if alert else ACCENT
    draw.rectangle([(0, 0), (W, 22)], fill=bar_colour)
    draw.rectangle([(0, H - 150), (W, H)], fill=PANEL)
    draw.text((80, H - 120), "Beat the Scam", font=load_font(40), fill=WHITE)
    draw.text((80, H - 70), "beatthescam.com", font=load_font(32), fill=SECONDARY)


def render_card(
    out_path: Path,
    *,
    eyebrow: Optional[str] = None,
    headline: Optional[str] = None,
    body_lines: Optional[List[str]] = None,
    cta: Optional[str] = None,
    big_number: Optional[str] = None,
    alert: bool = False,
    headline_size: int = 96,
):
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    draw_chrome(draw, alert=alert)

    pad = 90
    text_w = W - 2 * pad
    y = 260

    if eyebrow:
        eyebrow_colour = ALERT_RED if alert else SECONDARY
        draw.text((pad, y), eyebrow.upper(), font=load_font(52), fill=eyebrow_colour)
        y += 90

    if big_number:
        f = load_font(380)
        bbox = draw.textbbox((0, 0), big_number, font=f)
        x = (W - (bbox[2] - bbox[0])) // 2
        draw.text((x, y), big_number, font=f, fill=ACCENT)
        y += 440

    if headline:
        f = load_font(headline_size)
        line_height = int(headline_size * 1.25)
        for line in wrap(draw, headline, f, text_w)[:6]:
            draw.text((pad, y), line, font=f, fill=WHITE)
            y += line_height

    if body_lines:
        y += 50
        f = load_font(58)
        for line in body_lines[:5]:
            for wrapped in wrap(draw, line, f, text_w):
                draw.text((pad, y), wrapped, font=f, fill=WHITE)
                y += 76
            y += 14

    if cta:
        f = load_font(78)
        for line in wrap(draw, cta, f, text_w):
            draw.text((pad, y), line, font=f, fill=ACCENT)
            y += 100

    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, "PNG", optimize=True)


# ─── Thumbnail rendering (YouTube custom thumbnails, 1280×720 landscape) ──

THUMB_W, THUMB_H = 1280, 720


def render_thumbnail(out_path: Path, *, topic: str, family: str) -> Path:
    """Render a 1280×720 YouTube thumbnail. Brand-aligned (matches the video
    cards) but landscape-oriented.

    Layout (top to bottom):
      - 24px red accent bar
      - "SCAM ALERT" eyebrow (top-left, red, ~54px)
      - Big topic text centered horizontally and vertically. Auto-sizes
        font down from 200→80px to fit in 1-2 lines.
      - "3 WARNING SIGNS" subtitle in accent blue
      - Brand footer strip: "Beat the Scam" left, "beatthescam.com" right

    Saves as JPEG (YouTube prefers JPEG; quality 90 keeps the file <500 KB,
    well under YouTube's 2 MB hard cap).
    """
    tpl = HOOK_TEMPLATES.get(family, HOOK_TEMPLATES["message"])
    thumb_text = tpl.get("thumbnail_text", "{topic} SCAM").format(topic=topic).upper()

    img = Image.new("RGB", (THUMB_W, THUMB_H), BG)
    draw = ImageDraw.Draw(img)

    # Top accent bar
    draw.rectangle([(0, 0), (THUMB_W, 24)], fill=ALERT_RED)

    # SCAM ALERT eyebrow (top-left)
    pad = 70
    draw.text((pad, 60), "SCAM ALERT", font=load_font(54), fill=ALERT_RED)

    # Centerpiece: big topic text, auto-sized to fit
    max_text_w = THUMB_W - 2 * pad
    # The centerpiece area is roughly y=160 to y=540 (380px tall)
    centerpiece_top, centerpiece_bottom = 160, 540
    centerpiece_h = centerpiece_bottom - centerpiece_top

    chosen_size = 200
    chosen_lines: List[str] = []
    chosen_line_h = 0
    for size in range(200, 79, -10):
        f = load_font(size)
        lines = wrap(draw, thumb_text, f, max_text_w)
        line_h = int(size * 1.05)  # tight line height for big display type
        total_h = len(lines) * line_h
        # Vertical fit check + horizontal fit check (wrap() can't split a
        # single long word, so a wide word like "MARKETPLACE" at 200pt
        # would overflow horizontally — drop the size until it fits).
        widest = max(
            (draw.textbbox((0, 0), line, font=f)[2] for line in lines),
            default=0,
        )
        if total_h <= centerpiece_h and widest <= max_text_w:
            chosen_size = size
            chosen_lines = lines
            chosen_line_h = line_h
            break
    else:
        # Even at 80px it overflowed — accept it and let it crowd
        f = load_font(80)
        chosen_size = 80
        chosen_lines = wrap(draw, thumb_text, f, max_text_w)
        chosen_line_h = int(80 * 1.05)

    f = load_font(chosen_size)
    block_h = len(chosen_lines) * chosen_line_h
    block_top = centerpiece_top + (centerpiece_h - block_h) // 2
    for i, line in enumerate(chosen_lines):
        bbox = draw.textbbox((0, 0), line, font=f)
        x = (THUMB_W - (bbox[2] - bbox[0])) // 2
        draw.text((x, block_top + i * chosen_line_h), line, font=f, fill=WHITE)

    # "3 WARNING SIGNS" subtitle
    sub_text = "3 WARNING SIGNS"
    sub_f = load_font(64)
    sub_bbox = draw.textbbox((0, 0), sub_text, font=sub_f)
    sub_x = (THUMB_W - (sub_bbox[2] - sub_bbox[0])) // 2
    draw.text((sub_x, 580), sub_text, font=sub_f, fill=ACCENT)

    # Brand footer strip
    footer_h = 60
    draw.rectangle([(0, THUMB_H - footer_h), (THUMB_W, THUMB_H)], fill=PANEL)
    brand_f = load_font(28)
    draw.text((pad, THUMB_H - footer_h + 15), "Beat the Scam", font=brand_f, fill=WHITE)
    url_text = "beatthescam.com"
    url_bbox = draw.textbbox((0, 0), url_text, font=brand_f)
    draw.text(
        (THUMB_W - pad - (url_bbox[2] - url_bbox[0]), THUMB_H - footer_h + 15),
        url_text, font=brand_f, fill=SECONDARY,
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_path, "JPEG", quality=90, optimize=True)
    return out_path


# ─── Content extraction ────────────────────────────────────────────────────

def _coerce_body(body) -> str:
    """Body can be a string, a Python list, or a string that contains a
    repr-ed Python list (legacy bug). Normalise to a clean newline-joined
    string of bullet lines. Same shape as build.py's _normalize_bullet_body."""
    if isinstance(body, list):
        return "\n".join(str(x) for x in body)
    s = str(body or "").strip()
    if (s.startswith("['") or s.startswith('["')) and s.endswith("]"):
        try:
            import ast
            parsed = ast.literal_eval(s)
            if isinstance(parsed, list):
                return "\n".join(str(item) for item in parsed)
        except (ValueError, SyntaxError):
            pass
    return s


def extract_warning_signs(post) -> List[str]:
    for title, body in post.get("sections", []):
        if "warning" in (title or "").lower():
            text = _coerce_body(body)
            items = [l.strip().lstrip("- ").strip() for l in text.splitlines() if l.strip()]
            return [x for x in items if x]
    return []


# Hand-curated topic prefixes — these are the brand names we want spoken at
# the start of the video. Keyed by the lowercased opening of the post slug
# (or title prefix); first match wins. Extend liberally — it's the cleanest
# way to keep the hook tight on YMYL content.
TOPIC_OVERRIDES = {
    "hmrc":            "HMRC",
    "dvla":            "DVLA",
    "ncsc":            "NCSC",
    "royal-mail":      "Royal Mail",
    "royal mail":      "Royal Mail",
    "facebook-marketplace": "Facebook Marketplace",
    "facebook marketplace": "Facebook Marketplace",
    "tv-licence":      "TV Licensing",
    "tv-licensing":    "TV Licensing",
    "tv licence":      "TV Licensing",
    "tv licensing":    "TV Licensing",
    "council-tax":     "Council Tax",
    "national-insurance": "National Insurance",
    "tax-return":      "tax return",
    "universal-credit": "Universal Credit",
    "bank-transfer":   "bank transfer",
    "amazon-delivery": "Amazon delivery",
    "amazon-order":    "Amazon order",
    "fake-online-pharmacy": "fake pharmacy",
    # Ticket-resale brands — keep topic names short so the ticket_resale
    # hook copy reads cleanly ("Looking for Glastonbury tickets?" not
    # "Looking for Glastonbury Ticket Scam UK tickets?").
    "glastonbury":            "Glastonbury",
    "wimbledon":              "Wimbledon",
    "reading-festival":       "Reading Festival",
    "f1-british-gp":          "British GP",
    "viagogo":                "Viagogo",
    "stubhub":                "StubHub",
    "concert-ticket":         "concert",
    "fake-festival-ticket":   "festival",
    "fake-airline-ticket":    "airline",
}


# Hook/promise copy keyed by topic family. The "message" family is the
# original HMRC template — works for emails, texts, app messages where the
# threat IS a link to tap. Other families override for topics where that
# framing reads awkwardly (Marketplace listings aren't messages; "Hi Mum"
# scams aren't about tapping links; phone-call scams aren't messages at all).
#
# Each template can use {topic}, {n}, or {sign_word} placeholders. Unused
# placeholders are silently ignored.
HOOK_TEMPLATES = {
    "message": {
        "hook_headline":   "Got a {topic} message? Don't tap that link.",
        "hook_speech":     "Got a {topic} message? Stop. Don't tap that link.",
        "promise":         "{n} warning {sign_word} that the {topic} message is a scam.",
        "verify_headline": "Verify through the official site yourself — never via the link.",
        "verify_speech":   "Always verify through the official site yourself. Never via a link in the message.",
        "thumbnail_text":  "{topic} SCAM",  # e.g. "HMRC SCAM", "DVLA SCAM", "ROYAL MAIL SCAM"
    },
    "marketplace": {
        "hook_headline":   "Spotted a {topic} bargain? Stop — it might be a scam.",
        "hook_speech":     "Spotted a {topic} bargain? Stop. It might be a scam.",
        "promise":         "{n} warning {sign_word} that the listing is fake.",
        "verify_headline": "Pay through Marketplace. Never bank transfer to a stranger.",
        "verify_speech":   "Pay through Marketplace itself. Never bank transfer to a seller you haven't met in person.",
        "thumbnail_text":  "MARKETPLACE SCAM",  # "Facebook Marketplace SCAM" is too long for thumbnail
    },
    "family_message": {
        "hook_headline":   "\"Hi Mum, I've lost my phone — can you send £200?\" Stop.",
        "hook_speech":     "Hi Mum, I've lost my phone, can you send two hundred pounds? Stop. It's a scam, not your kid.",
        "promise":         "{n} warning {sign_word} it's a scammer, not your family.",
        "verify_headline": "Call your family on their old number. Don't send a penny yet.",
        "verify_speech":   "Call your family member on their original number first. Don't send anything until you've heard their voice.",
        "thumbnail_text":  "\"HI MUM\" SCAM",
    },
    "call": {
        "hook_headline":   "A {topic} call asking you to move money? Hang up.",
        "hook_speech":     "Got a {topic} call asking you to move money? Hang up.",
        "promise":         "{n} warning {sign_word} that the {topic} call is a scam.",
        "verify_headline": "Hang up. Call your bank back on the number from your card.",
        "verify_speech":   "Hang up. Call your bank back using the number printed on the back of your card.",
        "thumbnail_text":  "{topic} CALL SCAM",
    },
    "ticket_resale": {
        "hook_headline":   "Looking for {topic} tickets? That \"bargain\" is a scam.",
        "hook_speech":     "Looking for {topic} tickets? Stop. That bargain is probably a scam.",
        "promise":         "{n} warning {sign_word} the {topic} ticket seller is a scammer.",
        "verify_headline": "Buy through official resellers only. Never bank transfer to a stranger.",
        "verify_speech":   "Only buy through official resellers like Ticketmaster, See Tickets, or AXS. Never bank transfer to a face-value seller you haven't met.",
        "thumbnail_text":  "{topic} TICKET SCAM",
    },
}

# Map a slug substring to its hook-template family. Checked in order — more
# specific patterns should come first if they would otherwise be shadowed.
# Anything not matched falls back to "message" (the HMRC default).
SLUG_FAMILIES = [
    # marketplace
    ("facebook-marketplace", "marketplace"),
    ("ebay",                 "marketplace"),
    ("vinted",               "marketplace"),
    ("gumtree",              "marketplace"),
    ("shpock",               "marketplace"),
    ("depop",                "marketplace"),
    # family-impersonation messaging (Hi Mum / new number)
    ("whatsapp-family",      "family_message"),
    ("whatsapp-hi-mum",      "family_message"),
    ("hi-mum",               "family_message"),
    ("whatsapp-new-number",  "family_message"),
    ("family-emergency",     "family_message"),
    # phone-call scams
    ("bank-impersonation-call", "call"),
    ("bank-phone",              "call"),
    ("police-impersonation",    "call"),
    ("courier-fraud",           "call"),
    ("phone-call-scam",         "call"),
    # ticket resale / event scams — peak summer (festivals, sport)
    ("glastonbury",             "ticket_resale"),
    ("wimbledon",               "ticket_resale"),
    ("reading-festival",        "ticket_resale"),
    ("f1-british-gp",           "ticket_resale"),
    ("viagogo",                 "ticket_resale"),
    ("stubhub",                 "ticket_resale"),
    ("concert-ticket",          "ticket_resale"),
    ("fake-festival-ticket",    "ticket_resale"),
    ("fake-airline-ticket",     "ticket_resale"),
    ("-ticket-scam",            "ticket_resale"),  # generic catch-all
]


def _topic_family(post: dict) -> str:
    """Return the hook-template family for a post. Defaults to 'message'."""
    slug = (post.get("slug") or "").lower()
    for prefix, family in SLUG_FAMILIES:
        if prefix in slug:
            return family
    return "message"


def short_topic(post) -> str:
    """A 1-3 word topic for the hook ('Revolut', 'HMRC', 'Royal Mail').

    Resolution order:
      1. Manual override map (matched on slug prefix, then title prefix)
      2. Leading all-caps acronym in the title (HMRC, DVLA, etc.)
      3. Entity field if explicitly provided on the post (rare)
      4. First 1-2 significant words of the title
      5. Literal 'this' as last-resort fallback
    """
    slug = (post.get("slug") or "").lower()
    title = (post.get("title") or "").split(":")[0].strip()
    title_lower = title.lower()

    # 1. Slug- or title-prefix override
    for key, label in TOPIC_OVERRIDES.items():
        if slug.startswith(key) or title_lower.startswith(key):
            return label

    # 2. Leading all-caps acronym (2-6 chars)
    m = re.match(r"^([A-Z]{2,6})\b", title)
    if m:
        return m.group(1)

    # 3. Explicit entity field (publishing queue may set this)
    entity = (post.get("entity") or "").strip()
    if entity and entity.lower() not in {"unknown", "general", "various"}:
        return entity

    # 4. First 1-2 significant words
    STOPWORDS = {"scam", "scams", "fraud", "warning", "signs", "guide",
                 "uk", "how", "to", "spot", "fake", "the", "a", "an"}
    words = title.split()
    keepers = []
    for w in words[:4]:
        if w.lower() in STOPWORDS:
            break
        keepers.append(w)
        if len(" ".join(keepers)) > 18:
            break
    if keepers:
        return " ".join(keepers)
    return "this"


def shorten_warning(text: str, max_chars: int = 90) -> str:
    """Trim warning text for both card display AND speech.

    Aggressive on purpose — long signs create awkward TTS reads and push the
    video past the 30-40s TikTok sweet spot. Strategy in order:
      1. Drop parentheticals: "(e.g., something)"
      2. Drop em-dash / en-dash continuations: "main point — elaboration"
         (handles no-space variant "main point—elaboration" too)
      3. Drop "using/via/by/through X, Y, Z" payment-method or example
         lists with 2+ items (the lead-in connector is kept; only the list
         is stripped). Catches "pay using bank transfer, gift cards, or
         crypto" → "pay" so the clause is finished cleanly upstream.
      4. Drop quoted-example phrases together with their lead-in:
            "Urgent language like 'X' or 'Y' is a red flag" → "Urgent language is a red flag"
            "Domain such as @foo.com is wrong" → "Domain is wrong"
      5. Prefer cutting at clause boundary (",", ";", " but ", " and ",
         " or ", " so ") — gives complete sentences instead of dangling
         "didn't expect…" ellipses.
      6. Word-boundary fallback with ellipsis (last resort).
    """
    text = re.sub(r"\s+", " ", text or "").strip()

    # 1. Parentheticals
    text = re.sub(r"\s*\([^)]*\)", "", text)

    # 2. Em-dash / en-dash (Unicode only, not the hyphen used in compound words)
    text = re.split(r"\s*[—–]\s*", text)[0]

    # 3. Strip "using/via/by/through X, Y, Z" lists (2+ items, comma-separated,
    #    optionally ending "or Z"). Catches "pay using bank transfer, Google
    #    Play cards, iTunes vouchers, or cryptocurrency" but leaves "using
    #    urgent language" (single thing, not a list) alone.
    text = re.sub(
        r"\s+(?:using|via|by|through|with)\s+"
        r"[^,.;]+(?:,\s*[^,.;]+){1,}"          # at least one comma-separated item
        r"(?:,?\s*(?:or|and)\s+[^,.;]+)?",     # optional trailing ", or Z"
        "",
        text,
        flags=re.I,
    )

    # 3b. Strip ": A, B, C" colon-introduces-examples lists (2+ items). The
    #     colon promises examples — if there are multiple comma-separated
    #     examples, the trim downstream would otherwise cut after just the
    #     first one and read like a mid-list truncation. e.g. on the
    #     Glastonbury ticket-scam article:
    #       "payment methods that can't be traced or reversed: cryptocurrency,
    #        bank transfer to a personal account, or iTunes/Google Play gift
    #        cards." -> "payment methods that can't be traced or reversed"
    #     Single-example colons ("there's only one: A.") aren't matched.
    text = re.sub(
        r":\s+[^,.;:]+(?:\s*,\s*[^,.;:]+){1,}\s*\.?",
        "",
        text,
    )

    # 4. Quoted-example lead-ins + their content (and any "or 'Y'" siblings)
    text = re.sub(
        r"\s+(\b(?:like|such as|including|e\.?g\.?)\s+)?"
        r"['\"][^'\"]+['\"]"
        r"(\s+(?:or|and)\s+['\"][^'\"]+['\"])*",
        "",
        text,
        flags=re.I,
    )

    # Clean up residue from stripping: double punctuation, stranded separators
    text = re.sub(r"\s*,\s*,\s*", ", ", text)
    text = re.sub(r"\s*[,;]\s*(or|and)\b", r" \1", text, flags=re.I)
    text = re.sub(r"\b(or|and)\s+[,;]", r"\1", text, flags=re.I)
    text = re.sub(r"\s+", " ", text).strip().rstrip(".,;:")
    if not text:
        return ""

    if len(text) <= max_chars:
        return text

    # 5. Find latest clause boundary that fits in the window. We accept:
    #    - commas / semicolons (hard clause break)
    #    - connector words (but / and / or / so)
    #    - prepositions that introduce an optional sub-clause (within /
    #      during / after / before / throughout / around)
    #    so we don't strand mid-clause text like "but you didn't expect
    #    them to change it" or "within a short timeframe".
    cut_at = -1
    for m in re.finditer(
        r"[,;]|\s+(?:but|and|or|so|within|during|after|before|throughout|around)\s+",
        text[:max_chars],
        flags=re.I,
    ):
        cut_at = m.start()
    if cut_at >= 25:
        return text[:cut_at].rstrip(",.;: ")

    # 6. No clean clause boundary found within max_chars. Hard rule: never
    #    cut mid-phrase with an ellipsis (the "bank…" / "didn't expect…"
    #    failure mode that produced unreadable cards). Return the full
    #    original sentence intact — card auto-sizing + audio length both
    #    handle longer text fine. Never strands the viewer mid-thought.
    return text


# ─── Storyboard ────────────────────────────────────────────────────────────

def build_scripts(post) -> List[dict]:
    """Per-card visual + narration. Returns scenes as dicts."""
    category   = (post.get("category") or "scam").replace("-", " ")
    topic      = short_topic(post)
    warnings   = [shorten_warning(w) for w in extract_warning_signs(post)[:3]]
    full_title = post["title"]

    # If we found fewer than 3 warning signs, pad with generic ones so the
    # video has enough rhythm. Better than a thin 1-sign storyboard.
    GENERIC_WARNINGS = [
        "Urgency you weren't expecting",
        "An unfamiliar sender, link, or domain",
        "Requests for security codes or payment details",
    ]
    seen = {w.lower() for w in warnings}
    for g in GENERIC_WARNINGS:
        if len(warnings) >= 3:
            break
        if g.lower() not in seen:
            warnings.append(g)

    scenes = []

    # Pick the hook/promise copy family for this topic. Default ("message")
    # matches the original HMRC template; marketplace / family_message / call
    # override for topics where that framing reads awkwardly.
    family = _topic_family(post)
    tpl = HOOK_TEMPLATES.get(family, HOOK_TEMPLATES["message"])
    sign_word = "sign" if len(warnings) == 1 else "signs"
    n_word = _num_word(len(warnings))
    fmt_kwargs = {"topic": topic, "n": n_word, "sign_word": sign_word}

    # 1. Hook — pattern interrupt
    scenes.append({
        "filename": "01-hook.png",
        "alert": True,
        "render_args": {
            "eyebrow": "scam alert",
            "headline": tpl["hook_headline"].format(**fmt_kwargs),
            "alert": True,
        },
        "speech": tpl["hook_speech"].format(**fmt_kwargs),
    })

    # 2. Promise / setup
    scenes.append({
        "filename": "02-promise.png",
        "render_args": {
            "eyebrow": "in this short",
            "big_number": str(len(warnings)),
            "headline": f"warning {sign_word} to spot",
        },
        "speech": tpl["promise"].format(**fmt_kwargs),
    })

    # 3..N. Warning cards
    for i, w in enumerate(warnings, start=1):
        scenes.append({
            "filename": f"03-sign-{i}.png",
            "render_args": {
                "eyebrow": f"sign {i} of {len(warnings)}",
                "headline": w,
            },
            "speech": f"Sign {_num_word(i)}. {w}.",
        })

    # N+1. Verify — family-specific advice. The HOOK_TEMPLATES family that
    # picked the hook also dictates the verify message, so Hi Mum scams say
    # "call them on their old number" instead of generic "official site"
    # advice that doesn't apply. Falls back to the message-family default.
    scenes.append({
        "filename": "04-verify.png",
        "render_args": {
            "eyebrow": "do this instead",
            "headline": tpl["verify_headline"],
        },
        "speech": tpl["verify_speech"],
    })

    # N+2. CTA
    scenes.append({
        "filename": "05-cta.png",
        "render_args": {
            "eyebrow": "full guide at",
            "headline": full_title,
            "cta": "beatthescam.com",
        },
        "speech": "Full guide at beat the scam dot com.",
    })

    # N+3. End card — branded close.
    # Uses the static designed image at assets/video/end-card.png when present
    # (consistent across every video). Falls back to a generated card otherwise
    # so the script keeps working on a fresh checkout.
    use_static_endcard = END_CARD_IMAGE.exists()
    scenes.append({
        "filename": "06-end.png",
        "static_image": END_CARD_IMAGE if use_static_endcard else None,
        "render_args": {
            "eyebrow": "remember",
            "headline": "Stay safe out there.",
            "headline_size": 130,
            "alert": False,
        },
        "speech": "Remember — Beat the Scam.",
        # End card lingers a little — viewers need time to read the brand
        # info, URL, and feature pills before the video loops/cuts.
        "min_duration": 4.5,
    })

    # Apply phonetic overrides to all speech AFTER building the storyboard,
    # so display text stays untouched and "Revolut" shows correctly on cards.
    for s in scenes:
        s["speech"] = for_speech(s["speech"])

    return scenes


def _num_word(n: int) -> str:
    return {1: "one", 2: "two", 3: "three", 4: "four", 5: "five"}.get(n, str(n))


# ─── TTS ───────────────────────────────────────────────────────────────────

def _synth_elevenlabs(text: str, out_mp3: Path) -> Path:
    """Synthesize via ElevenLabs (preferred — far more natural than gTTS)."""
    client = ElevenLabs(api_key=ELEVEN_API_KEY)
    stream = client.text_to_speech.convert(
        voice_id=ELEVEN_VOICE_ID,
        model_id=ELEVEN_MODEL_ID,
        text=text,
        output_format="mp3_44100_128",
    )
    out_mp3.parent.mkdir(parents=True, exist_ok=True)
    with open(out_mp3, "wb") as f:
        for chunk in stream:
            if chunk:
                f.write(chunk)
    return out_mp3


def _synth_gtts(text: str, out_mp3: Path) -> Path:
    """Fallback TTS via gTTS — free, UK accent, robotic intonation."""
    if not _GTTS_OK:
        raise SystemExit("Neither ElevenLabs API key nor gTTS available.")
    out_mp3.parent.mkdir(parents=True, exist_ok=True)
    # tld='co.uk' gives a UK-accented voice instead of the default US one
    tts = gTTS(text=text, lang="en", tld="co.uk", slow=False)
    tts.save(str(out_mp3))
    return out_mp3


def synth_tts(text: str, out_mp3: Path) -> Path:
    """Synthesize speech. Prefers ElevenLabs when ELEVENLABS_API_KEY is set,
    falls back to gTTS so the script keeps working without paid credits."""
    if ELEVEN_API_KEY and _ELEVEN_OK:
        return _synth_elevenlabs(text, out_mp3)
    return _synth_gtts(text, out_mp3)


def tts_provider_label() -> str:
    if ELEVEN_API_KEY and _ELEVEN_OK:
        return f"ElevenLabs (voice={ELEVEN_VOICE_ID[:8]}…, model={ELEVEN_MODEL_ID})"
    if _GTTS_OK:
        return "gTTS (UK English, free fallback)"
    return "<no TTS provider available>"


def audio_duration(path: Path) -> float:
    """Get audio duration in seconds via MoviePy."""
    with AudioFileClip(str(path)) as a:
        return float(a.duration)


# ─── Assembly ──────────────────────────────────────────────────────────────

def build_video(post, slug: str, out_dir: Path, music_path: Optional[Path]) -> Path:
    frames_dir = out_dir / f"{slug}-frames"
    audio_dir  = out_dir / f"{slug}-audio"
    for d in (frames_dir, audio_dir):
        if d.exists():
            shutil.rmtree(d)

    scenes = build_scripts(post)

    # 1. Render each card PNG — or use a pre-designed static image when supplied
    print(f"→ Rendering {len(scenes)} cards…")
    for s in scenes:
        target = frames_dir / s["filename"]
        static = s.get("static_image")
        if static and Path(static).exists():
            shutil.copy(static, target)
        else:
            render_card(target, **s["render_args"])

    # 2. Synthesize TTS per card; this also gives us per-card duration
    print(f"→ Synthesising voiceover ({len(scenes)} clips via {tts_provider_label()})…")
    for i, s in enumerate(scenes, start=1):
        mp3 = audio_dir / f"{i:02d}.mp3"
        synth_tts(s["speech"], mp3)
        s["audio_path"] = mp3
        s["audio_dur"]  = audio_duration(mp3)
        # Card duration = speech + tail buffer, but never shorter than the
        # scene's declared min_duration (useful for the end card so viewers
        # have time to read the static brand layout).
        s["scene_dur"]  = max(s.get("min_duration", 2.0), s["audio_dur"] + 0.6)

    total = sum(s["scene_dur"] for s in scenes)
    print(f"  total target duration: {total:.1f}s")
    for s in scenes:
        print(f"   {s['scene_dur']:>4.1f}s  {s['filename']:25s}  ⌜{s['speech'][:60]}…⌟")

    # 3. Build per-scene video clips with Ken Burns zoom + crossfade
    overlap = 0.35  # crossfade duration
    timeline = []
    cursor = 0.0
    for i, s in enumerate(scenes):
        dur = s["scene_dur"]

        # Image clip; the slow zoom is the "motion" — keeps the eye engaged
        # without the cards feeling like a static slideshow.
        clip = (
            ImageClip(str(frames_dir / s["filename"]))
            .with_duration(dur)
            .resized(lambda t, d=dur: 1.0 + 0.04 * (t / d))  # 4% zoom across the card
        )

        # Per-card voice
        voice = AudioFileClip(str(s["audio_path"])).with_start(0)
        clip  = clip.with_audio(voice)

        # Crossfade in for all but the first card
        if i > 0:
            clip = clip.with_effects([CrossFadeIn(overlap)])

        clip = clip.with_start(cursor)
        timeline.append(clip)
        cursor += dur - overlap

    final_duration = cursor + overlap
    video = CompositeVideoClip(timeline, size=(W, H)).with_duration(final_duration)

    # 4. Mix background music at -20dB if present
    if music_path and music_path.exists():
        try:
            with AudioFileClip(str(music_path)) as raw:
                music_dur = float(raw.duration)
            music = AudioFileClip(str(music_path))
            if music_dur >= final_duration:
                music = music.subclipped(0, final_duration)
            else:
                # If shorter than the video, leave it to play once and cut.
                # Looping in v2 needs audio_loop fx; for a test, a single play
                # is usually fine since news beds are typically 30-60s.
                pass
            music = music.with_volume_scaled(0.1)  # -20 dB
            mixed_audio = CompositeAudioClip([video.audio, music])
            video = video.with_audio(mixed_audio)
            print(f"→ Mixed music bed at -20dB: {music_path.name}")
        except Exception as e:
            print(f"  (music skipped — could not load {music_path.name}: {e})")
    else:
        print("→ No music bed (drop a file at assets/audio/news-bed.mp3 to enable)")

    # 5. Render
    out_path = out_dir / f"{slug}.mp4"
    print(f"\n→ Encoding MP4 → {out_path}")
    video.write_videofile(
        str(out_path),
        fps=FPS,
        codec="libx264",
        audio_codec="aac",
        audio_bitrate="192k",
        preset="medium",
        bitrate="5000k",
        threads=4,
        logger=None,
    )
    return out_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("slug", help="post slug from content/posts.json")
    parser.add_argument("--posts", default="content/posts.json")
    parser.add_argument("--out-dir", default="out/videos")
    parser.add_argument("--music", default=str(DEFAULT_MUSIC),
                        help=f"background music path (default: {DEFAULT_MUSIC})")
    parser.add_argument("--no-music", action="store_true",
                        help="skip background music even if file exists")
    args = parser.parse_args()

    posts = json.loads(Path(args.posts).read_text(encoding="utf-8"))
    post = next((p for p in posts if p.get("slug") == args.slug), None)
    if not post:
        sys.exit(f"slug not found: {args.slug!r}")

    out_dir = Path(args.out_dir)
    music_path = None if args.no_music else Path(args.music)

    out_path = build_video(post, args.slug, out_dir, music_path)
    size_mb = out_path.stat().st_size / (1024 * 1024)
    print(f"\n✓ Done — {out_path} ({size_mb:.2f} MB)")
    print(f"  Inspect frames: {out_dir / (args.slug + '-frames')}")

    # Render YouTube thumbnail alongside the MP4. upload_to_youtube.py picks
    # this up automatically if it's present at {slug}.thumbnail.jpg.
    thumb_path = out_dir / f"{args.slug}.thumbnail.jpg"
    topic = short_topic(post)
    family = _topic_family(post)
    render_thumbnail(thumb_path, topic=topic, family=family)
    thumb_kb = thumb_path.stat().st_size // 1024
    print(f"  Thumbnail:      {thumb_path} ({thumb_kb} KB)")


if __name__ == "__main__":
    main()
