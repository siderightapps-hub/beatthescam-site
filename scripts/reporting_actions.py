"""Closed instruction vocabulary. No article or canon-authored template prose.

IDs select complete cases. Adding a method/purpose requires a code review and
new compatibility tests; arbitrary canon strings cannot expand this registry.
"""
from types import MappingProxyType
from dataclasses import dataclass

LEGACY_VERSION = 'restricted-actions/v1'
V2_VERSION = 'restricted-actions/v2'
VERSION = 'restricted-actions/v3'


@dataclass(frozen=True)
class SmsComposition:
    """Resolved code-owned semantics, never an author-supplied message."""
    provider_scope_id: str
    provider_owner_id: str
    recipient_relation: str
    method_id: str
    payload_profile_id: str
    composition_mode: str
    literal_semantic_id: str
    literal: str
    components: tuple
    separator: str
    destination_field: str
    destination_kind: str
    numbering_context: str
    condition_ids: tuple
    eligibility_ids: tuple


SMS_COMPOSITION_CASES = MappingProxyType({
    'o2-call-then-caller-number': SmsComposition(
        'o2-uk-mobile-line', 'o2', 'reader-mobile-provider',
        'report-caller-number-sms', 'caller-number-from-recent-calls-sms',
        'new-sms-prefix-and-caller-number', 'call-prefix', 'Call',
        ('call-prefix', 'caller-number-from-recent-calls-sms'), ' ',
        'sms', 'shortcode', 'GB', ('suspicious-mobile-call',),
        ('recipient-mobile-line',)),
})


def sms_composition(case_id):
    """One closed lookup. No runtime registration, defaults or component input."""
    registered(case_id, SMS_COMPOSITION_CASES, 'SMS composition case')
    return SMS_COMPOSITION_CASES[case_id]
CONDITIONS = MappingProxyType({
    'suspicious-email': 'For a suspicious email only.',
    'suspicious-text': 'For a suspicious text message only.',
    'money-sent': 'If you have already sent money.',
    'account-at-risk': 'If your account or payment details may be at risk.',
    'email-claims-service-brand': 'For a suspicious email claiming to be from {brand} only.',
    'email-refers-to-service-brand': 'For a suspicious email that refers to {brand} only.',
    'not-responded-to-email': 'Use this email-reporting method only if you have not responded to the suspicious email.',
    'suspected-authorised-bank-transfer-to-fraudster': 'If you suspect an authorised bank transfer from your own account went to a scammer.',
    'suspicious-mobile-call': 'For a suspicious call received on your mobile only.',
    'banking-device-safe': 'Use the banking app only when the device is safe for banking. If the device may have been compromised, do not use its banking app until it is safe.',
})
ELIGIBILITY = MappingProxyType({
    'consumer-seeking-advice': 'For people seeking consumer advice.',
    'person-affected-by-crime': 'For people affected by crime.',
    'o2-pay-monthly-origin': 'Call from your own O2 Pay Monthly mobile in the UK.',
    'o2-payg-origin': 'Call from your own O2 Pay As You Go mobile in the UK.',
    'sender-own-account': 'The transfer must have been made from your own account.',
    'recipient-mobile-line': 'Use the mobile line on which you received the suspicious call.',
    'existing-customer': 'For existing customers of this service only.',
    'adult': 'For people aged eighteen or over only.',
    'minor': 'For people under eighteen only.',
    'platform-account': 'For content on this service and accounts with this service only.',
})
LIMITATIONS = MappingProxyType({
    'no-refund-promise': 'This service does not promise a refund.',
    'not-emergency': 'This route is not an emergency service.',
    'evidence-only': 'This channel accepts suspicious-message evidence; it does not investigate financial losses.',
    'support-only': 'This service offers support; it does not take a police crime report.',
    'no-individual-outcome-feedback': 'You will not receive individual feedback about the outcome of this report.',
    'no-money-recovery-guarantee': 'Getting the money back is not guaranteed.',
    'no-recovery-promise': 'Recovery of money or removal of content is not guaranteed.',
})
# template: action type, destination kind, purpose, mode, required condition,
# permitted optional conditions, complete instruction (trusted channel slot).
TEMPLATES = MappingProxyType({
    'report-phishing-web': ('report', 'url', 'phishing-report', 'intake', ('suspicious-email',), (), 'Report the suspicious email to {service} using {channel}.'),
    'report-crime-web': ('report', 'url', 'police-report', 'intake', (), (), 'Report the fraud to {service} using {channel}.'),
    'contact-support-web': ('contact', 'url', 'account-support', 'support', (), ('account-at-risk',), 'Contact {service} using {channel}.'),
    'call-support': ('call', 'phone', 'account-support', 'support', (), ('account-at-risk',), 'Call {service} on {channel}.'),
    'call-police': ('call', 'phone', 'police-report', 'intake', (), (), 'Call {service} on {channel} to report the fraud.'),
    'email-evidence': ('email', 'email', 'phishing-report', 'intake', ('suspicious-email',), (), 'Email the suspicious-message evidence to {service} at {channel}.'),
    'forward-email': ('forward', 'email', 'phishing-report', 'intake', ('suspicious-email',), (), 'Forward the original suspicious email to {service} at {channel}.'),
    'attach-email': ('forward', 'email', 'phishing-report', 'intake', ('suspicious-email',), (), 'Attach the original suspicious email to a new email addressed to {service} at {channel}.'),
    'forward-text': ('forward', 'shortcode', 'phishing-report', 'intake', ('suspicious-text',), (), 'Forward the suspicious text message to {service} on {channel}.'),
    'submit-platform': ('submit', 'url', 'platform-report', 'intake', (), (), 'Submit the evidence to {service} using {channel}.'),
    'visit-verification': ('visit', 'url', 'site-verification', 'verification', (), (), 'Visit {service} at {channel} to check the service details.'),
    'call-consumer-advice-english': ('call', 'phone', 'consumer-advice', 'support', (), (), 'For consumer advice, call the English-language {service} line on {channel}.'),
    'call-victim-support': ('call', 'phone', 'victim-support', 'support', (), (), 'Call {service} on {channel} for support.'),
    'call-o2-personal-support': ('call', 'voice-shortcode', 'account-support', 'support', (), (), 'Call {channel} from the eligible O2 mobile line for customer support.'),
    'forward-brand-email': ('forward', 'email', 'phishing-report', 'intake', ('suspicious-email', 'email-claims-service-brand'), (), 'Forward the original suspicious email to {service} at {channel}.'),
    'forward-brand-reference-email': ('forward', 'email', 'phishing-report', 'intake', ('suspicious-email', 'email-refers-to-service-brand'), (), 'Forward the original suspicious email to {service} at {channel}.'),
    'forward-unanswered-email': ('forward', 'email', 'phishing-report', 'intake', ('suspicious-email', 'not-responded-to-email'), ('email-claims-service-brand', 'email-refers-to-service-brand'), 'Forward the original suspicious email to {service} at {channel}.'),
    'email-original-file': ('email', 'email', 'phishing-report', 'intake', ('suspicious-email', 'email-claims-service-brand'), (), ''),
    'report-caller-number-sms': ('report', 'shortcode', 'suspicious-call-report', 'intake', ('suspicious-mobile-call',), (), ''),
    'open-verification': ('open', 'url', 'site-verification', 'navigation', (), (), 'Open {service} at {channel} to check the service details.'),
})
READER_METHODS = MappingProxyType({
    'existing-bank-app': 'Contact the bank that sent that transfer immediately through the existing banking app you already use for that sending account.',
    'number-on-bank-card': "Contact the bank that sent that transfer immediately. Use the contact number printed on that bank's card for the sending account.",
})
PURPOSES = MappingProxyType({
    'consumer-advice': 'consumer advice', 'victim-support': 'support for people affected by crime',
    'suspicious-call-report': 'suspicious mobile call reporting',
    'phishing-report': 'suspicious-message reporting', 'police-report': 'police fraud reporting',
    'account-support': 'account support', 'platform-report': 'platform evidence submission',
    'site-verification': 'service verification', 'payment-recovery': 'payment recovery',
})


# Text, semantic category, compatible method IDs. No caller-supplied parameters.
QUALIFIERS = MappingProxyType({
    'free-uk-phone-call': ('Calls from UK mobiles and landlines are free.', 'cost', ('call-consumer-advice-english', 'call-victim-support')),
    'free-from-required-o2-phone': ('The call is free from the required O2 phone.', 'cost', ('call-o2-personal-support',)),
    'free-sms-to-provider': ('The SMS report to your mobile provider is free.', 'cost', ('report-caller-number-sms',)),
    'weekday-0900-1700-excluding-bank-holidays': ('Open Monday to Friday, 09:00–17:00, excluding bank holidays.', 'availability', ('call-consumer-advice-english',)),
    'support-24-hours-every-day': ('Support is available 24 hours a day, every day.', 'availability', ('call-victim-support',)),
    'o2-personal-support-hours': ('Customer service: Monday to Friday 08:00–21:00; Saturday 08:00–20:00; Sunday 08:00–18:00.', 'availability', ('call-o2-personal-support',)),
    'no-police-report-needed': ('You do not need to have reported the crime to the police to receive support.', 'access clarification', ('call-victim-support',)),
})
O2_PLATINUM_HOURS = 'For Pay Monthly Platinum customers: Monday to Friday 08:00–20:00; Saturday and Sunday 09:00–18:00.'
RECIPIENT_RELATIONS = MappingProxyType({
    'service-operator': 'The selected canon service operator.',
    'sending-bank-of-affected-transfer': 'The bank of the account that sent the affected transfer.',
    'reader-mobile-provider': 'The provider of the mobile line that received the suspicious call.',
})
# object, preparation, composition mode, literal subject. Indivisible profiles.
PAYLOAD_PROFILES = MappingProxyType({
    'original-email': ('original suspicious email', 'retain original email', 'forward', ''),
    'original-email-file-with-phishing-example-subject': ('original email message file', 'save original email as a message file', 'new email with saved original attached', 'phishing email example'),
    'caller-number-from-recent-calls-sms': ('number of the suspicious mobile caller', 'copy number from recent calls', 'new SMS', ''),
})
DIALLING_NETWORKS = MappingProxyType({'o2-uk': 'O2 mobile in the UK'})

# Internal compatibility sets, not new author-extensible vocabularies.
_PAYLOAD_METHODS = MappingProxyType({
    **{m: 'original-email' for m in ('forward-email', 'forward-brand-email', 'forward-brand-reference-email', 'forward-unanswered-email')},
    'email-original-file': 'original-email-file-with-phishing-example-subject',
    'report-caller-number-sms': 'caller-number-from-recent-calls-sms',
})
_ELIGIBILITY_METHODS = MappingProxyType({
    'contact-support-web': (('existing-customer',), ()),
    'call-support': (('existing-customer',), ()),
    'submit-platform': (('platform-account',), ('adult', 'minor')),
    'call-consumer-advice-english': (('consumer-seeking-advice',), ()),
    'call-victim-support': (('person-affected-by-crime',), ()),
    'report-caller-number-sms': (('recipient-mobile-line',), ()),
})


def ids(value, registry, name):
    if (not isinstance(value, list) or len(value) > 8
            or any(not isinstance(x, str) or x not in registry for x in value)
            or len(set(value)) != len(value)):
        raise ValueError('unknown, duplicate or invalid ' + name)
    return set(value)


def registered(value, registry, name):
    if not isinstance(value, str) or value not in registry:
        raise ValueError('unknown or invalid ' + name)
    return value


def contract(action_type, purpose, mode, condition_ids, instruction, *,
             schema_version, eligibility_ids, qualifier_ids, limitation_ids):
    """Exact v2 compatibility or the sole v3 composition; never parse fallback."""
    if schema_version not in (V2_VERSION, VERSION):
        raise ValueError('unsupported action schema version')
    conditions = ids(condition_ids, CONDITIONS, 'condition IDs')
    eligible = ids(eligibility_ids, ELIGIBILITY, 'eligibility IDs')
    qualifiers = ids(qualifier_ids, QUALIFIERS, 'qualifier IDs')
    limits = ids(limitation_ids, LIMITATIONS, 'limitation IDs')
    if (not limits or {'adult', 'minor'} <= eligible
            or {'email-claims-service-brand', 'email-refers-to-service-brand'} <= conditions):
        raise ValueError('missing limits or incompatible predicates')
    if not isinstance(instruction, dict):
        raise ValueError('instruction must select a closed contract')
    composition = None
    if schema_version == VERSION:
        composition = sms_composition(instruction.get('sms_composition_case_id'))
        if (instruction.get('template_id') != composition.method_id
                or instruction.get('kind') != 'fixed-destination'):
            raise ValueError('v3 schema requires the closed composed-SMS method')
    recipient = registered(instruction.get('recipient_relation'), RECIPIENT_RELATIONS, 'recipient relation')
    if instruction.get('kind') == 'reader-held-channel':
        method = registered(instruction.get('method_id'), READER_METHODS, 'reader-held method')
        required = {'suspected-authorised-bank-transfer-to-fraudster'}
        if method == 'existing-bank-app': required.add('banking-device-safe')
        if (set(instruction) != {'kind', 'role', 'method_id', 'recipient_relation'}
                or instruction['role'] != 'own-bank'
                or recipient != 'sending-bank-of-affected-transfer'
                or (action_type, purpose, mode) != ('contact', 'payment-recovery', 'support')
                or conditions != required or eligible != {'sender-own-account'}
                or qualifiers or 'no-money-recovery-guarantee' not in limits):
            raise ValueError('incompatible reader-held contact action')
        return method, ()
    template = registered(instruction.get('template_id'), TEMPLATES, 'method/template ID')
    expected_fields = {'kind', 'template_id', 'channels', 'recipient_relation'}
    if composition is not None:
        expected_fields.add('sms_composition_case_id')
    if template in _PAYLOAD_METHODS:
        expected_fields.add('payload_profile_id')
        payload = registered(instruction.get('payload_profile_id'), PAYLOAD_PROFILES, 'payload profile')
        if payload != _PAYLOAD_METHODS[template]:
            raise ValueError('incompatible method/payload profile')
    if set(instruction) != expected_fields or instruction.get('kind') != 'fixed-destination':
        raise ValueError('unknown instruction kind or fields')
    expected_recipient = 'reader-mobile-provider' if template == 'report-caller-number-sms' else 'service-operator'
    required_eligible, optional_eligible = _ELIGIBILITY_METHODS.get(template, ((), ()))
    if template == 'call-o2-personal-support':
        if eligible not in ({'o2-pay-monthly-origin'}, {'o2-payg-origin'}):
            raise ValueError('O2 support requires exactly one originating plan')
    elif not set(required_eligible) <= eligible or not eligible <= set(required_eligible + optional_eligible):
        raise ValueError('incompatible method/eligibility tuple')
    expected_qualifiers = {q for q, (_, _, methods) in QUALIFIERS.items() if template in methods}
    atype, kind, expected_purpose, expected_mode, required, optional, _ = TEMPLATES[template]
    channels = instruction['channels']
    if ((action_type, purpose, mode) != (atype, expected_purpose, expected_mode)
            or recipient != expected_recipient or qualifiers != expected_qualifiers
            or not set(required) <= conditions or not conditions <= set(required + optional)
            or not isinstance(channels, list) or len(channels) != 1
            or not isinstance(channels[0], dict) or channels[0].get('kind') != kind):
        raise ValueError('incompatible action/purpose/method/condition/channel/recipient/qualifier tuple')
    channel = channels[0]
    if composition is not None:
        if (recipient != composition.recipient_relation
                or instruction['payload_profile_id'] != composition.payload_profile_id
                or conditions != set(composition.condition_ids)
                or eligible != set(composition.eligibility_ids)
                or channel != {'field': composition.destination_field,
                               'kind': composition.destination_kind,
                               'numbering_context': composition.numbering_context}):
            raise ValueError('incompatible composed-SMS case tuple')
    if template == 'call-o2-personal-support':
        registered(channel.get('dialling_network_id'), DIALLING_NETWORKS, 'dialling network')
        if channel.get('field') != 'phone': raise ValueError('voice shortcode requires the ordinary phone field')
    elif 'dialling_network_id' in channel:
        raise ValueError('dialling network is forbidden for this method')
    if template in ('call-consumer-advice-english', 'call-victim-support') and channel.get('field') != 'phone':
        raise ValueError('selected phone method requires the ordinary phone field')
    if mode == 'support':
        allowed_scope = {'support-only', 'no-recovery-promise'} if template in ('call-support', 'contact-support-web') else {'support-only'}
        if not allowed_scope & limits:
            raise ValueError('support requires a visible scope limitation')
    if template in ('forward-brand-email', 'forward-brand-reference-email', 'forward-unanswered-email', 'email-original-file') and 'evidence-only' not in limits:
        raise ValueError('selected email method requires evidence-only scope')
    return template, channels
