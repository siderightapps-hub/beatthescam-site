#!/usr/bin/env python3
"""
Recover the DPD / Yodel / UPS courier scam guides that were redirected to
/categories/sms/ in the 2026-05-24 AdSense "low value content" purge.

Search Console (pulled 2026-06-05) showed these were among the highest-demand
URLs on the whole site — /guides/dpd-delivery-scam-text/ alone had 1,905
impressions at position 10.2 — yet they 301'd to a thin category page, so a
dozen DPD near-miss queries were ranking with zero clicks. The original sin was
*thinness* (<300-word stubs), not the topic. These replacements are full
~1,000-word, courier-specific guides, so they reclaim the demand without
re-triggering low-value flags.

This script also refines the meta description (snippet only — NOT the title) of
the bank-text-codes-not-arriving page around the SIM-swap angle.

Companion change (must be done too): remove the three slugs from
ARTICLE_REDIRECTS in scripts/build.py, or build() will emit a forced 301 that
overrides the new guide page.

Run from the repo root:
    python3 scripts/recover_courier_guides.py
"""
import json
import sys
from pathlib import Path

POSTS_FILE = Path("content/posts.json")
TODAY = "2026-06-05"

NEW_POSTS = [
    {
        "slug": "dpd-delivery-scam-text",
        "title": "DPD Scam Text Messages: How to Spot a Fake DPD Delivery Text",
        "description": "Fake DPD 'missed delivery' or 'redelivery fee' texts are smishing scams. Here's how to spot a fake DPD text, verify a genuine one, and report it in the UK.",
        "hero": "Had a text from 'DPD' about a missed parcel or a small redelivery fee? Here's how to tell a genuine DPD message from a scam.",
        "date": TODAY,
        "category": "sms",
        "keywords": [
            "dpd scam text", "fake dpd text", "dpd uk scam text", "dpd sms scam",
            "dpd delivery scam", "dpd redelivery fee scam", "dpd phishing text",
            "dpd missed delivery scam", "dpd text scam uk", "is this dpd text real",
            "dpd fake text message",
        ],
        "sections": [
            ["What is the DPD scam text?",
             "A DPD scam text is a smishing (SMS phishing) message that pretends to be from the courier DPD to trick you into handing over personal or card details. It usually claims your parcel couldn't be delivered, that your address is incomplete, or that a small fee is needed to release or reschedule the delivery — always with a link to tap. The reason this scam works so well in the UK is that DPD genuinely does send delivery texts, often with a one-hour delivery window, so a fake one doesn't look out of place. Scammers send these messages in huge, untargeted batches; they don't know whether you're actually expecting a parcel, but with so many people shopping online, a good share of recipients are. If you tap the link and enter details on the fake page, the criminals capture them in real time."],
            ["How the DPD text scam works, step by step",
             "- A text arrives claiming to be from DPD about a missed delivery, an address problem, or an unpaid fee, with a link and a sense of urgency.\n- The link leads to a convincing copy of the DPD website on a lookalike domain (for example 'dpd-redelivery' or 'dpd-parcel' followed by an unusual ending).\n- You're asked to confirm personal details and pay a small 'redelivery' or 'customs' fee — often just one or two pounds — to make it feel low-risk.\n- The card details and personal information you enter are harvested instantly.\n- Days later, many victims get a follow-up phone call from someone posing as their bank's fraud team, using the stolen details to sound convincing and pressuring them to move money to a 'safe account'. This second stage is where the largest losses happen."],
            ["Warning signs of a fake DPD text",
             "- The message contains a link asking you to pay a fee or 'confirm' details. Genuine DPD delivery texts do not ask for payment by text.\n- It asks for a redelivery fee at all — DPD does not charge consumers a fee to reattempt a standard delivery.\n- The sender is an ordinary mobile number or an international number, not a recognisable short code or 'DPD' sender ID.\n- The web address isn't the official dpd.co.uk — look for misspellings, extra words, or unusual endings.\n- It uses a generic greeting and pressures you to act within hours or the parcel will be 'returned'.\n- You weren't expecting a parcel, or the tracking number doesn't match anything you ordered."],
            ["How to check whether a DPD text is genuine",
             "Never tap the link in the message. Instead, verify the delivery independently. If you're expecting a parcel, find the tracking number in the dispatch email or order confirmation the retailer sent you, then go to the official dpd.co.uk site or the DPD app by typing the address yourself — not by following any link in the text. Genuine DPD tracking shows the same parcel and status without ever asking for a fee or your card details. If there's no matching order, the text is a scam. When in doubt, contact the retailer you bought from; they can confirm who is actually delivering and whether a parcel is in transit. A real courier will never need your full card number, PIN, online banking password, or a one-time security code to deliver a parcel."],
            ["What to do if you tapped the link or paid",
             "- Contact your bank immediately using the number on the back of your card, and tell them you may have entered card details on a scam site. Ask them to block the card and watch for fraudulent transactions.\n- If you entered an online banking password or one-time code, change the password and report it to your bank as compromised.\n- Be on guard for a follow-up call claiming to be your bank — this is part of the scam. Your real bank will never ask you to move money to a 'safe account'. Hang up and call back on the card number.\n- Keep the message and any payment confirmation as evidence, then report it.\n- Monitor your statements and consider checking your credit file for applications you don't recognise."],
            ["How to report a DPD scam text in the UK",
             "Reporting these texts is quick and genuinely helps shut the scams down. Forward the message free of charge to 7726 — the spam-reporting shortcode run by mobile networks, which spells 'SPAM' on a keypad — then delete it. Report the scam to Action Fraud at reportfraud.police.uk or on 0300 123 2040 if you've lost money or shared details; in Scotland, report to Police Scotland on 101. You can also report phishing that impersonates DPD to the National Cyber Security Centre by forwarding suspicious emails to report@phishing.gov.uk, and let DPD know through the security or contact section of their official website so they can act on the fake domains."],
        ],
        "faq": [
            ["Does DPD charge a redelivery fee by text?",
             "No. DPD does not charge consumers a fee to redeliver a standard parcel, and it does not ask for payment through a link in a text message. Any text demanding a small 'redelivery', 'release', or 'customs' fee to free your parcel is a scam designed to capture your card details. If a delivery genuinely needs action, you can check it yourself on the official dpd.co.uk site using the tracking number from your order confirmation."],
            ["What does a genuine DPD text look like?",
             "A real DPD text relates to a parcel you're actually expecting and typically gives a one-hour delivery window and a link to track or change the delivery on dpd.co.uk. It never asks for a fee, your full card number, your PIN, or an online banking code. If you're unsure, don't tap the link — open the DPD app or type dpd.co.uk into your browser and enter your tracking number manually to confirm the status."],
            ["I paid a DPD 'redelivery fee' — what should I do now?",
             "Contact your bank straight away on the number printed on the back of your card, explain you entered card details on a scam site, and ask them to block the card and monitor for fraud. Change any password or code you entered. Be especially wary of a follow-up call claiming to be your bank's fraud team — that is the next stage of the scam. Report it to Action Fraud at reportfraud.police.uk or 0300 123 2040."],
            ["How do I report a fake DPD text message?",
             "Forward the text free to 7726 so your mobile network can investigate the sender, then delete it. If you lost money or shared personal or card details, report it to Action Fraud at reportfraud.police.uk or 0300 123 2040 (Police Scotland on 101 in Scotland). You can also report the fake DPD website to the NCSC and flag it to DPD through their official site."],
        ],
    },
    {
        "slug": "yodel-scam-text-messages",
        "title": "Yodel Scam Text Messages: How to Spot a Fake Yodel Text (UK)",
        "description": "Fake Yodel texts about a missed parcel or small 'redelivery' fee are smishing scams. Here's how to spot a fake Yodel text, check a real one, and report it in the UK.",
        "hero": "A text from 'Yodel' says your parcel is waiting and needs a small fee or new details? Here's how to spot a Yodel scam text.",
        "date": TODAY,
        "category": "sms",
        "keywords": [
            "yodel scam text", "yodel scams", "yodel text scam", "fake yodel text",
            "yodel sms scam", "yodel parcel scam", "yodel redelivery scam",
            "yodel phishing text", "is this yodel text real", "yodel delivery scam uk",
        ],
        "sections": [
            ["What is the Yodel scam text?",
             "A Yodel scam text is a fake message impersonating the UK courier Yodel to steal your personal and payment details. It typically says a parcel couldn't be delivered, is 'waiting' for you, or needs your address confirmed, and includes a link to arrange redelivery. Because Yodel handles a large volume of online-shopping deliveries and does send genuine tracking texts, a fake message blends in easily. The criminals behind these texts send them in bulk to random numbers — they have no idea whether you've ordered anything, but rely on the fact that many people have a parcel on the way at any given time. The goal is to get you onto a fake Yodel page and hand over enough information to defraud you."],
            ["How the Yodel text scam works, step by step",
             "- You receive a text claiming to be from Yodel about a missed or waiting parcel, usually with a link and an urgent tone.\n- Tapping the link opens a counterfeit version of the Yodel site on a lookalike web address rather than the real yodel.co.uk.\n- The page asks you to re-enter your address and pay a small 'redelivery' or 'service' fee to release the parcel.\n- The card details, address, and contact information you submit are captured by the scammers immediately.\n- A common follow-up is a phone call or further texts using those details to impersonate your bank, pressuring you to authorise payments or move money — the stage at which people lose the most."],
            ["Warning signs of a fake Yodel text",
             "- It asks you to pay any fee to receive or redeliver a parcel. Yodel does not charge the recipient a fee to reattempt a standard delivery.\n- There's a link asking for personal or card details — genuine tracking links never need your card number or banking codes.\n- The sender is a random mobile or international number rather than a clearly identifiable Yodel sender.\n- The web address is not the official yodel.co.uk; watch for added words, hyphens, or odd endings.\n- The message uses a generic greeting and a tight deadline to rush you.\n- You haven't ordered anything, or the details don't match a parcel you're expecting."],
            ["How to check whether a Yodel text is genuine",
             "Don't tap any link in the message. If you're expecting a delivery, look up the tracking number in the confirmation email from the shop you ordered from, then visit the official yodel.co.uk site or app by typing the address in yourself and entering the tracking number. The genuine tracking page will show your parcel without ever asking for payment or card details. If nothing matches, treat the text as a scam. You can also contact the retailer directly to confirm which courier is handling your order and whether anything is actually out for delivery. Remember that a real courier never needs your full card number, PIN, online banking password, or a one-time passcode to complete a delivery."],
            ["What to do if you interacted with a Yodel scam text",
             "- Call your bank immediately on the number printed on your card and tell them you may have entered card details on a fake site; ask them to freeze the card and watch for fraud.\n- Change any password or security detail you typed in, and treat one-time codes you shared as compromised.\n- Expect a possible follow-up call pretending to be your bank — hang up and call back on the official number. Your bank will never tell you to move money to a 'safe account'.\n- Save the text and any receipt as evidence before reporting.\n- Keep an eye on your statements and credit file for anything you don't recognise."],
            ["How to report a Yodel scam text in the UK",
             "Forward the message free to 7726, the spam-reporting shortcode that lets your mobile network investigate and block the sender, then delete it. If you've lost money or handed over details, report it to Action Fraud at reportfraud.police.uk or 0300 123 2040 (in Scotland, contact Police Scotland on 101). Suspicious links and phishing pages can be reported to the National Cyber Security Centre, and you can alert Yodel through the contact or security section of their official website so they can take down the fake domains. Reporting takes a minute and helps protect the next person who receives the same text."],
        ],
        "faq": [
            ["Does Yodel charge a fee to redeliver a parcel?",
             "No. Yodel does not charge the recipient a fee to reattempt a standard delivery, and it won't ask for payment through a link in a text. A message demanding a small 'redelivery' or 'release' fee to free your parcel is a scam built to harvest your card details. To check a delivery, use the tracking number from your order confirmation on the official yodel.co.uk site rather than any link in the text."],
            ["How can I tell a real Yodel text from a scam?",
             "A genuine Yodel text relates to a parcel you're actually expecting and links to the real yodel.co.uk for tracking; it never requests a fee, your card number, or a banking code. Scam texts come from random numbers, use lookalike web addresses, and pressure you to pay or 'confirm' details quickly. If in doubt, don't tap the link — type yodel.co.uk in yourself and enter the tracking number to check."],
            ["I entered my details on a Yodel link — what now?",
             "Contact your bank right away using the number on the back of your card, say you entered details on a scam site, and ask them to block the card and monitor for fraud. Change any passwords or codes you shared. Be wary of a follow-up call claiming to be your bank's fraud team — that's part of the scam. Report what happened to Action Fraud at reportfraud.police.uk or 0300 123 2040."],
            ["Where do I report a fake Yodel text?",
             "Forward it free to 7726 so your network can act on the sender, then delete the message. If money or details were lost, report to Action Fraud at reportfraud.police.uk or 0300 123 2040 (Police Scotland on 101 in Scotland). You can also report the phishing site to the NCSC and notify Yodel via their official website."],
        ],
    },
    {
        "slug": "ups-delivery-scam-text-messages-uk",
        "title": "UPS Scam Text Messages: Spot a Fake UPS Delivery Text (UK)",
        "description": "Fake UPS texts about a missed delivery or 'customs fee' are smishing scams. Here's how to spot a fake UPS text, verify a genuine one, and report it in the UK.",
        "hero": "A 'UPS' text says your parcel is held and a customs or delivery fee is due? Here's how to spot a UPS scam text.",
        "date": TODAY,
        "category": "sms",
        "keywords": [
            "ups scam text", "ups delivery scam text", "fake ups text", "ups sms scam",
            "ups customs fee scam", "ups import fee scam", "ups phishing text",
            "ups parcel scam uk", "is this ups text real", "ups text scam uk",
        ],
        "sections": [
            ["What is the UPS scam text?",
             "A UPS scam text is a phishing message that impersonates the courier UPS to steal money and personal details. It usually claims a parcel is being held and that you must pay a fee — frequently framed as a 'customs charge', 'import duty', or 'brokerage fee' — or that a delivery was missed and needs rescheduling through a link. UPS handles a large share of international shipments into the UK, and genuine customs charges can apply to parcels from outside the UK, which is exactly why the 'pay this customs fee' version of the scam is so convincing. Scammers send these texts in bulk; they're betting that enough recipients are expecting something from abroad to make the customs story believable. Tap the link and you land on a fake UPS page built to capture whatever you type."],
            ["How the UPS text scam works, step by step",
             "- A text claiming to be from UPS says your parcel is held pending a customs, import, or redelivery fee, with a link to pay.\n- The link opens a counterfeit UPS page on a lookalike domain rather than the official ups.com.\n- You're asked for personal details and to pay a modest fee by card, made to seem small and reasonable.\n- Your card and contact details are captured instantly and can be used or sold on.\n- Some victims then receive a follow-up call from a fake 'bank fraud team' that uses the stolen information to sound legitimate and pressure them into authorising larger payments."],
            ["Warning signs of a fake UPS text",
             "- It asks you to pay a customs, import, duty, or redelivery fee via a link in the text. Genuine duties are handled through official channels, not a random SMS link.\n- The sender is an ordinary mobile or international number rather than an identifiable UPS sender.\n- The web address isn't the official ups.com — look for extra words, hyphens, or unusual endings.\n- It uses urgency ('parcel will be returned today') and a generic greeting.\n- You aren't expecting an international parcel, or the amount and reference don't match anything you ordered.\n- It asks for card details, a one-time passcode, or banking information to 'release' the parcel."],
            ["How a genuine UPS charge or delivery actually works",
             "Real customs charges on parcels from outside the UK do exist, but legitimate UPS contacts you about them in a verifiable way and lets you check the charge against your specific tracking number on the official ups.com site. To verify any UPS message, don't use its link — find your tracking number in the retailer's dispatch email, then type ups.com into your browser or open the UPS app and enter the number yourself. If you have a UPS My Choice account, check there. A genuine process will match a parcel you're actually expecting and won't ask for your full card number, PIN, online banking password, or a security code by text. If anything doesn't line up, treat the message as a scam and check with the retailer you bought from."],
            ["What to do if you paid a UPS 'customs' or 'delivery' fee",
             "- Phone your bank straight away on the number on the back of your card, tell them you entered details on a scam site, and ask them to block the card and monitor for fraud.\n- Change any password or code you entered and treat it as compromised.\n- Watch for a follow-up call posing as your bank — it's part of the scam. Hang up and call back on the official number; your bank will never ask you to move money to a 'safe account'.\n- Keep the message and payment details as evidence for your report.\n- Check your statements and credit file for anything unexpected over the following weeks."],
            ["How to report a UPS scam text in the UK",
             "Forward the text free to 7726 so your mobile network can investigate and block the sender, then delete it. If you've lost money or shared details, report it to Action Fraud at reportfraud.police.uk or 0300 123 2040 (in Scotland, Police Scotland on 101). Phishing links can be reported to the National Cyber Security Centre, and you can alert UPS through the fraud or security section of ups.com so they can act on the fake sites. A quick report helps networks and investigators disrupt the campaign behind the message."],
        ],
        "faq": [
            ["Does UPS ask for a customs fee by text?",
             "Legitimate customs charges on parcels from outside the UK do exist, but UPS does not collect them through a random link in a text message. A text pressuring you to pay a 'customs', 'import', or 'brokerage' fee via a link is almost always a scam. Verify any charge yourself by entering your tracking number on the official ups.com site rather than tapping the link, and check with the retailer if you're unsure."],
            ["How do I know if a UPS text is real?",
             "A genuine UPS text matches a parcel you're actually expecting and lets you verify everything on the official ups.com site or in the UPS app using your tracking number; it never asks for your full card number, PIN, or a banking passcode by text. Scam texts come from random numbers, use lookalike web addresses, and rush you to pay. When unsure, don't tap the link — go to ups.com yourself."],
            ["I paid a UPS scam text fee — what should I do?",
             "Contact your bank immediately on the number printed on your card, explain you entered details on a fake site, and ask them to freeze the card and watch for fraud. Change any passwords or codes you shared. Be cautious of a follow-up call claiming to be your bank's fraud team — that's the next stage of the scam. Report it to Action Fraud at reportfraud.police.uk or 0300 123 2040."],
            ["Where can I report a fake UPS text in the UK?",
             "Forward the message free to 7726 so your network can investigate the sender, then delete it. If money or personal details were lost, report to Action Fraud at reportfraud.police.uk or 0300 123 2040 (Police Scotland on 101 in Scotland). You can also report the phishing page to the NCSC and notify UPS through ups.com."],
        ],
    },
]

# Snippet-only refinement (NOT the title) for the site's biggest-ranking page.
BANK_SNIPPET = {
    "slug": "bank-text-codes-not-arriving",
    "description": "Bank texts not arriving? Most causes are routine — the quick fixes, the UK sender IDs that prove a text is genuine, and the SIM-swap scam signs to watch for.",
}


def main() -> int:
    if not POSTS_FILE.exists():
        print(f"❌ {POSTS_FILE} not found. Run from the repo root.")
        return 1

    data = json.loads(POSTS_FILE.read_text(encoding="utf-8"))
    if not isinstance(data, list) or not data:
        print(f"❌ {POSTS_FILE} should be a non-empty list.")
        return 1

    print(f"📚  Current posts: {len(data)}")
    template_keys = set(data[0].keys())

    existing = {p.get("slug") for p in data}
    for post in NEW_POSTS:
        if post["slug"] in existing:
            print(f"❌ Slug already exists, aborting: {post['slug']!r}")
            return 1
        extra = set(post.keys()) - template_keys
        missing = template_keys - set(post.keys())
        if missing or extra:
            print(f"❌ Key mismatch for {post['slug']!r}: missing={sorted(missing)} extra={sorted(extra)}")
            return 1

    # Insert as a block at the top so DPD lands first (newest-first convention).
    data[0:0] = NEW_POSTS

    # Refine the bank page snippet (description only).
    bank = next((p for p in data if p.get("slug") == BANK_SNIPPET["slug"]), None)
    if bank is None:
        print(f"⚠️  {BANK_SNIPPET['slug']!r} not found — skipping snippet refinement.")
    else:
        old = bank.get("description", "")
        bank["description"] = BANK_SNIPPET["description"]
        print(f"✏️   Updated {BANK_SNIPPET['slug']} description ({len(old)} → {len(BANK_SNIPPET['description'])} chars)")

    POSTS_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"✅  Inserted {len(NEW_POSTS)} courier guides: {', '.join(p['slug'] for p in NEW_POSTS)}")
    print(f"📚  Total posts: {len(data)}")
    print()
    print("Next: remove those 3 slugs from ARTICLE_REDIRECTS in scripts/build.py, then run build.py.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
