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
   no PR is open, and no nonterminal Copilot cloud-agent task exists, create
   one task that opens one bounded PR.

The reusable workflows are referenced at immutable commits:

- merge/revalidation policy:
  `5983b41ace75040c1d81818171ca7d0f3653254e`;
- hourly review-repair policy with called-workflow source bound to
  `job.workflow_repository` and `job.workflow_sha`:
  `21397126d708d2d536ccc1d68b0d333653ce9315`.

This prevents a privileged scheduled run from silently changing behavior
because the central `main` branch moved. Updating either central policy
requires an explicit reviewed SHA change in RankWeave. The caller grants the
union of permissions required by the two pinned governance workflows; the
local product-development job overrides that token with `contents: read` and
`pull-requests: read` only.

## Single-flight and fail-closed behavior

The workflow uses one concurrency group with `cancel-in-progress: true`, so a
new hourly run replaces a stale previous orchestration instead of building an
unbounded queue.

Product development starts only after all governance jobs succeeded and both
queue gates pass:

- `GET /repos/ContextualWisdomLab/RankWeave/pulls?state=open` returns no open
  pull request;
- every paginated page from
  `GET /agents/repos/ContextualWisdomLab/RankWeave/tasks` contains no task in
  `queued`, `in_progress`, `idle`, `waiting_for_user`, or an unknown state.

Unknown task response shapes, pagination failures, task-inventory API failures,
missing credentials, failed PR-governance jobs, and unrecognized task states
all block task creation. Completed, failed, timed-out, and cancelled tasks are
terminal, but an open PR still owns the queue regardless of task state.

The generated prompt requires exactly one buyer-visible product gap, test-first
implementation, complete docstrings, 100% line and branch coverage, preserved
stdlib-only and store-agnostic boundaries, documentation and changelog updates,
and one PR. The task is explicitly forbidden from self-merging or bypassing
reviews and required checks.

## Required secret

Create a repository or organization Actions secret named
`COPILOT_GITHUB_TOKEN` containing a **user-to-server token** accepted by the
GitHub Copilot agent-tasks API. A personal access token, OAuth user token, or
GitHub App user-to-server token may be used. GitHub App installation tokens and
the Actions `GITHUB_TOKEN` are not supported by that API.

The workflow never falls back from `COPILOT_GITHUB_TOKEN` to `github.token` for
agent task listing or creation. Without the secret, PR maintenance still runs,
but new product development remains intentionally disabled and emits a warning.

Minimum access must be limited to RankWeave and the operations required by the
agent. When using issue assignment instead of the task endpoint, GitHub's
current fine-grained-token guidance requires metadata read and Actions,
contents, issues, and pull-request read/write access. Reassess permissions when
the public-preview API changes.

## Operational verification

After merging the workflow:

1. Open **Actions → Hourly RankWeave Commercialization Loop** and run it
   manually.
2. Confirm inspect and revalidation use the pinned merge-policy SHA and review
   repair uses the separately pinned immutable-source SHA.
3. Confirm the called governance jobs can request reviews, dispatch repair,
   update branches, and enable or perform policy-compliant merges.
4. With an open PR, confirm the product-development gate reports
   `eligible=false` and creates no task.
5. With no open PR but an active task on a later pagination page, confirm it
   creates no duplicate.
6. With both queues empty and the secret configured, confirm one cloud-agent
   task is created with `base_ref=main` and `create_pull_request=true`.
7. Confirm the resulting PR enters the normal central review/check/merge loop
   and is not merged by the agent that authored it.

## Scope

This loop is software-delivery automation, not proof of market value. It keeps
technical gaps moving through a governed queue. Buyer adoption, validated
retrieval lift, operating economics, support readiness, and commercial due
diligence still require external evidence before any valuation claim is made.
