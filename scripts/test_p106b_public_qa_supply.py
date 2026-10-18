"""Synthetic public-QA inventory tests; real source/model/GPU entrypoints blocked."""
from __future__ import annotations
from contextlib import ExitStack, redirect_stdout, redirect_stderr
import copy
import io
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import diag_p106b_public_qa_supply as d
from scripts.p106b_shards import ShardWriter


class CharTokenizer:
    def __init__(self, missing_eot=False): self.missing_eot = missing_eot
    def token_to_id(self, token): return {'<|im_start|>': 1, '<|im_end|>': 2}.get(token)
    def encode(self, text):
        ids = []; offsets = []; i = 0
        while i < len(text):
            special = next((s for s in ('<|im_start|>', '<|im_end|>') if text.startswith(s, i)), None)
            width = len(special) if special else 1
            token = self.token_to_id(special) if special else ord(text[i]) + 10
            if special == '<|im_end|>' and self.missing_eot: token = 999
            ids.append(token); offsets.append((i, i + width)); i += width
        return NS(ids=ids, offsets=offsets)


def documents(count=180):
    result = {}
    for language in ('ko', 'en'):
        articles = []
        for i in range(count):
            title = language + '_supply_article_' + str(i)
            answer = str(i); context = ('번호 ' if language == 'ko' else 'Identifier ') + answer + '.'
            question = ('어느 번호인가요 ' if language == 'ko' else 'Which identifier ') + str(i) + '?'
            articles.append(dict(title=title, paragraphs=[dict(context=context, qas=[dict(id=language + str(i),
                question=question, answers=[dict(text=answer, answer_start=context.index(answer))])])]))
        result[language] = {split: dict(path=d.data.SOURCES[language][split][0],
            sha256=d.data.SOURCES[language][split][1], document=dict(data=articles if split == 'train' else []))
            for split in ('train', 'dev')}
    return result


def collect(docs=None, **kwargs):
    return d.collect_documents(documents() if docs is None else docs, CharTokenizer(),
        eval_limit=2, min_eval_contexts=2, common_bpb_count=0, **kwargs)


def baseline_index(rows):
    return {p['root']: dict(root=p['root'], language=p['language'], split=split,
        full_row_sha256=d.data.sha(p)) for split, values in rows.items() for p in values}


def details(rows, cap=2, index=None):
    index = {} if index is None else index
    return [d.pair_detail(p, CharTokenizer(), cap, index) for split in ('train', 'dev', 'test') for p in rows[split]]


class Guarded(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack(); self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.object(d, 'load_documents', side_effect=AssertionError('real source read forbidden')))
        self.stack.enter_context(patch('builtins.input', side_effect=AssertionError('interactive input forbidden')))
        import torch
        self.stack.enter_context(patch('torch.load', side_effect=AssertionError('learned weights forbidden')))
        self.stack.enter_context(patch('torch.save', side_effect=AssertionError('checkpoint writing forbidden')))

    def temp_paths(self):
        temp = TemporaryDirectory(prefix='public_qa_supply_fixture_'); self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        for name, path in (('ROOT', root), ('LOCAL', root / 'local'), ('EVIDENCE', root / 'evidence'), ('BASELINE', root / 'baseline')):
            self.stack.enter_context(patch.object(d, name, path))
        return root


class CollectorTests(Guarded):
    def test_ast_and_exact_text_allow_only_six_declared_changes(self):
        proof = d.core_equivalence()
        self.assertTrue(proof['ast_equal_after_declared_edits'])
        self.assertTrue(proof['character_equal_after_declared_edits'])
        self.assertEqual(len(proof['allowed_edits']), 6)
        source = Path(d.__file__).read_text(encoding='utf-8')
        for old, new in (("('test', 'dev', 'train')", "('train', 'dev', 'test')"),
                         ('common_bpb_count=4000', 'common_bpb_count=0'),
                         ('min_eval_contexts=128', 'min_eval_contexts=1'),
                         ('if not answers or', 'if False and'),
                         ("reserved_contexts.add(pair['context_id'])", "reserved_contexts.add('wrong')")):
            at = source.rfind(old); self.assertGreaterEqual(at, 0)
            changed = source[:at] + source[at:].replace(old, new, 1)
            with self.subTest(change=old), self.assertRaises((ValueError, SyntaxError)):
                d.core_equivalence(candidate_source=changed)

    def test_finite_cap2_is_identical_to_original_collector_without_monkeypatch(self):
        docs = documents(); tok = CharTokenizer()
        expected = d.data.collect_documents(docs, tok, train_limit=6, eval_limit=2,
            min_eval_contexts=2, context_question_cap=2, common_bpb_count=0)
        actual = d.collect_documents(docs, tok, train_limit=6, eval_limit=2,
            min_eval_contexts=2, context_question_cap=2, common_bpb_count=0)
        self.assertEqual(actual, expected)

    def test_unbounded_train_exhaustion_is_measured_not_quota_error(self):
        docs = documents()
        rows, report = collect(docs)
        self.assertGreater(len(rows['train']), 100)
        with self.assertRaisesRegex(ValueError, 'need 1000000'):
            d.data.collect_documents(docs, CharTokenizer(), train_limit=1000000,
                eval_limit=2, min_eval_contexts=2, common_bpb_count=0)
        for language in ('ko', 'en'):
            self.assertEqual(report['languages'][language]['splits']['train']['pairs'],
                sum(p['language'] == language for p in rows['train']))

    def test_empty_train_lane_keeps_strict_sealed_evaluation_and_zero_counts(self):
        docs = documents()
        for language in docs:
            docs[language]['train']['document']['data'] = [a for a in docs[language]['train']['document']['data']
                if d.data.article_split(language, a['title']) != 'train']
        rows, _ = collect(docs)
        self.assertEqual(rows['train'], [])
        summary = d.detail_summary(details(rows))
        for language in ('ko', 'en'):
            self.assertEqual(summary[language]['train']['unique_qa_roots'], 0)
            self.assertEqual(summary[language]['train']['two_view_exposure']['assistant_targets'], 0)
            self.assertEqual(summary[language]['test']['unique_qa_roots'], 2)
        for language in docs: docs[language]['train']['document']['data'] = []
        with self.assertRaises(ValueError): collect(docs)

    def test_article_splits_official_dev_common_and_whole_clean_reservation_preserved(self):
        docs = documents()
        for language in docs:
            copied = copy.deepcopy(docs[language]['train']['document']['data'][0])
            copied['title'] = 'official reserve title ' + language
            docs[language]['dev']['document']['data'].append(copied)
        rows, report = collect(docs)
        for language in ('ko', 'en'):
            self.assertGreaterEqual(report['languages'][language]['rejections']['official_dev_context'], 1)
        common = min(p['context'] for a in docs['en']['train']['document']['data'] for p in a['paragraphs'])
        more, inventory = d.collect_documents(docs, CharTokenizer(), eval_limit=2, min_eval_contexts=2, common_bpb_count=1)
        self.assertEqual(inventory['languages']['en']['common_bpb_unique_contexts'], 1)
        self.assertTrue(all(p['context'] != common for values in more.values() for p in values if p['language'] == 'en'))
        for a, b in (('train', 'dev'), ('train', 'test'), ('dev', 'test')):
            for field in ('root', 'article_id', 'context_id'):
                self.assertFalse({p[field] for p in rows[a]} & {p[field] for p in rows[b]})

    def test_unanswerable_counts_exclusions_without_creating_answers(self):
        docs = documents()
        for language in docs:
            qs = docs[language]['train']['document']['data'][0]['paragraphs'][0]['qas']
            qs.append(dict(id='missing', question='Unanswerable '+language, answers=[], is_impossible=True))
            qs[0]['answers'][0]['answer_start'] += 1
        rows, report = collect(docs); annotation = d.annotation_inventory(docs)
        for language in docs:
            self.assertEqual(annotation[language]['train']['annotated_unanswerable_union'], 1)
            self.assertEqual(annotation[language]['train']['replacement_answers_generated'], 0)
            self.assertEqual(report['languages'][language]['rejections']['unanswerable'], 1)
            self.assertEqual(report['languages'][language]['rejections']['answer_span_mismatch'], 1)
        self.assertTrue(all(p['qa_id'] != 'missing' for values in rows.values() for p in values))

    def test_complete_length_and_eot_filters_are_not_relaxed(self):
        rows, _ = collect(); pair = rows['train'][0]
        value, reason = d.data._encoded_pair(pair, CharTokenizer(missing_eot=True))
        self.assertIsNone(value); self.assertEqual(reason, 'complete_answer_eot_mask')
        docs = documents()
        for language in docs:
            for article in docs[language]['train']['document']['data']:
                article['paragraphs'][0]['context'] += ' z' * 600
        with self.assertRaisesRegex(ValueError, 'complete pairs'): collect(docs)


class CountsAndMembershipTests(Guarded):
    @classmethod
    def setUpClass(cls): cls.rows, cls.inventory = collect(train_limit=4)

    def test_single_and_two_views_keep_qa_identity_separate_from_exposure(self):
        values = details(self.rows); summary = d.detail_summary(values)
        for language in ('ko', 'en'):
            train = summary[language]['train']
            self.assertEqual(train['unique_qa_roots'], 4)
            self.assertEqual(train['two_view_exposure']['conversations'], 8)
            self.assertEqual(train['by_view']['0']['assistant_targets'], train['by_view']['1']['assistant_targets'])
            self.assertEqual(train['two_view_exposure']['assistant_targets'], 2 * train['by_view']['0']['assistant_targets'])
            self.assertEqual(train['by_view']['0']['eot_targets'], 4)
            self.assertEqual(train['two_view_exposure']['eot_targets'], 8)
        self.assertTrue(all(not any(k in row for k in ('question', 'context', 'answers', 'aliases', 'views', 'article_title')) for row in values))

    def test_original32k_full_row_reverse_mapping_and_missing_are_exact(self):
        index = baseline_index(self.rows); unlimited, _ = collect()
        values = details(unlimited, index=index); result = d.membership(values, index, require_all=True)
        self.assertEqual(result['ko']['common'], 4); self.assertEqual(result['ko']['missing'], 0)
        self.assertGreater(result['ko']['additional'], 10)
        removed = [r for r in values if r['root'] != next(iter(index))]
        with self.assertRaises(ValueError): d.membership(removed, index, require_all=True)
        changed = copy.deepcopy(values); old_member = next(r for r in changed if r['source32k_member'])
        old_member['full_row_sha256'] = 'X' * 64
        with self.assertRaises(ValueError): d.membership(changed, index)
        pair = copy.deepcopy(self.rows['train'][0]); pair['qa_id'] += '_changed'
        with self.assertRaises(ValueError): d.pair_detail(pair, CharTokenizer(), 2, index)

    def test_corrupted_masks_counts_missing_view_or_split_overlap_refused(self):
        values = details(self.rows)
        for key, value in (('assistant_targets', 0), ('eot_targets', 0), ('content_targets', 999), ('prompt_tokens', 1000)):
            changed = copy.deepcopy(values); changed[0]['metrics']['0'][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError): d.detail_summary(changed)
        changed = copy.deepcopy(values); del changed[0]['metrics']['1']
        with self.assertRaises(ValueError): d.detail_summary(changed)
        changed = copy.deepcopy(values); changed.append(copy.deepcopy(changed[0]))
        with self.assertRaises(ValueError): d.detail_summary(changed)
        changed = copy.deepcopy(values); changed[0]['question'] = 'source text must not be copied'
        with self.assertRaises(ValueError): d.detail_summary(changed)

    def test_cap4_is_not_assumed_to_include_cap2_under_greedy_question_dedup(self):
        docs = documents()
        for language in ('ko', 'en'):
            train = docs[language]['train']['document']['data']
            titles = [a['title'] for a in train if d.article_split(language, a['title']) == 'train'][:2]
            titles.sort(key=lambda t: d.sha([d.SEED, 'ARTICLE_ORDER', d.sha([language, d.normalized(t)])]))
            duplicate = 'Shared counterexample question ' + language
            for pos, title in enumerate(titles):
                context = ('수 7 ' if language == 'ko' else 'Value 7 ') + str(pos)
                answers = [dict(text='7', answer_start=context.index('7'))]
                def key(q, candidate_context):
                    root = d.sha([d.VERSION, language, docs[language]['train']['sha256'], title, candidate_context, q, answers])
                    return d.sha([d.SEED, 'QA_ORDER', root])
                pivot = key(duplicate, context)
                candidates = [('Unique counterexample '+language+' '+str(pos)+' '+str(i),
                    context if pos == 0 else context + ' unique ' + str(i)) for i in range(1000)]
                before = [(q, c) for q, c in candidates if key(q, c) < pivot][:2]
                after = [(q, c) for q, c in candidates if key(q, c) > pivot][:1]
                self.assertEqual((len(before), len(after)), (2, 1))
                chosen = before + [(duplicate, context)] + after
                paragraphs = {}
                for i, (question, candidate_context) in enumerate(chosen):
                    paragraphs.setdefault(candidate_context, []).append(dict(id=language+'_cf_'+str(pos)+'_'+str(i),
                        question=question, answers=copy.deepcopy(answers)))
                at = next(i for i, a in enumerate(train) if a['title'] == title)
                train[at] = dict(title=title, paragraphs=[dict(context=c, qas=qs) for c, qs in paragraphs.items()])
        left, _ = collect(docs, context_question_cap=2); right, _ = collect(docs, context_question_cap=4)
        a = details(left, 2); b = details(right, 4); compared = d.compare_caps(a, b)
        for language in ('ko', 'en'):
            self.assertGreater(compared[language]['absent_in_cap4'], 0)
            self.assertFalse(compared[language]['cap2_subset_cap4'])
            self.assertGreater(compared[language]['added_in_cap4'], 0)
        for split in ('dev', 'test'): self.assertEqual(left[split], right[split])


class StorageTests(Guarded):
    def fixture_baseline(self):
        self.temp_paths(); rows, _ = collect(train_limit=2); code = {'fixture': 'CODE'}; manifests = {}
        for split, pairs in rows.items():
            writer = ShardWriter(d.BASELINE, split)
            for pair in pairs: writer.append(pair)
            manifests[split] = writer.close(lineage=dict(tag=d.baseline_driver.TAG, code_sha256=code))
        report = dict(status='DIVERSITY_CPU_FROZEN', code_sha256=code, manifests=manifests)
        d.write(d.BASELINE / 'report.json', report)
        return rows, report, code

    def test_baseline_full_manifests_roots_and_exact_row_signatures(self):
        rows, _, code = self.fixture_baseline()
        binding, index = d.load_baseline(expected_train=2, expected_eval=2, expected_code=code, enforce_observed=False)
        self.assertEqual(binding['counts'], dict(train=4, dev=4, test=4))
        self.assertEqual(index, baseline_index(rows))

    def test_missing_original_manifest_and_corrupted_raw_are_rejected(self):
        _, report, code = self.fixture_baseline()
        path = d.BASELINE / 'report.json'; changed = copy.deepcopy(report); del changed['manifests']['test']
        path.write_text(json.dumps(changed), encoding='utf-8')
        with self.assertRaises(d.PrerequisitePending):
            d.load_baseline(expected_train=2, expected_eval=2, expected_code=code, enforce_observed=False)
        path.write_text(json.dumps(report), encoding='utf-8')
        raw = d.BASELINE / report['manifests']['train']['shards'][0]['path']
        raw.write_text(raw.read_text(encoding='utf-8').replace('qa_id', 'wrong', 1), encoding='utf-8')
        with self.assertRaises(ValueError):
            d.load_baseline(expected_train=2, expected_eval=2, expected_code=code, enforce_observed=False)

    def test_write_once_symlink_no_overwrite_and_empty_not_run(self):
        root = self.temp_paths(); d.write(root / 'report.json', dict(ok=True))
        with self.assertRaises(FileExistsError): d.write(root / 'report.json', dict(ok=False))
        with self.assertRaises(d.PrerequisitePending): d.required(root / 'missing.json')
        real = root / 'real'; real.mkdir(); link = root / 'linked'; link.symlink_to(real, target_is_directory=True)
        with self.assertRaises(ValueError): d.safe(link / 'report.json')
        with self.assertRaises(ValueError): d.safe(root / '..' / 'outside')

    def test_saved_inventory_check_recounts_raw_and_rejects_count_or_policy_tamper(self):
        baseline_rows, _, _ = self.fixture_baseline()
        index = baseline_index(baseline_rows); binding = dict(report_sha256='BASELINE', counts=dict(train=4, dev=4, test=4))
        metadata = dict(tag=d.TAG, code_sha256={'fixture': 'CODE'},
            existing29m_overlap='NOT_MEASURED', new75m_quota_integration='NOT_MEASURED', no_additive75m_claim=True)
        self.stack.enter_context(patch.object(d, 'info', return_value=metadata))
        self.stack.enter_context(patch.object(d, 'load_baseline', return_value=(binding, index)))
        original_digest = d.data.digest
        source_hashes = {d.ROOT / relative: identity for splits in d.data.SOURCES.values() for relative, identity in splits.values()}
        self.stack.enter_context(patch.object(d.data, 'digest', side_effect=lambda p:
            source_hashes[Path(p)] if Path(p) in source_hashes else original_digest(p)))
        unlimited, _ = collect(); by_cap = {}; cohorts = {}
        for cap in (2, 4):
            values = details(unlimited, cap, index); by_cap[cap] = values
            stem = 'cap' + str(cap); manifest = d.write_detail_shards(stem, values)
            cohorts[str(cap)] = dict(summary=d.detail_summary(values), source32k_membership=d.membership(values, index, require_all=cap == 2),
                detail_manifest=manifest, detail_manifest_sha256=d.data.digest(d.LOCAL / (stem + '_shards_manifest.json')),
                policy='REFERENCE_CAP2' if cap == 2 else 'HYPOTHETICAL_NOT_ADOPTED')
        manifest = d.write_detail_shards('baseline', sorted(index.values(), key=lambda v: v['root']))
        report = dict(metadata, status='CPU_PUBLIC_QA_SUPPLY_COMPLETE_NO_TRAINING_CLAIM',
            baseline=binding, baseline_manifest=manifest,
            baseline_manifest_sha256=d.data.digest(d.LOCAL / 'baseline_shards_manifest.json'),
            cohorts=cohorts, cap_comparison=d.compare_caps(by_cap[2], by_cap[4]),
            cuda_initialized=False, source_text_or_qa_copied_to_output=False, free_answer_quality='NOT_MEASURED')
        path = d.EVIDENCE / 'report.json'; d.write(path, report)
        with redirect_stdout(io.StringIO()): self.assertEqual(d.check(), 0)
        changed = copy.deepcopy(report); changed['cohorts']['2']['summary']['ko']['train']['unique_qa_roots'] += 1
        path.write_text(json.dumps(changed), encoding='utf-8')
        with self.assertRaises(ValueError): d.check()
        changed = copy.deepcopy(report); changed['cohorts']['4']['policy'] = 'REFERENCE_CAP2'
        path.write_text(json.dumps(changed), encoding='utf-8')
        with self.assertRaises(ValueError): d.check()


class DirectEntryTests(Guarded):
    def test_real_common_pipeline_executes_exact_three_commands_and_hold_skips_collect(self):
        commands = []; notes = []
        def launch(command): commands.append(command); return 0
        self.assertEqual(d.prepare(60, launch=launch, note=notes.append), 0)
        self.assertEqual(len(commands), 3)
        self.assertIn('unittest', commands[0]); self.assertIn('--check-only', commands[1])
        self.assertEqual(commands[2][commands[2].index('--mode') + 1], 'collect')
        self.assertIn('--execute', commands[2]); self.assertTrue(any('[EXPERIMENT_FINAL]' in line for line in notes))
        commands.clear(); result = iter((0, 8))
        self.assertEqual(d.prepare(60, launch=lambda command: (commands.append(command), next(result))[1], note=notes.append), 8)
        self.assertEqual(len(commands), 2)

    def test_default_launch_uses_devnull_and_total_timeout_with_actual_pipeline(self):
        run = Mock(return_value=NS(returncode=0))
        with patch.object(d.subprocess, 'run', run), redirect_stdout(io.StringIO()):
            self.assertEqual(d.prepare(60), 0)
        self.assertEqual(run.call_count, 3)
        self.assertTrue(all(call.kwargs['stdin'] == subprocess.DEVNULL and 0 < call.kwargs['timeout'] <= 60
                            for call in run.call_args_list))
        self.assertTrue(all(call.kwargs['env']['CUDA_VISIBLE_DEVICES'] == ''
                            and call.kwargs['env']['OMP_NUM_THREADS'] == '2' for call in run.call_args_list))

    def test_all_cli_modes_connect_to_actions_without_new_sources(self):
        with patch.object(d, 'info', return_value=dict(tag=d.TAG)), \
                patch.object(d, 'prepare', return_value=0) as prepare, \
                patch.object(d, 'collect_work', return_value=0) as collect_action, \
                patch.object(d, 'check', return_value=0) as check, redirect_stdout(io.StringIO()):
            for mode in ('prepare', 'collect', 'check'):
                self.assertEqual(d.main(['--mode', mode, '--check-only']), 0)
            prepare.assert_not_called(); collect_action.assert_not_called(); check.assert_not_called()
            for mode in ('prepare', 'collect', 'check'):
                self.assertEqual(d.main(['--mode', mode, '--execute', '--max-wall-sec', '60']), 0)
            prepare.assert_called_once_with(60); collect_action.assert_called_once_with(60); check.assert_called_once_with()

    def test_invalid_cli_omitted_authority_and_pending_remain_distinct(self):
        with redirect_stderr(io.StringIO()):
            for args in (['--mode', 'prepare'], ['--mode', 'prepare', '--execute', '--check-only'],
                         ['--mode', 'check', '--execute', '--max-wall-sec', '3601']):
                with self.assertRaises(SystemExit): d.main(args)
        with patch.object(d, 'check', side_effect=d.PrerequisitePending('not run')), redirect_stdout(io.StringIO()):
            self.assertEqual(d.main(['--mode', 'check', '--execute']), 8)

    def test_source_free_help_and_check_only_in_fresh_process(self):
        for args in (['--help'], ['--mode', 'prepare', '--check-only']):
            result = subprocess.run([sys.executable, '-B', '-X', 'utf8', str(ROOT / 'scripts/diag_p106b_public_qa_supply.py'), *args],
                cwd=ROOT, stdin=subprocess.DEVNULL, text=True, capture_output=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__': unittest.main(verbosity=2)
