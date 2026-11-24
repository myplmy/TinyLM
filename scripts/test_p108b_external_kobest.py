import unittest
from types import SimpleNamespace
from scripts import diag_p108b_external_kobest as driver

class ExternalKoBESTTests(unittest.TestCase):
    def test_exact_task_set_excludes_unneeded_core6(self):
        counts=dict(kobest_a=1404,kobest_b=1000,kobest_c=1000,kobest_d=1000,kobest_e=157)
        tasks={n:SimpleNamespace(eval_docs=[None]*size)for n,size in counts.items()}
        tasks['unneeded_core']=SimpleNamespace(eval_docs=[None])
        self.assertEqual(set(driver.select_tasks(tasks,counts)),set(counts))
    def test_missing_or_extra_task_fails_closed(self):
        counts=dict(kobest_a=1404,kobest_b=1000,kobest_c=1000,kobest_d=1000,kobest_e=157)
        with self.assertRaises(ValueError):driver.select_tasks({},counts)
        bad={n:SimpleNamespace(eval_docs=[None]*size)for n,size in counts.items()};bad['kobest_extra']=SimpleNamespace(eval_docs=[])
        with self.assertRaises(ValueError):driver.select_tasks(bad,counts)

if __name__=='__main__':unittest.main()
