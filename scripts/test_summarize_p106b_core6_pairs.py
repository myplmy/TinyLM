#!/usr/bin/env python3
"""CPU-only regression for the paired recount; temporary evidence stays in /tmp."""
from __future__ import annotations

from collections import Counter
import ast
import copy
import importlib.util
import itertools
import json
import math
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts import summarize_p106b_core6_pairs as subject
from scripts.p106b_shards import ShardWriter


class FakeTask:
    """Storage/row fixture, not a replacement evaluator or an evaluated model."""
    def __init__(self, multiple_input=False):
        self.multiple_input = multiple_input
        self.task_docs = [dict(question='한국어 Q0', choices=['a', 'long'], gold=0),
                          dict(question='Q1', choices=['a', 'long'], gold=1)]

    def doc_to_text(self, doc):
        return doc['gold'] if self.multiple_input else doc['question']

    def doc_to_target(self, doc):
        return ' trailing continuation' if self.multiple_input else doc['gold']

    def doc_to_choice(self, doc):
        return doc['choices']

    def process_results(self, doc, filtered):
        original = subject.official.independent_row(doc['choices'], doc['gold'], [r[0] for r in filtered])
        return {name: original[name] for name in ('acc', 'acc_norm')}


def requests(task, doc, index):
    target = task.doc_to_target(doc)
    args = [(choice, target) if task.multiple_input else (doc['question'], ' ' + choice)
            for choice in doc['choices']]
    return doc['question'], list(doc['choices']), [SimpleNamespace(args=arg) for arg in args]


def fixture_rows(task=None):
    task = task or FakeTask()
    rows = []
    for index, doc in enumerate(task.task_docs):
        _, _, reqs = requests(task, doc, index)
        args = [list(req.args) for req in reqs]
        filtered = [[-1.0 - index, False], [-2.0 + index / 2, False]]
        target = task.doc_to_target(doc)
        metrics = task.process_results(doc, filtered)
        rows.append(dict(doc_id=index, doc=copy.deepcopy(doc), target=target, arguments=args,
            resps=[[copy.deepcopy(value)] for value in filtered], filtered_resps=filtered,
            filter='none', metrics=list(metrics), **metrics,
            doc_hash=subject.sha_string(json.dumps(doc, indent=2, ensure_ascii=False)),
            prompt_hash=subject.sha_string(args[0][0]), target_hash=subject.sha_string(str(target))))
    return task, rows


def fixture_report(model='native595-f'):
    external = model in subject.EXTERNAL
    files = {'scripts/original.py': 'A' * 64}
    return dict(model=model, schema='P106B_EXTERNAL_HF_CORE6_V3' if external else 'P106B_OFFICIAL_CORE6_V1',
        status='EXTERNAL_OFFICIAL_CORE6_FULL_COMPLETE' if external else 'OFFICIAL_CORE6_FULL_COMPLETE',
        mode='full', returncode=0, sources_unchanged=True, training=False, optimizer_updates=0,
        checkpoint_writes=0, expected_counts=dict(subject.COUNTS), actual_counts=dict(subject.COUNTS),
        framework_commit=subject.assets.COMMIT, data_manifest_sha256=subject.assets.MANIFEST_SHA,
        started_at='2026-10-23T00:00:00+00:00', ended_at='2026-10-23T00:01:00+00:00',
        sample_manifests={name: {} for name in subject.COUNTS},
        independent_audits={name: {} for name in subject.COUNTS},
        official_results={name: {} for name in subject.COUNTS},
        token_lengths_summary={'requests': 67106}, model_proof={'kind': 'TEST_PROVENANCE_ONLY'},
        source_identity=dict(files=files, sha256=subject.digest_bytes(json.dumps(files, sort_keys=True).encode())),
        policy=dict(num_fewshot=0, chat_template=False, max_length=1024, seed=1337,
            continuation='COMPLETE_SUM_LOGLIKELIHOOD; TASK_OWNS_ACC_NORM',
            bos='NO_EXTRA_BOS_FOR_NONEMPTY_CONTEXT; NATIVE_PREFIX_FOR_EMPTY_CONTEXT',
            bootstrap_iters=100000, batch_size=1 if external else 8,
            precision='FP32; MODEL_EAGER_AND_SDPA_MATH; TF32_OFF' if external else 'FP32; SDPA_MATH_OR_MODEL_EAGER; TF32_OFF',
            use_cache=False, request_cache=False, sqlite_cache=False, logits_cache=False,
            softmax_dtype='float32', mixed_precision=False),
        tag='p106b_external_core6_v3_s1337', raw_independent_recount=True, choice_likelihoods=67106)


class RecountTests(unittest.TestCase):
    def recount(self, task, rows):
        return subject.recount_task('piqa', task, rows, expected=2, request_builder=requests)

    def test_exact_official_recount_and_separate_baselines(self):
        task, rows = fixture_rows()
        result = self.recount(task, rows)
        self.assertEqual(result['values'], [1, 1])
        self.assertEqual(result['choice_likelihoods'], 4)
        self.assertEqual(result['audit']['random_expected_correct'], 1)
        self.assertEqual(result['audit']['posthoc_majority_correct'], 1)
        self.assertEqual(result['audit']['shortest_correct'], 1)
        self.assertEqual(result['audit']['longest_correct'], 1)
        self.assertEqual(set(result['correspondence']),
            {name + '_ordered_sha256' for name in ('docs', 'arguments', 'gold_choices', 'cases')})

    def test_input_rows_and_documents_are_not_mutated(self):
        task, rows = fixture_rows()
        before = copy.deepcopy((task.task_docs, rows))
        self.recount(task, rows)
        self.assertEqual((task.task_docs, rows), before)

    def test_multiple_input_target_is_not_gold(self):
        task, rows = fixture_rows(FakeTask(multiple_input=True))
        self.assertIsInstance(rows[0]['target'], str)
        self.assertEqual(self.recount(task, rows)['values'], [1, 1])

    def test_raw_sorted_doc_order_does_not_replace_original_hash_order(self):
        task, rows = fixture_rows()
        rows = subject.decode(subject.canonical(rows))
        self.assertNotEqual(list(rows[0]['doc']), list(task.task_docs[0]))
        self.recount(task, rows)
        rows[0]['doc_hash'] = subject.sha_string(json.dumps(rows[0]['doc'], indent=2, ensure_ascii=False))
        with self.assertRaises(ValueError):
            self.recount(task, rows)

    def test_every_raw_identity_and_metric_mutation_rejected(self):
        mutations = [lambda r: r.update(doc_id=1), lambda r: r.update(filter='other'),
            lambda r: r['doc'].update(question='changed'), lambda r: r.update(target=1),
            lambda r: r['arguments'][0].__setitem__(0, 'changed'),
            lambda r: r.update(doc_hash='0' * 64), lambda r: r.update(prompt_hash='0' * 64),
            lambda r: r.update(target_hash='0' * 64), lambda r: r.update(acc=0),
            lambda r: r.update(acc_norm=1), lambda r: r.update(metrics=['acc']),
            lambda r: r['resps'][0][0].__setitem__(0, -3),
            lambda r: r.update(filtered_resps=[]), lambda r: r.update(resps=[])]
        for mutate in mutations:
            with self.subTest(mutation=mutate):
                task, rows = fixture_rows()
                mutate(rows[0])
                with self.assertRaises(ValueError):
                    self.recount(task, rows)

    def test_row_order_and_missing_row_rejected(self):
        task, rows = fixture_rows()
        for invalid in (rows[::-1], rows[:1], rows + rows):
            with self.assertRaises(ValueError):
                self.recount(task, invalid)

    def test_original_audit_receipt_recount_and_mismatch(self):
        task, rows = fixture_rows()
        audit = self.recount(task, rows)['audit']
        subject.verify_audit(audit, subject.decode(subject.canonical(audit)))
        for key in audit:
            wrong = copy.deepcopy(audit)
            wrong[key] = None
            with self.subTest(field=key), self.assertRaises(ValueError):
                subject.verify_audit(audit, wrong)

    def test_original_metric_method_not_an_approximation(self):
        task, rows = fixture_rows()
        task.process_results = lambda *_: {'acc': 0, 'acc_norm': 0}
        with self.assertRaises(ValueError):
            self.recount(task, rows)

    def test_contract_reuse_does_not_rebuild_or_mutate_official_task(self):
        task, rows = fixture_rows()
        original = dict(task.__dict__)
        calls = []
        def count_requests(*args):
            calls.append(args[2])
            return requests(*args)
        contracts = subject.CaseContracts(task, 2, count_requests)
        before = copy.deepcopy(contracts.rows)
        expected = self.recount(task, rows)
        for _ in range(2):
            actual = subject.recount_task('piqa', task, rows, expected=2,
                                         request_builder=count_requests, contracts=contracts)
            self.assertEqual(actual, expected)
        self.assertEqual(calls, [0, 1])
        self.assertEqual(contracts.rows, before)
        self.assertEqual(task.__dict__, original)


class AdmissionTests(unittest.TestCase):
    def test_closed_internal_and_v3_external_admitted(self):
        for model in ('native595-f', 'gemma270', 'qwen06', 'gemma1b'):
            subject.admit_report(model, fixture_report(model))

    def test_known_v3_does_not_emit_expected_counts_but_actual_is_exact(self):
        report = fixture_report('gemma270')
        del report['expected_counts']
        subject.admit_report('gemma270', report)
        report['expected_counts'] = {}
        with self.assertRaises(ValueError):
            subject.admit_report('gemma270', report)

    def test_closed_full_fields_not_optional(self):
        for key, value in [('mode', 'cost'), ('returncode', 8), ('returncode', False),
            ('status', 'RUNNING'), ('sources_unchanged', False), ('training', True),
            ('optimizer_updates', 1), ('checkpoint_writes', 1), ('expected_counts', {}),
            ('actual_counts', {}), ('framework_commit', 'wrong'), ('data_manifest_sha256', 'wrong'),
            ('ended_at', None), ('sample_manifests', {}), ('independent_audits', {}),
            ('official_results', {}), ('token_lengths_summary', {'requests': 67105}),
            ('model_proof', {}), ('source_identity', {})]:
            report = fixture_report()
            report[key] = value
            with self.subTest(field=key), self.assertRaises(ValueError):
                subject.admit_report('native595-f', report)

    def test_external_wrong_version_partial_or_unrecounted_rejected(self):
        for key, value in [('schema', 'P106B_EXTERNAL_HF_CORE6_V2'), ('tag', 'old'),
            ('raw_independent_recount', False), ('choice_likelihoods', 0)]:
            report = fixture_report('gemma270')
            report[key] = value
            with self.subTest(field=key), self.assertRaises(ValueError):
                subject.admit_report('gemma270', report)

    def test_inference_policy_and_naive_timestamp_rejected(self):
        report = fixture_report()
        report['policy']['max_length'] = 512
        with self.assertRaises(ValueError):
            subject.admit_report('native595-f', report)
        report = fixture_report()
        report['ended_at'] = '2026-10-23T00:01:00'
        with self.assertRaises(ValueError):
            subject.admit_report('native595-f', report)

    def test_precision_batch_and_reversed_closure_rejected(self):
        for model in ('native595-f', 'gemma270'):
            for key, value in [('precision', 'BF16'), ('batch_size', 32), ('bootstrap_iters', 1000), ('bos', 'other')]:
                report = fixture_report(model)
                report['policy'][key] = value
                with self.subTest(model=model, policy=key), self.assertRaises(ValueError):
                    subject.admit_report(model, report)
        report = fixture_report()
        report['ended_at'] = '2026-10-22T00:01:00+00:00'
        with self.assertRaises(ValueError):
            subject.admit_report('native595-f', report)

    def test_historical_source_receipt_not_silently_replaced(self):
        report = fixture_report()
        report['source_identity']['files']['scripts/original.py'] = 'B' * 64
        with self.assertRaises(ValueError):
            subject.admit_report('native595-f', report)

    def test_unknown_native_schema_is_not_guessed(self):
        with self.assertRaises(ValueError):
            subject.report_path('native-successor')
        with self.assertRaises(ValueError):
            subject.collect(['native595-f', 'native-successor'])

    def test_unclosed_report_refused_before_scientific_import(self):
        with tempfile.TemporaryDirectory(prefix='p106b_pairs_test_', dir='/tmp') as temporary:
            with patch.object(subject, 'load_readonly_tasks', side_effect=AssertionError('must not import')):
                with self.assertRaises(subject.IncompleteFull):
                    subject.collect(['native595-f', 'native595-q'], root=Path(temporary))

    def test_duplicate_and_nonfinite_json_rejected(self):
        for raw in ('{"a":1,"a":2}', '{"a":NaN}', '{"a":Infinity}'):
            with self.assertRaises(ValueError):
                subject.decode(raw)

    def test_memory_storage_override_preserves_original_science(self):
        class Original:
            def __init__(self, config):
                self.config = config
                self.download(config)

            def download(self, *_):
                raise AssertionError('original storage must not load/cache')

            def process_results(self, *_):
                return 'official-unchanged'
        dataset = {'validation': [1, 2]}
        task = subject.memory_task(Original, {'scientific': 'untouched'}, dataset)
        self.assertIs(task.dataset, dataset)
        self.assertIs(type(task).process_results, Original.process_results)
        self.assertEqual(set(type(task).__dict__) - {'__module__', '__doc__'}, {'download'})


class EvidenceTests(unittest.TestCase):
    def test_small_shard_reuses_exact_existing_verifier(self):
        with tempfile.TemporaryDirectory(prefix='p106b_pairs_test_', dir='/tmp') as temporary:
            directory = Path(temporary)
            writer = ShardWriter(directory, 'piqa_samples', limit=2048)
            for index in range(2):
                writer.append({'doc_id': index})
            manifest = writer.close(lineage=dict(model='native595-f', task='piqa', mode='full'))
            inputs = subject.Inputs()
            with patch.dict(subject.COUNTS, piqa=2):
                rows = subject.read_samples(directory, 'piqa', manifest, 'native595-f', inputs)
                self.assertEqual(rows, [{'doc_id': 0}, {'doc_id': 1}])
                self.assertTrue(inputs.unchanged())
                wrong = copy.deepcopy(manifest)
                wrong['shards'][0]['sha256'] = '0' * 64
                with self.assertRaises(ValueError):
                    subject.read_samples(directory, 'piqa', wrong, 'native595-f', subject.Inputs())
                with (directory / manifest['shards'][0]['path']).open('ab') as stream:
                    stream.write(b'{}\n')
                with self.assertRaises(ValueError):
                    subject.read_samples(directory, 'piqa', manifest, 'native595-f', subject.Inputs())
                with self.assertRaises(ValueError):
                    inputs.unchanged()

    def test_input_expected_hash_and_symlink_refused(self):
        with tempfile.TemporaryDirectory(prefix='p106b_pairs_test_', dir='/tmp') as temporary:
            path = Path(temporary) / 'input.json'
            with path.open('xb') as stream:
                stream.write(b'{}\n')
            with self.assertRaises(ValueError):
                subject.Inputs().add(path, '0' * 64)
            link = Path(temporary) / 'linked.json'
            link.symlink_to(path)
            with self.assertRaises(ValueError):
                subject.read_json(link)

    def test_namespace_safe_exclusive_and_small_output_hashes(self):
        with tempfile.TemporaryDirectory(prefix='p106b_pairs_test_', dir='/tmp') as temporary:
            root = Path(temporary)
            for invalid in (None, '', '../escape', '/absolute', 'x/y', '한글', '.hidden', 'a' * 81):
                with self.subTest(stamp=invalid), self.assertRaises(ValueError):
                    subject.output_path(invalid, root)
            target = subject.output_path('regression_1', root)
            self.assertEqual(target, root / 'test_result/evidence' / subject.TAG / 'regression_1')
            report = dict(source_identity={'sha256': 'A' * 64}, input_files={}, synthetic_only=True)
            receipt = subject.write_summary(target, report)
            outputs = subject.read_json(target / 'outputs.json')
            self.assertEqual(outputs['schema'], 'P106B_CORE6_PAIRS_OUTPUT_RECEIPT_V2')
            self.assertEqual(receipt['report_sha256'], subject.digest(target / 'report.json'))
            self.assertEqual(receipt['outputs_receipt_sha256'], subject.digest(target / 'outputs.json'))
            self.assertEqual(outputs['outputs']['report.json']['sha256'], receipt['report_sha256'])
            self.assertLess(receipt['report_bytes'], subject.MAX_BYTES)
            with self.assertRaises(FileExistsError):
                subject.write_summary(target, report)
            with self.assertRaises(FileExistsError):
                subject.output_path('regression_1', root)

    def test_oversize_refused_before_namespace_creation(self):
        with tempfile.TemporaryDirectory(prefix='p106b_pairs_test_', dir='/tmp') as temporary:
            target = Path(temporary) / 'too_large'
            with patch.object(subject, 'MAX_BYTES', 100), self.assertRaises(ValueError):
                subject.write_summary(target, {'large': 'x' * 100})
            self.assertFalse(target.exists())

    def test_source_identity_cache_policy_and_no_heavy_check_only(self):
        identity = subject.source_identity()
        self.assertEqual(set(identity['files']), set(subject.SOURCES))
        self.assertEqual(identity['sha256'], subject.digest_bytes(subject.canonical(identity['files'])))
        code = ("import os,runpy,sys\n"
                "os.environ['HF_HOME']='/tmp/p106b_pairs_unused_external_HF'\n"
                "sys.argv=['check','--check-only']\ntry:\n"
                f"    runpy.run_path({str(ROOT / subject.SCRIPT)!r},run_name='__main__')\n"
                "except SystemExit as result:\n    assert result.code == 0\n"
                "import tinylm\n"
                "assert os.environ['HF_HOME'] == str(tinylm.paths.HF_DIR)\n"
                "assert os.environ['HF_HUB_CACHE'] == str(tinylm.paths.HF_DIR / 'hub')\n"
                "assert os.environ['HF_DATASETS_CACHE'] == str(tinylm.paths.HF_DIR / 'datasets')\n"
                "assert not any(n in sys.modules for n in ('torch','numpy','datasets','transformers','lm_eval'))")
        result = subprocess.run([sys.executable, '-B', '-X', 'utf8', '-c', code],
            check=True, capture_output=True, text=True, timeout=10, cwd=ROOT)
        report = json.loads(result.stdout)
        self.assertEqual((report['raw_reads'], report['evidence_writes'], report['models_loaded']), (0, 0, 0))
        self.assertTrue(report['cache_policy_imported'])

    def test_v1_archive_exact_bytes_and_combined_source_receipt_preserved(self):
        directory = ROOT / 'handoff/audit/source_20261024_pairs_v1'
        receipt = subject.read_json(directory / 'sha256_receipt.json')
        self.assertEqual(receipt['original_source_identity']['sha256'],
            'F004BC42E9B0E829FAC469BFE8C024AF9A829CC0630CA64EE7494AC04F8710FA')
        original_files = receipt['original_source_identity']['files']
        self.assertEqual(subject.digest_bytes(subject.canonical(original_files)),
                         receipt['original_source_identity']['sha256'])
        for spec in receipt['preserved_files']:
            path = ROOT / spec['archived_path']
            self.assertEqual(subject.digest(path), spec['sha256'])
            self.assertEqual(path.stat().st_size, spec['bytes'])
            self.assertEqual(spec['sha256'], original_files[spec['original_path']])

    def test_v2_namespace_and_tinylm_import_precedes_scientific_helpers(self):
        self.assertEqual(subject.TAG, 'p106b_core6_pairs_v2_s1337')
        self.assertEqual(subject.SCHEMA, 'P106B_OFFICIAL_CORE6_PAIRED_RECOUNT_V2')
        tree = ast.parse((ROOT / subject.SCRIPT).read_text(encoding='utf-8'))
        bootstrap = next(node for node in tree.body if isinstance(node, ast.Import)
                         and any(alias.name == 'tinylm' for alias in node.names))
        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
                self.assertNotIn(node.value.id, {'cfg', 'config'})
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if isinstance(node.func.value, ast.Attribute) and node.func.attr == 'insert':
                    self.assertLess(node.lineno, bootstrap.lineno)
        first_helper = next(node for node in tree.body if isinstance(node, ast.ImportFrom)
                            and node.module == 'scripts')
        self.assertLess(bootstrap.lineno, first_helper.lineno)

    def test_v2_science_and_task_methods_ast_identical_to_archived_v1(self):
        archived = ROOT / 'handoff/audit/source_20261024_pairs_v1/summarize_p106b_core6_pairs.py'
        trees = [ast.parse(path.read_text(encoding='utf-8')) for path in (archived, ROOT / subject.SCRIPT)]
        definitions = [{node.name: node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.ClassDef))}
                       for tree in trees]
        unchanged = ('admit_report', 'read_samples', 'CaseContracts', 'recount_task', 'verify_audit',
                     'recount_model', 'category_mean_samples', 'paired_intervals', 'cpu_wall_limit', 'collect')
        for name in unchanged:
            with self.subTest(definition=name):
                self.assertEqual(ast.dump(definitions[0][name]), ast.dump(definitions[1][name]))
        class DictionaryNameOnly(ast.NodeTransformer):
            def visit_Name(self, node):
                if node.id == 'config':
                    node.id = 'task_yaml'
                return node
            def visit_arg(self, node):
                if node.arg == 'config':
                    node.arg = 'task_yaml'
                return node
        for name in ('memory_task', 'load_readonly_tasks'):
            original = DictionaryNameOnly().visit(copy.deepcopy(definitions[0][name]))
            self.assertEqual(ast.dump(original), ast.dump(definitions[1][name]))

    def test_no_other_alarm_overwrite_and_valid_wall_limit(self):
        for invalid in (0, 121, True, 1.5):
            with self.subTest(seconds=invalid), self.assertRaises(ValueError):
                with subject.cpu_wall_limit(invalid):
                    pass
        with patch.object(signal, 'getitimer', return_value=(5.0, 0.0)):
            with self.assertRaises(ValueError):
                with subject.cpu_wall_limit(1):
                    pass
        before = signal.getsignal(signal.SIGALRM)
        with subject.cpu_wall_limit(1):
            self.assertGreater(signal.getitimer(signal.ITIMER_REAL)[0], 0)
        self.assertEqual(signal.getsignal(signal.SIGALRM), before)
        self.assertEqual(signal.getitimer(signal.ITIMER_REAL), (0.0, 0.0))


@unittest.skipUnless(importlib.util.find_spec('numpy'), 'numpy absent; no installation allowed')
class StatisticsTests(unittest.TestCase):
    def setUp(self):
        import numpy as np
        self.np = np

    def test_count_multinomial_equals_exhaustive_direct_case_mean_distribution(self):
        # Directly enumerate every paired case-index resample, not a second scorer.
        deltas = [-1, 0, 0, 1]
        n = len(deltas)
        direct = Counter(sum(deltas[i] for i in indices) for indices in itertools.product(range(n), repeat=n))
        multinomial = Counter()
        counts = Counter(deltas)
        for negative in range(n + 1):
            for zero in range(n - negative + 1):
                positive = n - negative - zero
                multiplicity = math.factorial(n) // (math.factorial(negative) * math.factorial(zero) * math.factorial(positive))
                multiplicity *= counts[-1] ** negative * counts[0] ** zero * counts[1] ** positive
                multinomial[positive - negative] += multiplicity
        self.assertEqual(direct, multinomial)
        self.assertEqual(sum(direct.values()), n ** n)
        np = self.np
        actual, _ = subject.category_mean_samples(np, deltas, np.random.default_rng(subject.SEED), subject.RESAMPLES)
        direct_sample = np.asarray(deltas)[np.random.default_rng(subject.SEED).integers(0, n, size=(subject.RESAMPLES, n))].mean(axis=1)
        self.assertEqual(np.quantile(actual, [.025, .975]).tolist(),
                         np.quantile(direct_sample, [.025, .975]).tolist())
        self.assertAlmostEqual(float(actual.mean()), float(direct_sample.mean()), delta=.006)

    def test_identical_pairs_have_exact_zero_ci(self):
        values = {name: [0, 1, 1, 0] for name in subject.PRIMARY}
        result = subject.paired_intervals(values, values)
        self.assertEqual(result['mean6']['ci95'], [0.0, 0.0])
        self.assertEqual(result['mean6']['right_minus_left'], 0.0)
        self.assertFalse(result['multiple_comparisons_corrected'])
        self.assertEqual((result['seed'], result['resamples']), (20261024, 100000))
        for task in result['per_task'].values():
            self.assertEqual(task['ci95'], [0.0, 0.0])
            self.assertEqual(task['same_correctness'], 4)

    def test_fixed_tasks_have_equal_not_pooled_case_weight(self):
        sizes = [1, 2, 3, 4, 5, 100]
        left = {name: [0] * size for name, size in zip(subject.PRIMARY, sizes)}
        right = {name: [int(i < 5)] * size for i, (name, size) in enumerate(zip(subject.PRIMARY, sizes))}
        result = subject.paired_intervals(left, right, draws=100)
        self.assertAlmostEqual(result['mean6']['right_minus_left'], 5 / 6)
        self.assertNotAlmostEqual(result['mean6']['right_minus_left'], 15 / 115)
        for endpoint in result['mean6']['ci95']:
            self.assertAlmostEqual(endpoint, 5 / 6)

    def test_delta_sign_counts_reproducibility_and_unsigned_input(self):
        np = self.np
        left = {name: np.array([1, 0, 0, 1], dtype=np.uint8) for name in subject.PRIMARY}
        right = {name: np.array([0, 1, 1, 1], dtype=np.uint8) for name in subject.PRIMARY}
        result = subject.paired_intervals(left, right, draws=1000)
        self.assertEqual(result, subject.paired_intervals(left, right, draws=1000))
        for task in result['per_task'].values():
            self.assertEqual((task['discordant_right_worse'], task['same_correctness'], task['discordant_right_better']), (1, 1, 2))
            self.assertEqual(task['right_minus_left'], .25)

    def test_invalid_paired_binary_strata_rejected_without_drops(self):
        valid = {name: [0, 1] for name in subject.PRIMARY}
        for change in ({}, {'piqa': []}, {'piqa': [0]}, {'piqa': [0, 2]}, {'piqa': [[0, 1]]}):
            bad = copy.deepcopy(valid)
            if not change:
                bad.pop('piqa')
            else:
                bad.update(change)
            with self.subTest(change=change), self.assertRaises(ValueError):
                subject.paired_intervals(valid, bad, draws=100)

    def test_invalid_delta_inputs_and_resample_count(self):
        np = self.np
        for values, draws in [([], 10), ([2], 10), ([[0]], 10), ([0], 0), ([0], True)]:
            with self.subTest(values=values, draws=draws), self.assertRaises(ValueError):
                subject.category_mean_samples(np, values, np.random.default_rng(0), draws)


if __name__ == '__main__':
    unittest.main(verbosity=2)
