"""독립 TRAIN producer: wrapper1의 필드 순서만 뒤집은 새 wrapper3.

기존 collector/render_view/봉인 wrapper2를 변경하거나 호출해 학습하지 않는다.
이미 검산된 TRAIN pair와 실제 레코드를 입력받아 원형·정답을 보존한다.
"""
from __future__ import annotations
from collections import Counter
import copy
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import p106b_night_qa_data as original
from scripts import p106b_night_learning as method

TAG = 'p106b_night_order_v1_s1337'
CORPUS = ROOT / 'HF/sft_ready' / TAG / 'corpus'
EVIDENCE = ROOT / 'test_result/evidence' / TAG
VERSION = 'P106B_NIGHT_FIELD_ORDER_ONLY_V1'


def render(pair):
    from tinylm.chat.canonical import normalize, validate
    if pair.get('split') != 'train' or pair.get('language') not in ('ko', 'en'):
        raise ValueError('출처가 검산된 TRAIN 한영 질문만 새 producer에 허용')
    row = validate(normalize(copy.deepcopy(pair['views']['1'])))
    messages = row['messages']
    if (len(messages) != 2 or messages[0]['role'] != 'user' or messages[1]['role'] != 'assistant'
            or original.text(messages[0]) != original._user(pair['context'], pair['question'], pair['language'], 1)
            or original.text(messages[1]) != pair['answers'][0]['text']):
        raise ValueError('원래 wrapper1의 실제 지시·원형·정답이 달라짐')
    if pair['language'] == 'ko':
        content = '다음 지문에 근거해 질문에 대한 답만 쓰세요.\n질문:\n' + pair['question'] + '\n지문:\n' + pair['context']
    else:
        content = 'Answer the question using only the passage below.\nQuestion:\n' + pair['question'] + '\nPassage:\n' + pair['context']
    if Counter(content) != Counter(original.text(messages[0])):
        raise ValueError('필드 순서 외에 문자·지시·원문을 바꾸면 안 됨')
    messages[0]['content'] = content
    row['meta'].update(wrapper_view=3, original_wrapper_view=1, course_version=VERSION,
        producer_transform='FIELD_ORDER_ONLY_QUESTION_BEFORE_CONTEXT', held_wrapper2_training=False)
    return validate(normalize(row))


def transform(quarters, old_courses, tok):
    from tinylm.train.mtp_sft import encode_record
    from tinylm.chat.serialize import serialize
    if len(quarters) != 4 or len(old_courses) != 4: raise ValueError('같은 네 논리구간 필요')
    new_courses = []; proofs = []; total = Counter(); schedules = []
    for index, (pairs, (natural, replay)) in enumerate(zip(quarters, old_courses)):
        if len(pairs) != len(natural): raise ValueError('같은 원형·레코드 순서 필요')
        transformed = []
        for pair, records in zip(pairs, natural):
            if len(records) != 2: raise ValueError('원래0/1 쌍 필요')
            row = render(pair); record = encode_record(row, tok)
            prompt = serialize(dict(messages=row['messages'][:-1]), 'chatml', add_generation_prompt=True)
            target = [v for v in record.y if v != -100]
            if (target != [v for v in records[0].y if v != -100]
                    or record.targets != records[1].targets or len(record.x) != len(record.y)
                    or record.x_tokens > 1024 or len(tok.encode(prompt).ids) + 128 > 1024):
                raise ValueError('새3의 실제 정답 ID/완전한 입력·생성 예산이 달라짐')
            method.paired_positions([records[0], record], tok.token_to_id('<|im_end|>'))
            transformed.append([records[0], record])
            proofs.append(dict(root=pair['root'], language=pair['language'], logical_quarter=index + 1,
                source_root=pair['root'], original_views=[0, 1], training_views=[0, 3],
                char_multiset_equal=True, original_x_tokens=records[1].x_tokens, x_tokens=record.x_tokens,
                assistant_targets=record.targets, x_sha256=original.sha(record.x), y_sha256=original.sha(record.y),
                target_ids_sha256=original.sha(target), canonical_sha256=original.sha(row)))
        exposure = Counter(); words = []; content_n = 0
        groups = method.schedule(len(transformed), len(replay), index)
        from scripts import diag_p106b_night_train as prior
        for group in groups:
            denom, content = prior.denominators(group, transformed, replay); words.append(denom); content_n += content
            for micro in group:
                for record in prior.micro_records(micro, transformed, replay):
                    exposure.update(rows=1, x_tokens=record.x_tokens, assistant_targets=record.targets)
        total.update(exposure)
        schedules.append(dict(quarter=index + 1, updates=len(groups), exposure=dict(exposure),
            content_targets=content_n, denominators=words,
            schedule_sha256=original.sha([[dict(kind=m.kind, indices=m.indices) for m in g] for g in groups])))
        new_courses.append((transformed, replay))
    return new_courses, proofs, dict(total), schedules
