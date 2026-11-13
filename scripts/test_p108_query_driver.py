import unittest
from unittest.mock import patch
import torch
from scripts import diag_p108_query_value as d


class QueryDriver(unittest.TestCase):
    def test_position_adapter_does_not_use_subject_or_answer_end(self):
        item=dict(x=torch.tensor([[5,6,7,8,9]]),prompt_ids=[5,6,7],start=2,position=0)
        with patch.object(d.prior,'pack',return_value=item):actual=d.pack({}, {})
        self.assertEqual(actual['position'],2);self.assertEqual(item['position'],0)

    def test_fit_only_selection_and_fixed_caps(self):
        def row(exact,nll,norm,dev):return dict(oracle_fit=dict(exact=exact),optimization=dict(trace=[dict(nll=nll)],actual_value_norm=norm),dev_exact=dev)
        a,b=row(1,2.,3.,False),row(0,.1,1.,True)
        self.assertIs(d.pick([a,b]),a)
        self.assertIsNone(d.pick([b]))
        self.assertEqual([d.cap_status(x) for x in [.05,.051,.20,.21,0.]],
            ['PRIMARY_CAP5','LARGE_EDIT_DIAGNOSTIC_ONLY','LARGE_EDIT_DIAGNOSTIC_ONLY','CAP20_REJECTED','CAP20_REJECTED'])


if __name__=='__main__':unittest.main()
