from datetime import timedelta
from unittest.mock import patch
import unittest
from scripts import diag_p108_joint_write as d


class JointDriverContracts(unittest.TestCase):
    def test_authority_reserve_rejects_expired_before_model(self):
        class Late:
            @staticmethod
            def now(zone):return d.DEADLINE+timedelta(seconds=1)
        with patch.object(d,'datetime',Late):
            with self.assertRaises(TimeoutError):d.Budget().check()

    def test_existing_prefill_and_registered_edit_primitives_are_reused(self):
        from scripts import p108_wsp_attention
        from scripts import diag_p108_query_transport
        self.assertIs(d.wsp.edit,p108_wsp_attention.edit)
        self.assertIs(d.transport.capture,diag_p108_query_transport.capture)
        self.assertIs(d.transport.local_answer,diag_p108_query_transport.local_answer)


if __name__=='__main__':unittest.main()
