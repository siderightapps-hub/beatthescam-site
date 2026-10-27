"""Network representations for structured reporting; never an authority source.

Detection is deliberately more conservative than URL admission. NFKC and
decoding belong ONLY to the raw-text detector. Host comparison uses maintained
IDNA 2008 / UTS #46, nontransitional processing (never Python's IDNA 2003 codec).
The stricter DNS/IDNA subset rejects ambiguous browser-accepted spellings;
failed host parsing must never make domain-shaped prose safe.

Canon URLs retain exact ASCII evidence bytes. Citations may retain Unicode
hosts, but are separately reviewed occurrences, never reporting destinations.
The idna dependency is lazy so legacy-only builds keep their stdlib runtime.
"""
import re
import unicodedata
from urllib.parse import unquote, urlsplit


NETWORK_DOTS = ".\u3002\uff0e\uff61"
# Detection holds only, NOT aliases or an equivalence/confusable mapping.
AMBIGUOUS_DOTS = "\u2024\u2027\u2219\u00b7\u2022\u22c5\u0387\u06d4\u30fb"
_SCHEME = re.compile(r"(?:[a-z][a-z0-9+.-]*://|https?:|mailto:|tel:|sms:|www\.)", re.I | re.ASCII)
_MAIL = re.compile(r"[\w.+-]+@[\w.-]+")
_NETWORK_PATH = re.compile(r"[\\/]{2}[^\s/\\]")


def canonical_host(host):
    """Return a comparison-only ASCII DNS host, or raise ValueError.

    UTS46 maps the standard separators and width/case forms, then NFC and IDNA
    validate labels, bidi/joiners and DNS lengths. No visual-confusable folding,
    percent decoding, userinfo, port or URL repair is performed here. A single
    trailing root dot is comparison-equivalent, never admitted in canon URLs.
    Symbols/invalid A-labels and browser's non-DNS IPv4 aliases fail closed.
    """
    import idna  # required for structured mode; no permissive fallback
    if (not isinstance(host, str) or not host or len(host) > 2048
            or any(c.isspace() or unicodedata.category(c).startswith('C') for c in host)
            or any(c in host for c in '/\\:@%?#')):
        raise ValueError('invalid DNS host representation')
    try:
        result = idna.encode(host, uts46=True, transitional=False,
                             std3_rules=True).decode('ascii').lower()
    except (idna.IDNAError, UnicodeError) as exc:
        raise ValueError('invalid IDNA host') from exc
    result = result.removesuffix('.')
    labels = result.split('.')
    if (len(labels) < 2 or len(result) > 253 or any(not x or len(x) > 63 for x in labels)
            or re.fullmatch(r'(?:[0-9]+|0x[0-9a-f]+)', labels[-1], re.I)):
        raise ValueError('expected a bounded DNS domain, not an IP alias')
    return result


def https_identity(value, *, unicode_host=False):
    """Validate original HTTPS syntax; return (ASCII host, exact path, query).

    The original URL is never rewritten or used to infer authority. Admission
    is narrower than browser parsing: no credentials, ports, escaped authority,
    fragments, syntax compatibility characters, controls or dot segments.
    Paths/queries remain exact ASCII (Unicode can be explicitly percent-encoded).
    """
    if (not isinstance(value, str) or not value.startswith('https://')
            or len(value) > 2048 or re.search(r"[\s\\<>\"'`{}]", value)
            or any(unicodedata.category(c).startswith('C') for c in value)
            or re.search(r'%(?![0-9a-fA-F]{2})', value)):
        raise ValueError('expected an exact safe HTTPS URL')
    decoded = unquote(value)
    if re.search(r"[\x00-\x20\x7f\\<>\"']", decoded):
        raise ValueError('encoded control/markup characters are forbidden')
    p = urlsplit(value)
    if (not p.hostname or p.username is not None or p.password is not None
            or p.port is not None or '#' in value or '%' in p.netloc
            or ':' in p.netloc or '@' in p.netloc
            or not (p.path + p.query).isascii()):
        raise ValueError('invalid authority, port, fragment or non-ASCII path/query')
    host = canonical_host(p.netloc)
    # Unicode host input is limited to the hostname. ASCII syntax is not
    # NFKC-repaired into a URL, and canon admission still requires exact bytes.
    if not unicode_host and (not value.isascii() or p.netloc != host):
        raise ValueError('canon host must be exact lowercase ASCII IDNA without a root dot')
    if any(part in ('.', '..') for part in unquote(p.path).split('/')):
        raise ValueError('path traversal segment')
    return host, p.path or '/', '?' in value, p.query


def raw_network_destinations(text):
    """Classify syntax only. Valid AND malformed domain-shaped tokens are held.

    Called after the caller's bounded decoding/NFKC closure, on source and final
    effective text. Returning an ASCII host here grants no capability. Numeric
    dotted data has no letters and remains with the separate NumericFact policy.
    """
    found = []
    # URL parsing discards ASCII tab/CR/LF. Check that view for split targets;
    # it is detection-only and is never rendered or admitted as a canon value.
    for value in dict.fromkeys((text, text.translate({9: None, 10: None, 13: None}))):
        found.extend(m.group() for pattern in (_SCHEME, _MAIL, _NETWORK_PATH)
                     for m in pattern.finditer(value))
        token = []
        def check():
            candidate = ''.join(token).rstrip(NETWORK_DOTS)
            # Delimiters alone, prose words and purely numeric data are not
            # domains. Alphabetic content may occur anywhere (e.g. 123.中国).
            if (not any(c in NETWORK_DOTS + AMBIGUOUS_DOTS for c in candidate)
                    or not any(c.isalpha() or unicodedata.category(c) == 'So' for c in candidate)):
                return
            tail = re.split('[' + re.escape(NETWORK_DOTS + AMBIGUOUS_DOTS) + ']', candidate)[-1]
            if tail.isdecimal() and not any(c.isalpha() for c in candidate.lstrip('vV')):
                return  # versions/IPs/decimal facts stay in the numeric policy
            if any(c in AMBIGUOUS_DOTS for c in candidate):
                found.append('ambiguous domain separator: ' + candidate)
                return
            try:
                host = canonical_host(candidate)
                found.append('raw domain: ' + host)
            except ValueError:
                found.append('malformed domain-shaped value: ' + candidate)
        for char in value + ' ':
            if (unicodedata.category(char)[0] in 'LMNS'
                    or char in '_-' + NETWORK_DOTS + AMBIGUOUS_DOTS):
                token.append(char)
            else:
                if token:
                    check()
                    token.clear()
    return found
