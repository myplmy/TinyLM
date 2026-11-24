"""Count verified quote QA in the local SODA release with exact split deduplication."""

import argparse
from collections import Counter
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path
import time

from scripts import diag_p106b_soda_speaker_switch as quote
from scripts import eval_p109c_completed as native
from scripts import p106b_soda_original_lineage as source
from tinylm.train.mtp_sft import encode_record


def turns(row):
    roles, utterances = row["speakers"], row["dialogue"]
    if not isinstance(roles, list) or not isinstance(utterances, list) or len(roles) != len(utterances) or len(roles) < 2:
        return None
    normalized = [(source.text_key(role), source.text_key(text)) for role, text in zip(roles, utterances, strict=True)]
    if any(not role or not text or ": " in role or "\n" in role or "\n" in text or "\r" in text for role, text in normalized):
        return None
    return normalized


def spoken_key(turn_rows):
    return sha256(json.dumps([quote.quote_key(text) for _, text in turn_rows], ensure_ascii=False,
                             separators=(",", ":")).encode("utf-8")).digest()


def released_groups(directory, check):
    roots, utterances = set(), set()
    counts = Counter()
    for split in ("valid", "test"):
        count, checksum = source.RELEASE[split]
        with source.pinned_rows(directory / f"{split}.parquet", count, checksum) as rows:
            for index, row in enumerate(rows):
                if index % 8192 == 0:
                    check()
                if row["split"] != split:
                    raise ValueError("a held-out row declares a different partition")
                counts[split] += 1
                roots.add(row["original_index"])
                raw = turns(row)
                if raw:
                    utterances.add(spoken_key(raw))
    return roots, utterances, counts


def audit(directory, cutoff, *, on_accepted=None):
    def check():
        if time.time() >= cutoff:
            raise TimeoutError("the official local release audit reached its cutoff")

    tokenizer = native.load_tokenizer()
    eot = tokenizer.token_to_id("<|im_end|>")
    held_roots, held_content, rows_seen = released_groups(directory, check)
    prior, prior_sha = quote.read(quote.SOURCE_MAP)
    if prior["revision"] != source.REVISION:
        raise ValueError("the existing source mapping is from another release")
    covered = {row["original_index"] for row in prior["rows"] if row["status"] == "EXACT_TRAIN_LINK"}
    used_roots, used_content = set(), set()
    rejects, accepted, turn_gaps = Counter(), Counter(), Counter()
    groups = sha256()
    count, checksum = source.RELEASE["train"]
    with source.pinned_rows(directory / "train.parquet", count, checksum) as rows:
        for index, row in enumerate(rows):
            if index % 8192 == 0:
                check()
            if index % 131072 == 0:
                print("SODA_QUOTE_RELEASE", index, dict(accepted), flush=True)
            if row["split"] != "train":
                raise ValueError("a training row declares a different partition")
            rows_seen["train"] += 1
            root = row["original_index"]
            raw = turns(row)
            if type(root) is not int or root < 0 or raw is None:
                rejects["invalid_root_or_dialogue"] += 1
                continue
            key = spoken_key(raw)
            if root in held_roots or key in held_content:
                rejects["heldout_root_or_utterances"] += 1
                continue
            if root in covered:
                rejects["already_linked_train_root"] += 1
                continue
            if root in used_roots or key in used_content:
                rejects["repeated_candidate_root_or_utterances"] += 1
                continue
            dialogue = "\n\n".join(f"{role}: {text}" for role, text in raw)
            selected = quote.questions(dialogue)
            if selected is None:
                rejects["no_distinct_unambiguous_quotes"] += 1
                continue
            group = source.hash_json([source.REPO, source.REVISION, root])
            binding = dict(source_group_id=group, original_index=root, aya_id=None)
            record = quote.format_record(dialogue, selected, binding, source.hash_json(row))
            try:
                encoded = encode_record(record, tokenizer, context=quote.CONTEXT)
            except ValueError as error:
                if "context" not in str(error).casefold():
                    raise
                rejects["over_context"] += 1
                continue
            expected = record["meta"]["target_labels"]
            for turn, name in enumerate(expected, 1):
                labels = [token for token, owner in zip(encoded.y, encoded.segments, strict=True) if owner == turn]
                if not labels or labels[-1] != eot or tokenizer.decode(labels[:-1]).strip() != name:
                    raise ValueError("a verified source answer changed in the real training encoder")
            if any((owner == 0) != (label == quote.IGNORE)
                   for owner, label in zip(encoded.segments, encoded.y, strict=True)):
                raise ValueError("a non-assistant position received supervision")
            used_roots.add(root)
            used_content.add(key)
            groups.update(bytes.fromhex(group))
            if on_accepted is not None:
                on_accepted(index)
            delta = dict(rows=1, input_tokens=encoded.x_tokens, answer_and_end_targets=encoded.targets)
            accepted.update(delta)
            turn_gaps[abs(selected[0][0]-selected[1][0])] += 1
    if (dict(rows_seen) != {name: count for name, (count, _) in source.RELEASE.items()}
            or sum(rejects.values()) + accepted["rows"] != count
            or len(used_roots) != len(used_content) or len(used_roots) != accepted["rows"]):
        raise ValueError("the accepted and skipped rows do not close the official full release")
    return dict(status="FULL_EXACT_RELEASE_AUDIT", revision=source.REVISION, official_files=source.RELEASE,
                scanned=rows_seen, accepted=accepted, rejected=rejects, excluded_existing_roots=len(covered),
                existing_join_sha256=prior_sha, accepted_ordered_groups_sha256=groups.hexdigest().upper(),
                quote_distance_by_turn=turn_gaps, task_templates=1, cpu_only=True,
                cross_split_key="official index or exact NFC, case and whitespace folded utterance sequence without speaker names",
                teacher_calls=0, student_updates=0, training_rows_published=0,
                tokenizer_sha256=native.TOKENIZER_SHA)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original-dir", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--stop-by", required=True, type=datetime.fromisoformat)
    args = parser.parse_args()
    if args.stop_by.tzinfo is None or args.report.exists():
        parser.error("the audit requires a fresh report and a timezone-aware cutoff")
    started = time.monotonic()
    result = audit(args.original_dir, args.stop_by.timestamp())
    native.training.publish(args.report, dict(result, seconds=time.monotonic()-started))
    print(result["status"], dict(result["accepted"]), dict(result["rejected"]), flush=True)


if __name__ == "__main__":
    main()
