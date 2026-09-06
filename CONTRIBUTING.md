# Contributing to RankWeave

This file is for maintainers, reviewers, and automation that change the
RankWeave source tree. Operators who only need to install, run, or call the
published contract should start at [README.md](README.md).

RankWeave is a leaf product. It must keep working as a standalone package and
as a published dependency. [Naruon](https://github.com/ContextualWisdomLab/naruon)
may call RankWeave through that published contract; do not treat that hub-and-leaf
composition as a layering violation, and do not make a Naruon checkout a
prerequisite for RankWeave development or tests.

## Local development

```bash
pip install -e ".[dev]"
python -m ruff check .
python -m coverage run -m pytest -q
python -m coverage report
python -m pip wheel . --no-deps --wheel-dir dist
```

Production modules require complete public docstrings and 100% statement and
branch coverage. Runtime code may import only the Python standard library.

Follow [AGENTS.md](AGENTS.md) and [ARCHITECTURE.md](ARCHITECTURE.md).
`AGENTS.md` is a reviewed agent-control file; only an explicit maintainer pull
request may change it.

## Release metadata

A release updates `pyproject.toml`, `rankweave.__version__`, the expected
version test, and `CHANGELOG.md` together. See [docs/releasing.md](docs/releasing.md).

## Hourly governed development loop

The default branch runs an hourly workflow at minute 17:

`PR review/merge scan → review-feedback repair → exact-head revalidation → one
bounded buyer-visible product proposal when the governed PR queue is empty`.

PR inspection, review repair, and merge decisions use immutable reusable
workflows from the organization's central `.github` repository. The local
product stage uses a hash-pinned OpenCode binary with the official NVIDIA
provider and `NVIDIA_NIM_API_KEY`; it does not use GitHub Copilot Agent Tasks or
alter the existing review-agent credential path.

The workflow first permits edits only to tests and a design specification, then
runs pytest without network or inherited credentials and requires a genuine
failed test. Only then may the agent implement one bounded production change.
`AGENTS.md`, workflow, ownership, security, environment, and repository-control
files remain maintainer-owned and outside autonomous scope. Ruff, the complete
tests, 100% line/branch coverage, wheel build, offline installation, import
smoke, and `pip check` run in a network-isolated process.

Before requesting the short-lived OIDC-derived GitHub App token, the workflow
rechecks both the open-PR queue and exact `main` SHA. It repeats both checks
immediately before opening one PR. Generated work is never self-approved,
merged, published, or released.

The credential, sandbox, failure, and operating contracts live in
[Hourly commercialization loop](docs/operations/hourly-commercialization-loop.md).
Do not document that loop in the customer README.
