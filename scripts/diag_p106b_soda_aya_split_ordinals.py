"""Verify Aya SODA release order and measure splits of identical source views."""

from collections import Counter
from datetime import datetime, timedelta
from hashlib import sha256
import json
import os
from time import monotonic

from scripts import diag_p106b_soda_aya_grouping as content
from tinylm.data.sft import conversation_split_key


OUTPUT = content.AUDIT / "SODA_AYA_ORDINAL_AND_SPLIT_v1.json"
TOPIC_ROWS, DIALOGUE_ROWS = 1_191_582, 628_713
TOPIC_START, DIALOGUE_START, PREMISE_START = 9_108_639, 10_300_221, 10_928_934
TRANSLATED_START = 2_030_495
CEILING = 200


def slice_rows(files, first, count, name):
    start, end = first - 1, first - 1 + count
    expected = (content.FAMILIES[1] if name == "translated_1" else content.FAMILIES[0],
                int(name[-1]))
    row_id = first
    for parquet, file_start in files:
        if file_start >= end or file_start + parquet.metadata.num_rows <= start:
            continue
        offset = file_start
        for index in range(parquet.metadata.num_row_groups):
            group_end = offset + parquet.metadata.row_group(index).num_rows
            lo, hi = max(offset, start), min(group_end, end)
            if hi > lo:
                table = parquet.read_row_group(index, columns=content.COLUMNS, use_threads=False)
                for item in table.slice(lo - offset, hi - lo).to_pylist():
                    if (item["id"] != row_id or (item["dataset_name"], item["template_id"]) != expected
                            or item["language"] != "eng" or item["split"] != "train"):
                        raise ValueError("Aya range is not a continuous run of the expected template and split")
                    yield item
                    row_id += 1
            offset = group_end
            if offset >= end:
                break
    if row_id != first + count:
        raise ValueError("Incomplete exact Aya range")


def ordered_topic_hash(files, first, name, gate):
    check = sha256()
    for index, row in enumerate(slice_rows(files, first, TOPIC_ROWS, name)):
        if index % 8192 == 0:
            gate()
        story, _, topic = content.extract(name, row["inputs"], row["targets"])
        if not story or not topic:
            raise ValueError("Exact topic-and-narrative wrapper required")
        check.update(content.compound_key(story, topic))
    return check.hexdigest().upper()


def legacy_split(row):
    key = conversation_split_key({"messages": [{"role": "user", "content": row["inputs"]}]})
    return ("val" if int.from_bytes(key[:4], "big") % 20 == 0 else "train"), key.hex().upper()


def compare_dialogue(files, gate):
    counts, across, witness = Counter(), Counter(), None
    dialogue = slice_rows(files, DIALOGUE_START, DIALOGUE_ROWS, "plain_1")
    premise = slice_rows(files, PREMISE_START, DIALOGUE_ROWS, "plain_2")
    for index, (a, b) in enumerate(zip(dialogue, premise, strict=True)):
        if index % 8192 == 0:
            gate()
        story_a, lines_a, _ = content.extract("plain_1", a["inputs"], a["targets"])
        story_b, lines_b, _ = content.extract("plain_2", b["inputs"], b["targets"])
        if not story_a or not story_b:
            raise ValueError("Missing exact extracted narrative")
        counts["pairs"] += 1
        if story_a != story_b:
            continue
        counts["same_narrative"] += 1
        left, right = content.exact_dialogue(lines_a), content.exact_dialogue(lines_b)
        if not left or left != right:
            continue
        counts["same_narrative_and_dialogue"] += 1
        split_a, key_a = legacy_split(a)
        split_b, key_b = legacy_split(b)
        across[f"{split_a}__{split_b}"] += 1
        if split_a != split_b and witness is None:
            witness = dict(narrative_and_dialogue_sha256=content.compound_key(story_a,left).hex().upper(),
                           plain_1=dict(id=a["id"], split=split_a, first_user_sha256=key_a),
                           plain_2=dict(id=b["id"], split=split_b, first_user_sha256=key_b))
    assert sum(across.values()) == counts["same_narrative_and_dialogue"]
    return dict(counts=dict(counts), within_exact_dialogue_legacy_splits=dict(across),
                crossed=across["train__val"] + across["val__train"], first_crossed_pair=witness)


def main():
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "" or OUTPUT.exists():
        raise ValueError("Explicit CPU mode and fresh audit receipt required")
    started = monotonic()
    start = datetime.now().astimezone()
    if content.END - start < timedelta(seconds=240):
        raise TimeoutError("User 177 window")

    def gate():
        if monotonic() - started > CEILING or datetime.now(content.END.tzinfo) >= content.END:
            raise TimeoutError("Scoped Aya range audit time limit")

    with content.OUTPUT.open(encoding="utf-8") as f:
        earlier = json.load(f)
    if (earlier["revision"] != content.REVISION
            or earlier["observed_rows"] != {"translated_1": 4 * TOPIC_ROWS, "plain_4": TOPIC_ROWS,
                                            "plain_3": DIALOGUE_ROWS, "plain_1": DIALOGUE_ROWS, "plain_2": DIALOGUE_ROWS}
            or earlier["wrapper_refusals"] or earlier["row_ordinal_disagreements"]):
        raise ValueError("The full prior metadata/content scan must support the precise ranges")
    paths = content.read_sources()
    files = []
    offset = 0
    for path, prior in paths:
        parquet = content.pq.ParquetFile(path)
        if parquet.metadata.num_rows != prior["raw_metadata_rows"]:
            raise ValueError("Physical row extent changed")
        files.append((parquet, offset))
        offset += parquet.metadata.num_rows
    base = ordered_topic_hash(files, TOPIC_START, "plain_4", gate)
    orders = []
    for index in range(4):
        first = TRANSLATED_START + index * TOPIC_ROWS
        digest = ordered_topic_hash(files, first, "translated_1", gate)
        orders.append(dict(first_id=first, last_id=first + TOPIC_ROWS - 1, sha256=digest, same_order=digest==base))
        print("SODA_ORDER_BLOCK", index + 1, first, digest == base, flush=True)
    comparison = compare_dialogue(files, gate)
    if not all(content.signature(path) == prior["file_identity"] for path, prior in paths):
        raise ValueError("At least one physical source changed during the audit")
    result = dict(schema="P106B_SODA_AYA_ORDINAL_AND_SPLIT_V1", revision=content.REVISION,
                  preceding_scan_sha256=content.checksum(content.OUTPUT),
                  topic_narrative_plain=dict(first_id=TOPIC_START, last_id=TOPIC_START+TOPIC_ROWS-1,
                                             rows=TOPIC_ROWS, sha256=base), translated_blocks=orders,
                  dialogue_first_ids={"plain_1": DIALOGUE_START, "plain_2": PREMISE_START},
                  dialogue=comparison, original_ai2_rows_read=0, actual_split_changes=0, corpus_admitted_rows=0,
                  teacher_calls=0, started=start.isoformat(), finished=datetime.now().astimezone().isoformat(),
                  seconds=monotonic()-started)
    with OUTPUT.open("x", encoding="utf-8") as target:
        json.dump(result, target, ensure_ascii=False, indent=2, allow_nan=False)
        target.write("\n")
    print("SODA_LEGACY_SPLIT", comparison, flush=True)


if __name__ == "__main__":
    main()
