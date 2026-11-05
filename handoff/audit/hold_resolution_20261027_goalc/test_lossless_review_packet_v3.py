"""Use the existing independent decoder and test the bounded long-doc branch."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parent))
import lossless_review_packet_v3 as core
import scoped_lossless_review_entry_v3 as entry
import test_lossless_review_packet_v2 as legacy


class LosslessV3Tests(legacy.LosslessV2Tests):
    def setUp(self):
        self.core_patch = patch.object(legacy,'core',core)
        self.core_patch.start()
        self.addCleanup(self.core_patch.stop)
        self.entry_patch = patch.object(legacy,'entry',entry)
        self.entry_patch.start()
        self.addCleanup(self.entry_patch.stop)

    def compare(self,source,candidate):
        old,new = source.encode('utf-8'),candidate.encode('utf-8')
        values = self.assert_transport(old,new)
        baseline = core.previous.prepare_views(old,new)
        self.assertLessEqual(len(values['pair'].encode()),len(baseline['pair'].encode()))
        return values,baseline

    def test_long_unique_lines_changes_at_both_ends(self):
        source=''.join(f'paragraph_{n:04d} unique content and retained context.'+chr(10) for n in range(1800))
        candidate=source.replace('paragraph_0000','section_0000',1).replace('paragraph_1799','section_1799',1)
        values,baseline=self.compare(source,candidate)
        self.assertLess(len(values['pair'].encode()),len(baseline['pair'].encode()))
        self.assertEqual(values['candidate_representation'],'EXACT_PATCH_WITH_OLD_AND_NEW')

    def test_long_repetitive_no_unique_anchor_falls_back(self):
        source='start'+chr(10)+('repeat identical'+chr(10))*4000+'end'
        self.compare(source,source.replace('start','other',1)[:-3]+'END')

    def test_long_reordered_unique_lines_reconstructs(self):
        lines=[f'line {n:05d} context with a distinct anchor'+chr(10) for n in range(1500)]
        source=''.join(lines);candidate=''.join(lines[100:200]+lines[:100]+lines[200:])
        self.compare(source,candidate)

    def test_long_crlf_unicode_and_fake_marker(self):
        source=''.join(f'{n:04d} 한글🙂 FULL_ORIGINAL_END 각 줄'+chr(13)+chr(10) for n in range(2200))
        self.compare(source,source.replace('0000 한글','0000 새한글',1).replace('2199 한글','2199 새한글',1))

    def test_single_long_line_falls_back(self):
        source='A'+'x'*50000+'Z'
        self.compare(source,'B'+source[1:-1]+'Y')

    def test_many_tiny_changes_never_increase_transport(self):
        source=''.join(f'unique {n:05d} content preserved line'+chr(10) for n in range(2200))
        candidate=source.replace('content','CONTent')
        self.compare(source,candidate)

    def test_character_work_bound_skips_anchor_path(self):
        source=('retained source'+chr(10))*4000
        with patch.object(core,'MAX_OPTIMIZED_CHARACTERS',80000),patch.object(core,'anchored_changes') as anchors:
            values=core.prepare_views(source.encode(),('new'+source).encode())
            self.assertEqual(legacy.decode_pair(values['pair'],values),(source.encode(),('new'+source).encode()))
            anchors.assert_not_called()


if __name__=='__main__':
    unittest.main(verbosity=2)
