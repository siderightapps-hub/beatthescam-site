"""Validate closed canon action contracts and explicit destination relationships."""
from dataclasses import replace
from types import MappingProxyType
from itertools import combinations
from reporting_network import https_identity, canonical_host
from reporting_syntax import normalize_phone
import reporting_actions as vocabulary


def destination_identity(destination, context='', network=''):
    kind, value = destination.kind, destination.value
    if kind == 'url':
        return (kind, *https_identity(value, unicode_host=True))
    if kind == 'email':
        local, host = value.split('@')
        return kind, local, canonical_host(host)
    return kind, context, network, normalize_phone(value, kind=kind)


def catalog(canon, expected_digest=None):
    import reporting_structured as s
    fail = s._fail
    if not isinstance(canon, dict):
        fail('canon', 'expected an object')
    identity = s.digest(canon)
    if expected_digest is not None and identity != expected_digest:
        fail('canon', 'reviewed digest mismatch')
    fields = {'action_type', 'purpose', 'mode', 'jurisdictions', 'condition_ids',
              'instruction', 'limitation_ids', 'companions', 'status',
              'schema_version', 'eligibility_ids', 'qualifier_ids'}
    service_fields = s._SERVICE_FIELDS | {'owner_id', 'numbering_context'}
    actions, services, owners = {}, set(), {}
    for group in s._GROUPS:
        records = canon.get(group, [])
        if not isinstance(records, list):
            fail(group, 'expected a list')
        for record in records:
            if not isinstance(record, dict):
                fail(group, 'expected service objects')
            key = s._slug(record.get('key'), group + '.key')
            if key in services:
                fail(key, 'duplicate service ID across canon groups')
            services.add(key)
            if 'actions' not in record:
                continue  # Legacy evidence never creates an action.
            if set(record) - service_fields:
                fail(key, 'unknown service fields')
            owner_id = s._slug(record.get('owner_id'), key + '.owner_id')
            owner = s._text(record.get('brand'), key + '.brand')
            service = s._text(record.get('name'), key + '.name')
            if owner_id in owners and owners[owner_id] != owner:
                fail(key, 'one owner identity has conflicting labels')
            owners[owner_id] = owner
            definitions = record['actions']
            if not isinstance(definitions, dict) or not definitions or len(definitions) > 64:
                fail(key, 'actions must be a bounded nonempty object')
            for local, definition in definitions.items():
                s._slug(local, key + '.action')
                rid = s.validate_route_id(key + ':' + local)
                if (not isinstance(definition, dict) or fields - set(definition)
                        or set(definition) - fields - {'source_url', 'checked_on'}):
                    fail(rid, 'unknown or missing restricted action fields')
                try:
                    template, channels = vocabulary.contract(definition['action_type'],
                        definition['purpose'], definition['mode'], definition['condition_ids'], definition['instruction'],
                        schema_version=definition['schema_version'], eligibility_ids=definition['eligibility_ids'],
                        qualifier_ids=definition['qualifier_ids'], limitation_ids=definition['limitation_ids'])
                except (ValueError, TypeError) as exc:
                    fail(rid, str(exc))
                relation = definition['instruction']['recipient_relation']
                roles = {'sending-bank-of-affected-transfer': ('own-bank', 'Your own bank'),
                         'reader-mobile-provider': ('own-mobile-provider', 'Your mobile provider')}
                if relation in roles:
                    role_id, label = roles[relation]
                    if (key, owner_id, owner, service) != (role_id, role_id, label, label):
                        fail(rid, 'relative recipient requires its exact closed role envelope')
                elif key in ('own-bank', 'own-mobile-provider') or owner_id in ('own-bank', 'own-mobile-provider'):
                    fail(rid, 'relative role cannot impersonate a fixed service operator')
                if not channels and any(f in record for f in s._DEST_FIELDS):
                    fail(rid, 'reader-held role cannot contain a fixed destination override')
                nations = definition['jurisdictions']
                if (not isinstance(nations, list) or not nations
                        or any(not isinstance(n, str) or n not in s._NATIONS for n in nations)
                        or len(set(nations)) != len(nations) or ('Global' in nations and len(nations) != 1)):
                    fail(rid, 'invalid jurisdiction set')
                # Global payment recovery and police intake are not modelled.
                if definition['purpose'] in ('police-report', 'payment-recovery') and 'Global' in nations:
                    fail(rid, 'purpose has no Global contract')
                if definition['schema_version'] == vocabulary.VERSION and set(nations) != set(s._NATIONS[:4]):
                    fail(rid, 'composed-SMS case requires its explicit four-nation scope')
                limits = definition['limitation_ids']
                if (not isinstance(limits, list) or not limits or len(limits) > 8
                        or any(not isinstance(x, str) or x not in vocabulary.LIMITATIONS for x in limits)
                        or len(set(limits)) != len(limits)):
                    fail(rid, 'unknown, missing or duplicate limitation IDs')
                if definition['mode'] == 'support' and not {'support-only', 'no-recovery-promise', 'no-money-recovery-guarantee'} & set(limits):
                    fail(rid, 'support requires a visible scope limitation')
                companions = definition['companions']
                if not isinstance(companions, list) or len(companions) > s.MAX_ROUTES:
                    fail(rid, 'companions must be a bounded ID list')
                for value in companions:
                    s.validate_route_id(value)
                if rid in companions or len(set(companions)) != len(companions):
                    fail(rid, 'self/duplicate companion')
                status = definition['status']
                if status not in ('active', 'withdrawn'):
                    fail(rid, 'unknown action status')
                source = s.validate_url(definition.get('source_url', record.get('source_url')), rid + '.source_url')
                checked = definition.get('checked_on', record.get('checked_on'))
                s._date(checked, rid + '.checked_on')
                destinations = []
                context = record.get('numbering_context', '')
                if not isinstance(context, str) or context not in ('', 'GB', 'international'):
                    fail(rid, 'invalid service numbering context')
                network = ''
                for channel in channels:
                    if set(channel) - {'field', 'kind', 'numbering_context', 'dialling_network_id'} or {'field', 'kind'} - set(channel):
                        fail(rid, 'channel may only select a canon field and kind')
                    field, kind = channel['field'], channel['kind']
                    context = channel.get('numbering_context', context)
                    network = channel.get('dialling_network_id', '')
                    if 'numbering_context' in channel and kind not in ('phone', 'shortcode', 'voice-shortcode'):
                        fail(rid, 'numbering context only applies to numeric channels')
                    if not isinstance(field, str) or field not in s._DEST_FIELDS:
                        fail(rid, 'unknown destination field')
                    if ((field.endswith('url') and kind != 'url') or (field == 'email' and kind != 'email')
                            or (field == 'sms' and kind != 'shortcode')
                            or (field == 'phone' and kind not in ('phone', 'voice-shortcode'))
                            or (field == 'phone_welsh' and kind != 'phone')):
                        fail(rid, 'destination field/kind conflict')
                    if field in ('info_url', 'navigation_url') and definition['mode'] not in ('navigation', 'verification'):
                        fail(rid, 'information/navigation field is not an intake')
                    if kind in ('phone', 'shortcode', 'voice-shortcode') and context not in ('GB', 'international'):
                        fail(rid, 'telephone destination needs an explicit numbering context')
                    value = s._destination(kind, record.get(field), rid + '.' + field)
                    if kind == 'phone' and (value.value.startswith('+') != (context == 'international')):
                        fail(rid, 'number syntax conflicts with numbering context')
                    if kind in ('shortcode', 'voice-shortcode') and context != 'GB':
                        fail(rid, 'shortcode requires GB context')
                    destinations.append(value)
                conditions = tuple(sorted(definition['condition_ids']))
                limits = tuple(sorted(limits))
                # Compatibility attributes are derived trusted language only.
                composed = definition['schema_version'] == vocabulary.VERSION
                extra = {}
                if composed:
                    case_id = definition['instruction']['sms_composition_case_id']
                    extra = {'sms_composition_case_id': case_id,
                             'sms_composition': vocabulary.sms_composition(case_id)}
                action_class = s.ComposedSmsAction if composed else s.Action
                actions[rid] = action_class(rid, owner, service, definition['purpose'], definition['mode'],
                    tuple(n for n in s._NATIONS if n in nations), tuple(destinations),
                    definition['action_type'].capitalize() + ' — ' + service,
                    vocabulary.READER_METHODS.get(template, ''),
                    tuple(('condition', vocabulary.CONDITIONS[x]) for x in conditions),
                    tuple(vocabulary.LIMITATIONS[x] for x in limits), tuple(sorted(companions)), status, source, checked,
                    owner_id, key, definition['action_type'], template, conditions, limits, context,
                    channels[0]['field'] if channels else '',
                    schema_version=definition['schema_version'],
                    eligibility_ids=tuple(sorted(definition['eligibility_ids'])),
                    qualifier_ids=tuple(sorted(definition['qualifier_ids'])),
                    recipient_relation=relation, payload_profile_id=definition['instruction'].get('payload_profile_id', ''),
                    dialling_network_id=network, resolution_kind=definition['instruction']['kind'], **extra)
    for action in actions.values():
        if type(action) is s.ComposedSmsAction:
            row = action.sms_composition
            if (row.provider_scope_id != 'o2-uk-mobile-line' or row.provider_owner_id != 'o2'
                    or owners.get(row.provider_owner_id) != 'O2'):
                fail(action.route_id, 'composed SMS requires the canonical O2 provider identity')
            s.validate_composed_sms(action)
        for companion in action.companions:
            if companion not in actions or actions[companion].status != 'active':
                fail(action.route_id, 'unknown/withdrawn companion')
    attributions = validate_relationships(canon.get('destination_relationships', []), actions)
    actions = {rid: replace(action, attributions=tuple(sorted(attributions.get(rid, ()))))
               for rid, action in actions.items()}
    return s.Catalog(identity, MappingProxyType(actions))


def validate_relationships(relationships, actions):
    import reporting_structured as s
    if not isinstance(relationships, list) or len(relationships) > 64:
        s._fail('destination relationships', 'expected a bounded list')
    by_identity, permits, seen = {}, [], set()
    covered_pairs, alias_identities, attributions = set(), set(), {}
    for action in actions.values():
        for d in action.channels:
            by_identity.setdefault(destination_identity(d, action.numbering_context, action.dialling_network_id), []).append(action)
    for relationship in relationships:
        fields = {'id', 'type', 'operator_owner_id', 'members', 'source_url', 'checked_on', 'status', 'attribution_id'}
        if not isinstance(relationship, dict) or set(relationship) != fields:
            s._fail('relationship', 'unknown or missing fields')
        key = s._slug(relationship['id'], 'relationship.id')
        if key in seen:
            s._fail(key, 'duplicate relationship')
        seen.add(key)
        if relationship['type'] not in ('shared-service', 'delegated-intake', 'geographic-routing', 'alias'):
            s._fail(key, 'unknown relationship type')
        if relationship['status'] != 'active':
            s._fail(key, 'unverified or inactive relationship')
        if relationship['attribution_id'] != 'operated-by':
            s._fail(key, 'unknown or absent operator attribution')
        s.validate_url(relationship['source_url'], key + '.source_url')
        checked = s._date(relationship['checked_on'], key + '.checked_on')
        from datetime import date, timedelta
        if not date.today() - timedelta(days=90) <= checked <= date.today():
            s._fail(key, 'relationship evidence is future or expired')
        members = relationship['members']
        if not isinstance(members, list) or not 2 <= len(members) <= 16:
            s._fail(key, 'expected two to sixteen exact members')
        selected = []
        for member in members:
            if not isinstance(member, dict) or set(member) != {'route_id', 'owner_id', 'purpose', 'jurisdictions', 'destination_field', 'destination_identity'}:
                s._fail(key, 'relationship member must bind the full scope')
            action = actions.get(member['route_id'])
            if (action is None or action.status != 'active' or len(action.channels) != 1
                    or member['owner_id'] != action.owner_id or member['purpose'] != action.purpose
                    or member['jurisdictions'] != list(action.jurisdictions)
                    or member['destination_field'] != action.destination_field
                    or member['destination_identity'] != list(destination_identity(action.channels[0], action.numbering_context, action.dialling_network_id))):
                s._fail(key, 'relationship member differs from its active contract')
            selected.append(action)
        if len({a.route_id for a in selected}) != len(selected):
            s._fail(key, 'duplicate relationship member')
        if relationship['operator_owner_id'] in ('own-bank', 'own-mobile-provider'):
            s._fail(key, 'relative recipient cannot be a named relationship operator')
        if relationship['operator_owner_id'] not in {a.owner_id for a in selected}:
            s._fail(key, 'operator must be one of the explicit owners')
        identities = {destination_identity(a.channels[0], a.numbering_context, a.dialling_network_id) for a in selected}
        if len({i[0] for i in identities}) != 1:
            s._fail(key, 'cross-kind aliases are forbidden')
        if relationship['type'] != 'alias' and len(identities) != 1:
            s._fail(key, 'shared destination identities differ')
        if relationship['type'] == 'alias' and len(identities) < 2:
            s._fail(key, 'alias must bind distinct identities')
        if relationship['type'] == 'alias':
            if identities & alias_identities:
                s._fail(key, 'overlapping alias chains/cycles require one complete identity group')
            alias_identities.update(identities)
        for left, right in combinations(selected, 2):
            pair = frozenset((left.route_id, right.route_id))
            if pair in covered_pairs:
                s._fail(key, 'duplicate or contradictory overlapping relationship')
            covered_pairs.add(pair)
        operator = next(a.owner for a in selected if a.owner_id == relationship['operator_owner_id'])
        for a in selected:
            if any(old_operator != operator for _, old_operator in attributions.get(a.route_id, [])):
                s._fail(key, 'one action has contradictory responsible operators')
            attributions.setdefault(a.route_id, []).append((key, operator))
        permits.append(frozenset(a.route_id for a in selected))
        # Alias closure: every action on every identity must itself be an
        # explicit member or separately covered. No transitive owner inheritance.
        for i in identities:
            for j in identities:
                if i != j:
                    for left in by_identity.get(i, []):
                        for right in by_identity.get(j, []):
                            if {left.route_id, right.route_id} - permits[-1]:
                                s._fail(key, 'alias omits an action using this identity')
    for values in by_identity.values():
        for left, right in combinations(values, 2):
            same = (left.owner_id, left.service_id, left.jurisdictions, left.purpose, left.mode) == (right.owner_id, right.service_id, right.jurisdictions, right.purpose, right.mode)
            if not same and not any({left.route_id, right.route_id} <= p for p in permits):
                s._fail(right.route_id, 'normalized destination collision requires an explicit evidenced relationship')
    return attributions
