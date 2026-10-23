#!/usr/bin/env python3
"""입력 표현만 바꾸는 trace128 추가 팔. 실행·실자료 준비는 총괄 소유다.

check-only는 Python 소스만 읽고 torch/자료/토크나이저/CP를 열지 않는다.
기존 닫힌 통제군을 재학습하지 않는다. 새 ROOT 평가도 관측된 실패 뒤 설계한
사전동결 진단이며 독립 연구 확증·공식 벤치·일반 지능 증거가 아니다.
모든 실제 실행은 외부 timeout으로도 감싸야 한다. 부분 raw/CP의 존재는 완료가
아니며 adapter 영수증과 종료시각 검산이 모두 필요하다.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from contextlib import contextmanager
import copy
from datetime import datetime, timezone
import gc
import json
from pathlib import Path
import re
import signal
import sys
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts import diag_p101a_reasoning_surface_cpu as surface
from scripts import p106b_verified_trace_data as rules
from scripts.p106b_shards import ShardWriter, verify

VERSION = 'P101A_REASONING_SURFACE_BRIDGE_V1'
TAG = 'p101a_sft_mtp_reasoning_surface_bridge_v1_s1337'
CONTROL = 'p101a_sft_mtp_verified_trace_v3_s1337'
SELECTION_SEED = 20261022
QUOTAS = dict(addition=64, lookup=32, update=32)
PROFILES = ('STRUCTURED', 'UNSEEN_NATURAL', 'UNSEEN_NATURAL_FINAL')
MODEL_END = datetime.fromisoformat('2026-10-22T16:30:00+09:00')
USER_END = datetime.fromisoformat('2026-10-22T17:00:00+09:00')
OWN = ('scripts/p101a_reasoning_surface_bridge.py', 'scripts/test_p101a_reasoning_surface_bridge.py')
EXTRA = ('scripts/diag_p101a_reasoning_surface_cpu.py', 'scripts/p106b_education_followup.py',
         'scripts/p106b_gate_runtime.py', 'scripts/p106b_source_cleanup.py', 'scripts/train_sft_p090.py')

# 네 가지 TRAIN 문구와 한 가지 held-out 문구. 숫자에 한국어 조사를 붙이지 않는다.
ADDITION = {
    'ko': ('다음 두 수를 더해 주세요: {a}, {b}.', '덧셈을 해 주세요. 첫 수: {a}. 둘째 수: {b}.',
           '두 수의 합을 구해 주세요: {a}, {b}.', '이 두 수를 합해 주세요: {a}, {b}.',
           '계산을 부탁할게요. 첫 번째 수는 {a}, 두 번째 수는 {b}입니다. 둘을 합치면 얼마인가요?'),
    'en': ('Please add these two numbers: {a}, {b}.', 'Do an addition. First number: {a}. Second number: {b}.',
           'Find the sum of these numbers: {a}, {b}.', 'Add these values together: {a}, {b}.',
           'Could you work this out? The first number is {a} and the second is {b}. What is their total?')}
RECORD = {
    'ko': ('기록된 값을 읽어 주세요. {first}: {v0}; {second}: {v1}.', '두 항목의 기록입니다. {first}: {v0}; {second}: {v1}.',
           '이 값을 기억해 주세요. {first}: {v0}; {second}: {v1}.', '현재 기록은 다음과 같습니다. {first}: {v0}; {second}: {v1}.',
           '메모에 두 항목이 있어요. 먼저 {first}: {v0}, 그다음 {second}: {v1}입니다.'),
    'en': ('Read these recorded values. {first}: {v0}; {second}: {v1}.', 'Here are two entries. {first}: {v0}; {second}: {v1}.',
           'Keep these values in mind. {first}: {v0}; {second}: {v1}.', 'The current records are as follows. {first}: {v0}; {second}: {v1}.',
           'My note has two entries: first {first}: {v0}, then {second}: {v1}.')}
QUERY = {
    'ko': ('현재 값을 알려 주세요. 질문 대상: {asked}.', '지금 값을 구해 주세요. 대상 항목: {asked}.',
           '다음 항목의 현재 값은 얼마인가요? 항목: {asked}.', '기록에서 현재 값을 찾아 주세요. 대상: {asked}.',
           '제가 알고 싶은 항목은 {asked}입니다. 지금 그 항목에 적힌 값은 무엇인가요?'),
    'en': ('Give the current value. Requested entry: {asked}.', 'Find the value now. Entry to look up: {asked}.',
           'What is the current value of this entry: {asked}?', 'Look up the current value. Requested entry: {asked}.',
           'The entry I want to know about is {asked}. What value does that entry have now?')}
UPDATE = {
    'ko': ('한 번 변경합니다. 대상: {subject}; 새 값: {value}.', '기록 하나를 바꿉니다. 항목: {subject}; 새 값: {value}.',
           '다음 항목만 갱신합니다. 대상: {subject}; 변경 후 값: {value}.', '값을 한 번 고칩니다. 항목: {subject}; 새 값: {value}.',
           '그 뒤 메모를 한 번 고쳤어요. 변경한 항목: {subject}. 새로 적은 값: {value}.'),
    'en': ('Make one change. Entry: {subject}; new value: {value}.', 'Change one record. Entry: {subject}; new value: {value}.',
           'Update only this entry. Entry: {subject}; value after the change: {value}.', 'Revise one value. Entry: {subject}; new value: {value}.',
           'After that, I revised the note once: the value for entry {subject} is now {value}.')}


def source_contract():
    value = surface.source_contract()
    files = dict(value['code_files_sha256'])
    files.update({p: surface.digest(ROOT / p) for p in (*OWN, *EXTRA)})
    return dict(code_sha256=surface.jsha(files), code_files_sha256=files,
                frozen_dependency_sha256=value['dependency_sha256'])


def safe(path):
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError('연결 경로 금지')
    return path


def snapshot(paths):
    return {str(p.relative_to(ROOT)): surface.digest(p) for p in paths}


def unchanged(files):
    if any(surface.digest(ROOT / p) != h for p, h in files.items()):
        raise ValueError('봉인 입력/CP 바이트 변경')


def read_json(path):
    if surface.regular(path).stat().st_size >= surface.LIMIT:
        raise ValueError('JSON 20MB 미만 필요')
    return json.loads(path.read_text(encoding='utf-8'))


def check_time(a):
    deadline = datetime.fromisoformat(a.deadline.replace('Z', '+00:00'))
    end = USER_END if a.mode == 'prepare' else MODEL_END
    if (deadline.tzinfo is None or deadline.utcoffset() is None or deadline > end
            or not 1 <= a.max_wall_sec <= 7200 or (deadline - surface.utc_now()).total_seconds() < a.max_wall_sec):
        raise ValueError('현재 창 안의 aware deadline/max-wall 및 16:30 모델 종료 경계 필요')
    return deadline


def natural_question(row, template):
    if type(template) is not int or not 0 <= template <= 4:
        raise ValueError('동결 표현 0..4만 허용')
    m = row['meta']; task = m['task']; lang = m['language']; rules.checked_task(task)
    if task['family'] == 'addition':
        return ADDITION[lang][template].format(**task)
    p = m['presentation']; first = p['first_subject']; second = next(n for n in task['facts'] if n != first)
    record = RECORD[lang][template].format(first=first, second=second, v0=task['facts'][first], v1=task['facts'][second])
    query = QUERY[lang][template].format(asked=task['asked'])
    update = UPDATE[lang][template].format(**task['update']) if task['family'] == 'update' else ''
    return '\n'.join(s for s in ((query, record, update) if p['wording'] else (record, update, query)) if s)


def validate_row(row):
    m = row['meta']; task = m['task']; rules.checked_task(task)
    if (m['root'] != rules.canonical_root(task) or m['gold_value'] != rules.truth(task)
            or [x['role'] for x in row['messages']] != ['user', 'assistant']
            or m['question_sha256'] != rules.sha(surface.text(row['messages'][0]['content']))
            or not rules.score_response(task, surface.text(row['messages'][1]['content']), m['language'], 'trace')['policy_compliant']):
        raise ValueError('ROOT/질문/정답/trace 계약 다름')
    rules.validate_steps(task, rules.build_steps(task))


def bridge_rows(rows):
    """원본 순서를 유지하며 lane별 ROOT 정렬 후 홀수 순위만 치환한다."""
    lanes = defaultdict(list)
    for i, row in enumerate(rows):
        validate_row(row); m = row['meta']
        if surface.text(row['messages'][0]['content']).splitlines()[-1] != surface.FINAL_INSTRUCTION[m['language']]:
            raise ValueError('원 최종행 요구 그대로 보존 필요')
        lanes[m['family'], m['language']].append((m['root'], i))
    selected = {}
    for lane in lanes.values():
        ordered = sorted(lane)
        if len(ordered) % 2 or len({r for r, _ in ordered}) != len(ordered):
            raise ValueError('lane별 짝수 고유 ROOT 필요')
        selected.update({i: (rank // 2) % 4 for rank, (_, i) in enumerate(ordered) if rank % 2})
    result = []
    for i, original in enumerate(rows):
        row = copy.deepcopy(original); template = selected.get(i)
        if template is not None:
            q = natural_question(row, template) + '\n' + surface.text(original['messages'][0]['content']).splitlines()[-1]
            row['messages'][0]['content'] = q; row['meta']['question_sha256'] = rules.sha(q)
        row['meta']['surface_bridge'] = dict(original_row_sha256=rules.sha(original), train_template=template,
            original_question_sha256=original['meta']['question_sha256'], assignment='sorted_ROOT_odd_rank_per_family_language')
        validate_row(row); result.append(row)
    return result


def select_test(old_roots):
    """결과를 보지 않는 seed20261022 후보 순서; 독립 rank-bit 8셀."""
    rows = []; roots = []; consumed = {}
    for family, count in QUOTAS.items():
        strata = defaultdict(list); seen = set()
        for index, task in enumerate(rules._candidates(family, SELECTION_SEED, 50_000)):
            root = rules.canonical_root(task)
            if root in seen or root in old_roots or rules.is_reserved(task) or rules.split_for_root(root, 1337) != 'test':
                continue
            seen.add(root)
            stratum = sorted(task['facts'], key=task['facts'].get).index(task['update']['subject']) if family == 'update' else 0
            need = count // 2 if family == 'update' else count
            if len(strata[stratum]) < need:
                strata[stratum].append(task)
            if sum(map(len, strata.values())) == count:
                consumed[family] = index + 1; break
        if sum(map(len, strata.values())) != count:
            raise ValueError('새 TEST ROOT/변경 low-high 공급 부족; 축소 금지')
        for stratum in sorted(strata):
            for rank, task in enumerate(strata[stratum]):
                oriented = rules.oriented_task(task, bool(rank % 2))
                view = (rank // 2) % 2 + 2 * ((rank // 4) % 2)
                root = rules.canonical_root(task); roots.append(root)
                for lang in ('ko', 'en'):
                    base = rules.render_row(oriented, lang, 'trace', 'test', view)
                    for profile in PROFILES:
                        row = copy.deepcopy(base)
                        if profile != 'STRUCTURED':
                            q = natural_question(base, 4)
                            if profile.endswith('_FINAL'):
                                q += '\n' + surface.text(base['messages'][0]['content']).splitlines()[-1]
                            row['messages'][0]['content'] = q; row['meta']['question_sha256'] = rules.sha(q)
                        row['meta']['surface_profile'] = profile
                        row['meta']['row_id'] = rules.sha([VERSION, root, lang, profile, view])
                        row['meta']['selection'] = dict(seed=SELECTION_SEED, rank=rank, update_canonical_stratum=stratum)
                        validate_row(row); rows.append(row)
    structured = [r for r in rows if r['meta']['surface_profile'] == 'STRUCTURED']
    summary = rules.presentation_summary(structured)
    for family in ('lookup', 'update'):
        for lang in ('ko', 'en'):
            c = summary[family + ':' + lang]; n = QUOTAS[family]
            keys = ['asked=A', 'asked=B', 'first_subject=A', 'first_subject=B', 'raw_A_lt_B=True', 'raw_A_lt_B=False']
            if family == 'update':
                keys += ['target_updated=True', 'target_updated=False', 'answer_changed=True', 'answer_changed=False']
            joint = [f'joint:orientation={o}:asked={a}:first={f}' for o in (True, False) for a in ('A', 'B') for f in ('A', 'B')]
            if any(c.get(k, 0) != n // 2 for k in keys) or any(c.get(k, 0) != n // 8 for k in joint):
                raise ValueError('독립 보기 균형 실패')
    if len(roots) != 128 or len(set(roots)) != 128 or set(roots) & set(old_roots) or len(rows) != 768:
        raise ValueError('새128ROOT/768행/겹침0 계약 실패')
    return rows, dict(roots=roots, roots_sha256=rules.sha(roots), rows_sha256=rules.sha(rows), candidates_consumed=consumed,
        presentation_counts=summary, shortcut_baselines=rules.shortcut_baselines(structured), selection_seed=SELECTION_SEED,
        scope='PRE_FROZEN_NEW_ROOT_DIAGNOSTIC_DESIGNED_AFTER_OBSERVED_FAILURE_NOT_INDEPENDENT_CONFIRMATION')


def original_inputs(code):
    from scripts import diag_p101a_sft_mtp as engine
    from scripts.p101a_sft_mtp_data import stream_rows
    corpus, evidence = engine.paths(CONTROL); train_path = evidence / 'parent_ntp/report.json'
    pin = surface.PINS['trace']
    if surface.digest(corpus / 'report.json') != pin['corpus'] or surface.digest(train_path) != pin['report']:
        raise ValueError('닫힌 trace 원자료/학습 report SHA 다름')
    report = engine.corpus_report(corpus); trained = read_json(train_path)
    if (trained['status'] != 'SFT_MTP_TRAINED_EVAL_PENDING' or not trained['checkpoint_saved']
            or trained['updates'] != 128 or trained['assistant_targets'] != 512464
            or trained['parent_sha256'] != engine.PARENT_SHA or trained['tokenizer_sha256'] != surface.TOK_SHA
            or trained['corpus_sha256'] != pin['corpus'] or trained['checkpoint_sha256'] != pin['checkpoint']
            or report.get('preparation_schema') != 'P101A_CLEAN_BILINGUAL_PREPARATION_V3'):
        raise ValueError('기존 통제군의 닫힌128회/지도량/부모 계보 다름')
    if any(code['code_files_sha256'].get(k) != v for k, v in trained['code_sha256'].items()):
        raise ValueError('원 학습 당시 engine/core 바이트 다름')
    paths = [corpus / 'report.json', train_path]
    for manifest in report['manifests'].values():
        paths.extend(corpus / s['path'] for s in manifest['shards'])
    files = snapshot(paths)
    datasets = {s: list(stream_rows(corpus, report['manifests'][s])) for s in ('train', 'val', 'test')}
    roots = {r['meta']['root'] for group in datasets.values() for r in group}
    if len(datasets['train']) != 4096 or any(len(datasets[s]) != 1024 for s in ('val', 'test')) or len(roots) != 4352:
        raise ValueError('원 TRAIN4096/DEV128ROOT/TEST128ROOT 필요')
    for group in datasets.values():
        for row in group:
            validate_row(row)
    unchanged(files)
    return datasets, report, trained, files


def prepare(a, code):
    from scripts import diag_p101a_sft_mtp as engine
    from scripts import diag_p101a_clean_bilingual as clean
    from tinylm.chat.canonical import normalize, validate
    from tokenizers import Tokenizer
    datasets, old_report, old_train, files = original_inputs(code)
    corpus, _ = engine.paths(TAG); safe(corpus)
    if corpus.exists():
        raise FileExistsError('새 corpus 덮어쓰기 금지')
    if surface.digest(ROOT / surface.TOKENIZER) != surface.TOK_SHA:
        raise ValueError('토크나이저 SHA 다름')
    files[surface.TOKENIZER] = surface.TOK_SHA
    tok = Tokenizer.from_file(str(ROOT / surface.TOKENIZER))
    train = bridge_rows(datasets['train'])
    test, selection = select_test({r['meta']['root'] for group in datasets.values() for r in group})
    prepared = {'train': train, 'val': datasets['val'], 'test': test}
    manifests = {}; counts = {}; canonical_test = []; corpus.mkdir(parents=True, exist_ok=False)
    for split, rows in prepared.items():
        writer = ShardWriter(corpus, split, limit=surface.LIMIT); total = Counter()
        for i, row in enumerate(rows):
            row = validate(normalize(copy.deepcopy(row))); rec = clean.masked_record(row, tok)
            if split == 'test':
                canonical_test.append(row)
            if split == 'train':
                old = datasets['train'][i]; before = clean.masked_record(old, tok)
                assert_same_supervision(old, row, before, rec)
            writer.append(row); total.update(rows=1, x_tokens=rec.x_tokens, assistant_targets=rec.targets)
        manifests[split] = writer.close(lineage=dict(schema=VERSION, split=split, original_inputs_sha256=files))
        verify(corpus, manifests[split]); counts[split] = dict(total)
    if counts['train']['assistant_targets'] * 4 != 512464 or old_report['counts']['train']['assistant_targets'] * 4 != 512464:
        raise ValueError('동일 누적512464 targets 필수')
    selection['canonical_rows_sha256'] = rules.sha(canonical_test)
    unchanged(files)
    report = dict(schema=engine.data.VERSION, preparation_schema=VERSION, status='CORPUS_READY', tag=TAG,
        tokenizer_sha256=surface.TOK_SHA, epochs=4, manifests=manifests, counts=counts,
        actual_unique_train_x_tokens=counts['train']['x_tokens'], target_processed_x_tokens=4*counts['train']['x_tokens'],
        learning_updates=128, four_pass_assistant_targets=512464, padded_slots=128*8*16*1024,
        original_unique_train_x_tokens=old_report['actual_unique_train_x_tokens'],
        initial_core_sha256=old_train['initial_core_sha256'], parent_sha256=old_train['parent_sha256'],
        original_inputs_sha256=files, original_control=dict(tag=CONTROL, **surface.PINS['trace']), selection=selection,
        code_sha256=code['code_files_sha256'], code_contract_sha256=code['code_sha256'], formal_train_ready=False,
        independent_variable='50% user-expression replacement only; input x differs; assistant target exposure identical',
        assignment='sorted_ROOT_odd_rank_per_family_language', train_templates_sha256=rules.sha([ADDITION, RECORD, QUERY, UPDATE]),
        adapter_differences=['new source/deadline/initial-core gates', 'clean encoded/optimizer factory reused',
                             'separate CPU surface evaluator on new pre-frozen ROOTs'],
        semantic_quality='PROCEDURAL_CODE_CHECKED_NOT_GENERAL_INTELLIGENCE', universal_wrong_turn_exclusion_claim=False)
    surface.write_json(corpus / 'report.json', report)
    return dict(corpus_sha256=surface.digest(corpus / 'report.json'), counts=counts, selection=selection)


def assert_same_supervision(old, row, before, after):
    if (surface.text(row['messages'][1]['content']) != surface.text(old['messages'][1]['content'])
            or [(y, s) for y, s in zip(after.y, after.segments) if y != -100]
            != [(y, s) for y, s in zip(before.y, before.segments) if y != -100]):
        raise ValueError('assistant 원문/shift된 h1 target 또는 owner 변경')


def receipt(evidence, mode):
    return evidence / ('adapter_' + mode) / 'report.json'


def require_receipt(evidence, mode, code):
    value = read_json(receipt(evidence, mode))
    end = datetime.fromisoformat(value['finished_at'])
    deadline = datetime.fromisoformat(value['deadline'])
    if (value['status'] != 'ADAPTER_COMPLETE' or value['returncode'] != 0 or value['mode'] != mode
            or value['code_sha256'] != code['code_sha256'] or end.tzinfo is None or deadline.tzinfo is None or end >= deadline
            or deadline > (USER_END if mode == 'prepare' else MODEL_END)):
        raise ValueError('동일 코드·기한 내 adapter 완료 영수증 필요')
    return value


def prepared_inputs(code):
    from scripts import diag_p101a_sft_mtp as engine
    corpus, evidence = engine.paths(TAG); prep = require_receipt(evidence, 'prepare', code)
    report = engine.corpus_report(corpus)
    if (report['preparation_schema'] != VERSION or report['code_contract_sha256'] != code['code_sha256']
            or report['code_sha256'] != code['code_files_sha256'] or report['four_pass_assistant_targets'] != 512464
            or surface.digest(corpus / 'report.json') != prep['result']['corpus_sha256']):
        raise ValueError('같은 새 코드/자료/지도량 필요')
    unchanged(report['original_inputs_sha256'])
    return corpus, evidence, report


def corpus_snapshot(corpus, report):
    return snapshot([corpus / 'report.json', ROOT / surface.TOKENIZER,
        *(corpus / s['path'] for manifest in report['manifests'].values() for s in manifest['shards'])])


def remaining_seconds(a):
    return min(a.max_wall_sec, a._end_monotonic-time.monotonic(),
               (datetime.fromisoformat(a.deadline)-surface.utc_now()).total_seconds())


@contextmanager
def bounded_engine_wall(a, gate=None):
    """원 guard를 실제 호출하되 전체 입장/준비에 쓴 시간을 다시 주지 않는다."""
    if gate is None:
        from scripts import p106b_gate_runtime as gate
    original = gate.wall_limit
    @contextmanager
    def narrowed(seconds):
        budget = int(min(seconds, remaining_seconds(a)))
        if budget < 1:
            raise surface.BudgetExpired('남은 정수초0: 모델 호출 금지')
        if budget < 60:
            raise surface.BudgetExpired('기존 guard의 최소60초보다 남은 전체 창이 작음')
        try:
            with original(budget):
                yield
        finally:
            # 원 guard가 해제한 바깥 alarm을 실제 남은 시간으로만 복원한다.
            signal.setitimer(signal.ITIMER_REAL, max(.001, remaining_seconds(a)))
    with patch.object(gate, 'wall_limit', narrowed):
        yield


def train(a, code):
    from scripts import diag_p101a_sft_mtp as engine
    from scripts import diag_p101a_clean_bilingual as clean
    if not hasattr(a, '_end_monotonic'):
        raise ValueError('전체 실행 예산 envelope 필요')
    corpus, evidence, report = prepared_inputs(code)
    watched = dict(report['original_inputs_sha256'], **corpus_snapshot(corpus, report))
    watched.update(snapshot([engine.PARENT]))
    if a.mode == 'train':
        prior = require_receipt(evidence, 'calibrate', code)
        cost = read_json(engine.report_path(evidence, 'parent_ntp', True))
        if (cost['status'] != 'COST_CALIBRATION_COMPLETE' or cost['updates'] != 32
                or cost['code_sha256'] != code['code_files_sha256'] or cost['corpus_sha256'] != surface.digest(corpus / 'report.json')
                or surface.digest(engine.report_path(evidence, 'parent_ntp', True)) != prior['result']['engine_report_sha256']):
            raise ValueError('이 새 코드/자료의 exact cost32 필요')
        estimate = max(cost['estimated_full_update_sec'], cost['whole_wall_sec'] + 96*max(cost['update_seconds'][1:]))
        if a.reserve_sec is None or a.reserve_sec < 0 or estimate + a.reserve_sec > a.max_wall_sec:
            raise ValueError('실측 cost32+명시 보수 reserve가 max-wall 안에 들어야 함')
    else:
        estimate = None
    base_runtime = engine.load_runtime
    def runtime(arm):
        loaded = base_runtime(arm)
        if loaded[4] != report['initial_core_sha256'] or loaded[2].mtp_aux or not loaded[2].grad_checkpoint:
            raise ValueError('동일 초기 core/ckptON/MTPoff 필요')
        return loaded
    def encoded(c, r, tok):
        records = clean.encoded(c, r, tok)
        if (len(records['train']) != 4096 or sum(v.targets for v in records['train'])*4 != 512464
                or sum(v.x_tokens for v in records['train']) != r['actual_unique_train_x_tokens']):
            raise ValueError('동일4096/512464 실제 label 분모 필요')
        return records
    metadata = engine.info(a)
    metadata.update(preparation_schema=VERSION, code_sha256=code['code_files_sha256'], lr=5e-5, muon_lr=2e-4,
        unique_train_x_target=report['actual_unique_train_x_tokens'], processed_x_target_approx=report['target_processed_x_tokens'],
        initial_core_expected_sha256=report['initial_core_sha256'], independent_variable=report['independent_variable'],
        original_control=report['original_control'], adapter_completion_receipt_required=True,
        mtp_aux=False, active_training_horizons=[1], semantic_quality=report['semantic_quality'],
        predicted_train_sec=estimate, explicit_reserve_sec=a.reserve_sec,
        estimate_scope='cost32 measured training path; full before/after probes/export remain unmeasured, not a wall guarantee')
    with bounded_engine_wall(a), patch.object(clean, 'ORIGINAL_OPTIMIZERS', engine.optimizers), patch.object(engine, 'optimizers', clean.optimizers), \
         patch.object(engine, 'encoded', encoded), patch.object(engine, 'load_runtime', runtime):
        rc = engine.train_arm(a, corpus, evidence, metadata, calibrate=a.mode == 'calibrate', epochs=4)
    result_path = engine.report_path(evidence, 'parent_ntp', a.mode == 'calibrate'); result = read_json(result_path)
    if (rc != 0 or result['updates'] != (32 if a.mode == 'calibrate' else 128)
            or result['assistant_targets'] != (128116 if a.mode == 'calibrate' else 512464)
            or result['status'] != ('COST_CALIBRATION_COMPLETE' if a.mode == 'calibrate' else 'SFT_MTP_TRAINED_EVAL_PENDING')
            or result['checkpoint_saved'] != (a.mode == 'train')
            or result['initial_core_sha256'] != report['initial_core_sha256']):
        raise ValueError('실제 업데이트/감독량/초기화 종료 검산 실패')
    unchanged(watched)
    return dict(engine_report_sha256=surface.digest(result_path), updates=result['updates'], assistant_targets=result['assistant_targets'])


def evaluation_inputs(a, code):
    from scripts import diag_p101a_sft_mtp as engine
    from scripts.p101a_sft_mtp_data import stream_rows
    corpus, evidence, report = prepared_inputs(code)
    if a.model == 'control':
        _, _, trained, _ = original_inputs(code)
        cp = engine.checkpoint(CONTROL, 'parent_ntp'); expected = surface.PINS['trace']['checkpoint']
        trained_sha = surface.PINS['trace']['report']
    else:
        train_receipt = require_receipt(evidence, 'train', code)
        path = engine.report_path(evidence, 'parent_ntp'); trained = read_json(path); cp = engine.checkpoint(TAG, 'parent_ntp')
        trained_sha = surface.digest(path); expected = trained['checkpoint_sha256']
        if (trained_sha != train_receipt['result']['engine_report_sha256'] or trained['updates'] != 128
                or trained['assistant_targets'] != 512464 or trained['corpus_sha256'] != surface.digest(corpus / 'report.json')
                or trained['status'] != 'SFT_MTP_TRAINED_EVAL_PENDING' or not trained['checkpoint_saved']):
            raise ValueError('같은 완성 새 학생 CP 필요')
    if (trained['initial_core_sha256'] != report['initial_core_sha256'] or surface.digest(cp) != expected
            or surface.digest(ROOT / surface.TOKENIZER) != surface.TOK_SHA):
        raise ValueError('실물 CP/초기 core/토크나이저 계보 다름')
    rows = list(stream_rows(corpus, report['manifests']['test']))
    if len(rows) != 768 or rules.sha(rows) != report['selection']['canonical_rows_sha256']:
        raise ValueError('동결768행 다름')
    return rows, cp, dict(checkpoint_sha256=expected, trained_report_sha256=trained_sha,
        corpus_sha256=surface.digest(corpus / 'report.json'), initial_core_sha256=report['initial_core_sha256'],
        tokenizer_sha256=surface.TOK_SHA, test_manifest=report['manifests']['test'], selection=report['selection'],
        original_inputs_sha256=report['original_inputs_sha256'], input_files_sha256=corpus_snapshot(corpus, report))


def evaluate(a, code, folder):
    from scripts.diag_p101a_clean_eval import prompt_messages
    rows, cp, identity = evaluation_inputs(a, code)
    writer = ShardWriter(folder, 'first_answers', limit=surface.LIMIT)
    summaries = defaultdict(Counter); reviews = defaultdict(list); started = time.monotonic(); error = None
    status = 'PARTIAL'; count = 0
    try:
        with surface.cpu_runtime() as rt:
            tok = rt.Tokenizer.from_file(str(ROOT / surface.TOKENIZER)); stop = tok.encode('<|im_end|>').ids
            if not stop:
                raise ValueError('종료 토큰 없음')
            base, cfg, device = rt.load_model(ckpt_path=cp, device='cpu', mtp_heads='off')
            base.float().eval()
            if (str(device) != 'cpu' or cfg.max_seq_len < 1024 or cfg.mtp_aux
                    or any(p.device.type != 'cpu' or p.dtype != rt.torch.float32 for p in base.parameters())
                    or any(b.device.type != 'cpu' or (b.is_floating_point() and b.dtype != rt.torch.float32) for b in base.buffers())):
                raise ValueError('CPU FP32/문맥/MTPoff 다름')
            model = rt.PrecisionForward(base, 'fp32_math')
            for index, row in enumerate(rows):
                if surface.utc_now() >= datetime.fromisoformat(a.deadline):
                    raise surface.BudgetExpired('절대 기한 도달')
                prompt = rt.serialize(dict(messages=prompt_messages(row)), 'chatml', add_generation_prompt=True)
                ids = tok.encode(prompt).ids
                if not ids or len(ids) + 128 > 1024:
                    raise ValueError('1024 문맥 초과; 축소/대체 금지')
                tick = time.monotonic(); prefix = tok.decode(ids)
                decoded, generation = rt.sample(model, cfg, tok, prompt, max_new=128, temperature=0, top_k=1,
                    use_cache=True, device='cpu', logits_last_only=True, return_metadata=True,
                    stop_token_sequences=[stop], mtp_tokens=1)
                if not 0 <= generation['generated_tokens'] <= 128:
                    raise ValueError('생성 토큰 계약 다름')
                ok = decoded.startswith(prefix); answer = decoded[len(prefix):].split('<|im_end|>', 1)[0] if ok else ''
                grading = surface.surface_score(dict(source=row), answer, 'trace', ok)
                m = row['meta']; key = (m['surface_profile'], m['language'])
                value = dict(index=index, model=a.model, source=row, source_sha256=rules.sha(row), answer=answer,
                    raw_full_text=decoded, generation=generation, grading=grading, input_tokens=len(ids), elapsed_sec=time.monotonic()-tick)
                writer.append(value); writer._file.flush(); count += 1
                summaries[key].update(rows=1, strict_final_value=grading['final_correct'], bare_numeric_exact=grading['bare_numeric_exact'],
                    unjudged=grading['content_value_status'] == 'UNJUDGED_READ_RAW', extraction_failed=not ok,
                    trace_valid=grading['trace_valid'] is True, ended=generation['finish_reason'] in ('STOP_SEQUENCE', 'EOS'))
                reviews[key].extend([f'## index {index} / ROOT {m["root"]}', '', '### 질문', surface.text(row['messages'][0]['content']),
                    '', '### 기준 trace', surface.text(row['messages'][1]['content']), '', '### 첫 실제 답', answer or '[빈 답/추출 실패]',
                    '', '### 종료·별도 진단', json.dumps(generation, ensure_ascii=False), json.dumps(grading, ensure_ascii=False), ''])
                if count % 32 == 0:
                    elapsed = time.monotonic()-started
                    print('[BRIDGE_CPU_PROGRESS] ' + json.dumps(dict(model=a.model, completed=count, total=768,
                        elapsed_sec=elapsed, linear_full_sec=elapsed/count*768, estimate_not_guarantee=True)), flush=True)
    except BaseException as exc:
        error = exc
    finally:
        manifest = writer.close(lineage=dict(schema=VERSION, model=a.model, **identity)) if count else None
        if manifest:
            verify(folder, manifest)
        if error is None:
            try:
                unchanged(identity['original_inputs_sha256']); unchanged(identity['input_files_sha256'])
                if count != 768 or surface.digest(cp) != identity['checkpoint_sha256']:
                    raise ValueError('CP/768 원답 종료 검산 실패')
                if surface.utc_now() >= datetime.fromisoformat(a.deadline):
                    raise surface.BudgetExpired('평가 종료 검산 중 기한 도달')
                status = 'CPU_FIRST_ANSWER_COLLECTION_COMPLETE'
            except BaseException as exc:
                error = exc
        review_paths = []
        for (profile, lang), lines in reviews.items():
            path = safe(ROOT / 'review_request' / f'20261022_reasoning_bridge_{a.run_id}_{a.model}_{profile.lower()}_{lang}.md')
            body = '# 사전동결 새 ROOT 표현 진단: 실제 첫 답\n\n일반 지능/독립 확증/공식 벤치가 아닙니다. 숫자·형식·미판독을 분리합니다.\n\n' + '\n'.join(lines)
            if len(body.encode()) >= surface.LIMIT:
                raise ValueError('분리된 검수 문서 20MB 미만 필요')
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open('x', encoding='utf-8') as stream:
                stream.write(body)
            review_paths.append(str(path.relative_to(ROOT)))
        surface.write_json(folder / 'collection.json', dict(identity, status=status, completed=count, expected=768,
            raw_manifest=manifest, summaries={':'.join(k): dict(v) for k, v in summaries.items()}, reviews=review_paths,
            precision='FP32_MATH_TF32_OFF', cache=True, retries=0, max_new=128, mtp_inference=False,
            error=None if error is None else dict(type=type(error).__name__, message=str(error)[:1000])))
        gc.collect()
    if error:
        raise error
    return dict(completed=count, collection_sha256=surface.digest(folder / 'collection.json'), **identity)


def execute(a, code):
    from scripts import diag_p101a_sft_mtp as engine
    _, evidence = engine.paths(TAG)
    folder = safe(evidence / ('adapter_' + (f'evaluate_{a.model}_{a.run_id}' if a.mode == 'evaluate' else a.mode)))
    deadline = check_time(a)
    started = time.monotonic(); a._end_monotonic = started+a.max_wall_sec
    folder.mkdir(parents=True, exist_ok=False)
    result = None; error = None; rc = 9
    try:
        with surface.wall_guard(a.max_wall_sec):
            result = prepare(a, code) if a.mode == 'prepare' else train(a, code) if a.mode in ('calibrate', 'train') else evaluate(a, code, folder)
            if surface.utc_now() >= deadline or time.monotonic()-started >= a.max_wall_sec:
                raise surface.BudgetExpired('완료 직전 시간 재검산 실패')
            if source_contract() != code:
                raise ValueError('완료 직전 소스 재검산 실패')
            rc = 0
    except BaseException as exc:
        error = dict(type=type(exc).__name__, message=str(exc)[:1500])
        rc = 124 if isinstance(exc, surface.BudgetExpired) else 130 if isinstance(exc, KeyboardInterrupt) else 8 if isinstance(exc, (FileNotFoundError, FileExistsError)) else 9
    finished = surface.utc_now()
    if rc == 0 and finished >= deadline:
        rc = 124; error = dict(type='BudgetExpired', message='최종 영수증 직전 기한 초과')
    surface.write_json(folder / 'report.json', dict(schema=VERSION, mode=a.mode, model=a.model, code_sha256=code['code_sha256'],
        status='ADAPTER_COMPLETE' if rc == 0 else 'PARTIAL_OR_FAILED', returncode=rc, result=result, error=error,
        deadline=deadline.isoformat(), max_wall_sec=a.max_wall_sec, finished_at=finished.isoformat(),
        elapsed_sec=time.monotonic()-started, external_timeout_required=True, completion_requires_this_receipt=True,
        wall_scope='namespace/실자료 해시/준비·tokenizer·인코딩/model/학습·평가·CP/종료검산 포함; CLI·초기 source-only hash 및 최종 JSON 직렬화 제외'))
    return rc


def arguments(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mode', required=True, choices=('prepare', 'calibrate', 'train', 'evaluate'))
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument('--check-only', action='store_true'); g.add_argument('--execute', action='store_true')
    p.add_argument('--deadline', required=True); p.add_argument('--max-wall-sec', required=True, type=int)
    p.add_argument('--code-sha256'); p.add_argument('--reserve-sec', type=int)
    p.add_argument('--model', choices=('control', 'bridge')); p.add_argument('--run-id', default='first')
    a = p.parse_args(argv); a.tag = TAG; a.arm = 'parent_ntp'
    if not re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,31}', a.run_id) or (a.mode == 'evaluate') != bool(a.model):
        raise ValueError('안전 run-id 및 evaluate에만 명시 control/bridge 필요')
    if a.execute and not re.fullmatch(r'[A-Fa-f0-9]{64}', a.code_sha256 or ''):
        raise ValueError('실행에는 검토한 소스 SHA 필요')
    check_time(a)
    return a


def main(argv=None):
    a = arguments(argv); code = source_contract()
    if a.check_only:
        print(json.dumps(dict(code, status='SOURCE_ARGS_ONLY', asset_reads=0, torch_imports=0, train_updates=128,
            test_rows_per_model=768, cumulative_assistant_targets=512464, actual_model_execution='NOT_RUN'), ensure_ascii=False))
        return 0
    if a.code_sha256.upper() != code['code_sha256']:
        raise ValueError('검토한 코드 SHA와 실행 소스 다름')
    return execute(a, code)


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (FileNotFoundError, FileExistsError) as exc:
        print('[HOLD] ' + str(exc)); raise SystemExit(8)
