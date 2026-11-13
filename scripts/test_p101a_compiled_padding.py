import json
import os
import signal
from pathlib import Path
import sys
import tempfile
import unittest
from scripts import diag_p101a_compiled_padding as d
from scripts import test_p101a_padding_crop as fixture
from scripts import diag_p101a_sft_mtp as engine
from tinylm.train import mtp_sft as core


class CompiledContracts(unittest.TestCase):
    def test_registered_arm_interface_preserves_all_six_physical_conditions(self):
        for mode in ('ntp','mtp'):
            for q in (128,64,32):self.assertEqual(d.unpack_arm(d.phase_name(mode,q)),(mode,q))
        for value in ('ntp_q16','float_q128','mtp','unknown'):
            with self.assertRaises(ValueError):d.unpack_arm(value)

    def test_exact_modes_policies_and_sorted_original_groups(self):
        for mode in ('ntp','mtp'):
            for q in (32,64,128):self.assertEqual(d.phase_name(mode,q),mode+'_q'+str(q))
        with self.assertRaises(ValueError):d.phase_name('ntp',16)
        with self.assertRaises(ValueError):d.phase_name('float',128)
        rows=[dict(absolute_update=i) for i in (142,629,590,72,549,26,332)]
        self.assertEqual([g['absolute_update'] for g in d.ordered_groups(dict(selected_groups=rows))],[26,72,142,332,549,590,629])

    def test_whole_group_masses_match_existing_horizon_helper(self):
        _,_,records=fixture.encoded_fixture();groups=next(engine.batches(records,0))
        expected={h:sum(core.count_record(r)[h] for r in records) for h in (1,2,3,4)}
        self.assertEqual(d.denominators(groups),expected)
        with self.assertRaises(ValueError):d.denominators(groups[:15])

    def test_child_stdout_preserved_and_process_reaped(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'stdout.txt'
            r=d.run_child([sys.executable,'-c','print(12345)'],path,5,dict(os.environ))
            self.assertEqual(r['returncode'],0);self.assertEqual(path.read_text().strip(),'12345')

    def test_timed_out_owned_child_group_is_terminated(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'stdout.txt'
            with self.assertRaises(TimeoutError):d.run_child([sys.executable,'-c','import time; time.sleep(30)'],path,.1,dict(os.environ))

    def test_fresh_process_and_initial_head_identity_are_required(self):
        a=dict(initial_core_sha256='core',initial_head_sha256={'2':'head'},process_id=1)
        d.check_block_identity(a,dict(a,process_id=2))
        with self.assertRaises(ValueError):d.check_block_identity(a,a)
        with self.assertRaises(ValueError):d.check_block_identity(a,dict(a,process_id=2,initial_head_sha256={}))

    def test_real_parent_termination_restores_signal_handler(self):
        original=signal.getsignal(signal.SIGTERM)
        with self.assertRaises(TimeoutError):
            with d.termination_as_exception():os.kill(os.getpid(),signal.SIGTERM)
        self.assertIs(signal.getsignal(signal.SIGTERM),original)


if __name__=='__main__':unittest.main()
