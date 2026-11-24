"""Read owned P109C v2 saves and track the same DEV questions during training."""

import argparse
from collections import Counter
from datetime import datetime
import hashlib
import json
import math
import os
from pathlib import Path
import time

import torch
from torch.nn.attention import SDPBackend, sdpa_kernel

from scripts import eval_p109c_completed as evaluation
from scripts import p106b_final_holdout as holdout
from scripts import run_p109c_scratch_mixed as mixed
from scripts.eval_p109b_first_use import DecodeSuffix
from scripts.interactive_research_infer import answer_from_tokens, prompt_messages
from tinylm.chat.serialize import serialize
from tinylm.config import TMTConfig
from tinylm.infer.generate import sample
from tinylm.model import TiedMLPTransformer
from tinylm.train import context_training_state, trainer


STEPS = (64, 128, 768, 1536, 2240)


def frozen_questions():
    _, contract = evaluation.final200_inputs()
    cases = evaluation.read_json(evaluation.FINAL200 / "dev.json")
    if holdout.digest(cases) != contract["dev_sha256"] or len(cases) != 20:
        raise ValueError("the frozen DEV-only cohort differs")
    return cases, contract["dev_sha256"]


def load_saved_body(path, manifest_sha, first, last):
    with path.open("rb") as stream:
        state = torch.load(stream, weights_only=True, map_location="cpu")
        if state["step"] < first:
            return None
        if state["step"] >= last:
            return state["step"], None, None
        stream.seek(0)
        digest = hashlib.sha256()
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    context = state[trainer.CONTEXT_STATE_KEY]
    recipe = context["binding"]["recipe"]["p109c_mixed_v2"]
    step = state["step"]
    if (state["tokenizer_sha256"].upper() != evaluation.TOKENIZER_SHA
            or recipe["manifest_sha256"] != manifest_sha
            or context["payload_sha256"] != context_training_state._payload_sha(context)
            or context["cursor"]["cursor"]["optimizer_updates"] != step
            or context["control"]["n_skip"] != 0):
        raise ValueError("the saved native optimizer and input contract disagree")
    cfg = TMTConfig(**state["cfg"])
    cfg.infer_repeat = 2.0
    model = TiedMLPTransformer(cfg).eval().requires_grad_(False)
    weights = {name: tensor for name, tensor in state["model"].items() if not name.startswith("decimal_head.")}
    model.load_state_dict(weights, strict=True)
    model.set_anneal(1.)
    model.freeze_quant()
    if len(model.visit_schedule()) != 28 or cfg.max_seq_len != mixed.prep.WIDTH:
        raise ValueError("the saved body is outside the fixed P109C inference route")
    return step, digest.hexdigest().upper(), model


def inspect(model, tokenizer, cases, check):
    counts = {layout: {language: Counter() for language in ("ko", "en")}
              for layout in ("chatml", "plain_qa")}
    rows = []
    with torch.inference_mode(), sdpa_kernel(SDPBackend.MATH):
        for case in cases:
            question = case["prompt"]
            ko = case["language"] == "ko"
            prompts = {
                "chatml": serialize({"messages": prompt_messages(question)}, "chatml", add_generation_prompt=True),
                "plain_qa": f"질문: {question}\n답:" if ko else f"Question: {question}\nAnswer:",
            }
            for layout, prompt in prompts.items():
                check()
                prompt_ids = tokenizer.encode(prompt).ids
                if len(prompt_ids) + holdout.MAX_NEW > model.cfg.max_seq_len:
                    raise ValueError("the frozen development request exceeds the native context")
                capture = DecodeSuffix(tokenizer, prompt_ids)
                _, meta = sample(model, model.cfg, capture, prompt, max_new=holdout.MAX_NEW, temperature=0.,
                                 top_k=1, device="cpu", eos_id=2, logits_last_only=True,
                                 return_metadata=True, stop_token_sequences=[[4]])
                answer, meta = answer_from_tokens(tokenizer, prompt_ids, prompt_ids + capture.ids, meta,
                                                  holdout.MAX_NEW)
                match = holdout.reference_match(answer, case)
                count = counts[layout][case["language"]]
                count.update(rows=1, content=int(bool(answer.strip())), first_eot=int(capture.ids[:1] == [4]),
                             first_eos=int(capture.ids[:1] == [2]), reference_rows=int(match is not None),
                             reference_match=int(match is True), ends=int(meta["finish_reason"] in ("EOS", "STOP_SEQUENCE")))
                rows.append(dict(id=case["id"], language=case["language"], layout=layout, prompt=prompt,
                                 answer=answer, reference_match=match, metadata=meta))
    return counts, rows


def read_progress(args, record, cases, dev_sha, tokenizer):
    cutoff = args.stop_by.timestamp()
    manifest_sha = mixed.native.digest(args.manifest_sha256)
    audit = []

    def check():
        if time.time() >= cutoff:
            raise TimeoutError("the authorized development check window elapsed")

    header = args.training / "input.json"
    terminal = args.training / "supervisor.json"
    while not header.is_file() and not terminal.is_file() and time.time() < cutoff:
        time.sleep(min(15., max(0., cutoff - time.time())))
    if not header.is_file():
        return audit
    source = evaluation.read_json(header)
    end = source["steps"]
    if source["manifest_sha256"] != manifest_sha or end <= STEPS[-1]:
        raise ValueError("the owned training manifest or schedule differs")
    display = f"{math.ceil(end * mixed.prep.ACCUM * mixed.MICRO_TOKENS / 1e6)}M"
    checkpoint = args.training / "ckpt" / f"{mixed.native.PRESET}_ko-en_{display}_{mixed.TAG}.pt"

    for first, last in zip(STEPS, (*STEPS[1:], end), strict=True):
        saved = None
        seen = None
        while time.time() < cutoff:
            if checkpoint.is_file():
                if checkpoint.is_symlink():
                    raise ValueError("the owned checkpoint path may not be a symlink")
                stamp = mixed.native.file_stamp(checkpoint)
                if stamp != seen:
                    saved = load_saved_body(checkpoint, manifest_sha, first, last)
                    if saved is not None:
                        break
                    seen = stamp
            if terminal.exists():
                break
            time.sleep(min(15., max(0., cutoff - time.time())))
        else:
            break
        if saved is None:
            break
        step, sha, model = saved
        if model is None:
            audit.append(dict(first=first, last=last, status="SAVE_WINDOW_PASSED", observed_step=step))
            continue
        counts, rows = inspect(model, tokenizer, cases, check)
        result = dict(first=first, last=last, step=step, status="COMPLETE", checkpoint_sha256=sha,
                      dev_sha256=dev_sha, precision="CPU_FP32_MATH", scores=counts)
        mixed.native.publish(record / f"step_{step}.json", dict(result, rows=rows))
        audit.append(result)
        print("P109C_DEV_CHECK", step, json.dumps(counts), flush=True)
    return audit


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--training", type=Path, required=True)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--record", type=Path, required=True)
    parser.add_argument("--stop-by", type=datetime.fromisoformat, required=True)
    args = parser.parse_args()
    if os.environ.get("CUDA_VISIBLE_DEVICES") != "" or args.stop_by.tzinfo is None:
        parser.error("the development samples require CPU-only mode and a timezone-aware cutoff")
    args.training = args.training.absolute()
    args.record = args.record.absolute()
    if (args.training.parent != args.record.parent or args.training.parent != mixed.prep.EVIDENCE
            or args.training.is_symlink() or not args.training.name.startswith("p109c_scratch_mixed_v2_")):
        parser.error("the run and audit must use the owned P109C v2 evidence directory")
    cases, dev_sha = frozen_questions()
    tokenizer = evaluation.load_tokenizer()
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    args.record.mkdir(exist_ok=False)
    print("P109C_DEV_CHECK_WAIT", args.training, flush=True)
    audit = read_progress(args, args.record, cases, dev_sha, tokenizer)
    mixed.native.publish(args.record / "report.json", dict(dev_sha256=dev_sha, minimum_steps=STEPS,
                                                          windows=audit, training=str(args.training)))


if __name__ == "__main__":
    main()
