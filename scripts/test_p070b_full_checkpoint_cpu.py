"""Synthetic/temp-only CPU regressions; never open a real CP/tokenizer/bin.

The miniature14-layer vocabulary67 fixture intentionally is not a real-model
receipt. Full production info is retained (not replaced by a minimal mock) so
JSON serialization and complete metadata matching are exercised end to end.
"""
from __future__ import annotations

from contextlib import contextmanager, redirect_stdout, redirect_stderr, ExitStack
import copy
from dataclasses import asdict, replace
from datetime import datetime, timedelta, timezone
import io
import importlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts import diag_p070b_full_checkpoint_cpu as d

_PRODUCTION_RECIPE = None
_NATIVE_INFO = None


def production_metadata():
    global _PRODUCTION_RECIPE, _NATIVE_INFO
    if _PRODUCTION_RECIPE is None:
        _PRODUCTION_RECIPE = d.info()
        _NATIVE_INFO = d.native_module().info()
    return copy.deepcopy(_PRODUCTION_RECIPE), copy.deepcopy(_NATIVE_INFO)


def config():
    from tinylm.config import TMTConfig
    return TMTConfig(vocab_size=67, dim=32, ffn_dim=64, n_q_heads=4, n_kv_heads=2,
        emb_rank=8, n_prelude=2, n_middle=10, n_coda=2, mlp_group=2, tie_mlp=False,
        cla_group=2, cla_edges=True, micro_group=0, grad_checkpoint=True, max_seq_len=1024)


def tiny_model(mode='uniform', repeats=2):
    import torch
    from scripts import p070b_cla_routes as r
    from tinylm.model import TiedMLPTransformer
    torch.manual_seed(1337)
    cfg = replace(config(), train_repeat=float(repeats))
    model = TiedMLPTransformer(cfg) if mode is None else r.FixedRouteTransformer(cfg, mode, repeats, d.SEED)
    model.set_anneal(1.)
    return model


class TinyTokenizer:
    def encode(self, text, *, add_special_tokens):
        if add_special_tokens is not False: raise AssertionError('no implicit special tokens')
        ids = [1, 5, 9, 13, 17, 21] if text == d.PROMPTS[0][1] else [2, 6, 10, 14, 18, 22, 26]
        return type('Encoding', (), dict(ids=ids))()


def put(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8') as stream: json.dump(value, stream, ensure_ascii=False)


@contextmanager
def fixture():
    """All asset and output paths belong to one temporary directory only."""
    import torch
    recipe, native_info = production_metadata()
    with tempfile.TemporaryDirectory(prefix='p070b-cpu-test-') as directory, ExitStack() as stack:
        root = Path(directory); real_root = d.ROOT
        paths = {name: root / getattr(d, name).relative_to(real_root) for name in (
            'CACHE', 'RAW', 'EVIDENCE', 'PARENT', 'TOKENIZER', 'NATIVE_REPORT', 'NATIVE_ACTIVITY', 'NATIVE_REFERENCE', 'F4')}
        stack.enter_context(patch.multiple(d, ROOT=root, **paths))
        end = datetime.now(timezone.utc) + timedelta(days=1)
        stack.enter_context(patch.object(d, 'END', end))
        paths['TOKENIZER'].parent.mkdir(parents=True, exist_ok=True)
        paths['TOKENIZER'].write_bytes(b'fixture tokenizer; no actual tokenizer opened')
        put(paths['NATIVE_REFERENCE'], dict(scope='TINY_SYNTHETIC_ONLY'))
        model = tiny_model(None, 1); core = d.fingerprint(model)
        report = dict(native_info, status='TRAIN_COMPLETE', arm='ternary', endpoint='native', cost=False,
            updates=2281, totals=dict(targets=298975232), initial_core_sha256='A' * 64,
            scratch_core_sha256='A' * 64, final_core_sha256=core, parent_checkpoint_sha256=None,
            parent_core_sha256=None, checkpoint_writes=1, optimizer_saved=False,
            reference_sha256=d.digest(paths['NATIVE_REFERENCE']), checkpoint=str(paths['PARENT'].relative_to(root)))
        from scripts.p106b_weight_route import route_metadata
        payload = dict(model=model.state_dict(), cfg=asdict(model.cfg), step=2281,
            tokenizer_sha256=d.digest(paths['TOKENIZER']), tokenizer_lineage='chat32',
            quantization_route=route_metadata('ternary'), experiment=d.native_module().cp_experiment(report))
        paths['PARENT'].parent.mkdir(parents=True, exist_ok=True)
        with paths['PARENT'].open('xb') as stream: torch.save(payload, stream)
        parent_sha, tok_sha = d.digest(paths['PARENT']), d.digest(paths['TOKENIZER'])
        stack.enter_context(patch.multiple(d, PARENT_SHA=parent_sha, PARENT_CORE=core, TOKENIZER_SHA=tok_sha))
        report['checkpoint_sha256'] = parent_sha
        put(paths['NATIVE_REPORT'], report)
        activity = dict(schema=native_info['schema'], tag=d.NATIVE_TAG, key='train_ternary', mode='train',
            arm='ternary', endpoint=None, complete=True, returncode=0, error_type=None,
            seconds=1., max_wall_sec=600, started_at='2026-10-19T13:00:00+00:00', ended_at='2026-10-19T13:00:01+00:00',
            result_sha256=d.digest(paths['NATIVE_REPORT']), reference_sha256=report['reference_sha256'],
            code_sha256=native_info['code_sha256'])
        put(paths['NATIVE_ACTIVITY'], activity)
        recipe.update(parent_sha256=parent_sha, parent_core_sha256=core, tokenizer_sha256=tok_sha,
            authority_end_utc=end.isoformat())
        for key in recipe['shape']: recipe['shape'][key] = getattr(model.cfg, key)
        stack.enter_context(patch.object(d, 'info', side_effect=lambda: copy.deepcopy(recipe)))
        stack.enter_context(patch.object(d.native_module(), 'info', return_value=copy.deepcopy(native_info)))
        stack.enter_context(patch('tokenizers.Tokenizer.from_file', return_value=TinyTokenizer()))
        prepare_module = importlib.import_module('tinylm.data.prepare')
        stack.enter_context(patch.object(prepare_module, 'verify_chat_tokenizer'))
        yield dict(root=root, recipe=recipe, model=model, payload=payload, parent=report, activity=activity,
                   native_info=native_info)


def ids():
    import torch
    return torch.tensor([[1, 5, 9, 13, 17, 21]], dtype=torch.long)


def completed():
    d.worker(30)
    return d.read_json(d.EVIDENCE / 'report.json')


def term_probe():
    """Called in a separate owned process; actual TERM, synthetic assets only."""
    import torch
    torch.set_num_threads(1)
    with fixture():
        previous = signal.getsignal(signal.SIGTERM)
        def terminate(_):
            os.kill(os.getpid(), signal.SIGTERM)
            raise AssertionError('TERM must unwind the actual worker')
        with patch.object(d, 'run_gate', side_effect=terminate):
            rc = d.main(['--execute', '--worker', '--max-wall-sec', '30'])
        activity = d.read_json(d.EVIDENCE / 'activity.json')
        print(json.dumps(dict(rc=rc, activity=activity,
            restored=signal.getsignal(signal.SIGTERM) == previous)), flush=True)


class PureContracts(unittest.TestCase):
    def test_full_production_info_json_round_trip(self):
        recipe, _ = production_metadata()
        self.assertEqual(recipe, json.loads(json.dumps(recipe)))
        self.assertTrue(recipe['code_complete']); self.assertIn(d.SCRIPT, recipe['code_sha256'])
        self.assertIn(d.TEST, recipe['code_sha256']); self.assertGreater(len(recipe['code_sha256']), 20)
        self.assertEqual(recipe['shape']['dim'], 768)
        self.assertFalse(recipe['limitations']['parent_is_r2_trained'])

    def test_check_only_is_code_only_and_never_dispatches_assets(self):
        recipe, _ = production_metadata()
        with patch.object(d, 'info', return_value=recipe), patch.object(d, 'preflight') as p, patch.object(d, 'worker') as w:
            with redirect_stdout(io.StringIO()): self.assertEqual(d.main(['--check-only']), 0)
        p.assert_not_called(); w.assert_not_called()

    def test_three_phase_commands_use_self_and_bounded_worker(self):
        phases = d.phase_commands(60)
        self.assertEqual([x[0] for x in phases], ['REGRESSION', 'PREFLIGHT', 'EXECUTE'])
        self.assertIn('scripts.test_p070b_full_checkpoint_cpu', phases[0][1])
        self.assertTrue(all(d.SCRIPT in c for _, c in phases[1:]))
        self.assertNotIn('--worker', phases[1][1]); self.assertIn('--worker', phases[2][1])

    def test_invalid_caps_and_unused_worker_are_rejected(self):
        for value in (0, 601, True, 1.5):
            with self.subTest(value=value), self.assertRaises(ValueError): d.cap(value)
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(d.main(['--check-only', '--worker']), 9)

    def test_absolute_deadline_preserves600s_record_reserve(self):
        d.authority(600, now=d.END - timedelta(seconds=1200))
        with self.assertRaises(d.Pending): d.authority(600, now=d.END - timedelta(seconds=1199))
        with self.assertRaises(ValueError): d.authority(1, now=datetime(2026, 1, 1))

    def test_no_namespace_writes_outside_exact_new_scope(self):
        with fixture() as f:
            with self.assertRaises(ValueError): d.write_json(f['root'] / 'unapproved.json', {})
            link = f['root'] / 'link'; link.symlink_to(f['root'] / 'data_cache', target_is_directory=True)
            with self.assertRaises(ValueError): d.safe(link / 'bad.json')

    def test_json_and_raw_size_guards_are_prewrite(self):
        import numpy as np
        with fixture(), patch.object(d, 'PUBLIC_LIMIT', 500):
            with self.assertRaises(ValueError): d.write_json(d.EVIDENCE / 'big.json', dict(data='x' * 500))
            full = np.zeros((1, 4, 67), dtype=np.float32)
            with self.assertRaises(ValueError): d.save_raw('big', np.zeros((1, 4), dtype=np.int64), full, full)
            with self.assertRaises(ValueError):
                d.save_raw('failed_big', np.zeros((1, 4), dtype=np.int64), full, full + 1e-3,
                    allow_tolerance_failure=True)
            self.assertFalse(d.EVIDENCE.exists()); self.assertFalse(d.RAW.exists())

    def test_preflight_never_loads_cp_tensor_or_tokenizer(self):
        with fixture(), patch('torch.load', side_effect=AssertionError('actual load in preflight')), \
                patch('tokenizers.Tokenizer.from_file', side_effect=AssertionError('tokenizer in preflight')):
            result = d.preflight(30)
            self.assertEqual(result['real_models_created'], 0)
            self.assertEqual(result['checkpoint_tensors_loaded'], 0); self.assertFalse(result['tokenizer_loaded'])
            self.assertFalse(any(p.exists() for p in (d.CACHE, d.RAW, d.EVIDENCE)))

    def test_preflight_rejects_prior_partial_namespace(self):
        with fixture():
            d.RAW.mkdir(parents=True)
            with self.assertRaises(FileExistsError): d.preflight(30)

    def test_producer_report_is_exact_scratch_r1_not_sft_parent(self):
        with fixture() as f:
            for key, wrong in (('endpoint', 'sft'), ('parent_training_weights_copied', True),
                               ('final_core_sha256', '0' * 64), ('checkpoint_writes', 0)):
                report = copy.deepcopy(f['parent']); report[key] = wrong
                with self.subTest(key=key), self.assertRaises(ValueError):
                    d.validate_parent_receipt(report, f['activity'], f['native_info'],
                        d.digest(d.NATIVE_REPORT), d.digest(d.NATIVE_REFERENCE))

    def test_producer_activity_requires_report_and_code_binding(self):
        with fixture() as f:
            for key, wrong in (('complete', False), ('result_sha256', '0' * 64), ('code_sha256', {})):
                activity = copy.deepcopy(f['activity']); activity[key] = wrong
                with self.subTest(key=key), self.assertRaises(ValueError):
                    d.validate_parent_receipt(f['parent'], activity, f['native_info'],
                        d.digest(d.NATIVE_REPORT), d.digest(d.NATIVE_REFERENCE))

    def test_payload_requires_ternary_route_step_cfg_and_experiment(self):
        with fixture() as f:
            d.validate_payload(f['payload'], f['model'].cfg, f['parent'])
            for key, wrong in (('step', 0), ('experiment', {}), ('tokenizer_lineage', 'legacy'),
                               ('quantization_route', dict(mode='float'))):
                payload = dict(f['payload'], **{key: wrong})
                with self.subTest(key=key), self.assertRaises(ValueError):
                    d.validate_payload(payload, f['model'].cfg, f['parent'])

    def test_cfg_rejects_changed_architecture_and_recursion(self):
        with fixture():
            d.validate_cfg(config())
            for key, wrong in (('dim', 64), ('cla_group', 1), ('train_repeat', 2.), ('tie_mlp', True)):
                cfg = config(); setattr(cfg, key, wrong)
                with self.subTest(key=key), self.assertRaises(ValueError): d.validate_cfg(cfg)


class TinyNumerics(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import torch
        torch.set_num_threads(1)

    def test_strict_cpu_load_and_fingerprint(self):
        with fixture() as f:
            model = tiny_model('uniform', 2); d.strict_load(model, f['payload'], d.PARENT_CORE)
            self.assertEqual(d.fingerprint(model), d.PARENT_CORE)

    def test_wrong_key_or_dtype_rejected_before_copy(self):
        with fixture() as f:
            model = tiny_model(); before = d.fingerprint(model)
            for kind in ('key', 'dtype'):
                payload = copy.deepcopy(f['payload']); key = next(iter(payload['model']))
                if kind == 'key': payload['model'].pop(key)
                else: payload['model'][key] = payload['model'][key].double()
                with self.subTest(kind=kind), self.assertRaises(ValueError): d.strict_load(model, payload, d.PARENT_CORE)
                self.assertEqual(d.fingerprint(model), before)

    def test_conflicting_parameter_aliases_are_rejected(self):
        with fixture() as f:
            model = tiny_model(); model.register_parameter('fixture_alias', model.emb.weight); groups = {}
            for name, parameter in model.named_parameters(remove_duplicate=False): groups.setdefault(id(parameter), []).append(name)
            alias = next(names for names in groups.values() if len(names) > 1)
            payload = dict(f['payload'], model=dict(model.state_dict()))
            payload['model'][alias[1]] = payload['model'][alias[1]].clone() + 1
            with self.assertRaisesRegex(ValueError, '공유 Parameter'): d.strict_load(model, payload, d.PARENT_CORE)

    def test_all_five_routes_real_tiny_cache_shapes_and_parity(self):
        routes = {}
        for name, mode, repeats in d.ROUTES:
            model = tiny_model(mode, repeats)
            full, cached, result = d.cache_case(model, ids(), fixed=mode is not None)
            self.assertTrue(result['comparison']['close']); self.assertEqual(full.shape, cached.shape)
            self.assertEqual(result['cache']['kv_entries'], 7 if repeats == 1 else 12)
            self.assertEqual(result['cache']['visits'], 4 + 10 * repeats)
            routes[name] = result['cache']['route']
        self.assertEqual(routes['product_r1'], routes['fixed_r1'])
        self.assertEqual(len({tuple(routes[n]) for n in ('r2_uniform', 'r2_reverse', 'r2_shuffle')}), 3)

    def test_cache_receipt_rejects_wrong_route_shape_dtype(self):
        import torch
        from scripts import p070b_cla_routes as r
        model = tiny_model(); model.eval()
        with torch.no_grad(): _, bank = model(ids()[:, :3], use_cache=True)
        with self.assertRaises(ValueError): d.cache_receipt(model, r.RouteCache('BAD', bank.bank), 3, fixed=True)
        wrong = dict(bank.bank); key = next(iter(wrong)); k, v = wrong[key]; wrong[key] = (k.double(), v)
        with self.assertRaises(ValueError): d.cache_receipt(model, r.RouteCache(bank.route_sha256, wrong), 3, fixed=True)

    def test_changed_route_cache_rejected_and_route_restored(self):
        model = tiny_model(); before = model.route_sha256
        result = d.route_change_rejected(model, ids())
        self.assertTrue(result['rejected']); self.assertEqual(model.route_sha256, before)

    def test_silently_accepting_changed_cache_is_not_a_pass(self):
        model = tiny_model(); original = model.forward
        def broken(*args, **kwargs):
            if kwargs.get('past_kv') is not None: return None
            return original(*args, **kwargs)
        with patch.object(model, 'forward', side_effect=broken), self.assertRaisesRegex(ValueError, 'silently accepted'):
            d.route_change_rejected(model, ids())

    def test_backward_unfreezes_eval_cache_and_preserves_all_weights(self):
        import torch
        model = tiny_model(); model.eval()
        with torch.no_grad(): model.freeze_quant()
        self.assertFalse(model._tlinear_cache[0]._wq.requires_grad)
        result = d.backward_case(model, ids())
        self.assertEqual(result['core_before'], result['core_after']); self.assertEqual(result['targets'], 5)
        self.assertTrue(result['gradients']['finite']); self.assertEqual(result['gradients']['connected_tlinear_weights'], 84)
        self.assertFalse(model._quant_frozen); self.assertTrue(all(p.grad is None for p in model.parameters()))

    def test_missing_body_or_embedding_gradient_cannot_pass(self):
        model = tiny_model()
        with self.assertRaisesRegex(ValueError, 'connection'): d.gradient_receipt(model)

    def test_nonfinite_gradient_cannot_pass(self):
        import torch
        model = tiny_model(); model.emb.weight.grad = torch.full_like(model.emb.weight, float('nan'))
        with self.assertRaisesRegex(ValueError, 'nonfinite'): d.gradient_receipt(model)

    def test_original_tolerance_is_fixed_and_nonfinite_arrays_rejected(self):
        import numpy as np
        full = np.zeros((1, 4, 67), dtype=np.float32)
        for wrong in (full + 1e-3, np.full_like(full, np.nan), full.astype(np.float64), full[:, :3]):
            with self.subTest(dtype=wrong.dtype), self.assertRaises(ValueError): d.comparison(full, wrong)

    def test_raw_round_trip_hash_and_denominator_recheck(self):
        import numpy as np
        with fixture():
            d.RAW.mkdir(parents=True)
            full, cached, _ = d.cache_case(tiny_model(), ids(), fixed=True)
            entry = d.save_raw('fixture', ids().numpy(), full, cached)
            actual_ids, actual_full = d.read_raw(entry)
            self.assertTrue(np.array_equal(ids().numpy(), actual_ids)); self.assertTrue(np.array_equal(full, actual_full))
            entry['comparison']['elements'] += 1
            with self.assertRaises(ValueError): d.read_raw(entry)


class ReceiptIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import torch
        torch.set_num_threads(1)

    def test_actual_tiny_worker_full_info_serialization_and_readback(self):
        with fixture() as f:
            report = completed()
            self.assertEqual(report['recipe'], f['recipe'])
            self.assertGreater(len(report['recipe']), 20)
            self.assertEqual(d.readback()['raw_cases'], 10)
            self.assertFalse(report['limitations']['old_stage1w_r2_parent_complete'])
            with self.assertRaises(FileExistsError): d.worker(30)

    def test_damaged_or_forged_complete_reports_are_rejected(self):
        with fixture():
            original = completed()
            mutations = [lambda r: r['recipe'].update(dtype='bfloat16'),
                lambda r: r['cases'].pop(), lambda r: r['cases'][0]['cache'].update(route_sha256='0' * 64),
                lambda r: r['route_cfgs']['r2_reverse'].update(cla_group=1),
                lambda r: r['cases'][0]['comparison'].update(close=False),
                lambda r: r['backward']['gradients'].update(total_l2=0.),
                lambda r: r['backward'].update(targets=1),
                lambda r: r['limitations'].update(language_quality='PASS'),
                lambda r: r.update(model_instances=0)]
            for index, mutate in enumerate(mutations):
                report = copy.deepcopy(original); report.pop('integrity_sha256'); mutate(report); report = d.seal(report)
                with self.subTest(index=index), self.assertRaises(ValueError): d.validate_report_core(report)

    def test_report_integrity_is_checked_before_raw(self):
        with fixture():
            report = completed(); report['status'] = 'PASS'
            with self.assertRaises(ValueError): d.validate_report_core(report)

    def test_activity_is_required_and_hash_bound_to_complete_report(self):
        with fixture():
            completed(); activity = d.read_json(d.EVIDENCE / 'activity.json')
            activity['report_sha256'] = '0' * 64; put(d.EVIDENCE / 'activity.json', activity)
            with self.assertRaises(ValueError): d.readback()

    def test_activity_deadline_damage_is_rejected(self):
        with fixture():
            completed(); activity = d.read_json(d.EVIDENCE / 'activity.json')
            activity['ended_at'] = (d.END + timedelta(seconds=1)).isoformat()
            put(d.EVIDENCE / 'activity.json', activity)
            with self.assertRaises(ValueError): d.readback()

    def test_existing_namespace_is_hold_without_appending_another_final(self):
        with fixture():
            d.EVIDENCE.mkdir(parents=True)
            with redirect_stdout(io.StringIO()): self.assertEqual(d.main(['--execute', '--max-wall-sec', '30']), 8)
            self.assertFalse((d.EVIDENCE / 'final.json').exists())

    def test_raw_byte_damage_is_not_a_report_pass(self):
        with fixture():
            report = completed(); entry = report['cases'][0]['raw']; path = d.ROOT / entry['path']
            with path.open('ab') as stream: stream.write(b'corruption')
            with self.assertRaises(ValueError): d.validate_report_core(report)

    def test_actual_worker_error_preserves_failure_activity(self):
        with fixture(), patch.object(d, 'run_gate', side_effect=ValueError('synthetic implementation fault')):
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()) as error:
                self.assertEqual(d.main(['--execute', '--worker', '--max-wall-sec', '30']), 9)
            self.assertIn('synthetic implementation fault', error.getvalue())
            activity = d.read_json(d.EVIDENCE / 'activity.json')
            self.assertEqual(activity['returncode'], 9); self.assertFalse(activity['complete'])
            self.assertEqual(activity['error_type'], 'ValueError'); self.assertIsNone(activity['report_sha256'])

    def assert_preserved_tolerance_negative(self, kind):
        import numpy as np
        failure = d.read_json(d.EVIDENCE / 'failure.json'); activity = d.read_json(d.EVIDENCE / 'activity.json')
        self.assertEqual(failure['status'], 'CPU_TOLERANCE_FAILED'); self.assertFalse(failure['complete'])
        self.assertEqual(failure['comparison_kind'], kind); self.assertEqual(failure['language'], 'ko')
        self.assertEqual(len(failure['route_sha256']), 64)
        self.assertFalse(failure['raw']['comparison']['close'])
        self.assertGreater(failure['raw']['comparison']['max_abs'], 0.)
        self.assertGreater(failure['raw']['comparison']['mean_abs'], 0.)
        path = d.ROOT / failure['raw']['path']; self.assertLess(path.stat().st_size, d.PUBLIC_LIMIT)
        self.assertEqual(d.digest(path), failure['raw']['sha256'])
        with np.load(path, allow_pickle=False) as arrays:
            self.assertEqual(arrays['ids'].shape[1], failure['input_ids'])
            with self.assertRaises(d.ToleranceFailure) as error: d.comparison(arrays['full'], arrays['cached'])
            self.assertEqual(error.exception.metrics, failure['raw']['comparison'])
        self.assertEqual(activity['returncode'], 9); self.assertFalse(activity['complete'])
        self.assertEqual(activity['error_type'], 'ToleranceFailure')
        self.assertEqual(activity['failure_sha256'], d.digest(d.EVIDENCE / 'failure.json'))
        self.assertIsNone(activity['report_sha256']); self.assertFalse((d.EVIDENCE / 'report.json').exists())
        with self.assertRaises(d.Pending): d.readback()

    def test_finite_cache_mismatch_preserves_negative_raw_metrics_and_failure_activity(self):
        with fixture():
            original = d.cache_case
            def mismatch(model, values, *, fixed):
                full, cached, _ = original(model, values, fixed=fixed)
                d.comparison(full, cached + 1e-3)
                raise AssertionError('finite mismatch must fail')
            with patch.object(d, 'cache_case', side_effect=mismatch), redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()) as error:
                self.assertEqual(d.main(['--execute', '--worker', '--max-wall-sec', '30']), 9)
            self.assertIn('max_abs', error.getvalue())
            self.assert_preserved_tolerance_negative('FULL_VS_CACHED')
            self.assertEqual(d.read_json(d.EVIDENCE / 'failure.json')['route'], 'product_r1')

    def test_product_fixed_r1_mismatch_also_preserves_distinct_comparison_negative(self):
        with fixture():
            original = d.cache_case
            def mismatch(model, values, *, fixed):
                full, cached, observed = original(model, values, fixed=fixed)
                if fixed and model.cfg.train_repeat == 1.:
                    full, cached = full + 1e-3, cached + 1e-3
                    observed['comparison'] = d.comparison(full, cached)
                return full, cached, observed
            with patch.object(d, 'cache_case', side_effect=mismatch), redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                self.assertEqual(d.main(['--execute', '--worker', '--max-wall-sec', '30']), 9)
            self.assert_preserved_tolerance_negative('PRODUCT_R1_VS_FIXED_R1')
            self.assertEqual(d.read_json(d.EVIDENCE / 'failure.json')['route'], 'fixed_r1')

    def test_nonfinite_shape_invalids_remain_rejected_without_tolerance_raw(self):
        import numpy as np
        with fixture():
            def invalid(*_, **__):
                full = np.zeros((1, 4, 67), dtype=np.float32)
                return d.comparison(full, np.full_like(full, np.nan))
            with patch.object(d, 'cache_case', side_effect=invalid), redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                self.assertEqual(d.main(['--execute', '--worker', '--max-wall-sec', '30']), 9)
            self.assertFalse((d.EVIDENCE / 'failure.json').exists()); self.assertEqual(list(d.RAW.iterdir()), [])
            self.assertEqual(d.read_json(d.EVIDENCE / 'activity.json')['error_type'], 'ValueError')

    def test_actual_owned_subprocess_term_records130_and_restores_handler(self):
        code = 'from scripts.test_p070b_full_checkpoint_cpu import term_probe; term_probe()'
        env = dict(os.environ); env.update(d.THREAD_ENV)
        result = subprocess.run([sys.executable, '-B', '-c', code], cwd=ROOT, env=env,
            stdin=subprocess.DEVNULL, capture_output=True, text=True, start_new_session=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        result = json.loads(result.stdout.splitlines()[-1]); self.assertEqual(result['rc'], 130)
        self.assertTrue(result['restored']); self.assertFalse(result['activity']['complete'])
        self.assertEqual(result['activity']['returncode'], 130)

    def test_zero_work_fake_execute_success_cannot_become_final_pass(self):
        with fixture(), patch.object(d, 'launch', return_value=0), redirect_stdout(io.StringIO()) as output, redirect_stderr(io.StringIO()):
            self.assertEqual(d.main(['--execute', '--max-wall-sec', '30']), 9)
            self.assertIn('"status": "ERROR"', output.getvalue())
            self.assertFalse((d.EVIDENCE / 'report.json').exists())


class ProcessContracts(unittest.TestCase):
    def test_term_handler_restored_on_exception_and_repeated_term_is_ignored(self):
        previous = signal.getsignal(signal.SIGTERM)
        with d.termination_guard():
            handler = signal.getsignal(signal.SIGTERM)
            with self.assertRaises(KeyboardInterrupt): handler(signal.SIGTERM, None)
            handler(signal.SIGTERM, None)
        self.assertEqual(signal.getsignal(signal.SIGTERM), previous)

    def test_alarm_and_environment_restore_on_error(self):
        previous = signal.getsignal(signal.SIGALRM); env = {k: os.environ.get(k) for k in d.THREAD_ENV}
        with self.assertRaisesRegex(ValueError, 'fixture'):
            with d.bounded_worker(1):
                self.assertTrue(all(os.environ[k] == v for k, v in d.THREAD_ENV.items()))
                raise ValueError('fixture')
        self.assertEqual(signal.getsignal(signal.SIGALRM), previous)
        self.assertEqual({k: os.environ.get(k) for k in d.THREAD_ENV}, env)

    def test_alarm_timeout_reaches_failure_activity(self):
        with fixture():
            def expired(_):
                handler = signal.getsignal(signal.SIGALRM); handler(signal.SIGALRM, None)
            with patch.object(d, 'run_gate', side_effect=expired):
                with self.assertRaises(TimeoutError): d.worker(30)
            self.assertEqual(d.read_json(d.EVIDENCE / 'activity.json')['error_type'], 'TimeoutError')

    def test_launch_uses_stdin0_and_only_own_process_group_term(self):
        process = Mock(pid=1234); process.wait.side_effect = [subprocess.TimeoutExpired(['fixture'], 1), 0]
        process.poll.return_value = None
        with patch.object(d.subprocess, 'Popen', return_value=process) as popen, \
                patch.object(d.os, 'getpgid', return_value=1234), patch.object(d.os, 'killpg') as kill:
            self.assertEqual(d.launch(['fixture'], 1), 124)
            kill.assert_called_once_with(1234, signal.SIGTERM)
            self.assertEqual(popen.call_args.kwargs['stdin'], subprocess.DEVNULL)
            self.assertTrue(popen.call_args.kwargs['start_new_session'])

    def test_launch_never_terms_other_process_group(self):
        process = Mock(pid=1234); process.wait.side_effect = subprocess.TimeoutExpired(['fixture'], 1)
        process.poll.return_value = None
        with patch.object(d.subprocess, 'Popen', return_value=process), \
                patch.object(d.os, 'getpgid', return_value=999), patch.object(d.os, 'killpg') as kill:
            self.assertEqual(d.launch(['fixture'], 1), 124); kill.assert_not_called()


if __name__ == '__main__':
    unittest.main()
