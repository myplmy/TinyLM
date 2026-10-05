"""CPU contracts only; never model/GPU."""
import unittest
from unittest.mock import patch
from scripts import p106b_qwen_teacher as p


class Contracts(unittest.TestCase):
    def test_sampler(self):
        value=p.payload(p.cases()[0],1337)
        self.assertEqual(value['min_p'],0.0)
        self.assertEqual(value['temperature'],1.0)
        self.assertEqual(value['reasoning_effort'],'low')
        self.assertGreater(value['max_tokens'],value['thinking_budget_tokens'])
        self.assertFalse(value['cache_prompt'])
    def test_command(self):
        args=p.command(8888,'not-a-real-key')
        for pair in [('--gpu-layers','all'),('--fit','off'),('--spec-type','draft-mtp'),
                     ('--reasoning-format','deepseek'),('--parallel','1')]:
            self.assertEqual(args[args.index(pair[0])+1],pair[1])
        self.assertIn('--offline',args); self.assertIn('--no-op-offload',args)
        self.assertNotIn('--no-kv-offload',args)
        self.assertNotIn('--lora-scaled',args)
    def test_four_profiles(self):
        self.assertEqual([x['language'] for x in p.cases()],['ko','en','ko','ko'])
        self.assertEqual(len({x['id'] for x in p.cases()}),4)
    def test_existing_defaults_unchanged(self):
        from scripts import p106b_mtp_teacher as old
        self.assertNotEqual(old.MODEL,p.MODEL)
        self.assertNotEqual(old.SERVER,p.SERVER)
    def test_invalid_placement(self):
        with self.assertRaises(ValueError):p.command(1,'x','auto')
    def test_real_student_and_width_contract(self):
        from scripts import diag_p106b_qwen_coload as d
        with patch.object(d.OUTPUT.__class__,'exists',return_value=False), \
             patch.object(d,'arm_inputs',return_value={'parent':'p','sha':'h','tok_sha':'t'}), \
             patch.object(p,'assets',return_value={}), patch.object(p,'digest',return_value='D'):
            info=d.check()
        self.assertEqual((info['micro_bs'],info['accum'],info['seq']),(8,16,1024))
        self.assertEqual(info['padded_slots'],131072)
        self.assertTrue(info['grad_checkpoint'])
        self.assertEqual(info['optimizer_updates'],1)


if __name__=='__main__':unittest.main()
