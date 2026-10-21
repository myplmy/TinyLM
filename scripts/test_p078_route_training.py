"""Small random-weight CPU-only route/SFT tests; no real data, CP or GPU."""
from __future__ import annotations
import copy
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
import io
import json
from pathlib import Path
import random
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from scripts import p078_route_training as r
r.import_guard()
import torch
from tinylm.config import TMTConfig
from tinylm.model import TiedMLPTransformer
from tinylm.train import mtp_sft as core
torch.set_num_threads(1)
ATOL, RTOL = 1e-5, 1e-4  # Original P070B toy tolerances, never repaired after observation.


def cfg(cap=2):
    return TMTConfig(vocab_size=67, dim=32, ffn_dim=64, n_q_heads=4, n_kv_heads=2, emb_rank=8,
        n_prelude=1, n_middle=8, n_coda=1, mlp_group=2, cla_group=2, micro_group=0,
        train_repeat=float(cap), max_seq_len=32, grad_checkpoint=True, quantize_embedding=False)


def model(arm='uniform_r2'):
    torch.manual_seed(1337); policy = r.Policy(arm)
    result = r.build_model(cfg(policy.cap), policy); result.set_anneal(1.)
    return result


def records(n=128):
    return [core.Record([3, 7, 8, 9], [-100, -100, 9, 4], [0, 0, 1, 1]) for _ in range(n)]


class Routes(unittest.TestCase):
    def setUp(self):
        self.cuda_module = patch.object(torch.nn.Module, 'cuda', side_effect=AssertionError('CPU toy only'))
        self.cuda_tensor = patch.object(torch.Tensor, 'cuda', side_effect=AssertionError('CPU toy only'))
        self.cuda_module.start(); self.cuda_tensor.start()
    def tearDown(self):
        self.cuda_tensor.stop(); self.cuda_module.stop(); self.assertFalse(torch.cuda.is_initialized())
    def test_balanced_counts_match_r2_for_full_and_remainder_schedules(self):
        p = r.Policy('balanced_count'); before = random.getstate()
        for count in (1, 2, 3, 4, 8, 32, 128, 686, 3296):
            sequence = [r.bounded_count(p, i, count, 'val') for i in range(count)]
            self.assertEqual(sum(sequence), 2 * count)
            if count >= 4: self.assertEqual(sorted(sequence[:4]), [1, 2, 2, 3])
            self.assertEqual(sequence, [r.bounded_count(p, i, count, 'val') for i in range(count)])
        self.assertEqual(before, random.getstate())

    def test_atomic_schedule_seed_receipt_and_nonidentity_fixed_shuffle(self):
        m = model(); before = random.getstate(); receipts = []
        for arm in r.ARMS:
            for i in range(8):
                policy = r.Policy(arm); a = r.plan(m.cfg, m.owner, policy, i, 8)
                self.assertEqual(a, r.plan(m.cfg, m.owner, policy, i, 8))
                r.backend().trace(m.cfg, m.owner, a['route']); receipts.append(a)
        self.assertEqual(before, random.getstate())
        fixed = [x for x in receipts if x['arm'] == 'fixed_shuffle_r2']
        self.assertTrue(all(not x['identity_order'] for x in fixed)); self.assertEqual(len({x['route_sha256'] for x in fixed}), 1)
        variable = [x for x in receipts if x['arm'] == 'update_shuffle_r2']
        self.assertGreater(len({x['route_sha256'] for x in variable}), 1)

    def test_uniform_default_logits_and_gradients_equal_product(self):
        m = model(); base = TiedMLPTransformer(copy.deepcopy(m.cfg)); base.load_state_dict(m.state_dict()); base.set_anneal(1.)
        x = torch.tensor([[3, 7, 8, 9]])
        with m.route_scope(0, 1):
            a = m(x); b = base(x); self.assertTrue(torch.equal(a, b))
            a.square().mean().backward(); b.square().mean().backward()
            checked = 0
            for (na, pa), (nb, pb) in zip(m.named_parameters(), base.named_parameters()):
                self.assertEqual(na, nb)
                if pa.grad is None or pb.grad is None: self.assertIs(pa.grad, None); self.assertIs(pb.grad, None)
                else: self.assertTrue(torch.equal(pa.grad, pb.grad), na); checked += 1
            self.assertGreater(checked, 0)

    def test_route_is_locked_through_backward_and_mutated_receipts_rejected(self):
        m = model('update_shuffle_r2'); route = r.backend().schedule(m.cfg, m.owner, 'reverse', 2)
        with m.route_scope(0, 2):
            out = m(torch.tensor([[1, 2, 3]]))
            with self.assertRaises(RuntimeError): m.set_route(route)
            out.sum().backward()
            with self.assertRaises(RuntimeError):
                with m.route_scope(1, 2): pass
        with self.assertRaises(RuntimeError): m(torch.tensor([[1, 2, 3]]))
        with self.assertRaises(RuntimeError):
            with m.route_scope(0, 1):
                m._fixed_route = tuple(route); m(torch.tensor([[1, 2, 3]]))

    def test_causality_and_prefix_input_excludes_all_answer_future_tokens(self):
        record = records(1)[0]; prefix = r.question_prefix(record); changed = copy.deepcopy(record)
        changed.x[3] = 50; changed.y[2:] = [40, 41]
        self.assertEqual(prefix, r.question_prefix(changed)); self.assertEqual(prefix.token_ids, (3, 7, 8))
        m = model('update_shuffle_r2'); m.eval(); x = torch.tensor([[1, 2, 3, 4, 5, 6]])
        with m.route_scope(0, 1, 'val'), torch.no_grad():
            a = m(x); x[:, 3:] += 20; b = m(x)
        self.assertTrue(torch.allclose(a[:, :3], b[:, :3], atol=ATOL, rtol=RTOL))
        with self.assertRaises(NotImplementedError): r.learned_router(prefix)

    def test_cache_session_is_frozen_and_rejects_same_route_old_or_foreign_cache(self):
        m = model(); m.eval(); prefix = r.QuestionPrefix((1, 2, 3)); tokens = torch.tensor([[1, 2, 3, 4, 5]])
        with m.route_scope(0, 1, 'probe', prefix), torch.no_grad():
            full = m(tokens); first, cache = m(tokens[:, :3], use_cache=True); parts = [first]
            with self.assertRaises(RuntimeError): m.set_route(m.visit_schedule())
            for i in (3, 4):
                out, cache = m(tokens[:, i:i + 1], past_kv=cache, use_cache=True); parts.append(out)
            self.assertTrue(torch.allclose(full, torch.cat(parts, 1), atol=ATOL, rtol=RTOL))
            old = cache
        with m.route_scope(0, 1, 'probe', prefix), torch.no_grad():
            with self.assertRaises(ValueError): m(torch.tensor([[6]]), past_kv=old, use_cache=True)
            with self.assertRaises(ValueError): m(torch.tensor([[9, 9, 9]]), use_cache=True)
        other = model(); other.eval()
        with other.route_scope(0, 1, 'probe', prefix), torch.no_grad():
            with self.assertRaises(ValueError): other(torch.tensor([[6]]), past_kv=old, use_cache=True)

    def test_scaled_dense14_quantized_embedding_parent_geometry_and_backward(self):
        policy = r.Policy('balanced_count')
        config = TMTConfig(vocab_size=67, dim=32, ffn_dim=64, n_q_heads=4, n_kv_heads=2, emb_rank=8,
            n_prelude=2, n_middle=10, n_coda=2, mlp_group=2, cla_group=2, micro_group=0,
            tie_mlp=False, train_repeat=3., max_seq_len=32, grad_checkpoint=True, quantize_embedding=True)
        torch.manual_seed(1337); m = r.build_model(config, policy); m.set_anneal(1.)
        self.assertEqual(m.cfg.n_layers, 14)
        counts = [r.plan(m.cfg, m.owner, policy, i, 4) for i in range(4)]
        self.assertEqual(sum(p['visits'] for p in counts), 4 * 24)
        opt = torch.optim.SGD(m.parameters(), lr=.001)
        event = r.sft_update(m, records(103), (opt,), 0, 4, width=4)
        self.assertEqual(event['assistant_targets'], 206); self.assertGreater(event['gradient_max'], 0)

    def test_real_sft_micro8_accum16_tail_zero_gradient_and_optimizer_continuity(self):
        m = model('balanced_count'); opt = torch.optim.SGD(m.parameters(), lr=.01); oid = id(opt)
        before = {k: v.detach().clone() for k, v in m.state_dict().items()}
        events = [r.sft_update(m, records(n), (opt,), i, 4, width=4) for i, n in enumerate((128, 103, 128, 128))]
        self.assertEqual(sorted(e['route']['actual_repeats'] for e in events), [1, 2, 2, 3])
        self.assertEqual(sum(e['route']['visits'] for e in events), 4 * (2 + 2 * 8))
        self.assertTrue(all(e['micro_bs'] == 8 and e['accum'] == 16 and e['optimizer_ids'] == [oid] for e in events))
        self.assertEqual(events[1]['actual_rows'], 103); self.assertEqual(events[1]['dummy_rows'], 25)
        self.assertEqual(events[1]['assistant_targets'], 206); self.assertEqual(events[1]['actual_x_tokens'], 412)
        self.assertTrue(all(e['gradient_max'] > 0 and e['ce'] > 0 for e in events))
        self.assertTrue(any(not torch.equal(before[k], v) for k, v in m.state_dict().items()))
        with self.assertRaises(ValueError): r.sft_update(m, [], (opt,), 0, 1, width=4)

    def test_neutral_dummy_positions_have_zero_supervised_gradient(self):
        hidden = torch.randn(1, 4, 8, requires_grad=True)
        class Head:
            def _head_logits(self, value): return value
        y = torch.tensor([[-100, 2, -100, -100]]); segments = torch.tensor([[0, 1, 0, 0]])
        sums, counts = core.components(Head(), hidden, y, segments, horizons=(), checkpoint_heads=False)
        sums[1].backward(); self.assertEqual(counts[1], 1)
        self.assertEqual(float(hidden.grad[:, [0, 2, 3]].abs().max()), 0.)
        self.assertGreater(float(hidden.grad[:, 1].abs().sum()), 0.)

    def test_explicit_wrong_turn_mask_is_reused_and_never_becomes_router_prefix(self):
        from scripts.diag_p101a_clean_bilingual import masked_record
        unmasked = core.Record([3, 7, 8, 9], [-100, 8, 9, 4], [0, 1, 2, 2])
        with patch.object(core, 'encode_record', return_value=unmasked):
            result = masked_record(dict(meta=dict(supervised_assistant_turns=[2])), None)
        self.assertEqual(result.y, [-100, -100, 9, 4]); self.assertEqual(result.segments, [0, 0, 2, 2])
        self.assertEqual(result.targets, 2)
        with self.assertRaises(ValueError): r.question_prefix(result)

    def test_driver_dynamic_manifest_counts_and_corpus_namespaces(self):
        from scripts import diag_p078_route_training as d
        clean = SimpleNamespace(corpus=d.CLEAN_CORPUS); old = SimpleNamespace(corpus=d.CORPUS)
        self.assertEqual(d.update_count(dict(manifests=dict(train=dict(rows=22528)))), 704)
        self.assertEqual(d.update_count(dict(manifests=dict(train=dict(rows=105447)))), 3296)
        self.assertNotEqual(d.namespace(clean), d.namespace(old)); self.assertNotEqual(d.cp_name('uniform_r2', clean), d.cp_name('uniform_r2', old))

    def test_check_only_new_process_imports_no_torch_and_reads_no_data(self):
        code = "from scripts import diag_p078_route_training as d; import sys; assert 'torch' not in sys.modules; assert d.main(['--mode','train','--check-only'])==0; assert 'torch' not in sys.modules"
        result = subprocess.run([sys.executable, '-B', '-X', 'utf8', '-c', code], cwd=ROOT, capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr); self.assertIn('"corpus_reads": 0', result.stdout)

    def test_driver_gate_false_is_scoped_and_router_cannot_fake_success(self):
        from scripts import diag_p078_route_training as d
        with patch.object(d, 'READY', False), patch.object(d, 'worker', side_effect=AssertionError('real stage reached')):
            with redirect_stdout(io.StringIO()): self.assertEqual(d.main(['--mode', 'train', '--execute']), 8)
        with patch.object(d, 'READY', True), patch.object(d, 'worker', side_effect=AssertionError('router stage reached')):
            with redirect_stdout(io.StringIO()): self.assertEqual(d.main(['--mode', 'router', '--execute']), 8)

    def test_authority_is_new_pinned_user_metadata_not_an_old_clock_facade(self):
        from scripts import diag_p078_route_training as d
        args = SimpleNamespace(corpus=d.CLEAN_CORPUS, max_wall_sec=600, authorization='handoff/audit/toy_authority.json', authorization_sha256=None)
        info = {'source': 'toy only'}
        auth = dict(schema='P078_TRAIN_EXECUTION_AUTHORIZATION_V1', tag=d.namespace(args), allow_gpu_training=True,
            input_signature_sha256=r.sha(info), max_family_seconds=144000, max_worker_seconds=1800,
            expires_at=(datetime.now(timezone.utc) + timedelta(hours=1)).isoformat())
        with tempfile.TemporaryDirectory(prefix='p078_authority_toy_') as temporary, patch.object(d, 'ROOT', Path(temporary)):
            target = Path(temporary) / args.authorization; target.parent.mkdir(parents=True)
            target.write_text(json.dumps(auth), encoding='utf-8'); args.authorization_sha256 = d.digest(target)
            self.assertGreater(d.authority(args, info), 600)
            target.write_text(json.dumps(dict(auth, max_family_seconds=144001)), encoding='utf-8')
            with self.assertRaises(ValueError): d.authority(args, info)
            args.authorization_sha256 = d.digest(target)
            with self.assertRaises(d.Hold): d.authority(args, info)

    def test_cost32_forecast_rejects_missing_nonfinite_cost_and_exposes_resource_scope(self):
        from scripts import diag_p078_route_training as d
        cost = dict(update_seconds=[1.] * 32, validation_timing=dict(batch_seconds=[.1] * 8),
            probe_timing=[dict(seconds=.2, generation=dict(generated_tokens=2))] * 2,
            gpu_total_mib=16384., peak_reserved_mib=14000.)
        train, evaluation = d.cost_forecast(cost, 704, 64)
        self.assertGreater(train, 704); self.assertGreater(evaluation, 0)
        for changed in (dict(cost, update_seconds=[1.] * 31), dict(cost, update_seconds=[float('nan')] * 32),
                        dict(cost, peak_reserved_mib=16000.), dict(cost, probe_timing=[])):
            with self.assertRaises(d.Hold): d.cost_forecast(changed, 704, 64)

    def test_metadata_only_corpus_contract_accepts_new_source_and_blocks_retired_admission(self):
        from scripts import diag_p078_route_training as d
        args = SimpleNamespace(corpus=d.CLEAN_CORPUS, corpus_sha256='A' * 64)
        report = dict(schema='P101A_SFT_MTP_CORPUS_V1', status='CORPUS_READY', epochs=4, tokenizer_sha256=d.TOK_SHA,
            preparation_schema='P101A_CLEAN_BILINGUAL_PREPARATION_V3', family='mtp',
            sources=dict(old_contextless_teacher4473_rows=0, luna_drafts_admitted=0),
            manifests={s: dict(rows=n, shards=[]) for s, n in (('train', 22528), ('val', 512))})
        with patch.object(d, 'digest', return_value='A' * 64), patch.object(d, 'read', return_value=report):
            self.assertIs(d.inputs(args), report)
            report['sources']['luna_drafts_admitted'] = 1
            with self.assertRaises(ValueError): d.inputs(args)


if __name__ == '__main__': unittest.main()
