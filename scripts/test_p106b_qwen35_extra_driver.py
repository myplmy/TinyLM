from datetime import timedelta
import unittest
from scripts import diag_p106b_qwen35_extra as d


class ExtraDriverContracts(unittest.TestCase):
    def test_official_lambada_function_uses_private_storage_globals_only(self):
        self.assertIs(d.LOAD_LAMBADA.__code__,d.l.load_task.__code__)
        self.assertIsNot(d.LOAD_LAMBADA.__globals__,d.l.load_task.__globals__)
        self.assertEqual(d.LOAD_LAMBADA.__globals__['CACHE'],d.BASE/'runtime_cache')
        self.assertNotEqual(d.l.CACHE,d.BASE/'runtime_cache')

    def test_phase_budget_preserves_deadline_and_rejects_expired(self):
        now=d.qfixed.DEADLINE-timedelta(hours=2)
        self.assertEqual(d.phase_budget('cost',now),1800)
        self.assertEqual(d.phase_budget('belebele',now),6300)
        with self.assertRaises(TimeoutError):d.phase_budget('lambada',d.qfixed.DEADLINE)


if __name__=='__main__':unittest.main()
