"""Small synthetic-only broad-course contracts; no source files/model/GPU."""
from __future__ import annotations

from collections import Counter
import copy
import hashlib
from pathlib import Path
import re
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import p106b_broad_course as course
from scripts import p106b_night_qa_data as natural
from scripts import p106b_relation_fields as fields
from tinylm.chat.canonical import normalize


class Words:
    """Only an in-memory offset tokenizer, with the declared atomic EOT4."""
    def token_to_id(self, text):
        return {'<pad>': 0, '<eos>': 2, '<|im_start|>': 3, '<|im_end|>': 4}.get(text)

    def encode(self, text):
        pieces = list(re.finditer(r'<\|im_start\|>|<\|im_end\|>|[^\s<]+|<', text))
        ids = [self.token_to_id(p.group()) if self.token_to_id(p.group()) is not None
               else 10 + int(hashlib.sha256(p.group().encode()).hexdigest()[:8], 16) % 30000
               for p in pieces]
        return SimpleNamespace(ids=ids, offsets=[p.span() for p in pieces])


def public(index, language='en', *, source='fixture_public', question=None, answer=None):
    return normalize(dict(messages=[
        dict(role='user', content=question or f'Explain original fixture topic P{index}.'),
        dict(role='assistant', content=answer or f'Original explanation for P{index}.')],
        meta=dict(language=language, source=source, source_id=str(index),
                  source_revision='fixture-revision', source_license='FIXTURE_ONLY', original_split='train')))


def pair(index, tok, *, split='train', context=None):
    lang = 'ko' if index % 2 else 'en'
    context = context or f'Unique natural source N{index} contains value{index}.'
    answer = f'value{index}'
    if answer not in context:
        context += ' ' + answer
    answers = [dict(text=answer, answer_start=context.index(answer))]
    source_sha = course.sha(['source', lang])
    title = f'Natural article N{index}'
    question = f'Which value is described by N{index}?'
    raw = dict(language=lang, split=split, article_title=title,
        article_id=course.sha([lang, natural.normalized(title)]),
        context_id=course.sha([lang, natural.normalized(context)]), qa_id=f'qa{index}',
        context=context, question=question, source_path=f'fixture/{lang}/train.json',
        source_sha256=source_sha, answers=answers, aliases=[answer])
    raw['root'] = course.sha([natural.VERSION, lang, source_sha, title, context, question, answers])
    encoded, error = natural._encoded_pair(raw, tok)
    if error:
        raise AssertionError(error)
    return encoded


def replay(index):
    row = public('replay' + str(index), 'ko' if index % 2 else 'en',
                 source='fixture_code', question=f'Given code record R{index}, return its value.', answer=str(index))
    row['meta'].update(kind='arithmetic', source_split='train',
                       semantic_root_id=course.sha(['replay', index]))
    return row


class Fixtures(unittest.TestCase):
    def setUp(self):
        self.tok = Words()
        self.pairs = [pair(i, self.tok) for i in range(4)]
        self.replay = [replay(i) for i in range(4)]
        self.public = [public(i, 'ko' if i == 0 else 'en') for i in range(8)]
        self.val = [public('reserved')]
        self.heldout = [pair(101, self.tok, split='test')]
        self.geometry = course._Geometry(4, 4, 4, 4, 2, 2)

    def build(self, **changes):
        args = dict(natural_pairs=self.pairs, replay_rows=self.replay,
                    public_train=self.public, tok=self.tok, public_val=self.val,
                    heldout_rows=self.heldout, geometry=self.geometry)
        args.update(changes)
        return course._build_course(**args)

    def inspect(self, values=None, **changes):
        args = dict(public_train=self.public if values is None else values, tok=self.tok,
                    public_val=self.val, heldout_rows=self.heldout, monitor_rows=(),
                    training_rows=(), selection_key=course.SELECTION_KEY, goal=4)
        args.update(changes)
        return course._select_general(**args)

    def test_production_geometry_is22528_rows176_groups352_updates(self):
        g = course._Geometry()
        self.assertEqual(2 * g.natural_pairs + g.replay_rows + g.general_rows, 22528)
        self.assertEqual((2 * g.natural_pairs + g.replay_rows + g.general_rows) // g.group_rows, 176)
        self.assertEqual((g.group_rows // g.micro_rows, g.passes), (16, 2))
        with self.assertRaises(course.SourceUnavailable) as error:
            course.build_course(self.pairs, self.replay, self.public, self.tok,
                                public_val=self.val, heldout_rows=self.heldout)
        self.assertEqual(error.exception.report['reason'], 'fixed_source_counts_differ')

    def test_groups_are_identical_and_each_pass_visits_every_row_once(self):
        result = self.build()
        self.assertEqual(result.schedules['staged'], [[2, 0, 1, 3], [2, 0, 1, 3]])
        for arm in course.ARMS:
            for epoch in range(2):
                order = result.schedules[arm][epoch]
                self.assertEqual(sorted(order), list(range(4)))
                seen = [i for group in order for i in result.groups[group]]
                self.assertEqual(sorted(seen), list(range(16)))
                for slot, group in enumerate(order):
                    micros = course.materialize_group(result, arm, epoch, slot)
                    self.assertEqual([len(m) for m in micros], [2, 2])
                    self.assertEqual([id(r) for micro in micros for r in micro],
                                     [id(result.records[i]) for i in result.groups[group]])

    def test_mixed_is_deterministic_and_source_inputs_unchanged(self):
        before = course.sha([self.pairs, self.replay, self.public, self.val, self.heldout])
        a, b = self.build(), self.build()
        self.assertEqual(a.report, b.report)
        self.assertEqual(a.schedules, b.schedules)
        self.assertEqual(before, course.sha([self.pairs, self.replay, self.public, self.val, self.heldout]))

    def test_general_selection_includes_all_available_ko_then_en(self):
        selected, report, _ = self.inspect()
        self.assertEqual(report['status'], 'ADMISSIBLE')
        self.assertEqual(report['selected_language_rows'], dict(ko=1, en=3))
        self.assertEqual(selected[0][1]['meta']['language'], 'ko')
        for index, row, _ in selected:
            self.assertEqual(row, self.public[index])

    def test_general_content_selection_is_stable_under_input_reordering(self):
        first, _, _ = self.inspect()
        second, _, _ = self.inspect(list(reversed(self.public)))
        self.assertEqual([course.sha(v[1]) for v in first], [course.sha(v[1]) for v in second])

    def test_inspection_returns_shortage_instead_of_shrinking_or_repeating(self):
        report = course.inspect_general(self.public, self.tok, public_val=self.val, heldout_rows=self.heldout)
        self.assertEqual((report['status'], report['requested_general_rows'], report['selected_rows']),
                         ('SOURCE_UNAVAILABLE', 2048, 8))
        self.assertEqual(report['repeated_fill_rows'], 0)
        with self.assertRaises(course.SourceUnavailable) as error:
            self.build(public_train=self.public[:2])
        self.assertEqual(error.exception.report['eligible_unique_rows'], 2)

    def test_general_same_source_concept_is_selected_once(self):
        duplicate = public(0, 'en', question='Different wording for the same source concept.')
        _, report, _ = self.inspect([*self.public, duplicate])
        self.assertEqual(report['eligible_unique_rows'], 8)
        self.assertEqual(report['rejected']['same_concept_or_exact_conversation'], 1)

    def test_exact_messages_and_first_user_duplicates_are_not_new_concepts(self):
        duplicate = public('different_source_identity')
        duplicate['messages'] = copy.deepcopy(self.public[1]['messages'])
        same_prompt = public('other_prompt_identity', question='Explain original fixture topic P2.', answer='Another answer.')
        _, report, _ = self.inspect([*self.public, duplicate, same_prompt])
        self.assertEqual(report['eligible_unique_rows'], 8)
        self.assertEqual(report['rejected']['same_concept_or_exact_conversation'], 2)

    def test_explicit_concept_alias_deduplication(self):
        rows = copy.deepcopy(self.public)
        rows[0]['meta']['parent_concept_id'] = 'SHARED_ROOT'
        rows[1]['meta']['semantic_root_id'] = 'SHARED_ROOT'
        _, report, _ = self.inspect(rows)
        self.assertEqual(report['eligible_unique_rows'], 7)

    def test_alias_chains_are_one_concept_independent_of_input_order(self):
        a = public('chainA', 'ko', question='First wording of a linked concept.')
        b = public('chainA', question='Second wording of the linked concept.')
        c = public('chainC', question='Second wording of the linked concept.', answer='Another annotation.')
        for rows in ([*self.public, a, b, c], [c, b, a, *reversed(self.public)]):
            _, report, _ = self.inspect(rows)
            self.assertEqual(report['eligible_unique_rows'], 9)
            self.assertEqual(report['rejected']['same_concept_or_exact_conversation'], 2)

    def test_source_ids_are_namespaced(self):
        a = public(0, source='different_dataset', question='Another source asks another question.')
        _, report, _ = self.inspect([*self.public, a])
        self.assertEqual(report['eligible_unique_rows'], 9)

    def test_reserved_exact_messages_and_first_user_are_excluded(self):
        reserved = copy.deepcopy(self.public[0])
        reserved['meta']['source_id'] = 'val-different-id'
        _, report, _ = self.inspect(public_val=[reserved])
        self.assertEqual(report['selected_language_rows'].get('ko', 0), 0)
        self.assertEqual(report['rejected']['reserved_evaluation_collision'], 1)

    def test_reserved_source_id_excluded_even_if_text_differs(self):
        reserved = public(0, question='Validation has different wording but same source ID.')
        _, report, _ = self.inspect(public_val=[reserved])
        self.assertEqual(report['rejected']['reserved_evaluation_collision'], 1)

    def test_original24word_overlap_is_a_technical_exclusion(self):
        common = ' '.join('originalword' + str(i) for i in range(24))
        rows = [public('train', question='First ' + common + ' training question.'), *self.public]
        reserved = public('val', question='Other ' + common + ' validation question.')
        _, report, _ = self.inspect(rows, public_val=[reserved])
        self.assertEqual(report['rejected']['reserved_evaluation_collision'], 1)
        collision = report['exclusions'][0]['collision']
        self.assertIn('word24', collision)
        self.assertNotIn('first_user', collision)

    def test_normal_short_answers_and_unique_output_not_rejected_by_similarity(self):
        rows = [public(i, question=f'Original independent calculation {i}?', answer='2') for i in range(8)]
        reserved = public('val', question='Unrelated validation calculation?', answer='2')
        _, report, _ = self.inspect(rows, public_val=[reserved])
        self.assertEqual(report['eligible_unique_rows'], 8)
        self.assertEqual(report['language_or_knowledge_quality_string_filters'], 0)

    def test_monitor_collisions_are_excluded_with_origin_proof(self):
        _, report, _ = self.inspect(monitor_rows=[self.public[0]])
        self.assertEqual(report['rejected']['reserved_evaluation_collision'], 1)
        self.assertEqual(report['protected_reference_rows']['monitor'], 1)
        origins = report['exclusions'][0]['collision']['messages']['origins']
        self.assertTrue(origins[0].startswith('monitor:'))

    def test_prompt_only_monitor_cases_need_no_injected_gold_answer(self):
        case = dict(messages=copy.deepcopy(self.public[0]['messages'][:1]),
                    lane='general', language='ko', group_id='original_monitor_group')
        _, report, _ = self.inspect(monitor_rows=[case])
        self.assertEqual(report['rejected']['reserved_evaluation_collision'], 1)
        collision = report['exclusions'][0]['collision']
        self.assertIn('first_user', collision)
        self.assertNotIn('messages', collision)

    def test_existing_training_identity_cannot_be_generalized_as_new_source(self):
        _, report, _ = self.inspect(training_rows=[self.public[0]])
        self.assertEqual(report['eligible_unique_rows'], 7)
        self.assertEqual(report['rejected']['same_concept_or_exact_conversation'], 1)

    def test_invalid_source_metadata_split_language_and_length_reported(self):
        missing = public('missing'); del missing['meta']['source_revision']
        wrong_split = public('split'); wrong_split['meta']['original_split'] = 'val'
        wrong_language = public('language'); wrong_language['meta']['language'] = 'unknown'
        long_row = public('long', question=' '.join('token' + str(i) for i in range(1200)))
        _, report, _ = self.inspect([*self.public, missing, wrong_split, wrong_language, long_row])
        self.assertEqual(report['rejected']['missing_original_source_metadata'], 1)
        self.assertEqual(report['rejected']['not_original_train_split'], 1)
        self.assertEqual(report['rejected']['unregistered_language'], 1)
        self.assertEqual(report['rejected']['length_or_encoding_contract'], 1)

    def test_natural_source_target_in_context_is_not_rejected_as_leak(self):
        result = self.build()
        self.assertEqual(result.report['natural_unique_roots'], 4)
        self.assertEqual(sum(r['lane'] == 'grounded' for r in result.rows), 8)

    def test_two_natural_views_preserve_target_ids_and_turns(self):
        result = self.build()
        for start in range(0, 8, 2):
            a, b = result.records[start:start + 2]
            self.assertEqual([y for y in a.y if y != -100], [y for y in b.y if y != -100])
        self.assertTrue(result.report['same_two_views_per_pair'])

    def test_natural_changed_encoding_or_gold_is_rejected(self):
        changed = copy.deepcopy(self.pairs)
        changed[0]['encoding']['0']['assistant_targets'] += 1
        with self.assertRaisesRegex(ValueError, 'consumer'):
            self.build(natural_pairs=changed)
        changed = copy.deepcopy(self.pairs)
        changed[0]['views']['1']['messages'][1]['content'][0]['text'] = 'changed gold'
        with self.assertRaisesRegex(ValueError, 'wrapper changed'):
            self.build(natural_pairs=changed)

    def test_natural_heldout_root_and_context_collisions_stop_fixed_geometry(self):
        with self.assertRaises(course.SourceUnavailable) as error:
            self.build(heldout_rows=[self.pairs[0]])
        self.assertEqual(error.exception.report['reason'], 'fixed_training_reserved_evaluation_collision')
        self.assertTrue(any(c['lane'] == 'grounded' for c in error.exception.report['conflicts']))

    def test_natural_train_cannot_include_reserved_wrapper2(self):
        changed = copy.deepcopy(self.pairs)
        changed[0]['views']['2'] = changed[0]['views']['0']
        with self.assertRaisesRegex(ValueError, 'two original'):
            self.build(natural_pairs=changed)

    def test_synthetic_shared_template_is_not_original24word_overlap(self):
        common = ' '.join('templateword' + str(i) for i in range(30))
        rows = copy.deepcopy(self.replay)
        rows[0]['messages'][0]['content'][0]['text'] = common + ' specific training value.'
        reserved = replay(200)
        reserved['messages'][0]['content'][0]['text'] = common + ' specific validation value.'
        result = self.build(replay_rows=rows, heldout_rows=[reserved])
        self.assertEqual(result.report['per_pass']['totals']['rows'], 16)

    def test_replay_reserved_exact_collision_stops_before_student(self):
        with self.assertRaises(course.SourceUnavailable) as error:
            self.build(heldout_rows=[self.replay[0]])
        self.assertEqual(error.exception.report['status'], 'SOURCE_UNAVAILABLE')
        self.assertTrue(any(c['lane'] == 'replay' for c in error.exception.report['conflicts']))

    def test_actual_factory_c2_keeps_old_wrong_answer_masked_with_positive_owner(self):
        graph = fields.graph(0, 'train')
        c2 = fields.make(graph, 'en', fields.MODES.index('correct'))
        rows = [c2, *self.replay[1:]]
        result = self.build(replay_rows=rows)
        index = next(i for i, m in enumerate(result.rows) if m['lane'] == 'replay' and m['source_index'] == 0)
        encoded = result.records[index]
        self.assertTrue(any(y == -100 and owner == 1 for y, owner in zip(encoded.y, encoded.segments)))
        self.assertFalse(any(y != -100 and owner == 1 for y, owner in zip(encoded.y, encoded.segments)))
        self.assertEqual(result.rows[index]['supervised_turns'], 1)
        self.assertEqual(result.rows[index]['assistant_turns'], 2)

    def test_public_multiple_turns_and_source_identifiers_preserved(self):
        rows = copy.deepcopy(self.public)
        rows[0]['messages'] += [dict(role='user', content=[dict(type='text', text='Continue the original explanation.')]),
                               dict(role='assistant', content=[dict(type='text', text='A second original answer.')])]
        result = self.build(public_train=rows)
        meta = next(m for m in result.rows if m['lane'] == 'general' and m['source_index'] == 0)
        self.assertEqual((meta['assistant_turns'], meta['supervised_turns']), (2, 2))
        self.assertEqual(meta['source']['source_id'], '0')

    def test_counts_separate_real_input_targets_padding_and_repeated_exposure(self):
        result = self.build()
        counts = result.report['per_pass']['totals']
        self.assertEqual(counts['x_tokens'], sum(r.x_tokens for r in result.records))
        self.assertEqual(counts['assistant_targets'], sum(r.targets for r in result.records))
        self.assertEqual(counts['assistant_targets'], counts['content_targets'] + counts['eot_targets'])
        self.assertLess(counts['x_tokens'], result.report['padded_sft_slots_per_pass'])
        self.assertEqual(result.report['two_pass_totals']['assistant_targets'], 2 * counts['assistant_targets'])
        self.assertFalse(result.report['total75m_complete'])

    def test_public_report_contains_no_source_messages_or_token_arrays(self):
        result = self.build()
        report = course.public_report(result)
        def keys(value):
            if isinstance(value, dict):
                for key, child in value.items():
                    yield key; yield from keys(child)
            elif isinstance(value, list):
                for child in value: yield from keys(child)
        self.assertFalse({'messages', 'x', 'y', 'segments'} & set(keys(report)))
        report['geometry']['passes'] = 0
        self.assertEqual(result.report['geometry']['passes'], 2)

    def test_mutated_group_membership_or_encoded_targets_are_rejected(self):
        result = self.build()
        result.groups[0][1] = result.groups[0][0]
        with self.assertRaisesRegex(ValueError, 'membership'):
            course.materialize_group(result, 'staged', 0, 1)
        result = self.build()
        result.records[0].y[-1] = 5
        with self.assertRaisesRegex(ValueError, 'membership'):
            course.materialize_group(result, 'staged', 0, 1)

    def test_invalid_order_selector_and_native_absolute_indices(self):
        result = self.build()
        for args in [('wrong', 0, 0), ('mixed', True, 0), ('mixed', 2, 0), ('mixed', 0, -1)]:
            with self.subTest(args=args), self.assertRaises(ValueError):
                course.materialize_group(result, *args)
        self.assertEqual(course.native_indices(0), tuple(range(8)))
        self.assertEqual(course.native_indices(351), tuple(range(2808, 2816)))
        for value in (-1, 352, True, 0.):
            with self.subTest(value=value), self.assertRaises(ValueError):
                course.native_indices(value)

    def test_changed_schedule_or_row_metadata_is_rejected(self):
        result = self.build()
        result.schedules['mixed'][0][0] = result.schedules['mixed'][0][1]
        with self.assertRaisesRegex(ValueError, 'order changed'):
            course.materialize_group(result, 'mixed', 0, 0)
        result = self.build()
        result.rows[0]['assistant_targets'] += 1
        with self.assertRaisesRegex(ValueError, 'membership'):
            course.materialize_group(result, 'staged', 0, 1)

    def test_build_is_pure_no_assets_models_or_cuda(self):
        with patch('builtins.open', side_effect=AssertionError('file I/O forbidden')), \
             patch.object(Path, 'open', side_effect=AssertionError('file I/O forbidden')), \
             patch('torch.load', side_effect=AssertionError('checkpoint forbidden')), \
             patch('torch.cuda.init', side_effect=AssertionError('CUDA forbidden')):
            result = self.build()
        self.assertFalse(result.report['model_loaded'])


if __name__ == '__main__':
    unittest.main()
