# Canonical Fusion Policy Artifacts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a strict, versioned, deterministic, exact-byte-identifiable deployment artifact for fixed weighted-convex and weighted-RRF policies.

**Architecture:** A new standard-library-only `policy_artifacts.py` module owns immutable transport records, strict JSON parsing, deterministic serialization, SHA-256 identity, constructors from native tuning reports, and delegation to the existing fusion engines. A packaged Draft 2020-12 schema and existing schema-discovery API publish the transport contract. Release work updates every version-bearing, package-smoke, architectural, agent, research, and changelog boundary together.

**Tech Stack:** Python 3.10–3.13, standard-library `dataclasses`/`json`/`hashlib`, pytest, coverage.py, Ruff, JSON Schema Draft 2020-12, pinned development-only `jsonschema`, uv, Hatchling.

## Global Constraints

- Runtime dependencies remain empty.
- Production statement and branch coverage remain exactly 100%.
- Every public production module, class, function, and method has a complete docstring.
- No database, filesystem, network, provider, LLM, scheduler, credential, or remote-registry dependency enters production code.
- Native fusion arithmetic remains only in `weighted_convex_fuse` and `weighted_reciprocal_rank_fuse`.
- Emitted bytes are deterministic but are not represented as RFC 8785 JCS.
- SHA-256 is an integrity binding, not a signature, authentication mechanism, attestation, provenance proof, or SLSA level.
- Package version for the completed feature is `0.19.0`.
- All documentation references use APA 7th edition formatting.

---

### Task 1: Lock the public policy-record contract with failing tests

**Files:**
- Create: `tests/test_policy_artifacts.py`
- Reference: `src/rankweave/tuning.py`
- Reference: `src/rankweave/ranked_list_fusion.py`

**Interfaces:**
- Consumes: existing `WeightedConvexTuningReport`, `WeightedRRFTuningReport`, `weighted_convex_fuse`, and `weighted_reciprocal_rank_fuse`.
- Produces: required behavior for `FusionPolicyChannelWeight`, `FusionPolicyArtifact`, `fusion_policy_from_convex_tuning`, `fusion_policy_from_rrf_tuning`, `serialize_fusion_policy`, `parse_fusion_policy`, `sha256_fusion_policy`, and `apply_fusion_policy`.

- [ ] **Step 1: Write the failing valid-artifact constructor tests**

```python
from rankweave.policy_artifacts import (
    FUSION_POLICY_SCHEMA_VERSION,
    FusionPolicyArtifact,
    FusionPolicyChannelWeight,
)


def test_weighted_convex_policy_is_frozen_and_ordered():
    artifact = FusionPolicyArtifact(
        schema_version=FUSION_POLICY_SCHEMA_VERSION,
        policy_kind="weighted_convex",
        policy_id="lexical-heavy",
        channel_weights=(
            FusionPolicyChannelWeight("lexical", 0.8),
            FusionPolicyChannelWeight("dense", 0.2),
        ),
        rank_constant_eta=None,
        selection_source="validation_tuning",
    )

    assert tuple(weight.channel_name for weight in artifact.channel_weights) == (
        "lexical",
        "dense",
    )
```

- [ ] **Step 2: Write parametrized failing validation tests**

Cover wrong schema, unknown kind, padded/control policy IDs and channel names, empty weights, duplicate channels, NaN/infinity, negative or >1 weights, non-unit sums, boolean eta, convex non-null eta, RRF null/non-positive eta, and unsupported selection source.

- [ ] **Step 3: Run the focused tests and verify RED**

Run:

```bash
uv run --frozen --extra dev --python 3.13 \
  python -m pytest tests/test_policy_artifacts.py -q
```

Expected: collection fails because `rankweave.policy_artifacts` does not exist.

- [ ] **Step 4: Commit the failing contracts**

```bash
git add tests/test_policy_artifacts.py
git commit -m "test: define fusion policy artifact contract"
```

---

### Task 2: Implement immutable records and direct validation

**Files:**
- Create: `src/rankweave/policy_artifacts.py`
- Test: `tests/test_policy_artifacts.py`

**Interfaces:**
- Produces:
  - `FUSION_POLICY_SCHEMA_VERSION = "rankweave.fusion-policy.v1"`
  - `WEIGHTED_CONVEX_POLICY_KIND = "weighted_convex"`
  - `WEIGHTED_RRF_POLICY_KIND = "weighted_rrf"`
  - `FusionPolicyChannelWeight(channel_name: str, weight: float)`
  - `FusionPolicyArtifact(schema_version: str, policy_kind: str, policy_id: str, channel_weights: tuple[FusionPolicyChannelWeight, ...], rank_constant_eta: int | None, selection_source: str)`

- [ ] **Step 1: Implement the minimum immutable records**

Use frozen dataclasses and `__post_init__` validation. Snapshot iterable input to tuples only through public constructors; direct dataclass fields require the declared immutable tuple.

- [ ] **Step 2: Reuse native convex-weight validation**

Construct an insertion-ordered `dict` from the weight tuple and call the existing `_validate_convex_weights`. Reject duplicate names before conversion so dictionary overwrites cannot hide malformed input.

- [ ] **Step 3: Run focused tests and verify GREEN**

```bash
uv run --frozen --extra dev --python 3.13 \
  python -m pytest tests/test_policy_artifacts.py -q
```

- [ ] **Step 4: Run Ruff and coverage for the module**

```bash
uv run --frozen --extra dev --python 3.13 python -m ruff check \
  src/rankweave/policy_artifacts.py tests/test_policy_artifacts.py
uv run --frozen --extra dev --python 3.13 python -m coverage run \
  -m pytest tests/test_policy_artifacts.py -q
uv run --frozen --extra dev --python 3.13 python -m coverage report
```

- [ ] **Step 5: Commit**

```bash
git add src/rankweave/policy_artifacts.py tests/test_policy_artifacts.py
git commit -m "feat: validate immutable fusion policy artifacts"
```

---

### Task 3: Add strict deterministic transport and exact-byte identity

**Files:**
- Modify: `src/rankweave/policy_artifacts.py`
- Modify: `tests/test_policy_artifacts.py`

**Interfaces:**
- Produces:
  - `serialize_fusion_policy(artifact: FusionPolicyArtifact) -> bytes`
  - `parse_fusion_policy(document: str) -> FusionPolicyArtifact`
  - `sha256_fusion_policy(artifact: FusionPolicyArtifact) -> str`

- [ ] **Step 1: Write failing byte-transport tests**

Assert the exact compact document and terminal newline:

```python
assert serialize_fusion_policy(artifact) == (
    b'{"schema_version":"rankweave.fusion-policy.v1",'
    b'"policy_kind":"weighted_convex","policy_id":"lexical-heavy",'
    b'"channel_weights":[{"channel_name":"lexical","weight":0.8},'
    b'{"channel_name":"dense","weight":0.2}],'
    b'"rank_constant_eta":null,"selection_source":"validation_tuning"}\n'
)
```

Add byte-identical round trip and Unicode-ID cases.

- [ ] **Step 2: Write failing hostile JSON tests**

Reject duplicate properties with `object_pairs_hook`, `NaN`/`Infinity` with `parse_constant`, non-object roots, unknown and missing properties, extra nested properties, wrong arrays, invalid eta, duplicate channels, and malformed weights.

- [ ] **Step 3: Verify RED**

Run the focused tests and confirm missing functions cause the expected failures.

- [ ] **Step 4: Implement deterministic serialization**

Build the object in fixed insertion order, call `json.dumps(..., ensure_ascii=False, allow_nan=False, separators=(",", ":"))`, encode UTF-8, and append `b"\n"`.

- [ ] **Step 5: Implement strict parsing**

Reject duplicate names before ordinary mapping construction. Require the exact root-key tuple in the public order; require exact nested keys for channel entries; then construct frozen records so one validation path owns value domains.

- [ ] **Step 6: Implement SHA-256**

```python
return hashlib.sha256(serialize_fusion_policy(artifact)).hexdigest()
```

- [ ] **Step 7: Run focused tests, Ruff, and module coverage**

Expected: all focused tests pass and every production branch introduced in the module is executed.

- [ ] **Step 8: Commit**

```bash
git add src/rankweave/policy_artifacts.py tests/test_policy_artifacts.py
git commit -m "feat: serialize and verify exact fusion policy bytes"
```

---

### Task 4: Construct artifacts from native tuning evidence

**Files:**
- Modify: `src/rankweave/policy_artifacts.py`
- Modify: `tests/test_policy_artifacts.py`

**Interfaces:**
- Produces:
  - `fusion_policy_from_convex_tuning(report, *, policy_id: str, selection_source: str) -> FusionPolicyArtifact`
  - `fusion_policy_from_rrf_tuning(report, *, policy_id: str, selection_source: str) -> FusionPolicyArtifact`

- [ ] **Step 1: Write failing tests using real tuning calls**

Create two judged queries, run `tune_weighted_convex_fusion` and `tune_weighted_reciprocal_rank_fusion`, and assert selected channel order, exact weights, kind, policy ID, source, and eta.

- [ ] **Step 2: Write identity-boundary tests**

When `best_policy_id` is a string, reject a different `policy_id`. When the report identifier is non-string, accept an explicit valid transport ID and never call `str(report.best_policy_id)`.

- [ ] **Step 3: Verify RED**

- [ ] **Step 4: Implement report constructors**

Type-check the report classes, preserve `best_channel_weights`, and delegate all artifact validation to `FusionPolicyArtifact`.

- [ ] **Step 5: Verify GREEN and commit**

```bash
git add src/rankweave/policy_artifacts.py tests/test_policy_artifacts.py
git commit -m "feat: create deployable policies from tuning evidence"
```

---

### Task 5: Apply artifacts through native fusion engines

**Files:**
- Modify: `src/rankweave/policy_artifacts.py`
- Modify: `tests/test_policy_artifacts.py`

**Interfaces:**
- Produces:
  - `apply_fusion_policy(artifact, *, channel_results=None, channel_rankings=None, limit=None)`

- [ ] **Step 1: Write failing real-result parity tests**

For convex and weighted RRF, compare the returned frozen fused items with direct native calls using the artifact's channel weights and eta.

- [ ] **Step 2: Write incompatible-mode tests**

Reject neither input, both inputs, rankings for convex, results for RRF, and boolean/non-positive limits through established native contracts.

- [ ] **Step 3: Verify RED**

- [ ] **Step 4: Implement one dispatch adapter**

Convert the ordered weights to an ordinary insertion-ordered dictionary and call only the matching native fusion API. Do not perform score or rank arithmetic.

- [ ] **Step 5: Verify GREEN and commit**

```bash
git add src/rankweave/policy_artifacts.py tests/test_policy_artifacts.py
git commit -m "feat: apply policy artifacts through native fusion"
```

---

### Task 6: Publish and validate the Draft 2020-12 schema

**Files:**
- Create: `src/rankweave/schemas/fusion-policy-v1.schema.json`
- Modify: `src/rankweave/report_schemas.py`
- Modify: `tests/test_report_schemas.py`
- Modify: `tests/test_policy_artifacts.py`

**Interfaces:**
- Existing `available_report_schemas`, `load_report_schema_text`, and `load_report_schema` add selector `("policy", "v1")`.

- [ ] **Step 1: Write failing schema-discovery test**

Append the exact `ReportSchemaDescriptor` to stable discovery order.

- [ ] **Step 2: Write failing real-artifact validation tests**

Validate emitted convex and RRF artifacts with `Draft202012Validator`. Mutate representative required, extra, enum, digest-independent, eta, and weight structures and require `ValidationError`.

- [ ] **Step 3: Verify RED**

- [ ] **Step 4: Add the strict schema resource**

Use `$schema`, stable `$id`, `const`, exact `required`, `additionalProperties: false`, array `minItems`, nested strict entries, string patterns, numeric ranges, and conditional eta semantics.

- [ ] **Step 5: Extend schema discovery**

Add `policy` to supported report types and one descriptor without changing existing descriptor order.

- [ ] **Step 6: Verify GREEN and commit**

```bash
git add src/rankweave/schemas/fusion-policy-v1.schema.json \
  src/rankweave/report_schemas.py tests/test_report_schemas.py \
  tests/test_policy_artifacts.py
git commit -m "feat: publish the fusion policy schema"
```

---

### Task 7: Export the public API and verify the installed package

**Files:**
- Modify: `src/rankweave/__init__.py`
- Modify: `.github/workflows/ci.yml`
- Modify: `tests/test_version.py`
- Test: installed-wheel smoke embedded in `.github/workflows/ci.yml`

**Interfaces:**
- Package root re-exports all public policy constants, records, constructors, transport helpers, digest helper, and application adapter.

- [ ] **Step 1: Add failing root-export tests**

Import every public symbol from `rankweave` rather than the implementation module.

- [ ] **Step 2: Export symbols and update `__all__`**

- [ ] **Step 3: Require wheel members**

Add `rankweave/policy_artifacts.py` and `rankweave/schemas/fusion-policy-v1.schema.json` to package inspection.

- [ ] **Step 4: Extend installed smoke**

In the isolated environment, construct tuning reports, create both artifacts, assert exact serialize/parse/digest behavior, load the packaged schema, and reproduce native fusion outputs.

- [ ] **Step 5: Run full local package gate**

```bash
uv sync --frozen --extra dev --python 3.13
uv run --frozen --extra dev --python 3.13 python -m compileall -q src
uv run --frozen --extra dev --python 3.13 python -m ruff check .
uv run --frozen --extra dev --python 3.13 python -m coverage run -m pytest -q
uv run --frozen --extra dev --python 3.13 python -m coverage report
uv build --wheel --sdist --out-dir dist
```

- [ ] **Step 6: Commit**

```bash
git add src/rankweave/__init__.py .github/workflows/ci.yml tests
git commit -m "test: verify installed fusion policy contracts"
```

---

### Task 8: Synchronize RankWeave 0.19.0 and commercial documentation

**Files:**
- Modify: `pyproject.toml`
- Modify: `uv.lock`
- Modify: `src/rankweave/__init__.py`
- Modify: `tests/test_version.py`
- Modify: `CHANGELOG.md`
- Modify: `README.md`
- Modify: `AGENTS.md`
- Modify: `CLAUDE.md`
- Modify: `ARCHITECTURE.md`
- Modify: `docs/releasing.md`
- Modify: `docs/research/README.md`
- Create: `docs/fusion-policy-artifacts.md`
- Create: `docs/adr/0007-canonical-fusion-policy-artifact.md`

**Interfaces:**
- Release identity becomes exactly `0.19.0` everywhere.

- [ ] **Step 1: Update version-bearing files**

Synchronize project metadata, lock metadata, public version, expected-version test, installed smoke, README installation examples, and release runbook.

- [ ] **Step 2: Add the release entry**

Record added API, validation, compatibility, deterministic-byte boundary, digest limitation, and no-runtime-dependency guarantee in `CHANGELOG.md`.

- [ ] **Step 3: Write product documentation and Mermaid flow**

Document creation, persistence, strict parsing, digest comparison, application, held-out interpretation, naruon handoff, and rollback. Include exact API examples and a machine-readable transport example.

- [ ] **Step 4: Record architecture and agent contracts**

Require native fusion delegation, ordered weights, strict parsing, schema/version synchronization, no JCS overclaim, and no source-only consumer claim.

- [ ] **Step 5: Add APA 7th authority**

Document RFC 8785 as the explicit non-conformance boundary, FIPS 180-4 for SHA-256, JSON Schema Draft 2020-12 for structural validation, and SLSA v1.2 for the digest/provenance distinction.

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml uv.lock src tests .github README.md CHANGELOG.md \
  AGENTS.md CLAUDE.md ARCHITECTURE.md docs
git commit -m "release: prepare RankWeave 0.19.0"
```

---

### Task 9: Perform exact-head verification and protected merge

**Files:**
- Verify only; no additional product behavior.

- [ ] **Step 1: Run Python 3.10–3.13 CI**

Require compile, Ruff, complete tests, and 100% statement/branch coverage in every matrix lane.

- [ ] **Step 2: Run package smoke**

Require wheel and sdist inspection, isolated installation, root API/schema/policy application smoke, and `pip check`.

- [ ] **Step 3: Run Security Scan, Semgrep, CodeQL, Strix, Noema, OpenCode, and CodeRabbit surfaces**

Inspect every actionable current-head review and resolve all valid threads.

- [ ] **Step 4: Confirm exact-head state**

Require non-draft, mergeable, zero unresolved actionable threads, no current-head changes requested, required status success, and no bootstrap or patch files in the final diff.

- [ ] **Step 5: Squash merge without bypass**

Enable auto-merge or use protected squash merge with the exact expected head SHA.

- [ ] **Step 6: Confirm PR queue state and continue the commercialization loop**

If the queue is empty, select the next buyer-visible gap. Do not publish 0.19.0 until the governed release workflow, external Trusted Publisher configuration, artifacts, and attestations are independently verified.
