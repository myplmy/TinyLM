"""Exercise packed training, fixed validation and exact CLI checkpoint restart on CPU."""

import copy
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import torch
from tokenizers import Tokenizer
from tokenizers.models import WordLevel

from scripts.diag_p102a_g4_full_delta_train import state_sha
from tinylm import cli, config
from tinylm.train import document_input, packed_document_training, trainer


TAG = "p013_packed_document_cli_v1_20261119"
NAME = f"tiny_synthetic_256_{TAG}"
VOCAB = 64


class InputFixture:
    def __init__(self, *, overlap=None, admitted=False):
        self.root = Path(tempfile.mkdtemp(prefix="p013_packed_cli_"))
        (self.root / "inputs").mkdir()
        tokens = {"<unk>": 0, **{str(index): index for index in range(1, VOCAB)}}
        tokenizer = Tokenizer(WordLevel(tokens, unk_token="<unk>"))
        token_file = self.put("inputs/tokenizer.json", tokenizer.to_str().encode())
        train = self.rows("train", 35, [4, 9, 6, 13, 8, 14])
        validation = self.rows("val", 49, [3, 5, 11, 7, 6, 15])
        if overlap is not None:
            validation[0][overlap] = train[0][overlap]
        self.profile = dict(schema=packed_document_training.INPUT_SCHEMA, input_root="inputs",
                            tokenizer=dict(token_file, vocab_size=VOCAB), validation_batches=3,
                            train=self.manifest("train", train, token_file["sha256"], admitted),
                            validation=self.manifest("val", validation, token_file["sha256"], admitted))
        self.profile_path = self.put_profile("profile.json", self.profile)

    def rows(self, split, base, lengths):
        return [dict(source_id=f"{split}-{index}", language="synthetic",
                     source_sha256=sha256(f"{split} {index}".encode()).hexdigest().upper(),
                     token_ids=[base + (offset + index) % 13 for offset in range(length)])
                for index, length in enumerate(lengths)]

    def put(self, path, data):
        with (self.root / path).open("xb") as stream:
            stream.write(data)
        return dict(path=path, bytes=len(data), sha256=document_input.sha256(data))

    def put_profile(self, name, profile):
        self.put(name, json.dumps(profile).encode())
        return self.root / name

    def manifest(self, split, rows, tokenizer, admitted):
        if admitted:
            for row in rows:
                row["language"] = "ko"
        content = "".join(json.dumps(row) + chr(10) for row in rows)
        shard = self.put(f"inputs/{split}.jsonl", content.encode())
        shards = [dict(file=shard, documents=len(rows), tokens=sum(len(row["token_ids"]) for row in rows))]
        purpose = "SYNTHETIC_TECHNICAL"
        admission = dict(status="TECHNICAL_FIXTURE_ONLY", authority_ref="P013_TEST_FIXTURE",
                         training_authorized=False, evidence=None)
        if admitted:
            train = split == "train"
            purpose = "TRAIN_ADMITTED" if train else "EVAL_ADMITTED"
            evidence = dict(schema=document_input.ADMISSION_SCHEMA, split=split,
                            authority_ref=admission["authority_ref"], tokenizer_sha256=tokenizer,
                            shards_sha256=document_input.canonical_sha(shards))
            evidence["approved_for_training" if train else "approved_for_evaluation"] = True
            admission.update(status="TRAIN_APPROVED" if train else "EVAL_APPROVED", training_authorized=train,
                             evidence=self.put(f"inputs/{split}-admission.json", json.dumps(evidence).encode()))
        manifest = dict(schema=document_input.SCHEMA, split=split, purpose=purpose, admission=admission,
                        shards=shards, tokenizer=dict(sha256=tokenizer, vocab_size=VOCAB))
        return self.put(f"inputs/{split}-manifest.json", json.dumps(manifest).encode())


def tiny_g4(seq, ckpt):
    return config.TMTConfig(vocab_size=VOCAB, dim=32, ffn_dim=64, emb_rank=8, max_seq_len=seq,
                            n_q_heads=4, n_kv_heads=2, n_prelude=2, n_middle=12, n_coda=2,
                            tie_mlp=True, mlp_group=4, cla_group=2, micro_group=8, grad_checkpoint=ckpt)


class TestBoundary(Exception):
    pass


def worker(profile, directory, phase):
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    argv = ["tinylm", "train", "--preset", "tiny", "--data", "synthetic", "--tokens", "0.000256M",
            "--steps", "4", "--eval-every", "1", "--seq", "16", "--micro-bs", "2", "--accum", "2",
            "--train-repeat", "2", "--optimizer", "adamw", "--lr", "3e-4", "--anneal-start", "0",
            "--tag", TAG,
            "--context-curriculum", "1:4,2:8,4:16", "--packed-document-profile", str(profile)]
    if phase == "resume":
        argv.append("--resume")
    save = packed_document_training.save_packed_checkpoint

    def save_then_stop(path, state):
        save(path, state)
        if state["step"] == 1 and path.name.endswith("_best.pt"):
            raise TestBoundary

    with (patch.dict(config.PRESETS, {"tiny": tiny_g4}), patch.object(sys, "argv", argv),
          patch.object(trainer, "CKPT", directory / "ckpt"), patch.object(trainer, "LOGS", directory / "logs"),
          patch.object(trainer, "prepare", side_effect=AssertionError("legacy cache access")),
          patch.object(trainer, "Loader", side_effect=AssertionError("flat loader access"))):
        if phase == "prefix":
            try:
                with patch.object(packed_document_training, "save_packed_checkpoint", save_then_stop):
                    cli.main()
            except TestBoundary:
                return
            raise AssertionError("first full checkpoint was not saved")
        cli.main()


class PackedDocumentCLI(unittest.TestCase):
    def test_cooldown_parent_is_bound_on_resume_without_deserializing_twice(self):
        parent = Path(tempfile.mkdtemp(prefix="p013_packed_parent_")) / "parent.pt"
        torch.save({"model": {"weight": torch.arange(4.)}}, parent)
        identity, weights = packed_document_training.load_packed_parent(parent, read_weights=True)
        self.assertEqual(identity["sha256"], document_input.sha256(parent.read_bytes()))
        self.assertTrue(torch.equal(weights["model"]["weight"], torch.arange(4.)))
        with patch.object(torch, "load", side_effect=AssertionError("resume must load its own state")):
            resume_identity, state = packed_document_training.load_packed_parent(parent, read_weights=False)
        self.assertEqual(identity, resume_identity)
        self.assertIsNone(state)

    def test_rejects_cross_split_id_raw_source_and_actual_token_overlap(self):
        for field, message in (("source_id", "source_id"), ("source_sha256", "declared_source_sha256"),
                               ("token_ids", "token_sha256")):
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, message):
                packed_document_training.load_packed_document_profile(InputFixture(overlap=field).profile_path)

    def test_admitted_eval_is_separate_from_train_and_tokenizer_bound(self):
        fixture = InputFixture(admitted=True)
        packet = packed_document_training.load_packed_document_profile(fixture.profile_path)
        self.assertEqual(packet.train.contract["admission_status"], "TRAIN_APPROVED")
        self.assertEqual(packet.validation.contract["admission_status"], "EVAL_APPROVED")
        profile = copy.deepcopy(fixture.profile)
        profile["validation"] = profile["train"]
        with self.assertRaisesRegex(ValueError, "split"):
            packed_document_training.load_packed_document_profile(fixture.put_profile("wrong_split.json", profile))
        profile = copy.deepcopy(fixture.profile)
        profile["tokenizer"]["sha256"] = "A" * 64
        with self.assertRaises(ValueError):
            packed_document_training.load_packed_document_profile(fixture.put_profile("wrong_tokenizer.json", profile))

    def test_atomic_checkpoint_keeps_previous_checkpoint_if_serialization_fails(self):
        path = Path(tempfile.mkdtemp(prefix="p013_packed_atomic_")) / "model.pt"
        packed_document_training.save_packed_checkpoint(path, {"steps": 1})
        before = path.read_bytes()

        def broken(state, stream):
            stream.write(b"partial")
            raise OSError("fixture serialization failure")

        with patch.object(torch, "save", broken), self.assertRaises(OSError):
            packed_document_training.save_packed_checkpoint(path, {"steps": 2})
        self.assertEqual(path.read_bytes(), before)

    def test_cli_continuous_and_new_process_restarts_are_exact(self):
        fixture = InputFixture()
        baseline = fixture.root / "continuous"
        restart = fixture.root / "restart"

        def run(directory, phase, profile=fixture.profile_path, ok=True):
            cmd = [sys.executable, "-B", "-m", __spec__.name, "worker", str(profile), str(directory), phase]
            event = subprocess.run(cmd, text=True, capture_output=True, timeout=75)
            if ok:
                self.assertEqual(event.returncode, 0, event.stdout[-3000:] + event.stderr[-3000:])
            else:
                self.assertNotEqual(event.returncode, 0, event.stdout[-3000:] + event.stderr[-3000:])
            return event

        run(baseline, "continuous")
        run(restart, "prefix")
        resume_path = restart / "ckpt" / (NAME + ".pt")
        before = resume_path.read_bytes()
        prefix = torch.load(resume_path, map_location="cpu", weights_only=True)
        self.assertEqual(prefix["step"], 1)
        changed = copy.deepcopy(fixture.profile)
        changed["validation_batches"] = 4
        other = fixture.put_profile("different_validation.json", changed)
        failed = run(restart, "resume", profile=other, ok=False)
        self.assertIn("binding differs", failed.stderr)
        self.assertEqual(before, resume_path.read_bytes())
        run(restart, "resume")
        control = torch.load(baseline / "ckpt" / (NAME + ".pt"), map_location="cpu", weights_only=True)
        resumed = torch.load(resume_path, map_location="cpu", weights_only=True)
        self.assertEqual(control["step"], resumed["step"])
        self.assertEqual(control["step"], 4)
        for field in ("model", "opt", trainer.CONTEXT_STATE_KEY):
            self.assertEqual(state_sha(control[field]), state_sha(resumed[field]), field)
        context = resumed[trainer.CONTEXT_STATE_KEY]
        self.assertEqual(context["cursor"]["optimizer_updates"], 4)
        self.assertIsNone(context["validation_rng"])
        self.assertGreater(context["cursor"]["valid_targets"], 0)
        self.assertLess(context["cursor"]["valid_targets"], 256)
        rows = context["control"]["history"]
        self.assertEqual([row["step"] for row in rows], [1, 2, 3, 4])
        self.assertEqual(len({row["val_valid_targets"] for row in rows}), 1)
        report = json.loads((restart / "logs" / (NAME + ".json")).read_text())
        self.assertEqual(report["final"]["val_loss"], rows[-1]["val_loss"])
        self.assertEqual(report["final"]["val_valid_targets"], rows[-1]["val_valid_targets"])
        print("PACKED_CLI_PROOF", context["cursor"]["valid_targets"], rows[-1]["val_valid_targets"],
              state_sha(resumed["model"]), state_sha(resumed["opt"]), flush=True)


if __name__ == "__main__":
    if len(sys.argv) == 5 and sys.argv[1] == "worker":
        worker(Path(sys.argv[2]), Path(sys.argv[3]), sys.argv[4])
    else:
        unittest.main()
