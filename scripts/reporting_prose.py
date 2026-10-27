"""Closed contextual language for NEW structured publication, never action authority.

Every production consumes a complete value or sentence. There are no arbitrary
noun/verb slots, prefix exemptions, reviewer exceptions, or semantic denylist.
Expanding this small authoring language requires policy/code review, not a signature.
Frozen legacy pages do not use this contract. Raw destination checks remain
independent defence in depth; labelled numeric data has its own closed grammar.
"""
import re
from reporting_syntax import schema_plain, normalize_bullet_body

VERSION = 'restricted-prose/v2'

FACT_PATTERNS = {
    'version': r'(?:[Vv]ersion|[Rr]elease) v?[0-9]+(?:\.[0-9]+){1,3}',
    'ip': r'(?:[Ii][Pp](?: address)?|Address) (?:[0-9]{1,3}\.){3}[0-9]{1,3}',
    'decimal': r'(?:[Vv]alue|[Aa]verage) [0-9]+\.[0-9]+',
    'percentage': r'(?:[Rr]ate|[Pp]ercentage) [0-9]+(?:\.[0-9]+)?%',
    'date': r'(?:[Dd]ate|[Dd]ated) [0-9]{1,4}[-/.][0-9]{1,2}[-/.][0-9]{1,4}',
    'money': r'(?:[Cc]ost|[Pp]rice|[Bb]alance) [£$€][0-9]+(?:,[0-9]{3})*(?:\.[0-9]{2})?',
    'year': r'(?:[Ii]n|[Yy]ear) (?:19|20)[0-9]{2}',
    'legislation': r'(?:[Ss]ection|[Aa]rticle|[Rr]egulation) [0-9]{1,4}',
    'identifier': r'(?:[Oo]rder|[Rr]eference|Article ID) [A-Za-z]+[0-9]+',
    'count': r'(?:[Cc]ount|[Tt]otal) [0-9]+',
}

# Reusable contextual productions, never approvals for individual pages.
# All alternatives are finite, non-operational vocabulary. Protective stopping,
# evidence retention and internal reading do not confer reporting/contact powers.
_SENTENCES = (
    r'Reporting (?:the incident|fraud) (?:(?:may|can) help|helps) investigators',
    r'Police recommend reporting sextortion promptly',
    r'Banks can sometimes stop or recover payments',
    r'Victims may need support after fraud',
    r'Scammers use (?:urgency|fear|pressure) to discourage independent checks',
    r'A familiar (?:brand|logo) (?:does not establish authenticity|is not proof of authenticity|does not establish that a message is genuine)',
    r'Unexpected requests can create pressure and uncertainty',
    r'An unexpected request can be fraudulent even when it names a familiar organisation',
    r'Pressure and secrecy are warning signs',
    r'(?:Pressure|Urgency|Secrecy) is a warning sign',
    r'A convincing appearance does not establish that a request is genuine',
    r'A phishing email can create pressure',
    r'The police report records a rise in attempts',
    r'A phone scam can appear convincing',
    r'Only two choices',
    r'Do not send more money',
    r'Keep (?:your account details private|the original message|evidence|safe)',
    r'Pause(?: before acting| and check the (?:request|message)(?: before acting| independently)?)?',
    r'Check (?:safely|independently)',
    r'Read (?:settings|help|the guide|the recovery guide and keep evidence)',
    r'Before Read the guide afterwards',
    r'What should I do first\?',
)
_TOPICS = r'(?:suspicious message|phishing emails?|email scams?|phone scams?|phone numbers?|email addresses?|unsolicited calls?|suspicious emails?|police reports?)'
_LABELS = (
    _TOPICS, r'A suspicious message: safe next steps',
    r'(?:(?:Independent|Official|Second|Numeric|Reviewed) evidence(?: title)?|Official guidance|Reviewed source|Evidence|Reporting|Background|Unexpected request|Illustrative message|Decision flow|Safe plain text|Read|Help)',
)
_SENTENCE = re.compile('(?:' + '|'.join(_SENTENCES) + r')\.?', re.I | re.ASCII)
_LABEL = re.compile('(?:' + '|'.join(_LABELS) + r')\.?', re.I | re.ASCII)
_KEYWORDS = re.compile(_TOPICS + '(?:, ' + _TOPICS + ')*', re.I | re.ASCII)
_STEPS = re.compile(r'(?:Step [1-8]: (?:Pause|Check independently|Keep evidence)\.)(?: Step [1-8]: (?:Pause|Check independently|Keep evidence)\.)*', re.ASCII)
_STRING = r'''(?:'(?:[^'\\\r\n]|\\[^\r\n])*'|"(?:[^"\\\r\n]|\\[^\r\n])*")'''
_BODY_LIST = re.compile(r'\[\s*' + _STRING + r'(?:\s*,\s*' + _STRING + r')*\s*,?\s*\]', re.ASCII)


def body_text(text, field):
    """Only body renderers interpret lists; no comments/implicit concatenation.

    All other fields retain their literal reader-visible text. This is a closed
    subset of the legacy body converter, not an exemption applied to fragments.
    """
    value = text.strip()
    if value.startswith('['):
        if not _BODY_LIST.fullmatch(value):
            raise ValueError(f'{field}: restricted action-authoring boundary: unsupported body list syntax')
        return normalize_bullet_body(text)
    return text


def violation(text, *, field=''):
    """Unknown prose fails closed, even if reviewed and cryptographically signed.

    No category exception: machine identifiers must use the taxonomy resolver.
    Inline syntax has the SAME plain projection as the renderer. Every original,
    HTML and schema projection is also independently checked by the caller.
    """
    if not isinstance(text, str):
        return 'non-text value'
    value = schema_plain(text).strip()
    if not value:
        return None  # Optional absent prose has no authority.
    if any(re.fullmatch(p + r'\.?', value, re.ASCII) for p in FACT_PATTERNS.values()):
        return None
    if _LABEL.fullmatch(value) or _KEYWORDS.fullmatch(value) or _STEPS.fullmatch(value):
        return None
    # Punctuation/newline boundaries only. A label is NOT a removable phrase
    # inside a sentence and cannot be concatenated with an arbitrary predicate.
    for sentence in re.split(r'(?<=[.!?])\s+|[\r\n]+', value):
        if not _SENTENCE.fullmatch(sentence.strip()):
            return sentence
    return None


def require_explanatory(text, field=''):
    found = violation(text, field=field)
    if found is not None:
        raise ValueError(f'{field}: restricted action-authoring boundary: unadmitted contextual production {found!r}; operational instructions require a structured action')
