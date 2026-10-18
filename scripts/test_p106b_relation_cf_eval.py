"""Synthetic CPU contracts only; learned model/weight/GPU entrypoints blocked."""
from __future__ import annotations

from contextlib import ExitStack, redirect_stderr, redirect_stdout
import copy
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
sys.path.insert(0, str(ROOT))
from scripts import p106b_relation_cf_eval as cf
from scripts.p106b_shards import ShardWriter


class CharTokenizer:
    """Offset-preserving synthetic tokenizer, never an actual asset or model."""
    def __init__(self, straddle=False, inflate=False):
        self.straddle = straddle; self.inflate = inflate

    def token_to_id(self, token):
        return {'<|im_start|>': 3, '<|im_end|>': 4, '<pad>': 0}.get(token)

    def encode(self, text):
        ids = []; offsets = []; i = 0
        boundary = text.find('<|im_start|>assistant\n') + len('<|im_start|>assistant')
        while i < len(text):
            special = next((s for s in ('<|im_start|>', '<|im_end|>') if text.startswith(s, i)), None)
            if special:
                ids.append(self.token_to_id(special)); offsets.append((i, i + len(special))); i += len(special)
            elif self.straddle and i == boundary and i + 1 < len(text):
                ids.append(999); offsets.append((i, i + 2)); i += 2
            else:
                ids.append(1000 + ord(text[i])); offsets.append((i, i + 1)); i += 1
        if self.inflate:
            ids *= 8; offsets *= 8
        return SimpleNamespace(ids=ids, offsets=offsets)


def relations():
    return cf.data.generate(dict(train=16, dev=8, test=16), eligible=lambda b:
        len(b['answers'][0]) == len(b['answers'][1]))


def source_cases(rows):
    return [cf.original_case(b, q) for b in rows['test'] for q in (0, 1)]


def cases(rows):
    return cf.construct_cases(rows, source_cases(rows), expected_bundles=len(rows['test']))


def metadata(messages, tok, *, reason='STOP_SEQUENCE'):
    from tinylm.chat.serialize import serialize
    prompt = serialize(dict(messages=messages), 'chatml', add_generation_prompt=True)
    prefix = tok.encode(prompt).ids
    return dict(generated_tokens=3 if reason == 'STOP_SEQUENCE' else 128,
        finish_reason=reason, precision='FP32_MATH', temperature=0., top_k=1,
        use_cache=True, mtp=False, prompt_sha256=cf.data.sha(prompt),
        prompt_ids_sha256=cf.data.sha(prefix), prompt_tokens=len(prefix),
        candidate_answers_supplied=False, max_new=128,
        stop_token_sequences=[[4]], matched_stop_sequence=[4] if reason == 'STOP_SEQUENCE' else None,
        generated_ids_sha256='A' * 64)


def answer_events(values, tok, *, bound=None, gold_field='gold'):
    result = []
    for case in values:
        event = dict(id=case['id'], case=copy.deepcopy(case), answer=case[gold_field],
                     generation=metadata(case['messages'], tok))
        if bound is not None:
            event['lineage'] = copy.deepcopy(bound)
        result.append(event)
    return result


def identity(label):
    return dict(endpoint=label, checkpoint='runs/ckpt/synthetic_' + label + '.pt',
        checkpoint_sha256=('A' if label == 'parent' else 'B' if label == 'ce' else 'C') * 64,
        expected_core_sha256='D' * 64, training_report_sha256=None if label == 'parent' else 'E' * 64)


def write_fixture_json(path, value):
    """Intentional temp-fixture mutation only, never a project source edit."""
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True) + '\n', encoding='utf-8')


class Guarded(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack(); self.addCleanup(self.stack.close)
        for name in ('load_parent', 'emit_answer', 'run', 'evaluate', 'native_probe', 'dev_probe', 'rank_probe'):
            self.stack.enter_context(patch.object(cf.original, name,
                side_effect=AssertionError('forbidden real model/GPU path: ' + name)))
        self.stack.enter_context(patch.object(cf.original, 'read_prepared',
            side_effect=AssertionError('real source access forbidden in synthetic tests')))
        self.stack.enter_context(patch('builtins.input', side_effect=AssertionError('interactive input forbidden')))
        import torch
        self.stack.enter_context(patch('torch.load', side_effect=AssertionError('learned weights forbidden')))
        self.stack.enter_context(patch('torch.save', side_effect=AssertionError('checkpoint writing forbidden')))


class DerivativeTests(Guarded):
    def setUp(self):
        super().setUp(); self.rows = relations(); self.values = cases(self.rows); self.tok = CharTokenizer()

    def test_original_bundles_remain_byte_identical_and_valid(self):
        before = copy.deepcopy(self.rows)
        self.assertEqual(self.values, cases(self.rows))
        self.assertEqual(self.rows, before)
        self.assertTrue(cf.data.validate_splits(self.rows))

    def test_derivative_separates_original_and_new_hashes_and_inherits_test(self):
        by_id = {b['bundle_id']: b for b in self.rows['test']}
        for case in self.values:
            parent = by_id[case['parent_bundle_id']]
            self.assertEqual(case['schema'], cf.CASE_SCHEMA)
            self.assertEqual(case['parent_bundle_sha256'], parent['bundle_sha256'])
            self.assertEqual(case['parent_group_id'], parent['group_id'])
            self.assertEqual(case['inherited_source_split'], 'test')
            self.assertNotEqual(case['derivative_fact_graph_sha256'], parent['group_id'])
            self.assertEqual(case['derivative_case_sha256'], cf.data.sha(
                {k: v for k, v in case.items() if k != 'derivative_case_sha256'}))
            self.assertFalse(case['training_example'])

    def test_exactly_two_value_cells_and_two_whole_fact_lines_change(self):
        by_id = {b['bundle_id']: b for b in self.rows['test']}
        for case in self.values:
            parent = by_id[case['parent_bundle_id']]
            changed = [(a, b) for a, b in zip(parent['facts'], case['derivative_facts']) if a != b]
            self.assertEqual(len(changed), 2)
            self.assertTrue(all(a[:2] == b[:2] and a[0] == parent['subject'] for a, b in changed))
            old = cf.original.original.text(case['original_case']['messages'][0]).split('\n')
            new = cf.original.original.text(case['messages'][0]).split('\n')
            changed_lines = [i for i, (a, b) in enumerate(zip(old, new)) if a != b]
            self.assertEqual(changed_lines, [e['line'] for e in case['fact_sentence_edits']])
            self.assertEqual(len(changed_lines), 2)
            self.assertEqual(len(old), len(new))
            self.assertEqual(old[-2:], new[-2:])
            self.assertEqual(case['fact_order'], parent['fact_order'])
            self.assertEqual(case['query_order'], parent['query_order'])

    def test_literal_ko_and_en_roles_swap_while_subject_and_distractor_stay(self):
        for language in ('ko', 'en'):
            found = next(b for b in self.rows['test'] if b['language'] == language)
            case = cf.build_case(found, 0)
            old = found['facts']; new = case['derivative_facts']; subject = found['subject']
            table_old = {(s, r): a for s, r, a in old}; table_new = {(s, r): a for s, r, a in new}
            self.assertEqual(table_new[subject, 0], table_old[subject, 1])
            self.assertEqual(table_new[subject, 1], table_old[subject, 0])
            self.assertEqual([f for f in old if f[0] != subject], [f for f in new if f[0] != subject])
            self.assertEqual(case['gold'], found['answers'][1])
            self.assertNotEqual(case['gold'], case['original_gold'])

    def test_view0_id_mapping_is_exact_and_altered_question_is_rejected(self):
        source = source_cases(self.rows)
        self.assertEqual({c['original_case_id'] for c in self.values}, {c['id'] for c in source})
        changed = copy.deepcopy(source); changed[0]['messages'][0]['content'][0]['text'] += 'changed'
        with self.assertRaises(ValueError):
            cf.construct_cases(self.rows, changed, expected_bundles=16)
        with self.assertRaises(ValueError):
            cf.construct_cases(self.rows, source[:-1], expected_bundles=16)

    def test_train_dev_and_invalid_query_refused(self):
        for split in ('train', 'dev'):
            with self.assertRaises(ValueError): cf.build_case(self.rows[split][0], 0)
        for qi in (-1, 2, True):
            with self.assertRaises(ValueError): cf.build_case(self.rows['test'][0], qi)

    def test_original_tamper_is_not_recertified_by_rehash(self):
        changed = copy.deepcopy(self.rows['test'][0]); changed['answers'][0] = 'invented'
        changed['bundle_sha256'] = cf.data.sha({k: v for k, v in changed.items() if k != 'bundle_sha256'})
        with self.assertRaises(ValueError): cf.build_case(changed, 0)

    def test_missing_or_duplicated_fact_sentence_is_refused(self):
        original_case = cf.original_case
        for mode in ('duplicate', 'missing'):
            def source(bundle, qi):
                case = original_case(bundle, qi)
                prompt = case['messages'][0]['content'][0]['text']
                line = cf.data._sentence(bundle['family'], bundle['facts'][0], bundle['language'])
                case['messages'][0]['content'][0]['text'] = (prompt + '\n' + line if mode == 'duplicate'
                                                           else prompt.replace(line, 'absent', 1))
                return case
            with self.subTest(mode=mode), patch.object(cf, 'original_case', side_effect=source):
                # Ensure the chosen first fact belongs to the queried subject.
                with self.assertRaises((ValueError, IndexError)):
                    cf.build_case(self.rows['test'][0], 0)

    def test_derivative_graph_collision_with_train_is_refused(self):
        rows = copy.deepcopy(self.rows); replacement = None
        for b in rows['test']:
            slots = list(b['slots']); slots[2], slots[3] = slots[3], slots[2]
            candidate = cf.data.build_bundle(b['family'], slots, b['language'])
            if candidate['split'] == 'train':
                replacement = (b['family'], slots); break
        self.assertIsNotNone(replacement)
        family, slots = replacement
        for language in ('ko', 'en'):
            index = next(i for i, b in enumerate(rows['train']) if b['family'] == family and b['language'] == language)
            rows['train'][index] = cf.data.build_bundle(family, slots, language)
        self.assertTrue(cf.data.validate_splits(rows))
        with self.assertRaisesRegex(ValueError, 'overlaps original TRAIN'):
            cf.construct_cases(rows, source_cases(rows), expected_bundles=16)

    def test_inverse_swap_pair_already_in_original_test_is_refused(self):
        rows = copy.deepcopy(self.rows)
        slots_a = [5, 8, 11, 15, 16, 9]
        slots_b = [5, 8, 15, 11, 16, 9]
        for language in ('ko', 'en'):
            indices = [i for i, b in enumerate(rows['test'])
                       if b['family'] == 'kinship' and b['language'] == language]
            self.assertEqual(len(indices), 2)
            for index, slots in zip(indices, (slots_a, slots_b)):
                rows['test'][index] = cf.data.build_bundle('kinship', slots, language)
        self.assertTrue(cf.data.validate_splits(rows))
        a = cf.data.build_bundle('kinship', slots_a, 'ko')
        b = cf.data.build_bundle('kinship', slots_b, 'ko')
        self.assertEqual((a['split'], b['split']), ('test', 'test'))
        self.assertEqual(cf.build_case(a, 0)['derivative_fact_graph_sha256'], b['group_id'])
        self.assertEqual(cf.build_case(b, 0)['derivative_fact_graph_sha256'], a['group_id'])
        with self.assertRaisesRegex(ValueError, 'overlaps original TEST'):
            cf.construct_cases(rows, source_cases(rows), expected_bundles=16)

    def test_coverage_and_prefix_are_source_only_with_minimal_canonical_metadata(self):
        proof = cf.encoding_proof(self.values, self.tok)
        self.assertEqual(proof['responses'], 32)
        self.assertFalse(proof['candidates_in_generation'])
        self.assertLessEqual(proof['max_prompt_tokens'] + 128, 1024)
        row = cf.canonical_row(self.values[0]['messages'], self.values[0]['gold'])
        self.assertEqual(set(row['meta']), {'canonical_version', 'supervised_assistant_turns'})
        self.assertEqual([m['role'] for m in row['messages']], ['user', 'assistant'])

    def test_header_straddle_overflow_and_assistant_in_input_rejected(self):
        with self.assertRaises(ValueError): cf.encoding_proof(self.values, CharTokenizer(straddle=True))
        with self.assertRaises(ValueError): cf.encoding_proof(self.values, CharTokenizer(inflate=True))
        changed = copy.deepcopy(self.values)
        changed[0]['messages'].append(dict(role='assistant', content='oracle'))
        with self.assertRaises(ValueError): cf.encoding_proof(changed, self.tok)

    def test_fixed_production_count_is256_and64_bilingual_graphs(self):
        rows = cf.data.generate(dict(train=8, dev=8, test=128))
        values = cf.construct_cases(rows, source_cases(rows))
        self.assertEqual(len(values), 256)
        self.assertEqual(len({c['parent_group_id'] for c in values}), 64)
        with self.assertRaises(ValueError): cf.construct_cases(self.rows, source_cases(self.rows))


class SummaryTests(Guarded):
    def setUp(self):
        super().setUp(); self.rows = relations(); self.values = cases(self.rows); self.tok = CharTokenizer()
        self.bound = dict(tag=cf.TAG, **identity('ce'))
        self.old = answer_events(source_cases(self.rows), self.tok)
        self.new = answer_events(self.values, self.tok, bound=self.bound)

    def summary(self, new=None, old=None):
        return cf.summarize(self.new if new is None else new, self.values,
            self.old if old is None else old, self.bound, self.tok)

    def test_success_requires_both_original_and_swapped_correct(self):
        summary = self.summary()
        self.assertEqual(summary['additional_responses'], 32)
        self.assertEqual(summary['reused_original_responses'], 32)
        self.assertEqual(summary['independent_fact_graphs'], 8)
        self.assertEqual(summary['bilingual_all_eight_exact'], 8)
        for language in ('ko', 'en'):
            self.assertEqual(summary['counts'][language]['original_and_swapped_exact'], 16)
            self.assertEqual(summary['paired_graphs'][language]['original_and_swapped_all_four_exact'], 8)

    def test_answer_changed_but_still_wrong_is_not_success(self):
        new = copy.deepcopy(self.new)
        for event in new: event['answer'] = 'unrelated new answer'
        summary = self.summary(new)
        for language in ('ko', 'en'):
            self.assertEqual(summary['counts'][language]['answer_changed'], 16)
            self.assertEqual(summary['counts'][language]['original_and_swapped_exact'], 0)
            self.assertEqual(summary['paired_graphs'][language]['original_and_swapped_all_four_exact'], 0)

    def test_original_wrong_swapped_right_is_not_double_success(self):
        old = copy.deepcopy(self.old)
        for event in old: event['answer'] = 'wrong original'
        summary = self.summary(old=old)
        self.assertEqual(summary['counts']['ko']['swapped_exact'], 16)
        self.assertEqual(summary['counts']['ko']['original_and_swapped_exact'], 0)

    def test_previous_gold_stuck_and_actual_answer_repeat_are_explicit(self):
        new = copy.deepcopy(self.new)
        for event in new: event['answer'] = event['case']['original_gold']
        summary = self.summary(new)
        self.assertEqual(summary['counts']['en']['retained_original_gold'], 16)
        self.assertEqual(summary['counts']['en']['repeated_actual_original_answer'], 16)
        self.assertEqual(summary['counts']['en']['swapped_exact'], 0)

    def test_termination_and_exactness_are_independent(self):
        new = copy.deepcopy(self.new)
        for event in new: event['generation'] = metadata(event['case']['messages'], self.tok, reason='MAX_NEW')
        summary = self.summary(new)
        self.assertEqual(summary['counts']['ko']['swapped_exact'], 16)
        self.assertEqual(summary['counts']['ko']['swapped_stopped'], 0)
        self.assertEqual(summary['counts']['ko']['original_and_swapped_exact_and_stopped'], 0)
        self.assertIn('ko|STOP_SEQUENCE|MAX_NEW', summary['by_original_and_swapped_finish'])

    def test_empty_answer_stops_without_becoming_correct(self):
        new = copy.deepcopy(self.new); new[0]['answer'] = ''
        summary = self.summary(new); lang = new[0]['case']['language']
        self.assertEqual(summary['counts'][lang]['swapped_empty'], 1)
        self.assertEqual(summary['counts'][lang]['swapped_stopped'], 16)
        self.assertEqual(summary['counts'][lang]['swapped_exact'], 15)

    def test_empty_or_partial_output_and_missing_original_are_not_run(self):
        for values in ([], self.new[:-1]):
            with self.assertRaises(cf.Pending): self.summary(values)
        with self.assertRaises(cf.Pending): self.summary(old=self.old[:-1])

    def test_duplicate_other_endpoint_or_changed_case_is_tool_error(self):
        for kind in ('duplicate', 'endpoint', 'gold', 'original'):
            changed = copy.deepcopy(self.new)
            if kind == 'duplicate': changed.append(changed[0])
            elif kind == 'endpoint': changed[0]['lineage']['endpoint'] = 'contrast'
            elif kind == 'gold': changed[0]['case']['gold'] = 'invented'
            else: changed[0]['case']['original_case_id'] = 'wrong'
            with self.subTest(kind=kind), self.assertRaises(ValueError): self.summary(changed)

    def test_generation_policy_prompt_token_or_eot_tamper_refused(self):
        changes = dict(precision='BF16', candidate_answers_supplied=True, temperature=1., top_k=2,
            use_cache=False, mtp=True, prompt_sha256='X' * 64, prompt_ids_sha256='X' * 64,
            prompt_tokens=1, max_new=1, generated_tokens=0, generated_ids_sha256='wrong',
            matched_stop_sequence=None, finish_reason='invented', stop_token_sequences=[[99]])
        for key, value in changes.items():
            changed = copy.deepcopy(self.new); changed[0]['generation'][key] = value
            with self.subTest(field=key), self.assertRaises(ValueError): self.summary(changed)


class StorageAndAdmissionTests(Guarded):
    def setUp(self):
        super().setUp()
        temporary = tempfile.TemporaryDirectory(prefix='relation_cf_contract_')
        self.addCleanup(temporary.cleanup); self.root = Path(temporary.name)
        for module, name, path in ((cf, 'ROOT', self.root), (cf, 'LOCAL', self.root / 'local_cf'),
                (cf, 'CORPUS', self.root / 'local_cf/corpus'), (cf, 'EVIDENCE', self.root / 'evidence_cf'),
                (cf.original, 'LOCAL', self.root / 'local_original'),
                (cf.original, 'EVIDENCE', self.root / 'evidence_original')):
            self.stack.enter_context(patch.object(module, name, path))
        self.rows = relations(); self.values = cases(self.rows); self.tok = CharTokenizer()
        self.context = dict(relations=self.rows, source_cases=source_cases(self.rows), cases=self.values,
            tok=self.tok, source=dict(original_code_sha256={'synthetic.py': 'A' * 64},
                original_corpus_report_sha256='B' * 64), prepared_report_sha256='F' * 64)

    def install_original_results(self):
        source = self.context['source_cases']; reports = {}; outputs = {}; hashes = {}
        for label in cf.ENDPOINTS:
            bound = dict(tag=cf.original.TAG, **identity(label))
            local = cf.original.LOCAL / ('evaluate_' + label)
            writer = ShardWriter(local, 'answers', limit=19_999_999)
            events = answer_events(source, self.tok)
            for event in events: writer.append(event)
            manifest = writer.close(lineage=bound)
            rank_writer = ShardWriter(local, 'rank', limit=19_999_999)
            specs = cf.original.rank_specifications(self.rows['test'], self.tok); rank = []
            for bundle in self.rows['test']:
                spec = specs[bundle['bundle_id']]
                first = [dict(branch, correct_logit=-1., crossed_logit=-2., gap=1.) for branch in spec['branches']]
                row = dict(bundle_id=bundle['bundle_id'], group_id=bundle['group_id'], language=bundle['language'],
                    family=bundle['family'], matrix=[[-1., -2.], [-2., -1.]],
                    content_counts=spec['content_counts'], first_divergence=first,
                    source_spec_sha256=cf.data.sha(spec))
                rank.append(row); rank_writer.append(row)
            rank_manifest = rank_writer.close(lineage=bound)
            report = dict(status='ACTUAL_FIRST_ANSWERS_RECORDED', endpoint=label, lineage=bound,
                code_sha256=self.context['source']['original_code_sha256'],
                corpus_sha256=self.context['source']['original_corpus_report_sha256'],
                cases_sha256=cf.data.sha(source), checkpoint_sha256=identity(label)['checkpoint_sha256'],
                core_before=identity(label)['expected_core_sha256'], core_after=identity(label)['expected_core_sha256'],
                answer_manifest=manifest, rank_manifest=rank_manifest,
                answer_manifest_sha256=cf.digest(local / 'answers_shards_manifest.json'),
                rank_manifest_sha256=cf.digest(local / 'rank_shards_manifest.json'),
                model_training=False, weights_changed=False, checkpoints_written=0,
                summary=cf.original.summarize_answers(events, source),
                rank_summary=cf.original.summarize_ranks(rank, self.rows['test'], specs))
            path = cf.original.EVIDENCE / ('evaluate_' + label) / 'report.json'; cf.write(path, report)
            reports[label] = report; outputs[label] = events; hashes[label] = cf.digest(path)
        readback = dict(status='RAW_READBACK_COMPLETE_NO_AUTOMATIC_ADOPTION', tag=cf.original.TAG,
            errors=0, learning_seeds=1, model_training=False,
            code_sha256=self.context['source']['original_code_sha256'],
            cases_sha256=cf.data.sha(source), source_reports_sha256=hashes,
            summaries={k: r['summary'] for k, r in reports.items()},
            contrast_minus_ce=cf.original.paired_relation(outputs['ce'], outputs['contrast'], source))
        cf.write(cf.original.EVIDENCE / 'readback.json', readback)
        self.stack.enter_context(patch.object(cf.original, 'endpoint_identity', side_effect=identity))
        return reports

    def test_write_once_safe_paths_and_empty_stage_status(self):
        path = self.root / 'new/report.json'; cf.write(path, dict(ok=True))
        with self.assertRaises(FileExistsError): cf.write(path, dict(ok=False))
        with self.assertRaises(cf.Pending): cf.required(self.root / 'absent.json')
        empty = self.root / 'empty.json'; empty.touch()
        with self.assertRaises(cf.Pending): cf.required(empty)
        malformed = self.root / 'malformed.json'; malformed.write_text('{', encoding='utf-8')
        with self.assertRaises(ValueError): cf.required(malformed)
        with self.assertRaises(ValueError): cf.safe(self.root / '..' / 'outside')
        with self.assertRaises(ValueError): cf.safe(self.root.parent / 'outside')

    def test_symlink_file_and_parent_paths_are_rejected(self):
        directory = self.root / 'real'; directory.mkdir()
        link = self.root / 'linked'; link.symlink_to(directory, target_is_directory=True)
        for path in (link, link / 'nested.json'):
            with self.assertRaises(ValueError): cf.safe(path)

    def test_write_once_shards_keep_partial_distinct_from_hash_corruption(self):
        directory = self.root / 'shards'; writer = ShardWriter(directory, 'answers')
        writer.append(dict(id=1)); manifest = writer.close(lineage=dict(test=True))
        self.assertEqual(cf.read_shards(directory, manifest, 'answers', 1), [dict(id=1)])
        with self.assertRaises(cf.Pending): cf.read_shards(directory, manifest, 'answers', 2)
        with self.assertRaises(ValueError): cf.read_shards(directory, manifest, 'other', 1)
        (directory / manifest['shards'][0]['path']).write_text('{"id":2}\n', encoding='utf-8')
        with self.assertRaises(ValueError): cf.read_shards(directory, manifest, 'answers', 1)

    def test_original_three_endpoint_manifests_and_readback_recount_pass(self):
        self.install_original_results()
        result = cf.original_results(self.context)
        self.assertEqual(set(result['outputs']), set(cf.ENDPOINTS))
        self.assertEqual(result['identities']['ce'], identity('ce'))
        self.assertEqual(len(result['binding']['original_readback_sha256']), 64)

    def test_missing_original_readback_stops_before_any_model_entry(self):
        with patch.object(cf, 'read_prepared', return_value=self.context):
            with self.assertRaises(cf.Pending): cf.evaluate(3600)
        self.assertFalse(cf.EVIDENCE.exists()); self.assertFalse(cf.LOCAL.exists())

    def test_original_report_replaced_by_other_arm_is_rejected(self):
        reports = self.install_original_results()
        path = cf.original.EVIDENCE / 'evaluate_ce/report.json'
        write_fixture_json(path, reports['contrast'])
        with self.assertRaises(ValueError): cf.original_results(self.context)

    def test_original_raw_corruption_and_manifest_tamper_rejected(self):
        self.install_original_results()
        manifest = cf.required(cf.original.LOCAL / 'evaluate_ce/answers_shards_manifest.json')
        raw = cf.original.LOCAL / 'evaluate_ce' / manifest['shards'][0]['path']
        raw.write_text(raw.read_text(encoding='utf-8').replace('STOP_SEQUENCE', 'STOP_SEQUENCX', 1), encoding='utf-8')
        with self.assertRaises(ValueError): cf.original_results(self.context)

    def test_incomplete_original_readback_status_is_not_run(self):
        self.install_original_results()
        path = cf.original.EVIDENCE / 'readback.json'; report = cf.required(path)
        report['status'] = 'PARTIAL'; write_fixture_json(path, report)
        with self.assertRaises(cf.Pending): cf.original_results(self.context)

    def test_complete_original_readback_tamper_is_tool_error(self):
        self.install_original_results()
        path = cf.original.EVIDENCE / 'readback.json'; report = cf.required(path)
        report['summaries']['ce']['actual_responses'] = 1; write_fixture_json(path, report)
        with self.assertRaises(ValueError): cf.original_results(self.context)

    def test_cpu_prepare_and_readback_roundtrip_without_original_results_or_model(self):
        metadata_info = dict(schema=cf.SCHEMA, tag=cf.TAG, code_sha256={'fixture': '1' * 64})
        self.context['proof'] = cf.encoding_proof(self.values, self.tok)
        with patch.object(cf, 'source_context', return_value=self.context), \
                patch.object(cf, 'info', return_value=metadata_info), \
                patch.object(cf, 'EXPECTED_RESPONSES', 32), redirect_stdout(io.StringIO()):
            self.assertEqual(cf.prepare(), 0)
            self.assertEqual(cf.read_prepared()['cases'], self.values)
            with self.assertRaises(FileExistsError): cf.prepare()
            path = cf.CORPUS / 'report.json'; report = cf.required(path)
            report['source']['original_corpus_report_sha256'] = 'changed'; write_fixture_json(path, report)
            with self.assertRaises(ValueError): cf.read_prepared()

    def test_public_cpu_contract_mutation_is_rejected(self):
        self.context['proof'] = cf.encoding_proof(self.values, self.tok)
        with patch.object(cf, 'source_context', return_value=self.context), \
                patch.object(cf, 'info', return_value=dict(schema=cf.SCHEMA, tag=cf.TAG)), \
                patch.object(cf, 'EXPECTED_RESPONSES', 32), redirect_stdout(io.StringIO()):
            cf.prepare()
            path = cf.EVIDENCE / 'cpu_contract.json'; changed = cf.required(path)
            changed['model_loaded'] = True; write_fixture_json(path, changed)
            with self.assertRaises(ValueError): cf.read_prepared()

    def test_complete_counterfactual_raw_readback_recounts_each_endpoint_write_once(self):
        self.install_original_results(); originals = cf.original_results(self.context)
        metadata_info = dict(schema=cf.SCHEMA, tag=cf.TAG)
        for label in cf.ENDPOINTS:
            bound = cf.lineage(self.context, originals, label)
            events = answer_events(self.values, self.tok, bound=bound)
            local = cf.LOCAL / ('evaluate_' + label)
            writer = ShardWriter(local, 'answers', limit=19_999_999)
            for event in events: writer.append(event)
            manifest = writer.close(lineage=bound)
            report = dict(metadata_info, status='ACTUAL_CF_FIRST_ANSWERS_RECORDED', endpoint=label,
                lineage=bound, source_binding=originals['binding'], cases_sha256=cf.data.sha(self.values),
                core_before='D' * 64, core_after='D' * 64, answer_manifest=manifest,
                answer_manifest_sha256=cf.digest(local / 'answers_shards_manifest.json'),
                summary=cf.summarize(events, self.values, originals['outputs'][label], bound, self.tok),
                model_training=False, weights_changed=False, checkpoints_written=0)
            cf.write(cf.EVIDENCE / ('evaluate_' + label) / 'report.json', report)
        with patch.object(cf, 'read_prepared', return_value=self.context), \
                patch.object(cf, 'info', return_value=metadata_info), \
                patch.object(cf, 'EXPECTED_RESPONSES', 32), redirect_stdout(io.StringIO()):
            self.assertEqual(cf.readback('ce'), 0)
            self.assertEqual(cf.readback(), 0)
            with self.assertRaises(FileExistsError): cf.readback()
        result = cf.required(cf.EVIDENCE / 'readback.json')
        self.assertEqual(set(result['summaries']), set(cf.ENDPOINTS))
        self.assertEqual(result['summaries']['ce']['additional_responses'], 32)
        self.assertEqual(result['summaries']['ce']['independent_fact_graphs'], 8)

    def test_derivative_report_rejects_other_body_source_or_manifest_lineage(self):
        originals = dict(identities={label: identity(label) for label in cf.ENDPOINTS}, binding=dict(original='A' * 64))
        bound = cf.lineage(self.context, originals, 'ce')
        report = dict(status='ACTUAL_CF_FIRST_ANSWERS_RECORDED', endpoint='ce', lineage=bound,
            source_binding=originals['binding'], cases_sha256=cf.data.sha(self.values),
            core_before='D' * 64, core_after='D' * 64, answer_manifest=dict(lineage=bound),
            model_training=False, weights_changed=False, checkpoints_written=0)
        with patch.object(cf, 'info', return_value={}):
            cf.validate_report(report, self.context, originals, 'ce')
            for field, value in dict(endpoint='contrast', source_binding={}, cases_sha256='wrong',
                    core_before='wrong', core_after='wrong', answer_manifest=dict(lineage={}),
                    model_training=True, weights_changed=True, checkpoints_written=1).items():
                changed = copy.deepcopy(report); changed[field] = value
                with self.subTest(field=field), self.assertRaises(ValueError):
                    cf.validate_report(changed, self.context, originals, 'ce')

    def test_cli_check_only_never_opens_sources_or_calls_actions(self):
        with patch.object(cf, 'info', return_value=dict(tag=cf.TAG)), \
                patch.object(cf, 'prepare', side_effect=AssertionError('prepare execution forbidden')), \
                patch.object(cf, 'evaluate', side_effect=AssertionError('GPU execution forbidden')), \
                patch.object(cf, 'readback', side_effect=AssertionError('readback execution forbidden')), \
                redirect_stdout(io.StringIO()):
            for mode in ('prepare', 'evaluate', 'readback'):
                self.assertEqual(cf.main(['--mode', mode, '--check-only']), 0)

    def test_cli_missing_or_conflicting_authority_and_invalid_bounds_fail(self):
        bad = (['--mode', 'prepare'], ['--mode', 'prepare', '--execute', '--check-only'],
               ['--mode', 'prepare', '--execute', '--model', 'ce'],
               ['--mode', 'evaluate', '--execute', '--max-wall-sec', '0'])
        with redirect_stderr(io.StringIO()):
            for args in bad:
                with self.subTest(args=args), self.assertRaises(SystemExit): cf.main(args)

    def test_cli_pending_and_tool_error_remain_distinct(self):
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            with patch.object(cf, 'prepare', side_effect=cf.Pending('not run')):
                self.assertEqual(cf.main(['--mode', 'prepare', '--execute']), 8)
            with patch.object(cf, 'prepare', side_effect=ValueError('tampered')):
                self.assertEqual(cf.main(['--mode', 'prepare', '--execute']), 9)


class CLIProcessTests(unittest.TestCase):
    def test_help_and_check_only_run_in_fresh_process_without_sources(self):
        script = ROOT / 'scripts/p106b_relation_cf_eval.py'
        for args in (['--help'], ['--mode', 'evaluate', '--check-only', '--model', 'ce']):
            result = subprocess.run([sys.executable, '-B', str(script), *args], cwd=ROOT,
                stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertNotIn('Traceback', result.stderr)


if __name__ == '__main__':
    unittest.main(verbosity=2)
