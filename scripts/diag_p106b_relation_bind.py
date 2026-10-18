#!/usr/bin/env python3
"""Relation CE/ranking preparation and user-run GPU experiment.

prepare is tokenizer/data-only CPU work. check-only and --help never load a
learned model. cost/train/evaluate require --execute and are user GPU actions;
the CPU preparation session does not execute them. Never overwrite old output.
"""
from __future__ import annotations
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import argparse
from collections import Counter, defaultdict
from dataclasses import asdict
from datetime import datetime, timezone
import json
import math
import os
import random
import tempfile
import time
from scripts import p106b_relation_bind_data as data
from scripts import p106b_night_qa_data as original
from scripts.p106b_shards import ShardWriter, verify

TAG = data.TAG
LOCAL = ROOT / 'test_result/evidence/local' / TAG
CORPUS = LOCAL / 'corpus'
EVIDENCE = ROOT / 'test_result/evidence' / TAG
ARMS = ('ce', 'contrast')
WEIGHTS = dict(ce=0., contrast=.1)
PARENT = ROOT / 'runs/ckpt/m100s10_ko-en_300M_dense_chat32_p090b_s1337.pt'
PARENT_SHA = '12E18658CDCD0AFEBE5A87073DC8977304C0D490A03A8471779D514FBB0D9950'
PARENT_CORE = 'E854AB4EC2E505DDC581CE08C94F9C8B4A8081E456AFBA193DF28A877E34A193'
NATIVE = ROOT / 'data_cache/ko-en_601000000_chat32'
NATIVE_TRAIN_SHA = 'DBD12235B4A1478177246B4BD5214C8B8BBF10D077CBA80304690AD12A8E59A2'
NATIVE_VAL_SHA = 'AD7EFB0DBD0D830A216B4D21A91C8ACB3FC41DAE2B23A3A55999AE8727AA374C'
UPDATES = 768
CODE = ('scripts/diag_p106b_relation_bind.py', 'scripts/p106b_relation_bind_data.py',
        'scripts/p106b_relation_bind_loss.py', 'scripts/test_p106b_relation_bind_data.py',
        'scripts/test_p106b_relation_bind_loss.py', 'scripts/test_p106b_relation_bind.py',
        'scripts/p106b_shards.py', 'scripts/p106b_native_windows.py',
        'scripts/diag_p101a_mtp_parity.py', 'tinylm/infer/generate.py',
        'tinylm/config.py', 'tinylm/model/modules.py', 'tinylm/model/ternary.py',
        'tinylm/model/__init__.py', 'tinylm/model/ternary_kernel.py',
        'tinylm/model/lut.py', 'tinylm/model/lut_cpu.py', 'tinylm/model/sparse_connectivity.py',
        'tinylm/model/scout_memory.py', 'tinylm/model/scout_coda.py',
        'tinylm/train/muon.py', 'tinylm/train/optimizer_audit.py',
        'scripts/p106b_gate_runtime.py', 'scripts/train_sft_p090.py')
CODE += ('scripts/p106b_relation_bind_entry.py', 'scripts/test_p106b_relation_bind_entry.py',
         'scripts/p106b_stage_receipt.py')


class PrerequisitePending(RuntimeError):
    """An unexecuted stage, not an observed model-quality failure."""


def stage_report(path):
    if not Path(path).is_file(): raise PrerequisitePending('required earlier stage has not run: ' + str(path))
    return required(path)


def failure_status(exc):
    if isinstance(exc, KeyboardInterrupt): return 'INTERRUPTED', 130
    if isinstance(exc, PrerequisitePending): return 'PREREQUISITE_NOT_RUN', 8
    from scripts.p106b_gate_runtime import PrerequisiteHold
    if isinstance(exc, PrerequisiteHold):
        return 'RESOURCE_PRECONDITION_NOT_RUN', 8
    if type(exc).__module__.startswith('torch') and type(exc).__name__ == 'OutOfMemoryError':
        return 'ACTUAL_RESOURCE_OOM', 8
    return 'TOOL_ERROR', 9


def safe(path):
    path = Path(path)
    if '..' in path.parts: raise ValueError('unresolved output path')
    try: path.absolute().relative_to(ROOT)
    except ValueError: raise ValueError('research outputs must stay inside repository')
    for parent in (path, *path.parents):
        if parent.is_symlink(): raise ValueError('linked research output/source')
        if parent == ROOT: break
    return path


def write(path, value):
    path = safe(path)
    body = (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + '\n').encode('utf-8')
    if len(body) >= 20_000_000: raise ValueError('split result before20MB')
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream: stream.write(body)


def required(path):
    if not original.regular(path): raise FileNotFoundError(str(path))
    return json.loads(Path(path).read_text(encoding='utf-8'))


def info():
    from scripts import p106b_night_course as old
    paths = sorted(set(CODE + old.CODE + ('scripts/diag_p106b_night_foundation.py',
                                         'scripts/p106b_night_foundation_data.py')))
    return dict(schema='P106B_RELATION_BIND_RUNTIME_V1', tag=TAG,
        code_sha256={name: original.digest(ROOT / name) for name in paths},
        parent=str(PARENT.relative_to(ROOT)), parent_sha256=PARENT_SHA,
        expected_parent_core_sha256=PARENT_CORE, tokenizer_sha256=original.TOK_SHA,
        arms=list(ARMS), weights=WEIGHTS, micro_bs=8, accum=16, seq=1024,
        grad_checkpoint=True, compile='default', seed=1337, epochs=4, updates=UPDATES,
        adam_lr=5e-5, muon_lr=2e-4, optimizer='AdamW+Muon_RMS4',
        schedule='constant', fresh_optimizer=True, weight_decay=0., grad_clip=1.,
        weight_decay_scope='explicit zero in every actual AdamW/Muon group, including embedding',
        positive_rows_per_pass=24576, crossed_scoring_rows_per_pass=4096,
        native_targets_per_update=8192, mtp=False, teacher_calls=0,
        extra_inference_parameters=0, negative_authority='code-generated fictional relation table only',
        comparison='same positive/cross inputs and paths; only relation lambda0/.1 differs',
        observed_gpu_memory='NOT_RUN', meaningful_model_training='NOT_RUN',
        formal_train_ready=False, checkpoint_policy='final weight-only per arm; cost8 writes none')


def old_source():
    from scripts.diag_p106b_night_foundation import read_qa_source
    report, rows = read_qa_source()
    if (len(rows['train']) != 8192 or len(rows['replay']) != 4096
            or not rows['dev'] or not rows['test']):
        raise ValueError('exact existing natural8192/replay4096 and independent DEV/TEST required')
    return report, rows


def encode_old(rows, tok):
    from scripts.p106b_night_course import records
    return records(rows['train'], rows['replay'], tok)


def record_identity(rec):
    return data.sha(dict(x=rec.x, y=rec.y, segments=rec.segments))


def relation_summary(rows, tok):
    counts = Counter(); lengths = Counter(); records = []
    for b in rows:
        pos, cross = data.encode_bundle(b, tok)
        n = [r.targets - 1 for r in pos]
        if n[0] != n[1]: raise ValueError('first pilot requires equal actual candidate BPE lengths')
        lengths[str(n[0])] += 1
        for rec in pos: counts.update(positive_rows=1, x_tokens=rec.x_tokens, assistant_targets=rec.targets)
        for rec in cross: counts.update(crossed_rows=1, crossed_x_tokens=rec.x_tokens,
                                         crossed_scored_content_targets=rec.targets - 1)
        records.append([b['bundle_id'], [record_identity(r) for r in pos],
                        [record_identity(r) for r in cross]])
    return dict(counts=dict(counts), candidate_content_lengths=dict(lengths),
        actual_encoded_records_sha256=data.sha(records), independent_fact_graphs=len({b['group_id'] for b in rows}),
        language_family_counts={l + '|' + f: sum(b['language'] == l and b['family'] == f for b in rows)
            for l in ('ko', 'en') for f in data.FAMILIES}, shortcuts=data.shortcut_counts(rows))


def exposures(natural, replay, relations):
    counts = Counter()
    for pair in natural:
        for rec in pair: counts.update(positive_rows=1, x_tokens=rec.x_tokens, assistant_targets=rec.targets)
    for rec in replay: counts.update(positive_rows=1, x_tokens=rec.x_tokens, assistant_targets=rec.targets)
    counts.update(relations['counts'])
    return dict(per_pass=dict(counts), four_pass={k: 4 * v for k, v in counts.items()},
        padded_positive_slots_four_pass=UPDATES * 8 * 16 * 1024,
        padded_crossed_slots_four_pass=4 * 4096 * 1024,
        native_targets_four_pass=UPDATES * 8192,
        padded_slots_not_actual_tokens=True, cross_is_not_positive_supervision=True)


def schedule_proof():
    from scripts import p106b_relation_bind_loss as loss
    output = []
    for epoch in range(4):
        groups = loss.schedule(8192, 2048, 4096, epoch)
        seen = {kind: [] for kind in ('natural', 'relation', 'replay')}
        for group in groups:
            if len(group) != 16: raise ValueError('exact accumulation16 required')
            for micro in group: seen[micro.kind].extend(micro.indices)
        if (len(groups) != 192 or sorted(seen['natural']) != list(range(8192))
                or sorted(seen['relation']) != list(range(2048))
                or sorted(seen['replay']) != list(range(4096))):
            raise ValueError('schedule omitted/repeated a source or changed update count')
        output.append(dict(epoch=epoch + 1, updates=len(groups),
            schedule_sha256=data.sha([[asdict(m) for m in g] for g in groups])))
    return output


def evaluation_input_proof(cases, tok):
    from tinylm.chat.serialize import serialize
    entries = []; counts = Counter()
    for case in cases:
        if [m['role'] for m in case['messages']] != ['user']:
            raise ValueError('no gold answer/history candidate in first-answer evaluation input')
        prompt = serialize(dict(messages=case['messages']), 'chatml', add_generation_prompt=True)
        ids = tok.encode(prompt).ids
        if not ids or len(ids) + 128 > 1024:
            raise ValueError('complete evaluation input plus128 generation budget required')
        counts[case['lane'] + '|' + case['language']] += 1
        entries.append([case['id'], len(ids), data.sha(ids)])
    return dict(cases_sha256=data.sha(cases), actual_prompt_ids_sha256=data.sha(entries),
        responses=len(cases), lane_counts=dict(counts), max_prompt_tokens=max(e[1] for e in entries),
        context=1024, generation_budget=128, oracle_candidates_in_generation=False)


def prepare():
    import torch
    from tokenizers import Tokenizer
    from scripts import p106b_night_course as old
    from scripts import p106b_night_foundation_data as foundation
    from scripts.diag_p106b_night_train import special_ids
    for target in (CORPUS, EVIDENCE):
        safe(target)
        if target.exists(): raise FileExistsError('old preparation namespace preserved: ' + str(target))
    metadata = info()
    if original.digest(original.TOKENIZER) != original.TOK_SHA: raise ValueError('pinned tokenizer changed')
    tok = Tokenizer.from_file(str(original.TOKENIZER)); pad, eot, _ = special_ids(tok)
    source_report, rows = old_source(); natural, replay = encode_old(rows, tok)
    # Selection observes only source facts and actual token lengths, never model output.
    def eligible(bundle):
        pos, _ = data.encode_bundle(bundle, tok)
        return pos[0].targets == pos[1].targets
    relations = data.generate(eligible=eligible)
    relation_reports = {s: relation_summary(values, tok) for s, values in relations.items()}
    evaluation_proof = evaluation_input_proof(evaluation_cases(rows, relations), tok)
    actual = exposures(natural, replay, relation_reports['train'])
    if actual['per_pass']['positive_rows'] != 24576: raise ValueError('positive exposure changed')
    for name, identity in (('train.bin', NATIVE_TRAIN_SHA), ('val.bin', NATIVE_VAL_SHA)):
        if original.digest(NATIVE / name) != identity: raise ValueError('native read-only source changed')
    length = (NATIVE / 'train.bin').stat().st_size // 2
    if length != foundation.NATIVE_TRAIN_TOKENS: raise ValueError('native TRAIN size differs')
    blocks = random.Random(20261017).sample(range((length - 1) // 1025), UPDATES * 8)
    native_offsets = [b * 1025 for b in blocks]
    if torch.cuda.is_initialized(): raise ValueError('CPU preparation initialized CUDA')
    CORPUS.mkdir(parents=True, exist_ok=False)
    manifests = {}
    for split, values in relations.items():
        writer = ShardWriter(CORPUS, split)
        for bundle in values: writer.append(bundle)
        manifests[split] = writer.close(lineage=dict(tag=TAG, split=split, code_facts_only=True))
        verify(CORPUS, manifests[split])
    result = dict(metadata, status='CPU_DATA_AND_ENCODER_VERIFIED', manifests=manifests,
        natural_source_report=str((old.CORPUS / 'report.json').relative_to(ROOT)),
        natural_source_sha256=original.digest(old.CORPUS / 'report.json'),
        natural_manifest_sha256=data.sha(source_report['manifests']),
        relation_reports=relation_reports, exposure=actual, schedules=schedule_proof(),
        evaluation_input_proof=evaluation_proof,
        native_access='INDEXED_TRAIN_ONLY', native_train_file='data_cache/ko-en_601000000_chat32/train.bin',
        native_train_offsets=native_offsets, native_train_sha256=NATIVE_TRAIN_SHA, native_val_sha256=NATIVE_VAL_SHA,
        pad=pad, eot=eot, cuda_initialized=False, model_loaded=False, model_forward=False,
        optimizer_updates=0, checkpoint_writes=0,
        eval_scope='new fictional fact assignments; same names and role families; test facts64 translated into128 bundles',
        natural_eval_scope='previously observed development cohort, not a new independent TEST')
    write(CORPUS / 'report.json', result)
    summary = {k: v for k, v in result.items() if k not in ('manifests', 'native_train_offsets')}
    summary.update(corpus_report_sha256=original.digest(CORPUS / 'report.json'))
    write(EVIDENCE / 'cpu_contract.json', summary)
    print('[RELATION_CPU_PREPARED] ' + json.dumps(dict(status=result['status'],
        counts={s: len(v) for s, v in relations.items()}, exposure=actual,
        independent_graphs={s: relation_reports[s]['independent_fact_graphs'] for s in relations},
        model_loading=False, cuda_initialized=False), ensure_ascii=False), flush=True)
    return 0


def read_prepared():
    frozen = stage_report(CORPUS / 'report.json')
    if frozen.get('status') != 'CPU_DATA_AND_ENCODER_VERIFIED' or any(frozen.get(k) != v for k, v in info().items()):
        raise ValueError('same-code/parent/recipe CPU preparation required')
    if original.digest(original.TOKENIZER) != original.TOK_SHA: raise ValueError('tokenizer changed')
    source_report, rows = old_source()
    from scripts import p106b_night_course as old
    if (frozen['natural_source_sha256'] != original.digest(old.CORPUS / 'report.json')
            or frozen['natural_manifest_sha256'] != data.sha(source_report['manifests'])):
        raise ValueError('natural/replay source changed')
    relations = {}
    for split, manifest in frozen['manifests'].items():
        verify(CORPUS, manifest); values = []
        for shard in manifest['shards']:
            with (CORPUS / shard['path']).open(encoding='utf-8') as stream:
                values.extend(json.loads(line) for line in stream)
        relations[split] = values
    data.validate_splits(relations)
    if {s: len(v) for s, v in relations.items()} != data.COUNTS:
        raise ValueError('frozen relation count changed')
    if frozen['schedules'] != schedule_proof(): raise ValueError('schedule changed')
    proof = required(EVIDENCE / 'cpu_contract.json')
    if proof['corpus_report_sha256'] != original.digest(CORPUS / 'report.json'):
        raise ValueError('CPU input proof changed')
    return frozen, rows, relations


def preflight():
    import torch
    from tokenizers import Tokenizer
    frozen, rows, relations = read_prepared()
    tok = Tokenizer.from_file(str(original.TOKENIZER))
    natural, replay = encode_old(rows, tok)
    for split in data.SPLITS:
        if relation_summary(relations[split], tok) != frozen['relation_reports'][split]:
            raise ValueError('actual source encoder differs from CPU contract')
    if (exposures(natural, replay, frozen['relation_reports']['train']) != frozen['exposure']
            or evaluation_input_proof(evaluation_cases(rows, relations), tok) != frozen['evaluation_input_proof']):
        raise ValueError('actual training/evaluation consumer proof differs')
    if torch.cuda.is_initialized(): raise ValueError('data-only preflight initialized CUDA')
    print('[RELATION_PREFLIGHT] exact data/code/tokenizer/target proof; model/GPU not loaded; quality NOT_RUN', flush=True)
    return 0


def checkpoint(arm):
    if arm not in ARMS: raise ValueError('explicit registered arm required')
    return ROOT / 'runs/ckpt' / ('m100s10_ko-en_relation_' + TAG + '_' + arm + '.pt')


def load_parent():
    from scripts import diag_p101a_sft_mtp as runtime
    torch, base, cfg, tok, initial = runtime.load_runtime('parent_ntp')
    if initial != PARENT_CORE: raise ValueError('actual initial parent body differs')
    return torch, base, cfg, tok, initial


def make_optimizers(model):
    """Local explicit WD0 repair; never change the frozen old optimizer helper.

    The old helper sets matrix WD0 but can retain embedding AdamW WD.1.
    Both new arms explicitly use all-group WD0 and report the real groups.
    """
    from scripts import diag_p101a_sft_mtp as runtime
    adam, muon = runtime.optimizers(model)
    receipts = []
    for name, opt in (('adamw', adam), ('muon', muon)):
        for index, group in enumerate(opt.param_groups):
            group['lr'] *= .5
            group['weight_decay'] = 0.
            receipts.append(dict(optimizer=name, group=index, lr=group['lr'],
                weight_decay=group['weight_decay'], tensors=len(group['params']),
                parameters=sum(p.numel() for p in group['params'])))
    if not receipts or any(r['weight_decay'] != 0. for r in receipts):
        raise ValueError('actual all-group optimizer WD0 was not enforced')
    return adam, muon, receipts


def micro_records(micro, natural, relation_records, replay):
    if micro.kind == 'natural': return [r for i in micro.indices for r in natural[i]]
    if micro.kind == 'relation': return [r for i in micro.indices for r in relation_records[i][0]]
    if micro.kind == 'replay': return [replay[i] for i in micro.indices]
    raise ValueError('unknown lane')


def denominators(group, natural, relation_records, replay):
    words = sum(r.targets for m in group for r in micro_records(m, natural, relation_records, replay))
    edges = sum(2 * len(m.indices) for m in group if m.kind == 'relation')
    if words <= 0: raise ValueError('zero correct assistant target update')
    return words, edges


def cost_budget(hours):
    if not math.isfinite(hours) or hours <= 0: raise ValueError('positive user wall budget required')
    estimates = {}
    for arm in ARMS:
        r = stage_report(EVIDENCE / ('cost_' + arm) / 'report.json')
        if (r.get('status') != 'COST8_COMPLETE' or r.get('updates') != 8 or r.get('arm') != arm
                or r.get('code_sha256') != info()['code_sha256']
                or r.get('corpus_sha256') != original.digest(CORPUS / 'report.json')
                or r.get('initial_core_sha256') != PARENT_CORE or not r.get('crossed_rows', 0)
                or r.get('checkpoint_written') is not False):
            raise ValueError('both same-code/corpus/parent successful cost8 reports required')
        warm = r['step_seconds'][1:]
        if len(warm) != 7 or any(not math.isfinite(v) or v <= 0 for v in warm):
            raise ValueError('seven finite warmed update times required')
        estimates[arm] = max(warm) * UPDATES + 600
    forecast = sum(estimates.values()) + 3600
    return dict(per_arm_seconds=estimates, forecast_including_evaluation_sec=forecast,
        user_budget_sec=hours * 3600, fits=forecast <= hours * 3600,
        scope='conservative estimate, not an upper bound; no adoption/quality claim')


def encoded_relations(bundles, tok, frozen, split):
    if relation_summary(bundles, tok) != frozen['relation_reports'][split]:
        raise ValueError('actual relation encoder differs from frozen CPU proof')
    return [data.encode_bundle(bundle, tok) for bundle in bundles]


def native_probe(base):
    """Fixed first32 VAL crops, FP32 MATH; neither full VAL nor BF16 train loss."""
    import numpy as np
    import torch
    from torch.nn.attention import sdpa_kernel, SDPBackend
    from tinylm.train import mtp_sft as core
    if original.digest(NATIVE / 'val.bin') != NATIVE_VAL_SHA: raise ValueError('native VAL changed')
    values = np.memmap(NATIVE / 'val.bin', mode='r', dtype=np.uint16)
    total = 0.; count = 0
    base.eval(); base.freeze_quant()
    try:
        with torch.no_grad(), sdpa_kernel(SDPBackend.MATH), torch.autocast('cuda', enabled=False):
            for start in range(0, 32 * 1024, 1024):
                ids = values[start:start + 1025].astype('int64').tolist()
                if len(ids) != 1025: raise ValueError('native32 crop incomplete')
                x = torch.tensor([ids[:-1]], device='cuda'); y = torch.tensor([ids[1:]], device='cuda')
                sums, counts = core.components(base, base(x, return_hidden=True), y, torch.ones_like(y),
                                               horizons=(), checkpoint_heads=False)
                total += float(sums[1]); count += counts[1]
    finally:
        base.clear_quant(); base.train()
    if count != 32768 or not math.isfinite(total): raise ValueError('native32 denominator/nonfinite error')
    return dict(ce=total / count, targets=count, windows=32, precision='FP32_MATH',
        val_sha256=NATIVE_VAL_SHA, scope='fixed first32 contiguous1024 crops, not full VAL')


def dev_probe(base, rows, relations, tok, pad, eot):
    import torch
    from tinylm.train import mtp_sft as core
    from scripts import p106b_relation_bind_loss as loss
    selected = rows['dev'][:64]
    records = [core.encode_record(pair['views'][str(v)], tok) for pair in selected for v in (0, 1)]
    records += [r for b in relations for r in data.encode_bundle(b, tok)[0]]
    total = 0.; words = 0
    base.eval(); base.freeze_quant()
    try:
        with torch.no_grad():
            for start in range(0, len(records), 8):
                chunk = records[start:start + 8]
                x, _, _ = core.pad_records(chunk, pad, 'cuda', fixed_width=1024, batch_size=len(chunk))
                with torch.autocast('cuda', dtype=torch.bfloat16):
                    content, ends, _ = loss.sequence_terms(base, base(x, return_hidden=True), chunk, eot, False)
                total -= float((content + ends).sum()); words += sum(r.targets for r in chunk)
    finally:
        base.clear_quant(); base.train()
    if not words or not math.isfinite(total): raise ValueError('invalid DEV correct CE')
    return dict(ce=total / words, assistant_targets=words, natural_bundles=len(selected),
        relation_bundles=len(relations), precision='BF16_AUTO_head_FP32',
        scope='fixed source-order DEV correct CE; no test selection or free-answer claim')


def run(arm, cost, seconds, hours):
    from scripts import p106b_relation_bind_loss as loss
    from scripts import diag_p101a_sft_mtp as runtime
    from scripts.p106b_native_windows import reader
    from scripts.p106b_gate_runtime import idle_before_gpu, wall_limit
    from tinylm.train import mtp_sft as core
    frozen, rows, relation_rows = read_prepared()
    target = safe(EVIDENCE / (('cost_' if cost else 'train_') + arm))
    if target.exists() or (not cost and checkpoint(arm).exists()):
        raise FileExistsError('previous run/checkpoint preserved; new stage needed')
    if not cost:
        budget = cost_budget(hours)
        print('[RELATION_BUDGET] ' + json.dumps(budget), flush=True)
        if not budget['fits']: raise PrerequisitePending('both arms/evaluation exceed declared user budget')
    for name, identity in (('train.bin', NATIVE_TRAIN_SHA), ('val.bin', NATIVE_VAL_SHA)):
        if original.digest(NATIVE / name) != identity: raise ValueError('native source changed')
    idle_before_gpu()
    target.mkdir(parents=True, exist_ok=False)
    events = ShardWriter(target, 'updates')
    began = time.perf_counter()
    write(target / 'start.json', dict(arm=arm, phase='cost' if cost else 'train',
        corpus_sha256=original.digest(CORPUS / 'report.json'), code_sha256=info()['code_sha256'],
        started_at=datetime.now(timezone.utc).isoformat(), max_wall_sec=seconds))
    try:
        with wall_limit(seconds):
            torch, base, cfg, tok, initial = load_parent()
            from scripts.diag_p106b_night_train import special_ids
            pad, eot, _ = special_ids(tok)
            natural, replay = encode_old(rows, tok)
            relation_records = encoded_relations(relation_rows['train'], tok, frozen, 'train')
            if exposures(natural, replay, frozen['relation_reports']['train']) != frozen['exposure']:
                raise ValueError('actual positive/cross consumers differ from frozen contract')
            native = reader(ROOT, frozen)
            base = base.cuda()
            torch.backends.cuda.matmul.allow_tf32 = False; torch.backends.cudnn.allow_tf32 = False
            torch.cuda.reset_peak_memory_stats()
            native_before = None if cost else native_probe(base)
            dev_before = None if cost else dev_probe(base, rows, relation_rows['dev'], tok, pad, eot)
            os.environ['TORCHINDUCTOR_CACHE_DIR'] = tempfile.mkdtemp(prefix='p106b_relation_')
            model = torch.compile(base, mode='default')
            adam, muon, optimizer_receipts = make_optimizers(base)
            print('[RELATION_ACTUAL_OPTIMIZERS] ' + json.dumps(optimizer_receipts), flush=True)
            totals = Counter(); history = []; times = []; grad_max = 0.; clips = 0
            updates = 0
            for epoch in range(4):
                for group in loss.schedule(len(natural), len(relation_records), len(replay), epoch):
                    tick = time.perf_counter(); words, edges = denominators(group, natural, relation_records, replay)
                    for opt in (adam, muon): opt.zero_grad(set_to_none=True)
                    stats = torch.zeros(3, device='cuda'); observed_words = observed_edges = 0
                    for micro in group:
                        records = micro_records(micro, natural, relation_records, replay)
                        if len(records) != 8: raise ValueError('physical positive micro8 required')
                        x, y, seg = core.pad_records(records, pad, 'cuda', fixed_width=1024, batch_size=8)
                        with torch.autocast('cuda', dtype=torch.bfloat16):
                            hidden = model(x, return_hidden=True)
                            if micro.kind == 'relation':
                                content, ends, n = loss.sequence_terms(base, hidden, records, eot)
                                correct = -(content + ends).sum()
                                crossed = [r for i in micro.indices for r in relation_records[i][1]]
                                cx, _, _ = core.pad_records(crossed, pad, 'cuda', fixed_width=1024, batch_size=8)
                                ch = model(cx, return_hidden=True)
                                cc, ce, cn = loss.sequence_terms(base, ch, crossed, eot)
                                matrix = loss.score_matrix(loss.content_means(content, n), loss.content_means(cc, cn))
                                ranking = loss.row_contrast_sum(matrix)
                                # Same graph at lambda0. EOT of crossed answers is NOT a ranking target.
                                ranking = ranking + ce.sum() * 0.
                                observed_edges += 2 * len(micro.indices)
                                totals.update(crossed_rows=len(crossed), crossed_x_tokens=sum(r.x_tokens for r in crossed),
                                    crossed_scored_content_targets=sum(r.targets - 1 for r in crossed),
                                    padded_crossed_slots=cx.numel())
                            else:
                                sums, _ = core.components(base, hidden, y, seg, horizons=())
                                correct = sums[1]; ranking = correct * 0.
                            objective = loss.normalized_loss(correct, words, ranking, edges, WEIGHTS[arm])
                        if not bool(torch.isfinite(objective)): raise ValueError('nonfinite scoped assistant/ranking loss')
                        objective.backward()
                        observed_words += sum(r.targets for r in records)
                        totals.update(positive_rows=len(records), x_tokens=sum(r.x_tokens for r in records),
                            assistant_targets=sum(r.targets for r in records), padded_positive_slots=x.numel())
                        stats[0] += correct.detach(); stats[1] += ranking.detach()
                    if observed_words != words or observed_edges != edges:
                        raise ValueError('whole-update actual CE/relation denominators differ')
                    native_records = [core.Record(v[:-1].astype('int64').tolist(), v[1:].astype('int64').tolist(),
                        [1] * 1024) for v in native[updates * 8:(updates + 1) * 8]]
                    if len(native_records) != 8: raise ValueError('native TRAIN source exhausted')
                    nx, ny, ns = core.pad_records(native_records, pad, 'cuda', fixed_width=1024, batch_size=8)
                    with torch.autocast('cuda', dtype=torch.bfloat16):
                        sums, valid = core.components(base, model(nx, return_hidden=True), ny, ns, horizons=())
                        native_loss = sums[1] / 8192
                    if valid[1] != 8192 or not bool(torch.isfinite(native_loss)):
                        raise ValueError('native denominator/nonfinite loss')
                    native_loss.backward()
                    grad = torch.nn.utils.clip_grad_norm_(base.parameters(), 1.)
                    if not bool(torch.isfinite(grad)): raise ValueError('nonfinite gradient')
                    grad_max = max(grad_max, float(grad)); clips += int(grad > 1.)
                    adam.step(); muon.step(); updates += 1
                    totals.update(native_targets=8192, relation_questions=edges)
                    torch.cuda.synchronize(); elapsed = time.perf_counter() - tick; times.append(elapsed)
                    value = stats.cpu().tolist()
                    event = dict(update=updates, epoch=epoch + 1, correct_ce=value[0] / words,
                        row_contrast=value[1] / edges if edges else None, relation_questions=edges,
                        assistant_targets=words, lambda_weight=WEIGHTS[arm], native_ce=float(native_loss.detach()),
                        gradient_norm=float(grad), clipped=bool(grad > 1.), step_seconds=elapsed)
                    events.append(event)
                    if updates <= 8 or updates % 20 == 0:
                        print('[RELATION_UPDATE] ' + json.dumps(dict(arm=arm, **event)), flush=True)
                    if cost and updates == 8: break
                if cost: break
                entry = dict(epoch=epoch + 1, updates=updates,
                    dev=dev_probe(base, rows, relation_rows['dev'], tok, pad, eot), native=native_probe(base))
                history.append(entry); print('[RELATION_EPOCH] ' + json.dumps(entry), flush=True)
            if updates != (8 if cost else UPDATES): raise ValueError('planned update count not reached')
            if not cost:
                expected = frozen['exposure']['four_pass']
                if (any(totals[k] != v for k, v in expected.items())
                        or totals['padded_positive_slots'] != frozen['exposure']['padded_positive_slots_four_pass']
                        or totals['padded_crossed_slots'] != frozen['exposure']['padded_crossed_slots_four_pass']
                        or totals['native_targets'] != frozen['exposure']['native_targets_four_pass']
                        or totals['relation_questions'] != 4 * 4096):
                    raise ValueError('final actual exposure differs from full frozen contract')
            if cost and not totals['crossed_rows']: raise ValueError('cost8 did not exercise relation branch')
            result = dict(info(), status='COST8_COMPLETE' if cost else 'TRAIN_COMPLETE_EVALUATION_PENDING',
                arm=arm, weight=WEIGHTS[arm], updates=updates, initial_core_sha256=initial,
                final_core_sha256=runtime.state_fingerprint(base), corpus_sha256=original.digest(CORPUS / 'report.json'),
                totals=dict(totals), crossed_rows=totals['crossed_rows'], history=history,
                native_before=native_before, dev_before=dev_before, step_seconds=times,
                whole_seconds=time.perf_counter() - began, grad_max=grad_max, clip_events=clips,
                peak_allocated_mib=torch.cuda.max_memory_allocated() / 2**20,
                peak_reserved_mib=torch.cuda.max_memory_reserved() / 2**20,
                memory_scope='this torch process allocator, not full device/WDDM peak',
                meaningful_model_training='COST_ONLY' if cost else 'ACTUAL_768_UPDATES',
                observed_gpu_memory='MEASURED_ALLOCATOR_ONLY', checkpoint_written=not cost,
                actual_optimizer_groups=optimizer_receipts,
                optimizer_saved=False, semantic_adoption='NOT_DECIDED')
            if not cost:
                cp = safe(checkpoint(arm))
                with cp.open('xb') as stream:
                    torch.save(dict(model=base.state_dict(), cfg=asdict(cfg), step=updates,
                        tokenizer_sha256=original.TOK_SHA, tokenizer_lineage='chat32',
                        relation_course=dict(tag=TAG, arm=arm, epoch=4, weight=WEIGHTS[arm]),
                        optimizer_saved=False), stream)
                result.update(checkpoint=str(cp.relative_to(ROOT)), checkpoint_sha256=original.digest(cp))
            result['event_manifest'] = events.close(lineage=dict(tag=TAG, arm=arm, status=result['status']))
            write(target / 'report.json', result)
    except BaseException as exc:
        status, code = failure_status(exc)
        write(target / 'error.json', dict(status=status, exit_code=code, arm=arm,
            exception=type(exc).__name__, message=str(exc), original_sources_preserved=True,
            timestamp=datetime.now(timezone.utc).isoformat()))
        raise
    print('[RELATION_FINAL] ' + json.dumps(dict(arm=arm, status=result['status'], updates=updates,
        checkpoint_written=not cost, quality='EVALUATION_PENDING')), flush=True)
    return 0


def evaluation_cases(rows, relations):
    """Fixed before child output; no candidate answer or gold in generation input."""
    cases = []
    for b in relations['test']:
        for view in (0, 1, 2):
            for qi in (0, 1):
                row = data.render(b, qi, view=view)
                cases.append(dict(id=data.sha(['RELATION', b['bundle_id'], view, qi]), lane='relation',
                    language=b['language'], family=b['family'], group_id=b['group_id'],
                    bundle_id=b['bundle_id'], view=view, question_index=qi,
                    messages=row['messages'][:1], gold=b['answers'][qi]))
    natural = []
    for language in ('ko', 'en'):
        selected = sorted((r for r in rows['test'] if r['language'] == language),
                          key=lambda r: data.sha([20261017, 'MONITOR', r['root']]))[:32]
        if len(selected) != 32: raise ValueError('same64 natural monitor source required')
        natural.extend(selected)
    for case in natural:
        for view in (0, 1, 2):
            row = original.render_view(case, view)
            cases.append(dict(id=data.sha(['NATURAL', case['root'], view]), lane='natural',
                language=case['language'], group_id=case['article_id'], root=case['root'], view=view,
                messages=row['messages'][:1], aliases=case['aliases']))
    # These are monitoring canaries, not new independent world-knowledge tests.
    for language in ('ko', 'en'):
        for i in range(12):
            a, b = i + 2, (i * 7 + 3) % 17 + 1
            question = (f'{a}+{b}의 값은? 정수만 답하세요.' if language == 'ko'
                        else f'What is {a}+{b}? Answer only the integer.')
            cases.append(dict(id=data.sha(['ARITHMETIC_MONITOR', language, i]), lane='canary',
                language=language, group_id='arithmetic_' + str(i),
                messages=[dict(role='user', content=question)], gold=str(a + b)))
    questions = ('1+1은?', '2+2는?', 'A는 사과고 B는 당근이다 B는?',
        '문맥: 민수는 사과 3개, 영희는 사과 5개를 가지고 있습니다. 질문: 영희의 사과는 몇 개입니까? 답만 쓰세요.',
        '사과에 대해 알려줘', '농구란?')
    for i, question in enumerate(questions):
        cases.append(dict(id=data.sha(['USER_SEEN_MONITOR', i]), lane='user_seen', language='ko',
            group_id='user_seen_' + str(i), messages=[dict(role='user', content=question)],
            semantic_review='NOT_AUTOMATICALLY_ADJUDICATED'))
    if len({c['id'] for c in cases}) != len(cases): raise ValueError('duplicate evaluation case')
    return cases


def summarize_answers(events, cases):
    from scripts.p106b_night_learning import qa_scores
    expected = {c['id']: c for c in cases}; indexed = {}; totals = defaultdict(Counter)
    bundles = defaultdict(list)
    for event in events:
        ident = event.get('id'); case = expected.get(ident)
        if case is None or ident in indexed or event.get('case') != case:
            raise ValueError('unknown/duplicate/changed evaluation source')
        answer = event.get('answer'); meta = event.get('generation')
        if (not isinstance(answer, str) or not isinstance(meta, dict)
                or type(meta.get('generated_tokens')) is not int or meta['generated_tokens'] <= 0
                or not isinstance(meta.get('finish_reason'), str)):
            raise ValueError('actual answer/termination/token accounting required')
        indexed[ident] = event
        key = case['lane'] + '|' + case['language'] + '|v' + str(case.get('view', 0))
        totals[key].update(responses=1, stopped=int(meta['finish_reason'] == 'STOP_SEQUENCE'))
        if case['lane'] in ('relation', 'canary'):
            correct = int(data.exact_answer(answer) == data.exact_answer(case['gold']))
            totals[key].update(exact=correct)
            if case['lane'] == 'relation':
                bundles[case['language'], case['view'], case['bundle_id']].append((case['question_index'], correct))
        elif case['lane'] == 'natural':
            totals[key].update(qa_scores(answer, case['aliases'], case['language']))
        else:
            totals[key].update(unadjudicated=1)
    if set(indexed) != set(expected): raise ValueError('evaluation answers missing; never fill with zeros')
    relation = defaultdict(Counter)
    for (language, view, _), values in bundles.items():
        if sorted(q for q, _ in values) != [0, 1]: raise ValueError('both relation questions required')
        relation[language + '|v' + str(view)].update(bundles=1, both_correct=int(all(v for _, v in values)))
    return dict(counts={k: dict(v) for k, v in sorted(totals.items())},
        relation_both_correct={k: dict(v) for k, v in sorted(relation.items())},
        actual_responses=len(indexed), user_seen_semantic_quality='NOT_ADJUDICATED',
        primary='candidate-free greedy first answer; two questions both exact, within language/view',
        natural_metric='local QA EM/F1, previously observed development cohort')


def paired_relation(left, right, cases, *, draws=2000):
    """Descriptive paired intervals by fact graph within each language/view."""
    summarize_answers(left, cases); summarize_answers(right, cases)
    a = {e['id']: e for e in left}; b = {e['id']: e for e in right}
    groups = defaultdict(lambda: defaultdict(list))
    for c in cases:
        if c['lane'] != 'relation': continue
        good_a = data.exact_answer(a[c['id']]['answer']) == data.exact_answer(c['gold'])
        good_b = data.exact_answer(b[c['id']]['answer']) == data.exact_answer(c['gold'])
        groups[c['language'], c['view']][c['group_id']].append((good_a, good_b))
    if type(draws) is not int or draws <= 0: raise ValueError('positive fixed bootstrap draws required')
    result = {}
    for (language, view), graph in groups.items():
        differences = []
        for values in graph.values():
            if len(values) != 2: raise ValueError('one complete bilingual graph member per language required')
            differences.append(int(all(v[1] for v in values)) - int(all(v[0] for v in values)))
        rng = random.Random(20261017); n = len(differences)
        if not n: raise ValueError('no independent fact graphs')
        sampled = sorted(100 * sum(differences[rng.randrange(n)] for _ in range(n)) / n for _ in range(draws))
        result[language + '|v' + str(view)] = dict(independent_graphs=n,
            delta_both_correct_pp=100 * sum(differences) / n,
            descriptive_ci95_pp=[sampled[int(.025 * (draws - 1))], sampled[int(.975 * (draws - 1))]],
            draws=draws, learning_seeds=1, multiple_comparisons_adjusted=False,
            scope='paired generated-fact graph interval; not architecture/global intelligence adoption')
    return result


def emit_answer(base, cfg, tok, messages):
    from tinylm.chat.serialize import serialize
    from tinylm.infer.generate import sample
    from scripts.diag_p101a_mtp_parity import CaptureTokens, PrecisionForward
    prompt = serialize(dict(messages=messages), 'chatml', add_generation_prompt=True)
    prefix = tok.encode(prompt).ids
    if len(prefix) + 128 > cfg.max_seq_len: raise ValueError('complete evaluation prompt exceeds generation budget')
    capture = CaptureTokens(tok)
    _, meta = sample(PrecisionForward(base, 'fp32_math'), cfg, capture, prompt, max_new=128,
        temperature=0., top_k=1, device='cuda', use_cache=True, logits_last_only=True,
        return_metadata=True, stop_token_sequences=[[tok.token_to_id('<|im_end|>')]])
    ids = capture.decoded_ids
    if (not isinstance(ids, list) or ids[:len(prefix)] != prefix
            or len(ids) - len(prefix) != meta['generated_tokens']):
        raise ValueError('actual generated IDs and complete prompt boundary differ')
    continuation = ids[len(prefix):]
    eot = tok.token_to_id('<|im_end|>')
    if meta['finish_reason'] == 'STOP_SEQUENCE':
        if not continuation or continuation[-1] != eot: raise ValueError('actual terminal EOT differs')
        continuation = continuation[:-1]
    answer = tok.decode(continuation, skip_special_tokens=False)
    meta.update(precision='FP32_MATH', temperature=0., top_k=1, use_cache=True, mtp=False,
        prompt_sha256=data.sha(prompt), prompt_ids_sha256=data.sha(prefix),
        generated_ids_sha256=data.sha(ids[len(prefix):]), prompt_tokens=len(prefix),
        candidate_answers_supplied=False)
    return answer, meta


def rank_probe(base, tok, bundles):
    """Teacher-forced row/column diagnostics, separate from real free answers."""
    import torch
    from torch.nn.attention import sdpa_kernel, SDPBackend
    from tinylm.train import mtp_sft as core
    from scripts import p106b_relation_bind_loss as loss
    pad = tok.token_to_id('<pad>'); eot = tok.token_to_id('<|im_end|>')
    output = []; specifications = rank_specifications(bundles, tok)
    with torch.no_grad(), sdpa_kernel(SDPBackend.MATH), torch.autocast('cuda', enabled=False):
        for bundle in bundles:
            positive, crossed = data.encode_bundle(bundle, tok)
            px, _, _ = core.pad_records(positive, pad, 'cuda', fixed_width=1024)
            cx, _, _ = core.pad_records(crossed, pad, 'cuda', fixed_width=1024)
            ph = base(px, return_hidden=True); ch = base(cx, return_hidden=True)
            p, pe, pn = loss.sequence_terms(base, ph, positive, eot, False)
            c, ce, cn = loss.sequence_terms(base, ch, crossed, eot, False)
            matrix = loss.score_matrix(loss.content_means(p, pn), loss.content_means(c, cn))[0].cpu().tolist()
            first = []
            for qi in (0, 1):
                pp = [i for i, y in enumerate(positive[qi].y) if y != -100][:-1]
                cp = [i for i, y in enumerate(crossed[qi].y) if y != -100][:-1]
                pt = [positive[qi].y[i] for i in pp]; ct = [crossed[qi].y[i] for i in cp]
                divergence = next((i for i, pair in enumerate(zip(pt, ct)) if pair[0] != pair[1]), None)
                if divergence is None or len(pt) != len(ct): raise ValueError('equal-length distinct candidate branch required')
                # Shared teacher-forced candidate prefix, not actual generated history.
                if positive[qi].x[:pp[divergence] + 1] != crossed[qi].x[:cp[divergence] + 1]:
                    raise ValueError('first divergence does not share an actual causal prefix')
                logits = base._head_logits(ph[qi, pp[divergence]].reshape(1, 1, -1))[0, 0].float()
                gold_logit, other_logit = float(logits[pt[divergence]]), float(logits[ct[divergence]])
                first.append(dict(question_index=qi, branch_content_index=divergence,
                    correct_token=pt[divergence], crossed_token=ct[divergence],
                    correct_logit=gold_logit, crossed_logit=other_logit,
                    gap=gold_logit - other_logit))
            output.append(dict(bundle_id=bundle['bundle_id'], group_id=bundle['group_id'],
                language=bundle['language'], family=bundle['family'], matrix=matrix,
                content_counts=pn, first_divergence=first,
                source_spec_sha256=data.sha(specifications[bundle['bundle_id']]),
                scope='teacher-forced FP32 content means; not free-answer success'))
    return output


def rank_specifications(bundles, tok):
    result = {}
    for bundle in bundles:
        pos, cross = data.encode_bundle(bundle, tok); branches = []
        counts = []
        for qi in (0, 1):
            p = [v for v in pos[qi].y if v != -100][:-1]
            c = [v for v in cross[qi].y if v != -100][:-1]
            if len(p) != len(c): raise ValueError('equal candidate lengths required')
            d = next((i for i, pair in enumerate(zip(p, c)) if pair[0] != pair[1]), None)
            if d is None: raise ValueError('distinct token branch required')
            counts.append(len(p)); branches.append(dict(question_index=qi, branch_content_index=d,
                correct_token=p[d], crossed_token=c[d]))
        result[bundle['bundle_id']] = dict(content_counts=counts, branches=branches,
            candidate_records_sha256=data.sha([record_identity(r) for r in pos + cross]))
    return result


def summarize_ranks(events, bundles, expected_specs):
    expected = {b['bundle_id']: b for b in bundles}; seen = set(); totals = defaultdict(Counter)
    for event in events:
        bundle = expected.get(event.get('bundle_id')); matrix = event.get('matrix')
        if (bundle is None or event['bundle_id'] in seen or event.get('group_id') != bundle['group_id']
                or event.get('language') != bundle['language'] or event.get('family') != bundle['family']
                or not isinstance(matrix, list) or len(matrix) != 2 or any(not isinstance(r, list) or len(r) != 2 for r in matrix)
                or any(type(v) not in (int, float) or not math.isfinite(v) or v > 0 for r in matrix for v in r)):
            raise ValueError('one finite source-bound2x2 score matrix per bundle required')
        spec = expected_specs.get(bundle['bundle_id'])
        if (not isinstance(spec, dict) or event.get('content_counts') != spec['content_counts']
                or event.get('source_spec_sha256') != data.sha(spec)):
            raise ValueError('exact frozen tokenizer candidate lengths/record identity required')
        first = event.get('first_divergence')
        if (not isinstance(first, list) or len(first) != 2
                or [f.get('question_index') for f in first] != [0, 1]
                or any(type(f.get('branch_content_index')) is not int or f['branch_content_index'] < 0
                       or f.get('correct_token') == f.get('crossed_token')
                       or any(type(f.get(k)) not in (int, float) or not math.isfinite(f[k])
                              for k in ('correct_logit', 'crossed_logit', 'gap'))
                       or f['gap'] != f['correct_logit'] - f['crossed_logit'] for f in first)):
            raise ValueError('two independently recomputable first-divergence logit margins required')
        if [{k: f[k] for k in ('question_index', 'branch_content_index', 'correct_token', 'crossed_token')}
                for f in first] != spec['branches']:
            raise ValueError('actual first-divergence position/token IDs differ from frozen candidates')
        seen.add(event['bundle_id'])
        row = [matrix[0][0] - matrix[0][1], matrix[1][1] - matrix[1][0]]
        column = [matrix[0][0] - matrix[1][0], matrix[1][1] - matrix[0][1]]
        totals[bundle['language']].update(bundles=1, row_both_positive=int(all(x > 0 for x in row)),
            column_both_positive=int(all(x > 0 for x in column)),
            first_divergence_both_positive=int(all(f['gap'] > 0 for f in first)))
    if seen != set(expected): raise ValueError('missing candidate score bundle')
    return {language: dict(values) for language, values in totals.items()}


def endpoint_identity(label):
    if label == 'parent':
        if original.digest(PARENT) != PARENT_SHA: raise ValueError('actual immutable parent changed')
        return dict(endpoint=label, checkpoint=str(PARENT.relative_to(ROOT)),
            checkpoint_sha256=PARENT_SHA, expected_core_sha256=PARENT_CORE, training_report_sha256=None)
    if label not in ARMS: raise ValueError('explicit endpoint required')
    path = EVIDENCE / ('train_' + label) / 'report.json'; report = stage_report(path)
    if (report.get('status') != 'TRAIN_COMPLETE_EVALUATION_PENDING' or report.get('arm') != label
            or report.get('updates') != UPDATES or report.get('weight') != WEIGHTS[label]
            or report.get('code_sha256') != info()['code_sha256']
            or report.get('corpus_sha256') != original.digest(CORPUS / 'report.json')
            or report.get('initial_core_sha256') != PARENT_CORE
            or report.get('checkpoint') != str(checkpoint(label).relative_to(ROOT))
            or original.digest(checkpoint(label)) != report.get('checkpoint_sha256')
            or not isinstance(report.get('final_core_sha256'), str) or len(report['final_core_sha256']) != 64):
        raise ValueError('exact trained endpoint/report/corpus/code/checkpoint binding required')
    return dict(endpoint=label, checkpoint=report['checkpoint'], checkpoint_sha256=report['checkpoint_sha256'],
        expected_core_sha256=report['final_core_sha256'], training_report_sha256=original.digest(path))


def validate_evaluation_report(report, identity, cases_sha, corpus_sha, code_sha):
    lineage = dict(tag=TAG, **identity)
    if (report.get('status') != 'ACTUAL_FIRST_ANSWERS_RECORDED' or report.get('lineage') != lineage
            or report.get('endpoint') != identity['endpoint'] or report.get('code_sha256') != code_sha
            or report.get('corpus_sha256') != corpus_sha or report.get('cases_sha256') != cases_sha
            or report.get('checkpoint_sha256') != identity['checkpoint_sha256']
            or report.get('core_before') != identity['expected_core_sha256']
            or report.get('core_after') != identity['expected_core_sha256']
            or report.get('answer_manifest', {}).get('lineage') != lineage
            or report.get('rank_manifest', {}).get('lineage') != lineage):
        raise ValueError('evaluation label/source/checkpoint/body/raw-lineage binding differs')
    return True


def evaluate(seconds):
    import gc
    import torch
    from tinylm.infer.generate import _strip
    from scripts import diag_p101a_sft_mtp as runtime
    from scripts.p106b_gate_runtime import idle_before_gpu, wall_limit
    frozen, rows, relations = read_prepared()
    cases = evaluation_cases(rows, relations)
    targets = [(label, safe(EVIDENCE / ('evaluate_' + label)), safe(LOCAL / ('evaluate_' + label)))
               for label in ('parent', *ARMS)]
    for _, target, local in targets:
        if target.exists() or local.exists(): raise FileExistsError('old evaluation output preserved')
    identities = {label: endpoint_identity(label) for label in ('parent', *ARMS)}
    idle_before_gpu(); began = time.perf_counter()
    with wall_limit(seconds):
        for label, target, local in targets:
            target.mkdir(parents=True, exist_ok=False); local.mkdir(parents=True, exist_ok=False)
            writer = ShardWriter(local, 'answers'); events = []
            try:
                torch, base, cfg, tok, initial = load_parent()
                if evaluation_input_proof(cases, tok) != frozen['evaluation_input_proof']:
                    raise ValueError('actual evaluation prompt tokens differ from CPU input proof')
                cp = PARENT if label == 'parent' else checkpoint(label)
                identity = identities[label]
                if label != 'parent':
                    saved = torch.load(cp, map_location='cpu', weights_only=True)
                    if (saved.get('relation_course') != dict(tag=TAG, arm=label, epoch=4, weight=WEIGHTS[label])
                            or saved.get('tokenizer_sha256') != original.TOK_SHA):
                        raise ValueError('saved child lineage/tokenizer mismatch')
                    base.load_state_dict(_strip(saved['model']), strict=True); del saved
                before = runtime.state_fingerprint(base)
                if before != identity['expected_core_sha256']:
                    raise ValueError('saved child body differs from training final')
                base = base.cuda(); base.eval(); base.freeze_quant()
                torch.backends.cuda.matmul.allow_tf32 = False; torch.backends.cudnn.allow_tf32 = False
                with torch.no_grad():
                    for i, case in enumerate(cases):
                        answer, meta = emit_answer(base, cfg, tok, case['messages'])
                        event = dict(id=case['id'], case=case, answer=answer, generation=meta)
                        events.append(event); writer.append(event)
                        if i < 4 or case['lane'] in ('canary', 'user_seen'):
                            print('[RELATION_ACTUAL_ANSWER] ' + json.dumps(dict(model=label, lane=case['lane'],
                                question=original.text(case['messages'][0]), answer=answer,
                                finish=meta['finish_reason']), ensure_ascii=False), flush=True)
                        if (i + 1) % 64 == 0:
                            print('[RELATION_EVAL_PROGRESS] ' + json.dumps(dict(model=label,
                                responses=i + 1, expected=len(cases))), flush=True)
                ranking = rank_probe(base, tok, relations['test'])
                rank_summary = summarize_ranks(ranking, relations['test'], rank_specifications(relations['test'], tok))
                base.clear_quant()
                native = native_probe(base)
                after = runtime.state_fingerprint(base)
                if before != after: raise ValueError('evaluation changed trained weights')
                summary = summarize_answers(events, cases)
                lineage = dict(tag=TAG, **identity)
                manifest = writer.close(lineage=lineage)
                verify(local, manifest)
                rank_writer = ShardWriter(local, 'rank')
                for row in ranking: rank_writer.append(row)
                rank_manifest = rank_writer.close(lineage=lineage); verify(local, rank_manifest)
                result = dict(info(), status='ACTUAL_FIRST_ANSWERS_RECORDED', endpoint=label,
                    checkpoint_sha256=identity['checkpoint_sha256'], core_before=before, core_after=after,
                    lineage=lineage, rank_summary=rank_summary, rank_manifest=rank_manifest,
                    corpus_sha256=original.digest(CORPUS / 'report.json'), cases_sha256=data.sha(cases),
                    summary=summary, answer_manifest=manifest, native32_fp32=native,
                    answer_manifest_sha256=original.digest(local / 'answers_shards_manifest.json'),
                    rank_manifest_sha256=original.digest(local / 'rank_shards_manifest.json'),
                    model_training=False, weights_changed=False, checkpoints_written=0,
                    whole_seconds_since_evaluation_start=time.perf_counter() - began)
                write(target / 'report.json', result)
            except BaseException as exc:
                status, code = failure_status(exc)
                write(target / 'error.json', dict(status=status, exit_code=code, endpoint=label,
                    exception=type(exc).__name__, message=str(exc), partial_raw_preserved=True))
                raise
            finally:
                if 'base' in locals(): del base
                gc.collect(); torch.cuda.empty_cache()
    print('[RELATION_FINAL] actual first answers saved; readback required; no automatic model adoption', flush=True)
    return 0


def readback():
    frozen, rows, relations = read_prepared(); cases = evaluation_cases(rows, relations)
    from tokenizers import Tokenizer
    tok = Tokenizer.from_file(str(original.TOKENIZER))
    if evaluation_input_proof(cases, tok) != frozen['evaluation_input_proof']:
        raise ValueError('actual evaluation source prompt proof changed')
    rank_specs = rank_specifications(relations['test'], tok)
    outputs = {}; reports = {}
    for label in ('parent', *ARMS):
        report = stage_report(EVIDENCE / ('evaluate_' + label) / 'report.json')
        identity = endpoint_identity(label)
        validate_evaluation_report(report, identity, data.sha(cases), original.digest(CORPUS / 'report.json'), info()['code_sha256'])
        local = LOCAL / ('evaluate_' + label); manifest = report['answer_manifest']
        for stem, digest_field, data_field in (('answers', 'answer_manifest_sha256', 'answer_manifest'),
                                               ('rank', 'rank_manifest_sha256', 'rank_manifest')):
            path = local / (stem + '_shards_manifest.json')
            if original.digest(path) != report.get(digest_field) or required(path) != report.get(data_field):
                raise ValueError('stored manifest/hash and endpoint report differ')
        verify(local, manifest); events = []
        for spec in manifest['shards']:
            with (local / spec['path']).open(encoding='utf-8') as stream:
                events.extend(json.loads(line) for line in stream)
        if summarize_answers(events, cases) != report['summary']: raise ValueError('raw answer recount differs')
        ranking = []
        verify(local, report['rank_manifest'])
        for spec in report['rank_manifest']['shards']:
            with (local / spec['path']).open(encoding='utf-8') as stream:
                ranking.extend(json.loads(line) for line in stream)
        if summarize_ranks(ranking, relations['test'], rank_specs) != report['rank_summary']:
            raise ValueError('raw candidate scores and first-divergence recount differ')
        outputs[label] = events; reports[label] = report
    result = dict(status='RAW_READBACK_COMPLETE_NO_AUTOMATIC_ADOPTION', tag=TAG,
        code_sha256=info()['code_sha256'], cases_sha256=data.sha(cases), errors=0,
        source_reports_sha256={k: original.digest(EVIDENCE / ('evaluate_' + k) / 'report.json') for k in outputs},
        summaries={k: r['summary'] for k, r in reports.items()},
        contrast_minus_ce=paired_relation(outputs['ce'], outputs['contrast'], cases),
        learning_seeds=1, model_training=False, semantic_adoption='USER_REVIEW_REQUIRED')
    write(EVIDENCE / 'readback.json', result)
    print('[RELATION_READBACK] ' + json.dumps(result, ensure_ascii=False), flush=True)
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=('prepare', 'preflight', 'cost', 'train', 'evaluate', 'readback', 'budget'), required=True)
    parser.add_argument('--arm', choices=ARMS)
    parser.add_argument('--max-wall-sec', type=int, default=7200)
    parser.add_argument('--budget-hours', type=float, default=4.)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--execute', action='store_true'); action.add_argument('--check-only', action='store_true')
    args = parser.parse_args()
    if not 60 <= args.max_wall_sec <= 21600: parser.error('bounded60..21600 wall seconds required')
    if not math.isfinite(args.budget_hours) or not 0 < args.budget_hours <= 24:
        parser.error('positive wall budget up to24hours required')
    if args.check_only:
        print('[RELATION_CHECK_ONLY] ' + json.dumps(info(), ensure_ascii=False)); return 0
    if args.mode in ('cost', 'train') and args.arm is None: parser.error('explicit arm required')
    try:
        if args.mode == 'prepare': return prepare()
        if args.mode == 'preflight': return preflight()
        if args.mode == 'budget': print(json.dumps(cost_budget(args.budget_hours))); return 0
        if args.mode == 'readback': return readback()
        if args.mode == 'evaluate': return evaluate(args.max_wall_sec)
        return run(args.arm, args.mode == 'cost', args.max_wall_sec, args.budget_hours)
    except KeyboardInterrupt:
        print('[RELATION_FINAL] INTERRUPTED130; partial evidence preserved; no success claim', flush=True); return 130
    except Exception as exc:
        import traceback
        status, code = failure_status(exc)
        if code == 9: traceback.print_exc()
        print('[RELATION_FINAL] ' + status + str(code) + ': ' + str(exc), flush=True); return code


if __name__ == '__main__': raise SystemExit(main())
