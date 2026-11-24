"""Compile the existing 458 pairs with every correction view in the mixed phase."""

import json
from pathlib import Path
import shutil

import numpy as np
from tokenizers import Tokenizer

from scripts import build_p109c_authored_course as authored
from scripts import compile_p109c_course as compiler
from scripts import run_p109c_correction_scratch as baseline
from scripts import run_p109c_scratch330 as entry
from tinylm.data.prepare import verify_chat_tokenizer
from tinylm.train.mtp_sft import IGNORE


TAG = "p109c_authored_curriculum_correction_only_cpu_v1_20261121"
SOURCE = baseline.DATA
OUTPUT = SOURCE.parent / TAG


def verify(reference):
    path = entry.bundle_path(SOURCE, reference["file"])
    if entry.file_sha(path).upper() != reference["sha256"]:
        raise ValueError(f"saved authored input differs: {path}")
    return path


def keep_file(reference):
    source = verify(reference)
    shutil.copyfile(source, OUTPUT / source.name)
    return authored.reference(OUTPUT / source.name)


def main():
    if entry.file_sha(SOURCE / "report.json") != baseline.COURSE_SHA:
        raise ValueError("the original authored receipt changed")
    original = baseline.read_json(SOURCE / "report.json")
    old_manifest = verify(original["compiled"])
    old_spec = baseline.read_json(old_manifest)
    train = original["files"]["train"]
    plain = list(compiler.read_rows(verify(train["plain"])))
    pairs = {row["root"]: row for row in compiler.read_rows(verify(train["correction_pairs"]))}
    if len(pairs) != entry.STEPS - entry.BOUNDARY:
        raise ValueError("need one existing correction pair per mixed update")
    replaced, changed = [], []
    remaining = set(pairs)
    for index, row in enumerate(plain):
        root = row["root"]
        if root not in pairs:
            replaced.append(row)
            continue
        pair = pairs[root]
        if root not in remaining or pair[pair["selected"]] != row:
            raise ValueError("the saved pair does not match its original schedule position")
        other = pair["correction"]
        if other["root"] != root or other["record"]["meta"]["supervised_assistant_turns"] != [2]:
            raise ValueError("the correction row does not exclusively supervise the final answer")
        replaced.append(other)
        remaining.remove(root)
        if other != row:
            changed.append(index)
    if remaining or [row["root"] for row in replaced] != [row["root"] for row in plain]:
        raise ValueError("correction-only schedule lost or reordered a source")

    OUTPUT.mkdir(exist_ok=False)
    tokenizer = keep_file(original["tokenizer"])
    roots = keep_file(original["roots"])
    relation = keep_file(train["all_axes"])
    course = authored.write_rows(OUTPUT / "train_plain.jsonl", replaced)
    specification = dict(schema=compiler.SCHEMA, admission={"course": "LOCAL_AUTHORED_CORRECTION_ONLY_CANDIDATE"},
                         tokenizer=tokenizer, roots=roots,
                         plain=dict(course, slots=old_spec["course"]["plain"]["slots"]),
                         all_axes=dict(relation, slots=old_spec["course"]["all_axes"]["slots"], gold=train["gold"]))
    path = OUTPUT / "schedule.json"
    entry.publish(path, specification)
    manifest, compiled_sha = compiler.compile_schedule(path, authored.reference(path)["sha256"], "compiled")
    variant = baseline.read_json(manifest)
    for name in ("all_axes", "decimal"):
        previous = old_spec["course"][name]
        verify(previous)
        if previous != variant["course"][name]:
            raise ValueError(f"a separate curriculum family changed: {name}")
    first = np.load(verify(old_spec["course"]["plain"]), mmap_mode="r", allow_pickle=False)
    second = np.load(OUTPUT / variant["course"]["plain"]["file"], mmap_mode="r", allow_pickle=False)
    changed_mask = np.zeros(len(plain), dtype=np.bool_)
    changed_mask[changed] = True
    if first.shape != second.shape or not np.array_equal(first[~changed_mask], second[~changed_mask]):
        raise ValueError("an unrelated tokenized row or slot changed")
    for old, new in zip(first[:, 1], second[:, 1], strict=True):
        if not np.array_equal(old[old != IGNORE], new[new != IGNORE]):
            raise ValueError("a row changed its supervised target sequence")
    tok = Tokenizer.from_file(str(OUTPUT / tokenizer["file"]))
    pad = verify_chat_tokenizer(tok)["<pad>"]
    input_delta = int(np.count_nonzero(second[:, 0] != pad) - np.count_nonzero(first[:, 0] != pad))
    summary = dict(tag=TAG, original=baseline.COURSE_SHA, original_schedule=original["compiled"],
                   compiled=dict(file=manifest.name, sha256=compiled_sha), correction_pairs=len(pairs), changed=len(changed),
                   input_delta=input_delta, actual_input_ids=original["actual_input_ids"] + input_delta,
                   course_slots=original["course_slots"], supervised_nll_tokens=original["supervised_nll_tokens"],
                   source=authored.reference(Path(__file__)), relation_and_decimal_sha_equal=True,
                   target_ids_equal=True, schema=variant["schema"])
    entry.publish(OUTPUT / "report.json", summary)
    print(json.dumps(summary, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
