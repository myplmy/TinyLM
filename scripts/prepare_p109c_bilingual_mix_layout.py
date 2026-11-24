"""Seal the per-update slots for the verified P109C bilingual course additions."""

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path

import numpy as np

from scripts import run_p109c_scratch_mixed as mixed


prep, native = mixed.prep, mixed.native
ROOT = prep.ROOT
PAIR_AUDIT = ROOT / "handoff/audit/P109C_V2_BILINGUAL_PAIR_ADMISSION_20261123.json"
PAIR_SOURCE = ROOT / "test_result/evidence/p109c_bilingual_value_transfer_cpu_v1_20261121/wide_pairs.npz"
COUNT = 32768


def assignments(bundle, additions, audit, lengths):
    sources = bundle.manifest["lanes"]
    relation = {i for i, row in enumerate(sources) if row["kind"] == "relation"}
    starts = set()
    for row in additions["positions"]:
        step, slot = row["update"] - 1, row["micro_slot"]
        lane, _ = bundle.schedule[step, slot]
        if lane < 0 or lane in relation or sources[lane]["name"] != row["lane"]:
            raise ValueError("general course additions must stay in their original non-relation batches")
        starts.add((step, slot))
    ordering = np.random.default_rng(10923).permutation(np.arange(COUNT))
    layout, fingerprint = [], []
    for quarter, indices in enumerate(np.array_split(ordering, 4), 1):
        receipt = audit["quarters"][str(quarter)]
        begin, end = receipt["first_update"]-1, receipt["last_update"]
        selected = list(range(begin, end))
        if len(selected) != receipt["paired_updates"] or len(indices) != receipt["pairs"]:
            raise ValueError("the new placement must use the four audited mixed quarters")
        for step, subset in zip(selected, np.array_split(indices, len(selected)), strict=True):
            scheduled = bundle.schedule[step]
            relation_slots = [i for i, (lane, _) in enumerate(scheduled) if lane in relation]
            if len(relation_slots) < 2:
                raise ValueError("each bilingual batch needs one slot released by within-update packing")
            anchor, slot = relation_slots[:2]
            if (step, slot) in starts:
                raise ValueError("the bilingual and general additions both occupy the same slot")
            relation_widths = np.zeros(prep.BATCH, dtype=np.int64)
            for i in relation_slots:
                lane, position = scheduled[i]
                relation_widths += np.count_nonzero(bundle.data[lane][position][:, 2], axis=1)
            if relation_widths.max() > prep.WIDTH:
                raise ValueError("the original relation members do not fit within the planned anchor batch")
            cursor = [0] * prep.BATCH
            offsets = []
            for local, pair in enumerate(subset):
                left = 2 * (local % 2)
                offsets.append([int(pair), left, cursor[left], cursor[left + 1]])
                cursor[left] += int(lengths[2*pair])
                cursor[left + 1] += int(lengths[2*pair + 1])
            if max(cursor) > receipt["max_row_width"]:
                raise ValueError("bilingual packing exceeds the checked row width")
            layout.append(dict(update=step+1, relation_anchor=anchor, relation_slots_to_merge=relation_slots[1:],
                               new_bilingual_slot=slot, pairs=offsets, row_widths=cursor))
            fingerprint.append((step+1, [int(pair) for pair in subset]))
    value = sha256(json.dumps(fingerprint,separators=(",",":")).encode()).hexdigest().upper()
    if value != audit["assignment_sha256"] or len(layout) != bundle.steps-bundle.warmup:
        raise ValueError("the placement does not reconstruct the audited pair order")
    return layout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for option in ("manifest", "layout", "record"):
        parser.add_argument("--" + option, type=Path, required=True)
    for option in ("manifest-sha256", "layout-sha256"):
        parser.add_argument("--" + option, required=True)
    args = parser.parse_args()
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "" or args.record.exists() or args.record.is_symlink():
        parser.error("explicit CPU-only preparation with a fresh record is required")
    bundle = mixed.Bundle(args.manifest.absolute(),args.manifest_sha256)
    audit = json.loads(PAIR_AUDIT.read_text(encoding="utf-8"))
    general = json.loads(native.manifest_bytes(args.layout.absolute(),args.layout_sha256))
    archive_sha = prep.sha(PAIR_SOURCE)
    if (audit["comparison"]["manifest_sha256"] != bundle.digest or general["old_manifest_sha256"] != bundle.digest
            or audit["comparison"]["identical_input_token_rows"] != 0 or audit["comparison"]["novel_complete_pairs"] != COUNT
            or audit["combined_with_general_256"]["general_layout_sha256"] != native.digest(args.layout_sha256)
            or archive_sha != audit["paired_archive"]["sha256"]):
        raise ValueError("the frozen pair-source, dedup and general admission must agree")
    with np.load(PAIR_SOURCE,allow_pickle=False) as source:
        x, y, sites, context = (source[key] for key in ("tokens", "labels", "sites", "context"))
    positions = np.arange(x.shape[1])+1
    lengths = np.where((x!=0) | (y!=prep.IGNORE),positions,0).max(1)
    if (len(x)!=2*COUNT or np.any(sites[:,:-1] < 0) or np.any(sites[:,:-1] >= lengths[:,None])
            or np.any((y!=prep.IGNORE) & (context!=prep.IGNORE)) or not np.all((y==prep.END).sum(1)==1)
            or int(lengths.sum())!=audit["additional_novel_input_tokens"]
            or prep.sha(PAIR_SOURCE)!=archive_sha):
        raise ValueError("the paired source must retain its original answer and context boundaries")
    layout = assignments(bundle,general,audit,lengths)
    bundle.unchanged()
    args.record.mkdir(exist_ok=False)
    native.publish(args.record / "layout.json",dict(status="BILINGUAL_UPDATE_PLACEMENT_SEALED",
        input_manifest_sha256=bundle.digest, general_layout_sha256=native.digest(args.layout_sha256),
        pair_archive_sha256=archive_sha, admission_audit_sha256=prep.sha(PAIR_AUDIT),
        assignment_sha256=audit["assignment_sha256"], updates=bundle.steps, packed_updates=len(layout),
        combined_input_tokens=audit["combined_with_general_256"]["total_nonpad_inputs"],
        optimizer_updates_applied=0, physical_slots=general["physical_slots"],
        pair_fields=["archive_pair", "ko_row", "ko_offset", "en_offset"], placements=layout))
    print("BILINGUAL_UPDATE_PLACEMENT_SEALED",len(layout),prep.sha(args.record / "layout.json"),flush=True)


if __name__ == "__main__":
    main()
