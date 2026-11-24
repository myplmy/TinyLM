"""Separate prompt wording and operand width at the same answer values."""

import argparse
from collections import Counter, defaultdict
from datetime import datetime
import json
import os
from pathlib import Path
import random
from time import perf_counter
from unittest.mock import patch

from scripts import eval_p109b_first_use as first
from scripts import eval_p109c_mixed_v2 as mixed
from scripts import interactive_research_infer as dialogue
from scripts import p106b_final_holdout as panel


original = mixed.original
TAG = "p109c_addition_matched_prompts_cpu_v1_20261124"
MAX_NEW = 24
SUMS = (101, 107, 109, 116, 121, 124, 126, 128, 138, 142, 146, 155, 161, 164, 171, 176)


def cases():
    official = panel.build("final") + panel.build("dev")
    holdout_prompts = {row["prompt"] for row in official}
    holdout_values = {row["reference"] for row in official if row["language"] == "en"
                      and row["category"] == "reasoning" and isinstance(row["reference"], str)}
    rng = random.Random(624171)
    rows = []
    for i, value in enumerate(SUMS):
        a = rng.randrange(max(10, value - 99), 99)
        small = rng.randrange(1, min(9, value - 100) + 1)
        for scope, left, right in (("two_plus_two", a, value - a), ("three_plus_one", value - small, small)):
            for form, question in (("calculate", f"Calculate {left}+{right}."),
                                   ("how_much", f"How much is {left}+{right}?")):
                text = question + " Reply with only one integer."
                rows.append(dict(id=f"addition_dev_{i:02d}_{scope}_{form}", pair=i, scope=scope, form=form,
                                 prompt=text, reference=str(value), operands=[left, right]))
    if (len({r["prompt"] for r in rows}) != len(rows) or any(r["prompt"] in holdout_prompts for r in rows)
            or any(r["reference"] in holdout_values for r in rows)):
        raise ValueError("the new development questions or values overlap the frozen comparison panel")
    return rows


def load_conditions(record, manifest_sha):
    source = original.read_json(original.regular_file(record / "input.json"))
    with patch.object(mixed.native, "STEPS", source["steps"]):
        checkpoint, digest = mixed.completed_v2(record, manifest_sha)
    proof = dict(tag=TAG, training_record=str(record), training_manifest_sha256=manifest_sha.upper(),
                 checkpoint=str(checkpoint), checkpoint_sha256=digest, step=source["steps"], max_new=MAX_NEW,
                 tokenizer_sha256=original.TOKENIZER_SHA, inference_precision="CPU_FP32_INFERENCE",
                 sources=mixed.pinned_sources(), rows=cases())
    path = Path(__file__).resolve()
    proof["sources"][str(path.relative_to(original.ROOT))] = original.core6.digest(path)
    return proof


def run(proof, deadline):
    import torch
    from torch.nn.attention import SDPBackend, sdpa_kernel
    from tinylm.chat.serialize import serialize
    from tinylm.infer.generate import sample

    if proof != load_conditions(Path(proof["training_record"]), proof["training_manifest_sha256"]):
        raise ValueError("the model, sources or authored development pairs changed")
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    start = perf_counter()
    checkpoint = Path(proof["checkpoint"])
    model = original.load_model(checkpoint, proof["step"], "cpu")
    tokenizer = original.load_tokenizer()
    rows, groups = [], defaultdict(Counter)
    original_stamp = mixed.native.file_stamp(checkpoint)
    with torch.inference_mode(), sdpa_kernel(SDPBackend.MATH):
        for case in proof["rows"]:
            if datetime.now(deadline.tzinfo) >= deadline:
                raise TimeoutError("the addition development diagnostic reached its cutoff")
            prompt = serialize({"messages": dialogue.prompt_messages(case["prompt"])}, "chatml", add_generation_prompt=True)
            ids = tokenizer.encode(prompt).ids
            complete = tokenizer.encode(prompt + case["reference"]).ids
            if complete[:len(ids)] != ids or len(complete) <= len(ids) or len(ids) + MAX_NEW > model.cfg.max_seq_len:
                raise ValueError("the answer boundary or context geometry changed")
            gold = complete[len(ids):]
            logits = model(torch.tensor([complete[:-1]], dtype=torch.long))[0, len(ids) - 1:]
            rows_of_interest = torch.arange(len(gold))
            gold_logits = logits[rows_of_interest, gold]
            ranks = (logits > gold_logits[:, None]).sum(-1) + 1
            nll = torch.logsumexp(logits, -1) - gold_logits
            capture = first.DecodeSuffix(tokenizer, ids)
            _, metadata = sample(model, model.cfg, capture, prompt, max_new=MAX_NEW, temperature=0., top_k=1,
                                 device="cpu", eos_id=2, use_cache=True, logits_last_only=True,
                                 return_metadata=True, stop_token_sequences=[[4]])
            answer, meta = dialogue.answer_from_tokens(tokenizer, ids, ids + capture.ids, metadata, MAX_NEW)
            exact = answer.strip() == case["reference"]
            finish = meta["finish_reason"]
            rank = int(ranks[0])
            rows.append(dict(case, answer=answer, exact=exact, finish=finish, gold_token_ids=gold,
                             gold_ranks=ranks.tolist(), gold_nll=nll.tolist()))
            groups[f"{case['scope']}/{case['form']}"].update(rows=1, exact=int(exact), top1=int(rank == 1),
                                                          stopped=int(finish in {"EOS", "STOP_SEQUENCE"}))
    if mixed.native.file_stamp(checkpoint) != original_stamp or original.core6.digest(checkpoint) != proof["checkpoint_sha256"]:
        raise ValueError("the original checkpoint changed during the paired diagnostic")
    return dict(status="MATCHED_ADDITION_DEV_CPU_COMPLETE", checkpoint_sha256=proof["checkpoint_sha256"],
                by_scope_and_form=dict(groups), rows=rows, seconds=perf_counter() - start)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    prepare = sub.add_parser("prepare")
    prepare.add_argument("--training-record", required=True, type=Path)
    prepare.add_argument("--training-manifest-sha256", required=True)
    prepare.add_argument("--profile", required=True, type=Path)
    execute = sub.add_parser("run")
    execute.add_argument("--profile", required=True, type=Path)
    execute.add_argument("--profile-sha256", required=True)
    execute.add_argument("--output", required=True, type=Path)
    execute.add_argument("--stop-by", required=True, type=datetime.fromisoformat)
    args = parser.parse_args()
    if args.action == "prepare":
        profile = load_conditions(args.training_record.resolve(strict=True), args.training_manifest_sha256)
        mixed.native.publish(args.profile.absolute(), profile)
        print(original.core6.digest(args.profile))
        return
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "" or args.stop_by.tzinfo is None:
        parser.error("a CPU-only device mask and a timezone-aware deadline are required")
    profile = json.loads(mixed.native.manifest_bytes(args.profile.absolute(), args.profile_sha256))
    result = run(profile, args.stop_by)
    mixed.native.publish(args.output.absolute(), dict(result, profile_sha256=args.profile_sha256.upper()))
    print(result["status"], result["by_scope_and_form"], flush=True)


if __name__ == "__main__":
    main()
