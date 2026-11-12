"""Exercise literal edit data and fail-before-write invariants only on fixtures."""
from pathlib import Path
from contextlib import redirect_stdout
import io
import json
import sys
import tempfile
import unittest
from unittest.mock import patch

AUDIT=Path(__file__).resolve().parent
sys.path[:0]=[str(AUDIT),str(AUDIT.parents[2])]
from literal_author_editor_v1 import cli,digest,edit


class LiteralEditor(unittest.TestCase):
    def request(self,raw,edits):
        return dict(expected_sha256=digest(raw),edits=edits)

    def test_exact_unicode_data(self):
        raw='고유명과 1914년. 비본문 팝업. 조건은 그대로.'.encode()
        after,_=edit(raw,self.request(raw,[dict(old=' 비본문 팝업.',new='')]))
        self.assertEqual(after.decode(),'고유명과 1914년. 조건은 그대로.')

    def test_stale_sha_rejects(self):
        with self.assertRaises(ValueError):edit(b'abc',dict(expected_sha256='0'*64,edits=[dict(old='b',new='')]))

    def test_multiple_matches_reject(self):
        raw=b'abc abc'
        with self.assertRaises(ValueError):edit(raw,self.request(raw,[dict(old='abc',new='a')]))

    def test_no_partial_batch_result_on_later_failure(self):
        raw=b'abcdef'
        with self.assertRaises(ValueError):edit(raw,self.request(raw,[dict(old='bc',new='X'),dict(old='missing',new='Y')]))
        self.assertEqual(raw,b'abcdef')

    def test_shell_tokens_are_literal_text(self):
        raw=b'prefix suffix'
        after,_=edit(raw,self.request(raw,[dict(old='suffix',new='$(no_command) `no_command`')]))
        self.assertEqual(after,b'prefix $(no_command) `no_command`')

    def test_empty_final_rejects(self):
        raw=b'abc'
        with self.assertRaises(ValueError):edit(raw,self.request(raw,[dict(old='abc',new='')]))

    def test_non_edit_instruction_field_rejects(self):
        raw=b'abc'
        with self.assertRaises(ValueError):edit(raw,self.request(raw,[dict(old='b',new='c',command='none')]))

    def test_multiple_unique_changes_in_one_final(self):
        raw=b'abcd'
        after,hunks=edit(raw,self.request(raw,[dict(old='a',new='A'),dict(old='d',new='D')]))
        self.assertEqual(after,b'AbcD')
        self.assertEqual(len(hunks),2)

    def test_fixture_cli_updates_only_final_and_leaves_no_temporary_copy(self):
        with tempfile.TemporaryDirectory(prefix='literal-editor-fixture-') as directory:
            root=Path(directory)
            raw='본래 이름과 날짜 1914. 빈 부분.'.encode()
            source=root/'source.txt'
            source.write_bytes(raw)
            (root/'writer').mkdir()
            target=root/'writer/final.txt'
            target.write_bytes(raw)
            scope=dict(id='expanded_train:335240',role='legacy_review',unfinished_final_only=True,
                original=dict(path='source.txt',sha256=digest(raw)),candidate=dict(path='candidate.txt',sha256=digest(raw)),
                target='writer/final.txt',author_directory='writer')
            scope_path=root/'scope.json'
            scope_path.write_text(json.dumps(scope),encoding='utf-8')
            request=self.request(raw,[dict(old=' 빈 부분.',new='')])
            incoming=io.TextIOWrapper(io.BytesIO(json.dumps(request).encode()))
            output=io.StringIO()
            with patch.object(sys,'argv',['editor','335240','--apply']),patch.object(sys,'stdin',incoming),redirect_stdout(output):
                cli(root,'legacy_review',dict(path='scope.json',sha256=digest(scope_path.read_bytes())))
            self.assertEqual(source.read_bytes(),raw)
            self.assertEqual(target.read_bytes(),'본래 이름과 날짜 1914.'.encode())
            self.assertEqual(list((root/'writer').glob('.literal-edit-*')),[])
            self.assertEqual(json.loads(output.getvalue())['temporary_files_remaining'],0)


if __name__=='__main__':
    unittest.main()
