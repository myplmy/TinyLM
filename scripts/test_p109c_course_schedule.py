"""Verify the P109C compiler with canonical authored dialogues and sealed split roots."""

import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import numpy as np
from tokenizers import Tokenizer, models, pre_tokenizers

from scripts import compile_p109c_course as compiler
from scripts import run_p109c_scratch330 as entry
from tinylm.chat.canonical import normalize
from tinylm.chat.tokens import SLOT_NAMES


TOKENIZER = None
SHAPE = dict(STEPS=3, BOUNDARY=2, MICRO=4, ACCUM=6, WIDTH=64)


def reference(path):
    return dict(file=path.name, sha256=entry.file_sha(path).upper())


def record(question, answer, root, **extra):
    return dict(root=root, record=normalize(dict(messages=[dict(role="user", content=question),
                                                dict(role="assistant", content=answer)])), **extra)


def source_pair(root, cache, tokenizer_path, tokenize_sha):
    def write(path, rows):
        with path.open("w", encoding="utf-8") as stream:
            for row in rows:
                stream.write(json.dumps(row) + chr(10))
        return reference(path)

    roots = root / "roots.json"
    entry.publish(roots, dict(train=["P", "R"], validation=["V"], test=["T"]))
    plain_rows = [record("What is 2 + 3?", "5", "P", operands=[2, 3])] * 4
    relation_rows = [record(f"What is the label of {name}?", answer, "R")
                     for name in ("Mina", "Jina", "Aram", "Haru")
                     for answer in ("red", "blue", "white", "black")]
    return dict(schema=compiler.SCHEMA, admission=dict(raw="FIXTURE", course="FIXTURE"),
                cache=dict(directory=cache.name, sha256={name: entry.file_sha(cache / name).upper()
                                                        for name in entry.CACHE_FILES}),
                roots=reference(roots), tokenizer=dict(file=tokenizer_path.name, sha256=tokenize_sha),
                plain=dict(write(root / "plain.jsonl", plain_rows), slots=[1]),
                all_axes=dict(write(root / "relation.jsonl", relation_rows), slots=[2, 3, 4, 5], gold=[0, 1, 2, 3]))


def small_tokenizer():
    specials = ("<pad>", "<bos>", "<eos>", *SLOT_NAMES)
    normal = ("unk", "user", "assistant", "What", "is", "the", "label", "of", "2", "+", "3?", "5",
              "Mina?", "Jina?", "Aram?", "Haru?", "red", "blue", "white", "black")
    words = (*specials, *normal)
    tok = Tokenizer(models.WordLevel(vocab={word: index for index, word in enumerate(words)}, unk_token="unk"))
    tok.pre_tokenizer = pre_tokenizers.WhitespaceSplit()
    tok.add_special_tokens(list(specials))
    return tok


class CompileCourseTest(unittest.TestCase):
    def test_canonical_course_and_runtime_share_the_exact_contract(self):
        tokenizer = Tokenizer.from_file(str(TOKENIZER)) if TOKENIZER else small_tokenizer()
        vocab = tokenizer.get_vocab_size()
        with TemporaryDirectory(prefix="p109c_compiler_") as directory, patch.multiple(entry, VOCAB=vocab, **SHAPE):
            root = Path(directory)
            tok_path = root / "tokenizer.json"
            if TOKENIZER:
                tok_path.write_bytes(TOKENIZER.read_bytes())
            else:
                tokenizer.save(str(tok_path))
            tok_sha = reference(tok_path)["sha256"]
            cache = root / "fixture_chat32"
            cache.mkdir()
            train, val = 2 * entry.STEPS * entry.MICRO * entry.ACCUM * entry.WIDTH, 256
            for split, tokens in (("train", train), ("val", val)):
                (np.arange(tokens, dtype=np.uint16) % vocab).tofile(cache / f"{split}.bin")
            entry.publish(cache / "meta.json", dict(data="ko-en", tokenizer_sha256=tok_sha, vocab=vocab,
                token_dtype="uint16", tokenizer_lineage="chat32", train=train, val=val, tokens=train + val))
            source = source_pair(root, cache, tok_path, tok_sha)
            manifest = root / "schedule.json"
            entry.publish(manifest, source)
            generated, sha = compiler.compile_schedule(manifest, reference(manifest)["sha256"], "compiled")
            result = entry.load_bundle(generated, sha)
            self.assertEqual(len(result.decimal.by_row), 4)
            self.assertEqual(result.all_axes.gold_by_question, (0, 1, 2, 3))
            self.assertEqual(result.receipt()["course_slots"], 20 * entry.WIDTH)
            self.assertEqual({code for code, _ in result.decimal.by_row.values()}, {1005})

            entry.publish(root / "overlap.json", dict(train=["P", "R"], validation=["P"], test=["T"]))
            bad_roots = root / "overlap_schedule.json"
            entry.publish(bad_roots, dict(source, roots=reference(root / "overlap.json")))
            with self.assertRaisesRegex(ValueError, "independent train"):
                compiler.compile_schedule(bad_roots, reference(bad_roots)["sha256"], "overlap")
            self.assertFalse((root / "overlap_manifest.json").exists())

            wrong_cases = (("wrong_operand", "What is 2 + 3?", [2, 4], "operands disagree"),
                           ("wrong_operator", "What is 2 - 3?", [2, 3], "addition question"))
            for name, question, operands, error in wrong_cases:
                wrong = root / f"{name}.jsonl"
                wrong.write_text(json.dumps(record(question, "5", "P", operands=operands)) + chr(10), encoding="utf-8")
                bad_label = root / f"{name}_schedule.json"
                entry.publish(bad_label, dict(source, plain=dict(reference(wrong), slots=[1])))
                with self.assertRaisesRegex(ValueError, error):
                    compiler.compile_schedule(bad_label, reference(bad_label)["sha256"], name)
                self.assertFalse((root / f"{name}_manifest.json").exists())

            first_wrong = root / "first_wrong.jsonl"
            correction = normalize(dict(messages=[
                dict(role="user", content="What is 2 + 3?"), dict(role="assistant", content="red"),
                dict(role="user", content="What is 2 + 3?"), dict(role="assistant", content="5"),
            ], meta=dict(view="correction", supervised_assistant_turns=[1])))
            first_wrong.write_text(json.dumps(dict(root="P", record=correction)) + chr(10), encoding="utf-8")
            wrong_turn = root / "wrong_turn_schedule.json"
            entry.publish(wrong_turn, dict(source, plain=dict(reference(first_wrong), slots=[1])))
            with self.assertRaisesRegex(ValueError, "only the final assistant reply"):
                compiler.compile_schedule(wrong_turn, reference(wrong_turn)["sha256"], "wrong_turn")
            self.assertFalse((root / "wrong_turn_manifest.json").exists())


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--tokenizer":
        TOKENIZER = Path(sys.argv[2])
        del sys.argv[1:3]
    unittest.main()
