"""CPU contracts only; never model/GPU."""
import unittest
from unittest.mock import patch
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
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
    def test_empty_optional_note_raw_preserved(self):
        final='[[QUESTION]]\nq\n[[/QUESTION]]\n[[ANSWER]]\na\n[[/ANSWER]]\n[[NOTE]]\n[[/NOTE]]'
        reply={'choices':[{'finish_reason':'stop','message':{'content':final,'reasoning_content':'thought'}}]}
        result=p.parsed_response(reply,'en')
        self.assertEqual(result['format_status'],'TAGGED_COMPLETE')
        self.assertEqual(result['teacher_final_content'],final)
        self.assertEqual(reply['choices'][0]['message']['content'],final)
        self.assertEqual(result['parsed_content']['assistant_text'],'a')
    def test_required_fields_and_length_remain_rejected(self):
        for final,finish in [('[[NOTE]]\n[[/NOTE]]','stop'),
            ('[[QUESTION]]\nq\n[[/QUESTION]]\n[[ANSWER]]\na','length')]:
            self.assertNotEqual(p.parsed_response({'choices':[{'finish_reason':finish,'message':{'content':final}}]},'en')['format_status'],'TAGGED_COMPLETE')
    def test_canonical_excludes_thinking_and_preserves_source(self):
        from tinylm.chat.serialize import serialize
        case=dict(id='fixture',language='en',question='q')
        final='[[QUESTION]]\nq\n[[/QUESTION]]\n[[ANSWER]]\na\n[[/ANSWER]]'
        reply={'choices':[{'finish_reason':'stop','message':{'content':final,'reasoning_content':'not-student-secret'}}]}
        row=p.canonical_candidate(reply,case,'test_result/evidence/fixture.json')
        self.assertEqual([x['role'] for x in row['messages']],['user','assistant'])
        self.assertEqual(row['meta']['teacher_model_sha256'],p.MODEL_SHA)
        self.assertNotIn('not-student-secret',serialize(row,'chatml'))
        self.assertEqual(row['meta']['label_status'],'PSEUDO_UNVERIFIED')
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
