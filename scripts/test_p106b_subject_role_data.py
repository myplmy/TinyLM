"""Pure fictional bundles/tokenizer fixtures; no asset, learned model or GPU IO."""
from __future__ import annotations
import copy
import itertools
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from types import SimpleNamespace as NS
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import p106b_subject_role_data as d


class CharTokenizer:
    """Atomic ChatML tokens and Unicode offsets; no tokenizer file is opened."""
    def __init__(self, *, straddle=False, collapse=False, by_question=False, no_eot=False, inflate=False):
        self.straddle = straddle; self.collapse = collapse; self.by_question = by_question
        self.no_eot = no_eot; self.inflate = inflate

    def token_to_id(self, token):
        return {'<|im_start|>': 3, '<|im_end|>': 4, '<pad>': 0}.get(token)

    def encode(self, text):
        ids = []; offsets = []; i = 0
        header = '<|im_start|>assistant\n'
        body = text.find(header) + len(header) if header in text else len(text)
        delta = (sum(ord(c) for c in text[:body]) % 19) * 100000 if self.by_question else 0
        while i < len(text):
            special = next((s for s in ('<|im_start|>', '<|im_end|>') if text.startswith(s, i)), None)
            if special:
                ids.append(999 if self.no_eot and special == '<|im_end|>' else self.token_to_id(special))
                offsets.append((i, i + len(special))); i += len(special)
            elif self.straddle and i == body - 1 and body < len(text):
                ids.append(998); offsets.append((i, i + 2)); i += 2
            else:
                ids.append((777 if self.collapse else 1000 + ord(text[i])) + (delta if i >= body else 0))
                offsets.append((i, i + 1)); i += 1
        if self.inflate: ids *= 8; offsets *= 8
        return NS(ids=ids, offsets=offsets)


def targets(record): return [v for v in record.y if v != -100]


class SubjectRoleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parents = d.original.generate(dict(train=8, dev=8, test=8))

    def setUp(self):
        self.tok = CharTokenizer()

    def bundle(self, language='ko', family='kinship', split='test'):
        return d.derive_bundle(next(b for b in self.parents[split] if b['language'] == language and b['family'] == family))

    def test_original_parent_is_unchanged_and_derivative_is_honest_schema(self):
        for split, parents in self.parents.items():
            for parent in parents:
                before = copy.deepcopy(parent); bundle = d.derive_bundle(parent)
                self.assertEqual(parent, before); self.assertTrue(d.original.validate_bundle(parent))
                self.assertNotEqual(bundle['schema'], parent['schema'])
                self.assertEqual(bundle['parent_bundle'], parent)
                self.assertEqual(bundle['parent_bundle_sha256'], parent['bundle_sha256'])
                self.assertEqual(bundle['facts'], parent['facts']); self.assertEqual(bundle['slots'], parent['slots'])
                self.assertEqual(bundle['fact_order'], parent['fact_order'])
                self.assertEqual(bundle['query_order'], parent['query_order'])
                self.assertEqual(bundle['split'], split); self.assertTrue(d.validate_bundle(bundle, parent))
                self.assertEqual(bundle['new_fact_graphs_created'], 0)
                self.assertFalse(bundle['world_knowledge_claim']); self.assertFalse(bundle['training_policy_adopted'])

    def test_translations_share_parent_graph_and_split_without_creating_knowledge(self):
        groups = {}
        for parents in self.parents.values():
            for parent in parents:
                groups.setdefault(parent['group_id'], []).append(d.derive_bundle(parent))
        for values in groups.values():
            self.assertEqual(len(values), 2)
            self.assertEqual(values[0]['parent_group_id'], values[1]['parent_group_id'])
            self.assertEqual(values[0]['group_id'], values[1]['group_id'])
            self.assertEqual(values[0]['split'], values[1]['split'])
            self.assertNotEqual(values[0]['bundle_id'], values[1]['bundle_id'])

    def test_literal_four_gold_lookups_for_fixed_subjects_and_roles(self):
        expected = {'ko': ('민수', '영희', ['지훈', '수진', '성호', '지영']),
                    'en': ('Alice', 'Brian', ['Clara', 'David', 'Emma', 'Frank'])}
        for language, (first, other, answers) in expected.items():
            parent = d.original.build_bundle('work', [0, 1, 2, 3, 4, 5], language)
            bundle = d.derive_bundle(parent)
            for qi, query in enumerate(bundle['queries']):
                self.assertEqual(query['subject_id'], qi // 2)
                role = parent['query_order'][qi % 2]
                self.assertEqual(bundle['answers'][qi], answers[2 * (qi // 2) + role])
                prompt = d.message_text(d.render(bundle, qi)['messages'][0])
                question = prompt.split('질문: ' if language == 'ko' else 'Question: ')[1].split('\n')[0]
                self.assertIn(first if qi < 2 else other, question)
            self.assertEqual(len(set(bundle['answers'])), 4)

    def test_first_two_user_and_gold_bytes_match_original_in_all_test_views(self):
        for parent in self.parents['test']:
            bundle = d.derive_bundle(parent)
            for view, qi in itertools.product(range(3), range(2)):
                before = d.original.render(parent, qi, view=view); after = d.render(bundle, qi, view=view)
                self.assertEqual(d.message_text(before['messages'][0]), d.message_text(after['messages'][0]))
                self.assertEqual(d.message_text(before['messages'][1]), d.message_text(after['messages'][1]))
                self.assertEqual(d.query_id(bundle, qi, view), d.original.sha(['RELATION', parent['bundle_id'], view, qi]))

    def test_added_queries_change_only_the_exact_question_line_subject(self):
        for parent in self.parents['test']:
            bundle = d.derive_bundle(parent)
            for view, qi in itertools.product(range(3), (2, 3)):
                before = d.message_text(d.original.render(parent, qi % 2, view=view)['messages'][0]).split('\n')
                after = d.message_text(d.render(bundle, qi, view=view)['messages'][0]).split('\n')
                changed = [i for i, (a, b) in enumerate(zip(before, after)) if a != b]
                self.assertEqual(len(changed), 1); self.assertEqual(before[-1], after[-1])
                self.assertEqual(len(before), len(after))
                for i in range(len(before)):
                    if i not in changed: self.assertEqual(before[i], after[i])
                self.assertEqual(d.message_text(d.render(bundle, qi, view=view)['messages'][1]), bundle['answers'][qi])

    def test_query_ids_stable_candidates_do_not_leak_into_generation(self):
        from tinylm.chat.serialize import serialize
        bundle = self.bundle(); case_ids = []
        for view in range(3):
            for qi in range(4):
                case = d.evaluation_case(bundle, qi, view); case_ids.append(case['id'])
                self.assertEqual([m['role'] for m in case['messages']], ['user'])
                self.assertFalse(case['candidate_answers_supplied'])
                self.assertEqual(case['id'], d.query_id(bundle, qi, view))
                prompts = []
                for ai in range(4):
                    row = d.render(bundle, qi, ai, view)
                    self.assertEqual(set(row['meta']), {'canonical_version', 'supervised_assistant_turns'})
                    self.assertNotIn('source_transform', row['meta'])
                    prompts.append(serialize(dict(messages=row['messages'][:1]), 'chatml', add_generation_prompt=True))
                self.assertEqual(len(set(prompts)), 1)
        self.assertEqual(len(set(case_ids)), 12)

    def test_errors_are_three_exclusive_code_table_types_and_masks_match(self):
        bundle = self.bundle(); checks = d.negative_checks(bundle); masks = d.negative_masks()
        self.assertEqual(len(checks), 12)
        for qi in range(4):
            row = [v for v in checks if v['question_index'] == qi]
            self.assertEqual({v['error_type'] for v in row}, {d.SAME_SUBJECT_OTHER_ROLE,
                d.OTHER_SUBJECT_SAME_ROLE, d.OTHER_SUBJECT_OTHER_ROLE})
            self.assertEqual(d.error_type(qi, qi ^ 1), d.SAME_SUBJECT_OTHER_ROLE)
            self.assertEqual(d.error_type(qi, qi ^ 2), d.OTHER_SUBJECT_SAME_ROLE)
            self.assertEqual(d.error_type(qi, qi ^ 3), d.OTHER_SUBJECT_OTHER_ROLE)
            self.assertEqual(sum(masks['ROLE_ONLY4'][qi]), 1)
            self.assertEqual(sum(masks['ALL_AXES4'][qi]), 3)
            self.assertFalse(masks['ROLE_ONLY4'][qi][qi]); self.assertFalse(masks['ALL_AXES4'][qi][qi])
        masks['ROLE_ONLY4'][0][1] = False
        self.assertTrue(d.negative_masks()['ROLE_ONLY4'][0][1])

    def test_generated_answer_classification_keeps_outside_and_empty_separate(self):
        bundle = self.bundle()
        for qi, ai in itertools.product(range(4), repeat=2):
            self.assertEqual(d.classify_answer(bundle, qi, ' ' + bundle['answers'][ai] + '\n'), d.error_type(qi, ai))
        self.assertEqual(d.classify_answer(bundle, 0, ''), 'EMPTY')
        subject_name = d.original.NAMES[bundle['language']][bundle['subjects'][0]]
        self.assertEqual(d.classify_answer(bundle, 0, subject_name), 'OTHER_CONTEXT_ENTITY')
        self.assertEqual(d.classify_answer(bundle, 0, 'unrelated text'), 'OUT_OF_TABLE')

    def test_fact_gold_label_parent_and_resigned_hash_tamper_refused(self):
        bundle = self.bundle()
        changes = dict(answers=['wrong'] * 4, slots=[0] * 6, facts=[], fact_order=[0, 1, 2, 3],
            queries=[], split='train', parent_bundle_sha256='X' * 64, group_id='wrong',
            label_status='GPT_CERTIFIED_WORLD_TRUTH', training_policy_adopted=True)
        for field, value in changes.items():
            changed = copy.deepcopy(bundle); changed[field] = value
            changed['bundle_sha256'] = d.original.sha({k: v for k, v in changed.items() if k != 'bundle_sha256'})
            if changed == bundle: continue
            with self.subTest(field=field), self.assertRaises(ValueError): d.validate_bundle(changed)
        parent = copy.deepcopy(bundle['parent_bundle']); parent['subject'] = parent['slots'][1]
        with self.assertRaises(ValueError): d.derive_bundle(parent)
        parent = copy.deepcopy(bundle['parent_bundle']); parent['slots'][3] = parent['slots'][2]
        with self.assertRaises(ValueError): d.derive_bundle(parent)
        with self.assertRaises(ValueError): d.validate_bundle(bundle, self.parents['dev'][0])

    def test_complete_records_all_candidates_keep_targets_lengths_prefix_and_eot(self):
        for language in ('ko', 'en'):
            bundle = self.bundle(language); positives, crossed = d.encode_bundle(bundle, self.tok)
            records = dict(zip(d.POSITIVE_LAYOUT + d.CROSSED_LAYOUT, positives + crossed))
            self.assertEqual((len(positives), len(crossed)), (4, 12))
            for qi, ai in itertools.product(range(4), repeat=2):
                rec = records[qi, ai]
                self.assertEqual(targets(rec), targets(positives[ai]))
                self.assertEqual(targets(rec)[-1], 4)
                first = next(i for i, y in enumerate(rec.y) if y != -100)
                prefix = rec.x[:first + 1]
                self.assertEqual(prefix, records[qi, qi].x[:first + 1])
                self.assertEqual(sum(rec.segments), len(targets(rec)))
                self.assertTrue(all(y == -100 for y in rec.y[:first]))

    def test_unequal_candidate_lengths_are_not_filtered_or_treated_as_more_questions(self):
        parent = d.original.build_bundle('work', [0, 1, 2, 3, 4, 5], 'en')
        bundle = d.derive_bundle(parent); positive, cross = d.encode_bundle(bundle, self.tok)
        lengths = [len(targets(r)) - 1 for r in positive]
        self.assertGreater(len(set(lengths)), 1)
        self.assertEqual(len(positive), 4); self.assertEqual(len(cross), 12)
        self.assertEqual(sorted(lengths), sorted(len(name) for name in ('Clara', 'David', 'Emma', 'Frank')))

    def test_straddle_missing_eot_collapsed_names_question_dependent_tokens_overflow_fail(self):
        bundle = self.bundle()
        for tokenizer in (CharTokenizer(straddle=True), CharTokenizer(no_eot=True),
                          CharTokenizer(collapse=True), CharTokenizer(by_question=True), CharTokenizer(inflate=True)):
            with self.subTest(tokenizer=tokenizer.__dict__), self.assertRaises(ValueError):
                d.encode_bundle(bundle, tokenizer)

    def test_flattened_graph_question_candidate_order_and_micro8x3(self):
        self.assertEqual(d.POSITIVE_LAYOUT, ((0, 0), (1, 1), (2, 2), (3, 3)))
        self.assertEqual(d.CROSSED_LAYOUT, tuple((i, j) for i in range(4) for j in range(4) if j != i))
        bundles = [d.derive_bundle(b) for b in self.parents['train'][:2]]
        positive, cross = d.encode_micro(bundles, self.tok)
        self.assertEqual((len(positive), len(cross)), (8, 24))
        individual = [d.encode_bundle(b, self.tok) for b in bundles]
        self.assertEqual(positive, individual[0][0] + individual[1][0])
        self.assertEqual(cross, individual[0][1] + individual[1][1])
        batches = d.cross_micro_batches(cross)
        self.assertEqual([len(v) for v in batches], [8, 8, 8])
        self.assertEqual(sum(batches, []), cross)
        with self.assertRaises(ValueError): d.encode_micro(bundles[:1], self.tok)
        with self.assertRaises(ValueError): d.encode_micro([bundles[0]] * 2, self.tok)
        with self.assertRaises(ValueError): d.cross_micro_batches(cross[:-1])

    def test_train_eval_view_boundary_matches_original(self):
        bundle = self.bundle(split='train')
        for qi in range(4):
            d.render(bundle, qi)
            for view in (1, 2):
                with self.assertRaises(ValueError): d.render(bundle, qi, view=view)
        for value in (-1, 4, True):
            with self.assertRaises(ValueError): d.render(self.bundle(), value)
            with self.assertRaises(ValueError): d.error_type(0, value)

    def test_shortcut_upper_bounds_and_restricted_scope_are_independent_certificates(self):
        for parent in self.parents['test']:
            bundle = d.derive_bundle(parent); gold = bundle['answers']
            for view in range(3):
                bounds = d.shortcut_bounds(bundle, view)
                self.assertEqual({k: v['correct'] for k, v in bounds.items()},
                    dict(role_only=2, subject_only=2, constant=1, first_fact=1))
                self.assertTrue(bounds['role_only']['original_two_correct'])
                self.assertFalse(bounds['role_only']['additional_two_correct'])
                self.assertTrue(all(not v['all_four_correct'] for v in bounds.values()))
            role_max = max(sum(choice[i % 2] == gold[i] for i in range(4))
                           for choice in itertools.product(gold, repeat=2))
            subject_max = max(sum(choice[i // 2] == gold[i] for i in range(4))
                              for choice in itertools.product(gold, repeat=2))
            constant_max = max(sum(value == answer for answer in gold) for value in gold)
            self.assertEqual((role_max, subject_max, constant_max), (2, 2, 1))
        self.assertIn('unrestricted language models', d.shortcut_bounds.__doc__)
        self.assertIn('stochastic', d.shortcut_bounds.__doc__)
        self.assertIn('unconditional', d.shortcut_bounds.__doc__)

    def test_module_operations_do_not_open_assets_or_construct_models(self):
        bundle = self.bundle()
        with patch('builtins.open', side_effect=AssertionError('asset IO forbidden')):
            d.validate_bundle(bundle); d.render(bundle, 3); d.query_id(bundle, 3)
            d.evaluation_case(bundle, 2); d.negative_checks(bundle); d.shortcut_bounds(bundle)

    def test_absolute_direct_import_from_arbitrary_cwd(self):
        script = ROOT / 'scripts/p106b_subject_role_data.py'
        program = ('import importlib.util, sys; '
            'spec = importlib.util.spec_from_file_location("subject_role_direct_import", sys.argv[1]); '
            'module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module); '
            'assert str(module.ROOT) == sys.argv[2]; '
            'assert module.TAG == "p106b_subject_role_v1_s1337"; '
            'assert len(module.CROSSED_LAYOUT) == 12')
        with TemporaryDirectory(prefix='subject_role_direct_import_') as folder:
            result = subprocess.run([sys.executable, '-B', '-X', 'utf8', '-c', program, str(script), str(ROOT)],
                cwd=folder, stdin=subprocess.DEVNULL, text=True, capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__': unittest.main(verbosity=2)
