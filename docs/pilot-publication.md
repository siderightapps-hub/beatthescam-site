# Restricted pilot approval and artifact verification

WP3C9K-R6B2 model compatibility closure, 22 October 2026. The six WP3D9E
contracts retain their exact v2 semantics and evidence clearances. The operator
authorized the deterministic R6B model-pin update after full six-contract
compatibility checks. Actual contract eligibility is exactly six. The composed-SMS
model still requires the independent WP3D9K-R6B security review before adoption.
No public page is migrated or approved; O2/Ofcom caller-SMS contracts remain held.
No production trust, page scope, release baseline or platform setting changes.

## Contract eligibility and publication authority

`reporting_eligibility.contract_production_eligible_ids` and
`is_contract_production_eligible` check the closed schema, active status, evidence
freshness, exact six-ID clearance, and reviewed whole-canon/model digests. They
read no signing store or runtime environment. The digests are reviewed source-data
baselines, not cryptographic reviewer roots or production activation. They cover
provenance and held cases as well as definitions; changing any canon/model bytes
requires a new independently reviewed baseline. Never automatically refresh them
from candidate content. Endpoint values remain solely in the canon.

`publication_endorsed_ids` additionally requires the existing contracts-role
signature. The historical `eligible_ids` API remains an alias for this stricter
publication prerequisite. `verify_contract` verifies that signed endorsement
alone; production callers use `require_actions` to require both layers.
The inventory reports `contract_production_eligible`,
`publication_endorsed_contracts`, and `test_endorsed_contracts` separately.

`reporting_publication.is_page_publication_eligible` additionally checks the exact
page, permitted plan and role-correct signed context under production authority.
It always returns false for test environments and frozen legacy pages. A passing
page predicate is only a source-page approval, not output/deployment approval.
`reporting_pilot.verify_release`, `verify_bundle` and `netlify_verify` retain the
signed exact-output, source/dependency, trust/runtime and deployment-hook checks.
Their local results do not attest remote GitHub/Netlify settings. The six contract evidence
clearances therefore coexist with zero approved public pages and no deployment
clearance. The generator still requires publication endorsements and separately
authorized resumption; contract eligibility alone cannot activate drafting.

## Explicit v2 action contracts

The earlier WP3C9D2 extension supplied model infrastructure. WP3C9F subsequently
implemented C02, C03, C07, C08, C09 and M10 after independent evidence clearance.
C01, C04, C05 and C06 remain evidence-incomplete; M04 and M05 retain residual
model gaps. Emergency/physical safety M07, image workflows and conditional
multi-operator routing remain deferred. No jurisdiction or relationship-schema
extension is included.

Unchanged explicit v2 actions require `schema_version: restricted-actions/v2`, bounded
`eligibility_ids` and `qualifier_ids` lists, and `instruction.recipient_relation`.
Selected email/SMS methods require `instruction.payload_profile_id`; every other
method forbids it. Only the O2 voice-shortcode method requires
`instruction.channels[0].dialling_network_id: o2-uk`; other methods forbid it.
All fields are exact and recursively closed. Sets contain at most eight unique
registered strings. Old explicit definitions reject, rather than being upgraded.
Legacy canon records without actions still produce no action IDs.

The five new code-owned registries are `ELIGIBILITY`, `QUALIFIERS`,
`RECIPIENT_RELATIONS`, `PAYLOAD_PROFILES` and `DIALLING_NETWORKS` in
`scripts/reporting_actions.py`. Their methods fix allowed combinations; a known
ID used in another semantic category or incompatible method rejects. Existing
customer/age/platform predicates move into eligibility in synthetic v2 fixtures;
no production migration or new age semantics is implied. Conditions explain when,
eligibility who, limitations excluded outcomes, and qualifiers required cost,
availability or access details. All are rendered with every complete action.

Service `note` is internal evidence metadata. The 43 historical inventory fields
called `current_visible_qualifier` copied these notes; they are not visibility
proof and are never automatically converted to qualifier IDs or output. Preserve
the original inventory and notes. A later inventory correction must separately
record observed page visibility with rendered evidence.

Bank methods require an already-made suspected fraudulent authorised transfer,
`sender-own-account` and `sending-bank-of-affected-transfer`. The card method
selects only the contact number on the sending bank's card for that account.
The app method also requires `banking-device-safe` and displays the exclusion.
The locked `own-bank` role cannot carry any fixed endpoint, alternative search
rule or free recipient name. Both display the money-only no-guarantee limit.
The renderer supplies immediate timing, rather than accepting an urgency field.

Caller-number reporting uses `report`, `suspicious-mobile-call`,
`recipient-mobile-line`, the locked `own-mobile-provider` role and
`caller-number-from-recent-calls-sms`. It copies the number from recent calls
into a newly composed SMS to a canon shortcode. It never forwards an original
message or treats Ofcom as the recipient. The generic v2 method adds no prefix.
It does not assert that a prefix is forbidden or unnecessary on every provider. Relative role
records cannot be named operators of sharing relationships.

Voice shortcodes have a distinct namespace `(kind, numbering_context, network,
digits)` and require canonical ASCII digits, GB numbering context and the O2
network/plan method. Their complete instructions show the required originating
line; they receive no automatic tel link. The exact code/plan/owner pairing needs
evidence review and is signature-bound. Future O2 definitions need two separate
service records for the two codes, with one verified owner, not `phone_welsh`.

The original-email profile differs from the original-message-file profile. The
latter supplies the fixed new-email/subject/attachment sequence; it does not ask
for an attachment embedded in the suspicious message. No arbitrary message body,
subject, evidence object, transfer reference or workflow steps are admitted.

Contract evidence uses `beatthescam-contract-evidence-v3`, contextual approval
`beatthescam-publication-v4`, output `pilot-output/v4`, and release
`beatthescam-pilot-release-v4`. The trust root remains `bts-trust/v1`. Old versions
fail, including genuinely signed old packets; no dual verifier is available.
Contract claims bind the complete normalized Action, full canon, schema and a
model digest over the five model/validator/renderer/syntax files. Context and
manifest bind the same protection-first ordered plan (bank first, then route ID).
Literal hours, subject or renderer changes invalidate existing evidence as well
as context/release approval. Canon notes are nonoperational but still covered by
full-canon identity.

`reporting_action_tool.py inspect --route-id ID` validates the canon and shows
read-only semantics and the complete renderer output. It cannot create evidence
or eligibility. `list` distinguishes contract clearance from test and production
publication endorsements. Generator
descriptors contain closed semantics only, and the sole writable choice is the
complete eligible route ID. Unknown IDs or overrides are retained for rejection;
zero production publication endorsements stops the request before any model call.

## Bounded v3 composed SMS

Only `instruction.sms_composition_case_id: o2-call-then-caller-number` is new
canon input. `SMS_COMPOSITION_CASES` contains one immutable code-owned row:
O2 UK mobile line (`o2-uk-mobile-line`, canonical owner `o2`), `call-prefix`
rendered as `Call`, then one space and the existing typed caller-number object.
The site accepts no actual caller number, prefix/body/provider/order input or
runtime registry additions. The relative recipient remains Your mobile provider;
canonical O2 identity is an additional required anchor, never the endpoint owner.
The exact existing `sms` / `shortcode` / `GB` selection supplies the destination.
Shape-valid digits confer no evidence or publication authority.

V3 is accepted only for this complete case. V2 rejects the new selector and keeps
its original grammar/Action serialization. Missing/null/unknown selectors fail;
there is no parse fallback, inferred recipe or automatic schema migration.
`ComposedSmsAction` adds a required case ID and complete frozen row. Both appear
in action/plan hashes and therefore contract, context, manifest and artifact
bindings. The current model envelope is `restricted-actions/v3`; every action
retains its own explicit schema version. Old signed envelopes cannot be consumed.

All main, summary, FAQ, plain and FAQ schema occurrences retain the visible O2
scope and exact operation. Generic caller-SMS and O2 composed caller-SMS cannot
be selected together, including in placements. O2 support contracts, Ofcom
provenance, sibling brands, citations and raw prose cannot select the case.
Generators select only complete endorsed route IDs; descriptors are read-only.
Invalid extra fields survive normalization and fail before any writer mutation.

No real v3 contract is installed. The six reviewed IDs/canon digest, old model
pin and public trust digest remain fixed. A separate independent compatibility
review must explicitly accept an immutable new model digest before a separately
recorded six-only pin update. Test-only hypothetical pin acceptance is not that
review. R5's eighteen identities and three source decisions remain unresolved;
the existing phone-hub 7726 purpose mismatch remains a legitimate gate block.

## Trust and separation

Use one controlled reviewer account/workstation separate from the authoring and
generation environment. Keep the Ed25519 private keys there, owner-readable only,
outside the repository and verification store. Do not run unreviewed candidate
code on that workstation. Review the verifier/signing code before using it.
Generation and build hosts receive only public roots and signed decisions. Never
put a private key in GitHub/Netlify variables, secrets, logs, content, artifacts
or generated output. This package does not configure or rotate real keys.

Three roles have distinct signature domains: `contracts` approves exact evidence
claims, `context` reviews a page, and `release` approves exact output. Roles can
belong to the same responsible human; separate keys reduce accidental scope
confusion. The author/model/build must not possess those keys. Human authority is
key custody and an explicit reviewed operation, not a `trusted: true` field or a
passing validator. CI/Netlify production signing is prohibited by the signer.

The verifier defaults to production. Test mode requires an explicit
`BTS_REVIEW_ENVIRONMENT=test`, a test-labelled trust root, a test-labelled signed
body and a test SSH namespace. The production deployment entry points refuse
test mode. Fixture keys are temporary fake credentials, not production roots.

## Verification store (public material only)

`BTS_REVIEW_STORE` is an operator-owned absolute real directory outside the repo.
No symlinks or hard-linked authority files are admitted. The store root and
protected files must be owned by the verifier user without group/world write;
the operator must also secure ancestor directories and ACLs on the trusted host.
The verifier does not audit every ancestor's owner or ACL. Its files are:

- `trust.json`: exact `bts-trust/v1` schema with `environment`, `site`, three
  `roles`, `pilot_page_ids` (one to seven exact `guide:slug`/`hub:slug` identities
  when a release is enabled), `baseline_sha256`, and `revocations_sha256`.
- Each role contains one or more `{identity, public_key}` records; keys use
  `ssh-ed25519 BASE64` without options or comments.
- `baseline.json`: an explicit relative-path → SHA-256 map of reviewed unchanged
  non-pilot dist files. `baseline_sha256` is the canonical JSON digest of this
  map. A reviewer must establish this baseline, not infer trust from current
  unreviewed output.
- `revoked.json`: decision IDs that must not verify; an empty list is explicit.
  Its canonical JSON hash must equal `revocations_sha256`. A revocation update
  requires an operator-controlled trust-root update and a new external pin;
  replacing this public file with an older list cannot restore a decision.
  The new policy also invalidates prior release manifests. Removing a compromised
  public key from its role requires the same external enrollment update.
- `contracts/<sha256(route-ID)>.json`: signed exact contract evidence packets.
- `packets/<sha256(page-ID)>.json`: signed exact contextual review packets.
- `release.json`: signed release manifest, installed only after output review.

Production additionally requires `BTS_PRODUCTION_TRUST_SHA256`, the canonical JSON
digest of `trust.json`, configured **outside Git**. The signature never chooses
its own trusted public key. A changed enrollment, baseline or pilot list requires
an operator trust-pin update and fresh release approval. Do not derive that pin
from a candidate checkout in CI. Treat revocation files as current release inputs;
the operator must update them and remove compromised keys from the externally
pinned configuration when necessary. Do not reuse an old verification bundle
after a revocation event.

The allowed JSON schema is defined in `scripts/reporting_trust.py`. An incomplete
root fails closed. `reporting_fixture_review.py` shows only a disposable **test**
root; do not copy or promote its keys into production.

## Review flow

1. Complete factual evidence and the closed action contract in a separately
   reviewed future change. `reporting_eligibility.claims` resolves the entire
   contract and binds its owner/service, purpose, method, endpoints or closed
   destination-free method, scope, conditions/eligibility, limitations, derived
   qualifiers and sharing attribution. The exact model and renderer files are bound by contract evidence as well as
   page/release implementation dependencies. Source
   URL/date alone do not confer authority.
2. A contract reviewer runs `reporting_action_tool.py issue-contract-reviewed`
   with `--human-reviewed --route-id ID --reviewer ID --private-key EXTERNAL`.
   Install the public packet in the corresponding contracts file. No unsupported
   grammar, missing evidence or old signature becomes eligible by page approval.
3. Prepare the exact page and action selections. The context reviewer runs
   `reporting_action_tool.py issue-reviewed` with `--human-reviewed`, the page,
   page ID, reviewer, audience and external private key. Install the packet in
   `packets/`. Whole-page approval never waives the prose/action boundary.
4. Use the real authenticated writer/build path. Rejected drafts fail before
   replacement; configure the writer's quarantine directory when retaining an
   audit record is needed. Build once in the controlled candidate environment.
5. `python3 scripts/reporting_pilot.py candidate --artifact /absolute/dist`
   recomputes the manifest. It validates every selected action's evidence,
   reauthenticates each page, rerenders selected pages with the actual build
   primitives and compares exact bytes. All structured pages must be explicitly
   enrolled; non-pilot raw records must remain in the frozen legacy snapshot.
6. The release reviewer inspects the full pages, manifest, action plans and input
   changes, then uses `reporting_pilot.py issue-reviewed --human-reviewed
   --reviewer ID --private-key EXTERNAL --artifact /absolute/dist`.
   This emits a public signed packet; it neither installs nor publishes it.
7. `reporting_pilot.py bundle --packet RELEASE --artifact /absolute/dist
   --bundle /external/new-bundle.zip` verifies and captures the exact bytes into a
   deterministic, uncompressed ZIP. It returns the ZIP SHA-256. Existing output
   files are never overwritten. Immediately before an authorized transfer use
   `verify-bundle --packet RELEASE --bundle FILE`; deploy those exact ZIP bytes,
   not a separate rebuild. No upload/deploy command is provided here.

`inventory` lists derived contract eligibility. `status` lists current structured
surfaces and attempts the same production deployment verification; a hold returns
nonzero with its reason. `test-verify-bundle` is explicitly non-production and
never reports production deployment eligibility.

## What is approved

The release manifest has explicit page records, each with page ID, output path,
source digest, selected route IDs, full resolved action-plan digest, contextual
packet digest and HTML digest. It also binds the canon, implementation/runtime
dependencies, trust policy, relevant input-tree digest, and the exact path/hash
map of every artifact file. No wildcard approval is accepted.

Only the enrolled page paths may differ from the external baseline. Everything
else, including assets, redirects, RSS/search exports and legacy pages, must be
byte-identical to that baseline. An eighth page, deletion, stale asset or extra
action block fails. A pilot that needs changes to shared exports/assets needs a
separately reviewed baseline/scope decision; do not silently exclude those files.

The relevant input digest covers scripts, content, templates, assets, static,
Netlify Functions, workflows and dependency/configuration files. Python caches
are excluded from **source** inputs only. Nothing is excluded from artifact
bytes. Verification material is bound by its own signatures/digests, avoiding a
release-packet self-reference. Ordinary docs do not determine rendering.

There is **no HTML normalization**. Timestamped `humans.txt`/`security.txt`, UTC
year changes, Pillow/minifier differences, optional libraries and asset hashes
can affect output. Frozen non-pilot bytes may be reused; selected HTML must match
the actual renderer. Any difference requires a fresh candidate/review, not an
allow-list of arbitrary ignored bytes. Publication dependencies bind exact
Python patch, idna and Unicode versions; use the same pinned environment for
review and verification. The current CI `3.12` selector is not a reproducible
patch pin and must match the chosen signer runtime before real enrollment.

Page, evidence and release decisions expire within seven days and support
revocation. Canon changes invalidate page/contract/release bindings, including
destination, owner, purpose, eligibility and qualifiers. Source changes or
artifact A/B substitution fail. Verifiers capture immutable byte snapshots,
reject path traversal/symlinks/nonregular archive entries, and check source and
artifact stability around rendering. This assumes a trusted verifier host; it
does not defend against arbitrary concurrent code execution as the same user.

## GitHub and Netlify activation

The uncommitted Netlify build command now installs the verifier dependency and
runs `reporting_pilot.py netlify-verify`; it does **not** rebuild or sign. Missing
configuration is an intentional deployment hold, including legacy-only releases.
The old build-ignore shortcut was removed. No existing live setting was changed.

For a future authorized release, place only public verification material under
`deployment/review-store/` and configure the external trust pin in Netlify's
production context. The hook copies that public material into a private temporary
directory and verifies the exact committed dist. It prints the canonical ZIP
digest and manifest digest, then rereads dist to detect mutation during checking.
Public verification material is outside dist and is not shipped to visitors.
Keep Netlify post-processing disabled for these approved pages; verify actual
publish directory/build-command behavior before pilot release. A privileged
operator can bypass repository configuration via a manual deploy; protect that
account and require the same verified ZIP procedure.

GitHub's separate `pilot-artifact` job uses the public external pin from repository
variables and has no signing/deploy secrets, write permission or persisted checkout
credentials. It runs on the existing PR/push triggers, with no schedule or release
action. Missing trust enrollment intentionally blocks it. Existing offline tests
use fake keys. No `pull_request_target` or privileged artifact-follow-up flow was
added. Required-check/branch protections and Netlify account restrictions need
operator activation and independent verification; no account settings changed here.

Sources for the integration design: [GitHub secure-use guidance](https://docs.github.com/en/actions/reference/security/secure-use)
and [Netlify file configuration](https://docs.netlify.com/build/configure-builds/file-based-configuration/).

## Later WP3E post-deploy check (design only)

Record the verified ZIP SHA-256 and the platform's resulting immutable deploy ID.
Use that deploy-specific origin first, then the canonical origin. Fetch only the
one-to-seven approved page URLs and referenced frozen assets; require expected
HTTP status, canonical path and exact decoded-response byte hashes. Standard
HTTP content decoding is transport handling, not HTML normalization. Compare
resolved ACTION destinations and visible qualifiers with the manifest/approved
render, and enumerate unexpected operational links/blocks. A byte mismatch is a
hold/rollback investigation, not permission to ignore CDN rewriting. If a platform
transform is unavoidable, review a narrowly specified projection verifier before
release; this package supplies no normalization escape hatch. Do not crawl or
request indexing as part of this bounded check.

Production activation, evidence completion, pilot selection/migration, signers,
trust enrollment, real approvals, deployment and post-deploy checks remain
separate operator-authorized work. Passing infrastructure tests is not that
authorization, and WP3A generation/social containment remains in force.


## WP3C9G1: explicit receipt signing (not activated)

The old `issue-reviewed` / `issue-contract-reviewed` CLI entrypoints now refuse.
Use `scripts/reporting_reviewer.py prepare` and `sign`. Neither installs a root,
updates an external pin, approves a held contract, uploads, or deploys. Production
still has no enrolled reviewers or approved public pages.

Use trusted reviewed code in the separate signer account. Select CPython from
`.python-version`, Node from `.nvmrc`, the npm version in `package.json`, and set
`TZ=UTC LC_ALL=C LANG=C PYTHONUTF8=1`. Install the verification-only dependency
with `python -m pip install --require-hashes --only-binary=:all: -r
requirements-reporting.lock`; the model SDK is unnecessary. Run
`python scripts/reporting_runtime.py` before review. The runtime policy binds the
lockfiles; changes require review and invalidate existing receipts/approvals.

Set `BTS_REVIEW_STORE` to the external public store and, for future production,
set its independently approved `BTS_PRODUCTION_TRUST_SHA256`. Never calculate an
authoritative expected pin from candidate code. Use exact absolute paths.

Example future contract review (placeholders; no production signing authorized):

```sh
python scripts/reporting_reviewer.py prepare --environment production --role contracts --candidate /absolute/reviewed/checkout --reviewer CONTRACTS_ID --route-id EXACT_CLEARED_ID
```

Review the complete JSON receipt: candidate input hash, exact role and principal,
public-key fingerprint, environment, canon/model/runtime/dependencies, enrolled
scope, contract claims and rendered action wording. Retain its receipt digest.
Then repeat those exact options with `sign`, adding `--expected-receipt-sha256
REVIEWED_DIGEST --key-file /absolute/external/key --output /absolute/external/new-packet.json`.
A real production operation displays the receipt and requires typing the full
confirmation phrase at a local terminal. CI cannot sign. There is no production
`--yes` option. The expected digest must come from the reviewed receipt, not an
inline recalculation in the signing command. Source, policy and artifact are
recomputed before signing and again before packet export.

For `--role context`, supply `--page /absolute/page.json --page-id guide:exact-slug
--audience England Wales` with the actually reviewed audience. This is a complete
source/action receipt, not an unauthenticated full production-page preview.
The page must be within the external enrolled scope and every action needs both
independent clearance and a contracts-role endorsement. Numeric factual
exceptions are conservatively unsupported by this small CLI. No autoapproval.

For `--role release`, supply `--artifact /absolute/exact-artifact` and
`--candidate-sha EXACT_COMMITTED_SOURCE_SHA`. Working bytes must match the exact
commit; release packets are detached from that commit. See
`docs/publication-enforcement.md` for the immutable approval-transport workflow. The receipt
contains the complete recomputed manifest, every output hash and canonical ZIP
hash. Missing artifact paths never default to `dist`. Context packets and all
contracts are independently reverified. Verify/exported packets are public data
only. Export uses exclusive creation and cannot overwrite an existing packet.
Installation into the appropriate public verification store remains a separate
reviewed operation; the signer does not install authority or change pins.

External keys must be absolute, owner-only regular files, outside every Git
checkout/worktree. Production rejects paths named as test/fixture/synthetic keys.
An encrypted key may be unlocked in the dedicated review account's short-lived
`ssh-agent`; `--key-file` can then reference its owner-only public `.pub` file.
No private key/passphrase or agent socket goes to CI, Netlify, a generator, or an
AI account. Local code/host isolation remains necessary: pathname checks do not
protect against arbitrary code already running as the signing account.

`python scripts/reporting_reviewer.py` defaults to a read-only dry-run report.
It reports runtime/trust/deployment holds and never grants a deploy capability.
`python scripts/reporting_preflight_selftest.py` creates disposable TEST authority
and a synthetic copy outside the repository, with a credential-free worker
environment. `test-verify-bundle` additionally checks the real independent
contract predicate, returns `deployment_eligible:false`, and cannot publish.
TEST signatures must never be offered as production authority.

Repository CI and Netlify pins are prepared, not activated. Netlify's authenticated
15 October inspection found its build command unset and its Git-only production
restriction off. The available Git-only control also forbids direct preview
promotion according to provider documentation; rollback/current-policy behavior
and the trusted-owner boundary still require a separately authorized acceptance
exercise. No settings were saved. See the G1 review packet for exact gaps.

Protected review must cover these surfaces together. This is an ownership map,
not active GitHub protection or a substitute for a human reviewer:

| Surface | Required review responsibility |
|---|---|
| `scripts/reporting_trust.py`, reviewer/publication/pilot/runtime modules and tests | Trust, key custody, canonical payload, runtime and exact artifact controls |
| `content/sources.json`, action schema/model, independent eligibility constants | Independent factual/contract review; signatures cannot grant clearance |
| `deployment/review-store/` public material and external pin changes | Owner-validated public fingerprints, scope, baseline and current revocations |
| `.github/workflows/`, future CODEOWNERS, runtime selectors and dependency locks | Execution authority, secret isolation, required-check identity and reproducibility |
| `netlify.toml`, Function source, templates/assets and served `dist/` | Effective deployment boundary, rendering, routing and provider output evidence |

The inspected repository has one owner/admin collaborator and no required review
rules. A future owner-authored control PR needs another eligible reviewer. Do not
invent a second account, share credentials or use a bot/admin bypass. Add the
agreed CODEOWNERS identities only after that arrangement is settled.

The verifier profile deliberately excludes Pillow and minifiers: selected-page
verification consumes already captured CSS/JS. It is not a reproducible full-site
asset/OG-image build profile. Full builds remain held by the pre-existing hub
preflight, and optional rendering packages/fonts still need a separate frozen
profile. Neither a successful synthetic render nor unchanged legacy pages clears
that full-build prerequisite.
# Offline provider handoff and readback (WP3C9G2)

`scripts/reporting_provider.py` prepares a non-secret handoff only after current
contract/context/release authentication and exact artifact verification. Select
`--environment` explicitly; TEST authority remains TEST. The command does not
deploy, collect credentials, fetch URLs, enroll a root or issue signatures.

The record binds the actual candidate input digest, declared full Git revision,
release packet/manifest/archive hashes, runtime, every artifact path/hash,
expected HTTP paths, HTML event projections, Netlify configuration, Function
source map and npm lock. The source revision is checked against immutable Git objects, the exact working
file map and the signed release revision. Dirty candidates and another commit
with identical output reject. The release packet remains outside the source
commit to avoid a signature/commit circular dependency.

The target JSON has exactly `site_id` (UUID), `team_id` (24 lowercase hex digits),
`project` (Netlify slug) and `production_origin` (`https://beatthescam.com`).
Provide owner-verified values. Do not infer the target from a deployment token.

After a separately authorized release, an independent trusted collector can
capture response bodies for every `served_paths` entry at both the immutable
deploy origin and the canonical origin. The verifier itself stays offline:
it reads `capture/deploy/<artifact-path>` and
`capture/production/<artifact-path>` plus a public observation JSON. HTTP
transfer decompression is permitted before capture; body bytes are otherwise
unchanged. No arbitrary HTML, timestamp, query, script or whitespace exclusion
is allowed. `_redirects` and `_headers` are provider instructions, not HTTP files;
their bytes remain in the approved artifact map and require separate effective
configuration checks. `index.html` maps to its directory URL. Other files retain
their literal paths; unexpected redirects hold acceptance.

Observation schema: `version: bts-provider-observation/v1`, `site_id`, `team_id`,
`deploy_id`, `source_revision`, `candidate_inputs_sha256`, `manifest_sha256`,
`canonical_archive_sha256`, and `responses`, with exactly `deploy` and
`production` maps. Each map contains every served artifact path with exactly
`url`, `status` and `sha256`. Status must be 200. The immutable origin is
`https://<24-hex-deploy-id>--<project>.netlify.app`; canonical origin is the
owner-verified target. `expected_observation()` documents the schema for TEST
fixtures, **not a collector or evidence generator**. Record actual observations;
copying expected values is not a readback. Association fields such as the
manifest hash come from the retained handoff, not a claim that Netlify supplies
an authenticated manifest attestation.

Future commands, from the reviewed candidate with the measured runtime and
explicit external public trust configuration:

```text
python scripts/reporting_provider.py prepare --environment production --artifact /absolute/artifact --packet /absolute/release.json --target /absolute/target.json --source-revision FULL_40_HEX_REVISION --output /absolute/new/handoff.json
python scripts/reporting_provider.py compare --environment production --artifact /absolute/artifact --packet /absolute/release.json --target /absolute/target.json --source-revision FULL_40_HEX_REVISION --handoff /absolute/handoff.json --expected-handoff-sha256 RETAINED_REVIEWED_DIGEST --observation /absolute/observation.json --capture /absolute/capture --expected-deploy-id OWNER_OBSERVED_DEPLOY_ID
```

Retain the handoff digest independently before transfer; do not recompute the
expected digest from a received record. Export is exclusive, external and
owner-controlled. Comparison reauthenticates current authority/expiry/revocation,
recomputes the handoff, and checks artifact/capture changes before success. Any
missing/extra/stale/changed file, action, qualifier, bank wording, method,
observation identity or URL fails. The HTML projection preserves ordered tags,
attributes and text; it is a diagnostic alongside mandatory exact-byte equality,
not an HTML sanitizer or permission to accept altered output.

`static_readback: PASS` means only that the supplied captures match the currently
authenticated static artifact. `deployment_eligible` stays false and
`production_acceptance` stays HOLD: collector provenance, provider-compiled
Functions, effective headers/routing/Pretty URLs, integrations and current
account controls need independent platform evidence. The static ZIP cannot
attest executable provider bundles. No production readback is authorized by
these examples. Never paste private keys, passphrases, PATs, deploy tokens,
build-hook secrets, recovery codes or 2FA codes into chat.
