#!/usr/bin/env python3
"""닫힌 두 학생의 표현·최종행 지시 진단. 실제 CPU 모델 실행은 총괄 소유다.

확인 전용은 소스와 인자만 읽는다. 실행에는 확인 출력의 code_sha256을
--code-sha256으로 다시 지정해야 한다. 기존 평가 폴더·학습·CP 저장은 건드리지 않는다.
신호는 네이티브 연산 도중 지연될 수 있다. 실제 총괄 실행은 외부 timeout으로도
감싸며, 기한 초과 결과를 완료로 승인하지 않는다. 강제 종료 뒤에는 닫히지 않은
raw가 남을 수 있으므로 성공 report가 없으면 완료로 해석하지 않는다.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import gc
import hashlib
import importlib
import json
import os
from pathlib import Path
import re
import signal
import sys
import time
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
VERSION = 'P101A_REASONING_SURFACE_CPU_V1'
PROFILES = ('ORIGINAL', 'CASUAL', 'CASUAL_FINAL')
MODELS = ('direct', 'trace')
MAX_NEW = 128
LIMIT = 19_999_999
TOKENIZER = 'data_cache/tok-ko-en-32768-chat32.json'
TOK_SHA = '9716F40E4C504D6AF37DDE76CCA578E30B45E9CA86C8B6BB79B2FA095D3AC88E'
DEPENDENCY_SHA = '0D7A02C917E4109338280493A8EDF60911DBF162A2F319C842A890EDFA32DA1B'
EXTRA_SOURCES = (
    'scripts/diag_p101a_clean_eval.py', 'scripts/test_p101a_clean_eval.py',
    'scripts/diag_p101a_mtp_parity.py', 'scripts/diag_p101a_sft_mtp.py',
    'scripts/diag_p101a_clean_bilingual.py', 'scripts/p101a_sft_mtp_data.py',
    'scripts/p106b_shards.py', 'scripts/p106b_verified_trace_data.py',
    'scripts/p101a_sft_mtp_infer.py', 'scripts/test_p101a_sft_mtp.py',
    'scripts/test_p101a_sft_mtp_data.py', 'scripts/test_p101a_sft_mtp_driver.py',
    'scripts/test_p101a_clean_bilingual.py')
OWN_SOURCES = ('scripts/diag_p101a_reasoning_surface_cpu.py',
               'scripts/test_p101a_reasoning_surface_cpu.py')
PINS = {
    'direct': dict(report='F6845DE0DC50C6DAF07BC2B3FDAE6D08EBC29709C6CAFE0E53176C68C76AC209',
        evaluation='4050E99C8CC93118354A96FE85CD750019DD09378F1B1D671279429DF989FCAD',
        corpus='B814B42FC4D5B1D1AE4F1E77F03E97E73440D8EEEED031FCEEA9112F3D515AA4',
        checkpoint='993744FC2846DCAF8172335E445C44457551104491634AD17EA88967B5FA1D43'),
    'trace': dict(report='152AFAE3545D405DBD4E05034B241B6CDE72B45236C5BEF144C2E9E58A6E2811',
        evaluation='39A27A712ECAA2E8D622019A466564923C504A91E839E9FF3515E52C9D3DB869',
        corpus='3D4374CFB5944A703C6509F44E01D4FFA239C6D3123F1C8D54FA18622EF8CB6E',
        checkpoint='1E85D33ADB3D02A2854D416B83D90FE2459D75C987523ACADF87CDCE3287D031')}
FINAL_INSTRUCTION = {
    'ko': "마지막 줄은 '답: 정수' 형식으로 정확히 한 번 쓰세요.",
    'en': "Write exactly one final line in the form 'Answer: integer'."}


def utc_now():
    return datetime.now(timezone.utc)


def jsha(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
        separators=(',', ':'), allow_nan=False).encode()).hexdigest().upper()


def regular(path):
    if any(p.is_symlink() for p in (path, *path.parents)) or not path.is_file():
        raise ValueError('일반 파일만 허용: ' + str(path))
    return path


def digest(path):
    h = hashlib.sha256()
    with regular(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest().upper()


def source_contract():
    paths = sorted(set(EXTRA_SOURCES) | {p.relative_to(ROOT).as_posix()
        for p in (ROOT / 'tinylm').rglob('*.py')})
    sources = {p: digest(ROOT / p) for p in paths}
    if jsha(sources) != DEPENDENCY_SHA:
        raise ValueError('동결 의존 소스 SHA가 다름')
    sources.update({p: digest(ROOT / p) for p in OWN_SOURCES})
    return dict(code_sha256=jsha(sources), code_files_sha256=sources,
                dependency_sha256=DEPENDENCY_SHA)


def arguments(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument('--check-only', action='store_true')
    g.add_argument('--execute', action='store_true')
    p.add_argument('--run-id', required=True)
    p.add_argument('--deadline', required=True)
    p.add_argument('--max-wall-sec', required=True, type=int)
    p.add_argument('--code-sha256')
    a = p.parse_args(argv)
    validate_arguments(a)
    return a


def validate_arguments(a):
    if not re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,47}', a.run_id):
        raise ValueError('짧은 ASCII 실행 식별자 필요')
    if not 60 <= a.max_wall_sec <= 900:
        raise ValueError('max-wall-sec는 60..900')
    d = datetime.fromisoformat(a.deadline.replace('Z', '+00:00'))
    if d.tzinfo is None or d.utcoffset() is None or d <= utc_now():
        raise ValueError('미래의 시간대 포함 절대 기한 필요')
    if bool(a.execute) == bool(a.check_only):
        raise ValueError('확인 또는 명시 실행 하나만 필요')
    if a.execute and not re.fullmatch(r'[A-Fa-f0-9]{64}', a.code_sha256 or ''):
        raise ValueError('실행에는 검토한 code-sha256 필요')
    return d.astimezone(timezone.utc)


def text(content):
    return content if isinstance(content, str) else ''.join(b['text'] for b in content)


def select_cases(rows):
    """정오·gold를 보지 않고 가족별 정렬 ROOT의 앞 2/1/1개만 고른다."""
    from scripts.p106b_verified_trace_data import canonical_root, checked_task
    result = []
    for family, count in (('addition', 2), ('lookup', 1), ('update', 1)):
        roots = sorted({r['meta']['root'] for r in rows if r['meta']['family'] == family})
        if len(roots) < count:
            raise ValueError('선택할 ROOT 부족')
        for root in roots[:count]:
            for language in ('ko', 'en'):
                found = [(i, r) for i, r in enumerate(rows) if
                    (r['meta']['root'], r['meta']['language'], r['meta']['view']) == (root, language, 0)]
                if len(found) != 1:
                    raise ValueError('ROOT/언어/view0의 단일 행 필요')
                index, row = found[0]
                m = row['meta']; checked_task(m['task'])
                if canonical_root(m['task']) != root or [x['role'] for x in row['messages']] != ['user', 'assistant']:
                    raise ValueError('원 ROOT/역할 계약 다름')
                original = text(row['messages'][0]['content'])
                if m['question_sha256'] != jsha(original) or original.splitlines()[-1] != FINAL_INSTRUCTION[language]:
                    raise ValueError('원 질문 SHA/마지막 지시문 다름')
                result.append(dict(index=index, source=row, source_sha256=jsha(row)))
    if len(result) != 8:
        raise ValueError('고정 8케이스 필요')
    return result


def profile_question(case, profile):
    r = case['source']; m = r['meta']; t = m['task']; ko = m['language'] == 'ko'
    original = text(r['messages'][0]['content'])
    if profile == 'ORIGINAL':
        return original
    if profile not in PROFILES:
        raise ValueError('등록된 표현만 허용')
    if t['family'] == 'addition':
        body = f"{t['a']}에 {t['b']}를 더하면 얼마야?" if ko else f"What's {t['a']} plus {t['b']}?"
    else:
        first = m['presentation']['first_subject']; second = next(n for n in t['facts'] if n != first)
        a, b = t['facts'][first], t['facts'][second]
        body = f'{first}는 {a}, {second}는 {b}야. ' if ko else f'{first} is {a} and {second} is {b}. '
        if t['family'] == 'update':
            u = t['update']
            body += f"{u['subject']} 값을 {u['value']}로 바꿨어. " if ko else f"I changed {u['subject']} to {u['value']}. "
        body += f"지금 {t['asked']} 값이 뭐야?" if ko else f"What is {t['asked']} now?"
    return body if profile == 'CASUAL' else body + '\n' + original.splitlines()[-1]


def surface_score(case, answer, model, extraction_ok=True):
    from scripts.p106b_verified_trace_data import score_response, truth
    m = case['source']['meta']; gold = truth(m['task'])
    z = score_response(m['task'], answer, m['language'], model)
    bare = bool(re.fullmatch(r'0|[1-9][0-9]*', answer.strip()))
    bare_value = int(answer.strip()) if bare and len(answer.strip()) <= 10 else None
    exact = extraction_ok and answer.strip() == str(gold)
    content = extraction_ok and (z['final_correct'] or exact)
    status = 'EXACT_VALUE_MATCH' if content else 'EXPLICIT_VALUE_WRONG' if extraction_ok and (
        z['final_contract'] or bare_value is not None) else 'UNJUDGED_READ_RAW'
    return dict(z, extraction_ok=extraction_ok, bare_numeric_exact=bool(exact),
                bare_numeric_value=bare_value, content_value_status=status,
                semantic_truth='NOT_AUTOMATICALLY_ESTABLISHED')


def pinned_json(relative, expected):
    p = ROOT / relative
    if digest(p) != expected:
        raise ValueError('동결 report SHA 다름: ' + relative)
    return json.loads(p.read_text(encoding='utf-8'))


def load_inputs(code):
    """기존 prerequisites의 출력 존재 검사는 우회하지 않고 새 입장을 독립 검산한다."""
    from scripts.p101a_sft_mtp_data import stream_rows
    corpora = {}; gpu = {}; checkpoints = {}; receipts = {}; trained = {}
    for model in MODELS:
        tag = f'p101a_sft_mtp_verified_{model}_v3_s1337'; pin = PINS[model]
        evidence = f'test_result/evidence/{tag}'
        train = pinned_json(evidence + '/parent_ntp/report.json', pin['report']); trained[model] = train
        evaluation = pinned_json(evidence + '/first_answer_parent_ntp/report.json', pin['evaluation'])
        corpus_path = ROOT / 'HF/sft_ready' / tag / 'corpus'
        corpus = pinned_json(str((corpus_path / 'report.json').relative_to(ROOT)), pin['corpus'])
        if (train['status'] != 'SFT_MTP_TRAINED_EVAL_PENDING' or not train['checkpoint_saved']
                or train['updates'] != 128 or train['corpus_sha256'] != pin['corpus']
                or evaluation['status'] != 'FIRST_ANSWER_COLLECTION_COMPLETE' or evaluation['returncode'] != 0
                or evaluation['corpus_sha256'] != pin['corpus'] or evaluation['trained_report_sha256'] != pin['report']
                or evaluation['checkpoint_sha256'] != pin['checkpoint'] or corpus['status'] != 'CORPUS_READY'
                or any(v['tokenizer_sha256'] != TOK_SHA for v in (train, evaluation, corpus))):
            raise ValueError('닫힌 같은 교과/팔 조건이 아님')
        if any(code['code_files_sha256'].get(k) != v for obj in (train['code_sha256'], evaluation['source_sha256'])
               for k, v in obj.items()):
            raise ValueError('실행 당시 소스 SHA 다름')
        cp = ROOT / 'runs/ckpt' / f'm100s10_ko-en_32M_dense_chat32_{tag}_parent_ntp.pt'
        if train['checkpoint'] != cp.relative_to(ROOT).as_posix() or digest(cp) != pin['checkpoint']:
            raise ValueError('정확한 닫힌 CP가 아님')
        checkpoints[model] = cp
        corpora[model] = list(stream_rows(corpus_path, corpus['manifests']['test']))
        outputs = list(stream_rows(ROOT / evidence / 'first_answer_parent_ntp', evaluation['raw_manifest']))
        if len(corpora[model]) != 1024 or len(outputs) != 1024 or any(
            r['index'] != i or r['source'] != corpora[model][i] for i, r in enumerate(outputs)):
            raise ValueError('원 TEST/GPU 답 대응 다름')
        gpu[model] = outputs
        receipts[model] = dict(PINS[model], tag=tag)
    for d, t in zip(corpora['direct'], corpora['trace']):
        if d['messages'][0] != t['messages'][0] or any(d['meta'][k] != t['meta'][k]
                for k in ('root', 'task', 'language', 'view', 'presentation', 'gold_value')):
            raise ValueError('두 팔의 원 질문/조건 다름')
    if any(trained['direct'][k] != trained['trace'][k] for k in
           ('initial_core_sha256', 'parent_sha256', 'seed', 'updates', 'code_sha256')):
        raise ValueError('같은 초기화/업데이트 대조가 아님')
    if digest(ROOT / TOKENIZER) != TOK_SHA:
        raise ValueError('토크나이저 SHA 다름')
    return dict(cases=select_cases(corpora['direct']), gpu=gpu,
                checkpoints=checkpoints, receipt=receipts)


class BudgetExpired(RuntimeError):
    pass


@contextmanager
def wall_guard(seconds):
    if os.name != 'posix' or signal.getitimer(signal.ITIMER_REAL)[0] > 0:
        raise RuntimeError('독립 Linux 주 스레드의 시간 제한 필요')
    previous = {s: signal.getsignal(s) for s in (signal.SIGALRM, signal.SIGTERM)}
    def expired(*_):
        raise BudgetExpired('CPU 진단 기한 도달')
    for s in previous:
        signal.signal(s, expired)
    signal.setitimer(signal.ITIMER_REAL, max(.001, seconds))
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        for s, handler in previous.items():
            signal.signal(s, handler)


def deny_cuda(*args, **kwargs):
    raise RuntimeError('CPU 진단에서 CUDA 초기화 금지')


@contextmanager
def cpu_runtime():
    os.environ['OMP_NUM_THREADS'] = '2'
    os.environ['MKL_NUM_THREADS'] = '2'
    torch = importlib.import_module('torch')
    with patch.object(torch.cuda, '_lazy_init', deny_cuda):
        torch.set_num_threads(2); torch.set_num_interop_threads(2)
        if torch.get_num_threads() != 2 or torch.get_num_interop_threads() != 2:
            raise ValueError('CPU thread 2 고정 실패')
        inference = importlib.import_module('tinylm.infer.generate')
        tokens = importlib.import_module('tokenizers')
        precision = importlib.import_module('scripts.diag_p101a_mtp_parity')
        serializer = importlib.import_module('tinylm.chat.serialize')
        with torch.no_grad():
            yield SimpleNamespace(torch=torch, load_model=inference.load_model, sample=inference.sample,
                Tokenizer=tokens.Tokenizer, PrecisionForward=precision.PrecisionForward,
                serialize=serializer.serialize)


def write_json(path, value):
    body = json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n'
    if len(body.encode()) >= LIMIT:
        raise ValueError('보고서 크기 상한')
    with path.open('x', encoding='utf-8') as f:
        f.write(body)


def new_namespace(a):
    target = ROOT / 'test_result/evidence/p101a_reasoning_surface_cpu_v1' / a.run_id
    review = ROOT / 'review_request' / f'20261022_reasoning_surface_cpu_{a.run_id}.md'
    if any(p.is_symlink() for v in (target, review) for p in (v, *v.parents)):
        raise ValueError('연결된 출력 경로 금지')
    if target.exists() or review.exists():
        raise FileExistsError('같은 실행/문서 덮어쓰기 금지')
    target.mkdir(parents=True, exist_ok=False)
    review.parent.mkdir(parents=True, exist_ok=True)
    return target, review


def execute(a, code):
    from scripts.p106b_shards import ShardWriter, verify
    from scripts.diag_p101a_clean_eval import prompt_messages
    deadline = validate_arguments(a)
    if not a.execute or a.code_sha256.upper() != code['code_sha256']:
        raise ValueError('명시 실행/검토 소스 서명 불일치')
    target, review = new_namespace(a)
    start = time.monotonic(); end = start + a.max_wall_sec
    cells = {}; status = 'EXECUTION_ERROR'; rc = 9; error = None; inputs = None
    for model in MODELS:
        for profile in PROFILES:
            folder = target / (model + '_' + profile.lower()); folder.mkdir()
            cells[model, profile] = dict(folder=folder, writer=ShardWriter(folder, 'answers', limit=LIMIT), rows=[])
    lines = ['# CPU 표현 진단 실제 답', '', '관찰한 TEST 재사용 진단이며 새 blind 평가가 아닙니다.',
        'CPU/GPU 차이와 표현 효과를 분리합니다. 완료·부분 상태는 마지막 절과 report를 확인하세요.', '']
    def check():
        if utc_now() >= deadline or time.monotonic() >= end:
            raise BudgetExpired('절대 기한 또는 max-wall 도달')
    try:
        with wall_guard(min(a.max_wall_sec, (deadline - utc_now()).total_seconds())):
            check(); inputs = load_inputs(code); check()
            with cpu_runtime() as rt:
                tok = rt.Tokenizer.from_file(str(ROOT / TOKENIZER))
                stop = tok.encode('<|im_end|>').ids
                if not stop:
                    raise ValueError('정지 토큰 없음')
                for model in MODELS:
                    base = wrapper = None
                    try:
                        check()
                        if digest(inputs['checkpoints'][model]) != PINS[model]['checkpoint']:
                            raise ValueError('로드 직전 CP 변경')
                        base, cfg, device = rt.load_model(ckpt_path=inputs['checkpoints'][model], device='cpu', mtp_heads='off')
                        base.float().eval(); check()
                        if (str(device) != 'cpu' or cfg.max_seq_len < 1024 or cfg.mtp_aux
                                or any(p.device.type != 'cpu' or p.dtype != rt.torch.float32 for p in base.parameters())
                                or any(b.device.type != 'cpu' or (b.is_floating_point() and b.dtype != rt.torch.float32)
                                       for b in base.buffers())
                                or digest(inputs['checkpoints'][model]) != PINS[model]['checkpoint']):
                            raise ValueError('CPU/FP32/문맥/CP 조건 다름')
                        wrapper = rt.PrecisionForward(base, 'fp32_math')
                        originals = {}
                        for profile in PROFILES:
                            cell = cells[model, profile]
                            for case in inputs['cases']:
                                check(); source = case['source']; question = profile_question(case, profile)
                                messages = prompt_messages(source) if profile == 'ORIGINAL' else [dict(role='user', content=question)]
                                prompt = rt.serialize(dict(messages=messages), 'chatml', add_generation_prompt=True)
                                ids = tok.encode(prompt).ids
                                if not ids or len(ids) + MAX_NEW > 1024:
                                    raise ValueError('입력+출력 1024 초과: 자르지 않고 거부')
                                prefix = tok.decode(ids)
                                decoded, generation = rt.sample(wrapper, cfg, tok, prompt, max_new=MAX_NEW,
                                    temperature=0, top_k=1, use_cache=True, device='cpu', logits_last_only=True,
                                    return_metadata=True, stop_token_sequences=[stop], mtp_tokens=1)
                                check()
                                if not 0 <= generation['generated_tokens'] <= MAX_NEW:
                                    raise ValueError('생성 길이 계약 다름')
                                ok = decoded.startswith(prefix)
                                answer = decoded[len(prefix):].split('<|im_end|>', 1)[0] if ok else ''
                                gpu = inputs['gpu'][model][case['index']]
                                row = dict(model=model, profile=profile, index=case['index'], source=source,
                                    source_sha256=case['source_sha256'], root=source['meta']['root'], language=source['meta']['language'],
                                    original_question_sha256=source['meta']['question_sha256'], question=question,
                                    question_sha256=jsha(question), prompt_messages=messages, gold_value=source['meta']['gold_value'],
                                    final_line_requested=profile != 'CASUAL',
                                    answer=answer, raw_full_text=decoded, generation=generation,
                                    grading=surface_score(case, answer, model, ok), original_gpu_answer=gpu['answer'],
                                    original_gpu_grading=gpu.get('grading'),
                                    cpu_original_answer=answer if profile == 'ORIGINAL' else originals[case['index']],
                                    original_cpu_gpu_text_equal=(answer == gpu['answer']) if profile == 'ORIGINAL' and ok else None)
                                if profile == 'ORIGINAL':
                                    originals[case['index']] = answer
                                cell['writer'].append(row)
                                cell['writer']._file.flush()
                                os.fsync(cell['writer']._file.fileno())
                                cell['rows'].append(row)
                                lines += [f'## {model} / {profile} / 원 TEST index {case["index"]}', '',
                                    '### 질문', question, '', '### 기준 값', str(source['meta']['gold_value']), '',
                                    '### CPU 실제 답', answer or '[빈 답/입력 복구 실패]', '',
                                    '### 원 GPU 답과 CPU 원형 답', gpu['answer'], row['cpu_original_answer'], '',
                                    '### 분리된 기술 판독', json.dumps(row['grading'], ensure_ascii=False),
                                    '원형 CPU/GPU 문구 일치: ' + str(row['original_cpu_gpu_text_equal'])
                                    if profile == 'ORIGINAL' else '구어체 효과는 위 CPU 원형 답을 기준으로 따로 판독합니다.', '']
                    finally:
                        del wrapper, base
                        gc.collect()
            check()
            if any(digest(inputs['checkpoints'][m]) != PINS[m]['checkpoint'] for m in MODELS):
                raise ValueError('수집 중 CP 변경')
            status = 'CPU_SURFACE_COLLECTION_COMPLETE'; rc = 0
    except BaseException as exc:
        status = 'PARTIAL_DEADLINE' if isinstance(exc, BudgetExpired) else 'INTERRUPTED' if isinstance(exc, KeyboardInterrupt) else 'EXECUTION_ERROR'
        rc = 124 if isinstance(exc, BudgetExpired) else 130 if isinstance(exc, KeyboardInterrupt) else 9
        error = dict(type=type(exc).__name__, message=str(exc)[:1500])
    finally:
        summaries = []
        for (model, profile), cell in cells.items():
            rows = cell['rows']; manifest = cell['writer'].close(lineage=dict(schema=VERSION, model=model, profile=profile)) if rows else None
            if manifest:
                verify(cell['folder'], manifest)
            value = dict(schema=VERSION, model=model, profile=profile, expected_rows=8, rows=len(rows),
                status='CELL_COMPLETE' if len(rows) == 8 else 'PARTIAL' if rows else 'NOT_STARTED', raw_manifest=manifest,
                metrics=dict(strict_final_line_value_correct=sum(r['grading']['final_correct'] for r in rows),
                    bare_numeric_exact=sum(r['grading']['bare_numeric_exact'] for r in rows),
                    unambiguous_value_match=sum(r['grading']['content_value_status'] == 'EXACT_VALUE_MATCH' for r in rows),
                    unjudged_read_raw=sum(r['grading']['content_value_status'] == 'UNJUDGED_READ_RAW' for r in rows),
                    trace_valid=sum(r['grading']['trace_valid'] is True for r in rows),
                    training_style_policy_compliant=sum(r['grading']['policy_compliant'] for r in rows),
                    original_cpu_gpu_text_equal=sum(r['original_cpu_gpu_text_equal'] is True for r in rows)
                    if profile == 'ORIGINAL' else None),
                grading_scope='동결 학습 형식·정확 숫자·단계의 별도 진단. CASUAL의 형식 불일치는 내용 오답이 아님. 일반 문장은 원답 판독 필요')
            write_json(cell['folder'] / 'report.json', value); summaries.append(value)
        total = sum(c['rows'] for c in summaries)
        if total != 48 and rc == 0:
            status = 'EXECUTION_ERROR'; rc = 9
        report = dict(code, schema=VERSION, status=status, returncode=rc, error=error, expected_requests=48,
            completed_requests=total, cells=summaries, deadline=deadline.isoformat(), max_wall_sec=a.max_wall_sec,
            elapsed_sec=time.monotonic()-start, device='cpu', omp_threads=2, precision='FP32_MATH', mtp_inference=False,
            elapsed_scope='새 실행 namespace 생성 뒤 입장/모델/생성 구간. 초기 소스 검사와 최종 기록 직렬화는 별도',
            cache=True, max_new=MAX_NEW, temperature=0, training_updates=0, checkpoint_writes=0,
            inputs=inputs['receipt'] if inputs else None, selection=[dict(index=c['index'], root=c['source']['meta']['root'],
                language=c['source']['meta']['language'], source_sha256=c['source_sha256']) for c in inputs['cases']] if inputs else None,
            test_scope='OBSERVED_TEST_DIAGNOSTIC_NOT_BLIND', cpu_gpu_differences_are_not_surface_effect=True,
            hard_native_interrupt_guaranteed=False, quality_or_speed_adopted=False, review=str(review.relative_to(ROOT)))
        lines += ['## 수집 종료 상태', status, f'완료 요청: {total}/48', json.dumps(error, ensure_ascii=False)]
        body = '\n'.join(lines) + '\n'
        try:
            if len(body.encode()) >= LIMIT:
                raise ValueError('판독 문서 20MB 상한')
            with review.open('x', encoding='utf-8') as f:
                f.write(body)
        except (OSError, ValueError) as exc:
            report.update(status='EXECUTION_ERROR', returncode=9,
                review_error=dict(type=type(exc).__name__, message=str(exc)[:1000]))
            rc = 9
        write_json(target / 'report.json', report)
    return rc


def main(argv=None):
    a = arguments(argv); code = source_contract()
    if a.check_only:
        print(json.dumps(dict(code_sha256=code['code_sha256'], dependency_sha256=DEPENDENCY_SHA,
            status='SOURCE_ARGS_ONLY', scheduled_requests=48, model_loading='NOT_RUN'), ensure_ascii=False))
        return 0
    return execute(a, code)


if __name__ == '__main__':
    raise SystemExit(main())
