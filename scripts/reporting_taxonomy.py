"""Closed taxonomy identity and projections; never reporting/action authority."""
import re
from dataclasses import dataclass
from types import MappingProxyType
from reporting_output import Capability, Provenance

CATEGORY_LABELS = {
    "marketplace": "Marketplace Scams",
    "sms":         "Text Message Scams",
    "payment":     "Payment Scams",
    "crypto":      "Crypto Scams",
    "tech":        "Tech Support Scams",
    "website":     "Website Scams",
    "government":  "Government Impersonation",
    "employment":  "Employment Scams",
    "social":      "Social Media Scams",
    "dating":      "Romance & Dating Scams",
    "email":       "Email Scams",
    "phone":       "Phone Scams",
    "travel":      "Travel Scams",
    "shopping":    "Shopping Scams",
    "finance":     "Investment & Finance Scams",
    "fraud":       "Fraud & Impersonation",
    "utility":     "Utility Scams",
}
CATEGORY_LABELS = MappingProxyType(CATEGORY_LABELS)


def identifier(value):
    # Syntax only: action-looking words are valid identifiers, not prose.
    if type(value) is not str or len(value) > 64 or not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', value, re.ASCII):
        raise ValueError('taxonomy identifier: invalid ASCII slug syntax')
    return value


def resolve(value):
    identifier(value)
    if value not in CATEGORY_LABELS:
        raise ValueError('taxonomy identifier: not enrolled in the closed category registry')
    return TaxonomyUse(value)


@dataclass(frozen=True)
class TaxonomyUse:
    identifier: str
    capability = Capability.TAXONOMY
    provenance = Provenance.TAXONOMY

    def project(self, projection='label'):
        identifier(self.identifier)
        if self.identifier not in CATEGORY_LABELS:
            raise ValueError('taxonomy identifier: not enrolled in the closed category registry')
        label = CATEGORY_LABELS[self.identifier]
        # No arbitrary labels, HTML, destination, action ID or template argument.
        if projection == 'identifier':
            return self.identifier
        if projection == 'label':
            return label
        if projection == 'path':
            return '/categories/' + self.identifier + '/'
        if projection == 'grid':
            return 'All ' + label.lower() + ' guides'
        raise ValueError('taxonomy projection: unknown projection')

    def validate(self):
        self.project()
        return self
