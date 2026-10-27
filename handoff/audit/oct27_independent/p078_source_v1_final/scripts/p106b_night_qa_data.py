"""Read-only, explicit-span natural QA for the authorized overnight course.

This module never writes a corpus, loads a model, or starts a GPU operation.
Source annotation/span agreement is not a semantic truth certificate.
"""
from __future__ import annotations

from collections import Counter, defaultdict, deque
import copy
import hashlib
import json
from pathlib import Path
import sys
import unicodedata

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from tinylm.chat.canonical import normalize, validate
from tinylm.chat.serialize import serialize
from tinylm.data.sft import encode_conversation

TAG = 'p106b_night_grounded_v1_s1337'
CORPUS = ROOT / 'HF/sft_ready' / TAG / 'corpus'
EVIDENCE = ROOT / 'test_result/evidence' / TAG
TOKENIZER = ROOT / 'data_cache/tok-ko-en-32768-chat32.json'
TOK_SHA = '9716F40E4C504D6AF37DDE76CCA578E30B45E9CA86C8B6BB79B2FA095D3AC88E'
VERSION = 'P106B_NIGHT_EXPLICIT_SPAN_QA_V1'
SEED = 20261016
CONTEXT = 1024
MAX_NEW = 128
SOURCES = {
    'ko': {
        'train': ('datasets/KorQuad/KorQuAD_2.1/KorQuAD_v1.0_train.json',
                  '40D5115879A701751781DF721D901ABFA736D8DB5F89000F2619433F39BF2DD2'),
        'dev': ('datasets/KorQuad/KorQuAD_2.1/KorQuAD_v1.0_dev.json',
                '25FFEB51E6C51EC02C071B60A10188E10005C144110F0D876B26079D80A35BDF'),
    },
    'en': {
        'train': ('datasets/squad/train-v2.0.json',
                  '68DCFBB971BD3E96D5B46C7177B16C1A4E7D4BDEF19FB204502738552DEDE002'),
        'dev': ('datasets/squad/dev-v2.0.json',
                '80A5225E94905956A6446D296CA1093975C4D3B3260F1D6C8F68BC2AB77182D8'),
    },
}


def regular(path):
    path = Path(path)
    if not path.is_file() or path.is_symlink():
        return False
    absolute = path.absolute()
    try:
        absolute.relative_to(ROOT)
    except ValueError:
        # In-memory/unit-fixture callers may use a regular external file.
        return True
    if '..' in absolute.parts:
        return False
    for parent in absolute.parents:
        if parent.is_symlink():
            return False
        if parent == ROOT:
            break
    return True


def digest(path):
    path = Path(path)
    if not regular(path):
        raise ValueError('regular, non-symlink source required: ' + str(path))
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest().upper()


def sha(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(',', ':')).encode()).hexdigest().upper()


def text(message):
    value = message['content']
    if isinstance(value, str):
        return value
    if any(b.get('type') != 'text' for b in value):
        raise ValueError('text-only canonical message required')
    return ''.join(b['text'] for b in value)


def normalized(value):
    return ' '.join(unicodedata.normalize('NFKC', value).casefold().split())


def overlap_keys(context, language):
    """Exact overlap units; not a content-quality or truth filter."""
    value = normalized(context)
    if language == 'en':
        words = value.split()
        return {' '.join(words[i:i + 24]) for i in range(max(0, len(words) - 23))}
    if language != 'ko':
        raise ValueError('only declared ko/en sources')
    value = ''.join(value.split())
    return {value[i:i + 64] for i in range(max(0, len(value) - 63))}


def article_split(language, title, seed=SEED):
    bucket = int(sha([VERSION, seed, language, normalized(title)])[:16], 16) % 100
    return 'train' if bucket < 90 else 'dev' if bucket < 95 else 'test'


def _paragraphs(document):
    if not isinstance(document, dict) or not isinstance(document.get('data'), list):
        raise ValueError('explicit SQuAD-shaped data list required')
    for article in document['data']:
        title = article['title']
        if not isinstance(title, str) or not title.strip():
            raise ValueError('original nonempty article title required')
        for paragraph in article['paragraphs']:
            context = paragraph['context']
            if not isinstance(context, str) or not context.strip():
                raise ValueError('original nonempty context required')
            if not isinstance(paragraph['qas'], list):
                raise ValueError('explicit qas list required')
            yield title, context, paragraph['qas']


def _user(context, question, language, view):
    if language == 'ko':
        if view == 0:
            prefix, middle = '자료를 읽고 질문의 답만 짧게 쓰세요.\n자료:\n', '\n질문:\n'
        elif view == 1:
            prefix, middle = '다음 지문에 근거해 질문에 대한 답만 쓰세요.\n지문:\n', '\n질문:\n'
        elif view == 2:
            prefix = '아래 질문에 자료만 이용해 간결하게 답하세요.\n질문:\n'
            return prefix + question + '\n자료:\n' + context
        else:
            raise ValueError('registered wrapper 0,1,2 required')
    elif language == 'en':
        if view == 0:
            prefix, middle = 'Read the reference and give only the short answer.\nReference:\n', '\nQuestion:\n'
        elif view == 1:
            prefix, middle = 'Answer the question using only the passage below.\nPassage:\n', '\nQuestion:\n'
        elif view == 2:
            prefix = 'Give a concise answer to the question using only the reference.\nQuestion:\n'
            return prefix + question + '\nReference:\n' + context
        else:
            raise ValueError('registered wrapper 0,1,2 required')
    else:
        raise ValueError('declared language required')
    return prefix + context + middle + question


def encode_view(row, tokenizer):
    """Return the real canonical training encoder's (ids, labels, text)."""
    return encode_conversation(row, tokenizer, 'chatml')


def render_view(pair, view):
    if view not in (0, 1, 2) or (pair['split'] == 'train' and view == 2):
        raise ValueError('held-out wrapper2 is never a training row')
    meta = {k: copy.deepcopy(pair[k]) for k in
            ('root', 'language', 'split', 'article_id', 'article_title', 'context_id',
             'qa_id', 'source_path', 'source_sha256', 'answers', 'aliases')}
    meta.update(kind='night_natural_qa', source='explicit_public_context_qa',
                semantic_root_id=pair['root'], parent_concept_id=pair['root'],
                source_split=pair['split'], source_original_split='train',
                wrapper_view=view, course_version=VERSION,
                source_task_contract='EXPLICIT_CONTEXT_QUESTION_ANSWER_START',
                label_status='ORIGINAL_SPAN_ANNOTATION_CHAR_VERIFIED',
                semantic_truth='SOURCE_ANNOTATION_NOT_FULL_SEMANTIC_REVIEW',
                supervised_assistant_turns=[1], teacher_calls=0,
                question_original=pair['question'], context_original=pair['context'])
    return validate(normalize(dict(messages=[
        dict(role='user', content=_user(pair['context'], pair['question'], pair['language'], view)),
        dict(role='assistant', content=pair['answers'][0]['text'])], meta=meta)))


def _encoded_pair(pair, tokenizer):
    views, encodings, target_ids = {}, {}, None
    end = tokenizer.token_to_id('<|im_end|>')
    if end is None:
        raise ValueError('chat32 EOT token is required')
    for view in ((0, 1) if pair['split'] == 'train' else (0, 1, 2)):
        row = render_view(pair, view)
        ids, labels, serialized = encode_view(row, tokenizer)
        prompt = serialize(dict(messages=row['messages'][:1]), 'chatml', add_generation_prompt=True)
        supervised = [v for v in labels[1:] if v != -100]
        prompt_tokens = len(tokenizer.encode(prompt).ids)
        if len(ids) - 1 > CONTEXT or prompt_tokens + MAX_NEW > CONTEXT:
            return None, 'complete_context_or_generation_budget'
        if not supervised or len(supervised) > MAX_NEW or supervised[-1] != end:
            return None, 'complete_answer_eot_mask'
        # Exactly the assistant span is supervised; all prompt tokens precede it.
        first = next(i for i, value in enumerate(labels) if value != -100)
        if first != prompt_tokens or any(v != -100 for v in labels[:prompt_tokens]):
            raise ValueError('assistant-only target owner differs from complete prompt')
        if target_ids is not None and supervised != target_ids:
            return None, 'paired_assistant_target_ids_differ'
        target_ids = supervised
        if text(row['messages'][1]) != pair['answers'][0]['text']:
            raise ValueError('original gold bytes changed')
        views[str(view)] = row
        encodings[str(view)] = dict(x_tokens=len(ids) - 1, prompt_tokens=prompt_tokens,
                                    assistant_targets=len(supervised), eot_supervised=True,
                                    target_ids_sha256=sha(supervised))
    return dict(pair, views=views, encoding=encodings), None


def _balanced_candidates(candidates, seed):
    by_article = defaultdict(list)
    for pair in candidates:
        by_article[pair['article_id']].append(pair)
    active = deque()
    for article in sorted(by_article, key=lambda key: sha([seed, 'ARTICLE_ORDER', key])):
        values = sorted(by_article[article], key=lambda p: sha([seed, 'QA_ORDER', p['root']]))
        active.append(iter(values))
    while active:
        iterator = active.popleft()
        try:
            yield next(iterator)
            active.append(iterator)
        except StopIteration:
            pass


def collect_documents(documents, tokenizer, *, train_limit=4096, eval_limit=256,
                      min_eval_contexts=128, context_question_cap=2,
                      common_bpb_count=4000, seed=SEED):
    """Pure in-memory fixture/collector core; documents carry source descriptors.

    documents[language][split] = {'document': parsed original JSON,
        'path': original source path, 'sha256': pinned original file digest}.
    Only original TRAIN QAs become new train/dev/test; official DEV is excluded.
    """
    if (set(documents) != {'ko', 'en'} or train_limit < 1 or eval_limit < 1
            or context_question_cap < 1 or min_eval_contexts < 0
            or common_bpb_count < 0):
        raise ValueError('bounded bilingual collection configuration required')
    rows = {s: [] for s in ('train', 'dev', 'test')}
    report = dict(schema=VERSION, tag=TAG, seed=seed, tokenizer_sha256=None,
                  tokenizer_identity='CALLER_SUPPLIED_IN_MEMORY_CORE',
                  train_wrappers=[0, 1], heldout_wrapper=2, heldout_wrapper_train_rows=0,
                  context=CONTEXT, max_new=MAX_NEW, sources={}, languages={},
                  semantic_review='NOT_FULLY_REVIEWED', teacher_calls=0,
                  source_original_split='train', split_unit='original article',
                  split_hash_percent=dict(train=90, dev=5, test=5),
                  common_bpb_policy=f'sorted unique first{common_bpb_count} English TRAIN contexts excluded; old metric not redefined',
                  near_overlap=dict(en='NFKC casefold whitespace word24', ko='NFKC casefold nonspace char64'),
                  corpus_written=False, model_loaded=False, optimizer_updates=0)
    for language in ('ko', 'en'):
        if set(documents[language]) != {'train', 'dev'}:
            raise ValueError('exact original train/dev descriptors required')
        original = list(_paragraphs(documents[language]['train']['document']))
        reserved = list(_paragraphs(documents[language]['dev']['document']))
        report['sources'][language] = {s: {k: documents[language][s][k] for k in ('path', 'sha256')}
                                       for s in ('train', 'dev')}
        dev_titles = {normalized(t) for t, c, q in reserved}
        dev_contexts = {normalized(c) for t, c, q in reserved}
        dev_questions = {normalized(q['question']) for t, c, qs in reserved for q in qs}
        dev_grams = set()
        for context in dev_contexts:
            dev_grams.update(overlap_keys(context, language))
        common = set(sorted({c for t, c, q in original})[:common_bpb_count]) if language == 'en' else set()
        common_normalized = {normalized(c) for c in common}
        common_grams = set()
        for context in common_normalized:
            common_grams.update(overlap_keys(context, language))
        common_near_contexts = set()
        rejected = Counter()
        candidates = defaultdict(list)
        seen = set()
        for title, context, qas in original:
            context_grams = overlap_keys(context, language)
            common_near = (normalized(context) not in common_normalized
                           and bool(context_grams & common_grams))
            if common_near:
                common_near_contexts.add(sha([language, normalized(context)]))
            reason = ('official_dev_article' if normalized(title) in dev_titles else
                      'common_bpb_context' if normalized(context) in common_normalized else
                      'common_near_context' if common_near else
                      'official_dev_context' if normalized(context) in dev_contexts else
                      'official_dev_near_context' if context_grams & dev_grams else None)
            if reason:
                rejected[reason] += len(qas)
                continue
            split = article_split(language, title, seed)
            article_id = sha([language, normalized(title)])
            context_id = sha([language, normalized(context)])
            for qa in qas:
                question, answers = qa['question'], qa['answers']
                if not isinstance(question, str) or not question.strip():
                    rejected['empty_question'] += 1
                    continue
                if not answers or qa.get('is_impossible') is True:
                    rejected['unanswerable'] += 1
                    continue
                if normalized(question) in dev_questions:
                    rejected['official_dev_question'] += 1
                    continue
                if any(not isinstance(a.get('text'), str) or not a['text']
                       or type(a.get('answer_start')) is not int or a['answer_start'] < 0
                       or context[a['answer_start']:a['answer_start'] + len(a['text'])] != a['text']
                       for a in answers):
                    rejected['answer_span_mismatch'] += 1
                    continue
                key = (context_id, normalized(question))
                if key in seen:
                    rejected['duplicate_context_question'] += 1
                    continue
                seen.add(key)
                source = documents[language]['train']
                root = sha([VERSION, language, source['sha256'], title, context, question, answers])
                candidates[split].append(dict(root=root, language=language, split=split,
                    article_id=article_id, article_title=title, context_id=context_id,
                    qa_id=qa['id'], question=question, context=context,
                    answers=copy.deepcopy(answers), aliases=list(dict.fromkeys(a['text'] for a in answers)),
                    source_path=source['path'], source_sha256=source['sha256']))
        # Prefer sealed TEST, then DEV, when different articles share source text
        # or questions. The lower-priority split loses the colliding records.
        reserved_contexts, reserved_questions, reserved_grams = set(), set(), set()
        split_counts = {}
        for split in ('test', 'dev', 'train'):
            clean = []
            for pair in candidates[split]:
                if (pair['context_id'] in reserved_contexts
                        or normalized(pair['question']) in reserved_questions
                        or overlap_keys(pair['context'], language) & reserved_grams):
                    rejected['cross_split_context_question_or_near'] += 1
                else:
                    clean.append(pair)
            used_contexts, used_questions, selected = Counter(), set(), []
            limit = train_limit if split == 'train' else eval_limit
            for pair in _balanced_candidates(clean, seed):
                question_key = normalized(pair['question'])
                if used_contexts[pair['context_id']] >= context_question_cap or question_key in used_questions:
                    continue
                encoded, reason = _encoded_pair(pair, tokenizer)
                if reason:
                    rejected[reason] += 1
                    continue
                selected.append(encoded)
                used_contexts[pair['context_id']] += 1
                used_questions.add(question_key)
                if len(selected) == limit:
                    break
            if len(selected) != limit:
                raise ValueError(f'{language}/{split}: need {limit} complete pairs, found {len(selected)}')
            if split != 'train' and len(used_contexts) < min_eval_contexts:
                raise ValueError(f'{language}/{split}: fewer than {min_eval_contexts} original contexts')
            rows[split].extend(selected)
            # Reserve the whole clean split, including unselected QAs, so no
            # source article/context becomes training through quota subsampling.
            for pair in clean:
                reserved_contexts.add(pair['context_id'])
                reserved_questions.add(normalized(pair['question']))
            for context in {p['context'] for p in clean}:
                reserved_grams.update(overlap_keys(context, language))
            split_counts[split] = dict(pairs=len(selected), contexts=len(used_contexts),
                articles=len({p['article_id'] for p in selected}),
                unique_questions=len(used_questions), eligible_before_tokenizer=len(clean),
                x_tokens_by_view={str(v): sum(p['encoding'][str(v)]['x_tokens'] for p in selected)
                                  for v in ((0, 1) if split == 'train' else (0, 1, 2))},
                assistant_targets=sum(p['encoding']['0']['assistant_targets'] for p in selected),
                roots_sha256=sha(sorted(p['root'] for p in selected)))
        report['languages'][language] = dict(splits=split_counts, rejections=dict(rejected),
            original_train_articles=len({normalized(t) for t, c, q in original}),
            original_train_questions=sum(len(q) for t, c, q in original),
            common_bpb_unique_contexts=len(common), common_bpb_near_contexts=len(common_near_contexts),
            official_dev_contexts=len(dev_contexts),
            official_dev_exact_context_intersection=len({normalized(c) for t, c, q in original} & dev_contexts))
    for a, b in (('train', 'dev'), ('train', 'test'), ('dev', 'test')):
        for field in ('root', 'article_id', 'context_id'):
            if {p[field] for p in rows[a]} & {p[field] for p in rows[b]}:
                raise ValueError('selected split overlap: ' + field)
        if {(p['language'], normalized(p['question'])) for p in rows[a]} & {
                (p['language'], normalized(p['question'])) for p in rows[b]}:
            raise ValueError('selected normalized question overlap')
    report['selected_roots_sha256'] = sha({s: sorted(p['root'] for p in r) for s, r in rows.items()})
    report['paired_targets_identical'] = True
    report['source_span_agreement_is_semantic_truth'] = False
    return rows, report


def collect_natural(tokenizer):
    """Read pinned local sources and return pairs/metadata without writing."""
    if digest(TOKENIZER) != TOK_SHA:
        raise ValueError('pinned chat32 tokenizer file changed')
    if (not hasattr(tokenizer, 'to_str')
            or json.loads(tokenizer.to_str()) != json.loads(TOKENIZER.read_text(encoding='utf-8'))):
        raise ValueError('supplied tokenizer object differs from pinned chat32 file')
    documents = {}
    for language, splits in SOURCES.items():
        documents[language] = {}
        for split, (relative, expected) in splits.items():
            path = ROOT / relative
            if digest(path) != expected:
                raise ValueError('pinned original source changed: ' + relative)
            documents[language][split] = dict(path=relative, sha256=expected,
                document=json.loads(path.read_text(encoding='utf-8')))
    rows, report = collect_documents(documents, tokenizer)
    report.update(tokenizer_sha256=TOK_SHA, tokenizer_identity='PINNED_FILE_AND_ACTUAL_OBJECT_EQUAL')
    return rows, report
