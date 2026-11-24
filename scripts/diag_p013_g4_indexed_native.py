"""Run the indexed packed, native G4 document path on the existing authored fixture."""

import argparse
from collections import Counter
from datetime import datetime, timedelta
import json
import math
import os
from pathlib import Path
import subprocess
import sys
from time import perf_counter

import torch
from tokenizers import Tokenizer
from torch.nn.attention import SDPBackend, sdpa_kernel

from scripts import diag_p013_g4_document_context as previous
from scripts.diag_p102a_g4_full_delta_train import state_sha
from scripts.diag_p102a_g4_recompute_shapes import idle
from scripts.diag_p107_hybrid_mntp import close_owned_cuda
from tinylm.model import TiedMLPTransformer
from tinylm.train import document_input
from tinylm.train.document_context_curriculum import backward_document_context, regroup_document_context
from tinylm.train.indexed_document_source import load_indexed_document_input


ROOT, warm, manual, sampling = previous.ROOT, previous.warm, previous.manual, previous.sampling
TAG = "p013_g4_indexed_native_v1_20261119"
OUT = previous.OUT.with_name(TAG)
PROFILE = OUT / "profile.json"
SEALED_PLAN = OUT / "plan_at_execution.md"
CPU_LOG = ROOT / "test_result/106_log_20261119_P013_Stage7W_NativeDocCPU.txt"
PLAN = previous.ContextPlan(((1, 256), (2, 512), (4, 1024)), 8, 2, 1024)
LIMIT = 100
VOCAB, SEED = 32768, 1337


def gate(reserve=0):
    if (OUT / "STOP").exists() or datetime.now(previous.END.tzinfo) + timedelta(seconds=reserve) >= previous.END:
        raise RuntimeError("owned STOP or deadline")


def file_ref(path):
    return dict(path=str(path.relative_to(ROOT)), bytes=path.stat().st_size, sha256=manual.file_sha(path))


def verify(profile):
    assert profile["tag"] == TAG and profile["authority"] == 177
    for name, expected in profile["pins"].items():
        assert manual.file_sha(ROOT / name) == expected, name


def source(profile):
    data = load_indexed_document_input(ROOT, profile["input_manifest"],
        allowed_root=str((OUT / "input").relative_to(ROOT)), tokenizer_sha256=previous.TOKENIZER_SHA,
        vocab_size=VOCAB, allow_admitted=False)
    assert data.contract["purpose"] == "SYNTHETIC_TECHNICAL"
    return data.as_source(batch=PLAN.micro_bs, length=PLAN.full_length, micros=PLAN.base_accum,
                          vocab=VOCAB, seed=SEED, packed=True)


def read_windows(stream):
    windows = stream.next_update()
    counts = [int((docs[:, 1:] == docs[:, :-1]).sum()) for _, docs in windows]
    assert all(bool((docs >= 0).all()) for _, docs in windows)
    return windows, dict(sha256=state_sha(windows), counts=counts, targets=sum(counts))


def prepare():
    assert not torch.cuda.is_initialized()
    original = previous.read(previous.SOURCE / "profile.json")
    earlier = previous.read(previous.PROFILE)
    earlier_result = previous.read(previous.OUT / "report.json")
    assert earlier_result["source_preserved"] and earlier_result["profile_sha256"] == manual.file_sha(previous.PROFILE)
    assert manual.file_sha(warm.PARENT) == original["sources"]["parent_sha"] == earlier["parent_sha256"]
    assert manual.file_sha(previous.TOKENIZER) == previous.TOKENIZER_SHA
    cpu_log = CPU_LOG.read_text(encoding="utf-8")
    assert "Ran 55 tests" in cpu_log and cpu_log.splitlines()[-1] == "EXIT 0"
    section = previous.PLAN.read_text(encoding="utf-8").split("### Stage7Wb ", 1)
    assert len(section) == 2 and TAG in section[1]
    tokenizer = Tokenizer.from_file(str(previous.TOKENIZER))
    rows, languages = [], Counter()
    for row in original["data"]["documents"]:
        if row["split"] == "train":
            languages[row["language"]] += 1
            ids = tokenizer.encode(row["text"], add_special_tokens=False).ids
            rows.append(dict(source_id=row["id"], token_ids=ids, language="synthetic",
                             source_sha256=document_input.sha256(row["text"].encode())))
    assert len(rows) == 768 and sum(len(row["token_ids"]) for row in rows) == earlier["pools"]["train"]["tokens"]
    directory = OUT / "input"
    directory.mkdir(parents=True, exist_ok=False)
    SEALED_PLAN.write_text("### Stage7Wb " + section[1], encoding="utf-8")
    shard, manifest = directory / "documents.jsonl", directory / "manifest.json"
    with shard.open("x", encoding="utf-8") as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False) + chr(10))
    previous.write(manifest, dict(schema=document_input.SCHEMA, purpose="SYNTHETIC_TECHNICAL", split="train",
        tokenizer=dict(sha256=previous.TOKENIZER_SHA, vocab_size=VOCAB),
        admission=dict(status="TECHNICAL_FIXTURE_ONLY", authority_ref="WIP177_AUTHORED_TECHNICAL",
                       training_authorized=False, evidence=None),
        shards=[dict(file=file_ref(shard), documents=len(rows), tokens=sum(len(row["token_ids"]) for row in rows))]))
    pin_names = (*warm.SOURCES, "tinylm/model/visibility.py", "tinylm/train/document_input.py",
                 "tinylm/train/indexed_document_source.py", "tinylm/train/context_curriculum.py",
                 "tinylm/train/document_context_curriculum.py", "tinylm/train/hybrid_mntp.py",
                 "scripts/test_p013_document_context_native.py", "scripts/test_p107_indexed_document_source.py")
    paths = (*(ROOT / name for name in pin_names), Path(__file__), CPU_LOG, SEALED_PLAN,
             manifest, shard, warm.PARENT, previous.TOKENIZER, previous.PROFILE, previous.OUT / "report.json",
             previous.SOURCE / "profile.json")
    profile = dict(tag=TAG, authority=177, input_manifest=file_ref(manifest), plan=PLAN.contract(),
                   source_languages=dict(languages), previous_held_reused=True,
                   pins={str(path.relative_to(ROOT)): manual.file_sha(path) for path in paths})
    stream = source(profile)
    expected = [read_windows(stream)[1] for _ in range(PLAN.steps)]
    restarted = source(profile)
    for _ in range(2):
        read_windows(restarted)
    saved = restarted.state_dict()
    reopened = source(profile)
    reopened.load_state_dict(saved)
    assert [read_windows(reopened)[1] for _ in range(2)] == expected[2:]
    profile.update(windows=expected, source_contract=stream.contract, max_authored_length=max(
        len(row["token_ids"]) for row in rows), replayed_after_two=2)
    verify(profile)
    previous.write(PROFILE, profile)
    print("INDEXED_G4_PREPARE", [row["counts"] for row in expected], profile["source_languages"], flush=True)


def train(profile):
    torch.manual_seed(SEED)
    cfg, state, step = warm.load_parent(torch)
    assert step == 2289 and cfg.max_seq_len >= PLAN.full_length
    cfg.train_repeat = 2.
    model = TiedMLPTransformer(cfg)
    model.load_state_dict(state, strict=True)
    del state
    model.set_anneal(1.)
    model = model.cuda().train()
    assert len(model.visit_schedule()) == 28
    initial = manual.state_fingerprint(model)
    optimizer = torch.optim.AdamW(model.parameters(), lr=previous.LR, betas=(.9, .95),
                                  weight_decay=0., foreach=False, fused=False)
    stream = source(profile)
    assert stream.contract == profile["source_contract"]
    torch.cuda.synchronize()
    torch.cuda.reset_peak_memory_stats()
    history = []
    for index in range(PLAN.steps):
        gate(5)
        start = perf_counter()
        windows, proof = read_windows(stream)
        assert proof == profile["windows"][index]
        batch = regroup_document_context(windows, PLAN, PLAN.length_at(index), vocab_size=VOCAB)
        assert batch.target_count == proof["targets"] and batch.input_slots == PLAN.tokens_per_update
        prepared = perf_counter() - start
        optimizer.zero_grad(set_to_none=True)
        nll = backward_document_context(model, batch, autocast_dtype=torch.bfloat16)
        norm = float(torch.nn.utils.clip_grad_norm_(model.parameters(), 1., error_if_nonfinite=True))
        assert math.isfinite(nll) and norm > 0
        optimizer.step()
        torch.cuda.synchronize()
        free, total = torch.cuda.mem_get_info()
        assert total - free <= 13_000_000_000, "physical occupancy budget exceeded"
        row = dict(step=index+1, width=batch.length, slots=batch.input_slots, targets=batch.target_count,
                   target_denominators=proof["counts"], nll=nll, gradient_norm=norm,
                   prepare_seconds=prepared, seconds=perf_counter()-start)
        history.append(row)
        print("INDEXED_G4_UPDATE", row, flush=True)
        del windows, batch
    final = manual.state_fingerprint(model)
    steps = {int(value["step"].item()) for value in optimizer.state.values()}
    assert steps == {PLAN.steps} and initial != final and stream.cursor == PLAN.steps
    return dict(history=history, initial=initial, final=final, optimizer_updates=PLAN.steps,
                source_record_reads=stream.record_reads, decoded_bytes=stream.requested_record_bytes,
                max_decoded_document_tokens=stream.max_decoded_document_tokens, checkpoint_writes=0,
                peak_allocated=torch.cuda.max_memory_allocated(), peak_reserved=torch.cuda.max_memory_reserved())


def worker(profile):
    assert torch.cuda.device_count() == 1 and torch.cuda.mem_get_info()[0] >= 13000*2**20
    torch.use_deterministic_algorithms(True)
    torch.backends.cuda.matmul.allow_tf32 = False
    with sdpa_kernel(SDPBackend.MATH):
        result = train(profile)
    close_owned_cuda(torch, result)
    previous.write(OUT / "training.json", result)


def run(profile):
    assert idle(), "GPU has another compute process"
    before = subprocess.check_output(sampling.DEVICE, text=True, timeout=8).strip()
    raw = OUT / "device_100ms.csv"
    previous.write(OUT / "active.json", dict(tag=TAG, pid=os.getpid()))
    with raw.open("xb") as stream:
        sampler = subprocess.Popen((*sampling.DEVICE, f"--loop-ms={sampling.INTERVAL_MS}"), stdout=stream)
        try:
            args = ["timeout", "--kill-after=5s", f"{LIMIT}s", sys.executable, "-B", "-u",
                    "-m", __spec__.name, "worker"]
            code = subprocess.run(args, cwd=ROOT, check=False).returncode
        finally:
            if sampler.poll() is None:
                sampler.terminate()
            sampler.wait(timeout=8)
    after = subprocess.check_output(sampling.DEVICE, text=True, timeout=8).strip()
    returned = idle()
    verify(profile)
    samples = sampling.read_samples(raw)
    previous.write(OUT / "report.json", dict(exit=code, device_returned=returned, sources_preserved=True,
        before=before, after=after, profile_sha256=manual.file_sha(PROFILE),
        samples=len(samples), device_peak=max(samples, key=lambda row: row["occupied_mib"]) if samples else None))
    print("INDEXED_G4_RELEASE", code, returned, after, flush=True)
    if code or not returned or not samples:
        raise SystemExit(code or 1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("prepare", "run", "worker"))
    phase = parser.parse_args().phase
    gate(LIMIT if phase == "run" else 0)
    assert os.environ.get("CUDA_VISIBLE_DEVICES") == ("" if phase == "prepare" else "0")
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    if phase == "prepare":
        prepare()
    else:
        profile = previous.read(PROFILE)
        if phase == "run":
            verify(profile)
            run(profile)
        else:
            worker(profile)


if __name__ == "__main__":
    main()
