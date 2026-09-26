# Hourly reusable-workflow reachability incident

- **Date:** 2026-08-07
- **Component:** `.github/workflows/hourly-commercialization-loop.yml`
- **Failure:** scheduled workflow concluded `failure` before GitHub created any
  jobs.

## Root cause

RankWeave pinned the central review-fix reusable workflow to commit
`21397126d708d2d536ccc1d68b0d333653ce9315`. That commit later diverged from the
protected central history, so the caller could no longer resolve the reusable
workflow. Recent failed runs contained zero jobs, while the last successful
hourly run used the same RankWeave caller before the central ref became
unreachable.

## Remediation

The local hourly workflow now retains its reachable immutable merge-scheduler
calls and replaces the unavailable repair call with a read-only local hold job.
The bridge checks whether an open PR exists and records the fail-closed repair
state, but it has no write, OIDC, issue, provider, or model credential. It does
not copy the repair engine and does not fall back to GitHub Models.

The central repair call may return only after a protected central NVIDIA
NIM/OpenCode scheduler has merged and RankWeave pins its reachable immutable
commit. The existing independent review workflows and their credentials remain
unchanged.

## Verification

- Contract tests reject any `pr-review-fix-scheduler.yml@...` reference in the
  temporary bridge state.
- Contract tests require two immutable merge-scheduler calls.
- Contract tests require the bridge to remain local, read-only, secret-free,
  provider-neutral, and bounded.
- Full Python 3.10-3.13 CI, package smoke, Security Scan, and SAST must pass on
  the exact PR head before merge.

## Rollback

Restore a central review-repair call only with a protected, reachable, reviewed
commit SHA whose workflow uses NVIDIA NIM/OpenCode and preserves the existing
review-agent credential boundary. Never restore the orphaned SHA or substitute
a mutable branch.

## References

GitHub. (2026). *Reusing workflow configurations*. GitHub Docs.
https://docs.github.com/en/actions/reference/workflows-and-actions/reusing-workflow-configurations

GitHub. (2026). *GITHUB_TOKEN*. GitHub Docs.
https://docs.github.com/en/actions/concepts/security/github_token
