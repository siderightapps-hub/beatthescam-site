#!/usr/bin/env python3
"""Offline WP3C8B fixtures. Synthetic routes never enter the production canon.

No network, model, build, corpus writes or ignored-review dependencies. Expected
contract facts are independently stated below; mutation checks pin the reviewed
input, not a second operational policy table.
"""
import argparse
from collections import Counter
import copy
from dataclasses import replace
from html.parser import HTMLParser
import json
from pathlib import Path
import tempfile
from unittest.mock import patch

from reporting_fixture_review import packet_for
import canon
import content_gate as gate
import reporting_structured as sr
import build


def action(field="report_url", kind="url", **changes):
    template = {"url": "report-phishing-web", "email": "attach-email",
                "phone": "call-support", "shortcode": "forward-text"}[kind]
    from reporting_actions import TEMPLATES, V2_VERSION as VERSION
    atype, _, purpose, mode, conditions, _, _ = TEMPLATES[template]
    result = {"schema_version": VERSION, "eligibility_ids": ["existing-customer"] if kind == "phone" else [],
        "qualifier_ids": [], "action_type": atype, "purpose": purpose, "mode": mode,
        "jurisdictions": ["England", "Wales", "Scotland", "Northern Ireland"],
        "condition_ids": list(conditions),
        "instruction": {"kind": "fixed-destination", "template_id": template, "recipient_relation": "service-operator",
                        "channels": [{"field": field, "kind": kind}]},
        "limitation_ids": ["support-only"] if kind == "phone" else ["no-refund-promise"],
        "companions": [], "status": "active"}
    result.update(changes)
    return result


def fixture_canon():
    value = copy.deepcopy(canon.load_canon())
    # Keep the synthetic model/security cases independent of newly represented
    # real contracts. The confirmed-contract suites separately exercise their
    # exact real identities, collisions and signed eligibility boundaries.
    for group in sr._GROUPS:
        value[group] = [r for r in value.get(group, [])
                        if r['key'] not in ('o2-pay-monthly', 'o2-payg', 'own-bank')]
        for service in value[group]: service.pop('actions', None)
    value["verified_org_contacts"].append({"key": "fixture-service", "name": "Fixture Service",
        "brand": "Fixture Owner", "owner_id": "fixture-owner", "numbering_context": "GB", "report_url": "https://routes.example/report?a=one&b=two",
        "email": "evidence@routes.example", "phone": "01234 567890", "sms": "8999",
        "source_url": "https://routes.example/evidence", "checked_on": "2026-10-01",
        "actions": {"web": action(), "email": action("email", "email"),
                    "phone": action("phone", "phone"),
                    "text": action("sms", "shortcode")}})
    return value


def fixture_page():
    return {"slug": "structured-fixture", "title": "A suspicious message: safe next steps",
        "description": "Unexpected requests can create pressure and uncertainty. A familiar brand does not establish that a message is genuine.",
        "hero": "Pause and check the request before acting.", "date": "2026-10-09",
        "category": "email", "keywords": ["suspicious message"],
        "quick_answer": "An unexpected request can be fraudulent even when it names a familiar organisation. Pressure and secrecy are warning signs. Keep your account details private. A convincing appearance does not establish that a request is genuine.",
        "sections": [["Check safely", "Scammers use urgency to discourage independent checks. A familiar brand does not establish authenticity."]],
        "faq": [["What should I do first?", "Pause before acting. Do not send more money."]],
        "reporting_routes": ["fixture-service:web"]}


def review_for(page, c, allowed=None, *, approved_fields=None, **changes):
    # These are independently authored safe fixture strings, not permission
    # inferred from the candidate. Unknown/changed strings get NO approval.
    safe_fields = dict(sr.approval_fields(fixture_page()))
    safe_fields['intro'] = 'Check safely.'
    safe_fields.update(approved_fields or {})
    page_id = changes.get('page_id', 'guide:' + page['slug'] if 'slug' in page else 'hub:email')
    approvals = tuple(sr.ProseApproval(page_id, path, sr.prose_hash(text), sr.digest(page),
        sr.PROSE_APPROVAL_SCOPE, 'offline-fixture-reviewer', '2026-10-09T00:00:00Z', sr.digest(c))
        for path, text in sr.approval_fields(page) if safe_fields.get(path) == text)
    values = dict(canon_sha256=sr.digest(c), page_sha256=sr.digest(page),
        allowed_route_ids=tuple(allowed if allowed is not None else page["reporting_routes"]),
        reviewed_on="2026-10-09", citations=tuple(tuple(p) for p in page.get("sources_checked", [])),
        page_id=page_id, prose_approvals=approvals)
    values.update(changes)
    return sr.ReviewContext(**values)


class Links(HTMLParser):
    def __init__(self, text):
        super().__init__(); self.links = []; self.tags = []; self.feed(text)

    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)
        if tag == "a":
            self.links.append(dict(attrs).get("href"))


def run_cases():
    rows = []

    def check(name, group, fn):
        try:
            ok = bool(fn()); detail = "" if ok else "assertion false"
        except Exception as exc:
            ok, detail = False, f"{type(exc).__name__}: {exc}"
        rows.append({"name": name, "group": group, "ok": ok, "detail": detail})

    def rejects(fn):
        try:
            fn()
        except (sr.ReportingError, canon.CanonError):
            return True
        return False

    c = fixture_canon(); cat = canon.reporting_catalog(c); page = fixture_page()
    for route in ("fixture-service:web", "a:b", "a1-b2:c3-d4", "a" * 64 + ":" + "b" * 64):
        check("valid grammar " + route, "route_id", lambda route=route: sr.validate_route_id(route) == route)
    for route in (None, [], {}, 17, "", ":", "a", "a:b:c", "a:", ":b", "a--b:c", "A:b",
                  "a:B", " a:b", "a:b ", "a:\nb", "a:../b", "../a:b", "a:b/../c", "https://x.example/",
                  "a:b?next=x", "a:b#x", "a:b%20", "a:b;sh", "a:$(id)", "a:__x", "a:b_", "a:b\\c",
                  "a:é", "а:b", "a:b\u200b", "a" * 65 + ":b", "a:" + "b" * 65):
        check("reject grammar " + repr(route), "route_id", lambda route=route: rejects(lambda: sr.validate_route_id(route)))
    for route in ("missing:web", "fixture-service:unsupported", "fixture-service:WEB"):
        check("unknown action " + route, "route_id", lambda route=route: rejects(lambda: cat.resolve(route)))
    for ids in (None, "fixture-service:web", {}, ["fixture-service:web"] * 2, ["fixture-service:web"] * 33,
                [{"route_id": "fixture-service:web", "href": "https://evil.example"}]):
        check("invalid plan " + repr(ids), "route_id", lambda ids=ids: rejects(lambda: cat.select(ids)))
    check("exact resolution", "route_id", lambda: cat.resolve("fixture-service:web").owner == "Fixture Owner")
    check("order is canonical", "route_id", lambda: cat.select(["fixture-service:web", "fixture-service:email"])
          == cat.select(["fixture-service:email", "fixture-service:web"]))

    check("valid canon through common loader", "contract", lambda: not canon.validate_canon(c))
    legacy_only = copy.deepcopy(canon.load_canon())
    for group in sr._GROUPS:
        for service in legacy_only.get(group, []): service.pop('actions', None)
    check("legacy fields alone confer no actions", "contract", lambda: not canon.reporting_catalog(legacy_only).actions)
    check("frozen view cannot be assigned", "contract", lambda: _immutable(cat))
    for field, value in (("brand", "Attacker Owner"), ("report_url", "https://other.example/report")):
        changed = copy.deepcopy(c); changed["verified_org_contacts"][-1][field] = value
        check("review binding detects " + field, "contract",
              lambda changed=changed: rejects(lambda: canon.reporting_catalog(changed, expected_digest=sr.digest(c))))
    for field, value in (("purpose", "refund-request"), ("jurisdictions", ["Global"]),
                         ("channels", [{"field": "report_url", "kind": "email"}])):
        changed = copy.deepcopy(c); changed["verified_org_contacts"][-1]["actions"]["web"][field] = value
        check("review binding detects " + field, "contract",
              lambda changed=changed: rejects(lambda: canon.reporting_catalog(changed, expected_digest=sr.digest(c))))
    # State-independent malformed contracts fail even without an expected digest.
    mutations = [("purpose", ""), ("purpose", "BAD"), ("mode", "refund"), ("mode", []),
        ("jurisdictions", []), ("jurisdictions", ["Brazil"]), ("jurisdictions", ["Scotland", "Scotland"]),
        ("jurisdictions", ["Global", "Scotland"]), ("jurisdictions", [{}]),
        ("label", ""), ("label", " padded "), ("method", None), ("limitations", "none"),
        ("limitations", [""]), ("conditions", [{"kind": "nation", "value": "Brazil"}]),
        ("conditions", [{"kind": [], "value": "x"}]), ("conditions", [{"kind": "age", "value": "Adult", "override": True}]),
        ("companions", ["fixture-service:web"]), ("companions", ["missing:web"]),
        ("status", "pending"), ("channels", []), ("channels", [{"field": "email", "kind": "fax"}]),
        ("channels", [{"field": "report_url", "kind": []}]),
        ("channels", [{"field": "report_url", "kind": "url", "value": "https://evil.example"}]),
        ("channels", [{"field": "report_url", "kind": "url"}] * 2),
        ("checked_on", "2026-02-30"), ("checked_on", "2026-1-01"), ("source_url", "http://routes.example/evidence")]
    for field, value in mutations:
        changed = copy.deepcopy(c); changed["verified_org_contacts"][-1]["actions"]["web"][field] = value
        check("invalid contract " + field + repr(value), "contract",
              lambda changed=changed: rejects(lambda: canon.reporting_catalog(changed)))
    for field in sr._REQUIRED_ACTION:
        changed = copy.deepcopy(c); del changed["verified_org_contacts"][-1]["actions"]["web"][field]
        check("required action field " + field, "contract", lambda changed=changed: rejects(lambda: canon.reporting_catalog(changed)))
    for field in ("brand", "name", "source_url", "checked_on"):
        changed = copy.deepcopy(c); del changed["verified_org_contacts"][-1][field]
        check("required service field " + field, "contract", lambda changed=changed: rejects(lambda: canon.reporting_catalog(changed)))
    for where in ("action", "service"):
        changed = copy.deepcopy(c); target = changed["verified_org_contacts"][-1]
        if where == "action": target = target["actions"]["web"]
        target["destination_override"] = "https://evil.example"
        check("unknown " + where + " field", "contract", lambda changed=changed: rejects(lambda: canon.reporting_catalog(changed)))
    changed = copy.deepcopy(c); changed["official_routes"].append(copy.deepcopy(changed["verified_org_contacts"][-1]))
    check("cross-group service collision", "contract", lambda: rejects(lambda: canon.reporting_catalog(changed)))
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "canon.json"
        text = json.dumps(c).replace('"web": {', '"web": {}, "web": {', 1); path.write_text(text)
        check("duplicate JSON action key fails loader", "contract", lambda: rejects(lambda: canon.load_canon(path)))
    changed = copy.deepcopy(c); other = copy.deepcopy(changed["verified_org_contacts"][-1]); other["key"] = "imposter"; other["brand"] = "Wrong Owner"
    changed["verified_org_contacts"].append(other)
    check("duplicate destination owner conflict", "contract", lambda: rejects(lambda: canon.reporting_catalog(changed)))
    changed = copy.deepcopy(c); changed["verified_org_contacts"][-1]["actions"]["web"]["status"] = "withdrawn"
    withdrawn = canon.reporting_catalog(changed)
    check("withdrawn action cannot resolve", "contract", lambda: rejects(lambda: withdrawn.resolve("fixture-service:web")))
    changed = copy.deepcopy(c); r = changed["verified_org_contacts"][-1]; r["info_url"] = r["report_url"]; r["actions"]["web"]["instruction"]["channels"][0]["field"] = "info_url"
    check("information URL is not an intake", "contract", lambda: rejects(lambda: canon.reporting_catalog(changed)))
    r["actions"]["web"].update(action_type='open', purpose='site-verification', mode='navigation', condition_ids=[])
    r["actions"]["web"]['instruction']['template_id'] = 'open-verification'
    check("explicit navigation supported", "contract", lambda: canon.reporting_catalog(changed).resolve("fixture-service:web").mode == "navigation")

    # Current verified record represented explicitly IN MEMORY only. No values
    # or source dates are invented for the fourteen incomplete production records.
    converted = copy.deepcopy(canon.load_canon()); rf = converted["official_routes"][0]
    rf.update(owner_id='report-fraud', numbering_context='GB')
    rf["actions"] = {"fraud": action(action_type='report', purpose='police-report',
        jurisdictions=["England", "Wales", "Northern Ireland"], condition_ids=[],
        instruction={'kind':'fixed-destination','recipient_relation':'service-operator','template_id':'report-crime-web',
                     'channels':[{'field':'report_url','kind':'url'}]})}
    resolved = canon.reporting_catalog(converted).resolve("action-fraud:fraud")
    check("verified legacy record exact destination", "contract", lambda: resolved.channels == (
        sr.Destination("url", "https://www.reportfraud.police.uk"),))
    check("verified legacy record owner purpose scope", "contract", lambda: (resolved.owner, resolved.purpose, resolved.jurisdictions)
          == ("Report Fraud", "police-report", ("England", "Wales", "Northern Ireland")))
    check("verified legacy record evidence unchanged", "contract", lambda: (resolved.source_url, resolved.checked_on)
          == ("https://www.reportfraud.police.uk/reporting-a-fraud/", "2026-10-05"))

    ids = ["fixture-service:" + key for key in ("web", "email", "phone", "text")]
    rendered = sr.render_block(cat, ids); parsed = Links(rendered)
    for expected in ("https://routes.example/report?a=one&b=two", "mailto:evidence@routes.example", "tel:01234567890"):
        check("exact renderer target " + expected, "renderer", lambda expected=expected: expected in parsed.links)
    for text in ("8999", "Fixture Owner", "Report the suspicious email", "Scotland", "Northern Ireland",
                 "This service does not promise a refund.", "Attach the original suspicious email", "For existing customers"):
        check("visible qualification " + text, "renderer", lambda text=text: text in rendered)
    check("shortcode is not an automatic send link", "renderer", lambda: not any(x.startswith("sms:") for x in parsed.links))
    check("accessible reporting heading", "renderer", lambda: 'aria-labelledby="reporting-routes-heading"' in rendered)
    check("deterministic complete block", "renderer", lambda: rendered == sr.render_block(cat, list(reversed(ids))))
    check("plain projection retains scope method limitations", "renderer", lambda: all(x in sr.render_plain(cat, ids)
          for x in ("Scotland", "Attach the original suspicious email", "refund", "8999")))
    for bad in (["unknown:route"], ["fixture-service:web"] * 2):
        check("renderer rejects invalid plan " + repr(bad), "renderer", lambda bad=bad: rejects(lambda: sr.render_block(cat, bad)))
    changed = copy.deepcopy(c); changed["verified_org_contacts"][-1]["name"] = '<img src=x onerror="alert(1)"> & "label"'
    escaped = sr.render_block(canon.reporting_catalog(changed), ["fixture-service:web"])
    check("malicious display text escaped", "renderer", lambda: "img" not in Links(escaped).tags and '&lt;img' in escaped and '&quot;' in escaped)
    check("query ampersand is attribute escaped", "renderer", lambda: "a=one&amp;b=two" in rendered)

    review = review_for(page, c)
    check("valid structured article", "article", lambda: sr.validate_page(page, cat, review) == cat.select(page["reporting_routes"]))
    check("structured gate valid fixture", "article", lambda: not any(i['severity'] == 'block' for i in gate.check_deterministic(
        page, reporting_canon=c, reporting_review=review)))
    for key, value in (("reporting_routes", None), ("reporting_routes", []), ("reporting_routes", ["missing:web"]),
                       ("reporting_routes", ["fixture-service:web", "fixture-service:web"]),
                       ("reporting_routes", [{"route_id": "fixture-service:web", "owner": "Other"}]),
                       ("href", "https://evil.example"), ("owner", "Other"), ("purpose", "refund-request"),
                       ("jurisdiction", "Brazil"), ("reporting_label", "Other service"), ("legacy", True),
                       ("reporting_mode", sr.LEGACY_DIAGNOSTIC)):
        changed = copy.deepcopy(page); changed[key] = value
        # The review cannot rescue invalid schema, even if the page hash matches.
        ctx = review_for(changed, c, allowed=page['reporting_routes'])
        check("invalid article " + key + repr(value), "article", lambda changed=changed, ctx=ctx: rejects(lambda: sr.validate_page(changed, cat, ctx)))
    check("missing review fails", "article", lambda: rejects(lambda: sr.validate_page(page, cat, None)))
    changed = copy.deepcopy(page); changed['title'] += " Changed"
    check("review invalidated by ordinary title edit", "article", lambda: rejects(lambda: sr.validate_page(changed, cat, review)))
    for ctx in (replace(review, canon_sha256='0' * 64), replace(review, page_sha256='0' * 64),
                replace(review, allowed_route_ids=("fixture-service:email",)),
                replace(review, reviewed_on="2027-02-01"), replace(review, reviewed_on="2026-09-30")):
        check("review context mutation " + repr(ctx), "article", lambda ctx=ctx: rejects(lambda: sr.validate_page(page, cat, ctx)))
    changed = copy.deepcopy(page); changed['reporting_routes'] = []
    check("reviewed empty plan", "article", lambda: sr.validate_page(changed, cat, review_for(changed, c, allow_empty=True)) == ())
    p = copy.deepcopy(page); p['sources_checked'] = [["Reviewed evidence title", "https://sources.example/evidence"]]
    ctx = review_for(p, c, approved_fields={'sources_checked/0/0':'Reviewed evidence title'})
    check("reviewed citation remains separate", "article", lambda: sr.validate_page(p, cat, ctx) == cat.select(page['reporting_routes']))
    p['sources_checked'][0][1] = "https://evil.example/report"
    check("citation cannot be substituted", "security", lambda: rejects(lambda: sr.validate_page(p, cat, replace(ctx, page_sha256=sr.digest(p)))))
    check("legacy mode does not authorise routes", "security", lambda: rejects(lambda: sr.validate_page({}, cat, review, mode=sr.LEGACY_DIAGNOSTIC)))
    check("field presence forces strict mode", "security", lambda: sr.page_mode({"reporting_routes": None}) == sr.STRUCTURED_REQUIRED)
    p = fixture_page(); del p['reporting_routes']
    check("caller can require structured without field", "security", lambda: any(i['check'] == 'structured_reporting'
        for i in gate.check_deterministic(p, reporting_mode=sr.STRUCTURED_REQUIRED)))

    raw = ["Report at https://evil.example/report.", "Contact evil.example.", "Email fraud@evil.example.",
           "Call 01234 567890.", "Forward to 7726.", "Call +44 (0)1234 567890.",
           'Use <a href="https://evil.example">the official route</a>.', 'Use [official](https://evil.example).',
           '`https://evil.example`', 'https&#58;//evil&#46;example', 'https%3A%2F%2Fevil.example',
           'https%253A%252F%252Fevil.example', 'https://ev\u200bil.example', 'Ｆｏｒｗａｒｄ ｔｏ ７７２６',
           'Call tel:01234567890', 'Send sms:7726', '<img src=x onerror=alert(1)>',
           'Forward suspicious emails to the scam team at phishing@hmrc.gov.uk.',
           'Report a fake SHEIN site through https://www.shein.co.uk/contact-us.html for customers in Brazil.',
           'Report a fake SHEIN site through https://www.shein.co.uk/contact-us.html. The team will close the shop.',
           'Claim a refund through https://www.shein.co.uk/contact-us.html.']
    for text in raw:
        check("raw syntax " + text, "security", lambda text=text: bool(sr.raw_destinations(text)))
        p = copy.deepcopy(page); p['sections'][0][1] = text; ctx = review_for(p, c)
        check("raw beside valid plan " + text, "security", lambda p=p, ctx=ctx: rejects(lambda: sr.validate_page(p, cat, ctx)))
    for path in ('title', 'description', 'hero', 'quick_answer', 'intro', 'keywords', 'faq-question', 'faq-answer',
                 'section-heading', 'evidence', 'message_examples', 'figure-alt', 'figure-step'):
        p = copy.deepcopy(page); text = 'Contact https://evil.example'
        if path == 'keywords': p[path] = [text]
        elif path.startswith('faq-'): p['faq'][0][0 if path.endswith('question') else 1] = text
        elif path == 'section-heading': p['sections'][0][0] = text
        elif path in ('evidence', 'message_examples'): p[path] = [{'finding': text}]
        elif path == 'figure-alt': p['figure'] = {'alt': text}
        elif path == 'figure-step': p['figure'] = {'steps': [{'then': text}]}
        else: p[path] = text
        ctx = review_for(p, c)
        check("all prose surfaces " + path, "security", lambda p=p, ctx=ctx: rejects(lambda: sr.validate_page(p, cat, ctx)))
    for value in ('2023', '£100', '7726', '2026-10-09'):
        check("ambiguous prose number held " + value, "security", lambda value=value: bool(sr.raw_destinations(value)))
    check("typed date metadata allowed", "article", lambda: sr.validate_page(page, cat, review) is not None)
    for field, value in [('evidence', [{'finding': 7726}]), ('message_examples', [{'message': 7726}]),
                         ('evidence', [{'finding': {'https://evil.example': 'Send evidence'}}]),
                         ('figure', {'alt': 7726}), ('figure', {'steps': [{'then': 7726}]}),
                         ('title', 7726), ('hero', ['Safe text']), ('keywords', [7726]),
                         ('message_examples', [{'assessment': {'owner': 'Wrong service'}}])]:
        p = copy.deepcopy(page); p[field] = value; ctx = review_for(p, c)
        check('no renderer coercion bypass ' + field + repr(value), 'security',
              lambda p=p, ctx=ctx: rejects(lambda: sr.validate_page(p, cat, ctx)))
    p = copy.deepcopy(page); p['evidence'] = [{'signal': 'Unexpected request', 'finding': 'Check independently.', 'basis': 'Reviewed source'}]
    p['message_examples'] = [{'label': 'Illustrative message', 'message': 'Unexpected requests can create pressure and uncertainty.', 'assessment': 'Pressure is a warning sign.'}]
    check('valid string evidence and examples', 'article', lambda: bool(sr.validate_page(p, cat, review_for(p, c,
        approved_fields={'evidence/0/signal':'Unexpected request', 'evidence/0/finding':'Check independently.',
            'evidence/0/basis':'Reviewed source', 'message_examples/0/label':'Illustrative message',
            'message_examples/0/message':'Unexpected requests can create pressure and uncertainty.', 'message_examples/0/assessment':'Pressure is a warning sign.'}))))
    command_example = copy.deepcopy(p)
    command_example['message_examples'][0]['message'] = 'Please pay now.'
    check('reviewed example is not an imperative exemption', 'security', lambda: rejects(lambda:
        sr.validate_page(command_example, cat, review_for(command_example, c,
            approved_fields=dict(sr.approval_fields(command_example))))))
    check("destination-free advice allowed", "article", lambda: not sr.raw_destinations('Contact your bank through its official app.'))
    check("internal Markdown link allowed", "article", lambda: not sr.raw_destinations('[Recovery](/recovery/)'))
    for url in ('https://user@routes.example/report', 'https://routes.example:443/report', 'http://routes.example/',
                'javascript:alert(1)', '//routes.example', 'https://', 'https://routes.example\\@evil.example',
                'https://routes.example/%0afoo', 'https://routes.example/%2e%2e/report',
                'https://routes.example/#report', 'https://routes.example/%XX', 'https://routes.example/\" onmouseover=\"x',
                'https://routes.example./', 'https://ROUTES.example/'):
        changed = copy.deepcopy(c); changed['verified_org_contacts'][-1]['report_url'] = url
        check("unsafe canon URL " + url, "security", lambda changed=changed: rejects(lambda: canon.reporting_catalog(changed)))
    for field, value in (('email', 'a@routes.example?subject=x'), ('email', 'a@routes.example\nBcc:x@evil.example'),
                         ('email', 'a@-routes.example'), ('email', 'a@routes-.example'),
                         ('phone', '01234" onclick="x'), ('phone', '01234 ((567890'), ('sms', '77 26')):
        changed = copy.deepcopy(c); changed['verified_org_contacts'][-1][field] = value
        check("unsafe canon contact " + field + repr(value), "security", lambda changed=changed: rejects(lambda: canon.reporting_catalog(changed)))
    # Prove structural trust is independent of every legacy destination parser.
    legacy_names = ['check_phones', 'check_shortcodes', 'check_report_mailboxes', 'check_sources',
                    'check_scotland_routing', 'check_nation_consumer_routing', 'check_ncsc_route_scope',
                    'check_report_fraud_destinations', '_route_instruction', '_route_fields', '_route_text']
    from contextlib import ExitStack
    with ExitStack() as stack:
        mocks = [stack.enter_context(patch.object(gate, name, side_effect=AssertionError('legacy trust called')))
                 for name in legacy_names]
        mocks.append(stack.enter_context(patch.object(gate.reporting, 'authorize', side_effect=AssertionError('legacy trust called'))))
        # Canary: demonstrate that the mocks really are installed at this point.
        try:
            gate.reporting.authorize(None, None)
        except AssertionError:
            pass
        else:
            raise AssertionError('legacy isolation canary was not active')
        for mock in mocks: mock.reset_mock()
        check("structured gate never calls prose authorisers", "security", lambda: not any(i['severity'] == 'block'
              for i in gate.check_deterministic(page, reporting_canon=c, reporting_review=review))
              and all(mock.call_count == 0 for mock in mocks))

    # Mutate every selected contract, not only the example web route. Every
    # well-formed change still needs a new independent reviewed canon binding.
    for local in ('web', 'email', 'phone', 'text'):
        for field, value in [('purpose', 'refund-request'), ('jurisdictions', ['Global']),
                             ('method', 'A different submission method.'), ('conditions', []),
                             ('limitations', []), ('label', 'Impersonated service')]:
            changed = copy.deepcopy(c); changed['verified_org_contacts'][-1]['actions'][local][field] = value
            check(f"reviewed action mutation {local}/{field}", "security",
                  lambda changed=changed: rejects(lambda: canon.reporting_catalog(changed, expected_digest=sr.digest(c))))

    conditional = copy.deepcopy(c)
    pair = ['fixture-ewni:fraud', 'fixture-scotland:fraud']
    for name, nations, other in [('fixture-ewni', ['England', 'Wales', 'Northern Ireland'], 'fixture-scotland'),
                                 ('fixture-scotland', ['Scotland'], 'fixture-ewni')]:
        conditional['verified_org_contacts'].append({'key': name, 'owner_id': name, 'brand': name, 'name': name,
            'report_url': 'https://police.example/intake', 'source_url': 'https://police.example/evidence', 'checked_on': '2026-10-01',
            'actions': {'fraud': action(action_type='report', purpose='police-report', jurisdictions=nations,
                companions=[other + ':fraud'], condition_ids=[], instruction={'kind':'fixed-destination','recipient_relation':'service-operator',
                'template_id':'report-crime-web','channels':[{'field':'report_url','kind':'url'}]})}})
    conditional['destination_relationships'] = [{'id':'national-intake', 'type':'geographic-routing',
        'operator_owner_id':'fixture-ewni', 'attribution_id':'operated-by', 'members':[{'route_id':x['key']+':fraud','owner_id':x['owner_id'],
        'purpose':'police-report','jurisdictions':x['actions']['fraud']['jurisdictions'],
        'destination_field':'report_url','destination_identity':['url','police.example','/intake',False,'']}
        for x in conditional['verified_org_contacts'][-2:]], 'source_url':'https://police.example/evidence',
        'checked_on':'2026-10-01','status':'active'}]
    cc = canon.reporting_catalog(conditional)
    check("explicit evidenced national sharing", "contract", lambda: len(cc.select(pair)) == 2)
    check("missing national companion rejected", "security", lambda: rejects(lambda: cc.select(pair[:1])))
    check("both national scopes visible", "renderer", lambda: all(n in sr.render_block(cc, pair) for n in sr._NATIONS[:-1]))
    for age in ('adult', 'minor'):
        modified = copy.deepcopy(c); modified['verified_org_contacts'][-1]['actions']['web']['condition_ids'].append(age)
        check("unsupported age on phishing contract rejected " + age, "renderer", lambda modified=modified: rejects(lambda: canon.reporting_catalog(modified)))
    contract = sr.generator_contract(cat, ['fixture-service:web'])
    check("generator receives IDs not destinations", "generator", lambda: contract['allowed_reporting_routes'] == ['fixture-service:web']
          and 'routes.example' not in json.dumps(contract))
    check("generator unknown allow-list entry denied", "generator", lambda: rejects(lambda: sr.generator_contract(cat, ['unknown:web'])))
    p = copy.deepcopy(page); p['reporting_routes'] = ['fixture-service:email']
    ctx = review_for(p, c, allowed=['fixture-service:web'])
    check("known but unapproved generated ID quarantines", "generator", lambda: not gate.run_gate(p,
        reporting_canon=c, reporting_review=packet_for(p, c, ctx)).passed)
    p['reporting_routes'] = ['invented:route']; ctx = review_for(p, c, allowed=['fixture-service:web'])
    check("invented generated ID quarantines", "generator", lambda: not gate.run_gate(p,
        reporting_canon=c, reporting_review=packet_for(p, c, ctx)).passed)
    check("route integrity never claims publication ready", "generator", lambda: gate.run_gate(page,
        reporting_canon=c, reporting_review=packet_for(page, c, review)).publication_ready is False)

    site = json.loads((build.ROOT / 'content/site.json').read_text())
    rendered_page = build.render_post(site, page, [page], sources=c, reporting_review=packet_for(page, c, review))
    check("guide integrates complete block once", "renderer", lambda: rendered_page.count('id="reporting-routes"') == 1)
    check("guide block between quick answer and main prose", "renderer", lambda: rendered_page.index('id="reporting-routes"')
          > rendered_page.index('class="quick-answer"') and rendered_page.index('id="reporting-routes"') < rendered_page.index('id="check-safely"'))
    check("guide has no unselected legacy reporting destination", "renderer", lambda: 'mailto:report@phishing.gov.uk' not in rendered_page
          and 'tel:03001232040' not in rendered_page)
    check("renderer requires review independently", "security", lambda: rejects(lambda: build.render_post(site, page, [page], sources=c)))
    p = copy.deepcopy(page); p['reporting_routes'] = ['unknown:web']
    check("renderer unknown ID independently fails", "security", lambda: rejects(lambda: build.render_post(site, p, [p], sources=c, reporting_review=packet_for(p, c, review))))
    hub = {k: copy.deepcopy(page[k]) for k in ('title', 'description', 'sections', 'faq', 'reporting_routes')}
    hub['intro'] = 'Pause and check the message.'; hub['sources_checked'] = [['Evidence', 'https://routes.example/evidence']]
    hr = review_for(hub, c, approved_fields={'intro':'Pause and check the message.',
                                          'sources_checked/0/0':'Evidence'})
    check("hub schema accepts structured fixture", "article", lambda: build.validate_category_hubs({'email': hub},
        reporting_sources=c, reporting_reviews={'email': packet_for(hub, c, hr)}) is None)
    hub_html = build.render_category_page(site, 'email', [], hub=hub, reporting_sources=c, reporting_review=packet_for(hub, c, hr))
    check("hub integrates complete block once", "renderer", lambda: hub_html.count('id="reporting-routes"') == 1)
    check("hub renderer fails without reviewed context", "security", lambda: rejects(lambda: build.render_category_page(site, 'email', [], hub=hub, reporting_sources=c)))
    return rows


def _immutable(catalog):
    try:
        catalog.actions['fake:route'] = None
    except TypeError:
        return True
    return False


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--json', type=Path); args = parser.parse_args()
    rows = run_cases()
    if args.json: args.json.write_text(json.dumps(rows, indent=2, ensure_ascii=False) + '\n')
    groups = sorted({r['group'] for r in rows})
    for group in groups:
        subset = [r for r in rows if r['group'] == group]
        print(f"{group}: {sum(r['ok'] for r in subset)}/{len(subset)} PASS")
    for r in rows:
        if not r['ok']: print(f"FAIL [{r['group']}] {r['name']}: {r['detail']}")
    print(f"Structured reporting: {sum(r['ok'] for r in rows)} PASS / {sum(not r['ok'] for r in rows)} FAIL")
    return int(any(not r['ok'] for r in rows))


if __name__ == '__main__':
    raise SystemExit(main())
