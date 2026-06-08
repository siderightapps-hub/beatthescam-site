#!/usr/bin/env python3
"""
Second purge-recovery batch (2026-06-07). GSC showed a second tranche of
high-demand URLs the 2026-05-24 AdSense purge had 301'd to thin category pages,
bleeding ~350 impressions at terrible positions. This resurrects the four with
no live equivalent as full ~1,000-word guides:
  - amazon-phone-call-scam-uk     ("amazon scam calls uk", 100 impr)
  - chargeback-scam-uk            ("chargeback scam", 43 impr)
  - gumtree-scam-uk-guide         ("gumtree scams", 29 impr)
  - google-voice-verification-scam("google voice verification code scam", 24 impr)

(The two with live twins — royal-mail-text-scam-guide, amazon-scam-email-uk —
are handled as redirects in build.py's ARTICLE_REDIRECTS instead.)

Companion change already made: those four slugs removed from ARTICLE_REDIRECTS.

Run from the repo root:  python3 scripts/recover_purged_pages_2.py
"""
import json
import sys
from pathlib import Path

POSTS_FILE = Path("content/posts.json")
TODAY = "2026-06-07"

NEW_POSTS = [
    {
        "slug": "amazon-phone-call-scam-uk",
        "title": "Amazon Scam Phone Calls UK: How to Spot a Fake Amazon Call",
        "description": "Got an automated 'Amazon' call about a suspicious order or account? It's almost certainly a scam. Here's how the fake Amazon call works and how to stop it.",
        "hero": "An automated call says there's a problem with your Amazon order or account — here's why it's a scam and what to do.",
        "date": TODAY,
        "category": "phone",
        "keywords": [
            "amazon scam calls uk", "amazon scam phone call uk", "fake amazon call",
            "amazon phone scam", "report amazon scam calls uk", "amazon account scam call",
            "amazon refund scam call", "amazon press 1 scam", "is amazon calling me a scam",
            "amazon iphone order scam call",
        ],
        "sections": [
            ["What is the Amazon scam phone call?",
             "An Amazon scam call is a fraudster impersonating Amazon by phone — usually an automated recording — to frighten you into handing over money, card details, or control of your devices. Common scripts claim there's 'suspicious activity' on your account, that an expensive order (often an iPhone) has been placed and you must 'press 1' to cancel, or that your Prime membership is auto-renewing. Amazon is one of the most impersonated brands in the UK precisely because almost everyone has an account, so a cold call about it feels plausible. The call may show a UK number through caller-ID spoofing. Amazon does not cold-call customers about orders or account security, so an unexpected call claiming to be Amazon is the warning sign in itself."],
            ["How the Amazon call scam works, step by step",
             "- An automated call claims there's a problem — a suspicious order, an account on hold, or a Prime charge — and tells you to press a key or stay on the line to reach an 'agent'.\n- The 'agent' builds urgency: your account is compromised, money is at risk, you must act now.\n- They ask you to install remote-access software (such as AnyDesk or TeamViewer) so they can 'secure your account' or 'process a refund' — this hands them control of your device.\n- They 'refund' you but claim to have sent too much, then pressure you to repay the difference by bank transfer or gift cards (the overpayment trick).\n- Alternatively they ask directly for your card number, bank login, or a one-time security code.\n- Once they have access, money, or details, they drain accounts or make purchases."],
            ["Warning signs of a fake Amazon call",
             "- It's an automated/recorded call, or asks you to 'press 1' — Amazon doesn't operate that way.\n- It's about something you didn't expect: an order you never placed, or 'suspicious activity'.\n- You're asked to install software, allow remote access, or download an app to 'fix' or 'refund' anything.\n- You're asked to pay, repay an over-refund, or buy gift cards to resolve a problem.\n- You're asked for your full card number, bank login, PIN, or a one-time passcode.\n- High pressure and secrecy — 'don't hang up', 'don't tell your bank', 'act immediately'."],
            ["What a genuine Amazon contact looks like — and how to verify",
             "Amazon will not phone you out of the blue asking for remote access, payment, gift cards, or your full card or security details. Genuine account and order information always lives inside your account. If a call worries you, hang up and check independently: open the Amazon app or type amazon.co.uk into your browser yourself, sign in, and look at Your Orders and Your Account — if there's no rogue order and no security alert there, the call was fake. Never call back a number the caller gave you; use the Help pages on Amazon's official site to contact them. A real company will never need you to install software or move money to 'protect' your account."],
            ["What to do if you've been called — or already acted",
             "- If you only listened, just hang up and block the number. No harm done.\n- If you installed any software or app they asked for, disconnect from the internet, uninstall it, and run a security scan; if it's a phone, consider a factory reset after backing up.\n- If you shared card or bank details, or paid anything, contact your bank immediately on the number on your card — block the card and report fraud.\n- Change the passwords for your Amazon account, email, and online banking, and turn on two-step verification.\n- Watch for follow-up calls pretending to be your bank's fraud team — that's often the next stage. Hang up and call your bank back on the official number."],
            ["How to report an Amazon scam call in the UK",
             "Report scam calls to Action Fraud at reportfraud.police.uk or on 0300 123 2040 (in Scotland, contact Police Scotland on 101), especially if you lost money or shared details. Report the impersonation to Amazon through the 'Report Something Suspicious' section of their official help pages so they can warn other customers. You can report nuisance and scam calls to your phone provider, and forward scam text messages to 7726. Reporting helps investigators track the campaigns behind these calls and protects the next person who picks up."],
        ],
        "faq": [
            ["Does Amazon call you about suspicious orders or account activity?",
             "No. Amazon does not cold-call customers about orders, account security, or refunds, and never asks you to press a key, install software, allow remote access, pay a fee, or read out a security code over the phone. Any unexpected call claiming to be Amazon — especially an automated one — should be treated as a scam. Hang up and check your account yourself via the app or amazon.co.uk."],
            ["What is the 'press 1' Amazon call or the iPhone-order call?",
             "It's a common automated scam: a recording claims a costly order (often an iPhone) has been placed on your account, or that there's suspicious activity, and tells you to press 1 or stay on the line to reach an 'agent'. The 'agent' then tries to get remote access to your device or your card and bank details. Amazon doesn't make these calls — there is no real order. Hang up and check Your Orders in the app or on the website."],
            ["I let them install software or gave my details — what do I do now?",
             "Act quickly. Uninstall any software they had you install, disconnect the device from the internet and run a security scan. Call your bank on the number on your card to block it and report fraud. Change your Amazon, email, and banking passwords and enable two-step verification. Be wary of a follow-up call claiming to be your bank — that's part of the scam. Report it to Action Fraud at reportfraud.police.uk or 0300 123 2040."],
            ["How do I report a fake Amazon call in the UK?",
             "Report it to Action Fraud at reportfraud.police.uk or on 0300 123 2040 (Police Scotland on 101 in Scotland), and flag the impersonation to Amazon via the 'Report Something Suspicious' pages on their official site. You can also report nuisance calls to your phone provider. If you received scam texts alongside the calls, forward them free to 7726."],
        ],
    },
    {
        "slug": "chargeback-scam-uk",
        "title": "Chargeback Scam UK: How Chargeback Fraud Works and How to Avoid It",
        "description": "Chargeback scams let a buyer keep the goods and get their money back, leaving the seller out of pocket. Here's how chargeback fraud works and how to protect yourself.",
        "hero": "A buyer pays, receives the item, then disputes the charge to get their money back too — here's how chargeback fraud works and how to avoid it.",
        "date": TODAY,
        "category": "payment",
        "keywords": [
            "chargeback scam", "chargeback scammer", "chargeback fraud uk",
            "friendly fraud", "chargeback scams", "fraudulent chargebacks",
            "paypal chargeback scam", "chargeback scam selling", "chargeback abuse",
            "how to avoid chargeback fraud",
        ],
        "sections": [
            ["What is a chargeback scam?",
             "A chargeback is a legitimate consumer protection: if your card is used fraudulently, or a seller fails to deliver, your bank can reverse the payment. A chargeback scam abuses that system. The scammer pays for goods or a service with a card or PayPal, receives what they bought, and then files a dispute with their bank claiming the transaction was unauthorised or never delivered — so they get their money back and keep the item. The seller loses both the goods and the payment, and often a dispute fee on top. It's sometimes called 'friendly fraud' because the 'fraud' comes from a real customer rather than a stolen card. Private sellers on marketplaces, freelancers, and small businesses are the usual targets."],
            ["How chargeback fraud works, step by step",
             "- The scammer buys from you and pays by card, PayPal, or a similar reversible method.\n- You send the goods or deliver the service in good faith.\n- Days or weeks later, the scammer contacts their card issuer or PayPal and disputes the payment — claiming it was unauthorised, the item never arrived, or it 'wasn't as described'.\n- The bank provisionally refunds them while it investigates, pulling the money back from you.\n- Without solid proof of delivery and a legitimate transaction, you struggle to win the dispute — so you lose the money and the item.\n- A variant: the scammer 'overpays', asks you to refund the difference by bank transfer, then charges back the original card payment, leaving you doubly out of pocket."],
            ["Who scammers target and common set-ups",
             "Chargeback fraud most often hits people selling to strangers: private sellers on Gumtree, Facebook Marketplace, eBay and Vinted; freelancers and digital sellers; and small online shops. Watch for buyers who push to move off a platform's protected checkout, who insist on paying by 'friends and family' on PayPal (which has no buyer or seller protection), who arrange their own courier for collection, or who send a screenshot or email 'confirming' a payment that never lands in your account. High-value, easily-resold items — phones, consoles, designer goods, event tickets — attract the most chargeback abuse."],
            ["Warning signs of a chargeback scammer",
             "- The buyer wants to pay by a reversible method but rushes the handover before funds clearly clear.\n- They insist on their own courier, or on collection, then later claim the item never arrived.\n- They ask you to refund an 'overpayment' by bank transfer.\n- They push communication and payment off the platform's protected system.\n- They send a payment-confirmation email or screenshot rather than you seeing the money in your own account.\n- The story changes, or pressure ramps up to complete quickly and quietly."],
            ["How to protect yourself",
             "- Sell through a platform's protected checkout where you can and keep all communication on-platform.\n- Never accept PayPal 'friends and family' for a sale — it strips seller protection.\n- Wait for funds to actually appear in your own account; ignore emailed 'confirmations' and screenshots.\n- Use tracked, signed-for delivery and keep the proof; for collection, get a signed receipt and photos.\n- Keep records: listing, messages, payment, postage, serial numbers — evidence wins disputes.\n- Be wary of 'overpayment' and never refund the difference by a separate method.\n- For higher-value items, consider only accepting cleared bank transfer or cash on collection with ID."],
            ["Legitimate chargebacks vs abuse — and how to report",
             "Not every chargeback is a scam: if you genuinely didn't receive goods, or your card was used without permission, a chargeback is your right under card scheme rules, and the Section 75 protection on UK credit-card purchases over £100 is a separate, legitimate safeguard. Chargeback fraud is the deliberate misuse of that process to steal. If you're hit, respond to the dispute promptly with your evidence through your payment provider, and report the fraud to Action Fraud at reportfraud.police.uk or 0300 123 2040 (Police Scotland on 101 in Scotland). Report the buyer to the marketplace too, so they can act on the account."],
        ],
        "faq": [
            ["What is a chargeback scam or 'friendly fraud'?",
             "It's when a real buyer pays for something, receives it, then disputes the payment with their bank or PayPal to claw the money back while keeping the goods. Because the dispute comes from a genuine customer rather than a stolen card, it's nicknamed 'friendly fraud'. The seller loses the item and the money. Private sellers, freelancers and small businesses are the main targets."],
            ["Can someone really chargeback and keep the item?",
             "Yes — if the seller can't prove a legitimate, delivered transaction, the bank often sides with the cardholder and reverses the payment, leaving the seller out of pocket. That's why proof matters: tracked and signed-for delivery, on-platform payment, and full records of the listing and messages are what let you win a dispute and deter the scam in the first place."],
            ["How do I protect myself from chargeback fraud as a seller?",
             "Sell through protected checkouts, keep communication and payment on the platform, and never accept PayPal 'friends and family' for a sale. Wait for funds to land in your own account rather than trusting emailed confirmations. Use tracked, signed-for postage and keep all evidence. Refuse 'overpayment' refunds. For pricey items, prefer cleared bank transfer or cash on collection with ID."],
            ["Is a chargeback the same as a scam?",
             "No. A chargeback is a legitimate protection for when you're charged fraudulently or don't receive what you paid for, and UK credit-card Section 75 cover is a separate genuine safeguard. The scam is the deliberate abuse of the chargeback process to get a refund while keeping the goods. If you're targeted, fight the dispute with evidence and report it to Action Fraud at reportfraud.police.uk or 0300 123 2040."],
        ],
    },
    {
        "slug": "gumtree-scam-uk-guide",
        "title": "Gumtree Scams UK: How to Spot and Avoid Fake Listings and Buyers",
        "description": "Gumtree is legitimate, but scammers use it. Here are the most common Gumtree scams targeting UK buyers and sellers, the warning signs, and how to stay safe.",
        "hero": "Gumtree itself is legit — but scammers work it hard. Here's how to spot the fake listings, dodgy buyers, and payment tricks.",
        "date": TODAY,
        "category": "marketplace",
        "keywords": [
            "gumtree scams", "scams on gumtree", "gumtree scam", "gumtree scammers",
            "gumtree buyer scam", "gumtree seller scam", "gumtree fake listing",
            "is gumtree safe", "gumtree overpayment scam", "gumtree courier scam",
        ],
        "sections": [
            ["What are Gumtree scams?",
             "Gumtree is a genuine UK classifieds platform, but because listings are free, local, and often paid for in cash or bank transfer, scammers use it heavily. Gumtree scams fall into two camps: tricks aimed at buyers (fake listings for items, cars, pets or rentals that don't exist) and tricks aimed at sellers (overpayment and fake-courier scams that take your item or your money). The platform itself isn't the problem — the danger is in how payment and delivery happen, especially when either side pushes you off Gumtree's messaging, asks for bank transfer up front, or 'confirms' a payment you can't actually see in your account. Knowing the handful of common patterns is enough to avoid almost all of them."],
            ["Common Gumtree scams when you're buying",
             "- Advance-fee listings: an item, car, pet or flat is priced temptingly low, but you must pay a deposit or the full amount by bank transfer before viewing — and it never arrives.\n- 'I'm away, I'll post it': the seller can't meet, asks for payment first, and disappears.\n- Vehicle scams: a car well below market value, with a story about being abroad or needing a 'shipping company' or 'escrow' to handle payment.\n- Rental scams: a cheap flat you can't view in person, with a deposit demanded to 'hold' it.\n- Phishing links sent in chat to 'complete payment' on a fake page."],
            ["Common Gumtree scams when you're selling",
             "- Overpayment: a buyer 'accidentally' pays too much (often with a fake transfer or cheque) and asks you to refund the difference before the original payment bounces.\n- Fake courier collection: the buyer insists on arranging their own courier and sends a convincing email or screenshot 'confirming' payment that never reaches your account; the courier collects the item and the money never lands.\n- PayPal 'friends and family' or off-platform payment that strips your protection.\n- Buyers who pressure you to post before the money has actually cleared in your bank."],
            ["Warning signs on Gumtree",
             "- Any request to pay — or be paid — by bank transfer before meeting, or before funds clearly clear in your own account.\n- Pressure to move off Gumtree's messaging to WhatsApp, email or text early on.\n- A price that's too good to be true, or a seller who can't meet or let you view.\n- A buyer who insists on their own courier and emails a payment 'confirmation' instead of you seeing the money.\n- Requests for a deposit to 'hold' an item, pet, car or flat you haven't seen.\n- Spelling, story inconsistencies, or refusal to answer simple questions in person."],
            ["How to buy and sell safely on Gumtree",
             "- Deal locally and in person where you can: see the item, the car, or the property before any money changes hands.\n- For higher-value items meet in a safe public place, and for vehicles never pay before viewing and checking the V5C and history.\n- As a seller, take cash on collection or wait for a bank transfer to actually appear in your account — never trust an emailed or screenshot 'confirmation', and never refund an 'overpayment'.\n- Decline buyer-arranged couriers for valuable items unless payment has genuinely cleared first.\n- Keep all messages on Gumtree, and never pay a deposit for something you can't view.\n- Trust your instincts — if you're being rushed or pushed off-platform, walk away."],
            ["How to report a Gumtree scam in the UK",
             "Report the listing or user to Gumtree through the 'Report' link on the advert or profile so they can remove it. If you've lost money or shared details, report it to Action Fraud at reportfraud.police.uk or 0300 123 2040 (in Scotland, Police Scotland on 101). If you paid by bank transfer, contact your bank straight away — under the APP fraud reimbursement rules most UK banks may be able to help. Forward any scam texts to 7726, and keep screenshots of the listing and conversation as evidence."],
        ],
        "faq": [
            ["Is Gumtree safe, or is Gumtree a scam?",
             "Gumtree is a legitimate UK classifieds site — it isn't a scam. But because it's free and local, scammers post fake listings and pose as buyers. The risk is almost always in how payment and delivery are handled: pay or get paid the wrong way and you're exposed. Deal in person, keep payment safe and verifiable, and the platform is perfectly usable."],
            ["I'm selling on Gumtree — how do I avoid buyer scams?",
             "Take cash on collection, or wait for a bank transfer to actually show in your own account before handing anything over — never trust an emailed or screenshot 'payment confirmation'. Refuse buyer-arranged couriers for valuable items, never refund an 'overpayment', and avoid PayPal 'friends and family'. Keep messages on Gumtree and be wary of anyone rushing you to post before funds clear."],
            ["I'm buying on Gumtree — how do I avoid fake listings?",
             "Never pay a deposit or the full price by bank transfer before seeing the item, car, pet or flat in person. Be suspicious of prices well below market value, sellers who are 'away' and want payment up front, and any 'shipping company' or 'escrow' middleman. View first, pay on collection where possible, and walk away from pressure."],
            ["How do I report a Gumtree scammer?",
             "Use the 'Report' link on the advert or the user's profile to flag it to Gumtree. If money or details were lost, report to Action Fraud at reportfraud.police.uk or 0300 123 2040 (Police Scotland on 101 in Scotland), and contact your bank immediately if you paid by transfer. Keep screenshots of the listing and chat as evidence."],
        ],
    },
    {
        "slug": "google-voice-verification-scam",
        "title": "Google Voice Verification Code Scam UK: Don't Share That Code",
        "description": "Someone asks you to read back a Google verification code to 'prove you're real'? It's a scam to hijack your number. Here's how it works and what to do.",
        "hero": "A buyer or match asks you to read back a Google verification code — never do it. Here's the Google Voice scam explained.",
        "date": TODAY,
        "category": "fraud",
        "keywords": [
            "google voice verification code scam", "google voice code scam",
            "verification code scam", "google voice scam uk", "share verification code scam",
            "google voice number scam", "marketplace verification code scam",
            "do not share verification code", "google voice fraud", "otp code scam",
        ],
        "sections": [
            ["What is the Google Voice verification code scam?",
             "In this scam, someone you've met online — often a 'buyer' replying to a marketplace listing, or a new match on a dating app — asks to verify that you're 'a real person and not a bot'. They say they'll send a verification code to your phone and ask you to read it back. In reality they are trying to register a Google Voice phone number using YOUR mobile number as the verification, or to take over an account tied to your number. The six-digit code Google texts you is the key to that — so by reading it out, you hand them the ability to set up a Google Voice number in your name, which they then use to scam other people while hiding their own identity. The whole 'are you real?' framing exists only to get the code out of you."],
            ["How the scam works, step by step",
             "- A stranger contacts you — a too-keen buyer for your marketplace item, or a fast-moving dating-app match.\n- They claim they've been scammed before and want to 'verify' you, or check you're 'not a bot'.\n- They say they're sending a Google (or other) verification code to your number and ask you to share or read it back.\n- A six-digit code arrives by text — it's actually Google verifying a Google Voice sign-up that uses your number.\n- If you read the code back, they complete the sign-up and now control a Google Voice number linked to you.\n- They use that number to defraud others; if your number was tied to your own accounts, they may also try to break into those."],
            ["Where it happens and who's targeted",
             "It thrives anywhere strangers message each other: Facebook Marketplace, Gumtree, eBay and Vinted listings; dating apps; and even replies to rental or job ads. Sellers are a favourite target because a 'verify you're real' request can sound like a cautious, sensible buyer. The same trick is used with other services' one-time codes too — the principle is identical: a code that arrives on your phone is meant for you alone, and anyone steering you to read it out is trying to take something over in your name."],
            ["Warning signs",
             "- A stranger asks you to share, read back, or type in a verification code they've 'sent' you.\n- The reason given is to 'prove you're real', 'check you're not a bot', or 'verify' you before buying or chatting.\n- A code arrives by text that you didn't request for any login of your own.\n- The contact is unusually keen, moves fast, or pushes the 'verification' before any normal buyer/seller or dating conversation.\n- Any pressure or urgency around the code."],
            ["What to do if you shared the code",
             "- Don't panic, but act. If you gave away a Google verification code, go to voice.google.com, sign in, and reclaim or remove any Google Voice number linked to your number (Google has a dedicated process for this).\n- Change your Google account password and turn on two-step verification.\n- Review your other accounts that use your phone number for security, and update any passwords you're unsure about.\n- Watch for unusual texts or calls suggesting your number is being used to contact others.\n- Stop contact with the scammer and report them on the platform you met them."],
            ["How to report it in the UK",
             "Report the account to the platform where it happened (the marketplace or dating app) so they can ban it. Report the fraud to Action Fraud at reportfraud.police.uk or 0300 123 2040 (in Scotland, contact Police Scotland on 101). You can reclaim a Google Voice number taken out in your name at voice.google.com, and report abuse to Google. Forward scam text messages free to 7726. The simplest protection going forward: never share a verification or one-time code with anyone — no genuine person or company needs you to read one back."],
        ],
        "faq": [
            ["What is the Google Voice verification code scam?",
             "It's a trick where a stranger online asks you to read back a verification code 'to prove you're real'. The code is actually Google verifying a Google Voice number being set up using your mobile number. If you share it, the scammer registers that number in your name and uses it to defraud others while hiding their identity. The 'are you a real person?' line is just bait for the code."],
            ["Why do they want my verification code?",
             "Because a code sent to your phone authorises something tied to your number — most often creating a Google Voice number, but the same trick works against other accounts' one-time codes. With your code, the scammer completes a sign-up or login as if they were you. That's why no genuine buyer, match, or company ever needs you to read a code back — the code is for you alone."],
            ["I shared the code — what do I do?",
             "Go to voice.google.com, sign in, and reclaim or remove any Google Voice number linked to your number using Google's process. Change your Google password and enable two-step verification, and review other accounts that rely on your phone number. Stop contact with the scammer, report them on the platform you met them, and report the fraud to Action Fraud at reportfraud.police.uk or 0300 123 2040."],
            ["How do I report the Google Voice scam in the UK?",
             "Report the account to the marketplace or dating app it came from, and report the fraud to Action Fraud at reportfraud.police.uk or 0300 123 2040 (Police Scotland on 101 in Scotland). Reclaim any Google Voice number set up in your name at voice.google.com and report abuse to Google. Forward scam texts to 7726. Going forward, never share a one-time or verification code with anyone."],
        ],
    },
]


def main() -> int:
    if not POSTS_FILE.exists():
        print(f"❌ {POSTS_FILE} not found. Run from the repo root.")
        return 1
    data = json.loads(POSTS_FILE.read_text(encoding="utf-8"))
    if not isinstance(data, list) or not data:
        print(f"❌ {POSTS_FILE} should be a non-empty list.")
        return 1

    template_keys = set(data[0].keys())
    existing = {p.get("slug") for p in data}
    for post in NEW_POSTS:
        if post["slug"] in existing:
            print(f"❌ Slug already exists, aborting: {post['slug']!r}")
            return 1
        if set(post.keys()) != template_keys:
            print(f"❌ Key mismatch for {post['slug']!r}: "
                  f"missing={sorted(template_keys - set(post))} extra={sorted(set(post) - template_keys)}")
            return 1

    data[0:0] = NEW_POSTS  # newest first
    POSTS_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"✅ Inserted {len(NEW_POSTS)} guides: {', '.join(p['slug'] for p in NEW_POSTS)}")
    print(f"📚 Total posts: {len(data)}")
    print("Next: remove the 4 slugs from ARTICLE_REDIRECTS (done) + run build.py.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
