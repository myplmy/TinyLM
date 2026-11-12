"""Keep the inherited path/role/ID denials after normalizing a local MD note."""
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(Path(__file__).resolve().parent))
from scripts.test_p106b_hold_resolution_author_output_bindings_v1 import BindingTests
from scripts.p106b_hold_resolution_author_output_bindings_v1 import declared_txt_basename
from exact_review_output_cell_alias_v1 import normalize_output,wrap_review_entries


class CellAliasTests(BindingTests):
    def bind(self,cell,status='EDIT_TEXT'):
        return declared_txt_basename(normalize_output(cell,'expanded_train:123'),
                                     'expanded_train:123',self.directory,self.paths,status)

    def test_relative_body_and_local_same_id_sidecar(self):
        self.assertEqual(self.bind('`revision_123.txt`; `hold_123_v1.md`'),'revision_123.txt')

    def test_absolute_body_and_descriptive_local_note(self):
        cell='`'+str(self.directory/'revision_123.txt')+'`; 좁은 HOLD는 `123_hold_v1.md`'
        self.assertEqual(self.bind(cell),'revision_123.txt')

    def test_foreign_output_with_valid_note_still_rejected(self):
        with self.assertRaises(ValueError):
            self.bind('/tmp/foreign/revision_123.txt; hold_123.md')

    def test_two_body_paths_are_not_collapsed(self):
        with self.assertRaises(ValueError):
            self.bind('revision_123.txt; revision_123_other.txt; hold_123.md')

    def test_other_id_note_is_not_used_to_disambiguate(self):
        cell='revision_123.txt; hold_124.md'
        self.assertEqual(normalize_output(cell,'expanded_train:123'),cell)
        with self.assertRaises(ValueError):
            self.bind(cell)

    def test_exact_partial_status_only_is_normalized(self):
        payload='synthetic MD bytes'
        entry=dict(number=3,header=['ID','판정','판독 범위','출력','근거'],
                   cells=['expanded_train:123','REVISE_TEXT_PARTIAL','full EOF',
                          'revision_123.txt; hold_123.md','actual partial edit'])
        wrapped=wrap_review_entries(lambda data,allow_sections=False:[entry])
        result=wrapped(payload)[0]
        self.assertEqual(result['cells'][1],'REVISE_TEXT')
        self.assertEqual(result['cells'][3],'revision_123.txt')
        self.assertEqual(entry['cells'][1],'REVISE_TEXT_PARTIAL')


if __name__=='__main__':
    unittest.main(verbosity=2)
