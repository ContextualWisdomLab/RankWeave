# Trusted release provenance grounding

RankWeave's release workflow separates four claims that are often conflated:

1. **Workflow-artifact transport** — GitHub stores an immutable workflow artifact and automatically compares its archive digest when it is downloaded.
2. **Fail-closed distribution identity** — RankWeave carries a `SHA256SUMS` file and the manifest's SHA-256 through a build-job output; downstream jobs verify the manifest and then the wheel and source distribution before use.
3. **GitHub build provenance** — `actions/attest` signs an in-toto/SLSA provenance statement for the exact wheel and source-distribution digests.
4. **PyPI index-hosted attestations** — PyPI Trusted Publishing exchanges the GitHub OIDC identity for a short-lived upload credential and stores PEP 740 attestations with the distributions.

GitHub's official workflow-artifact documentation states that `download-artifact` automatically validates the downloaded archive digest but reports a mismatch as a warning. The action's current input contract has no `digest-mismatch` option. RankWeave therefore does not treat that warning-only validation as its publication decision and does not pass an unsupported input. The separate manifest digest is exported by the non-publishing build job, so changing both downloaded files and their manifest cannot satisfy the downstream check without also changing the trusted job output.

The workflow's checksum verification establishes exact-byte identity across jobs. GitHub and PyPI attestations establish signed provenance statements within their respective trust roots. None of these controls proves that RankWeave is free of vulnerabilities, that a reported retrieval comparison is scientifically valid, or that a downstream deployment satisfies a buyer's governance policy.

## References — APA 7th edition

GitHub. (n.d.). *Storing and sharing data from a workflow*. GitHub Docs. Retrieved August 5, 2026, from https://docs.github.com/en/actions/writing-workflows/choosing-what-your-workflow-does/storing-and-sharing-data-from-a-workflow

GitHub. (n.d.). *Using artifact attestations to establish provenance for builds*. GitHub Docs. Retrieved August 5, 2026, from https://docs.github.com/en/actions/how-tos/secure-your-work/use-artifact-attestations/use-artifact-attestations

Python Packaging Authority. (n.d.). *Publishing with a Trusted Publisher*. PyPI documentation. Retrieved August 5, 2026, from https://docs.pypi.org/trusted-publishers/using-a-publisher/

Supply-chain Levels for Software Artifacts. (n.d.). *Build: Verifying artifacts (SLSA specification v1.2)*. OpenSSF. Retrieved August 5, 2026, from https://slsa.dev/spec/v1.2/verifying-artifacts

Trail of Bits. (2023). PEP 740—Index support for digital attestations. *Python Enhancement Proposals*. https://peps.python.org/pep-0740/
