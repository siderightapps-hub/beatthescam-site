"""
generate_content_claude.py
Generates full 800-1200 word scam-awareness guides using the Claude API.
Each section is written by Claude with genuine, specific content.
"""

import argparse
import csv
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime, date
from pathlib import Path
from typing import Dict, List, Sequence

from anthropic import Anthropic

from content_gate import run_gate, ACCURACY_BLOCK, quarantine_post, write_manifest

DEFAULT_MODEL   = "claude-haiku-4-5-20251001"
REQUIRED_FIELDS = ["title", "slug", "category", "excerpt", "description",
                   "hero", "date", "content", "sections", "faq", "keywords"]


# ─── DATA CLASSES ────────────────────────────────────────────────────────────

@dataclass
class Topic:
    keyword:  str
    entity:   str
    category: str


# ─── HELPERS ─────────────────────────────────────────────────────────────────

def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"\s+", "-", text)
    return re.sub(r"-{2,}", "-", text).strip("-")


def clean(value) -> str:
    return (value or "").strip()


def load_posts(path: str) -> List[Dict]:
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_posts(path: str, posts: List[Dict]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(posts, f, indent=2, ensure_ascii=False)


def topic_exists(posts: Sequence[Dict], slug: str) -> bool:
    return any(p.get("slug") == slug for p in posts)


def read_topics(csv_path: str) -> List[Topic]:
    topics: List[Topic] = []
    with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            kw = clean(row.get("keyword", ""))
            if not kw:
                continue
            topics.append(Topic(
                keyword=kw,
                entity=clean(row.get("entity", "")) or kw,
                category=clean(row.get("category", "")) or "website",
            ))
    return topics


def extract_json(text: str) -> Dict:
    text = text.strip()
    # Strip markdown fences
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise ValueError("No valid JSON in Claude response")


# ─── CLAUDE PROMPT ───────────────────────────────────────────────────────────

SYSTEM_PROMPT = f"""You are a UK consumer protection writer for the website Beat the Scam (beatthescam.com).
You write practical, detailed scam-awareness guides for ordinary UK residents.

Your writing style:
- Plain English, no jargon
- Specific and practical — not generic advice
- UK-focused (Report Fraud, NCSC, Citizens Advice, UK banks, UK platforms)
- Calm tone — not alarmist
- Reference named companies, products, and organisations only when you are confident they are real and publicly verifiable

{ACCURACY_BLOCK}

You ALWAYS respond with valid JSON only. No markdown fences, no preamble, no trailing text."""


def build_prompt(topic: Topic, all_slugs: List[str]) -> str:
    # Pick 3-4 related slugs for internal linking suggestions
    related = [s for s in all_slugs if s != slugify(topic.keyword)][:8]
    related_str = ", ".join(f"/guides/{s}/" for s in related[:4]) if related else "none available yet"

    return f"""Write a complete UK scam-awareness guide for: "{topic.keyword}"

Entity being impersonated or platform: {topic.entity}
Category: {topic.category}

Return a single JSON object with exactly these fields:

{{
  "title": "SEO-optimised title (include UK, include the main keyword)",
  "slug": "lowercase-hyphenated-slug",
  "category": "{topic.category}",
  "excerpt": "One sentence (max 160 chars) summarising the guide for search results.",
  "description": "Two sentences expanding on the excerpt. Practical and specific.",
  "hero": "One punchy lead sentence for the article header.",
  "keywords": ["keyword 1", "keyword 2", "keyword 3", "keyword 4", "keyword 5"],
  "sections": [
    ["Section title", "Section body — 120 to 180 words of specific, practical content"],
    ...
  ],
  "faq": [
    ["Question?", "Answer — 2-3 sentences, specific and practical."],
    ...
  ]
}}

Section requirements — COVER ALL SIX essentials below, but DO NOT reuse a fixed template. Give each section a NATURAL, SCAM-SPECIFIC heading (e.g. "How the fake [brand] text reaches you" rather than the generic "How this scam works step by step"), and ORDER the sections the way someone searching for THIS specific scam would actually want to read them — lead with whatever matters most for the query (a "is [brand] legit?" review intent should open with the verdict; an "I've already been scammed" intent should open with what to do right now). Deliberately vary the structure from one guide to the next; you may split, merge, reorder, or add one extra section (5 to 8 sections total) where this scam genuinely warrants it. Do not pad — every section must earn its place.

The six essentials to cover (in whatever order, under whatever natural headings fit best):
- What the scam is — the specific pattern, explained clearly (120-180 words)
- The warning signs — 6-8 specific red flags as a bullet list (every item starts with "- "), 1-2 sentences each
- How it works — from first contact through to the money or data loss (150-200 words)
- How to verify whether it is genuine — verification steps specific to THIS exact scam. Where relevant, link to a related guide using one of these internal URLs: {related_str}
- What to do if you have already interacted — recovery actions in order of urgency (120-160 words)
- How to report it in the UK — specific routes with org names: Report Fraud (0300 123 2040), NCSC Suspicious Email Reporting Service (report@phishing.gov.uk), forward SMS to 7726, Citizens Advice consumer helpline (0808 223 1133) (120-150 words)

FAQ requirements — write 3 to 5 FAQs that are the REAL questions someone would type about THIS specific scam, varied from guide to guide (do not force a fixed set). Phrase each the natural way a worried person would ask it; do NOT write "Is [X] a legitimate company?" when [X] is a scam type rather than an actual company. Good candidates: whether a specific message / website / caller is genuine, what to do if money or details were already shared, a detail unique to this scam, and how to report it.

Rules:
- Every section body must be 120+ words. Short sections will be rejected.
- The warning-signs bullet list items must start with "- "
- All content must be specific to {topic.keyword}, not generic scam advice
- Keep the official reporting routes above (Report Fraud, NCSC, 7726, Citizens Advice) accurate and unchanged
- slug must be lowercase with hyphens only
- Return ONLY the JSON object, nothing else"""


# ─── GENERATION ──────────────────────────────────────────────────────────────

def claude_post(topic: Topic, today: str, model: str, client: Anthropic,
                all_slugs: List[str]) -> Dict:

    response = client.messages.create(
        model=model,
        max_tokens=3000,
        temperature=0,   # factual reference content — minimise creative drift
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": build_prompt(topic, all_slugs)}],
    )

    raw = "".join(b.text for b in response.content if getattr(b, "type", None) == "text")

    try:
        data = extract_json(raw)
    except Exception as e:
        # Malformed model output → do NOT silently publish a generic fallback
        # guide (Executive Verdict, Critical #3 — the fallback is ~490 templated
        # words, thin and low-value but not fabricated, so the gate wouldn't
        # catch it). Raise so the caller skips this topic; it retries next run.
        raise ValueError(f"malformed model output for '{topic.keyword}': {e}")

    # strict=True: valid JSON that yields <4 usable sections (dict-shaped
    # sections, refusals, truncation) must raise too — otherwise it would fall
    # through normalise()'s templated sections and publish a thin generic guide,
    # the same class Executive Verdict Critical #3 closed for malformed JSON.
    return normalise(data, topic, today, strict=True)


def fallback_post(topic: Topic, today: str) -> Dict:
    return normalise({}, topic, today)


def normalise(data: Dict, topic: Topic, today: str, strict: bool = False) -> Dict:
    """Validate and fill any missing fields with safe defaults.

    strict=True (claude mode) raises instead of substituting the templated
    sections, reserving the template purely for --mode template."""
    kw  = topic.keyword
    ent = topic.entity
    cat = topic.category

    title       = clean(data.get("title"))       or f"{kw.title()} — UK Guide {date.today().year}"
    slug        = slugify(clean(data.get("slug")) or kw)
    excerpt     = clean(data.get("excerpt"))      or f"A practical UK guide to {kw}."
    description = clean(data.get("description"))  or excerpt
    hero        = clean(data.get("hero"))         or description
    category    = clean(data.get("category"))     or cat
    keywords    = [clean(k) for k in (data.get("keywords") or []) if clean(str(k))]
    if not keywords:
        keywords = [kw, cat, ent, f"{kw} uk", f"{kw} scam"]

    # Validate sections — must be list of [str, str] pairs each 120+ words
    raw_sections = data.get("sections") or []
    sections: List[List[str]] = []
    for item in raw_sections:
        if isinstance(item, (list, tuple)) and len(item) >= 2:
            heading = clean(str(item[0]))
            raw_body = item[1]
            # If Claude returned a list (e.g. for bullet-point sections),
            # join with newlines so the renderer treats them as bullets.
            if isinstance(raw_body, list):
                body = clean("\n".join(str(x) for x in raw_body))
            else:
                body = clean(str(raw_body))
            if heading and body:
                sections.append([heading, body])

    # Fallback sections if Claude didn't deliver
    if len(sections) < 4:
        if strict:
            raise ValueError(
                f"model returned only {len(sections)} usable sections for "
                f"'{kw}' — refusing to publish the templated fallback")
        sections = [
            ["What is this scam?",
             f"{ent} impersonation scams target UK residents through fake messages, calls, or websites. "
             f"Fraudsters create convincing copies of {ent} communications to extract money, personal information, "
             f"or account access. These scams are sophisticated and can be difficult to distinguish from genuine contact. "
             f"The goal is always to create urgency — pressure you into acting quickly before you have time to think or verify."],
            ["Warning signs to look for",
             f"- Messages asking you to click a link or call a number not from {ent}'s official website\n"
             f"- Requests for payment, bank details, or one-time passcodes\n"
             f"- Unusual urgency — threats of fines, account suspension, or legal action\n"
             f"- Poor spelling or grammar in emails or texts\n"
             f"- Sender addresses that don't match {ent}'s official domain\n"
             f"- Requests to pay by bank transfer, cryptocurrency, or gift cards"],
            ["How this scam works step by step",
             f"The scam typically begins with an unsolicited message claiming to be from {ent}. "
             f"The message creates a sense of urgency — a package held, a tax refund, a security alert, or an overdue payment. "
             f"You are directed to a link or phone number controlled by the fraudster. "
             f"The fake site or operator collects payment details, login credentials, or one-time passcodes. "
             f"Once the fraudster has this information, they either take money directly or use the credentials to access your accounts. "
             f"Recovery is often difficult because bank transfers and some card payments are hard to reverse."],
            ["How to verify if it is genuine",
             f"Never use the contact details in the suspicious message. Instead, go directly to {ent}'s official website "
             f"by typing the address into your browser. Check your account or order history directly through the official app or website. "
             f"If in doubt, call {ent} using a number from their official website — not the one in the message. "
             f"For government bodies, cross-reference the sender's address against GOV.UK."],
            ["What to do if you have already interacted",
             f"If you have clicked a link: close the page immediately and run a virus scan. "
             f"If you have entered payment details: contact your bank immediately using the number on the back of your card. "
             f"If you have shared a one-time passcode: call your bank immediately as this may have authorised a payment. "
             f"Change passwords for any affected accounts. Enable two-factor authentication. "
             f"Document everything — screenshots, message text, dates — before reporting."],
            ["Reporting this scam in the UK",
             f"Report to Report Fraud online at reportfraud.police.uk or by phone on 0300 123 2040. "
             f"If you received a suspicious email, forward it to report@phishing.gov.uk (the NCSC's Suspicious Email Reporting Service). "
             f"If you received a suspicious text, forward it to 7726 — this is free on all UK networks and goes to your mobile operator. "
             f"You can also report to Citizens Advice on 0808 223 1133. "
             f"If money left your account, your bank's fraud team should be your first call — they can sometimes recall payments within 24 hours."],
        ]

    # Validate FAQ
    raw_faq = data.get("faq") or []
    faq: List[List[str]] = []
    for item in raw_faq:
        if isinstance(item, (list, tuple)) and len(item) >= 2:
            q, a = clean(str(item[0])), clean(str(item[1]))
            if q and a:
                faq.append([q, a])
    if len(faq) < 3:
        faq = [
            [f"Is every message from {ent} a scam?",
             f"No. {ent} does send legitimate communications. The key is to verify through official channels — "
             f"their website or official app — rather than trusting links or numbers in the message itself."],
            ["What should I do if I already sent money?",
             f"Contact your bank immediately using the number on the back of your card. "
             f"Banks can sometimes recall bank transfers if reported quickly. "
             f"Also report to Report Fraud at reportfraud.police.uk."],
            [f"How do I tell a fake {ent} website from the real one?",
             f"Check the domain name carefully — scammers use lookalike domains with extra words or different endings. "
             f"Always access the site by typing the address directly, not via a link in a message."],
            ["Who do I report this to in the UK?",
             f"Report to Report Fraud (0300 123 2040 or reportfraud.police.uk). "
             f"Forward suspicious texts to 7726 and emails to report@phishing.gov.uk."],
        ]

    content = "\n\n".join(f"## {t}\n\n{b}" for t, b in sections)

    post = {
        "title":       title,
        "slug":        slug,
        "category":    category,
        "excerpt":     excerpt,
        "description": description,
        "hero":        hero,
        "date":        today,
        "content":     content,
        "sections":    sections,
        "faq":         faq,
        "keywords":    keywords,
    }

    # Validate
    for field in REQUIRED_FIELDS:
        if field not in post:
            raise ValueError(f"Missing required field: {field}")

    return post


# ─── MAIN ────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description="Generate scam-awareness guides via Claude API")
    parser.add_argument("csv_file",           help="CSV file with keyword, entity, category columns")
    parser.add_argument("--posts",  required=True, help="Path to posts.json")
    parser.add_argument("--mode",   choices=["claude", "template"], default="claude")
    parser.add_argument("--model",  default=DEFAULT_MODEL)
    parser.add_argument("--date",   default=date.today().isoformat())
    parser.add_argument("--force",  action="store_true", help="Overwrite existing slugs")
    parser.add_argument("--no-gate", action="store_true",
                        help="Skip the accuracy gate entirely (manual override — unsafe for autonomous runs)")
    parser.add_argument("--gate-no-llm", action="store_true",
                        help="Run only the deterministic gate checks (skip the LLM judge)")
    args = parser.parse_args()

    posts  = load_posts(args.posts)
    topics = read_topics(args.csv_file)

    client     = None
    all_slugs  = [p["slug"] for p in posts]

    if args.mode == "claude":
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            print("ERROR: ANTHROPIC_API_KEY not set", file=sys.stderr)
            return 1
        client = Anthropic(api_key=api_key)

    added = 0
    published_slugs: List[str] = []     # real post slugs (URLs) — used for tweeting
    published_topics: List[str] = []    # topic slugs (slugify(keyword)) — used to mark queue rows
    quarantined_topics: List[str] = []  # topic slugs — used to mark queue rows
    skipped_topics: List[str] = []      # topic slugs already published under this slug — used to mark queue rows
    for topic in topics:
        slug = slugify(topic.keyword)

        if topic_exists(posts, slug) and not args.force:
            print(f"  skip  {slug} (already exists)")
            skipped_topics.append(slug)
            continue

        print(f"  gen   {slug} …", end=" ", flush=True)
        try:
            if args.mode == "claude":
                post = claude_post(topic, args.date, args.model, client, all_slugs)
            else:
                post = fallback_post(topic, args.date)
        except Exception as e:
            print(f"ERROR: {e}", file=sys.stderr)
            continue

        # ── Accuracy gate: PASS → publish, FAIL → quarantine (never published).
        result = None
        if args.mode == "claude" and not args.no_gate:
            result = run_gate(post, client=client, model=args.model,
                              use_llm=not args.gate_no_llm, corpus=posts)
            if not result.passed:
                quarantine_post(post, result, args.date)
                quarantined_topics.append(slug)
                print(f"QUARANTINED — {result.summary()}", file=sys.stderr)
                continue

        # The model (or the template) chooses its own post["slug"], which can
        # differ from slugify(topic.keyword) (already checked above) and collide
        # with an existing post. Re-check here, before the manifest write, so a
        # duplicate slug can neither overwrite another guide's manifest nor
        # silently replace its live page when build.py renders posts.json.
        if post["slug"] in all_slugs and not args.force:
            print(f"SKIPPED — generated slug '{post['slug']}' already exists", file=sys.stderr)
            skipped_topics.append(slug)
            continue

        if result is not None:
            # PASS → write the claim manifest (audit trail; never fail a publish on this)
            try:
                write_manifest(post, result, model=args.model, today=args.date)
            except Exception as e:
                print(f"  [warn] manifest write failed for {slug}: {e}", file=sys.stderr)

        if args.force:
            posts = [p for p in posts if p.get("slug") != post["slug"]]

        posts.append(post)
        all_slugs.append(post["slug"])
        published_slugs.append(post["slug"])
        published_topics.append(slug)
        added += 1
        wc = sum(len((t + " " + b).split()) for t, b in post["sections"])
        print(f"ok ({wc}w)")

    save_posts(args.posts, posts)
    print(f"\nDone: added {added} post(s) to {args.posts}")
    if quarantined_topics:
        print(f"Quarantined {len(quarantined_topics)} topic(s) for review: {', '.join(quarantined_topics)}")
    # Machine-readable lines the orchestrator (run_daily_publish.py) parses.
    # GATE_PUBLISHED   = real post slugs (for tweeting / NEW_ARTICLE_SLUGS).
    # *_TOPICS         = topic slugs (slugify(keyword)) used to mark the right queue
    #                    rows; the post slug can differ when the model picks its own.
    # GATE_SKIPPED_TOPICS = topic slugs that already exist under this slug — resolved,
    #                       not retried, but not a fresh publish either (no tweet).
    print(f"GATE_PUBLISHED={','.join(published_slugs)}")
    print(f"GATE_PUBLISHED_TOPICS={','.join(published_topics)}")
    print(f"GATE_QUARANTINED_TOPICS={','.join(quarantined_topics)}")
    print(f"GATE_SKIPPED_TOPICS={','.join(skipped_topics)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
