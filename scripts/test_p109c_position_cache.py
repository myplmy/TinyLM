"""CPU checks for consuming published document locations as a P109C cache."""

from base64 import b64encode
from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
import zlib

import numpy as np
from tokenizers import Tokenizer, pre_tokenizers

from scripts import build_p109c_position_cache as builder
from scripts import compile_p109c_course as compiler
from scripts import run_p109c_scratch330 as entry
from scripts.test_p109c_course_schedule import SHAPE, source_pair
from scripts.test_p109c_scratch_bundle import ACCUM, BOUNDARY, MICRO, STEPS, VOCAB, WIDTH, make_bundle
from tinylm.data.loader import Loader
from tinylm.data.prepare import chat_tokenizer_path


def install_slot(state, *, compressed=False):
    body = json.dumps(state).encode()
    if compressed:
        body = json.dumps(dict(zlib_json=b64encode(zlib.compress(body)).decode("ascii"))).encode()
    slot = sha256(body).hexdigest().encode("ascii") + b"\n" + body
    return slot.ljust(builder.SLOT_BYTES, b"\0")


def position_fixture(root, token_path, rows, *, excluded=(), stage="published"):
    corpus = root / "released.txt"
    positions = root / "released.txt.work"
    scope = root / "scope.json"
    encoded = [(number, (body.encode() + builder.SEPARATOR) if body is not None else b"") for number, body in rows]
    corpus.write_bytes(b"".join(data for _, data in encoded))
    records = b"".join(builder.POSITION.pack(number, len(body) or 3, len(body)) for number, body in encoded)
    source_proof = builder.PROOF.pack(12, 16, 1)
    state = dict(version="1.1", stage=stage, revision=21, rows=len(encoded), index_offset=builder.INDEX_OFFSET,
                 index_format="<III", stored_documents=sum(bool(b) for _, b in encoded),
                 output_bytes=corpus.stat().st_size, input_stamp=[0, 0, sum(len(b) or 3 for _, b in encoded), 0],
                 content_admission_hold=[6], source_binding_proof=dict(rows=1,
                     offset=builder.INDEX_OFFSET + len(records), sha256=sha256(source_proof).hexdigest()))
    positions.write_bytes(install_slot(dict(state, revision=20, stage="published")) +
                          install_slot(state, compressed=True) + records + source_proof)
    scope.write_text(json.dumps(dict(inputs=[dict(split=split, intervals=2) for split in ("train", "val", "train")])))
    path = root / "raw_manifest.json"

    def pin(p):
        return dict(file=p.name, sha256=entry.file_sha(p))

    spec = dict(schema=builder.SCHEMA, source_release=entry.RELEASE, admission="SYNTHETIC_FIXTURE_ONLY",
                text=pin(corpus), positions=pin(positions), split_scope=pin(scope), tokenizer=pin(token_path),
                excluded_positions=list(excluded))
    entry.publish(path, spec)
    return path


def comparison(tokenizer, bodies):
    return [token for body in bodies for token in (*tokenizer.encode(body, add_special_tokens=False).ids,
                                                   tokenizer.token_to_id("<eos>"))]


class PositionCacheTest(unittest.TestCase):
    def test_unordered_positions_compile_and_admit_to_existing_bundle(self):
        with TemporaryDirectory(prefix="p109c_positions_") as directory:
            root = Path(directory)
            bundle = make_bundle(root)
            token_file = root / "tokenizer.json"
            tokenizer = Tokenizer.from_file(str(token_file))
            tokenizer.pre_tokenizer = pre_tokenizers.WhitespaceSplit()
            tokenizer.save(str(token_file))
            a, b = " ".join(["w1", "w2"] * 900), " ".join(["w3", "w4"] * 900)
            v1, v2 = " ".join(["w16", "w18"] * 20), " ".join(["w17", "w19"] * 20)
            rows = [(6, None), (3, v1), (2, b), (5, "w2 <eos> w3"), (4, v2), (1, a)]
            path = position_fixture(root, token_file, rows, excluded=(5,))
            with patch.multiple(entry, STEPS=STEPS, BOUNDARY=BOUNDARY, MICRO=MICRO, ACCUM=ACCUM,
                                WIDTH=WIDTH, VOCAB=VOCAB):
                built = builder.build_cache(path, entry.file_sha(path), "release_chat32", batch_size=1)
                second = builder.build_cache(path, entry.file_sha(path), "batch_chat32", batch_size=64)
                bundle["cache"] = built
                bundle["tokenizer"]["sha256"] = entry.file_sha(token_file)
                bundle["course"]["tokenizer_sha256"] = bundle["tokenizer"]["sha256"]
                manifest = root / "bundle.json"
                entry.publish(manifest, bundle)
                admitted = entry.load_bundle(manifest, entry.file_sha(manifest))
                self.assertEqual(admitted.receipt()["train_pool"], 3602)
                with self.assertRaises(FileExistsError):
                    builder.build_cache(path, entry.file_sha(path), "release_chat32")
            for split, expected in (("train", [b, a]), ("val", [v1, v2])):
                name = f"{split}.bin"
                self.assertEqual(built["sha256"][name], second["sha256"][name])
                saved = Loader(split, 1, 16, "cpu", root / built["directory"]).d
                self.assertEqual(saved.tolist(), comparison(tokenizer, expected))
            meta = json.loads((root / built["directory"] / "meta.json").read_text())
            self.assertEqual((meta["train_documents"], meta["val_documents"], meta["position_revision"]), (2, 2, 21))
            self.assertEqual(meta["excluded_positions"], [5])

    def test_actual_32k_chat_tokenizer_and_course_compile_to_one_bundle(self):
        with TemporaryDirectory(prefix="p109c_positions_chat32_") as directory:
            root = Path(directory)
            token_path = root / "chat32.json"
            token_path.write_bytes(chat_tokenizer_path("ko-en").read_bytes())
            tokenizer = Tokenizer.from_file(str(token_path))
            train = "모델은 서로 다른 문서의 경계를 보존한다. " * 1200
            val = "This validation passage keeps the original split. " * 16
            path = position_fixture(root, token_path, [(3, val), (1, train), (6, None)])
            with patch.multiple(entry, **SHAPE):
                result = builder.build_cache(path, entry.file_sha(path), "actual_chat32")
                spec = source_pair(root, root / result["directory"], token_path, entry.file_sha(token_path))
                self.assertEqual(spec["cache"], result)
                schedule = root / "schedule.json"
                entry.publish(schedule, spec)
                manifest, digest = compiler.compile_schedule(schedule, entry.file_sha(schedule), "compiled")
                loaded = entry.load_bundle(manifest, digest)
                self.assertEqual(loaded.receipt()["course_slots"], 20 * SHAPE["WIDTH"])
                self.assertEqual(loaded.receipt()["decimal_rows"], 4)
                self.assertEqual(loaded.receipt()["train_pool"], len(comparison(tokenizer, [train])))
            for split, expected in (("train", [train]), ("val", [val])):
                raw = np.fromfile(root / result["directory"] / f"{split}.bin", dtype="<u2")
                self.assertEqual(raw.tolist(), comparison(tokenizer, expected))

    def test_rejects_cross_split_overlap_and_keeps_metadata_unpublished(self):
        for texts in (("w1  w2", "w1 w2"), ("w1 different", "w1 alternate")):
            with self.subTest(texts=texts), TemporaryDirectory(prefix="p109c_overlap_") as directory:
                root = Path(directory)
                make_bundle(root)
                path = root / "tokenizer.json"
                tokenizer = Tokenizer.from_file(str(path))
                tokenizer.pre_tokenizer = pre_tokenizers.WhitespaceSplit()
                tokenizer.save(str(path))
                spec = position_fixture(root, path, [(3, texts[0]), (1, texts[1])])
                with patch.object(entry, "VOCAB", VOCAB), self.assertRaisesRegex(ValueError, "TRAIN/VAL"):
                    builder.build_cache(spec, entry.file_sha(spec), "dup_chat32")
                self.assertFalse((root / "dup_chat32/meta.json").exists())

    def test_refuses_unpublished_slot_and_nonzero_position_under_hold(self):
        for rows, stage, expected in (([(3, "w1"), (1, "w2")], "refining", "latest"),
                                      ([(6, "w3"), (3, "w1"), (1, "w2")], "published", "held published")):
            with self.subTest(stage=stage), TemporaryDirectory(prefix="p109c_reject_") as directory:
                root = Path(directory)
                make_bundle(root)
                spec = position_fixture(root, root / "tokenizer.json", rows, stage=stage)
                with (patch.object(entry, "VOCAB", VOCAB), self.assertRaisesRegex(ValueError, expected)):
                    builder.build_cache(spec, entry.file_sha(spec), "reject_chat32")
                self.assertFalse((root / "reject_chat32/meta.json").exists())


if __name__ == "__main__":
    unittest.main()
