import unittest
from scripts.check_p101a_clean_cost import validate


class CostTests(unittest.TestCase):
    def setUp(self):
        self.metadata = dict(code_sha256={"source": "A"}, family="mtp", seed=1337, lr=5e-5,
                             model_loading="NOT_RUN", meaningful_training="NOT_RUN", max_wall_sec=1200)
        self.cost = dict(self.metadata, arm="parent_mtp", corpus_sha256="B", updates=32,
            expected_full_updates=704, checkpoint_saved=False, status="COST_CALIBRATION_COMPLETE",
            update_seconds=[2.] * 32, whole_wall_sec=100., actual_processed_x_tokens=1000,
            assistant_targets=100, model_loading="MEASURED", meaningful_training="RESOURCE_ONLY")

    def check(self, cost=None):
        return validate(self.cost if cost is None else cost, self.metadata, "B", "parent_mtp", 704)

    def test_valid(self): self.assertTrue(self.check())
    def test_code(self):
        self.cost["code_sha256"] = {"source": "C"}
        with self.assertRaises(ValueError): self.check()
    def test_learning_rate(self):
        self.cost["lr"] = 1e-4
        with self.assertRaises(ValueError): self.check()
    def test_arm(self):
        self.cost["arm"] = "parent_ntp"
        with self.assertRaises(ValueError): self.check()
    def test_corpus(self):
        self.cost["corpus_sha256"] = "C"
        with self.assertRaises(ValueError): self.check()
    def test_nonfinite(self):
        self.cost["update_seconds"][2] = float("nan")
        with self.assertRaises(ValueError): self.check()
    def test_partial(self):
        self.cost["update_seconds"].pop()
        with self.assertRaises(ValueError): self.check()
    def test_saved_checkpoint(self):
        self.cost["checkpoint_saved"] = True
        with self.assertRaises(ValueError): self.check()


if __name__ == "__main__": unittest.main()
