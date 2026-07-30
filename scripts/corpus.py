"""corpus.py — the ONE definition of what the public corpus is.

`content/posts.json` holds **source records**. Not all of them are pages. A guide
that has been consolidated into another is deliberately retained as an archive
copy, is never rendered, and 301s to its replacement at the edge.

Before this module that partition lived in three places and agreed by accident:

  * `build.CONSOLIDATED_LIVE_SLUGS` — a hand-maintained set of slugs;
  * `build.ARTICLE_REDIRECTS` — a *second* hand-maintained entry for the same
    slug, giving the 301 target;
  * `similarity_report.py` — excluded redirected records, while the publication
    gate did not, so the gate compared an archive copy against the very guide it
    had been consolidated into and reported a 54% duplicate-content BLOCK. The
    gate's own remedy text reads "or consolidate the two guides", which had
    already happened (operator review, 2026-07-30).

Now a single field on the record is the source of truth:

    "consolidated_into": "evri-delivery-scam-guide"

Everything else — non-rendering, the 301, internal-link canonicalisation, and
exclusion from the publication similarity check — is derived from it. A
consolidated record is not being shipped, so it is outside the AdSense
duplicate-page question by construction rather than by a named exception.

Validation fails closed. A broken consolidation graph stops the build and the
publication gate rather than silently un-publishing a guide or publishing an
archive copy.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

# The field that makes a source record non-public.
CONSOLIDATED_INTO = "consolidated_into"


# Article-level 301 redirects. Used when an article is deleted but its URL
# may have inbound links from Google's index, Search Console history, or
# external sites. The value is either:
#   - another article slug (the canonical replacement), or
#   - "__CAT__:<category-slug>" to redirect to a category landing page.
#
# Populated as part of the AdSense "Low value content" remediation on
# 2026-05-24: 51 short / duplicate articles were removed (the bimodal
# distribution of 49 articles <300 words alongside 155 articles >800 words
# was flagged by an AdSense reviewer). _redirects entries are emitted by
# build() so the deleted URLs still resolve via 301.
ARTICLE_REDIRECTS = {
    # ── Slug-collision artifacts (the "-2" duplicates) ──────────────────
    # Older builds auto-generated these "-2" URLs when two posts.json
    # entries shared a base slug. Deduplicating posts.json on 2026-05-24
    # stopped them being generated, so they 404'd — and Google had
    # discovered/indexed several (showed up as "Not found (404)" in Search
    # Console on 2026-05-28). Redirect each to its surviving canonical.
    "facebook-marketplace-scam-uk-guide-2":       "facebook-marketplace-scam-uk",
    "fake-online-pharmacy-uk-scam-2":             "fake-online-pharmacy-uk-scam",
    "is-temu-a-scam-uk-2":                        "is-temu-a-scam-uk",
    "concert-ticket-scam-uk-2":                   "concert-ticket-scam-uk",
    "forex-trading-scam-uk-2":                    "forex-trading-scam-uk",
    "evri-text-scam-uk-2":                        "evri-delivery-scam-guide",
    # ── Thin/duplicate articles removed in the AdSense remediation ──────
    "paypal-email-scam-signs":                    "__CAT__:payment",
    "facebook-marketplace-scam-uk-guide":         "facebook-marketplace-scam-uk",
    "facebook-marketplace-scam-signs":            "facebook-marketplace-scam-uk",
    "hmrc-tax-refund-scam-checklist":             "__CAT__:government",
    "gumtree-scam-uk":                            "__CAT__:marketplace",
    "parking-fine-scam-text-messages-uk":         "parking-fine-scam-text-uk",
    "bank-transfer-scam-warning-signs":           "__CAT__:payment",
    "crypto-investment-scam-checklist":           "__CAT__:crypto",
    # GSC 2026-06-04: flagged as Not found (404). The canonical live guide
    # on this exact topic is crypto-investment-scams-uk-protection — article
    # → article redirect preserves more SEO juice than article → category.
    "crypto-investment-scam-uk-guide":            "crypto-investment-scams-uk-protection",
    "phone-call-scam-red-flags":                  "__CAT__:phone",
    "romance-scam-slow-burn-patterns":            "__CAT__:dating",
    "job-scam-checklist-uk":                      "__CAT__:employment",
    "puppy-sale-scam-checklist":                  "__CAT__:shopping",
    "travel-booking-scam-checklist":              "__CAT__:travel",
    "ticket-resale-scam-checklist":               "__CAT__:shopping",
    "shein-scam-or-legit-uk":                     "__CAT__:website",
    "ebay-scam-buyer-protection-uk":              "ebay-buyer-scam-uk",
    "evri-text-scam-uk":                          "__CAT__:sms",
    # royal-mail-text-scam-guide 404'd (no post at that slug); redirect to the live
    # royal-mail-text-scam-uk so the "royal mail parcel scams" demand lands somewhere real.
    "royal-mail-text-scam-guide":                 "royal-mail-text-scam-uk",
    # dpd-delivery-scam-text, yodel-scam-text-messages and
    # ups-delivery-scam-text-messages-uk were resurrected as full ~1,000-word
    # guides on 2026-06-05 — they were the site's highest-demand URLs (DPD alone
    # had 1,905 GSC impressions at pos 10.2) but the 2026-05-24 purge 301'd them
    # to a thin category page. Redirects removed so build() serves the real
    # guide pages again. See scripts/recover_courier_guides.py.
    "paypal-email-scam-uk":                       "__CAT__:payment",
    "invoice-scam-email-uk":                      "__CAT__:payment",
    "refund-scam-uk":                             "__CAT__:payment",
    "direct-debit-scam-uk":                       "__CAT__:payment",
    "hmrc-tax-refund-scam-awareness":             "__CAT__:government",
    "dvla-scam-email-awareness":                  "__CAT__:government",
    "dvla-email-scam-car-tax":                     "dvla-email-scam-uk",
    # ── Batch 14 consolidations (2026-07-03): near-duplicate topics merged
    # into the stronger surviving page rather than shipping two near-
    # identical guides. See docs/content-diversification-plan.md.
    "bt-broadband-tech-support-scam-uk":          "bt-broadband-scam-calls-uk",
    "linkedin-recruitment-scam-uk":               "linkedin-job-scam-guide-uk",
    # ── Batch 16 consolidations (2026-07-05): near-duplicate topics merged
    # into the stronger surviving page. See docs/content-diversification-plan.md.
    # NB: solar-panel-scam-uk was deliberately NOT consolidated here — the
    # 2026-06-15 audit already decided it and solar-panel-cold-caller-scam-uk
    # target genuinely different vectors (online/advertised vs cold-call) and
    # should stay separate, cross-linked pages.
    "sky-broadband-scam-call-uk":                 "isp-impersonation-scam-bt-sky-virgin-media",
    "tinder-investment-scam-uk":                  "pig-butchering-scam-uk",
    # ── Batch 17 consolidations (2026-07-06): near-duplicate topics merged
    # into the stronger surviving page. See docs/content-diversification-plan.md.
    # Resolves the 3-way bank/police impersonation overlap flagged since batch 15
    # (both redundant pages covered the same fake-authority-figure-phone-call
    # pattern already covered in depth by the survivor).
    "bank-impersonation-phone-scam-uk":                                        "police-impersonation-scam-call-uk",
    "impersonation-scams-when-criminals-pretend-to-be-your-bank-or-the-police": "police-impersonation-scam-call-uk",
    "fake-trading-platform-uk":                   "forex-trading-scam-uk",
    "debt-management-scam-uk":                    "debt-relief-scam-uk",
    "nhs-covid-scam-message":                     "__CAT__:government",
    "forex-trading-scams-uk-protection-guide":    "__CAT__:crypto",
    "trading-signal-scam-uk":                     "__CAT__:crypto",
    "work-from-home-scams-uk":                    "__CAT__:employment",
    "romance-scam-signs-uk-dating":               "__CAT__:dating",
    "puppy-scam-uk":                              "__CAT__:marketplace",
    "ticket-scam-uk":                             "__CAT__:marketplace",
    "holiday-booking-scam-uk":                    "__CAT__:travel",
    # 2nd purge-recovery batch (2026-06-07, see recover_purged_pages_2.py):
    # amazon-scam-email-uk → redirected to its live twin (consolidates the demand);
    # amazon-phone-call-scam-uk / chargeback / gumtree / google-voice resurrected as full guides.
    "amazon-scam-email-uk":                       "amazon-order-scam-email-checklist",
    "amazon-refund-scam-uk":                      "__CAT__:payment",
    "google-voice-scam-uk":                       "__CAT__:tech",
    "apple-id-scam-email-uk":                     "__CAT__:tech",
    "whatsapp-family-scam-urgent-money-messages": "__CAT__:social",
    "instagram-scam-message-uk":                  "__CAT__:social",
    "snapchat-scam-account-awareness":            "__CAT__:social",
    "energy-bill-scam-uk":                        "__CAT__:utility",
    "credit-score-scam-uk":                       "__CAT__:finance",
    # ── Cannibalisation cleanup (2026-06-15, external audit) ────────────────
    # Near-duplicate guides competing for the same intent were consolidated to
    # one canonical each. Survivors chosen by quality (freshness, clean slug,
    # no data defects); unique advice from each loser was grafted into its
    # survivor first, so these are article→article 301s (no content lost).
    # NB: solar-panel-scam-uk and solar-panel-cold-caller-scam-uk were KEPT as
    # separate guides — they target genuinely different vectors (general vs
    # cold-call) and are now reciprocally cross-linked, not merged.
    "concert-ticket-scam-uk-2026":                "concert-ticket-scam-uk",
    "forex-trading-scam-uk-2026":                 "forex-trading-scam-uk",
    "qr-code-payment-scam-guide":                 "qr-code-scam-uk",
    "qr-code-scam-payment-uk":                    "qr-code-scam-uk",
    "whatsapp-scam-family-message-uk":            "whatsapp-family-emergency-scam",
    # 2026-07-10 (batch 19): Action Fraud's own taxonomy doesn't separate
    # "mandate fraud" from "invoice fraud" by recurring-vs-one-off — it's the
    # formal reporting name for the whole redirected-payment pattern (UK
    # Finance/NCSC track "invoice and mandate" as one combined category too).
    # invoice-fraud-uk-businesses already said as much in its own FAQ. The one
    # genuinely new fact from the loser page (Direct Debit Guarantee vs the
    # business-size-gated APP reimbursement rules) was grafted into the
    # survivor first — this is an article -> article 301, no content lost.
    "mandate-fraud-uk-businesses":                "invoice-fraud-uk-businesses",
    # 2026-07-10 (final diversification batch): both near-duplicates found
    # while scoping the last generic-template pages, confirmed independently
    # against primary sources before merging.
    # windows-tech-support-scam-uk described the identical scam as
    # microsoft-support-scam-uk-guide (unsolicited call/pop-up -> fake virus
    # alert -> AnyDesk/TeamViewer remote access -> fake fix fee), and cited
    # "reportfraud.org.uk" as a reporting route — confirmed by direct DNS/HTTP
    # check to be a parked domain (names.co.uk registrar parking page), not a
    # real fraud-reporting service. No unique content to graft.
    "windows-tech-support-scam-uk":                "microsoft-support-scam-uk-guide",
    # push-payment-fraud-uk is "authorised push-payment (APP) fraud" — the
    # exact term bank-transfer-scam-uk already opens by defining itself as,
    # covering the same "safe account" con with 159 + PSR reimbursement-rule
    # detail. The loser's solicitor/conveyancing-payment FAQ entry is already
    # covered in depth by the dedicated conveyancing-fraud-uk page (now
    # cross-linked from the survivor) — no unique content lost.
    "push-payment-fraud-uk":                       "bank-transfer-scam-uk",
    # TRANSITIONAL — the last consolidation still declared here rather than on
    # its own record. `consolidation-metadata-v1` moves it to
    # "consolidated_into" on the Hermes record and deletes this line, in the
    # same patch. Until then corpus.legacy_static_consolidations() bridges it,
    # so no archive record can render while the two halves are reviewed apart.
    "hermes-parcel-scam-text-uk":                  "evri-delivery-scam-guide",
}


def _static(static_redirects: Optional[Dict[str, str]]) -> Dict[str, str]:
    """Default to the module's own map.

    Passing None must mean "the real redirects", not "no redirects". A caller
    that silently got {} would compute a DIFFERENT public corpus from the build
    — which is exactly how the publication gate came to disagree with
    similarity_report.py about whether the Hermes archive record was a page.
    Tests pass an explicit dict (including {}) to isolate the graph.
    """
    return ARTICLE_REDIRECTS if static_redirects is None else static_redirects


class CorpusError(Exception):
    """The consolidation graph is invalid. Nothing may be applied or built."""


def consolidation_map(posts: List[dict]) -> Dict[str, str]:
    """{consolidated slug: target slug}, straight off the records.

    Only well-formed entries appear here. Callers reach this through
    `partition()`, which validates first, so a malformed value has already
    stopped the build — it is never silently dropped back into the public set.
    """
    return {
        p["slug"]: p[CONSOLIDATED_INTO]
        for p in posts
        if isinstance(p, dict) and isinstance(p.get(CONSOLIDATED_INTO), str)
        and p[CONSOLIDATED_INTO].strip()
    }


# TRANSITIONAL, and deliberately a closed MAP of exactly the slugs mid-migration
# to the target each one must redirect to.
#
# Before `consolidation-metadata-v2`, consolidation was declared by a static
# ARTICLE_REDIRECTS entry beside a surviving source record. This map names the
# records still in that state so the code half and the content half can be
# reviewed apart without a window where an archive record renders.
#
# It is a MAP, not a set, because a set only asserted that a static entry
# EXISTED. Retargeting the pending entry to `no-such-guide` validated clean and
# shipped a broken redirect; retargeting it to `__CAT__:sms` republished the
# record entirely (operator review, 2026-07-30). The target is now pinned.
#
# It is also NOT a general rule. An earlier version bridged ANY source slug that
# happened to collide with a static redirect, which silently retired a record
# with no declaration anywhere. Outside this map, that collision is an error.
#
# `consolidation-metadata-v2` empties this and deletes it together with
# `pending_migrations()` and the union in `partition()`, in ONE reviewed
# transaction — see `release_manifest.py`'s migration applier.
PENDING_MIGRATION = {"hermes-parcel-scam-text-uk": "evri-delivery-scam-guide"}


def pending_migrations(posts: List[dict],
                       static_redirects: Optional[Dict[str, str]] = None,
                       pending: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    """{slug: target} for records still declaring consolidation the old way."""
    static_redirects = _static(static_redirects)
    pending = PENDING_MIGRATION if pending is None else pending
    declared = _declared([p for p in posts if isinstance(p, dict) and isinstance(p.get("slug"), str)])
    return {
        p["slug"]: static_redirects[p["slug"]]
        for p in posts
        if isinstance(p, dict) and isinstance(p.get("slug"), str)
        and p["slug"] in pending
        and p["slug"] in static_redirects
        and p["slug"] not in declared
        and not str(static_redirects[p["slug"]]).startswith("__CAT__:")
    }


def _declared(posts: List[dict]) -> Dict[str, object]:
    """Every record that CARRIES the field, whatever its value.

    Presence, not truthiness. `"consolidated_into": ""` is a broken
    consolidation, not an absent one: reading it as absent would quietly
    publish a record whose author meant to retire it.
    """
    return {
        p["slug"]: p[CONSOLIDATED_INTO]
        for p in posts
        if isinstance(p, dict) and isinstance(p.get("slug"), str) and CONSOLIDATED_INTO in p
    }


def validate_consolidation(posts: List[dict],
                           static_redirects: Optional[Dict[str, str]] = None,
                           pending: Optional[Dict[str, str]] = None) -> List[str]:
    """Return a list of problems. Empty list == valid.

    Pure and side-effect free, so the same fixtures run against every consumer.
    """
    problems: List[str] = []
    static_redirects = _static(static_redirects)
    # Explicit, so a migration transaction can validate the FINAL state (with the
    # static entry removed and the map emptied) BEFORE writing anything — the
    # applier cannot import a module version that does not exist on disk yet.
    pending = PENDING_MIGRATION if pending is None else pending

    if not isinstance(posts, list) or not posts:
        return ["posts must be a non-empty list"]

    # Duplicate raw slugs make "which record is consolidated?" ambiguous, and
    # the answer would depend on list order.
    seen: Dict[str, int] = {}
    for p in posts:
        if not isinstance(p, dict):
            problems.append(f"post record is {type(p).__name__}, expected an object")
            continue
        slug = p.get("slug")
        if not isinstance(slug, str) or not slug.strip():
            problems.append("a post record has no 'slug'")
            continue
        seen[slug] = seen.get(slug, 0) + 1
    for slug, n in sorted(seen.items()):
        if n > 1:
            problems.append(f"duplicate source slug {slug!r} ({n} records)")

    all_slugs = set(seen)
    valid_records = [p for p in posts if isinstance(p, dict) and isinstance(p.get("slug"), str)]
    declared = _declared(valid_records)
    mapping = consolidation_map(valid_records)

    for slug, target in sorted(declared.items(), key=lambda kv: kv[0]):
        if not isinstance(target, str) or not target.strip():
            problems.append(
                f"{slug!r}: {CONSOLIDATED_INTO} is present but empty ({target!r}). Remove the "
                f"field to publish the record, or give it a target to retire it."
            )
            continue
        if target == slug:
            problems.append(f"{slug!r}: {CONSOLIDATED_INTO} points at itself")
            continue
        if target not in all_slugs:
            problems.append(f"{slug!r}: {CONSOLIDATED_INTO} target {target!r} is not a source record")
            continue
        if target in mapping:
            # A chain means a reader is 301'd to a page that also 301s. Any
            # cycle also lands here, because every node in a cycle is
            # consolidated and so is its target.
            problems.append(
                f"{slug!r}: {CONSOLIDATED_INTO} target {target!r} is itself consolidated "
                f"(into {mapping[target]!r}) — chains and cycles are not allowed; point "
                f"straight at the final guide"
            )
            continue
        if target in static_redirects:
            problems.append(
                f"{slug!r}: {CONSOLIDATED_INTO} target {target!r} is itself statically "
                f"redirected (to {static_redirects[target]!r})"
            )
        if slug in static_redirects:
            # Two sources of truth for one slug is precisely what this field
            # exists to remove — reject even when they happen to agree.
            problems.append(
                f"{slug!r} is BOTH consolidated via {CONSOLIDATED_INTO} and listed in the "
                f"static redirect map (to {static_redirects[slug]!r}) — remove the static entry"
            )

    # A source record must never share its slug with a static redirect. The
    # static map is for slugs with NO record; a collision means two places claim
    # to decide the same URL, and the record would be silently retired with no
    # declaration on it. Only slugs mid-migration are exempt, and each of those
    # is separately asserted below.
    for slug in sorted(all_slugs & set(static_redirects)):
        if slug in pending:
            continue
        problems.append(
            f"{slug!r} has a source record AND a static redirect entry (to "
            f"{static_redirects[slug]!r}). Declare the consolidation on the record with "
            f"{CONSOLIDATED_INTO} and remove the static entry — a static entry is for slugs "
            f"with no record."
        )

    # BOTH halves of each pending migration, so neither can land alone. The
    # metadata-only half is caught by the collision rule above; this catches the
    # code-only half, which used to republish the record with no redirect and no
    # error at all (operator review, 2026-07-30).
    for slug, want_target in sorted(pending.items()):
        if slug not in all_slugs:
            continue                       # record already gone; nothing to migrate
        has_meta = slug in declared
        has_static = slug in static_redirects
        # PIN the target while the bridge exists. Checking only that a static
        # entry exists let it be retargeted to a non-existent guide (broken
        # redirect) or to a category (record republished) with zero problems.
        if has_static and static_redirects[slug] != want_target:
            problems.append(
                f"{slug!r} is mid-migration and must redirect to {want_target!r}, but the static "
                f"map says {static_redirects[slug]!r}"
            )
        if has_static and want_target not in all_slugs:
            problems.append(
                f"{slug!r} is mid-migration and its pinned target {want_target!r} is not a "
                f"source record"
            )
        if has_meta and not has_static:
            problems.append(
                f"{slug!r} has completed its migration — remove it from "
                f"corpus.PENDING_MIGRATION (and delete the set if it is now empty)."
            )
        elif not has_meta and not has_static:
            problems.append(
                f"{slug!r} is mid-migration but declares its consolidation NOWHERE: the "
                f"static redirect entry was deleted without adding {CONSOLIDATED_INTO} to the "
                f"record. The guide would republish with no redirect. Apply both halves."
            )

    # An explicit cycle walk. The chain rule above already catches every cycle;
    # this states the property directly so a future relaxation of that rule
    # cannot reintroduce one silently.
    for start in sorted(mapping):
        slow, fast = start, start
        while True:
            fast = mapping.get(mapping.get(fast, ""), "")
            slow = mapping.get(slow, "")
            if not fast or not slow:
                break
            if slow == fast:
                problems.append(f"consolidation cycle reachable from {start!r}")
                break

    return sorted(set(problems))


def partition(posts: List[dict],
              static_redirects: Optional[Dict[str, str]] = None,
              pending: Optional[Dict[str, str]] = None) -> Tuple[List[dict], List[dict]]:
    """(public, consolidated). Raises CorpusError if the graph is invalid.

    `public` is what gets rendered, indexed, listed, searched and similarity-
    checked. `consolidated` is retained source data that 301s.
    """
    problems = validate_consolidation(posts, static_redirects, pending)
    if problems:
        detail = "\n".join(f"  - {p}" for p in problems)
        raise CorpusError(
            f"content/posts.json consolidation is invalid ({len(problems)} problem(s)):\n{detail}"
        )
    retired = set(consolidation_map(posts)) | set(
        pending_migrations(posts, static_redirects, pending))
    public = [p for p in posts if p["slug"] not in retired]
    consolidated = [p for p in posts if p["slug"] in retired]
    return public, consolidated


def public_posts(posts: List[dict],
                 static_redirects: Optional[Dict[str, str]] = None,
                 pending: Optional[Dict[str, str]] = None) -> List[dict]:
    return partition(posts, static_redirects, pending)[0]


def redirect_map(posts: List[dict],
                 static_redirects: Optional[Dict[str, str]] = None,
                 pending: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    """The complete slug → target map the edge and the internal-link
    canonicaliser both use: historical static redirects plus every
    consolidation derived from the records.

    Validated first, so a broken graph cannot reach `_redirects`.
    """
    partition(posts, static_redirects, pending)  # raises on an invalid graph
    merged = dict(_static(static_redirects))
    merged.update(consolidation_map(posts))     # metadata wins; collisions already rejected
    return merged


# ─── NEGATIVE FIXTURES ───────────────────────────────────────────────────────
# Run against validate_consolidation() and against every real consumer, so
# "they share a partition" is a tested property rather than a claim.

def _valid_fixture() -> List[dict]:
    def post(slug, **extra):
        return {"slug": slug, "title": slug, "description": "d", "hero": "h",
                "date": "2026-01-01", "category": "sms", "keywords": [],
                "sections": [["S", "body"]], "faq": [], **extra}
    return [
        post("fixture-surviving-guide"),
        post("fixture-archived-guide", consolidated_into="fixture-surviving-guide"),
        post("fixture-other-guide"),
    ]


def negative_fixtures() -> List[tuple]:
    """(description, posts, static_redirects) triples that MUST be rejected."""
    import copy

    def m(fn, static=None):
        return fn(copy.deepcopy(_valid_fixture())), (static or {})

    def edit(posts, slug, **fields):
        for p in posts:
            if p["slug"] == slug:
                p.update(fields)
        return posts

    def drop(posts, slug):
        return [p for p in posts if p["slug"] != slug]

    out = []
    d, s = m(lambda p: edit(p, "fixture-archived-guide", consolidated_into=""))
    out.append(("an empty consolidation target is rejected", d, s))
    d, s = m(lambda p: edit(p, "fixture-archived-guide",
                            consolidated_into="fixture-archived-guide"))
    out.append(("a self-referencing target is rejected", d, s))
    d, s = m(lambda p: edit(p, "fixture-archived-guide", consolidated_into="no-such-guide"))
    out.append(("a target that is not a source record is rejected", d, s))
    d, s = m(lambda p: drop(edit(p, "fixture-archived-guide",
                                 consolidated_into="fixture-other-guide"), "fixture-other-guide"))
    out.append(("a target removed from the corpus is rejected", d, s))
    d, s = m(lambda p: edit(p, "fixture-other-guide", consolidated_into="fixture-surviving-guide")
             and edit(p, "fixture-archived-guide", consolidated_into="fixture-other-guide"))
    out.append(("a two-hop chain is rejected", d, s))
    d, s = m(lambda p: edit(p, "fixture-surviving-guide",
                            consolidated_into="fixture-archived-guide"))
    out.append(("a two-node cycle is rejected", d, s))
    d, s = m(lambda p: p + [dict(p[1])])
    out.append(("a duplicate source slug is rejected", d, s))
    d, s = m(lambda p: p, {"fixture-surviving-guide": "some-other-guide"})
    out.append(("a target that is itself statically redirected is rejected", d, s))
    d, s = m(lambda p: p, {"fixture-archived-guide": "fixture-surviving-guide"})
    out.append(("a slug in BOTH the metadata and the static map is rejected, "
                "even when the targets agree", d, s))
    return out
