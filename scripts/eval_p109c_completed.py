"""Evaluate the admitted P109C completion with the pinned offline tasks."""

import argparse
from collections import Counter
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime
from functools import partial
import json
import math
import os
from pathlib import Path
import sys
import sysconfig
import time
import traceback
from unittest.mock import patch

from scripts import diag_p106b_official_core6 as core6
from scripts import p109_gpu_supervisor as telemetry
from scripts import resume_p109c_scratch330 as recovery
from scripts import run_p109c_scratch330 as training
from scripts.p106b_shards import ShardWriter, verify as verify_shards


ROOT = core6.ROOT
TOKENIZER = ROOT / "data_cache/tok-ko-en-32768-chat32.json"
TOKENIZER_SHA = "9716F40E4C504D6AF37DDE76CCA578E30B45E9CA86C8B6BB79B2FA095D3AC88E"
FINAL200 = ROOT / "data_cache/p106b_final200_v2_20261101"
FINAL200_SHA = "DD4E185752771528AE009C73D7BD6FEC00CF6C53E3A725CDAEDF091015C475AD"
MODEL_NAME = "p109c-scratch330-v1"
STAGE_GROUPS = ("first_use", "core6", "korean_choices", "final200")
SOURCE_FILES = set(core6.SOURCES) | {
    "scripts/eval_p109c_completed.py", "scripts/eval_p109b_first_use.py",
    "scripts/p106b_final_holdout.py", "scripts/diag_p106b_bonsai_native_mc.py",
    "scripts/diag_p106b_kobest_exact_followups.py", "scripts/diag_p106b_belebele.py",
    "scripts/run_p109c_scratch330.py", "scripts/resume_p109c_scratch330.py", "scripts/p109_gpu_supervisor.py",
    "tinylm/config.py", "tinylm/chat/serialize.py",
    "tinylm/infer/generate.py", "tinylm/model/transformer.py", "tinylm/model/ternary.py",
    "tinylm/model/modules.py", "tinylm/model/visibility.py", "tinylm/data/prepare.py",
}


def read_json(path):
    return json.loads(path.read_bytes())


def regular_file(path):
    if path.resolve(strict=True) != path or not path.is_file():
        raise ValueError(f"an unlinked project file is required: {path}")
    return path


def source_pins():
    return {name: core6.digest(regular_file(ROOT / name)) for name in sorted(SOURCE_FILES)}


def load_tokenizer():
    from tokenizers import Tokenizer
    from tinylm.data.prepare import verify_chat_tokenizer

    if core6.digest(regular_file(TOKENIZER)) != TOKENIZER_SHA:
        raise ValueError("the admitted chat32 tokenizer identity differs")
    tokenizer = Tokenizer.from_file(str(TOKENIZER))
    tokens = verify_chat_tokenizer(tokenizer, training.VOCAB)
    if tuple(tokens[name] for name in ("<pad>", "<bos>", "<eos>", "<|im_start|>", "<|im_end|>")) != (0, 1, 2, 3, 4):
        raise ValueError("the exact stop and prefix ID contract differs")
    return tokenizer


def final200_inputs():
    from scripts import p106b_final_holdout as data

    manifest = read_json(regular_file(FINAL200 / "manifest.json"))
    final = read_json(regular_file(FINAL200 / "final.json"))
    dev = read_json(regular_file(FINAL200 / "dev.json"))
    if (core6.digest(FINAL200 / "manifest.json") != FINAL200_SHA
            or data.validate(final, dev) != manifest["contract"]
            or manifest["tokenizer_sha256"] != TOKENIZER_SHA
            or manifest["max_new"] != data.MAX_NEW):
        raise ValueError("the frozen FINAL200 inputs differ")
    return final, manifest["contract"]


def load_inputs(groups):
    from scripts.prepare_p106b_official_eval import configure_hf_cache, MANIFEST_SHA

    os.environ.update(core6.OFFLINE, HF_EVALUATE_OFFLINE="1", HF_HUB_DISABLE_TELEMETRY="1")
    configure_hf_cache()
    tasks, proofs = {}, {}
    if "core6" in groups:
        from scripts.p106b_official_tasks import load_tasks

        suite, _, provenance = load_tasks()
        if {name: len(task.eval_docs) for name, task in suite.items()} != core6.TASK_COUNTS:
            raise ValueError("the Core6 denominators differ")
        tasks["core6"] = suite
        proofs["core6"] = dict(framework_commit=provenance["framework_source_commit"], manifest_sha256=MANIFEST_SHA,
                               rows=core6.TASK_COUNTS)
    if "korean_choices" in groups:
        from scripts import diag_p106b_bonsai_native_mc as choice

        suite, asset_pins, _ = choice.load_tasks()
        items, receipts = choice.prepare_items(suite)
        tasks["korean_choices"] = (suite, items)
        proofs["korean_choices"] = dict(assets=asset_pins, requests=receipts)
    if "final200" in groups:
        tasks["final200"], proofs["final200"] = final200_inputs()
    return tasks, proofs


def training_input(path, manifest_sha256):
    receipt = read_json(regular_file(path / "input.json"))
    slots = training.STEPS * training.MICRO * training.ACCUM * training.WIDTH
    if (receipt["manifest_sha256"] != training.digest(manifest_sha256)
            or receipt["updates"] != training.STEPS or receipt["input_slots"] != slots
            or receipt["tokenizer_sha256"] != TOKENIZER_SHA):
        raise ValueError("the input does not describe the admitted P109C run")
    return receipt


def completed_checkpoint(path, manifest_sha256):
    receipt = training_input(path, manifest_sha256)
    supervisor = read_json(regular_file(path / "supervisor.json"))
    if supervisor["returncode"] != 0 or supervisor["stop_reason"] is not None:
        raise ValueError("the P109C supervisor did not close successfully")
    if supervisor["card_after_exit"].get("compute_pids") != []:
        raise ValueError("the completed P109C run has no confirmed device return")
    checkpoint = regular_file(path / "evaluation.pt")
    result = read_json(regular_file(path / "training.json"))
    updates = result["updates"]
    stamp = core6.digest(checkpoint)
    prefix = path / "resume_prefix.json"
    start = 0
    if prefix.exists():
        proof = read_json(regular_file(prefix))
        original = regular_file(Path(proof["original_checkpoint"]))
        prior = Path(proof["original_record"])
        start = proof["step"]
        verified = recovery.inspect(original, proof["original_checkpoint_sha256"], start,
                                    receipt["manifest_sha256"], prior)
        if proof != verified or read_json(regular_file(prior / "input.json")) != receipt:
            raise ValueError("the original checkpoint does not close the resumed prefix")
    slots = training.MICRO * training.ACCUM * training.WIDTH
    if (len(updates) != receipt["updates"] - start or result["evaluation_sha256"] != stamp
            or any(row["index"] != index or not row["optimizer_applied"] or row["draw_tokens"] != slots
                   for index, row in enumerate(updates, start))):
        raise ValueError("training completion or evaluation artifact identity differs")
    return checkpoint, stamp


def load_model(path, step, device):
    import torch
    from tinylm.config import TMTConfig
    from tinylm.model import TiedMLPTransformer

    state = torch.load(path, map_location="cpu", weights_only=True, mmap=True)
    if state["step"] != step or state["tokenizer_sha256"].upper() != TOKENIZER_SHA:
        raise ValueError("the strict checkpoint header differs")
    cfg = TMTConfig(**state["cfg"])
    if ((cfg.n_prelude, cfg.n_middle, cfg.n_coda, cfg.mlp_group, cfg.cla_group) != (2, 12, 2, 4, 2)
            or not cfg.tie_mlp or cfg.train_repeat != 2.0 or cfg.vocab_size != training.VOCAB
            or cfg.max_seq_len != training.WIDTH or cfg.mtp_aux):
        raise ValueError("the model must be the native G4 R2, 1,024-context P109C")
    cfg.infer_repeat = 2.0
    model = TiedMLPTransformer(cfg)
    model.load_state_dict(state["model"], strict=True)
    model = model.to(device=device, dtype=torch.float32).eval()
    model.set_anneal(1.)
    model.freeze_quant()
    if len(model.visit_schedule()) != 28:
        raise ValueError("the shared model does not have the fixed 28-visit inference route")
    return model


def evaluate_core6(lm, tasks, record, check):
    from lm_eval.evaluator import simple_evaluate
    from lm_eval.tasks import TaskManager
    from scripts.prepare_p106b_official_eval import COMMIT

    manager = TaskManager()
    summary = {}
    for name in core6.TASK_COUNTS:
        check()
        task = tasks[name]
        count = core6.TASK_COUNTS[name]
        lengths = ShardWriter(record, name + "_lengths")
        started = time.monotonic()
        with core6.length_observer(lm, lengths) as length_summary:
            result = simple_evaluate(
                model=lm, tasks=[task], num_fewshot=0, task_manager=manager, batch_size=8,
                device="cuda", use_cache=None, cache_requests=False, limit=None,
                bootstrap_iters=100000, log_samples=True, apply_chat_template=False,
                fewshot_as_multiturn=False, random_seed=1337, numpy_random_seed=1337,
                torch_random_seed=1337, fewshot_random_seed=1337,
            )
        if set(result["samples"]) != {name}:
            raise ValueError("the requested official task did not produce one sample collection")
        rows = result.pop("samples")[name]
        audit = core6.audit_samples(task, rows, count)
        for metric, field in (("acc", "correct"), ("acc_norm", "correct_norm")):
            official = result["results"][name].get(metric + ",none")
            if official is not None and not math.isclose(official, audit[field] / count, abs_tol=1e-12):
                raise ValueError("the official aggregate disagrees with the independent recount")
        lineage = dict(model=MODEL_NAME, task=name, framework_commit=COMMIT, mode="full")
        writer = ShardWriter(record, name + "_samples")
        for row in rows:
            writer.append(core6.plain(row))
        samples_manifest = writer.close(lineage=lineage)
        lengths_manifest = lengths.close(lineage=lineage)
        verify_shards(record, samples_manifest)
        verify_shards(record, lengths_manifest)
        summary[name] = dict(rows=count, audit=audit, official=core6.plain(result["results"][name]),
                             samples=samples_manifest, lengths=lengths_manifest,
                             length_summary=length_summary, seconds=time.monotonic() - started)
        training.publish(record / f"{name}.json", summary[name])
        print("CORE6_TASK_COMPLETE", name, count, summary[name]["seconds"], flush=True)
    return summary


def evaluate_korean_choices(lm, inputs, record, check):
    from scripts import diag_p106b_bonsai_native_mc as choice
    from scripts.diag_p106b_kobest_exact_followups import score

    tasks, items = inputs
    summary = {}
    for name, task in tasks.items():
        writer = ShardWriter(record, name + "_samples")
        rows = []
        started = time.monotonic()
        for offset in range(0, len(items[name]), 32):
            check()
            batch = items[name][offset:offset + 32]
            for item, response in zip(batch, score(lm, name, batch), strict=True):
                pred, norm, metrics = choice.item_score(task, item, response)
                row = dict(item, pred=pred, pred_norm=norm, metrics=metrics, responses=response)
                writer.append(row)
                rows.append(row)
        manifest = writer.close(lineage=dict(model=MODEL_NAME, task=name, mode="full"))
        verify_shards(record, manifest)
        summary[name] = dict(rows=len(rows), samples=manifest, seconds=time.monotonic() - started,
                             **choice.aggregate(task, rows))
        training.publish(record / f"{name}.json", summary[name])
        print("OFFICIAL_CHOICE_TASK_COMPLETE", name, len(rows), summary[name]["metrics"], flush=True)
    return summary


def evaluate_generation(group, runtime, record, rows, check):
    from scripts import eval_p109b_first_use as first
    from scripts import interactive_research_infer as manual
    from scripts import p106b_final_holdout as final
    from tinylm.chat.serialize import serialize
    from tinylm.infer.generate import sample

    torch, tokenizer, model = (runtime[name] for name in ("torch", "tokenizer", "model"))
    first_use = group == "first_use"
    cases = first.examples(tokenizer) if first_use else rows
    budget = first.ANSWER if first_use else final.MAX_NEW
    captures = ShardWriter(record, group + "_answers")
    by_language = {name: Counter(rows=0) for name in ("ko", "en")}
    started = time.monotonic()
    for case in cases:
        check()
        prompt = case["prompt"] if first_use else serialize(
            {"messages": manual.prompt_messages(case["prompt"])}, "chatml", add_generation_prompt=True)
        ids = tokenizer.encode(prompt).ids
        if len(ids) + budget > model.cfg.max_seq_len:
            raise ValueError("the frozen prompt would be clipped")
        capture = first.DecodeSuffix(tokenizer, ids)
        with torch.autocast("cuda", enabled=first_use, dtype=torch.bfloat16):
            _, metadata = sample(model, model.cfg, capture, prompt, max_new=budget,
                                 temperature=0., top_k=0 if first_use else 1, device="cuda",
                                 eos_id=2, use_cache=True, logits_last_only=True,
                                 return_metadata=True, stop_token_sequences=[[4]])
        answer, metadata = manual.answer_from_tokens(tokenizer, ids, ids + capture.ids, metadata, budget)
        record_case = {key: value for key, value in case.items() if key != "input_ids"}
        stop = metadata["finish_reason"] in ("EOS", "STOP_SEQUENCE")
        repeated = first.repeat_tail(metadata["generated_ids"])
        counts = by_language[case["language"]]
        counts.update(dict(rows=1, empty=int(not answer.strip()), stop=int(stop),
                           capped=int(not stop), repeat_tail=int(repeated)))
        if first_use:
            visible_answer = tokenizer.decode(capture.ids, skip_special_tokens=True)
            match = first.strict(visible_answer) == first.strict(case["answer"])
            record_case["expected"] = record_case.pop("answer")
        else:
            match = final.reference_match(answer, case)
            record_case.update(review_signals=final.review_signals(answer, metadata, case),
                               semantic_review="NOT_RUN")
        if match is not None:
            counts.update(reference_rows=1, reference_match=int(match))
        captures.append(dict(record_case, model=MODEL_NAME, answer=answer, metadata=metadata,
                             repeat_tail=repeated, reference_match=match))
    manifest = captures.close(lineage=dict(model=MODEL_NAME, task=group, max_new=budget,
                                          precision="BF16_MATH" if first_use else "FP32_MATH"))
    verify_shards(record, manifest)
    return dict(rows=len(cases), answers=manifest, by_language=by_language,
                elapsed_seconds=time.monotonic() - started)


def run_worker(profile_path, profile_sha256, resume, record, cutoff):
    import torch
    from torch.nn.attention import SDPBackend, sdpa_kernel
    from scripts.p106b_official_lm_adapter import create_adapter

    def check():
        if time.time() >= cutoff:
            raise TimeoutError("the authorized evaluation cutoff was reached")

    profile = json.loads(training.manifest_bytes(profile_path, profile_sha256))
    if profile["sources"] != source_pins():
        raise ValueError("a sealed evaluation source changed")
    tasks, proofs = load_inputs(profile["groups"])
    if json.loads(json.dumps(proofs)) != profile["inputs"]:
        raise ValueError("a sealed evaluation input changed")
    checkpoint, checksum = completed_checkpoint(Path(profile["training_record"]), profile["training_manifest_sha256"])
    checkpoint_stamp = training.file_stamp(checkpoint)
    check()
    if not torch.cuda.is_available() or torch.cuda.device_count() != 1:
        raise RuntimeError("one assigned CUDA device is required")
    torch.set_num_threads(4)
    torch.manual_seed(1337)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    model = load_model(checkpoint, training.STEPS, "cuda")
    runtime = dict(torch=torch, model=model, cfg=model.cfg, tokenizer=load_tokenizer(),
                   precision="FP32_MATH", checkpoint=str(checkpoint),
                   checkpoint_sha256=checksum, tokenizer_sha256=TOKENIZER_SHA)
    report = dict(model=MODEL_NAME, model_sha256=checksum, profile_sha256=training.digest(profile_sha256),
                  parameters=sum(p.numel() for p in model.parameters()), groups={}, status="STARTED")
    adapter = None
    try:
        with torch.no_grad(), sdpa_kernel(SDPBackend.MATH):
            if {"core6", "korean_choices"} & set(profile["groups"]):
                adapter = create_adapter(runtime, runtime_root=Path(sysconfig.get_paths()["purelib"]), batch_size=8)
                report["numerical_canary"] = core6.numerical_canary(adapter, torch)
            for group in profile["groups"]:
                check()
                if group == "core6":
                    result = evaluate_core6(adapter, tasks[group], record, check)
                elif group == "korean_choices":
                    result = evaluate_korean_choices(adapter, tasks[group], record, check)
                else:
                    result = evaluate_generation(group, runtime, record, tasks.get(group), check)
                report["groups"][group] = result
                training.publish(record / f"{group}.json", result)
                print("P109C_EVAL_GROUP_COMPLETE", group, flush=True)
        if source_pins() != profile["sources"] or checkpoint_stamp != training.file_stamp(checkpoint):
            raise ValueError("evaluation sources or the admitted checkpoint changed")
        report["status"] = "COMPLETE"
    except BaseException as error:
        report.update(status="ERROR", error_type=type(error).__name__, error=str(error))
        raise
    finally:
        if adapter is not None:
            adapter.close()
        report["peak_allocated_mib"] = torch.cuda.max_memory_allocated() / 2**20
        report["peak_reserved_mib"] = torch.cuda.max_memory_reserved() / 2**20
        training.publish(record / "report.json", report)


def worker(profile, checksum, resume, record, cutoff):
    with ((record / "stdout.txt").open("x", encoding="utf-8", buffering=1) as output,
          redirect_stdout(output), redirect_stderr(output)):
        try:
            run_worker(profile, checksum, resume, record, cutoff)
        except BaseException:
            traceback.print_exc()
            raise


def wait_for_training(path, pid, deadline):
    print("P109C_EVAL_WAIT", pid, path, flush=True)
    receipt = path / "supervisor.json"
    telemetry = path / "gpu.csv"
    while True:
        if receipt.exists():
            try:
                closed = read_json(receipt)
            except json.JSONDecodeError:
                pass
            else:
                if closed["pid"] != pid:
                    raise ValueError("the training handover belongs to a different worker")
                return
        if time.time() >= deadline:
            raise TimeoutError("the training handover did not fit the authorized window")
        if time.time() - telemetry.stat().st_mtime > 120:
            raise RuntimeError("the training supervisor stopped reporting without a valid receipt")
        time.sleep(2)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    actions = parser.add_subparsers(dest="action", required=True)
    prepare = actions.add_parser("prepare")
    prepare.add_argument("--training-record", type=Path, required=True)
    prepare.add_argument("--training-manifest-sha256", required=True)
    prepare.add_argument("--groups", nargs="+", choices=STAGE_GROUPS, default=STAGE_GROUPS)
    prepare.add_argument("--profile", type=Path, required=True)
    run = actions.add_parser("run")
    run.add_argument("--profile", type=Path, required=True)
    run.add_argument("--profile-sha256", required=True)
    run.add_argument("--record", type=Path, required=True)
    run.add_argument("--stop-by", type=datetime.fromisoformat, required=True)
    run.add_argument("--wait-pid", type=int)
    args = parser.parse_args()
    profile_path = args.profile.absolute()
    if args.action == "prepare":
        if len(set(args.groups)) != len(args.groups):
            parser.error("evaluation groups must be unique")
        train_dir = args.training_record.absolute()
        training_input(train_dir, args.training_manifest_sha256)
        load_tokenizer()
        pins = source_pins()
        _, proofs = load_inputs(args.groups)
        if source_pins() != pins:
            raise ValueError("an evaluation source changed during preparation")
        training.publish(profile_path, dict(schema="P109C_COMPLETED_EVALUATION_V1",
            training_record=str(train_dir), training_manifest_sha256=training.digest(args.training_manifest_sha256),
            groups=args.groups, inputs=proofs, sources=pins, policy=core6.policy()))
        print("P109C_EVAL_PROFILE_READY", profile_path, core6.digest(profile_path), flush=True)
        return 0
    if args.stop_by.tzinfo is None:
        parser.error("--stop-by needs a UTC offset")
    profile = json.loads(training.manifest_bytes(profile_path, args.profile_sha256))
    train_dir = Path(profile["training_record"])
    if args.wait_pid is not None:
        wait_for_training(train_dir, args.wait_pid, args.stop_by.timestamp() - 35)
    completed_checkpoint(train_dir, profile["training_manifest_sha256"])
    record = args.record.absolute()
    with (patch.object(training, "gpu_worker", worker),
          patch.object(training, "gpu_status", partial(telemetry.gpu_status, record))):
        return training.supervise(profile_path, args.profile_sha256, False, record, args.stop_by)


if __name__ == "__main__":
    sys.exit(main())
