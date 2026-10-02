#!/usr/bin/env python3
"""P106B user-approved, write-once four-checkpoint generation-path audit.

Only --execute imports torch/loads a model. No training, teacher, downloads,
checkpoint/cache writes, general benchmark claim or semantic-quality admission.
"""
from __future__ import annotations
import argparse
import gc
import hashlib
import json
import math
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.p106b_education_followup import ARMS, score_answer
from scripts.p106b_repeat4_gate import PROBES
from scripts.p106b_gate_runtime import idle_before_gpu, wall_limit
from tinylm.chat.serialize import serialize

OUTPUT = ROOT / "test_result/evidence/101_P106B_Stage3sWa_generation_path_audit.json"
MAX_NEW = 160
HARD_WALL_SEC = 900
SUBJECTS = (
    ("b_parent", "b", ARMS["b"]["parent"], ARMS["b"]["sha"], 2289),
    ("b_student", "b", "runs/ckpt/m100s10_ko-en_300M_p106b_s3k_contract_chat32_s1337.pt",
     "BAE1EA97141DEEAC80CB76A35C2DC53B5BAFEAA83535C5A5A157254B9EB95717", 2293),
    ("a_parent", "a", ARMS["a"]["parent"], ARMS["a"]["sha"], 2289),
    ("a_student", "a", "runs/ckpt/m100R1c_ko-en_300M_p106b_s3l_contract_a_s1337.pt",
     "50189D67742E6AA1D536030279A9D3607DD009F05140DB7FB879EE39D16B9842", 2293),
)


def digest(path):
    if not path.is_file() or path.is_symlink():
        raise ValueError(f"exact regular input required: {path}")
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1048576), b""):
            result.update(chunk)
    return result.hexdigest().upper()


def prompt_for(question, kind):
    if kind == "qa":
        return "질문: " + question + "\n답: " if any("\uac00" <= c <= "\ud7a3" for c in question) else "Question: " + question + "\nAnswer: "
    if kind != "chatml":
        raise ValueError("only paired qa/chatml prompts are allowed")
    return serialize({"messages": [{"role": "user", "content": question}]},
                     "chatml", add_generation_prompt=True)


class CaptureTokenizer:
    """Observe ids passed to decode without changing the shared sampler."""
    def __init__(self, original):
        self.original, self.last_ids = original, None
    def __getattr__(self, name):
        return getattr(self.original, name)
    def decode(self, ids, *args, **kwargs):
        self.last_ids = list(ids)
        return self.original.decode(ids, *args, **kwargs)


def extracted(prompt, tokenizer, decoded, full_ids):
    prefix_ids = list(tokenizer.encode(prompt).ids)
    if full_ids is None or list(full_ids[:len(prefix_ids)]) != prefix_ids:
        raise ValueError("sampler did not preserve prompt token ids")
    tail = list(full_ids[len(prefix_ids):])
    prefix = tokenizer.decode(prefix_ids)
    aligned = decoded.startswith(prefix)
    legacy = decoded[len(prefix):] if aligned else None
    answer = tokenizer.decode(tail)
    return {"prefix_text_matches": aligned,
            "legacy_answer": legacy,
            "token_tail_answer": answer,
            "legacy_equals_token_tail": legacy == answer if aligned else False,
            "raw_answer_with_special_tokens": tokenizer.decode(tail, skip_special_tokens=False),
            "generated_token_ids": tail}


def check():
    if OUTPUT.exists() or OUTPUT.is_symlink():
        raise FileExistsError(f"new audit output already exists: {OUTPUT}")
    files = []
    for name, arm, path, expected, step in SUBJECTS:
        actual = digest(ROOT / path)
        if actual != expected:
            raise ValueError(f"{name}: checkpoint SHA differs")
        files.append({"subject": name, "path": path, "sha256": actual, "expected_step": step})
    for arm, spec in ARMS.items():
        actual = digest(ROOT / spec["tokenizer"])
        if actual != spec["tok_sha"]:
            raise ValueError(f"{arm}: tokenizer SHA differs")
        files.append({"arm": arm, "path": spec["tokenizer"], "sha256": actual})
    return {"schema": "P106B_GENERATION_PATH_PREFLIGHT_V1", "files": files,
            "checkpoint_count": 4, "questions": len(PROBES), "prompt_kinds": ["qa", "chatml"],
            "cache_modes": [True, False], "expected_cases": 4 * len(PROBES) * 4,
            "max_new": MAX_NEW, "temperature": 0, "top_k": 1,
            "hard_wall_sec": HARD_WALL_SEC, "training_updates": 0,
            "output": OUTPUT.relative_to(ROOT).as_posix(),
            "source_sha256": digest(Path(__file__)),
            "sampler_sha256": digest(ROOT / "tinylm/infer/generate.py"),
            "claim": "diagnostic only; BF16 cache differences alone do not establish a logic bug"}


def parameter_delta(arm):
    """CPU state-tensor comparison, not a training update or checkpoint rewrite."""
    import torch
    from tinylm.infer.generate import _strip
    parent = next(s for s in SUBJECTS if s[0] == arm + "_parent")
    child = next(s for s in SUBJECTS if s[0] == arm + "_student")
    before = _strip(torch.load(ROOT / parent[2], map_location="cpu", weights_only=True)["model"])
    after = _strip(torch.load(ROOT / child[2], map_location="cpu", weights_only=True)["model"])
    if set(before) != set(after):
        raise ValueError(f"{arm}: parent/child state keys differ")
    changed, total, square_sum, maximum = 0, 0, 0.0, 0.0
    for name in before:
        a, b = before[name], after[name]
        if a.shape != b.shape:
            raise ValueError(f"{arm}: tensor shape differs: {name}")
        if not torch.is_floating_point(a):
            continue
        total += a.numel()
        flat_a, flat_b = a.reshape(-1), b.reshape(-1)
        local = 0.0
        for start in range(0, a.numel(), 262144):
            delta = flat_b[start:start+262144].float() - flat_a[start:start+262144].float()
            if not bool(torch.isfinite(delta).all()):
                raise ValueError(f"{arm}: nonfinite state delta")
            local = max(local, float(delta.abs().max()) if delta.numel() else 0.0)
            square_sum += float(delta.double().square().sum())
        changed += int(local > 0)
        maximum = max(maximum, local)
    del before, after
    gc.collect()
    return {"arm": arm, "changed_float_state_tensors": changed, "floating_state_elements": total,
            "l2_delta": math.sqrt(square_sum), "max_absolute_delta": maximum,
            "scope": "floating state includes parameters/buffers; proves change, not learning quality"}


def execute(info):
    import torch
    from tokenizers import Tokenizer
    from tinylm.config import TMTConfig
    from tinylm.model import TiedMLPTransformer
    from tinylm.infer.generate import sample, _strip
    torch.set_num_threads(1)
    began, records = time.monotonic(), []
    report = {"schema": "P106B_GENERATION_PATH_AUDIT_V1", "status": "RUNNING",
              "input": info, "records": records, "parameter_deltas": [],
              "training_updates": 0, "semantic_truth": "NOT_RUN"}
    try:
        idle_before_gpu()
        with wall_limit(HARD_WALL_SEC):
            for arm in ("b", "a"):
                report["parameter_deltas"].append(parameter_delta(arm))
            for subject, arm, ckpt, expected, step in SUBJECTS:
                spec = ARMS[arm]
                state = torch.load(ROOT / ckpt, map_location="cpu", weights_only=True)
                cfg = TMTConfig(**state["cfg"])
                if state.get("step") != step or cfg.n_layers != spec["layers"] or cfg.tie_mlp != spec["tied"] or cfg.vocab_size != 32768:
                    raise ValueError(f"{subject}: geometry/step differs")
                tok = Tokenizer.from_file(str(ROOT / spec["tokenizer"]))
                base = TiedMLPTransformer(cfg).cuda()
                base.load_state_dict(_strip(state["model"]), strict=True)
                del state
                base.requires_grad_(False)
                base.set_anneal(1.0)
                base.eval()
                base.freeze_quant()
                torch.cuda.reset_peak_memory_stats()
                print("[SUBJECT_READY] " + json.dumps({"subject": subject, "step": step}), flush=True)
                for index, (ident, question) in enumerate(PROBES):
                    for kind in ("qa", "chatml"):
                        prompt = prompt_for(question, kind)
                        for cache in (True, False):
                            capture = CaptureTokenizer(tok)
                            torch.manual_seed(20261000 + index * 10 + 1)
                            torch.cuda.synchronize()
                            start = time.monotonic()
                            decoded, metadata = sample(base, cfg, capture, prompt,
                                max_new=MAX_NEW, temperature=0, top_k=1, device="cuda",
                                use_cache=cache, logits_last_only=True, return_metadata=True,
                                stop_token_sequences=[tok.encode("<|im_end|>").ids] if kind == "chatml" else None)
                            torch.cuda.synchronize()
                            result = extracted(prompt, tok, decoded, capture.last_ids)
                            record = {"subject": subject, "arm": arm, "id": ident, "question": question,
                                "prompt_kind": kind, "prompt": prompt, "use_cache": cache,
                                "decoded_full_text": decoded, **result, "generation": metadata,
                                "wall_sec": time.monotonic() - start}
                            rendered = result["token_tail_answer"].split("<|im_end|>", 1)[0]
                            record["rendered_answer"] = rendered
                            record["narrow_rubric_pass"] = score_answer(ident, rendered)
                            records.append(record)
                            print("[GENERATION_CASE] " + json.dumps(record, ensure_ascii=False), flush=True)
                print("[SUBJECT_DONE] " + json.dumps({"subject": subject,
                    "peak_reserved_mib": torch.cuda.max_memory_reserved() / 1048576}), flush=True)
                base.clear_quant()
                del base, tok, capture
                gc.collect()
                torch.cuda.empty_cache()
        report["status"] = "DIAGNOSTIC_COMPLETE"
        report["prefix_mismatches"] = sum(not r["prefix_text_matches"] for r in records)
        report["tail_decode_differences"] = sum(not r["legacy_equals_token_tail"] for r in records)
        pairs = []
        for offset in range(0, len(records), 2):
            on, off = records[offset:offset+2]
            assert (on["subject"], on["id"], on["prompt_kind"]) == (off["subject"], off["id"], off["prompt_kind"])
            pairs.append({"subject": on["subject"], "id": on["id"], "prompt_kind": on["prompt_kind"],
                          "token_ids_identical": on["generated_token_ids"] == off["generated_token_ids"],
                          "answers_identical": on["rendered_answer"] == off["rendered_answer"]})
        report["cache_pairs"], report["cache_token_mismatches"] = pairs, sum(not p["token_ids_identical"] for p in pairs)
        report["narrow_first_pass"] = {subject: {kind: sum(r["narrow_rubric_pass"] for r in records
            if r["subject"] == subject and r["prompt_kind"] == kind and r["use_cache"])
            for kind in ("qa", "chatml")} for subject, *_ in SUBJECTS}
        report["case_count"] = len(records)
        report["finish_reasons"] = {reason: sum(r["generation"]["finish_reason"] == reason for r in records)
                                    for reason in sorted({r["generation"]["finish_reason"] for r in records})}
        if len(records) != info["expected_cases"]:
            raise ValueError("incomplete generation panel")
        report["exit_code"] = 0
    except BaseException as exc:
        report.update(status="INCOMPLETE", exit_code=130 if isinstance(exc, KeyboardInterrupt) else 9,
                      failure=f"{type(exc).__name__}: {exc}", case_count=len(records))
        raise
    finally:
        report["whole_wall_sec"] = time.monotonic() - began
        with OUTPUT.open("x", encoding="utf-8") as stream:
            json.dump(report, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        print("[GENERATION_AUDIT] " + json.dumps({k: v for k, v in report.items()
              if k not in ("records", "cache_pairs", "input")}, ensure_ascii=False), flush=True)
    return report["exit_code"]


def self_test():
    from types import SimpleNamespace
    class Tokenizer:
        def encode(self, text):
            return SimpleNamespace(ids=[1])
        def decode(self, ids, **_kwargs):
            return "".join({1: "Q:", 5: "5"}[i] for i in ids)
    tok = Tokenizer()
    normal = extracted("Q:", tok, "Q:5", [1, 5])
    assert normal["prefix_text_matches"] and normal["token_tail_answer"] == "5"
    mismatch = extracted("Q:", tok, "changed-prefix-5", [1, 5])
    assert not mismatch["prefix_text_matches"] and mismatch["token_tail_answer"] == "5"
    try:
        extracted("Q:", tok, "wrong", [5])
    except ValueError:
        pass
    else:
        raise AssertionError("prompt-token mismatch accepted")
    assert "<|im_start|>" in prompt_for("2+3", "chatml")
    assert "<|im_start|>" not in prompt_for("2+3", "qa")
    assert len(SUBJECTS) * len(PROBES) * 4 == 128
    print("[PASS] CPU prompt/capture/extraction fixtures; model/GPU NOT_RUN")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--self-test", action="store_true")
    modes.add_argument("--check-only", action="store_true")
    modes.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    try:
        info = check()
        if args.check_only:
            print(json.dumps(info, ensure_ascii=False, sort_keys=True))
            return 0
        return execute(info)
    except Exception as exc:
        print(f"[FAIL] {type(exc).__name__}: {exc}", file=sys.stderr)
        return 9


if __name__ == "__main__":
    raise SystemExit(main())

