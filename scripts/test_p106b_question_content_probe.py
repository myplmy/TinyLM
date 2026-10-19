"""Synthetic/temp-only tests; actual source/model/tokenizer/GPU consumers mocked."""
from __future__ import annotations

from contextlib import ExitStack, nullcontext, redirect_stdout
import copy
from datetime import datetime, timedelta, timezone
import io
import json
import math
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import diag_p106b_question_content_probe as probe
from scripts import p106b_question_transfer_data as data


class FakeTokenizer:
    def __init__(self):
        self.ids = {}; self.words = {}; self.next = 10

    def token_to_id(self, word):
        return {'<pad>': 0, '<eos>': 2, '<|im_end|>': 4}[word]

    def encode(self, text):
        result = []
        for word in text:
            if word not in self.ids:
                self.ids[word] = self.next; self.words[self.next] = word; self.next += 1
            result.append(self.ids[word])
        return SimpleNamespace(ids=result, offsets=[(i, i + 1) for i in range(len(text))])

    def decode(self, ids, skip_special_tokens=False):
        return ''.join(self.words[i] for i in ids)


def serialized(messages):
    assert all(m['role'] == 'user' for m in messages)
    return 'USER\n' + messages[0]['content'] + '\nASSISTANT\n'


class FakeUpstream:
    @staticmethod
    def encode_row(row, tok):
        prompt = serialized(row['messages'][:1]); p = tok.encode(prompt).ids
        target = tok.encode(row['messages'][1]['content']).ids + [4]
        x = p + target[:-1]; y = [-100] * (len(p) - 1) + target
        owners = [0] * (len(p) - 1) + [1] * len(target)
        record = SimpleNamespace(x=x, y=y, segments=owners, x_tokens=len(x), targets=len(target))
        return record, dict(row_sha256=probe.sha(row), prompt_sha256=probe.sha(prompt),
            prompt_ids_sha256=probe.sha(p), prompt_tokens=len(p),
            target_ids_sha256=probe.sha(target), assistant_targets=len(target), eot_targets=1)

    @staticmethod
    def wire(record, identity, lane, language, parent, evidence=None):
        return dict(id=identity, lane=lane, language=language, parent_group_id=parent,
            x=list(record.x), y=list(record.y), segments=list(record.segments),
            x_tokens=record.x_tokens, assistant_targets=record.targets, encoding=evidence,
            record_sha256=probe.sha(dict(x=record.x, y=record.y, segments=record.segments)))

    @staticmethod
    def schedule(epoch):
        indices = list(range(12288))
        return [[indices[start + m * 8:start + (m + 1) * 8] for m in range(16)]
                for start in range(0, 12288, 128)]


def generation(case, answer, ids):
    content = ids[:-1]
    return dict(max_new=64, precision='FP32_MATH', temperature=0., top_k=1,
        use_cache=True, mtp=False, candidate_answers_supplied=False, terminal_only_removed=True,
        stop_token_sequences=[[4]], generated_ids=ids, terminal_ids=[4], generated_tokens=len(ids),
        generated_ids_sha256=probe.sha(ids), content_ids_sha256=probe.sha(content),
        finish_reason='STOP_SEQUENCE', matched_stop_sequence=[4],
        body_utf8_sha256=__import__('hashlib').sha256(answer.encode()).hexdigest().upper(),
        **{k: case['encoding'][k] for k in ('prompt_sha256', 'prompt_ids_sha256', 'prompt_tokens')})


class Fixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.course = data.build_course()
        cls.tok = FakeTokenizer()
        with mock.patch.object(probe, 'serialize_messages', side_effect=serialized):
            cls.cases = probe.build_cases(cls.course, cls.tok, FakeUpstream())
        cls.frozen = dict(eot_id=4, eos_id=2, pad_id=0, cases_sha256=probe.sha(cls.cases),
            display_ids=probe.display_ids(cls.cases), display_sha256=probe.sha(probe.display_ids(cls.cases)),
            d_pairs=probe.d_pairs(cls.cases))

    def score(self, case, other=None):
        width = self.tok.next + 2
        rows = []
        for target in case['target_ids']:
            vector = [0.] * width; vector[target] = 3.
            rows.append(probe.score_vector(vector, target, 4, 2))
        first_vector = [0.] * width; first_vector[case['target_ids'][0]] = 3.
        first = probe.score_vector(first_vector, case['target_ids'][0], 4, 2, other)
        return dict(targets=rows, first_full=rows[0], first_prefix=first,
            first_predictor_position=len(case['prompt_ids']) - 1,
            first_prefix_ids_sha256=probe.sha(case['prompt_ids']),
            prefix_vs_full_max_abs=0., prefix_vs_full_argmax_equal=True,
            precision='FP32_MATH', no_grad=True, full_head='NORMAL_FULL_SEQUENCE')

    def events(self, *, empty=False):
        lookup = {probe.sha(c['messages']): c for c in self.cases}

        def generate(messages):
            self.assertTrue(all(m['role'] == 'user' for m in messages))
            case = lookup[probe.sha(messages)]
            answer = '' if empty else case['gold']
            ids = [4] if empty else list(case['target_ids'])
            return answer, generation(case, answer, ids)

        collected = []
        result = probe.evaluate_cases(self.cases, self.frozen, self.score, generate,
                                      {'endpoint': 'SYNTHETIC_ONLY'}, collected.append)
        self.assertEqual(collected, result)
        return result


class SelectionAndEncodingTests(Fixture):
    def test_source_first64_and256_layout_preserves_whole_groups(self):
        selected = probe.select_problems(self.course)
        self.assertEqual(len(selected), 64)
        self.assertEqual(len(self.cases), 256)
        for split in ('train', 'test'):
            for family in data.FAMILIES:
                rows = [p for p in selected if p['split'] == split and p['family'] == family]
                self.assertEqual(len(rows), 8)
                if family in ('lookup', 'format'):
                    sizes = __import__('collections').Counter(p['parent_group_id'] for p in rows)
                    self.assertEqual(set(sizes.values()), {4 if family == 'lookup' else 2})
        self.assertEqual({c['wording'] for c in self.cases}, {0, 2})
        self.assertEqual({c['position'] for c in self.cases}, {'CQ'})
        self.assertTrue(all([m['role'] for m in c['messages']] == ['user'] for c in self.cases))

    def test_display_and_d_selection_do_not_use_model_answers(self):
        before = copy.deepcopy(self.cases)
        selected = probe.display_ids(self.cases); pairs = probe.d_pairs(self.cases)
        self.assertEqual(len(selected), 16)
        self.events(empty=True)
        self.assertEqual(probe.display_ids(self.cases), selected)
        self.assertEqual(probe.d_pairs(self.cases), pairs)
        self.assertEqual(self.cases, before)

    def test_exact_shift_mask_prompt_target_and_eot_contract(self):
        for case in self.cases:
            positions = probe.validate_encoding(case, 4)
            self.assertEqual(positions[0], len(case['prompt_ids']) - 1)
            self.assertEqual(case['target_ids'][-1], 4)
            self.assertLessEqual(len(case['target_ids']), 64)
            self.assertLessEqual(len(case['prompt_ids']) + 64, 1024)
            self.assertGreater(case['lengths']['context_tokens'], 0)
            self.assertGreater(case['lengths']['question_tokens'], 0)

    def test_causal_off_by_one_and_owner_tamper_rejected(self):
        for mutation in ('prefix', 'shift', 'owner', 'target'):
            case = copy.deepcopy(self.cases[0]); k = len(case['prompt_ids']) - 1
            if mutation == 'prefix': case['wire']['x'][0] += 1
            if mutation == 'shift': case['wire']['y'][k], case['wire']['y'][k - 1] = -100, case['wire']['y'][k]
            if mutation == 'owner': case['wire']['segments'][k] = 0
            if mutation == 'target': case['target_ids'][0] += 1
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                probe.validate_encoding(case, 4)

    def test_bpe_boundary_straddle_is_not_standalone_gold_encoding(self):
        case = copy.deepcopy(self.cases[0])
        case['prompt_ids'][-1] += 1
        with self.assertRaises(ValueError):
            probe.validate_encoding(case, 4)

    def test_one_token_d_requires_same_question_different_context_and_target(self):
        byid = {c['id']: c for c in self.cases}
        for pair in probe.d_pairs(self.cases):
            a, b = byid[pair['left']], byid[pair['right']]
            self.assertEqual(len(a['target_ids']), 2); self.assertEqual(len(b['target_ids']), 2)
            self.assertEqual(a['question_sha256'], b['question_sha256'])
            self.assertNotEqual(a['context_sha256'], b['context_sha256'])
            self.assertNotEqual(a['target_ids'][0], b['target_ids'][0])
        self.assertEqual(probe.d_pairs([c for c in self.cases if c['family'] == 'format']), [])


class MetricTests(Fixture):
    def test_global_rank_tie_interval_is_not_strict_argmax_success(self):
        row = probe.score_vector([3., 3., 1., 0., -1.], 1, 4, 2)
        self.assertEqual((row['rank_low'], row['rank_high'], row['ties']), (1, 2, 2))
        self.assertFalse(row['argmax_correct'])
        self.assertEqual(row['margin_any_nongold'], 0.)
        probe.validate_target(row, 1, 4, 2)

    def test_impossible_argmax_rank_and_missing_competitor_are_rejected(self):
        original = probe.score_vector([3., 2., 1., 0.], 0, 2, 3)
        mutations = [dict(argmax_id=1, argmax_logit=100., argmax_correct=False),
            dict(rank_low=2, rank_high=2, ties=1),
            dict(best_any_nongold_id=None, best_any_nongold_logit=None, margin_any_nongold=None)]
        for change in mutations:
            row = dict(original, **change)
            with self.subTest(change=change), self.assertRaises(ValueError):
                probe.validate_target(row, 0, 2, 3)

    def test_terminal_self_logits_and_observed_ties_are_consistent(self):
        for target in (2, 3):
            row = probe.score_vector([1., 0., 3., 2.], target, 2, 3)
            probe.validate_target(row, target, 2, 3)
            row['eot_logit'] -= .5; row['margin_eot'] += .5
            with self.subTest(target=target), self.assertRaises(ValueError):
                probe.validate_target(row, target, 2, 3)
        row = probe.score_vector([3., 3., 3., 0.], 1, 2, 3)
        row.update(rank_high=2, ties=2)
        with self.assertRaises(ValueError): probe.validate_target(row, 1, 2, 3)

    def test_offline_pair_token_id_and_absent_gap_are_bound(self):
        row = probe.score_vector([3., 2., 1., 0.], 0, 2, 3, other=1)
        probe.validate_target(row, 0, 2, 3, other=1)
        with self.assertRaises(ValueError): probe.validate_target(row, 0, 2, 3, other=3)
        row = probe.score_vector([3., 2., 1., 0.], 0, 2, 3)
        row['d_gap'] = 1.
        with self.assertRaises(ValueError): probe.validate_target(row, 0, 2, 3)

    def test_any_nongold_and_nonterminal_competitors_are_separate(self):
        row = probe.score_vector([1., .5, 4., 2., 3.], 0, 4, 2)
        self.assertEqual(row['best_any_nongold_id'], 2)
        self.assertEqual(row['best_nongold_nonterminal_id'], 3)
        self.assertEqual(row['margin_eot'], -2.)
        self.assertEqual(row['margin_eos'], -3.)
        probe.validate_target(row, 0, 4, 2)

    def test_content_and_eot_counts_boolean_baselines_and_all256_closure(self):
        events = self.events(); result = probe.recount(events, self.cases, self.frozen, tok=self.tok)
        self.assertEqual(result['actual_answers'], 256)
        self.assertEqual(len(result['cells']), 32)
        self.assertEqual(sum(v['n'] for v in result['cells']), 256)
        self.assertEqual(sum(v['eot_targets'] for v in result['cells']), 256)
        self.assertEqual(result['neutral_query_count'], 64)
        self.assertNotIn('independent_neutral_queries', result)
        parents = {(p['split'], p['family']): p['parent_groups'] for p in result['family_parent_group_counts']}
        self.assertEqual(parents[('train', 'lookup')], 2)
        self.assertEqual(parents[('train', 'format')], 4)
        self.assertIn('not independently recomputed', result['numerical_readback_scope'])
        self.assertTrue(all(v['correct'] == 8 for v in result['cells']))
        for cell in result['cells']:
            self.assertEqual(cell['content_ce'], cell['content_nll'] / cell['content_targets'])
            if cell['stratum'][1] == 'boolean':
                self.assertEqual(cell['gold_true'] + cell['gold_false'], 8)
                self.assertEqual(cell['constant_false_correct'], cell['gold_false'])

    def test_bad_model_answers_are_technical_completion_not_tool_errors(self):
        events = self.events(empty=True)
        result = probe.recount(events, self.cases, self.frozen, tok=self.tok)
        self.assertEqual(result['actual_answers'], 256)
        self.assertEqual(sum(v['correct'] for v in result['cells']), 0)
        self.assertEqual(sum(v['tf_perfect_free_ids_differ'] for v in result['cells']), 256)
        self.assertTrue(all(e['path_flag_scope'].startswith('numeric/path') for e in events))

    def test_partial_duplicate_and_corrupt_raw_are_not_counted_as_wrong(self):
        events = self.events()
        with self.assertRaises(probe.Pending): probe.recount(events[:-1], self.cases, self.frozen)
        duplicate = copy.deepcopy(events); duplicate[-1] = duplicate[0]
        with self.assertRaises(probe.Pending): probe.recount(duplicate, self.cases, self.frozen)
        corrupt = copy.deepcopy(events); corrupt[0]['tf']['targets'][0]['nll'] += .01
        with self.assertRaises(ValueError): probe.recount(corrupt, self.cases, self.frozen)

    def test_terminal_and_length_first_divergences_are_preserved(self):
        a = probe.divergence([10, 4], [10], [7, 8])
        self.assertEqual(a['index'], 1); self.assertFalse(a['reached'])
        self.assertEqual(a['mechanism'], 'UNRESOLVED_BEYOND_FIRST')
        b = probe.divergence([10, 4], [10, 2], [7, 8])
        self.assertEqual(b['reference_id'], 4); self.assertEqual(b['generated_id'], 2)
        self.assertTrue(b['reached']); self.assertTrue(b['equal_prefix'])
        self.assertEqual(b['reference_prefix_sha256'], b['actual_prefix_sha256'])

    def test_json_syntax_key_payload_strict_and_bytes_are_distinct(self):
        case = next(c for c in self.cases if c['family'] == 'format')
        p = case['problem']; key = p['query']['key']; literal = p['state']['literal']
        self.assertTrue(probe.json_metrics(p, case['gold'])['strict'])
        duplicate = '{"' + key + '":"' + literal + '","' + key + '":"' + literal + '"}'
        m = probe.json_metrics(p, duplicate)
        self.assertTrue(m['syntax']); self.assertFalse(m['unique_keys']); self.assertFalse(m['strict'])
        m = probe.json_metrics(p, json.dumps({key: int(literal)}))
        self.assertTrue(m['requested_key_set']); self.assertFalse(m['payload_string_exact'])
        m = probe.json_metrics(p, json.dumps({'other': literal}))
        self.assertFalse(m['requested_key_set'])
        alternate = json.dumps({key: literal}, separators=(',', ':'))
        ids = self.tok.encode(alternate).ids + [4]
        m = probe.answer_metrics(case, alternate, ids)
        self.assertTrue(m['correct']); self.assertEqual(m['canonical_body_bytes_equal'], alternate == case['gold'])

    def test_deeply_nested_bad_json_remains_an_answer_failure(self):
        problem = next(c['problem'] for c in self.cases if c['family'] == 'format')
        metrics = probe.json_metrics(problem, '[' * 2000 + '0' + ']' * 2000)
        self.assertFalse(metrics['syntax']); self.assertFalse(metrics['strict'])

    def test_generation_receipt_preserves_empty_eot_and_rejects_hash_corruption(self):
        case = self.cases[0]; g = generation(case, '', [4])
        probe.validate_generation(case, '', g, self.frozen, self.tok)
        g['generated_ids_sha256'] = '0' * 64
        with self.assertRaises(ValueError): probe.validate_generation(case, '', g, self.frozen)

    def test_cpu_tensor_logit_implementation_matches_synthetic_reference(self):
        import torch
        vectors = [[3., 3., 0., -1., 1.], [-1., 0., .5, 3., 2.]]
        actual = probe.score_tensor(torch.tensor(vectors, device='cpu'), [1, 3], 4, 2, other=0)
        for row, vector, target in zip(actual, vectors, [1, 3]):
            expected = probe.score_vector(vector, target, 4, 2, other=0)
            for key in ('argmax_id', 'argmax_correct', 'rank_low', 'rank_high', 'ties',
                        'best_any_nongold_id', 'best_nongold_nonterminal_id'):
                self.assertEqual(row[key], expected[key])
            for key in ('nll', 'gold_logit', 'margin_eot', 'margin_eos', 'd_gap'):
                self.assertAlmostEqual(row[key], expected[key], places=5)


class MembershipTests(Fixture):
    def setup_projection(self):
        zero = next(c for c in self.cases if c['split'] == 'train' and c['wording'] == 0)
        two = next(c for c in self.cases if c['problem']['query_id'] == zero['problem']['query_id']
                   and c['language'] == zero['language'] and c['wording'] == 2)
        up = SimpleNamespace(CORPUS=Path('/MOCK_SOURCE_ONLY'), schedule=FakeUpstream.schedule)
        projection = dict(upstream=up, frozen={'manifests': {}, 'exposure': {}}, training={})
        rows = {}
        for arm in probe.ARMS:
            projection['frozen']['exposure'][arm] = []
            projection['training'][arm] = dict(events=[dict(update=i + 1) for i in range(384)],
                                               manifest_sha256='M', report_sha256='R')
            for epoch in range(4):
                stem = arm + '_e' + str(epoch + 1)
                projection['frozen']['manifests'][stem] = dict(shards=[dict(path=stem + '_000000.jsonl', rows=1)])
                projection['frozen']['exposure'][arm].append(dict(schedule_sha256=probe.sha(up.schedule(epoch))))
                if data.schedule_view(zero['problem'], arm, epoch) == dict(wording=0, position='CQ'):
                    wire = copy.deepcopy(zero['wire'])
                    wire['id'] = probe.sha(['CODED', zero['problem']['query_id'], zero['language']])
                else:
                    wire = dict(x=[32000], y=[4], segments=[1], id='OTHER', record_sha256='OTHER')
                rows[stem] = [wire]
        return projection, [zero, two], rows

    def test_actual_wire_membership_is_four_vs_one_not_renderer_only(self):
        projection, cases, rows = self.setup_projection()
        with mock.patch.object(probe, 'read_rows', side_effect=lambda d, m, stem, n, **k: rows[stem]):
            proof = probe.membership(projection, cases)
        for arm, expected in (('fixed_last', 4), ('varied_balanced', 1)):
            self.assertEqual(proof[arm][cases[0]['id']]['prompt_prefix_seen_count'], expected)
            self.assertEqual(proof[arm][cases[0]['id']]['exact_full_record_matches'], expected)
            self.assertEqual(proof[arm][cases[1]['id']]['prompt_prefix_seen_count'], 0)

    def test_same_prefix_wrong_target_owner_or_mask_is_not_unseen(self):
        for what in ('target', 'owner', 'mask'):
            projection, cases, rows = self.setup_projection()
            case = cases[1]; wire = copy.deepcopy(case['wire']); k = len(case['prompt_ids']) - 1
            if what == 'target': wire['y'][k] += 1
            if what == 'owner': wire['segments'][k] += 1
            if what == 'mask': wire['y'][k] = -100
            wire['assistant_targets'] = sum(y != -100 for y in wire['y'])
            wire['record_sha256'] = probe.sha({k: wire[k] for k in ('x', 'y', 'segments')})
            # Prefix belongs to T2, even with a different supervised target/owner.
            rows['varied_balanced_e1'] = [wire]
            with self.subTest(what=what), \
                    mock.patch.object(probe, 'read_rows', side_effect=lambda d, m, stem, n, **k: rows[stem]), \
                    self.assertRaises(probe.Pending) as e:
                probe.membership(projection, cases)
            self.assertIn('not unseen', str(e.exception))

    def test_missing_executed_t0_wire_is_hold_not_a_seen_claim(self):
        projection, cases, rows = self.setup_projection()
        rows['fixed_last_e1'] = []
        with mock.patch.object(probe, 'read_rows', side_effect=lambda d, m, stem, n, **k: rows[stem]), \
                self.assertRaises(probe.Pending):
            probe.membership(projection, cases)


class TempFixture(Fixture):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='question_content_fixture_')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.stack = ExitStack(); self.addCleanup(self.stack.close)
        self.stack.enter_context(mock.patch.object(probe, 'ROOT', self.root))
        self.stack.enter_context(mock.patch.object(probe, 'CORPUS', self.root / 'corpus'))
        self.stack.enter_context(mock.patch.object(probe, 'LOCAL', self.root / 'local'))
        self.stack.enter_context(mock.patch.object(probe, 'EVIDENCE', self.root / 'evidence'))


class TempAndCliTests(TempFixture):

    def test_exact_stem_rejected_before_payload_hash_or_delegate(self):
        fake = SimpleNamespace(read_rows=mock.Mock())
        manifest = dict(schema='P106B_WRITE_ONCE_SHARDS_V1', rows=1,
            shards=[dict(path='/MOCK_PROTECTED/never.jsonl', bytes=10)])
        with mock.patch.object(probe, 'digest') as hashed, self.assertRaises(ValueError):
            probe.read_rows(self.root, manifest, 'coded', 1, up=fake)
        hashed.assert_not_called(); fake.read_rows.assert_not_called()

    def test_temp_shards_roundtrip_tamper_and_no_overwrite(self):
        directory = self.root / 'raw'; rows = [dict(id=i, value='가나다') for i in range(4)]
        manifest = probe.put(directory, 'fixture', rows, {'tag': 'SYNTHETIC_ONLY'})
        self.assertEqual(probe.read_rows(directory, manifest, 'fixture', 4), rows)
        with self.assertRaises(FileExistsError): probe.put(directory, 'fixture', rows, {})
        path = directory / 'fixture_000000.jsonl'; path.write_bytes(path.read_bytes() + b'{}\n')
        with self.assertRaises(ValueError): probe.read_rows(directory, manifest, 'fixture', 4)

    def test_topdown_symlink_rejected_before_descendant_metadata(self):
        seen = []
        def linked(path):
            seen.append(str(path)); return path == self.root / 'linked'
        with mock.patch.object(Path, 'is_symlink', autospec=True, side_effect=linked), self.assertRaises(ValueError):
            probe.safe(self.root / 'linked/deep/file')
        self.assertEqual(seen, [str(self.root), str(self.root / 'linked')])

    def test_check_only_all_modes_are_source_free_and_never_launch_children(self):
        for mode in probe.MODES:
            args = ['--mode', mode, '--check-only']
            if mode == 'evaluate': args += ['--endpoint', 'parent']
            with self.subTest(mode=mode), mock.patch.object(probe, 'upstream') as up, \
                    mock.patch.object(probe.subprocess, 'run') as child, redirect_stdout(io.StringIO()):
                self.assertEqual(probe.main(args), 0)
            up.assert_not_called(); child.assert_not_called()

    def test_public_pipeline_actually_invokes_three_mock_phases_with_devnull(self):
        for mode in ('prepare', 'preflight', 'evaluate', 'readback', 'source'):
            args = ['--mode', mode, '--execute']
            if mode == 'evaluate': args += ['--endpoint', 'fixed_last']
            with self.subTest(mode=mode), \
                    mock.patch.object(probe.subprocess, 'run', return_value=SimpleNamespace(returncode=0)) as launch, \
                    redirect_stdout(io.StringIO()):
                self.assertEqual(probe.main(args), 0)
            self.assertEqual(launch.call_count, 3)
            self.assertTrue(all(c.kwargs['stdin'] == subprocess.DEVNULL for c in launch.call_args_list))
            for call in launch.call_args_list:
                command = call.args[0]
                expected = int(command[command.index('--max-wall-sec') + 1]) if '--max-wall-sec' in command else 300
                self.assertEqual(call.kwargs['timeout'], expected)

    def test_prepare_preflight_is_source_not_uncreated_new_corpus(self):
        phases = probe.phase_commands('prepare')
        self.assertEqual(phases[1][1][phases[1][1].index('--mode') + 1], 'source')
        self.assertEqual(phases[2][1][phases[2][1].index('--mode') + 1], 'prepare')

    def test_pipeline_hold_error_and_timeout_do_not_invoke_execute(self):
        for outcomes, expected in (([0, 8], 8), ([9], 9), ([0, 9], 9)):
            with self.subTest(outcomes=outcomes), \
                    mock.patch.object(probe.subprocess, 'run', side_effect=[SimpleNamespace(returncode=n) for n in outcomes]) as launch, \
                    redirect_stdout(io.StringIO()):
                self.assertEqual(probe.main(['--mode', 'prepare', '--execute']), expected)
            self.assertEqual(launch.call_count, len(outcomes))
        with mock.patch.object(probe.subprocess, 'run', side_effect=subprocess.TimeoutExpired('MOCK', 1)), redirect_stdout(io.StringIO()):
            self.assertEqual(probe.main(['--mode', 'prepare', '--execute']), 9)

    def test_worker_selectors_bounds_and_authority(self):
        for mode, endpoint, bound in (('evaluate', None, 600), ('prepare', 'parent', 300),
                                     ('prepare', None, 301), ('evaluate', 'parent', 601),
                                     ('prepare', None, 59), ('evaluate', 'parent', 1)):
            with self.subTest(mode=mode, endpoint=endpoint), self.assertRaises(ValueError):
                probe.phase_commands(mode, endpoint, bound)
        phases = probe.phase_commands('evaluate', 'parent', 60)
        self.assertEqual(phases[-1][1][phases[-1][1].index('--max-wall-sec') + 1], '60')
        with self.assertRaises(probe.Pending):
            probe.authority(1, probe.END - timedelta(seconds=3600))
        self.assertGreater(probe.authority(300, probe.END - timedelta(hours=2)), 300)

    def test_worker_modes_dispatch_with_bounded_mock_context_only(self):
        for mode, function in (('source', 'read_projection'), ('preflight', 'read_prepared')):
            with self.subTest(mode=mode), mock.patch.object(probe, 'authority'), \
                    mock.patch.object(probe, function) as worker, \
                    mock.patch.object(probe, 'wall_context', return_value=nullcontext()) as bounded, \
                    redirect_stdout(io.StringIO()):
                self.assertEqual(probe.run_worker(mode, None, 300), 0)
            worker.assert_called_once_with(); bounded.assert_called_once_with(300)

    def test_absolute_help_from_arbitrary_cwd_without_source_assets(self):
        before = Path.cwd()
        try:
            __import__('os').chdir(self.root)
            with mock.patch.object(sys, 'argv', [str(ROOT / probe.OWN_CODE[0]), '--help']), \
                    redirect_stdout(io.StringIO()), self.assertRaises(SystemExit) as e:
                runpy.run_path(str(ROOT / probe.OWN_CODE[0]), run_name='__main__')
            self.assertEqual(e.exception.code, 0)
        finally:
            __import__('os').chdir(before)


class ProjectionAndActivityTests(TempFixture):
    def frozen_diagnostic(self):
        up = FakeUpstream()
        up.natural = SimpleNamespace(TOK_SHA='A' * 64)
        projection = dict(upstream=up, course=self.course)
        for name, value in (('upstream', mock.Mock(return_value=up)),
                ('read_projection', mock.Mock(return_value=projection)),
                ('tokenizer', mock.Mock(return_value=self.tok)),
                ('membership', mock.Mock(return_value={'fixture': 'EXACT_EXPOSURES_MOCKED'})),
                ('source_binding', mock.Mock(return_value={'fixture': 'SCOPED_SOURCE'})),
                ('code_pins', mock.Mock(return_value={'fixture.py': 'B' * 64})),
                ('serialize_messages', mock.Mock(side_effect=serialized)),
                ('authority', mock.Mock()), ('wall_context', mock.Mock(return_value=nullcontext()))):
            self.stack.enter_context(mock.patch.object(probe, name, value))
        with redirect_stdout(io.StringIO()):
            self.assertEqual(probe.run_worker('prepare', None, 300), 0)
        return projection

    def receipt(self, mode, endpoint=None):
        started = datetime(2026, 1, 1, tzinfo=timezone.utc)
        return dict(probe.info(), mode=mode, endpoint=endpoint, returncode=0,
            status='COMPLETE', complete=True, seconds=.1, requested_limit=probe.LIMITS[mode],
            started_at=started.isoformat(), recorded_at=(started + timedelta(seconds=.1)).isoformat(),
            within_requested_time_and_authority=True,
            code_sha256=probe.code_pins(None), corpus_report_sha256=probe.digest(probe.CORPUS / 'report.json'))

    def test_prepare_closed_temp_roundtrip_reencodes_all256_cases(self):
        projection = self.frozen_diagnostic()
        report, cases, actual_projection = probe.read_prepared()
        self.assertEqual(cases, self.cases)
        self.assertIs(actual_projection, projection)
        self.assertEqual(report['status'], 'QUESTION_CONTENT_CPU_FROZEN')
        self.assertEqual(actual_projection['activity_prepare']['sha256'],
                         probe.digest(probe.activity_path('prepare')))
        self.assertEqual(probe.build_cases(self.course, self.tok, projection['upstream']), cases)
        with self.assertRaises(FileExistsError): probe.prepare()

    def test_missing_or_live_prepare_receipt_stops_before_source_projection(self):
        self.frozen_diagnostic()
        original = probe.required; path = probe.activity_path('prepare')
        for state in ('MISSING', 'RUNNING'):
            def fixture_required(p):
                if Path(p) == path:
                    if state == 'MISSING': raise probe.Pending('mock missing worker closure')
                    return dict(self.receipt('prepare'), status='RUNNING', returncode=None, complete=False)
                return original(p)
            probe.read_projection.reset_mock()
            with self.subTest(state=state), mock.patch.object(probe, 'required', side_effect=fixture_required), \
                    self.assertRaises(probe.Pending):
                probe.read_prepared()
            probe.read_projection.assert_not_called()

    def test_activity_identity_code_corpus_and_failure_status_cannot_be_relabelled(self):
        self.frozen_diagnostic(); baseline = self.receipt('prepare')
        mutations = [dict(mode='evaluate'), dict(endpoint='parent'), dict(tag='OTHER'),
            dict(code_sha256={}), dict(corpus_report_sha256='F' * 64),
            dict(status='COMPLETE', returncode=9), dict(complete=False), dict(requested_limit=59)]
        mutations += [dict(status=s, returncode=code, complete=False)
                      for s, code in (('TOOL_ERROR', 9), ('HOLD', 8), ('INTERRUPTED', 130))]
        for change in mutations:
            with self.subTest(change=change), mock.patch.object(probe, 'required', return_value=dict(baseline, **change)), \
                    self.assertRaises(ValueError):
                probe.completed_activity('prepare', None, baseline['corpus_report_sha256'])

    def test_activity_elapsed_timestamps_and_authority_have_no_hidden_tolerance(self):
        self.frozen_diagnostic(); baseline = self.receipt('prepare')
        changes = [dict(seconds=1e30), dict(seconds=300.000001), dict(recorded_at='not-time'),
            dict(recorded_at=None), dict(recorded_at='2026-10-19T12:00:00'),
            dict(within_requested_time_and_authority=False),
            dict(recorded_at=(probe.END - timedelta(seconds=3599)).isoformat()),
            dict(recorded_at=(probe.activity_time(baseline['started_at']) + timedelta(seconds=301)).isoformat()),
            dict(started_at=(probe.activity_time(baseline['recorded_at']) + timedelta(seconds=1)).isoformat())]
        for change in changes:
            with self.subTest(change=change), mock.patch.object(probe, 'required', return_value=dict(baseline, **change)), \
                    self.assertRaises(ValueError):
                probe.completed_activity('prepare', None, baseline['corpus_report_sha256'])

    def test_activity_future_timestamp_is_rejected_at_exact_aware_admission(self):
        self.frozen_diagnostic(); receipt = self.receipt('prepare')
        recorded = probe.activity_time(receipt['recorded_at'])
        with mock.patch.object(probe, 'required', return_value=receipt):
            with self.assertRaises(ValueError):
                probe.completed_activity('prepare', None, receipt['corpus_report_sha256'],
                                         now=recorded - timedelta(microseconds=1))
            result = probe.completed_activity('prepare', None, receipt['corpus_report_sha256'], now=recorded)
            self.assertIn('sha256', result)
            with self.assertRaises(ValueError):
                probe.completed_activity('prepare', None, receipt['corpus_report_sha256'],
                                         now=recorded.replace(tzinfo=None))

    def test_worker_overrun_cannot_leave_a_complete_activity_or_zero_return(self):
        self.frozen_diagnostic()
        with mock.patch.object(probe, 'evaluate', return_value=0), \
                mock.patch.object(probe.time, 'perf_counter', side_effect=[100., 701.]):
            self.assertEqual(probe.run_worker('evaluate', 'parent', 600), 8)
        receipt = probe.required(probe.activity_path('evaluate', 'parent'))
        self.assertEqual((receipt['status'], receipt['complete'], receipt['returncode']), ('HOLD', False, 8))
        self.assertEqual(receipt['seconds'], 601.)
        self.assertFalse(receipt['within_requested_time_and_authority'])

    def test_worker_utc_jump_past_record_reserve_is_not_complete(self):
        self.frozen_diagnostic(); start = probe.END - timedelta(hours=2)
        with mock.patch.object(probe, 'evaluate', return_value=0), \
                mock.patch.object(probe.time, 'perf_counter', side_effect=[100., 101.]), \
                mock.patch.object(probe, 'datetime') as clock:
            clock.now.side_effect = [start, probe.END - timedelta(seconds=3599)]
            self.assertEqual(probe.run_worker('evaluate', 'parent', 600), 8)
        receipt = probe.required(probe.activity_path('evaluate', 'parent'))
        self.assertEqual(receipt['status'], 'HOLD'); self.assertFalse(receipt['complete'])

    def test_report_then_show_or_cleanup_failure_is_not_completed_evaluation(self):
        self.frozen_diagnostic()
        def failed_evaluation(endpoint):
            probe.write(probe.EVIDENCE / ('evaluate_' + endpoint) / 'report.json',
                        {'status': 'QUESTION_CONTENT_ACTUAL_COMPLETE', 'fixture': 'REPORT_ALREADY_WRITTEN'})
            raise RuntimeError('mock display/cleanup failure after report')
        with mock.patch.object(probe, 'evaluate', side_effect=failed_evaluation), self.assertRaises(RuntimeError):
            probe.run_worker('evaluate', 'parent', 600)
        receipt = probe.required(probe.activity_path('evaluate', 'parent'))
        self.assertEqual((receipt['status'], receipt['returncode'], receipt['complete']), ('TOOL_ERROR', 9, False))
        self.assertTrue((probe.EVIDENCE / 'evaluate_parent/report.json').is_file())
        with mock.patch.object(probe, 'endpoint_identity') as identity, self.assertRaises(ValueError):
            probe.readback()
        identity.assert_not_called()  # No checkpoint path or raw answer admission.

    def test_missing_evaluation_activity_is_hold_before_checkpoint_or_answers(self):
        self.frozen_diagnostic()
        with mock.patch.object(probe, 'endpoint_identity') as identity, self.assertRaises(probe.Pending):
            probe.readback()
        identity.assert_not_called()

    def test_final_activity_uses_safe_path_before_report_metadata(self):
        self.frozen_diagnostic()
        corpus = probe.CORPUS
        seen = []
        def linked(path):
            seen.append(str(path)); return path == corpus
        def metadata(path):
            self.assertNotEqual(path, corpus / 'report.json', 'descendant metadata reached before link rejection')
            return False
        with mock.patch.object(probe, 'evaluate', side_effect=RuntimeError('mock failure')), \
                mock.patch.object(Path, 'is_symlink', autospec=True, side_effect=linked), \
                mock.patch.object(Path, 'is_file', autospec=True, side_effect=metadata), self.assertRaises(ValueError):
            probe.run_worker('evaluate', 'parent', 600)
        self.assertIn(str(corpus), seen)

    def test_temp_case_raw_corruption_cannot_pass_downstream(self):
        self.frozen_diagnostic()
        report = probe.required(probe.CORPUS / 'report.json')
        first = probe.CORPUS / report['manifest']['shards'][0]['path']
        first.write_bytes(first.read_bytes() + b'{}\n')
        with self.assertRaises(ValueError): probe.read_prepared()

    def test_complete_three_endpoint_readback_binds_activities_and_preserves_sources(self):
        projection = self.frozen_diagnostic()
        frozen, cases, _ = probe.read_prepared()
        corpus_sha = probe.digest(probe.CORPUS / 'report.json')
        identities = {endpoint: dict(endpoint=endpoint, checkpoint='claims/' + endpoint + '.fixture',
            checkpoint_sha256='C' * 64, core_sha256='D' * 64) for endpoint in probe.ENDPOINTS}
        paths = []
        for endpoint in probe.ENDPOINTS:
            lineage = dict(tag=probe.TAG, **identities[endpoint], corpus_report_sha256=corpus_sha)
            events = self.events()
            for event in events: event['lineage'] = lineage
            directory = probe.LOCAL / ('evaluate_' + endpoint)
            manifest = probe.put(directory, 'answers', events, lineage)
            report = dict(probe.info(), status='QUESTION_CONTENT_ACTUAL_COMPLETE', endpoint=endpoint,
                code_sha256=probe.code_pins(None), source_binding=frozen['source_binding'],
                activity_prepare=projection['activity_prepare'], cases_sha256=frozen['cases_sha256'],
                corpus_report_sha256=corpus_sha, lineage=lineage, core_before='D' * 64, core_after='D' * 64,
                model_training=False, weights_changed=False, manifest=manifest,
                manifest_sha256=probe.digest(directory / 'answers_shards_manifest.json'),
                summary=probe.recount(events, cases, frozen, tok=self.tok, lineage=lineage))
            probe.write(probe.EVIDENCE / ('evaluate_' + endpoint) / 'report.json', report)
            probe.write(probe.activity_path('evaluate', endpoint), self.receipt('evaluate', endpoint))
            paths.extend(directory / spec['path'] for spec in manifest['shards'])
        before = {str(path): probe.digest(path) for path in paths}; original_digest = probe.digest
        def fixture_digest(path):
            return 'C' * 64 if Path(path).parent == self.root / 'claims' else original_digest(path)
        with mock.patch.object(probe, 'endpoint_identity', side_effect=lambda e, p: identities[e]), \
                mock.patch.object(probe, 'digest', side_effect=fixture_digest), redirect_stdout(io.StringIO()) as output:
            self.assertEqual(probe.readback(), 0)
        result = probe.required(probe.EVIDENCE / 'readback.json')
        self.assertEqual(result['actual_answers'], 768)
        self.assertTrue(all('activity_evaluate' in v for v in result['models'].values()))
        self.assertEqual({str(path): original_digest(path) for path in paths}, before)
        self.assertEqual(output.getvalue().count('[QUESTION_CONTENT_ACTUAL_QUESTION_ANSWER]'), 48)
        original_required = probe.required; parent_report = probe.EVIDENCE / 'evaluate_parent/report.json'
        baseline = original_required(parent_report)
        for change in (dict(endpoint='fixed_last'), dict(source_binding={}),
                       dict(corpus_report_sha256='E' * 64), dict(max_new=128)):
            def altered(path):
                return dict(baseline, **change) if Path(path) == parent_report else original_required(path)
            with self.subTest(change=change), \
                    mock.patch.object(probe, 'endpoint_identity', side_effect=lambda e, p: identities[e]), \
                    mock.patch.object(probe, 'digest', side_effect=fixture_digest), \
                    mock.patch.object(probe, 'required', side_effect=altered), self.assertRaises(ValueError):
                probe.readback()


class SourceProjectionTests(TempFixture):
    def source_fixture(self):
        up = SimpleNamespace(TAG='SYNTHETIC_UPSTREAM_V2', CORPUS=self.root / 'source/corpus',
            EVIDENCE=self.root / 'source/evidence')
        current = dict(tag=up.TAG, source_code_sha256={str(i): 'A' * 64 for i in range(60)})
        up.info = lambda: copy.deepcopy(current)
        up.checkpoint = lambda arm: self.root / 'claims' / (arm + '.fixture')
        up.read_rows = lambda directory, manifest, stem, count: probe.read_rows(directory, manifest, stem, count)
        frozen = dict(current, status='QUESTION_TRANSFER_CPU_VERIFIED', blocked=self.course['blocked'],
            course_sha256=probe.sha(self.course), expected_parent_core_sha256='B' * 64,
            native_train_offsets=[], manifests={}, exposure={})
        coded = [dict(split=s, problem=p) for s in ('train', 'dev', 'test') for p in self.course[s]]
        frozen['manifests']['coded'] = probe.put(up.CORPUS, 'coded', coded, {'tag': up.TAG, 'stem': 'coded'})
        for arm in probe.ARMS:
            frozen['exposure'][arm] = []
            for epoch in range(4):
                stem = arm + '_e' + str(epoch + 1)
                frozen['manifests'][stem] = dict(lineage=dict(tag=up.TAG, stem=stem))
                frozen['exposure'][arm].append(dict(counts=dict(positive_rows=12288, assistant_targets=24576,
                    x_tokens=98304), update_target_denominators=[256] * 96))
        probe.write(up.CORPUS / 'report.json', frozen)
        source_sha = probe.digest(up.CORPUS / 'report.json')
        self.stack.enter_context(mock.patch.object(probe, 'SOURCE_REPORT_SHA', source_sha))
        public = {k: v for k, v in frozen.items() if k not in ('manifests', 'native_train_offsets', 'blocked')}
        public['corpus_report_sha256'] = source_sha
        probe.write(up.EVIDENCE / 'cpu_contract.json', public)
        for arm in probe.ARMS:
            directory = up.EVIDENCE / ('train_' + arm)
            events = [dict(update=i + 1, epoch=i // 96 + 1, assistant_targets=256, native_targets=8192,
                x_tokens=1024, assistant_ce=.3, native_ce=2., gradient_norm=.5, step_seconds=1.) for i in range(384)]
            manifest = probe.put(directory, 'updates', events, dict(tag=up.TAG, arm=arm, cost=False))
            report = dict(current, status='TRAIN_COMPLETE_EVALUATION_PENDING', arm=arm, updates=384,
                checkpoint_written=True, optimizer_saved=False, checkpoint=str(up.checkpoint(arm).relative_to(self.root)),
                checkpoint_sha256='C' * 64, final_core_sha256='D' * 64,
                initial_core_sha256='B' * 64, corpus_sha256=source_sha,
                history=[dict(epoch=e + 1, updates=(e + 1) * 96) for e in range(4)],
                totals=dict(positive_rows=49152, assistant_targets=98304, x_tokens=393216, native_targets=3145728),
                event_manifest=manifest, step_seconds=[1.] * 384, grad_max=.5, clip_events=0)
            probe.write(directory / 'report.json', report)
            probe.write(directory / 'start.json', dict(current, arm=arm, cost=False))
        return up, frozen

    def test_exact_projection_reconstructs2432_and_recounts_closed384_twice(self):
        up, frozen = self.source_fixture()
        result = probe.read_projection(up)
        self.assertEqual(result['course'], self.course)
        self.assertEqual(result['frozen'], frozen)
        self.assertEqual(len(result['training']), 2)
        self.assertTrue(all(len(t['events']) == 384 for t in result['training'].values()))

    def test_unclosed_or_changed_source_rejected_before_declared_payloads(self):
        up, _ = self.source_fixture()
        with mock.patch.object(probe, 'closed_training', side_effect=probe.Pending('mock unfinished384')), \
                mock.patch.object(probe, 'read_rows') as payload, self.assertRaises(probe.Pending):
            probe.read_projection(up)
        payload.assert_not_called()
        with mock.patch.object(up, 'info', return_value={'tag': 'CHANGED'}), \
                mock.patch.object(probe, 'read_rows') as payload, self.assertRaises(ValueError):
            probe.read_projection(up)
        payload.assert_not_called()


if __name__ == '__main__':
    unittest.main()
