#!/usr/bin/env python3
"""Single-turn first-answer comparison using the unchanged strict research UI.

Local UTF-8 JSONL: id, language(ko/en), category, question, expected_exact(null
or a caller-supplied code-defined short answer). Open explanations are never
automatically graded. No downloads; learned models run only with --execute.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from scripts import interactive_research_infer as ui
from scripts import p106b_minimal_pair_benchmark as common
from scripts.p106b_shards import ShardWriter, verify

SCHEMA = 'P106B_SINGLE_TURN_CHAT_PROBE_BATCH_V1'
MODELS = tuple(spec.name for spec in ui.MODELS)
FIELDS = ('id', 'language', 'category', 'question', 'expected_exact')
LIMIT = 19_999_999
CODE = ('scripts/p106b_chat_probe_batch.py', 'scripts/test_p106b_chat_probe_batch.py',
        'scripts/p106b_minimal_pair_benchmark.py', 'scripts/interactive_research_infer.py',
        'scripts/p106b_shards.py', 'tinylm/chat/serialize.py')


def validate_questions(rows):
    if not isinstance(rows, list) or not rows: raise ValueError('nonempty explicit question batch required')
    seen = set()
    for row in rows:
        if (not isinstance(row, dict) or set(row) != set(FIELDS)
                or any(not isinstance(row[k], str) or not row[k].strip() for k in FIELDS[:-1])
                or row['language'] not in ('ko', 'en')
                or (row['expected_exact'] is not None
                    and (not isinstance(row['expected_exact'], str) or not row['expected_exact'].strip()))):
            raise ValueError('exact id/language/category/question/nullable expected_exact schema required')
        if row['id'] in seen: raise ValueError('duplicate question id')
        seen.add(row['id'])
    return True


def load_questions(path, root=ROOT):
    path = common.safe_path(path, root); rows = []; digest = hashlib.sha256()
    with path.open('rb') as stream:
        before = os.fstat(stream.fileno())
        for line in stream:
            if not line.strip() or len(line) > LIMIT: raise ValueError('blank/oversized question row')
            digest.update(line)
            rows.append(json.loads(line.decode('utf-8'), object_pairs_hook=common._unique_object))
        after = os.fstat(stream.fileno())
    stamp = lambda value: (value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns)
    if stamp(before) != stamp(after) or stamp(after) != stamp(path.stat()): raise ValueError('question file changed while reading')
    validate_questions(rows)
    return rows, dict(path=str(path.relative_to(Path(root).absolute())), bytes=after.st_size,
        sha256=digest.hexdigest().upper(), questions_sha256=common.sha(rows), count=len(rows),
        expected_authority='CALLER_SUPPLIED_CODE_DEFINED; not independently certified by this tool')


def question_proofs(rows, tokenizer, max_new):
    from tinylm.chat.serialize import serialize
    validate_questions(rows)
    if type(max_new) is not int or not 1 <= max_new <= 1024: raise ValueError('explicit generation1..1024 required')
    proofs = []
    for row in rows:
        prompt = serialize(dict(messages=ui.prompt_messages(row['question'], ())), 'chatml', add_generation_prompt=True)
        ids = list(tokenizer.encode(prompt).ids)
        if (not ids or any(type(i) is not int or i < 0 for i in ids) or len(ids) + max_new > 1024):
            raise ValueError('complete prompt plus generation must fit1024; no automatic truncation')
        proofs.append(dict(id=row['id'], prompt_sha256=hashlib.sha256(prompt.encode('utf-8')).hexdigest().upper(),
            prompt_tokens=len(ids), prompt_ids_sha256=common.sha(ids), actual_history=False))
    return proofs


def whitespace_diagnostic(answer, expected):
    if not isinstance(answer, str): raise ValueError('preserve even an empty actual answer string')
    if expected is None: return dict(status='HUMAN_REVIEW_REQUIRED', whitespace_exact=None)
    return dict(status='CODE_DEFINED_STRING_DIAGNOSTIC_ONLY',
        whitespace_exact=' '.join(answer.split()) == ' '.join(expected.split()),
        normalization='collapse whitespace and strip only; case/punctuation/signs/decimal preserved')


def validate_generation(meta, proof, max_new):
    if not isinstance(meta, dict): raise ValueError('actual UI generation receipt required')
    ids = meta.get('generated_ids'); count = meta.get('generated_tokens'); reason = meta.get('finish_reason')
    if (type(count) is not int or not 1 <= count <= max_new or not isinstance(ids, list) or len(ids) != count
            or any(type(i) is not int or i < 0 for i in ids)
            or meta.get('prompt_tokens') != proof['prompt_tokens'] or meta.get('prompt_sha256') != proof['prompt_sha256']
            or meta.get('precision') != 'FP32_MATH' or meta.get('tf32') is not False
            or meta.get('actual_history') is not False or meta.get('mtp') is not False
            or meta.get('use_cache') is not True or meta.get('temperature') != 0. or meta.get('top_k') != 1
            or meta.get('terminal_only_removed') is not True):
        raise ValueError('single-turn prompt/FP32/greedy/raw token receipt differs')
    if reason == 'STOP_SEQUENCE':
        terminal = [4]
        if meta.get('matched_stop_sequence') != terminal: raise ValueError('EOT receipt differs')
    elif reason == 'EOS':
        terminal = [2]
        if meta.get('matched_stop_sequence') is not None: raise ValueError('EOS receipt differs')
    elif reason == 'MAX_NEW' and count == max_new and meta.get('matched_stop_sequence') is None:
        terminal = []
    else: raise ValueError('unknown or incomplete finish reason')
    content = ids[:-1] if terminal else ids
    if (meta.get('terminal_ids') != terminal or terminal and ids[-1:] != terminal
            or any(i in (2, 4) for i in content) or meta.get('content_tokens') != len(content)):
        raise ValueError('actual content/terminal IDs differ')
    return True


def event_for(row, proof, answer, generation, seconds, max_new):
    if proof['id'] != row['id']: raise ValueError('question/prompt identity differs')
    if type(seconds) not in (int, float) or not math.isfinite(seconds) or seconds < 0: raise ValueError('finite timing required')
    validate_generation(generation, proof, max_new)
    return dict(id=row['id'], source=copy.deepcopy(row), source_sha256=common.sha(row),
        proof=copy.deepcopy(proof), answer=answer, generation=copy.deepcopy(generation), seconds=seconds,
        diagnostic=whitespace_diagnostic(answer, row['expected_exact']), first_answer_only=True)


def summarize(events, rows, proofs, max_new):
    validate_questions(rows)
    if len(events) != len(rows) or len(proofs) != len(rows): raise ValueError('complete first answers required; no zero filling')
    cells = defaultdict(Counter); seen = set()
    for event, row, proof in zip(events, rows, proofs):
        expected = event_for(row, proof, event.get('answer'), event.get('generation'), event.get('seconds'), max_new)
        if event != expected or row['id'] in seen: raise ValueError('ordered raw answer/source/diagnostic changed')
        seen.add(row['id']); cell = cells[row['language'] + '|' + row['category']]
        cell.update(responses=1, generated_tokens=event['generation']['generated_tokens'],
            empty_answers=int(not event['answer'].strip()), seconds=event['seconds'])
        cell['finish_' + event['generation']['finish_reason']] += 1
        if row['expected_exact'] is None: cell['human_review_required'] += 1
        else: cell.update(code_defined_diagnostics=1, whitespace_exact=int(event['diagnostic']['whitespace_exact']))
    total = Counter()
    for cell in cells.values(): total.update(cell)
    return dict(responses=len(events), counts=dict(total), by_language_category={k: dict(v) for k, v in sorted(cells.items())},
        dialogue_turns=1, history_carried_between_questions=False, open_answer_semantic_quality='NOT_AUTOMATICALLY_ADJUDICATED',
        exact_scope='caller code-defined short strings only; not semantic quality or an overall chat accuracy',
        training_updates=0, checkpoint_writes=0)


def collect_batch(output, rows, proofs, lineage, emit, max_new=128, root=ROOT):
    validate_questions(rows)
    if len(proofs) != len(rows) or [p['id'] for p in proofs] != [r['id'] for r in rows]:
        raise ValueError('complete ordered question-only prompt proofs required before generation')
    output = common.safe_path(output, root); output.mkdir(parents=True, exist_ok=False)
    writer = ShardWriter(output, 'answers', limit=LIMIT); events = []
    try:
        for row, proof in zip(rows, proofs):
            tick = time.perf_counter(); answer, generation = emit(row['question'])
            event = event_for(row, proof, answer, generation, time.perf_counter() - tick, max_new)
            writer.append(event); events.append(event)
        manifest = writer.close(lineage=dict(signature=common.sha(lineage), status='RAW_COMPLETE_STRICT_EXIT_PENDING'))
        verify(output, manifest)
        return dict(schema=SCHEMA, status='RAW_COMPLETE_STRICT_EXIT_PENDING', signature=common.sha(lineage),
            lineage=copy.deepcopy(lineage), raw_manifest=manifest, summary=summarize(events, rows, proofs, max_new)), events
    except BaseException as exc:
        partial = (writer.close(lineage=dict(signature=common.sha(lineage), status='INCOMPLETE'))
                   if writer._total_rows and not writer.manifest_path.exists() else None)
        common.atomic_json(output / 'error.json', dict(status='INCOMPLETE', error_type=type(exc).__name__,
            message=str(exc), first_answers_preserved=len(events), partial_manifest=partial))
        raise


def review_path(path, root=ROOT):
    path = common.safe_path(path, root)
    try: path.relative_to(Path(root).absolute() / 'review_request')
    except ValueError: raise ValueError('human Markdown belongs in review_request')
    if path.suffix != '.md': raise ValueError('explicit new Markdown review path required')
    return path


def human_markdown(events, lineage):
    def block(text):
        fence = '`' * (max([len(v) for v in re.findall(r'`+', text)] or [0]) + 3)
        return fence + 'text\n' + text + '\n' + fence
    lines = ['# 연구 모델 단일 질문 첫답 검수', '',
        '아래는 실제 원답이다. 설명형 답의 정답성은 자동 판정하지 않았다. 종료/짧은 길이는 정답 증거가 아니다.', '',
        '모델: ' + lineage['model'], 'CP SHA: ' + lineage['checkpoint_sha256'],
        '본체 core SHA: ' + lineage['core_sha256'], 'tokenizer SHA: ' + lineage['tokenizer_sha256'],
        '질문 원본 SHA: ' + lineage['source']['sha256'], '정밀도: FP32 MATH / TF32 OFF / greedy / KV ON / MTP OFF', '']
    for event in events:
        row, meta = event['source'], event['generation']
        lines.extend(['## ' + row['id'] + ' · ' + row['language'] + ' · ' + row['category'], '',
            '질문:', '', block(row['question']), '', '실제 첫 답:', '', block(event['answer']), '',
            '종료: ' + meta['finish_reason'] + ' / 생성 token: ' + str(meta['generated_tokens'])
            + ' / 초: ' + format(event['seconds'], '.6f'), ''])
        if row['expected_exact'] is None: lines.extend(['의미·사실·질문 적합성: 사람 검토 필요. 자동 정답 점수 없음.', ''])
        else: lines.extend(['제공된 코드 정의 기대문자열(이 도구가 진위를 인증하지 않음):', '',
            block(row['expected_exact']), '', '공백 정규화 문자일치 진단: '
            + str(event['diagnostic']['whitespace_exact']) + ' (의미 판정 아님)', ''])
    return '\n'.join(lines) + '\n'


def publish_batch(output, review, result, events, rows, proofs, max_new=128, root=ROOT):
    output = common.safe_path(output, root); review = review_path(review, root)
    if (output / 'report.json').exists() or review.exists(): raise FileExistsError('existing report/review preserved')
    if (result.get('status') != 'RAW_COMPLETE_STRICT_EXIT_PENDING'
            or result.get('strict_model_context_exit_verified') is not True
            or result.get('signature') != common.sha(result['lineage'])
            or result['raw_manifest'].get('lineage') != dict(signature=result['signature'], status='RAW_COMPLETE_STRICT_EXIT_PENDING')
            or result['lineage'].get('questions_sha256') != common.sha(rows)
            or result['lineage'].get('proofs_sha256') != common.sha(proofs)):
        raise ValueError('strict context or source lineage is not closed')
    manifest = json.loads((output / 'answers_shards_manifest.json').read_text(encoding='utf-8'))
    if manifest != result['raw_manifest']: raise ValueError('closed raw manifest changed')
    verify(output, manifest); actual = []
    for shard in manifest['shards']:
        with (output / shard['path']).open(encoding='utf-8') as stream: actual.extend(json.loads(line) for line in stream)
    if actual != events or summarize(actual, rows, proofs, max_new) != result['summary']:
        raise ValueError('stored first answers or summary differ from raw recount')
    payload = human_markdown(actual, result['lineage']).encode('utf-8')
    if len(payload) > LIMIT: raise ValueError('human review must be below20MB')
    if review.exists(): raise FileExistsError('existing human review preserved')
    review.parent.mkdir(parents=True, exist_ok=True)
    with review.open('xb') as stream: stream.write(payload)
    report = dict(result, status='CHAT_FIRST_ANSWERS_RECORDED_HUMAN_REVIEW_PENDING',
        review=dict(path=str(review.relative_to(Path(root).absolute())), bytes=len(payload), sha256=common.file_sha(review)),
        model_training=False, checkpoint_writes=0, human_semantic_review='NOT_RUN')
    common.atomic_json(output / 'report.json', report)
    return report


def execute(args):
    from scripts.p106b_gate_runtime import wall_limit
    if args.model not in MODELS: raise ValueError('exact registered research model name required')
    rows, source = load_questions(args.data, root=ROOT)
    output = common.safe_path(args.output, ROOT); review = review_path(args.review_output, ROOT)
    if output.exists() or review.exists(): raise FileExistsError('previous batch/review preserved')
    began = time.perf_counter(); result = events = None
    try:
        with wall_limit(args.max_wall_sec):
            manifest = ui.verify_manifest(ROOT); tokenizer = ui.local_tokenizer(manifest, ROOT)
            proofs = question_proofs(rows, tokenizer, args.max_new)
            pins = {p: common.file_sha(ROOT / p) for p in CODE}
            with ui.selected_runtime(ui.resolve_model(args.model), root=ROOT) as active:
                if (active['name'] != args.model or active['tokenizer_sha256'] != ui.TOKENIZER_SHA
                        or active['precision'] != 'FP32_MATH'
                        or question_proofs(rows, active['tokenizer'], args.max_new) != proofs):
                    raise ValueError('actual model/tokenizer differs from CPU prompt proof')
                lineage = dict(schema=SCHEMA, model=args.model, checkpoint=active['checkpoint'],
                    checkpoint_sha256=active['checkpoint_sha256'], core_sha256=active['core_sha256'],
                    tokenizer_sha256=active['tokenizer_sha256'], model_report_sha256=active['report_sha256'],
                    model_manifest_sha256=active['manifest_sha256'], quantization_route=copy.deepcopy(active['quantization_route']),
                    source=source, questions_sha256=common.sha(rows), proofs_sha256=common.sha(proofs), code_sha256=pins,
                    precision='FP32_MATH_TF32_OFF', max_new=args.max_new, first_answer_only=True, history=False)
                result, events = collect_batch(output, rows, proofs, lineage,
                    lambda question: ui.emit(active, question, max_new=args.max_new, history=()), args.max_new, ROOT)
            if load_questions(args.data, ROOT)[1] != source or {p: common.file_sha(ROOT / p) for p in CODE} != pins:
                raise ValueError('question/code source changed during inference')
            result.update(strict_model_context_exit_verified=True, whole_seconds=time.perf_counter() - began)
            report = publish_batch(output, review, result, events, rows, proofs, args.max_new, ROOT)
    except BaseException as exc:
        if output.is_dir() and not (output / 'error.json').exists():
            common.atomic_json(output / 'error.json', dict(status='INCOMPLETE', error_type=type(exc).__name__, message=str(exc),
                strict_context_exit_verified=False, first_answers_preserved=len(events) if events else 'READ_RAW_SHARDS'))
        raise
    print('[CHAT_PROBE_FIRST_ANSWERS] ' + json.dumps(report['summary'], ensure_ascii=False), flush=True)
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model', choices=MODELS, required=True)
    parser.add_argument('--data', required=True); parser.add_argument('--output', required=True)
    parser.add_argument('--review-output', required=True)
    parser.add_argument('--max-wall-sec', type=int, default=1800); parser.add_argument('--max-new', type=int, default=128)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--check-only', action='store_true'); action.add_argument('--execute', action='store_true')
    args = parser.parse_args(argv)
    if not 60 <= args.max_wall_sec <= 21600 or not 1 <= args.max_new <= 1024: parser.error('bounded wall60..21600 and max-new1..1024 required')
    try:
        if args.check_only:
            rows, source = load_questions(args.data, ROOT); output = common.safe_path(args.output, ROOT)
            review = review_path(args.review_output, ROOT)
            if output.exists() or review.exists(): raise FileExistsError('old batch/review preserved')
            print('[CHAT_PROBE_CHECK_ONLY] ' + json.dumps(dict(schema=SCHEMA, model=args.model, source=source,
                languages=dict(Counter(r['language'] for r in rows)), max_new=args.max_new, first_answer_only=True,
                model_loads=0, checkpoint_tensor_loads=0, gpu_calls=0, writes=0,
                human_review='REQUIRED_FOR_OPEN_QUESTIONS'), ensure_ascii=False)); return 0
        return execute(args)
    except KeyboardInterrupt: return 130
    except Exception as exc:
        print('[CHAT_PROBE_ERROR] ' + type(exc).__name__ + ': ' + str(exc), file=sys.stderr, flush=True); return 9


if __name__ == '__main__': raise SystemExit(main())
