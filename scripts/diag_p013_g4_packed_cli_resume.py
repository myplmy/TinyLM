"""Check a real P079 packed CLI continuation from a shared saved boundary."""

import argparse
from datetime import datetime, timedelta
import json
import os
from pathlib import Path
import subprocess
import sys
from time import perf_counter
from unittest.mock import patch

import torch
from tokenizers import Tokenizer
from torch.nn.attention import SDPBackend, sdpa_kernel

from scripts import diag_p013_g4_indexed_native as indexed
from scripts.diag_p102a_g4_recompute_shapes import idle
from scripts.diag_p107_hybrid_mntp import close_owned_cuda
from tinylm import cli
from tinylm.config import build_config
from tinylm.model import TiedMLPTransformer
from tinylm.train import document_input as envelope
from tinylm.train import packed_document_training as packed
from tinylm.train import trainer
from tinylm.train.init_utils import _strip


earlier, warm, manual = indexed.previous, indexed.warm, indexed.manual
ROOT, END = indexed.ROOT, earlier.END
TAG = "p013_g4_packed_cli_resume_v1_20261119"
OUT = indexed.OUT.with_name(TAG)
PROFILE = OUT / "profile.json"
SEALED_PLAN = OUT / "plan_at_execution.md"
INPUT = OUT / "packed_input.json"
CPU_LOG = ROOT / "test_result/106_log_20261119_P013_Stage7We_PackedCooldownTests_CPU.txt"
NAME = f"m100s12_g4_ko-en_65536_{TAG}.pt"
BEST = NAME.removesuffix(".pt") + "_best.pt"
PHASES = ("continuous", "resume")
BOUNDARY, STEPS, LIMIT = 2, 4, 180
BATCH, ACCUM, WIDTH, VAL_BATCHES = 8, 2, 1024, 2
PLAN = earlier.ContextPlan(((1, 256), (2, 512), (4, 1024)), BATCH, ACCUM, WIDTH)
SOURCES = (
    "scripts/diag_p013_g4_indexed_native.py", "scripts/diag_p102a_g4_full_delta_train.py",
    "tinylm/cli.py", "tinylm/config.py", "tinylm/train/trainer.py",
    "tinylm/train/context_training_state.py", "tinylm/train/context_curriculum.py",
    "tinylm/train/document_input.py", "tinylm/train/indexed_document_source.py",
    "tinylm/train/packed_document_training.py", "tinylm/train/document_context_curriculum.py",
    "tinylm/train/hybrid_mntp.py", "tinylm/train/anneal_schedule.py",
    "tinylm/model/transformer.py", "tinylm/model/modules.py", "tinylm/model/visibility.py",
)


def gate(reserve=0):
    if (OUT / "STOP").exists() or datetime.now(END.tzinfo) + timedelta(seconds=reserve) >= END:
        raise RuntimeError("owned STOP or deadline")


def write(path, value):
    earlier.write(path, value)


def ref(path):
    return dict(path=path.relative_to(OUT).as_posix(), bytes=path.stat().st_size, sha256=manual.file_sha(path))


def verify(profile):
    assert profile["tag"] == TAG and profile["approval"] == 177
    for name, digest in profile["pins"].items():
        assert manual.file_sha(ROOT / name) == digest, name


def make_inputs(previous, original):
    directory = OUT / "input"
    directory.mkdir()
    seals = previous["input_manifest"]
    source_manifest = ROOT / seals["path"]
    assert manual.file_sha(source_manifest) == seals["sha256"]
    train = earlier.read(source_manifest)
    old_shard, = train["shards"]
    old = ROOT / old_shard["file"]["path"]
    raw = old.read_bytes()
    assert len(raw) == old_shard["file"]["bytes"] and envelope.sha256(raw) == old_shard["file"]["sha256"]
    train_shard = directory / "train.jsonl"
    with train_shard.open("xb") as stream:
        stream.write(raw)
    old_shard["file"] = ref(train_shard)
    train_manifest = directory / "train_manifest.json"
    write(train_manifest, train)
    validation_shard = directory / "val.jsonl"
    tokenizer = Tokenizer.from_file(str(earlier.TOKENIZER))
    rows = []
    for row in original["data"]["documents"]:
        if row["split"] == "held":
            ids = tokenizer.encode(row["text"], add_special_tokens=False).ids
            rows.append(dict(source_id=row["id"], token_ids=ids, language="synthetic",
                             source_sha256=envelope.sha256(row["text"].encode())))
    assert len(rows) == 48
    with validation_shard.open("x", encoding="utf-8") as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False) + chr(10))
    validation_manifest = directory / "val_manifest.json"
    shards = [dict(file=ref(validation_shard), documents=len(rows),
                   tokens=sum(len(row["token_ids"]) for row in rows))]
    write(validation_manifest, dict(train, split="val", shards=shards))
    token_copy = directory / "tokenizer.json"
    with token_copy.open("xb") as stream:
        stream.write(earlier.TOKENIZER.read_bytes())
    assert manual.file_sha(token_copy) == earlier.TOKENIZER_SHA
    write(INPUT, dict(schema=packed.INPUT_SCHEMA, input_root="input", train=ref(train_manifest),
                      validation=ref(validation_manifest), validation_batches=VAL_BATCHES,
                      tokenizer=dict(ref(token_copy), vocab_size=32768)))
    return source_manifest, old


def prepare():
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    unit = CPU_LOG.read_text(encoding="utf-8")
    assert "Ran 83 tests" in unit and unit.splitlines()[-1] == "EXIT 0"
    previous_path = indexed.OUT / "profile.json"
    old_report_path = indexed.OUT / "report.json"
    prev, old_report = map(earlier.read, (previous_path, old_report_path))
    assert old_report["exit"] == 0 and old_report["device_returned"]
    assert old_report["profile_sha256"] == manual.file_sha(previous_path)
    original_path = earlier.SOURCE / "profile.json"
    original = earlier.read(original_path)
    parent, state = packed.load_packed_parent(warm.PARENT, read_weights=True)
    assert parent["sha256"] == original["sources"]["parent_sha"] and state["step"] == 2289
    cfg = build_config("m100s12_g4", "tied", WIDTH, True)
    cfg.train_repeat = 2.
    model = TiedMLPTransformer(cfg)
    reference = _strip(state["model"])
    model.load_state_dict(reference, strict=True)
    initial_sha = indexed.state_sha(reference)
    assert indexed.state_sha(model.state_dict()) == initial_sha and len(model.visit_schedule()) == 28
    del model, state, reference
    section = earlier.PLAN.read_text(encoding="utf-8").split("### Stage7We ", 1)
    assert len(section) == 2 and TAG in section[1]
    OUT.mkdir(exist_ok=False)
    SEALED_PLAN.write_text("### Stage7We " + section[1], encoding="utf-8")
    inputs = make_inputs(prev, original)
    packet = packed.load_packed_document_profile(INPUT)
    assert packet.train.contract["corpus_sha256"] == prev["source_contract"]["corpus_sha256"]
    assert packet.validation.contract["documents"] == 48 and packet.train.contract["documents"] == 768
    cursor = packet.cursor(PLAN, seed=1234)
    expected = []
    for step in range(1, STEPS + 1):
        update = cursor.prepare()
        cursor.finish(optimizer_applied=True)
        expected.append(dict(step=step, width=update.length, targets=update.target_count,
                             cursor_sha256=indexed.state_sha(cursor.state_dict())))
    validation = packet.validation.as_source(batch=BATCH, length=WIDTH, micros=1, vocab=32768, seed=99, packed=True)
    held = sum(indexed.read_windows(validation)[1]["targets"] for _ in range(VAL_BATCHES))
    paths = [*(ROOT / name for name in SOURCES), Path(__file__), SEALED_PLAN, warm.PARENT,
             original_path, previous_path, old_report_path, CPU_LOG, earlier.TOKENIZER, *inputs,
             INPUT, *(OUT / "input").iterdir()]
    profile = dict(tag=TAG, approval=177, parent=parent, parent_weights_sha256=initial_sha,
                   expected=expected, held_targets=held, train=packet.train.contract, validation=packet.validation.contract,
                   pins={str(path.relative_to(ROOT)):manual.file_sha(path) for path in paths})
    verify(profile)
    assert not torch.cuda.is_initialized()
    write(PROFILE, profile)
    print("G4_PACKED_CLI_PREPARE", [row["targets"] for row in expected], held, parent["sha256"], flush=True)


def worker(profile, phase):
    gate(20)
    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    assert torch.cuda.device_count() == 1 and torch.cuda.mem_get_info()[0] >= 12500 * 2**20
    torch.use_deterministic_algorithms(True)
    directory = OUT / phase
    argv = ["tinylm", "train", "--preset", "m100s12_g4", "--data", "ko-en",
            "--steps", "4", "--eval-every", "2", "--save-every", "2", "--seq", "1024",
            "--micro-bs", "8", "--accum", "2", "--train-repeat", "2", "--optimizer", "adamw",
            "--lr", "3e-5", "--sched", "decay", "--decay-from", profile["parent"]["path"],
            "--tokens", "0.065536M", "--tag", TAG, "--context-curriculum", "1:256,2:512,4:1024",
            "--packed-document-profile", str(INPUT)]
    if phase == "resume":
        argv.append("--resume")
    save = packed.save_packed_checkpoint

    def save_visible(path, state):
        save(path, state)
        tick = state["step"]
        if phase == "continuous" and tick == BOUNDARY:
            assert path.name in (NAME, BEST)
            os.link(path, OUT / "boundary" / path.name)
            os.link(path, OUT / "resume" / "ckpt" / path.name)
        gate()
        free, total = torch.cuda.mem_get_info()
        if total - free > 13_000_000_000:
            raise RuntimeError("physical occupancy exceeds the prepared ceiling")
        print("G4_PACKED_CLI_SAVE", phase, tick, path.name, path.stat().st_size, flush=True)

    with (patch.object(sys, "argv", argv), patch.object(trainer, "CKPT", directory / "ckpt"),
          patch.object(trainer, "LOGS", directory / "logs"), patch.object(packed, "save_packed_checkpoint", save_visible),
          patch.object(trainer, "prepare", side_effect=AssertionError("legacy data access")),
          patch.object(trainer, "Loader", side_effect=AssertionError("flat loader access")),
          sdpa_kernel(SDPBackend.MATH)):
        cli.main()
    cleanup = {}
    close_owned_cuda(torch, cleanup)
    write(OUT / f"cleanup_{phase}.json", cleanup)


def read_phase(phase):
    root = OUT / phase
    path = root / "ckpt" / NAME
    return (torch.load(path, weights_only=True, map_location="cpu"),
            earlier.read(root / "logs" / (NAME.removesuffix(".pt") + ".json")))


def compare(profile):
    boundary = torch.load(OUT / "boundary" / NAME, map_location="cpu", weights_only=True)
    a, ar = read_phase("continuous")
    b, br = read_phase("resume")
    assert boundary["step"] == br["context_resume_start_step"] == BOUNDARY and a["step"] == b["step"] == STEPS
    key = trainer.CONTEXT_STATE_KEY
    exact = {field: indexed.state_sha(a[field]) == indexed.state_sha(b[field]) for field in ("model", "opt", key)}
    state = b[key]
    assert state["binding"]["recipe"]["packed_decay_parent"] == profile["parent"]
    for value, index in ((boundary, BOUNDARY - 1), (b, STEPS - 1)):
        cursor = value[key]["cursor"]
        assert indexed.state_sha(cursor) == profile["expected"][index]["cursor_sha256"]
    assert indexed.state_sha(b["model"]) != profile["parent_weights_sha256"]
    assert all(exact.values()) and ar["final"] == br["final"], (exact, ar["final"], br["final"])
    assert [row["step"] for row in state["control"]["history"]] == [2, 4]
    assert {row["val_valid_targets"] for row in state["control"]["history"]} == {profile["held_targets"]}
    assert state["cuda_rng"].numel() > 0
    paths = [OUT / prefix / name for prefix in ("boundary", "continuous/ckpt", "resume/ckpt") for name in (NAME, BEST)]
    files, unique = {}, {}
    for path in paths:
        info = path.stat()
        files[path.relative_to(OUT).as_posix()] = info.st_size
        unique[(info.st_dev, info.st_ino)] = info.st_blocks * 512
    measured = {name: dict(phase_wall=row["t1_phase_wall"], allocator_gib=row["vram_alloc_gb"],
                           reserved_gib=row["vram_reserved_gb"])
                for name, row in (("continuous", ar), ("resume", br))}
    return dict(exact=exact, model_sha256=indexed.state_sha(b["model"]), adamw_sha256=indexed.state_sha(b["opt"]),
                final=br["final"], target_exposures=state["cursor"]["valid_targets"], actual_updates=6,
                validation_calls=3, files=files, unique_file_bytes=sum(unique.values()), unique_files=len(unique),
                measurements=measured)


def run(profile):
    assert idle(), "GPU has another compute process"
    gate(len(PHASES) * (LIMIT + 5))
    (OUT / "boundary").mkdir(exist_ok=False)
    (OUT / "resume" / "ckpt").mkdir(parents=True, exist_ok=False)
    sample = indexed.sampling
    before = subprocess.check_output(sample.DEVICE, text=True, timeout=8).strip()
    raw = OUT / "device_100ms.csv"
    write(OUT / "active.json", dict(tag=TAG, pid=os.getpid(), phases=PHASES))
    exits, wall = {}, {}
    with raw.open("xb") as stream:
        monitor = subprocess.Popen((*sample.DEVICE, f"--loop-ms={sample.INTERVAL_MS}"), stdout=stream)
        try:
            for phase in PHASES:
                gate(LIMIT + 5)
                assert idle()
                cmd = ["timeout", "--kill-after=5s", f"{LIMIT}s", sys.executable, "-B", "-u",
                       "-m", __spec__.name, "worker", phase]
                start = perf_counter()
                exits[phase] = subprocess.run(cmd, cwd=ROOT, check=False).returncode
                wall[phase] = perf_counter() - start
                print("G4_PACKED_CLI_EXIT", phase, exits[phase], wall[phase], flush=True)
                if exits[phase]:
                    break
        finally:
            if monitor.poll() is None:
                monitor.terminate()
            monitor.wait(timeout=8)
    after = subprocess.check_output(sample.DEVICE, text=True, timeout=8).strip()
    returned = idle()
    verify(profile)
    samples = sample.read_samples(raw)
    observation = dict(tag=TAG, exits=exits, process_seconds=wall, device_returned=returned,
                       device_peak=max(samples, key=lambda row: row["occupied_mib"]), samples=len(samples),
                       device_before=before, device_after=after, source_preserved=True,
                       profile_sha256=manual.file_sha(PROFILE))
    write(OUT / "device_report.json", observation)
    print("G4_PACKED_CLI_RELEASE", returned, after, flush=True)
    if exits != dict.fromkeys(PHASES, 0) or not returned:
        raise SystemExit(1)
    proof = compare(profile)
    write(OUT / "report.json", dict(observation, result=proof))
    print("G4_PACKED_CLI_COMPARE", proof["exact"], proof["unique_file_bytes"], proof["target_exposures"], flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "run", "worker"))
    parser.add_argument("phase", nargs="?", choices=PHASES)
    args = parser.parse_args()
    assert os.environ.get("CUDA_VISIBLE_DEVICES") == ("" if args.mode == "prepare" else "0")
    gate()
    if args.mode == "prepare":
        prepare()
    else:
        profile = earlier.read(PROFILE)
        if args.mode == "run":
            verify(profile)
            run(profile)
        else:
            worker(profile, args.phase)
