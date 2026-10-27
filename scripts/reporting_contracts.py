"""Destination-first reporting authorization. No prose or caller can add trust.

The adapter supplies a Request; authorization is an exact relation over a
normalized destination, owner, purpose and jurisdiction. Values come only from
sources.json. Policy below scopes those existing values; it admits no new URL,
mailbox or phone. Missing policy, unresolved scope and unsupported combinations
are denials. This module has no model/network dependency.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from urllib.parse import urlsplit


UK = frozenset({'england', 'wales', 'scotland', 'ni'})
GB = UK - {'ni'}
EW = frozenset({'england', 'wales'})


@dataclass(frozen=True)
class Destination:
    kind: str
    canonical_value: str
    host: str = ''
    path: str = ''


def normalize(kind, value):
    """Reject ambiguous syntax rather than repairing it into a trusted value."""
    if kind in ('url', 'link'):
        if kind == 'link' and not value.lower().startswith('https://'):
            return None
        if re.search(r'[\\\s%]', value):
            return None
        try:
            p = urlsplit(value if '://' in value else 'https://' + value)
            host = (p.hostname or '').lower().removesuffix('.')
            host = host.removeprefix('www.')
            if (p.scheme.lower() != 'https' or '@' in p.netloc or ':' in p.netloc
                    or '?' in value or '#' in value
                    or not re.fullmatch(r'[a-z0-9-]+(?:\.[a-z0-9-]+)+', host)):
                return None
            path = p.path.rstrip('/')
            return Destination('url', 'https://' + host + path, host, path)
        except ValueError:
            return None
    if kind == 'email':
        # Do not consume one half of a malformed double-@ address. No plus-tag
        # removal, local-part rewriting, Unicode mapping or domain suffix trust.
        if not re.fullmatch(r'[A-Za-z0-9.!#$&*+/=?^_`{|}~-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+', value):
            return None
        return Destination('email', value.lower(), value.rsplit('@', 1)[1].lower())
    if kind in ('phone', 'shortcode'):
        if not re.fullmatch(r'(?:\+44\s*|0)?[0-9 ()-]+', value):
            return None
        digits = re.sub(r'\D', '', value)
        if value.startswith('+44'):
            digits = '0' + digits[2:]
        if len(digits) not in (3, 4, 5, 6, 10, 11):
            return None
        return Destination('shortcode' if len(digits) <= 6 else 'phone', digits)
    return None


@dataclass(frozen=True)
class ServiceContract:
    service: str
    organisation: str
    destinations: frozenset
    purposes: frozenset
    jurisdictions: frozenset
    global_scope: bool = False
    mode: str = 'intake'


@dataclass(frozen=True)
class Request:
    destination: Destination | None
    # None means genuinely unnamed. An unresolved/ambiguous explicit recipient
    # is the literal 'unknown', never None. Multiple recipients are ambiguous.
    organisations: frozenset | None
    purposes: frozenset
    jurisdictions: frozenset = frozenset()
    mode: str = 'intake'


def authorize(request, contracts):
    """Return (allowed, reason, matching services); no successful-first shortcut.

    All dimensions must be satisfied by ONE contract; membership in separate
    canon records cannot be combined into a fictitious capability.
    """
    if request.destination is None:
        return False, 'invalid-destination', ()
    exact = [c for c in contracts if request.destination in c.destinations]
    if not exact:
        return False, 'unverified-destination', ()
    if request.organisations is not None:
        if len(request.organisations) != 1 or 'unknown' in request.organisations:
            return False, 'unresolved-owner', ()
        exact = [c for c in exact if c.organisation in request.organisations]
        if not exact:
            return False, 'owner-mismatch', ()
    exact = [c for c in exact if c.mode == request.mode]
    if not exact:
        return False, 'service-mode-mismatch', ()
    if not request.purposes or 'unknown' in request.purposes:
        return False, 'unresolved-purpose', ()
    exact = [c for c in exact if request.purposes <= c.purposes]
    if not exact:
        return False, 'purpose-mismatch', ()
    if 'unknown' in request.jurisdictions:
        return False, 'unresolved-jurisdiction', ()
    exact = [c for c in exact if c.global_scope or request.jurisdictions <= c.jurisdictions]
    if not exact:
        return False, 'jurisdiction-mismatch', ()
    return True, 'supported-contract', tuple(c.service for c in exact)


# Closed policies derived from the existing canon's roles, notes and nation
# fields. These are capabilities, not lexical patterns. No implicit fallback
# based on key suffix, organisation name or a trusted government domain exists.
# These real services have only restricted v2 action contracts. The legacy
# prose adapter cannot express their network/plan or relative-recipient
# conditions, so it deliberately derives NO destination capability. Keep
# unknown keys fatal; never infer permission from the presence of actions.
STRUCTURED_ONLY_SERVICES = frozenset({'o2-pay-monthly', 'o2-payg', 'own-bank'})

POLICIES = {
    'action-fraud': ('Report Fraud', 'crime email text call website message social-impersonation property-fraud', UK - {'scotland'}),
    'police-scotland': ('Police Scotland', 'crime email text call website message social-impersonation property-fraud', frozenset({'scotland'})),
    'ncsc-sers': ('NCSC', 'email', UK),
    'ncsc-scam-website': ('NCSC', 'website', UK),
    'citizens-advice': ('Citizens Advice', 'consumer-advice', EW),
    'advice-direct-scotland': ('Advice Direct Scotland', 'consumer-advice', frozenset({'scotland'})),
    'advice-direct-scotland-consumeradvice': ('Advice Direct Scotland', 'consumer-advice', frozenset({'scotland'})),
    'consumerline-ni': ('Consumerline', 'consumer-advice', frozenset({'ni'})),
    'fca-firm-checker': ('FCA', 'financial-conduct', UK),
    'report-spam-sms': ('mobile networks', 'text', UK),
    'stop-scams-159': ('your bank', 'bank-contact', UK),
    'gas-emergency': ('National Gas Emergency Service', 'gas-emergency', GB),
    'power-cut-105': ('electricity network', 'power-emergency', GB),
    'police-101': ('police', 'crime email text call website message social-impersonation property-fraud', UK),
    'emergency-999': ('emergency services', 'emergency', UK),
    'emergency-112': ('emergency services', 'emergency', UK),
    'revenge-porn-helpline': ('Revenge Porn Helpline', 'image-abuse', UK),
    'companies-house-enquiries': ('Companies House', 'company-enquiry', UK),
    'victim-support': ('Victim Support', 'victim-support', EW),
    'talktalk': ('TalkTalk', 'account-support', UK),
    'universal-credit-gb': ('Universal Credit', 'own-claim', GB),
    'universal-credit-ni': ('Universal Credit', 'own-claim', frozenset({'ni'})),
    'mhra-online-seller': ('MHRA', 'medicine-seller', UK),
    'mhra-yellow-card': ('MHRA', 'medicine-safety', UK),
    'hmrc-phishing': ('HMRC', 'email text', UK),
    'natwest-scam-texts': ('NatWest', 'text', UK),
    'hsbc-phishing': ('HSBC', 'email text', UK),
    'santander-phishing': ('Santander', 'email', UK),
    'santander-smishing': ('Santander', 'text', UK),
    'natwest-phishing': ('NatWest', 'email', UK),
    'nationwide-phishing': ('Nationwide', 'email text message', UK),
    'tsb-emailscams': ('TSB', 'email text', UK),
    'amazon-reportascam': ('Amazon', 'email text message call impersonation', UK),
    'royalmail-reportascam': ('Royal Mail', 'email text call website', UK),
    'paypal-phishing': ('PayPal', 'email', UK),
    'apple-reportphishing': ('Apple', 'email text', UK),
    'ee-phishing': ('EE', 'email text message', UK),
    'vodafone-phishing': ('Vodafone', 'email text message', UK),
    'virginmedia-phishing': ('Virgin Media', 'email', UK),
    'talktalk-phishing': ('TalkTalk', 'email', UK),
    'britishgas-phishing': ('British Gas', 'email text', UK),
    'netflix-phishing': ('Netflix', 'email text', UK),
    'slc-fcpu-alerts': ('Student Loans Company', 'email text', UK),
    'yodel-infosec': ('Yodel', 'email', UK),
    'microsoft-phish': ('Microsoft', 'email', UK),
    'depop-reportphishing': ('Depop', 'email', UK),
    'revolut-support': ('Revolut', 'app-inaccessible', UK),
    'ups-fraud': ('UPS', 'email text call message', UK),
    'microsoft-support-scam': ('Microsoft', 'support-scam', UK),
    'hmrc-phone-scam': ('HMRC', 'call', UK),
    'ebay-phishing': ('eBay', 'email call', UK),
    'depop-support': ('Depop', 'platform-account', UK),
    'pandora-brand-protection': ('Pandora', 'counterfeit', UK),
    'hmrc-branddefence': ('HMRC', 'social-impersonation', UK),
    'shein-uk-scam-notification': ('SHEIN', 'brand-scam-notification', UK),
}


def contracts_from_canon(canon):
    contracts = []
    routes = canon['official_routes'] + canon.get('verified_org_contacts', [])
    for r in routes:
        key = r['key']
        if key in STRUCTURED_ONLY_SERVICES:
            continue  # Explicit denial in this legacy authorization domain.
        if key not in POLICIES:
            raise ValueError('Missing reporting service contract: ' + key)
        owner, purposes, nations = POLICIES[key]
        # A change in a declared jurisdiction is never silently ignored. The
        # declaration can narrow a policy, but cannot widen its reviewed scope.
        declared = jurisdiction(r.get('nation', ''))
        if declared and not declared <= nations and 'Global' not in r.get('nation', ''):
            raise ValueError('Canon/policy jurisdiction disagreement: ' + key)
        for field, kind in (('report_url', 'url'), ('info_url', 'url'), ('email', 'email'),
                            ('phone', 'phone'), ('phone_welsh', 'phone'), ('sms', 'shortcode')):
            if not r.get(field):
                continue
            d = normalize(kind, r[field])
            if d is None:
                raise ValueError('Malformed canonical destination: ' + key + '/' + field)
            scoped = frozenset(purposes.split())
            if key == 'hmrc-phishing':
                scoped = frozenset({'text' if field == 'sms' else 'email'})
            contracts.append(ServiceContract(key, owner.casefold(), frozenset({d}), scoped,
                                             frozenset(declared or nations), r.get('nation', '').startswith('Global')))
    owned = {d.canonical_value for c in contracts for d in c.destinations if d.kind == 'email'}
    # These two existing canon mailboxes predate service records. Give them
    # explicit contracts, without admitting any new address or domain wildcard.
    legacy = {'companieshouse.gov.uk': ('Companies House', 'email'),
              'landregistry.gov.uk': ('HM Land Registry', 'property-fraud')}
    for value in canon['report_emails']:
        d = normalize('email', value)
        if d is None:
            raise ValueError('Malformed canonical mailbox')
        if d.canonical_value in owned:
            continue
        if d.host not in legacy:
            raise ValueError('Unowned canonical mailbox: ' + value)
        owner, purpose = legacy[d.host]
        contracts.append(ServiceContract('legacy-' + d.host, owner.casefold(), frozenset({d}),
                                         frozenset({purpose}), UK))
    for r in canon.get('verified_number_sources', []):
        if r['purpose'] != 'fraud-phone-lookup':
            raise ValueError('Unknown number source capability')
        d = normalize('url', r['navigation_url'])
        if d is None:
            raise ValueError('Malformed number source')
        contracts.append(ServiceContract(r['key'], r['brand'].casefold(), frozenset({d}),
                                         frozenset({'number-lookup'}), UK, mode='number-lookup'))
    return tuple(contracts)


def jurisdiction(text):
    """Closed UK places plus explicit foreign scope, never an audience noun list.

    The adapter supplies the local condition or a bounded inherited condition.
    An unrecognized explicit location is retained as outside verified UK scope.
    """
    result = set()
    text = re.sub(r'\bnot\s+(?:a\s+)?(?:global|worldwide|international)\b', '', text, flags=re.I)
    places = ((r'Northern\s+Ireland|\bNI\b', {'ni'}),
              (r'United\s+Kingdom|\bUK\b', UK),
              (r'Great\s+Britain|\bGB\b|\bBritain\b', GB),
              (r'England|English', {'england'}), (r'Wales|Welsh', {'wales'}),
              (r'Scotland|Scottish|Scots', {'scotland'}))
    remainder = text
    for pattern, nations in places:
        if re.search(r'\b(?:' + pattern + r')\b', text, re.I):
            result.update(nations)
        remainder = re.sub(r'\b(?:' + pattern + r')\b', ' UKPLACE ', remainder, flags=re.I)
    if re.search(r'\b(?:global|worldwide|international|overseas|outside|all\s+countries|any\s+country)\b', remainder, re.I):
        result.add('foreign')
    # in/from/of a named place, irrespective of shoppers/readers/residents/etc.
    for m in re.finditer(r'\b(?:in|from|of)\s+(?:the\s+)?([A-Za-z]+)', remainder, re.I):
        if m.group(1).strip().upper() != 'UKPLACE':
            # Organisations are not places. Only location-bearing clauses or
            # an initial "In PLACE" are passed as conditions by the adapter.
            result.add('foreign')
    return frozenset(result)


def purposes(text):
    """Parse the asserted object into capabilities, independent of destination.

    Specific objects take precedence over generic scam/report nouns. Financial
    redress, third-party benefit allegations and unspecified objects never
    acquire notification capability merely by mentioning a scam as well.
    """
    text = re.sub(r'\bemailed\s+version\b', 'email', text, flags=re.I)
    text = re.sub(r'\b(?:tax\s+refund|refund)\s+scam\b', 'phishing scam', text, flags=re.I)
    has = lambda pattern: bool(re.search(pattern, text, re.I))
    if has(r'\b(?:refund|reimbursement|compensation|chargeback)\b|\b(?:money|payment|funds?)\s+back\b|\b(?:recover|claim)\s+(?:your\s+)?(?:money|payment|funds?)\b'):
        return frozenset({'redress'})
    if has(r'\b(?:social[- ]media\s+accounts?|social[- ]media\s+impersonation)\b'):
        return frozenset({'social-impersonation'})
    if has(r'\bUniversal\s+Credit\b'):
        return frozenset({'own-claim' if has(r'\b(?:your|my|own)\s+(?:Universal\s+Credit\s+)?(?:claim|account)\b') and not has(r'\b(?:someone\s+else|another\s+(?:person|claimant)|neighbour)\b') else 'unknown'})
    if has(r'\b(?:fake|fraudulent|phishing|scam)\s+SHEIN\s+(?:sites?|websites?|shops?|stores?|messages?|emails?|accounts?)\b|\bSHEIN(?:[- ]related)?\s+(?:scams?|fraud|phishing|impersonation|fake\s+(?:sites?|websites?))\b|\b(?:scams?|fraud|phishing)\s+(?:involving|about)\s+SHEIN\b|\b(?:impersonat(?:es|ed|ing)|impersonation\s+of|pretending\s+to\s+be|posing\s+as)\s+SHEIN\b'):
        # The object must be the incident, not an unrelated request about it.
        if has(r'\b(?:order|password|return|delay|authenticate|verify|takedown)\b'):
            return frozenset({'unknown'})
        return frozenset({'brand-scam-notification'})
    if has(r'\bmedicines?|medical[- ]devices?\b'):
        if has(r'\b(?:sellers?|sales|selling)\b'):
            return frozenset({'medicine-seller'})
        if has(r'\bmedicines?\b') and has(r'\b(?:counterfeit|falsified|defective|adverse|side[- ]effects?|reaction|unsafe|safety)\b'):
            return frozenset({'medicine-safety'})
        return frozenset({'unknown'})
    if has(r'\b(?:counterfeits?|fake\s+(?:sites?|websites?|sellers?))\b') and has(r'\bPandora\b'):
        return frozenset({'counterfeit'})
    if has(r'\b(?:tech(?:nical)?[- ]support|support[- ]scams?)\b'):
        return frozenset({'support-scam'})
    if has(r'\bDepop\b') and has(r'\b(?:seller|buyer|listing|profile|transaction|account)s?\b'):
        return frozenset({'platform-account'})
    if has(r'\b(?:cannot|can.t|unable\s+to)\b.*\b(?:app|chat)\b'):
        return frozenset({'app-inaccessible'})
    if has(r'\b(?:property|land|title\s+deed)\b'):
        return frozenset({'property-fraud'})
    if has(r'\b(?:emergency|danger|on\s+their\s+way\s+to\s+your\s+door)\b'):
        return frozenset({'emergency'})
    if has(r'\b(?:FCA|Financial\s+Conduct\s+Authority|unauthorised\s+or\s+clone\s+firm)\b'):
        return frozenset({'financial-conduct'})
    if has(r'\b(?:consumer\s+(?:advice|service|helpline)|Citizens\s+Advice|Advice\s+Direct\s+Scotland|Consumerline)\b'):
        return frozenset({'consumer-advice'})
    if has(r'\bFCA\b'):
        return frozenset({'financial-conduct'})
    if has(r'\b(?:bank|card\s+issuer)\b') and has(r'\b(?:call|contact|ring|dial)\b'):
        return frozenset({'bank-contact'})
    if has(r'\bCompanies\s+House\b') and has(r'\b(?:enquir\w*|filing|company\s+details)\b'):
        return frozenset({'company-enquiry'})
    # A link inside a forwarded email is evidence within that email, not a
    # second website-report request. Coordinated instructions split upstream.
    media = {'crime': r'(?:loss(?:es)?|complaints?|crime)', 'email': r'e-?mails?', 'text': r'(?:texts?|SMS)', 'website': r'(?:websites?|sites?|links?)', 'call': r'calls?'}
    coordinated = set()
    for left, lp in media.items():
        for right, rp in media.items():
            if left != right and has(r'\b' + lp + r'\s+(?:and|or)\s+(?:(?:a|the|your|their|suspicious|fraudulent|fake|scam)\s+)*' + rp + r'\b'):
                coordinated.update((left, right))
    if coordinated:
        return frozenset(coordinated)
    if has(r'\be-?mails?\b'):
        return frozenset({'email'})
    if has(r'\b(?:texts?|SMS)\b'):
        return frozenset({'text'})
    if has(r"\b(?:phone[- ]calls?|calls?|caller[’']s\s+(?:phone\s+)?number)\b"):
        return frozenset({'call'})
    if has(r'\b(?:websites?|webpages?|links?|sites?)\b'):
        return frozenset({'website'})
    if has(r'\b(?:messages?|communications?)\b'):
        return frozenset({'message'})
    if has(r'\b(?:phishing)\b'):
        return frozenset({'email'})
    if has(r'\b(?:impersonation)\b'):
        return frozenset({'impersonation'})
    if has(r'\b(?:reports?|reporting|complaint|crime|loss|fraud|scam|evidence|details|Police|Scotland|Scottish)\b'):
        return frozenset({'crime'})
    return frozenset({'unknown'})


def attached_claims_supported(text):
    """Closed grammar for additional notification-service claims.

    A recognized negative limitation cannot grant an affirmative capability.
    Unknown affirmative outcome/complement claims are unsupported, rather than
    relying on an ever-growing blacklist of refund/takedown synonyms.
    """
    text = text.strip(' .')
    if not text:
        return True
    # Split contrast/coordinated claims, so a denial cannot hide a promise.
    claims = re.split(r'[,;]|\b(?:but|and)\b', text, flags=re.I)
    for claim in claims:
        claim = claim.strip(' .')
        if not claim:
            continue
        if re.fullmatch(r'(?:(?:this|that)(?:\s+(?:route|service))?|it|the\s+(?:route|service))?\s*(?:is|does|will|can)?\s*(?:not|never)\b.*', claim, re.I):
            continue
        if re.fullmatch(r'(?:it|this)\s+is\s+free', claim, re.I):
            continue
        if re.fullmatch(r'it\s+goes\s+to\s+your\s+mobile\s+operator', claim, re.I):
            continue
        if re.fullmatch(r'(?:this|that|it|the\s+(?:route|service))\s+(?:lets|allows|enables)\s+(?:us|you)\s+(?:to\s+)?notify\s+(?:the\s+brand|SHEIN)', claim, re.I):
            continue
        if re.fullmatch(r'to\s+(?:notify|inform)\s+(?:the\s+brand|SHEIN)(?:\s+(?:about|of)\s+(?:the\s+)?scam)?', claim, re.I):
            continue
        return False
    return True
