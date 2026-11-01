"""CPU contracts for shot attribution, frozen parity and unchanged official body."""
from pathlib import Path
import json
import tempfile
import unittest
from scripts import diag_p106b_falcon_logitreuse_shots as driver


class ShotContract(unittest.TestCase):
    def test_deadline_and_only_compute_reuse_policy(self):
        self.assertEqual(driver.base.prior.DEADLINE.isoformat(),'2026-11-01T06:00:00+00:00')
        for shot in (0,5):
            old=driver.completed.ORIGIN_PRIOR.policy(shot)
            new=driver.base.prior.policy(shot)
            self.assertFalse(old.pop('logits_cache'))
            self.assertTrue(new.pop('logits_cache'))
            self.assertEqual(old,new)

    def test_official_evaluate_body_is_unchanged(self):
        self.assertEqual(driver.base.evaluate.__code__.co_filename,driver.base.__file__)
        self.assertNotEqual(driver.PROFILE,driver.COMPLETED_PROFILE)
        self.assertIn('shots_v1',str(driver.OUTPUT))

    def fixture(self, root, *, shots=5, delta=0., wrong_arg=False):
        folder=Path(root)/'shot5/cost'
        report=dict(final_exit=0,actual_rows=114,shots=shots,profile_sha256='PROFILE',samples={})
        for i in range(57):
            name='task'+str(i)
            path=folder/'samples'/name/'responses.jsonl'
            path.parent.mkdir(parents=True)
            rows=[dict(doc_id=j,arguments=[['different' if wrong_arg else 'context',' A']],
                filtered_resps=[[float(k)+delta,False] for k in range(4)]) for j in range(2)]
            path.write_text(chr(10).join(json.dumps(x) for x in rows)+chr(10))
            report['samples'][name]={'shards':[{'path':path.name,'sha256':driver.base.data.digest(path)}]}
        (folder/'report.json').write_text(json.dumps(report))

    def compare_fixture(self, **changes):
        with tempfile.TemporaryDirectory() as t:
            a,b=Path(t)/'old',Path(t)/'new'
            self.fixture(a)
            self.fixture(b,**changes)
            return driver.compare_cost(5,a,b,'PROFILE')

    def test_valid_full_cost_parity(self):
        result=self.compare_fixture(delta=1e-6)
        self.assertEqual((result['shots'],result['rows'],result['loglikelihoods']),(5,114,456))

    def test_wrong_shot_cannot_pass(self):
        with self.assertRaises(AssertionError):
            self.compare_fixture(shots=0)

    def test_prompt_mismatch_cannot_pass(self):
        with self.assertRaises(AssertionError):
            self.compare_fixture(wrong_arg=True)

    def test_numeric_mismatch_cannot_pass(self):
        with self.assertRaises(AssertionError):
            self.compare_fixture(delta=.01)

    def test_bad_shot_type_fails_before_read(self):
        for shot in (True,1,4):
            with self.assertRaises(ValueError):
                driver.compare_cost(shot,Path('/not-read'),Path('/not-read'),'x')


if __name__=='__main__':
    unittest.main()
