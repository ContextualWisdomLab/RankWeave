# CLAUDE.md — RankWeave

All automated contributors must follow [`AGENTS.md`](AGENTS.md) and the
architectural boundaries in [`ARCHITECTURE.md`](ARCHITECTURE.md).

RankWeave is a standard-library-only runtime. Keep statistical arithmetic in
the pure Python core, keep CLI behavior as a transport adapter, preserve
standalone and naruon/MSA use, write tests before behavior changes, and maintain
100% production statement and branch coverage plus complete public docstrings.

Report JSON Schemas are public compatibility resources. Any transport change
requires synchronized schema, tests, installed-wheel smoke, documentation, and
release metadata. Do not use `COPILOT_GITHUB_TOKEN`; the governed product loop
uses the existing `NVIDIA_NIM_API_KEY` OpenCode path without altering review
agent credentials.
