"""CPU-only course, grouping, visible reference and assistant MTP contracts."""
import json
import unittest
from collections import Counter
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
from scripts import p106b_context_quality as data

class CourseTests(unittest.TestCase):
    def test_balanced_unique_grouped_split(self):
        rows=data.build();allrows=[r for v in rows.values() for r in v]
        self.assertEqual([len(rows[s]) for s in ('train','val')],[4096,512])
        self.assertEqual(len({r['meta']['semantic_root_id'] for r in allrows}),4608)
        self.assertEqual(len({data.sha(r['messages']) for r in allrows}),4608)
        self.assertEqual(Counter(r['meta']['language'] for r in rows['train']),{'ko':2048,'en':2048})
        self.assertEqual(set(Counter(r['meta']['kind'] for r in rows['val']).values()),{64})
    def test_root_shared_across_translations_formats_and_query_targets(self):
        for seed in (1,2,3,17,31):
            ko=data.make('lookup','ko',seed);en=data.make('lookup','en',seed)
            obj=data.make('json','ko',seed);missing=data.make('missing_item','ko',seed)
            roots={r['meta']['semantic_root_id'] for r in (ko,en,obj,missing)}
            self.assertEqual(len(roots),1)
            self.assertEqual(data.make('missing_reference','ko',seed)['meta']['semantic_root_id'],
                data.make('clarify_followup','en',seed)['meta']['semantic_root_id'])
    def test_known_json_and_updated_integer(self):
        row=data.make('json','ko',17);value=json.loads(data.text(row,-1))
        self.assertEqual(set(value),{'answer'})
        row=data.make('update','ko',17)
        self.assertEqual([m['role'] for m in row['messages']],['user','assistant','user','assistant'])
        self.assertNotEqual(data.text(row,1),data.text(row,3))
    def test_teacher_has_only_visible_reference_and_explicit_clarification(self):
        request=data.teacher_payload('Which building?',None,'en',17)
        body=json.loads(request['messages'][1]['content'])
        self.assertEqual(body['STUDENT_VISIBLE_REFERENCE'],'')
        self.assertEqual(set(body),{'language','question','STUDENT_VISIBLE_REFERENCE','producer_task'})
        self.assertIn('instead of guessing',request['messages'][0]['content'])
        self.assertFalse(request['cache_prompt'])
    def test_turn_mask_and_target_counts(self):
        from tinylm.data.prepare import SyntheticTokenizer
        from tinylm.train import mtp_sft as core
        import torch
        record=core.encode_record(data.make('clarify_followup','ko',17),SyntheticTokenizer())
        self.assertEqual({s for s in record.segments if s},{1,2})
        _,y,s=core.pad_records([record],0)
        for h in (2,3,4):
            target,valid=core.horizon_targets(y,s,h)
            shift=h-1
            self.assertTrue(bool((s[:,:-shift][valid]==s[:,shift:][valid]).all()))
            self.assertFalse(bool((target[valid]==-100).any()))

if __name__=='__main__':unittest.main(verbosity=2)
