#!/usr/bin/env python3
"""Apply the 18 July 2026 query-intent and evidence upgrade.

The migration is deterministic and idempotent so the editorial changes are
reviewable in source control. It updates the five Search Console opportunity
guides and replaces duplicated payment/identity recovery detail with a link to
the maintained /recovery/ hub.
"""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
POSTS_PATH = ROOT / "content" / "posts.json"
REVIEW_DATE = "2026-07-18"


def source(label: str, url: str) -> list[str]:
    return [label, url]


UPDATES: dict[str, dict] = {
    "dpd-delivery-scam-text": {
        "title": "DPD Scam Text or Genuine Message? Check a Fake Delivery Text",
        "description": "Received a DPD delivery text? Check the parcel independently, distinguish a fake redelivery fee from genuine import charges, and report a scam safely.",
        "hero": "A DPD text is not proved genuine by its sender name. Match it to a real order and parcel number through DPD's official site or app before using any payment route.",
        "sections": {
            "What is the DPD scam text?": "A DPD scam text is an SMS phishing message that impersonates the courier to collect personal or card details. Common versions claim a delivery failed, an address is incomplete, or a small redelivery fee is due. The quickest safe answer is not to judge the logo or sender name: find the parcel number in the retailer's dispatch confirmation and enter it through the official DPD site or app. No matching parcel means the message has no verified connection to your order.\n\nPayment wording needs one important distinction. An unexpected fee to reattempt an ordinary UK delivery is a common scam pattern, but DPD's international guidance says a recipient can receive an SMS or email with a secure payment link for genuine import duties or taxes. Verify the parcel, charge and route independently before paying either kind of request.",
            "How to check whether a DPD text is genuine": "Use this three-part check before tapping anything:\n\n- Order: are you expecting a parcel, and does the retailer say DPD is carrying it?\n- Parcel: does the parcel number from the retailer work when you type it into DPD's official site or app yourself?\n- Request: does the independently opened tracking record show the same delivery status or verified import charge?\n\nDo not rely on the displayed sender name, spelling or page design. If you cannot match all three elements, contact the retailer through your order record. DPD does not need your card PIN, online-banking password or one-time banking code to deliver a parcel.",
        },
        "evidence": [
            {"signal": "Standard redelivery fee", "finding": "An unexpected small fee to reattempt an ordinary delivery is a strong scam warning. Verify the parcel rather than paying from the text.", "basis": "DPD phishing guidance and independent parcel tracking."},
            {"signal": "Import duties or taxes", "finding": "A payment message is not automatically fake: DPD says it may notify recipients by SMS or email when genuine international duties or taxes are due.", "basis": "DPD UK International support."},
            {"signal": "Sender says DPD", "finding": "A sender label is not identity proof. Match the message to the retailer's order and the independently opened DPD tracking record.", "basis": "Ofcom advises contacting an organisation through a route found independently."},
        ],
        "message_examples": [
            {"label": "Likely redelivery-fee scam", "message": "DPD: We could not deliver your parcel. Pay £1.45 within 12 hours: dpd-redelivery-check.example", "assessment": "The deadline, unverified parcel and lookalike route are warning signs. Do not use the link."},
            {"label": "Import charge requiring verification", "message": "DPD: Duties and taxes are due for parcel [reference].", "assessment": "This could be genuine for an international parcel, but only pay after the retailer's parcel number and the charge match DPD's official tracking or support route."},
        ],
        "sources_checked": [
            source("DPD — Warning about phishing emails and text messages", "https://www.dpd.com/de/en/news/warning-about-phishing-e-mails-and-text-messages-in-the-name-of-dpd/"),
            source("DPD UK International — duties and taxes payment support", "https://international.dpd.co.uk/support"),
            source("Ofcom — What to do about a scam call, text or message", "https://www.ofcom.org.uk/phones-and-broadband/scam-calls-and-messages/what-to-do-about-a-scam-call-text-or-message"),
        ],
    },
    "bank-text-codes-not-arriving": {
        "title": "Halifax Text Not Arriving? Bank Verification Code Fixes",
        "description": "Halifax or another bank verification text not arriving? Check the registered number, app, signal and message filters, then use a safe alternative verification route.",
        "hero": "A missing Halifax or bank passcode is usually a delivery or account-verification problem, not proof of a scam. Run these checks once, then contact the bank safely.",
        "keywords": [
            "halifax text messages not arriving", "halifax passcode not received",
            "bank verification text not arriving", "bank text not arriving",
            "verification code not received", "security code not coming through",
            "bank registered mobile number", "bank app verification",
        ],
        "sections": {
            "First identify which bank text is missing": "If a Halifax or other bank verification text has not arrived, first check whether the bank has your current mobile number, whether the official app is offering approval instead, and whether ordinary calls and texts still work. Then request one fresh code only. Repeated requests can leave several short-lived codes arriving out of order.\n\nA missing expected code is different from an unexpected message claiming to be the bank. This page solves non-delivery. If a text arrived and asks you to log in, share a code or move money, use the separate [Halifax scam-text guide](/guides/halifax-bank-scam-text-uk/).",
            "Halifax text messages not arriving: the relevant checks": "Halifax says its extra security checks can use the Mobile Banking app, a texted passcode or an automated phone call. It also says the mobile number on the account must be current.\n\n- Open Halifax through a trusted bookmark or type `halifax.co.uk` yourself.\n- Check or update the mobile number shown for the account.\n- If the official screen offers app approval or an automated call, use that route rather than waiting for repeated texts.\n- Halifax is moving customers to the Lloyds brand, so follow the current instructions displayed for your own account and card rather than assuming which app applies.\n- If no offered method works, contact Halifax through the app or the number printed on the card. Halifax says a One Time Password can be posted when a passcode cannot be received by text or automated call, although that is not an instant fix.",
        },
        "evidence": [
            {"signal": "Registered number", "finding": "Halifax needs the current mobile number to send a passcode or make an automated verification call.", "basis": "Halifax extra-security guidance."},
            {"signal": "Alternative approval", "finding": "Depending on the task, Halifax can use its app, an SMS passcode or an automated call.", "basis": "Halifax extra-security guidance."},
            {"signal": "No text and no call", "finding": "Contact Halifax through the app or card number. Halifax documents a posted One Time Password route when text and automated call are unavailable.", "basis": "Halifax passcode guidance."},
            {"signal": "Phone also lost service", "finding": "Treat this as more urgent than one missing code and ask the mobile provider about an unrecognised SIM replacement or number port.", "basis": "NCSC SMS-security guidance and Halifax SIM-swap warning."},
        ],
        "sources_checked": [
            source("Halifax — Extra security checks for shopping and banking online", "https://www.halifax.co.uk/helpcentre/everyday-banking/payments-and-transfers/security-checks.html"),
            source("Halifax — Passcode scams and alternative One Time Password", "https://www.halifax.co.uk/helpcentre/protecting-yourself-from-fraud/bank-safely-sms-one-time-passcode.html"),
            source("Halifax — Latest scams and SIM-swap warning signs", "https://www.halifax.co.uk/helpcentre/protecting-yourself-from-fraud/latest-scams.html"),
            source("NCSC — Protecting SMS used in critical business processes", "https://www.ncsc.gov.uk/guidance/protecting-sms-messages-used-in-critical-business-processes"),
        ],
    },
    "halifax-bank-scam-text-uk": {
        "title": "Fake Halifax Text? Scam Checks, 159 and Safe Reporting",
        "description": "Received an unexpected Halifax fraud or payment text? Do not share a passcode or move money. Check it in the app, through the card number or via 159.",
        "hero": "This page is for an unexpected Halifax message. If an expected Halifax passcode simply did not arrive, use the separate troubleshooting guide.",
        "sections": {
            "What a fake Halifax text looks like": "A Halifax scam text impersonates the bank to make you tap a link, disclose banking details, share a passcode or move money. Common stories include a blocked payment, new payee, locked account or suspicious login. The wording is not proof either way.\n\nUse this page when a message arrived unexpectedly. If you initiated a login or card payment and the expected verification text did not arrive, go to the [Halifax text-not-arriving guide](/guides/bank-text-codes-not-arriving/) instead.",
            "How to check if a Halifax text is genuine": "Do not reply, use the link or call a number in the message. Open the official Halifax or Lloyds app used for your account, call the number printed on your card, or call 159; Stop Scams UK lists Halifax as a participating bank.\n\nDuring the Halifax-to-Lloyds brand change, Halifax says links or QR codes it sends will be for general information only: it will not use them to ask you to log in or verify yourself. Halifax also says it will not ask you to share personal details or move money by phone, email or text. A request for a passcode, app approval or transfer to a 'safe account' is therefore enough to end the interaction and contact the bank independently.",
        },
        "evidence": [
            {"signal": "Link asks for login or verification", "finding": "Treat it as a scam during the brand transition; Halifax says its informational links and QR codes will not ask customers to log in or verify.", "basis": "Halifax latest-scams guidance."},
            {"signal": "Caller or text asks for a passcode", "finding": "Do not share it or approve an action for someone else. Halifax says a passcode is for the customer alone.", "basis": "Halifax passcode-scam guidance."},
            {"signal": "Instruction to move money", "finding": "Stop. Halifax says it will not ask customers to move money by phone, email or text.", "basis": "Halifax brand-change fraud warning."},
            {"signal": "Safe callback", "finding": "Use the number on the card, the official app, or 159 rather than a number in the message.", "basis": "Halifax and Stop Scams UK."},
        ],
        "message_examples": [
            {"label": "Reconstructed blocked-payment lure", "message": "HALIFAX: We blocked a payment of £79.99. If this wasn't you, verify now: halifax-secure-check.example", "assessment": "Do not use the link. Check activity in the official app or call the card number or 159."},
            {"label": "Reconstructed passcode follow-up", "message": "Read us the code we just sent so we can cancel the fraud.", "assessment": "Halifax says passcodes are private and it will not call to ask you to use one to stop fraud, issue a refund or secure an account."},
        ],
        "sources_checked": [
            source("Halifax — Latest scams and the Halifax-to-Lloyds brand change", "https://www.halifax.co.uk/helpcentre/protecting-yourself-from-fraud/latest-scams.html"),
            source("Halifax — Passcode scams", "https://www.halifax.co.uk/helpcentre/protecting-yourself-from-fraud/bank-safely-sms-one-time-passcode.html"),
            source("Halifax — How to protect yourself from fraud", "https://www.halifax.co.uk/helpcentre/protecting-yourself-from-fraud.html"),
            source("Stop Scams UK — 159 participating banks", "https://stopscamsuk.org.uk/our-programmes/159-phone-number/"),
        ],
    },
    "nhs-appointment-scam-text-uk": {
        "title": "Is This NHS Appointment Text Genuine? Checks and Scam Signs",
        "description": "The NHS can send appointment texts and NHS App fallback messages. Check the appointment independently and recognise links asking for payment or sensitive details.",
        "hero": "Yes, NHS services can send genuine appointment texts. The decisive check is whether the message matches your NHS App, provider or appointment—not whether it merely says NHS.",
        "sections": {
            "What a fake NHS text looks like": "An NHS scam text imitates an appointment reminder, cancellation, waiting-list check or health-service message to collect personal or payment details. But a text is not automatically fake: NHS services and their messaging suppliers can use SMS, including when an NHS App message is not delivered or read.\n\nNHS England's current messaging guidance gives one specific fallback example: a text from `NHSApp` telling the named patient that a secure message is waiting in the NHS App or at `https://www.nhs.uk/inbox`. Other legitimate provider messages can differ. The safe test is to open the NHS App or NHS account yourself, or contact the named GP surgery or hospital through independently found details, and match the message to a real appointment or communication.",
            "How to check an NHS text safely": "Do not start from an unexpected link. Instead:\n\n- Open the NHS App yourself and check Messages, Appointments, referrals and hospital appointments.\n- NHS England says App notifications can fall back to SMS within a few hours if they are not delivered or read, so check whether the same secure message exists in the App.\n- Contact the named GP surgery, hospital or clinic through a number on an appointment letter or its official `nhs.uk` page.\n- A surprise demand for a fee to keep or rebook ordinary NHS care, or a request for bank details to receive a grant or refund, needs direct verification before any response.\n- A non-`nhs.uk` link is not automatically fraudulent because some trusts use patient portals, but never trust it solely because it arrived by text. Confirm the provider and portal independently.",
        },
        "evidence": [
            {"signal": "Text from NHSApp", "finding": "NHS England documents an SMS fallback that tells a named patient to open the NHS App or use `https://www.nhs.uk/inbox`.", "basis": "NHS England notifications and messaging guidance."},
            {"signal": "Appointment change", "finding": "Genuine cancellations, reminders and updates can appear through the NHS App, a trust portal, SMS or email. Match the message to the provider and appointment.", "basis": "NHS England hospital appointments guidance."},
            {"signal": "Payment request", "finding": "A surprise charge to retain or rebook ordinary NHS care is a strong warning and must be checked directly; limited statutory NHS charges do exist.", "basis": "NHS Constitution for England."},
            {"signal": "Link outside nhs.uk", "finding": "Treat it as unverified, not automatically fake: NHS trusts can use patient-engagement portals. Confirm the trust and portal independently.", "basis": "NHS England hospital appointments guidance."},
        ],
        "message_examples": [
            {"label": "Documented NHS App fallback pattern", "message": "NHSApp: You have received a new secure message from the NHS. Open the NHS App to read it.", "assessment": "NHS England documents this pattern. Open the App yourself rather than relying on the text link."},
            {"label": "Reconstructed appointment-fee scam", "message": "NHS: Your appointment will be cancelled today. Pay £2.49 to keep your slot: nhs-booking-check.example", "assessment": "The urgent fee and unverified route are strong scam signs. Check the appointment in the App or with the provider."},
        ],
        "sources_checked": [
            source("NHS England Digital — Notifications and messaging in the NHS App", "https://digital.nhs.uk/services/nhs-app/nhs-app-features/notifications-and-messaging-in-the-nhs-app"),
            source("NHS England Digital — Hospital and specialist appointments in the NHS App", "https://digital.nhs.uk/services/nhs-app/nhs-app-features/hospital-referrals-and-appointments-in-the-nhs-app"),
            source("NHS — Messages in the NHS App", "https://www.nhs.uk/nhs-app/help/messages/"),
            source("GOV.UK — The NHS Constitution for England", "https://www.gov.uk/government/publications/the-nhs-constitution-for-england/the-nhs-constitution-for-england"),
        ],
    },
    "dvla-vehicle-tax-text-scam": {
        "title": "DVLA Vehicle Tax Text: Is It Genuine or a Scam?",
        "description": "A DVLA text says vehicle tax failed or a refund is waiting? DVLA says it will not ask for bank or payment details this way. Check only through GOV.UK.",
        "hero": "A DVLA text asking you to confirm bank or payment details, or claim a vehicle-tax refund through a link, is a scam. Use GOV.UK directly instead.",
        "sections": {
            "What the fake DVLA tax text says": "Fake DVLA texts commonly claim a vehicle-tax payment failed, tax is overdue, a penalty is imminent, or a refund is waiting. They direct the recipient to a GOV.UK-style copycat page that collects card, bank or identity details.\n\nDVLA's current advice makes the answer narrower and more reliable than judging the sender name: it will not ask for bank-account details or ask you to confirm payment details by email or text, and vehicle-tax refunds are issued automatically rather than claimed through an emailed link. Older DVLA guidance also states that it does not send text messages about vehicle-tax refunds. Use GOV.UK yourself to check the vehicle instead of opening the message route.",
            "How to check with DVLA safely": "Close the message and type `gov.uk` yourself. Use:\n\n- `gov.uk/check-vehicle-tax` to check whether a vehicle is taxed.\n- `gov.uk/vehicle-tax` to tax a vehicle through the official service.\n- `gov.uk/vehicle-tax-refund` to understand when a refund is issued automatically.\n\nDVLA says it may ask a person to confirm personal details by email or text when there is a live enquiry, so 'DVLA never texts' is not a safe universal rule. The red line is a text or email asking for bank details, asking you to confirm payment details, or directing you to claim a vehicle-tax refund. If a message refers to a real enquiry, confirm it through the GOV.UK service or contact route you open yourself.",
        },
        "evidence": [
            {"signal": "Vehicle-tax refund link", "finding": "Treat it as a scam. DVLA says refunds are issued automatically and not through a message link.", "basis": "DVLA scam-avoidance guidance, updated December 2025."},
            {"signal": "Bank or payment details", "finding": "DVLA says it will not ask for bank-account details or ask you to confirm payment details by email or text.", "basis": "DVLA scam-avoidance guidance."},
            {"signal": "Text about a live enquiry", "finding": "A message is not automatically fake: DVLA says it may ask for confirmation of personal details where a live enquiry exists. Verify through GOV.UK.", "basis": "DVLA scam-avoidance guidance."},
            {"signal": "Check tax status", "finding": "Ignore the message route and use the official vehicle-tax checker on GOV.UK.", "basis": "GOV.UK vehicle services."},
        ],
        "message_examples": [
            {"label": "Reconstructed failed-payment lure", "message": "DVLA: Your vehicle tax payment failed. Update payment details today to avoid a penalty: gov-uk-tax-check.example", "assessment": "DVLA says it will not ask for bank or payment details this way. Use GOV.UK directly."},
            {"label": "Reconstructed refund lure", "message": "DVLA: You have a £68.40 vehicle tax refund. Claim within 24 hours.", "assessment": "DVLA says vehicle-tax refunds are automatic, not claimed from a text link."},
        ],
        "sources_checked": [
            source("DVLA — Top tips for avoiding scams", "https://www.gov.uk/government/news/dvlas-top-tips-for-avoiding-scams"),
            source("GOV.UK — Check if a vehicle is taxed", "https://www.gov.uk/check-vehicle-tax"),
            source("GOV.UK — Vehicle tax refund", "https://www.gov.uk/vehicle-tax-refund"),
            source("Ofcom — What to do about a scam call, text or message", "https://www.ofcom.org.uk/phones-and-broadband/scam-calls-and-messages/what-to-do-about-a-scam-call-text-or-message"),
        ],
    },
}


def replace_section(post: dict, heading: str, body: str) -> None:
    for section in post.get("sections", []):
        if section[0] == heading:
            section[1] = body
            return
    raise ValueError(f"{post['slug']}: missing section {heading!r}")


def consolidate_recovery_copy(post: dict) -> bool:
    """Replace duplicated threshold/detail paragraphs with the central hub.

    Only paragraphs containing the exact audited PSR/Cifas boilerplate are
    touched. Brand-specific urgent actions and reporting instructions remain.
    """
    changed = False
    for section in post.get("sections", []):
        paragraphs = section[1].split("\n\n")
        new_paragraphs: list[str] = []
        for paragraph in paragraphs:
            if (
                "The PSR rules include a 13-month claim window" in paragraph
                or paragraph.startswith("If money or payment details were involved, contact your bank or card issuer immediately. The payment method changes the recovery route;")
            ):
                # The article-wide do-now component already links the maintained
                # recovery hub. Dropping this paragraph avoids replacing one
                # repeated legal block with a different repeated CTA paragraph.
                changed = True
                continue
            if (
                (
                    "Cifas Protective Registration at `cifas.org.uk`" in paragraph
                    and ("credit report" in paragraph or "credit file" in paragraph)
                )
                or paragraph.startswith("If identity details may have been exposed, follow the identity-protection steps in the")
            ):
                changed = True
                continue
            new_paragraphs.append(paragraph)
        section[1] = "\n\n".join(new_paragraphs) or (
            "Act now using the payment, account and identity steps in our "
            "[scam recovery checklist](/recovery/)."
        )
    return changed


def main() -> None:
    posts = json.loads(POSTS_PATH.read_text(encoding="utf-8"))
    by_slug = {post["slug"]: post for post in posts}

    missing = sorted(set(UPDATES) - set(by_slug))
    if missing:
        raise SystemExit(f"Missing target posts: {', '.join(missing)}")

    for slug, update in UPDATES.items():
        post = by_slug[slug]
        for key in ("title", "description", "hero", "keywords", "evidence", "message_examples", "sources_checked"):
            if key in update:
                post[key] = update[key]
        for heading, body in update.get("sections", {}).items():
            replace_section(post, heading, body)
        # Remove stale legacy copies: the build and editorial gate use sections.
        post.pop("content", None)
        post.pop("excerpt", None)
        post["updated"] = REVIEW_DATE

    consolidated = 0
    for post in posts:
        if consolidate_recovery_copy(post):
            post["updated"] = REVIEW_DATE
            consolidated += 1

    POSTS_PATH.write_text(
        json.dumps(posts, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Updated {len(UPDATES)} priority guides; consolidated recovery copy in {consolidated} guides")


if __name__ == "__main__":
    main()
