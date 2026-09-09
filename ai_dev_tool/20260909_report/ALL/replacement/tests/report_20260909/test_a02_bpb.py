import math
import unittest
import torch
from scripts.common_bpb import document_nll
from scripts.build_bpb_exclusion import rolling_hashes
from tinylm.eval.bpb_corpus import corpus_digest, exclude_documents, merge_exclusions
from tinylm.eval.paired_records import paired_bpb
from support_report import CharacterTokenizer, paired_record


class UniformModel:
    def __call__(self, ids):
        return torch.zeros((*ids.shape, 32), device=ids.device)


class BpbTests(unittest.TestCase):
    def test_every_target_including_tail_and_unicode_bytes(self):
        for seq, stride, batch in [(4, 3, 1), (4, 4, 2), (8, 1, 3)]:
            text = "a한b글xyz"
            result = document_nll(UniformModel(), CharacterTokenizer(), text,
                                  device="cpu", seq=seq, stride=stride, micro_bs=batch, ce_chunk=2)
            self.assertEqual(result["scored_tokens"], len(text))
            self.assertEqual(result["scored_bytes"], len(text.encode("utf-8")))
            self.assertEqual(result["tail_tokens_omitted"], 0)
            self.assertAlmostEqual(result["nll_sum"], len(text) * math.log(32), places=5)

    def test_exact_rolling_hash(self):
        ids, width = [1, 2, 3, 4, 5, 6], 3
        expected = []
        for start in range(len(ids) - width + 1):
            value = 0
            for x in ids[start:start+width]:
                value = (value * 1000003 + x + 1) & ((1 << 64) - 1)
            expected.append((value, start))
        self.assertEqual(list(rolling_hashes(ids, width)), expected)

    def test_exclusion_does_not_silently_ignore_ids(self):
        docs = [{"id": "a", "text_sha256": "1"}, {"id": "b", "text_sha256": "2"}]
        manifest = {"schema": "tinylm.bpb-exclusion.v1", "corpus_sha256": corpus_digest(docs),
                    "scan_complete": True, "document_count": 2, "excluded_ids": ["a"]}
        self.assertEqual([d["id"] for d in exclude_documents(docs, manifest)], ["b"])
        manifest["excluded_ids"] = ["missing"]
        with self.assertRaises(ValueError):
            exclude_documents(docs, manifest)

    def test_byte_weighted_difference_is_not_document_mean(self):
        left, right = [], []
        for ident, size, delta in [("a", 1, 10.0), ("b", 9, 0.0)]:
            a = paired_record(ident, delta, metric="bpb")
            b = paired_record(ident, 0.0, metric="bpb")
            a.update(scored_bytes=size, nll_sum=delta * size * math.log(2))
            b.update(scored_bytes=size, nll_sum=0.0)
            left.append(a)
            right.append(b)
        result = paired_bpb(left, right, draws=100)
        self.assertAlmostEqual(result["mean"], 1.0)

    def test_multiple_tokenizer_exclusions_use_common_union(self):
        docs = [{"id": i, "text_sha256": i} for i in ("a", "b", "c")]
        base = {"schema": "tinylm.bpb-exclusion.v1", "corpus_sha256": corpus_digest(docs),
                "scan_complete": True, "document_count": len(docs)}
        manifests = [dict(base, excluded_ids=["a"], tokenizer_sha256="native"),
                     dict(base, excluded_ids=["b"], tokenizer_sha256="teacher")]
        merged = merge_exclusions(docs, manifests, inputs=[{"sha256": "1"}, {"sha256": "2"}])
        self.assertEqual(merged["excluded_ids"], ["a", "b"])
        self.assertEqual([d["id"] for d in exclude_documents(docs, merged)], ["c"])
        manifests[1]["corpus_sha256"] = "different"
        with self.assertRaises(ValueError):
            merge_exclusions(docs, manifests, inputs=[{}, {}])
