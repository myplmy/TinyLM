"""Train a matched uniform/adaptive MNTP pair on the admitted v1.1 document cache."""

import argparse
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import asdict
from datetime import datetime
from functools import partial
import gc
import hashlib
import json
import math
import os
from pathlib import Path
import random
import sys
import time
import traceback
from unittest.mock import patch

import numpy as np
import torch

from scripts import eval_p109c_completed as evaluation
from scripts import p102a_fp32_target_head as target_head
from scripts import p107_v11_binary_documents as documents
from scripts import p109_gpu_supervisor as telemetry
from scripts import run_p109c_scratch330 as supervisor
from tinylm.config import PRESETS
from tinylm.model import TiedMLPTransformer
from tinylm.train import adaptive_training
from tinylm.train.adaptive_masking import PolicyConfig
from tinylm.train.anneal_schedule import quant_anneal_factor, resolve_quant_start
from tinylm.train.experimental_optimizers import build_experimental_optimizers
from tinylm.train.hybrid_mntp import causal_batch
from tinylm.train.hybrid_session import HybridTrainingSession
from tinylm.train.packed_document_training import save_packed_checkpoint


ARMS = ("observe", "adaptive")
SEED, LENGTH, BATCH, MICROS = 1337, 1024, 4, 32
STEPS, WARMUP, PROBE, CE_ROWS = 2289, 100, 16, 512
SLOTS = LENGTH * BATCH * MICROS
SOURCES = (
    "scripts/run_p107_v11_mask_pair.py", "scripts/p107_v11_binary_documents.py",
    "scripts/p102a_fp32_target_head.py", "scripts/run_p109c_scratch330.py", "scripts/p109_gpu_supervisor.py",
    "tinylm/config.py", "tinylm/model/transformer.py", "tinylm/model/visibility.py",
    "tinylm/model/modules.py", "tinylm/model/ternary.py",
    "tinylm/train/adaptive_training.py", "tinylm/train/adaptive_masking.py",
    "tinylm/train/anneal_schedule.py", "tinylm/train/hybrid_mntp.py",
    "tinylm/train/hybrid_session.py", "tinylm/train/muon.py",
    "tinylm/train/packed_document_training.py", "tinylm/train/experimental_optimizers.py",
)


class DocumentG4(TiedMLPTransformer):
    def forward(self, tokens, *, attention_mask=None):
        return super().forward(tokens, attention_mask=attention_mask,
                               allow_fixed_g4_r2=attention_mask is not None)


class HiddenForCE:
    def __init__(self, hidden):
        self.hidden = hidden
        self.predictions = None

    def detach(self):
        if self.predictions is None:
            raise ValueError("a masked forward did not collect its selected prediction IDs")
        return self.predictions


def source_pins():
    return {name: evaluation.core6.digest(evaluation.ROOT / name) for name in SOURCES}


def load_index(path, sha256):
    inputs = json.loads(supervisor.manifest_bytes(path, sha256))
    if (inputs["schema"] != "P107_V11_BINARY_DOCUMENTS_V1"
            or set(inputs["splits"]) != set(documents.SPLITS)
            or inputs["tokenizer_sha256"] != evaluation.TOKENIZER_SHA
            or inputs["splits"]["train"]["tokens"] < 2 * STEPS * SLOTS
            or any(receipt["literal_mask_tokens"] for receipt in inputs["splits"].values())
            or inputs["sources"]["scripts/p107_v11_binary_documents.py"] != source_pins()["scripts/p107_v11_binary_documents.py"]):
        raise ValueError("the admitted v1.1 document splits do not cover the planned experiment")
    return inputs


def make_session(profile, corpus, arm):
    torch.manual_seed(SEED)
    random.seed(SEED)
    np.random.seed(SEED)
    source = documents.BinaryDocumentSource(corpus["train"], batch=BATCH, length=LENGTH, micros=MICROS, seed=SEED)
    cfg = PRESETS[supervisor.PRESET](LENGTH, profile["activation_checkpointing"])
    cfg.train_repeat, cfg.infer_repeat = 2., 1.
    model = DocumentG4(cfg).to(profile["device"]).train()
    if len(model.visit_schedule()) != 28:
        raise ValueError("fixed training and evaluation must share the 28-visit route")
    optimizer = build_experimental_optimizers(model, "muon_matched", lr=.001, matrix_lr_mult=4.)
    signature = hashlib.sha256(
        (profile["sources"]["scripts/run_p107_v11_mask_pair.py"] + source.signature + arm
         + profile["device"]).encode()).hexdigest().upper()
    policy = PolicyConfig(supervisor.VOCAB, .15, .2, 2, "keep", SEED, 34, documents.MASK,
                          source.corpus_sha256, signature)
    trainer = adaptive_training.AdaptiveMNTPTrainer(
        model, (optimizer.matrix, optimizer.adamw), source, policy_config=policy, mode=arm,
        masked_micros=MICROS // 2, signature=signature, clip=1.,
        collect_ids=lambda ids, _: ids.cpu(), autocast_dtype=torch.bfloat16,
    )
    return HybridTrainingSession(trainer, total_updates=STEPS, warmup_updates=WARMUP, schedule="wsd")


@torch.no_grad()
def causal_validation(model, source, cutoff):
    start = time.monotonic()
    model.eval()
    model.freeze_quant()
    total, targets = 0., 0
    try:
        for tokens, docs in source.next_update():
            if time.time() >= cutoff:
                raise TimeoutError("not enough authorized time for the paired causal validation")
            batch = causal_batch(tokens, docs, vocab_size=supervisor.VOCAB)
            device = next(model.parameters()).device
            with torch.autocast(device.type, dtype=torch.bfloat16):
                logits = model(batch.inputs.to(device), attention_mask=batch.attention_mask.to(device))
                summed = torch.nn.functional.cross_entropy(logits.flatten(0, 1).float(),
                    batch.targets.flatten().to(device), ignore_index=-100, reduction="sum")
            total += float(summed)
            targets += batch.target_count
    finally:
        model.clear_quant()
        model.train()
    return dict(nll=total / targets, validation_source="ADMITTED_V11_VAL_EXPLICIT_DOCUMENTS",
                target_count=targets, seconds=time.monotonic() - start)


def write_boundary(session, profile, initial, directory):
    path = directory / f"step_{session.cursor}.pt"
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    state = session.state_dict()
    save_packed_checkpoint(path, dict(session=state, initial_sha256=initial, profile=profile,
                                     cfg=asdict(session.trainer.model.cfg)))
    receipt = dict(path=str(path), sha256=evaluation.core6.digest(path), updates=session.cursor,
                   slots=session.cursor * SLOTS)
    supervisor.publish(path.with_suffix(".json"), receipt)
    return receipt


def train_arm(profile, corpus, arm, end, record, cutoff, resume=None):
    from scripts.interactive_research_infer import state_fingerprint
    from torch.nn.attention import SDPBackend, sdpa_kernel

    directory = record / arm
    directory.mkdir(exist_ok=resume is not None)
    session = make_session(profile, corpus, arm)
    model = session.trainer.model
    initial = state_fingerprint(model)
    if resume is not None:
        path = evaluation.regular_file(Path(resume["path"]))
        if evaluation.core6.digest(path) != resume["sha256"]:
            raise ValueError("the selected boundary changed")
        state = torch.load(path, map_location="cpu", weights_only=True, mmap=True)
        if state["initial_sha256"] != initial or state["profile"] != profile:
            raise ValueError("the matched initializer or profile changed during replay")
        session.load_state_dict(state["session"])
        del state

    initial_cursor = session.cursor
    validation = documents.BinaryDocumentSource(corpus["val"], batch=BATCH, length=LENGTH, micros=16, seed=99)
    forwards = 0

    def objective(output, targets):
        nonlocal forwards
        masked = forwards % MICROS >= MICROS // 2
        value, count, ids = target_head.objective(model, output.hidden, targets, rows=CE_ROWS, collect_ids=masked)
        output.predictions = ids
        forwards += 1
        return value, count

    target_start = resolve_quant_start(WARMUP, STEPS)
    elapsed, raw_counts, validation_receipts = [], [], []
    with (directory / f"updates_after_{initial_cursor}.jsonl").open("x", encoding="utf-8", buffering=1) as log:
        with sdpa_kernel(SDPBackend.MATH):
            for absolute in range(initial_cursor, end):
                if time.time() >= cutoff:
                    raise TimeoutError("the authorized training cutoff was reached")
                anneal = quant_anneal_factor(absolute, STEPS, "wsd", "linear", target_start, .60)
                model.set_anneal(anneal)
                with (patch.object(model, "_head_logits", HiddenForCE),
                      patch.object(adaptive_training, "objective_mean", objective)):
                    row = session.update()
                if (row["status"] != "COMPLETE" or row["update"] != absolute
                        or row["executed_input_tokens"] != SLOTS or forwards != (absolute+1-initial_cursor)*MICROS
                        or session.trainer.source.cursor != session.cursor
                        or row["observed_micro_batches"] != MICROS // 2):
                    raise RuntimeError("matched training input or applied optimizer accounting differs")
                row["anneal"] = anneal
                raw_counts.append((row["causal_targets"], row["masked_targets"]))
                log.write(json.dumps(row, allow_nan=False) + chr(10))
                elapsed.append(row["seconds"])
                if absolute < initial_cursor + 2 or (absolute+1) % 20 == 0:
                    print("P107_V11_UPDATE", arm, absolute+1, row["loss"], row["seconds"], flush=True)
                if (absolute+1) % 512 == 0 and absolute+1 != end:
                    proof = write_boundary(session, profile, initial, directory)
                    validation_receipts.append(dict(step=absolute+1, boundary=proof))
            measured = causal_validation(model, validation, cutoff)
    final_boundary = write_boundary(session, profile, initial, directory)
    if end == STEPS:
        checkpoint = directory / "evaluation.pt"
        save_packed_checkpoint(checkpoint, dict(model=model.state_dict(), cfg=asdict(model.cfg),
                               step=end, tokenizer_sha256=evaluation.TOKENIZER_SHA))
        final_boundary["evaluation"] = documents.pin(checkpoint)
    result = dict(arm=arm, initial_sha256=initial, start=initial_cursor, end=end,
                  final=final_boundary, intermediate=validation_receipts, seconds=elapsed,
                  causal_targets=sum(row[0] for row in raw_counts), masked_targets=sum(row[1] for row in raw_counts),
                  source_end_rng=hashlib.sha256(session.trainer.source.rng.get_state().numpy()).hexdigest().upper(),
                  causal_validation=measured)
    supervisor.publish(directory / f"receipt_{end}.json", result)
    return result


def worker(path, sha256, _resume, record, cutoff):
    profile = json.loads(supervisor.manifest_bytes(path, sha256))
    if profile["sources"] != source_pins() or profile["device"] != "cuda":
        raise ValueError("the exact CUDA preparation contract is required")
    corpus = load_index(Path(profile["index"]), profile["index_sha256"])["splits"]
    if torch.cuda.device_count() != 1:
        raise ValueError("one reserved CUDA device is required")
    total_mib, used_mib, _ = telemetry.gpu_status(record)
    allocator_budget_mib = supervisor.CARD_LIMIT_MIB - used_mib - 384
    if allocator_budget_mib <= 0:
        raise RuntimeError("the monitored card cap leaves no room for training allocations")
    torch.cuda.set_per_process_memory_fraction(allocator_budget_mib / total_mib)
    torch.set_num_threads(2)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    started = time.monotonic()
    result = dict(status="STARTED", probe={}, arms={}, profile_sha256=supervisor.digest(sha256),
                  allocator_budget_mib=allocator_budget_mib)
    with ((record / "stdout.txt").open("x", encoding="utf-8", buffering=1) as log,
          redirect_stdout(log), redirect_stderr(log)):
        try:
            for arm in ARMS:
                result["probe"][arm] = train_arm(profile, corpus, arm, PROBE, record, cutoff)
                gc.collect()
                torch.cuda.empty_cache()
            control, candidate = (result["probe"][arm] for arm in ARMS)
            if any(control[key] != candidate[key] for key in ("initial_sha256", "causal_targets", "source_end_rng")):
                raise ValueError("the two arms do not share initialized weights and original windows")
            p90 = {arm: float(np.percentile(result["probe"][arm]["seconds"][4:], 90)) for arm in ARMS}
            possible = PROBE + math.floor((cutoff - time.time() - 300) / (sum(p90.values()) * 1.25))
            maximum = STEPS if possible >= STEPS else max(PROBE, 128*(possible//128))
            result["budget"] = dict(p90_seconds=p90, remaining_seconds=cutoff-time.time(),
                                    planned_per_arm=maximum, full_steps=STEPS)
            supervisor.publish(record / "budget.json", result["budget"])
            print("P107_V11_PAIR_BUDGET", result["budget"], flush=True)
            if maximum < 512:
                result["status"] = "PROBE_COMPLETE_TIME_HOLD"
                return
            for arm in ARMS:
                result["arms"][arm] = train_arm(profile, corpus, arm, maximum, record, cutoff,
                                                resume=result["probe"][arm]["final"])
                gc.collect()
                torch.cuda.empty_cache()
            control, candidate = (result["arms"][arm] for arm in ARMS)
            if any(control[key] != candidate[key] for key in ("initial_sha256", "causal_targets", "source_end_rng")):
                raise ValueError("the completed compare pair differs in initialized weights or raw exposures")
            if profile["sources"] != source_pins():
                raise ValueError("the confirmed training sources changed")
            result["status"] = "FULL_300M_PAIR" if maximum == STEPS else "MATCHED_PARTIAL_BUDGET_PAIR"
        except BaseException as error:
            traceback.print_exc()
            result.update(status="ERROR", error_type=type(error).__name__, error=str(error))
            raise
        finally:
            result["wall_seconds"] = time.monotonic() - started
            result["peak_allocated_mib"] = torch.cuda.max_memory_allocated() / 2**20
            result["peak_reserved_mib"] = torch.cuda.max_memory_reserved() / 2**20
            supervisor.publish(record / "report.json", result)


def wait_for_evaluation(path, deadline):
    print("P107_V11_WAIT_FOR_P109C", path, flush=True)
    terminal = path / "supervisor.json"
    while time.time() < deadline:
        if terminal.is_file():
            try:
                receipt = evaluation.read_json(terminal)
            except json.JSONDecodeError:
                pass
            else:
                if (receipt["returncode"] != 0 or receipt["stop_reason"] is not None
                        or receipt["card_after_exit"].get("compute_pids") != []
                        or evaluation.read_json(path / "report.json")["status"] != "COMPLETE"):
                    raise RuntimeError("P109C needs completion or recovery before the next GPU job")
                return
        time.sleep(5.)
    raise TimeoutError("P109C did not release the GPU with enough time for the next matched probe")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="mode", required=True)
    prep = sub.add_parser("prepare")
    prep.add_argument("--index", required=True, type=Path)
    prep.add_argument("--index-sha256", required=True)
    prep.add_argument("--profile", required=True, type=Path)
    run = sub.add_parser("run")
    run.add_argument("--profile", required=True, type=Path)
    run.add_argument("--profile-sha256", required=True)
    run.add_argument("--record", required=True, type=Path)
    run.add_argument("--stop-by", required=True, type=datetime.fromisoformat)
    run.add_argument("--after-evaluation", type=Path)
    args = parser.parse_args()
    path = args.profile.absolute()
    if args.mode == "prepare":
        index = args.index.absolute()
        inputs = load_index(index, args.index_sha256)
        receipt = evaluation.read_json(index.with_name("window_check.json"))
        if any(not counts["same_replay"] or counts["full_input_slots"] != SLOTS for counts in receipt.values()):
            raise ValueError("the actual CPU windows and replay must be verified")
        profile = dict(schema="P107_ADOPTED_V11_MASK_PAIR_V1", device="cuda", sources=source_pins(),
                       index=str(index), index_sha256=supervisor.digest(args.index_sha256),
                       source_release_sha256=inputs["source_release_sha256"], arms=list(ARMS),
                       train_pool=inputs["splits"]["train"]["tokens"], max_slots_per_arm=STEPS*SLOTS,
                       activation_checkpointing=True, validation=receipt)
        supervisor.publish(path, profile)
        print("P107_V11_PAIR_PROFILE", path, evaluation.core6.digest(path), flush=True)
        return 0
    if args.stop_by.tzinfo is None:
        parser.error("--stop-by needs a UTC offset")
    if args.after_evaluation is not None:
        wait_for_evaluation(args.after_evaluation.absolute(), args.stop_by.timestamp() - 900)
    record = args.record.absolute()
    with (patch.object(supervisor, "gpu_worker", worker),
          patch.object(supervisor, "gpu_status", partial(telemetry.gpu_status, record))):
        return supervisor.supervise(path, args.profile_sha256, False, record, args.stop_by)


if __name__ == "__main__":
    sys.exit(main())
