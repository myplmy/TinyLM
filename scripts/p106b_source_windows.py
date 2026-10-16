"""Frozen-history source-window interventions, not a semantic quality filter."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from collections import Counter, defaultdict
import copy
import hashlib
import json
import math
from scripts import p106b_original_qa3_evaluation as original
from tinylm.chat.serialize import serialize

VERSION = 'P106B_FIXED_ACTUAL_HISTORY_SOURCE_WINDOWS_V1'
MODES = ('FULL', 'QUERY', 'RANDOM', 'GOLD_LITERAL', 'REMOVE_REFERENCE')
WIDTH, STRIDE, SEED = 128, 64, 1337
MARKERS = {'ko': ('\n자료:\n', '\n질문:\n'), 'en': ('\nReference:\n', '\nQuestion:\n')}


def sha(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
        separators=(',', ':')).encode()).hexdigest().upper()


def decompose(row, event):
    """Use the signed producer reference length; never guess from answer text."""
    m = row['meta']; language = m['language']; turn = event['turn']
    if language not in MARKERS or turn not in (1, 2, 3):
        raise ValueError('registered language/turn required')
    if event['history'] != 'ACTUAL_MODEL' or event['root'] != m['semantic_root_id'] or event['language'] != language:
        raise ValueError('exact primary actual-history source required')
    messages = event['messages']
    if len(messages) != 2 * turn - 1 or [x['role'] for x in messages] != (['user', 'assistant'] * 3)[:len(messages)]:
        raise ValueError('unchanged alternating actual prefix required')
    if len(row['messages']) != 6:
        raise ValueError('original three-QA role row required')
    for i in range(0, len(messages), 2):
        if original.text(messages[i]) != original.text(row['messages'][i]):
            raise ValueError('original user questions changed')
    if event['gold'] != original.text(row['messages'][2 * turn - 1]):
        raise ValueError('source target changed')
    first = original.text(messages[0]); begin_marker, question_marker = MARKERS[language]
    a, b = m['original_reference_range']
    if a != 0 or type(b) is not int or b <= 0:
        raise ValueError('explicit original producer reference length required')
    start = first.find(begin_marker)
    if start < 0:
        raise ValueError('outer reference marker absent')
    start += len(begin_marker); end = start + b
    if not first[end:].startswith(question_marker):
        raise ValueError('signed reference length does not reach question marker')
    prefix, reference, suffix = first[:start], first[start:end], first[end:]
    question = suffix[len(question_marker):]
    if not question or prefix + reference + suffix != first:
        raise ValueError('lossless reference reconstruction required')
    questions = [question] + [original.text(x) for x in messages[2::2]]
    return dict(prefix=prefix, reference=reference, suffix=suffix, questions=questions)


def windows(reference, tok, width=WIDTH, stride=STRIDE):
    if not reference or type(width) is not int or not 1 <= stride <= width:
        raise ValueError('nonempty source and bounded token windows required')
    offsets = [(a, b) for a, b in tok.encode(reference).offsets if b > a]
    if not offsets:
        raise ValueError('source has no ordinary token offsets')
    result = []; seen = set()
    for i in range(0, len(offsets), stride):
        part = offsets[i:i + width]; a = min(x[0] for x in part); b = max(x[1] for x in part)
        if not 0 <= a < b <= len(reference):
            raise ValueError('token offsets outside preserved source')
        if (a, b) in seen:
            continue
        seen.add((a, b))
        result.append(dict(char_range=[a, b], original_token_range=[i, min(i + width, len(offsets))],
            text=reference[a:b], actual_window_tokens=len(tok.encode(reference[a:b]).ids)))
    return result


def grams(text):
    text = text.casefold()
    return Counter(text[i:i + 3] for i in range(max(0, len(text) - 2)))


def query_scores(chunks, questions):
    """Character3-gram log-TF, smoothed local IDF, cosine; no gold argument."""
    if not chunks or not questions:
        raise ValueError('nonempty chunks and existing user questions required')
    query = Counter()
    for question in questions[:-1] + [questions[-1], questions[-1]]:
        query.update(grams(question))
    docs = [grams(w['text']) for w in chunks]; df = Counter()
    for doc in docs:
        df.update(doc.keys())
    n = len(docs)
    def vector(counts):
        return {g: (1 + math.log(v)) * (1 + math.log((1 + n) / (1 + df.get(g, 0))))
            for g, v in counts.items()}
    q = vector(query); qn = math.sqrt(sum(v * v for v in q.values())); out = []
    for doc in docs:
        d = vector(doc); dn = math.sqrt(sum(v * v for v in d.values()))
        value = sum(v * d.get(g, 0.) for g, v in q.items()) / (qn * dn) if qn and dn else 0.
        if not math.isfinite(value) or value < -1e-12 or value > 1 + 1e-12:
            raise ValueError('finite cosine required')
        out.append(min(1., max(0., value)))
    return out


def selection(reference, questions, root, turn, gold, tok):
    chunks = windows(reference, tok); scores = query_scores(chunks, questions)
    best = min(range(len(chunks)), key=lambda i: (-scores[i], chunks[i]['char_range'][0]))
    random_index = int(sha([VERSION, SEED, root, turn])[:16], 16) % len(chunks)
    eligible = [i for i, w in enumerate(chunks) if gold and gold in w['text']]
    literal = min(eligible, key=lambda i: (-scores[i], chunks[i]['char_range'][0])) if eligible else None
    def chosen(i):
        return dict(chunks[i], cosine=scores[i], window_index=i, eligible=True)
    return dict(FULL=dict(text=reference, char_range=[0, len(reference)], eligible=True),
        QUERY=chosen(best), RANDOM=chosen(random_index),
        GOLD_LITERAL=chosen(literal) if literal is not None else dict(eligible=False, reason='NO_LITERAL_CONTAINING_WINDOW'),
        REMOVE_REFERENCE=dict(text='', char_range=[0, 0], eligible=True)), len(chunks)


def make_case(row, event, endpoint, tok):
    frame = decompose(row, event); source = frame['reference']
    selected, n = selection(source, frame['questions'], event['root'], event['turn'], event['gold'], tok)
    variants = []
    for mode in MODES:
        choice = selected[mode]
        if not choice['eligible']:
            variants.append(dict(mode=mode, eligible=False, reason=choice['reason']))
            continue
        a, b = choice['char_range']
        if source[a:b] != choice['text']:
            raise ValueError('exact original substring required, no rephrasing')
        messages = copy.deepcopy(event['messages'])
        if len(messages[0]['content']) != 1 or messages[0]['content'][0]['type'] != 'text':
            raise ValueError('exact original text-block input required')
        messages[0]['content'][0]['text'] = frame['prefix'] + choice['text'] + frame['suffix']
        if messages[1:] != event['messages'][1:]:
            raise ValueError('fixed previous actual responses or current question changed')
        prompt = serialize(dict(messages=messages), 'chatml', add_generation_prompt=True)
        tokens = len(tok.encode(prompt).ids)
        if not 0 < tokens < 1024:
            raise ValueError('complete diagnostic prompt needs generation room in1024')
        if mode == 'FULL':
            if messages != event['messages'] or tokens != event['generation']['prompt_tokens']:
                raise ValueError('FULL does not reconstruct the actual original consumer input')
        variants.append(dict(mode=mode, eligible=True, messages=messages, prompt_tokens=tokens,
            selected_char_range=choice['char_range'], cosine=choice.get('cosine'),
            original_window_index=choice.get('window_index'), literal_in_window=event['gold'] in choice['text']))
    return dict(schema=VERSION, endpoint=endpoint, root=event['root'], language=event['language'], turn=event['turn'],
        case_id=sha([event['root'], event['turn']]), gold=event['gold'], baseline_answer=event['answer'],
        full_messages_sha256=sha(event['messages']), original_reference_sha256=sha(source),
        full_prompt_tokens=event['generation']['prompt_tokens'], source_window_count=n, variants=variants,
        history_policy='FIXED_PREVIOUS_ACTUAL_FROM_PRIMARY; new answers are not propagated',
        diagnostic_only=True, train_ready=False, semantic_truth='ORIGINAL_PUBLIC_UNVERIFIED')


def score(answer, gold, generation):
    return original.score(dict(answer=answer, gold=gold, generation=generation))


def recount(events):
    seen = set(); out = defaultdict(Counter)
    for event in events:
        key = (event['endpoint'], event['root'], event['turn'], event['mode'])
        if key in seen:
            raise ValueError('duplicate endpoint/root/turn/mode event')
        seen.add(key)
        if event['status'] == 'NOT_ELIGIBLE':
            out[event['endpoint'] + '/' + event['mode'] + '/all']['not_eligible'] += 1
            continue
        if event['status'] != 'GENERATED' or score(event['answer'], event['gold'], event['generation']) != event['scores']:
            raise ValueError('raw generation/score mismatch')
        for lane in ('all', 'language=' + event['language'], 'turn=' + str(event['turn'])):
            out[event['endpoint'] + '/' + event['mode'] + '/' + lane].update(event['scores'])
    return {k: dict(v) for k, v in sorted(out.items())}


def paired(full, variant, draws=4000, seed=1337):
    """Matched eligible cases; sum differences / sum cases, resampling roots."""
    import numpy as np
    def index(rows):
        result = {(r['root'], r['turn']): r for r in rows if r['status'] == 'GENERATED'}
        if len(result) != sum(r['status'] == 'GENERATED' for r in rows):
            raise ValueError('duplicate within-mode case')
        return result
    a, b = index(full), index(variant)
    if not b or not set(b) <= set(a):
        raise ValueError('nonempty eligible variant subset of FULL required')
    totals = defaultdict(lambda: [0., 0., 0])
    for key, y in b.items():
        x = a[key]
        if x['gold'] != y['gold'] or x['language'] != y['language'] or x['endpoint'] != y['endpoint']:
            raise ValueError('same endpoint/target for every paired case required')
        v = totals[key[0]]
        v[0] += y['scores']['literal'] - x['scores']['literal']
        v[1] += y['scores']['lexical_f1'] - x['scores']['lexical_f1']; v[2] += 1
    values = np.asarray([v for _, v in sorted(totals.items())], dtype=float)
    ids = np.random.default_rng(seed).integers(len(values), size=(draws, len(values))); picked = values[ids]
    metrics = {}
    for j, name in enumerate(('literal', 'lexical_f1')):
        samples = picked[:, :, j].sum(1) / picked[:, :, 2].sum(1)
        metrics[name] = dict(variant_minus_full=float(values[:, j].sum() / values[:, 2].sum()),
            ci95=np.quantile(samples, [.025, .975]).tolist())
    return dict(cases=len(b),roots=len(values),full_correct_on_same_cases=sum(a[k]['scores']['literal'] for k in b),
        variant_correct=sum(v['scores']['literal'] for v in b.values()),metrics=metrics,draws=draws,seed=seed,
        scope='posthoc fixed-history source-window intervention; no multiplicity adjustment, truth or seed-generalization claim')
