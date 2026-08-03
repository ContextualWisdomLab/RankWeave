import rankweave
from rankweave.trec import (
    TrecQrelEntry,
    TrecQrels,
    TrecRun,
    TrecRunEntry,
    evaluate_trec_run,
    format_trec_qrels,
    format_trec_run,
    parse_trec_qrels,
    parse_trec_run,
)


def test_trec_interoperability_api_is_exported_from_package_root():
    assert rankweave.TrecQrelEntry is TrecQrelEntry
    assert rankweave.TrecQrels is TrecQrels
    assert rankweave.TrecRunEntry is TrecRunEntry
    assert rankweave.TrecRun is TrecRun
    assert rankweave.parse_trec_qrels is parse_trec_qrels
    assert rankweave.parse_trec_run is parse_trec_run
    assert rankweave.format_trec_qrels is format_trec_qrels
    assert rankweave.format_trec_run is format_trec_run
    assert rankweave.evaluate_trec_run is evaluate_trec_run
