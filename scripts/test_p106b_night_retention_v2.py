"""CPU in-memory regressions for shared semantic roots and full raw replay."""
from pathlib import Path
import copy
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import p106b_night_retention_v2 as retained
from tinylm.chat.canonical import normalize, validate
from tinylm.chat.serialize import serialize


def row(language, scenario, root='shared-semantic-root', turns=2):
    messages = []
    for turn in range(1, turns + 1):
        messages.extend([dict(role='user', content=f'{language} question {scenario} turn{turn}'),
                         dict(role='assistant', content=f'{language} gold {scenario} turn{turn}')])
    return validate(normalize(dict(messages=messages, meta=dict(
        language=language, semantic_root_id=root, neutral_root='shared-neutral-root',
        kind='fixture_code', condition=0, family='fixture', first_response_intent='ANSWER',
        query_sufficient=True, view=0, question_style=2))))


def emit(prefix):
    answer = '' if 'empty' in retained.old.c.data.text(prefix[-1]) else '0'
    prompt = serialize(dict(messages=prefix), 'chatml', add_generation_prompt=True)
    return answer, dict(finish_reason='STOP_SEQUENCE',
                        actual_prompt_sha256=retained._sha(prompt),
                        raw_answer_sha256=retained._sha(answer))


def originals():
    # Both the cross-language shared root and two same-language scenarios are
    # genuine separate frozen rows, not duplicated generation events.
    return [row('ko', 'A'), row('en', 'A'), row('ko', 'B')]


def legacy(rows=None):
    return [event for original in (originals() if rows is None else rows)
            for event in retained.old.dialogue(original, emit)]


def collected(rows=None, lane='code'):
    return [event for index, original in enumerate(originals() if rows is None else rows)
            for event in retained.collect(original, emit, lane=lane, row_index=index)]


class RetentionIdentityTests(unittest.TestCase):
    def test_actual_shared_root_failure_is_fixed_without_changing_old_summarizer(self):
        raw = legacy()
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            retained.old.summarize_dialogue(raw)
        events = retained.augment_legacy(raw, originals(), 'code')
        summary = retained.summarize(events)
        self.assertEqual(summary['ACTUAL_MODEL/all']['n'], 6)
        self.assertEqual(summary['GOLD_REFERENCE/all']['n'], 3)
        self.assertEqual(summary['ACTUAL_MODEL/ko']['n'], 4)
        self.assertEqual(summary['ACTUAL_MODEL/en']['n'], 2)
        self.assertEqual(len({event['case_id'] for event in events}), 3)

    def test_collect_matches_lossless_legacy_augmentation_and_preserves_inputs(self):
        sources = originals()
        raw = legacy(sources)
        sources_before, raw_before = copy.deepcopy(sources), copy.deepcopy(raw)
        augmented = retained.augment_legacy(raw, sources, 'code')
        direct = collected(sources)
        self.assertEqual(augmented, direct)
        self.assertEqual(sources, sources_before)
        self.assertEqual(raw, raw_before)
        self.assertFalse(any(field in event for field in retained.IDENTITY_FIELDS for event in raw))
        self.assertEqual(retained.verify(augmented, sources, 'code'), retained.summarize(direct))

    def test_identity_is_full_original_row_plus_lane_and_frozen_index(self):
        source = originals()[0]
        events = retained.collect(source, emit, lane='code', row_index=4)
        for event in events:
            self.assertEqual(event['case_source_sha256'], retained._sha(source))
            self.assertEqual(event['case_id'], retained._sha(['code', 4, source]))
            self.assertEqual(event['frozen_row_index'], 4)
        other_index = retained.collect(source, emit, lane='code', row_index=5)
        other_lane = retained.collect(source, emit, lane='role', row_index=4)
        self.assertNotEqual(events[0]['case_id'], other_index[0]['case_id'])
        self.assertNotEqual(events[0]['case_id'], other_lane[0]['case_id'])

    def test_same_original_at_two_frozen_indices_is_two_occurrences(self):
        source = originals()[0]
        events = collected([source, copy.deepcopy(source)])
        self.assertEqual(retained.verify(events, [source, source], 'code')['ACTUAL_MODEL/all']['n'], 4)

    def test_exact_duplicate_and_missing_events_rejected(self):
        events = collected()
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            retained.summarize(events + [copy.deepcopy(events[0])])
        for changed in (events[:-1], events + [copy.deepcopy(events[0])]):
            with self.assertRaises(ValueError):
                retained.verify(changed, originals(), 'code')
        with self.assertRaises(ValueError):
            retained.augment_legacy(legacy()[:-1], originals(), 'code')

    def test_identity_mutations_and_wrong_lane_rejected(self):
        for field, value in (('case_id', 'F' * 64), ('case_source_sha256', 'E' * 64),
                             ('frozen_row_index', 22), ('lane', 'wrong')):
            events = collected()
            events[0][field] = value
            with self.assertRaises(ValueError, msg=field):
                retained.verify(events, originals(), 'code')
        with self.assertRaises(ValueError):
            retained.verify(collected(), originals(), 'role')

    def test_question_gold_and_original_metadata_mutations_rejected(self):
        for augmented in (False, True):
            base = collected() if augmented else legacy()
            for field, value in (('gold', 'changed gold'), ('root', 'changed root'),
                                 ('condition', 1), ('kind', 'changed kind')):
                events = copy.deepcopy(base)
                events[0][field] = value
                with self.assertRaises(ValueError, msg=field):
                    if augmented:
                        retained.verify(events, originals(), 'code')
                    else:
                        retained.augment_legacy(events, originals(), 'code')
            events = copy.deepcopy(base)
            events[0]['messages'][0]['content'][0]['text'] = 'changed question'
            with self.assertRaises(ValueError):
                if augmented:
                    retained.verify(events, originals(), 'code')
                else:
                    retained.augment_legacy(events, originals(), 'code')

    def test_actual_and_gold_history_are_rebuilt_separately(self):
        for position in (1, 2):
            events = collected()
            # One actual-history row contains model text strings; the gold
            # history row contains the frozen canonical gold assistant blocks.
            events[position]['messages'][1]['content'] = 'forged earlier answer'
            with self.assertRaises(ValueError):
                retained.verify(events, originals(), 'code')
        events = collected()
        events[1], events[2] = events[2], events[1]
        with self.assertRaises(ValueError):
            retained.verify(events, originals(), 'code')

    def test_preserved_row_order_and_full_originals_are_required(self):
        events = collected()
        events[:3], events[3:6] = events[3:6], events[:3]
        with self.assertRaises(ValueError):
            retained.verify(events, originals(), 'code')
        changed = originals()
        changed[0]['messages'][1]['content'][0]['text'] = 'new source gold'
        with self.assertRaises(ValueError):
            retained.verify(collected(), changed, 'code')
        with self.assertRaises(ValueError):
            retained.augment_legacy(legacy(), originals()[1:], 'code')

    def test_generation_hash_and_literal_recount_detect_tampering(self):
        for field, value in (('literal', 1), ('answer', 'forged answer')):
            events = collected()
            events[0][field] = value
            with self.assertRaises(ValueError):
                retained.summarize(events)
        events = collected()
        events[0]['generation']['actual_prompt_sha256'] = 'F' * 64
        with self.assertRaises(ValueError):
            retained.verify(events, originals(), 'code')

    def test_zero_scores_empty_answers_and_zero_condition_are_retained(self):
        sources = [row('ko', 'empty', turns=3), row('en', 'A', turns=1)]
        events = collected(sources)
        result = retained.verify(events, sources, 'code')
        self.assertEqual(result['ACTUAL_MODEL/all']['n'], 4)
        self.assertEqual(result['ACTUAL_MODEL/all']['literal'], 0)
        self.assertEqual(result['ACTUAL_MODEL/all']['empty'], 3)
        self.assertEqual(result['GOLD_REFERENCE/all']['empty'], 2)
        self.assertEqual(result['ACTUAL_MODEL/condition0']['n'], 4)
        self.assertEqual(result['ACTUAL_MODEL/ko/turn2']['n'], 1)

    def test_summary_partial_history_and_empty_input_refused(self):
        events = collected()
        del events[2]
        with self.assertRaises(ValueError):
            retained.summarize(events)
        for function in (lambda: retained.summarize([]),
                         lambda: retained.verify([], [], 'code'),
                         lambda: retained.augment_legacy([], [], 'code')):
            with self.assertRaises(ValueError):
                function()


if __name__ == '__main__':
    unittest.main()
