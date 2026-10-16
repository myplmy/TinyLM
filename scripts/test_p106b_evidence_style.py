#!/usr/bin/env python3
"""CPU-only posthoc wording invariants and exact replay regression."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import copy
from datetime import datetime,timezone,timedelta
import unittest
from scripts import diag_p106b_evidence_style as gate
from scripts import p106b_evidence_recovery as method


class WordingContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tok=gate.course.upstream.old._tokenizer()
        cls.rows=[method.make(g,lang,condition,True,3,cls.tok)
            for g in method.graphs(4,'test') for lang in ('ko','en') for condition in range(4)]

    def test_only_wording_changes_and_full_output_budget(self):
        for row in self.rows:
            result=gate.views(row,self.tok);m=row['meta'];prefixes=[]
            for style in (0,3):
                view=result['views'][str(style)]
                q=method.question(m['requested_fields'][0],m['language'],style)
                content=gate.text(view['messages'][0]);self.assertTrue(content.endswith(q))
                prefixes.append(content[:-len(q)]);self.assertLessEqual(view['prompt_tokens']+64,1024)
            self.assertEqual(prefixes[0],prefixes[1])
            self.assertEqual(result['gold'],gate.text(row['messages'][1]))

    def test_original_style3_input_drift_is_rejected(self):
        row=copy.deepcopy(self.rows[0]);row['messages'][0]['content'][0]['text']+=' EXTRA'
        with self.assertRaisesRegex(ValueError,'original style3'):gate.views(row,self.tok)

    def test_anchor_checks_answer_and_generation_not_just_count(self):
        event=dict(messages=[dict(role='user',content='question')],answer='5',gold='5',
            generation=dict(prompt_tokens=20,actual_max_new=64,finish_reason='STOP_SEQUENCE'))
        gate.anchor_check(event,copy.deepcopy(event))
        changed=copy.deepcopy(event);changed['answer']='6'
        with self.assertRaisesRegex(ValueError,'replay'):gate.anchor_check(event,changed)
        changed=copy.deepcopy(event);changed['generation']['actual_max_new']=63
        with self.assertRaisesRegex(ValueError,'generation'):gate.anchor_check(event,changed)

    def test_raw_summary_keeps_answer_and_clarification_proxy_separate(self):
        events=[]
        for row in self.rows:
            case=gate.views(row,self.tok)
            for style in (0,3):
                e=dict(case,style=style,answer=case['gold'],generation=dict(finish_reason='STOP_SEQUENCE'))
                e['scores']=gate.prior.method.source.score(e);events.append(e)
        out=gate.summarize(events)
        self.assertEqual(out['0/all']['cases'],32)
        self.assertEqual(out['3/ANSWER']['cases'],16)
        self.assertEqual(out['3/ASK_PROXY']['cases'],16)
        self.assertEqual(out['3/all']['literal'],32)

    def test_deadline_and_1615_boundary(self):
        deadline=datetime(2026,10,16,8,tzinfo=timezone.utc)
        self.assertTrue(gate.can_start(deadline-timedelta(hours=2),deadline,600))
        self.assertFalse(gate.can_start(deadline-timedelta(minutes=45),deadline,600))
        self.assertFalse(gate.can_start(datetime(2026,10,16,7,15,tzinfo=timezone.utc),deadline,60))
        self.assertFalse(gate.can_start(deadline,deadline,60))


if __name__=='__main__':unittest.main()
