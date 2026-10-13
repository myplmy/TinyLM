"""CPU fixtures for freshness, fatal state and restoration; no hardware queries."""
import subprocess
import unittest
from scripts.p106b_memory_stream import FreshSamples,parse_memory,stream_session_scope

class MemoryTests(unittest.TestCase):
    def test_parse_valid_single_gpu(self):
        self.assertEqual(parse_memory('1234, 14000\n'),(1234,14000))
    def test_bad_rows_fail_closed(self):
        for line in ('N/A,2','1,2,3','-1,2','GPU lost','1.0,2',''):
            with self.assertRaises(ValueError):parse_memory(line)
    def test_same_numeric_value_needs_new_sequence(self):
        state=FreshSamples(timeout=.01);state.observe((1,9));self.assertEqual(state.read(),(1,9))
        with self.assertRaises(subprocess.TimeoutExpired):state.read()
        state.observe((1,9));self.assertEqual(state.read(),(1,9))
        self.assertEqual(state.snapshot()['delivered_sequence'],2)
    def test_newest_frame_only_and_staleness(self):
        tick=[10.];state=FreshSamples(clock=lambda:tick[0],timeout=0,max_age=2)
        state.observe((1,9));state.observe((2,8));self.assertEqual(state.read(),(2,8))
        state.observe((3,7));tick[0]=13
        with self.assertRaises(subprocess.TimeoutExpired):state.read()
    def test_dead_stream_never_returns_buffered_good_frame(self):
        state=FreshSamples();state.observe((1,9));state.mark_dead('EOF')
        with self.assertRaisesRegex(RuntimeError,'EOF'):state.read()
    def test_invalid_value_is_not_accepted(self):
        state=FreshSamples()
        for v in ((True,1),(-1,2),(1,),[1,2]):
            with self.assertRaises(ValueError):state.observe(v)
    def test_scope_restores_even_on_error(self):
        from scripts import diag_p106_vram_sample as memory
        from scripts import diag_p106b_mtp_teacher as life
        original=(memory.read_memory,life.Session.memory)
        reader=lambda:(1,9)
        with self.assertRaises(RuntimeError):
            with stream_session_scope(reader):
                self.assertIs(memory.read_memory,reader)
                self.assertIsNot(life.Session.memory,original[1]);raise RuntimeError('fixture')
        self.assertIs(memory.read_memory,original[0]);self.assertIs(life.Session.memory,original[1])

if __name__=='__main__':unittest.main(verbosity=2)
