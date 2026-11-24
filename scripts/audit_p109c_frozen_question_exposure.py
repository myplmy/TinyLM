"""Check exact frozen evaluation questions against the admitted P109C inputs."""

from collections import defaultdict
import json
from pathlib import Path
from time import perf_counter
import unicodedata

import numpy as np

from scripts import audit_p109c_v11_partial_overlap as anchors
from scripts import eval_p109b_first_use as first
from scripts import eval_p109c_completed as evaluation


ROOT = evaluation.ROOT
INPUT = ROOT / "data_cache/p109c_scratch330_v1_admitted_bundle_20261121.json"
INPUT_SHA = "26A2CFA47F83E222B8E985365B473284390060EE98B1CA1FCB6D6EE4B3E8436E"
DOCUMENTS = ROOT / "test_result/evidence/p107_v11_binary_documents_v1_20261121/profile.json"
OUT = DOCUMENTS.parent.with_name("p109c_frozen_question_exposure_cpu_20261121")


def questions(tokenizer):
    final, _ = evaluation.final200_inputs()
    queries = {row["id"]: row["prompt"] for row in final}
    for row in first.examples(tokenizer):
        prefix = "<|im_start|>user\n"
        suffix = "<|im_end|>\n<|im_start|>assistant\n"
        if not row["prompt"].startswith(prefix) or not row["prompt"].endswith(suffix):
            raise ValueError("a frozen first-use ChatML envelope differs")
        queries[f"first_{row['language']}_{row['case']}"] = row["prompt"][len(prefix):-len(suffix)]
    return queries


def canonical(value):
    return " ".join(unicodedata.normalize("NFC", value).split())


def course_matches(manifest, prompts):
    directory = (ROOT / manifest["provenance"]["local_course"]).parent
    schedule = directory / "schedule.json"
    if evaluation.core6.digest(schedule) != manifest["provenance"]["verified_course_schedule_sha256"]:
        raise ValueError("the admitted course schedule identity differs")
    proof = evaluation.read_json(schedule)
    normalized = {key: canonical(value) for key, value in prompts.items()}
    records = {}
    matches = []
    for lane in ("plain", "all_axes"):
        path = evaluation.regular_file(directory / proof[lane]["file"])
        if path.parent != directory or evaluation.core6.digest(path) != proof[lane]["sha256"]:
            raise ValueError("the admitted authored course source differs")
        records[lane] = dict(rows=0, user_turns=0)
        with path.open(encoding="utf-8") as stream:
            for number, line in enumerate(stream, 1):
                row = json.loads(line)
                records[lane]["rows"] += 1
                for turn, message in enumerate(row["record"]["messages"]):
                    if message["role"] != "user":
                        continue
                    body = canonical("\n".join(item["text"] for item in message["content"] if item["type"] == "text"))
                    records[lane]["user_turns"] += 1
                    for key, value in normalized.items():
                        if value in body:
                            matches.append(dict(id=key, lane=lane, row=number, turn=turn, root=row["root"],
                                                exact_normalized_turn=value == body))
    return dict(records=records, matches=matches)


def raw_matches(data, beyond, tokenizer, prompts):
    patterns = defaultdict(set)
    for name, prompt in prompts.items():
        for boundary in ("", " ", "\n"):
            patterns[tuple(tokenizer.encode(boundary + prompt).ids)].add(name)
    table = defaultdict(list)
    for ids, names in patterns.items():
        offset = (len(ids) - 6) // 2
        if offset < 0:
            raise ValueError("the full-prompt anchor requires at least six tokens")
        tokens = np.asarray(ids, dtype=np.uint16)
        key = int(anchors.keys(tokens, np.array([offset]))[0])
        table[key].append((tokens, offset, names))
    sorted_keys = np.array(sorted(table), dtype=np.uint64)
    lookup = np.zeros(int(anchors.LOW_BITS) + 1, dtype=bool)
    lookup[sorted_keys & anchors.LOW_BITS] = True
    hits = defaultdict(set)
    for low in range(0, len(data) - 5, anchors.CHUNK):
        high = min(low + anchors.CHUNK, len(data) - 5)
        signatures = anchors.keys(data, np.arange(low, high, dtype=np.int64))
        possible = np.flatnonzero(lookup[signatures & anchors.LOW_BITS])
        values = signatures[possible]
        indices = np.minimum(np.searchsorted(sorted_keys, values), len(sorted_keys) - 1)
        for index in possible[sorted_keys[indices] == values]:
            for tokens, offset, names in table[int(signatures[index])]:
                start = low + int(index) - offset
                stop = start + len(tokens)
                if start < 0 or stop > len(data) or not np.array_equal(tokens, data[start:stop]):
                    continue
                document = int(np.searchsorted(beyond, start, side="left"))
                if stop <= beyond[document] + 1:
                    for name in names:
                        hits[name].add((document, start, len(tokens)))
    return dict(training_tokens=len(data), anchor_positions=len(data) - 5, variants=len(patterns),
                matches={key: sorted(value) for key, value in sorted(hits.items())})


def main():
    if OUT.exists():
        raise FileExistsError(OUT)
    started = perf_counter()
    if evaluation.core6.digest(INPUT) != INPUT_SHA:
        raise ValueError("the admitted P109C input manifest differs")
    manifest = evaluation.read_json(INPUT)
    source = evaluation.read_json(DOCUMENTS)
    train = source["splits"]["train"]
    if train["binary"]["sha256"] != manifest["cache"]["sha256"]["train.bin"]:
        raise ValueError("the document index does not refer to the admitted P109C train bytes")
    tokenizer = evaluation.load_tokenizer()
    prompts = questions(tokenizer)
    course = course_matches(manifest, prompts)
    data, _, ends = anchors.split(train)
    report = dict(input_sha256=INPUT_SHA, source_sha256=evaluation.core6.digest(Path(__file__)),
                  train_index_sha256=train["index"]["sha256"], questions=len(prompts), course=course,
                  raw=raw_matches(data, ends, tokenizer, prompts), seconds=perf_counter() - started)
    OUT.mkdir(exist_ok=False)
    evaluation.training.publish(OUT / "report.json", report)
    print("P109C_EXACT_QUESTION_AUDIT", len(prompts), len(course["matches"]), len(report["raw"]["matches"]), flush=True)


if __name__ == "__main__":
    main()
