"""Local fixtures and synthetic scorer/tokenizer only; real learned models forbidden."""
from __future__ import annotations

from contextlib import ExitStack, redirect_stderr, redirect_stdout
import copy
import hashlib
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
from scripts import p106b_minimal_pair_benchmark as m


class Tokenizer:
    mapping = {'\n': [0, 9], 'good': [1, 2], 'bad': [2, 1], 'good2': [3, 4],
               'bad2': [5], 'tie-good': [6], 'tie-bad': [7], 'empty-encoded': []}
    def __init__(self, bos=True): self.bos = bos
    def get_vocab_size(self): return 16
    def token_to_id(self, token): return 15 if token == '<bos>' and self.bos else None
    def encode(self, text): return NS(ids=list(self.mapping[text]))


def rows():
    return [dict(pair_id='p' + str(i), phenomenon='A' if i < 2 else 'B',
        sentence_good=a, sentence_bad=b, source='SYNTHETIC', split='test')
        for i, (a, b) in enumerate((('good', 'bad'), ('good2', 'bad2'), ('tie-good', 'tie-bad')))]


SCORES = {'good': (5., 10., 2), 'bad': (6., 12., 2), 'good2': (3., 6., 2),
          'bad2': (4., 4., 1), 'tie-good': (2., 2., 1), 'tie-bad': (2., 2., 1)}


def fixture():
    tok = Tokenizer(); metric = m.protocol(tok); source = dict(sha256='A' * 64, ordered_pairs_sha256=m.sha(rows()))
    plans = m.prepare_pairs(rows(), tok, metric)
    baseline = m.baseline_bundle(plans, source, 'B' * 64, metric)
    return plans, baseline


class Guarded(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack(); self.addCleanup(self.stack.close)
        self.stack.enter_context(patch('builtins.input', side_effect=AssertionError('no interactive input')))
        # These imports expose existing definitions only; never enter a runtime.
        from scripts import interactive_research_infer as research
        self.stack.enter_context(patch.object(research, 'selected_runtime', side_effect=AssertionError('no learned model')))


class DataAndEncodingTests(Guarded):
    def test_utf8_jsonl_source_bytes_and_exact_rows_are_preserved(self):
        values = rows(); values[0]['phenomenon'] = '한국어'
        raw = ''.join(json.dumps(row, ensure_ascii=False) + '\n' for row in values).encode('utf-8')
        with tempfile.TemporaryDirectory(prefix='minimal_pair_source_') as folder:
            root = Path(folder); path = root / 'pairs.jsonl'; path.write_bytes(raw)
            actual, source = m.read_dataset(path, root)
        self.assertEqual(actual, values); self.assertEqual(source['sha256'], hashlib.sha256(raw).hexdigest().upper())
        self.assertEqual(source['pairs'], 3); self.assertEqual(source['bytes'], len(raw))

    def test_missing_field_duplicate_id_empty_identical_and_nonstrings_are_rejected(self):
        variants = [[]]
        for field, value in (('sentence_good', ''), ('sentence_bad', '  '), ('pair_id', None)):
            bad = rows(); bad[0][field] = value; variants.append(bad)
        bad = rows(); bad[0].pop('source'); variants.append(bad)
        bad = rows(); bad[1]['pair_id'] = bad[0]['pair_id']; variants.append(bad)
        bad = rows(); bad[0]['sentence_bad'] = bad[0]['sentence_good']; variants.append(bad)
        for bad in variants:
            with self.assertRaises(ValueError): m.validate_pairs(bad)

    def test_blank_invalid_utf8_and_duplicate_json_fields_are_rejected(self):
        with tempfile.TemporaryDirectory(prefix='minimal_pair_bad_source_') as folder:
            root = Path(folder); path = root / 'pairs.jsonl'
            for raw in (b'\n', b'\xff\n', b'{"pair_id":"a","pair_id":"b"}\n'):
                path.write_bytes(raw)
                with self.assertRaises((ValueError, UnicodeError)): m.read_dataset(path, root)

    def test_newline_prefix_is_explicit_first_id_and_bos_never_silently_falls_back(self):
        self.assertEqual(m.protocol(Tokenizer())['prefix_ids'], [0])
        self.assertEqual(m.protocol(Tokenizer(), 'tokenizer_bos')['prefix_ids'], [15])
        with self.assertRaises(ValueError): m.protocol(Tokenizer(bos=False), 'tokenizer_bos')
        with self.assertRaises(ValueError): m.protocol(Tokenizer(), 'unknown')

    def test_empty_encoded_or_identical_candidate_ids_are_refused(self):
        values = rows(); values[0]['sentence_good'] = 'empty-encoded'
        with self.assertRaises(ValueError): m.prepare_pairs(values, Tokenizer(), m.protocol(Tokenizer()))
        tok = Tokenizer(); tok.mapping = dict(tok.mapping, bad=[1, 2])
        with self.assertRaises(ValueError): m.prepare_pairs(rows(), tok, m.protocol(tok))

    def test_complete_pair_overlength_is_recorded_without_truncation_or_scoring(self):
        plans = m.prepare_pairs(rows(), Tokenizer(), m.protocol(Tokenizer(), seq_max=2))
        scorer = Mock(side_effect=lambda text: SCORES[text])
        event = m.score_pair(plans[0], scorer)
        self.assertTrue(event['skipped']); self.assertEqual(event['reason'], 'complete_sentence_exceeds_context')
        scorer.assert_not_called(); self.assertEqual(event['plan']['good_ids'], [1, 2])
        with self.assertRaises(ValueError): m.prepare_pairs(rows()[:2], Tokenizer(), m.protocol(Tokenizer(), seq_max=2))

    def test_prefix_proxy_overrides_identity_sentinel_not_an_input_string(self):
        tok = Tokenizer(); proxy = m.PrefixTokenizer(tok, [15])
        self.assertEqual(proxy.encode(proxy.marker).ids, [15]); self.assertEqual(proxy.encode('good').ids, [1, 2])


class ScoreAndBaselineTests(Guarded):
    def test_primary_is_sum_not_mean_and_ties_are_not_correct(self):
        plans, baseline = fixture(); events = [m.score_pair(p, lambda s: SCORES[s]) for p in plans]
        self.assertEqual(events[0]['decision'], dict(correct=1, ties=0, incorrect=0))
        self.assertLess(events[1]['good']['mean_nll'], events[1]['bad']['mean_nll'])
        self.assertEqual(events[1]['decision'], dict(correct=0, ties=0, incorrect=1))
        self.assertEqual(events[2]['decision'], dict(correct=0, ties=1, incorrect=0))
        report = m.summarize(events, plans, baseline)
        self.assertAlmostEqual(report['micro_accuracy'], 1 / 3)
        self.assertEqual(report['macro_phenomenon_accuracy'], .25)
        self.assertEqual(report['counts']['ties'], 1); self.assertFalse(report['official_babylm_equivalence'])

    def test_source_only_unigram_is_order_invariant_and_length_ties_are_explicit(self):
        plans, baseline = fixture(); first = baseline['records'][0]
        self.assertEqual(first['unigram_good_logp'], first['unigram_bad_logp'])
        self.assertEqual(first['unigram']['ties'], 1); self.assertEqual(first['token_length']['ties'], 1)
        self.assertIn('BOTH evaluation candidates', baseline['specification']['unigram'])
        self.assertEqual(baseline['specification']['unigram_total_tokens'], 9)

    def test_all_skipped_phenomena_do_not_silently_enter_the_macro_denominator(self):
        values = rows(); values[0]['phenomenon'] = 'long_only'; values[1]['phenomenon'] = 'long_only'
        tok = Tokenizer(); metric = m.protocol(tok, seq_max=2)
        plans = m.prepare_pairs(values, tok, metric)
        baseline = m.baseline_bundle(plans, {}, 'B' * 64, metric)
        events = [m.score_pair(p, lambda s: SCORES[s]) for p in plans]
        report = m.summarize(events, plans, baseline)
        self.assertEqual(report['asked'], 3); self.assertEqual(report['scored'], 1)
        self.assertEqual(report['phenomena_asked'], 2); self.assertEqual(report['phenomena'], 1)
        self.assertEqual(report['all_skipped_phenomena'], ['long_only'])
        self.assertEqual(report['macro_phenomenon_accuracy'], 0.)

    def test_baseline_signature_is_model_independent_but_source_tokenizer_prefix_sensitive(self):
        plans, baseline = fixture(); spec = baseline['specification']
        self.assertNotIn('checkpoint_sha256', spec); self.assertNotIn('model', spec)
        for source, tok_sha, metric in ((dict(sha256='changed'), 'B' * 64, spec['protocol']),
                (spec['source'], 'C' * 64, spec['protocol']),
                (spec['source'], 'B' * 64, dict(spec['protocol'], prefix_ids=[15]))):
            altered = m.baseline_bundle(plans, source, tok_sha, metric)
            self.assertNotEqual(altered['signature'], baseline['signature'])

    def test_missing_duplicate_source_or_numerical_mutation_is_rejected(self):
        plans, baseline = fixture(); raw = [m.score_pair(p, lambda s: SCORES[s]) for p in plans]
        variants = [raw[:-1], raw + [raw[0]], [raw[0], raw[0], raw[2]]]
        bad = copy.deepcopy(raw); bad[0]['plan']['pair']['source'] = 'changed'; variants.append(bad)
        bad = copy.deepcopy(raw); bad[0]['good']['sum_nll'] += 1; variants.append(bad)
        bad = copy.deepcopy(raw); bad[0]['decision']['correct'] = 0; variants.append(bad)
        for bad in variants:
            with self.assertRaises(ValueError): m.summarize(bad, plans, baseline)

    def test_nonfinite_negative_empty_or_wrong_target_count_scorer_is_rejected(self):
        plans, _ = fixture()
        for value in (None, (float('nan'), 1., 2), (1., float('inf'), 2), (-1., -2., 2),
                      (1., 2., 3), (1., 9., 2), (True, 2., 2)):
            with self.assertRaises(ValueError): m.score_pair(plans[0], lambda sentence: value)

    def test_existing_scorer_receives_explicit_prefix_and_fp32_wrapper_without_model_forward(self):
        from scripts import eval_bench_suite as suite
        from scripts import diag_p106b_current_benchmark as public
        route = NS(assert_active=Mock()); tok = Tokenizer(); metric = m.protocol(tok, 'tokenizer_bos')
        active = dict(precision='FP32_MATH', cfg=NS(max_seq_len=1024), tokenizer=tok,
                      model=object(), torch=object(), route=route)
        def fake(model, tokenizer, device, prompt, sentence, seq_max, torch, F):
            self.assertEqual(model, 'FP32_WRAPPED'); self.assertEqual(device, 'cuda')
            self.assertEqual(tokenizer.encode(prompt).ids, [15]); self.assertEqual(tokenizer.encode(sentence).ids, [1, 2])
            return 5., 10., 2
        with patch.object(public, 'FP32Forward', return_value='FP32_WRAPPED'), patch.object(suite, 'seq_ce', side_effect=fake):
            self.assertEqual(m.make_scorer(active, metric)('good'), (5., 10., 2))
        route.assert_active.assert_called_once()


class StorageTests(Guarded):
    def test_write_once_raw_completion_and_same_signature_baseline_reuse(self):
        plans, baseline = fixture(); lineage = dict(model='SYNTHETIC', checkpoint_sha256='E' * 64, scope='NO_MODEL')
        with tempfile.TemporaryDirectory(prefix='minimal_pair_output_') as folder:
            root = Path(folder); output = root / 'run'
            result = m.collect_run(output, plans, baseline, lineage, lambda s: SCORES[s], root)
            self.assertFalse((output / 'report.json').exists())
            self.assertEqual(result['status'], 'RAW_COMPLETE_SESSION_EXIT_PENDING')
            with self.assertRaises(ValueError): m.publish_run(output, result, root)
            result['strict_model_context_exit_verified'] = True  # Synthetic successful context fixture, not a model call.
            report = m.publish_run(output, result, root)
            self.assertEqual(report['summary']['scored'], 3)
            self.assertTrue(all(p.stat().st_size < 20_000_000 for p in output.iterdir()))
            self.assertEqual(m.reuse_baseline(output, baseline, root)['signature'], baseline['signature'])
            before = (output / 'report.json').read_bytes()
            with self.assertRaises(FileExistsError): m.publish_run(output, result, root)
            self.assertEqual((output / 'report.json').read_bytes(), before)
            with self.assertRaises(FileExistsError): m.collect_run(output, plans, baseline, lineage, lambda s: SCORES[s], root)

    def test_pending_lineage_or_closed_manifest_mutation_cannot_publish_success(self):
        plans, baseline = fixture()
        with tempfile.TemporaryDirectory(prefix='minimal_pair_lineage_') as folder:
            root = Path(folder); output = root / 'run'
            result = m.collect_run(output, plans, baseline, dict(checkpoint_sha256='E' * 64), lambda s: SCORES[s], root)
            result['strict_model_context_exit_verified'] = True
            changed = copy.deepcopy(result); changed['lineage']['checkpoint_sha256'] = 'F' * 64
            with self.assertRaises(ValueError): m.publish_run(output, changed, root)
            path = output / 'scores_shards_manifest.json'; on_disk = json.loads(path.read_text())
            on_disk['lineage']['signature'] = 'changed'; path.write_text(json.dumps(on_disk), encoding='utf-8')
            with self.assertRaises(ValueError): m.publish_run(output, result, root)
            self.assertFalse((output / 'report.json').exists())

    def test_scorer_failure_preserves_closed_partial_raw_without_success_report(self):
        plans, baseline = fixture(); seen = []
        def scorer(sentence):
            seen.append(sentence)
            if len(seen) > 2: raise RuntimeError('synthetic failure after one complete pair')
            return SCORES[sentence]
        with tempfile.TemporaryDirectory(prefix='minimal_pair_partial_') as folder:
            root = Path(folder); output = root / 'run'
            with self.assertRaises(RuntimeError): m.collect_run(output, plans, baseline, {}, scorer, root)
            self.assertFalse((output / 'report.json').exists())
            failure = json.loads((output / 'error.json').read_text())
            self.assertEqual(failure['complete_pairs'], 1)
            self.assertEqual(failure['partial_manifest']['lineage']['status'], 'INCOMPLETE')
            self.assertIn('sentence_good', (output / 'scores_000000.jsonl').read_text())

    def test_baseline_source_signature_or_raw_shard_mutation_is_rejected(self):
        plans, baseline = fixture()
        with tempfile.TemporaryDirectory(prefix='minimal_pair_reuse_') as folder:
            root = Path(folder); output = root / 'run'
            m.collect_run(output, plans, baseline, {}, lambda s: SCORES[s], root)
            changed = copy.deepcopy(baseline); changed['signature'] = 'different'
            with self.assertRaises(ValueError): m.reuse_baseline(output, changed, root)
            path = output / 'baseline_000000.jsonl'; path.write_bytes(path.read_bytes() + b'{}\n')
            with self.assertRaises(ValueError): m.reuse_baseline(output, baseline, root)

    def test_output_escape_protected_path_symlink_and_size_guard(self):
        with tempfile.TemporaryDirectory(prefix='minimal_pair_paths_') as folder:
            root = Path(folder)
            for target in (root.parent / 'escape', root / '..' / 'escape', root / 'datasets/TinyDataset/file', root / '.git/file'):
                with self.assertRaises(ValueError): m.safe_path(target, root)
            (root / 'target').mkdir(); (root / 'link').symlink_to(root / 'target', target_is_directory=True)
            with self.assertRaises(ValueError): m.safe_path(root / 'link' / 'out', root)
            with patch.object(m, 'LIMIT', 64):
                with self.assertRaises(ValueError): m.atomic_json(root / 'oversized.json', {'text': 'a' * 100})
            self.assertFalse((root / 'oversized.json').exists())


class CliTests(Guarded):
    def test_check_only_uses_local_rows_and_no_runtime_or_output(self):
        with tempfile.TemporaryDirectory(prefix='minimal_pair_cli_') as folder:
            root = Path(folder); source = root / 'pairs.jsonl'
            source.write_text(''.join(json.dumps(r) + '\n' for r in rows()), encoding='utf-8')
            with patch.object(m, 'ROOT', root), patch.object(m, 'execute', side_effect=AssertionError('execute forbidden')), \
                    redirect_stdout(io.StringIO()):
                self.assertEqual(m.main(['--model', 'native595-f', '--data', str(source),
                                        '--output', str(root / 'out'), '--check-only']), 0)
            self.assertFalse((root / 'out').exists())

    def test_cli_invalid_models_missing_action_and_wall_bounds_fail_before_data(self):
        common = ['--model', 'native595-f', '--data', 'does-not-exist', '--output', 'out']
        for argv in (common, common + ['--execute', '--check-only'],
                     common + ['--check-only', '--max-wall-sec', '59'],
                     ['--model', 'generic-float', '--data', 'x', '--output', 'y', '--check-only']):
            with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error: m.main(argv)
            self.assertEqual(error.exception.code, 2)

    def test_direct_help_never_requires_assets_or_learned_models(self):
        result = subprocess.run([sys.executable, '-B', '-I', str(ROOT / 'scripts/p106b_minimal_pair_benchmark.py'), '--help'],
            stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('--baseline-from', result.stdout); self.assertIn('--bos-policy', result.stdout)


if __name__ == '__main__': unittest.main()
