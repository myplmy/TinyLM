"""Safe PathLike oracle reading and immutable prior-failure admission."""
from copy import deepcopy
import io
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts import diag_p014e_large_vocab_resume as d


class SafeLoaderRecovery(unittest.TestCase):
    def test_path_string_and_named_handle_keep_full_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root/'oracle'/'cpu'/'ko128.pt'
            path.parent.mkdir(parents=True)
            path.write_bytes(b'fixture')
            for file in (path, str(path), SimpleNamespace(name=str(path))):
                self.assertEqual(d.checked_load_path(file, root, weights_only=True), path.resolve())
            with path.open('rb') as file:
                self.assertEqual(d.checked_load_path(file, root, weights_only=True), path.resolve())

    def test_outside_original_checkpoint_and_unsafe_options_refused(self):
        root = ROOT/'runs/deploy/new_fixture'
        for path, safe in ((ROOT/d.prior.CP, True), (root/'fake.pt', None),
                           (root/'fake.pt', False), (root/'fake.json', True),
                           (root.parent/'escape.pt', True)):
            with self.subTest(path=path, weights_only=safe), self.assertRaises(ValueError):
                d.checked_load_path(path, root, weights_only=safe)

    def test_symlink_cannot_escape_new_payload_namespace(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); allowed = root/'allowed'; allowed.mkdir()
            outside = root/'outside.pt'; outside.write_bytes(b'x')
            link = allowed/'escape.pt'; link.symlink_to(outside)
            with self.assertRaises(ValueError):
                d.checked_load_path(link, allowed, weights_only=True)

    def test_unnamed_memory_or_integer_file_descriptor_refused(self):
        for file in (io.BytesIO(), SimpleNamespace(name=12), object()):
            with self.assertRaises(ValueError):
                d.checked_load_path(file, d.prior.folder(), weights_only=True)

    def test_actual_pathlike_torch_load_invokes_original_and_restores_on_failure(self):
        import torch
        report = {}; path = d.prior.folder()/'oracle/cpu/fp32_unchanged/ko128.pt'
        with patch.object(torch, 'load', side_effect=RuntimeError('fixture reader failure')) as reader:
            with self.assertRaisesRegex(RuntimeError, 'fixture reader failure'):
                with d.guarded_new_tensor_loads(report):
                    torch.load(path, weights_only=True, map_location='cpu')
            self.assertIs(torch.load, reader)
            reader.assert_called_once_with(path, weights_only=True, map_location='cpu')
        self.assertEqual(report['torch_load_files'], [path.relative_to(ROOT).as_posix()])

    def test_original_checkpoint_is_rejected_before_real_reader(self):
        import torch
        report = {}
        with patch.object(torch, 'load') as reader:
            with d.guarded_new_tensor_loads(report), self.assertRaises(ValueError):
                torch.load(ROOT/d.prior.CP, weights_only=True)
            self.assertFalse(reader.called)
        self.assertEqual(report['torch_load_files'], [])

    def test_only_known_closed_loader_error_is_admitted(self):
        error = dict(mode='deploy-cpu', exit_code=9, status='ERROR_NOT_COMPLETE', original_checkpoint_loads=0,
            variants=[dict(variant='fp32_unchanged', model_released=True, cleanup_errors=[],
                execution_error=dict(message='only new deployment/oracle safe loads allowed'),
                result=dict(numeric=[], records=[]))])
        d.validate_prior_error(error)
        for kind in ('exit', 'load', 'cleanup', 'numeric', 'cause'):
            other = deepcopy(error)
            if kind == 'exit': other['exit_code'] = 0
            elif kind == 'load': other['original_checkpoint_loads'] = 1
            elif kind == 'cleanup': other['variants'][0]['model_released'] = False
            elif kind == 'numeric': other['variants'][0]['result']['numeric'] = [{}]
            else: other['variants'][0]['execution_error']['message'] = 'different error'
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                d.validate_prior_error(other)


if __name__ == '__main__':
    unittest.main()
