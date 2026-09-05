"""Time an explicit JSON replay request; emit only timings and evidence digests."""

import hashlib
import json
import sys
import time
from dataclasses import asdict

from rankweave import compare_paired_p95


def main() -> None:
    """Measure every requested call, including the first, without a warm-up."""
    sample_count = int(sys.argv[1])
    if sample_count < 1 or len(sys.argv) != 2:
        raise ValueError("provide one positive timing sample count")
    replay_request = json.load(sys.stdin)
    replay_request["observation_pairs"] = [
        tuple(row) for row in replay_request["observation_pairs"]
    ]
    elapsed_ms = []
    result_digests = set()
    for _ in range(sample_count):
        started = time.perf_counter_ns()
        report = compare_paired_p95(**replay_request)
        elapsed_ms.append((time.perf_counter_ns() - started) / 1_000_000)
        result_digests.add(
            hashlib.sha256(
                json.dumps(
                    asdict(report),
                    sort_keys=True,
                    allow_nan=False,
                ).encode()
            ).hexdigest()
        )
    if len(result_digests) != 1:
        raise AssertionError("replaying the same request changed its report")
    print(
        json.dumps(
            {
                "elapsed_ms": elapsed_ms,
                "result_digest": result_digests.pop(),
                "input_digest": report.ordered_input_digest,
                "observation_count": report.observation_count,
                "draw_count": len(report.resampled_differences),
            }
        )
    )


if __name__ == "__main__":
    main()
