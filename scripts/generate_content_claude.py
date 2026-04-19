import argparse
import csv
import json
import os
from datetime import datetime
from typing import Dict, List

from anthropic import Anthropic


# ---------------------------
# Helpers
# ---------------------------

def slugify(text: str) -> str:
    return text.lower().strip().replace(" ", "-").replace("?", "").replace(",", "")


def load_posts(path: str) -> List[Dict]:
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
import argparse
import csv
import json
import os
import re
from dataclasses import dataclass
from typing import Dict, List, Sequence

from anthropic import Anthropic


DEFAULT_MODEL = "claude-haiku-4-5-20251001"
REQUIRED_FIELDS = [
    "title",
    "slug",
    "category",
    "excerpt",
    "description",
    "hero",
    "date",
    "content",
    "sections",
    "faq",
    "keywords",
]


@dataclass
class Topic:
    keyword: str
    entity: str
    category: str


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"\s+", "-", text)
    text = re.sub(r"-{2,}", "-", text)
    return text.strip("-")


def clean_text(value: str) -> str:
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
    return any(post.get("slug") == slug for post in posts)


def read_topics(csv_path: str) -> List[Topic]:
    topics: List[Topic] = []
    with open(csv_path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            keyword = clean_text(row.get("keyword", ""))
            entity = clean_text(row.get("entity", ""))
            category = clean_text(row.get("category", ""))

            if not keyword:
                continue

            if not entity:
                entity = keyword

            if not category:
                category = "website"

            topics.append(Topic(keyword=keyword, entity=entity, category=category))
    return topics


def build_sections(keyword: str, entity: str, category: str, excerpt: str) -> List[List[str]]:
    return [
        [
            "Quick answer",
            excerpt,
        ],
        [
            "Warning signs",
            "- Pressure to act immediately\n- Requests for payment, login details, or one-time codes\n- Suspicious links or domains\n- Requests for upfront payment\n- Messages that create urgency or fear",
        ],
        [
            "How this scam usually works",
            f"Scammers impersonate trusted names such as {entity} to extract money, account access, or personal information. The usual pattern is urgency, impersonation, and a push to click a link or send payment.",
        ],
        [
            "How to verify safely",
            "Go to the official website manually, verify the domain carefully, and use independently verified contact details before taking any action.",
        ],
        [
            "What to do if you already interacted",
            "Change passwords immediately, contact your bank if payment details were involved, keep evidence, and report the incident through the relevant UK channel such as Action Fraud.",
        ],
    ]


def markdown_from_sections(sections: List[List[str]]) -> str:
    parts: List[str] = []
    for title, body in sections:
        parts.append(f"## {title}\n\n{body}")
    return "\n\n".join(parts)


def build_faq(keyword: str, entity: str) -> List[List[str]]:
    return [
        [
            f"Is {entity} a scam?",
            f"{entity} itself may be legitimate, but scammers often impersonate it. Always verify the source independently before acting.",
        ],
        [
            f"How can I verify {entity} safely?",
            "Use the official website directly, avoid message links, and confirm contact details through trusted public sources.",
        ],
        [
            "What should I do if I already interacted?",
            "Change passwords, contact your bank if needed, keep evidence, and report the incident through the relevant UK reporting route.",
        ],
    ]


def validate_post(post: Dict) -> None:
    for field in REQUIRED_FIELDS:
        if field not in post:
            raise ValueError(f"Missing required field: {field}")

    if not isinstance(post["sections"], list) or not post["sections"]:
        raise ValueError("Post sections must be a non-empty list")

    if not isinstance(post["faq"], list) or not post["faq"]:
        raise ValueError("Post faq must be a non-empty list")

    if not isinstance(post["keywords"], list) or not post["keywords"]:
        raise ValueError("Post keywords must be a non-empty list")


def enforce_structure(data: Dict, topic: Topic, date: str) -> Dict:
    keyword = topic.keyword
    entity = topic.entity
    category = topic.category

    title = clean_text(data.get("title", "")) or f"{keyword.title()} (2026 Guide)"
    slug = slugify(clean_text(data.get("slug", "")) or keyword)
    excerpt = clean_text(data.get("excerpt", "")) or f"A practical UK-focused guide to {keyword}, including warning signs, verification steps, and what to do if targeted."
    description = clean_text(data.get("description", "")) or excerpt
    hero = clean_text(data.get("hero", "")) or description
    post_category = clean_text(data.get("category", "")) or category

    sections = build_sections(keyword, entity, post_category, description)
    faq = build_faq(keyword, entity)
    content = markdown_from_sections(sections)

    keywords = data.get("keywords") or [
        keyword,
        post_category,
        entity,
        f"{keyword} uk",
        f"{keyword} scam",
    ]
    keywords = [clean_text(k) for k in keywords if clean_text(str(k))]

    post = {
        "title": title,
        "slug": slug,
        "category": post_category,
        "excerpt": excerpt,
        "description": description,
        "hero": hero,
        "date": date,
        "content": content,
        "sections": sections,
        "faq": faq,
        "keywords": keywords,
    }

    validate_post(post)
    return post


def template_post(topic: Topic, date: str) -> Dict:
    keyword = topic.keyword
    entity = topic.entity
    category = topic.category

    raw = {
        "title": f"{keyword.title()} (2026 Guide)",
        "slug": slugify(keyword),
        "category": category,
        "excerpt": f"A practical UK-focused guide to {keyword}, including warning signs, verification steps, and what to do if targeted.",
        "description": f"A practical UK-focused guide to {keyword}, including warning signs, verification steps, and what to do if targeted.",
        "hero": f"A practical UK-focused guide to {keyword}, including warning signs, verification steps, and what to do if targeted.",
        "keywords": [
            keyword,
            category,
            entity,
            f"{keyword} uk",
            f"{keyword} scam",
        ],
    }
    return enforce_structure(raw, topic, date)


def extract_json_object(text: str) -> Dict:
    text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError("No JSON object found in Claude response")

    return json.loads(match.group(0))


def claude_post(topic: Topic, date: str, model: str) -> Dict:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set in this terminal session")

    client = Anthropic(api_key=api_key)

    prompt = f"""Write a UK-focused scam-awareness article seed as JSON only.

Topic keyword: {topic.keyword}
Entity: {topic.entity}
Category: {topic.category}

Return JSON only with these keys:
title
slug
category
excerpt
description
hero
keywords

Rules:
- Keep it factual and practical.
- Do not use markdown.
- slug must be lowercase with hyphens.
- excerpt and description should be concise and useful.
- hero should be one short lead sentence.
- keywords should be a short array of strings.
"""

    response = client.messages.create(
        model=model,
        max_tokens=900,
        messages=[{"role": "user", "content": prompt}],
    )

    text_blocks = []
    for block in response.content:
        if getattr(block, "type", None) == "text":
            text_blocks.append(block.text)

    raw_text = "\n".join(text_blocks).strip()
    raw_data = extract_json_object(raw_text)
    return enforce_structure(raw_data, topic, date)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_file")
    parser.add_argument("--posts", required=True)
    parser.add_argument("--mode", choices=["claude", "template"], default="template")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--date", default="2026-04-17")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    posts = load_posts(args.posts)
    topics = read_topics(args.csv_file)

    added = 0

    for topic in topics:
        slug = slugify(topic.keyword)

        if topic_exists(posts, slug) and not args.force:
            continue

        if args.mode == "claude":
            post = claude_post(topic, args.date, args.model)
        else:
            post = template_post(topic, args.date)

        if args.force:
            posts = [p for p in posts if p.get("slug") != post["slug"]]

        posts.append(post)
        added += 1

    save_posts(args.posts, posts)
    print(f"Added {added} post(s) to {args.posts}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

def save_posts(path: str, posts: List[Dict]):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(posts, f, indent=2, ensure_ascii=False)


def topic_exists(posts: List[Dict], slug: str) -> bool:
    return any(p.get("slug") == slug for p in posts)


# ---------------------------
# STRUCTURE ENFORCER (CRITICAL)
# ---------------------------

def enforce_structure(data: Dict, topic: Dict, date: str) -> Dict:
    keyword = topic.get("keyword", "").strip()
    entity = topic.get("entity", keyword)
    category = topic.get("category", "website")

    data["slug"] = slugify(data.get("slug") or keyword)
    data["category"] = data.get("category") or category

    data["excerpt"] = data.get("excerpt") or f"A practical UK-focused guide to {keyword}."
    data["description"] = data.get("description") or data["excerpt"]
    data["hero"] = data.get("hero") or data["description"]
    data["date"] = date

    data["keywords"] = data.get("keywords") or [
        keyword,
        category,
        entity,
        f"{keyword} uk",
        f"{keyword} scam",
    ]

    # FORCE SECTIONS
    data["sections"] = [
        {"title": "Quick answer", "body": data["description"]},
        {"title": "Warning signs", "body": "- Urgency\n- Payment requests\n- Suspicious links\n- Impersonation"},
        {"title": "How this scam usually works", "body": f"Scammers impersonate {entity} to extract money or data."},
        {"title": "How to verify safely", "body": "Check official sites, avoid message links, verify domains."},
        {"title": "What to do if you already interacted", "body": "Change passwords, contact bank, report to Action Fraud."}
    ]

    # FORCE FAQ
    data["faq"] = [
        [f"Is {entity} a scam?", f"{entity} may be legitimate, but scams often impersonate it."],
        [f"How do I verify {entity}?", "Use official website and trusted sources."],
        ["What should I do if scammed?", "Contact your bank and report it immediately."]
    ]

    return data


# ---------------------------
# CLAUDE GENERATION
# ---------------------------

def claude_post(topic: Dict, date: str) -> Dict:
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set")

    client = Anthropic(api_key=api_key)

    keyword = topic["keyword"]
    entity = topic.get("entity", keyword)
    category = topic.get("category", "website")

    prompt = f"""
Write a UK-focused scam awareness article.

Topic: {keyword}

Return JSON only with:
title, slug, excerpt, description, content, keywords
"""

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = response.content[0].text.strip()

    try:
        data = json.loads(raw)
    except:
        data = {
            "title": f"{keyword.title()} (2026 Guide)",
            "slug": slugify(keyword),
            "excerpt": f"A guide to {keyword}.",
            "description": f"A guide to {keyword}.",
            "content": f"Guide about {keyword}.",
            "keywords": [keyword],
        }

    return enforce_structure(data, topic, date)


# ---------------------------
# FALLBACK TEMPLATE
# ---------------------------

def template_post(topic: Dict, date: str) -> Dict:
    keyword = topic["keyword"]

    data = {
        "title": f"{keyword.title()} (2026 Guide)",
        "slug": slugify(keyword),
        "excerpt": f"A guide to {keyword}.",
        "description": f"A guide to {keyword}.",
        "content": f"Guide about {keyword}.",
        "keywords": [keyword],
    }

    return enforce_structure(data, topic, date)


# ---------------------------
# MAIN
# ---------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_file")
    parser.add_argument("--posts", required=True)
    parser.add_argument("--mode", choices=["claude", "template"], default="template")
    parser.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"))
    args = parser.parse_args()

    posts = load_posts(args.posts)

    added = 0

    with open(args.csv_file, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for topic in reader:
            slug = slugify(topic["keyword"])

            if topic_exists(posts, slug):
                continue

            if args.mode == "claude":
                post = claude_post(topic, args.date)
            else:
                post = template_post(topic, args.date)

            posts.append(post)
            added += 1

    save_posts(args.posts, posts)

    print(f"Added {added} post(s) to {args.posts}")


if __name__ == "__main__":
    main()