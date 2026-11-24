"""Resolve P109C raw-window and loss policies against the native mixed batches."""

import argparse
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
import json
from math import fsum, isclose
import os
from pathlib import Path
from time import perf_counter

import numpy as np
import torch

from scripts import p109c_bilingual_supervised_training as supervised
from scripts import prepare_p109c_ranked_raw_overlap_repair as ranked
from scripts import run_p109c_early_course_share as early


prep, inputs, base = supervised.prep, supervised.terms.inputs, supervised.base
AUDIT = prep.ROOT / "handoff/audit"
CAP = AUDIT / "P109C_V2_BILINGUAL_WSD_COURSE_CAP_20261124.json"
WSD = AUDIT / "P109C_V2_BILINGUAL_WSD_COURSE_WEIGHTS_20261124.json"
ORIGINAL_CHOICES = ("original", "full_replacement", "ranked_repair")
ANSWER_KINDS = ("start", "body", "end")


@dataclass(frozen=True)
class LossSchedule:
    course: tuple
    value: tuple
    contract: dict

    def weights(self, address, targets):
        if not 0 <= address < len(self.course):
            raise IndexError("the loss schedule only accepts absolute optimizer addresses")
        raw = targets["raw"]
        context = targets["context"]
        answers = targets["answers"]
        share = self.course[address]
        active = fsum(w for n, w in zip(answers, base.KIND_WEIGHTS, strict=True) if n)
        if raw <= 0 or (share != 0 and active == 0):
            raise ValueError("the admitted loss shares need raw and answer supervision")
        weights = tuple(share * w / (active * n) if n else 0.
                        for n, w in zip(answers, base.KIND_WEIGHTS, strict=True))
        return dict(course_share=share, raw_context_weight=(1. - share) / (raw + context),
                    answer_weights=weights, value_weight=self.value[address] if targets["locations"] else 0.,
                    valid_ce_targets=raw + context + sum(answers))


def load_loss_schedule(bundle, course_mode, location_mode):
    if course_mode not in {"fixed", "capped"} or location_mode not in {"fixed", "proportional"}:
        raise ValueError("the declared course and value-location policies must be explicit")
    cap, reference = prep.read_json(CAP), prep.read_json(WSD)
    curve = np.array(cap["course_weight_by_update"], dtype="<f8")
    if (cap["status"] != "CPU_CAPPED_SCHEDULE_VERIFIED" or cap["original_receipt"] != prep.sha(WSD)
            or cap["source"] != prep.sha(prep.ROOT / "scripts/audit_p109c_course_weight_caps.py")
            or len(curve) != bundle.steps or reference["warmup"] != bundle.warmup
            or sha256(curve.tobytes()).hexdigest().upper() != cap["schedule_bytes_sha256"]
            or not np.all((curve >= 0) & (curve < 1)) or np.any(curve[:bundle.warmup] != 0)):
        raise ValueError("the capped schedule is not the exact previously admitted one")
    fixed = np.zeros(bundle.steps, dtype="<f8")
    fixed[bundle.warmup:] = .25
    if (not isclose(fsum(curve), fsum(fixed), rel_tol=0, abs_tol=1e-10)
            or not np.all(curve[bundle.warmup:reference["prefix_end"]] == .1)
            or not np.all(curve[reference["first_wsd_decay_update"] - 1:] == .25)):
        raise ValueError("the capped shares changed the observed prefix, cooldown or total")
    shares = fixed if course_mode == "fixed" else curve
    position = .02 * (shares / .25 if location_mode == "proportional" else (shares > 0))
    digest = sha256(np.column_stack((shares, position)).astype("<f8", copy=False).tobytes()).hexdigest().upper()
    return LossSchedule(tuple(shares.tolist()), tuple(position.tolist()),
                        dict(course=course_mode, location=location_mode, steps=bundle.steps,
                             coefficient_sha256=digest, cap_source_sha256=prep.sha(CAP)))


def select_raw_windows(bundle, name):
    if name not in ORIGINAL_CHOICES:
        raise ValueError("explicit admitted raw-window policy required")
    original = bundle.path.with_name("raw_starts.npy")
    if name == "original":
        path, digest = original, bundle.manifest["raw_starts_sha256"]
    elif name == "full_replacement":
        path = ranked.training.WINDOWS / "raw_starts.npy"
        proof = prep.read_json(path.with_name("profile.json"))
        digest = proof["stored_npy_sha256"]
        if proof["original_manifest_sha256"] != bundle.digest:
            raise ValueError("the whole-replacement source is from a different original manifest")
    else:
        path = ranked.RECORD / "raw_starts.npy"
        proof = prep.read_json(path.with_name("profile.json"))
        lineage = ranked.repair.RECORD / "profile.json"
        digest = proof["stored_npy_sha256"]
        if (proof["prior_profile_sha256"] != prep.sha(lineage)
                or prep.read_json(lineage)["source_manifest_sha256"] != bundle.digest
                or proof["same_schedule_sha256"] != bundle.manifest["schedule_sha256"]):
            raise ValueError("the ranked source must use the exact original raw and course schedule")
    stamp = supervised.native.file_stamp(path)
    rows = ranked.source.read_array(path, digest)
    if (rows.shape != bundle.starts.shape or rows.dtype != bundle.starts.dtype or rows.min() < 0
            or rows.max() + prep.WIDTH >= len(bundle.raw)
            or (name != "original" and np.any(np.diff(np.sort(rows.ravel())) <= prep.WIDTH))):
        raise ValueError("the admitted raw addresses changed shape, extent or nonoverlap")
    rows.flags.writeable = False
    bundle.starts = rows
    bundle.stamps[path] = stamp
    return dict(name=name, file=str(path.relative_to(prep.ROOT)), sha256=digest,
                disjoint=name != "original")


def read_targets(bundle, slots, address):
    layout = bundle.schedule[address]
    lanes = layout[:, 0]
    if len(layout) != prep.ACCUM or np.any(lanes < -2):
        raise ValueError("every update needs the same sealed reserved batch geometry")
    counts = np.zeros(4, dtype=np.int64)
    context = locations = pairs = relations = decimals = content = bilingual_micros = 0
    for lane, index in layout[lanes >= 0]:
        _, _, batch = supervised.course_microbatch(bundle, slots, address, lane, index)
        content += int(np.count_nonzero(batch.segments))
        counts += np.bincount(batch.kinds.ravel(), minlength=4)
        relations += len(batch.groups)
        decimals += len(batch.decimal)
        if batch.bilingual is not None:
            bilingual_micros += 1
            context += len(batch.bilingual.context_targets)
            locations += len(batch.bilingual.value_classes)
            pairs += len(batch.bilingual.gold)
    if bilingual_micros > 1 or locations != 2 * pairs:
        raise ValueError("the native position normalization requires one paired microbatch per update")
    return dict(raw=int((lanes == -1).sum()) * base.MICRO_TOKENS, answers=tuple(counts[1:].tolist()),
                context=context, locations=locations, pairs=pairs, relations=relations, decimals=decimals,
                course_inputs=content, empty=int((lanes == -2).sum()), reserved=len(layout))


def verify(deadline):
    bundle, layout = inputs.load_inputs()
    slots = supervised.terms.BilingualSlots(bundle, layout["layout_sha256"])
    baseline = load_loss_schedule(bundle, "fixed", "fixed")
    capped = load_loss_schedule(bundle, "capped", "proportional")
    reference = prep.read_json(inputs.V2_ONLY_AUDIT)
    cap = prep.read_json(CAP)
    begin, end = cap["affected_updates"]
    peaks = {mode: np.zeros(3) for mode in ("fixed", "capped")}
    counts, written = [], sha256()
    for address in range(bundle.steps):
        if datetime.now(deadline.tzinfo) >= deadline:
            raise TimeoutError("the authorized CPU inspection reached its cutoff")
        row = read_targets(bundle, slots, address)
        old, new = baseline.weights(address, row), capped.weights(address, row)
        for weights in (old, new):
            course_mass = fsum(n * w for n, w in zip(row["answers"], weights["answer_weights"], strict=True))
            full_mass = course_mass + (row["raw"] + row["context"]) * weights["raw_context_weight"]
            if not (isclose(course_mass, weights["course_share"], abs_tol=1e-12)
                    and isclose(full_mass, 1., abs_tol=1e-12)):
                raise ValueError("the absolute native input lost a loss denominator")
        if begin <= address + 1 <= end:
            for mode, value in (("fixed", old), ("capped", new)):
                peaks[mode] = np.maximum(peaks[mode], np.array(value["answer_weights"]) / value["raw_context_weight"])
        counts.append(row)
        written.update(json.dumps(dict(address=address, targets=row, capped=new), sort_keys=True).encode())

    totals = {key: sum(row[key] for row in counts) for key in
              ("raw", "context", "locations", "pairs", "relations", "decimals", "course_inputs", "empty", "reserved")}
    totals["answers"] = [sum(row["answers"][index] for row in counts) for index in range(3)]
    if (totals["answers"] != [reference["targets"][f"answer_{name}"] for name in ANSWER_KINDS]
            or totals["raw"] != reference["targets"]["raw"] or totals["course_inputs"] != layout["course_tokens"]
            or totals["pairs"] != layout["bilingual_pairs"] or totals["empty"] != layout["empty_slots"]
            or totals["relations"] != reference["packed_relations"] or totals["decimals"] != reference["decimal_auxiliary_sites"]):
        raise ValueError(f"native full-layout readback differs from the independent accounting: {totals}")
    for i, field in enumerate(("answer_start_targets", "answer_body_targets", "answer_eot_targets")):
        for mode, label in (("fixed", "flat"), ("capped", "capped")):
            if not isclose(peaks[mode][i], cap["per_target_peaks"][field][label], rel_tol=1e-10, abs_tol=1e-10):
                raise ValueError("the real packed rows did not reproduce the previously computed CE peaks")

    windows = []
    for name in ORIGINAL_CHOICES:
        record = select_raw_windows(bundle, name)
        for address in (0, bundle.warmup, bundle.steps - 1):
            lane, idx = bundle.schedule[address].T
            if not np.array_equal(bundle.raw_batch(idx[lane == -1]),
                                  bundle.raw[bundle.starts[idx[lane == -1], :, None] + np.arange(prep.WIDTH + 1)]):
                raise ValueError("the selected raw policy did not reach the native batch reader")
        windows.append(record)
    bundle.unchanged()

    resume = []
    archive = early.prep.EVIDENCE / early.TAG
    old_report = prep.read_json(archive / "report.json")
    reload = load_loss_schedule(bundle, "capped", "proportional")
    if reload.contract != capped.contract:
        raise ValueError("the independently reconstructed loss schedule has a different identity")
    for phase in ("shared", "lowered"):
        saved = old_report["phases"][phase]
        digest, state = early.phase_checkpoint(Path(saved["checkpoint"]), saved["identity"], torch)
        cursor = state[supervised.trainer.CONTEXT_STATE_KEY]["cursor"]["cursor"]
        address = cursor["next_update"]
        weights = reload.weights(address, counts[address])
        if digest != saved["sha256"] or weights != capped.weights(address, counts[address]):
            raise ValueError("the saved native cursor did not index the same next coefficient")
        resume.append(dict(source_step=state["step"], next_absolute_step=address + 1,
                           checkpoint_sha256=digest, targets=counts[address], weights=weights))
        del state
    return dict(status="NATIVE_CURRICULUM_CPU_READBACK_VERIFIED", source_sha256=prep.sha(Path(__file__)),
                layout=layout, policy_contracts=[baseline.contract, capped.contract], raw_options=windows,
                native_batch_accounting_sha256=written.hexdigest().upper(), totals=totals,
                observed_per_target_peaks={name: a.tolist() for name, a in peaks.items()},
                native_cursor_examples=resume, cpu_batches_read=bundle.steps, optimizer_updates=0)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--stop-by", required=True, type=datetime.fromisoformat)
    args = parser.parse_args()
    if (os.environ.get("CUDA_VISIBLE_DEVICES") != "" or args.stop_by.tzinfo is None
            or args.stop_by > ranked.training.STOP):
        parser.error("the approved CPU scope and cutoff are required")
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    start = perf_counter()
    result = verify(args.stop_by)
    result["elapsed_seconds"] = perf_counter() - start
    supervised.native.publish(args.output, result)
    print(result["status"], result["cpu_batches_read"], result["totals"], flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
