"""Prepare quote-grounded question-switch candidates from already joined SODA TRAIN rows."""

from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import re
import unicodedata

from scripts import diag_p106b_soda_exact_teacher as exact
from tinylm.chat.canonical import normalize, validate
from tinylm.data.sft import IGNORE
from tinylm.train.mtp_sft import encode_record


EVIDENCE = exact.SOURCE.parent
OUT = EVIDENCE / "p106b_soda_speaker_switch_cpu_v1_20261121"
INVENTORY = EVIDENCE / "p106b_soda_candidate_inventory_v1_20261120/report.json"
SOURCE_MAP = EVIDENCE / "p106b_soda_original_lineage_stratified256_v1_20261120/report.json"
RELEASE = "fdc848ab0183208ea7808206c91c724414d0a071"
SOURCE_URL = f"https://huggingface.co/datasets/allenai/soda/blob/{RELEASE}/README.md"
LICENSE = "CC-BY-4.0"
CONTEXT = 1024


def read(path):
    data = path.read_bytes()
    return json.loads(data), sha256(data).hexdigest()


def quote_key(value):
    return " ".join(unicodedata.normalize("NFC", value).casefold().split())


def questions(dialogue):
    turns = [tuple(block.split(": ", 1)) for block in dialogue.split("\n\n")]
    duplicates = Counter(quote_key(utterance) for _, utterance in turns)
    labels = sorted({label for label, _ in turns}, key=len, reverse=True)
    mention = re.compile(r"(?<!\w)(?:" + "|".join(re.escape(name) for name in labels) + r")(?!\w)", re.I)
    qualifying = [(index, label, utterance) for index, (label, utterance) in enumerate(turns)
                  if 12 <= len(utterance) <= 160 and duplicates[quote_key(utterance)] == 1
                  and not mention.search(utterance)]
    if not qualifying:
        return None
    first = qualifying[0]
    second = next((turn for turn in qualifying if turn[1].casefold() != first[1].casefold()), None)
    if second is None:
        return None
    return first, second


def format_record(dialogue, selected, binding, root_sha):
    (_, name_a, quote_a), (_, name_b, quote_b) = selected

    def ask(quote):
        return f"Who says this exact utterance? {json.dumps(quote, ensure_ascii=False)} Reply with the speaker label only."

    group = binding["source_group_id"]
    split = "heldout" if int(group[:8], 16) % 5 == 0 else "candidate_train"
    return validate(normalize(dict(messages=[
        dict(role="user", content="Use the following fictional dialogue as the only source.\n\n" + dialogue + "\n\n" + ask(quote_a)),
        dict(role="assistant", content=name_a),
        dict(role="user", content="Refer to the same dialogue for a different speaker. " + ask(quote_b)),
        dict(role="assistant", content=name_b),
    ], meta=dict(original_source="allenai/soda", original_revision=RELEASE, source_url=SOURCE_URL,
                 source_license=LICENSE, attribution="Ai2 and the SODA authors; quote and question adaptation",
                 original_index=binding["original_index"], aya_id=binding["aya_id"], original_source_split="train",
                 source_group_id=group, source_raw_sha256=root_sha, independent_candidate_split=split,
                 evidence_turn_indices=[selected[0][0], selected[1][0]],
                 target_labels=[name_a, name_b], corpus_admitted=False, generation="RULE_BASED_VISIBLE_SPEAKER"))))


def main():
    bind, bind_sha = read(exact.SOURCE / "report.json")
    original, original_sha = read(SOURCE_MAP)
    inventory, inventory_sha = read(INVENTORY)
    if original["revision"] != RELEASE or bind["source_map_sha256"].lower() != original_sha:
        raise ValueError("the official origin map differs from the existing preparation receipt")
    train_links = {row["aya_id"]: row for row in original["rows"]
                   if row["status"] == "EXACT_TRAIN_LINK" and row["root_splits"] == ["train"]}
    excluded = {row["source_group"] for row in inventory["selected_groups"]}
    source = exact.open_source()
    tokenizer = exact.previous.fixture.tokenize()
    im_end = tokenizer.token_to_id("<|im_end|>")
    cursor = source.start()
    inventory = {"candidate_train": Counter(), "heldout": Counter()}
    skipped, candidates, used = Counter(), [], set()
    for binding in bind["original_group_binding"]:
        row = source.read_next(cursor)
        if row is None or row.next_cursor["next_row"] != cursor["next_row"] + 1:
            raise ValueError("the source ended or skipped a pinned row")
        cursor = row.next_cursor
        if row.prepared is None or row.prepared.trace["source_reference"]["source_row_id"] != binding["aya_id"]:
            raise ValueError("the Aya source row differs")
        group = binding["source_group_id"]
        match = train_links[binding["aya_id"]]
        if any(match[field] != binding[field] for field in ("original_index", "source_group_id")):
            raise ValueError("the source row is outside the verified official TRAIN mapping")
        if group in excluded or group in used:
            skipped["already_represented"] += 1
            continue
        dialogue = row.prepared.evidence_source["messages"][0]["content"][0]["text"]
        selected = questions(dialogue)
        if selected is None:
            skipped["no_distinct_unambiguous_quotes"] += 1
            continue
        record = format_record(dialogue, selected, binding, row.raw_sha256)
        try:
            encoded = encode_record(record, tokenizer, context=CONTEXT)
        except ValueError as error:
            if "context" not in str(error).casefold():
                raise
            skipped["context_exceeded"] += 1
            continue
        for turn, expected in enumerate(record["meta"]["target_labels"], 1):
            labels = [token for token, owner in zip(encoded.y, encoded.segments, strict=True) if owner == turn]
            if not labels or labels[-1] != im_end or tokenizer.decode(labels[:-1]).strip() != expected:
                raise ValueError("a speaker answer or assistant termination changed in the student encoder")
        if any((owner == 0) != (label == IGNORE)
               for owner, label in zip(encoded.segments, encoded.y, strict=True)):
            raise ValueError("user instruction or context received assistant supervision")
        values = inventory[record["meta"]["independent_candidate_split"]]
        values.update(groups=1, input_tokens=encoded.x_tokens, assistant_targets=encoded.targets)
        record["meta"].update(actual_x_tokens=encoded.x_tokens, assistant_targets=encoded.targets)
        candidates.append(record)
        used.add(group)
    if source.read_next(cursor) is not None or sum(skipped.values()) + len(candidates) != bind["mapped_rows"]:
        raise ValueError("source coverage differs from the prepared inventory")
    if not candidates or not all(inventory.values()):
        raise ValueError("both candidate splits require independently rooted examples")

    OUT.mkdir(exist_ok=False)
    writer = exact.previous.ShardWriter(OUT, "candidate")
    for row in candidates:
        writer.append(row)
    exact.previous.verify(OUT, writer.close(lineage=dict(scope="VISIBLE_SPEAKER_SWITCH_RESEARCH", corpus_admitted=False)))
    exact.io.write(OUT / "report.json", dict(original_release=RELEASE, source_url=SOURCE_URL, source_license=LICENSE,
        original_split="train", scope="RESEARCH_CANDIDATE_ONLY", source_provenance_sha256=original_sha,
        source_preparation_sha256=bind_sha, prior_candidate_inventory_sha256=inventory_sha,
        manifest_sha256=source.manifest_sha256, tokenizer_sha256=exact.io.digest(exact.previous.fixture.TOKENIZER),
        source_rows=bind["mapped_rows"], inventory={name: dict(counts) for name, counts in inventory.items()},
        skipped=dict(skipped), candidates=len(candidates), teacher_calls=0, student_updates=0, admitted_rows=0,
        count_added_to_v5=0, source_sha256=exact.io.digest(Path(__file__))))
    print("SODA_SPEAKER_SWITCH", len(candidates), dict(inventory), dict(skipped), flush=True)


if __name__ == "__main__":
    main()
