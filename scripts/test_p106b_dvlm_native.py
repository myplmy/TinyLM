"""Independent tiny Qwen causal reference for explicit PTS/HPA masks and positions."""
from dataclasses import asdict, replace
import unittest

from scripts.p106b_dvlm_pts import AdmissionHold, build_layout
from scripts.p106b_dvlm_native import restore_layout, validate_layout, native_case


def example_layout():
    return build_layout([1,2,3], [10,11], [b'a',b'b',b'cd'], [b'ab',b'cd'],
                        [[20,21],[22],[23,24]], max_length=64)


class NativeLayoutTests(unittest.TestCase):
    def test_roundtrip_preserves_complete_expansions_and_default_serial_positions(self):
        original = example_layout()
        self.assertEqual(restore_layout(asdict(original)), original)

    def test_lost_private_head_is_refused(self):
        layout = example_layout()
        with self.assertRaisesRegex(AdmissionHold, 'head locations'):
            validate_layout(replace(layout, head_indices=(2,3,4)))

    def test_physical_concatenation_positions_are_refused(self):
        layout = example_layout()
        with self.assertRaisesRegex(AdmissionHold, 'logical positions'):
            validate_layout(replace(layout, position_ids=tuple(range(len(layout.input_ids)))))

    def test_duplicate_group_coverage_is_refused(self):
        layout = example_layout()
        with self.assertRaisesRegex(AdmissionHold, 'coverage'):
            validate_layout(replace(layout, groups=(layout.groups[0],layout.groups[0])))

    def test_outside_student_owner_is_refused(self):
        layout = example_layout()
        with self.assertRaisesRegex(AdmissionHold, 'owners outside'):
            validate_layout(replace(layout, expansion_owner=(0,0,1,2,9)))

    def test_actual_tiny_cpu_qwen_matches_independent_causal_branches(self):
        import torch
        import tinylm  # Follow the runtime cache policy in the CPU contract test.
        from transformers import Qwen3Config, Qwen3ForCausalLM
        before_cuda = torch.cuda.is_initialized()
        torch.set_num_threads(1)
        torch.manual_seed(1337)
        config = Qwen3Config(vocab_size=64, hidden_size=32, intermediate_size=48,
            num_hidden_layers=2, num_attention_heads=4, num_key_value_heads=2,
            head_dim=8, max_position_embeddings=128, attention_dropout=0., use_cache=False)
        config._attn_implementation = 'eager'
        with torch.device('cpu'):
            model = Qwen3ForCausalLM(config).eval()
        calls = []
        hook = model.lm_head.register_forward_hook(lambda *_: calls.append(1))
        try:
            with torch.inference_mode():
                report, packets = native_case(torch, model, example_layout(), atol=1e-5, rtol=1e-4)
            self.assertTrue(report['passed'], report)
            self.assertEqual(calls, [])
            self.assertEqual(packets['pts_private'].shape, (5,32))
            self.assertIsNotNone(report['same_group_response'])
        finally:
            hook.remove()
        self.assertEqual(torch.cuda.is_initialized(), before_cuda)


if __name__ == '__main__':
    unittest.main()
