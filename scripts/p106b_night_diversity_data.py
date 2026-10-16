"""고유 자연 질문 32,768개의 한 순회를 네 논리 구간으로 분할하고 검산한다.

호출자가 메모리에 제공한 수집·동결 원형만 사용한다. 원천·토크나이저·
코퍼스·체크포인트·산출물 파일을 열지 않는다. 기존 course.records는
원래 레코드 인코더로만 재사용한다.
"""
from __future__ import annotations

from collections import Counter
import copy
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import p106b_night_course as c
from scripts import p106b_night_qa_data as data

TAG = 'p106b_night_diversity_v1_s1337'
CORPUS = ROOT / 'HF/sft_ready' / TAG / 'corpus'
EVIDENCE = ROOT / 'test_result/evidence' / TAG
VERSION = 'P106B_NIGHT_UNIQUE_QA_QUARTERS_V1'
PARENT_SHA = '12E18658CDCD0AFEBE5A87073DC8977304C0D490A03A8471779D514FBB0D9950'
BASELINE_REPORT_SHA = 'E340BCE35E0B5FA6CC0EE2F08694E584A711231BC6443C5D599D55F95D5D122B'
OBSERVED_SELECTION_SHA = '44DFC5375364899CA4C1134729D1D34B1A92A06858D8433BAC3FDE0421B1063D'
OBSERVED_TRAIN = {
    'ko': dict(pairs=16384, contexts=8405, articles=1263,
               x_tokens_by_view={'0': 4737971, '1': 4754355}, assistant_targets_one_view=74153,
               roots_sha256='5B2181B34144E9F586546ECED7235420508A426176A1B14E0B2495F24E76A335'),
    'en': dict(pairs=16384, contexts=10502, articles=412,
               x_tokens_by_view={'0': 3570745, '1': 3587129}, assistant_targets_one_view=107154,
               roots_sha256='F2E017964B0235CBF5ED4D990E3FBF22675721FC4E212B32E6322DD4D0BB59E3'),
}
OBSERVED_EVAL_ROOTS = {
    'dev': 'CCD1731973251D131BF18DA1BD1F0FAEF673BD2B7ABE455F78B5CA752E2ADB76',
    'test': '5576834122522E58E0CEE11CF2454B5A6242040D226A6B1FF0909F6D648E9802',
}
REPLAY_PER_QUARTER = dict(rows=4096, x_tokens=777315, assistant_targets=37770)


def _sha(value):
    """큰 문자열을 만들지 않고 data.sha와 같은 정규 JSON 해시를 계산한다."""
    digest = hashlib.sha256()
    encoder = json.JSONEncoder(ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)
    for block in encoder.iterencode(value):
        digest.update(block.encode())
    return digest.hexdigest().upper()


def _nonempty(value, label):
    if not isinstance(value, str) or not value:
        raise ValueError('다양성 대조의 비어 있지 않은 필드 필요: ' + label)


def _pair(pair, split, enforce_source):
    if not isinstance(pair, dict) or pair.get('split') != split or pair.get('language') not in ('ko', 'en'):
        raise ValueError('원래 질문 묶음의 언어와 분할 명시 필요')
    for key in ('root', 'article_id', 'article_title', 'context_id', 'qa_id', 'source_path',
                'source_sha256', 'question', 'context'):
        _nonempty(pair.get(key), key)
    language = pair['language']
    if data.article_split(language, pair['article_title']) != split:
        raise ValueError('원래 기사 해시 분할이 달라짐')
    if pair['article_id'] != data.sha([language, data.normalized(pair['article_title'])]):
        raise ValueError('기사 식별자가 원래 제목과 다름')
    if pair['context_id'] != data.sha([language, data.normalized(pair['context'])]):
        raise ValueError('문맥 식별자가 원래 본문과 다름')
    if enforce_source and (pair['source_path'], pair['source_sha256']) != data.SOURCES[language]['train']:
        raise ValueError('고정된 원천 식별자가 다름')
    answers = pair.get('answers')
    if not isinstance(answers, list) or not answers:
        raise ValueError('원래 정답 주석 필요')
    for answer in answers:
        if (not isinstance(answer, dict) or not isinstance(answer.get('text'), str) or not answer['text']
                or type(answer.get('answer_start')) is not int or answer['answer_start'] < 0
                or pair['context'][answer['answer_start']:answer['answer_start'] + len(answer['text'])] != answer['text']):
            raise ValueError('원래 정답과 문자 위치의 일치가 깨짐')
    if pair.get('aliases') != list(dict.fromkeys(a['text'] for a in answers)):
        raise ValueError('원래 정답 별칭이 달라짐')
    expected_root = data.sha([data.VERSION, language, pair['source_sha256'], pair['article_title'],
                              pair['context'], pair['question'], answers])
    if pair['root'] != expected_root:
        raise ValueError('원래 원천·질문·정답의 root가 다름')
    views = (0, 1) if split == 'train' else (0, 1, 2)
    if (not isinstance(pair.get('views'), dict) or set(pair['views']) != {str(v) for v in views}
            or not isinstance(pair.get('encoding'), dict)
            or set(pair['encoding']) != {str(v) for v in views}):
        raise ValueError('원래 학습 wrapper0/1과 미학습 평가 wrapper2만 허용')
    target = None
    for view in views:
        if pair['views'][str(view)] != data.render_view(pair, view):
            raise ValueError('정규 뷰가 원래 렌더러와 다름')
        encoding = pair['encoding'][str(view)]
        if (not isinstance(encoding, dict)
                or any(type(encoding.get(k)) is not int for k in ('x_tokens', 'prompt_tokens', 'assistant_targets'))
                or not 1 <= encoding['x_tokens'] <= 1024 or encoding['prompt_tokens'] < 1
                or encoding['prompt_tokens'] + 128 > 1024
                or not 2 <= encoding['assistant_targets'] <= 128
                or encoding['prompt_tokens'] - 1 + encoding['assistant_targets'] > encoding['x_tokens']
                or encoding.get('eot_supervised') is not True
                or not isinstance(encoding.get('target_ids_sha256'), str)
                or len(encoding['target_ids_sha256']) != 64
                or any(ch not in '0123456789ABCDEF' for ch in encoding['target_ids_sha256'])):
            raise ValueError('완전한 1024/128 예산과 원래 지도 메타데이터 필요')
        signature = (encoding['assistant_targets'], encoding['target_ids_sha256'])
        if target is not None and signature != target:
            raise ValueError('두 wrapper의 지도 식별자 또는 개수가 다름')
        target = signature


def _summary(pairs):
    result = {}
    for language in ('ko', 'en'):
        values = [p for p in pairs if p['language'] == language]
        result[language] = dict(pairs=len(values), contexts=len({p['context_id'] for p in values}),
            articles=len({p['article_id'] for p in values}),
            unique_questions=len({data.normalized(p['question']) for p in values}),
            unique_sources=len({(p['source_path'], p['source_sha256'], p['qa_id']) for p in values}),
            roots_sha256=data.sha(sorted(p['root'] for p in values)),
            x_tokens_by_view={str(v): sum(p['encoding'][str(v)]['x_tokens'] for p in values) for v in (0, 1)},
            assistant_targets_one_view=sum(p['encoding']['0']['assistant_targets'] for p in values))
    return result


def _natural_exposure(pairs):
    return dict(rows=2 * len(pairs),
                x_tokens=sum(p['encoding'][str(v)]['x_tokens'] for p in pairs for v in (0, 1)),
                assistant_targets=sum(p['encoding'][str(v)]['assistant_targets'] for p in pairs for v in (0, 1)))


def _logical_counts(per_language):
    """실물은 160회씩 네 구간이며 작은 모의 입력의 불완전 배치는 None으로 표시한다."""
    natural_rows = 4 * per_language
    quarter_rows = natural_rows + REPLAY_PER_QUARTER['rows']
    updates = quarter_rows // 128 if quarter_rows % 128 == 0 else None
    return dict(natural_ce_rows_per_quarter=natural_rows, sft_rows_per_quarter=quarter_rows,
                updates_per_quarter=updates, total_sft_rows=4 * quarter_rows,
                total_updates=4 * updates if updates is not None else None,
                native_start_updates=[index * updates if updates is not None else None for index in range(4)])


def _dataset(rows, train_per_language, eval_per_language, enforce_source):
    if not isinstance(rows, dict) or any(s not in rows for s in ('train', 'dev', 'test')):
        raise ValueError('제공된 train/dev/test 원형 대응표 필요')
    sets = {}
    for split in ('train', 'dev', 'test'):
        values = rows[split]
        if not isinstance(values, list) or not values:
            raise ValueError('비어 있지 않은 원래 질문 묶음 목록 필요')
        for pair in values:
            _pair(pair, split, enforce_source)
        n = train_per_language if split == 'train' else eval_per_language
        if Counter(p['language'] for p in values) != dict(ko=n, en=n):
            raise ValueError('언어별·분할별 정확한 질문 묶음 수 필요')
        keys = dict(root={p['root'] for p in values},
                    article={(p['language'], p['article_id']) for p in values},
                    context={(p['language'], p['context_id']) for p in values},
                    question={(p['language'], data.normalized(p['question'])) for p in values},
                    source={(p['language'], p['source_path'], p['source_sha256'], p['qa_id']) for p in values})
        if any(len(keys[name]) != len(values) for name in ('root', 'question', 'source')):
            raise ValueError('원래 질문의 root·질문·원천 식별자가 중복됨')
        if max(Counter((p['language'], p['context_id']) for p in values).values()) > 2:
            raise ValueError('원래 문맥당 질문 두 개 상한을 초과함')
        sets[split] = keys
    for a, b in (('train', 'dev'), ('train', 'test'), ('dev', 'test')):
        for name in sets[a]:
            if sets[a][name] & sets[b][name]:
                raise ValueError('원래 train/dev/test 간 중복: ' + name)
    return sets


def split_quarters(expanded_rows, baseline_rows, *, per_language=4096,
                   eval_per_language=256, enforce_inventory=True):
    """입력을 바꾸지 않고 질문이 겹치지 않는 네 구간과 검산 메타데이터를 반환한다.

    각 구간은 원래 한국어 다음 영어 순서다. quarter0은 기존 TRAIN 목록의
    전체 사전 내용과 순서가 같아야 한다. 학습 구간끼리의 기사·문맥 중복은
    허용하되 공개하며, 기사 표본의 독립성으로 주장하지 않는다.
    """
    if (type(per_language) is not int or per_language < 1
            or type(eval_per_language) is not int or eval_per_language < 1
            or type(enforce_inventory) is not bool
            or (enforce_inventory and (per_language != 4096 or eval_per_language != 256))):
        raise ValueError('고정 실물 규모 또는 명시된 작은 모의 입력 규모 필요')
    expanded_sets = _dataset(expanded_rows, 4 * per_language, eval_per_language, enforce_inventory)
    _dataset(baseline_rows, per_language, eval_per_language, enforce_inventory)
    for split in ('dev', 'test'):
        if expanded_rows[split] != baseline_rows[split]:
            raise ValueError('DEV/TEST 전체 원형 또는 순서가 달라짐')
    by_language = {language: [p for p in expanded_rows['train'] if p['language'] == language]
                   for language in ('ko', 'en')}
    quarters = [sum((by_language[language][index * per_language:(index + 1) * per_language]
                     for language in ('ko', 'en')), []) for index in range(4)]
    if quarters[0] != baseline_rows['train']:
        raise ValueError('quarter0 전체 사전 내용 또는 순서가 기준 TRAIN과 다름')
    quarter_roots = [{p['root'] for p in values} for values in quarters]
    if (len(set.union(*quarter_roots)) != len(expanded_rows['train'])
            or any(quarter_roots[a] & quarter_roots[b] for a in range(4) for b in range(a + 1, 4))):
        raise ValueError('각 고유 질문은 네 구간 전체에서 정확히 한 번만 포함되어야 함')
    stats = _summary(expanded_rows['train'])
    selection_sha = data.sha({s: sorted(p['root'] for p in expanded_rows[s]) for s in ('train', 'dev', 'test')})
    eval_roots = {s: data.sha(sorted(p['root'] for p in expanded_rows[s])) for s in ('dev', 'test')}
    if enforce_inventory:
        for language, expected in OBSERVED_TRAIN.items():
            if any(stats[language][key] != value for key, value in expected.items()):
                raise ValueError('실측 32,768개 재고와 다름: ' + language)
        if selection_sha != OBSERVED_SELECTION_SHA or eval_roots != OBSERVED_EVAL_ROOTS:
            raise ValueError('실측 32,768개 선택 또는 원래 평가 root SHA가 다름')
    natural = _natural_exposure(expanded_rows['train'])
    baseline = {key: 4 * value for key, value in _natural_exposure(baseline_rows['train']).items()}
    schedule = _logical_counts(per_language)
    updates_per_quarter = schedule['updates_per_quarter']
    quarter_proof = []
    overlaps = {}
    for index, values in enumerate(quarters):
        quarter_proof.append(dict(index=index, train_pairs=len(values), summary=_summary(values),
            exposure=_natural_exposure(values), roots_sha256=data.sha(sorted(p['root'] for p in values)),
            ordered_roots_sha256=data.sha([p['root'] for p in values]),
            logical_quarter=index, schedule_seed=1337 + index,
            native_start_update=schedule['native_start_updates'][index],
            optimizer_updates=updates_per_quarter,
            record_encoder='변경하지 않은 p106b_night_course.records'))
    for a in range(4):
        for b in range(a + 1, 4):
            overlaps[str(a) + '_' + str(b)] = {
                key: len({(p['language'], p[key]) for p in quarters[a]}
                         & {(p['language'], p[key]) for p in quarters[b]})
                for key in ('article_id', 'context_id')}
    replay_four = {key: 4 * value for key, value in REPLAY_PER_QUARTER.items()}
    candidate_total = {key: natural[key] + replay_four[key] for key in natural}
    baseline_total = {key: baseline[key] + replay_four[key] for key in baseline}
    updates = candidate_total['rows'] // 128 if candidate_total['rows'] % 128 == 0 else None
    if updates != schedule['total_updates'] or candidate_total['rows'] != schedule['total_sft_rows']:
        raise ValueError('네 논리 구간의 노출 예산이 다름')
    proof = dict(schema=VERSION, tag=TAG, inventory_enforced=enforce_inventory,
        fixed_parent_sha256=PARENT_SHA, baseline_report_sha256=BASELINE_REPORT_SHA,
        natural_epoch=1, logical_quarters=4, per_quarter_language_pairs=per_language,
        train_summary=stats, quarters=quarter_proof, quarter0_complete_originals_equal=True,
        dev_test_complete_originals_equal=True, evaluation_roots_sha256=eval_roots,
        evaluation_full_rows_sha256={s: _sha(expanded_rows[s]) for s in ('dev', 'test')},
        selected_roots_sha256=selection_sha, cross_quarter_overlap=overlaps,
        source_row_split_disjoint=True, article_split_disjoint=True,
        common_source_files_across_splits_are_expected=True,
        candidate_natural_exposure=natural, baseline_repeated_natural_exposure=baseline,
        natural_input_ratio=natural['x_tokens'] / baseline['x_tokens'],
        natural_target_ratio=natural['assistant_targets'] / baseline['assistant_targets'],
        same_natural_ce_rows=natural['rows'] == baseline['rows'],
        replay_four_pass_exposure=replay_four, candidate_total_sft=candidate_total,
        baseline_total_sft=baseline_total, planned_updates=updates,
        planned_native_targets=updates * 8192 if updates is not None else None,
        planned_padded_sft_slots=candidate_total['rows'] * 1024,
        token_counts_basis='제공된 수집기 인코딩 메타데이터의 합이며 quarter_records가 실제 인코더를 별도로 검산함',
        replay_counts_basis='고정 V2 보고서의 선언값이며 호출자가 동결 보존 자료와 위치를 검산함',
        overlap_scope='TRAIN 구간끼리 기사·문맥 중복은 허용하며 질문 root는 겹치지 않음',
        source_content_verification='고정 원천 수집·목록 검산은 호출자 소유이며 이 도구는 자산을 읽지 않음',
        generated_answers_read=False, files_written=False, model_loaded=False,
        quality_claim='NOT_RUN; 같은 행 수·업데이트가 같은 입력·지도 토큰 노출을 뜻하지 않음')
    return copy.deepcopy(quarters), proof


def quarter_records(quarters, index, replay, tok):
    """변경하지 않은 기존 course.records로 한 논리 구간을 인코딩한다."""
    if (not isinstance(quarters, (list, tuple)) or len(quarters) != 4
            or type(index) is not int or index not in range(4)):
        raise ValueError('동결된 구간 네 개와 0부터 3 사이의 명시된 구간 번호 필요')
    natural, controls = c.records(quarters[index], replay, tok)
    for pair, records in zip(quarters[index], natural):
        for view, record in enumerate(records):
            targets = [value for value in record.y if value != -100]
            if data.sha(targets) != pair['encoding'][str(view)]['target_ids_sha256']:
                raise ValueError('실제 구간 인코더의 지도 식별자 해시가 다름')
    return natural, controls
