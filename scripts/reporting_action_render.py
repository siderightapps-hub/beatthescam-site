"""Complete resolved action projections, never article-supplied fragments."""
from dataclasses import dataclass
from html import escape
from reporting_output import Capability, Provenance, Fragment
from reporting_actions import (CONDITIONS, ELIGIBILITY, LIMITATIONS, QUALIFIERS, TEMPLATES,
    READER_METHODS, PURPOSES, PAYLOAD_PROFILES, O2_PLATINUM_HOURS)


@dataclass(frozen=True)
class ActionComponent:
    catalog: object
    action: object

    def validate(self):
        if self.catalog.resolve(self.action.route_id) is not self.action:
            raise ValueError('action component was not issued by this canon')

    @property
    def capability(self):
        return {'report': Capability.REPORTING_ACTION, 'contact': Capability.CONTACT_ACTION,
            'call': Capability.CALL_ACTION, 'email': Capability.EMAIL_ACTION,
            'forward': Capability.FORWARD_ACTION, 'submit': Capability.SUBMIT_ACTION,
            'visit': Capability.NAVIGATION_ACTION, 'open': Capability.NAVIGATION_ACTION}[self.action.action_type]

    @property
    def provenance(self):
        return Provenance.REPORTING_ROUTE

    @property
    def value(self):
        """Inspection only; endpoint-free components have no destination value."""
        return self.action.channels[0].value if self.action.channels else None

    def html(self):
        self.validate()
        a = self.action
        scope = ('Available worldwide.' if a.jurisdictions == ('Global',) else
                 'For ' + ', '.join(a.jurisdictions) + '.')
        applicability = [scope]
        # Render registry order, independently of input/set serialization order.
        applicability += [text.format(brand=a.owner) for x, text in CONDITIONS.items() if x in a.condition_ids]
        applicability += [text for x, text in ELIGIBILITY.items() if x in a.eligibility_ids]
        from reporting_structured import ComposedSmsAction
        composed = type(a) is ComposedSmsAction
        if composed:
            # One reviewed case, not a component interpreter. Row equality is
            # checked by catalog.resolve before any projection is emitted.
            if (a.sms_composition_case_id != 'o2-call-then-caller-number'
                    or a.sms_composition.provider_scope_id != 'o2-uk-mobile-line'):
                raise ValueError('unsupported composed-SMS render case')
            applicability.append('This format is for the O2 mobile line in the UK on which you received the call.')
        if a.template_id in READER_METHODS:
            operation = '<p>' + escape(READER_METHODS[a.template_id]) + '</p>'
            owner = 'Bank that sent your transfer — payment recovery.'
        else:
            from reporting_structured import ReportingDestination, render_destination
            channel = render_destination(self.catalog, ReportingDestination(self.catalog, a, a.channels[0]))
            if a.template_id == 'email-original-file':
                subject = PAYLOAD_PROFILES[a.payload_profile_id][3]
                operation = ('<ol><li>Save the original email as a message file. This means the original message, not an attachment contained inside it.</li>'
                    + '<li>Create a new email to ' + channel + '.</li>'
                    + '<li>Use the subject <span>' + escape(subject) + '</span>.</li>'
                    + '<li>Attach that saved message file and send the new email.</li></ol>')
            elif a.template_id == 'report-caller-number-sms':
                if composed:
                    operation = ('<ol><li>Copy the suspicious caller’s number from recent calls on that mobile.</li>'
                        + '<li>Compose a new SMS beginning with <span>' + escape(a.sms_composition.literal)
                        + '</span>, followed by one space and that caller number. Include no other message text.</li>'
                        + '<li>Send that SMS report to ' + channel + ' for your mobile provider.</li></ol>')
                else:
                    operation = ('<ol><li>Copy the suspicious caller’s number from recent calls on that mobile.</li>'
                        + '<li>Compose a new SMS containing that caller number to ' + channel
                        + ' for your mobile provider.</li><li>Send that SMS report.</li></ol>')
            else:
                operation = '<p>' + TEMPLATES[a.template_id][-1].format(service=escape(a.service), channel=channel) + '</p>'
            owner = ('Your mobile provider — suspicious mobile call reporting.' if a.recipient_relation == 'reader-mobile-provider'
                     else f'{a.service} — {a.owner}; {PURPOSES[a.purpose]}.')
        qualifiers = [text for x, (text, _, _) in QUALIFIERS.items() if x in a.qualifier_ids]
        if 'o2-personal-support-hours' in a.qualifier_ids and 'o2-pay-monthly-origin' in a.eligibility_ids:
            qualifiers.append(O2_PLATINUM_HOURS)
        return ('<div class="restricted-action" data-action-id="' + escape(a.route_id, quote=True) + '">'
            + '<p>' + escape(owner) + '</p><p>' + escape(' '.join(applicability)) + '</p>' + operation
            + ''.join('<p>This route is operated by ' + escape(operator) + '.</p>' for _, operator in a.attributions)
            + ''.join('<p>' + escape(text) + '</p>' for text in qualifiers)
            + ''.join('<p>' + escape(text) + '</p>' for x, text in LIMITATIONS.items() if x in a.limitation_ids) + '</div>')

    def plain(self):
        return Fragment(self.html()).text.strip()


def components(catalog, route_ids):
    # Protection first; stable IDs break ties. The article cannot reorder cases.
    from reporting_structured import ordered_actions
    return tuple(ActionComponent(catalog, a) for a in ordered_actions(catalog, route_ids))


def block(catalog, route_ids):
    nodes = components(catalog, route_ids)
    if not nodes:
        return ''
    return ('<section class="reporting-routes" id="reporting-routes" aria-labelledby="reporting-routes-heading">'
        '<h2 id="reporting-routes-heading">Reporting and support options</h2>'
        + ''.join(node.html() for node in nodes) + '</section>')


QUESTIONS = {'where-to-report': 'Where can I report this?', 'how-to-contact': 'How can I get support?'}


def placement(value, plan, catalog, *, faq=False):
    expected = {'kind', 'question_id', 'route_ids'} if faq else {'kind', 'route_ids'}
    if (not isinstance(value, dict) or set(value) != expected
            or value.get('kind') != ('action-faq' if faq else 'action-summary')
            or (faq and value.get('question_id') not in QUESTIONS)):
        raise ValueError('invalid closed action placement')
    nodes = components(catalog, value['route_ids'])
    if not nodes or set(value['route_ids']) - set(plan):
        raise ValueError('placement must reference selected complete actions')
    return nodes


def faq_projection(items, plan, catalog):
    from reporting_syntax import inline_html
    html, pairs, nodes = [], [], []
    for item in items:
        if isinstance(item, dict):
            selected = placement(item, plan, catalog, faq=True)
            q = QUESTIONS[item['question_id']]
            a = '\n'.join(n.plain() for n in selected)
            # Keep eligibility visible rather than hiding it in a collapsed FAQ.
            html.append('<div class="action-faq"><h3>' + escape(q) + '</h3>'
                        + ''.join(n.html() for n in selected) + '</div>')
            nodes.extend(selected)
        else:
            q, a = item
            html.append('<details><summary>' + inline_html(q) + '</summary><p>' + inline_html(a) + '</p></details>')
        pairs.append((q, a))
    return ''.join(html), pairs, nodes
