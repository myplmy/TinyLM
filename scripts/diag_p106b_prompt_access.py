#!/usr/bin/env python3
"""Bounded inference-only 24 probes x four fixed prompt packages x six CPs.

No experiment Runtime, training, teacher, or checkpoint saving. Literal mismatch
does not mean semantic error. Every condition is retained; no best-of selection.
Metadata/check-only use stdlib and the strict research UI's metadata API only.
Actual generation is CUDA-only through that loader; there is no CPU fallback.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from scripts import interactive_research_infer as ui  # stdlib-only module import

TAG = 'p106b_prompt_access_v1_s1337'
SCHEMA = 'P106B_PROMPT_ACCESS_V1'
F4 = 'handoff/audit/WIP_20261021_PROMPT_ACCESS_F4.json'
SCRIPT, TEST = 'scripts/diag_p106b_prompt_access.py', 'scripts/test_p106b_prompt_access.py'
EXTRA_SOURCES = (SCRIPT, TEST, 'scripts/p106b_shards.py', 'scripts/p106b_stage_receipt.py')
FORMATS = ('chat_bare', 'chat_contract', 'chat_fewshot', 'raw_qa')
SAMPLE_CASE_IDS = ('add_1_1_ko', 'younghee_5_ko', 'apple_general_ko', 'greeting_general_en')
MODEL_NAMES = ('native595-q', 'native595-f', 'old299-broad-q', 'old299-broad-f', 'new595-broad-q', 'new595-broad-f')
LIMITS = dict(end_utc='2026-10-21T07:40:00+00:00', worker_cap_seconds=600,
              wrapper_cap_seconds=630, record_before_user17KST=True)
REPORT_END = '2026-10-21T08:00:00+00:00'
IMPLEMENTATION_READY = True

# Exact bilingual questions and code-owned literal oracles are frozen here.
PROBES = (
    ('add_1_1', 'arithmetic', '1+1은?', 'What is 1+1?', '2', '2'),
    ('add_2_2', 'arithmetic', '2+2는?', 'What is 2+2?', '4', '4'),
    ('add_7_5', 'arithmetic', '7+5는?', 'What is 7+5?', '12', '12'),
    ('sub_20_8', 'arithmetic', '20-8은?', 'What is 20-8?', '12', '12'),
    ('food_B', 'lookup', 'A는 사과고 B는 당근이다. B는?', 'A is an apple and B is a carrot. What is B?', '당근', 'carrot'),
    ('younghee_5', 'lookup', '민수는 사과 3개, 영희는 사과 5개를 가지고 있습니다. 영희의 사과는 몇 개입니까?',
     'Minsu has 3 apples and Younghee has 5 apples. How many apples does Younghee have?', '5', '5'),
    ('book_blue', 'lookup', '책은 파랑이고 카드는 빨강이다. 책의 색은?', 'The book is blue and the card is red. What color is the book?', '파랑', 'blue'),
    ('update_B_3', 'update', 'A=1, B=8이다. B를 3으로 바꾼다. B는?', 'A=1 and B=8. Update B to 3. What is B?', '3', '3'),
    ('apple_general', 'general', '사과에 대해 알려줘', 'Tell me about apples.', None, None),
    ('basketball_general', 'general', '농구란?', 'What is basketball?', None, None),
    ('greeting_general', 'general', '반가워', 'Nice to meet you.', None, None),
    ('help_general', 'general', '무엇을 도와줄 수 있어?', 'What can you help with?', None, None),
)
EXAMPLES = {
    'arithmetic': {
        'ko': (('demo_add_6_8', '6+8은?', '14'), ('demo_sub_21_5', '21-5는?', '16')),
        'en': (('demo_add_6_8', 'What is 6+8?', '14'), ('demo_sub_21_5', 'What is 21-5?', '16'))},
    'lookup': {
        'ko': (('demo_food_D', 'C는 배이고 D는 오이다. D는?', '오이'),
               ('demo_sujin_2', '수진은 공 2개, 지훈은 공 9개를 가지고 있다. 수진의 공은 몇 개?', '2'),
               ('demo_cup_white', '컵은 흰색이고 펜은 검정이다. 컵의 색은?', '흰색')),
        'en': (('demo_food_D', 'C is a pear and D is a cucumber. What is D?', 'cucumber'),
               ('demo_sujin_2', 'Sujin has 2 balls and Jihun has 9 balls. How many balls does Sujin have?', '2'),
               ('demo_cup_white', 'The cup is white and the pen is black. What color is the cup?', 'white'))},
    'update': {
        'ko': (('demo_update_C_6', 'C=4, D=9이다. C를 6으로 바꾼다. C는?', '6'),
               ('demo_update_S_7', 'R=5, S=2이다. S를 7로 바꾼다. S는?', '7')),
        'en': (('demo_update_C_6', 'C=4 and D=9. Update C to 6. What is C?', '6'),
               ('demo_update_S_7', 'R=5 and S=2. Update S to 7. What is S?', '7'))},
    'general': {
        'ko': (('demo_goodbye', '잘 가', '안녕히 가세요.'), ('demo_thanks', '고마워', '천만에요.')),
        'en': (('demo_goodbye', 'Goodbye.', 'Goodbye.'), ('demo_thanks', 'Thank you.', "You're welcome."))},
}


class Hold(RuntimeError): pass


def sha(value): return ui.canonical_sha(value)
def text_sha(value): return hashlib.sha256(value.encode('utf-8')).hexdigest().upper()
def utc_now(): return datetime.now(timezone.utc)


def cases():
    result = []
    for root, family, ko, en, gold_ko, gold_en in PROBES:
        for language, question, oracle in (('ko', ko, gold_ko), ('en', en, gold_en)):
            result.append(dict(id=root + '_' + language, root=root, family=family, language=language,
                question=question, oracle=oracle, scoring='HUMAN_REVIEW' if oracle is None else 'exact_literal_match'))
    if len(result) != 24 or sum(c['oracle'] is not None for c in result) != 16 or len({c['id'] for c in result}) != 24:
        raise ValueError('exact24/16oracle/8qualitative frozen probes required')
    return result


def render_input(case, form):
    if form not in FORMATS: raise ValueError('one of four frozen prompt packages required')
    question = case['question']; ko = case['language'] == 'ko'; demonstrations = []
    qmark, amark = ('질문:', '답:') if ko else ('Question:', 'Answer:')
    if form == 'raw_qa':
        return dict(format=form, question=question, user_text=None, text=qmark + ' ' + question + '\n' + amark,
                    serialization='PLAIN_QA_NO_CHATML', demonstrations=[], actual_history=False)
    body = question
    if form == 'chat_contract':
        instruction = ('풀이 없이 정답 단어 또는 숫자만 쓰세요.' if ko else 'Give only the answer word or number, without explanation.')
        if case['oracle'] is None: instruction = '한국어로 간단히 답하세요.' if ko else 'Answer briefly in English.'
        body = instruction + '\n' + question
    elif form == 'chat_fewshot':
        examples = EXAMPLES[case['family']][case['language']]
        if not 2 <= len(examples) <= 3 or any(root == case['root'] or q == question for root, q, _ in examples):
            raise ValueError('two or three explicit different-problem demonstrations required')
        heading = ('다음은 예시입니다. 마지막 질문에만 답하세요.' if ko else 'The following are examples. Answer only the final question.')
        parts = [heading]
        for index, (root, q, a) in enumerate(examples, 1):
            demonstrations.append(dict(root=root, question=q, answer=a))
            parts.append(('예시 ' if ko else 'Example ') + str(index) + '\n' + qmark + ' ' + q + '\n' + amark + ' ' + a)
        parts.append(('마지막 질문: ' if ko else 'Final question: ') + question + '\n' + amark)
        body = '\n\n'.join(parts)
    return dict(format=form, question=question, user_text=body,
        text='<|im_start|>user\n' + body + '<|im_end|>\n<|im_start|>assistant\n',
        serialization='CHATML_ONE_USER_NO_HISTORY', demonstrations=demonstrations, actual_history=False)


def requests():
    return [dict(model=model, format=form, case=case) for model in MODEL_NAMES for form in FORMATS for case in cases()]


def score(case, answer):
    if not isinstance(answer, str): raise ValueError('full raw text answer required')
    return None if case['oracle'] is None else answer == case['oracle']


def whitespace_score(case, answer):
    if not isinstance(answer, str): raise ValueError('full raw text answer required')
    return None if case['oracle'] is None else answer.strip() == case['oracle']


def sample_payload(row):
    case = row['request']['case']
    if case['id'] not in SAMPLE_CASE_IDS: return None
    return dict(model=row['request']['model'], format=row['request']['format'], case_id=case['id'],
        question=case['question'], input_text=row['input']['text'], actual_answer=row['answer'],
        finish=row['generation']['finish_reason'], exact_literal_match=row['exact_literal_match'],
        whitespace_literal_match=row['whitespace_literal_match'])


def owned_path(relative, root=ROOT):
    relative, root = Path(relative), Path(root)
    if (not root.is_absolute() or '..' in root.parts or root.is_symlink() or not root.is_dir()
            or relative.is_absolute() or not relative.parts or '..' in relative.parts
            or relative.parts[0] in ('HF', 'datasets', 'data_cache')):
        raise ValueError('explicit nonsymlink nonprotected repository-relative path required')
    if any(ancestor.is_symlink() for ancestor in root.parents): raise ValueError('symlink ROOT ancestor refused')
    path = root
    for index, part in enumerate(relative.parts):
        path = path / part
        if path.is_symlink(): raise ValueError('symlink output/source or ancestor refused')
        if index < len(relative.parts) - 1 and path.exists() and not path.is_dir(): raise ValueError('non-directory ancestor refused')
    return path


def output_path(relative, root=ROOT):
    if not (Path(relative).is_relative_to(Path('runs/eval') / TAG) or Path(relative).is_relative_to(Path('test_result/evidence') / TAG)):
        raise ValueError('only new prompt-access raw/report/activity namespace may be written')
    return owned_path(relative, root)


def write_json(relative, value, root=ROOT):
    path = output_path(relative, root); raw = (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + '\n').encode('utf-8')
    if len(raw) >= 20_000_000: raise ValueError('small evidence must stay below20MB')
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream: stream.write(raw)


def read_json(relative, root=ROOT):
    path = owned_path(relative, root)
    with path.open('rb') as stream: raw = stream.read(20_000_000)
    if len(raw) >= 20_000_000: raise ValueError('small evidence limit exceeded')
    value = json.loads(raw.decode('utf-8'))
    if not isinstance(value, dict): raise ValueError('evidence JSON object required')
    return value


def report_path(mode): return 'test_result/evidence/' + TAG + '/' + mode + '/report.json'
def activity_path(mode): return 'test_result/evidence/' + TAG + '/activity_' + mode + '.json'
def raw_path(): return 'runs/eval/' + TAG


def metadata(root=ROOT):
    f4 = read_json(F4, root); manifest = ui.verify_manifest(root)
    design = dict(models=list(MODEL_NAMES), formats=list(FORMATS), cases=24, oracle_cases=16, qualitative_cases=8,
        requests=576, max_new=64, precision='FP32_MATH', tf32=False, kv=True, mtp=False, greedy=True,
        temperature=0, top_k=1, weight_updates=0, checkpoint_writes=0, teacher_calls=0)
    if (f4.get('schema') != 'TINYLM_PROMPT_ACCESS_F4_V1' or f4.get('tag') != TAG or sha(f4.get('design')) != sha(design)
            or sha(f4.get('limits')) != sha(LIMITS) or tuple(s.name for s in ui.MODELS) != MODEL_NAMES):
        raise ValueError('exact current prompt-access F4/six-model/limits contract required')
    pins = dict(manifest['source_sha256'])
    pins.update({p: ui.file_sha(owned_path(p, root)) for p in EXTRA_SOURCES})
    bindings = {name: dict(checkpoint=e['checkpoint']['path'], checkpoint_sha256=e['checkpoint']['sha256'],
        core_sha256=e['core_sha256'], report_sha256=e['report']['sha256'], quantization_route=e['header']['quantization_route'])
        for name, e in manifest['entries'].items()}
    return dict(schema=SCHEMA, tag=TAG, design=design, limits=LIMITS, report_end_utc=REPORT_END,
        f4_sha256=ui.file_sha(owned_path(F4, root)), source_sha256=pins,
        manifest_sha256=sha(manifest), bindings=bindings, tokenizer_sha256=ui.TOKENIZER_SHA,
        cases_sha256=sha(cases()), requests_sha256=sha(requests()),
        inputs_sha256=sha([render_input(case, form) for form in FORMATS for case in cases()]),
        metric='exact_literal_match_NOT_SEMANTIC_ERROR', no_best_of_selection=True,
        secondary_metric='whitespace_literal_match', secondary_rule='answer.strip() == oracle',
        sample_case_ids=list(SAMPLE_CASE_IDS), fixed_stdout_samples=96,
        training_updates=0, checkpoint_writes=0, teacher_calls=0)


def authority(mode, now=None):
    now = utc_now() if now is None else now
    if now.tzinfo is None: raise ValueError('aware actual UTC required')
    end = datetime.fromisoformat(LIMITS['end_utc'] if mode == 'evaluate' else REPORT_END)
    remaining = (end - now).total_seconds()
    if remaining <= 0: raise Hold('own inference16:40/report17:00 boundary reached')
    return remaining


@contextmanager
def bounded(seconds):
    old_term, old_alarm = signal.getsignal(signal.SIGTERM), signal.getsignal(signal.SIGALRM)
    old_timer = signal.getitimer(signal.ITIMER_REAL)
    def terminate(_n, _f): raise KeyboardInterrupt('own SIGTERM')
    def timeout(_n, _f): raise Hold('own actual wall cap reached; partial is not PASS')
    signal.signal(signal.SIGTERM, terminate); signal.signal(signal.SIGALRM, timeout)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try: yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, *old_timer)
        signal.signal(signal.SIGALRM, old_alarm); signal.signal(signal.SIGTERM, old_term)


def emit_request(active, case, form):
    rendered = render_input(case, form); tok = active['tokenizer']; prefix = tok.encode(rendered['text']).ids
    if active['cfg'].max_seq_len != 1024 or len(prefix) + 64 > 1024: raise ValueError('complete input plus64 must fit1024; never truncate')
    active['route'].assert_active()
    if form != 'raw_qa':
        answer, generation = ui.emit(active, rendered['user_text'], max_new=64, history=())
    else:
        sample, capture_type, forward_type = ui.generation_tools(Path(active['root']))
        capture = capture_type(tok)
        with active['torch'].no_grad():
            _, meta = sample(forward_type(active['model'], 'fp32_math'), active['cfg'], capture, rendered['text'],
                max_new=64, temperature=0., top_k=1, device='cuda', use_cache=True,
                logits_last_only=True, return_metadata=True, mtp_tokens=1, stop_token_sequences=[[4]])
        answer, generation = ui.answer_from_tokens(tok, prefix, capture.decoded_ids, meta, 64)
        generation.update(precision='FP32_MATH', tf32=False, use_cache=True, mtp=False, temperature=0., top_k=1,
                          actual_history=False, prompt_sha256=text_sha(rendered['text']))
    active['route'].assert_active()
    if generation.get('prompt_sha256') != text_sha(rendered['text']) or generation.get('prompt_tokens') != len(prefix):
        raise ValueError('UI actual serializer/prefix differs from exact frozen rendered input')
    generation.update(prompt_ids=prefix, prompt_ids_sha256=sha(prefix))
    return answer, generation, rendered


def validate_generation(row, tok):
    request = row['request']; rendered = render_input(request['case'], request['format']); generation = row['generation']
    prefix = tok.encode(rendered['text']).ids; ids = generation.get('generated_ids')
    if (row.get('input') != rendered or not isinstance(ids, list)
            or any(type(i) is not int or not 0 <= i < 32768 for i in prefix + ids)
            or len(prefix) + 64 > 1024 or generation.get('prompt_ids') != prefix or generation.get('prompt_ids_sha256') != sha(prefix)
            or generation.get('prompt_sha256') != text_sha(rendered['text']) or type(generation.get('max_new')) is not int or generation['max_new'] != 64
            or generation.get('precision') != 'FP32_MATH' or generation.get('tf32') is not False
            or generation.get('use_cache') is not True or generation.get('mtp') is not False
            or type(generation.get('temperature')) not in (int, float) or generation['temperature'] != 0.
            or type(generation.get('top_k')) is not int or generation['top_k'] != 1 or generation.get('actual_history') is not False
            or type(generation.get('content_tokens')) is not int or generation.get('terminal_only_removed') is not True
            or not isinstance(generation.get('terminal_ids'), list) or any(type(i) is not int for i in generation['terminal_ids'])
            or generation.get('eos_token_available') is not True or generation.get('stop_at_eos_requested') is not True
            or generation.get('stop_at_eos_effective') is not True or generation.get('stop_token_sequences') != [[4]]):
        raise ValueError('exact input/IDs/prefix/precision/no-history receipt differs')
    answer, verified = ui.answer_from_tokens(tok, prefix, prefix + ids, generation, 64)
    if (answer != row.get('answer') or any(generation.get(k) != verified[k] for k in
            ('prompt_tokens', 'content_tokens', 'terminal_ids', 'terminal_only_removed'))):
        raise ValueError('actual body ID decode/terminal-only removal differs')


def summarize(rows):
    expected = requests()
    if len(rows) != 576: raise ValueError('all576 fixed first answers required; no partial/best-of verdict')
    groups = {}; total = dict(requests=0, oracle=0, qualitative=0, exact_literal_match=0, whitespace_literal_match=0)
    for index, (row, request) in enumerate(zip(rows, expected)):
        case = request['case']; literal = score(case, row['answer']); whitespace = whitespace_score(case, row['answer'])
        if (row.get('index') != index or row.get('request') != request or row.get('exact_literal_match') is not literal
                or row.get('whitespace_literal_match') is not whitespace):
            raise ValueError('raw original request/order/literal regrade differs')
        key = request['model'] + ':' + request['format']
        group = groups.setdefault(key, dict(rows=0, oracle=0, qualitative=0, exact_literal_match=0, whitespace_literal_match=0,
            finish_reasons={}, generated_tokens=0, question_substring_present=0, by_language={}))
        group['rows'] += 1; group['generated_tokens'] += row['generation']['generated_tokens']
        reason = row['generation']['finish_reason']; group['finish_reasons'][reason] = group['finish_reasons'].get(reason, 0) + 1
        group['question_substring_present'] += int(case['question'] in row['answer'])
        lane = group['by_language'].setdefault(case['language'], dict(rows=0, oracle=0, qualitative=0, exact_literal_match=0, whitespace_literal_match=0))
        for bucket in (group, lane, total):
            if bucket is not group: bucket['requests' if bucket is total else 'rows'] += 1
            bucket['oracle'] += int(literal is not None); bucket['qualitative'] += int(literal is None)
            bucket['exact_literal_match'] += int(literal is True)
            bucket['whitespace_literal_match'] += int(whitespace is True)
    if len(groups) != 24 or any(g['rows'] != 24 or g['oracle'] != 16 or g['qualitative'] != 8 for g in groups.values()):
        raise ValueError('exact six x four groups of24/16oracle/8qualitative required')
    return dict(total=total, by_model_format=groups, metric='exact_literal_match',
        secondary_metric='whitespace_literal_match', secondary_rule='answer.strip() == oracle',
        question_substring_warning='Literal substring presence only; not an error or semantic copying judgment.',
        qualitative='HUMAN_REVIEW_NO_AUTOMATIC_SEMANTIC_SCORE',
        limitation='Expanded correct sentences may fail both literal metrics; mismatch is not semantic error. Secondary removes only leading/trailing whitespace.',
        no_best_of_selection=True, fixed_question_texts=24, semantic_roots=12, repeated_prompt_conditions=576)


def evaluate(identity, root=ROOT):
    from scripts.p106b_shards import ShardWriter
    directory = output_path(raw_path(), root)
    if directory.exists(): raise FileExistsError('existing complete/partial answers preserved')
    directory.mkdir(parents=True, exist_ok=False); output_path(raw_path(), root)
    writer = ShardWriter(directory, 'answers', limit=19_999_999); rows = []; sessions = []; complete = False
    sample_lines = progress_lines = 0
    try:
        for spec in ui.MODELS:
            authority('evaluate'); binding = identity['bindings'][spec.name]
            with ui.selected_runtime(spec, root=root) as active:
                runtime = {k: active[k] for k in ('name', 'checkpoint', 'checkpoint_sha256', 'core_sha256', 'report_sha256',
                    'manifest_sha256', 'tokenizer_sha256', 'quantization_route', 'gpu_point_query', 'precision', 'body_check_scope')}
                if (runtime['name'] != spec.name or runtime['precision'] != 'FP32_MATH'
                        or any(runtime[k] != v for k, v in binding.items()) or runtime['manifest_sha256'] != identity['manifest_sha256']
                        or runtime['tokenizer_sha256'] != identity['tokenizer_sha256']): raise ValueError('selected actual runtime/CP/core/route differs')
                start = len(rows)
                for form in FORMATS:
                    format_start = len(rows)
                    for case in cases():
                        authority('evaluate'); active['route'].assert_active()
                        answer, generation, rendered = emit_request(active, case, form)
                        row = dict(index=len(rows), request=dict(model=spec.name, format=form, case=case), input=rendered,
                            answer=answer, generation=generation, runtime=runtime, source_sha256=sha(identity['source_sha256']),
                            exact_literal_match=score(case, answer), whitespace_literal_match=whitespace_score(case, answer),
                            score_scope=case['scoring'])
                        validate_generation(row, active['tokenizer']); writer.append(row); rows.append(row)
                        sample = sample_payload(row)
                        if sample is not None:
                            print('[PROMPT_ACCESS_SAMPLE] ' + json.dumps(sample, ensure_ascii=False, sort_keys=True), flush=True)
                            sample_lines += 1
                    print('[PROMPT_ACCESS_PROGRESS] ' + json.dumps(dict(model=spec.name, format=form,
                        format_answers=len(rows) - format_start, model_answers=len(rows) - start, total_answers=len(rows),
                        expected_total=576, scope='FORMAT_COMPLETE_NOT_FINAL_VERDICT'), sort_keys=True), flush=True)
                    progress_lines += 1
                after = ui.state_fingerprint(active['model'])
                if after != binding['core_sha256']: raise RuntimeError('actual session body core changed')
                session = dict(name=spec.name, core_before=binding['core_sha256'], core_after=after, answers=len(rows) - start,
                    weights_changed=False, checkpoint_writes=0, session_exit_verified=False)
            # A failure in the UI context's final core/source check never reaches here.
            session['session_exit_verified'] = True; sessions.append(session)
        if metadata(root) != identity: raise ValueError('current runner/F4/manifest/source changed during inference')
        summary = summarize(rows)
        raw_manifest = writer.close(lineage=dict(tag=TAG, complete=True, requests_sha256=identity['requests_sha256'])); writer = None
        complete = True
        return dict(info=identity, status='PROMPT_ACCESS_COMPLETE', rows=len(rows), raw_manifest=raw_manifest,
            sessions=sessions, models_loaded=len(sessions), checkpoint_tensor_loads=len(sessions),
            stdout_sample_lines=sample_lines, stdout_progress_lines=progress_lines,
            weight_updates=0, checkpoint_writes=0, teacher_calls=0, summary=summary)
    finally:
        if writer is not None and rows:
            writer.close(lineage=dict(tag=TAG, complete=complete, partial=True, rows=len(rows)))


def closed(mode, identity, root=ROOT):
    activity = read_json(activity_path(mode), root); report = read_json(report_path(mode), root)
    begin, end = (datetime.fromisoformat(activity[k]) for k in ('started_at', 'ended_at'))
    cutoff = datetime.fromisoformat(LIMITS['end_utc'] if mode == 'evaluate' else REPORT_END)
    invocation = report.get('invocation', {})
    if (activity.get('complete') is not True or type(activity.get('returncode')) is not int or activity['returncode'] != 0
            or activity.get('mode') != mode or activity.get('info') != identity or report.get('info') != identity
            or activity.get('error_type') is not None or activity.get('result_sha256') != ui.file_sha(owned_path(report_path(mode), root))
            or type(activity.get('pid')) is not int or activity['pid'] <= 0 or type(activity.get('pgid')) is not int or activity['pgid'] != activity['pid']
            or type(activity.get('max_wall_sec')) is not int or activity['max_wall_sec'] != 600
            or type(report.get('max_wall_sec')) is not int or report['max_wall_sec'] != 600
            or begin.tzinfo is None or end.tzinfo is None or begin > end or begin + timedelta(seconds=600) > cutoff or end > cutoff
            or any(type(activity.get(k)) not in (int, float) or not math.isfinite(activity[k]) or activity[k] < 0 for k in ('seconds', 'utc_seconds'))
            or activity['seconds'] > 630 or not math.isclose(activity['utc_seconds'], (end - begin).total_seconds(), abs_tol=1e-5)
            or type(activity.get('admission_remaining')) not in (int, float) or not math.isfinite(activity['admission_remaining'])
            or activity['admission_remaining'] < 600
            or set(invocation) != {'mode', 'max_wall_sec', 'worker', 'argv', 'executable'}
            or invocation.get('mode') != mode or invocation.get('worker') is not True
            or type(invocation.get('max_wall_sec')) is not int or invocation['max_wall_sec'] != 600
            or not isinstance(invocation.get('argv'), list) or not invocation['argv']
            or any(not isinstance(v, str) or not v for v in invocation['argv'])
            or not isinstance(invocation.get('executable'), str) or not invocation['executable']
            or activity.get('invocation') != invocation):
        raise ValueError('original closed successful source/UTC/cap/PGID/report receipt required')
    return report


def readback(identity, root=ROOT):
    from scripts.p106b_shards import verify
    report = closed('evaluate', identity, root)
    if (report.get('status') != 'PROMPT_ACCESS_COMPLETE' or report.get('rows') != 576 or report.get('models_loaded') != 6
            or report.get('checkpoint_tensor_loads') != 6 or report.get('weight_updates') != 0
            or report.get('checkpoint_writes') != 0 or report.get('teacher_calls') != 0
            or report.get('stdout_sample_lines') != 96 or report.get('stdout_progress_lines') != 24): raise ValueError('full inference-only six-load result required')
    sessions = report['sessions']
    if [s['name'] for s in sessions] != list(MODEL_NAMES): raise ValueError('all six completed sessions required')
    for session in sessions:
        core = identity['bindings'][session['name']]['core_sha256']
        if (session.get('core_before') != core or session.get('core_after') != core or session.get('answers') != 96
                or session.get('session_exit_verified') is not True or session.get('weights_changed') is not False
                or session.get('checkpoint_writes') != 0): raise ValueError('actual unchanged core and successful final UI context exit required')
    directory = owned_path(raw_path(), root); manifest = read_json(raw_path() + '/answers_shards_manifest.json', root)
    if manifest != report['raw_manifest'] or manifest.get('lineage') != dict(tag=TAG, complete=True, requests_sha256=identity['requests_sha256']):
        raise ValueError('original complete raw manifest binding differs')
    verify(directory, manifest); rows = []
    for shard in manifest['shards']:
        with owned_path(raw_path() + '/' + shard['path'], root).open(encoding='utf-8') as stream:
            rows.extend(json.loads(line) for line in stream)
    ui.validate_import_environment(root); current = ui.verify_manifest(root)
    if sha(current) != identity['manifest_sha256']: raise ValueError('current strict inference manifest changed')
    tok = ui.local_tokenizer(current, root)
    for row in rows:
        request = row['request']; binding = identity['bindings'][request['model']]
        if (row['runtime'].get('name') != request['model'] or row['runtime'].get('precision') != 'FP32_MATH'
                or any(row['runtime'].get(k) != v for k, v in binding.items())
                or row['runtime'].get('manifest_sha256') != identity['manifest_sha256']
                or row['runtime'].get('tokenizer_sha256') != identity['tokenizer_sha256']
                or row.get('source_sha256') != sha(identity['source_sha256']) or row.get('score_scope') != request['case']['scoring']):
            raise ValueError('actual raw CP/core/route/source/scoring lineage differs')
        validate_generation(row, tok)
    summary = summarize(rows)
    if report.get('summary') != summary: raise ValueError('report summary differs from independent raw full regrade')
    return dict(info=identity, status='RAW_RECOUNTED_NOT_SEMANTIC_TRUTH', rows=len(rows), summary=summary,
        sessions=sessions, models_loaded=0, checkpoint_tensor_loads=0, tokenizer_loaded=True,
        weight_updates=0, checkpoint_writes=0, teacher_calls=0)


def worker(args, root=ROOT):
    mode = args.mode; began = utc_now(); tick = time.perf_counter(); identity = None; admitted = None; code = 9; error = None
    invocation = dict(mode=mode, max_wall_sec=600, worker=True, argv=list(sys.argv), executable=sys.executable)
    # Resolve the narrow write targets before the try/finally can create evidence.
    if owned_path(activity_path(mode), root).exists() or owned_path(report_path(mode), root).exists():
        raise FileExistsError('existing successful/failed stage preserved')
    try:
        with bounded(600):
            if os.getpgrp() != os.getpid(): raise Hold('internal worker must own a new process group')
            admitted = authority(mode)
            if admitted < 600: raise Hold('whole600-second cap does not fit remaining own UTC authority')
            identity = metadata(root)
            result = evaluate(identity, root) if mode == 'evaluate' else readback(identity, root)
            authority(mode)
            if metadata(root) != identity: raise ValueError('source/F4 changed before closing stage')
            result.update(max_wall_sec=600, invocation=invocation)
            write_json(report_path(mode), result, root); authority(mode); code = 0
    except KeyboardInterrupt: code = 130; error = 'KeyboardInterrupt'
    except Hold as exc: code = 8; error = type(exc).__name__; print('[HOLD] ' + str(exc), flush=True)
    except Exception as exc: code = 9; error = type(exc).__name__; print('[ERROR] ' + type(exc).__name__ + ': ' + str(exc), flush=True)
    finally:
        ended = utc_now()
        write_json(activity_path(mode), dict(info=identity, mode=mode, complete=code == 0, returncode=code, error_type=error,
            started_at=began.isoformat(), ended_at=ended.isoformat(), seconds=time.perf_counter() - tick,
            utc_seconds=(ended - began).total_seconds(), pid=os.getpid(), pgid=os.getpgrp(), max_wall_sec=600,
            admission_remaining=admitted, invocation=invocation,
            result_sha256=ui.file_sha(owned_path(report_path(mode), root)) if owned_path(report_path(mode), root).is_file() else None), root)
    return code


def verify_readonly(args, root=ROOT):
    cap = min(600., authority('readback'))
    with bounded(cap):
        identity = metadata(root); actual = readback(identity, root)
        if args.mode == 'readback':
            report = closed('readback', identity, root)
            if {k: v for k, v in report.items() if k not in ('max_wall_sec', 'invocation')} != actual: raise ValueError('final readback report differs from raw recount')
        authority('readback')
        print('[READONLY_VERIFIED] ' + json.dumps(dict(status=actual['status'], rows=actual['rows'], models_loaded=0,
            checkpoint_tensor_loads=0, max_wall_sec=cap)), flush=True)
    return 0


def launch(command, cap):
    proc = subprocess.Popen(command, cwd=ROOT, stdin=subprocess.DEVNULL, start_new_session=True)
    try: return proc.wait(timeout=cap)
    except (subprocess.TimeoutExpired, KeyboardInterrupt):
        os.killpg(proc.pid, signal.SIGTERM)
        try: proc.wait(timeout=30)
        except subprocess.TimeoutExpired: os.killpg(proc.pid, signal.SIGKILL); proc.wait()
        return 130


def execute(args):
    from scripts.p106b_stage_receipt import pipeline
    base = [sys.executable, '-B', '-X', 'utf8', SCRIPT, '--mode', args.mode, '--max-wall-sec', '600']
    command = base + ['--execute', '--worker']
    def dispatch(value):
        code = launch(value, 600)
        if code == 0 and value == command:
            try: cap = min(600., authority('readback'))
            except Hold as exc: print('[HOLD] ' + str(exc), flush=True); return 8
            code = launch(base + ['--verify-readonly'], cap)
        return code
    phases = [('REGRESSION', [sys.executable, '-B', '-X', 'utf8', '-m', 'unittest', 'scripts.test_p106b_prompt_access']),
              ('PREFLIGHT', base + ['--check-only']), ('EXECUTE', command)]
    return pipeline(phases, dispatch, lambda s: print(s, flush=True), experiment=TAG + '_' + args.mode)['returncode']


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--mode', choices=('evaluate', 'readback'), required=True)
    p.add_argument('--max-wall-sec', type=int, default=600); p.add_argument('--worker', action='store_true')
    action = p.add_mutually_exclusive_group(required=True)
    action.add_argument('--check-only', action='store_true'); action.add_argument('--execute', action='store_true')
    action.add_argument('--verify-readonly', action='store_true'); args = p.parse_args(argv)
    try:
        if args.max_wall_sec != 600 or args.worker and not args.execute: raise ValueError('fixed600 cap; worker only with execute')
        if not IMPLEMENTATION_READY: raise Hold('implementation/root review pending; actual inference NOT_RUN')
        if args.check_only:
            identity = metadata(); print('[STATIC_ONLY] ' + json.dumps(dict(requests=576, source_files=len(identity['source_sha256']),
                torch_imports=0, models_loaded=0, checkpoint_tensor_loads=0, training_updates=0)), flush=True); return 0
        if args.verify_readonly: return verify_readonly(args)
        return worker(args) if args.worker else execute(args)
    except Hold as exc: print('[HOLD] ' + str(exc), flush=True); return 8
    except KeyboardInterrupt: print('[INTERRUPTED] no final PASS', flush=True); return 130
    except Exception as exc: print('[ERROR] ' + type(exc).__name__ + ': ' + str(exc), file=sys.stderr, flush=True); return 9


if __name__ == '__main__': raise SystemExit(main())
