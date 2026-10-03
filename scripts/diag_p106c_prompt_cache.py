#!/usr/bin/env python3
"""Bounded P106C A: frozen parent/two endpoints, prompt order and cache attribution.

No training or checkpoint writes. Only --execute loads models. Original v1
reports/shards are SHA-locked. The reused test is POSTHOC, not a new sealed test.
"""
from __future__ import annotations
import argparse
from collections import Counter
import gc
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.p106b_education_followup import ARMS
from scripts.p106b_shards import verify
from scripts.diag_p106b_generation_path_audit import CaptureTokenizer, digest, extracted
from scripts.diag_p106b_cache_fp32_recheck import FP32Forward
from scripts.p106b_gate_runtime import idle_before_gpu, wall_limit
from scripts.p106c_data import canonical, data_hash

ORIGINAL = ROOT / "HF/sft_ready/p106c_replay_v1"
OUTPUT = ROOT / "test_result/evidence/102_P106C_Stage5Wa_prompt_cache_attribution.json"
POLICY_SHA = "FE8C953F65934822957929905593DFE6D076F7F27AC302DFC98A0EAC9D306984"
PREPARE_SHA = "461DE0CE71A75E103F34D3098BC7D3D0E0F91C795DBD8DC3779F1CDCA91DC297"
SUBJECTS = (
    ("parent", ARMS["b"]["parent"], ARMS["b"]["sha"]),
    ("baseline", "HF/sft_ready/p106c_replay_v1/policy/baseline_student.pt", "2E2187E72AE1F0505DF22CDA93C9C7DB92AF02D94F001B14CAD8230EB6D4A169"),
    ("selected", "HF/sft_ready/p106c_replay_v1/policy/selected_student.pt", "D00F902BBA0F2644A89D00E953776FDE7D56A034E85B990012869BC5C187AD9E"),
)
MAX_WALL_SEC, MAX_NEW = 900, 32


def locked_report(relative, sha):
    path = ORIGINAL / relative
    if digest(path) != sha:
        raise ValueError(f"frozen report changed: {relative}")
    return json.loads(path.read_text(encoding="utf-8"))


def frozen_role(role):
    source = locked_report("prepare/report.json", PREPARE_SHA)
    directory = ORIGINAL / "prepare"
    path = directory / (role + "_shards_manifest.json")
    digest(path)
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest["concat_sha256"] != source["datasets"][role]["sha256"]:
        raise ValueError("dataset role concat differs")
    verify(directory, manifest)
    return [json.loads(line) for s in manifest["shards"]
            for line in (directory/s["path"]).read_text(encoding="utf-8").splitlines()]


def prompt_grid(source):
    if len(source) < 16:
        raise ValueError("eight complete source pairs required")
    rows = []
    for pair in range(8):
        left, right = source[2*pair:2*pair+2]
        if left["pair_id"] != right["pair_id"] or left["gold"] == right["gold"]:
            raise ValueError("paired facts must share context and differ in target")
        a, b = left["pair_id"]+"a", left["pair_id"]+"b"
        values = {a: left["gold"], b: right["gold"]}
        for family in ("table", "box"):
            for reverse in (False, True):
                first, second = (b, a) if reverse else (a, b)
                for target in (a, b):
                    ko = left["language"] == "ko"
                    if family == "table":
                        q = (f"표: {first}={values[first]}, {second}={values[second]}. {target}의 색은? 색 이름 한 단어만 답하세요." if ko else
                             f"Table: {first}={values[first]}, {second}={values[second]}. What color is {target}? Answer with the color only.")
                    else:
                        q = (f"상자 {first}는 {values[first]}이고 상자 {second}는 {values[second]}이다. {target} 상자의 색만 적으세요." if ko else
                             f"Box {first} is {values[first]} and box {second} is {values[second]}. Write only the color of box {target}.")
                    other = b if target == a else a
                    rows.append({"id": f"pair{pair}_{family}_{int(reverse)}_{target[-1]}",
                                 "pair_id": left["pair_id"], "family": family, "reversed": reverse,
                                 "target": target, "language": left["language"], "question": q,
                                 "gold": values[target], "other": values[other], "facts": values,
                                 "role": "POSTHOC_DIAGNOSTIC", "repeat_expected": False, "task": "context_lookup"})
    return rows


def check():
    if OUTPUT.exists() or OUTPUT.is_symlink():
        raise FileExistsError("preserve A output; rerun needs new stage/version")
    locked_report("policy/report.json", POLICY_SHA)
    if digest(ROOT/ARMS["b"]["tokenizer"]) != ARMS["b"]["tok_sha"]:
        raise ValueError("chat32 tokenizer differs")
    for name, file, expected in SUBJECTS:
        if digest(ROOT/file) != expected:
            raise ValueError(f"checkpoint differs: {name}")
    grid = prompt_grid(frozen_role("sealed"))
    return grid, {"subjects": SUBJECTS, "grid_sha256": data_hash(grid), "prompts_per_subject": 64,
                  "expected_cases": 384, "max_new": MAX_NEW, "max_wall_sec": MAX_WALL_SEC,
                  "policy_sha256": POLICY_SHA, "prepare_sha256": PREPARE_SHA,
                  "script_sha256": digest(Path(__file__)), "training_updates": 0,
                  "claim": "POSTHOC reused eight fact pairs; not new sealed generalization"}


def question_prompt(row):
    from tinylm.chat.serialize import serialize
    return serialize({"messages": [{"role": "user", "content": row["question"]}]},
                     "chatml", add_generation_prompt=True)


def encode_prefix(row, tokenizer):
    from scripts.train_sft_p090 import encode_records
    encoded = encode_records([canonical(row)], tokenizer, 256, 32768)[0]
    prefix = tokenizer.encode(question_prompt(row)).ids
    first = next(i for i, y in enumerate(encoded[1]) if y != -100)
    if encoded[0][:len(prefix)] != prefix or first != len(prefix)-1:
        raise ValueError("training/generation prefix or first target shift differs")
    return encoded


def likelihood(base, tokenizer, row):
    import torch
    import torch.nn.functional as F
    scores = []
    detail = {}
    end = tokenizer.token_to_id("<|im_end|>")
    for gold in (row["gold"], row["other"]):
        x, y, n = encode_prefix(dict(row, gold=gold), tokenizer)
        with torch.no_grad(), torch.autocast("cuda", dtype=torch.bfloat16):
            logits = base(torch.tensor([x], device="cuda"))[0].float()
        if not torch.isfinite(logits).all():
            raise ValueError("nonfinite evaluation logits")
        ix = [i for i, v in enumerate(y) if v != -100 and v != end]
        lp = F.log_softmax(logits, dim=-1)
        scores.append(float(torch.stack([lp[i, y[i]] for i in ix]).mean()))
        if gold == row["gold"]:
            supervised = [i for i,v in enumerate(y) if v != -100]
            detail = {"gold_nll": float(F.cross_entropy(logits, torch.tensor(y, device="cuda"), ignore_index=-100)),
                      "all_gold_targets_argmax": all(int(logits[i].argmax())==y[i] for i in supervised),
                      "targets": n}
    return {**detail, "gold_minus_other_margin": scores[0]-scores[1]}


def generate_one(model, cfg, tokenizer, row, cache):
    from tinylm.infer.generate import sample
    capture = CaptureTokenizer(tokenizer)
    prompt = question_prompt(row)
    decoded, meta = sample(model, cfg, capture, prompt, max_new=MAX_NEW, temperature=0, top_k=1,
        device="cuda", use_cache=cache, logits_last_only=True, return_metadata=True,
        stop_token_sequences=[[tokenizer.token_to_id("<|im_end|>")]])
    out = extracted(prompt, tokenizer, decoded, capture.last_ids)
    if not out["prefix_text_matches"] or not out["legacy_equals_token_tail"]:
        raise ValueError("token/text answer extraction differs")
    answer = out["token_tail_answer"].split("<|im_end|>", 1)[0].strip()
    return {"answer": answer, "generated_token_ids": out["generated_token_ids"], "generation": meta,
            "exact_and_stopped": answer==row["gold"] and meta["finish_reason"] in ("STOP_SEQUENCE", "EOS")}


def execute(grid, info):
    import torch
    from tokenizers import Tokenizer
    from tinylm.config import TMTConfig
    from tinylm.model import TiedMLPTransformer
    from tinylm.infer.generate import _strip
    torch.set_num_threads(1)
    torch.set_float32_matmul_precision("highest")
    torch.backends.cuda.matmul.allow_tf32 = False
    began = time.perf_counter()
    report = {"schema": "P106C_PROMPT_CACHE_A_V1", "status": "RUNNING", "input": info,
              "records": [], "fp32_rechecks": [], "training_updates": 0, "checkpoint_writes": 0,
              "precision": "BF16 autocast; TF32 off throughout; FP32 only for divergent cache pairs"}
    try:
        idle_before_gpu()
        with wall_limit(MAX_WALL_SEC), torch.no_grad():
            for subject, file, _sha in SUBJECTS:
                state = torch.load(ROOT/file, map_location="cpu", weights_only=True)
                cfg = TMTConfig(**state["cfg"])
                if cfg.n_layers != 14 or cfg.tie_mlp or cfg.vocab_size != 32768:
                    raise ValueError("subject geometry differs from B lineage")
                if subject != "parent" and (state.get("sft", {}).get("updates") != 128 or state["sft"]["arm"] != subject):
                    raise ValueError("child endpoint identity differs")
                tok = Tokenizer.from_file(str(ROOT/ARMS["b"]["tokenizer"]))
                base = TiedMLPTransformer(cfg).cuda()
                base.load_state_dict(_strip(state["model"]), strict=True)
                del state
                base.requires_grad_(False); base.set_anneal(1); base.eval(); base.freeze_quant()
                torch.cuda.reset_peak_memory_stats()
                mismatches = []
                counts = Counter()
                for row in grid:
                    score = likelihood(base, tok, row)
                    outputs = [generate_one(base, cfg, tok, row, cache) for cache in (True, False)]
                    equal = outputs[0]["generated_token_ids"] == outputs[1]["generated_token_ids"]
                    if not equal:
                        mismatches.append(row)
                    entry = {"subject": subject, **row, "likelihood": score,
                             "cache_on": outputs[0], "cache_off": outputs[1], "bf16_cache_identical": equal}
                    report["records"].append(entry)
                    key = row["family"]+":"+str(row["reversed"])+":"+row["language"]
                    counts[key+":n"] += 1; counts[key+":pass"] += outputs[0]["exact_and_stopped"]
                if mismatches:
                    base.clear_quant(); cfg.wq_dtype="fp32"; base.freeze_quant()
                    torch.set_float32_matmul_precision("highest"); torch.backends.cuda.matmul.allow_tf32=False
                    for row in mismatches:
                        outcomes = [generate_one(FP32Forward(base), cfg, tok, row, cache) for cache in (True, False)]
                        report["fp32_rechecks"].append({"subject": subject, "id": row["id"], "outcomes": outcomes,
                            "identical": outcomes[0]["generated_token_ids"] == outcomes[1]["generated_token_ids"]})
                print("[A_SUBJECT] "+json.dumps({"subject":subject,"counts":dict(counts),"bf16_cache_differences":len(mismatches),
                    "peak_reserved_mib":torch.cuda.max_memory_reserved()/2**20}),flush=True)
                base.clear_quant(); del base,tok; gc.collect(); torch.cuda.empty_cache()
        bad = sum(not row["identical"] for row in report["fp32_rechecks"])
        report.update(status="PROMPT_CACHE_DIAGNOSTIC_COMPLETE", case_count=2*len(report["records"]),
                      bf16_cache_differences=sum(not r["bf16_cache_identical"] for r in report["records"]),
                      unresolved_fp32_cache_differences=bad, path_gate_passed=bad==0 and len(report["records"])==192,
                      exit_code=0 if bad==0 and len(report["records"])==192 else 8)
    except (Exception, KeyboardInterrupt) as exc:
        report.update(status="INCOMPLETE", exit_code=130 if isinstance(exc, KeyboardInterrupt) else 9,
                      reason=f"{type(exc).__name__}: {exc}", path_gate_passed=False)
    finally:
        report["whole_wall_sec"] = time.perf_counter()-began
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        with OUTPUT.open("x", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2); f.write("\n")
        print("[P106C_A_SUMMARY] "+json.dumps({k:v for k,v in report.items() if k not in ("records","fp32_rechecks")},ensure_ascii=False),flush=True)
    return report["exit_code"]


def main():
    global OUTPUT
    p=argparse.ArgumentParser(description=__doc__)
    g=p.add_mutually_exclusive_group(required=True)
    g.add_argument("--check-only",action="store_true");g.add_argument("--execute",action="store_true")
    p.add_argument("--mode", choices=("original", "recovery"), default="original")
    args=p.parse_args()
    if args.mode == "recovery":
        OUTPUT = ROOT / "test_result/evidence/102_P106C_Stage5Wb_prompt_cache_attribution.json"
    try:
        rows,info=check()
        if args.check_only:
            print(json.dumps(info,ensure_ascii=False));return 0
        return execute(rows,info)
    except Exception as exc:
        print(f"[HOLD] {type(exc).__name__}: {exc}",file=sys.stderr);return 8


if __name__=="__main__":
    raise SystemExit(main())
