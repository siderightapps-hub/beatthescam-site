"""Historical parser regression adapter; diagnostic results are not releases.

New/changed input must use content_gate.run_gate and authenticated publication.
These old suites specifically exercise the retained legacy parser's decisions.
"""
import content_gate as gate


def diagnostic_gate(post, *, use_llm=False, is_draft=True, is_hub=False, corpus=None, **kwargs):
    if use_llm:
        raise ValueError('legacy regression fixtures are offline only')
    issues = gate.check_deterministic(post, is_draft=is_draft, is_hub=is_hub)
    issues += gate.check_similarity(post, corpus)
    return gate.GateResult(slug=post.get('slug','?'),
        passed=not any(i['severity']==gate.SEVERITY_BLOCK for i in issues), issues=issues,
        reporting_mode=gate.structured.LEGACY_DIAGNOSTIC, publication_ready=False)
