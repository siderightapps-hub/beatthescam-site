"""Shared representation rules; these never confer reporting authority.

The legacy prose authorisers intentionally keep their historical grammars.
Structured destinations and raw-number review use the primitive below instead.
"""
import re
import unicodedata
from html import escape


# Exactly one leading slash, nonempty ASCII slug segments, optional final slash.
# No decoding, trimming, case folding or label-based trust at this boundary.
INTERNAL_PATH = r"/[a-z0-9_-]+(?:/[a-z0-9_-]+)*/?"
INTERNAL_MARKDOWN_LINK_RE = re.compile(
    r"\[([^\]\n]+)\]\((" + INTERNAL_PATH + r")\)", re.I | re.ASCII)
INVALID_MARKDOWN_LINK_RE = re.compile(
    r"(?:\[[^\]\n]+)?\]\((?!" + INTERNAL_PATH + r"\))[^)]*\)", re.I | re.ASCII)

# Explicitly supported display separators. Tabs/newlines, slashes, commas,
# zero-width/bidi characters, letters and digit lookalikes are NOT stripped.
PHONE_SEPARATORS = " .-()\u00a0\u202f\u2009\u2010\u2011\u2012\u2013\u2014\u2015\u2212"
NUMERIC_RUN_RE = re.compile(
    r"(?<!\w)\+?\d(?:[\d" + re.escape(PHONE_SEPARATORS) + r"]*\d)?(?!\w)")


def inline_html(text):
    """The renderer's actual inline conversion, shared with its validator."""
    escaped = escape(text)
    escaped = re.sub(r"`([^`]+)`", lambda m: f"<code>{m.group(1)}</code>", escaped)
    return INTERNAL_MARKDOWN_LINK_RE.sub(
        lambda m: f'<a href="{m.group(2)}">{m.group(1)}</a>', escaped)


def schema_plain(text):
    return INTERNAL_MARKDOWN_LINK_RE.sub(
        lambda m: m.group(1), str(text).strip().replace("`", ""))


def normalize_bullet_body(para):
    """Legacy list-literal conversion. Validation uses this exact conversion."""
    if isinstance(para, list):
        return "\n".join(str(x) for x in para)
    if not isinstance(para, str):
        return str(para)
    s = para.strip()
    if (s.startswith("['") or s.startswith('["')) and s.endswith("]"):
        try:
            import ast
            parsed = ast.literal_eval(s)
            if isinstance(parsed, list):
                return "\n".join(str(item) for item in parsed)
        except (ValueError, SyntaxError):
            pass
    return para


def numeric_fragments(text):
    """Detection only: punctuation/space/marks cannot split a numeric hold.

    Unlike normalize_phone this NEVER produces a trusted identity. Unsupported
    separators (including all marks and controls) stay ambiguous. Letters end a
    run; alphanumeric identifiers remain identifiers, not telephone identities.
    """
    return [m.group() for m in re.finditer(
        r"(?<![^\W_])\d(?:[\d\W_]*\d)?(?![^\W_])", text)
        if sum(unicodedata.category(c) == "Nd" for c in m.group()) >= 3]


_STEP_RE = re.compile(r"\bStep\s+\d+\s*[:.\)\-–]\s*", re.IGNORECASE)
_PAREN_NUM_RE = re.compile(r"\((\d+)\)\s+")


def parse_numbered_steps(text):
    """The renderer's numbered-step extraction, shared with validation."""
    text = (text or "").strip()
    if not text:
        return []
    if _STEP_RE.search(text):
        steps = [p.strip().rstrip(".") for p in _STEP_RE.split(text) if p.strip()]
        if len(steps) >= 3:
            return steps
    if _PAREN_NUM_RE.search(text):
        parts = _PAREN_NUM_RE.split(text)
        steps = [parts[i].strip().rstrip(";.") for i in range(2, len(parts), 2)
                 if parts[i].strip().rstrip(";.")]
        if len(steps) >= 3:
            return steps
    return []


def howto_step_text(text):
    """Validate AFTER this truncation: it can expose a numeric token boundary."""
    return str(text).replace("`", "")[:500]


def normalize_phone(value, *, kind=None):
    """Normalize a representation, never infer a phone or authorize a number.

    NFC is deliberate: compatibility digits such as superscripts/circled
    numbers must not become trusted digits. Map ONLY Unicode decimal (Nd)
    characters through decimal(); reject every other nonseparator. Preserve
    a literal leading + and all digits, including any country/trunk prefix.
    There is no +44/0044/domestic aliasing or correction of optional '(0)'.

    A declared phone needs 7–15 digits; a shortcode needs 3–6 and no plus.
    kind=None is representation-only for the conservative raw numeric hold:
    dates, versions, amounts and IPs are not thereby classified as phones.
    Canon admission additionally requires its narrow ASCII serialization.
    """
    if not isinstance(value, str) or not value or kind not in (None, "phone", "shortcode", "voice-shortcode"):
        return None
    value = unicodedata.normalize("NFC", value)
    plus = value.startswith("+")
    body = value[1:] if plus else value
    digits = []
    for char in body:
        if unicodedata.category(char) == "Nd":
            digits.append(str(unicodedata.decimal(char)))
        elif char not in PHONE_SEPARATORS:
            return None
    if not digits:
        return None
    if kind == "phone" and not 7 <= len(digits) <= 15:
        return None
    if kind in ("shortcode", "voice-shortcode") and (plus or not 3 <= len(digits) <= 6):
        return None
    return ("+" if plus else "") + "".join(digits)
