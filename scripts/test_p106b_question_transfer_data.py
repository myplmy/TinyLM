"""Synthetic stdlib tests only: no source, tokenizer, tensors or model IO."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import builtins
from collections import Counter, defaultdict
from contextlib import ExitStack
import copy
from functools import lru_cache
import io
import itertools
import json
import os
import random
import unittest
from unittest.mock import patch
from scripts import p106b_question_transfer_data as d


@lru_cache(maxsize=1)
def course():
    return d.build_course()


def first(family, split='train'):
    return next(p for p in course()[split] if p['family'] == family)


def groups(values):
    output = defaultdict(list)
    for problem in values:
        output[problem['parent_group_id']].append(problem)
    return output


def resign(problem):
    problem['problem_sha256'] = d.sha({k: v for k, v in problem.items() if k != 'problem_sha256'})


class CourseTests(unittest.TestCase):
    def test_exact_neutral_and_bilingual_quotas_and_json_roundtrip(self):
        c = course()
        self.assertEqual([len(c[s]) for s in d.SPLITS], [2048, 192, 192])
        for split in d.SPLITS:
            self.assertEqual(Counter(p['family'] for p in c[split]), d.QUOTAS[split])
            self.assertEqual(c['metadata']['summary'][split]['bilingual_records'], 2 * len(c[split]))
        self.assertTrue(d.validate_course(json.loads(json.dumps(c, ensure_ascii=False))))

    def test_deterministic_seed_local_rng_and_inputs_unmodified(self):
        blocked = {'arithmetic': [['+', 1, 1], ['+', 2, 2]], 'format_literals': ['100', 'red']}
        before = copy.deepcopy(blocked); rng = random.getstate()
        a = d.build_course(blocked); b = d.build_course(copy.deepcopy(blocked))
        self.assertEqual(a, b); self.assertEqual(blocked, before); self.assertEqual(random.getstate(), rng)
        self.assertNotEqual(d.sha(a['train']), d.sha(d.build_course(blocked, seed=20261020)['train']))

    def test_all_parents_and_query_ids_are_split_disjoint(self):
        c = course(); ids = [p['query_id'] for s in d.SPLITS for p in c[s]]
        self.assertEqual(len(ids), len(set(ids)))
        for a, b in itertools.combinations(d.SPLITS, 2):
            self.assertFalse(set(groups(c[a])) & set(groups(c[b])))
        for split in d.SPLITS:
            self.assertTrue(all(p['split'] == split for p in c[split]))

    def test_arithmetic_domain_operator_balance_and_computed_targets(self):
        for split in d.SPLITS:
            values = [p for p in course()[split] if p['family'] == 'arithmetic']
            self.assertEqual(Counter(p['state']['op'] for p in values), {'+': len(values) // 2, '-': len(values) // 2})
            for p in values:
                a, b, op = p['state']['a'], p['state']['b'], p['state']['op']
                self.assertTrue(0 <= a <= 50 and 0 <= b <= 50)
                if op == '+': self.assertLessEqual(a, b)
                self.assertEqual(p['target_by_language'], dict.fromkeys(d.LANGUAGES, str(a + b if op == '+' else a - b)))
        self.assertTrue(any(p['target_by_language']['en'].startswith('-') for p in course()['train'] if p['family'] == 'arithmetic'))
        self.assertEqual(d.arithmetic_key('+', 9, 3), d.arithmetic_key('+', 3, 9))
        self.assertNotEqual(d.arithmetic_key('-', 9, 3), d.arithmetic_key('-', 3, 9))

    def test_boolean_pairs_all_valuations_and_operators_stay_in_one_split(self):
        banks = {}
        for split in d.SPLITS:
            values = [p for p in course()[split] if p['family'] == 'boolean']; banks[split] = set()
            counts = Counter(); labels = Counter()
            for p in values:
                bindings = dict(p['state']['bindings']); names = tuple(sorted(bindings)); banks[split].add(names)
                a, b = (bindings[n] for n in names); op = p['query']['operator']
                counts[op, a, b] += 1
                expected = a and b if op == 'AND' else a or b if op == 'OR' else a != b
                self.assertEqual(p['target_by_language'], dict.fromkeys(d.LANGUAGES, str(expected).lower()))
                labels[expected] += 1
            self.assertEqual(len(banks[split]), d.PAIR_QUOTAS[split])
            self.assertEqual(labels, {False: len(values) // 2, True: len(values) // 2})
            for op, each in d.BOOL_ALLOCATION[split].items():
                for a, b in itertools.product((False, True), repeat=2): self.assertEqual(counts[op, a, b], each)
            report = course()['metadata']['summary'][split]['boolean']
            self.assertEqual(report['truth_functions'], 3); self.assertEqual(report['ordered_truth_table_patterns'], 12)
            self.assertFalse(report['unseen_logical_functions_claim'])
        for a, b in itertools.combinations(d.SPLITS, 2): self.assertFalse(banks[a] & banks[b])

    def test_lookup_complete_four_queries_unique_answers_and_order_independent_sha(self):
        for split, expected in (('train', 128), ('dev', 8), ('test', 8)):
            bank = groups([p for p in course()[split] if p['family'] == 'lookup'])
            self.assertEqual(len(bank), expected)
            for gid, values in bank.items():
                self.assertEqual(len(values), 4)
                for language in d.LANGUAGES: self.assertEqual(len({p['target_by_language'][language] for p in values}), 4)
                state = copy.deepcopy(values[0]['state']); state['facts'].reverse(); state['subjects'].reverse()
                self.assertEqual(d.lookup_parent_signature(state), gid)
                self.assertEqual(len({p['rotation'] for p in values}), 1)

    def test_format_both_keys_and_languages_share_literal_group(self):
        for split, expected in (('train', 128), ('dev', 16), ('test', 16)):
            bank = groups([p for p in course()[split] if p['family'] == 'format'])
            self.assertEqual(len(bank), expected)
            for values in bank.values():
                self.assertEqual({p['query']['key'] for p in values}, {'answer', 'result'})
                self.assertEqual(len({p['state']['literal'] for p in values}), 1)
                self.assertEqual(len({p['rotation'] for p in values}), 1)
                for p in values:
                    for language in d.LANGUAGES:
                        self.assertEqual(json.loads(p['target_by_language'][language]), {p['query']['key']: p['state']['literal']})

    def test_metadata_is_source_only_not_actual_freeze_or_knowledge_claim(self):
        meta = course()['metadata']
        self.assertFalse(meta['actual_source_exclusions_verified']); self.assertFalse(meta['tokenizer_verified'])
        self.assertFalse(meta['natural_qa_or_replay_included']); self.assertFalse(meta['world_knowledge_claim'])
        self.assertFalse(meta['unique_logical_knowledge_claim']); self.assertEqual(meta['models_loaded'], 0)
        for split in d.SPLITS:
            controls = meta['summary'][split]['lookup_controls']; n = controls['neutral_queries']
            self.assertEqual(controls['correct_counts'], dict(first_fact=n // 4, subject_only=n // 2, attribute_only=n // 2))
            b = meta['summary'][split]['boolean']; self.assertEqual(b['constant_false_correct'], b['named_instances'] // 2)


class ExclusionTests(unittest.TestCase):
    def test_empty_means_no_hidden_exclusions_and_normalization_is_set_based(self):
        self.assertTrue(all(v == [] for v in course()['blocked'].values()))
        supplied = dict(arithmetic=[['+', 8, 3], ['+', 3, 8], ['*', 90, -2]],
                        boolean_name_pairs=[['B', 'A'], ['A', 'B'], ['Ian', 'Jin']],
                        format_literals=['blue', '100', '100'])
        before = copy.deepcopy(supplied); out = d.normalize_blocked(supplied)
        self.assertEqual(supplied, before)
        self.assertEqual(out['arithmetic'], [['*', -2, 90], ['+', 3, 8]])
        self.assertEqual(out['boolean_name_pairs'], [['A', 'B'], ['Ian', 'Jin']])
        self.assertEqual(out['format_literals'], ['100', 'blue'])

    def test_explicit_user_and_reversed_addition_exclusions_apply_to_every_split(self):
        key = first('arithmetic')['state']; supplied = {'arithmetic': [['+', 1, 1], ['+', 2, 2], [key['op'], key['b'], key['a']]]}
        if key['op'] == '-': supplied['arithmetic'][-1] = ['-', key['a'], key['b']]
        c = d.build_course(supplied); forbidden = {tuple(v) for v in c['blocked']['arithmetic']}
        for split in d.SPLITS:
            for p in c[split]:
                if p['family'] == 'arithmetic': self.assertNotIn(d.arithmetic_key(p['state']['op'], p['state']['a'], p['state']['b']), forbidden)
        self.assertTrue(d.validate_course(c))

    def test_all_six_old_abcd_pairs_are_excluded_without_silent_replacement_policy(self):
        denied = [list(v) for v in itertools.combinations('ABCD', 2)]
        c = d.build_course({'boolean_name_pairs': denied})
        for split in d.SPLITS:
            pairs = {tuple(sorted(n for n, v in p['state']['bindings'])) for p in c[split] if p['family'] == 'boolean'}
            self.assertFalse(pairs & {tuple(v) for v in denied}); self.assertEqual(len(pairs), d.PAIR_QUOTAS[split])

    def test_lookup_full_parent_and_literal_exclusions_are_exact(self):
        lookup = first('lookup'); literal = first('format')['state']['literal']
        c = d.build_course({'lookup_parent_signatures': [lookup['parent_group_id'].lower()], 'format_literals': [literal]})
        for split in d.SPLITS:
            self.assertTrue(all(p['parent_group_id'] != lookup['parent_group_id'] for p in c[split]))
            self.assertTrue(all(p['state'].get('literal') != literal for p in c[split]))

    def test_insufficient_arithmetic_preserves_domain_and_quotas(self):
        denied = [['+', a, b] for a in range(51) for b in range(a, 51)]
        with self.assertRaisesRegex(d.SupplyError, 'arithmetic/\\+'):
            d.build_course({'arithmetic': denied})

    def test_insufficient_boolean_pair_supply_is_not_filled_with_duplicates(self):
        pairs = list(itertools.combinations(d.LETTERS, 2))
        with self.assertRaisesRegex(d.SupplyError, 'need36 distinct groups, found35'):
            d.build_course({'boolean_name_pairs': [list(v) for v in pairs[35:]]})

    def test_insufficient_literal_or_lookup_supply_fails_instead_of_lowering_counts(self):
        with self.assertRaisesRegex(d.SupplyError, 'format literals'):
            d.build_course({'format_literals': [str(i) for i in range(100, 10000)]})
        with patch.object(d, '_lookup_candidates', return_value=iter(())):
            with self.assertRaisesRegex(d.SupplyError, 'lookup tables'):
                d.build_course()

    def test_malformed_blocked_input_cannot_bypass_the_declared_schema(self):
        for supplied in ({'unknown': []}, {'arithmetic': [['/', 1, 2]]}, {'arithmetic': [['+', True, 2]]},
                         {'boolean_name_pairs': [['A', 'A']]}, {'format_literals': [123]},
                         {'lookup_parent_signatures': ['../outside']}, {'arithmetic': 'not a list'}):
            with self.subTest(supplied=supplied), self.assertRaises(ValueError): d.normalize_blocked(supplied)


class IntegrityTests(unittest.TestCase):
    def test_target_state_query_fingerprint_and_unknown_fields_are_rejected(self):
        for family in d.FAMILIES:
            for field in ('target', 'state_sha', 'query_id', 'extra'):
                p = copy.deepcopy(first(family))
                if field == 'target': p['target_by_language']['ko'] = 'not the producer target'; resign(p)
                elif field == 'state_sha': p['state_sha256'] = '0' * 64; resign(p)
                elif field == 'query_id': p['query_id'] = '0' * 64; resign(p)
                else: p['source_transform'] = 'unregistered'
                with self.subTest(family=family, field=field), self.assertRaises(ValueError): d.validate_problem(p)

    def test_bad_numeric_bool_lookup_and_literal_domains_are_not_repaired(self):
        invalid = []
        p = copy.deepcopy(first('arithmetic')); p['state']['a'] = True; invalid.append(p)
        p = copy.deepcopy(first('arithmetic')); p['state']['a'] = 51; invalid.append(p)
        p = copy.deepcopy(first('boolean')); p['state']['bindings'][0][1] = 0; invalid.append(p)
        p = copy.deepcopy(first('boolean')); p['query']['operands'] = [[], 'A']; invalid.append(p)
        p = copy.deepcopy(first('lookup')); p['state']['facts'][0] = copy.deepcopy(p['state']['facts'][1]); invalid.append(p)
        p = copy.deepcopy(first('lookup')); p['state']['subjects'] = [[], 'A']; invalid.append(p)
        p = copy.deepcopy(first('format')); p['state']['literal'] = '099'; invalid.append(p)
        for p in invalid:
            resign(p)
            with self.subTest(family=p['family']), self.assertRaises(ValueError): d.validate_problem(p)

    def test_missing_duplicate_and_metadata_tamper_cannot_be_complete_course(self):
        for kind in ('missing', 'duplicate', 'metadata', 'family', 'seed'):
            c = copy.deepcopy(course())
            if kind == 'missing': c['train'].pop()
            elif kind == 'duplicate': c['train'][1] = copy.deepcopy(c['train'][0])
            elif kind == 'metadata': c['metadata']['summary']['train']['neutral_problems'] -= 1
            elif kind == 'family': c['train'][0]['family'] = []
            else: c['seed'] = True
            with self.subTest(kind=kind), self.assertRaises(ValueError): d.validate_course(c)

    def test_boolean_parent_leak_is_rejected_even_for_a_new_operator_query(self):
        c = copy.deepcopy(course()); existing = {p['query_id'] for split in d.SPLITS for p in c[split]}; added = None
        for p in c['train']:
            if p['family'] != 'boolean': continue
            for op in ('AND', 'OR', 'XOR'):
                q = dict(operator=op, operands=p['query']['operands'])
                candidate = d._problem('boolean', p['state'], q, 'dev')
                if candidate['query_id'] not in existing: added = candidate; break
            if added is not None: break
        self.assertIsNotNone(added)
        index = next(i for i, p in enumerate(c['dev']) if p['family'] == 'boolean'); c['dev'][index] = added
        with self.assertRaisesRegex(ValueError, 'parent group'): d.validate_course(c)


class ScheduleAndRenderingTests(unittest.TestCase):
    def test_all_four_arms_have_the_exact_per_instance_four_pass_views(self):
        expected = {'fixed_last': Counter({(0, 'CQ'): 4}),
                    'varied_last': Counter({(0, 'CQ'): 2, (1, 'CQ'): 2}),
                    'fixed_balanced': Counter({(0, 'CQ'): 2, (0, 'QC'): 2}),
                    'varied_balanced': Counter({(0, 'CQ'): 1, (0, 'QC'): 1, (1, 'CQ'): 1, (1, 'QC'): 1})}
        for p in course()['train']:
            for arm in d.ARMS:
                views = [d.schedule_view(p, arm, e) for e in range(4)]
                self.assertEqual(Counter((v['wording'], v['position']) for v in views), expected[arm])
                self.assertTrue(all(v['wording'] in (0, 1) for v in views))

    def test_family_language_and_boolean_target_are_counterbalanced_each_epoch(self):
        for split in d.SPLITS:
            for family in d.FAMILIES:
                values = [p for p in course()[split] if p['family'] == family]
                self.assertEqual(Counter(p['rotation'] for p in values), dict.fromkeys(range(4), len(values) // 4))
        for epoch in range(4):
            for family in d.FAMILIES:
                values = [p for p in course()['train'] if p['family'] == family]
                counts = Counter((d.schedule_view(p, 'varied_balanced', epoch)['wording'], d.schedule_view(p, 'varied_balanced', epoch)['position']) for p in values)
                self.assertEqual(set(counts.values()), {len(values) // 4})
            for target in ('true', 'false'):
                values = [p for p in course()['train'] if p['family'] == 'boolean' and p['target_by_language']['en'] == target]
                self.assertEqual(Counter(p['rotation'] for p in values), dict.fromkeys(range(4), len(values) // 4))

    def test_schedule_rejects_heldout_training_unknown_arms_and_bad_epochs(self):
        for arm, epoch, p in [('unknown', 0, first('arithmetic')), (d.ARMS[0], True, first('arithmetic')),
                              (d.ARMS[0], 4, first('arithmetic')), (d.ARMS[0], 0, first('arithmetic', 'test'))]:
            with self.assertRaises(ValueError): d.schedule_view(p, arm, epoch)

    def test_all_surfaces_and_positions_preserve_target_context_and_minimal_contract(self):
        for family in d.FAMILIES:
            p = first(family); original = copy.deepcopy(p)
            for language in d.LANGUAGES:
                questions = []
                for wording in range(4):
                    a = d.render(p, language, wording, 'CQ'); b = d.render(p, language, wording, 'QC')
                    self.assertEqual([m['role'] for m in a['messages']], ['user', 'assistant'])
                    self.assertEqual(a['messages'][1]['content'], p['target_by_language'][language])
                    self.assertEqual(a['messages'][1], b['messages'][1])
                    self.assertEqual(a['meta']['context_sha256'], b['meta']['context_sha256'])
                    self.assertEqual(a['meta']['question_sha256'], b['meta']['question_sha256'])
                    self.assertEqual(a['meta']['supervised_assistant_turns'], [1])
                    self.assertNotIn('source_transform', a['meta']); self.assertEqual(a['meta']['teacher_calls'], 0)
                    c_label, q_label = ('자료:\n', '질문:\n') if language == 'ko' else ('Data:\n', 'Question:\n')
                    body = a['messages'][0]['content']; instruction, rest = body.split('\n', 1)
                    context, question = rest[len(c_label):].split('\n' + q_label)
                    self.assertEqual(b['messages'][0]['content'], instruction + '\n' + q_label + question + '\n' + c_label + context)
                    questions.append(question)
                self.assertEqual(len(set(questions)), 4)
            self.assertEqual(p, original)

    def test_arithmetic_operands_and_operation_are_only_in_context_not_question(self):
        p = first('arithmetic')
        for language in d.LANGUAGES:
            for wording in range(4):
                row = d.render(p, language, wording, 'CQ'); label = '질문:\n' if language == 'ko' else 'Question:\n'
                question = row['messages'][0]['content'].split(label)[1]
                self.assertFalse(any(ch.isdigit() for ch in question)); self.assertNotIn('+', question); self.assertNotIn('-', question)
                self.assertIn('%d %s %d' % (p['state']['a'], p['state']['op'], p['state']['b']), row['messages'][0]['content'])

    def test_json_literal_is_input_data_not_a_precompleted_gold_object(self):
        p = first('format')
        for language in d.LANGUAGES:
            row = d.render(p, language, 2, 'QC')
            self.assertIn(json.dumps(p['state']['literal']), row['messages'][0]['content'])
            self.assertNotIn(p['target_by_language'][language], row['messages'][0]['content'])
            self.assertEqual(row['meta']['input_contract'], 'FORMAT_LITERAL_INPUT')

    def test_bad_render_arguments_fail_without_any_fallback(self):
        for language, wording, position in [('fr', 0, 'CQ'), ('ko', True, 'CQ'), ('en', 4, 'CQ'), ('ko', 0, 'QCQ')]:
            with self.assertRaises(ValueError): d.render(first('format'), language, wording, position)


class ClassificationTests(unittest.TestCase):
    def test_every_producer_target_is_accepted_without_mutation(self):
        c = course(); before = d.sha(c)
        for split in d.SPLITS:
            for p in c[split]:
                for language in d.LANGUAGES:
                    self.assertIs(d.classify(p, language, p['target_by_language'][language]), True)
        self.assertEqual(d.sha(c), before)

    def test_arithmetic_is_whole_signed_ascii_integer_not_digit_extraction(self):
        p = first('arithmetic'); target = p['target_by_language']['en']
        self.assertTrue(d.classify(p, 'en', '\n ' + target + '\t'))
        canonical = int(target)
        padded = ('-' if canonical < 0 else '+') + '00' + str(abs(canonical))
        self.assertTrue(d.classify(p, 'en', padded))
        for value in [target + '.0', 'answer=' + target, target + ' x', '', '１２', True, None, '--' + target]:
            self.assertFalse(d.classify(p, 'en', value))

    def test_boolean_casefold_and_outer_whitespace_are_not_substring_matching(self):
        p = first('boolean'); target = p['target_by_language']['en']
        self.assertTrue(d.classify(p, 'en', ' ' + target.upper() + '\n'))
        for value in ['not ' + target, target + ' because', '1', '', None]: self.assertFalse(d.classify(p, 'en', value))

    def test_lookup_is_exact_value_not_casefold_or_name_presence(self):
        p = first('lookup'); value = p['target_by_language']['en']
        self.assertTrue(d.classify(p, 'en', '\n' + value + ' '))
        self.assertFalse(d.classify(p, 'en', value.upper()))
        self.assertFalse(d.classify(p, 'en', 'The answer is ' + value))
        self.assertFalse(d.classify(p, 'en', p['query']['subject']))

    def test_strict_json_duplicate_extra_nonstring_and_wrapping_are_rejected(self):
        p = first('format'); key, literal = p['query']['key'], p['state']['literal']
        self.assertTrue(d.classify(p, 'en', ' \n' + json.dumps({key: literal}, indent=2) + '\t'))
        values = [literal, json.dumps(literal), '{"%s":"%s","%s":"%s"}' % (key, literal, key, literal),
                  json.dumps({key: literal, 'extra': literal}), json.dumps({key: int(literal)}),
                  json.dumps({key: ' ' + literal}), json.dumps({'wrong': literal}),
                  '[' + json.dumps({key: literal}) + ']', '```json\n' + p['target_by_language']['en'] + '\n```',
                  p['target_by_language']['en'] + ' explanation', '{"%s":NaN}' % key]
        for raw in values:
            before = raw
            with self.subTest(raw=raw): self.assertIs(d.classify(p, 'en', raw), False)
            self.assertEqual(raw, before)

    def test_counterfactual_lookup_and_boolean_targets_are_not_constant_controls(self):
        values = next(iter(groups([p for p in course()['train'] if p['family'] == 'lookup']).values()))
        constant = values[0]['target_by_language']['en']
        self.assertEqual(sum(d.classify(p, 'en', constant) for p in values), 1)
        p = first('boolean'); state = copy.deepcopy(p['state'])
        if p['query']['operator'] == 'XOR': state['bindings'][0][1] = not state['bindings'][0][1]
        else:
            wanted = not (p['target_by_language']['en'] == 'true')
            for b in state['bindings']: b[1] = wanted
        changed = d._problem('boolean', state, p['query'], 'test')
        self.assertNotEqual(p['target_by_language'], changed['target_by_language'])
        self.assertFalse(d.classify(changed, 'en', p['target_by_language']['en']))


class EvaluationAndPurityTests(unittest.TestCase):
    def test_outcome_independent_evaluation_quotas_and_whole_lookup_json_groups(self):
        c = course(); before = d.sha(c); selected = d.evaluation_problems(c)
        self.assertEqual(set(selected), {'test', 'train'})
        for split, quota in (('test', 32), ('train', 16)):
            self.assertEqual(Counter(p['family'] for p in selected[split]), dict.fromkeys(d.FAMILIES, quota))
            original_ids = {p['query_id'] for p in c[split]}
            self.assertTrue(all(p['query_id'] in original_ids for p in selected[split]))
            for family, width in (('lookup', 4), ('format', 2)):
                self.assertTrue(all(len(v) == width for v in groups([p for p in selected[split] if p['family'] == family]).values()))
        for family in d.FAMILIES: d.classify(first(family), 'en', 'wrong synthetic response')
        self.assertEqual(selected, d.evaluation_problems(c)); self.assertEqual(d.sha(c), before)
        selected['train'][0]['state'].clear(); self.assertEqual(d.sha(c), before)

    def test_all_public_data_operations_are_asset_free_and_do_not_write(self):
        course()
        with ExitStack() as stack:
            forbidden = []
            for owner, name in ((builtins, 'open'), (io, 'open'), (os, 'open')):
                forbidden.append(stack.enter_context(patch.object(owner, name, side_effect=AssertionError('asset/file IO forbidden'))))
            c = d.build_course(); self.assertTrue(d.validate_course(c)); selected = d.evaluation_problems(c)
            for p in selected['train'][:8]:
                for language in d.LANGUAGES:
                    row = d.render(p, language, **d.schedule_view(p, 'varied_balanced', 0))
                    self.assertTrue(d.classify(p, language, row['messages'][1]['content']))
            for mocked in forbidden: mocked.assert_not_called()


if __name__ == '__main__':
    unittest.main()
