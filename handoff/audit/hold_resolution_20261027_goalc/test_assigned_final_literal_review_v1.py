"""Check exact reconstruction, bounded long paragraphs and pre-I/O exclusions."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
import difflib
import random
import sys
import unittest

AUDIT=Path(__file__).resolve().parent
sys.path.insert(0,str(AUDIT))
import assigned_final_literal_review_v1 as current
import lossless_review_packet_v3 as core


class FinalLiteralReviewTests(unittest.TestCase):
    def check(self,source,final):
        changes=current.exact_changes(source,final,core)
        self.assertEqual(core.base.reconstruct(source,changes).encode('utf-8'),final.encode('utf-8'))
        return changes

    def test_identity_empty_and_one_sided_changes(self):
        for a,b in [('',''),('abc','abc'),('','한글ᄀ'),('abc',''),('a','b')]:self.check(a,b)

    def test_every_changed_unicode_byte_and_final_newline_is_preserved(self):
        for a,b in [('가ᄀퟅ U+302E() 끝'+chr(10),'가ᄀퟅ U+302E 끝'),
                    ('\r\n한글\r\n','\n한글\n'),('첫😀문장 끝','첫😀새 문장 끝')]:self.check(a,b)

    def test_many_distant_edits_in_one_long_paragraph_are_small(self):
        source=' '.join('word'+str(n) for n in range(5000))
        final=source
        for n in [50,500,2000,4500]:final=final.replace('word'+str(n)+' ','fixed'+str(n)+' ',1)
        changes=self.check(source,final)
        self.assertLessEqual(len(changes),8)
        view=current.changes_view(source,changes)
        old=''.join(difflib.unified_diff([source],[final],n=1))
        self.assertLess(len(view.encode('utf-8')),len(old.encode('utf-8'))//10)

    def test_repeated_or_unanchored_material_is_never_lost(self):
        for a,b in [('ab '*10000,'ab '*4500+'X '+'ab '*5500),
                    ('x'*9000+'a'+'y'*9000,'x'*9000+'b'+'y'*9000)]:self.check(a,b)

    def test_random_edits_reconstruct_every_case(self):
        rng=random.Random(12122)
        for _ in range(100):
            source=''.join(rng.choices('ab 가나漢😀'+chr(10),k=rng.randrange(1,300)))
            a,b=sorted(rng.choices(range(len(source)+1),k=2))
            final=source[:a]+''.join(rng.choices('XYZ퀀텀 ',k=rng.randrange(12)))+source[b:]
            self.check(source,final)

    def test_final_target_cannot_leave_own_role_cohort_or_id(self):
        context=dict(source_id='expanded_train:12',role='legacy_review',cohort='remaining_field_title_page_016_counter_v1')
        for name in ['../expanded_train_12_v1.txt','expanded_train_13_v1.txt','/tmp/x.txt','expanded_train_12_v1.md']:
            with self.assertRaises(ValueError):current.target(AUDIT.parents[2],context,name,'A'*64,core)
        with self.assertRaises(ValueError):current.target(AUDIT.parents[2],context,'expanded_train_12_v1.txt','a'*64,core)

    def test_restricted_original_candidate_and_final_are_denied_before_io(self):
        contract=dict(restricted_ids=[],restricted_hashes=['F'*64],trusted_metadata={})
        base=dict(source_id='expanded_train:12',role='legacy_review',cohort='remaining_field_title_page_016_counter_v1',
            original=dict(path='unused',sha256='A'*64),candidate=dict(path='unused',sha256='B'*64))
        for where in ['original','candidate','final']:
            context={**base,'original':dict(base['original']),'candidate':dict(base['candidate'])}
            if where!='final':context[where]['sha256']='F'*64
            fake=SimpleNamespace(resolve_assignment=lambda *args:context,base=core.base,require=core.require)
            read=Mock(side_effect=AssertionError('payload must not open'))
            with self.assertRaises(ValueError):current.load_final(AUDIT.parents[2],'legacy_review',context['cohort'],
                context['source_id'],'expanded_train_12_v1.txt','F'*64 if where=='final' else 'C'*64,
                fake,{},None,contract,read)
            read.assert_not_called()

    def test_metadata_assignment_failure_never_opens_payload(self):
        fake=SimpleNamespace(resolve_assignment=Mock(side_effect=ValueError('unassigned role or ID')))
        read=Mock()
        with self.assertRaises(ValueError):current.load_final(AUDIT.parents[2],'bad','bad','expanded_train:12',
            'expanded_train_12_v1.txt','A'*64,fake,{},None,{},read)
        read.assert_not_called()


if __name__=='__main__':unittest.main()
