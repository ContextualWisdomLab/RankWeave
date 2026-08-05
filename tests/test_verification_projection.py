"""Regression tests for the artifact-verification JSON projection."""

import pytest

from rankweave.cli import artifact_verification_to_dict


def test_artifact_verification_projection_rejects_wrong_report_type():
    """Reject non-verification values instead of emitting misleading JSON."""
    with pytest.raises(
        ValueError,
        match="report must be ArtifactVerificationReport",
    ):
        artifact_verification_to_dict(object())
