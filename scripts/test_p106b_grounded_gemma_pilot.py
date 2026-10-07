#!/usr/bin/env python3
"""CPU grounded job/provenance controls; no inventory/teacher/model files."""
import copy
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.diag_p106b_grounded_gemma_pilot import select_jobs
from scripts.test_p106b_capability_prepare import row


def samples():
    result=[]
    for language in ('ko','en'):
        for i in range(10):
            r=row(i,language=language)
            r['messages'][0]['content'][0]['text']=language+' question '+str(i)
            r['meta'].update(source_repo='public/repo',source_revision='r1',source_sha256='A'*64,
                             source_id=language+str(i),source_family='NQ-Open')
            result.append(dict(original=r,current_builder_eligible=True,sampling_rank=language+str(i).zfill(2)))
    return result


class GroundedTests(unittest.TestCase):
    def test_balanced_unique_source_groups_and_original_family(self):
        source=samples();before=copy.deepcopy(source);jobs=select_jobs(source)
        self.assertEqual(len(jobs),16);self.assertEqual(len({r['source_group_id'] for r in jobs}),16)
        for language in ('ko','en'):
            subset=[r for r in jobs if r['language']==language]
            self.assertEqual(len(subset),8)
            self.assertEqual([r['task'] for r in subset],['qa']*4+['json']*2+['multiturn']*2)
        self.assertTrue(all(r['source_family']=='NQ-Open' for r in jobs))
        self.assertEqual(source,before)

    def test_shortage_never_filled_by_repeating_sources(self):
        source=samples()[:4]*4
        with self.assertRaises(FileNotFoundError):select_jobs(source)

    def test_same_question_different_ids_do_not_create_new_groups(self):
        source=samples()
        for r in source:r['original']['messages'][0]['content'][0]['text']='same question'
        with self.assertRaises(FileNotFoundError):select_jobs(source)


if __name__=='__main__':unittest.main()
