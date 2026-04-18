import os, csv, json, re, sys
from pathlib import Path
from typing import List, Dict

try:
    import anthropic
except Exception:
    anthropic = None

ROOT = Path(__file__).resolve().parents[1]


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return re.sub(r"-+", "-", text).strip("-")


def read_topics(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def read_posts(path: Path) -> List[Dict]:
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def write_posts(path: Path, posts: List[Dict]):
    path.write_text(json.dumps(posts, indent=2, ensure_ascii=False), encoding="utf-8")


def fallback_post(topic: Dict[str, str], date: str) -> Dict:
    keyword = topic["keyword"].strip()
    entity = topic.get("entity", "this service").strip() or "this service"
    slug = slugify(keyword)
    category = topic.get("category", "website").strip() or "website"
    title = keyword.title() if "?" in keyword else f"{keyword.title()} (2026 Guide)"
    excerpt = f"A practical UK-focused guide to {keyword}, with warning signs, verification steps, and what to do if you have already engaged."
    content = f"""## Quick answer

{entity} may be legitimate in some contexts, but scammers often imitate brands, websites, texts, emails, or payment flows. You should verify the source independently before taking any action.

## Warning signs

- Pressure to act immediately
- Requests for payment, login details, or one-time codes
- Mismatched domains, email addresses, or phone numbers
- Links that do not clearly match the official brand
- Claims that you must pay first to release funds or prizes

## How this scam usually works

Scammers often copy the branding or tone of a real business, then push the target to click a link, sign in, transfer money, or disclose sensitive information. The tactic varies by channel, but the pattern is usually urgency plus impersonation.

## How to verify safely

1. Go to the official website manually rather than using a message link.
2. Check whether the email domain or website domain exactly matches the real brand.
3. Contact the company using contact details from its official website.
4. Do not share one-time passcodes, card details, or ID documents until you have verified the source.

## What to do if you already interacted

- Change passwords immediately if you entered them anywhere suspicious.
- Contact your bank or card provider if you made a payment.
- Report the incident to Action Fraud or the relevant UK reporting channel.
- Keep screenshots, transaction records, and message copies for evidence.
"""
    sections = [
        {
            "title": "Quick answer",
            "body": f"{entity} may be legitimate in some contexts, but scammers often imitate brands, websites, texts, emails, or payment flows. You should verify the source independently before taking any action."
        },
        {
            "title": "Warning signs",
            "body": "- Pressure to act immediately\n- Requests for payment, login details, or one-time codes\n- Mismatched domains, email addresses, or phone numbers\n- Links that do not clearly match the official brand\n- Claims that you must pay first to release funds or prizes"
        },
        {
            "title": "How this scam usually works",
            "body": "Scammers often copy the branding or tone of a real business, then push the target to click a link, sign in, transfer money, or disclose sensitive information."
        },
        {
            "title": "How to verify safely",
            "body": "1. Go to the official website manually rather than using a message link.\n2. Check whether the domain exactly matches the real brand.\n3. Contact the company using official details.\n4. Do not share sensitive data until verified."
        },
        {
            "title": "What to do if you already interacted",
            "body": "Change passwords, contact your bank, keep evidence, and report the incident to the appropriate UK authority."
        }
    ]

    faq = [
        [
            f"How can I check whether {entity} is real?",
            "Go to the official website manually, verify the domain carefully, and contact the organisation using details published on its real site."
        ],
        [
            "What should I do if I clicked a suspicious link?",
            "Stop interacting, close the page, change any affected passwords, run a device security check, and monitor your accounts."
        ],
        [
            "What if I already paid money?",
            "Contact your bank or card provider immediately, explain what happened, and ask what fraud or chargeback options are available."
        ]
    ]
    
    post = {
        "title": title,
        "slug": slug,
        "category": category,
        "excerpt": excerpt,
        "description": excerpt,
        "date": date,
        "content": content,
        "sections": sections,
        "faq": faq,
        "keywords": [
            keyword,
            category,
            entity,
            f"{keyword} uk",
            f"{keyword} scam",
        ],
    }

    post["keywords"] = [k for k in post["keywords"] if k]

    return post
    
def claude_post(topic: Dict[str, str], date: str, model: str = "claude-3-5-sonnet-latest") -> Dict:
    if anthropic is None:
        raise RuntimeError("anthropic SDK not installed")
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY not set")

    client = anthropic.Anthropic(api_key=api_key)

    keyword = topic["keyword"].strip()
    entity = topic.get("entity", "").strip()
    category = topic.get("category", "website").strip() or "website"
    type_ = topic.get("type", "website").strip() or "website"
    money_angle = topic.get("money_angle", "").strip()
    urgency = topic.get("urgency", "").strip()
    risk_hint = topic.get("risk_hint", "").strip()

    prompt = f'''You are generating one UK-focused scam-awareness article for a static website.
Return ONLY valid JSON with these keys exactly:
- title
- slug
- category
- excerpt
- description
- keywords
- date
- content

Rules:
- Target keyword: {keyword}
- Category: {category}
- Type: {type_}
- Entity: {entity}
- Money angle: {money_angle}
- Urgency: {urgency}
- Risk hint: {risk_hint}
- Date: {date}
- Slug must be lowercase with hyphens only.
- Excerpt must be 20-35 words.
- Description should match the excerpt closely and be suitable for SEO.
- Keywords must be a short JSON array of 4 to 6 relevant strings.
- Content must be markdown and include these H2 sections exactly:
  1. Quick answer
  2. Warning signs
  3. How this scam usually works
  4. How to verify safely
  5. What to do if you already interacted
- Keep tone practical, clear, non-alarmist, UK-focused.
- Do not make unsupported legal or financial guarantees.
- Do not use placeholders.
- Output JSON only. No code fences.
'''

    resp = client.messages.create(
        model=model,
        max_tokens=1800,
        temperature=0.7,
        messages=[{"role": "user", "content": prompt}],
    )

    text = "".join(
        block.text for block in resp.content
        if getattr(block, "type", None) == "text"
    ).strip()

    data = json.loads(text)

    data["slug"] = slugify(data.get("slug") or keyword)
    data["category"] = data.get("category") or category
    data["excerpt"] = data.get("excerpt") or f"A practical UK-focused guide to {keyword}, with warning signs, verification steps, and what to do if you have already engaged."
    data["description"] = data.get("description") or data["excerpt"]
    data["date"] = date
    data["keywords"] = data.get("keywords") or [
        keyword,
        category,
        entity,
        f"{keyword} uk",
        f"{keyword} scam",
    ]
    data["keywords"] = [k for k in data["keywords"] if k]
    data["sections"] = [
        {
            "title": "Quick answer",
            "body": data.get("description") or data.get("excerpt") or f"A practical UK-focused guide to {keyword}."
        },
        {
            "title": "Warning signs",
            "body": "- Pressure to act immediately\n- Requests for payment, login details, or one-time codes\n- Mismatched domains, email addresses, or phone numbers\n- Links that do not clearly match the official brand\n- Claims that you must pay first to release funds or prizes"
        },
        {
            "title": "How this scam usually works",
            "body": f"This guide covers the common pattern behind {keyword}, including impersonation, urgency, suspicious links, and attempts to extract money or sensitive information."
        },
        {
            "title": "How to verify safely",
            "body": "1. Go to the official website manually rather than using a message link.\n2. Check whether the sender, website, or number exactly matches the real brand.\n3. Contact the organisation using contact details from its official site.\n4. Do not share passcodes, payment details, or ID documents until verified."
        },
        {
            "title": "What to do if you already interacted",
            "body": "If you entered details or made a payment, change passwords immediately, contact your bank or card provider, keep evidence, and report the incident through the relevant UK channel."
        }
    ]

    data["faq"] = [
        [
            f"How can I verify {entity or keyword} safely?",
            "Use the official website, check the sender or domain carefully, and contact the organisation through independently verified contact details."
        ],
        [
            "What should I do if I shared information already?",
            "Change passwords, secure affected accounts, contact your bank if payment details were involved, and keep evidence of what happened."
        ],
        [
            "Where can I report a scam in the UK?",
            "You can report scams through the relevant UK reporting channels such as Action Fraud, your bank, or the impersonated organisation."
        ]
    ]

    return data
    
def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("topics")
    parser.add_argument("--posts", default="content/posts.json")
    parser.add_argument("--mode", choices=["claude", "template"], default="claude")
    parser.add_argument("--date", default="2026-04-17")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--model", default="claude-3-5-sonnet-latest")
    args = parser.parse_args()

    topics = read_topics(Path(args.topics))
    posts_path = Path(args.posts)
    posts = read_posts(posts_path)
    existing = {p.get("slug") for p in posts}
    generated = []

    for topic in topics:
        keyword = (topic.get("keyword") or "").strip()
        if not keyword:
            continue
        slug = slugify(keyword)
        if slug in existing and not args.force:
            continue
        if args.mode == "claude":
            try:
                post = claude_post(topic, args.date, model=args.model)
            except Exception:
                post = fallback_post(topic, args.date)
        else:
            post = fallback_post(topic, args.date)
        generated.append(post)
        existing.add(post["slug"])

    if args.dry_run:
        print(json.dumps(generated[:3], indent=2, ensure_ascii=False))
        print(f"Generated {len(generated)} post(s) in dry-run mode")
        return

    posts.extend(generated)
    write_posts(posts_path, posts)
    print(f"Added {len(generated)} post(s) to {posts_path}")

if __name__ == "__main__":
    main()
