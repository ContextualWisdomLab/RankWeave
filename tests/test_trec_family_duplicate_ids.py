from collections.abc import Mapping

import pytest

from rankweave.trec_family_comparison import compare_trec_run_family

BASELINE_RUN = "query Q0 relevant 1 1.0 baseline\n"
QRELS = "query 0 relevant 1\n"
CANDIDATE_RUN = "query Q0 relevant 1 1.0 candidate\n"


class _DuplicateCandidateMapping(Mapping):
    def __getitem__(self, key):
        return CANDIDATE_RUN

    def __iter__(self):
        return iter(("duplicate",))

    def __len__(self):
        return 1

    def items(self):
        return [
            ("duplicate", CANDIDATE_RUN),
            ("duplicate", CANDIDATE_RUN),
        ]


def test_family_comparison_rejects_duplicate_candidate_identifiers():
    with pytest.raises(ValueError, match="duplicate candidate identifier"):
        compare_trec_run_family(
            BASELINE_RUN,
            _DuplicateCandidateMapping(),
            QRELS,
            cutoff=1,
        )
