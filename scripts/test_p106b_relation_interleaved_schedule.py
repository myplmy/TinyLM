#!/usr/bin/env python3
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from collections import Counter
import copy
import unittest
from scripts import p106b_relation_interleaved_schedule as s


def fixture():
    return {'train'+str(v):[s.factory.make(s.factory.graph(i),lang,v) for i in range(8) for lang in ('ko','en')]+[dict(meta=dict(kind='replay'),epoch=v)] for v in range(4)}


class Schedule(unittest.TestCase):
    def test_same_global_multiset_and_replay(self):
        source=fixture();old=copy.deepcopy(source);mixed,refs,proof=s.schedules(source)
        self.assertTrue(proof['canonical_record_visit_multiset_equal']);self.assertEqual(source,old)
        for v in range(4):self.assertEqual(mixed['train'+str(v)][-1],source['train'+str(v)][-1])

    def test_every_root_sees_every_view_once_and_bilingual_children_together(self):
        mixed,_,proof=s.schedules(fixture())
        for i in range(8):
            self.assertEqual({mixed['train'+str(e)][2*i]['meta']['view'] for e in range(4)},set(range(4)))
            for e in range(4):self.assertEqual(mixed['train'+str(e)][2*i]['meta']['view'],mixed['train'+str(e)][2*i+1]['meta']['view'])
        for counts in proof['per_epoch_view_rows'].values():self.assertEqual(counts,dict.fromkeys('0123',4))

    def test_source_pointers_resolve_exact_original(self):
        source=fixture();mixed,refs,_=s.schedules(source)
        for key,items in refs.items():
            for actual,p in zip(mixed[key],items):self.assertEqual(actual,source['train'+str(p['source_view'])][p['source_row_index']])

    def test_misaligned_root_and_missing_row_fail_closed(self):
        source=fixture();source['train1'][0],source['train1'][2]=source['train1'][2],source['train1'][0]
        with self.assertRaisesRegex(ValueError,'alignment'):s.schedules(source)
        source=fixture();source['train1'].pop()
        with self.assertRaisesRegex(ValueError,'lengths'):s.schedules(source)

    def test_wrong_first_answer_mask_preserved(self):
        from tokenizers import Tokenizer
        tok=Tokenizer.from_file(str(ROOT/'data_cache/tok-ko-en-32768-chat32.json'));mixed,_,_=s.schedules(fixture())
        rows=[r for values in mixed.values() for r in values if r['meta']['kind']=='fictional_relation_fields' and r['meta']['view']==3]
        for r in rows:
            rec,label=s.factory.encode(r,tok);self.assertTrue(all(y==-100 for y,seg in zip(rec.y,rec.segments) if seg==1));self.assertEqual([q['turn'] for q in label['queries']],[2])


if __name__=='__main__':unittest.main()
