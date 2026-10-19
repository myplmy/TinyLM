#!/usr/bin/env python3
"""Read-only span-head inference on the exact saved v3 span03 backbone.

Only new cache/raw/evidence namespaces are written. No training, head fitting,
checkpoint creation, source mutation or gold-conditioned inference is offered.
Heavy historical modules are imported only by explicit source/runtime phases.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import asdict
from datetime import datetime, timezone
import gc
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
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts import p106b_span_readout as method
from scripts.p106b_shards import ShardWriter, verify
from scripts.p106b_stage_receipt import pipeline

TAG = 'p106b_span_readout_v1_s1337'
SCHEMA = 'P106B_SPAN_READOUT_V1'
MODES = ('source', 'prepare', 'preflight', 'evaluate', 'readback')
CACHE = ROOT / 'data_cache' / TAG
RAW = ROOT / 'runs/eval' / TAG
EVIDENCE = ROOT / 'test_result/evidence' / TAG
SOURCE_REPORT = ROOT / 'HF/sft_ready/p106b_grounded_span_v1_s1337/corpus/report.json'
SOURCE_REPORT_SHA = '4C77034473A4D83004932D9818CE3C50057302529241F7BB272F5682639B600A'
TRAIN_REPORT = ROOT / 'test_result/evidence/p106b_grounded_span_exec_v3_s1337/span03/report.json'
TRAIN_REPORT_SHA = '6E1B9C160043345DE73AD2629D04E0ABE5B414F977EEDF306C6D7AC9D78DC98E'
CHECKPOINT = ROOT / 'runs/ckpt/m100s10_ko-en_grounded_span_dense_chat32_p106b_grounded_span_exec_v3_s1337_span03.pt'
CHECKPOINT_SHA = 'E3D632CE40B549B8FC3384294850472EFEFCED8392B09DCF35FEEFF0D52B1446'
TOKENIZER = ROOT / 'data_cache/tok-ko-en-32768-chat32.json'
TOKENIZER_SHA = '9716F40E4C504D6AF37DDE76CCA578E30B45E9CA86C8B6BB79B2FA095D3AC88E'
SOURCE_TAG, TRAIN_TAG = 'p106b_grounded_span_v1_s1337', 'p106b_grounded_span_exec_v3_s1337'
END = datetime(2026, 10, 20, 8, tzinfo=timezone.utc)
ACTIVE_LIMIT, RECORD_RESERVE = 2400, 600
CONTEXT, MAX_NEW, DIM, RANK, PARAMETERS, CASES = 1024, 64, 768, 64, 196608, 640
OWN_CODE = ('scripts/p106b_span_readout.py', 'scripts/test_p106b_span_readout.py',
            'scripts/diag_p106b_span_readout.py', 'scripts/test_p106b_span_readout_driver.py')
CODE = (*OWN_CODE, 'scripts/diag_p106b_grounded_span.py',
        'scripts/diag_p106b_grounded_span_execution.py', 'scripts/p106b_grounded_span.py',
        'scripts/diag_p101a_sft_mtp.py', 'scripts/p101a_sft_mtp_data.py',
        'scripts/diag_p101a_mtp_parity.py', 'scripts/diag_p106b_question_transfer.py',
        'scripts/p106b_shards.py', 'scripts/p106b_stage_receipt.py',
        'scripts/p106b_gate_runtime.py', 'tinylm/config.py', 'tinylm/chat/canonical.py',
        'tinylm/chat/serialize.py', 'tinylm/data/sft.py', 'tinylm/model/transformer.py',
        'tinylm/infer/generate.py', 'tinylm/infer/mtp.py')


class Pending(RuntimeError):
    """An exact prerequisite or the bounded authority is absent."""


def sha(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
        separators=(',', ':'), allow_nan=False).encode('utf-8')).hexdigest().upper()


def safe(path):
    path = Path(path)
    if not path.is_absolute() or '..' in path.parts:
        raise ValueError('absolute unambiguous repository path required')
    try:
        path.relative_to(ROOT)
    except ValueError as exc:
        raise ValueError('repository-local exact path required') from exc
    for current in (path, *path.parents):
        if current.is_symlink():
            raise ValueError('linked input/output is not accepted')
        if current == ROOT:
            break
    return path


def digest(path):
    path = safe(path)
    if not path.is_file():
        raise Pending('regular exact input absent: ' + str(path.relative_to(ROOT)))
    result = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''):
            result.update(block)
    return result.hexdigest().upper()


def required(path):
    path = safe(path)
    if not path.is_file():
        raise Pending('owned prerequisite absent: ' + str(path.relative_to(ROOT)))
    if path.stat().st_size >= 20_000_000:
        raise ValueError('bounded JSON prerequisite required')
    return json.loads(path.read_text(encoding='utf-8'))


def write(path, value):
    path = safe(path)
    if not any(path.is_relative_to(base) for base in (CACHE, RAW, EVIDENCE)):
        raise ValueError('only the three new owned namespaces may be written')
    payload = (json.dumps(value, ensure_ascii=False, sort_keys=True,
        indent=2, allow_nan=False) + '\n').encode('utf-8')
    if len(payload) >= 20_000_000:
        raise ValueError('single artifact must stay below20MB')
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(payload)


def info():
    pins = {name: digest(ROOT / name) if safe(ROOT / name).is_file() else 'NOT_CREATED'
            for name in sorted(set(CODE))}
    return dict(schema=SCHEMA, tag=TAG, code_sha256=pins,
        code_complete=all(value != 'NOT_CREATED' for value in pins.values()),
        source_report=str(SOURCE_REPORT.relative_to(ROOT)), source_report_sha256=SOURCE_REPORT_SHA,
        training_report=str(TRAIN_REPORT.relative_to(ROOT)), training_report_sha256=TRAIN_REPORT_SHA,
        checkpoint=str(CHECKPOINT.relative_to(ROOT)), checkpoint_sha256=CHECKPOINT_SHA,
        tokenizer_sha256=TOKENIZER_SHA, input_tag=TRAIN_TAG, input_arm='span03',
        original_updates=96, auxiliary_rank=RANK, auxiliary_parameters=PARAMETERS,
        cases=CASES, train_natural_per_language=64, dev_natural=256, test_natural=256,
        max_new=MAX_NEW, seq=CONTEXT, vocab_protocol='FP32_MATH_GREEDY64_KV_ON_MTP_OFF',
        span_protocol='FP32_MATH_PREFIX_ONLY_NO_KV_EXISTING_HEAD',
        policies=list(method.POLICIES), normalization=method.NORMALIZATION,
        authority_end_utc=END.isoformat(), record_reserve_seconds=RECORD_RESERVE,
        active_limit_seconds=ACTIVE_LIMIT, optimizer_updates=0, checkpoint_writes=0,
        teacher_calls=0, inference_gold_arguments=False, general_assistant_improvement='NOT_ESTABLISHED')


def authority(now=None):
    current = datetime.now(timezone.utc) if now is None else now
    if current.tzinfo is None:
        raise ValueError('aware clock required')
    remaining = (END - current).total_seconds() - RECORD_RESERVE
    if remaining <= 0:
        raise Pending('Oct20 17KST authority/600-second record reserve exhausted')
    return remaining


def historical_modules():
    from scripts import diag_p106b_grounded_span as source
    from scripts import diag_p106b_grounded_span_execution as execution
    return source, execution


def validate_training_report(report, producer, execution_metadata):
    expected = dict(schema='P106B_GROUNDED_SPAN_V1', tag=TRAIN_TAG, status='TRAINED_TEST_PENDING',
        arm='span03', updates=96, weight=.3, auxiliary_rank=RANK, auxiliary_parameters=PARAMETERS,
        source_producer_tag=SOURCE_TAG, source_producer_report=str(SOURCE_REPORT.relative_to(ROOT)),
        source_producer_report_sha256=SOURCE_REPORT_SHA, corpus_sha256=SOURCE_REPORT_SHA,
        source_data_changed=False, tokenizer_sha256=TOKENIZER_SHA,
        checkpoint=str(CHECKPOINT.relative_to(ROOT)), checkpoint_sha256=CHECKPOINT_SHA,
        head_in_normal_model_state=False, head_in_free_generation=False, optimizer_saved=False)
    if any(report.get(key) != value for key, value in expected.items()):
        raise ValueError('exact completed v3/span03 report contract differs')
    if (report.get('source_producer_code_sha256') != producer['code_sha256']
            or report.get('code_sha256') != execution_metadata['code_sha256']
            or not math.isfinite(report.get('auxiliary_parameter_delta_l2', float('nan')))
            or report['auxiliary_parameter_delta_l2'] <= 0
            or producer.get('expected_updates') != 96):
        raise ValueError('same original source/trained code and active head required')


def source_state():
    source, execution = historical_modules()
    if not info()['code_complete']:
        raise ValueError('all four new helper/driver/test files must exist')
    for path, expected in ((SOURCE_REPORT, SOURCE_REPORT_SHA), (TRAIN_REPORT, TRAIN_REPORT_SHA),
                           (CHECKPOINT, CHECKPOINT_SHA), (TOKENIZER, TOKENIZER_SHA)):
        if digest(path) != expected:
            raise ValueError('pinned input SHA differs: ' + str(path.relative_to(ROOT)))
    producer, rows, labels = source.read_course()
    trained = required(TRAIN_REPORT)
    validate_training_report(trained, producer, execution.metadata(producer))
    counts = {}
    for split in ('train', 'dev', 'test'):
        if split not in rows:
            raise ValueError('all original source splits required')
        natural = [row for row in rows[split] if row['meta'].get('kind') == 'natural_first_qa']
        counts[split] = dict(Counter(row['meta']['language'] for row in natural))
    if counts != dict(train=dict(ko=1024, en=1024), dev=dict(ko=128, en=128), test=dict(ko=128, en=128)):
        raise ValueError('exact original natural source supply differs')
    binding = dict(source_report_sha256=SOURCE_REPORT_SHA, training_report_sha256=TRAIN_REPORT_SHA,
        checkpoint_sha256=CHECKPOINT_SHA, tokenizer_sha256=TOKENIZER_SHA,
        source_counts=producer['counts'], source_manifests=producer['manifests'],
        source_labels_manifest=producer['labels_manifest'], source_code_sha256=producer['code_sha256'],
        execution_code_sha256=trained['code_sha256'], natural_counts=counts,
        cross_language_semantic_overlap=producer.get('cross_language_semantic_overlap', 'NOT_AUDITED'),
        source_truth='PUBLIC_SOURCE_UNVERIFIED',
        checkpoint_tensor_validation='NOT_RUN_UNTIL_EVALUATE', models_loaded=0)
    return producer, rows, labels, binding


def selected_rows(rows):
    """Selection uses source/reference identity, never gold or head scores."""
    result = []
    for split in ('train', 'dev', 'test'):
        for language in ('ko', 'en'):
            values = [row for row in rows[split] if row['meta'].get('kind') == 'natural_first_qa'
                      and row['meta']['language'] == language]
            values.sort(key=lambda row: sha([TAG, split, row['meta']['semantic_root_id']]))
            if len({row['meta']['semantic_root_id'] for row in values}) != len(values):
                raise ValueError('one natural source per reference identity required')
            chosen = values[:64] if split == 'train' else values
            if len(chosen) != (64 if split == 'train' else 128):
                raise ValueError('registered natural split/language selection differs')
            result.extend((split, row) for row in chosen)
    if len(result) != CASES:
        raise ValueError('exact640 inference cases required')
    return result


def text(message):
    value = message['content']
    if isinstance(value, str):
        return value
    if not isinstance(value, list) or any(block.get('type') != 'text' for block in value):
        raise ValueError('text-only original message required')
    return ''.join(block['text'] for block in value)


def bank_snapshot(bank):
    return dict(ids=list(bank.ids), offsets=[list(pair) for pair in bank.offsets],
        positions=list(bank.positions), query=bank.query, reference_range=list(bank.reference_range))


def make_case(split, row, location, tokenizer):
    from tinylm.chat.serialize import serialize
    if (row['meta'].get('kind') != 'natural_first_qa' or len(row['messages']) != 2
            or [m['role'] for m in row['messages']] != ['user', 'assistant']):
        raise ValueError('one original natural user/assistant pair required')
    user, gold = map(text, row['messages'])
    lo, hi = row['meta']['user_reference_range']
    a, b = row['meta']['user_answer_range']
    if (any(type(v) is not int for v in (lo, hi, a, b))
            or not 0 <= lo <= a < b <= hi <= len(user) or user[a:b] != gold):
        raise ValueError('source annotation differs; do not repair its boundaries')
    prompt = serialize(dict(messages=row['messages'][:1]), 'chatml', add_generation_prompt=True)
    prefix_messages(prompt)
    if prompt.count(user) != 1:
        raise ValueError('unique entire user transport required')
    origin = prompt.index(user)
    bank = method.build_bank(tokenizer, prompt, (origin + lo, origin + hi), max_tokens=CONTEXT)
    if len(bank.ids) + MAX_NEW > CONTEXT:
        raise Pending('complete prompt plus64 does not fit; no silent crop or case exclusion')
    if (not isinstance(location, dict) or location.get('query') != bank.query
            or location.get('positions') != list(bank.positions)
            or type(location.get('start')) is not int or type(location.get('end')) is not int
            or not 0 <= location['start'] <= location['end'] < len(bank.positions)):
        raise ValueError('original trained bank/query/label contract differs')
    start_offset = bank.offsets[bank.positions[location['start']]]
    end_offset = bank.offsets[bank.positions[location['end']]]
    if not (start_offset[0] <= origin + a < start_offset[1]
            and end_offset[0] < origin + b <= end_offset[1]):
        raise ValueError('original span labels do not cover the source annotation')
    root = row['meta']['semantic_root_id']
    identity = sha([TAG, split, row['meta']['language'], root, sha(row['messages'][:1])])
    return dict(id=identity, split=split, language=row['meta']['language'], root=root,
        source_row_sha256=sha(row), inference=dict(prompt=prompt, reference_range=list(bank.reference_range)),
        encoding=bank_snapshot(bank), bank_sha256=sha(bank_snapshot(bank)),
        gold=gold, gold_audit=dict(start_index=location['start'], end_index=location['end'],
            char_range=[origin + a, origin + b], scope='SCORING_ONLY_NOT_AN_INFERENCE_ARGUMENT'))


def build_cases(rows, labels, tokenizer):
    cases = []
    for split, row in selected_rows(rows):
        location = labels.get(sha(row['messages']))
        cases.append(make_case(split, row, location, tokenizer))
    if len({case['id'] for case in cases}) != CASES:
        raise ValueError('one exact case per selected source required')
    return cases


def read_shards(directory, manifest, stem, count):
    directory = safe(directory)
    parts = manifest.get('shards', [])
    if (type(count) is not int or count <= 0 or manifest.get('rows') != count or not parts
            or any(p.get('path') != f'{stem}_{index:06d}.jsonl' for index, p in enumerate(parts))):
        raise ValueError('exact positive owned shard sequence/count required before IO')
    if required(directory / (stem + '_shards_manifest.json')) != manifest:
        raise ValueError('closed on-disk manifest differs')
    verify(directory, manifest)
    rows = []
    for part in parts:
        with safe(directory / part['path']).open(encoding='utf-8') as stream:
            rows.extend(json.loads(line) for line in stream)
    if len(rows) != count:
        raise ValueError('actual shard row denominator differs')
    return rows


def prepare():
    authority()
    for path in (CACHE, RAW, EVIDENCE):
        safe(path)
        # worker owns the activity path but creates no directory before dispatch.
        if path.exists():
            raise FileExistsError('old complete/partial namespace is preserved')
    _, rows, labels, binding = source_state()
    from tokenizers import Tokenizer
    tokenizer = Tokenizer.from_file(str(TOKENIZER))
    cases = build_cases(rows, labels, tokenizer)
    for path in (CACHE, RAW, EVIDENCE):
        path.mkdir(parents=True, exist_ok=False)
    writer = ShardWriter(CACHE, 'cases', limit=19_999_999)
    for case in cases:
        writer.append(case)
    manifest = writer.close(lineage=dict(tag=TAG, kind='GOLD_SEPARATED_FROZEN_CASES'))
    verify(CACHE, manifest)
    display = sorted((case['id'] for case in cases), key=lambda identity: sha([TAG, 'DISPLAY', identity]))[:16]
    frozen = dict(info(), status='SPAN_READOUT_CPU_PREPARED', binding=binding,
        cases_manifest=manifest, cases_sha256=sha(cases), display_ids=display,
        selection='tag/source-reference SHA order before answers or scores; train64/language; all natural DEV/TEST',
        models_loaded=0, checkpoints_tensor_loaded=0)
    write(CACHE / 'frozen_reference.json', frozen)
    write(EVIDENCE / 'cpu_contract.json', dict(frozen_reference_sha256=digest(CACHE / 'frozen_reference.json'),
        **{k: v for k, v in frozen.items() if k != 'cases_manifest'}))
    print('[SPAN_READOUT_CPU] full640 natural cases frozen; model/GPU not loaded', flush=True)
    return 0


def validate_activity(value, mode, *, complete=False):
    if mode not in ('prepare', 'evaluate', 'readback'):
        raise ValueError('owned activity mode required')
    if (value.get('schema') != SCHEMA or value.get('tag') != TAG or value.get('mode') != mode
            or value.get('key') != mode or type(value.get('max_wall_sec')) is not int
            or not 60 <= value['max_wall_sec'] <= 1800 or type(value.get('seconds')) not in (int, float)
            or not math.isfinite(value['seconds']) or not 0 <= value['seconds'] <= value['max_wall_sec'] + 30
            or type(value.get('complete')) is not bool or type(value.get('returncode')) is not int
            or value['complete'] != (value['returncode'] == 0)
            or value.get('code_sha256') != info()['code_sha256']):
        raise ValueError('same-code finite owned worker activity required')
    start = datetime.fromisoformat(value['started_at'])
    end = datetime.fromisoformat(value['ended_at'])
    if start.tzinfo is None or end.tzinfo is None or end < start:
        raise ValueError('aware ordered worker timestamps required')
    if complete and (not value['complete'] or value.get('error_type') is not None
                     or not isinstance(value.get('result_sha256'), str)):
        raise Pending('complete successful worker/report activity required')
    return value


def phase_result_path(mode):
    if mode == 'prepare':
        return EVIDENCE / 'cpu_contract.json'
    if mode not in ('evaluate', 'readback'):
        raise ValueError('owned result phase required')
    return EVIDENCE / mode / 'report.json'


def completed_activity(mode):
    value = validate_activity(required(EVIDENCE / ('activity_' + mode + '.json')), mode, complete=True)
    if (value.get('result_path') != str(phase_result_path(mode).relative_to(ROOT))
            or value['result_sha256'] != digest(phase_result_path(mode))
            or value.get('frozen_reference_sha256') != digest(CACHE / 'frozen_reference.json')):
        raise ValueError('worker activity/report/frozen reference identity differs')
    return value


def spent_seconds():
    total = 0.
    for mode in ('prepare', 'evaluate', 'readback'):
        path = safe(EVIDENCE / ('activity_' + mode + '.json'))
        if path.exists():
            total += validate_activity(required(path), mode)['seconds']
    return total


def prepared():
    _, rows, labels, binding = source_state()
    frozen = required(CACHE / 'frozen_reference.json')
    if (frozen.get('status') != 'SPAN_READOUT_CPU_PREPARED' or frozen.get('binding') != binding
            or any(frozen.get(k) != v for k, v in info().items())):
        raise ValueError('same current source/checkpoint/code reference required')
    public = dict(frozen_reference_sha256=digest(CACHE / 'frozen_reference.json'),
        **{k: v for k, v in frozen.items() if k != 'cases_manifest'})
    if required(EVIDENCE / 'cpu_contract.json') != public:
        raise ValueError('public CPU contract binding differs')
    completed_activity('prepare')
    from tokenizers import Tokenizer
    tokenizer = Tokenizer.from_file(str(TOKENIZER))
    cases = read_shards(CACHE, frozen['cases_manifest'], 'cases', CASES)
    reconstructed = build_cases(rows, labels, tokenizer)
    if (sha(cases) != frozen['cases_sha256'] or cases != reconstructed
            or frozen['display_ids'] != sorted((c['id'] for c in cases), key=lambda k: sha([TAG, 'DISPLAY', k]))[:16]):
        raise ValueError('complete source/bank/query/gold reconstruction differs')
    return frozen, cases, tokenizer


def validate_checkpoint_payload(saved, cfg):
    import torch
    expected_keys = {'model', 'cfg', 'step', 'tokenizer_sha256', 'tokenizer_lineage',
                     'training_only_auxiliary', 'auxiliary_method'}
    if (not isinstance(saved, dict) or set(saved) != expected_keys or saved['step'] != 96
            or saved['tokenizer_sha256'] != TOKENIZER_SHA or saved['tokenizer_lineage'] != 'chat32'
            or saved['auxiliary_method'] != dict(tag=TRAIN_TAG, arm='span03')
            or sha(saved['cfg']) != sha(asdict(cfg))
            or cfg.dim != DIM or cfg.n_layers != 14 or cfg.vocab_size != 32768 or cfg.tie_mlp
            or cfg.max_seq_len != CONTEXT or cfg.mtp_aux is not False):
        raise ValueError('strict self checkpoint cfg/tokenizer/tag/arm/96-step identity differs')
    state = saved['training_only_auxiliary']
    if not isinstance(state, dict) or set(state) != {key + '.weight' for key in ('qs', 'ks', 'qe', 'ke')}:
        raise ValueError('exact four saved span projections required')
    for value in state.values():
        if (not isinstance(value, torch.Tensor) or tuple(value.shape) != (RANK, DIM)
                or value.dtype != torch.float32 or not bool(torch.isfinite(value).all())):
            raise ValueError('finite FP32 rank64/dim768 saved projection required')
    if sum(value.numel() for value in state.values()) != PARAMETERS:
        raise ValueError('196608 existing head parameters required')


def fingerprint_state(state):
    import torch
    if hasattr(state, 'state_dict'):
        state = state.state_dict()
    result = hashlib.sha256()
    for name, value in sorted(state.items()):
        value = value.detach().cpu().contiguous()
        result.update((name + str(value.shape) + str(value.dtype)).encode('utf-8'))
        result.update(value.reshape(-1).view(torch.uint8).numpy().tobytes())
    return result.hexdigest().upper()


def load_saved_runtime():
    source, execution = historical_modules()
    if digest(CHECKPOINT) != CHECKPOINT_SHA:
        raise ValueError('self checkpoint SHA changed before tensor loading')
    torch, model, cfg, tokenizer, _ = source.training.load_runtime('parent_ntp')
    from tinylm.infer.generate import _strip
    saved = torch.load(CHECKPOINT, map_location='cpu', weights_only=True)
    validate_checkpoint_payload(saved, cfg)
    body_state = _strip(saved['model'])
    model.load_state_dict(body_state, strict=True)
    head = execution.strict_head(cfg.dim, 'cpu', rank=RANK)
    head.load_state_dict(saved['training_only_auxiliary'], strict=True)
    if (fingerprint_state(model) != fingerprint_state(body_state)
            or fingerprint_state(head) != fingerprint_state(saved['training_only_auxiliary'])):
        raise ValueError('strict saved backbone/head readback differs')
    del saved, body_state
    return torch, model, cfg, tokenizer, head


def prefix_messages(prompt):
    head, tail = '<|im_start|>user\n', '<|im_end|>\n<|im_start|>assistant\n'
    if not isinstance(prompt, str) or not prompt.startswith(head) or not prompt.endswith(tail):
        raise ValueError('exact single-user answer-free ChatML prefix required')
    body = prompt[len(head):-len(tail)]
    if not body or any(marker in body for marker in ('<|im_start|>', '<|im_end|>')):
        raise ValueError('unambiguous original user body required')
    return [dict(role='user', content=body)]


def emit_vocab(model, cfg, tokenizer, prompt):
    from scripts.diag_p106b_question_transfer import emit64
    return emit64(model, cfg, tokenizer, prefix_messages(prompt))


def infer_prefix(model, cfg, tokenizer, head, *, prompt, reference_range):
    """Inference boundary: no case, answer, annotation or gold location input."""
    import torch
    bank = method.build_bank(tokenizer, prompt, reference_range, max_tokens=CONTEXT)
    if len(bank.ids) + MAX_NEW > cfg.max_seq_len or model.training or head.training:
        raise ValueError('complete prefix/eval mode required')
    device = head['qs'].weight.device
    x = torch.tensor([bank.ids], dtype=torch.long, device=device)
    from torch.nn.attention import sdpa_kernel, SDPBackend
    with torch.no_grad(), torch.autocast(device_type=device.type, enabled=False), sdpa_kernel(SDPBackend.MATH):
        hidden = model(x, return_hidden=True)
        start, end = method.boundary_scores(head, hidden, bank)
    starts, ends = start.detach().cpu().tolist(), end.detach().cpu().tolist()
    policies = {policy: asdict(method.select_span(bank, starts, ends, policy)) for policy in method.POLICIES}
    answer, generation = emit_vocab(model, cfg, tokenizer, prompt)
    return dict(bank_sha256=sha(bank_snapshot(bank)), start_scores=starts, end_scores=ends,
        policies=policies, vocabulary=dict(answer=answer, generation=generation))


def validate_vocabulary(value, case, tokenizer):
    if not isinstance(value, dict) or set(value) != {'answer', 'generation'}:
        raise ValueError('exact vocabulary answer/receipt required')
    g = value['generation']
    expected = dict(precision='FP32_MATH', temperature=0., top_k=1, use_cache=True, mtp=False,
        max_new=MAX_NEW, eos_token_available=True, stop_at_eos_requested=True,
        stop_at_eos_effective=True, stop_token_sequences=[[tokenizer.token_to_id('<|im_end|>')]],
        candidate_answers_supplied=False, terminal_only_removed=True,
        prompt_sha256=sha(case['inference']['prompt']), prompt_ids_sha256=sha(case['encoding']['ids']),
        prompt_tokens=len(case['encoding']['ids']))
    if any(g.get(k) != v for k, v in expected.items()):
        raise ValueError('same complete prefix greedy64/KV receipt differs')
    ids, terminal = g.get('generated_ids'), g.get('terminal_ids')
    if (not isinstance(ids, list) or not 1 <= len(ids) <= MAX_NEW
            or any(type(v) is not int or not 0 <= v < 32768 for v in ids)
            or not isinstance(terminal, list) or type(g.get('generated_tokens')) is not int
            or g['generated_tokens'] != len(ids)):
        raise ValueError('bounded real generated IDs required')
    reason = g.get('finish_reason')
    if reason == 'STOP_SEQUENCE':
        if terminal != [tokenizer.token_to_id('<|im_end|>')] or g.get('matched_stop_sequence') != terminal:
            raise ValueError('authenticated terminal EOT required')
    elif reason == 'EOS':
        if terminal != [tokenizer.token_to_id('<eos>')] or terminal[0] is None or g.get('matched_stop_sequence') is not None:
            raise ValueError('authenticated EOS required')
    elif reason != 'MAX_NEW' or terminal or len(ids) != MAX_NEW:
        raise ValueError('unmodified EOT/EOS/MAX_NEW generation reason required')
    if terminal and ids[-1:] != terminal:
        raise ValueError('terminal ID differs from recorded tail')
    content = ids[:-1] if terminal else ids
    if any(value in (tokenizer.token_to_id('<eos>'), tokenizer.token_to_id('<|im_end|>')) for value in content):
        raise ValueError('terminal control ID cannot occur inside actual content')
    decoded = tokenizer.decode(content, skip_special_tokens=False)
    if (decoded != value['answer'] or sha(ids) != g.get('generated_ids_sha256')
            or sha(content) != g.get('content_ids_sha256')
            or hashlib.sha256(decoded.encode('utf-8')).hexdigest().upper() != g.get('body_utf8_sha256')):
        raise ValueError('actual vocabulary IDs/body/terminal re-decode differs')


def score_event(event, case, tokenizer):
    if (event.get('id') != case['id'] or event.get('case_sha256') != sha(case)
            or event.get('bank_sha256') != case['bank_sha256']):
        raise ValueError('same frozen case and inference bank required')
    bank = method.build_bank(tokenizer, case['inference']['prompt'],
                             case['inference']['reference_range'], max_tokens=CONTEXT)
    if bank_snapshot(bank) != case['encoding']:
        raise ValueError('complete original bank reconstruction differs')
    if set(event.get('policies', {})) != set(method.POLICIES):
        raise ValueError('both predeclared readout policies required')
    metrics = {}
    from scripts.p106b_grounded_span import token_f1
    for policy in method.POLICIES:
        prediction = method.select_span(bank, event['start_scores'], event['end_scores'], policy)
        if sha(asdict(prediction)) != sha(event['policies'][policy]):
            raise ValueError('saved boundary scores/policy/substring differ')
        answer = prediction.text or ''
        metrics[policy] = dict(literal=prediction.status == 'OK' and answer == case['gold'].strip(),
            token_f1=token_f1(answer, case['gold']), invalid=prediction.status != 'OK',
            start_correct=prediction.start_index == case['gold_audit']['start_index'],
            end_correct=prediction.end_index == case['gold_audit']['end_index'],
            both_correct=(prediction.start_index == case['gold_audit']['start_index']
                          and prediction.end_index == case['gold_audit']['end_index']))
    validate_vocabulary(event['vocabulary'], case, tokenizer)
    answer = event['vocabulary']['answer']
    metrics['vocabulary'] = dict(literal=answer.strip() == case['gold'].strip(),
        token_f1=token_f1(answer, case['gold']), empty=not answer.strip())
    a, b = case['gold_audit']['start_index'], case['gold_audit']['end_index']
    cover = bank.prefix[bank.offsets[bank.positions[a]][0]:bank.offsets[bank.positions[b]][1]]
    metrics['source_boundary_oracle'] = dict(literal=cover.strip() == case['gold'].strip(),
        scope='GOLD_LOCATION_POSTHOC_ONLY_NOT_HEAD_SELECTION')
    return metrics


def summarize(events, cases, tokenizer):
    if len(events) != CASES or len(cases) != CASES or len({e.get('id') for e in events}) != CASES:
        raise ValueError('exact640 unique actual responses required')
    lookup = {case['id']: case for case in cases}
    if set(lookup) != {event['id'] for event in events}:
        raise ValueError('missing or extra actual response IDs')
    totals = defaultdict(Counter)
    for event in events:
        case = lookup[event['id']]
        metrics = score_event(event, case, tokenizer)
        for lane in ('all', case['split'] + ':' + case['language']):
            for policy, values in metrics.items():
                target = totals[(lane, policy)]
                target['cases'] += 1
                for name, value in values.items():
                    if type(value) in (bool, int, float):
                        target['token_f1_sum' if name == 'token_f1' else name] += value
                if policy in method.POLICIES:
                    target['literal_vs_vocab_' + str(int(values['literal']))
                           + str(int(metrics['vocabulary']['literal']))] += 1
    result = []
    for (lane, policy), value in sorted(totals.items()):
        entry = dict(lane=lane, policy=policy, **dict(value))
        if 'token_f1_sum' in entry:
            entry['token_f1_mean'] = entry['token_f1_sum'] / entry['cases']
        result.append(entry)
    return result


def evaluate():
    frozen, cases, tokenizer = prepared()
    authority()
    target, directory = EVIDENCE / 'evaluate', RAW / 'evaluate'
    safe(target); safe(directory)
    if target.exists() or directory.exists():
        raise FileExistsError('old/partial evaluation is preserved')
    # Rebuild every original source/bank before idle and any model allocation.
    if digest(CHECKPOINT) != CHECKPOINT_SHA:
        raise ValueError('self checkpoint byte identity differs before GPU gate')
    from scripts.p106b_gate_runtime import idle_before_gpu
    idle_before_gpu()
    authority()
    torch, model, cfg, actual_tokenizer, head = load_saved_runtime()
    if sha(actual_tokenizer.to_str()) != sha(tokenizer.to_str()):
        raise ValueError('runtime tokenizer differs from full CPU source preparation')
    before_body, before_head = fingerprint_state(model), fingerprint_state(head)
    model = model.cuda(); head = head.cuda(); model.eval(); head.eval(); head.requires_grad_(False)
    model.freeze_quant()
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    writer = ShardWriter(directory, 'answers', limit=19_999_999)
    events = []
    began = time.perf_counter()
    try:
        for index, case in enumerate(cases):
            authority()
            # Deliberately pass only the two inference fields, never the case.
            value = infer_prefix(model, cfg, actual_tokenizer, head, **dict(case['inference']))
            event = dict(id=case['id'], case_sha256=sha(case), **value)
            score_event(event, case, actual_tokenizer)
            writer.append(event); events.append(event)
            if (index + 1) % 64 == 0:
                print('[SPAN_READOUT_PROGRESS] ' + json.dumps(dict(cases=index + 1, expected=CASES)), flush=True)
            if case['id'] in frozen['display_ids']:
                print('[SPAN_READOUT_SAMPLE] ' + json.dumps(dict(id=case['id'], split=case['split'], language=case['language'],
                    vocabulary=value['vocabulary']['answer'], independent=value['policies']['independent']['text'],
                    valid_joint=value['policies']['valid_joint']['text']), ensure_ascii=False), flush=True)
        model.clear_quant()
        after_body, after_head = fingerprint_state(model), fingerprint_state(head)
        if before_body != after_body or before_head != after_head or digest(CHECKPOINT) != CHECKPOINT_SHA:
            raise ValueError('readout changed saved backbone/head/checkpoint')
        lineage = dict(tag=TAG, checkpoint_sha256=CHECKPOINT_SHA, core_sha256=before_body, head_sha256=before_head,
            cases_sha256=frozen['cases_sha256'], code_sha256=info()['code_sha256'])
        manifest = writer.close(lineage=lineage)
        verify(directory, manifest)
        result = dict(info(), status='SPAN_READOUT_ACTUAL_COLLECTED', raw_directory=str(directory.relative_to(ROOT)),
            raw_manifest=manifest, lineage=lineage, cases_sha256=frozen['cases_sha256'],
            core_before=before_body, core_after=after_body, head_before=before_head, head_after=after_head,
            checkpoint_sha256_after=digest(CHECKPOINT), summary=summarize(events, cases, actual_tokenizer),
            display_ids=frozen['display_ids'], actual_cases=len(events), whole_seconds=time.perf_counter() - began,
            models_loaded=1, new_head_fitting=False, optimizer_updates=0, checkpoint_writes=0,
            interpretation='existing trained-head extractive readout versus same-body vocabulary generation; not assistant improvement')
        write(target / 'report.json', result)
    finally:
        model.clear_quant()
        del model, head
        gc.collect(); torch.cuda.empty_cache()
    return 0


def readback():
    frozen, cases, tokenizer = prepared()
    completed_activity('evaluate')
    report = required(EVIDENCE / 'evaluate/report.json')
    expected_directory = RAW / 'evaluate'
    if (report.get('status') != 'SPAN_READOUT_ACTUAL_COLLECTED'
            or any(report.get(k) != v for k, v in info().items())
            or report.get('raw_directory') != str(expected_directory.relative_to(ROOT))
            or report.get('actual_cases') != CASES or report.get('cases_sha256') != frozen['cases_sha256']
            or report.get('display_ids') != frozen['display_ids']
            or report.get('checkpoint_sha256_after') != CHECKPOINT_SHA
            or report.get('core_before') != report.get('core_after')
            or report.get('head_before') != report.get('head_after')
            or not all(isinstance(report.get(k), str) and len(report[k]) == 64 for k in ('core_before', 'head_before'))):
        raise ValueError('complete same-code/CP/backbone/head evaluation receipt required')
    lineage = dict(tag=TAG, checkpoint_sha256=CHECKPOINT_SHA, core_sha256=report['core_before'],
        head_sha256=report['head_before'], cases_sha256=frozen['cases_sha256'], code_sha256=info()['code_sha256'])
    if report.get('lineage') != lineage or report.get('raw_manifest', {}).get('lineage') != lineage:
        raise ValueError('actual raw scores/answers lineage differs')
    events = read_shards(expected_directory, report['raw_manifest'], 'answers', CASES)
    summary = summarize(events, cases, tokenizer)
    if summary != report['summary']:
        raise ValueError('complete raw boundary/vocabulary/source recount differs')
    output = dict(info(), status='SPAN_READOUT_RAW_RECOUNT_COMPLETE', cases=CASES,
        summary=summary, cases_sha256=frozen['cases_sha256'],
        evaluation_report_sha256=digest(EVIDENCE / 'evaluate/report.json'),
        raw_manifest_sha256=digest(expected_directory / 'answers_shards_manifest.json'),
        core_before=report['core_before'], core_after=report['core_after'],
        head_before=report['head_before'], head_after=report['head_after'],
        models_loaded=0, new_training=0, new_checkpoint_writes=0,
        limitations=['gold positions are posthoc oracle metrics only',
                    'literal source target is not semantic truth',
                    'extractive head output is not ordinary vocabulary generation improvement'])
    write(EVIDENCE / 'readback/report.json', output)
    print('[SPAN_READOUT_RECOUNT] ' + json.dumps([row for row in summary if row['lane'] == 'all'],
        ensure_ascii=False), flush=True)
    return 0


def worker(mode, max_wall_sec):
    if mode not in MODES or type(max_wall_sec) is not int or not 60 <= max_wall_sec <= 1800:
        raise ValueError('registered phase and60..1800 second wall required')
    if mode in ('source', 'preflight'):
        authority()
        source_state() if mode == 'source' else prepared()
        print('[SPAN_READOUT_PREFLIGHT] exact source/reference verified; model0', flush=True)
        return 0
    activity = safe(EVIDENCE / ('activity_' + mode + '.json'))
    if activity.exists():
        raise FileExistsError('prior worker activity preserved; no implicit retry')
    began, started = time.perf_counter(), datetime.now(timezone.utc).isoformat()
    code, error = 9, None
    metadata = info()
    try:
        if max_wall_sec > min(authority(), ACTIVE_LIMIT - spent_seconds()):
            raise Pending('requested worker exceeds remaining authority/activity cap')
        from scripts.p106b_gate_runtime import wall_limit
        with wall_limit(max_wall_sec):
            if mode == 'prepare':
                code = prepare()
            elif mode == 'evaluate':
                code = evaluate()
            elif mode == 'readback':
                code = readback()
            else:
                raise ValueError('registered activity worker mode required')
        if type(code) is not int:
            raise ValueError('explicit integer worker outcome required')
        if code == 0 and (not phase_result_path(mode).is_file()
                or not (CACHE / 'frozen_reference.json').is_file()
                or info()['code_sha256'] != metadata['code_sha256']):
            raise ValueError('exit0 requires the complete same-code owned result/reference')
        return code
    except BaseException as exc:
        error = type(exc).__name__
        code = 130 if isinstance(exc, KeyboardInterrupt) else 8 if isinstance(exc, (Pending, FileNotFoundError, FileExistsError)) else 9
        raise
    finally:
        path = phase_result_path(mode)
        reference = CACHE / 'frozen_reference.json'
        write(activity, dict(schema=SCHEMA, tag=TAG, key=mode, mode=mode,
            seconds=time.perf_counter() - began, max_wall_sec=max_wall_sec, returncode=code,
            complete=code == 0, error_type=error, started_at=started,
            ended_at=datetime.now(timezone.utc).isoformat(), code_sha256=metadata['code_sha256'],
            result_path=str(path.relative_to(ROOT)), result_sha256=digest(path) if path.is_file() else None,
            frozen_reference_sha256=digest(reference) if reference.is_file() else None))


def phase_commands(mode, max_wall_sec):
    if mode not in MODES or type(max_wall_sec) is not int or not 60 <= max_wall_sec <= 1800:
        raise ValueError('registered phase and60..1800 second wall required')
    py = [sys.executable, '-B', '-X', 'utf8']
    driver = py + ['scripts/diag_p106b_span_readout.py']
    prior = 'source' if mode in ('source', 'prepare') else 'preflight'
    return [('REGRESSION', py + ['-m', 'unittest', 'scripts.test_p106b_span_readout',
                                 'scripts.test_p106b_span_readout_driver', '-v']),
            ('PREFLIGHT', driver + ['--mode', prior, '--worker', '--execute', '--max-wall-sec', '600']),
            ('EXECUTE', driver + ['--mode', mode, '--worker', '--execute', '--max-wall-sec', str(max_wall_sec)])]


def launch(command, timeout):
    """Supervise exactly this child session; never signal unrelated user PIDs."""
    process = subprocess.Popen(command, cwd=ROOT, stdin=subprocess.DEVNULL, start_new_session=True)
    try:
        return process.wait(timeout=timeout)
    except (subprocess.TimeoutExpired, KeyboardInterrupt):
        interrupted = sys.exc_info()[0] is KeyboardInterrupt
        if process.poll() is None and os.getpgid(process.pid) == process.pid:
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                if process.poll() is None:
                    os.killpg(process.pid, signal.SIGKILL)
                process.wait(timeout=5)
        return 130 if interrupted else 124


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=MODES, required=True)
    parser.add_argument('--max-wall-sec', type=int, default=1200)
    parser.add_argument('--worker', action='store_true')
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--execute', action='store_true')
    action.add_argument('--check-only', action='store_true')
    args = parser.parse_args(argv)
    phases = phase_commands(args.mode, args.max_wall_sec)
    if args.check_only:
        value = dict(info(), model_loading='NOT_RUN', check_only=True,
            model_modules_present=[name for name in ('torch', 'transformers', 'datasets') if name in sys.modules])
        print('[SPAN_READOUT_CHECK_ONLY] ' + json.dumps(value, ensure_ascii=False, sort_keys=True), flush=True)
        return 0
    try:
        if args.worker:
            return worker(args.mode, args.max_wall_sec)
        return pipeline(phases, lambda command: launch(command, min(args.max_wall_sec + 120, authority())),
            lambda line: print(line, flush=True), experiment='P106B_SPAN_READOUT_' + args.mode)['returncode']
    except BaseException as exc:
        if isinstance(exc, SystemExit):
            raise
        code = 130 if isinstance(exc, KeyboardInterrupt) else 8 if isinstance(exc, (Pending, FileNotFoundError, FileExistsError)) else 9
        print('[SPAN_READOUT_FINAL] ' + type(exc).__name__ + ': ' + str(exc), flush=True)
        return code


if __name__ == '__main__':
    raise SystemExit(main())
