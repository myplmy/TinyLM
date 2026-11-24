"""Compare matched P107 weights at rare, common and numeric held-out targets."""

import argparse
from collections import defaultdict
from datetime import datetime
import json
import os
from pathlib import Path
import time

import numpy as np
import torch
from torch.nn.attention import SDPBackend, sdpa_kernel

from scripts import audit_p107_v11_attention_geometry as geometry
from scripts import eval_p107_v11_causal_groups_cpu as causal


GROUPS = ("unseen", "train_1_to_32", "train_33_to_1024", "train_above_1024", "decimal")
SEED, MAX_CASES, PREFIX = 20261122, 96, 128


def exact_inputs(profile_path, checksum):
    pair = causal.pair
    original = json.loads(pair.supervisor.manifest_bytes(profile_path, checksum))
    if original["source_sha256"] != pair.evaluation.core6.digest(Path(causal.__file__)):
        raise ValueError("the original lexical profile source differs")
    index = pair.load_index(Path(original["index_profile"]), original["index_sha256"])
    receipt = index["splits"]["val"]
    source = pair.documents.BinaryDocumentSource(receipt, batch=pair.BATCH, micros=causal.MICROS,
                                                   length=pair.LENGTH, seed=causal.SEED)
    return original, source


def prepare(original, source):
    val = source.data
    ends = source.ends.astype(np.int64)
    index = np.arange(len(val), dtype=np.int64)
    document = np.searchsorted(ends, index, side="left")
    starts = np.concatenate(([0], ends[:-1] + 1))
    within_document = index > starts[document]
    previous_targets = np.zeros(len(val), dtype=bool)
    for micros, seed in ((16, 99), (original["micros"], original["seed"])):
        for offset in geometry.scheduled_starts(len(val), 1, micros, seed).flat:
            previous_targets[offset + 1:offset + source.length + 1] = True
    result = {}
    rng = np.random.default_rng(SEED)
    for group in GROUPS:
        membership = np.zeros(causal.pair.supervisor.VOCAB, dtype=bool)
        membership[original["groups"][group]] = True
        all_occurrences = membership[val] & within_document
        candidates = np.flatnonzero(all_occurrences & ~previous_targets)
        positions = []
        seen = set()
        keep_all = group in GROUPS[:2]
        for target in candidates if keep_all else rng.permutation(candidates):
            doc = int(document[target])
            if not keep_all and doc in seen:
                continue
            start = max(int(starts[doc]), int(target) - PREFIX)
            positions.append(dict(document=doc, prefix_start=start, target=int(target), token=int(val[target])))
            seen.add(doc)
            if not keep_all and len(positions) == MAX_CASES:
                break
        result[group] = dict(val_targets=int(all_occurrences.sum()), off_prior_targets=len(candidates),
                             selected=sorted(positions, key=lambda row: row["target"]))
    source.unchanged()
    return dict(schema="P107_V11_TARGETED_CAUSAL_V1", max_prefix=PREFIX, seed=SEED,
                val_sha256=source.corpus_sha256, index_sha256=original["index_sha256"], groups=result,
                scoring_source_sha256=causal.pair.evaluation.core6.digest(Path(__file__)))


def score_model(model, groups, source, cutoff):
    by_length = defaultdict(dict)
    for group in groups.values():
        for case in group["selected"]:
            start, pos, token = (case[k] for k in ("prefix_start", "target", "token"))
            if (not 0 <= start < pos < len(source.data) or pos - start > PREFIX or int(source.data[pos]) != token
                    or np.searchsorted(source.ends, start, side="left") != case["document"]
                    or np.searchsorted(source.ends, pos, side="left") != case["document"]):
                raise ValueError("the target or within-document prefix differs")
            by_length[pos-start][pos] = case
    results = {}
    token_ids = torch.arange(causal.pair.supervisor.VOCAB)
    with torch.inference_mode(), sdpa_kernel(SDPBackend.MATH):
        for length, cases in sorted(by_length.items()):
            cases = list(cases.values())
            for offset in range(0, len(cases), 8):
                if time.time() >= cutoff:
                    raise TimeoutError("the CPU lexical panel reached its cutoff")
                batch = cases[offset:offset+8]
                x = torch.from_numpy(np.stack([source.data[c["target"]-length:c["target"]] for c in batch]).astype(np.int64))
                targets = torch.tensor([c["token"] for c in batch], dtype=torch.long)
                logits = model(x, logits_last_only=True)[:, -1, :].float()
                gold = logits.gather(1, targets[:, None])
                nll = logits.logsumexp(1) - gold[:, 0]
                rank = 1 + ((logits > gold) | ((logits == gold) & (token_ids < targets[:, None]))).sum(1)
                for case, loss, place in zip(batch, nll.tolist(), rank.tolist(), strict=True):
                    results[case["target"]] = dict(case, nll=loss, rank=place, top1=place == 1)
    source.unchanged()
    return {name: [results[c["target"]] for c in group["selected"]] for name, group in groups.items()}


def score(args, cohort, source):
    pair = causal.pair
    end_receipt = pair.evaluation.read_json(args.training_record / "supervisor.json")
    report = pair.evaluation.read_json(args.training_record / "report.json")
    if (end_receipt["returncode"] != 0 or end_receipt["stop_reason"] is not None
            or report["status"] not in {"FULL_300M_PAIR", "MATCHED_PARTIAL_BUDGET_PAIR"}):
        raise ValueError("a completed matched training boundary is required")
    observe, adaptive = (report["arms"][name] for name in pair.ARMS)
    if any(observe[k] != adaptive[k] for k in ("end", "initial_sha256", "source_end_rng", "causal_targets")):
        raise ValueError("the two checkpoints do not share the same exposure and boundary")
    args.record.mkdir(exist_ok=False)
    for arm in (observe, adaptive):
        if time.time() >= args.stop_by.timestamp():
            raise TimeoutError("the CPU lexical panel reached its cutoff")
        scored = score_model(causal.checkpoint_model(arm, arm["end"]), cohort["groups"], source,
                             args.stop_by.timestamp())
        pair.supervisor.publish(args.record / f"{arm['arm']}.json", dict(status="COMPLETE", precision="CPU_FP32_MATH",
            checkpoint_sha256=arm["final"]["sha256"], steps=arm["end"], cohort_sha256=args.cohort_sha256, rows=scored))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "score"))
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--profile-sha256", required=True)
    parser.add_argument("--cohort", type=Path, required=True)
    parser.add_argument("--cohort-sha256")
    parser.add_argument("--training-record", type=Path)
    parser.add_argument("--record", type=Path)
    parser.add_argument("--stop-by", type=datetime.fromisoformat)
    args = parser.parse_args()
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "":
        parser.error("the lexical panel runs on CPU only")
    torch.set_num_threads(3)
    original, source = exact_inputs(args.profile.absolute(), args.profile_sha256)
    if args.mode == "prepare":
        cohort = prepare(original, source)
        causal.pair.supervisor.publish(args.cohort, cohort)
        print({g: (v["val_targets"], v["off_prior_targets"], len(v["selected"])) for g, v in cohort["groups"].items()})
        return
    if not all((args.cohort_sha256, args.training_record, args.record, args.stop_by)) or args.stop_by.tzinfo is None:
        parser.error("score requires a sealed cohort, matched training record, output and cutoff")
    cohort = json.loads(causal.pair.supervisor.manifest_bytes(args.cohort.absolute(), args.cohort_sha256))
    if (cohort["val_sha256"] != source.corpus_sha256 or cohort["index_sha256"] != original["index_sha256"]
            or cohort["scoring_source_sha256"] != causal.pair.evaluation.core6.digest(Path(__file__))):
        raise ValueError("the frozen cohort differs from the current score inputs")
    score(args, cohort, source)


if __name__ == "__main__":
    main()
