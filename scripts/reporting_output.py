"""Effective article values and provenance, independent of the page shell.

HTML inspection is restricted to renderer-owned fragments, using HTMLParser
for attributes and adjacent text nodes. Trust is never inferred from HTML
classes, anchor labels or destination equality. Canon/citation nodes carry
references, not arbitrary exemptible article text.
"""
from dataclasses import dataclass
from enum import Enum
from html.parser import HTMLParser


class Capability(str, Enum):
    TEXT = 'text'
    TAXONOMY = 'taxonomy'
    INTERNAL_NAVIGATION = 'internal_navigation'
    CITATION = 'citation'
    REPORTING_ACTION = 'reporting_action'
    CONTACT_ACTION = 'contact_action'
    CALL_ACTION = 'call_action'
    EMAIL_ACTION = 'email_action'
    FORWARD_ACTION = 'forward_action'
    SUBMIT_ACTION = 'submit_action'
    NAVIGATION_ACTION = 'navigation_action'


class Provenance(str, Enum):
    ARTICLE = 'ordinary_article_text'
    TAXONOMY = 'taxonomy'
    NUMERIC_FACT = 'numeric_fact'
    METADATA = 'metadata'
    QUICK_ANSWER = 'quick_answer'
    FAQ = 'faq'
    SCHEMA = 'schema_derived'
    INTERNAL_LINK = 'internal_link'
    REVIEWED_SOURCE = 'reviewed_source'
    REPORTING_ROUTE = 'reporting_route'


def field_provenance(path):
    if path == 'quick_answer':
        return Provenance.QUICK_ANSWER
    if path.startswith('faq/'):
        return Provenance.FAQ
    if path.startswith('sources_checked/'):
        return Provenance.REVIEWED_SOURCE
    if path.split('/')[0] in ('title', 'description', 'keywords', 'category'):
        return Provenance.METADATA
    return Provenance.ARTICLE


@dataclass(frozen=True)
class TextUse:
    """Validated output use. Projection never replaces the original field identity."""
    source_paths: tuple
    value: str
    provenance: Provenance
    projection: str = 'text'

    @property
    def capability(self):
        return Capability.TEXT


@dataclass(frozen=True)
class InternalLink:
    source_paths: tuple
    href: str

    @property
    def capability(self):
        return Capability.INTERNAL_NAVIGATION

    @property
    def provenance(self):
        return Provenance.INTERNAL_LINK


@dataclass(frozen=True)
class ArticleText:
    path: str
    text: str
    projection: str = 'text'
    source_paths: tuple = ()


@dataclass(frozen=True)
class ArticleHTML:
    path: str
    html: str
    projection: str = 'html'
    source_paths: tuple = ()


@dataclass(frozen=True)
class CanonRoutes:
    route_ids: tuple


@dataclass(frozen=True)
class Citation:
    label: str
    url: str

    @property
    def capability(self):
        return Capability.CITATION

    @property
    def provenance(self):
        return Provenance.REVIEWED_SOURCE


class Fragment(HTMLParser):
    """Browser text projection: inline nodes concatenate; blocks separate.

    Entity references are decoded exactly once by the HTML parser. Source
    entities already escaped by inline_html remain literal reader text.
    """
    BLOCKS = frozenset({'p', 'div', 'section', 'article', 'aside', 'ul', 'ol',
        'li', 'h1', 'h2', 'h3', 'h4', 'details', 'summary', 'table', 'tr', 'td',
        'th', 'caption', 'figcaption', 'figure', 'br', 'hr', 'text', 'tspan'})

    def __init__(self, value):
        super().__init__(convert_charrefs=True)
        self.parts, self.hrefs, self.attributes = [], [], []
        self.feed(value)
        self.close()

    def handle_starttag(self, tag, attrs):
        if tag in self.BLOCKS:
            self.parts.append('\n')
        for key, value in attrs:
            if key in ('href', 'src', 'action', 'formaction', 'xlink:href'):
                self.hrefs.append(value or '')
            if key in ('alt', 'title', 'aria-label', 'content'):
                self.attributes.append(value or '')

    def handle_endtag(self, tag):
        if tag in self.BLOCKS:
            self.parts.append('\n')

    def handle_data(self, value):
        self.parts.append(value)

    @property
    def text(self):
        return ''.join(self.parts)
