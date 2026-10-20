"""head별 NS와 원 수치본문·메타데이터·임시 worker만 검산한다. 실물 모델/CP/GPU0."""
from __future__ import annotations

from contextlib import contextmanager, redirect_stdout
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import inspect
import io
import json
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from scripts import diag_p106b_headwise_muon as d
from scripts import diag_p106b_route_cross_resume as utility
import torch


def param(shape, seed=123):
    generator = torch.Generator().manual_seed(seed)
    return torch.nn.Parameter(torch.randn(shape, generator=generator))


def meta_projection(cfg, rows, cols):
    module = d.TLinear.__new__(d.TLinear)
    torch.nn.Module.__init__(module)
    module.cfg, module.in_f, module.out_f = cfg, cols, rows
    module.weight = torch.nn.Parameter(torch.empty(rows, cols, device='meta'))
    return module


def metadata_model():
    """실제 Transformer를 생성하지 않는 zero-storage meta Parameter 소유권 fixture."""
    cfg = types.SimpleNamespace(dim=768, n_layers=14, n_q_heads=12, n_kv_heads=3, head_dim=64,
        kv_dim=192, cla_group=2, cla_edges=True, attn_group=1, tie_mlp=False)
    model = torch.nn.Module(); model.cfg = cfg; model.owner = [i - i % 2 for i in range(14)]
    layers = []
    for index in range(14):
        layer = torch.nn.Module(); attention = torch.nn.Module(); attention.owns_kv = index % 2 == 0
        attention.q_proj = meta_projection(cfg, 768, 768)
        if attention.owns_kv: attention.k_proj = meta_projection(cfg, 192, 768)
        layer.attn = attention; layers.append(layer)
    model.layers = torch.nn.ModuleList(layers)
    return model


def group_fixture():
    return [dict(optimizer='AdamW' if index < 2 else 'HeadwiseMuon', group=index if index < 2 else 0,
        parameters=count, names_sha256=digest, lr=5e-5 if index < 2 else 2e-4,
        runtime_lr=1e-4 if index < 2 else 4e-4, runtime_weight_decay=.1 if index == 0 else 0.,
        weight_decay=0., lr_multiplier=.5, scale_mode=None if index < 2 else 'rms',
        actual_class=torch.optim.AdamW.__module__ + '.' + torch.optim.AdamW.__qualname__ if index < 2 else
            'scripts.diag_p106b_headwise_muon.HeadwiseMuon')
        for index, (count, digest) in enumerate(d.GROUP_PINS)]


def locked_reports():
    return (dict(checkpoint_sha256=d.PARENT_SHA, final_core_sha256=d.PARENT_CORE, clip=1.),
        dict(checkpoint_sha256=d.BASELINE_SHA, final_core_sha256=d.BASELINE_CORE,
            parent_checkpoint_sha256=d.PARENT_SHA, initial_core_sha256=d.PARENT_CORE,
            totals=deepcopy(d.TOTALS), clip=1.))


def source_fixture():
    frozen = dict(exposure={'varied_balanced': [dict(counts=dict(x_tokens=2052163, assistant_targets=75664),
        update_target_denominators=[788] * 95 + [804]) for _ in range(4)]},
        native_train_offsets=[index * 1025 for index in range(3072)])
    return frozen, [dict(id=str(index)) for index in range(1694)]


def clone(function, env):
    source = inspect.unwrap(function)
    value = types.FunctionType(source.__code__, env, source.__name__, source.__defaults__, source.__closure__)
    value.__kwdefaults__ = source.__kwdefaults__
    return value


def closure_fixture(function, **values):
    def cell(value):
        return (lambda: value).__closure__[0]
    closure = tuple(cell(values.get(name, original.cell_contents))
        for name, original in zip(function.__code__.co_freevars, function.__closure__))
    value = types.FunctionType(function.__code__, function.__globals__, function.__name__, function.__defaults__, closure)
    value.__kwdefaults__ = function.__kwdefaults__
    return value


@contextmanager
def worker_fixture():
    real = d.build_runtime()
    with tempfile.TemporaryDirectory(prefix='headwise-worker-') as temporary:
        root = Path(temporary); env = dict(vars(real))
        env.update(ROOT=root, CACHE=root / 'cache', RAW=root / 'raw', EVIDENCE=root / 'evidence',
            info=lambda: real.info(), authority=lambda training=False: 100000., execution_remaining=lambda training=False: 100000.)
        p = types.SimpleNamespace(**env)
        for name in ('safe', 'digest', 'required', 'write', 'result_path', 'completed_activity'):
            setattr(p, name, clone(getattr(real, name), env))
        env.update(vars(p))
        p.validate_activity = lambda value, *args: value
        env['validate_activity'] = p.validate_activity
        p._headwise = types.SimpleNamespace(state={}, check=lambda: None)
        p.spent_seconds = lambda: 0.
        def prepare():
            p.write(p.CACHE / 'frozen_reference.json', dict(info=real.info(), fixture=True))
            return 0
        p.prepare = prepare
        p.source_state = lambda: None
        p.prepared = lambda: None
        yield p


@contextmanager
def strict_training_fixture(cost):
    """실제 completed_activity/read_events/두 strict reader를 붙인 임시 producer.

    원 데이터/가중치/모델 대신 작은 scalar event와 CP가 아닌 byte marker만 쓴다.
    검산기는 Mock이 아니며 실제 닫힌 shard와 SHA·384/8 전체 행을 읽는다.
    """
    from scripts.p106b_shards import ShardWriter
    from scripts import p106b_weight_route as route
    real = d.build_runtime()
    with tempfile.TemporaryDirectory(prefix='headwise-strict-') as temporary:
        root = Path(temporary); env = dict(vars(real)); key = 'cost' if cost else 'train'
        env.update(ROOT=root, CACHE=root / 'cache', RAW=root / 'raw', EVIDENCE=root / 'evidence',
            info=lambda: real.info(), execution_remaining=lambda training=False: 100000.,
            authority=lambda training=False: 100000.)
        p = types.SimpleNamespace(**env)
        frozen, cases = source_fixture()
        records = [types.SimpleNamespace(x_tokens=167) for _ in range(128)]
        micros = [list(range(i, i + 8)) for i in range(0, 128, 8)]
        source = types.SimpleNamespace(read_prepared=lambda: (frozen, None, None),
            records_for=lambda *args: records, schedule=lambda epoch: [micros] * 96)
        env['modules'] = lambda: (None, source, route)
        p.modules = env['modules']
        for name in ('safe', 'digest', 'required', 'write', 'result_path', 'completed_activity',
                     'read_events', 'update_contract', 'actual_lrs', 'validate_native32', 'validate_route_receipt'):
            setattr(p, name, clone(getattr(real, name), env))
        p.phase_key = real.phase_key
        p.checkpoint = lambda arm, endpoint: root / 'synthetic_marker_not_tensor.pt'
        p.validate_activity = closure_fixture(real.validate_activity, p=p,
            captured={'validate_activity': clone(real._headwise.captured['validate_activity'], env)})
        p.validate_optimizer_groups = closure_fixture(real.validate_optimizer_groups, p=p)
        env.update(vars(p))
        p.write(p.CACHE / 'frozen_reference.json', dict(info=real.info(), fixture=True))
        parent, control = locked_reports()
        parent['scratch_core_sha256'] = 'A' * 64
        native_reader = clone(real._headwise.captured['train_report'], env)
        p.train_report = closure_fixture(real.train_report, p=p,
            captured={'train_report': native_reader}, parent_and_baseline=lambda: (parent, control),
            phase_key=p.phase_key, info=p.info)
        env['train_report'] = p.train_report
        observations = dict(pending_before_close=False, raw_reads=[])
        original_read_events = p.read_events
        def read_events(directory, manifest, count):
            observations['raw_reads'].append(count)
            return original_read_events(directory, manifest, count)
        p.read_events = read_events; env['read_events'] = read_events
        count = 8 if cost else 384
        stats = dict(optimizer='HeadwiseMuon', actual_class='scripts.diag_p106b_headwise_muon.HeadwiseMuon',
            steps=count, target_counts={row['name']: count for row in d.target_geometry()},
            target_geometry_sha256=d.sha(d.target_geometry()), all_target_updates_verified=True)
        p._headwise = types.SimpleNamespace(state={}, check=lambda: None,
            execution_stats=lambda actual: deepcopy(stats) if actual == count else None)
        p.spent_seconds = lambda: 0.
        def produce(arm, endpoint, is_cost, cap):
            if (arm, endpoint, is_cost) != ('float', 'sft', cost): raise AssertionError('합성 producer 선택자가 다르다')
            writer = ShardWriter(p.RAW / key, 'updates', limit=19_999_999)
            groups = group_fixture(); events = []
            for step in range(count):
                event = dict(update=step + 1, **p.update_contract('sft', step, frozen),
                    x_tokens=21376 + (268 if not cost and step == 383 else 0),
                    ce=1., native_replay_ce=1., gradient_norm=2., clipped=True,
                    step_seconds=.1, actual_lrs=p.actual_lrs(groups))
                writer.append(event); events.append(event)
            reference = p.digest(p.CACHE / 'frozen_reference.json')
            lineage = dict(tag=p.TAG, arm='float', endpoint='sft', cost=cost, reference_sha256=reference)
            manifest = writer.close(lineage=lineage)
            receipt = dict(mode='float', metadata=route.route_metadata('float'), tlinear_instances=1,
                owned_tlinear_instances=1, refreshed_tlinear_instances=1,
                forward_methods=['_guarded_forward'], refresh_methods=['_float_refresh'])
            cache = (dict(quality_forwards=0, optimizer_updates=0, finite=True,
                core_before='D' * 64, core_after='D' * 64, route=receipt, cache_tensors=1,
                cache_nominal_bytes=4, extra_cache_storage_bytes=0, seconds=.1,
                peak_allocated_mib=1., peak_reserved_mib=1.) if cost else None)
            checkpoint = p.checkpoint('float', 'sft')
            if not cost:
                with checkpoint.open('xb') as stream: stream.write(b'synthetic metadata marker; not checkpoint tensors')
            report = dict(p.info(), status='COST_COMPLETE' if cost else 'TRAIN_COMPLETE',
                arm='float', endpoint='sft', cost=cost, updates=count, reference_sha256=reference,
                scratch_core_sha256='A' * 64, initial_core_sha256=d.PARENT_CORE,
                final_core_sha256='D' * 64, parent_checkpoint_sha256=d.PARENT_SHA,
                parent_core_sha256=d.PARENT_CORE, actual_optimizer_groups=groups,
                quantization_route=route.route_metadata('float'), route=receipt, event_manifest=manifest,
                step_seconds=[.1] * count, totals={k: sum(event[k] for event in events) for k in
                    ('targets', 'x_tokens', 'native_replay_targets')}, max_preclip_gradient=2.,
                clip_events=count, late_probe=None, cache_audit=cache, optimizer_saved=False,
                checkpoint_writes=0 if cost else 1,
                checkpoint=None if cost else str(checkpoint.relative_to(root)),
                checkpoint_sha256=None if cost else p.digest(checkpoint),
                native32_fp32=None if cost else dict(ce=1., targets=32768, windows=32,
                    val_sha256=p.VAL_SHA, precision='FP32_MATH'))
            p.write(p.result_path(key), report)
            # 고장 원형: report가 존재해도 아직 현재 activity가 없으므로 real reader는 Pending이다.
            try: p.train_report('sft_cost' if cost else 'sft', 'float')
            except p.Pending: observations['pending_before_close'] = True
            else: raise AssertionError('닫히지 않은 현재 worker를 먼저 완료로 읽었다')
            return 0
        p.train = produce
        class FixedClock(datetime):
            @classmethod
            def now(cls, tz=None):
                return datetime(2026, 10, 20, 12, tzinfo=timezone.utc)
        with patch.object(d, 'datetime', FixedClock), patch.object(d.os, 'getpid', return_value=7), patch.object(d.os, 'getpgid', return_value=7):
            yield types.SimpleNamespace(p=p, key=key, count=count, cost=cost, observations=observations, env=env)


class NSTests(unittest.TestCase):
    def test_headwise_matches_independent_2d_reference_and_preserves_shape_dtype(self):
        gradient = param((6, 8)).detach()
        expected = torch.stack([d.original_ns(head) for head in gradient.reshape(3, 2, 8)]).reshape_as(gradient)
        actual = d.headwise_ns(gradient, 3, 2)
        self.assertTrue(torch.equal(actual, expected))
        self.assertEqual(actual.shape, gradient.shape)
        self.assertEqual(actual.dtype, gradient.dtype)

    def test_head_permutation_and_independent_scale_do_not_mix_other_heads(self):
        gradient = param((6, 8)).detach().reshape(3, 2, 8)
        base = d.headwise_ns(gradient.reshape(6, 8), 3, 2).reshape_as(gradient)
        perm = [2, 0, 1]
        actual = d.headwise_ns(gradient[perm].reshape(6, 8), 3, 2).reshape_as(gradient)
        self.assertTrue(torch.equal(actual, base[perm]))
        altered = gradient.clone(); altered[1] *= 8
        scaled = d.headwise_ns(altered.reshape(6, 8), 3, 2).reshape_as(gradient)
        self.assertTrue(torch.equal(scaled[[0, 2]], base[[0, 2]]))
        self.assertTrue(torch.equal(scaled[1], base[1]))

    def test_tall_heads_use_last_two_axes_and_zero_head_remains_zero(self):
        gradient = param((16, 2)).detach(); gradient[:8].zero_()
        expected = torch.stack([d.original_ns(head) for head in gradient.reshape(2, 8, 2)]).reshape_as(gradient)
        self.assertTrue(torch.equal(d.headwise_ns(gradient, 2, 8), expected))
        self.assertEqual(torch.count_nonzero(d.headwise_ns(gradient, 2, 8)[:8]).item(), 0)

    def test_invalid_3d_shape_steps_and_eps_rejected(self):
        for gradient, heads, dim, kwargs in ((torch.zeros(2, 2, 3), 2, 2, {}),
                (torch.zeros(4, 3), 3, 2, {}), (torch.zeros(4, 3), 2, 2, {'steps': 4}),
                (torch.zeros(4, 3), 2, 2, {'eps': 1e-6})):
            with self.subTest(shape=gradient.shape), self.assertRaises(ValueError):
                d.headwise_ns(gradient, heads, dim, **kwargs)

    def test_non_targets_are_bit_identical_to_product_muon_over_momentum_steps(self):
        for nesterov in (True, False):
            left, right = param((4, 6)), param((4, 6))
            control = d.Muon([left], lr=2e-4, momentum=.95, nesterov=nesterov, scale_mode='rms')
            changed = d.HeadwiseMuon([right], [], lr=2e-4, momentum=.95, nesterov=nesterov, scale_mode='rms')
            for step in range(4):
                gradient = param((4, 6), step).detach()
                left.grad, right.grad = gradient.clone(), gradient.clone()
                control.step(); changed.step()
                self.assertTrue(torch.equal(left, right))
                self.assertTrue(torch.equal(control.state[left]['buf'], changed.state[right]['buf']))

    def test_target_update_uses_original_2d_rms_scale_not_head_shape_scale(self):
        parameter = param((16, 2)); before = parameter.detach().clone(); gradient = param((16, 2), 9).detach()
        opt = d.HeadwiseMuon([parameter], [d.HeadSpec('target', parameter, 2, 8, 2)],
            lr=2e-4, scale_mode='rms', momentum=.95, nesterov=True)
        parameter.grad = gradient.clone()
        update = d.headwise_ns(gradient.add(gradient, alpha=.95), 2, 8)
        expected = before.clone().add_(update, alpha=-2e-4 * d.update_scale(16, 2, 'rms'))
        opt.step()
        self.assertTrue(torch.equal(parameter, expected))
        self.assertEqual(opt.headwise_counts, {'target': 1})
        self.assertEqual(type(opt).__name__, 'HeadwiseMuon')

    def test_original_ns_only_receives_2d_nontargets(self):
        target, other = param((4, 6)), param((4, 6), 3)
        opt = d.HeadwiseMuon([target, other], [d.HeadSpec('q', target, 2, 2, 6)], scale_mode='rms')
        target.grad = torch.ones_like(target); other.grad = torch.ones_like(other)
        original = d.original_ns
        with patch.object(d, 'original_ns', wraps=original) as ns:
            opt.step()
        self.assertEqual(ns.call_count, 1)
        self.assertEqual(ns.call_args.args[0].ndim, 2)

    def test_duplicate_targets_owners_wrong_shape_and_fp16_master_rejected(self):
        p = param((4, 6)); spec = d.HeadSpec('q', p, 2, 2, 6)
        with self.assertRaises(ValueError): d.HeadwiseMuon([p], [spec, spec])
        with self.assertRaises(ValueError): d.HeadwiseMuon([p], [d.HeadSpec('q', p, 3, 2, 6)])
        with self.assertRaises(ValueError): d.HeadwiseMuon([p, p], [spec])
        with self.assertRaises(ValueError): d.HeadwiseMuon([torch.nn.Parameter(torch.ones(2, 3, dtype=torch.float16))], [])


class OwnershipTests(unittest.TestCase):
    def test_exact_q14_and_kowner7_zero_storage_geometry(self):
        model = metadata_model(); specs = d.collect_targets(model)
        self.assertEqual(len(specs), 21)
        self.assertEqual(sum(spec.name.endswith('q_proj.weight') for spec in specs), 14)
        self.assertEqual(sum(spec.name.endswith('k_proj.weight') for spec in specs), 7)
        self.assertTrue(all(spec.parameter.device.type == 'meta' for spec in specs))
        self.assertEqual(len({id(spec.parameter) for spec in specs}), 21)

    def test_cfg_cla_owner_and_module_cfg_identity_changes_rejected(self):
        for kind in ('edges', 'attn', 'owner', 'cfg'):
            with self.subTest(kind=kind):
                model = metadata_model()
                if kind == 'edges': model.cfg.cla_edges = False
                elif kind == 'attn': model.cfg.attn_group = 2
                elif kind == 'owner': model.owner[1] = 1
                else: model.layers[0].attn.q_proj.cfg = deepcopy(model.cfg)
                with self.assertRaises(ValueError): d.collect_targets(model)

    def test_registered_parameter_alias_and_nonowner_k_are_rejected(self):
        model = metadata_model(); model.layers[1].attn.q_proj.weight = model.layers[0].attn.q_proj.weight
        with self.assertRaises(ValueError): d.collect_targets(model)
        model = metadata_model(); model.layers[1].attn.k_proj = model.layers[0].attn.k_proj
        with self.assertRaises(ValueError): d.collect_targets(model)

    def test_target_dtype_or_3d_matrix_is_rejected(self):
        for kind in ('dtype', 'shape'):
            with self.subTest(kind=kind):
                model = metadata_model()
                model.layers[0].attn.q_proj.weight = torch.nn.Parameter(torch.empty(
                    (768, 768) if kind == 'dtype' else (12, 64, 768), device='meta',
                    dtype=torch.float16 if kind == 'dtype' else torch.float32))
                with self.assertRaises(ValueError): d.collect_targets(model)


class ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.p = d.build_runtime()
    def tearDown(self): self.p._headwise.check()

    def test_all_pinned_code_and_frozen_native_bodies_are_unchanged(self):
        self.assertEqual(set(d.checked_code()), set(d.CODE_PINS))
        for name in d.BODY_NAMES:
            self.assertEqual(utility.body_sha(getattr(self.p, name)), utility.body_sha(getattr(self.p._headwise.original, name)))
            self.assertIs(inspect.unwrap(getattr(self.p, name)).__globals__, vars(self.p))

    def test_info_full_serialization_has_real_parent_baseline_clip1_and_counts(self):
        value = json.loads(json.dumps(self.p.info(), allow_nan=False))
        self.assertEqual(value['clip'], 1.)
        self.assertEqual(value['actual_parent_checkpoint_sha256'], d.PARENT_SHA)
        self.assertEqual(value['actual_baseline_checkpoint_sha256'], d.BASELINE_SHA)
        self.assertEqual(value['sft_actual_totals'], d.TOTALS)
        self.assertEqual(value['headwise_class'], 'HeadwiseMuon')
        self.assertEqual(len(value['headwise_targets']), 21)
        self.assertEqual(value['new_native_updates'], 0)
        self.assertTrue(value['code_complete'])

    def test_source_parent_and_baseline_globals_dates_stay_original(self):
        self.assertEqual(self.p._headwise.original.TAG, 'p106b_native_weight_route_v1_s1337')
        self.assertEqual(self.p._headwise.original.END.isoformat(), '2026-10-20T08:00:00+00:00')
        self.assertEqual(self.p._headwise.baseline.TAG, 'p106b_native_resume_v2_s1337')
        self.assertEqual(self.p.END, d.END)

    def test_fake_muon_name_or_wrong_actual_class_is_rejected(self):
        groups = group_fixture(); d.validate_headwise_groups(groups)
        for key, value in (('optimizer', 'Muon'), ('actual_class', 'fixture.Muon'), ('lr', 4e-4),
                           ('names_sha256', 'F' * 64), ('weight_decay', .1)):
            bad = deepcopy(groups); bad[2][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError): d.validate_headwise_groups(bad)

    def test_source_latepass_counts_offsets_and_case_identity_corruption_rejected(self):
        for kind in ('counts', 'denominator', 'offsets', 'cases'):
            frozen, cases = source_fixture(); d.source_contract(frozen, cases)
            if kind == 'counts': frozen['exposure']['varied_balanced'][3]['counts']['x_tokens'] += 1
            elif kind == 'denominator': frozen['exposure']['varied_balanced'][3]['update_target_denominators'][-1] += 1
            elif kind == 'offsets': frozen['native_train_offsets'].pop()
            else: cases[-1]['id'] = cases[0]['id']
            with self.subTest(kind=kind), self.assertRaises(ValueError): d.source_contract(frozen, cases)

    def test_locked_control_clip8_wrong_parent_or_tokens_rejected(self):
        parent, control = locked_reports(); d.validate_locked_reports(parent, control)
        for key, value in (('clip', 8.), ('parent_checkpoint_sha256', 'F' * 64), ('initial_core_sha256', 'F' * 64),
                           ('totals', dict(d.TOTALS, targets=302655)), ('checkpoint_sha256', d.PARENT_SHA)):
            bad = deepcopy(control); bad[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError): d.validate_locked_reports(parent, bad)

    def test_private_unapproved_binding_or_train_replacement_is_detected(self):
        try:
            self.p.arbitrary_loader = object()
            with self.assertRaises(ValueError): self.p._headwise.check()
        finally: del self.p.arbitrary_loader
        before = self.p.train
        try:
            self.p.train = lambda *args: 0
            with self.assertRaises(ValueError): self.p._headwise.check()
        finally: self.p.train = before

    def test_captured_loader_and_audit_provider_cannot_be_rebound(self):
        with self.assertRaises(TypeError): self.p._headwise.captured['routed_runtime'] = lambda: None
        with self.assertRaises(AttributeError): self.p._headwise.baseline = object()
        reader = self.p._headwise.baseline_reader
        before = reader.diagonal.__code__
        try:
            reader.diagonal.__code__ = (lambda: None).__code__
            with self.assertRaisesRegex(ValueError, 'reader의 본문'): self.p._headwise.check()
        finally: reader.diagonal.__code__ = before

    def test_cli_all_children_new_script_no_baseline_training_or_unused_proof(self):
        for mode in d.MODES:
            phases = d.phase_commands(mode, 600)
            for _, command in phases[1:]:
                self.assertEqual(command.count(d.SCRIPT), 1)
                self.assertNotIn(d.SOURCE, command)
        with self.assertRaises(ValueError): d.phase_commands('train', 600, Path('/tmp/unused'))
        for args in (('native', 600), ('train', 59), ('cost', 3601)):
            with self.assertRaises(ValueError): d.phase_commands(*args)

    def test_check_only_reads_no_report_or_asset_and_writes_nothing(self):
        with patch.object(d, 'build_runtime', return_value=self.p), patch.object(d, 'worker') as worker, redirect_stdout(io.StringIO()):
            self.assertEqual(d.main(['--mode', 'cost', '--check-only']), 0)
        worker.assert_not_called()

    def test_public_check_only_full_info_matches_imported_controller(self):
        child = subprocess.run([sys.executable, '-B', '-X', 'utf8', d.SCRIPT, '--mode', 'source', '--check-only'],
            cwd=ROOT, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=30)
        self.assertEqual(child.returncode, 0, child.stderr)
        actual = json.loads(child.stdout.split('] ', 1)[1])
        self.assertEqual(actual, self.p.info())

    def test_complete_production_info_prepare_and_prepared_roundtrip_in_temp(self):
        with worker_fixture() as p:
            source_reference = dict(display_ids=['synthetic'])
            frozen, cases = source_fixture(); binding = d.source_contract(frozen, cases)
            state = lambda: (source_reference, frozen, cases, [], binding)
            prepare = closure_fixture(self.p.prepare, p=p, source_state=state, info=self.p.info)
            prepared = closure_fixture(self.p.prepared, p=p, source_state=state, info=self.p.info)
            p.completed_activity = Mock(return_value={'fixture': True})
            self.assertEqual(prepare(), 0)
            value, observed, *_ = prepared()
            self.assertIs(observed, frozen)
            self.assertGreater(len(value), 65)
            self.assertEqual(value['clip'], 1.)
            self.assertEqual(value['actual_parent_checkpoint_sha256'], d.PARENT_SHA)
            p.completed_activity.assert_called_once_with('prepare')
            with self.assertRaises(FileExistsError): prepare()
            saved = p.required(p.CACHE / 'frozen_reference.json'); saved['binding']['cases_sha256'] = 'F' * 64
            with (p.CACHE / 'frozen_reference.json').open('w') as stream: json.dump(saved, stream)
            with self.assertRaises(ValueError): prepared()

    def test_headwise_cp_experiment_has_new_method_and_float_strict_guard(self):
        from dataclasses import dataclass, asdict
        @dataclass
        class Cfg:
            max_seq_len: int = 1024
        report = dict(arm='float', endpoint='sft', updates=384, reference_sha256='A' * 64,
            scratch_core_sha256='B' * 64, parent_checkpoint_sha256=d.PARENT_SHA,
            parent_core_sha256=d.PARENT_CORE, final_core_sha256='C' * 64)
        expected = self.p.cp_experiment(report)
        _, _, route = self.p.modules()
        saved = dict(model={}, cfg=asdict(Cfg()), step=384, tokenizer_sha256=self.p.TOKENIZER_SHA,
            tokenizer_lineage='chat32', quantization_route=route.route_metadata('float'), experiment=expected)
        self.p.validate_payload(saved, Cfg(), 'float', 'sft', expected)
        bad = deepcopy(saved); bad['experiment']['tag'] = 'p106b_native_resume_v2_s1337'
        with self.assertRaises(ValueError): self.p.validate_payload(bad, Cfg(), 'float', 'sft', expected)
        bad = deepcopy(saved); bad['experiment']['headwise_method_sha256'] = 'F' * 64
        with self.assertRaises(ValueError): self.p.validate_payload(bad, Cfg(), 'float', 'sft', expected)
        with self.assertRaises(RuntimeError): route.generic_loader_guard(saved)

    def test_masked_positive_owner_l0_denominator_and_nontarget_gradient_are_unchanged(self):
        from tinylm.train.mtp_sft import components
        class Head(torch.nn.Module):
            def __init__(self):
                super().__init__(); self.weight = param((4, 6))
            def _head_logits(self, hidden): return torch.nn.functional.linear(hidden, self.weight)
        left, right = Head(), Head()
        hidden = param((1, 3, 6)).detach().requires_grad_()
        y = torch.tensor([[-100, 1, 2]]); owners = torch.tensor([[1, 1, 1]])
        values, counts = components(left, hidden, y, owners, horizons=(), checkpoint_heads=False)
        other, other_counts = components(right, hidden.clone(), y, owners, horizons=(), checkpoint_heads=False)
        self.assertEqual(counts, {1: 2}); self.assertEqual(counts, other_counts)
        (values[1] / 2).backward(); (other[1] / 2).backward()
        self.assertTrue(torch.equal(left.weight.grad, right.weight.grad))
        d.Muon([left.weight], lr=2e-4, scale_mode='rms').step()
        d.HeadwiseMuon([right.weight], [], lr=2e-4, scale_mode='rms').step()
        self.assertTrue(torch.equal(left.weight, right.weight))

    def test_actual_q14_k7_update_counters_and_missing_gradient_cannot_pass(self):
        specs = []
        for index, row in enumerate(d.target_geometry()):
            parameter = param((4, 6), index)
            specs.append(d.HeadSpec(row['name'], parameter, 2, 2, 6))
        opt = d.HeadwiseMuon([spec.parameter for spec in specs], specs, lr=2e-4, scale_mode='rms')
        before = self.p._headwise.state['optimizers']
        try:
            self.p._headwise.state['optimizers'] = (None, opt)
            for _ in range(8):
                for spec in specs: spec.parameter.grad = torch.ones_like(spec.parameter)
                opt.step()
            stats = self.p._headwise.execution_stats(8)
            self.assertEqual(stats['target_counts'], {row['name']: 8 for row in d.target_geometry()})
            self.assertEqual(stats['optimizer'], 'HeadwiseMuon')
            opt.headwise_counts[specs[0].name] -= 1
            with self.assertRaises(ValueError): self.p._headwise.execution_stats(8)
        finally: self.p._headwise.state['optimizers'] = before


class IdleTests(unittest.TestCase):
    def proof(self):
        now = datetime(2026, 10, 20, 12, tzinfo=timezone.utc)
        return now, dict(schema='P106B_ROOT_IDLE_V1', tag=d.TAG, code_sha256={'fixture': 'A' * 64},
            start_utc=(now - timedelta(seconds=310)).isoformat(), end_utc=(now - timedelta(seconds=10)).isoformat(),
            start_monotonic=1000., end_monotonic=1300., no_gpu_work=True, no_heavy_cpu=True,
            evidence=[dict(path='test_result/idle_fixture.txt', sha256='B' * 64)])

    def test_both_clocks300_and_fresh600_are_required_not_peak_safety(self):
        now, proof = self.proof()
        value = d.idle_receipt(proof, proof['code_sha256'], now=now, monotonic=1310.)
        self.assertIn('NOT_CONTINUOUS_PEAK', value['scope'])
        for key, value in (('start_monotonic', 1001.), ('start_utc', (now - timedelta(seconds=309)).isoformat()),
                           ('tag', 'other'), ('no_gpu_work', False), ('no_heavy_cpu', False), ('evidence', [])):
            bad = deepcopy(proof); bad[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                d.idle_receipt(bad, proof['code_sha256'], now=now, monotonic=1310.)

    def test_stale_future_nan_or_different_source_proof_rejected(self):
        now, proof = self.proof()
        for current, mono, code in ((now + timedelta(seconds=601), 1310., proof['code_sha256']),
                (now, 1901., proof['code_sha256']), (now, 1299., proof['code_sha256']),
                (now, float('nan'), proof['code_sha256']), (now, 1310., {})):
            with self.assertRaises(ValueError): d.idle_receipt(proof, code, now=current, monotonic=mono)

    def test_evidence_protected_external_or_bad_hash_is_rejected_without_read(self):
        now, proof = self.proof()
        for path in ('datasets/TinyDataset/private.txt', '/tmp/outside', '.aws/credentials', '../outside'):
            bad = deepcopy(proof); bad['evidence'][0]['path'] = path
            with self.subTest(path=path), self.assertRaises(ValueError):
                d.idle_receipt(bad, proof['code_sha256'], now=now, monotonic=1310.)


class BudgetTests(unittest.TestCase):
    def test_first_worst_warm_existing135_and_measured_eval_prepare_reserves(self):
        value = d.resource_forecast([10.] + [2.] * 7, 162., 20., 40., 10000., 10000.)
        expected = 10 + 2 * 383 * 1.35 + 300
        self.assertEqual(value['estimates_seconds']['float_sft'], expected)
        self.assertEqual(value['evaluation_reserve_seconds'], 162 * 1.35)
        self.assertEqual(value['readback_reserve_seconds'], 20 * 1.35)
        self.assertEqual(value['needed_seconds'], expected + 162 * 1.35 + 20 * 1.35 + 600)
        self.assertTrue(value['fits'])

    def test_family_or_trainstop_or_end_limit_never_becomes_quality_failure(self):
        for spent, training, total in ((3500., 10000., 10000.), (0., 1., 10000.), (0., 10000., 1.)):
            self.assertFalse(d.resource_forecast([10.] + [2.] * 7, 162., 20., spent, training, total)['fits'])
        with self.assertRaises(ValueError): d.resource_forecast([float('nan')] * 8, 1., 1., 0., 10000., 10000.)

    def test_completed_training_is_not_reforecast_or_recounted_as_new(self):
        value = d.resource_forecast([10.] + [2.] * 7, 162., 20., 1000., 10000., 10000., completed=True)
        self.assertEqual(value['estimates_seconds']['float_sft'], 0.)
        self.assertEqual(value['spent_seconds'], 1000.)


class WorkerTests(unittest.TestCase):
    def test_successful_prepare_receipt_binds_real_report_and_reference(self):
        with worker_fixture() as p, patch.object(d.os, 'getpid', return_value=7), patch.object(d.os, 'getpgid', return_value=7):
            self.assertEqual(d.worker(p, 'prepare', 60), 0)
            value = p.required(p.EVIDENCE / 'activity_prepare.json')
            self.assertTrue(value['complete'])
            self.assertEqual(value['result_sha256'], p.digest(p.result_path('prepare')))
            self.assertEqual(value['reference_sha256'], p.digest(p.CACHE / 'frozen_reference.json'))

    def test_term_failure130_preserves_partial_and_handler(self):
        with worker_fixture() as p, patch.object(d.os, 'getpid', return_value=7), patch.object(d.os, 'getpgid', return_value=7):
            before = signal.getsignal(signal.SIGTERM)
            p.prepare = lambda: signal.raise_signal(signal.SIGTERM)
            with self.assertRaises(KeyboardInterrupt): d.worker(p, 'prepare', 60)
            value = p.required(p.EVIDENCE / 'activity_prepare.json')
            self.assertEqual(value['returncode'], 130)
            self.assertFalse(value['complete'])
            self.assertIs(signal.getsignal(signal.SIGTERM), before)

    def test_family_record_reserve_and_own_pgid_before_compute(self):
        with worker_fixture() as p, patch.object(d.os, 'getpid', return_value=7), patch.object(d.os, 'getpgid', return_value=7):
            p.spent_seconds = lambda: 3000.
            p.prepare = Mock()
            with self.assertRaises(p.Pending): d.worker(p, 'prepare', 60)
            p.prepare.assert_not_called()
        with worker_fixture() as p, patch.object(d.os, 'getpid', return_value=7), patch.object(d.os, 'getpgid', return_value=8):
            with self.assertRaises(ValueError): d.worker(p, 'prepare', 60)

    def test_actual_activity_and_report_are_write_once(self):
        with worker_fixture() as p, patch.object(d.os, 'getpid', return_value=7), patch.object(d.os, 'getpgid', return_value=7):
            d.worker(p, 'prepare', 60)
            before = p.digest(p.EVIDENCE / 'activity_prepare.json')
            with self.assertRaises(FileExistsError): d.worker(p, 'prepare', 60)
            self.assertEqual(before, p.digest(p.EVIDENCE / 'activity_prepare.json'))

    def test_source_drift_after_worker_body_is_error_not_complete(self):
        with worker_fixture() as p, patch.object(d.os, 'getpid', return_value=7), patch.object(d.os, 'getpgid', return_value=7):
            metadata = p.info(); changed = deepcopy(metadata); changed['code_sha256'] = {'changed': 'F' * 64}
            p.info = Mock(side_effect=[metadata, changed])
            with self.assertRaisesRegex(ValueError, 'source SHA'): d.worker(p, 'prepare', 60)
            self.assertFalse(p.required(p.EVIDENCE / 'activity_prepare.json')['complete'])

    def test_finish_cost_writes_linked_actual_optimizer_receipt_and_no_checkpoint_path(self):
        with worker_fixture() as p:
            stats = dict(optimizer='HeadwiseMuon', actual_class='scripts.diag_p106b_headwise_muon.HeadwiseMuon',
                steps=8, target_counts={row['name']: 8 for row in d.target_geometry()},
                target_geometry_sha256=d.sha(d.target_geometry()), all_target_updates_verified=True)
            def cost(arm, endpoint, is_cost, cap):
                self.assertEqual((arm, endpoint, is_cost, cap), ('float', 'sft', True, 60))
                p.write(p.result_path('cost'), {'synthetic_cost': True})
                return 0
            p.train = Mock(side_effect=cost)
            p.train_report = lambda *args: (_ for _ in ()).throw(AssertionError('finish에서 현재 activity reader를 부르면 안 된다'))
            p.checkpoint = Mock(side_effect=AssertionError('costCP0'))
            p._headwise.execution_stats = lambda count: stats if count == 8 else None
            self.assertEqual(d.finish_training(p, cost=True, max_wall_sec=60), 0)
            receipt = p.required(p.EVIDENCE / 'headwise_cost.json')
            self.assertEqual(receipt['report_sha256'], p.digest(p.result_path('cost')))
            self.assertEqual(receipt['target_counts'], stats['target_counts'])
            p.checkpoint.assert_not_called()
            self.assertIsNone(p._headwise.state['optimizers'])

    def test_excluded_source_preflight_ignore_family_2450_and_fixed600_cap(self):
        for mode in ('source', 'preflight'):
            with self.subTest(mode=mode), worker_fixture() as p, patch.object(d.os, 'getpid', return_value=7), patch.object(d.os, 'getpgid', return_value=7):
                p.spent_seconds = Mock(return_value=2450.)
                self.assertEqual(d.worker(p, mode, 600), 0)
                p.spent_seconds.assert_not_called()
                self.assertFalse(p.EVIDENCE.exists())


class ClosedWorkerVerificationTests(unittest.TestCase):
    def test_real_cost8_and_train384_readers_require_closed_activity_then_verify(self):
        for cost in (True, False):
            with self.subTest(cost=cost), strict_training_fixture(cost) as f, redirect_stdout(io.StringIO()):
                with self.assertRaises(f.p.Pending):
                    f.p.train_report('sft_cost' if cost else 'sft', 'float')
                self.assertEqual(d.worker(f.p, f.key, 60), 0)
                self.assertTrue(f.observations['pending_before_close'])
                self.assertEqual(f.observations['raw_reads'], [])
                activity = f.p.required(f.p.EVIDENCE / ('activity_' + f.key + '.json'))
                self.assertTrue(activity['complete'])
                self.assertEqual(activity['returncode'], 0)
                # VERIFY 제외대상은 family가 거의 소진돼도 strict reader를 실제로 끝낸다.
                f.p.spent_seconds = Mock(return_value=3599.)
                self.assertEqual(d.verify_training(f.p, f.key, 600), 0)
                f.p.spent_seconds.assert_not_called()
                self.assertEqual(f.observations['raw_reads'], [f.count])
                self.assertEqual(f.p.checkpoint('float', 'sft').exists(), not cost)

    def test_worker0_raw_corruption_verify9_keeps_actual_execution_and_final_error(self):
        for cost in (True, False):
            with self.subTest(cost=cost), strict_training_fixture(cost) as f, redirect_stdout(io.StringIO()) as output:
                calls = []
                def launch(command, timeout):
                    if '--mode' not in command: return 0
                    mode = command[command.index('--mode') + 1]
                    if mode == 'preflight': return 0
                    if '--worker' in command:
                        calls.append('worker')
                        self.assertEqual(d.worker(f.p, mode, 60), 0)
                        raw = f.p.RAW / f.key / 'updates_000000.jsonl'
                        with raw.open('ab') as stream: stream.write(b' ')
                        return 0
                    if '--verify-only' in command:
                        calls.append('verify')
                        try: return d.verify_training(f.p, mode, 60)
                        except d.VerificationError: return 9
                    raise AssertionError('등록되지 않은 합성 child다')
                f.p.launch = launch
                phases = d.phase_commands(f.key, 60)
                result = f.p.pipeline(phases, lambda command: d.launch_stage(f.p, command, 60), print,
                    experiment='HEADWISE_CPU_POST_VERIFY_FIXTURE')
                self.assertEqual(calls, ['worker', 'verify'])
                self.assertEqual(result['status'], 'ERROR')
                self.assertEqual(result['returncode'], 9)
                self.assertTrue(result['main_experiment_invoked'])
                record = f.p.required(f.p.EVIDENCE / ('activity_' + f.key + '.json'))
                self.assertTrue(record['complete'])
                self.assertEqual(record['returncode'], 0)
                self.assertTrue((f.p.RAW / f.key / 'updates_000000.jsonl').read_bytes().endswith(b' '))
                self.assertTrue((f.p.EVIDENCE / ('headwise_' + f.key + '.json')).is_file())
                composite = [json.loads(line.split('] ', 1)[1]) for line in output.getvalue().splitlines()
                    if line.startswith('[HEADWISE_EXECUTE_VERIFY_FINAL]')][-1]
                self.assertEqual(composite['worker_returncode'], 0)
                self.assertTrue(composite['worker_completed'])
                self.assertEqual(composite['verification_returncode'], 9)
                self.assertEqual(composite['status'], 'EXECUTED_VERIFY_FAILED')
                self.assertIn('[VERIFY_BEGIN]', output.getvalue())
                self.assertIn('[VERIFY_END]', output.getvalue())

    def test_three_phase_pipeline_completes_only_after_real_strict_verify(self):
        with strict_training_fixture(True) as f, redirect_stdout(io.StringIO()):
            calls = []
            def launch(command, timeout):
                if '--verify-only' in command:
                    calls.append('verify')
                    return d.verify_training(f.p, 'cost', 60)
                if '--mode' in command and command[command.index('--mode') + 1] == 'cost':
                    calls.append('worker')
                    return d.worker(f.p, 'cost', 60)
                return 0
            f.p.launch = launch
            phases = d.phase_commands('cost', 60)
            self.assertEqual([phase[0] for phase in phases], ['REGRESSION', 'PREFLIGHT', 'EXECUTE'])
            result = f.p.pipeline(phases, lambda command: d.launch_stage(f.p, command, 60), print,
                experiment='HEADWISE_CPU_CLOSED_VERIFY')
            self.assertEqual(calls, ['worker', 'verify'])
            self.assertEqual(result['status'], 'COMPLETE')
            self.assertEqual(f.observations['raw_reads'], [8])

    def test_failed_worker_or_regression_preflight_never_spawn_verifier(self):
        for command, code in ((d.phase_commands('cost', 60)[-1][1], 8),
                (d.phase_commands('cost', 60)[0][1], 0), (d.phase_commands('cost', 60)[1][1], 0)):
            p = types.SimpleNamespace(launch=Mock(return_value=code), execution_remaining=lambda: 100000.,
                spent_seconds=Mock(return_value=2450.))
            with redirect_stdout(io.StringIO()): self.assertEqual(d.launch_stage(p, command, 60), code)
            self.assertEqual(p.launch.call_count, 1)
            self.assertNotIn('--verify-only', p.launch.call_args.args[0])
            p.spent_seconds.assert_not_called()

    def test_missing_closed_activity_pending_is_verification_error_not_hold(self):
        with strict_training_fixture(True) as f, redirect_stdout(io.StringIO()):
            with self.assertRaises(d.VerificationError) as caught: d.verify_training(f.p, 'cost', 60)
            self.assertIsInstance(caught.exception.__cause__, f.p.Pending)

    def test_verify_deadline_failure_after_worker0_is_error_and_no_fake_completion(self):
        p = types.SimpleNamespace(launch=Mock(return_value=0), execution_remaining=Mock(side_effect=[1000., 59.]))
        with redirect_stdout(io.StringIO()):
            self.assertEqual(d.launch_stage(p, d.phase_commands('train', 60)[-1][1], 60), 9)
        self.assertEqual(p.launch.call_count, 1)

    def test_readonly_still_obeys_absolute_cap_and_own_pgid(self):
        with strict_training_fixture(True) as f, redirect_stdout(io.StringIO()):
            f.p.execution_remaining = lambda *args: 59.
            with self.assertRaises(d.VerificationError): d.verify_training(f.p, 'cost', 60)
            f.p.execution_remaining = lambda *args: 100000.
            with patch.object(d.os, 'getpgid', return_value=8):
                with self.assertRaises(d.VerificationError): d.verify_training(f.p, 'cost', 60)
        with worker_fixture() as p, patch.object(d.os, 'getpid', return_value=7), patch.object(d.os, 'getpgid', return_value=7):
            p.execution_remaining = lambda *args: 59.
            p.source_state = Mock()
            with self.assertRaises(p.Pending): d.worker(p, 'source', 60)
            p.source_state.assert_not_called()


class QueryStrataTests(unittest.TestCase):
    def case(self, index, family, query, query_id, split='TRAIN', op=None, lane='coded'):
        return dict(id=str(index), lane=lane, split=split, language='ko', family=family,
            problem=dict(query=query, query_id=query_id, state={'op': op} if op else {}))

    def test_subject_format_key_arithmetic_op_and_train_test_remain_separate(self):
        cases = [
            self.case(0, 'lookup', {'subject': 'A', 'attribute': 'color'}, 'lookup_A'),
            self.case(1, 'lookup', {'subject': 'B', 'attribute': 'color'}, 'lookup_B'),
            self.case(2, 'format', {'key': 'left'}, 'format_query'),
            self.case(3, 'format', {'key': 'right'}, 'format_query'),
            self.case(4, 'arithmetic', {'kind': 'result'}, 'arithmetic_query', op='+'),
            self.case(5, 'arithmetic', {'kind': 'result'}, 'arithmetic_query', op='-'),
            self.case(6, 'lookup', {'subject': 'A', 'attribute': 'color'}, 'same_split_query', split='TRAIN'),
            self.case(7, 'lookup', {'subject': 'A', 'attribute': 'color'}, 'same_split_query', split='TEST'),
            self.case(8, 'lookup', {'subject': 'A', 'attribute': 'color'}, 'same_split_query', split='TRAIN', lane='other'),
        ]
        left = [dict(id=case['id'], metrics={'correct': False}) for case in cases]
        right = [dict(id=case['id'], metrics={'correct': True}) for case in cases]
        rows = d.query_strata(cases, left, right)
        self.assertEqual(len(rows), len(cases))
        self.assertTrue(all(row['n'] == 1 and row['headwise_only'] == 1 for row in rows))
        self.assertEqual({row['arithmetic_op'] for row in rows if row['family'] == 'arithmetic'}, {'+', '-'})
        self.assertEqual({row['canonical_query']['subject'] for row in rows if row['family'] == 'lookup'}, {'A', 'B'})
        self.assertEqual({row['canonical_query']['key'] for row in rows if row['family'] == 'format'}, {'left', 'right'})
        self.assertEqual({row['split'] for row in rows if row['query_id'] == 'same_split_query'}, {'TRAIN', 'TEST'})

    def test_missing_query_id_is_explicit_case_fallback_and_order_is_checked(self):
        cases = [self.case(i, 'user', {}, None) for i in range(2)]
        answers = [dict(id=case['id'], metrics={'correct': None}) for case in cases]
        rows = d.query_strata(cases, answers, answers)
        self.assertEqual(len(rows), 2)
        self.assertEqual({row['fallback_case_id'] for row in rows}, {'0', '1'})
        self.assertTrue(all(row['query_id'] is None and row['scored'] == 0 for row in rows))
        with self.assertRaises(ValueError): d.query_strata(cases, answers[::-1], answers)
        cases[0].update(query_id=None, split=None)
        cases[0]['problem'].update(query_id='actual_source_query', split='TEST')
        observed = d.query_strata(cases, answers, answers)
        actual = next(row for row in observed if row['query_id'] == 'actual_source_query')
        self.assertEqual(actual['split'], 'TEST')
        self.assertIsNone(actual['fallback_case_id'])


if __name__ == '__main__':
    unittest.main()
