"""Small CPU fixtures for original-direction, split, wrapper and target gates."""
from pathlib import Path
import copy
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import p106b_night_qa_data as data


class CharTokenizer:
    """Byte-offset-like character fixture with atomic ChatML boundary tokens."""
    specials = {'<|im_start|>': 1, '<|im_end|>': 2}

    def token_to_id(self, text):
        return self.specials.get(text)

    def encode(self, text):
        ids, offsets, index = [], [], 0
        while index < len(text):
            special = next((s for s in self.specials if text.startswith(s, index)), None)
            length = len(special) if special else 1
            ids.append(self.specials[special] if special else ord(text[index]) + 10)
            offsets.append((index, index + length))
            index += length
        return SimpleNamespace(ids=ids, offsets=offsets)


def fixture_documents():
    documents = {}
    for language in ('ko', 'en'):
        articles = []
        # Enough deterministic article hashes for all 90/5/5 lanes. Different
        # short contexts have no structural word24/char64 overlap by design.
        for i in range(400):
            title = language + '_article_' + str(i)
            answer = str(i)
            context = ('번호 ' if language == 'ko' else 'Identifier ') + answer + '.'
            question = ('번호는 무엇인가요 ' if language == 'ko' else 'Which identifier ') + str(i) + '?'
            qa = dict(id=language + str(i), question=question,
                      answers=[dict(text=answer, answer_start=context.index(answer))])
            articles.append(dict(title=title, paragraphs=[dict(context=context, qas=[qa])]))
        documents[language] = {
            'train': dict(path=language + '/train.json', sha256='A' * 64,
                          document=dict(data=articles)),
            'dev': dict(path=language + '/dev.json', sha256='B' * 64,
                        document=dict(data=[])),
        }
    return documents


class NaturalQATests(unittest.TestCase):
    def setUp(self):
        self.tok = CharTokenizer()

    def collect(self, documents=None, **kwargs):
        return data.collect_documents(documents or fixture_documents(), self.tok,
            train_limit=12, eval_limit=4, min_eval_contexts=4,
            common_bpb_count=0, **kwargs)

    def test_original_questions_answers_and_paired_targets(self):
        rows, report = self.collect()
        self.assertTrue(report['paired_targets_identical'])
        for split, pairs in rows.items():
            self.assertEqual(len(pairs), 24 if split == 'train' else 8)
            for pair in pairs:
                target_ids = []
                for view, row in pair['views'].items():
                    self.assertIn(pair['question'], data.text(row['messages'][0]))
                    self.assertIn(pair['context'], data.text(row['messages'][0]))
                    self.assertEqual(data.text(row['messages'][1]), pair['answers'][0]['text'])
                    ids, labels, text = data.encode_view(row, self.tok)
                    target = [x for x in labels[1:] if x != -100]
                    self.assertEqual(target[-1], self.tok.token_to_id('<|im_end|>'))
                    target_ids.append(target)
                    self.assertLessEqual(pair['encoding'][view]['prompt_tokens'] + 128, 1024)
                self.assertTrue(all(v == target_ids[0] for v in target_ids))

    def test_article_context_and_normalized_question_separation(self):
        rows, _ = self.collect()
        for a, b in (('train', 'dev'), ('train', 'test'), ('dev', 'test')):
            for key in ('root', 'article_id', 'context_id'):
                self.assertFalse({p[key] for p in rows[a]} & {p[key] for p in rows[b]})
        self.assertNotIn('2', rows['train'][0]['views'])
        self.assertIn('2', rows['test'][0]['views'])
        with self.assertRaises(ValueError):
            data.render_view(rows['train'][0], 2)

    def test_reordering_source_articles_does_not_change_selection(self):
        original = fixture_documents()
        rows, report = self.collect(original)
        changed = copy.deepcopy(original)
        for language in changed:
            changed[language]['train']['document']['data'].reverse()
        other, report2 = self.collect(changed)
        self.assertEqual(report['selected_roots_sha256'], report2['selected_roots_sha256'])

    def test_official_dev_exact_context_and_question_are_excluded(self):
        documents = fixture_documents()
        for language in documents:
            article = documents[language]['train']['document']['data'][0]
            copied = copy.deepcopy(article)
            copied['title'] = 'different official dev title'
            documents[language]['dev']['document']['data'].append(copied)
        rows, report = self.collect(documents)
        for language in documents:
            self.assertEqual(report['languages'][language]['rejections']['official_dev_context'], 1)
        self.assertTrue(all(p['qa_id'] not in ('ko0', 'en0') for r in rows.values() for p in r))

    def test_common_bpb_context_excluded_without_redefining_old_metric(self):
        documents = fixture_documents()
        common = min(p['context'] for a in documents['en']['train']['document']['data']
                     for p in a['paragraphs'])
        rows, report = data.collect_documents(documents, self.tok, train_limit=12,
            eval_limit=4, min_eval_contexts=4, common_bpb_count=1)
        self.assertEqual(report['languages']['en']['common_bpb_unique_contexts'], 1)
        self.assertTrue(all(p['context'] != common for r in rows.values() for p in r if p['language'] == 'en'))

    def test_common_partial_overlap_rejected_and_unrelated_context_kept(self):
        documents = fixture_documents()
        original = documents['en']['train']['document']['data']
        shared = ' '.join('commonword' + str(i) for i in range(30))
        def article(title, context):
            return dict(title=title, paragraphs=[dict(context=context, qas=[
                dict(id=title, question='Which marker belongs to ' + title + '?',
                     answers=[dict(text='marker', answer_start=context.index('marker'))])])])
        original.extend([article('common base', '0000 marker ' + shared),
                         article('common partial', 'A different marker ' + shared + ' appendix')])
        rows, report = data.collect_documents(documents, self.tok, train_limit=12,
            eval_limit=4, min_eval_contexts=4, common_bpb_count=1)
        english = report['languages']['en']
        self.assertEqual(english['common_bpb_near_contexts'], 1)
        self.assertEqual(english['rejections']['common_near_context'], 1)
        selected = [p for r in rows.values() for p in r if p['language'] == 'en']
        self.assertTrue(selected)
        self.assertTrue(all(p['article_title'] not in ('common base', 'common partial') for p in selected))
        self.assertTrue(all(p['context'].startswith('Identifier ') for p in selected))

    def test_regular_refuses_repo_parent_symlink_without_reading_file(self):
        fixture = data.ROOT / 'data_cache' / 'fixture.json'
        with patch.object(Path, 'is_file', return_value=True), patch.object(
                Path, 'is_symlink', lambda path: path == data.ROOT / 'data_cache'):
            self.assertFalse(data.regular(fixture))
            with self.assertRaises(ValueError):
                data.digest(fixture)
            self.assertTrue(data.regular(Path('/tmp/external-fixture.json')))

    def test_official_dev_normalized_question_excluded(self):
        documents = fixture_documents()
        for language in documents:
            original = documents[language]['train']['document']['data'][0]['paragraphs'][0]['qas'][0]
            reserve = dict(title='reserved article', paragraphs=[dict(context='unrelated', qas=[
                dict(id='dev-question', question='  ' + original['question'].upper() + '  ', answers=[])])])
            documents[language]['dev']['document']['data'].append(reserve)
        rows, report = self.collect(documents)
        for language in documents:
            self.assertEqual(report['languages'][language]['rejections']['official_dev_question'], 1)

    def test_missing_eot_supervision_is_rejected(self):
        rows, _ = self.collect()
        original = data.encode_view
        def corrupted(row, tokenizer):
            ids, labels, text = original(row, tokenizer)
            labels = list(labels)
            index = max(i for i, value in enumerate(labels) if value != -100)
            labels[index] = -100
            return ids, labels, text
        try:
            data.encode_view = corrupted
            result, reason = data._encoded_pair(rows['train'][0], self.tok)
        finally:
            data.encode_view = original
        self.assertIsNone(result)
        self.assertEqual(reason, 'complete_answer_eot_mask')

    def test_explicit_span_failure_and_unanswerable_are_not_admitted(self):
        documents = fixture_documents()
        for language in documents:
            qas = documents[language]['train']['document']['data'][0]['paragraphs'][0]['qas']
            qas[0]['answers'][0]['answer_start'] += 1
            extra = copy.deepcopy(qas[0])
            extra.update(id='noanswer', question='Unanswerable ' + language, answers=[], is_impossible=True)
            qas.append(extra)
        _, report = self.collect(documents)
        for language in documents:
            rejected = report['languages'][language]['rejections']
            self.assertEqual(rejected['answer_span_mismatch'], 1)
            self.assertEqual(rejected['unanswerable'], 1)

    def test_entire_oversized_source_rejected_without_cropping(self):
        documents = fixture_documents()
        for language in documents:
            for article in documents[language]['train']['document']['data']:
                paragraph = article['paragraphs'][0]
                paragraph['context'] += ' z' * 600
        with self.assertRaisesRegex(ValueError, 'complete pairs'):
            self.collect(documents)

    def test_official_dev_near_overlap_units(self):
        self.assertTrue(data.overlap_keys(' '.join('word' + str(i) for i in range(30)), 'en'))
        self.assertTrue(data.overlap_keys('가' * 80, 'ko'))
        self.assertEqual(data.overlap_keys('short', 'en'), set())

    def test_paired_target_difference_is_rejected(self):
        rows, _ = self.collect()
        pair = rows['train'][0]
        original = data.encode_view
        def corrupted(row, tokenizer):
            ids, labels, text = original(row, tokenizer)
            if row['meta']['wrapper_view'] == 1:
                labels = list(labels)
                index = next(i for i, y in enumerate(labels) if y != -100)
                labels[index] += 1
            return ids, labels, text
        try:
            data.encode_view = corrupted
            result, reason = data._encoded_pair(pair, self.tok)
        finally:
            data.encode_view = original
        self.assertIsNone(result)
        self.assertEqual(reason, 'paired_assistant_target_ids_differ')


if __name__ == '__main__':
    unittest.main()
