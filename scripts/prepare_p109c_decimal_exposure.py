"""Seal extra exact carry labels for already-admitted scalar addition responses."""

import argparse
from collections import Counter
from pathlib import Path
import re

import numpy as np
from tokenizers import Tokenizer

from scripts import audit_p109c_english_operation_coverage as coverage
from scripts import diag_p109c_addition_matched_prompts as development
from scripts import p106b_joint_decimal as decimal


native, sources = coverage.native, coverage.comparison
PREP, CORE = native.prep, native.supervised
LANE = "binding_arithmetic_and_state_en_plain"
SCALAR = re.compile(r"Calculate ([0-9]{1,2})\+([0-9]{1,2})\. Reply with one integer only\.")
PLUS = re.compile(r"\b([0-9]+)\s*\+\s*([0-9]+)\b")
BASE_WEIGHT = .02
DEV_FILE = sources.ROOT / "handoff/audit/P109C_ADDITION_MATCHED_PROMPTS_20261124.json"
EXPECTED = sources.ROOT / "handoff/audit/P109C_VERIFIED_ADDITION_FORMATS_20261124.json"


def excluded_pairs():
    official = sources.panel.build("final") + sources.panel.build("dev")
    selected = [row["prompt"] for row in official if row["category"] == "reasoning"]
    authored = development.cases()
    if authored != PREP.read_json(DEV_FILE)["rows"]:
        raise ValueError("the addition development conditions changed")
    pairs = {tuple(sorted(map(int, match.groups()))) for prompt in selected for match in PLUS.finditer(prompt)}
    pairs.update(tuple(sorted(row["operands"])) for row in authored)
    return pairs


def verify_lane(bundle, lane, tokenizer, heldout):
    events, totals = {}, Counter()
    for index, pack in enumerate(bundle.data[lane]):
        x, y, segments = pack.transpose(1, 0, 2)
        if bundle.aux[lane][index]["gold"] >= 0 or bundle.aux[lane][index]["decimal"]:
            raise ValueError("the added labels require the original plain unlabeled lane")
        kinds = native.base.label_kinds(y, segments)
        for row, start in zip(*np.where(kinds == 1), strict=True):
            earlier = np.flatnonzero(segments[row, :start + 1] != segments[row, start])
            left = int(earlier[-1]+1) if len(earlier) else 0
            text = tokenizer.decode(x[row, left:start + 1].tolist(), skip_special_tokens=False)
            turns = coverage.ROLE.findall(text)
            if not turns or not (match := SCALAR.fullmatch(turns[-1].strip())):
                continue
            a, b = map(int, match.groups())
            total, _, _, carry = decimal.decimal_parts(a, b)
            end = start + 1
            while end < y.shape[1] and kinds[row, end] == 2:
                end += 1
            label = tokenizer.decode(y[row, start:end].tolist(), skip_special_tokens=False)
            if (label.strip() != str(total) or end >= y.shape[1] or y[row, end] != PREP.END
                    or not np.all(segments[row, left:end + 1] == segments[row, start])
                    or segments[row, start] <= 0):
                raise ValueError("a scalar addition target or its exact segment changed")
            if tuple(sorted((a, b))) in heldout:
                totals["excluded_operand_pairs"] += 1
                continue
            totals["verified_new_labels"] += 1
            totals["carry"] += carry
            events.setdefault(index, []).append([int(row), int(start), 1000 + total + 200 * carry])
    return events, totals


def schedule_readback(bundle, lane, events):
    base, extra = np.zeros(bundle.steps, dtype=np.int32), np.zeros(bundle.steps, dtype=np.int32)
    for address, row in enumerate(bundle.schedule):
        for key, index in row[row[:, 0] >= 0]:
            base[address] += len(bundle.aux[key][index]["decimal"])
            if key == lane:
                extra[address] += len(events.get(int(index), ()))
    return base, extra


def prepare():
    bundle, layout = native.inputs.load_inputs()
    tok = Tokenizer.from_file(str(PREP.TOKENIZER))
    lane = next(index for index, item in enumerate(bundle.manifest["lanes"]) if item["name"] == LANE)
    events, stats = verify_lane(bundle, lane, tok, excluded_pairs())
    base, extra = schedule_readback(bundle, lane, events)
    expected = PREP.read_json(EXPECTED)
    lane_count = expected["by_lane"][LANE]["bare_correct"]
    if (stats["verified_new_labels"] + stats["excluded_operand_pairs"] != lane_count
            or int(extra.sum()) != stats["verified_new_labels"] or int(base.sum()) != layout["decimal_sites"]):
        raise ValueError("addition rows and actual schedule did not reconcile")
    wsd = PREP.read_json(native.WSD)
    bounds = (0, bundle.warmup, 160, 320, wsd["first_wsd_decay_update"] - 1, bundle.steps)
    phases = []
    for low, high in zip(bounds[:-1], bounds[1:], strict=True):
        old_sites, new_sites = base[low:high], extra[low:high]
        active = old_sites > 0
        expanded = active | (new_sites > 0)
        mass = BASE_WEIGHT * int(active.sum())
        phases.append(dict(first_update=low+1, last_update=high, old_sites=int(old_sites.sum()),
                           candidate_sites=int(new_sites.sum()), old_active_updates=int(active.sum()),
                           new_active_updates=int(expanded.sum()), extra_within_existing_budget=int(new_sites[active].sum()),
                           old_auxiliary_mass=mass, phase_matched_weight=mass/int(expanded.sum()) if expanded.any() else 0.))
    bundle.unchanged()
    return dict(status="SAME_PACKED_TEXT_DECIMAL_LABELS_VERIFIED", manifest_sha256=bundle.digest,
                layout_sha256=layout["derived_schedule_sha256"], lane=lane, lane_name=LANE,
                math_label=stats, phases=phases, events_by_slot=events,
                sources=[sources.source(path) for path in (Path(__file__).resolve(), Path(decimal.__file__).resolve(),
                         DEV_FILE, EXPECTED, native.WSD)])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    report = prepare()
    CORE.native.publish(args.output.absolute(), report)
    print(report["status"], report["math_label"], flush=True)


if __name__ == "__main__":
    main()
