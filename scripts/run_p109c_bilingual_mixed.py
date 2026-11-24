"""Replay the exact P109C general and bilingual placement in the existing mixed trainer."""

import argparse
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime
from functools import partial
from hashlib import sha256
import json
import os
from pathlib import Path
import time
from unittest.mock import patch

import numpy as np
import torch
from torch.nn.attention import SDPBackend, sdpa_kernel

from scripts import diag_p109c_relation_pack_segment_rope_flash as relative
from scripts import diag_p109c_same_update_relation_pack_cpu as relation
from scripts import p109c_bilingual_training as training
from scripts import p109c_packed_relation_objective as relation_objective
from scripts import prepare_p109c_bilingual_mix_layout as placement
from scripts import run_p109c_general_course_extension as general


mixed, prep, native = placement.mixed, placement.prep, placement.native
GENERAL = prep.ROOT / "handoff/audit/P109C_V2_GENERAL_256_FIXED_SLOT_LAYOUT_20261123.json"
TAG = "p109c_scratch_bilingual_general_v11_chat32_s1337"
PROBE_TAG = "p109c_probe_bilingual_general_v11_chat32_s1337"
CPU_TAG = "p109c_probe_bilingual_general_cpu_v11_chat32_s1337"


def sources():
    paths = [Path(__file__).resolve()] + [Path(module.__file__).resolve() for module in
            (training, relation_objective, mixed, general, relative, relation, placement, native,
             training.packed_document_training)]
    return {str(path.relative_to(prep.ROOT)): prep.sha(path) for path in paths}


def packed_relation(bundle, original, positions, target):
    rows, winners = [], []
    for slot in positions:
        lane, index = map(int, original[slot])
        if lane < 0:
            raise ValueError("a relation replacement must consume an admitted course batch")
        item = bundle.aux[lane][index]
        gold = item["gold"]
        if gold < 0 or item["decimal"]:
            raise ValueError("the grouped relation batch must preserve its four-choice group and have no decimal supervision")
        x, y, segments = bundle.data[lane][index].transpose(1, 0, 2)
        rows.append((x, y, segments, None, gold, ()))
        winners.append(gold)
    x, y, segments = relation.pack(rows)
    target[:, 0, :x.shape[1]] = x
    target[:, 1, :y.shape[1]] = y
    target[:, 2, :segments.shape[1]] = segments
    groups = tuple(enumerate(winners, 1))
    positive = 0
    for group, gold in groups:
        source_x, source_y, source_segments, _, _, _ = rows[group-1]
        for row, before_x, before_y, before_segment in zip(target, source_x, source_y, source_segments, strict=True):
            selected, expected = row[2] == group, before_segment != 0
            if (not np.array_equal(row[0][selected], before_x[expected])
                    or not np.array_equal(row[1][selected], before_y[expected])):
                raise ValueError("a relation input or supervised answer changed during packing")
        positive += np.count_nonzero(source_y[gold] != prep.IGNORE)
    kinds = mixed.label_kinds(target[:, 1, :], target[:, 2, :])
    relation_objective.keep_relation_winners(kinds, target[:, 2, :], groups)
    if np.count_nonzero(kinds) != positive:
        raise ValueError("the packed answer masks must supervise only the original relation winners")
    return dict(gold=-1, decimal=(), relation_groups=groups)


def packed_pairs(target, block, x, y, lengths, consumed):
    for segment, (pair, row, ko_offset, en_offset) in enumerate(block["pairs"], 1):
        if pair in consumed or row not in (0, 2):
            raise ValueError("a sealed pair was reused or its two languages left their assigned adjacent rows")
        consumed.add(pair)
        for language, start in enumerate((ko_offset, en_offset)):
            index = pair * 2 + language
            end = start + int(lengths[index])
            tokens, labels, segments = target[row + language]
            if not 0 <= start < end <= prep.WIDTH or int(np.count_nonzero(segments)) != start:
                raise ValueError("a new bilingual example would overlap an existing segment or leave its row")
            tokens[start:end], labels[start:end], segments[start:end] = (
                x[index, :end-start], y[index, :end-start], segment)
    if tuple(np.count_nonzero(target[:, 2, :], axis=1)) != tuple(block["row_widths"]):
        raise ValueError("the exact bilingual row widths differ from the sealed schedule")
    return dict(gold=-1, decimal=())


def attach(bundle, layout_path, layout_sha):
    profile = json.loads(native.manifest_bytes(layout_path, layout_sha))
    if (profile["status"] != "BILINGUAL_UPDATE_PLACEMENT_SEALED" or profile["input_manifest_sha256"] != bundle.digest
            or prep.sha(placement.PAIR_SOURCE) != profile["pair_archive_sha256"]
            or prep.sha(placement.PAIR_AUDIT) != profile["admission_audit_sha256"]
            or profile["updates"] != bundle.steps or profile["packed_updates"] != bundle.steps - bundle.warmup
            or profile["physical_slots"] != bundle.steps * prep.ACCUM * mixed.MICRO_TOKENS):
        raise ValueError("the sealed general, bilingual and raw training contracts must agree")
    extension = general.attach(bundle, GENERAL, profile["general_layout_sha256"])
    with np.load(placement.PAIR_SOURCE, allow_pickle=False) as archive:
        x, y = archive["tokens"], archive["labels"]
    lengths = np.where((x != 0) | (y != prep.IGNORE), np.arange(x.shape[1]) + 1, 0).max(axis=1)
    if len(x) != 2 * placement.COUNT or not np.all((y == prep.END).sum(axis=1) == 1):
        raise ValueError("a bilingual response must still have its exact source and answer termination")

    count = profile["packed_updates"]
    data = np.zeros((2, count, *mixed.PACK_SHAPE), dtype=prep.DTYPE)
    data[:, :, :, 1, :] = prep.IGNORE
    order = np.array(bundle.schedule)
    relation_lane, pairs_lane = len(bundle.data), len(bundle.data) + 1
    metadata, pair_metadata, consumed = [], [], set()
    protected_raw = order[order[:, :, 0] == -1].copy()
    for index, block in enumerate(profile["placements"]):
        step = block["update"] - 1
        anchor, pairs = block["relation_anchor"], block["new_bilingual_slot"]
        replaced = block["relation_slots_to_merge"]
        if (step != bundle.warmup + index or not replaced or pairs != replaced[0]
                or len(set(replaced)) != len(replaced) or anchor in replaced):
            raise ValueError("the packed source schedule lost its absolute update or uniquely released slot")
        original = order[step].copy()
        expected_relation = [i for i, (lane, row) in enumerate(original)
                             if lane >= 0 and bundle.aux[lane][row]["gold"] >= 0]
        if expected_relation != [anchor, *replaced]:
            raise ValueError("every original relation group must remain in its own optimizer update")
        metadata.append(packed_relation(bundle, original, expected_relation, data[0, index]))
        pair_metadata.append(packed_pairs(data[1, index], block, x, y, lengths, consumed))
        order[step, replaced] = (-2, 0)
        order[step, anchor], order[step, pairs] = (relation_lane, index), (pairs_lane, index)
    if (consumed != set(range(placement.COUNT)) or not np.array_equal(protected_raw, order[order[:, :, 0] == -1])
            or not np.array_equal(bundle.schedule[:, :, 0] == -1, order[:, :, 0] == -1)):
        raise ValueError("a bilingual pair, raw index or raw position was lost")
    pair_tokens = int(np.count_nonzero(data[1, :, :, 2, :]))
    pair_targets = int(np.count_nonzero(data[1, :, :, 1, :] != prep.IGNORE))
    combined = prep.RAW_TOKENS + extension["expected_course_tokens"] + pair_tokens
    if combined != profile["combined_input_tokens"] or pair_tokens != int(lengths.sum()):
        raise ValueError("the packed token count differs from the independently prepared total")
    bundle.schedule = order
    order.flags.writeable = data.flags.writeable = False
    bundle.data.extend(data)
    bundle.aux.extend((metadata, pair_metadata))
    bundle.packed_hidden = relative.relative_hidden
    bundle.manifest = dict(bundle.manifest, course_tokens=combined-prep.RAW_TOKENS)
    for file in (layout_path, placement.PAIR_SOURCE, placement.PAIR_AUDIT):
        bundle.stamps[file] = native.file_stamp(file)
    bundle.unchanged()
    return dict(layout_sha256=layout_sha, manifest_sha256=bundle.digest, raw_tokens=prep.RAW_TOKENS,
                general_tokens=extension["expected_course_tokens"], bilingual_tokens=pair_tokens,
                combined_tokens=combined, course_tokens=combined-prep.RAW_TOKENS, steps=bundle.steps,
                relations=sum(len(row["relation_groups"]) for row in metadata), bilingual_pairs=len(consumed),
                answer_targets=extension["expected_answer_and_end_targets"] + pair_targets,
                optimizer_updates=0, physical_slots=profile["physical_slots"],
                derived_schedule_sha256=sha256(order.tobytes()).hexdigest().upper())


def worker(layout, layout_sha, receipt, probe, resume, manifest, manifest_sha, resuming, record, cutoff):
    with (training.locked_record(record),
          (record / "stdout.txt").open("x", encoding="utf-8", buffering=1) as log,
          redirect_stdout(log), redirect_stderr(log)):
        pins = sources()
        if (resuming != (resume is not None) or pins != receipt["sources"]
                or torch.cuda.device_count() != 1 or time.time() >= cutoff):
            raise ValueError("the sealed training sources, authorized GPU and cutoff are required")
        bundle = mixed.Bundle(manifest, manifest_sha)
        proof = attach(bundle, layout, layout_sha)
        if proof != receipt["inputs"]:
            raise ValueError("the actual training inputs differ from the CPU receipt")
        free, total = torch.cuda.mem_get_info()
        allowed = (native.CARD_LIMIT_MIB - 384) * 2**20 - (total - free)
        if not 0 < allowed <= total:
            raise ValueError("the approved GPU envelope has no allocation budget")
        torch.cuda.set_per_process_memory_fraction(allowed / total)
        native.publish(record / "extension.json", proof)
        native.publish(record / "input.json", dict(manifest_sha256=bundle.digest, steps=bundle.steps,
                       raw_tokens=prep.RAW_TOKENS, course_tokens=proof["course_tokens"], allocator_budget_bytes=allowed))
        samples = (0, bundle.warmup, 152) if probe else ()
        training.run(bundle, record, cutoff, PROBE_TAG if probe else TAG, pins, layout_sha,
                     proof=proof, resume=resume, probe_updates=samples)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("check", "cpu-probe", "probe", "run"))
    for key in ("manifest", "layout", "record"):
        parser.add_argument("--" + key, required=True, type=Path)
    for key in ("manifest-sha256", "layout-sha256", "source-sha256", "base-source-sha256"):
        parser.add_argument("--" + key, required=True)
    parser.add_argument("--receipt", type=Path)
    parser.add_argument("--stop-by", type=datetime.fromisoformat)
    parser.add_argument("--resume-from", type=Path)
    parser.add_argument("--resume-sha256")
    args = parser.parse_args()
    manifest, layout, record = (path.absolute() for path in (args.manifest, args.layout, args.record))
    layout_sha, own_sha, base_sha = map(native.digest, (args.layout_sha256, args.source_sha256, args.base_source_sha256))
    if (record.exists() or record.is_symlink() or own_sha != prep.sha(Path(__file__))
            or base_sha != prep.sha(Path(mixed.__file__))):
        parser.error("require a fresh record and both admitted source pins")
    if bool(args.resume_from) != bool(args.resume_sha256):
        parser.error("a continuation requires its complete checkpoint and SHA-256")
    resume = (args.resume_from.absolute(), native.digest(args.resume_sha256)) if args.resume_from else None
    if resume and args.mode not in ("check", "run"):
        parser.error("continuation is available only for a full training run or its CPU input check")
    if args.mode == "check":
        bundle = mixed.Bundle(manifest, args.manifest_sha256)
        proof = attach(bundle, layout, layout_sha)
        pins = sources()
        report = dict(status="BILINGUAL_MIX_INPUTS_VERIFIED", sources=pins, inputs=proof)
        if resume is not None:
            prefix, _, _ = training.inspect_resume(bundle, resume, TAG,
                                                    training.loss_signature(bundle, pins, layout_sha), proof)
            report["resume_prefix"] = prefix
        record.mkdir(exist_ok=False)
        native.publish(record / "report.json", report)
        print(proof, flush=True)
        return 0
    if not args.receipt or args.stop_by is None or args.stop_by.tzinfo is None:
        parser.error("grouped training requires its CPU receipt and an authorized cutoff")
    receipt = prep.read_json(args.receipt)
    if receipt["status"] != "BILINGUAL_MIX_INPUTS_VERIFIED" or receipt["sources"] != sources():
        raise ValueError("the receipt must correspond to the grouped training source")
    prefix = receipt.get("resume_prefix")
    if (bool(prefix) != bool(resume) or (resume and
            (prefix["checkpoint_sha256"] != resume[1] or prefix["prior_record"] != str(resume[0].parent.parent)))):
        parser.error("the CPU receipt must cover the same fresh start or exact resume checkpoint")
    if args.mode == "cpu-probe":
        if os.environ.get("CUDA_VISIBLE_DEVICES") != "":
            parser.error("the CPU diagnostic requires an empty CUDA mask")
        torch.set_num_threads(3)
        torch.set_num_interop_threads(1)
        cutoff = args.stop_by.timestamp()
        bundle = mixed.Bundle(manifest, args.manifest_sha256)
        proof = attach(bundle, layout, layout_sha)
        if proof != receipt["inputs"] or time.time() >= cutoff:
            raise ValueError("the CPU diagnostic needs the identical sealed inputs and remaining time")
        record.mkdir(exist_ok=False)
        native.publish(record / "extension.json", proof)
        with sdpa_kernel(SDPBackend.MATH):
            training.run(bundle, record, cutoff, CPU_TAG, receipt["sources"], layout_sha,
                         probe_updates=(152,), device="cpu")
        return 0
    task = partial(worker, layout, layout_sha, receipt, args.mode == "probe", resume)
    with (patch.object(native, "gpu_worker", task), patch.object(native, "gpu_status", partial(mixed.telemetry.gpu_status, record))):
        return native.supervise(manifest, args.manifest_sha256, resume is not None, record, args.stop_by)


if __name__ == "__main__":
    raise SystemExit(main())
