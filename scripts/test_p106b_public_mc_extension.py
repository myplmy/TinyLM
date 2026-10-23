"""Synthetic public rows/tokenizers/scorers only; no learned model or torch."""
from __future__ import annotations

from contextlib import ExitStack, contextmanager, nullcontext, redirect_stderr, redirect_stdout
import copy
from datetime import datetime, timedelta, timezone
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import p106b_public_mc_extension as m


class Tokenizer:
    def encode(self, text):
        if text == 'EMPTY': return NS(ids=[])
        if text == 'LONG': return NS(ids=[1] * 1024)
        return NS(ids=list(range(1, max(1, len(text.strip())) + 1)))


def adapter(row):
    return dict(ctx=row['goal'], choices=[' A', ' BBB'] if row['task'] == 'piqa'
        else [' A', ' BBB', ' CCC', ' DDDD'], gold=row['label'])


def fake_scores(plan):
    counts = [len(x) for x in plan['encoding']['continuation_ids']]
    sums = [2., 3., 5., 6.][:len(counts)]; means = [s / n for s, n in zip(sums, counts)]
    chars = [max(1, len(c)) for c in plan['item']['choices']]
    return dict(id=plan['id'], gold=plan['item']['gold'], n_tokens=counts, n_chars=chars,
        sum_nll=sums, mean_nll=means, score=means[:], pred_harness=0,
        pred_internal=min(range(len(means)), key=means.__getitem__),
        pred_internal_norm=min(range(len(means)), key=means.__getitem__),
        pred_harness_norm=min(range(len(sums)), key=lambda i: sums[i] / chars[i]),
        margin_mean=0., margin_decision=0.)


class FakeBudget:
    def __init__(self, *_args): self.ticks = 0
    def check(self): pass
    def elapsed(self): self.ticks += 1; return self.ticks / 100


def expected_baselines(plans):
    return dict(old_label_majority_correct=sum(p['baseline']['old_label_majority_correct'] for p in plans),
        shortest_character_correct=sum(p['baseline']['shortest_character_correct'] for p in plans),
        longest_character_correct=sum(p['baseline']['longest_character_correct'] for p in plans),
        new_label_majority_oracle_correct=sum(max(sum(p['item']['gold'] == g for p in plans if p['source']['task'] == t)
            for g in range(4)) for t in m.TASKS), candidate_forwards=sum(len(p['item']['choices']) for p in plans))


@contextmanager
def source_fixture():
    with tempfile.TemporaryDirectory(prefix='public_mc_synthetic_') as folder, ExitStack() as stack:
        root = Path(folder); bench = root / 'datasets/bench'; bench.mkdir(parents=True)
        sources = {}; old = dict(sources={}); pins = {}
        for task in m.TASKS:
            sources[task] = [dict(task=task, goal=task + ' question ' + str(i), question=task + ' question ' + str(i),
                ctx=task + ' question ' + str(i), ctx_a=task + ' question ' + str(i), ctx_b='', label=i % 2) for i in range(8)]
            path = bench / (task + '.jsonl')
            path.write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in sources[task]), encoding='utf-8')
            digest = m.common.file_sha(path); pins[task] = (8, digest)
            old['sources'][task] = dict(path='datasets/bench/' + task + '.jsonl', rows=8, sha256=digest, indices=[0, 1])
        old_path = root / m.OLD_REPORT; old_path.parent.mkdir(parents=True)
        old_path.write_text(json.dumps(old), encoding='utf-8')
        code_path = root / 'scripts/frozen.py'; code_path.parent.mkdir(); code_path.write_text('# synthetic code\n', encoding='utf-8')
        packet, _ = m.select_packet(sources, old['sources'], count=2)
        selection = dict(schema='P106B_PUBLIC_NEW768_SELECTION_AUDIT_V1', seed=m.SEED, task_order=list(m.TASKS),
            source_sha256={t: pins[t][1].lower() for t in m.TASKS},
            indices={t: [r['index'] for r in packet if r['task'] == t] for t in m.TASKS})
        for name, value in dict(COUNT=2, SOURCE_PINS=pins, OLD_REPORT_SHA=m.common.file_sha(old_path),
                IDS_SHA=m.common.sha([m.case_id(r) for r in packet]), PACKET_SHA=m.common.sha(packet),
                SELECTION_SHA=m.common.sha(selection), CODE=('scripts/frozen.py',)).items():
            stack.enter_context(patch.object(m, name, value))
        plans = m.adapt_plans(packet, sources, old, {t: adapter for t in m.TASKS}, Tokenizer())
        stack.enter_context(patch.object(m, 'KNOWN_BASELINES', expected_baselines(plans)))
        yield NS(root=root, sources=sources, old=old, packet=packet, plans=plans,
            prepared=root / 'data_cache/prepared', output=root / 'test_result/evidence/new_model')


class Guarded(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack(); self.addCleanup(self.stack.close)
        self.stack.enter_context(patch('builtins.input', side_effect=AssertionError('no interactive input')))
        self.stack.enter_context(patch.object(m, 'dependencies', side_effect=AssertionError('no actual runtime/imports')))

    def runtime(self, fixture, exit_hook=None, score_hook=None):
        ui = NS(TOKENIZER_SHA='T' * 64); ui.resolve_model = Mock(side_effect=lambda name: name)
        route = NS(assert_active=Mock()); model = Mock(return_value=object()); opened = []
        @contextmanager
        def selected(spec, root):
            self.assertEqual(root, fixture.root); self.assertIn(spec, m.MODELS); opened.append(spec)
            active = dict(name=spec, model=model, route=route, cfg=NS(max_seq_len=1024),
                tokenizer=Tokenizer(), torch=object(), checkpoint='SYNTHETIC_NO_CP',
                checkpoint_sha256='C' * 64, core_sha256='B' * 64, report_sha256='R' * 64,
                manifest_sha256='M' * 64, tokenizer_sha256=ui.TOKENIZER_SHA, precision='FP32_MATH',
                quantization_route=dict(mode='ternary' if spec.endswith('-q') else 'float'))
            try:
                yield active
                self.assertFalse((fixture.output / 'report.json').exists(), 'success before strict exit')
                if exit_hook: exit_hook()
            finally: active.clear()
        ui.selected_runtime = selected
        calls = []
        def run_mc(task, items, counted, tokenizer, dev, seq_max, torch, F, no_pmi):
            self.assertEqual((dev, seq_max, no_pmi), ('cuda', 1024, True)); self.assertEqual(len(items), 1)
            item = items[0]; calls.append(item['_iid'])
            plan = next(p for p in fixture.plans if p['id'] == item['_iid'])
            for _ in item['choices']: counted(NS(shape=(1, 8)))
            if score_hook: score_hook(item)
            row = fake_scores(plan)
            return dict(rows=[row], skip_rows=[], h_ok=[int(row['pred_harness'] == item['gold'])])
        suite = NS(ADAPTERS={t: adapter for t in m.TASKS}, run_mc=run_mc)
        return (ui, suite, lambda value: value, object(), lambda _seconds: nullcontext()), opened, calls, model

    def evaluate_fake(self, fixture, model_name='native595-f', **hooks):
        runtime, opened, calls, model = self.runtime(fixture, **hooks)
        args = NS(execute=True, model=model_name, max_wall_sec=60,
            deadline='2099-01-01T00:00:00+00:00', input=str(fixture.prepared), output=str(fixture.output))
        with patch.object(m, 'dependencies', return_value=runtime), patch.object(m, 'Budget', FakeBudget), \
                patch.object(m, 'parse_deadline', return_value=datetime(2099, 1, 1, tzinfo=timezone.utc)), redirect_stdout(io.StringIO()):
            result = m.evaluate(args, fixture.root)
        return result, opened, calls, model


class SelectionAndPacketTests(Guarded):
    def test_fixed_hash_constants_and_task_order_match_audit(self):
        self.assertEqual(m.TASKS, ('piqa', 'hellaswag', 'arc_easy'))
        self.assertEqual(m.IDS_SHA, 'B53F6B3430BB376E91AA3859F9266888C72320DB5F85ABA5256AABF29C9AF5D5')
        self.assertEqual(m.PACKET_SHA, '660CD423BE22905F325405FBBEE471F0DFF9C06424DE5B2DFFCDD98BF5DB2AB2')
        self.assertEqual(m.KNOWN_BASELINES, dict(old_label_majority_correct=266, shortest_character_correct=272,
            longest_character_correct=245, new_label_majority_oracle_correct=283, candidate_forwards=2559))

    def test_deterministic_selection_preserves_raw_rows_not_mutating_sources(self):
        with source_fixture() as f:
            before = copy.deepcopy(f.sources)
            a, _ = m.select_packet(f.sources, f.old['sources'], count=2)
            b, _ = m.select_packet(f.sources, f.old['sources'], count=2)
            self.assertEqual(a, b); self.assertEqual(f.sources, before)
            self.assertEqual(len(a), 6); self.assertEqual(len({m.case_id(x) for x in a}), 6)
            for r in a: self.assertEqual(r['source_row'], f.sources[r['task']][r['index']])

    def test_normalized_old_context_and_internal_duplicates_are_excluded(self):
        with source_fixture() as f:
            source = copy.deepcopy(f.sources)
            source['piqa'][2]['goal'] = '  PIQA\tQUESTION\u30000  '
            source['piqa'][3]['goal'] = source['piqa'][4]['goal']
            packet, exclusions = m.select_packet(source, f.old['sources'], count=2)
            ids = {m.case_id(x) for x in packet}
            self.assertNotIn('piqa#2', ids); self.assertEqual(exclusions['piqa']['old_body_extra_excluded'], 1)
            self.assertEqual(len({m.body(r['task'], r['source_row']) for r in packet}), len(packet))

    def test_insufficient_distinct_new_context_is_a_hard_error(self):
        with source_fixture() as f:
            for row in f.sources['piqa']: row['goal'] = 'same'
            with self.assertRaisesRegex(ValueError, 'insufficient'): m.select_packet(f.sources, f.old['sources'], count=2)

    def test_prepare_packet_file_bytes_and_logical_objects_have_distinct_receipts(self):
        with source_fixture() as f:
            report = m.prepare(f.prepared, f.root)
            self.assertEqual(report['proof']['logical_source_packet_sha256'], m.PACKET_SHA)
            self.assertEqual(report['raw_manifest']['rows'], 6)
            self.assertEqual(report['actual_jsonl_concat_sha256'], report['raw_manifest']['concat_sha256'])
            self.assertNotEqual(report['actual_jsonl_concat_sha256'], m.PACKET_SHA)
            packet, _, _, proof = m.source_material(f.root)
            receipts = m.load_prepared(f.prepared, packet, proof, f.root)
            self.assertEqual(len(receipts), 3)

    def test_original_public_source_or_old_selection_byte_mutation_is_rejected(self):
        for target in ('datasets/bench/piqa.jsonl', m.OLD_REPORT):
            with source_fixture() as f:
                path = f.root / target; path.write_bytes(path.read_bytes() + b' ')
                with self.assertRaises(ValueError): m.source_material(f.root)

    def test_prepared_shard_mutation_is_rejected_without_any_runtime(self):
        with source_fixture() as f:
            m.prepare(f.prepared, f.root); packet, _, _, proof = m.source_material(f.root)
            path = f.prepared / 'cases_000000.jsonl'; path.write_bytes(path.read_bytes() + b' ')
            with self.assertRaises(ValueError): m.load_prepared(f.prepared, packet, proof, f.root)

    def test_prepare_code_receipts_cannot_be_silently_replaced(self):
        with source_fixture() as f:
            m.prepare(f.prepared, f.root); packet, _, _, proof = m.source_material(f.root)
            (f.root / 'scripts/frozen.py').write_text('# changed after prepare\n', encoding='utf-8')
            with self.assertRaises(ValueError): m.load_prepared(f.prepared, packet, proof, f.root)

    def test_new_output_existing_protected_traversal_and_symlink_guards(self):
        with source_fixture() as f:
            f.output.mkdir(parents=True)
            for value in (f.output, f.root / 'datasets/new', f.root / 'runs/ckpt/new',
                    f.root / 'datasets/TinyDataset/nope', f.root / 'data_cache/../escape'):
                with self.assertRaises((ValueError, FileExistsError)): m.output_path(value, f.root)
            link = f.root / 'data_cache/link'; link.parent.mkdir(exist_ok=True); link.symlink_to(f.output, target_is_directory=True)
            with self.assertRaises(ValueError): m.output_path(link / 'new', f.root)

    def test_lf_jsonl_keeps_unicode_line_separator_inside_string(self):
        with tempfile.TemporaryDirectory(prefix='public_jsonl_') as folder:
            path = Path(folder) / 'rows.jsonl'; path.write_text('{"text":"a\u2028b"}\n', encoding='utf-8')
            self.assertEqual(m.read_jsonl(path), [dict(text='a\u2028b')])
            path.write_text('{"x":1,"x":2}\n', encoding='utf-8')
            with self.assertRaises(ValueError): m.read_jsonl(path)


class ScoringAndBudgetTests(Guarded):
    def test_sum_primary_is_separate_from_mean_character_normalization(self):
        with source_fixture() as f:
            diagnostic = m.score_diagnostics(fake_scores(f.plans[0]), f.plans[0])
            score = fake_scores(f.plans[0]); self.assertEqual(score['pred_harness'], 0)
            self.assertEqual(score['pred_internal'], 1); self.assertEqual(score['pred_harness_norm'], 1)
            self.assertIn('primary_correct', diagnostic)

    def test_literal_first_index_ties_are_preserved_and_diagnosed(self):
        with source_fixture() as f:
            plan = f.plans[0]; score = fake_scores(plan)
            score['sum_nll'] = [2., 2.]; score['mean_nll'] = [2., 2 / 3]; score['score'] = score['mean_nll'][:]
            self.assertTrue(m.score_diagnostics(score, plan)['sum_nll_tie'])
            self.assertEqual(score['pred_harness'], 0)

    def test_wrong_id_gold_count_predictions_and_nonfinite_are_rejected(self):
        with source_fixture() as f:
            plan = f.plans[0]
            for field, value in (('id', 'other'), ('gold', 100), ('n_tokens', [2, 3]),
                    ('pred_harness', 1), ('pred_internal', 0), ('sum_nll', [float('nan'), 2.])):
                score = fake_scores(plan); score[field] = value
                with self.assertRaises(ValueError): m.score_diagnostics(score, plan)

    def test_empty_and_overlength_are_retained_not_truncated_or_replaced(self):
        with source_fixture() as f:
            def adapted(row):
                value = adapter(row); value['choices'][0] = 'EMPTY' if row['task'] == 'piqa' else 'LONG'
                return value
            plans = m.adapt_plans(f.packet, f.sources, f.old, {t: adapted for t in m.TASKS}, Tokenizer())
            self.assertEqual(len(plans), 6)
            self.assertEqual({p['reason'] for p in plans}, {'empty_continuation', 'seq_max_exceeded'})
            self.assertEqual(len(plans[-1]['encoding']['continuation_ids'][0]), 1024)

    def test_surface_blank_option_is_excluded_even_if_tokenizer_returns_a_token(self):
        with source_fixture() as f:
            def adapted(row):
                value = adapter(row); value['choices'][0] = '  '; return value
            plans = m.adapt_plans(f.packet, f.sources, f.old, {t: adapted for t in m.TASKS}, Tokenizer())
            self.assertTrue(all(p['reason'] == 'empty_continuation' for p in plans))
            self.assertTrue(all(p['encoding']['continuation_ids'][0] for p in plans))

    def test_all_excluded_denominator_is_none_and_no_fake_zero_score(self):
        with source_fixture() as f:
            plans = copy.deepcopy(f.plans)
            for p in plans: p['reason'] = 'seq_max_exceeded'
            events = [dict(p, scores=None, diagnostics=None) for p in plans]
            summary = m.summarize(events, plans)
            self.assertIsNone(summary['accuracy']); self.assertEqual(summary['scored'], 0)
            self.assertTrue(all(c['accuracy'] is None for c in summary['by_task'].values()))

    def test_missing_duplicate_or_source_mutation_is_rejected(self):
        with source_fixture() as f:
            events = [dict(p, scores=fake_scores(p), diagnostics=m.score_diagnostics(fake_scores(p), p)) for p in f.plans]
            variants = [events[:-1], events + [events[0]]]
            changed = copy.deepcopy(events); changed[0]['source']['index'] += 1; variants.append(changed)
            for values in variants:
                with self.assertRaises(ValueError): m.summarize(values, f.plans)

    def test_aware_deadline_current_authorization_and_monotonic_cap(self):
        now = datetime(2026, 10, 22, 6, tzinfo=timezone.utc)
        deadline = m.parse_deadline('2026-10-22T16:00:00+09:00', now)
        for value in ('2026-10-22T16:00:00', '2026-10-22T05:59:59Z', '2026-10-23T00:00:00Z'):
            with self.assertRaises(ValueError): m.parse_deadline(value, now)
        clock = [0.]; budget = m.Budget(60, deadline, now=lambda: now, clock=lambda: clock[0])
        clock[0] = 60.
        with self.assertRaises(TimeoutError): budget.check()
        with self.assertRaises(TimeoutError): m.Budget(60, deadline, now=lambda: deadline, clock=lambda: 0.)

    def test_counter_counts_real_attempt_and_completion_not_estimate(self):
        route = NS(assert_active=Mock()); model = Mock(return_value='logits')
        counter = m.ForwardCounter(model, route, FakeBudget())
        self.assertEqual(counter(NS(shape=(1, 3))), 'logits'); self.assertEqual((counter.attempted, counter.completed), (1, 1))
        model.side_effect = RuntimeError('synthetic failure')
        with self.assertRaises(RuntimeError): counter(NS(shape=(1, 3)))
        self.assertEqual((counter.attempted, counter.completed), (2, 1))
        with self.assertRaises(ValueError): counter(NS(shape=(2, 3)))


class OrchestrationTests(Guarded):
    def test_success_calls_literal_api_once_per_case_and_publishes_after_exit(self):
        with source_fixture() as f:
            before = m.receipts([m.OLD_REPORT, *('datasets/bench/' + t + '.jsonl' for t in m.TASKS)], f.root)
            m.prepare(f.prepared, f.root); result, opened, calls, model = self.evaluate_fake(f)
            self.assertEqual(opened, ['native595-f']); self.assertEqual(calls, [p['id'] for p in f.plans])
            self.assertEqual(len(set(calls)), 6); self.assertEqual(result['forward_completed'], model.call_count)
            self.assertEqual(model.call_count, 20); self.assertTrue(result['strict_context_exit_verified'])
            self.assertEqual(result['status'], 'PUBLIC_MC_NEW768_COMPLETE')
            self.assertEqual(m.receipts(before, f.root), before)
            self.assertEqual(json.loads((f.output / 'report.json').read_text())['summary'], result['summary'])

    def test_other_two_fixed_models_use_same_cases_with_exact_qf_route(self):
        for name, mode in (('native595-q', 'ternary'), ('new595-broad-f', 'float')):
            with source_fixture() as f:
                m.prepare(f.prepared, f.root); result, opened, calls, model = self.evaluate_fake(f, model_name=name)
                self.assertEqual(opened, [name]); self.assertEqual(result['lineage']['quantization_route']['mode'], mode)
                self.assertEqual(calls, [p['id'] for p in f.plans]); self.assertEqual(model.call_count, 20)

    def test_strict_exit_failure_keeps_full_raw_but_never_success_report(self):
        with source_fixture() as f:
            m.prepare(f.prepared, f.root)
            with self.assertRaisesRegex(RuntimeError, 'exit'):
                self.evaluate_fake(f, exit_hook=lambda: (_ for _ in ()).throw(RuntimeError('strict exit failure')))
            self.assertFalse((f.output / 'report.json').exists())
            manifest = json.loads((f.output / 'answers_shards_manifest.json').read_text())
            self.assertEqual(manifest['rows'], 6); m.verify(f.output, manifest)
            self.assertFalse(json.loads((f.output / 'error.json').read_text())['strict_context_exit_verified'])

    def test_source_mutation_at_exit_fails_even_after_strict_context_succeeded(self):
        with source_fixture() as f:
            m.prepare(f.prepared, f.root)
            def mutate():
                path = f.root / 'datasets/bench/piqa.jsonl'; path.write_bytes(path.read_bytes() + b' ')
            with self.assertRaises(ValueError): self.evaluate_fake(f, exit_hook=mutate)
            self.assertFalse((f.output / 'report.json').exists()); self.assertTrue((f.output / 'error.json').exists())

    def test_failure_mid_batch_preserves_prefix_raw_and_actual_forward_attempts(self):
        with source_fixture() as f:
            m.prepare(f.prepared, f.root); calls = []
            def fail(item):
                calls.append(item['_iid'])
                if len(calls) == 2: raise RuntimeError('synthetic interrupted row')
            with self.assertRaises(RuntimeError): self.evaluate_fake(f, score_hook=fail)
            manifest = json.loads((f.output / 'answers_shards_manifest.json').read_text())
            self.assertEqual(manifest['rows'], 1); self.assertEqual(manifest['lineage']['status'], 'INCOMPLETE')
            error = json.loads((f.output / 'error.json').read_text()); self.assertEqual(error['forward_completed'], 4)
            self.assertFalse((f.output / 'report.json').exists()); m.verify(f.output, manifest)

    def test_chunk_receipts_include_first_chunk_without_replaying_it(self):
        with source_fixture() as f, redirect_stdout(io.StringIO()):
            f.output.mkdir(parents=True); budget = FakeBudget(); counter = NS(attempted=0, completed=0); calls = []
            def score(p):
                calls.append(p['id']); counter.completed += len(p['item']['choices']); counter.attempted = counter.completed
                return fake_scores(p)
            result, events = m.collect(f.output, f.plans, dict(plans_sha256=m.common.sha(f.plans)), score, counter, budget, chunk=2)
            self.assertEqual([p['cases'] for p in result['progress']], [2, 4, 6])
            self.assertEqual(calls, [p['id'] for p in f.plans]); self.assertEqual(len(events), 6)
            self.assertGreater(result['progress'][0]['chunk_seconds'], 0.01)

    def test_scorer_input_mutation_or_wrong_forward_count_aborts(self):
        for mutate in (False, True):
            with source_fixture() as f, redirect_stdout(io.StringIO()):
                f.output.mkdir(parents=True); counter = NS(attempted=0, completed=0)
                def score(p):
                    if mutate: p['item']['ctx'] += ' MUTATED'
                    else: counter.completed += 1
                    return fake_scores(p)
                with self.assertRaises(ValueError):
                    m.collect(f.output, f.plans, dict(plans_sha256=m.common.sha(f.plans)), score, counter, FakeBudget())

    def test_all_excluded_collect_never_calls_scorer_or_publishes_fake_zero(self):
        with source_fixture() as f, redirect_stdout(io.StringIO()):
            plans = copy.deepcopy(f.plans)
            for p in plans: p['reason'] = 'seq_max_exceeded'
            f.output.mkdir(parents=True); scorer = Mock(side_effect=AssertionError('no ineligible forwards'))
            with self.assertRaisesRegex(ValueError, 'no eligible'):
                m.collect(f.output, plans, dict(plans_sha256=m.common.sha(plans)), scorer,
                    NS(attempted=0, completed=0), FakeBudget())
            scorer.assert_not_called(); self.assertFalse((f.output / 'report.json').exists())
            manifest = json.loads((f.output / 'answers_shards_manifest.json').read_text())
            self.assertEqual(manifest['rows'], 6)
            raw = m.read_jsonl(f.output / manifest['shards'][0]['path'])
            self.assertTrue(all(e['scores'] is None for e in raw))

    def test_direct_evaluate_without_execute_is_refused_before_sources(self):
        with patch.object(m, 'source_material', side_effect=AssertionError('no source access')):
            with self.assertRaises(ValueError): m.evaluate(NS(execute=False, model='native595-f', max_wall_sec=60))


class CLITests(Guarded):
    def test_argument_validation_never_enters_any_runtime_or_asset_reader(self):
        with patch.object(m, 'source_material', side_effect=AssertionError('no assets')), redirect_stderr(io.StringIO()):
            for argv in (['evaluate'], ['evaluate', '--execute', '--model', 'native595-f'],
                    ['prepare'], ['check-only', '--execute'], ['check-only', '--model', 'old299-broad-f'],
                    ['check-only', '--max-wall-sec', '0'], ['check-only', '--source-root', '/tmp'],
                    ['prepare', '--output', 'data_cache/new', '--model', 'native595-f']):
                with self.assertRaises(SystemExit): m.main(argv)

    def test_code_only_does_not_open_assets_or_import_torch(self):
        with patch.object(m, 'source_material', side_effect=AssertionError('no assets')), \
                patch.object(m, 'load_prepared', side_effect=AssertionError('no prepared assets')), redirect_stdout(io.StringIO()) as out:
            self.assertEqual(m.main(['check-only']), 0)
        value = json.loads(out.getvalue().split('] ', 1)[1]); self.assertEqual(value['asset_opens'], 0)
        self.assertEqual(value['torch_imports'], 0); self.assertEqual(value['writes'], 0)

    def test_direct_script_help_and_code_only_work_without_torch(self):
        script = ROOT / 'scripts/p106b_public_mc_extension.py'
        program = """import builtins,runpy,sys
original=builtins.__import__
def guarded(name,*args,**kwargs):
    if name.split('.')[0] in ('torch','tokenizers','tinylm'):
        raise AssertionError('forbidden actual ML import: '+name)
    return original(name,*args,**kwargs)
builtins.__import__=guarded
sys.argv=[sys.argv[1]]+sys.argv[2:]
runpy.run_path(sys.argv[0],run_name='__main__')
"""
        for mode in ('--help', 'check-only'):
            value = subprocess.run([sys.executable, '-B', '-X', 'utf8', '-c', program, str(script), mode],
                cwd=ROOT, text=True, capture_output=True, timeout=20)
            self.assertEqual(value.returncode, 0, value.stderr)

    def test_atomic_report_guard_is_write_once_and_below20mb(self):
        with tempfile.TemporaryDirectory(prefix='public_report_') as folder:
            path = Path(folder) / 'report.json'; m.common.atomic_json(path, dict(ok=True))
            before = path.read_bytes()
            with self.assertRaises(FileExistsError): m.common.atomic_json(path, dict(ok=False))
            self.assertEqual(path.read_bytes(), before)
            with patch.object(m.common, 'LIMIT', 80):
                with self.assertRaises(ValueError): m.common.atomic_json(Path(folder) / 'huge.json', dict(text='x' * 90))


if __name__ == '__main__': unittest.main()
