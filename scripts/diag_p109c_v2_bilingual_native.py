"""Verify exactly v2 plus bilingual pairs through the native P109C trainer."""

import argparse
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime
from hashlib import sha256
import json
import os
from pathlib import Path
import time

import numpy as np

from scripts import p109_eval_resilient_supervisor as supervisor
from scripts import run_p109c_bilingual_mixed as reference


prep, mixed, native = reference.prep, reference.mixed, reference.native
placement, training = reference.placement, reference.training
TAG = "p109c_v2_bilingual_native_chat32_probe_v1_20261124"
AUTHORIZATION_END = datetime.fromisoformat("2026-11-25T17:00:00+09:00")
MANIFEST = prep.ROOT / "data_cache/p109c_mixed_v2_v11_course_20261122_v1/manifest.json"
LAYOUT = prep.ROOT / "data_cache/p109c_v2_bilingual_mixed_update_layout_20261123/layout.json"
V2_ONLY_AUDIT = prep.ROOT / "handoff/audit/P109C_V2_BILINGUAL_ONLY_ASSEMBLY_20261124.json"


def sources():
    pins = reference.sources()
    paths = (Path(__file__).resolve(), Path(supervisor.__file__).resolve(), Path(mixed.trainer.__file__).resolve())
    pins.update({str(p.relative_to(prep.ROOT)): prep.sha(p) for p in paths})
    return pins


def attach(bundle, layout, expected_layout):
    """Rebuild only the additions to the original v2 schedule and verify every slot."""
    profile = json.loads(native.manifest_bytes(layout, expected_layout))
    placements = profile["placements"]
    if (profile["status"] != "BILINGUAL_UPDATE_PLACEMENT_SEALED"
            or profile["input_manifest_sha256"] != bundle.digest
            or prep.sha(placement.PAIR_SOURCE) != profile["pair_archive_sha256"]
            or prep.sha(placement.PAIR_AUDIT) != profile["admission_audit_sha256"]
            or profile["updates"] != bundle.steps
            or len(placements) != profile["packed_updates"] or len(placements) != bundle.steps - bundle.warmup
            or profile["physical_slots"] != bundle.steps * prep.ACCUM * mixed.MICRO_TOKENS):
        raise ValueError("the sealed v2 and bilingual slot plans disagree")
    with np.load(placement.PAIR_SOURCE, allow_pickle=False) as archive:
        tokens, labels = archive["tokens"], archive["labels"]
    widths = np.where((tokens != 0) | (labels != prep.IGNORE), np.arange(tokens.shape[1]) + 1, 0).max(1)
    if tokens.shape != labels.shape or len(tokens) != 2 * placement.COUNT or not np.all((labels == prep.END).sum(1) == 1):
        raise ValueError("the approved bilingual examples require their original labels and one end token")

    data = np.zeros((2, len(placements), *mixed.PACK_SHAPE), dtype=prep.DTYPE)
    data[:, :, :, 1, :] = prep.IGNORE
    order = np.array(bundle.schedule)
    metadata, pair_meta, consumed = [], [], set()
    relation_lane = len(bundle.data)
    for index, block in enumerate(placements):
        step = bundle.warmup + index
        original = bundle.schedule[step]
        anchor, pair_slot = block["relation_anchor"], block["new_bilingual_slot"]
        released = block["relation_slots_to_merge"]
        originals = [s for s, (lane, row) in enumerate(original) if lane >= 0 and bundle.aux[lane][row]["gold"] >= 0]
        if (block["update"] != step + 1 or not released or pair_slot != released[0]
                or originals != [anchor, *released]):
            raise ValueError("placement must leave each v2 relation within its original update")
        metadata.append(reference.packed_relation(bundle, original, originals, data[0, index]))
        pair_meta.append(reference.packed_pairs(data[1, index], block, tokens, labels, widths, consumed))
        order[step, released] = (-2, 0)
        order[step, anchor], order[step, pair_slot] = (relation_lane, index), (relation_lane+1, index)
    if (consumed != set(range(placement.COUNT))
            or not np.array_equal(bundle.schedule[:, :, 0] == -1, order[:, :, 0] == -1)
            or not np.array_equal(bundle.schedule[bundle.schedule[:, :, 0] == -1], order[order[:, :, 0] == -1])):
        raise ValueError("a raw slot or bilingual pair has changed")

    pair_tokens = int(np.count_nonzero(data[1, :, :, 2, :]))
    if pair_tokens != int(widths.sum()):
        raise ValueError("bilingual input count differs from its uncompressed source")
    before = bundle.manifest["course_tokens"]
    course_tokens = before + pair_tokens
    bundle.schedule = order
    order.flags.writeable = data.flags.writeable = False
    bundle.data.extend(data)
    bundle.aux.extend((metadata, pair_meta))
    bundle.packed_hidden = reference.relative.relative_hidden
    bundle.manifest = dict(bundle.manifest, course_tokens=course_tokens)
    for file in (layout, placement.PAIR_SOURCE, placement.PAIR_AUDIT):
        bundle.stamps[file] = native.file_stamp(file)

    kind_totals = np.zeros(4, dtype=np.int64)
    input_tokens = relations = decimal = 0
    for lane, slot in order.reshape(-1, 2):
        if lane < 0:
            continue
        _, target, segment = bundle.data[lane][slot].transpose(1, 0, 2)
        aux = bundle.aux[lane][slot]
        kinds = mixed.label_kinds(target, segment)
        groups = reference.relation_objective.relation_groups_for(aux, prep.BATCH)
        reference.relation_objective.keep_relation_winners(kinds, segment, groups)
        kind_totals += np.bincount(kinds.ravel(), minlength=4)
        input_tokens += np.count_nonzero(segment)
        relations += len(groups)
        decimal += len(aux["decimal"])
    expected = prep.read_json(V2_ONLY_AUDIT)
    digest = sha256(order.tobytes()).hexdigest().upper()
    raw = int(np.count_nonzero(order[:, :, 0] == -1)) * mixed.MICRO_TOKENS
    if (expected["status"] != "V2_AND_BILINGUAL_SCHEDULE_CPU_VERIFIED"
            or expected["manifest_sha256"] != bundle.digest or expected["inherited_layout_sha256"] != expected_layout
            or expected["original_v2_course_tokens"] != before or expected["approved_bilingual_course_tokens"] != pair_tokens
            or expected["nonpadding_course_tokens"] != course_tokens or input_tokens != course_tokens
            or expected["derived_schedule_sha256"] != digest or expected["targets"] != dict(
                raw=raw, answer_start=int(kind_totals[1]), answer_body=int(kind_totals[2]), answer_end=int(kind_totals[3]))
            or expected["packed_relations"] != relations or expected["decimal_auxiliary_sites"] != decimal):
        raise ValueError("the native bundle differs from the earlier independent v2-only audit")
    bundle.unchanged()
    return dict(layout_sha256=expected_layout, manifest_sha256=bundle.digest, steps=bundle.steps,
                raw_tokens=raw, original_course_tokens=before, bilingual_tokens=pair_tokens,
                bilingual_pairs=len(consumed), course_tokens=course_tokens, combined_tokens=raw+course_tokens,
                relations=int(relations), decimal_sites=int(decimal), answer_targets=int(kind_totals[1:].sum()),
                empty_slots=int(np.count_nonzero(order[:, :, 0] == -2)), derived_schedule_sha256=digest)


def load_inputs():
    original = prep.read_json(V2_ONLY_AUDIT)
    bundle = mixed.Bundle(MANIFEST, original["manifest_sha256"])
    inputs = attach(bundle, LAYOUT, original["inherited_layout_sha256"])
    return bundle, inputs


def selection(bundle):
    # Includes a raw-only update, first mixed input, an empty slot and a later bilingual input.
    return (0, bundle.warmup, 152, 156)


def worker(profile, checksum, _resume, record, cutoff):
    import torch

    with (training.locked_record(record), (record / "stdout.txt").open("x", encoding="utf-8", buffering=1) as log,
          redirect_stdout(log), redirect_stderr(log)):
        sealed = json.loads(native.manifest_bytes(profile, checksum))
        pins = sources()
        if (sealed["sources"] != pins or torch.cuda.device_count() != 1 or time.time() >= cutoff
                or sealed["tag"] != TAG or sealed["cpu_audit_sha256"] != prep.sha(V2_ONLY_AUDIT)):
            raise ValueError("the GPU probe requires its original sealed source and approval interval")
        bundle, inputs = load_inputs()
        addresses = selection(bundle)
        if sealed["inputs"] != inputs or sealed["selected_source_updates"] != [i+1 for i in addresses]:
            raise ValueError("the rebuilt native input differs from the admitted probe")
        free, total = torch.cuda.mem_get_info()
        budget = (native.CARD_LIMIT_MIB - 384) * 2**20 - (total - free)
        if not 0 < budget <= total:
            raise ValueError("no CUDA allocation budget for the admitted probe")
        torch.cuda.set_per_process_memory_fraction(budget / total)
        native.publish(record / "extension.json", inputs)
        training.run(bundle, record, cutoff, TAG, pins, inputs["layout_sha256"], proof=inputs, probe_updates=addresses)
        if pins != sources():
            raise ValueError("a training source changed during the probe")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "probe"))
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--profile-sha256")
    parser.add_argument("--stop-by", type=datetime.fromisoformat)
    args = parser.parse_args()
    if args.action == "prepare":
        bundle, inputs = load_inputs()
        native.publish(args.profile, dict(tag=TAG, sources=sources(), cpu_audit_sha256=prep.sha(V2_ONLY_AUDIT),
            inputs=inputs, selected_source_updates=[i+1 for i in selection(bundle)]))
        print(prep.sha(args.profile), inputs, flush=True)
        return 0
    if (args.profile_sha256 is None or args.stop_by is None or args.stop_by.tzinfo is None
            or args.stop_by > AUTHORIZATION_END or os.environ.get("CUDA_VISIBLE_DEVICES") != "0"):
        parser.error("the exact profile, future approved cutoff and device 0 are required")
    return supervisor.supervise(worker, args.profile, args.profile_sha256, prep.EVIDENCE / TAG, args.stop_by)


if __name__ == "__main__":
    raise SystemExit(main())
