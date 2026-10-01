"""Synthetic packet-only tests, no actual answer quality review."""
import unittest
from scripts.p106b_review_packet import packet, validate_annotation, ASPECTS


class Tests(unittest.TestCase):
    def fixture(self):
        value = packet("Output1", "1", source={"arm": "hidden", "effort": "hidden"})
        annotation = {"packet_id": value["packet_id"], "packet_sha256": value["packet_sha256"],
            "reviewer": "fixture-not-model", "status": "REVIEWER_OPINION",
            "aspects": {name: {"label": "UNCERTAIN", "reason": "fixture", "answer_quote": ""} for name in ASPECTS}}
        return value, annotation

    def test_blinded_source_identity_preserves_hash_only(self):
        value, _a = self.fixture()
        self.assertNotIn("source_identity", value)
        self.assertNotIn("hidden", str(value))
        self.assertEqual(len(value["source_identity_sha256"]), 64)

    def test_review_cannot_promote_training_or_truth(self):
        value, annotation = self.fixture()
        result = validate_annotation(annotation, value)
        self.assertFalse(result["formal_train_ready"])
        self.assertFalse(result["independent_truth_verified"])

    def test_fabricated_quote_is_not_accepted(self):
        value, annotation = self.fixture()
        annotation["aspects"]["format"].update(label="ISSUE", answer_quote="not in source")
        with self.assertRaises(ValueError):
            validate_annotation(annotation, value)

    def test_source_modification_breaks_binding(self):
        value, annotation = self.fixture()
        value["answer"] = "changed"
        with self.assertRaises(ValueError):
            validate_annotation(annotation, value)

    def test_empty_answer_has_verifiable_absence_not_fabricated_quote(self):
        value = packet("Output1", "", source={"fixture": True})
        _v, annotation = self.fixture()
        annotation.update(packet_id=value["packet_id"], packet_sha256=value["packet_sha256"])
        annotation["aspects"]["format"].update(label="ISSUE", evidence_kind="MISSING_OUTPUT")
        self.assertFalse(validate_annotation(annotation, value)["formal_train_ready"])


if __name__ == "__main__":
    unittest.main()
