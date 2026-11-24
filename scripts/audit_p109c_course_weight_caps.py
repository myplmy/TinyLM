"""Bound P109C per-answer CE peaks without changing the tested prefix or WSD budget."""

import argparse
from fractions import Fraction
from hashlib import sha256
import json
from math import fsum, isclose
from pathlib import Path

import numpy as np

from scripts import audit_p109c_wsd_course_weights as schedule


PRIOR = schedule.AUDIT / "P109C_V2_BILINGUAL_WSD_COURSE_WEIGHTS_20261124.json"


def redistributed(nominal, ceilings):
    target = fsum(nominal)
    if fsum(ceilings) < target:
        raise ValueError("the peak ceilings cannot support the matched course budget")
    lower, upper = 0., float(np.max(ceilings))
    for _ in range(56):
        offset = (lower + upper) / 2
        if fsum(np.minimum(nominal + offset, ceilings)) < target:
            lower = offset
        else:
            upper = offset
    result = np.minimum(nominal + upper, ceilings)
    if not isclose(fsum(result), target, rel_tol=0, abs_tol=1e-10):
        raise ValueError("course coefficient redistribution did not preserve its sum")
    return result, upper


def audit():
    original = schedule.bilingual.prep.read_json(PRIOR)
    if (original["status"] != "CPU_COEFFICIENTS_VERIFIED"
            or any(schedule.digest(schedule.ROOT / path) != digest for path, digest in original["sources"].items())):
        raise ValueError("the exact suite of admitted schedule sources must match")
    old, partial, norm, assembly, layout, log, journal, pairs = schedule.pinned_inputs()
    native = schedule.bilingual.prep.read_json(log)
    steps, warm, prefix = (original[k] for k in ("steps", "warmup", "prefix_end"))
    base, low = (Fraction(str(partial["share_by_arm"][key])) for key in ("flat", "lowered"))
    factors = np.array([schedule.lr_factor(i, warm, steps, native["sched"], native["decay_frac"])
                        for i in range(steps)])
    curves, peak, taper, cooldown = schedule.schedules(steps, warm, prefix, original["ramp_end"],
        native["eval_every"], factors, base, low, Fraction(old["proposed"]["course_share_plateau_fraction"]))
    raw, kinds, context, _ = schedule.exact_counts(journal, pairs, layout, assembly, norm, warm, base)
    shares = np.array(curves["plateau_compensated"], dtype="<f8")
    if sha256(shares.tobytes()).hexdigest().upper() != original["arms"]["plateau_compensated"]["shares_sha256"]:
        raise ValueError("the capped candidate needs the verified plateau schedule")
    affected = slice(prefix, taper)
    nominal = shares[affected].copy()
    scale = (raw + context)[affected, None] * np.array(schedule.bilingual.base.KIND_WEIGHTS) / kinds[affected]
    flat = float(base)
    bounds = (scale * (flat / (1 - flat))).max(axis=0)
    ceilings = np.minimum(float(peak), (bounds / (scale + bounds)).min(axis=1))
    shares[affected], step_shift = redistributed(nominal, ceilings)
    capped = shares[affected]
    actual = scale * (capped / (1 - capped))[:, None]
    if np.any(actual > bounds + 1e-10) or np.any(factors[affected] != 1):
        raise ValueError("the scoped adjustment must honor the per-target cap during constant learning rate")
    weighted = fsum(shares * factors)
    raw_weighted = fsum((1 - shares) * factors)
    fixed = original["arms"]["flat"]
    if not (isclose(weighted, fixed["course_lr_sum"], abs_tol=1e-10, rel_tol=0)
            and isclose(raw_weighted, fixed["raw_and_context_lr_sum"], abs_tol=1e-10, rel_tol=0)
            and isclose(fsum(shares), fixed["course_sum"], abs_tol=1e-10, rel_tol=0)
            and np.all(shares[cooldown:] == flat) and np.all(shares[warm:prefix] == float(low))):
        raise ValueError("the WSD budget, tested prefix or fixed cooldown changed")
    nominal_ratios = scale * (nominal / (1 - nominal))[:, None]
    return dict(status="CPU_CAPPED_SCHEDULE_VERIFIED", original_receipt=schedule.digest(PRIOR),
                source=schedule.digest(Path(__file__).resolve()), steps=steps,
                affected_updates=[prefix + 1, taper], course_sum=fsum(shares), course_lr_sum=weighted,
                raw_and_context_lr_sum=raw_weighted, cap_binding_updates=int((nominal > ceilings + 1e-12).sum()),
                increased_share=float(step_shift), greatest_share_reduction=float(np.max(nominal - capped)),
                per_target_peaks={kind: dict(flat=float(bounds[i]), smooth=float(nominal_ratios[:, i].max()),
                                            capped=float(actual[:, i].max())) for i, kind in enumerate(schedule.KINDS)},
                optimizer_updates=0, schedule_bytes_sha256=sha256(shares.tobytes()).hexdigest().upper(),
                course_weight_by_update=shares.tolist())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", required=True, type=Path)
    args = parser.parse_args()
    proof = audit()
    with args.receipt.open("x", encoding="utf-8") as stream:
        json.dump(proof, stream, ensure_ascii=False, allow_nan=False, indent=2)
        print(file=stream)
    print(proof["cap_binding_updates"], proof["increased_share"], proof["per_target_peaks"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
