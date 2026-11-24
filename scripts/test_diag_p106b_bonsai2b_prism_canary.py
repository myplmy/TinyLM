"""Native vocabulary/context and exact child-group ownership; no server/model."""
import signal
import unittest
from unittest.mock import Mock
from scripts.diag_p106b_bonsai2b_prism_canary import (
    vocabulary_size,validate_context,close_owned_process,ProtocolHold)

class NativePrismCanaryContracts(unittest.TestCase):
    def test_native_output_and_embedding_vocabulary_must_match(self):
        layout=dict(metadata={'general.architecture':'qwen35'},tensors={
            'token_embd.weight':{'shape':[2048,151936]},'output.weight':{'shape':[2048,151935]}})
        with self.assertRaisesRegex(ProtocolHold,'differ'):vocabulary_size(layout)
        del layout['tensors']['output.weight']
        self.assertEqual(vocabulary_size(layout),151936)

    def test_all_native_prompt_tokens_are_reprocessed(self):
        reply=dict(tokens_evaluated=3,truncated=False,timings={'prompt_n':2},
            generation_settings={'post_sampling_probs':False})
        with self.assertRaisesRegex(ProtocolHold,'cache reuse'):validate_context(reply,[1,2,3])
        reply['timings']['prompt_n']=3;validate_context(reply,[1,2,3])

    def test_sampled_probabilities_or_truncation_are_not_raw_admission(self):
        reply=dict(tokens_evaluated=2,truncated=False,timings={'prompt_n':2},
            generation_settings={'post_sampling_probs':True})
        with self.assertRaisesRegex(ProtocolHold,'pre-sampling'):validate_context(reply,[1,2])
        reply['truncated']=True
        with self.assertRaisesRegex(ProtocolHold,'truncation'):validate_context(reply,[1,2])

    def test_foreign_process_group_must_never_be_signalled(self):
        proc=Mock(pid=123);proc.poll.return_value=None
        kill=Mock()
        with self.assertRaisesRegex(RuntimeError,'our own'):
            close_owned_process(proc,getpgid=lambda pid:999,killpg=kill)
        kill.assert_not_called()

    def test_owned_new_session_child_is_reaped_after_term(self):
        proc=Mock(pid=123,returncode=-15);proc.poll.side_effect=[None,-15]
        kill=Mock();report=close_owned_process(proc,getpgid=lambda pid:123,killpg=kill)
        kill.assert_called_once_with(123,signal.SIGTERM)
        self.assertTrue(report['terminal']);proc.wait.assert_called_once_with(timeout=10)

if __name__=='__main__':unittest.main()
