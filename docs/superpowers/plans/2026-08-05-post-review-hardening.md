# Post-review hardening implementation plan

1. Create a feature branch from the current default branch before any production
   or workflow change.
2. Add failing regression tests for explicit UTF-8 stdout bytes and autonomous
   `AGENTS.md` protection/token preflight ordering.
3. Implement the smallest CLI output helper and workflow policy changes that
   satisfy the reviewed design.
4. Update candidate grammar documentation and correct credential/token lifecycle
   wording.
5. Bump patch metadata to 0.11.1 and update CHANGELOG.
6. Run Python 3.10–3.13 CI, Ruff, full tests, 100% production line/branch
   coverage, package smoke, SAST, Security Scan, and current-head review.
7. Merge only through the protected PR path and confirm the open PR queue.
