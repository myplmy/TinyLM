"""Check speaker selection in the official SODA development split using frozen P109C."""

import argparse
from collections import Counter, defaultdict
from datetime import datetime
from itertools import combinations
import math
import os
from pathlib import Path
import sysconfig
import time
from types import SimpleNamespace
from unittest.mock import patch

import torch
from torch.nn.attention import SDPBackend, sdpa_kernel

from scripts import audit_p106b_soda_quote_release as release
from scripts import eval_p109b_first_use as first_use
from scripts import eval_p109c_mixed_v2 as evaluation
from scripts.p106b_official_lm_adapter import create_adapter


source, quote, original = release.source, release.quote, evaluation.original
PER_GAP = 16
PRESENTATIONS = ("names", "letter_codes", "letter_codes_swapped")


def inputs(directory, tokenizer, check):
    prior, _ = quote.read(quote.SOURCE_MAP)
    excluded = {row["original_index"] for row in prior["rows"] if "original_index" in row}
    grouped = defaultdict(list)
    seen = set()
    count, checksum = source.RELEASE["valid"]
    with source.pinned_rows(directory / "valid.parquet", count, checksum) as rows:
        for index, row in enumerate(rows):
            if index % 2048 == 0:
                check()
            root = row["original_index"]
            if row["split"] != "valid":
                raise ValueError("the frozen source unexpectedly left its development partition")
            key = source.hash_json([source.REVISION, root, "speaker-code-development"])[:12]
            if int(key, 16) % 97 or root in excluded:
                continue
            turns = release.turns(row)
            if not turns or len({name for name, _ in turns}) != 2:
                continue
            identity = release.spoken_key(turns)
            if identity in seen or any("<|im_" in utterance for _, utterance in turns):
                continue
            occurrences = Counter(quote.quote_key(utterance) for _, utterance in turns)
            choices = defaultdict(list)
            for (i, (a, u)), (j, (b, v)) in combinations(enumerate(turns), 2):
                gap = min(j - i, 3)
                if gap <= 0 or len(grouped[gap]) >= PER_GAP or a.casefold() == b.casefold():
                    continue
                if occurrences[quote.quote_key(u)] == occurrences[quote.quote_key(v)] == 1 and quote.questions(f"{a}: {u}\n\n{b}: {v}"):
                    choices[gap].append((i, j))
            if not choices:
                continue
            gap = min(choices, key=lambda value: (len(grouped[value]), value))
            pair = choices[gap][int(key, 16) % len(choices[gap])]
            group = source.hash_json([source.REPO, source.REVISION, root])
            item = (group, gap, turns, pair)
            prompts = requests(item)
            if max(len(tokenizer.encode(r["prompt"]).ids) for r in prompts) > first_use.INPUT:
                continue
            seen.add(identity)
            excluded.add(root)
            grouped[gap].append(item)
            if len(grouped) == 3 and all(len(grouped[g]) == PER_GAP for g in (1, 2, 3)):
                return [item for key in (1, 2, 3) for item in grouped[key]]
    raise ValueError("the approved source did not fill the predefined distance groups")


def requests(item):
    root, gap, turns, pair = item
    names = tuple(turns[i][0] for i in pair)
    rows = []
    for presentation, labels in zip(PRESENTATIONS, (names, ("A", "B"), ("B", "A")), strict=True):
        rendered = "\n\n".join(f"{labels[names.index(name)]}: {utterance}" for name, utterance in turns)
        for index, turn in enumerate(pair):
            question = f'Who says the exact line “{turns[turn][1]}”? Reply with the speaker label only.'
            prompt = first_use.dialog(f"Use the following fictional dialogue as the only source.\n\n{rendered}\n\n{question}")
            rows.append(dict(root=root, turn_gap=gap, presentation=presentation, label_index=index,
                             allowed=list(labels), prompt=prompt))
    return rows


def score(model, tokenizer, model_sha, items, check):
    runtime = dict(model=model, cfg=model.cfg, torch=torch, tokenizer=tokenizer,
                   precision="FP32_MATH", checkpoint_sha256=model_sha, tokenizer_sha256=original.TOKENIZER_SHA)
    adapter = create_adapter(runtime, runtime_root=Path(sysconfig.get_paths()["purelib"]), batch_size=8)
    output = []
    try:
        for index, item in enumerate(items, 1):
            check()
            rows = requests(item)
            options = [SimpleNamespace(args=(row["prompt"], label)) for row in rows for label in row["allowed"]]
            with torch.inference_mode(), sdpa_kernel(SDPBackend.MATH):
                scores = adapter.loglikelihood(options, disable_tqdm=True)
            for i, row in enumerate(rows):
                lengths = [len(adapter._encode_pair(*option.args)[1]) for option in options[2*i:2*i+2]]
                raw = [entry[0] for entry in scores[2*i:2*i+2]]
                if not all(lengths) or not all(map(math.isfinite, raw)):
                    raise ValueError("an exact answer candidate was empty or nonfinite")
                balanced = [value / length for value, length in zip(raw, lengths, strict=True)]
                gap = balanced[row["label_index"]] - balanced[1-row["label_index"]]
                output.append(dict(row, raw_logp=raw, candidate_tokens=lengths,
                                   normalized_correct=gap > 0, margin=gap))
            if index % 8 == 0:
                print("SODA_HELDOUT_SPEAKER_CODE_PROGRESS", index, flush=True)
        if adapter.core.diagnostics()["context_truncated_requests"]:
            raise ValueError("the comparison must keep the complete source dialogue")
    finally:
        adapter.close()
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for field in ("original-dir", "training", "record"):
        parser.add_argument("--" + field, type=Path, required=True)
    parser.add_argument("--training-manifest-sha256", required=True)
    parser.add_argument("--stop-by", type=datetime.fromisoformat, required=True)
    args = parser.parse_args()
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "" or args.stop_by.tzinfo is None or args.record.exists():
        parser.error("require explicit CPU-only execution, a cutoff and a fresh evidence directory")
    torch.set_num_threads(3)
    torch.set_num_interop_threads(1)

    def check():
        if time.time() >= args.stop_by.timestamp():
            raise TimeoutError("the SODA development readback reached its approved cutoff")

    start = time.monotonic()
    tokenizer = original.load_tokenizer()
    items = inputs(args.original_dir, tokenizer, check)
    training = args.training.absolute()
    end = original.read_json(training / "input.json")["steps"]
    with patch.object(evaluation.native, "STEPS", end):
        path, checksum = evaluation.completed_v2(training, args.training_manifest_sha256)
    output = score(original.load_model(path, end, "cpu"), tokenizer, checksum, items, check)
    groups = defaultdict(list)
    for row in output:
        if row["presentation"] != "names":
            groups[row["root"]].append(row["normalized_correct"])
    if len(groups) != len(items) or any(len(rows) != 4 for rows in groups.values()):
        raise ValueError("every dialogue needs two questions and both letter assignments")
    counts = {}
    for mode in PRESENTATIONS:
        rows = [row for row in output if row["presentation"] == mode]
        counts[mode] = {gap: dict(rows=sum(row["turn_gap"] == gap for row in rows),
                                 correct=sum(row["turn_gap"] == gap and row["normalized_correct"] for row in rows))
                        for gap in (1, 2, 3)}
    if original.core6.digest(path) != checksum:
        raise ValueError("the source model changed during the development readback")
    args.record.mkdir(exist_ok=False)
    original.training.publish(args.record / "report.json", dict(status="SODA_DEVELOPMENT_SPEAKER_CODE_READBACK_COMPLETE",
        official_source_revision=source.REVISION, split="valid", source_sha256=source.RELEASE["valid"][1],
        model_sha256=checksum, score="CPU_FP32_LENGTH_NORMALIZED_TWO_CHOICE", count_gaps=counts,
        code_sha256=original.core6.digest(Path(__file__)),
        roots=len(items), all_four_codes_correct=sum(all(values) for values in groups.values()),
        teacher_calls=0, student_updates=0, seconds=time.monotonic()-start, rows=output))
    print(counts, sum(all(values) for values in groups.values()), flush=True)


if __name__ == "__main__":
    main()
