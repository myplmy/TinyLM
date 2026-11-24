"""Encode a sealed P109C course schedule for the native chat32 launcher."""

import argparse
import json
from pathlib import Path
import re

import numpy as np
from tokenizers import Tokenizer

from scripts import p106b_joint_decimal as joint
from scripts import p109_mix_masked_course as mixed
from scripts import run_p109c_scratch330 as entry
from tinylm.chat.canonical import normalize, validate
from tinylm.chat.serialize import serialize
from tinylm.data.prepare import verify_chat_tokenizer
from tinylm.train.mtp_sft import encode_record


SCHEMA = "P109C_COURSE_SCHEDULE_V1"


def read_rows(path):
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            yield json.loads(line)


def split_roots(splits):
    groups = [splits[name] for name in ("train", "validation", "test")]
    if any(not isinstance(group, list) or not group or
           any(not isinstance(root, str) or not root.strip() for root in group) for group in groups):
        raise ValueError("source roots must be approved string identifiers")
    train, val, test = map(set, groups)
    if train & val or train & test or val & test:
        raise ValueError("independent train, validation and test roots are required")
    return train


def decimal_label(record, encoded, operands, tokenizer, end_id):
    left, right = operands
    total, _, _, _ = joint.decimal_parts(left, right)
    messages = record["messages"]
    if len(messages) != 2 or [message["role"] for message in messages] != ["user", "assistant"]:
        raise ValueError("decimal supervision needs one exact addition dialogue")
    question = " ".join(block["text"] for block in messages[0]["content"] if block["type"] == "text")
    if [int(number) for number in re.findall(r"[0-9]+", question)] != [left, right]:
        raise ValueError("declared operands disagree with the actual question")
    if (re.search(r"[0-9]+\s*[+＋]\s*[0-9]+", question) is None
            and f"Add {right} more apples." not in question
            and f"사과 {right}개를 더 넣었습니다." not in question):
        raise ValueError("decimal supervision needs an admitted addition question")
    prompt = serialize(dict(messages=messages[:-1]), "chatml", add_generation_prompt=True)
    tokens = tokenizer.encode(prompt).ids
    position = len(tokens) - 1
    answer = [token for token in encoded.y[position:] if token != mixed.IGNORE]
    if (not 0 <= position < len(encoded.y) or encoded.x[:len(tokens)] != tokens
            or any(token != mixed.IGNORE for token in encoded.y[:position])
            or encoded.y[position] == mixed.IGNORE or len(answer) < 2 or answer[-1] != end_id
            or tokenizer.decode(answer[:-1], skip_special_tokens=False).strip() != str(total)):
        raise ValueError("decimal supervision needs the exact inference prompt and verified answer")
    return position, left, right


def encode_layout(source, output, expected, train_roots, tokenizer, pad, end_id, *, decimal=None):
    data = np.lib.format.open_memmap(output, mode="w+", dtype="<i4", shape=(expected, 2, entry.WIDTH))
    if decimal is not None:
        labels = np.lib.format.open_memmap(decimal, mode="w+", dtype="<i4", shape=(expected, 3))
        labels[:] = -1
    count = 0
    graph_root = None
    for item in read_rows(source):
        if count >= expected or item["root"] not in train_roots:
            raise ValueError("course row count or approved TRAIN root differs")
        if decimal is None:
            if count % 16 == 0:
                graph_root = item["root"]
            if item["root"] != graph_root or "operands" in item:
                raise ValueError("one source root and no decimal label per relation graph")
        record = validate(normalize(item["record"]))
        if record["meta"].get("view") == "correction" and (
                [message["role"] for message in record["messages"]] != ["user", "assistant", "user", "assistant"]
                or record["meta"].get("supervised_assistant_turns") != [2]):
            raise ValueError("a correction row must supervise only the final assistant reply")
        tokens = encode_record(record, tokenizer, context=entry.WIDTH)
        if end_id not in tokens.y:
            raise ValueError("serialized chat32 response needs a supervised end token")
        data[count, 0] = pad
        data[count, 1] = mixed.IGNORE
        data[count, 0, :len(tokens.x)] = tokens.x
        data[count, 1, :len(tokens.y)] = tokens.y
        if len(tokens.x) < entry.WIDTH and tokens.y[-1] != mixed.IGNORE:
            data[count, 0, len(tokens.x)] = tokens.y[-1]
        if decimal is not None and "operands" in item:
            labels[count] = decimal_label(record, tokens, item["operands"], tokenizer, end_id)
        count += 1
    if count != expected:
        raise ValueError("course needs all its explicitly scheduled rows")
    data.flush()
    if decimal is not None:
        labels.flush()


def compile_schedule(path, sha256, output_name):
    if re.fullmatch(r"[a-zA-Z0-9_-]+", output_name) is None:
        raise ValueError("a new local output directory name is required")
    stamps = {path: entry.file_stamp(path)}
    spec = json.loads(entry.manifest_bytes(path, sha256))
    if spec["schema"] != SCHEMA or not spec["admission"]["course"].strip():
        raise ValueError("an admitted P109C course schedule is required")

    def input_file(item):
        source = entry.bundle_path(path.parent, item["file"])
        stamps[source] = entry.file_stamp(source)
        if not source.is_file() or entry.file_sha(source).upper() != entry.digest(item["sha256"]):
            raise ValueError(f"admitted source digest differs: {source.name}")
        return source

    roots = split_roots(json.loads(input_file(spec["roots"]).read_bytes()))
    tok = Tokenizer.from_file(str(input_file(spec["tokenizer"])))
    reserved = verify_chat_tokenizer(tok, entry.VOCAB)
    end_id = reserved["<|im_end|>"]
    out = path.parent / output_name
    parts = {name: input_file(spec[name]) for name in ("plain", "all_axes")}
    slots = {name: tuple(spec[name]["slots"]) for name in parts}
    all_slots = slots["plain"] + slots["all_axes"]
    if (not all(slots.values()) or any(type(slot) is not int or not 0 <= slot < entry.ACCUM for slot in all_slots)
            or len(all_slots) != len(set(all_slots)) or len(all_slots) >= entry.ACCUM
            or len(slots["all_axes"]) % 4 or any(tuple(sorted(item)) != item for item in slots.values())):
        raise ValueError("ordered nonoverlapping course slots with original NTP remaining are required")
    out.mkdir(exist_ok=False)

    def reference(file):
        return dict(file=str(file.relative_to(path.parent)), sha256=entry.file_sha(file).upper())

    course = dict(tokenizer_sha256=entry.digest(spec["tokenizer"]["sha256"]))
    labels = out / "decimal.npy"
    for name, source in parts.items():
        output = out / f"{name}.npy"
        rows = (entry.STEPS - entry.BOUNDARY) * len(slots[name]) * entry.MICRO
        encode_layout(source, output, rows, roots, tok, reserved["<pad>"], end_id,
                      decimal=labels if name == "plain" else None)
        course[name] = dict(reference(output), slots=slots[name])
    course["all_axes"]["gold"] = spec["all_axes"]["gold"]
    course["decimal"] = reference(labels)
    layouts = {name: mixed.Course(entry.BOUNDARY, slots[name], mixed.MappedRows(
        path.parent / course[name]["file"], course[name]["sha256"]), entry.VOCAB) for name in parts}
    mixed.AllAxesCourse(layouts["all_axes"], end_id, tuple(course["all_axes"]["gold"]))
    mixed.DecimalLabels.load(labels, course["decimal"]["sha256"], layouts["plain"], tok, end_id)
    if any(source.resolve(strict=True) != source or entry.file_stamp(source) != stamp for source, stamp in stamps.items()):
        raise ValueError("an input changed while compiling the course")

    compiled = dict(schema=entry.SCHEMA if "cache" in spec else "P109C_COMPILED_COURSE_V1",
                    source_release=entry.RELEASE,
                    admission=spec["admission"], tokenizer=spec["tokenizer"], course=course,
                    course_schedule_sha256=entry.digest(sha256))
    if "cache" in spec:
        compiled["cache"] = spec["cache"]
    manifest = path.parent / f"{output_name}_manifest.json"
    entry.publish(manifest, compiled)
    return manifest, entry.file_sha(manifest).upper()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--schedule", required=True, type=Path)
    parser.add_argument("--schedule-sha256", required=True)
    parser.add_argument("--output-name", required=True)
    args = parser.parse_args()
    path, sha256 = compile_schedule(args.schedule.absolute(), args.schedule_sha256, args.output_name)
    print(json.dumps(dict(manifest=str(path), sha256=sha256)))


if __name__ == "__main__":
    main()
