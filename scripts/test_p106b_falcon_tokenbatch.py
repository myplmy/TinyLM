"""CPU checks of bounded scheduling and the exact three-literal transform."""
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from scripts import diag_p106b_falcon_tokenbatch as variant


class BoundedBatch(unittest.TestCase):
    def chunks(self,lengths):
        from lm_eval.models.utils import Collator
        obj=SimpleNamespace()
        requests=[(None,[0]*n,[1]) for n in lengths]
        return list(Collator.get_chunks(requests,fn=lambda i,rs:variant.scheduler(obj,i,rs)))

    def test_exact_transform(self):
        self.assertEqual(variant.TRANSFORM_COUNTS,{'set':1,'assert':1,'call':1})

    def test_short(self):
        self.assertEqual([len(c) for c in self.chunks([512]*18)],[8,8,2])

    def test_long(self):
        self.assertEqual([len(c) for c in self.chunks([1024]*10)],[4,4,2])

    def test_boundary_never_grows_an_open_long_chunk(self):
        lengths=[1024]*5+[512]*17
        chunks=self.chunks(lengths)
        self.assertEqual([len(c) for c in chunks],[4,4,8,6])
        self.assertTrue(all(len(c)*min(len(c[0][1]),1024)<=4096 for c in chunks))
        self.assertEqual([len(r[1]) for c in chunks for r in c],lengths)

    def test_policy_changes_only_computational_batch(self):
        original=variant.ORIGIN_PRIOR.policy(0)
        changed=variant.policy(0)
        self.assertEqual({k:v for k,v in changed.items() if k not in ('batch_size','maximum_forward_padded_positions')},
            {k:v for k,v in original.items() if k!='batch_size'})

    def test_bounded_scheduler_installed_before_first_canary(self):
        lm=SimpleNamespace()
        def first(model,_):
            self.assertIs(model._batch_scheduler.__func__,variant.scheduler)
            return 'NO_AUTO_BATCH_SEARCH'
        with patch.object(variant.ORIGINAL_OLD,'numerical_canary',side_effect=first):
            self.assertEqual(variant.OldRuntimeProxy().numerical_canary(lm,None),'NO_AUTO_BATCH_SEARCH')


if __name__=='__main__':unittest.main()
