"""Pinned Qwen candidate, separate from the existing Bonsai teacher defaults."""
from __future__ import annotations
import hashlib
import copy
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / 'HF/model--ISTA-DASLab--Qwen3.8-27B-GSQ-RCO-GGUF/Qwen3.8-27B-GSQ-RCO-IQ2_XS-mtp.gguf'
MODEL_SHA = 'F3369F8D36968AB7DD12F5FF11452680AEF9371AA19C9922D22CCD5E58C2D9C8'
SERVER = Path('/home/uranus/llama-b11396/llama-server')
LIBRARIES = {
    'llama-server': 'C513DCE0107CD1157EE998E7DBB271180429AB194E66D81664F0365EBA68A8C9',
    'libllama-server-impl.so': '91C3B182D2DAF4CFAB7DEAAC81E279B9D29E2938D4B46AD492D16ECE03C8A0A3',
    'libllama-common.so.0.5.0': '6125F47E3AAAD720F89CE202B3E213CD3C8618B8BF8510EE87F1568167F1B3AC',
    'libllama.so.0.5.0': '9F9C5D70BC0E8E3EAC387B8E5065C97F6CCD06D536FD47B5DA782270B354E7D5',
    'libggml-cuda.so': 'A7CD12A05F0A8A6BC3070F8C3290F95774FB6A258D00B0D6FF687A9BE213AEE8',
    'libggml-base.so.0.25.3': '6814301534CAA15FC361B9AEC7463E081A6688312F0390FCF96B14C15F156C55',
    'libggml.so.0.25.3': '6FE347469E77A19024F3EC2B1D949CF8221F014495318AF3758AF0DF3A646BC1',
}
CONTEXT, MAX_OUTPUT, THINKING = 8192, 3072, 1024
SAMPLER = dict(temperature=1.0, top_p=0.95, top_k=20, min_p=0.0,
               presence_penalty=0.0, repetition_penalty=1.0)


def digest(path):
    if path.is_symlink() or not path.is_file() or any(p.is_symlink() for p in path.parents):
        raise ValueError('exact regular file required: ' + str(path))
    h = hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda: f.read(8 * 2**20), b''): h.update(b)
    return h.hexdigest().upper()


def assets(full_hash=False):
    from scripts.p106b_mtp_teacher import gguf_metadata
    if MODEL.is_symlink() or not MODEL.is_file() or MODEL.stat().st_size != 8771311680:
        raise ValueError('Qwen model absent, linked or wrong size')
    for name, sha in LIBRARIES.items():
        if digest(SERVER.parent / name) != sha: raise ValueError('binary/library SHA changed: ' + name)
    with MODEL.open('rb') as f: meta = gguf_metadata(f)
    if (meta['metadata'].get('general.architecture') != 'qwen35'
            or meta['metadata'].get('qwen35.nextn_predict_layers') != 1):
        raise ValueError('expected Qwen architecture and one MTP head')
    if full_hash and digest(MODEL) != MODEL_SHA: raise ValueError('model SHA changed')
    return dict(model=str(MODEL.relative_to(ROOT)), model_bytes=MODEL.stat().st_size,
        model_sha256=MODEL_SHA, model_hash_check='MATCH' if full_hash else 'NOT_REHASHED',
        server=str(SERVER), runtime_sha256=LIBRARIES, gguf_metadata=meta['metadata'],
        sampler=SAMPLER, effort='low', context=CONTEXT, max_output=MAX_OUTPUT,
        thinking_budget_tokens=THINKING, default_teacher_changed=False)


def command(port, key, gpu_layers='all'):
    if gpu_layers not in ('all', '48'): raise ValueError('preregistered GPU placement required')
    return [str(SERVER), '--offline', '--model', str(MODEL), '--host', '127.0.0.1',
        '--port', str(port), '--api-key', key, '--no-webui', '--parallel', '1',
        '--ctx-size', str(CONTEXT), '--batch-size', '64', '--ubatch-size', '64',
        '--threads', '8', '--fit', 'off', '--no-op-offload', '--gpu-layers', gpu_layers,
        '--cache-ram', '0', '--cache-reuse', '0', '--no-warmup', '--perf',
        '--verbosity', '4', '--log-colors', 'off', '--reasoning', 'auto',
        '--reasoning-format', 'deepseek', '--reasoning-budget', str(THINKING),
        '--spec-type', 'draft-mtp', '--spec-draft-n-max', '2']


def cases():
    return [dict(id='ram_ko', language='ko', question='RAM과 SSD의 차이를 초보자에게 두 문장으로 설명해 주세요.'),
        dict(id='arithmetic_en', language='en', question='What is 17 + 25? Show one short calculation and then the result.'),
        dict(id='context_ko', language='ko', question='민수는 파란 공, 지수는 빨간 공을 골랐습니다. 지수가 고른 공의 색만 답하세요.'),
        dict(id='translation_ko', language='ko', question='다음 문장을 한국어로 번역하세요: A leap year usually has 366 days.')]


def payload(case, seed):
    from scripts.p106b_teacher_format import teacher_prompt
    return dict(SAMPLER, messages=teacher_prompt('answer_given', case['language'],
        {'question': case['question']}), reasoning_effort='low', seed=seed,
        max_tokens=MAX_OUTPUT, thinking_budget_tokens=THINKING, cache_prompt=False)


def parsed_response(reply, language):
    """Normalize only an empty OPTIONAL NOTE tail, never question/answer/reasoning.

    The shared legacy parser expects a newline after note content even when it
    is empty. Raw server reply is immutable and remains the provenance source.
    Missing required fields, extra/nested markers and length stops still fail.
    """
    from scripts.p106b_teacher_format import parse_reply
    original=parse_reply(reply,language=language)
    if original['format_status']!='PARSE_ERROR' or original['finish_reason']!='stop':return original
    final=original['teacher_final_content']
    normalized=re.sub(r'\n\[\[NOTE\]\][ \t\r\n]*\[\[/NOTE\]\][ \t\r\n]*\Z','',final)
    if normalized==final:return original
    wrapped=copy.deepcopy(reply)
    wrapped['choices'][0]['message']['content']=normalized
    parsed=parse_reply(wrapped,language=language)
    if parsed['format_status']!='TAGGED_COMPLETE':return original
    parsed.update(teacher_final_content=final,final_normalization='OPTIONAL_EMPTY_NOTE_TAIL_REMOVED',
                  raw_final_sha256=hashlib.sha256(final.encode()).hexdigest().upper())
    return parsed


def canonical_candidate(reply, case, source_ref):
    from scripts.p106b_teacher_wrapper import wrap_turns
    parsed=parsed_response(reply,case['language'])
    if parsed['format_status']!='TAGGED_COMPLETE':raise ValueError('incomplete final cannot be student input')
    content=parsed['parsed_content']
    sha=lambda text:hashlib.sha256(text.encode()).hexdigest().upper()
    thought=parsed['teacher_reasoning_content']
    return wrap_turns([dict(user_text=content['user_text'],assistant_text=content['assistant_text'])],
        source_id='qwenrole:'+case['id'],source_sha256=sha(case['question']),
        teacher_model_sha256=MODEL_SHA,language=case['language'],
        source_license='repository-code-authored-role-question',generation_id='qwenrole_'+case['id'],
        correction_note=content.get('correction_note',''),
        reasoning_ref=source_ref+'#'+case['id'] if thought else '',
        reasoning_sha256=sha(thought) if thought else '')
