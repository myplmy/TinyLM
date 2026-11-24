"""Compare document and token exposure of the sealed P109C raw schedules."""

import argparse
from datetime import datetime
from hashlib import sha256
import os
from pathlib import Path
from time import perf_counter

import numpy as np
import torch

from scripts import eval_p107_v11_causal_groups_cpu as validation
from scripts import run_p109c_v2_raw_nonoverlap as training


prep, source = training.prep, training.windows
FULL = prep.ROOT / "handoff/audit/P109C_V2_RAW_NONOVERLAP_FULL_20261124.json"
LEXICAL = prep.ROOT / "handoff/audit/P109C_V2_RAW_NONOVERLAP_LEXICAL_20261123.json"
VAL = prep.ROOT / "data_cache/p107_v11_causal_group_profile_v1_20261121.json"
READBACK = prep.EVIDENCE / "p109c_same_raw_val_v1v2_cpu_v2_20261123/report.json"
WSD = prep.ROOT / "handoff/audit/P109C_V2_BILINGUAL_WSD_COURSE_WEIGHTS_20261124.json"
WIDTH, VOCAB = prep.WIDTH, validation.pair.supervisor.VOCAB
STAGES = (0, 100, 768, 1472, 2374, 2942)


def document_counts(starts, ends):
    """Integrate total draws and unique target positions at document edges."""
    starts = starts.ravel() + 1
    limit = int(ends[-1]) + 1
    points = np.r_[0, starts, starts + WIDTH, limit]
    values = np.r_[0, np.ones(len(starts), dtype=np.int64), -np.ones(len(starts), dtype=np.int64), 0]
    edges, index = np.unique(points, return_inverse=True)
    change = np.zeros(len(edges), dtype=np.int64)
    np.add.at(change, index, values)
    multiplicity = np.cumsum(change)
    if edges[0] != 0 or edges[-1] != limit or multiplicity[-1] != 0 or (multiplicity < 0).any():
        raise ValueError("invalid target interval extent or multiplicity")
    documents = np.r_[0, ends + 1]
    left = np.searchsorted(edges, documents, side="right") - 1
    distances = documents - edges[left]

    def by_document(level):
        prefix = np.r_[0, np.cumsum(np.diff(edges) * level[:-1])]
        return np.diff(prefix[left] + distances * level[left])

    draws, unique = by_document(multiplicity), by_document(multiplicity > 0)
    if (draws.sum() != len(starts) * WIDTH or (unique > draws).any()
            or (unique > np.diff(documents)).any()):
        raise ValueError("document exposure accounting did not close")
    return draws, unique


def counts_for(raw, starts, deadline):
    result = np.zeros(VOCAB, dtype=np.int64)
    positions = np.arange(1, WIDTH + 1)
    for i in range(0, len(starts), 1024):
        if datetime.now(deadline.tzinfo) >= deadline:
            raise TimeoutError("the authorized CPU exposure audit reached its cutoff")
        tokens = raw[starts[i:i + 1024, None] + positions]
        result += np.bincount(tokens.ravel(), minlength=VOCAB)
    if result.sum() != len(starts) * WIDTH:
        raise ValueError("token exposure accounting did not close")
    return result


def document_summary(draws, unique, lengths):
    touched = unique > 0
    return dict(target_draws=int(draws.sum()), unique_target_positions=int(unique.sum()),
                repeated_target_draws=int((draws - unique).sum()), documents_touched=int(touched.sum()),
                documents_fully_covered=int((unique == lengths).sum()),
                documents_with_any_repeated_position=int((draws > unique).sum()),
                median_fraction_covered=float(np.median(unique[touched] / lengths[touched])))


def val_thresholds(counts, val):
    return dict(validation_positions_exposed_zero=int(val[counts == 0].sum()),
                validation_positions_exposed_1_to_32=int(val[(counts >= 1) & (counts <= 32)].sum()),
                validation_positions_exposed_33_to_1024=int(val[(counts >= 33) & (counts <= 1024)].sum()),
                validation_positions_exposed_above_1024=int(val[counts > 1024].sum()),
                mean_log_one_plus_train_draws=float(val @ np.log1p(counts) / val.sum()))


def phases(raw, schedule, starts, ends, heldout, lengths, deadline):
    counts = np.zeros(VOCAB, dtype=np.int64)
    history = []
    for lo, hi in zip(STAGES[:-1], STAGES[1:], strict=True):
        batch = schedule[lo:hi]
        drawn = batch[:, :, 1][batch[:, :, 0] == -1]
        step_counts = counts_for(raw, starts[drawn].ravel(), deadline)
        counts += step_counts
        history.append(dict(start=lo + 1, stop=hi, draws=int(step_counts.sum()), counts=step_counts,
                            cumulative_validation=val_thresholds(counts, heldout)))
    draw, unique = document_counts(starts, ends)
    return history, counts, unique, document_summary(draw, unique, lengths)


def verify(deadline):
    assignment = prep.read_json(FULL)
    chosen = assignment["inputs"]
    manifest = source.read_pinned(training.MANIFEST, chosen["original_manifest_sha256"])
    starts = source.read_array(training.MANIFEST.with_name("raw_starts.npy"), manifest["raw_starts_sha256"])
    alternative = source.read_array(training.WINDOWS / "raw_starts.npy", chosen["stored_npy_sha256"])
    schedule = source.read_array(training.MANIFEST.with_name("schedule.npy"), manifest["schedule_sha256"])
    observed = schedule[:, :, 1][schedule[:, :, 0] == -1]
    learning = prep.read_json(WSD)
    if (manifest["steps"] != STAGES[-1] or manifest["warmup"] != STAGES[1]
            or learning["first_wsd_decay_update"] != STAGES[-2] + 1 or starts.shape != alternative.shape
            or not np.array_equal(np.sort(observed), np.arange(len(starts)))
            or np.any(np.diff(np.sort(alternative.ravel())) <= WIDTH)
            or sha256(alternative.tobytes()).hexdigest().upper() != chosen["raw_positions_sha256"]):
        raise ValueError("both complete schedules must match the admitted raw address geometry")
    readback = prep.read_json(READBACK)
    frozen = source.read_pinned(VAL, readback["profile_sha256"])
    if (frozen["index_sha256"] != chosen["document_index_sha256"]
            or frozen["frame_sha256"] != readback["window_sha256"]
            or prep.sha(Path(validation.__file__)) != frozen["source_sha256"]):
        raise ValueError("the original VAL and both training arms must use the same release")
    index = validation.pair.load_index(Path(frozen["index_profile"]), frozen["index_sha256"])
    train = index["splits"]["train"]
    raw_path = prep.CACHE / "train.bin"
    stamp = training.native.file_stamp(raw_path)
    checked_raw = validation.pair.documents.pin(raw_path)
    if (Path(train["binary"]["path"]) != raw_path or manifest["cache"]["files"]["train.bin"]
            != {key: train["binary"][key] for key in ("bytes", "sha256")}
            or checked_raw != train["binary"]):
        raise ValueError("the authorized train cache differs from the admitted document index")
    raw = np.memmap(raw_path, mode="r", dtype="<u2")
    ends = source.read_array(Path(train["index"]["path"]), train["index"]["sha256"]).astype(np.int64)
    if (len(ends) != train["documents"] or ends[-1] + 1 != len(raw)
            or (np.diff(ends) <= 0).any()):
        raise ValueError("the train document boundaries do not close")
    lengths = np.diff(np.r_[0, ends + 1])
    frames = validation.validation(index)
    target_counts = np.zeros(VOCAB, dtype=np.int64)
    for tokens, docs in frames:
        actual = tokens[:, 1:][docs[:, :-1] == docs[:, 1:]]
        target_counts += np.bincount(actual.numpy(), minlength=VOCAB)
    if (validation.frame_sha(frames) != frozen["frame_sha256"]
            or target_counts.sum() != frozen["validation_targets"]):
        raise ValueError("the targets must match the frozen document-isolated evaluation")

    original, control, old_positions, old_docs = phases(raw, schedule, starts, ends, target_counts, lengths, deadline)
    treatment, candidate, new_positions, new_docs = phases(
        raw, schedule, alternative, ends, target_counts, lengths, deadline)
    published = assignment["coverage"][-1]
    if (control.sum() != candidate.sum() or control.sum() != published["raw_draws"]
            or old_docs["unique_target_positions"] != published["original_unique"]
            or new_docs["unique_target_positions"] != published["nonoverlap_unique"]):
        raise ValueError("the audit differs from the frozen position accounting")
    phase_delta = []
    for a, b in zip(original, treatment, strict=True):
        if a["draws"] != b["draws"]:
            raise ValueError("per-phase exposure denominators must agree")
        delta = (np.abs(a.pop("counts") - b.pop("counts")).sum() / (2 * a["draws"]))
        phase_delta.append(dict(total_variation=float(delta), baseline=a, nonoverlap=b))
    masks = dict(all_valid=np.arange(VOCAB))
    masks.update({name: ids for name, ids in frozen["groups"].items() if int(target_counts[ids].sum()) > 0})
    by_group = {}
    for name, ids in masks.items():
        weight = target_counts[ids]
        a, b = control[ids], candidate[ids]
        by_group[name] = dict(targets=int(weight.sum()), baseline=val_thresholds(a, weight),
                              nonoverlap=val_thresholds(b, weight), more_draws=int(weight[b > a].sum()),
                              fewer_draws=int(weight[b < a].sum()))
    if training.native.file_stamp(raw_path) != stamp:
        raise ValueError("the approved raw file changed during the audit")
    return dict(status="MATCHED_RAW_DOCUMENT_AND_VOCAB_EXPOSURE", source_sha256=prep.sha(Path(__file__)),
                full_schedule_sha256=prep.sha(FULL), prior_lexical_sha256=prep.sha(LEXICAL),
                validation_profile_sha256=prep.sha(VAL), raw_sha256=checked_raw["sha256"],
                source_documents=len(ends), counts_baseline=old_docs, counts_nonoverlap=new_docs,
                shared_documents=int(np.count_nonzero((old_positions > 0) & (new_positions > 0))),
                new_documents=int(np.count_nonzero((old_positions == 0) & (new_positions > 0))),
                omitted_documents=int(np.count_nonzero((old_positions > 0) & (new_positions == 0))),
                distinct_ids=[int(np.count_nonzero(counts)) for counts in (control, candidate)],
                vocabulary_total_variation=float(np.abs(control - candidate).sum() / (2 * control.sum())),
                phases=phase_delta, heldout=by_group)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--stop-by", required=True, type=datetime.fromisoformat)
    args = parser.parse_args()
    if (os.environ.get("CUDA_VISIBLE_DEVICES") != "" or args.stop_by.tzinfo is None
            or args.stop_by > training.STOP):
        parser.error("the CPU device mask and the authorized time are required")
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    started = perf_counter()
    result = verify(args.stop_by)
    result["elapsed_seconds"] = perf_counter() - started
    training.native.publish(args.output, result)
    print(result["status"], result["counts_baseline"], result["counts_nonoverlap"], flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
