# Secure NVIDIA NIM Commercialization Loop Design

## Goal

Make RankWeave's hourly product-development stage operational without a Copilot
Agent Tasks token while preserving the central review, repair, exact-head check,
and protected-merge contract. The workflow may create one bounded pull request;
it may never approve, merge, publish, or release its own work.

## Buyer and maintainer problem

The existing hourly workflow invokes the organization-wide PR governance jobs
but its product-development stage depends on `COPILOT_GITHUB_TOKEN`. That secret
is not configured, so the workflow correctly fails closed but cannot close new
buyer-visible product gaps. Replacing the inactive task-creation call with an
in-run coding agent makes the loop useful, but executing model-authored code in
a write-capable GitHub Actions job introduces new credential, supply-chain,
network, time-of-check/time-of-use, and diff-scope risks.

The safe design therefore separates **authoring**, **execution**, **validation**,
and **GitHub mutation** into explicit trust zones.

## Sequence

1. Run the immutable central PR inspection, repair, and revalidation workflows.
2. Continue only when all three governance jobs succeeded, no pull request is
   open, and `NVIDIA_NIM_API_KEY` is configured.
3. Check out `main` with persisted Git credentials disabled and record its exact
   commit.
4. Install the hash-pinned OpenCode binary and prepare a trusted Python
   validation environment.
5. Verify the checked-out base already passes Ruff, the complete test suite,
   and the configured 100% line/branch coverage gate.
6. Run a **red phase** in which OpenCode may read trusted repository files but
   may edit only `tests/` and `docs/superpowers/specs/`. Bash, web access,
   subagents, LSP, external directories, and questions are denied.
7. Execute the resulting tests with no network and an empty inherited
   environment. Require pytest exit status `1` and an actual `FAILED` record.
8. Commit the verified red state locally so model fallback can reset to a known
   tree without pushing anything.
9. Run an **implementation phase** with the same no-execution and no-web
   permissions. Edits are allowed in Python product and documentation files but
   denied under `.github/`, `.git/`, agent-control files, `crates/`, Cargo
   manifests, and Python build metadata. Native changes require a separate
   maintainer-authored and reviewed pull request.
10. Apply a deterministic diff gate: text files only, no symlinks or submodules,
    no protected paths, no rename/copy/conflict state, bounded file count,
    bounded individual/aggregate bytes, and at least one production Python
    module changed.
11. Run Ruff, all tests, 100% coverage, wheel build, isolated wheel install,
    import smoke, and `pip check` inside a network namespace, PID namespace,
    fresh `/proc`, and `env -i` environment.
12. Compare pre/post validation manifests and fail if executed code changed any
    proposed file.
13. Recheck both the open-PR queue and the exact `main` commit. Discard the
    proposal if another PR appeared or the base moved.
14. Sanitize the model-authored title/body, squash the local red/green commits,
    push one run-unique branch, and open one PR with the built-in token.

## Credential boundary

`NVIDIA_API_KEY` is step-scoped only to the static gate and two OpenCode
processes. It is not a job-level environment variable and is absent from every
step that executes model-authored Python. OpenCode receives no `GH_TOKEN`,
`GITHUB_TOKEN`, or OIDC request variables.

The OpenCode configuration uses the built-in NVIDIA provider documented at
<https://opencode.ai/docs/providers/>. It does not dynamically select a custom
OpenAI-compatible provider package. OpenCode tool permissions deny Bash,
webfetch, websearch, external directories, tasks, skills, questions, LSP, and
doom-loop retries. The red phase restricts edits to tests and design files; the
implementation phase additionally denies edits to governance/control paths.

The GitHub token appears only in static queue checks and the final branch/PR
packaging step. No model-authored command runs in either token-bearing step.

## Model and supply-chain boundary

The workflow downloads one immutable OpenCode release archive and verifies its
reviewed SHA-256 digest before installation. It uses the official built-in
NVIDIA integration and an ordered fallback list of currently configured NVIDIA
NIM model identifiers. The model list is configuration, not an inferential or
benchmark claim.

The agent may not inspect issues, pull requests, or the web because those are
untrusted prompt surfaces and would expose the model-authored proposal to
prompt-injection content while a provider credential is present.

## Test-first contract

The red phase cannot edit production code. A successful OpenCode process is not
enough: the workflow itself runs pytest in a network-isolated, sanitized
process and requires a genuine failing test. Collection, invocation, and
internal errors do not satisfy the red gate. Only after this evidence is
captured may the implementation phase edit production files.

The final validation must pass the repository's existing `fail_under = 100`
line and branch coverage configuration. The agent cannot weaken CI because
`.github/` is protected, and the diff gate plus exact-head review exposes all
remaining changes in the generated PR.

## Single-flight and TOCTOU behavior

Workflow concurrency prevents overlapping scheduled runs. The initial queue
check prevents development while an existing PR owns the queue. A second queue
check immediately before branch creation handles external PRs that appear while
a model is authoring. The workflow also compares the live `main` SHA with the
recorded checkout SHA and discards stale work rather than rebasing or hiding a
base change.

## Failure behavior

The development stage produces no remote branch or PR when any of these occur:

- central governance job failure;
- missing NVIDIA credential;
- open PR at either queue check;
- base branch movement;
- unavailable network/PID isolation;
- OpenCode checksum or model failure;
- out-of-scope red-phase edit;
- no genuine failing test;
- protected, binary, symlink, oversized, or excessively broad diff;
- final Ruff, test, coverage, build, install, import, or dependency failure;
- validation-time workspace mutation;
- malformed or oversized PR message.

A later hourly run starts again from the then-current protected `main` branch.

## Non-goals

This workflow does not grant a market valuation, autonomously choose a release
channel, publish packages, alter governance, consume untrusted issues, perform
new external research, or merge its own PR. Research-dependent psychometric or
statistical changes remain out of scope unless their primary sources and APA
7th edition references already exist in the repository and the generated PR
preserves the existing scientific interpretation boundaries.
