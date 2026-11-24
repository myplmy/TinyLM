import copy
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from scripts import p108b_correction_course as course
from scripts import train_sft_p090 as trainer

def fixture():
    rows=[]
    for i,lang in enumerate(['ko','ko','ko','en']):
        q=dict(role='user',content='q'+str(i));a=dict(role='assistant',content='a'+str(i))
        for view in('single','correction'):
            messages=[q,a]if view=='single'else[q,dict(role='assistant',content='wrong'),dict(role='user',content='correct'),a]
            rows.append(dict(messages=messages,meta=dict(case_id=str(i),view=view,language=lang,source_group_id=str(i),
                root_teacher_review='ROOT_ACTUAL_TEXT_REVIEWED',supervised_assistant_turns=[1 if view=='single' else 2])))
    return rows

class CorrectionCourseTests(unittest.TestCase):
    def test_three_arms_share_order_and_each_case_once(self):
        cohort=course.pairs(fixture())
        for e in range(4):
            plans=[course.epoch_plan(cohort,a,e)for a in course.ARMS]
            self.assertEqual([[r['case_id']for r in p]for p in plans],[ [r['case_id']for r in plans[0]] ]*3)
            self.assertEqual(len({r['case_id']for r in plans[0]}),4)
    def test_each_case_sees_both_views_twice_including_odd_languages(self):
        cohort=course.pairs(fixture());seen={i:[]for i in cohort}
        for e in range(4):
            for r in course.epoch_plan(cohort,'MIXED_CROSSOVER',e):seen[r['case_id']].append(r['view'])
        for views in seen.values():self.assertEqual(views.count('single'),2);self.assertEqual(views.count('correction'),2)
    def test_planning_does_not_mutate_source_or_depend_on_dict_order(self):
        rows=fixture();before=copy.deepcopy(rows);cohort=course.pairs(rows)
        self.assertEqual(course.epoch_plan(cohort,'MIXED_CROSSOVER',1),course.epoch_plan(dict(reversed(list(cohort.items()))),'MIXED_CROSSOVER',1))
        self.assertEqual(rows,before)
    def test_missing_duplicate_or_changed_correct_answer_fails(self):
        for rows in [fixture()[:-1],fixture()+[fixture()[0]]]:
            with self.assertRaises(ValueError):course.pairs(rows)
        rows=fixture();rows[1]['messages'][-1]=dict(role='assistant',content='different')
        with self.assertRaises(ValueError):course.pairs(rows)

    def test_views_must_keep_the_question_and_assistant_role_order(self):
        rows = fixture()
        rows[1]["messages"][1] = {"role": "user", "content": "wrong role"}
        with self.assertRaisesRegex(ValueError, "explicit turn owners"):
            course.pairs(rows)


class TrainerCourseTests(unittest.TestCase):
    def test_normal_batches_preserve_matched_positions_and_targets(self):
        class Characters:
            def encode(self, text):
                return SimpleNamespace(ids=[ord(c) for c in text],
                                       offsets=[(i, i + 1) for i in range(len(text))])

        rows = fixture()
        records = trainer.encode_records(rows, Characters(), 1024, 32768)
        evidence = {}
        for arm in course.ARMS:
            epochs = trainer.paired_epochs(rows, records, arm, seed=1337)
            self.assertEqual(len(epochs), 4)
            evidence[arm] = []
            for order, receipt in epochs:
                observed = []
                self.assertEqual(len(order), 4)
                for blocks in trainer.micro_groups(records, order, 2, 1):
                    total = sum(record[2] for block in blocks for record in block)
                    measured = trainer.paired_update_receipt(blocks, 1024, total)
                    x, y = trainer.pad_batch(blocks[0], 0, width=1024)
                    self.assertEqual(x.shape, y.shape)
                    self.assertEqual(x.numel(), measured["padded_positions"])
                    self.assertEqual(int(y.ne(trainer.IGNORE).sum()), total)
                    observed.append(measured)
                evidence[arm].append((receipt["case_order_sha256"], receipt["view_order_sha256"], observed))
        matched = [
            [(case_order, [u["target_sha256"] for u in updates], [u["target_tokens"] for u in updates])
             for case_order, _, updates in evidence[arm]]
            for arm in course.ARMS
        ]
        self.assertEqual(matched[0], matched[1])
        self.assertEqual(matched[0], matched[2])
        self.assertNotEqual(evidence["SINGLE_ONLY"][0][1], evidence["MIXED_CROSSOVER"][0][1])
        self.assertLess(evidence["SINGLE_ONLY"][0][2][0]["input_tokens"],
                        evidence["CORRECTION_ONLY"][0][2][0]["input_tokens"])
        broken = copy.deepcopy(records)
        broken[1][1][-2] += 1
        with self.assertRaisesRegex(ValueError, "target IDs differ"):
            trainer.paired_epochs(rows, broken, "SINGLE_ONLY", seed=1337)
        with self.assertRaisesRegex(ValueError, "shorter than an input"):
            trainer.pad_batch(records[:2], 0, width=1)

    def test_raw_source_group_overlap_is_rejected_even_when_ids_and_prompts_differ(self):
        def row(source_id, group, question):
            return {"meta": {"source": "fixture", "source_id": source_id, "source_group_id": group},
                    "messages": [{"role": "user", "content": question}, {"role": "assistant", "content": "ok"}]}

        train = [row("one", "a", "one?")]
        dev = [row("two", "b", "two?")]
        final = [row("three", "c", "three?")]
        trainer.validate_paired_splits(train, dev, final)
        with self.assertRaisesRegex(ValueError, "source-group overlap"):
            trainer.validate_paired_splits(train, dev, [row("three", "b", "different fourth?")])
        with self.assertRaisesRegex(ValueError, "normalized first-prompt overlap"):
            trainer.validate_paired_splits(train, dev, [row("three", "c", " TWO? ")])
        with self.assertRaisesRegex(ValueError, "explicit source"):
            trainer.validate_paired_splits(train, dev, [row("three", "", "three?")])

    def test_public_cli_input_gate_requires_only_paired_runs_to_supply_final(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            ckpt, ready, logs, cache = [root / name for name in ("ckpt", "ready", "logs", "data_cache")]
            for directory in (ckpt, ready, logs, cache):
                directory.mkdir()
            parent = ckpt / "m100_ko-en_300M_chat32_fixture.pt"
            tokenizer = cache / "tok-ko-en-32768-chat32.json"
            inputs = {split: ready / f"fixture_{split}.canonical.jsonl" for split in ("train", "val", "final")}
            for file, body in [(parent, b"header only"), (tokenizer, b"hash only"),
                               *((path, split.encode()) for split, path in inputs.items())]:
                file.write_bytes(body)
            manifest_path = ready / "fixture_manifest.json"
            manifest = {"schema": "TINYLM_PUBLIC_SFT_V1", "source_quality_gate": "PASS",
                        "contamination_gate": "PASS", "tokenizer_mask_gate": "PASS",
                        "output_sha256": {split: trainer.sha256(path) for split, path in inputs.items()}}
            args = SimpleNamespace(parent=parent, tokenizer=tokenizer, train=inputs["train"], val=inputs["val"],
                                   manifest=manifest_path, output=ckpt / "new.pt", log=logs / "new.json",
                                   parent_sha256=trainer.sha256(parent), tokenizer_sha256=trainer.sha256(tokenizer),
                                   data="ko-en", lineage="chat32", pilot_only=False, epochs=4,
                                   correction_arm="MIXED_CROSSOVER")
            with patch.multiple(trainer, ROOT=root, READY=ready, CKPT=ckpt, LOGS=logs):
                manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
                self.assertEqual(trainer.check_inputs(args)[-1], manifest)
                args.pilot_only = True
                with self.assertRaisesRegex(ValueError, "four formal"):
                    trainer.check_inputs(args)
                args.pilot_only = False
                args.epochs = 3
                with self.assertRaisesRegex(ValueError, "four formal"):
                    trainer.check_inputs(args)
                args.epochs = 4
                manifest["source_quality_gate"] = "NOT_RUN"
                manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "source_quality_gate"):
                    trainer.check_inputs(args)
                manifest["source_quality_gate"] = "PASS"
                original_final = manifest["output_sha256"].pop("final")
                manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "pinned final split"):
                    trainer.check_inputs(args)
                args.correction_arm = None
                self.assertEqual(trainer.check_inputs(args)[-1], manifest)
                args.correction_arm = "SINGLE_ONLY"
                manifest["output_sha256"]["final"] = original_final
                manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
                inputs["final"].write_bytes(b"changed")
                with self.assertRaisesRegex(ValueError, "final SHA256"):
                    trainer.check_inputs(args)

    def test_train_consumes_the_paired_order_and_keeps_final_out_of_encoding(self):
        import torch

        class Tokenizer:
            def get_vocab_size(self):
                return 32768

            def token_to_id(self, token):
                return 0

            def encode(self, text):
                if "reserved question" in text:
                    raise AssertionError("reserved final text reached the tokenizer")
                return SimpleNamespace(ids=[ord(c) for c in text],
                                       offsets=[(i, i + 1) for i in range(len(text))])

        class Model(torch.nn.Module):
            def __init__(self):
                super().__init__()
                self.weight = torch.nn.Parameter(torch.tensor(1.0))

            def to(self, device):
                return self

            def set_anneal(self, value):
                pass

        def loss(model, batch, pad_id, device, vocab, chunk, *, width=None):
            self.assertEqual(width, 1024)
            positions, labels = trainer.pad_batch(batch, pad_id, width=width)
            self.assertEqual(positions.shape, labels.shape)
            return model.weight.square() * labels.ne(trainer.IGNORE).sum()

        rows = fixture()
        for row in rows:
            row["meta"].update(source="fixture", source_id=row["meta"]["case_id"])
        held = {"meta": {"source": "fixture", "source_id": "dev", "source_group_id": "dev"},
                "messages": [{"role": "user", "content": "dev question"}, {"role": "assistant", "content": "ok"}]}
        final = copy.deepcopy(held)
        final["meta"].update(source_id="final", source_group_id="final")
        final["messages"][0]["content"] = "reserved question"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            train, val, test = [root / f"fixture_{split}.canonical.jsonl" for split in ("train", "val", "final")]
            for path, values in ((train, rows), (val, [held]), (test, [final])):
                path.write_text("".join(json.dumps(row) + "\n" for row in values), encoding="utf-8")
            manifest = dict(contamination_gate="PASS", tokenizer_mask_gate="PASS", source_quality_gate="PASS",
                            output_sha256={split: trainer.sha256(path)
                                           for split, path in zip(("train", "val", "final"), (train, val, test))})
            args = SimpleNamespace(seed=1337, lineage="legacy", data="ko-en", tokenizer_sha256="0000",
                                   parent_sha256="0000", optimizer="adamw", lr=0.01, epochs=4, micro_bs=2,
                                   accum=1, ce_chunk=16, muon_lr_mult=4.0, matrix_weight_decay=0.0,
                                   pilot_only=False, correction_arm="MIXED_CROSSOVER")
            cfg = SimpleNamespace(max_seq_len=1024, vocab_size=32768, n_layers=1, dim=1, ffn_dim=1,
                                  emb_rank=1, cla_group=1, tie_mlp=False)
            tokenizer = Tokenizer()
            model = Model()
            optimizer = torch.optim.SGD(model.parameters(), lr=0.01)
            with (patch.object(trainer, "READY", root), patch.object(trainer, "loss_sum", side_effect=loss) as measured,
                  patch.object(torch.cuda, "is_available", return_value=True),
                  patch.object(torch, "load", return_value={"cfg": {}, "model": {"weight": torch.tensor(1.0)}}),
                  patch("tokenizers.Tokenizer", Mock(from_file=Mock(return_value=tokenizer))),
                  patch("tinylm.config.TMTConfig", return_value=cfg),
                  patch("tinylm.model.TiedMLPTransformer", return_value=model),
                  patch.object(trainer, "make_optimizers", return_value=(optimizer, None))):
                state = trainer.train(args, root / "fixture.pt", root / "tokenizer.json", train, val, manifest)
            self.assertEqual(measured.call_count, 12)
            self.assertEqual(state["sft"]["history"][-1]["updates"], 8)
            self.assertLess(float(state["model"]["weight"]), 1.0)
            self.assertFalse(state["sft"]["paired_course"]["reserved_final_used_for_learning"])
            records = trainer.encode_records(rows, tokenizer, 1024, 32768)
            for rec, (order, plan) in zip(state["sft"]["history"],
                                          trainer.paired_epochs(rows, records, "MIXED_CROSSOVER", 1337), strict=True):
                expected = [trainer.paired_update_receipt(blocks, 1024, sum(r[2] for block in blocks for r in block))
                            for blocks in trainer.micro_groups(records, order, 2, 1)]
                self.assertEqual(rec["paired_course"]["updates"], expected)
                self.assertEqual(rec["paired_course"]["view_order_sha256"], plan["view_order_sha256"])

if __name__=='__main__':unittest.main()
