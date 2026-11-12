from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parent))
from literal_author_editor_v2 import edit,previous


class AnchoredLiteralEditing(unittest.TestCase):
    def source(self):
        return 'KEEP BEFORE HERE duplicated popup KEEP AFTER HERE other duplicated popup'.encode()

    def request(self,raw,**span):
        return dict(expected_sha256=previous.digest(raw),spans=[dict(
            keep_before='KEEP BEFORE HERE',keep_after='KEEP AFTER HERE',replacement='',**span)])

    def test_duplicate_middle_can_be_selected_without_retyping(self):
        raw=self.source();new,hunks=edit(raw,self.request(raw))
        self.assertEqual(new,b'KEEP BEFORE HEREKEEP AFTER HERE other duplicated popup')
        self.assertEqual(len(hunks),1)

    def test_ambiguous_anchor_is_rejected(self):
        raw=self.source()+b' KEEP BEFORE HERE'
        with self.assertRaises(ValueError):edit(raw,self.request(raw))

    def test_missing_anchor_is_rejected(self):
        raw=self.source();request=self.request(raw);request['spans'][0]['keep_after']='MISSING ANCHOR'
        with self.assertRaises(ValueError):edit(raw,request)

    def test_wrong_anchor_order_is_rejected(self):
        raw=self.source();request=self.request(raw);request['spans'][0].update(
            keep_before='KEEP AFTER HERE',keep_after='KEEP BEFORE HERE')
        with self.assertRaises(ValueError):edit(raw,request)

    def test_stale_sha_is_rejected(self):
        raw=self.source();request=self.request(raw);request['expected_sha256']='0'*64
        with self.assertRaises(ValueError):edit(raw,request)

    def test_extra_command_field_is_rejected(self):
        raw=self.source();request=self.request(raw);request['command']='touch file'
        with self.assertRaises(ValueError):edit(raw,request)

    def test_second_failure_never_returns_partially_edited_data(self):
        raw=self.source();request=self.request(raw);request['spans'].append(dict(
            keep_before='MISSING BEFORE',keep_after='MISSING AFTER',replacement=''))
        with self.assertRaises(ValueError):edit(raw,request)
        self.assertEqual(raw,self.source())

    def test_literal_shell_characters_are_data(self):
        raw=self.source();request=self.request(raw);request['spans'][0]['replacement']='$(data)'
        new,_hunks=edit(raw,request)
        self.assertIn(b'$(data)',new)


if __name__=='__main__':
    unittest.main()
