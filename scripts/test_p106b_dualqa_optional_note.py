#!/usr/bin/env python3
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import unittest
from scripts import p106b_dualqa_optional_note as m
from scripts import diag_p106b_dualqa_optional_note as d
from scripts import test_p106b_dualqa_teacher as fixture


class Optional(unittest.TestCase):
    def test_real_style_missing_optional_note(self):
        final='Q1: At what age did Miura reach the summit?\nA1: He was80 years old.'
        with self.assertRaises(ValueError):m.ORIGINAL_PARSE(final,1)
        out=m.parse_fields(final,1);self.assertEqual(out['note'],'');self.assertTrue(out['empty_note_filled_by_code'])

    def test_korean_two_pairs_no_empty_metadata_required(self):
        out=m.parse_fields(fixture.FINAL.removesuffix('NOTE:'),2)
        self.assertEqual(len(out['pairs']),2);self.assertEqual(out['note'],'')

    def test_note_when_present_preserved(self):
        out=m.parse_fields(fixture.FINAL+'uncertainty stays in source',2)
        self.assertEqual(out['note'],'uncertainty stays in source');self.assertFalse(out['empty_note_filled_by_code'])

    def test_never_strip_reasoning_preface(self):
        with self.assertRaises(ValueError):m.parse_fields('Draft thought before fields\n'+fixture.FINAL,2)

    def test_required_payload_not_relaxed(self):
        for s in (fixture.FINAL.replace('A2:','Q1:'),fixture.FINAL.replace('화가','사서')):
            with self.assertRaises(ValueError):m.parse_fields(s,2)

    def test_decline_stays_typed(self):
        self.assertEqual(m.parse_fields('STATUS: INSUFFICIENT_SOURCE',2)['status'],'PRODUCER_DECLINED')
        self.assertEqual(m.parse_fields('STATUS: INSUFFICIENT_SOURCE\nNOTE: only one stated fact',2)['status'],'PRODUCER_DECLINED')

    def test_user_reference_bytes_unchanged(self):
        job=fixture.job();messages=m.messages(job,2)
        self.assertEqual(messages[1],m.ORIGINAL_MESSAGES(job,2)[1]);self.assertIn('OPTIONAL',messages[0]['content'])

    def test_seed_mapping_same_old_source_attempt(self):
        job=fixture.job()
        for attempt in range(1,4):
            payload=d.remapped_payload(job,2,d.seed(d.TAG,job['root'],attempt))
            self.assertEqual(payload['seed'],d.seed(d.SOURCE_TAG,job['root'],attempt))


if __name__=='__main__':unittest.main()
