# Repository publication-verification prerequisite

Status: IMPLEMENTED PREREQUISITE + REMOTE ENFORCEMENT REQUIRED. This document
does not activate protection or authorize publication. The production scope is
empty, baseline unestablished and approvals absent. The ordinary hub gate also
blocks the current candidate. These are intentional nonzero outcomes.

## Required-check interface

- Workflow: `Publication verification`, `.github/workflows/publication-verification.yml`.
- Single fixed job/check: `Trusted publication verification` (job ID `publication`).
- Future required status context: exactly `Trusted publication verification`.
  Verify the actual GitHub check-run context and GitHub Actions app ID during a
  separately approved installation; no remote run has established them yet.
- Only PRs targeting `main` and pushes to `main`; no path filters, conditional
  success, matrix, manual dispatch, reusable call, `workflow_run` or
  `pull_request_target`. JSON syntax in the `.yml` file is valid YAML and permits
  precise offline structural tests without an additional parser dependency.
- PASS = exit 0; BLOCKED = exit 1; unexpected ERROR = exit 2. Dependency/setup
  failures also fail the job. Verification never deploys or creates approvals.

## Trusted implementation and candidate data

For a PR, the implementation is checked out at the event's exact base SHA and
the candidate at its exact head SHA. For a push, the implementation is the exact
`before` SHA and candidate the event SHA. Missing, zero or malformed SHA fails.
The trusted revision must already contain this reviewed adapter: installing or
updating the control plane is a separate human-reviewed maintenance operation,
under a verified publication freeze. The first PR cannot approve its own new
verifier. Never change to a moving branch or candidate implementation to unblock it.

All three checkouts disable persisted credentials, submodules and LFS. Only trusted
runtime selectors and dependency locks are used; Python runs with `-I`, Node
installation uses `npm ci --ignore-scripts`. All third-party Actions use full
commit pins. The adapter reads candidate Git blobs by immutable object ID,
rejects symlinks/submodules/noncanonical paths and bounds files/bytes. Git
replacement objects, global configuration, hooks, fsmonitor and network
transports/lazy fetching are disabled. No candidate
Python module, dependency installer, shell script or template is executed.
Candidate templates and executable/configuration inputs must equal trusted bytes.
The adapter also checks trusted working bytes against the trusted commit.

The candidate data is materialized into an isolated temporary directory. The
existing public-mirror reader installs only public verification material into a
separate temporary store. `reporting_trust.config()` authenticates the canonical
root against the **required** `BTS_PRODUCTION_TRUST_SHA256` environment variable;
there is no repository fallback. The same baseline, current-scope, role, site,
environment, revocation, contract eligibility, context approval, exact render,
manifest and release-signature implementations remain authoritative. The
ordinary `validate_category_hubs` gate runs before release verification. A PASS
records exact candidate/trusted SHAs, whole candidate map hash and approved
archive/manifest hashes. `deployment_eligible` remains false in this interface.

This does not make PR-supplied workflow YAML intrinsically trusted. An attacker
who can get a modified workflow approved could fabricate a same-name check.
GitHub Actions app binding alone does not distinguish workflows. The control
comparison prevents a candidate replacing the verifier **when this workflow
executes as reviewed**; protected independent review of the workflow itself is
mandatory. Do not describe current unprotected `main` as protected.

## Critical change policy

`reporting_workflow.control_path()` closes the implementation boundary over all
files (including new and deleted files) in `scripts/`, `templates/`, `assets/`,
`static/`, `netlify/`, `.github/`, all declared pilot root input files, all
publication dependency files, `.gitattributes`, `.gitmodules`, `.npmrc`,
`pyproject.toml`, `setup.py`, `setup.cfg`, `AGENTS.md`, `CLAUDE.md`, and this policy.
Such changes are blocked from the ordinary publication path. A reviewed update
must install trusted code before it can verify later data candidates.

`critical_path()` additionally covers every `content/`, `deployment/`, and `dist/` file.
`critical_inventory()` derives the normalized path/SHA-256 map from the complete
captured candidate. Every output is critical data, including HTML, assets, feeds,
robots/sitemaps, `.well-known`, redirects and auxiliary metadata. No output is
excluded and no fixed count authorizes membership. `protected_output()` requires
exact equality to the reviewed baseline plus selected pilot paths; additions,
deletions and changed non-pilot bytes fail. Selected output must equal the trusted
render and signed manifest. A future output-set change needs explicit baseline/
scope review and a new release approval. Output changes are not control changes.
These data files need independent review and the applicable signed approvals,
but are not required to equal the old trusted content. The WP3C9J review packet
contains the exact current path/hash inventory; prefixes above intentionally
cover future additions too. No CODEOWNERS is installed: no second authorized
human reviewer has been established, and an unenforced file would imply false
protection. Assign actual eligible reviewers before enabling code-owner rules.

## Future remote activation packet — MUST, not executed

Target repository default branch `refs/heads/main`. Require PRs and at least one
independent human approval; dismiss stale reviews and require approval of the
latest reviewable push by somebody other than its pusher. No self approval,
automated Dependabot review substitute, owner bypass, bot bypass or admin bypass.
Require all conversations resolved and the exact check above from GitHub Actions;
require branches up to date. No direct pushes, force pushes or deletions. Critical
workflow/control changes require a separately reviewed maintenance procedure;
do not let their author also satisfy the critical review. Where available,
require approved CODEOWNERS for the complete critical prefixes and root paths.
Keep Actions default token permission read-only and disable Actions creating or
approving PRs. Existing approved manual generation/fact-audit PR creation needs
an explicitly reconciled policy before resumption; no bypass is pre-authorized.

The user-owned public repository currently lacks a second reviewer. Confirm
actual plan support and enforcement semantics before activation. Organization
required-workflow rules are not assumed available to this user-owned repo.
If ordinary protected review cannot meet the intended workflow provenance
guarantee, obtain an independent required-workflow/check authority in a separate
architecture package; a status context string alone is insufficient.

No GitHub Environment is needed for this read-only check. No Netlify token,
private signing key, secret, OIDC permission or deployment permission is required. The separately
reviewed detached-approval transport uses the public `BTS_PUBLICATION_APPROVAL_SHA`
variable; no value is installed by this package. Keep the existing public pin unchanged. Pin rotation
requires a separately reviewed operator action. Optional hardening: restrict
allowed Actions to this pinned set and enforce full SHA pinning account-wide,
after checking effects on unrelated existing workflows.

## Activation blockers and publication freeze

Before installation: independently review WP3C9J; reconcile dirty candidate and
remote divergence; resolve inherited A-class build/hub failures and remaining
diagnostic regressions or explicitly choose a reviewed freeze; establish real
review staffing; verify plan capabilities; and arrange a proven Netlify-side
publication freeze before any exceptional trusted-code installation. A local
HOLD is not a freeze of Netlify's existing Git auto-deploy.

The unestablished deployed baseline, empty scope and absent approvals mean the
publication check cannot currently pass. Requiring it can deliberately freeze
merges, but cannot stop already authorized Netlify deployments, manual deploys
or privileged bypass. Prefer a separately approved coordinated GitHub + Netlify
freeze while prerequisites are resolved. Reading, local tests and review remain
usable. Do not remove a required failing check to resume publishing. Rollback
must retain the separately verified provider freeze: capture prior rules, then
an explicitly authorized operator may restore those exact rules for maintenance,
install the last independently reviewed verifier, recheck the required context
and reinstate no-bypass protection before any provider unfreeze. No fully
specified account rollback is claimable until those prior settings and freeze
evidence exist. There is no fail-open rollback in this repository package.

## Local verification

With the reviewed runtime and public pin already provided in the environment:

```sh
python -I scripts/reporting_workflow.py --candidate /absolute/candidate/checkout \
  --candidate-sha FULL_CANDIDATE_SHA --trusted-sha FULL_TRUSTED_SHA \
  --approval-repository /absolute/approval/checkout --approval-sha FULL_APPROVAL_SHA
python -I scripts/reporting_workflow.py --candidate /absolute/current/repo \
  --diagnostic-working-tree
python -I -B scripts/reporting_workflow_selftest.py
python -I -B scripts/reporting_workflow_cli_selftest.py
```

Run the first command from the trusted checkout. The dirty diagnostic records a
byte-map digest, never claims commit identity, and cannot satisfy a required
check even if its data verifies. The self-test creates disposable TEST-only keys
and signatures outside the repository; no production private material is read.
Its positive fixture is a synthetic corpus without hubs; an independent negative
feeds the unchanged real hubs to prove the ordinary gate still blocks them.
No local simulation proves GitHub event execution, required-check enforcement,
Linux package installation, deployed baseline identity or Netlify enforcement.

## Exact revision approval (WP3C9J2)

Release schema `beatthescam-pilot-release-v3` signs a `pilot-output/v3` manifest.
Its `source_revision` is a closed `bts-source-revision/v1` object containing the
exact nonzero source commit, its Git tree, and SHA-256 of the complete candidate
path/hash map. These are additional bindings: existing canon, selected context
packets, action plan, runtime/dependencies, source inputs, full output map and
canonical archive checks remain mandatory. Old release versions or missing
revision fields reject; there are no production approvals to migrate.

A release approval is detached from the source commit. After the exact candidate
commit exists, the reviewer reviews and signs it, then a separately authorized
operation places only `release.json` in an independent approval commit. The
workflow reads that commit at the explicitly configured full
`BTS_PUBLICATION_APPROVAL_SHA`. The transport commit is data, not a source revision
or a signer: replacing it cannot change the signed candidate or bypass the
existing external production trust pin. There is no moving approval branch lookup,
implicit checkout fallback, signing command or automatic transport publication.
Missing transport configuration fails closed. No new remote variable is set here.

Contract and context records remain content/evidence approvals, not permission
to publish a revision. The final release binds their use through the candidate
map, policy/canon and per-page context packet digests, and reauthenticates them.
They may support a later separately reviewed release; the release approval itself
cannot be reused for a different source commit, even with identical tree/output.
Trusted verifier provenance is enforced by the event's exact base/before SHA,
control equality and signed verifier/dependency bytes; no particular Git commit
label is inferred from content equivalence.

PR verification selects only the event's head SHA; its base supplies trusted code.
It never substitutes GitHub's synthetic test-merge SHA. Push verification selects
the event SHA, with `before` supplying trusted code. A merge, rebase, cherry-pick or
empty commit creates a different source revision and needs a fresh detached
release approval. A PR-head PASS does not authorize a later merge commit. Keep
the provider freeze until the exact final publication commit has its own approval
and verified check. Installation must prove actual check-run/workflow/revision
association; this local package has not tested remote event execution.

Dirty worktrees cannot receive a release approval: reviewer `--role release`
requires `--candidate-sha`, and both tracked and nonignored untracked bytes plus
all actual served output must match that exact commit. Pilot CLI uses the same
explicit option; provider handoff verifies its `--source-revision` instead of
merely recording a label. Netlify's future verifier requires exact `COMMIT_REF`
and an explicit external `BTS_RELEASE_PACKET` path; it never consumes an embedded
release as revision authority. Provisioning that detached public file and proving
provider controls remain future activation work. No production approval can
become valid merely because dirty bytes are committed later.

The diagnostic mode remains nonauthorizing. With detached TEST approval it can
corroborate the packet's claimed commit and verify its data, but without an
independently selected event revision it unconditionally returns BLOCKED, exit 1.
The isolated `--test-only` CLI returns exit 0 for valid TEST fixtures with
`test_only:true` and `deployment_eligible:false`; the production workflow never
passes that option and refuses TEST authority. BLOCKED is exit 1; ERROR is exit 2.

The two commands in Local verification run unconditionally inside the single
`Trusted publication verification` job, before candidate verification, and in the
offline gate before legacy gates. Failure fails the job. The CLI suite also checks
that this mandatory wiring, immutable approval checkout, production mode and event
SHA validation remain present. Those tests execute trusted code and disposable
TEST Git repositories/keys only. They do not activate required checks or protect
against replacing the entire workflow on an unprotected branch; independent
remote review/no-bypass enforcement remains indispensable.
