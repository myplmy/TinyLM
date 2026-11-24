"""Recount P109C course coefficients against the exact native WSD schedule and bilingual rows."""

import argparse
from fractions import Fraction
from hashlib import sha256
import json
from math import fsum, isclose
from pathlib import Path

import numpy as np

from scripts import p109c_bilingual_supervised_training as bilingual
from scripts import prepare_p109c_bilingual_mix_layout as layout_tools
from tinylm.train.anneal_schedule import lr_factor


ROOT = bilingual.prep.ROOT
AUDIT = ROOT / "handoff" / "audit"
OLD_RAMP = AUDIT / "P109C_V2_CE_RAMP_BUDGET_20261123.json"
SHORT_TRIAL = AUDIT / "P109C_EARLY_COURSE_SHARE_20261124.json"
NORMALIZATION = AUDIT / "P109C_V2_BILINGUAL_AUXILIARY_NORMALIZATION_20261124.json"
ASSEMBLY = AUDIT / "P109C_V2_BILINGUAL_ONLY_ASSEMBLY_20261124.json"
LAYOUT = bilingual.terms.inputs.LAYOUT
SOURCES = (OLD_RAMP, SHORT_TRIAL, NORMALIZATION, ASSEMBLY, LAYOUT)
KINDS = ("answer_start_targets", "answer_body_targets", "answer_eot_targets")
IGNORE, EOT = bilingual.prep.IGNORE, bilingual.prep.END


def digest(path):
    return bilingual.prep.sha(path)


def pinned_inputs():
    old, partial, norm, assembly, layout = [bilingual.prep.read_json(path) for path in SOURCES]
    original = old["sources"]["v2_native_log"]
    native_log = ROOT / original["path"]
    journal = native_log.parent.parent / "updates.jsonl"
    pair_archive = layout_tools.PAIR_SOURCE
    verified = (digest(native_log) == original["sha256"],
                digest(journal) == norm["sources"]["native_updates_sha256"],
                digest(LAYOUT) == norm["sources"]["layout_sha256"] == assembly["inherited_layout_sha256"],
                digest(pair_archive) == layout["pair_archive_sha256"],
                partial["manifest_sha256"] == layout["input_manifest_sha256"] == assembly["manifest_sha256"])
    if not all(verified):
        raise ValueError("the actual v2 exposure and approved bilingual placement must match their audits")
    return old, partial, norm, assembly, layout, native_log, journal, pair_archive


def exact_counts(journal, pair_archive, layout, assembly, norm, warm, baseline):
    with journal.open(encoding="utf-8") as stream:
        rows = [json.loads(line) for line in stream]
    if (len(rows) != assembly["steps"] or len(layout["placements"]) != len(rows) - warm
            or any(row["index"] != i or row["source_update"] != i for i, row in enumerate(rows))):
        raise ValueError("all original progress rows must be present, unique and ordered")
    kinds = np.array([[row[key] for key in KINDS] for row in rows], dtype=np.int64)
    raw = np.array([row["raw_targets"] for row in rows], dtype=np.int64)
    expected = np.array([float(baseline if i >= warm else 0) for i in range(len(rows))])
    weights = np.array([row["ce_weights"] for row in rows], dtype=np.float64)
    if (not np.allclose((weights[:, 1:] * kinds).sum(axis=1), expected, atol=1e-12, rtol=0)
            or not np.allclose(weights[:, 0] * raw, 1 - expected, atol=1e-12, rtol=0)):
        raise ValueError("the logged loss coefficients differ from the flat baseline")
    with np.load(pair_archive, allow_pickle=False) as archive:
        labels, context = archive["labels"], archive["context"]
    valid = labels != IGNORE
    eot = (labels == EOT).sum(axis=1)
    starts = valid[:, 0].astype(np.int64) + (valid[:, 1:] & ~valid[:, :-1]).sum(axis=1)
    if (labels.shape[0] != 2 * layout_tools.COUNT or labels.shape != context.shape
            or not np.all(starts == 1) or not np.all(eot == 1) or np.any(valid & (context != IGNORE))):
        raise ValueError("each bilingual example needs one supervised answer and separate context")
    body = valid.sum(axis=1) - starts - eot
    counts = np.column_stack((starts, body, eot, (context != IGNORE).sum(axis=1)))
    additions = np.zeros((len(rows), 4), dtype=np.int64)
    seen = []
    for offset, block in enumerate(layout["placements"], warm):
        if block["update"] != offset + 1 or not block["pairs"]:
            raise ValueError("the bilingual slot must match the actual absolute optimizer index")
        pairs = np.array([row[0] for row in block["pairs"]], dtype=np.int64)
        indexes = (pairs[:, None] * 2 + np.arange(2)).ravel()
        additions[offset] = counts[indexes].sum(axis=0)
        seen.extend(pairs.tolist())
    if sorted(seen) != list(range(layout_tools.COUNT)):
        raise ValueError("all bilingual pairs must be assigned exactly once")
    kinds += additions[:, :3]
    totals = [assembly["targets"][f"answer_{key}"] for key in ("start", "body", "end")]
    if (kinds.sum(axis=0).tolist() != totals or int(raw.sum()) != assembly["targets"]["raw"]
            or int(additions[:, 3].sum()) != norm["total_context"]
            or int(additions[:, 0].sum()) != int(additions[:, 2].sum()) or not np.all(kinds[warm:] > 0)):
        raise ValueError("the bilingual response or context totals disagree with prior independent audits")
    return raw, kinds, additions[:, 3], additions[:, 0]


def schedules(steps, warm, hold_end, ramp_end, taper, factors, baseline, early, previous_peak):
    first_decay = next(i for i, factor in enumerate(factors) if i >= warm and factor < 1)
    taper_start = first_decay - taper
    if not 0 < warm < hold_end < ramp_end - 1 < taper_start < first_decay < steps or taper < 2:
        raise ValueError("the hold, ramp and taper must all fit before native cooldown")
    target = baseline * (steps - warm)
    flat = [Fraction(0)] * warm + [baseline] * (steps - warm)
    old = flat.copy()
    pieces = []
    for i in range(warm, steps):
        previous_progress = min(Fraction(i - warm, ramp_end - 1 - warm), 1)
        old[i] = early + (previous_peak - early) * previous_progress
        if i < hold_end:
            pieces.append((early, Fraction(0)))
        elif i < ramp_end:
            progress = Fraction(i - hold_end, ramp_end - 1 - hold_end)
            pieces.append((early * (1 - progress), progress))
        elif i < taper_start:
            pieces.append((Fraction(0), Fraction(1)))
        elif i < first_decay:
            progress = Fraction(i - taper_start, taper - 1)
            pieces.append((baseline * progress, 1 - progress))
        else:
            pieces.append((baseline, Fraction(0)))
    peak = (target - sum(constant for constant, _ in pieces)) / sum(slope for _, slope in pieces)
    inside = [Fraction(0)] * warm + [constant + slope * peak for constant, slope in pieces]
    if (sum(flat) != target or sum(old) != target or sum(inside) != target or not early < baseline < peak < 1
            or inside[warm:hold_end] != [early] * (hold_end - warm)
            or inside[first_decay - 1:] != flat[first_decay - 1:]
            or any(x != y and f != 1 for x, y, f in zip(flat, inside, factors, strict=True))):
        raise ValueError("the proposed course schedule does not preserve both coefficient budgets")
    return {"flat": flat, "prior_ramp": old, "plateau_compensated": inside}, peak, taper_start, first_decay


def stats(values):
    minimum, median, p95, maximum = np.quantile(values, (0, .5, .95, 1))
    return dict(min=float(minimum), median=float(median), p95=float(p95), max=float(maximum))


def summarize(weights, factors, windows, raw, kinds, context, locations, warm, base):
    share = np.asarray(weights, dtype=np.float64)
    overall = dict(course_sum=float(sum(weights)), course_lr_sum=fsum(share * factors),
                   raw_and_context_lr_sum=fsum((1 - share) * factors), peak=float(share.max()),
                   last=float(share[-1]), shares_sha256=sha256(share.astype("<f8").tobytes()).hexdigest().upper())
    response_unit = share[warm:, None] * np.array(bilingual.base.KIND_WEIGHTS) / kinds[warm:]
    raw_unit = (1 - share[warm:]) / (raw[warm:] + context[warm:])
    location = bilingual.VALUE_WEIGHT / locations[warm:]
    ratios = response_unit / raw_unit[:, None]
    location_vs_start = location / response_unit[:, 0]
    ratio_matched = location_vs_start * (share[warm:] / float(base))
    stage_stats = {}
    for name, (first, stop) in windows.items():
        span = slice(first, stop)
        local = slice(first - warm, stop - warm)
        stage_stats[name] = dict(first_update=first + 1, last_update=stop,
                                 review_share=stats(share[span]), course_sum=fsum(share[span]),
                                 course_lr_sum=fsum(share[span] * factors[span]),
                                 response_unit_vs_raw={key: stats(ratios[local, j]) for j, key in enumerate(KINDS)},
                                 fixed_location_unit_vs_answer_start=stats(location_vs_start[local]),
                                 proportional_location_unit_vs_answer_start=stats(ratio_matched[local]))
    overall["windows"] = stage_stats
    scaled = bilingual.VALUE_WEIGHT / float(base) * share
    overall["location_if_proportional"] = dict(earliest=float(scaled[warm]), peak=float(scaled.max()),
                                                lr_sum=fsum(scaled * factors), unweighted_sum=fsum(scaled))
    return overall


def audit():
    old, partial, norm, assembly, layout, native_log, journal, pair_archive = pinned_inputs()
    original = bilingual.prep.read_json(native_log)
    steps, warm = original["steps"], bilingual.prep.WARMUP
    if (steps != partial["horizon"] or original["sched"] != "wsd" or original["n_skip"] != 0
            or warm != partial["shared_updates"] or warm != max(5, min(steps // 10, 100))):
        raise ValueError("the existing run must supply the exact native WSD and warm-up contract")
    base, low = (Fraction(str(partial["share_by_arm"][key])) for key in ("flat", "lowered"))
    hold_end = warm + partial["mixed_updates"]
    ramp_end = old["proposed"]["ramp_ends_update"]
    factors = np.array([lr_factor(i, warm, steps, original["sched"], original["decay_frac"])
                        for i in range(steps)])
    variants, peak, taper_start, cooldown_start = schedules(steps, warm, hold_end, ramp_end,
        original["eval_every"], factors, base, low, Fraction(old["proposed"]["course_share_plateau_fraction"]))
    raw, kinds, context, positions = exact_counts(journal, pair_archive, layout, assembly, norm, warm, base)
    windows = dict(tested_prefix=(warm, hold_end), ramp=(hold_end, ramp_end),
                   stable_plateau=(ramp_end, taper_start), taper=(taper_start, cooldown_start),
                   cooldown=(cooldown_start, steps))
    arms = {name: summarize(share, factors, windows, raw, kinds, context, positions, warm, base)
            for name, share in variants.items()}
    a, c = arms["flat"], arms["plateau_compensated"]
    if not all(isclose(a[key], c[key], abs_tol=1e-10, rel_tol=0)
               for key in ("course_sum", "course_lr_sum", "raw_and_context_lr_sum")):
        raise ValueError("the native WSD coefficient budgets disagree")
    pins = (*SOURCES, native_log, journal, pair_archive, Path(__file__).resolve(),
            ROOT / "tinylm/train/anneal_schedule.py")
    return dict(status="CPU_COEFFICIENTS_VERIFIED", steps=steps, warmup=warm, prefix_end=hold_end,
                ramp_end=ramp_end, taper_start_update=taper_start + 1, first_wsd_decay_update=cooldown_start + 1,
                proposed_peak_fraction=str(peak), learning_rate=original["lr"],
                decay_frac=original["decay_frac"], arms=arms,
                first_raw_update=int(raw[warm]), first_context_update=int(context[warm]),
                first_course_kinds=kinds[warm].tolist(), sources={str(p.relative_to(ROOT)): digest(p) for p in pins},
                optimizer_updates=0)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", required=True, type=Path)
    args = parser.parse_args()
    proof = audit()
    with args.receipt.open("x", encoding="utf-8") as stream:
        json.dump(proof, stream, ensure_ascii=False, allow_nan=False, indent=2)
        print(file=stream)
    for name, arm in proof["arms"].items():
        print(name, arm["course_sum"], arm["course_lr_sum"], arm["peak"], arm["last"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
