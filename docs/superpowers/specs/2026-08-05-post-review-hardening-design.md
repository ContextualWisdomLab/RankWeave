# Post-review security and UTF-8 hardening design

## Context

RankWeave 0.11.0 added the candidate-family CLI and merged after all exact-head
CI, package, SAST, security, and CodeRabbit status checks succeeded. The final
CodeRabbit pass completed immediately after auto-merge and identified four
follow-up defects that remain valid on `main`:

1. the autonomous implementation agent may edit `AGENTS.md` even though it is
   an agent-control policy file;
2. the release notes overstate credential scoping and the timing of the OIDC
   GitHub App token relative to queue/base checks;
3. the candidate identifier grammar does not explicitly document the empty-ID
   and first-separator behavior;
4. successful Unicode JSON is written through the locale-configured text
   stream rather than as explicit UTF-8 bytes.

This is a bounded patch-release slice. It does not change retrieval algorithms,
TREC metrics, Holm adjustment, or naruon-shared fusion primitives.

## Goals

- Make `AGENTS.md` immutable to autonomous authoring.
- Check the open-PR queue and exact base SHA before requesting the generated-PR
  app token, then repeat the same checks after token exchange immediately before
  mutation.
- Describe the actual provider-credential and token lifecycle precisely.
- Emit CLI success output as UTF-8 bytes regardless of locale encoding.
- Specify the complete `ID=PATH` candidate grammar.
- Preserve 100% production statement/branch coverage, production docstrings,
  Python 3.10–3.13 compatibility, package smoke tests, and stdlib-only runtime.

## Architecture

### Autonomous policy boundary

The OpenCode implementation permission map explicitly denies `AGENTS.md`. The
post-authoring diff gate removes `AGENTS.md` from the exact allowlist and adds it
to the exact protected set. README, CHANGELOG, product/operations docs, tests,
package metadata, and production modules remain within the existing bounded
scope.

### Generated-PR token ordering

A credential-free preflight step uses the read-only workflow token to confirm:

- no pull request owns the development queue;
- `main` still equals `AUTOMATION_BASE_SHA`.

Only then may the workflow exchange OIDC for the GitHub App token. The final PR
step repeats both checks with the app token immediately before branch push and
PR creation. This does not eliminate all distributed-system races, but it
minimizes token lifetime and preserves a final fail-closed check at the mutation
boundary.

### UTF-8 output

The CLI encodes the completed JSON document plus newline with UTF-8 and writes
bytes through `sys.stdout.buffer`. A narrow fallback supports injected test
streams without a binary buffer, while production process streams always take
the byte path. Serialization remains `ensure_ascii=False`; exit status and
stderr-only error behavior remain unchanged.

### Candidate grammar

The first `=` separates a non-empty candidate identifier from the local path.
The identifier therefore cannot contain `=`. Later `=` characters belong to the
path. IDs remain unique, printable Unicode, and free of leading/trailing
whitespace; command-line order remains statistical-family evidence.

## Testing

- Add a CLI regression that replaces stdout with an ASCII `TextIOWrapper`, runs
  a Unicode candidate family, and verifies valid UTF-8 bytes plus newline.
- Extend workflow contract tests to require an explicit OpenCode deny for
  `AGENTS.md`, exclusion from `allowed_exact`, inclusion in protected paths,
  pre-token queue/base checks, and post-token rechecks.
- Keep existing pairwise and family CLI tests unchanged and green.
- Run Ruff, the full suite, 100% line/branch coverage, wheel and installed CLI
  smoke tests, Security Scan, and SAST.

## Release

Prepare RankWeave 0.11.1 as a patch release. Synchronize package metadata,
`rankweave.__version__`, the expected-version test, and CHANGELOG. No tag,
GitHub Release, or package publication occurs before protected merge.
