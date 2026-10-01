#!/usr/bin/env python3
"""User-run P106B: chat32 parent baseline, teacher correction, shared A/B SFT pilot.

All model loading is behind --execute. Prior v28 and parent checkpoints are immutable.
Correction remains PSEUDO_UNVERIFIED. Each lineage uses its own tokenizer/cache.
"""
from __future__ import annotations
import argparse
import ast
from collections import Counter
import gc
import hashlib
import json
import math
from pathlib import Path
import random
import re
import shutil
import sys
import time
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.diag_p106_bonsai_assets import regular, sha256_file
from scripts.p106b_gate_runtime import (TeacherSession, EffortView, GateNegative, PrerequisiteHold,
    ToolFailure, idle_before_gpu, new_directory, wall_limit, write_report, disposition,
    THINKING_SAMPLER, teacher_inputs)
from scripts.p106b_pipeline import CandidateWriter, validate_job_contract
from scripts.p106b_shards import ShardWriter, verify
from scripts.p106b_repeat4_gate import group_split, PROBES
from scripts.p106b_output_contract import request_group
from scripts.p106b_report_domains import separated_report
from scripts.p106b_lexical_observation import TextObserver
from scripts.train_sft_p090 import (encode_records, micro_groups, loss_sum, evaluate,
    validate_parent_lineage)
from tinylm.data.sft import conversation_split_key

V28 = ROOT / "HF/sft_ready/p106b_teacher_sft/v28_integrated_a2_one_slot_low"
V28_SHA = "CBC350C7AEA4C6F8F46904207F5EF517D9A11395EB4C67E16A32ECD5201023A5"
OLD_BASE = ROOT / "HF/sft_ready/p106b_teacher_sft/v29_corrected_lineage_pilot"
CHOICE_BASE = ROOT / "HF/sft_ready/p106b_teacher_sft/v32_prompt_wire_effort_panel"
CHOICE_SHA = "EA622B8D7448796B38D031F7A4C21B60496B47A54D7084E78FBC9B6498EC2E93"
BASE = ROOT / "HF/sft_ready/p106b_teacher_sft/v33_online_technical_contract"
CORRECTION_CONTEXT = 32768
CORRECTION_MAX_OUTPUT = 16384
CORRECTION_THINKING_BUDGET = 8192
CORRECTION_SCHEMA = "P106B_TECHNICAL_COLLECTION_V3"
EFFORT_PANEL_SCHEMA = "P106B_EFFORT_UPPER_PANEL_V1"
EFFORTS = ("low", "medium", "xhigh")
BASELINE_SHA = "38E1EB39FF0D14F7E8BCDB4C9614553A5CBBE93EDA2E2353E0FB7690F8C7F399"
BASELINE_FUNCTIONS = {"answers":"461A2E397562638006858E66FBF59711099EE645D1647044B789D8477463FA60","load_student":"D7189B898807091903B18AFCE143BB77C9A0179EFCB60DA65D7CEBCC8EC01F7B","native_text_probes":"6C44C41BF1DFDE9C030322623BE236F2DCF30543DB326AA639BB1714F3D499C6","parent_baseline":"B1A6632CB3CDC353E88D5692278679C516CDA192636AB11A611477F94A92A663","parent_baseline_check":"CE90569B9F88D3264F95ABF29279BED660B40466083C63690571B2EA048CCC49","score_answer":"05FC71EFEFF0AF25872C6D185EF5D0E77B9804E3ECB75FE712D57477183ED475"}
ARMS = {
    "a": {"parent": "runs/ckpt/m100R1c_ko-en_300M_p076_b3_ag2_mean_s1337.pt",
          "sha": "41036721CEAAE3EACA568BF45FA5079745EBAE85B42033D28ECC9709F5D00A71",
          "tokenizer": "data_cache/tok-ko-en-32768.json",
          "tok_sha": "3A69001ECC28A5BDF1E951A1036B234C9BDCB847B310252C6D72CFC6C52C48E3",
          "lineage": "legacy", "cache": "data_cache/ko-en_600000000", "layers": 20,
          "tied": True, "stem": "m100R1c_ko-en_300M_p106b_s3l_contract_a_s1337"},
    "b": {"parent": "runs/ckpt/m100s10_ko-en_300M_dense_chat32_p090b_s1337.pt",
          "sha": "12E18658CDCD0AFEBE5A87073DC8977304C0D490A03A8471779D514FBB0D9950",
          "tokenizer": "data_cache/tok-ko-en-32768-chat32.json",
          "tok_sha": "9716F40E4C504D6AF37DDE76CCA578E30B45E9CA86C8B6BB79B2FA095D3AC88E",
          "lineage": "chat32", "cache": "data_cache/ko-en_601000000_chat32", "layers": 14,
          "tied": False, "stem": "m100s10_ko-en_300M_p106b_s3k_contract_chat32_s1337"},
}
MODES = ("parent-b", "effort-panel", "choose-effort", "correct-pilot", "correct", "prepare", "train-b", "train-a", "compare")


def stage_directory(mode):
    names = {"parent-b": "parent-b", "effort-panel": "effort-panel", "choose-effort": "effort-choice", "correct-pilot": "correction-pilot",
             "correct": "correction", "prepare": "prepare",
             "train-a": "a", "train-b": "b", "compare": "compare"}
    return BASE / names[mode]


def sha_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest().upper()


def read_report(path, schema, status=None):
    if not regular(path):
        raise PrerequisiteHold(f"required report absent/linked: {path}")
    if (path.parent / "failure.json").exists():
        raise PrerequisiteHold(f"upstream failure journal present: {path.parent.name}")
    report = json.loads(path.read_text(encoding="utf-8"))
    if report.get("schema") != schema or (status and report.get("status") != status):
        raise PrerequisiteHold(f"required report not complete: {path.name}")
    return report


def read_rows(directory, stem, expected_sha=None):
    spec = read_report(directory / f"{stem}_shards_manifest.json", "P106B_WRITE_ONCE_SHARDS_V1")
    verify(directory, spec)
    if expected_sha and spec["concat_sha256"] != expected_sha:
        raise ValueError("source shard concat SHA differs")
    return [json.loads(line) for shard in spec["shards"]
            for line in (directory / shard["path"]).read_text(encoding="utf-8").splitlines()]


def runtime_contract():
    paths = ("tinylm/infer/generate.py", "scripts/train_sft_p090.py", "scripts/p106b_pipeline.py",
             "scripts/p106b_gate_runtime.py", "scripts/p106b_multi_answer.py",
             "scripts/p106b_teacher_format.py", "scripts/p106b_repeat4_gate.py",
             "scripts/p106b_request_budget.py", "scripts/p106b_output_contract.py",
             "scripts/p106b_report_domains.py", "scripts/p106b_teacher_wrapper.py",
             "scripts/p106b_lexical_observation.py",
             "scripts/view_p106b_saved_answers.py")
    return {path: sha256_file(ROOT / path) for path in paths}


def require_current_stage(report):
    if (report.get("input", {}).get("code_sha256") != sha256_file(Path(__file__))
            or report.get("input", {}).get("runtime_contract") != runtime_contract()):
        raise PrerequisiteHold("upstream code changed; use a new stage/version instead of historical PASS")


def write_rows(directory, stem, rows, lineage):
    writer = ShardWriter(directory, stem)
    for row in rows:
        writer.append(row)
    spec = writer.close(lineage=lineage)
    verify(directory, spec)
    return spec


def original_rows():
    manifest = V28 / "gate_manifest.json"
    if sha256_file(manifest) != V28_SHA:
        raise PrerequisiteHold("exact v28 gate SHA changed")
    report = read_report(manifest, "P106B_INTEGRATED_A2_GATE_V1", "A2_INTEGRATED_ONE_UPDATE_PASSED")
    if report.get("actually_trained_rows") != 128 or report.get("student", {}).get("optimizer_updates") != 1:
        raise ValueError("v28 update contract differs")
    rows = read_rows(V28, "training", report["training_concat_sha256"])
    if len(rows) != 128:
        raise ValueError("v28 training row count differs")
    return rows


def arm_inputs(arm):
    spec = ARMS[arm]
    for key, sha in (("parent", "sha"), ("tokenizer", "tok_sha")):
        path = ROOT / spec[key]
        if not regular(path) or sha256_file(path) != spec[sha]:
            raise PrerequisiteHold(f"{arm} {key} absent/changed")
    return spec


def text_content(message):
    content = message["content"]
    return content if isinstance(content, str) else "".join(p["text"] for p in content if p["type"] == "text")


def correction_groups(rows):
    grouped = {}
    for row in rows:
        key = (row["meta"]["parent_concept_id"], row["meta"]["language"], conversation_split_key(row))
        grouped.setdefault(key, []).append(row)
    return list(grouped.values())


def correction_plan(rows, pilot=False):
    plans = list(enumerate(correction_groups(rows)))
    if not pilot:
        return plans
    picked = {}
    for index, group in plans:
        profile = (group[0]["meta"]["language"], 2 if len(group) > 1 else 1)
        picked.setdefault(profile, (index, group))
    expected = {("ko", 1), ("en", 1), ("ko", 2), ("en", 2)}
    if set(picked) != expected:
        raise PrerequisiteHold("pilot lacks one-answer/two-answer Korean/English profiles")
    return [picked[profile] for profile in (("ko", 1), ("en", 1), ("ko", 2), ("en", 2))]


def build_correction_job(group):
    row, meta = group[0], group[0]["meta"]
    job = {"teacher_task": "answer_given", "target_language": meta["language"],
        "source_payload": {"question": text_content(row["messages"][0]),
            "answer_variants": [text_content(r["messages"][1]) for r in group],
            "question_policy": "Preserve intended question, quantities and output constraints. Draft answers are unverified context. Acknowledge missing evidence; no automatic word-error feedback."},
        "source_id": meta["source_id"], "source_sha256": sha_text(json.dumps(group, sort_keys=True, ensure_ascii=False)),
        "source_license": meta.get("source_license", "SOURCE_METADATA_ONLY"),
        "source_repo": meta.get("source_repo", "public_v28"), "source_revision": meta.get("source_revision", "v28"),
        "source_transform": "teacher_answer", "parent_concept_id": meta["parent_concept_id"],
        "rights_status": "CARD_ONLY", "split": "train"}
    validate_job_contract(job)
    return job


def baseline_evidence():
    """Reuse the observed B assessment, without promoting changed C code to E2E PASS."""
    path = OLD_BASE / "parent-b/report.json"
    if not regular(path) or sha256_file(path) != BASELINE_SHA:
        raise PrerequisiteHold("exact observed B baseline absent/changed")
    report = read_report(path, "P106B_PARENT_BASELINE_V1", "BASELINE_COMPLETE")
    current = parent_baseline_check()
    for key in ("parent_sha256", "native_val_sha256", "metadata_sha256"):
        if report["input"].get(key) != current[key]:
            raise PrerequisiteHold("B baseline input identity changed: " + key)
    tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
    actual = {node.name: sha_text(ast.dump(node, include_attributes=False)) for node in tree.body
              if isinstance(node, ast.FunctionDef) and node.name in BASELINE_FUNCTIONS}
    if actual != BASELINE_FUNCTIONS:
        raise PrerequisiteHold("baseline evaluation functions changed; old assessment cannot be relabeled")
    old_runtime = report["input"]["runtime_contract"]
    for name in ("tinylm/infer/generate.py", "scripts/train_sft_p090.py", "scripts/p106b_repeat4_gate.py"):
        if sha256_file(ROOT / name) != old_runtime[name]:
            raise PrerequisiteHold("baseline evaluation helper changed: " + name)
    for stem, summary in (("answers_parent", report["answers"]), ("native_text_parent", report["native_text_probes"])):
        read_rows(path.parent, stem, summary.get("raw_concat_sha256", summary.get("concat_sha256")))
    return {"path": path.relative_to(ROOT).as_posix(), "sha256": BASELINE_SHA,
        "recorded_commit": "20cef06", "observed_first_pass": report["answers"]["first_attempt_pass"],
        "observed_within3_pass": report["answers"]["pass_within_three"],
        "scope": "existing observed parent evidence only; recovery pipeline GPU NOT_RUN"}


def wire_encoding(rows, encoders):
    return {arm: [{"conversation_tokens": len(r[0]), "assistant_targets": r[2]}
                   for r in encode_records(rows, tok, 1024, 32768)]
            for arm, tok in encoders.items()}


def parent_baseline_check():
    spec = arm_inputs("b")
    for name in ("val.bin", "meta.json"):
        if not regular(ROOT / spec["cache"] / name):
            raise PrerequisiteHold("B native validation cache absent/linked")
    meta = json.loads((ROOT / "runs/logs/m100s10_ko-en_300M_dense_chat32_p090b_s1337.json").read_text(encoding="utf-8"))
    if meta.get("tokenizer_sha256") != spec["tok_sha"] or meta.get("steps") != 2289:
        raise ValueError("B pretrain metadata lineage differs")
    cache_meta = json.loads((ROOT / spec["cache"] / "meta.json").read_text(encoding="utf-8"))
    if cache_meta.get("data") != "ko-en" or cache_meta.get("vocab") != 32768:
        raise ValueError("B native cache geometry differs")
    train_path = ROOT / spec["cache"] / "train.bin"
    if not regular(train_path) or train_path.stat().st_size % 2:
        raise PrerequisiteHold("B native train uint16 pool absent or invalid")
    train_tokens = train_path.stat().st_size // 2
    return {"parent": spec["parent"], "parent_sha256": spec["sha"],
        "pretrain_data": "ko-en: Korean Wikipedia + English FineWeb-Edu",
        "pretrain_tokens": meta["tokens"], "pretrain_steps": meta["steps"],
        "mix_token_frac": meta["mix_token_frac"], "init_from": meta["init_from"],
        "pretrain_final_sample_val": meta["final"]["val_loss"], "pretrain_best_sample_val": meta["best_val"],
        "grad_max": meta["grad_max"], "n_skip": meta["n_skip"],
        "actual_pretrain_pool_tokens": train_tokens,
        "required_two_times_draw": meta["tokens"] * 2,
        "pool_shortfall_tokens": max(0, meta["tokens"] * 2 - train_tokens),
        "native_val_sha256": sha256_file(ROOT / spec["cache"] / "val.bin"),
        "metadata_sha256": sha256_file(ROOT / "runs/logs/m100s10_ko-en_300M_dense_chat32_p090b_s1337.json"),
        "limit": "native-token CE not comparable across A/B tokenizer; generation quality must be inspected"}


def prepare_preview():
    directory = stage_directory("correct")
    report = read_report(directory / "report.json", CORRECTION_SCHEMA, "COLLECTION_TECHNICAL_READY")
    require_current_stage(report)
    rows = read_rows(directory, "selected", report["selected_concat_sha256"])
    probe_questions = {re.sub(r"\s+", " ", text).strip().casefold() for _name, text in PROBES}
    exact_overlap = sum(re.sub(r"\s+", " ", text_content(row["messages"][0])).strip().casefold()
                        in probe_questions for row in rows)
    if exact_overlap:
        raise GateNegative("corrected corpus has exact fixed-probe question overlap")
    train, val = group_split(rows)
    from tokenizers import Tokenizer
    statistics = {}
    for arm in ("a", "b"):
        spec = arm_inputs(arm)
        tok = Tokenizer.from_file(str(ROOT / spec["tokenizer"]))
        tr, va = [encode_records(part, tok, 1024, 32768) for part in (train, val)]
        statistics[arm] = {"train_rows": len(tr), "val_rows": len(va),
            "train_conversation_tokens_per_epoch": sum(len(r[0]) for r in tr),
            "train_assistant_tokens_per_epoch": sum(r[2] for r in tr),
            "train_conversation_tokens_4epoch": 4 * sum(len(r[0]) for r in tr),
            "updates_expected": 4 * math.ceil(len(tr) / 128)}
    return train, val, {"source_report_sha256": sha256_file(directory / "report.json"),
        "source_concat_sha256": report["selected_concat_sha256"], "per_arm": statistics,
        "split_policy": "same parent concept and normalized first question stay together", "epochs": 4,
        "fixed_probe_exact_overlap": exact_overlap,
        "broad_benchmark_contamination": "NOT_RUN"}


def check(mode):
    target = stage_directory(mode)
    new_directory(target)
    info = {"schema": "P106B_EDUCATION_PREFLIGHT_V1", "mode": mode,
            "code_sha256": sha256_file(Path(__file__)), "runtime_contract": runtime_contract(),
            "hard_wall_sec": 21600 if mode == "correct" else 7200,
            "formal_train_ready": False}
    if mode == "parent-b":
        info.update(parent_baseline_check())
    elif mode in ("effort-panel", "correct-pilot", "correct"):
        info["baseline_evidence"] = baseline_evidence()
        if mode != "effort-panel":
            known = ROOT / "HF/sft_ready/p106b_teacher_sft/v33_output_contract_pilot/report.json"
            known_report = read_report(known, "P106B_KNOWN_OUTPUT_GATE_V1", "CONTRACT_PILOT_COMPLETE")
            if (known_report["input"].get("runtime_contract") != runtime_contract()
                    or known_report["input"].get("code_sha256") != sha256_file(ROOT / "scripts/diag_p106b_contract_gate.py")):
                raise PrerequisiteHold("known-output pilot code changed; new observed stage required")
            info["known_output_pilot_sha256"] = sha256_file(known)
            choice_path = CHOICE_BASE / "effort-choice/report.json"
            if not regular(choice_path) or sha256_file(choice_path) != CHOICE_SHA:
                raise PrerequisiteHold("exact observed effort choice absent/changed")
            choice = read_report(choice_path,
                                 "P106B_EFFORT_CHOICE_V1", "EFFORT_CHOSEN")
            if choice["effort"] != "xhigh":
                raise PrerequisiteHold("historical user effort choice differs")
            info["teacher_effort"] = choice["effort"]
            info["effort_choice_sha256"] = CHOICE_SHA
            info["effort_choice_scope"] = "frozen user setting only, not new runtime/quality PASS"
        if mode == "correct":
            pilot = read_report(stage_directory("correct-pilot") / "report.json",
                CORRECTION_SCHEMA, "CORRECTION_WIRING_PASSED")
            require_current_stage(pilot)
            if pilot["input"].get("mode") != "correct-pilot" or pilot["input"].get("source_groups") != 4:
                raise PrerequisiteHold("four-profile recovery pilot not observed complete")
            if pilot["input"].get("effort_choice_sha256") != info["effort_choice_sha256"]:
                raise PrerequisiteHold("pilot/full correction effort choice differs")
            info["pilot_report_sha256"] = sha256_file(stage_directory("correct-pilot") / "report.json")
        plans = correction_plan(original_rows(), pilot=mode in ("correct-pilot", "effort-panel"))
        groups = [group for _index, group in plans]
        for group in groups:
            build_correction_job(group)  # Actual canonical provenance checks, no teacher/model.
        counts = Counter(g[0]["meta"]["language"] for g in groups)
        info.update(source_manifest_sha256=V28_SHA, source_groups=len(groups),
                    source_group_indices=[index for index, _group in plans],
                    groups_per_language=dict(counts), maximum_attempts_per_group=3,
                    teacher_truth="PSEUDO_UNVERIFIED", max_output=CORRECTION_MAX_OUTPUT,
                    context=CORRECTION_CONTEXT, thinking_budget_tokens=CORRECTION_THINKING_BUDGET)
        info.update(teacher_inputs(), teacher_sampler=dict(THINKING_SAMPLER),
                    effort_calibration_note="low is a valid template label, but the model card says its short-reasoning calibration is unsupported/near xhigh")
        if mode == "effort-panel":
            info.update(efforts=list(EFFORTS), maximum_attempts_per_group=1,
                        source_groups=4, requests=12)
    elif mode == "choose-effort":
        panel = read_report(stage_directory("effort-panel") / "report.json", EFFORT_PANEL_SCHEMA, "EFFORT_PANEL_RECORDED")
        require_current_stage(panel)
        eligible = [e for e in EFFORTS if panel["per_effort"][e]["wire_complete"]]
        if not eligible:
            raise PrerequisiteHold("no effort completed all four technical profiles; preserve panel and redesign")
        info.update(eligible_efforts=eligible, panel_sha256=sha256_file(stage_directory("effort-panel") / "report.json"))
    elif mode == "prepare":
        _tr, _va, preview = prepare_preview()
        info.update(preview)
    elif mode.startswith("train-"):
        arm = mode[-1]
        spec = arm_inputs(arm)
        corpus = read_report(stage_directory("prepare") / "report.json", "P106B_SHARED_CORPUS_V1", "CORPUS_READY")
        require_current_stage(corpus)
        for stem in ("train", "val"):
            read_rows(stage_directory("prepare"), stem, corpus[stem + "_concat_sha256"])
        for suffix in (".pt",):
            output = ROOT / "runs/ckpt" / (spec["stem"] + suffix)
            if output.exists() or output.is_symlink():
                raise FileExistsError("new student output checkpoint exists")
        output = ROOT / "runs/logs" / (spec["stem"] + ".json")
        if output.exists() or output.is_symlink():
            raise FileExistsError("new student metadata exists")
        disk_free = shutil.disk_usage(ROOT / "runs/ckpt").free
        if disk_free < 2 * 1024**3:
            raise PrerequisiteHold("less than2GiB disk space for new child checkpoint/evidence")
        for name in ("val.bin", "meta.json"):
            if not regular(ROOT / spec["cache"] / name):
                raise PrerequisiteHold("lineage native validation cache absent/linked")
        info.update(arm=arm, parent_sha256=spec["sha"], tokenizer_sha256=spec["tok_sha"],
                    corpus_sha256=sha256_file(stage_directory("prepare") / "report.json"), micro=8, accum=16,
                    epochs=4, learning_rate=1e-4, optimizer="Muon RMS4", checkpoint_on=True,
                    quality="new before/after answer and own-cache full-val evidence", disk_free_bytes=disk_free)
    else:
        reports = [read_report(stage_directory("train-" + arm) / "report.json", "P106B_LINEAGE_EDUCATION_V1", "EDUCATION_COMPLETE") for arm in ("a", "b")]
        for report in reports:
            require_current_stage(report)
        if reports[0]["input"]["corpus_sha256"] != reports[1]["input"]["corpus_sha256"]:
            raise ValueError("A/B common raw corpus changed")
        info.update(corpus_sha256=reports[0]["input"]["corpus_sha256"],
                    causal_claim="DESCRIPTIVE_ONLY: architecture, tokenizer and pretrain parents differ")
    return target, info


def load_student(arm, training=False):
    import torch
    from tokenizers import Tokenizer
    from tinylm.config import TMTConfig
    from tinylm.model import TiedMLPTransformer
    from tinylm.infer.generate import _strip
    from tinylm.train.optimizer_audit import matrix_decay_groups
    from tinylm.train.muon import Muon, split_params
    spec = ARMS[arm]
    torch.set_num_threads(1)
    torch.manual_seed(1337)
    state = torch.load(ROOT / spec["parent"], map_location="cpu", weights_only=True)
    tok = Tokenizer.from_file(str(ROOT / spec["tokenizer"]))
    validate_parent_lineage(state, spec["tok_sha"], spec["lineage"], tok)
    cfg = TMTConfig(**state["cfg"])
    if state.get("step") != 2289:
        raise ValueError("parent step differs from completed 300M source")
    if cfg.n_layers != spec["layers"] or cfg.tie_mlp != spec["tied"] or cfg.vocab_size != 32768:
        raise ValueError("parent geometry differs from preregistered lineage")
    cfg.grad_checkpoint = True
    base = TiedMLPTransformer(cfg).cuda()
    base.load_state_dict(_strip(state["model"]), strict=True)
    del state
    base.set_anneal(1.0)
    if not training:
        return torch, base, cfg, tok
    import tempfile
    import os
    os.environ["TORCHINDUCTOR_CACHE_DIR"] = tempfile.mkdtemp(prefix="p106b_lineage_")
    model = torch.compile(base, mode="default")
    groups, _ = matrix_decay_groups(model, 1e-4, 0)
    matrices, _ = split_params(model)
    matrix_ids = {id(p) for p in matrices}
    others = [dict(g, params=[p for p in g["params"] if id(p) not in matrix_ids]) for g in groups]
    others = [g for g in others if g["params"]]
    adam = torch.optim.AdamW(others, betas=(0.9, 0.95), eps=1e-8)
    muon = Muon(matrices, lr=4e-4, scale_mode="rms", weight_decay=0)
    return torch, model, base, cfg, tok, adam, muon


def score_answer(ident, answer):
    text = answer.strip().rstrip(".!。").strip()
    if ident == "arithmetic_ko":
        return text == "5"
    if ident == "arithmetic_en":
        return text == "3"
    if ident == "format_en":
        try:
            data = json.loads(text)
            return isinstance(data, dict) and set(data) == {"result"} and type(data["result"]) is int and data["result"] == 5
        except ValueError:
            return False
    if ident == "format_ko":
        fruits = {"사과", "배", "포도", "딸기", "바나나", "귤", "오렌지", "수박", "복숭아", "망고"}
        words = [w.strip() for w in text.split(",")]
        return len(words) == 2 and len(set(words)) == 2 and all(w in fruits for w in words)
    if ident == "knowledge_ko":
        return "얼음" in text and not any(mark in text for mark in ("?", "<|", "아닙"))
    if ident == "knowledge_en":
        return text.casefold() == "earth"
    if ident == "memory_ko":
        return text == "별빛"
    return text.casefold() == "yes" if ident == "logic_en" else False


def answers(base, cfg, tok, directory, label):
    import torch
    from tinylm.infer.generate import sample
    from tinylm.chat.serialize import serialize
    writer = ShardWriter(directory, "answers_" + label)
    first = eventual = 0
    base.eval()
    base.freeze_quant()
    stops = [tok.encode("<|im_end|>").ids]
    for index, (ident, text) in enumerate(PROBES):
        passed = False
        for attempt in range(1, 4):
            user = text if attempt == 1 else text + "\nAnswer only what was asked, using the requested format."
            prompt = serialize({"messages": [{"role": "user", "content": user}]}, "chatml", add_generation_prompt=True)
            torch.manual_seed(20261000 + index * 10 + attempt)
            decoded, meta = sample(base, cfg, tok, prompt, max_new=160,
                temperature=0 if attempt == 1 else 0.8, top_k=1 if attempt == 1 else 40,
                device="cuda", logits_last_only=True, return_metadata=True, stop_token_sequences=stops)
            prefix = tok.decode(tok.encode(prompt).ids)
            answer = decoded[len(prefix):] if decoded.startswith(prefix) else ""
            rendered = answer.split("<|im_end|>", 1)[0]
            passed = score_answer(ident, rendered)
            first += int(attempt == 1 and passed)
            writer.append({"model": label, "id": ident, "attempt": attempt,
                "prompt": prompt, "raw_full_text": decoded, "answer_text": answer,
                "rendered_answer": rendered, "generation": meta, "narrow_rubric_pass": passed,
                "rubric": "P106B_NARROW_8_V1", "temperature": 0 if attempt == 1 else 0.8,
                "seed": 20261000 + index * 10 + attempt, "human_review": "NOT_RUN"})
            if passed:
                break
        eventual += int(passed)
    spec = writer.close(lineage={"label": label, "probe_count": 8, "maximum_attempts": 3})
    verify(directory, spec)
    base.clear_quant()
    base.train()
    return {"first_attempt_pass": first, "pass_within_three": eventual, "questions": 8,
            "actual_attempts": spec["rows"], "raw_concat_sha256": spec["concat_sha256"],
            "limit": "narrow rubric and conditional retry upper bound; human semantics separately reviewed"}


def parent_baseline(target, info):
    from scripts.paired_eval import full_val_losses
    _torch, base, cfg, tok = load_student("b")
    print("[BASELINE] loaded pinned B parent; measuring its native full validation and fixed Korean/English answers", flush=True)
    losses, tokens = full_val_losses(base, cfg, ROOT / ARMS["b"]["cache"], 1024, 4, "cuda")
    if not losses or not all(math.isfinite(x) for x in losses):
        raise ToolFailure("B native val empty/nonfinite")
    answer = answers(base, cfg, tok, target, "parent")
    native_text = native_text_probes(base, cfg, tok, target, "parent", ROOT / ARMS["b"]["cache"])
    return {"schema": "P106B_PARENT_BASELINE_V1", "status": "BASELINE_COMPLETE", "input": info,
        "native_full_val_ce": sum(losses) / len(losses), "native_val_crops": len(losses),
        "native_val_tokens": tokens, "answers": answer, "native_text_probes": native_text,
        "parent_quality": "MANUAL_RAW_REVIEW_REQUIRED",
        "limit": "technical baseline complete even if answer rubric fails; no trained-SFT claim"}


def native_text_probes(base, cfg, tok, directory, label, cache):
    """Deterministic native-val text continuations; statistical CE plus inspectable wording."""
    import numpy as np
    from tinylm.infer.generate import sample
    data = np.memmap(cache / "val.bin", dtype=np.uint16, mode="r")
    selected = {"ko": [], "en": []}
    writer = ShardWriter(directory, "native_text_" + label)
    base.eval()
    base.freeze_quant()
    for index in range(min(256, (len(data)-256)//1024)):
        ids = data[index*1024:index*1024+256].tolist()
        text = tok.decode(ids)
        letters = re.findall(r"[A-Za-z가-힣]", text)
        if not letters:
            continue
        ko_fraction = sum(bool(re.match(r"[가-힣]", c)) for c in letters)/len(letters)
        language = "ko" if ko_fraction >= .5 else "en" if ko_fraction <= .05 else None
        if language is None or len(selected[language]) >= 2:
            continue
        prompt = tok.decode(ids[:64])
        decoded, meta = sample(base, cfg, tok, prompt, max_new=80, temperature=0,
            top_k=1, device="cuda", logits_last_only=True, return_metadata=True)
        writer.append({"label": label, "language_heuristic": language, "native_crop": index,
            "prompt": prompt, "reference_continuation": tok.decode(ids[64:144]),
            "generated_full_text": decoded, "generation": meta,
            "quality": "MANUAL_CONTINUATION_REVIEW_REQUIRED"})
        selected[language].append(index)
        if all(len(v) == 2 for v in selected.values()):
            break
    spec = writer.close(lineage={"cache": cache.relative_to(ROOT).as_posix(), "label": label}) if writer._total_rows else None
    if spec:
        verify(directory, spec)
    base.clear_quant()
    base.train()
    return {"selected_native_crops": selected, "rows": spec["rows"] if spec else 0,
            "concat_sha256": spec["concat_sha256"] if spec else None,
            "language_status": {language: "OBSERVED" if indices else "NOT_RUN_NO_PREFIX_IN_FIXED_WINDOW"
                                for language, indices in selected.items()},
            "limit": "script-ratio heuristic and up to4 fixed prefixes; not whole-corpus quality"}


def correction_gate(completed, expected, accepted, selected_rows):
    required = {lang: math.ceil(expected.get(lang, 0) * .75) for lang in ("ko", "en")}
    passed = (completed and selected_rows > 0
              and all(required[lang] > 0 and accepted.get(lang, 0) >= required[lang]
                      for lang in ("ko", "en")))
    return bool(passed), required


def effort_panel(target, info):
    plans = correction_plan(original_rows(), pilot=True)
    from tokenizers import Tokenizer
    encoders = {arm: Tokenizer.from_file(str(ROOT / spec["tokenizer"])) for arm, spec in ARMS.items()}
    writer = CandidateWriter(target, info, observer=TextObserver("within"))
    journal = ShardWriter(target, "panel_journal")
    records, session = [], None
    orders = (("low", "medium", "xhigh"), ("xhigh", "medium", "low"),
              ("medium", "low", "xhigh"), ("xhigh", "low", "medium"))
    try:
        with TeacherSession(info["context"], 1, effort="medium",
                            thinking_budget=info["thinking_budget_tokens"]) as session:
            for position, (index, group) in enumerate(plans):
                job = build_correction_job(group)
                count = 2 if len(group) > 1 else 1
                for effort in orders[position]:
                    ident = f"panel_{effort}_C_{index:03d}"
                    rows = writer.request(EffortView(session, effort), job, ident,
                        20262000 + index * 10 + 1, count=count, per_slot=info["context"],
                        maximum=info["max_output"], dedupe_scope=effort)
                    encoding, encoding_error = {}, None
                    if rows:
                        try:
                            encoding = wire_encoding(rows, encoders)
                        except ValueError as exc:
                            encoding_error = str(exc)
                    wire_ok = len(rows) == count and bool(encoding) and encoding_error is None
                    diagnostic = writer.response_diagnostics[ident]
                    record = {"generation_id": ident, "group": index, "effort": effort,
                        "profile": [group[0]["meta"]["language"], count],
                        "order": list(orders[position]), "seed": 20262000 + index * 10 + 1,
                        "wire_ok": wire_ok, "encoding": encoding, "encoding_error": encoding_error,
                        "content_issues": None, "diagnostic": diagnostic}
                    # Request duration and usage remain exact in the corresponding raw record.
                    records.append(record)
                    journal.append(record)
                    session.check_monitor()
            session.require_valid_resources()
    finally:
        metrics = writer.close()
        jspec = journal.close(lineage=info) if records else None
        if jspec:
            verify(target, jspec)
    raw = read_rows(target, "raw", metrics["raw_concat_sha256"])
    canonical = read_rows(target, "canonical", metrics["canonical_concat_sha256"]) if metrics["canonical_rows"] else []
    from scripts.view_p106b_saved_answers import print_panel
    print_panel({"records": records}, raw, canonical, BASE.relative_to(ROOT).as_posix())
    by_id = {r["generation_id"]: r for r in raw}
    summaries = {}
    for effort in EFFORTS:
        subset = [r for r in records if r["effort"] == effort]
        wall = sum(by_id[r["generation_id"]]["wall_sec"] for r in subset)
        completion = sum(r["diagnostic"]["server_usage"].get("completion_tokens", 0) for r in subset)
        summaries[effort] = {"requests": len(subset), "wire_complete": len(subset) == 4 and all(r["wire_ok"] for r in subset),
            "wire_profiles": sum(r["wire_ok"] for r in subset), "content_screen_passed_groups": None,
            "request_sum_sec": wall, "completion_tokens": completion,
            "completion_tok_per_sec": completion / wall if wall else None,
            "usable_groups_per_sec": None,
            "semantic_truth": "NOT_RUN", "answer_refs": [r["generation_id"] for r in subset]}
    return {"schema": EFFORT_PANEL_SCHEMA, "status": "EFFORT_PANEL_RECORDED", "input": info,
        **metrics, "per_effort": summaries, "records": records,
        "panel_journal_sha256": jspec["concat_sha256"], "server": session.evidence(),
        "thinking_budget_effective_observation": "request configured; no separate emitted-reasoning token count in this server evidence",
        "student_training": "NOT_RUN", "quality": "NOT_RUN"}


def choose_effort(info, effort=None):
    panel = read_report(stage_directory("effort-panel") / "report.json", EFFORT_PANEL_SCHEMA, "EFFORT_PANEL_RECORDED")
    require_current_stage(panel)
    print("명시된 실행 전 설정을 확인합니다. 형식 통과는 정답성을 보장하지 않습니다.", flush=True)
    for number, candidate in enumerate(info["eligible_efforts"], 1):
        print(f"{number}. {candidate}: " + json.dumps(panel["per_effort"][candidate], ensure_ascii=False), flush=True)
    if effort not in info["eligible_efforts"]:
        raise PrerequisiteHold("explicit --effort must be one of the technically complete efforts; no input wait/default")
    return {"schema": "P106B_EFFORT_CHOICE_V1", "status": "EFFORT_CHOSEN", "input": info,
            "effort": effort, "selection_owner": "user", "semantic_truth": "PSEUDO_UNVERIFIED"}


def correct(target, info, *, whole_began=None):
    # This report is write-once inside finally. Store the existing whole-wall
    # metric before that write, and keep the exact same value in stdout.
    whole_began = time.monotonic() if whole_began is None else whole_began
    originals = original_rows()
    plans = correction_plan(originals, pilot=info.get("mode") == "correct-pilot")
    groups = [group for _index, group in plans]
    original_spec = write_rows(target, "original", originals, info)
    writer = CandidateWriter(target, info, observer=TextObserver("within"))
    journal = ShardWriter(target, "review_journal")
    selected, accepted = [], Counter()
    from tokenizers import Tokenizer
    encoders = {arm: Tokenizer.from_file(str(ROOT / spec["tokenizer"])) for arm, spec in ARMS.items()}
    wired = Counter()
    wired_indices = set()
    session, completed, fatal = None, False, None
    try:
        with TeacherSession(info.get("context", CORRECTION_CONTEXT), 1,
            effort=info.get("teacher_effort", "medium"),
            thinking_budget=info.get("thinking_budget_tokens", CORRECTION_THINKING_BUDGET)) as session:
            for index, group in plans:
                row = group[0]
                meta = row["meta"]
                job = build_correction_job(group)
                count = 2 if len(group) > 1 else 1
                def record_attempt(trace):
                    wire_ok = bool(trace["diagnostic"].get("transport_complete")
                                   and trace["encoding"] and not trace["encoding_error"])
                    if wire_ok and index not in wired_indices:
                        wired_indices.add(index)
                        wired[meta["language"]] += 1
                    journal.append({"group": index, **trace,
                        "content_issues": None, "wire_ok": wire_ok,
                        "original_generation_ids": [r["meta"]["generation_id"] for r in group],
                        "original_text_sha256": job["source_sha256"], "generated_rows": len(trace["retained_slots"]),
                        "selection_basis": "technical only; semantic review NOT_RUN"})
                rows, recovery = request_group(writer, session, job, f"C_{index:03d}",
                    20262000 + index * 10, count=count,
                    per_slot=info.get("context", CORRECTION_CONTEXT),
                    maximum=info.get("max_output", CORRECTION_MAX_OUTPUT),
                    maximum_attempts=info.get("maximum_attempts_per_group", 3),
                    encode=lambda part: wire_encoding(part, encoders), on_attempt=record_attempt)
                for candidate in rows:
                    candidate["meta"].update(correction_of=[r["meta"]["generation_id"] for r in group],
                        correction_source_sha256=job["source_sha256"], semantic_truth="PSEUDO_UNVERIFIED",
                        request_budget_used=recovery["budget_attempts"])
                selected.extend(rows)
                if rows:
                    accepted[meta["language"]] += 1
                session.check_monitor()
            session.require_valid_resources()
            completed = True
    except (Exception, KeyboardInterrupt) as exc:
        fatal = exc
        raise
    finally:
        metrics = writer.close()
        review = journal.close(lineage=info) if journal._total_rows else None
        if review:
            verify(target, review)
        spec = write_rows(target, "selected", selected, info) if selected else None
        # Always preserve partial evidence before reporting a negative screen.
        expected = Counter(group[0]["meta"]["language"] for group in groups)
        technical_passed, required = correction_gate(completed, expected, accepted, len(selected))
        pilot = info.get("mode") == "correct-pilot"
        wire_passed = completed and all(wired[lang] == expected[lang] and expected[lang] > 0 for lang in ("ko", "en"))
        passed = wire_passed if pilot else technical_passed
        failure_status, failure_rc = disposition(fatal) if fatal else ("GATE_NEGATIVE", 8)
        report = {"schema": CORRECTION_SCHEMA,
            "status": ("CORRECTION_WIRING_PASSED" if pilot else "COLLECTION_TECHNICAL_READY") if passed else failure_status,
            "exit_code": 0 if passed else failure_rc,
            "failure_reason": f"{type(fatal).__name__}: {str(fatal)[:250]}" if fatal else None,
            "input": info, **metrics, "selected_rows": len(selected),
            "original_concat_sha256": original_spec["concat_sha256"],
            "accepted_groups_by_language": dict(accepted), "expected_groups_by_language": dict(expected),
            "wired_groups_by_language": dict(wired), "wire_passed": wire_passed,
            "quality_screen_passed": None, "technical_gate_passed": passed,
            "content_screen_passed_groups": None, "usable_groups_per_sec": None,
            "student_training_allowed": bool(not pilot and technical_passed),
            "pipeline_formatted_response_counts_by_language": metrics["accepted_groups"],
            "selected_concat_sha256": spec["concat_sha256"] if spec else None,
            "review_journal_sha256": review["concat_sha256"] if review else None,
            "teacher_truth": "PSEUDO_UNVERIFIED", "semantic_quality": "MANUAL_REVIEW_REQUIRED",
            "required_groups_by_language": required,
            "server": session.evidence() if session else None}
        report["whole_wall_sec"] = time.monotonic() - whole_began
        report["report_domains"] = separated_report(report)
        write_report(target / "report.json", report)
        print("[CORRECTION_DIAGNOSTIC] " + json.dumps({"mode": info.get("mode"),
            "status": report["status"], "exit_code": report["exit_code"],
            "accepted_groups_by_language": report["accepted_groups_by_language"],
            "wired_groups_by_language": report["wired_groups_by_language"],
            "wire_passed": report["wire_passed"],
            "quality_screen_passed": report["quality_screen_passed"],
            "student_training_allowed": report["student_training_allowed"],
            "required_groups_by_language": report["required_groups_by_language"],
            "response_cause_counts": report["response_cause_counts"],
            "selected_rows": report["selected_rows"], "student_training": "NOT_RUN"},
            ensure_ascii=False, sort_keys=True), flush=True)
    if not passed:
        raise GateNegative("four-profile technical wiring incomplete" if pilot else "technical material below75% per language; semantics NOT_REVIEWED; partial preserved")
    return report


def prepare_corpus(target, info):
    train, val, expected = prepare_preview()
    tr = write_rows(target, "train", train, info)
    va = write_rows(target, "val", val, info)
    return {"schema": "P106B_SHARED_CORPUS_V1", "status": "CORPUS_READY", "input": info,
        **expected, "train_concat_sha256": tr["concat_sha256"], "val_concat_sha256": va["concat_sha256"],
        "formal_train_ready": False, "teacher_truth": "PSEUDO_UNVERIFIED"}


def educate(target, info, arm):
    from scripts.paired_eval import full_val_losses, paired_stats
    spec = ARMS[arm]
    torch, model, base, cfg, tok, adam, muon = load_student(arm, training=True)
    train_rows, val_rows = [read_rows(stage_directory("prepare"), name) for name in ("train", "val")]
    tr, va = [encode_records(rows, tok, 1024, cfg.vocab_size) for rows in (train_rows, val_rows)]
    pad = tok.token_to_id("<pad>")
    if pad is None:
        raise ToolFailure("PAD ID absent")
    args = SimpleNamespace(micro_bs=4, ce_chunk=2048)
    before, used = full_val_losses(base, cfg, ROOT / spec["cache"], 1024, 4, "cuda")
    before_sft = evaluate(base, va, args, pad, "cuda", cfg.vocab_size)
    parent_answers = answers(base, cfg, tok, target, "parent")
    before_text = native_text_probes(base, cfg, tok, target, "parent", ROOT / spec["cache"])
    history = []
    updates, grad_max = 0, 0.0
    torch.cuda.reset_peak_memory_stats()
    for epoch in range(1, 5):
        order = list(range(len(tr)))
        random.Random(1337 + epoch).shuffle(order)
        began, total_loss, total_targets = time.monotonic(), 0.0, 0
        for blocks in micro_groups(tr, order, 8, 16):
            targets = sum(row[2] for block in blocks for row in block)
            adam.zero_grad(set_to_none=True)
            muon.zero_grad(set_to_none=True)
            for block in blocks:
                part = loss_sum(model, block, pad, "cuda", cfg.vocab_size, 2048)
                if not bool(torch.isfinite(part)):
                    raise ToolFailure("nonfinite masked SFT loss")
                total_loss += float(part.detach())
                (part / targets).backward()
            grad = float(torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0))
            if not math.isfinite(grad):
                raise ToolFailure("nonfinite SFT gradient")
            grad_max = max(grad_max, grad)
            adam.step()
            muon.step()
            updates += 1
            total_targets += targets
        torch.cuda.synchronize()
        history.append({"epoch": epoch, "updates_total": updates, "train_ce": total_loss / total_targets,
            "sft_val_ce": evaluate(base, va, args, pad, "cuda", cfg.vocab_size),
            "processed_conversation_tokens": sum(len(r[0]) for r in tr), "assistant_targets": total_targets,
            "epoch_wall_sec": time.monotonic() - began})
        print("[EDUCATION_EPOCH] " + json.dumps(history[-1]), flush=True)
    after, _ = full_val_losses(base, cfg, ROOT / spec["cache"], 1024, 4, "cuda")
    child_answers = answers(base, cfg, tok, target, "student")
    after_text = native_text_probes(base, cfg, tok, target, "student", ROOT / spec["cache"])
    checkpoint = ROOT / "runs/ckpt" / (spec["stem"] + ".pt")
    with checkpoint.open("xb") as stream:
        torch.save({"model": base.state_dict(), "cfg": cfg.__dict__, "step": 2289 + updates,
            "tokenizer_lineage": spec["lineage"], "tokenizer_sha256": spec["tok_sha"],
            "p106b": {"input": info, "label_status": "PSEUDO_UNVERIFIED", "epochs": 4}}, stream)
    delta = sum(after) / len(after) - sum(before) / len(before)
    safety = delta <= .1 and history[-1]["sft_val_ce"] <= before_sft + .1
    report = {"schema": "P106B_LINEAGE_EDUCATION_V1", "status": "EDUCATION_COMPLETE", "input": info,
        "arm": arm, "updates": updates, "history": history, "parent_answers": parent_answers,
        "student_answers": child_answers, "before_sft_val_ce": before_sft,
        "parent_native_text": before_text, "student_native_text": after_text,
        "base_before_ce": sum(before) / len(before), "base_after_ce": sum(after) / len(after),
        "base_full_val_delta": delta, "base_full_val_tokens": used,
        "base_val_sha256": sha256_file(ROOT / spec["cache"] / "val.bin"),
        "paired_before_minus_after": paired_stats(before, after), "operational_safety": safety,
        "grad_max_before_clip": grad_max, "peak_reserved_mib": torch.cuda.max_memory_reserved() / 1048576,
        "processed_conversation_tokens": sum(h["processed_conversation_tokens"] for h in history),
        "checkpoint": checkpoint.relative_to(ROOT).as_posix(), "checkpoint_sha256": sha256_file(checkpoint),
        "formal_train_ready": False, "quality": "MANUAL_RAW_REVIEW_REQUIRED",
        "limit": "own-cache before/after only; cross-tokenizer CE ranking prohibited"}
    write_report(ROOT / "runs/logs" / (spec["stem"] + ".json"),
        {**report, "tag": spec["stem"].split("_300M_", 1)[1],
         "arch": "tied" if spec["tied"] else "dense", "preset": "m100R1c" if arm == "a" else "m100s10",
         "data": "ko-en", "steps": updates, "tokenizer_lineage": spec["lineage"],
         "tokenizer_sha256": spec["tok_sha"], "tokens": report["processed_conversation_tokens"],
         "grad_max": grad_max, "grad_max_scope": "four-update pilot; no warmup",
         "final": {"val_loss": report["base_after_ce"], "val_source": "own-lineage native deterministic full-val",
                   "sft_val_ce": history[-1]["sft_val_ce"]}, "best_val": None})
    gc.collect()
    return report


def compare(info):
    rows = [read_report(stage_directory("train-" + arm) / "report.json", "P106B_LINEAGE_EDUCATION_V1", "EDUCATION_COMPLETE") for arm in ("b", "a")]
    for arm, report in zip(("b", "a"), rows):
        if sha256_file(ROOT / report["checkpoint"]) != report["checkpoint_sha256"]:
            raise ValueError("student checkpoint changed")
        for label in ("parent", "student"):
            answers_rows = read_rows(stage_directory("train-" + arm), "answers_" + label, report[label + "_answers"]["raw_concat_sha256"])
            if {r["id"] for r in answers_rows} != {name for name, _ in PROBES}:
                raise ValueError("paired question set incomplete")
    return {"schema": "P106B_LINEAGE_PAIR_V1", "status": "EVIDENCE_PAIRED", "input": info,
        "arms": [{"arm": r["arm"], "parent_answers": r["parent_answers"],
            "student_answers": r["student_answers"], "own_base_val_delta": r["base_full_val_delta"],
            "operational_safety": r["operational_safety"], "processed_tokens": r["processed_conversation_tokens"]} for r in rows],
        "permitted_claim": "DESCRIPTIVE_ONLY", "manual_raw_answer_review": "REQUIRED"}


def self_test():
    from tinylm.chat.canonical import normalize
    assert score_answer("arithmetic_ko", "5") and not score_answer("arithmetic_ko", "5입니다")
    assert score_answer("format_en", '{"result":5}') and not score_answer("format_en", '{"result":true}')
    assert not score_answer("logic_en", "The box is heavy")
    rows = [normalize({"messages": [{"role": "user", "content": f"q{i//2}"},
             {"role": "assistant", "content": "a"}], "meta": {"source": "fixture", "source_id": str(i),
             "language": "ko", "parent_concept_id": f"{i//2:064X}"}}) for i in range(40)]
    tr, va = group_split(rows)
    assert not ({r["meta"]["parent_concept_id"] for r in tr} & {r["meta"]["parent_concept_id"] for r in va})
    assert len(correction_groups(rows)) == 20
    assert not globals().get("content_screen") and not globals().get("content_issues")
    assert separated_report({})["posthoc_review"]["fact_correctness"] is None
    print("[PASS] lineage-specific inputs/shared split/technical admission; semantics and GPU NOT_RUN")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    for flag in ("self-test", "check-only", "execute"):
        modes.add_argument("--" + flag, action="store_true")
    parser.add_argument("--mode", choices=MODES, default="parent-b")
    parser.add_argument("--effort", choices=EFFORTS)
    args = parser.parse_args()
    target = None
    try:
        if args.self_test:
            self_test()
            return 0
        if args.mode == "choose-effort" and not args.effort:
            raise PrerequisiteHold("choose-effort requires explicit --effort; unattended queue never reads stdin")
        if args.effort and args.mode != "choose-effort":
            raise PrerequisiteHold("--effort is only a predeclared choice; other modes consume its immutable report")
        target, info = check(args.mode)
        if args.check_only:
            print(json.dumps(info, ensure_ascii=False, sort_keys=True))
            return 0
        began = time.monotonic()
        choice_report = choose_effort(info, args.effort) if args.mode == "choose-effort" else None
        if args.mode in ("parent-b", "effort-panel", "correct-pilot", "correct", "train-a", "train-b"):
            idle_before_gpu()
        target.mkdir(parents=True, exist_ok=False)
        # Full96 teacher work is conditional on the short four-profile gate.
        # The old pilot cost already extrapolates beyond the former two-hour cap.
        with wall_limit(info["hard_wall_sec"]):
            if args.mode == "parent-b":
                report = parent_baseline(target, info)
            elif args.mode == "effort-panel":
                report = effort_panel(target, info)
            elif args.mode == "choose-effort":
                report = choice_report
            elif args.mode in ("correct", "correct-pilot"):
                report = correct(target, info, whole_began=began)
            elif args.mode == "prepare":
                report = prepare_corpus(target, info)
            elif args.mode.startswith("train-"):
                report = educate(target, info, args.mode[-1])
            else:
                report = compare(info)
        report.setdefault("whole_wall_sec", time.monotonic() - began)
        if args.mode not in ("correct", "correct-pilot"):
            report["report_domains"] = separated_report(report)
            write_report(target / "report.json", report)
        print("[EDUCATION_SUMMARY] " + json.dumps(report, ensure_ascii=False), flush=True)
        return 8 if report.get("operational_safety") is False else 0
    except (Exception, KeyboardInterrupt) as exc:
        status, rc = disposition(exc)
        if target and target.is_dir() and not (target / "failure.json").exists():
            write_report(target / "failure.json", {"status": status, "exit_code": rc,
                "reason": f"{type(exc).__name__}: {str(exc)[:250]}", "formal_train_ready": False})
        print(f"[{status}] {type(exc).__name__}: {str(exc)[:250]}", file=sys.stderr)
        return rc


if __name__ == "__main__":
    raise SystemExit(main())
