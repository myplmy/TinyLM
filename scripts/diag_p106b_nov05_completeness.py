"""Opt-in fixed-question completeness comparison; no automatic truth judgement."""
import hashlib
import json
from pathlib import Path
import sys
import time
import traceback
from unittest.mock import patch

from scripts import diag_p106b_supported_production8h as supported
from scripts.p106b_shards import ShardWriter, verify

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'test_result/evidence/p106b_completeness_v2_20261105'
READY = ROOT / 'handoff/audit/nov05_teacher_resume/PREFLIGHT_v1.json'
OLD = supported.OUTPUT / 'batch_000006'
REVIEWED = (0, 118, 237, 355, 474, 592, 711, 829, 948, 1066, 1185, 1302)
ADDITIONAL = (30, 147, 264, 381, 498, 615, 732, 849, 966, 1083, 1200, 1290)
CUE = (
    ' COMPLETENESS CONTROL: Answer the exact QUESTION directly. If the question asks which '
    'option, explicitly name the supported option, rather than only quoting related evidence. '
    'If the supplied evidence does not establish the requested comparison, explicitly identify '
    'what fact is missing. Do not infer a universal negative from mere non-mention. '
    'Keep uncertainty and do not invent evidence. This is an answer-writing instruction, '
    'not permission to change the QUESTION or the QUESTION/ANSWER/NOTE transport. ')


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b''):
            h.update(block)
    return h.hexdigest().upper()


def write(path, value):
    raw = (json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + chr(10)).encode()
    if len(raw) >= 4_000_000:
        raise ValueError('small artifact limit exceeded')
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(raw)


def rows(directory, manifest):
    verify(directory, manifest)
    for item in manifest['shards']:
        with (directory / item['path']).open(encoding='utf-8') as stream:
            for line in stream:
                yield json.loads(line)


def close_attempt(writer, directory, lineage):
    if writer._total_rows == 0:
        return dict(schema='P106B_EMPTY_ATTEMPT_V1', rows=0, bytes=0, shards=[],
                    reason='no rows written; not a published corpus')
    manifest = writer.close(lineage=lineage)
    verify(directory, manifest)
    return manifest


def make_payload(original, case, seed, complete, **kwargs):
    result = original(case['source'], case['language'], 'qa', seed,
                      fixed_question=case['question'], **kwargs)
    if complete:
        result['messages'][0]['content'] += CUE
    return result


def prepare():
    if OUT.exists():
        raise FileExistsError('fresh comparison namespace required')
    ready = json.loads(READY.read_text(encoding='utf-8'))
    if ready['status'] != 'TECHNICAL_INPUTS_READY_NOT_SEMANTIC_APPROVAL':
        raise ValueError('real replay preflight required')
    for relative, expected in ready['original_files'].items():
        if sha(ROOT / relative) != expected:
            raise ValueError('published V3 batch changed')
    report = json.loads((OLD / 'report.json').read_text(encoding='utf-8'))
    candidates = list(rows(OLD, report['candidate_manifest']))
    wanted = {}
    for index in REVIEWED + ADDITIONAL:
        candidate = candidates[index]
        meta = candidate['meta']
        key = meta['source_id']
        if key in wanted:
            raise ValueError('duplicate source in comparison')
        wanted[key] = dict(candidate_index=index,
            review_group='PREVIOUSLY_READ' if index in REVIEWED else 'ADDITIONAL_NOT_PREVIOUSLY_READ',
            language=meta['language'], question=meta['original_teacher_question'])
    for raw in rows(OLD, report['raw_manifest']):
        source = raw['source']
        key = source['meta']['source_id']
        if key in wanted and 'source' not in wanted[key]:
            wanted[key]['source'] = source
    cases = list(wanted.values())
    if len(cases) != 24 or any('source' not in c or not c['question'].strip() for c in cases):
        raise ValueError('exact 24 source/question packets required')
    with supported.scope(supported.OUTPUT) as (producer, info):
        original = producer.tasks.payload
        for index, case in enumerate(cases):
            case['id'] = 'case_' + str(index).zfill(2)
            case['seed'] = int(hashlib.sha256(
                (case['source']['meta']['source_id'] + case['question']).encode()).hexdigest()[:8], 16) & 0x7fffffff
            a = make_payload(original, case, case['seed'] + 1, False)
            b = make_payload(original, case, case['seed'] + 1, True)
            c = json.loads(json.dumps(b))
            if not c['messages'][0]['content'].endswith(CUE):
                raise ValueError('new cue missing')
            c['messages'][0]['content'] = c['messages'][0]['content'][:-len(CUE)]
            if a != c or json.loads(a['messages'][1]['content'])['producer_control']['learner_question_literal'] != case['question']:
                raise ValueError('paired payload differs outside the system suffix')
        profile = dict(schema='P106B_COMPLETENESS_PAIR_V1', authority_directive=109,
            mtp=True, source_contract=supported.VERSION, fixed_questions=True,
            quality_judgement='ROOT_REVIEW_AFTER_EXECUTION_NOT_AUTOMATIC',
            semantic_retry=False, total_structure_attempts=3, teacher_requests_minimum=48,
            same_seed_per_case=True, arm_order='alternating by case parity',
            source_family=sorted({c['source']['meta']['source_family'] for c in cases}),
            source_batch=sha(OLD / 'report.json'), readiness_sha256=sha(READY),
            cases=cases, complete_cue=CUE, input=info,
            max_wall_seconds=1800, deadline_utc='2026-11-05T08:00:00+00:00',
            no_production_admission=True, no_student_loading=True,
            sources={str(Path(__file__).relative_to(ROOT)): sha(Path(__file__)),
                     'scripts/diag_p106b_supported_production8h.py': sha(Path(supported.__file__))})
    write(OUT / 'profile.json', profile)
    print('[PREPARED] ' + json.dumps(dict(cases=24, requests_minimum=48,
          profile_sha256=sha(OUT / 'profile.json'), model_loading=False)), flush=True)


def execute():
    from scripts.p106b_memory_stream import PersistentMemory, stream_session_scope
    from scripts.diag_p106b_gemma_telemetry_resume import RetryingMemoryReader
    from scripts.diag_p106b_gemma_budget_resume import ProductionBudgetPause
    from tokenizers import Tokenizer
    from scripts.p106b_mixed_scale import TOKENIZER, TOK_SHA
    from tinylm.data.sft import encode_conversation, sft_targets
    profile = json.loads((OUT / 'profile.json').read_text(encoding='utf-8'))
    if sha(TOKENIZER) != TOK_SHA:
        raise ValueError('student tokenizer changed')
    tokenizer = Tokenizer.from_file(str(TOKENIZER))
    for name, expected in profile['sources'].items():
        if sha(ROOT / name) != expected:
            raise ValueError('comparison source changed')
    if (profile['complete_cue'] != CUE or sha(READY) != profile['readiness_sha256']
            or sha(OLD / 'report.json') != profile['source_batch']):
        raise ValueError('comparison profile changed')
    directory = OUT / 'paired'
    directory.mkdir(exist_ok=False)
    raw, candidates = ShardWriter(directory, 'raw'), ShardWriter(directory, 'candidates')
    result = dict(schema='P106B_COMPLETENESS_PAIR_RESULT_V1', status='RUNNING',
        input_sha256=sha(OUT / 'profile.json'), formal_train_ready=False,
        semantic_quality='NOT_REVIEWED', rows=[], new_student_training=False)
    session = None
    failure = None
    began = time.monotonic()
    try:
        with supported.scope(supported.OUTPUT) as (producer, info):
            if info != profile['input']:
                raise ValueError('V3 input controls changed')
            identity = producer.teacher.assets(True)
            role = producer.gate.read_report(producer.gate.previous.role_gate.OUTPUT / 'role/report.json', producer.gate.ROLE_SHA)
            if any(identity[k] != role['input']['asset_identity'][k] for k in ('model_sha256', 'draft_sha256')):
                raise ValueError('teacher assets changed')
            result['asset_identity'] = {k: identity[k] for k in ('model_sha256', 'draft_sha256')}
            seconds = supported.limit_window(profile['max_wall_seconds'], profile['deadline_utc'])
            original = producer.tasks.payload
            with PersistentMemory() as memory:
                reader = RetryingMemoryReader(memory, emit=lambda value: print(value, flush=True))
                try:
                    with stream_session_scope(reader), supported.supported_wall_limit(seconds):
                        with producer.teacher.GemmaSession(False) as session:
                            for index, case in enumerate(profile['cases']):
                                order = ('baseline', 'complete') if index % 2 == 0 else ('complete', 'baseline')
                                for arm in order:
                                    def payload(*args, **kwargs):
                                        return make_payload(original, case, args[3], arm == 'complete', **kwargs)
                                    before = raw._total_rows
                                    started = time.monotonic()
                                    with patch.object(producer.tasks, 'payload', payload):
                                        row = producer.produce_group(session, case['source'], case['language'],
                                            'qa', case['seed'], raw, identity)
                                    if row is not None:
                                        row['meta'].update(completeness_pair=case['id'],
                                            completeness_arm=arm, fixed_question=case['question'])
                                        candidates.append(row)
                                        ids, labels, _ = encode_conversation(row, tokenizer)
                                        x, y = sft_targets(ids, labels)
                                        wire = dict(input_tokens=len(x), targets=sum(v >= 0 for v in y),
                                            exact_fixed_question=row['meta']['original_teacher_question'] == case['question'])
                                        wire['technical_ready'] = 0 < wire['input_tokens'] <= 1024 and wire['targets'] > 0 and wire['exact_fixed_question']
                                    else:
                                        wire = dict(technical_ready=False)
                                    result['rows'].append(dict(case=case['id'], arm=arm, accepted=row is not None,
                                        raw_start_1based=before + 1, raw_end_1based=raw._total_rows,
                                        wire=wire, seconds=time.monotonic() - started))
                                    print('[PAIR_PROGRESS] ' + json.dumps(result['rows'][-1]), flush=True)
                            session.check()
                            result['memory'] = session.memory()
                    result['status'] = 'TECHNICAL_PAIR_COMPLETE_NOT_QUALITY_APPROVAL'
                finally:
                    result['memory_reader'] = reader.snapshot()
    except BaseException as exc:
        failure = exc
        result.update(status='PAUSED' if isinstance(exc, ProductionBudgetPause) else 'ERROR',
                      error_type=type(exc).__name__, error=str(exc), traceback=traceback.format_exc())
    finally:
        result['raw_manifest'] = close_attempt(raw, directory, dict(input_sha256=result['input_sha256']))
        result['candidate_manifest'] = close_attempt(candidates, directory, dict(input_sha256=result['input_sha256']))
        if session is not None and session.process is not None:
            result['owned_server_returncode'] = session.process.poll()
            result['owned_server_closed'] = session.process.poll() is not None
        else:
            result['owned_server_closed'] = True
        result['wall_seconds'] = time.monotonic() - began
        write(directory / 'report.json', result)
        print('[PAIR_FINAL] ' + json.dumps({k: result.get(k) for k in
              ('status', 'wall_seconds', 'owned_server_closed', 'error_type')}), flush=True)
    if failure is not None:
        raise failure
    return 0


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ('prepare', 'execute'):
        raise SystemExit('prepare or execute required')
    if sys.argv[1] == 'prepare':
        prepare()
    else:
        execute()


if __name__ == '__main__':
    raise SystemExit(main())
