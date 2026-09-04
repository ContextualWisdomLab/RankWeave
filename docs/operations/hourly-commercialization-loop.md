# Hourly commercialization loop

`.github/workflows/hourly-commercialization-loop.yml` runs at minute 17 of
every hour and can also be started manually. It turns the repository's
review→repair→revalidation→development policy into a bounded, inspectable
GitHub Actions workflow rather than an unobservable background promise.

## Sequence

Each run performs four jobs in order:

1. **Inspect the PR queue.** Call the central PR review/merge scheduler to
   request missing current-head reviews, update eligible behind branches, and
   merge or enable auto-merge only when repository policy is satisfied.
2. **Repair review feedback.** Call the central review-fix scheduler with one
   dispatch of budget and a one-hour same-head retry interval.
3. **Revalidate the PR queue.** Call the merge scheduler again so a repaired or
   newly approved current head is reconsidered under the same checks.
4. **Develop the next product gap.** Only when every governance job succeeded,
   no PR is open, and at least one of the org's five contextual-orchestrator
   provider secrets exists, author one design, prove a failing test,
   implement the bounded increment, validate it without network or inherited
   credentials, and open one pull request.

The reusable workflows are referenced at immutable commits:

- merge/revalidation policy:
  `5983b41ace75040c1d81818171ca7d0f3653254e`;
- hourly review-repair policy with called-workflow source bound to
  `job.workflow_repository` and `job.workflow_sha`:
  `21397126d708d2d536ccc1d68b0d333653ce9315`.

This prevents a privileged scheduled run from silently changing behavior
because the central `main` branch moved. Updating either central policy
requires an explicit reviewed SHA change in RankWeave.

## Product-development trust zones

The local development job is separated into four trust zones.

### 1. Trusted base verification

The workflow checks out `main` with `persist-credentials: false`, records the
exact commit, prepares an isolated development virtual environment, and runs
Ruff, the full test suite, and the configured 100% line/branch coverage gate.
It also proves that the runner can create a network and PID namespace. A broken
base or unavailable isolation primitive blocks model execution.

### 2. Test-first authoring

The hash-pinned OpenCode binary is configured with a single custom provider
pointed at a locally vendored contextual-orchestrator gateway sidecar
(`http://127.0.0.1:8000/v1`), routed through the org-wide, fail-closed
`orchestrator/free` pool instead of any direct provider API — see
[Gateway routing](#gateway-routing) below. Its first phase may edit only
`tests/` and `docs/superpowers/specs/`. The following tools and surfaces are
explicitly denied:

- Bash and arbitrary code execution;
- web search and URL fetching;
- external directories;
- LSP execution;
- subagents, skills, questions, and doom-loop retries;
- `.git`, environment files, and the OpenCode control file.

The prompt also forbids reading GitHub issues or pull requests. Those are
untrusted prompt surfaces and are not needed to select a gap from the trusted
repository itself.

After authoring, the workflow verifies the changed paths and runs pytest in a
network-isolated process with `env -i` and a fresh `/proc`. Pytest must exit
with status `1` and report an actual failed test. A passing suite, collection
error, invocation error, rename, deletion, or out-of-scope edit does not satisfy
the red gate.

### 3. Implementation and deterministic validation

The verified red state is committed locally only so model fallback can return
to a known tree. The implementation phase may edit normal product,
documentation, version, and package files, but it still cannot execute Bash,
use the web, touch external directories, or edit `.github/`, `.git/`, or agent
control files.

A deterministic post-agent gate rejects:

- workflow, ownership, security, environment, or Git-submodule changes;
- rename, copy, merge-conflict, symlink, submodule, or non-regular state;
- binary/NUL-bearing or unsupported file types;
- more than 25 changed files;
- any file larger than 256 KiB;
- more than 1 MiB of changed-file content;
- proposals without a production `src/rankweave/*.py` change.

The accepted proposal then runs, with no provider or GitHub credential and no
network access:

```text
Ruff
→ all pytest tests
→ 100% line and branch coverage
→ wheel build without network or build isolation
→ isolated wheel installation
→ import/version smoke test
→ pip check
```

A manifest taken immediately before validation must match the manifest after
validation. Model-authored tests or import code therefore cannot alter the
proposal as a validation side effect.

### 4. GitHub mutation

Only the final static packaging step receives the built-in GitHub token. It
rechecks that no PR appeared during authoring and that live `main` still equals
the recorded checkout commit. If either condition changed, the proposal is
discarded without pushing a branch.

The model-authored PR title and body are length- and character-bounded. The
workflow removes the message file, squashes the local red/green history to one
commit, disables Git hooks for commit and push, creates a run-unique branch,
and opens one PR. It never approves, merges, tags, publishes, or releases that
PR.

## Gateway routing

Every model call this job makes is routed through
[ContextualWisdomLab/contextual-orchestrator](https://github.com/ContextualWisdomLab/contextual-orchestrator)'s
fail-closed `orchestrator/free` pool instead of any direct provider API — the
same governed-gateway pattern already used by contextual-orchestrator's own
hourly maintenance loop and by the four central review workflows in
ContextualWisdomLab/.github. The `develop-next-product-gap` job:

1. vendors contextual-orchestrator's source at an exact reviewed commit
   (`CONTEXTUAL_ORCHESTRATOR_PIN_SHA`) into `$RUNNER_TEMP`, isolated from the
   read-only `AUTOMATION_VENV` used for RankWeave's own trusted tooling;
2. installs its hash-pinned `requirements.lock` with `pip install
   --require-hashes`;
3. starts `python -m scripts.ci.serve_seeded_gateway --serve
   --auto-discover-model-agents` in the background, which seeds each present
   org provider secret into the gateway's process-local KV once (never
   re-reading the environment afterward) and serves an OpenAI-compatible
   `/v1/chat/completions` endpoint on `127.0.0.1:8000`;
4. waits for `/healthz` before continuing.

OpenCode's `opencode.json` then points its one configured provider,
`contextual_orchestrator_gateway` (`npm: "@ai-sdk/openai-compatible"`), at
that loopback endpoint with `model: "contextual_orchestrator_gateway/orchestrator/free"`.
No provider secret is ever placed in the OpenCode process's own environment;
only the loopback-only ephemeral bearer token (written to a private file, not
a job-wide environment variable) authenticates to it.

## Credential boundary

Configure a repository or organization Actions secret for at least one of the
org's five contextual-orchestrator provider credentials: `BYTEZ_API_KEY`,
`NVIDIA_NIM_API_KEY`, `NVIDIA_NIM_API_KEY_SUB`, `OPENROUTER_API_KEY`, or
`OPENAI_API_KEY`. Each present secret is step-scoped only to:

- the static eligibility check;
- the gateway sidecar provisioning step (where it seeds the gateway's KV).

None of the five secrets is a job-level environment variable, and none is
present in the OpenCode processes that execute model-authored prompts — those
processes only ever see the loopback gateway's ephemeral bearer token, read
from a private file. The OpenCode processes explicitly remove `GH_TOKEN`,
`GITHUB_TOKEN`, and OIDC request variables. Their tool permissions deny
command execution and web access, so no credential is exposed to
model-authored shell or network operations.

The GitHub token is present only in the two static queue/base checks and the
final branch/PR creation step. No model-authored program is executed in those
steps.

## Model and binary configuration

OpenCode is pinned to version `1.17.13`; its Linux archive must match the
reviewed SHA-256 digest before installation. Model selection itself is no
longer a static per-workflow list: `orchestrator/free` is a single virtual
model that contextual-orchestrator routes, at request time, across every
live-discovered, credential-backed, free-priced candidate across all
configured providers. The workflow's own `OPENCODE_MODEL_CANDIDATES`
retry loop now has exactly one entry (the gateway model) rather than several
hand-picked NVIDIA model IDs — resilience against one candidate's failure is
now the gateway's own internal routing concern, not this workflow's.

The gateway has five minutes for the test-design phase and ten minutes for
the implementation phase (unchanged from before this migration). Partial work
from a failed attempt is discarded before any retry. The overall job has a
55-minute timeout so the next hourly run cannot accumulate behind an
unbounded agent session.

Review the vendored `CONTEXTUAL_ORCHESTRATOR_PIN_SHA` periodically against
contextual-orchestrator's current `main` and re-pin after reviewing the delta,
the same exact-head discipline the org's other central sidecars follow.

## Single-flight and TOCTOU behavior

The workflow uses one concurrency group with `cancel-in-progress: true`, so a
new hourly run replaces a stale previous orchestration instead of building an
unbounded queue.

The open-PR gate runs twice:

- before checkout and authoring;
- immediately before branch creation.

The final step also compares live `main` with the exact recorded base SHA. An
external PR or base-branch update therefore wins the queue, and stale generated
work is discarded rather than rebased, force-pushed, or opened against a
changed base.

## Fail-closed outcomes

PR maintenance still runs when product development is disabled. No generated
branch or PR is created after any of these conditions:

- failed central governance job;
- no contextual-orchestrator provider secret configured;
- open PR at either queue check;
- base branch movement;
- failed trusted-base validation;
- missing network/PID namespace support;
- OpenCode checksum, gateway sidecar, or gateway-model failure;
- out-of-scope red edit or absence of a real failed test;
- protected, binary, symlink, oversized, or overly broad diff;
- final lint, test, coverage, build, installation, import, or dependency
  failure;
- validation-time workspace mutation;
- invalid or oversized PR title/body.

The next hourly run begins from the then-current protected `main` branch.

## Operational verification

After merging the workflow:

1. Confirm the three central governance jobs use their immutable SHAs.
2. Run the workflow manually with an open PR and confirm the development gate
   reports `eligible=false`.
3. Remove the open PR while leaving all five provider secrets absent and
   confirm PR maintenance succeeds while development emits a fail-closed
   warning.
4. Configure at least one provider secret and confirm the base
   Ruff/tests/coverage and namespace preflight run before the gateway sidecar
   and OpenCode.
5. Inspect the red phase and confirm only tests/design changed and pytest exit
   status `1` was required.
6. Inspect final validation and confirm it ran under `unshare`, `env -i`, no
   network, no inherited provider/GitHub credential, and a stable workspace
   manifest.
7. Confirm exactly one branch and PR are created only when both queue checks
   and the exact-base check remain clear.
8. Confirm the generated PR enters the ordinary central review/check/merge loop
   and is not approved or merged by its authoring workflow.

## Scope

This loop is software-delivery automation, not proof of market value. It keeps
technical gaps moving through a governed queue. Buyer adoption, validated
retrieval lift, operating economics, support readiness, and commercial due
diligence still require external evidence before any valuation claim is made.

The full security and state-machine design is recorded in
[`docs/superpowers/specs/2026-08-04-nim-commercialization-loop-design.md`](../superpowers/specs/2026-08-04-nim-commercialization-loop-design.md).
