"""합성 배열·임시 tiny CP만 쓰는 CPU 회귀. 실물 자산과 GPU는 사용하지 않는다."""
from __future__ import annotations

from contextlib import contextmanager, ExitStack, redirect_stdout, redirect_stderr
import copy
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
import io
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from scripts import diag_p070b_prefill_shape_cause as d
_METADATA = None


def metadata():
    global _METADATA
    if _METADATA is None: _METADATA = (d.info(), d.old.info())
    return copy.deepcopy(_METADATA)


def put(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8') as stream: json.dump(value, stream, ensure_ascii=False)


@contextmanager
def fixture():
    """새 모듈의 입력 경계만 fixture로 대체하며 frozen legacy 전역은 바꾸지 않는다."""
    import numpy as np
    import torch
    from tinylm.config import TMTConfig
    from tinylm.model import TiedMLPTransformer
    from scripts.p070b_cla_routes import FixedRouteTransformer
    recipe, legacy_recipe = metadata()
    with tempfile.TemporaryDirectory(prefix='p070b-shape-test-') as directory, ExitStack() as stack:
        real_root = d.ROOT; root = Path(directory)
        paths = {name: root / getattr(d, name).relative_to(real_root) for name in
            ('CACHE', 'RAW', 'EVIDENCE', 'PARENT', 'TOKENIZER', 'OLD_FAILURE', 'OLD_RAW', 'F4')}
        stack.enter_context(patch.multiple(d, ROOT=root, **paths))
        end = datetime.now(timezone.utc) + timedelta(days=1)
        stack.enter_context(patch.object(d, 'END', end))
        cfg = TMTConfig(vocab_size=67, dim=32, ffn_dim=64, n_q_heads=4, n_kv_heads=2,
            emb_rank=8, n_prelude=2, n_middle=10, n_coda=2, mlp_group=2, tie_mlp=False,
            cla_group=2, cla_edges=True, micro_group=0, grad_checkpoint=True, max_seq_len=1024)
        torch.manual_seed(1337); parent = TiedMLPTransformer(cfg); core = d.old.fingerprint(parent)
        payload = dict(model=parent.state_dict(), cfg=asdict(cfg))
        d.PARENT.parent.mkdir(parents=True, exist_ok=True)
        with d.PARENT.open('xb') as stream: torch.save(payload, stream)
        d.TOKENIZER.parent.mkdir(parents=True, exist_ok=True); d.TOKENIZER.write_bytes(b'tiny fixture tokenizer metadata')
        parent_sha, tokenizer_sha = d.digest(d.PARENT), d.digest(d.TOKENIZER)
        stack.enter_context(patch.multiple(d, PARENT_SHA=parent_sha, PARENT_CORE=core, TOKENIZER_SHA=tokenizer_sha))
        for shape in (recipe['shape'], legacy_recipe['shape']):
            for key in shape: shape[key] = getattr(cfg, key)
        legacy_recipe.update(parent_sha256=parent_sha, parent_core_sha256=core, tokenizer_sha256=tokenizer_sha)
        recipe.update(parent_sha256=parent_sha, parent_core_sha256=core, tokenizer_sha256=tokenizer_sha,
            legacy_recipe_sha256=d.sha(legacy_recipe), authority_end_utc=end.isoformat())
        cfg2 = TMTConfig(**dict(asdict(cfg), train_repeat=2.))
        model = FixedRouteTransformer(cfg2, 'reverse', 2, 0)
        d.old.strict_load(model, payload, core)
        input_ids = np.arange(35, 44, dtype=np.int64).reshape(1, 9)
        full, cached, _ = d.old.cache_case(model, torch.tensor(input_ids), fixed=True)
        cached = cached.copy(); cached[0, 0, 0] += 1e-3
        # 합성 음성을 원 실험의 결과와 혼동하지 않는다.
        d.OLD_RAW.parent.mkdir(parents=True, exist_ok=True)
        with d.OLD_RAW.open('xb') as stream: np.savez(stream, ids=input_ids, full=full, cached=cached)
        old_raw_sha = d.digest(d.OLD_RAW)
        failure = d.seal(dict(recipe=legacy_recipe, status='CPU_TOLERANCE_FAILED', complete=False,
            route='r2_reverse', language='ko', comparison_kind='FULL_VS_CACHED', input_ids=9,
            parent_sha256=parent_sha, parent_core_sha256=core, route_sha256=model.route_sha256,
            raw=dict(sha256=old_raw_sha, ids_sha256=d.old.array_sha(input_ids), comparison=d.measured(full, cached))))
        put(d.OLD_FAILURE, failure); old_failure_sha = d.digest(d.OLD_FAILURE)
        stack.enter_context(patch.multiple(d, OLD_FAILURE_SHA=old_failure_sha, OLD_RAW_SHA=old_raw_sha))
        recipe.update(old_failure_sha256=old_failure_sha, old_raw_sha256=old_raw_sha)
        stack.enter_context(patch.object(d, 'info', side_effect=lambda: copy.deepcopy(recipe)))
        stack.enter_context(patch.object(d, 'parent_preflight', return_value=dict(
            recipe_sha256=d.sha(legacy_recipe), real_models_created=0, checkpoint_tensors_loaded=0, writes=0)))
        def load_tiny_bundle():
            loaded = torch.load(d.PARENT, map_location='cpu', weights_only=True)
            return torch, loaded, TMTConfig(**loaded['cfg']), object()
        stack.enter_context(patch.object(d, 'load_bundle', side_effect=load_tiny_bundle))
        yield dict(recipe=recipe, legacy_recipe=legacy_recipe, ids=input_ids, full=full, cached=cached)


def complete():
    d.worker(30)
    return d.read_json(d.EVIDENCE / 'report.json')


def term_probe():
    import torch
    torch.set_num_threads(1)
    with fixture():
        previous = signal.getsignal(signal.SIGTERM)
        def terminate(_): os.kill(os.getpid(), signal.SIGTERM)
        with patch.object(d, 'run_observation', side_effect=terminate), redirect_stdout(io.StringIO()):
            rc = d.main(['--execute', '--worker', '--max-wall-sec', '30'])
        print(json.dumps(dict(rc=rc, activity=d.read_json(d.EVIDENCE / 'activity.json'),
            handler_restored=signal.getsignal(signal.SIGTERM) == previous)), flush=True)


class Contracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import torch
        torch.set_num_threads(1)

    def test_full_production_recipe_roundtrip_and_no_old_pass(self):
        recipe, _ = metadata()
        self.assertEqual(recipe, json.loads(json.dumps(recipe))); self.assertTrue(recipe['code_complete'])
        self.assertIn(d.SCRIPT, recipe['code_sha256']); self.assertIn(d.TEST, recipe['code_sha256'])
        self.assertEqual(recipe['limitations']['old_gate_status'], 'ERROR9_PRESERVED')
        self.assertFalse(recipe['limitations']['old_gate_pass']); self.assertFalse(recipe['limitations']['threshold_changed'])

    def test_code_only_never_dispatches_input_or_model(self):
        recipe, _ = metadata()
        with patch.object(d, 'info', return_value=recipe), patch.object(d, 'preflight') as p, patch.object(d, 'load_bundle') as m:
            with redirect_stdout(io.StringIO()): self.assertEqual(d.main(['--check-only']), 0)
        p.assert_not_called(); m.assert_not_called()

    def test_phase_order_self_driver_and_stdin_owned_launcher(self):
        phases = d.phase_commands(600)
        self.assertEqual([p[0] for p in phases], ['REGRESSION', 'PREFLIGHT', 'EXECUTE'])
        self.assertIn('scripts.test_p070b_prefill_shape_cause', phases[0][1])
        self.assertTrue(all(d.SCRIPT in command for _, command in phases[1:]))
        self.assertIn('--worker', phases[-1][1]); self.assertNotIn('--worker', phases[1][1])

    def test_deadline_and_caps_are_unchanged(self):
        d.authority(600, now=d.END - timedelta(seconds=1200))
        with self.assertRaises(d.Pending): d.authority(600, now=d.END - timedelta(seconds=1199))
        for cap in (0, 601, True):
            with self.assertRaises(ValueError): d.phase_commands(cap)

    def test_special_ids_never_enter_future_control(self):
        import numpy as np
        values = np.arange(35, 44, dtype=np.int64).reshape(1, 9)
        changed = d.future_ids(values, 67)
        self.assertTrue(np.array_equal(changed[:, :3], values[:, :3]))
        self.assertEqual(int(np.count_nonzero(changed != values)), 6); self.assertTrue(bool((changed[:, 3:] >= 35).all()))
        values[0, 3] = 4
        with self.assertRaises(ValueError): d.future_ids(values, 67)

    def test_finite_numerical_negative_is_observed_not_relabelled_pass(self):
        import numpy as np
        left = np.zeros((1, 3, 67), dtype=np.float32); right = left + 1e-3
        measured = d.measured(left, right)
        self.assertFalse(measured['close']); self.assertGreater(measured['mismatch_elements'], 0)
        self.assertEqual(measured['atol'], 1e-5); self.assertEqual(measured['rtol'], 1e-4)
        with self.assertRaises(ValueError): d.measured(left, np.full_like(left, np.nan))
        with self.assertRaises(ValueError): d.measured(left, right[:, :2])

    def test_seven_contrasts_keep_shape_cache_and_future_axes_separate(self):
        import numpy as np
        a = np.zeros((1, 9, 67), dtype=np.float32); b = a[:, :3].copy() + 1e-3
        e = a.copy(); e[:, 3:] = 1
        probes = dict(A=a, Aon=a.copy(), B=b, C=b.copy(), D=a.copy(), E=e)
        result = d.contrasts(probes, a, a)
        self.assertEqual(set(result), set(d.CONTRASTS))
        self.assertFalse(result['A_prefix_vs_B']['close'])
        for name in ('A_vs_Aon', 'B_vs_C', 'A_prefix_vs_E_prefix'):
            self.assertTrue(result[name]['exact_equal'])

    def test_metadata_preflight_does_not_load_arrays_cp_or_tokenizer(self):
        with fixture(), patch('numpy.load', side_effect=AssertionError('metadata에서배열로드금지')), \
                patch.object(d, 'load_bundle', side_effect=AssertionError('metadata에서모델로드금지')):
            binding = d.preflight(30)
            self.assertEqual(binding['models_created'], 0); self.assertFalse(binding['raw_arrays_loaded'])
            self.assertFalse(any(p.exists() for p in (d.CACHE, d.RAW, d.EVIDENCE)))

    def test_source_failure_and_threshold_metadata_cannot_be_changed(self):
        with fixture():
            original = d.read_json(d.OLD_FAILURE)
            for key, value in (('complete', True), ('route', 'r2_uniform'), ('parent_core_sha256', '0' * 64)):
                damaged = copy.deepcopy(original); damaged.pop('integrity_sha256'); damaged[key] = value
                with self.subTest(key=key), self.assertRaises(ValueError): d.validate_old_failure(d.seal(damaged))
            damaged = copy.deepcopy(original); damaged.pop('integrity_sha256'); damaged['raw']['comparison']['atol'] = 1e-4
            with self.assertRaises(ValueError): d.validate_old_failure(d.seal(damaged))

    def test_raw_size_and_exact_output_scope(self):
        import numpy as np
        with fixture(), patch.object(d, 'LIMIT', 500):
            with self.assertRaises(ValueError): d.save_probe('A', np.zeros((1, 9), dtype=np.int64), np.zeros((1, 9, 67), dtype=np.float32))
            with self.assertRaises(ValueError): d.write_json(d.ROOT / 'outside.json', {})
            self.assertFalse(d.RAW.exists())

    def test_no_runtime_legacy_global_monkeypatch_in_driver(self):
        import ast
        tree = ast.parse((ROOT / d.SCRIPT).read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and isinstance(node.ctx, ast.Store):
                self.assertFalse(isinstance(node.value, ast.Name) and node.value.id == 'old')
        self.assertNotIn('unittest.mock', (ROOT / d.SCRIPT).read_text())


class Integration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import torch
        torch.set_num_threads(1)

    def test_tiny_actual_worker_full_recipe_and_raw_readback(self):
        with fixture() as f:
            report = complete(); receipt = d.readback()
            self.assertEqual(report['recipe'], f['recipe']); self.assertEqual(receipt['contrasts'], 7)
            self.assertEqual(set(report['probes']), set(d.PROBES))
            self.assertEqual(report['core_before'], report['core_after'])
            self.assertEqual(report['source_before'], report['source_after'])
            self.assertFalse(report['comparisons']['D_vs_old_cached']['close'])
            self.assertFalse(report['limitations']['old_gate_pass'])
            self.assertEqual(d.digest(d.OLD_RAW), d.OLD_RAW_SHA)
            self.assertEqual(d.digest(d.OLD_FAILURE), d.OLD_FAILURE_SHA)

    def test_missing_contrasts_and_false_pass_promotion_are_rejected(self):
        with fixture():
            original = complete()
            mutations = [lambda r: r['comparisons'].pop('B_vs_C'), lambda r: r['probes'].pop('E'),
                lambda r: r['limitations'].update(old_gate_pass=True),
                lambda r: r['comparisons']['A_vs_D'].update(max_abs=999.),
                lambda r: r['runtime_cfg'].update(train_repeat=1.)]
            for index, mutate in enumerate(mutations):
                report = copy.deepcopy(original); report.pop('integrity_sha256'); mutate(report)
                with self.subTest(index=index), self.assertRaises(ValueError): d.validate_report(d.seal(report))

    def test_raw_damage_and_activity_binding_are_rejected(self):
        with fixture():
            complete(); activity = d.read_json(d.EVIDENCE / 'activity.json')
            activity['report_sha256'] = '0' * 64; put(d.EVIDENCE / 'activity.json', activity)
            with self.assertRaises(ValueError): d.readback()
            with (d.RAW / 'E.npz').open('ab') as stream: stream.write(b'damage')
            with self.assertRaises(ValueError): d.validate_report(d.read_json(d.EVIDENCE / 'report.json'))

    def test_existing_namespace_is_not_reused_or_appended(self):
        with fixture():
            d.RAW.mkdir(parents=True)
            with redirect_stdout(io.StringIO()): self.assertEqual(d.main(['--execute', '--max-wall-sec', '30']), 8)
            self.assertFalse((d.EVIDENCE / 'final.json').exists())

    def test_actual_worker_exception_preserves_error_activity(self):
        with fixture(), patch.object(d, 'run_observation', side_effect=ValueError('합성오류')):
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                self.assertEqual(d.main(['--execute', '--worker', '--max-wall-sec', '30']), 9)
            activity = d.read_json(d.EVIDENCE / 'activity.json')
            self.assertEqual(activity['returncode'], 9); self.assertFalse(activity['complete'])
            self.assertIsNone(activity['report_sha256']); self.assertEqual(activity['old_gate_status'], 'ERROR9_PRESERVED')

    def test_owned_process_term_records130_and_restores_handler(self):
        code = 'from scripts.test_p070b_prefill_shape_cause import term_probe; term_probe()'
        env = dict(os.environ); env.update(d.old.THREAD_ENV)
        child = subprocess.run([sys.executable, '-B', '-c', code], cwd=ROOT, env=env,
            stdin=subprocess.DEVNULL, start_new_session=True, capture_output=True, text=True, timeout=30)
        self.assertEqual(child.returncode, 0, child.stderr)
        value = json.loads(child.stdout.splitlines()[-1])
        self.assertEqual(value['rc'], 130); self.assertTrue(value['handler_restored'])
        self.assertEqual(value['activity']['returncode'], 130); self.assertFalse(value['activity']['complete'])

    def test_alarm_timeout_preserves_failure_activity(self):
        with fixture():
            def expire(_): signal.getsignal(signal.SIGALRM)(signal.SIGALRM, None)
            with patch.object(d, 'run_observation', side_effect=expire), self.assertRaises(TimeoutError): d.worker(30)
            self.assertEqual(d.read_json(d.EVIDENCE / 'activity.json')['error_type'], 'TimeoutError')


if __name__ == '__main__': unittest.main()
