"""Small stdlib/CPU fixtures only: no real CP, tokenizer, torch, GPU or HF data."""
from __future__ import annotations

from contextlib import contextmanager, nullcontext, redirect_stderr, redirect_stdout
import copy
from dataclasses import asdict, dataclass
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts import interactive_research_infer as ui


class FakeTokenizer:
    def get_vocab_size(self): return 32768
    def token_to_id(self, name): return {'<|im_start|>': 3, '<|im_end|>': 4, '<eos>': 2}.get(name)
    def to_str(self): return 'fixed synthetic tokenizer'
    def encode(self, text): return NS(ids=[20 + ord(c) for c in text])
    def decode(self, ids, skip_special_tokens=True):
        return ''.join(chr(i - 20) for i in ids)


def write_metadata(root, spec, *, closed=True):
    report = dict(schema=spec.schema, tag=spec.tag, arm=spec.arm, status='TRAIN_COMPLETE',
        cost=False, updates=spec.updates, checkpoint=spec.checkpoint, checkpoint_writes=1,
        optimizer_saved=False, checkpoint_sha256='A' * 64, final_core_sha256='B' * 64,
        quantization_route=dict(mode=spec.arm, fixture=True))
    path = root / spec.report
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(report), encoding='utf-8')
    activity = dict(schema=spec.schema, tag=spec.tag, arm=spec.arm, mode='train',
        key='train_' + spec.arm, complete=closed, returncode=0 if closed else 9,
        error_type=None if closed else 'fixture_failure', result_sha256=ui.file_sha(path))
    (root / spec.activity).write_text(json.dumps(activity), encoding='utf-8')
    return report, activity


@dataclass
class FixtureCfg:
    vocab_size: int = 32768
    max_seq_len: int = 1024
    mtp_aux: bool = False
    n_layers: int = 14
    dim: int = 768
    tie_mlp: bool = False


def fixture_manifest(root):
    for relative in ui.EXISTING_IMPORT_DIRECTORIES:
        (root / relative).mkdir(parents=True, exist_ok=True)
    for relative in ui.REQUIRED_SOURCES:
        path = root / relative; path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(('synthetic source: ' + relative).encode())
    entries = {}
    for spec in ui.MODELS:
        report, activity = write_metadata(root, spec)
        cp = root / spec.checkpoint; cp.parent.mkdir(parents=True, exist_ok=True)
        cp.write_bytes(('synthetic non-tensor CP: ' + spec.name).encode())
        report['checkpoint_sha256'] = ui.file_sha(cp)
        (root / spec.report).write_text(json.dumps(report), encoding='utf-8')
        activity['result_sha256'] = ui.file_sha(root / spec.report)
        (root / spec.activity).write_text(json.dumps(activity), encoding='utf-8')
        header = dict(cfg=asdict(FixtureCfg()), step=spec.updates,
            tokenizer_sha256=ui.TOKENIZER_SHA, tokenizer_lineage='chat32',
            quantization_route=report['quantization_route'], experiment={'fixture': spec.name})
        def desc(relative):
            path = root / relative
            return dict(path=relative, bytes=path.stat().st_size, sha256=ui.file_sha(path))
        entries[spec.name] = dict(status='COMPLETE', tag=spec.tag, arm=spec.arm, updates=spec.updates,
            checkpoint=desc(spec.checkpoint), report=desc(spec.report), activity=desc(spec.activity),
            core_sha256='B' * 64, header=header, header_sha256=ui.canonical_sha(header),
            cfg_sha256=ui.canonical_sha(header['cfg']), route_sha256=ui.canonical_sha(header['quantization_route']))
    manifest = dict(schema=ui.MANIFEST_SCHEMA, inference_only=True, source_sha256=ui.required_source_pins(root),
        tokenizer=dict(path=ui.TOKENIZER, bytes=5, sha256=ui.TOKENIZER_SHA), entries=entries,
        export_validation={'fixture_only': True})
    path = root / ui.MANIFEST; path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest), encoding='utf-8')
    return manifest


class ManifestTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='research-manifest-fixture-')
        self.root = Path(self.temp.name); self.manifest = fixture_manifest(self.root)
    def tearDown(self): self.temp.cleanup()
    def save(self):
        (self.root / ui.MANIFEST).write_text(json.dumps(self.manifest), encoding='utf-8')

    def test_all_six_and_exact_source_map_pass_without_tensor_load(self):
        self.assertEqual(ui.verify_manifest(self.root), self.manifest)
        self.assertEqual(len(ui.REQUIRED_SOURCES), len(set(ui.REQUIRED_SOURCES)))
        self.assertEqual(ui.canonical_sha({'한': 1, 'a': [2]}), ui.canonical_sha({'a': [2], '한': 1}))

    def test_missing_model_or_pending_rejected(self):
        for mode in ('missing', 'pending'):
            with self.subTest(mode=mode):
                value = copy.deepcopy(self.manifest)
                if mode == 'missing': value['entries'].pop(ui.MODELS[-1].name)
                else: value['entries'][ui.MODELS[-1].name]['status'] = 'PENDING'
                (self.root / ui.MANIFEST).write_text(json.dumps(value), encoding='utf-8')
                with self.assertRaises(ValueError): ui.verify_manifest(self.root)

    def test_missing_extra_or_changed_source_pin_rejected(self):
        for mode in ('missing', 'extra', 'changed'):
            value = copy.deepcopy(self.manifest)
            if mode == 'missing': value['source_sha256'].pop(ui.REQUIRED_SOURCES[0])
            elif mode == 'extra': value['source_sha256']['extra.py'] = 'F' * 64
            else: value['source_sha256'][ui.REQUIRED_SOURCES[0]] = 'F' * 64
            (self.root / ui.MANIFEST).write_text(json.dumps(value), encoding='utf-8')
            with self.subTest(mode=mode), self.assertRaises(ValueError): ui.verify_manifest(self.root)

    def test_header_cfg_route_and_file_bindings_rejected(self):
        for field in ('header_sha256', 'cfg_sha256', 'route_sha256', 'core_sha256'):
            value = copy.deepcopy(self.manifest); value['entries'][ui.MODELS[0].name][field] = 'F' * 64
            (self.root / ui.MANIFEST).write_text(json.dumps(value), encoding='utf-8')
            with self.subTest(field=field), self.assertRaises(ValueError): ui.verify_manifest(self.root)
        self.save()
        (self.root / ui.MODELS[-1].activity).write_text('{}', encoding='utf-8')
        with self.assertRaises(ValueError): ui.verify_manifest(self.root)

    def test_metadata_never_follows_manifest_checkpoint_path(self):
        self.manifest['entries'][ui.MODELS[0].name]['checkpoint']['path'] = '../escape.pt'; self.save()
        with self.assertRaises(ValueError): ui.verify_manifest(self.root)

    def test_source_symlink_fails_closed(self):
        source = self.root / ui.REQUIRED_SOURCES[0]
        other = self.root / 'other_source'; other.write_bytes(source.read_bytes())
        source.rename(self.root / 'preserved_source')
        source.symlink_to(other)
        with self.assertRaises(ValueError): ui.verify_manifest(self.root)


class ImportEnvironmentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='research-environment-fixture-')
        self.root = Path(self.temp.name)
        for relative in ui.EXISTING_IMPORT_DIRECTORIES:
            (self.root / relative).mkdir(parents=True, exist_ok=True)
    def tearDown(self): self.temp.cleanup()

    def test_unset_or_exact_environment_pass_without_mutation_creation_or_listing(self):
        for environ in ({}, {'TINYLM_DIR': str(self.root), 'TINYLM_HF': str(self.root / 'HF')}):
            before = dict(environ)
            original_lstat = Path.lstat; inspected = []
            def lstat(path, *args, **kwargs):
                inspected.append(str(path)); return original_lstat(path, *args, **kwargs)
            with patch.object(Path, 'mkdir', side_effect=AssertionError('must not mkdir')), \
                    patch.object(Path, 'iterdir', side_effect=AssertionError('must not list')), \
                    patch.object(Path, 'open', side_effect=AssertionError('must not read HF')), \
                    patch.object(Path, 'lstat', new=lstat):
                ui.validate_import_environment(self.root, environ)
            self.assertEqual(environ, before)
            self.assertEqual(inspected, [str(self.root / p) for p in ui.EXISTING_IMPORT_DIRECTORIES])

    def test_alias_relative_dotdot_and_empty_environment_rejected(self):
        for key, target in (('TINYLM_DIR', self.root), ('TINYLM_HF', self.root / 'HF')):
            for wrong in ('', '.', 'relative', str(target) + '/', str(target) + '/..',
                          str(target) + '/.', str(target).replace('/tmp/', '/tmp//'), '/outside'):
                environ = {key: wrong}; before = dict(environ)
                with self.subTest(key=key, wrong=wrong), self.assertRaises(ValueError):
                    ui.validate_import_environment(self.root, environ)
                self.assertEqual(environ, before)

    def test_missing_file_or_symlink_directory_rejected_without_creation(self):
        path = self.root / 'runs/logs'; preserved = self.root / 'preserved_logs'
        path.rename(preserved)
        with self.assertRaises(ValueError): ui.validate_import_environment(self.root, {})
        self.assertFalse(path.exists())
        path.write_bytes(b'not a directory')
        with self.assertRaises(ValueError): ui.validate_import_environment(self.root, {})
        path.rename(self.root / 'preserved_file'); path.symlink_to(preserved, target_is_directory=True)
        with self.assertRaises(ValueError): ui.validate_import_environment(self.root, {})

    def test_environment_rejected_before_model_or_serializer_import(self):
        original_import = __import__
        def reject_project_import(name, *args, **kwargs):
            if name.startswith(('tinylm', 'scripts', 'torch', 'tokenizers')):
                raise AssertionError('must reject before model/serializer import')
            return original_import(name, *args, **kwargs)
        with patch.dict(ui.os.environ, {'TINYLM_DIR': '/outside'}, clear=False), \
                patch('builtins.__import__', side_effect=reject_project_import):
            for call in (lambda: ui.inference_modules(self.root), lambda: ui.generation_tools(self.root),
                         lambda: ui.emit({'root': str(self.root)}, 'question')):
                with self.subTest(call=call), self.assertRaises(ValueError): call()

    def test_selected_runtime_rejects_environment_before_tokenizer_or_model(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); fixture_manifest(root)
            with patch.dict(ui.os.environ, {'TINYLM_DIR': '/outside'}, clear=False), \
                    patch.object(ui, 'local_tokenizer') as tokenizer, \
                    patch.object(ui, 'inference_modules') as modules, \
                    patch.object(ui, 'require_idle_gpu') as gpu:
                with self.assertRaises(ValueError):
                    with ui.selected_runtime(ui.MODELS[0], root=root): pass
            tokenizer.assert_not_called(); modules.assert_not_called(); gpu.assert_not_called()


class MetadataTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='research-infer-fixture-')
        self.root = Path(self.temp.name)
    def tearDown(self): self.temp.cleanup()

    def test_stable_six_numbers_and_exact_names(self):
        self.assertEqual(len(ui.MODELS), 6)
        self.assertEqual(len({m.name for m in ui.MODELS}), 6)
        for index, spec in enumerate(ui.MODELS, 1):
            self.assertIs(ui.resolve_model(str(index)), spec)
            self.assertIs(ui.resolve_model(spec.name.upper()), spec)
        for wrong in ('0', '7', 'float', 'native', 'arbitrary.pt', None):
            with self.assertRaises(ValueError): ui.resolve_model(wrong)

    def test_pending_and_success_list_do_not_open_checkpoint(self):
        self.assertEqual(ui.inspect_model(ui.MODELS[0], self.root)['status'], 'PENDING')
        report, _ = write_metadata(self.root, ui.MODELS[0])
        state = ui.inspect_model(ui.MODELS[0], self.root)
        self.assertEqual(state['status'], 'READY_METADATA_ONLY')
        self.assertEqual(state['report'], report)
        self.assertFalse((self.root / ui.MODELS[0].checkpoint).exists())
        with redirect_stdout(io.StringIO()) as stdout:
            ui.list_models(self.root)
        self.assertIn('READY_METADATA_ONLY', stdout.getvalue())
        self.assertIn('PENDING', stdout.getvalue())

    def test_open_or_failed_worker_is_not_available(self):
        write_metadata(self.root, ui.MODELS[1], closed=False)
        self.assertEqual(ui.inspect_model(ui.MODELS[1], self.root)['status'], 'INCOMPLETE')

    def test_report_hash_cannot_be_reused_after_modification(self):
        spec = ui.MODELS[1]
        report, _ = write_metadata(self.root, spec)
        report['final_core_sha256'] = 'C' * 64
        (self.root / spec.report).write_text(json.dumps(report), encoding='utf-8')
        self.assertEqual(ui.inspect_model(spec, self.root)['status'], 'INVALID_METADATA')

    def test_wrong_route_path_and_training_counts_are_rejected(self):
        for field, wrong in (('checkpoint', 'runs/ckpt/other.pt'), ('updates', 8),
                             ('cost', True), ('arm', 'wrong'), ('optimizer_saved', True)):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as directory:
                root = Path(directory); spec = ui.MODELS[0]
                report, activity = write_metadata(root, spec)
                report[field] = wrong
                (root / spec.report).write_text(json.dumps(report), encoding='utf-8')
                activity['result_sha256'] = ui.file_sha(root / spec.report)
                (root / spec.activity).write_text(json.dumps(activity), encoding='utf-8')
                self.assertEqual(ui.inspect_model(spec, root)['status'], 'INVALID_METADATA')

    def test_oversized_metadata_and_symlink_refused(self):
        spec = ui.MODELS[0]
        report = self.root / spec.report; report.parent.mkdir(parents=True)
        report.write_bytes(b' ' * (ui.METADATA_LIMIT + 1))
        self.assertEqual(ui.inspect_model(spec, self.root)['status'], 'INVALID_METADATA')
        link = self.root / 'linked'; link.symlink_to(report)
        with self.assertRaises(ValueError): ui.owned_path('linked', self.root)
        for path in ('../escape', '/absolute'):
            with self.assertRaises(ValueError): ui.owned_path(path, self.root)


class GuardTests(unittest.TestCase):
    def replies(self, values):
        iterator = iter(values)
        return lambda *a, **k: next(iterator)
    def ok(self, stdout=''):
        return NS(returncode=0, stdout=stdout, stderr='')

    def test_empty_and_own_compute_process_point_queries(self):
        for process in ('', '123, GPU-abcd-1234\n'):
            result = ui.require_idle_gpu(self.replies([self.ok('GPU-abcd-1234\n'), self.ok(process)]), pid=123)
            self.assertEqual(result['competing_compute_pids'], [])
            self.assertIn('NOT_CONTINUOUS', result['scope'])

    def test_competing_pid_blocks_model(self):
        with self.assertRaisesRegex(RuntimeError, '456'):
            ui.require_idle_gpu(self.replies([self.ok('GPU-abcd\n'), self.ok('456, GPU-abcd\n')]), pid=123)

    def test_query_errors_warnings_and_unparseable_results_fail_closed(self):
        first = self.ok('GPU-abcd\n')
        for bad in (NS(returncode=1, stdout='', stderr='error'), NS(returncode=0, stdout='', stderr='warning'),
                    self.ok('unknown'), self.ok('0, GPU-abcd'), self.ok('12, GPU-other')):
            with self.subTest(reply=bad), self.assertRaises(RuntimeError):
                ui.require_idle_gpu(self.replies([first, bad]), pid=123)
        for bad in ('', 'GPU-abcd\nGPU-dead\n', 'N/A\n'):
            with self.subTest(reply=bad), self.assertRaises(RuntimeError):
                ui.require_idle_gpu(self.replies([self.ok(bad)]), pid=123)
        for error in (FileNotFoundError(), subprocess.TimeoutExpired('fixture', 1)):
            with self.subTest(error=error), self.assertRaises(RuntimeError):
                ui.require_idle_gpu(lambda *a, **k: (_ for _ in ()).throw(error))


class RuntimeTests(unittest.TestCase):
    def fake_modules(self, root, spec, manifest, *, wrong_core=False, bad_state=False):
        events = []; model_ref = []
        entry = manifest['entries'][spec.name]
        payload = dict(copy.deepcopy(entry['header']), model={'fixture_state': object()})
        def load(stream, **kwargs):
            self.assertEqual(kwargs, dict(map_location='cpu', weights_only=True))
            self.assertTrue(stream.read().startswith(b'synthetic non-tensor CP:'))
            events.append('cpu_payload'); return payload
        torch = NS(load=load, uint8=object(), device=lambda name: nullcontext(), no_grad=nullcontext,
            cuda=NS(is_available=lambda: True, empty_cache=lambda: events.append('empty_cache')),
            backends=NS(cuda=NS(matmul=NS(allow_tf32=True)), cudnn=NS(allow_tf32=True)))
        class Model:
            def __init__(self, cfg):
                self.cfg = cfg; self.core = 'C' * 64 if wrong_core else 'B' * 64
                self.device = 'cpu'; model_ref.append(self); events.append('construct_cpu')
            def clear_quant(self): events.append('clear')
            def eval(self): events.append('eval')
            def set_anneal(self, value): events.append(('anneal', value))
            def freeze_quant(self): events.append('freeze')
            def cuda(self): events.append('cuda'); self.device = 'cuda'; return self
        @contextmanager
        def weight_route(model, arm):
            route = NS(mode=arm, metadata=entry['header']['quantization_route'], active=True)
            def assert_active():
                if not route.active: raise RuntimeError('route closed')
            route.assert_active = assert_active
            events.append(('route_enter', model.device)); model.last_route = route
            try: yield route
            finally: route.active = False; events.append(('route_exit', model.device))
        def load_routed_state(model, actual, arm):
            self.assertIs(actual, payload); events.append('strict_cpu_state')
            if bad_state: raise ValueError('fixture strict shape mismatch')
        method = NS(weight_route=weight_route, load_routed_state=load_routed_state,
                    validate_route_metadata=lambda metadata, arm: self.assertEqual(metadata['mode'], arm))
        return (torch, FixtureCfg, Model, method), model_ref, events

    def setup_runtime(self, root, spec, manifest, **options):
        from contextlib import ExitStack
        modules, models, events = self.fake_modules(root, spec, manifest, **options)
        stack = ExitStack()
        stack.enter_context(patch.dict(ui.os.environ, {key: value for key, value in ui.os.environ.items()
            if key not in ('TINYLM_DIR', 'TINYLM_HF')}, clear=True))
        stack.enter_context(patch.object(ui, 'inference_modules', return_value=modules))
        stack.enter_context(patch.object(ui, 'local_tokenizer', return_value=FakeTokenizer()))
        stack.enter_context(patch.object(ui, 'require_idle_gpu', side_effect=lambda: events.append('gpu_point') or {'scope': 'fixture'}))
        stack.enter_context(patch.object(ui, 'state_fingerprint', side_effect=lambda model: events.append(('core', model.device)) or model.core))
        stack.enter_context(redirect_stdout(io.StringIO()))
        return stack, models, events

    def test_all_six_cpu_verify_before_cuda_and_hold_matching_route(self):
        for spec in ui.MODELS:
            with self.subTest(model=spec.name), tempfile.TemporaryDirectory() as directory:
                root = Path(directory); manifest = fixture_manifest(root)
                stack, models, events = self.setup_runtime(root, spec, manifest)
                with stack, ui.selected_runtime(spec, root=root) as active:
                    self.assertTrue(active['route'].active)
                    self.assertEqual(active['route'].mode, spec.arm)
                    self.assertEqual(active['core_sha256'], 'B' * 64)
                    self.assertIs(active['model'], models[0])
                    self.assertFalse(active['torch'].backends.cuda.matmul.allow_tf32)
                self.assertEqual(active, {})
                self.assertLess(events.index('strict_cpu_state'), events.index('cuda'))
                self.assertLess(events.index(('core', 'cpu')), events.index('gpu_point'))
                self.assertFalse(models[0].last_route.active); self.assertIn('empty_cache', events)

    def test_absent_manifest_never_imports_model_or_queries_gpu(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(ui, 'require_idle_gpu') as gpu:
            with patch.object(ui, 'inference_modules') as modules, self.assertRaisesRegex(ValueError, 'MANUAL_MANIFEST_NOT_READY'):
                with ui.selected_runtime(ui.MODELS[0], root=Path(directory)): pass
            modules.assert_not_called()
        gpu.assert_not_called()

    def test_strict_state_or_cpu_core_failure_never_admits_cuda(self):
        for options in ({'wrong_core': True}, {'bad_state': True}):
            with self.subTest(options=options), tempfile.TemporaryDirectory() as directory:
                root = Path(directory); manifest = fixture_manifest(root); spec = ui.MODELS[0]
                stack, models, events = self.setup_runtime(root, spec, manifest, **options)
                with stack, self.assertRaises(ValueError):
                    with ui.selected_runtime(spec, root=root): pass
                self.assertNotIn('cuda', events); self.assertNotIn('gpu_point', events)
                self.assertFalse(models[0].last_route.active)

    def test_prompt_exception_and_body_mutation_cleanup_route_and_gpu(self):
        for mutate in (False, True):
            with self.subTest(mutate=mutate), tempfile.TemporaryDirectory() as directory:
                root = Path(directory); manifest = fixture_manifest(root); spec = ui.MODELS[-1]
                stack, models, events = self.setup_runtime(root, spec, manifest)
                with stack, self.assertRaises(RuntimeError):
                    with ui.selected_runtime(spec, root=root) as active:
                        if mutate: models[0].core = 'C' * 64
                        else: raise RuntimeError('fixture prompt exception')
                self.assertEqual(active, {}); self.assertFalse(models[0].last_route.active)
                self.assertIn('empty_cache', events)

    def test_changed_cp_sha_rejects_before_tensor_load(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); manifest = fixture_manifest(root); spec = ui.MODELS[0]
            entry = manifest['entries'][spec.name]
            (root / spec.checkpoint).write_bytes(b'x' * entry['checkpoint']['bytes'])
            torch = NS(load=lambda *a, **k: self.fail('must reject before tensor load'))
            with self.assertRaisesRegex(ValueError, 'CP SHA'):
                ui.read_selected_payload(torch, spec, entry, root)

    def test_actual_cp_header_cannot_disagree_with_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); manifest = fixture_manifest(root); spec = ui.MODELS[0]
            entry = manifest['entries'][spec.name]
            payload = dict(copy.deepcopy(entry['header']), model={}); payload['step'] = 8
            with self.assertRaisesRegex(ValueError, 'header'):
                ui.read_selected_payload(NS(load=lambda *a, **k: payload), spec, entry, root)


class FingerprintTests(unittest.TestCase):
    def test_exact_legacy_function_definition_with_fake_tensor_views(self):
        import ast
        source = (ROOT / 'scripts/diag_p101a_sft_mtp.py').read_text(encoding='utf-8')
        node = next(node for node in ast.parse(source).body if isinstance(node, ast.FunctionDef) and node.name == 'state_fingerprint')
        namespace = dict(hashlib=hashlib)
        exec(compile(ast.Module(body=[node], type_ignores=[]), '<legacy fingerprint fixture>', 'exec'), namespace)
        class Tensor:
            shape = (2,); dtype = 'torch.float32'
            def __init__(self, raw): self.raw = raw
            def detach(self): return self
            def cpu(self): return self
            def contiguous(self): return self
            def view(self, *args): return self
            def numpy(self): return NS(tobytes=lambda: self.raw)
        model = NS(state_dict=lambda: {'z': Tensor(b'\x00\x01'), 'a': Tensor(b'\x02\x03'), 'mtp_up2': Tensor(b'ignored')})
        with patch.dict(sys.modules, {'torch': NS(uint8=object())}):
            self.assertEqual(ui.state_fingerprint(model), namespace['state_fingerprint'](model))

    def test_precision_class_extraction_does_not_import_experiment_runtime(self):
        before = set(sys.modules)
        capture, forward = ui.precision_types()
        tok = FakeTokenizer(); wrapped = capture(tok)
        wrapped.decode([ord('2') + 20])
        self.assertEqual(wrapped.decoded_ids, [ord('2') + 20])
        self.assertEqual(forward(object(), 'fp32_math').precision, 'fp32_math')
        imported = set(sys.modules) - before
        self.assertFalse(any('diag_p101a_sft_mtp' in name or 'diag_p106b_native' in name for name in imported))


class GenerationTests(unittest.TestCase):
    def setUp(self): self.tok = FakeTokenizer()

    def test_valid_eos_eot_and_max_new_keep_exact_body(self):
        for suffix, reason, stop in (([4], 'STOP_SEQUENCE', [4]), ([2], 'EOS', None), ([], 'MAX_NEW', None)):
            prefix = [80, 81]; body = [ord('2') + 20]
            ids = prefix + body + suffix
            meta = dict(generated_tokens=len(body + suffix), finish_reason=reason, matched_stop_sequence=stop)
            answer, result = ui.answer_from_tokens(self.tok, prefix, ids, meta, len(body + suffix))
            self.assertEqual(answer, '2'); self.assertEqual(result['terminal_ids'], suffix)
            self.assertEqual(result['generated_ids'], body + suffix)

    def test_forged_prefix_count_and_termination_receipts_rejected(self):
        valid = dict(generated_tokens=2, finish_reason='STOP_SEQUENCE', matched_stop_sequence=[4])
        for ids, changes in (([0, 70, 4], {}), ([80, 70, 4], {'generated_tokens': 1}),
                             ([80, 70, 2], {}), ([80, 4, 4], {}),
                             ([80, 70, 4], {'finish_reason': 'EOS'}),
                             ([80, 70, 4], {'finish_reason': 'EOS_UNAVAILABLE'}),
                             ([80, 70, 4], {'matched_stop_sequence': [2]}),
                             ([80, 70], {'finish_reason': 'MAX_NEW', 'generated_tokens': 1, 'matched_stop_sequence': None})):
            with self.subTest(ids=ids, changes=changes), self.assertRaises(ValueError):
                ui.answer_from_tokens(self.tok, [80], ids, dict(valid, **changes), 2)

    def test_prompt_history_is_complete_alternation_and_not_modified(self):
        history = [dict(role='user', content='old user'), dict(role='assistant', content='actual old answer')]
        before = copy.deepcopy(history)
        messages = ui.prompt_messages('new user', history)
        self.assertEqual(messages[-1]['content'], 'new user'); self.assertEqual(history, before)
        for bad in (history[:1], [dict(role='assistant', content='gold')], [{'role': 'user', 'content': [], 'meta': {}}]):
            with self.assertRaises(ValueError): ui.prompt_messages('new', bad)
        with self.assertRaises(ValueError): ui.prompt_messages('  ')

    def test_emit_matches_greedy_fp32_kv_and_refuses_context_without_sampling(self):
        # Import only the tracked canonical serializer; all generation/model tools are fake.
        ui.validate_import_environment()
        from tinylm.chat.serialize import serialize
        history = [dict(role='user', content='앞 질문'), dict(role='assistant', content='내 실제 답')]
        captured = {}
        class Capture:
            def __init__(self, tok): self.decoded_ids = None
        def sample(model, cfg, capture, prompt, **kwargs):
            captured.update(kwargs, model=model, prompt=prompt)
            capture.decoded_ids = self.tok.encode(prompt).ids + [ord('2') + 20, 4]
            return 'ignored decoded text', dict(generated_tokens=2, finish_reason='STOP_SEQUENCE', matched_stop_sequence=[4])
        route = NS(assert_active=lambda: None)
        active = dict(tokenizer=self.tok, cfg=NS(max_seq_len=1024), model=object(), route=route, torch=NS(no_grad=nullcontext))
        tools = (sample, Capture, lambda model, precision: (model, precision))
        with patch.object(ui, 'validate_import_environment'), patch.object(ui, 'generation_tools', return_value=tools):
            answer, metadata = ui.emit(active, '1+1은?', history=history)
        self.assertEqual(answer, '2'); self.assertEqual(captured['model'][1], 'fp32_math')
        self.assertEqual(captured['prompt'], serialize({'messages': history + [dict(role='user', content='1+1은?')]}, 'chatml', add_generation_prompt=True))
        self.assertEqual((captured['temperature'], captured['top_k'], captured['mtp_tokens']), (0., 1, 1))
        self.assertTrue(captured['use_cache']); self.assertEqual(captured['stop_token_sequences'], [[4]])
        self.assertEqual(captured['max_new'], 128); self.assertTrue(metadata['actual_history'])
        active['cfg'].max_seq_len = 1
        with patch.object(ui, 'validate_import_environment'), patch.object(ui, 'generation_tools') as runtime_tools, self.assertRaisesRegex(ValueError, '자동 절단'):
            ui.emit(active, '긴 질문')
        runtime_tools.assert_not_called()

    def test_only_actual_successful_answers_enter_history_and_reset(self):
        active = {}; args = NS(prompt=None, max_new=128, history=True)
        inputs = iter(('first', 'too long', 'second', ':reset', 'third', ':quit'))
        histories = []
        def fake_emit(active, question, max_new, history):
            histories.append((question, copy.deepcopy(history)))
            if question == 'too long': raise ValueError('fixture context refusal')
            return 'actual:' + question, {'finish_reason': 'EOS'}
        with patch('builtins.input', side_effect=lambda _: next(inputs)), patch.object(ui, 'emit', side_effect=fake_emit), redirect_stdout(io.StringIO()):
            ui.run_prompts(active, args)
        self.assertEqual(histories[1][1], [dict(role='user', content='first'), dict(role='assistant', content='actual:first')])
        self.assertEqual(histories[2][1], histories[1][1]); self.assertEqual(histories[3][1], [])


class CliTests(unittest.TestCase):
    def test_help_and_nontty_preconditions_never_load_model(self):
        with patch.object(ui, 'selected_runtime') as loader, patch.object(ui.sys.stdin, 'isatty', return_value=False), redirect_stderr(io.StringIO()), redirect_stdout(io.StringIO()):
            with self.assertRaises(SystemExit) as help_exit: ui.main(['--help'])
            self.assertEqual(help_exit.exception.code, 0)
            for argv in ([], ['--model', '1'], ['--prompt', 'question'], ['--model', '1', '--prompt', ' '],
                         ['--max-new', '0'], ['--model', '1', '--prompt', 'q', '--history']):
                with self.subTest(argv=argv), self.assertRaises(SystemExit): ui.main(argv)
            loader.assert_not_called()

    def test_list_does_not_query_or_import_runtime(self):
        with patch.object(ui, 'list_models') as listing, patch.object(ui, 'selected_runtime') as loader, patch.object(ui, 'require_idle_gpu') as gpu:
            self.assertEqual(ui.main(['--list']), 0)
        listing.assert_called_once_with(); loader.assert_not_called(); gpu.assert_not_called()

    def test_selected_noninteractive_call_loads_only_exact_choice(self):
        @contextmanager
        def selected(spec):
            self.assertIs(spec, ui.MODELS[-1]); yield {'fixture': True}
        with patch.object(ui.sys.stdin, 'isatty', return_value=False), patch.object(ui, 'selected_runtime', side_effect=selected) as loader, patch.object(ui, 'run_prompts') as prompts, redirect_stdout(io.StringIO()):
            self.assertEqual(ui.main(['--model', 'new595-broad-f', '--prompt', '1+1은?']), 0)
        loader.assert_called_once(); self.assertEqual(prompts.call_args[0][1].prompt, '1+1은?')


if __name__ == '__main__':
    unittest.main()
