"""작은 합성 구간과 메모리 토크나이저만 사용하며 실물 원천·모델을 읽지 않는다."""
from pathlib import Path
import copy
import sys
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import p106b_night_diversity_data as diversity
from scripts import p106b_night_qa_data as data
from tinylm.chat.canonical import normalize, validate
from tinylm.chat.serialize import serialize


class FixtureTokenizer:
    specials = {'<|im_start|>': 1, '<|im_end|>': 2, '<pad>': 3}

    def token_to_id(self, text):
        return self.specials.get(text)

    def encode(self, text):
        ids, offsets, index = [], [], 0
        while index < len(text):
            special = next((s for s in self.specials if text.startswith(s, index)), None)
            size = len(special) if special else 1
            ids.append(self.specials[special] if special else ord(text[index]) + 10)
            offsets.append((index, index + size))
            index += size
        return SimpleNamespace(ids=ids, offsets=offsets)


def title_for(language, split):
    return next(language + '_' + split + '_' + str(i) for i in range(10000)
                if data.article_split(language, language + '_' + split + '_' + str(i)) == split)


def make_pair(language, split, index, tok):
    title = title_for(language, split)
    answer = 'value' + str(index)
    context = 'Answer=' + answer + '; unique context ' + language + split + str(index)
    question = 'Which value ' + language + split + str(index) + '?'
    source_sha = data.sha(['fixture', language])
    answers = [dict(text=answer, answer_start=7)]
    root = data.sha([data.VERSION, language, source_sha, title, context, question, answers])
    pair = dict(root=root, language=language, split=split,
        article_id=data.sha([language, data.normalized(title)]), article_title=title,
        context_id=data.sha([language, data.normalized(context)]), qa_id=language + split + str(index),
        question=question, context=context, answers=answers, aliases=[answer],
        source_path='fixture/' + language + '_train.json', source_sha256=source_sha)
    views = {}
    encoding = {}
    for view in ((0, 1) if split == 'train' else (0, 1, 2)):
        row = data.render_view(pair, view)
        ids, labels, text = data.encode_view(row, tok)
        prompt = serialize(dict(messages=row['messages'][:1]), 'chatml', add_generation_prompt=True)
        targets = [v for v in labels[1:] if v != -100]
        views[str(view)] = row
        encoding[str(view)] = dict(x_tokens=len(ids) - 1, prompt_tokens=len(tok.encode(prompt).ids),
            assistant_targets=len(targets), eot_supervised=True, target_ids_sha256=data.sha(targets))
    return dict(pair, views=views, encoding=encoding)


def fixtures():
    tok = FixtureTokenizer()
    expanded = {split: [] for split in ('train', 'dev', 'test')}
    for split in expanded:
        for language in ('ko', 'en'):
            expanded[split].extend(make_pair(language, split, index, tok)
                                  for index in ([0, 1, 12, 13, 14, 15, 16, 17] if split == 'train' else [0]))
    baseline = dict(train=expanded['train'][:2] + expanded['train'][8:10],
                    dev=expanded['dev'], test=expanded['test'])
    return expanded, copy.deepcopy(baseline), tok


def split(expanded, baseline):
    return diversity.split_quarters(expanded, baseline, per_language=2,
                                     eval_per_language=1, enforce_inventory=False)


class DiversityTests(unittest.TestCase):
    def test_exact_quarter0_full_rows_order_and_four_unique_quarters(self):
        expanded, baseline, tok = fixtures()
        old_expanded, old_baseline = copy.deepcopy(expanded), copy.deepcopy(baseline)
        quarters, proof = split(expanded, baseline)
        self.assertEqual([len(q) for q in quarters], [4] * 4)
        self.assertEqual(quarters[0], baseline['train'])
        self.assertEqual(len({p['root'] for q in quarters for p in q}), 16)
        self.assertEqual(proof['natural_epoch'], 1)
        self.assertTrue(proof['same_natural_ce_rows'])
        self.assertTrue(proof['quarter0_complete_originals_equal'])
        self.assertTrue(proof['dev_test_complete_originals_equal'])
        self.assertEqual(expanded, old_expanded)
        self.assertEqual(baseline, old_baseline)
        quarters[0][0]['question'] = 'caller mutation'
        self.assertEqual(expanded, old_expanded)
        self.assertFalse(proof['inventory_enforced'])

    def test_exposures_recomputed_not_assumed_equal_in_tokens(self):
        expanded, baseline, tok = fixtures()
        quarters, proof = split(expanded, baseline)
        expected_x = sum(p['encoding'][v]['x_tokens'] for p in expanded['train'] for v in ('0', '1'))
        expected_targets = sum(p['encoding'][v]['assistant_targets'] for p in expanded['train'] for v in ('0', '1'))
        self.assertEqual(proof['candidate_natural_exposure'], dict(rows=32, x_tokens=expected_x,
                                                                 assistant_targets=expected_targets))
        self.assertEqual(sum(q['exposure']['x_tokens'] for q in proof['quarters']), expected_x)
        old_x = 4 * sum(p['encoding'][v]['x_tokens'] for p in baseline['train'] for v in ('0', '1'))
        self.assertEqual(proof['natural_input_ratio'], expected_x / old_x)
        self.assertGreater(proof['natural_input_ratio'], 1.)
        self.assertGreater(proof['natural_target_ratio'], 1.)
        self.assertIsNone(proof['planned_updates'])
        self.assertIsNone(proof['planned_native_targets'])

    def test_production640_updates_and_native_quarter_boundaries(self):
        schedule = diversity._logical_counts(4096)
        self.assertEqual(schedule['natural_ce_rows_per_quarter'], 16384)
        self.assertEqual(schedule['sft_rows_per_quarter'], 20480)
        self.assertEqual(schedule['updates_per_quarter'], 160)
        self.assertEqual(schedule['total_updates'], 640)
        self.assertEqual(schedule['total_sft_rows'], 81920)
        self.assertEqual(schedule['native_start_updates'], [0, 160, 320, 480])
        self.assertEqual(schedule['total_updates'] * 8192, 5242880)

    def test_article_overlap_inside_train_quarters_is_disclosed_not_rejected(self):
        expanded, baseline, tok = fixtures()
        quarters, proof = split(expanded, baseline)
        self.assertEqual(proof['cross_quarter_overlap']['0_1']['article_id'], 2)
        self.assertEqual(proof['cross_quarter_overlap']['0_1']['context_id'], 0)

    def test_actual_existing_records_path_reused_and_inputs_unchanged(self):
        expanded, baseline, tok = fixtures()
        quarters, proof = split(expanded, baseline)
        replay = [validate(normalize(dict(messages=[dict(role='user', content='fixture replay?'),
            dict(role='assistant', content='yes')], meta=dict(kind='fixture_replay'))))]
        old = copy.deepcopy((quarters, replay))
        for index in range(4):
            natural, controls = diversity.quarter_records(quarters, index, replay, tok)
            self.assertEqual(len(natural), 4)
            self.assertEqual(len(controls), 1)
            self.assertEqual(sum(rec.x_tokens for pair in natural for rec in pair), proof['quarters'][index]['exposure']['x_tokens'])
            self.assertEqual(sum(rec.targets for pair in natural for rec in pair), proof['quarters'][index]['exposure']['assistant_targets'])
        self.assertEqual((quarters, replay), old)

    def test_baseline_reorder_and_complete_pair_metadata_changes_rejected(self):
        expanded, baseline, tok = fixtures()
        baseline['train'][0], baseline['train'][1] = baseline['train'][1], baseline['train'][0]
        with self.assertRaisesRegex(ValueError, 'quarter0'):
            split(expanded, baseline)
        expanded, baseline, tok = fixtures()
        baseline['train'][0]['extra_frozen_metadata'] = 'changed'
        with self.assertRaisesRegex(ValueError, 'quarter0'):
            split(expanded, baseline)

    def test_dev_test_full_original_or_order_change_rejected(self):
        for name in ('dev', 'test'):
            expanded, baseline, tok = fixtures()
            baseline[name].reverse()
            with self.assertRaisesRegex(ValueError, 'DEV/TEST'):
                split(expanded, baseline)

    def test_duplicate_qa_source_root_or_question_rejected(self):
        expanded, baseline, tok = fixtures()
        expanded['train'][2] = copy.deepcopy(expanded['train'][1])
        with self.assertRaises(ValueError):
            split(expanded, baseline)
        expanded, baseline, tok = fixtures()
        expanded['train'][2]['qa_id'] = expanded['train'][1]['qa_id']
        for view in ('0', '1'):
            expanded['train'][2]['views'][view] = data.render_view(expanded['train'][2], int(view))
        with self.assertRaisesRegex(ValueError, '원천 식별자'):
            split(expanded, baseline)

    def test_source_content_ids_wrapper3_and_budget_pollution_rejected(self):
        for change in ('root', 'article_id', 'context_id', 'source_sha256'):
            expanded, baseline, tok = fixtures()
            expanded['train'][4][change] = 'tampered'
            with self.assertRaises(ValueError, msg=change):
                split(expanded, baseline)
        for change in ('wrapper3', 'targets', 'budget'):
            expanded, baseline, tok = fixtures()
            pair = expanded['train'][4]
            if change == 'wrapper3':
                pair['views']['3'] = copy.deepcopy(pair['views']['0'])
            elif change == 'targets':
                pair['encoding']['1']['assistant_targets'] += 1
            else:
                pair['encoding']['0']['prompt_tokens'] = 1000
            with self.assertRaises(ValueError, msg=change):
                split(expanded, baseline)

    def test_production_inventory_cannot_be_silently_replaced_by_fixture_counts(self):
        expanded, baseline, tok = fixtures()
        with self.assertRaises(ValueError):
            diversity.split_quarters(expanded, baseline)
        with self.assertRaises(ValueError):
            diversity.split_quarters(expanded, baseline, per_language=2,
                                       eval_per_language=1, enforce_inventory=True)

    def test_records_reject_target_digest_change_and_bad_quarter(self):
        expanded, baseline, tok = fixtures()
        quarters, proof = split(expanded, baseline)
        quarters[1][0]['encoding']['0']['target_ids_sha256'] = 'F' * 64
        with self.assertRaisesRegex(ValueError, '해시'):
            diversity.quarter_records(quarters, 1, [], tok)
        for index in (-1, 4, True):
            with self.assertRaises(ValueError):
                diversity.quarter_records(quarters, index, [], tok)

    def test_canonical_stream_digest_matches_original_data_sha(self):
        value = {'한국어': ['🙂', dict(x=2, question='Age?')], 'plain': [1, 2, 3]}
        self.assertEqual(diversity._sha(value), data.sha(value))


if __name__ == '__main__':
    unittest.main()
