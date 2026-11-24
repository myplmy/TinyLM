"""Check exact ACTD match parity and CPU cost for two native-prefix policies."""

import hashlib
import json
import os
from pathlib import Path
import random
import statistics
import time

from scripts import p106b_actd_cache as original
from scripts import p106b_actd_indexed_alignment as indexed


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "test_result/evidence/p106b_actd_indexed_prefix_alignment_cpu_v1_20261118"
SOURCES = ("scripts/p106b_actd_cache.py", "scripts/p106b_actd_anchor.py",
           "scripts/p106b_actd_indexed_alignment.py", "scripts/diag_p106b_actd_indexed_alignment.py")


def pins():
    return {file: hashlib.sha256((ROOT/file).read_bytes()).hexdigest().upper() for file in SOURCES}


def prefixes(counts, seed):
    random_source = random.Random(seed)
    rows = []
    for owner, count in enumerate(counts, 1):
        char = owner * 20_000
        for _ in range(count):
            char += random_source.randrange(4)
            i = len(rows)
            rows.append(dict(character_end=char, owner=owner, prefix_raw_index=i*2,
                             target_raw_index=i*2+1, target_id=random_source.randrange(32768)))
    return rows


def same(student, teacher, policy):
    old = original.align_positions(student, teacher, policy=policy)
    new = indexed.align_positions(student, teacher, policy=policy)
    assert old == new
    if policy == "causal_left_variant":
        assert all(row["lookahead_characters"] == 0 for row in new[0])
    return new


def measure(student, teacher, policy):
    expected = same(student, teacher, policy)
    timing = {"original": [], "indexed": []}
    for label, implementation in (("original", original), ("indexed", indexed),
                                  ("indexed", indexed), ("original", original)):
        started = time.perf_counter()
        value = implementation.align_positions(student, teacher, policy=policy)
        timing[label].append(time.perf_counter() - started)
        assert value == expected
    return dict(student=len(student), teacher=len(teacher), policy=policy, accepted=len(expected[0]),
        held=len(expected[1]), per_arm_seconds=timing,
        ratio=statistics.mean(timing["original"]) / statistics.mean(timing["indexed"]))


def main():
    assert os.environ.get("CUDA_VISIBLE_DEVICES") == ""
    if OUT.exists():
        raise FileExistsError("Preserve the previous alignment study")
    sources = pins()
    rng = random.Random(1337)
    checked = 0
    for case in range(100):
        s = prefixes([rng.randrange(17) for _ in range(5)], case * 2)
        t = prefixes([rng.randrange(17) for _ in range(5)], case * 2 + 1)
        for policy in original.POLICIES:
            out, holds = same(s, t, policy)
            assert len(out) + len(holds) == len(s)
            checked += len(s)
    timing = []
    for count in (256, 1024):
        s, t = prefixes([count], 41), prefixes([count], 77)
        for policy in original.POLICIES:
            timing.append(measure(s, t, policy))
    assert sources == pins()
    OUT.mkdir(exist_ok=False)
    with (OUT/"report.json").open("x", encoding="utf-8") as stream:
        json.dump(dict(schema="ACTD_INDEXED_PREFIX_CPU_V1", sources=sources, randomized_cases=100,
            randomized_student_cases_both_policies=checked, timing=timing, rows_and_holds_exact=True,
            actual_train_steps=0, model_loads=0, changed_legacy_paths=0), stream, indent=2, allow_nan=False)
        print(file=stream)
    print("ACTD_INDEXED_PREFIX_CPU", checked, [(r["student"], r["policy"], round(r["ratio"], 3)) for r in timing], flush=True)


if __name__ == "__main__":
    main()
