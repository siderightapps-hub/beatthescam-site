#!/usr/bin/env python3
"""
Add the comprehensive 'Bank text codes & 2FA verification not arriving' hub
guide to content/posts.json.

This replaces the earlier Halifax-specific draft — instead of one thin page
per bank, this is a single comprehensive page that ranks for:

  - "bank text not arriving"            (broad query)
  - "halifax text messages not arriving" (your current near-miss, 169 imp)
  - "lloyds text not arriving"
  - "natwest verification code not received"
  - "barclays sms not coming through"
  - "hsbc 2fa not working"
  - "santander code not arriving"
  - "nationwide text not received"
  - "verification code not arriving uk"
  - "hmrc verification code not received"
  - "google verification code not received"
  - and dozens of other related variants

Run from the repo root:
    python3 add_bank_codes_post.py
"""
import json
import sys
from pathlib import Path

POSTS_FILE = Path("content/posts.json")

NEW_POST = {
    "slug": "bank-text-codes-not-arriving",
    "title": "Bank Text Codes Not Arriving? UK Guide for Halifax, Lloyds, NatWest, Barclays, HSBC, Santander & More (2026)",
    "description": "Bank verification codes or 2FA texts not arriving? Common causes, quick fixes, sender IDs to spot real messages from every major UK bank, and what to do when missing codes could indicate something serious. Plain-English UK guide.",
    "hero": "Why your UK bank verification codes or 2FA texts aren't arriving — and what to do about it.",
    "date": "2026-05-07",
    "category": "sms",
    "keywords": [
        "bank text not arriving",
        "verification code not received",
        "2fa code not arriving",
        "security code not coming through",
        "halifax",
        "lloyds",
        "natwest",
        "barclays",
        "hsbc",
        "santander",
        "nationwide",
        "tsb",
        "first direct",
        "monzo",
        "starling",
        "uk bank scam",
        "sim swap",
        "smishing",
        "two factor authentication",
        "bank sender id",
        "hmrc verification",
        "google verification code",
        "microsoft authenticator",
    ],
    "sections": [
        [
            "Why your bank verification text might not be arriving",
            "If your bank verification code or 2FA text has stopped arriving, you're far from alone — it's one of the most common UK customer service queries every week, and the cause is almost always routine. Mobile signal, a phone setting, the bank's SMS gateway hitting a delay, or your network operator filtering messages account for the vast majority of cases. Genuine fraud — where a criminal has taken over your number to intercept codes — exists, but it's rare and produces a distinctive cluster of symptoms (we'll cover what to watch for later). This guide starts with universal quick fixes, lists how to identify a genuine message from every major UK bank, walks through getting your code another way, and only escalates to fraud concerns when the symptoms genuinely warrant it. Most people reading this will resolve the problem in the next five minutes."
        ],
        [
            "Quick fixes that work for any UK bank or service",
            "Try this checklist first, in order. Reboot your phone — it clears stuck network connections and resolves more cases than anything else. Confirm Aeroplane Mode is off, Do Not Disturb is off, and no Focus profile is filtering banking or login notifications. Open your Messages app and check the blocked-numbers list — banking shortcodes can get blocked accidentally if you've ever tagged a scam text as spam. Check that your phone storage isn't critically full; some devices stop accepting new messages when storage runs out. Move location to confirm signal isn't the issue. Open the Messages app's filter or junk folder, since bank texts sometimes get misclassified as promotional. Then request a fresh code to test. This sequence resolves the issue more than nine times out of ten and works identically for every bank and every 2FA service."
        ],
        [
            "UK bank reference: sender IDs and how to verify a real bank message",
            "Every major UK bank uses a consistent sender ID for security texts and includes specific signals you can use to verify a message is genuine. If a text claiming to be from your bank doesn't match these patterns, treat it as a scam. Major UK retail banks and their sender ID conventions:\n- Halifax — sender ID 'Halifax' (not 'HalifaxUK' or 'Halifax-UK'); messages include part of your name, account number, or postcode; app-based authentication available.\n- Lloyds Bank — sender ID 'Lloyds'; messages include partial account or postcode details; app codes via Lloyds Mobile Banking.\n- Bank of Scotland — sender ID 'BankScot' or 'BOS'; app codes via Bank of Scotland Mobile Banking.\n- NatWest — sender ID 'NatWest' or 'NatWestAlert'; app codes via the NatWest mobile banking app.\n- Royal Bank of Scotland — sender ID 'RBS' or 'RBSAlert'; app codes via the RBS mobile banking app.\n- Barclays — sender ID 'Barclays'; app codes via Barclays Mobile Banking or PINsentry.\n- HSBC UK — sender ID 'HSBC'; codes via HSBC Mobile Banking and the HSBC Authenticator app.\n- First Direct — sender ID 'firstdirect'; app codes via the First Direct app.\n- Santander UK — sender ID 'Santander'; OneTouch authentication via the Santander app.\n- Nationwide — sender ID 'Nationwide' (or 'NationwideBS'); app codes via the Nationwide app.\n- TSB — sender ID 'TSB'; codes via the TSB Mobile Banking app.\n- Monzo, Starling, Revolut, Chase UK — primarily app-based; SMS used only as fallback.\nFor every UK bank: real texts never contain a clickable link asking you to log in or 'verify' your account. To check a message, open your bank's app yourself or type the bank's address into your browser. Find your bank's customer service number on the back of your debit card."
        ],
        [
            "Skip SMS: use app-based codes for banks and 2FA services",
            "If SMS keeps failing, the fastest fix is often to bypass it entirely. Every major UK bank app generates secure login and payment codes inside the app — no SMS required. Set up app-based authentication once and you'll rarely need texts again. The same is true for non-banking services: Google's two-step verification works via the Google app or Authenticator without SMS; Apple ID 2FA delivers codes to your other Apple devices; Microsoft Authenticator handles Microsoft, Outlook, and Office 365 accounts independently of SMS; and most workplace systems support either Google or Microsoft Authenticator. For UK government services like Government Gateway, HMRC, and NHS login, you can also choose to receive codes by automated voice call instead of text. Switching to app-based or voice methods sidesteps SMS-delivery issues completely and is generally more secure than relying on SMS."
        ],
        [
            "When the bank or service network is at fault",
            "Sometimes the problem isn't your phone or settings — it's the sending side. Bank SMS gateways occasionally have operational delays where text delivery to certain UK networks slows or stops temporarily. Mobile operators sometimes flag legitimate sender IDs as spam after a flood of malicious texts, blocking real bank messages alongside scams. UK government services like HMRC and NHS Digital have had similar SMS delivery issues during peak load (self-assessment deadline windows, vaccine appointment booking surges). If your phone is otherwise working normally — texts from friends arrive, calls work, mobile data works — but only specific service messages aren't appearing, the issue is on their end. The fix isn't on your phone. Call the service on a verified number (from the back of your card or their official website) to ask whether there's a known SMS issue, and arrange an alternative method of verification while it's resolved."
        ],
        [
            "When missing codes could indicate something more serious",
            "Missing bank or 2FA texts on their own usually mean signal, settings, or a network-side issue. But if you also notice your phone showing 'no service' or 'SOS only' without explanation, calls suddenly failing, mobile data not working, or texts from other people also failing to arrive — that cluster of symptoms together can occasionally indicate a SIM-swap or port-out attack. This is rare, but it does happen. In a SIM-swap, a fraudster persuades your mobile network to transfer your number to a SIM card they control, so every text — including bank codes — goes to them instead of you. The warning sign is the combination of 'phone not working at all' plus 'missing codes', not missing codes alone. If only your bank texts are missing while everything else on your phone works fine, this almost certainly isn't what's happening."
        ],
        [
            "What to do if you see those warning signs",
            "If your phone has stopped working entirely and bank codes have stopped arriving, treat it as serious. Use a different phone — a friend's, a family member's, or a landline — to call your bank on a verified number (back of your card, or their official website) and request that online and mobile banking access be frozen while you investigate. Then call your mobile network provider on a published number and ask whether any SIM swap or port-out request has been processed on your account in the last 30 days. If yes and you didn't authorise it, ask for an immediate reversal and request a port-out PIN to prevent it happening again. Report the case to Action Fraud at actionfraud.police.uk or 0300 123 2040. Don't wait or assume it's just a network outage — these attacks usually drain accounts within an hour."
        ]
    ],
    "faq": [
        [
            "Why aren't my UK bank verification codes arriving?",
            "The most common reasons are weak mobile signal, a blocked sender, Do Not Disturb mode, full phone storage, or a temporary delivery delay on the bank's or your mobile network's side. Try the technical fixes in this guide first. If they don't help, call your bank on the number on the back of your debit card — they can verify whether there's a known issue and arrange a code via the app or by phone instead."
        ],
        [
            "How do I know if a 'bank' text is real or a scam?",
            "Genuine UK bank texts come from a named sender ID (e.g. 'Halifax', 'Lloyds', 'Barclays', 'HSBC') rather than a phone number, include part of your name or account details, and never contain a clickable link asking you to log in or 'verify' your account. The bank reference section above lists the standard sender IDs for each major UK bank. If a text fails any of these checks, treat it as a scam and forward it free to 7726."
        ],
        [
            "Can I get my verification codes without SMS at all?",
            "Yes, every major UK bank's mobile app generates secure codes directly inside the app — no SMS needed. The same goes for Google, Microsoft, and Apple 2FA. For UK government services like HMRC, Government Gateway, and NHS login, you can choose voice call delivery instead of SMS. Switching to app-based or voice authentication is generally faster and more secure than relying on SMS, and it sidesteps delivery issues entirely."
        ],
        [
            "My HMRC, Microsoft, or Google code isn't arriving — does the same advice apply?",
            "Yes, the universal fixes work for any service that sends verification codes by SMS. Reboot first, check signal and Do Not Disturb, and look for the message in any junk or filtered folder. Most major services also offer app-based or voice alternatives that bypass SMS entirely — for UK government services, sign in at gov.uk and switch your verification method in your Government Gateway settings. For Google, Apple, and Microsoft accounts, set up an authenticator app for codes that work even with no signal."
        ]
    ]
}


def main() -> int:
    if not POSTS_FILE.exists():
        print(f"❌ {POSTS_FILE} not found. Run this script from your repo root.")
        return 1

    try:
        data = json.loads(POSTS_FILE.read_text())
    except json.JSONDecodeError as e:
        print(f"❌ Could not parse {POSTS_FILE}: {e}")
        return 1

    if not isinstance(data, list) or not data:
        print(f"❌ {POSTS_FILE} should be a non-empty list.")
        return 1

    print(f"📚  Current posts: {len(data)}")
    print(f"🔑  First entry keys: {sorted(data[0].keys())}")

    template_keys = set(data[0].keys())
    new_keys = set(NEW_POST.keys())
    missing = template_keys - new_keys
    extra = new_keys - template_keys

    if missing:
        print()
        print(f"⚠️   Existing posts have these fields the new one doesn't:")
        for k in sorted(missing):
            sample_repr = repr(data[0][k])[:80]
            print(f"     - {k!r}  (example: {sample_repr})")
        print()
        print("To proceed anyway, re-run with --force.")
        if "--force" not in sys.argv:
            return 1

    if extra:
        print(f"ℹ️   New post has fields not on data[0]: {sorted(extra)} (usually fine)")

    if any(p.get("slug") == NEW_POST["slug"] for p in data):
        print(f"❌ A post with slug {NEW_POST['slug']!r} already exists. Aborting.")
        return 1

    data.insert(0, NEW_POST)
    POSTS_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")

    print()
    print(f"✅  Added {NEW_POST['slug']!r}.")
    print(f"📚  Total posts: {len(data)}")
    print()
    print("Next:")
    print("  1. python3 scripts/build.py")
    print("  2. open dist/guides/bank-text-codes-not-arriving/index.html  # visual check")
    print("  3. git add content/posts.json dist/")
    print("  4. git commit -m 'Add UK bank/2FA verification codes hub guide'")
    print("  5. git push origin main")
    print("  6. Search Console → Inspect URL → Request Indexing")
    return 0


if __name__ == "__main__":
    sys.exit(main())
