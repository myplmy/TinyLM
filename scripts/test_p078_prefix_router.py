"""Tiny CPU random-weight/temporary-fixture contracts; no real corpus/CP/GPU."""
from __future__ import annotations
import copy
from contextlib import contextmanager, redirect_stdout
from datetime import datetime, timedelta, timezone
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from scripts import p078_prefix_router as r
from scripts import diag_p078_prefix_router as d
r.route.import_guard()
import torch
from tinylm.config import TMTConfig
from tinylm.train import mtp_sft as core
torch.set_num_threads(1)


def toy_model():
    torch.manual_seed(1337)
    cfg = TMTConfig(vocab_size=67, dim=32, ffn_dim=64, n_q_heads=4, n_kv_heads=2, emb_rank=8,
        n_prelude=1, n_middle=8, n_coda=1, mlp_group=2, cla_group=2, micro_group=0,
        train_repeat=3., max_seq_len=32, grad_checkpoint=True, quantize_embedding=False)
    model = r.route.build_model(cfg, r.route.Policy('balanced_count')); r.freeze_body(model)
    return model


def toy_record(owner=1):
    return core.Record([3, 7, 8, 9, 10], [-100, -100, 9, 10, 4], [0, 0, owner, owner, owner])


def fixture_rows(n=96):
    return [dict(messages=[dict(role='user', content='unique question ' + str(i)), dict(role='assistant', content='answer')],
        meta=dict(language='ko' if i % 2 == 0 else 'en', article_id='article-' + str(i), context_id='context-' + str(i),
            parent_concept_id='root-' + str(i), context_original='explicit context ' + str(i))) for i in range(n)]


def args(**kw):
    values = dict(resource_only_r1=False, corpus=d.base.CLEAN_CORPUS, corpus_sha256='A' * 64,
        adam_lr=5e-5, muon_lr=2e-4, authorization='handoff/audit/toy_router.json', authorization_sha256=None,
        max_wall_sec=600, mode='prepare')
    values.update(kw); return SimpleNamespace(**values)


def body(model):
    return dict(core_sha256='C' * 64, feature_width=26,
        geometry=dict(n_layers=model.cfg.n_layers, n_prelude=model.cfg.n_prelude, n_middle=model.cfg.n_middle, n_coda=model.cfg.n_coda),
        owners=list(model.owner))


def lane(model, count=8, policy='learned'):
    quota = r.Quota(count); result = []
    for i in range(count):
        scores = [float(i % 3), float((i + 1) % 3), float((i + 2) % 3)]
        action, decision = quota.choose(None if policy == 'random_quota' else scores, random_choice=policy == 'random_quota')
        slot = r.action_slot(model, action)
        receipt = json.loads(json.dumps(r.route.plan(model.cfg, model.owner, model.policy, slot, 4, 'probe')))
        result.append(dict(case=i, corpus_index=i, row_sha256='row-' + str(i), group_sha256='group-' + str(i),
            language='ko' if i % 2 == 0 else 'en', policy=policy, predicted_relative_ce=None if policy == 'random_quota' else scores,
            decision=decision, route=receipt, prefix_ids=[3, 7, 8], assistant_nll=2. + i / 10,
            assistant_targets=3, actual_x_tokens=5, feature_head_seconds=.001, forward_seconds=.01,
            trial_candidates_executed=1, gold_used_for_selection=False))
    return result


class RouterTests(unittest.TestCase):
    def setUp(self):
        self.no_cuda_module = patch.object(torch.nn.Module, 'cuda', side_effect=AssertionError('tiny CPU only'))
        self.no_cuda_tensor = patch.object(torch.Tensor, 'cuda', side_effect=AssertionError('tiny CPU only'))
        self.no_load = patch.object(torch, 'load', side_effect=AssertionError('real checkpoint tensor loading forbidden'))
        self.no_cuda_module.start(); self.no_cuda_tensor.start(); self.no_load.start()
    def tearDown(self):
        self.no_load.stop(); self.no_cuda_tensor.stop(); self.no_cuda_module.stop()
        self.assertFalse(torch.cuda.is_initialized())

    def test_first_actual_supervised_owner2_keeps_known_past_but_excludes_gold_future(self):
        # Earlier wrong assistant tokens are intentionally present in x, but masked.
        record = core.Record([3, 14, 4, 3, 15, 4, 3, 8, 9], [-100] * 7 + [9, 4], [0] * 7 + [2, 2])
        before = copy.deepcopy(record); prefix = r.prefix(record)
        self.assertEqual(prefix.token_ids, tuple(record.x[:8])); self.assertIn(14, prefix.token_ids)
        changed = copy.deepcopy(record); changed.x[8] = 60; changed.y[7:] = [60, 2]
        self.assertEqual(r.prefix(changed), prefix); self.assertEqual(record, before)
        self.assertEqual(record.segments[7], 2)
        with self.assertRaises(ValueError): r.route.question_prefix(record)

    def test_zero_target_misaligned_or_zero_owner_prefix_is_refused(self):
        for record in (core.Record([3], [-100], [0]), core.Record([3, 7], [8], [1]), core.Record([3], [7], [0])):
            with self.assertRaises(ValueError): r.prefix(record)

    def test_real_mask_helper_owner2_flows_to_new_prefix_without_relabel_or_row_drop(self):
        from scripts.diag_p101a_clean_bilingual import masked_record
        raw = core.Record([3, 14, 4, 3, 15, 4, 3, 8, 9], [-100, 14, 4, -100, -100, -100, -100, 9, 4], [0, 1, 1, 0, 0, 0, 0, 2, 2])
        with patch.object(core, 'encode_record', return_value=raw):
            actual = masked_record(dict(meta=dict(supervised_assistant_turns=[2])), None)
        self.assertEqual(actual.targets, 2); self.assertEqual(actual.segments[-2:], [2, 2])
        self.assertEqual(r.prefix(actual).token_ids, tuple(raw.x[:8])); self.assertIn(14, r.prefix(actual).token_ids)

    def test_standalone_canonical_prefix_validation_owner2_excludes_gold_and_refuses_bpe_leak(self):
        row = dict(messages=[dict(role='user', content='first question'), dict(role='assistant', content='known wrong answer'),
            dict(role='user', content='current correction'), dict(role='assistant', content='future gold'), dict(role='user', content='future question')])
        record = core.Record([3, 14, 4, 3, 15, 4, 3, 8, 9], [-100] * 7 + [9, 4], [0] * 7 + [2, 2]); captured = []
        def serializer(conv, kind, **kw):
            captured.append(conv); self.assertEqual(kind, 'chatml'); self.assertTrue(kw['add_generation_prompt']); return 'known text'
        tok = SimpleNamespace(encode=lambda text: SimpleNamespace(ids=record.x[:8]))
        self.assertEqual(r.validate_prefix(row, record, tok, serializer=serializer), r.prefix(record))
        self.assertEqual(captured[0]['messages'], row['messages'][:3])
        self.assertNotIn('future gold', str(captured[0])); self.assertIn('known wrong answer', str(captured[0]))
        leaking = SimpleNamespace(encode=lambda text: SimpleNamespace(ids=record.x[:7]))
        with self.assertRaisesRegex(ValueError, 'HOLD_PREFIX_BOUNDARY'): r.validate_prefix(row, record, leaking, serializer=serializer)

    def test_features_are_detached_order_sensitive_and_future_gold_independent(self):
        model = toy_model(); record = toy_record(2); prefix = r.prefix(record)
        feature, fingerprint = r.features(model, prefix, body_sha256='A', tokenizer_sha256='B')
        self.assertEqual(feature.numel(), 26); self.assertFalse(feature.requires_grad)
        changed = copy.deepcopy(record); changed.x[3:] = [60, 61]; changed.y[2:] = [40, 41, 42]
        other, other_fingerprint = r.features(model, r.prefix(changed), body_sha256='A', tokenizer_sha256='B')
        self.assertTrue(torch.equal(feature, other)); self.assertEqual(fingerprint, other_fingerprint)
        permutation = r.route.QuestionPrefix(tuple(reversed(prefix.token_ids)))
        swapped, swapped_fingerprint = r.features(model, permutation, body_sha256='A', tokenizer_sha256='B')
        self.assertTrue(torch.allclose(feature[:8], swapped[:8], atol=1e-7, rtol=1e-6)); self.assertFalse(torch.equal(feature[8:], swapped[8:]))
        self.assertNotEqual(fingerprint, swapped_fingerprint)
        self.assertTrue(all(not p.requires_grad and p.grad is None for p in model.parameters()))

    def test_features_require_frozen_body_and_fingerprint_pins_body_tokenizer(self):
        model = toy_model(); prefix = r.prefix(toy_record())
        f, a = r.features(model, prefix, body_sha256='A', tokenizer_sha256='B')
        _, b = r.features(model, prefix, body_sha256='C', tokenizer_sha256='B'); self.assertNotEqual(a, b)
        next(model.parameters()).requires_grad_(True)
        with self.assertRaises(ValueError): r.features(model, prefix, body_sha256='A', tokenizer_sha256='B')

    def test_online_quota_exact_r2_all_tails_and_seed_reproducibility(self):
        import random
        original = random.getstate()
        for n in (1, 2, 3, 4, 5, 127, 128, 129, 512):
            for stochastic in (False, True):
                q = r.Quota(n); a = [q.choose([1., 0., 2.], random_choice=stochastic)[0] for _ in range(n)]
                self.assertEqual(sum(a), 2 * n)
                if n >= 4: self.assertEqual(sorted(a[:4]), [1, 2, 2, 3])
                again = r.Quota(n); self.assertEqual(a, [again.choose([1., 0., 2.], random_choice=stochastic)[0] for _ in range(n)])
                with self.assertRaises(ValueError): q.choose([1., 0., 2.])
        self.assertEqual(original, random.getstate())

    def test_quota_uses_only_current_scores_without_future_or_gold_fields(self):
        first = r.Quota(8); second = r.Quota(8)
        self.assertEqual(first.choose([2., 1., 0.]), second.choose([2., 1., 0.]))
        self.assertNotIn('gold', r.Quota.choose.__code__.co_varnames)
        with self.assertRaises(ValueError): r.Quota(4).choose([float('nan'), 0., 1.])
        with self.assertRaises(TypeError): r.Quota(4).choose([1., 2., 3.], answer='future')

    def test_action_scope_keeps_atomic_cla_route_and_session_cache_frozen(self):
        model = toy_model(); prefix = r.route.QuestionPrefix((3, 7, 8)); tokens = torch.tensor([[3, 7, 8]])
        with torch.no_grad(), r.action_scope(model, 3, prefix) as receipt:
            self.assertEqual(receipt['actual_repeats'], 3); model(tokens, use_cache=True)
            with self.assertRaises(RuntimeError): model.set_route(model.visit_schedule())
            with self.assertRaises(RuntimeError):
                with r.action_scope(model, 1, prefix): pass
        with self.assertRaises(RuntimeError): model(tokens)

    def test_trial_labels_train_only_and_corrected_owner2_counts_real_ce(self):
        model = toy_model(); records = [toy_record(1), toy_record(2)]; before = copy.deepcopy(model.state_dict())
        raw, relative, routes = r.trial_labels(model, records, split='train', width=8, device='cpu')
        self.assertEqual([r['actual_repeats'] for r in routes], [1, 2, 3]); self.assertEqual(len(raw), 2)
        for row, target in zip(raw, relative): self.assertEqual(target, r.relative_ce(row)); self.assertAlmostEqual(sum(target), 0.)
        for split in ('dev', 'test', 'val'):
            with patch.object(r, 'per_row_ce', side_effect=AssertionError('oracle trial reached')):
                with self.assertRaises(ValueError): r.trial_labels(model, records, split=split, width=8, device='cpu')
        self.assertTrue(all(torch.equal(v, before[k]) for k, v in model.state_dict().items()))
        self.assertTrue(all(p.grad is None and not p.requires_grad for p in model.parameters()))

    def test_selected_body_is_causal_and_all_three_actions_have_zero_body_grad(self):
        model = toy_model(); a = torch.tensor([[1, 2, 3, 4, 5]]); b = a.clone(); b[:, 3:] += 20
        for action in (1, 2, 3):
            with torch.no_grad(), r.action_scope(model, action):
                actual = model(a); other = model(b)
            self.assertTrue(torch.allclose(actual[:, :3], other[:, :3], atol=1e-5, rtol=1e-4))
            self.assertFalse(actual.requires_grad)
        self.assertTrue(all(p.grad is None for p in model.parameters()))

    def test_head_really_learns_with_body_unchanged_and_reproducible_initialization(self):
        model = toy_model(); before = copy.deepcopy(model.state_dict()); torch.manual_seed(9)
        x = torch.randn(16, 26); target = torch.stack((x[:, 0], -x[:, 0], x[:, 1]), 1)
        head = r.make_head(26); again = r.make_head(26)
        self.assertTrue(all(torch.equal(v, again.state_dict()[k]) for k, v in head.state_dict().items()))
        opt = torch.optim.Adam(head.parameters(), lr=.01); mean = x.mean(0); scale = x.std(0, unbiased=False).clamp_min(1e-6)
        losses = [r.head_update(head, opt, x, target, mean, scale) for _ in range(20)]
        self.assertLess(losses[-1], losses[0] * .3)
        self.assertTrue(all(torch.equal(v, before[k]) for k, v in model.state_dict().items()))
        self.assertTrue(all(p.grad is None for p in model.parameters()))

    def test_micro8_accumulation_matches_full_mean_gradient_and_no_rng_poison(self):
        torch.manual_seed(10); x = torch.randn(19, 26); y = torch.randn(19, 3); rng = torch.random.get_rng_state().clone()
        head = r.make_head(26); self.assertTrue(torch.equal(rng, torch.random.get_rng_state()))
        full = copy.deepcopy(head); mean = torch.zeros(26); scale = torch.ones(26)
        a = torch.optim.SGD(head.parameters(), lr=.01); b = torch.optim.SGD(full.parameters(), lr=.01)
        r.head_update(head, a, x, y, mean, scale); ((full(x) - y).square().mean()).backward(); b.step()
        for p, q in zip(head.parameters(), full.parameters()): self.assertTrue(torch.allclose(p, q, atol=1e-7, rtol=1e-6))

    def test_group_split_is_reproducible_balanced_and_has_no_keys_crossing(self):
        rows = fixture_rows(); a = r.split_manifest(rows, min_rows=1, min_language=1)
        self.assertEqual(a, r.split_manifest(rows, min_rows=1, min_language=1))
        left, right = (set(k for v in a['splits'][s] for k in v['keys']) for s in ('dev', 'test'))
        self.assertFalse(left & right); self.assertEqual(sum(a['counts'][s]['rows'] for s in ('dev', 'test')), len(rows))
        self.assertFalse(a['fully_pipeline_blind']); self.assertTrue(a['body_validation_reused'])

    def test_canonical_text_block_lists_preserve_content_groups_order_and_original_rows(self):
        text = '  한글\ncontext: A=1; B=8\nWho?  '
        blocks = [dict(type='text', text='  한글\n'), dict(type='text', text='context: A=1; B=8\nWho?  ')]
        original = copy.deepcopy(blocks)
        self.assertEqual(r.text_content(text), text); self.assertEqual(r.text_content(blocks), text)
        self.assertEqual(blocks, original)
        plain = fixture_rows(); canonical = copy.deepcopy(plain)
        for row in canonical:
            for message in row['messages']:
                content = message['content']; middle = len(content) // 2
                message['content'] = [dict(type='text', text=content[:middle]), dict(type='text', text=content[middle:])]
        unchanged = copy.deepcopy(canonical)
        for old, new in zip(plain, canonical):
            self.assertEqual(r.group_keys(old), r.group_keys(new)); self.assertEqual(r.case_order_sha(old), r.case_order_sha(new))
            self.assertNotEqual(r.row_sha(old), r.row_sha(new))  # Original representation identity remains untouched.
        split = r.split_manifest(canonical, min_rows=1, min_language=1)
        expected = r.split_manifest(plain, min_rows=1, min_language=1)
        self.assertEqual(split['counts'], expected['counts'])
        for name in ('dev', 'test'):
            self.assertEqual([e['index'] for e in split['splits'][name]], [e['index'] for e in expected['splits'][name]])
        self.assertEqual(canonical, unchanged)

    def test_nontext_or_malformed_canonical_content_is_refused_without_data_drop(self):
        for value in ([dict(type='thinking', text='hidden')], [dict(type='image', url='fixture')],
                      [dict(type='tool_result', content=[])], [dict(type='text', text=3)],
                      [dict(type='text')], ['raw nested text'], {'text': 'not a block list'}, None):
            with self.assertRaises(ValueError): r.text_content(value)
            row = fixture_rows(1)[0]; row['messages'][0]['content'] = value
            with self.assertRaises(ValueError): r.group_keys(row)
            with self.assertRaises(ValueError): r.case_order_sha(row)

    def test_case_order_hash_does_not_consume_assistant_gold_or_future_messages(self):
        row = fixture_rows(2)[0]; initial = r.case_order_sha(row); changed = copy.deepcopy(row)
        changed['messages'][1]['content'] = 'changed future gold'
        changed['messages'].append(dict(role='user', content='future question'))
        self.assertEqual(initial, r.case_order_sha(changed)); self.assertNotEqual(r.row_sha(row), r.row_sha(changed))

    def test_transitive_article_context_roots_and_language_views_share_component(self):
        rows = fixture_rows(); rows[1]['meta']['article_id'] = rows[0]['meta']['article_id']
        rows[2]['meta']['context_id'] = rows[1]['meta']['context_id']
        rows[3]['meta']['parent_concept_id'] = rows[2]['meta']['parent_concept_id']
        rows[4]['meta']['context_original'] = rows[3]['meta']['context_original']
        manifest = r.split_manifest(rows, min_rows=1, min_language=1)
        owners = {e['index']: (split, e['group_sha256']) for split in ('dev', 'test') for e in manifest['splits'][split]}
        self.assertEqual(len({owners[i] for i in range(5)}), 1)

    def test_split_minimum_shortage_missing_lineage_or_single_language_holds(self):
        with self.assertRaisesRegex(ValueError, 'HOLD_SPLIT_MINIMA'): r.split_manifest(fixture_rows())
        rows = fixture_rows(); del rows[0]['meta']['article_id']
        with self.assertRaises(ValueError): r.split_manifest(rows, min_rows=1, min_language=1)
        rows = fixture_rows()
        for row in rows: row['meta']['language'] = 'ko'
        with self.assertRaisesRegex(ValueError, 'HOLD_SPLIT_MINIMA'): r.split_manifest(rows, min_rows=1, min_language=1)

    def test_full512_synthetic_val_meets_production_minima_without_lowering_or_seed_search(self):
        manifest = r.split_manifest(fixture_rows(512))
        self.assertEqual(manifest['seed'], 1337); self.assertEqual(manifest['min_rows'], 128); self.assertEqual(manifest['min_language'], 64)
        for split in ('dev', 'test'):
            self.assertGreaterEqual(manifest['counts'][split]['rows'], 128)
            for language in ('ko', 'en'): self.assertGreaterEqual(manifest['counts'][split]['languages'][language], 64)

    def test_readonly_atomic_receipts_equal_original_live_plan_without_new_torch_import(self):
        model = toy_model(); evidence = body(model)
        for i in range(4): self.assertEqual(r.readonly_plan(evidence['geometry'], evidence['owners'], i),
            json.loads(json.dumps(r.route.plan(model.cfg, model.owner, model.policy, i, 4, 'probe'))))
        code = "from scripts import p078_prefix_router as r; import sys; g=dict(n_layers=10,n_prelude=1,n_middle=8,n_coda=1); r.readonly_plan(g,[0,1,1,3,3,5,5,7,7,9],0); assert 'torch' not in sys.modules"
        result = subprocess.run([sys.executable, '-B', '-c', code], cwd=ROOT, capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_driver_check_only_imports_no_torch_and_reads_only_pinned_sources(self):
        code = "from scripts import diag_p078_prefix_router as d; import sys; assert 'torch' not in sys.modules; assert d.main(['--mode','fit','--check-only'])==0; assert 'torch' not in sys.modules"
        result = subprocess.run([sys.executable, '-B', '-c', code], cwd=ROOT, capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr); self.assertIn('"corpus_reads": 0', result.stdout)

    def test_false_ready_gate_is_patched_not_bound_to_final_source_flag(self):
        with patch.object(d, 'READY', False), patch.object(d, 'worker', side_effect=AssertionError('real stage reached')):
            with redirect_stdout(io.StringIO()): self.assertEqual(d.main(['--mode', 'labels', '--execute']), 8)

    def test_new_namespace_preserves_original_four_arms_and_symlink_ancestors(self):
        a = args(); self.assertNotIn(d.namespace(a), d.base.namespace(a))
        self.assertNotEqual(d.namespace(a), d.namespace(args(resource_only_r1=True)))
        with tempfile.TemporaryDirectory(prefix='p078_router_path_') as temporary, patch.object(d.base, 'ROOT', Path(temporary)):
            root = Path(temporary); (root / 'runs').mkdir(); (root / 'elsewhere').mkdir(); (root / 'runs' / 'eval').symlink_to(root / 'elsewhere', target_is_directory=True)
            with self.assertRaises(ValueError): d.safe_output(a, d.raw_name(a, 'labels') + '/file.json')
            with self.assertRaises(ValueError): d.safe_output(a, 'test_result/evidence/old_namespace/report.json')
            with self.assertRaises(ValueError): d.root_path('../outside')

    def test_body_checkpoint_is_prespecified_balanced704_and_no_r1_quality_fallback(self):
        a = args(); self.assertFalse(d.body_evidence(args(resource_only_r1=True))['scientific_body'])
        with patch.object(d.base, 'closed', side_effect=FileNotFoundError('not created')):
            with self.assertRaises(d.Hold): d.body_evidence(a)
        value = dict(updates=703, status='ROUTE_SFT_COMPLETE_EVAL_REVIEW_REQUIRED', checkpoint_writes=1,
            arm='balanced_count', checkpoint=d.base.cp_name('balanced_count', a))
        with patch.object(d.base, 'closed', return_value=value):
            with self.assertRaises(d.Hold): d.body_evidence(a)

    def test_authority_byte_hash_deadline_source_body_and_resource_flags_are_exact(self):
        a = args(); info = dict(toy='SOURCE_ONLY')
        auth = dict(schema='P078_PREFIX_ROUTER_EXECUTION_AUTHORIZATION_V1', tag=d.namespace(a),
            input_signature_sha256=r.route.sha(info), allow_gpu_training=True, max_family_seconds=144000,
            max_worker_seconds=600, expires_at=(datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
            resource_only_r1=False, body_checkpoint_sha256='B' * 64)
        with tempfile.TemporaryDirectory(prefix='p078_router_auth_') as temporary, patch.object(d.base, 'ROOT', Path(temporary)):
            target = Path(temporary) / a.authorization; target.parent.mkdir(parents=True)
            target.write_text(json.dumps(auth), encoding='utf-8'); a.authorization_sha256 = d.base.digest(target)
            self.assertGreater(d.authority(a, info)[1], 600)
            target.write_text(json.dumps(dict(auth, resource_only_r1=True)), encoding='utf-8')
            with self.assertRaises(ValueError): d.authority(a, info)
            a.authorization_sha256 = d.base.digest(target)
            with self.assertRaises(d.Hold): d.authority(a, info)

    def test_metadata_prepare_accepts_no_body_and_no_gpu_authority_but_gpu_stages_reject_it(self):
        a = args(); info = {'fixture': 'CPU_PREPARE_ONLY'}
        auth = dict(schema='P078_PREFIX_ROUTER_EXECUTION_AUTHORIZATION_V1', tag=d.namespace(a),
            input_signature_sha256=r.route.sha(info), allow_gpu_training=False, max_family_seconds=144000,
            max_worker_seconds=600, expires_at=(datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
            resource_only_r1=False, body_checkpoint_sha256=None)
        with tempfile.TemporaryDirectory(prefix='p078_cpu_prepare_') as temporary, patch.object(d.base, 'ROOT', Path(temporary)):
            target = Path(temporary) / a.authorization; target.parent.mkdir(parents=True)
            target.write_text(json.dumps(auth), encoding='utf-8'); a.authorization_sha256 = d.base.digest(target)
            self.assertGreater(d.authority(a, info)[1], 600)
            for mode in ('cost', 'labels', 'fit', 'evaluate'):
                a.mode = mode
                with self.assertRaises(d.Hold): d.authority(a, info)
            a.mode = 'prepare'
            with patch.object(d, 'signature', return_value=info), patch.object(d.os, 'getpgrp', side_effect=d.os.getpid), \
                    patch.object(d, 'prepare', return_value=dict(status='CPU_FIXTURE', model_loads=0, checkpoint_tensor_loads=0)), \
                    patch.object(d, 'body_evidence', side_effect=AssertionError('prepare must not require absent CP')):
                self.assertEqual(d.worker(a), 0); report = d.closed(a, 'prepare')
                self.assertEqual(report['model_loads'], 0); self.assertEqual(report['checkpoint_tensor_loads'], 0)
            target.write_text(json.dumps(dict(auth, expires_at=(datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat())), encoding='utf-8')
            a.authorization_sha256 = d.base.digest(target)
            with self.assertRaises(d.Hold): d.authority(a, info)

    def test_independent_summary_rejects_target_policy_visit_or_case_tampering(self):
        events = lane(toy_model()); summary = d.summarize(events)
        self.assertEqual(summary['rows'], 8); self.assertEqual(summary['repeats'], 16); self.assertEqual(summary['assistant_targets'], 24)
        for modify in (lambda e: e[0].update(trial_candidates_executed=3), lambda e: e[0].update(gold_used_for_selection=True),
                       lambda e: e[0].update(case=10), lambda e: e[0]['decision'].update(action=3)):
            broken = copy.deepcopy(events); modify(broken)
            with self.assertRaises(ValueError): d.summarize(broken)
        changed = copy.deepcopy(events); changed[0]['assistant_nll'] += 1
        self.assertNotEqual(d.summarize(changed), summary)

    def test_answer_boundary_requires_real_terminal_and_counts_cacheoff_compute_not_just_rows(self):
        event = lane(toy_model())[0]; event['first_answer'] = dict(prefix_ids=event['prefix_ids'], route=event['route'], attempts=1,
            input_text='fixture only', actual_answer='fixture', seconds=.01,
            generation=dict(finish_reason='STOP_SEQUENCE', generated_tokens=2, generated_ids=[17, 4], max_new=128,
                prompt_tokens=3, content_tokens=1, terminal_ids=[4], terminal_only_removed=True, matched_stop_sequence=[4]))
        d.verify_answer(event); self.assertEqual(d.generation_input_slots(event), 3 + 4)
        for change in (dict(finish_reason='UNKNOWN'), dict(terminal_ids=[]), dict(generated_tokens=1), dict(generated_ids=[4, 17]),
                       dict(content_tokens=2), dict(max_new=64)):
            changed = copy.deepcopy(event); changed['first_answer']['generation'].update(change)
            with self.assertRaises(ValueError): d.verify_answer(changed)

    def test_head_same_handle_hash_read_rejects_changed_bytes_without_real_tensor_loading(self):
        with tempfile.TemporaryDirectory(prefix='p078_router_head_') as temporary:
            path = Path(temporary) / 'fixture.bin'; path.write_bytes(b'NOT_A_CHECKPOINT')
            fake = SimpleNamespace(load=lambda *a, **kw: dict(fixture=True))
            self.assertEqual(d.read_head(fake, path, d.base.digest(path)), dict(fixture=True))
            with self.assertRaises(ValueError): d.read_head(fake, path, '0' * 64)
            def changed(*unused, **kw): path.write_bytes(b'CHANGED_FIXTURE'); return {}
            with self.assertRaisesRegex(ValueError, 'changed during'): d.read_head(SimpleNamespace(load=changed), path, d.base.digest(path))

    def test_tiny_driver_fit_test_and_raw_readback_use_chosen_route_only_and_leave_body_unchanged(self):
        model = toy_model(); evidence = body(model); before = copy.deepcopy(model.state_dict()); a = args(); stage = {}; captured = {}
        examples = fixture_rows(8); entries = [dict(index=i, row_sha256=r.row_sha(examples[i]), group_sha256='group-' + str(i), language=examples[i]['meta']['language']) for i in range(8)]
        prep = dict(split_manifest=dict(splits=dict(dev=entries[:4], test=entries[4:]), counts=dict(dev=dict(rows=4), test=dict(rows=4))))
        torch.manual_seed(12); x = torch.randn(128, 26); y = torch.stack((x[:, 0], -x[:, 0], x[:, 1]), 1)
        label_rows = [dict(feature=xx.tolist(), relative_ce=yy.tolist()) for xx, yy in zip(x, y)]
        record_map = dict(train=[toy_record(2) for _ in range(128)], val=[toy_record(2) for _ in range(8)])
        tok = SimpleNamespace(token_to_id=lambda _: 0)
        @contextmanager
        def frozen(_args): yield torch, model, SimpleNamespace(max_seq_len=1024), tok, evidence
        original_ce = r.per_row_ce
        def cpu_ce(*positional, **kwargs): kwargs.update(device='cpu', width=8); return original_ce(*positional, **kwargs)
        def save(payload, stream): captured['payload'] = payload; stream.write(b'FIXTURE_NO_SAVED_TENSORS')
        def answer(_torch, body_model, _cfg, _tok, prefix, action):
            with r.action_scope(body_model, action, prefix) as receipt:
                return dict(prefix_ids=list(prefix.token_ids), route=receipt, attempts=1, input_text='fixture only', actual_answer='fixture', seconds=.01,
                    generation=dict(finish_reason='STOP_SEQUENCE', generated_tokens=2, generated_ids=[17, 4], max_new=128,
                        prompt_tokens=len(prefix.token_ids), content_tokens=1, terminal_ids=[4], terminal_only_removed=True, matched_stop_sequence=[4]))
        with tempfile.TemporaryDirectory(prefix='p078_router_pipeline_') as temporary, patch.object(d.base, 'ROOT', Path(temporary)), \
                patch.object(d, 'frozen_body', frozen), patch.object(d, 'signature', return_value={'fixture': True}), \
                patch.object(d, 'prepared', return_value=prep), patch.object(d, 'require_budget', return_value={}), \
                patch.object(d, 'verify_labels', side_effect=lambda _: (dict(body=evidence, raw_manifest=dict(concat_sha256='L' * 64)), label_rows)), \
                patch.object(d, 'records_and_rows', return_value=(record_map, {'val': examples})), \
                patch.object(d, 'closed', side_effect=lambda _, mode: stage[mode]), \
                patch.object(r, 'per_row_ce', side_effect=cpu_ce) as forwards, \
                patch.object(r, 'trial_labels', side_effect=AssertionError('DEV/TEST candidate sweep forbidden')), \
                patch.object(torch.cuda, 'synchronize'), patch.object(torch, 'save', side_effect=save), \
                patch.object(d, 'read_head', side_effect=lambda *_: captured['payload']), patch.object(d, 'generate', side_effect=answer):
            evidence['checkpoint'] = d.raw_name(a, 'body_fixture') + '/fixture.bin'
            target = d.safe_output(a, evidence['checkpoint']); target.parent.mkdir(parents=True); target.write_bytes(b'FIXTURE_BODY_BYTES_NOT_CP')
            evidence['checkpoint_sha256'] = d.base.digest(target)
            stage['fit'] = d.fit(a)
            with redirect_stdout(io.StringIO()): stage['evaluate'] = d.evaluate(a)
            result = d.readback(a)
            self.assertEqual(result['status'], 'ROUTER_RAW_RECOUNTED_NOT_ADOPTED'); self.assertEqual(result['checkpoint_tensor_loads'], 0)
            self.assertEqual(len(stage['fit']['head_updates']), 5); self.assertEqual(stage['fit']['TEST_evaluations'], 0)
            self.assertEqual(forwards.call_count, 3 * 4 + 4 * 4)
            self.assertTrue(all(len(call.args[1]) == 1 for call in forwards.call_args_list))
            for policy in r.POLICIES: self.assertEqual(result['summaries'][policy]['generated_answers'], 4)
            # Alter report-only aggregation: untouched independently verified raw must reject it.
            stage['evaluate']['summaries']['learned']['ce'] += 1.
            with self.assertRaisesRegex(ValueError, 'independent TEST raw summary'): d.readback(a)
        self.assertTrue(all(torch.equal(v, before[k]) for k, v in model.state_dict().items()))
        self.assertTrue(all(p.grad is None and not p.requires_grad for p in model.parameters()))

    def test_independent_lane_replays_online_selection_and_exact_atomic_trace(self):
        model = toy_model(); evidence = body(model); events = lane(model)
        entries = [dict(index=e['corpus_index'], row_sha256=e['row_sha256'], group_sha256=e['group_sha256'], language=e['language']) for e in events]
        d.verify_lane(events, entries, evidence)
        for modify in (lambda e: e[0]['route']['route'].reverse(), lambda e: e[0]['decision'].update(quota_before=[1, 1, 1, 1]),
                       lambda e: e[0].update(group_sha256='wrong')):
            changed = copy.deepcopy(events); modify(changed)
            with self.assertRaises(ValueError): d.verify_lane(changed, entries, evidence)

    def test_cost_forecast_is_full_pending_and_resource_parent_never_authorizes_labels(self):
        a = args(); prep = dict(train_rows=22528, split_manifest=dict(counts=dict(dev=dict(rows=256), test=dict(rows=256))))
        cost = dict(status='ROUTER_COST8_COMPLETE', trial_batch_seconds=[.1] * 8, selected_row_seconds=[.01] * 3,
            head64_seconds=.01, encoded_seconds=1., generation_timing=[dict(seconds=.1, generation=dict(generated_tokens=2))] * 2,
            gpu_total_mib=16384., peak_reserved_mib=14000., body=dict(toy=True), feature_row_seconds=[.001] * 64, head_predict_seconds=.001)
        with tempfile.TemporaryDirectory(prefix='p078_router_forecast_') as temporary, patch.object(d.base, 'ROOT', Path(temporary)), \
                patch.object(d, 'prepared', return_value=prep), patch.object(d, 'closed', return_value=cost), \
                patch.object(d, 'authority', return_value=({}, 100000.)), patch.object(d, 'spent', return_value=0.), patch.object(d, 'signature', return_value={}):
            value = d.forecast(a); self.assertTrue(value['fits']); self.assertGreater(value['forecasts_seconds']['evaluate'], 1000)
            with patch.object(d, 'authority', return_value=({}, 600.)): self.assertFalse(d.forecast(a)['fits'])
            with self.assertRaises(d.Hold): d.forecast(args(resource_only_r1=True))
            with patch.object(d, 'closed', return_value=dict(cost, trial_batch_seconds=[float('nan')] * 8)):
                with self.assertRaises(ValueError): d.forecast(a)

    def test_worker_direct_pg_group_admission_and_failure_receipt_are_closed(self):
        a = args(mode='labels'); writes = []; info = {'fixture': True}
        with tempfile.TemporaryDirectory(prefix='p078_router_worker_') as temporary, patch.object(d.base, 'ROOT', Path(temporary)), \
                patch.object(d, 'signature', return_value=info), patch.object(d, 'authority', return_value=({}, 599.)), \
                patch.object(d, 'write', side_effect=lambda *values: writes.append(values)), \
                patch.object(d, 'labels', side_effect=AssertionError('full cap admission bypassed')):
            with redirect_stdout(io.StringIO()): self.assertEqual(d.worker(a), 8)
        self.assertEqual(len(writes), 1); self.assertFalse(writes[0][-1]['complete']); self.assertEqual(writes[0][-1]['returncode'], 8)

    def test_closed_receipt_checks_mode_time_cap_finite_elapsed_pgid_report_hash_and_original_authority(self):
        a = args(mode='prepare'); info = {'fixture': True}; now = datetime.now(timezone.utc)
        auth = dict(schema='P078_PREFIX_ROUTER_EXECUTION_AUTHORIZATION_V1', tag=d.namespace(a),
            input_signature_sha256=r.route.sha(info), allow_gpu_training=True, max_family_seconds=144000,
            max_worker_seconds=600, expires_at=(now + timedelta(hours=1)).isoformat(), resource_only_r1=False, body_checkpoint_sha256='B' * 64)
        report = dict(input=info, mode='prepare', authorization=auth, authorization_sha256='A' * 64, fixture=True)
        activity = dict(input=info, mode='prepare', complete=True, returncode=0, authorization=auth,
            authorization_sha256='A' * 64, authorization_canonical_sha256=r.route.sha(auth),
            started_at=(now - timedelta(seconds=2)).isoformat(), ended_at=now.isoformat(),
            seconds=10., max_wall_sec=600, admission_remaining=3600., pid=123, pgid=123)
        with tempfile.TemporaryDirectory(prefix='p078_router_closed_') as temporary, patch.object(d.base, 'ROOT', Path(temporary)), \
                patch.object(d, 'signature', return_value=info):
            d.write(a, d.report_name(a, 'prepare'), report)
            activity['report_sha256'] = d.base.digest(d.root_path(d.report_name(a, 'prepare')))
            d.write(a, d.activity_name(a, 'prepare'), activity)
            self.assertEqual(d.closed(a, 'prepare'), report)  # UTC2sec/perf10sec intentionally need not be equal.
            target = d.root_path(d.activity_name(a, 'prepare'))
            for update in (dict(seconds=float('nan')), dict(seconds=631.), dict(admission_remaining=599.), dict(pgid=124),
                           dict(report_sha256='0' * 64), dict(mode='fit'), dict(complete=False), dict(returncode=130),
                           dict(started_at=(now + timedelta(seconds=1)).isoformat())):
                target.write_text(json.dumps(dict(activity, **update)), encoding='utf-8')
                with self.assertRaises(ValueError): d.closed(a, 'prepare')

    def test_partial_selected_evaluation_sinks_completed_cases_before_failure_without_trial_sweep(self):
        model = toy_model(); entries = [dict(index=i, row_sha256=str(i), group_sha256=str(i), language='ko') for i in range(4)]
        records = [toy_record() for _ in range(4)]; actual = r.per_row_ce; saved = []; calls = []
        def failing(*positional, **kwargs):
            calls.append(kwargs['action'])
            if len(calls) == 2: raise ValueError('injected second case failure')
            kwargs.update(device='cpu', width=8); return actual(*positional, **kwargs)
        with patch.object(r, 'per_row_ce', side_effect=failing), patch.object(torch.cuda, 'synchronize'), \
                patch.object(r, 'trial_labels', side_effect=AssertionError('trial labels reached')):
            with self.assertRaisesRegex(ValueError, 'second case'):
                d.selected_evaluation(torch, model, model.cfg, SimpleNamespace(token_to_id=lambda _: 0), body(model), records, entries,
                    policy='random_quota', sink=saved.append)
        self.assertEqual(len(saved), 1); self.assertEqual(saved[0]['case'], 0); self.assertEqual(saved[0]['trial_candidates_executed'], 1)

    def test_source_pin_covers_new_three_and_live_four_arm_helper_without_mutation(self):
        self.assertIn('scripts/p078_route_training.py', d.CODE); self.assertIn('scripts/diag_p078_route_training.py', d.CODE)
        self.assertIn('scripts/test_p078_prefix_router.py', d.CODE); self.assertEqual(len(d.CODE), len(set(d.CODE)))
        info = d.signature(args()); self.assertEqual(len(info['source_sha256']), len(d.CODE)); self.assertFalse(info['fully_blind'] if 'fully_blind' in info else info['split']['fully_blind'])
        self.assertEqual(info['head']['dev_epochs'], [1, 3, 5]); self.assertEqual(info['body_source_signature_sha256'], r.route.sha(d.base.signature(args())))


if __name__ == '__main__': unittest.main()
