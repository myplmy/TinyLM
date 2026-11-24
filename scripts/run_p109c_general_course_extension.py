"""Add the sealed general-response rows to the existing P109C padding slots."""

import argparse
from collections import defaultdict
from datetime import datetime
from functools import partial
import json
from pathlib import Path
from unittest.mock import patch

import numpy as np

from scripts import run_p109c_scratch_mixed as mixed


prep, native = mixed.prep, mixed.native
SOURCE = prep.ROOT / "data_cache/p106b_broad_curriculum_v2_s1337/wire/train_shards_manifest.json"
STATUS = "SAME_SLOT_GENERAL_256_LAYOUT_STATIC_ONLY"
TAG = "p109c_scratch_general256_v11_chat32_s1337"
PROBE_TAG = "p109c_probe_general256_v11_chat32_s1337"


class LaneWithExtension:
    """Expose read-only copies of the few batches containing inserted examples."""

    def __init__(self, base, replacements):
        self.base = base
        self.replacements = replacements

    def __getitem__(self, index):
        if index in self.replacements:
            return self.replacements[index]
        return self.base[index]


def sources(layout):
    expected = {item["source_id"]: item for item in layout["positions"]}
    if len(expected) != len(layout["positions"]) or prep.sha(SOURCE) != layout["wire_sha256"]:
        raise ValueError("the source records or their frozen manifest differ")
    blocked = prep.set_forbidden_questions()
    pins = {}
    results = {}
    for record in prep.verified_rows(SOURCE, pins):
        meta = record["meta"]
        source_id = meta["id"]
        if source_id not in expected:
            continue
        proof = expected[source_id]
        x, y = (np.asarray(record[key], dtype=prep.DTYPE) for key in ("x", "y"))
        supervised = y != prep.IGNORE
        first = np.flatnonzero(supervised & ~np.r_[False, supervised[:-1]])
        last = np.flatnonzero(supervised & ~np.r_[supervised[1:], False])
        if (source_id in results or meta["lane"] != "general" or meta["language"] != proof["language"]
                or meta["first_user_sha256"].lower() in blocked or meta["record_sha256"] != proof["row_sha256"]
                or meta["source"]["source"] != proof["source_label"]
                or prep.record_checks(x, y) != "first_use_context_or_answer_budget"
                or first[-1]+1 > 896 or (last-first+1).max() > 256
                or x.size != proof["stop"]-proof["start"] or int(supervised.sum()) != proof["targets"]):
            raise ValueError("an additional long response no longer meets its exact entry conditions")
        results[source_id] = (x, y)
    if results.keys() != expected.keys():
        raise ValueError("some additions are missing from the exact original source")
    return results, pins


def attach(bundle, layout_path, layout_sha):
    layout = json.loads(native.manifest_bytes(layout_path, layout_sha))
    if (layout["status"] != STATUS or layout["old_manifest_sha256"] != bundle.digest
            or layout["old_schedule_sha256"] != bundle.manifest["schedule_sha256"]
            or layout["absolute_optimizer_updates"] != bundle.steps
            or layout["physical_slots"] != bundle.steps * prep.ACCUM * mixed.MICRO_TOKENS
            or layout["raw_tokens"] != prep.RAW_TOKENS):
        raise ValueError("the extension must use the original agenda, raw windows and physical slots")
    rows, pins = sources(layout)
    replacements = defaultdict(dict)
    added_inputs = added_targets = 0
    for proof in layout["positions"]:
        lane, position = bundle.schedule[proof["update"]-1, proof["micro_slot"]]
        if lane < 0:
            raise ValueError("the new general response must use an existing curriculum batch")
        name = bundle.manifest["lanes"][lane]["name"]
        patching = replacements[lane]
        if position not in patching:
            patching[position] = bundle.data[lane][position].copy()
        slot = patching[position][proof["batch_row"]]
        tokens, labels, segments = slot
        start, stop = proof["start"], proof["stop"]
        if (bundle.aux[lane][position]["gold"] >= 0 or name != proof["lane"]
                or not name.endswith(f"_{proof['language']}_plain") or position != proof["lane_micro"]
                or not 0 <= start < stop <= prep.WIDTH or np.count_nonzero(segments) != start
                or np.any(segments[start:]) or np.any(labels[start:] != prep.IGNORE)
                or np.any(tokens[start:]) or proof["segment"] != int(segments.max())+1):
            raise ValueError("a new segment would cross an existing example or leave its scheduled batch")
        x, y = rows[proof["source_id"]]
        tokens[start:stop], labels[start:stop], segments[start:stop] = x, y, proof["segment"]
        added_inputs += x.size
        added_targets += proof["targets"]
    if (len(rows) != layout["source_record_rows"] or added_inputs != layout["additional_course_input_tokens"]
            or added_targets != layout["additional_course_supervised_positions"]):
        raise ValueError("the packed extension exposure is incomplete")
    for lane, new in replacements.items():
        source = bundle.data[lane]
        for index, packed in new.items():
            original = source[index]
            selected = np.broadcast_to(original[:, 2:3, :] != 0, original.shape)
            if not np.array_equal(packed[selected], original[selected]):
                raise ValueError("an unchanged input or supervisor target was modified")
            packed.flags.writeable = False
        bundle.data[lane] = LaneWithExtension(source, new)
    course_tokens = bundle.manifest["course_tokens"] + added_inputs
    target_tokens = sum(items.get("answer_targets", 0) for items in bundle.manifest["counts"].values()) + added_targets
    bundle.manifest = dict(bundle.manifest, course_tokens=course_tokens)
    bundle.stamps[layout_path] = native.file_stamp(layout_path)
    for relative, expected in pins.items():
        part = prep.ROOT / relative
        if prep.sha(part) != expected:
            raise ValueError("the archived source changed during validation")
        bundle.stamps[part] = native.file_stamp(part)
    return dict(layout_sha256=layout_sha, added_inputs=added_inputs, added_targets=added_targets,
                added_rows=len(rows), source_wire_sha256=layout["wire_sha256"],
                packed_micros=sum(len(new) for new in replacements.values()),
                first_new_update=min(item["update"] for item in layout["positions"]),
                source_sha256=prep.sha(Path(__file__)), base_source_sha256=prep.sha(Path(mixed.__file__)),
                expected_course_tokens=course_tokens, expected_answer_and_end_targets=target_tokens)


def worker(layout, layout_sha, source_sha, base_sha, probe, manifest, manifest_sha, _resume, record, cutoff):
    if prep.sha(Path(__file__)) != source_sha or prep.sha(Path(mixed.__file__)) != base_sha:
        raise ValueError("the sealed extension code changed")
    factory, bind, original_probe = mixed.Bundle, mixed.context_training_state.make_binding, mixed.probe_updates

    def build(path, expected):
        bundle = factory(path, expected)
        proof = attach(bundle, layout, layout_sha)
        native.publish(record / "extension.json", proof)
        return bundle

    def binding(plan, recipe, cache, device):
        return bind(plan, dict(recipe, p109c_general_course_layout_sha256=layout_sha), cache, device)

    def select(bundle):
        period = prep.read_json(record / "extension.json")["first_new_update"] - 1
        return tuple(sorted({*original_probe(bundle), period}))

    with (patch.object(mixed, "Bundle", build),
          patch.object(mixed.context_training_state, "make_binding", binding),
          patch.object(mixed, "probe_updates", select),
          patch.object(mixed, "TAG", TAG), patch.object(mixed, "PROBE_TAG", PROBE_TAG)):
        mixed.worker(True, .25, .02, None, probe, base_sha,
                     manifest, manifest_sha, False, record, cutoff)
    extension = prep.read_json(record / "extension.json")
    if probe:
        exposure = prep.read_json(record / "report.json")["exposure"]
        if extension["first_new_update"] - 1 not in {row["source_update"] for row in exposure}:
            raise ValueError("the probe did not exercise the added first mixed update")
    else:
        exposure = prep.read_json(record / "training.json")["exposure"]
        targets = sum(sum(row[key] for key in ("answer_start_targets", "answer_body_targets", "answer_eot_targets"))
                      for row in exposure)
        if (sum(row["course_tokens"] for row in exposure) != extension["expected_course_tokens"]
                or targets != extension["expected_answer_and_end_targets"]):
            raise ValueError("the native trainer consumed different course or answer totals than the sealed extension")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("check", "probe", "run"))
    for key in ("manifest", "record"):
        parser.add_argument("--" + key, required=True, type=Path)
    parser.add_argument("--layout", required=True, type=Path)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--layout-sha256", required=True)
    parser.add_argument("--source-sha256")
    parser.add_argument("--base-source-sha256")
    parser.add_argument("--stop-by", type=datetime.fromisoformat)
    args = parser.parse_args()
    manifest, layout, record = (path.absolute() for path in (args.manifest, args.layout, args.record))
    checksum, layout_sha = map(native.digest, (args.manifest_sha256, args.layout_sha256))
    if record.exists() or record.is_symlink():
        parser.error("a fresh output directory is required")
    if args.mode == "check":
        bundle = mixed.Bundle(manifest, checksum)
        proof = attach(bundle, layout, layout_sha)
        bundle.unchanged()
        record.mkdir(exist_ok=False)
        native.publish(record / "report.json", dict(status="MIXED_EXTENSION_INPUT_VERIFIED", **proof))
        print(proof, flush=True)
        return 0
    if args.stop_by is None or args.stop_by.tzinfo is None or not (args.source_sha256 and args.base_source_sha256):
        parser.error("the GPU run requires a sealed source and an authorized cutoff")
    source_sha, base_sha = map(native.digest, (args.source_sha256, args.base_source_sha256))
    task = partial(worker, layout, layout_sha, source_sha, base_sha, args.mode == "probe")
    with (patch.object(native, "gpu_worker", task),
          patch.object(native, "gpu_status", partial(mixed.telemetry.gpu_status, record))):
        return native.supervise(manifest, checksum, False, record, args.stop_by)


if __name__ == "__main__":
    raise SystemExit(main())
