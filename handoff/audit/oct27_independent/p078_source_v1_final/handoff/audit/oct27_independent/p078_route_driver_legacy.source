#!/usr/bin/env python3
"""Independent P078 Stage2 eager SFT controller; no historical Runtime/clock.

check-only reads source files only, never corpus/tokenizer/CP/model. Actual GPU
work needs a separately sealed, current user authorization and a pinned frozen
P101A corpus report. Learned routing is explicitly NOT_IMPLEMENTED.
"""
from __future__ import annotations
import argparse
import ast
from contextlib import contextmanager
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
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0, str(ROOT))
from scripts import p078_route_training as route
TAG = 'p078_route_training_v1_s1337'
PARENT = 'runs/ckpt/m100s10_ko-en_300M_dense_chat32_p090b_s1337.pt'
PARENT_SHA = '12E18658CDCD0AFEBE5A87073DC8977304C0D490A03A8471779D514FBB0D9950'
CORPUS = 'HF/sft_ready/p101a_sft_mtp_v1_s1337/corpus'
CLEAN_CORPUS = 'HF/sft_ready/p101a_sft_mtp_cleanbilingual_v3_s1337/corpus'
CORPORA = (CLEAN_CORPUS, CORPUS)
TOKENIZER = 'data_cache/tok-ko-en-32768-chat32.json'
TOK_SHA = '9716F40E4C504D6AF37DDE76CCA578E30B45E9CA86C8B6BB79B2FA095D3AC88E'
READY = True  # Root source review closed; runtime still requires exact user authority/corpus/cost.
MODES = ('toy', 'cost', 'budget', 'train', 'evaluate', 'readback', 'router')
CODE = ('scripts/p078_route_training.py', 'scripts/test_p078_route_training.py', 'scripts/diag_p078_route_training.py',
    'scripts/p070b_cla_routes.py', 'scripts/diag_p101a_sft_mtp.py', 'scripts/p101a_sft_mtp_data.py',
    'scripts/diag_p101a_clean_bilingual.py',
    'scripts/p106b_shards.py', 'scripts/p106b_repeat4_gate.py', 'scripts/interactive_research_infer.py',
    'scripts/diag_p101a_mtp_parity.py', 'scripts/train_sft_p090.py', 'tinylm/__init__.py', 'tinylm/paths.py',
    'tinylm/config.py', 'tinylm/model/__init__.py', 'tinylm/model/transformer.py', 'tinylm/model/modules.py',
    'tinylm/model/ternary.py', 'tinylm/model/ternary_kernel.py', 'tinylm/data/__init__.py', 'tinylm/data/prepare.py',
    'tinylm/data/loader.py', 'tinylm/data/sft.py', 'tinylm/chat/__init__.py', 'tinylm/chat/canonical.py',
    'tinylm/chat/serialize.py', 'tinylm/chat/tokens.py', 'tinylm/train/__init__.py', 'tinylm/train/trainer.py',
    'tinylm/train/lr_finder.py', 'tinylm/train/mtp_sft.py', 'tinylm/train/muon.py', 'tinylm/train/optimizer_audit.py',
    'tinylm/train/init_utils.py', 'tinylm/train/init_mapping.py', 'tinylm/train/anneal_schedule.py',
    'tinylm/training_defaults.py', 'tinylm/eval/__init__.py', 'tinylm/eval/evaluate.py', 'tinylm/eval/compare.py',
    'tinylm/audit_io.py', 'tinylm/infer/__init__.py', 'tinylm/infer/generate.py')


class Hold(RuntimeError): pass


def path(relative):
    p = Path(relative)
    if p.is_absolute() or '..' in p.parts or not p.parts or p.parts[:2] == ('datasets', 'TinyDataset'):
        raise ValueError('explicit repository relative path required')
    if p.parts[0] == 'HF' and not any(p.is_relative_to(c) for c in CORPORA): raise ValueError('only explicitly pinned frozen processed corpus is permitted')
    out = ROOT
    for part in p.parts:
        out = out / part
        if out.is_symlink(): raise ValueError('symlink input/output ancestor refused')
    return out


def digest(p):
    h = hashlib.sha256()
    with p.open('rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''): h.update(block)
    return h.hexdigest().upper()


def read(relative):
    raw = path(relative).read_bytes()
    if len(raw) >= 20_000_000: raise ValueError('small metadata limit')
    result = json.loads(raw)
    if not isinstance(result, dict): raise ValueError('JSON object required')
    return result


def write(relative, value):
    if not any(str(relative).startswith(base + TAG + suffix + '/') for base in ('test_result/evidence/', 'runs/eval/') for suffix in ('_cleanv3', '_old8m')): raise ValueError('new namespace only')
    p = path(relative); raw = (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()
    if len(raw) >= 20_000_000: raise ValueError('evidence must remain below20MB')
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open('xb') as stream: stream.write(raw)


def namespace(args): return TAG + ('_cleanv3' if args.corpus == CLEAN_CORPUS else '_old8m')
def report_name(mode, arm, args): return 'test_result/evidence/' + namespace(args) + '/' + mode + '_' + arm + '/report.json'
def activity_name(mode, arm, args): return 'test_result/evidence/' + namespace(args) + '/activity_' + mode + '_' + arm + '.json'
def cp_name(arm, args): return 'runs/ckpt/m100s10_ko-en_' + namespace(args) + '_' + arm + '.pt'
def update_count(report): return 4 * math.ceil(report['manifests']['train']['rows'] / 128)


def signature(args):
    return dict(schema='P078_ROUTE_SFT_V1', tag=namespace(args), source_sha256={p: digest(path(p)) for p in CODE},
        corpus_report=args.corpus + '/report.json', corpus_sha256=args.corpus_sha256, parent=PARENT, parent_sha256=PARENT_SHA,
        tokenizer_sha256=TOK_SHA, epochs=4, counts_and_updates='DERIVED_FROM_PINNED_ACTUAL_MANIFEST',
        micro_bs=8, accum=16, execution_width=1024,
        grad_checkpoint=True, mtp=False, teacher=False, compile=False,
        optimizer='P101A_FACTORY_WITH_EXPLICIT_ABSOLUTE_LRS', adam_lr=args.adam_lr, muon_lr=args.muon_lr,
        masking='diag_p101a_clean_bilingual.masked_record; explicit corrected-turn supervision preserved',
        partial_update='neutral dummy rows to128; shape differs from original variable active-micro tail when partial',
        primary_evaluation='SAME_TRAIN_POLICY_FROZEN_PER_VAL_BATCH_OR_GENERATION_CASE', generation_cache=False,
        secondary='COMMON_UNIFORM_R2_MISMATCH_DIAGNOSTIC_ONLY', learned_router='NOT_IMPLEMENTED',
        semantic_quality='PSEUDO_UNVERIFIED_NOT_FORMAL_TRAIN_READY')


def authority(args, info):
    if not args.authorization or not args.authorization_sha256: raise Hold('explicit current user authorization descriptor required')
    if not str(args.authorization).startswith('handoff/audit/'): raise ValueError('root-owned authorization metadata required')
    if digest(path(args.authorization)) != args.authorization_sha256: raise ValueError('authorization bytes changed')
    auth = read(args.authorization); end = datetime.fromisoformat(auth['expires_at']); now = datetime.now(timezone.utc)
    if (end.tzinfo is None or auth.get('schema') != 'P078_TRAIN_EXECUTION_AUTHORIZATION_V1'
            or auth.get('tag') != namespace(args) or auth.get('allow_gpu_training') is not True
            or auth.get('input_signature_sha256') != route.sha(info) or auth.get('max_family_seconds') != 144000
            or type(auth.get('max_worker_seconds')) is not int or args.max_wall_sec > auth['max_worker_seconds']):
        raise Hold('exact separately approved40h/input/source/worker authorization required')
    remaining = (end - now).total_seconds()
    if remaining <= 0: raise Hold('own execution authorization expired')
    return remaining


@contextmanager
def wall(seconds):
    old = signal.getsignal(signal.SIGALRM); term = signal.getsignal(signal.SIGTERM); timer = signal.getitimer(signal.ITIMER_REAL)
    def stop(_n, _f): raise KeyboardInterrupt('own worker termination')
    def expired(_n, _f): raise Hold('own actual wall cap reached; no COMPLETE')
    signal.signal(signal.SIGTERM, stop); signal.signal(signal.SIGALRM, expired); signal.setitimer(signal.ITIMER_REAL, seconds)
    try: yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, *timer); signal.signal(signal.SIGALRM, old); signal.signal(signal.SIGTERM, term)


def inputs(args):
    report_path = args.corpus + '/report.json'
    if digest(path(report_path)) != args.corpus_sha256: raise ValueError('explicit frozen corpus bytes changed')
    report = read(report_path)
    if (report.get('schema') != 'P101A_SFT_MTP_CORPUS_V1' or report.get('status') != 'CORPUS_READY'
            or report.get('epochs') != 4 or report.get('tokenizer_sha256') != TOK_SHA
            or set(report.get('manifests', {})) != {'train', 'val'}
            or any(type(report['manifests'][s].get('rows')) is not int or report['manifests'][s]['rows'] <= 0 for s in ('train', 'val'))):
        raise ValueError('exact selected frozen corpus/schema/positive manifests required')
    if args.corpus == CLEAN_CORPUS and (report.get('preparation_schema') != 'P101A_CLEAN_BILINGUAL_PREPARATION_V3'
            or report.get('family') != 'mtp' or report.get('sources', {}).get('old_contextless_teacher4473_rows') != 0
            or report.get('sources', {}).get('luna_drafts_admitted') != 0):
        raise ValueError('clean bilingual source admission/producer boundary differs')
    for manifest in report['manifests'].values():
        for shard in manifest['shards']: path(args.corpus + '/' + shard['path'])
    return report


def idle():
    from scripts.interactive_research_infer import require_idle_gpu
    return require_idle_gpu()


@contextmanager
def loaded(args, arm, trained=False):
    route.import_guard(); import torch
    from tokenizers import Tokenizer
    from tinylm.config import TMTConfig
    from tinylm.infer.generate import _strip
    from scripts import diag_p101a_sft_mtp as reference
    from scripts.train_sft_p090 import validate_parent_lineage
    raw = path(TOKENIZER).read_bytes()
    if hashlib.sha256(raw).hexdigest().upper() != TOK_SHA: raise ValueError('tokenizer bytes changed')
    tok = Tokenizer.from_str(raw.decode())
    if tok.get_vocab_size() != 32768 or (tok.token_to_id('<|im_start|>'), tok.token_to_id('<|im_end|>'), tok.token_to_id('<eos>')) != (3, 4, 2):
        raise ValueError('exact chat32 vocabulary required')
    chosen = cp_name(arm, args) if trained else PARENT
    expected = closed(args, 'train', arm)['checkpoint_sha256'] if trained else PARENT_SHA
    with path(chosen).open('rb') as stream:
        before = os.fstat(stream.fileno()); h = hashlib.sha256()
        for block in iter(lambda: stream.read(1 << 20), b''): h.update(block)
        if h.hexdigest().upper() != expected: raise ValueError('exact selected CP bytes required')
        stream.seek(0); state = torch.load(stream, map_location='cpu', weights_only=True)
        after = os.fstat(stream.fileno())
        if (before.st_size, before.st_mtime_ns, before.st_ino) != (after.st_size, after.st_mtime_ns, after.st_ino): raise ValueError('CP changed during read')
    if not trained: validate_parent_lineage(state, TOK_SHA, 'chat32', tok)
    elif (state.get('step') != update_count(inputs(args)) or state.get('tokenizer_sha256') != TOK_SHA
            or state.get('tokenizer_lineage') != 'chat32' or state.get('p078', {}).get('arm') != arm
            or state['p078'].get('source') != signature(args) or state['p078'].get('dedicated_route_loader_required') is not True):
        raise ValueError('dedicated matched-policy student loader/header required')
    original_cfg = dict(state['cfg']); policy = route.Policy(arm)
    config = dict(original_cfg, grad_checkpoint=True, mtp_aux=False, train_repeat=float(policy.cap), infer_repeat=1., repeat_mode='uniform')
    cfg = TMTConfig(**config)
    if cfg.n_layers != 14 or cfg.dim != 768 or cfg.tie_mlp or cfg.max_seq_len != 1024: raise ValueError('exact dense14 parent geometry required')
    torch.manual_seed(1337); model = route.build_model(cfg, policy)
    model.load_state_dict(_strip(state['model']), strict=True); del state
    initial = reference.state_fingerprint(model); gpu = False
    try:
        idle()
        if not torch.cuda.is_available(): raise Hold('CUDA-only training; no CPU fallback')
        torch.backends.cuda.matmul.allow_tf32 = False; torch.backends.cudnn.allow_tf32 = False
        model = model.cuda(); gpu = True
        yield torch, model, cfg, tok, initial, reference
    finally:
        model.clear_quant(); model = None; gc.collect()
        if gpu: torch.cuda.empty_cache()


def encoded(args, report, tok):
    from scripts import p101a_sft_mtp_data as data
    from tinylm.data.sft import conversation_split_key
    from scripts.diag_p101a_clean_bilingual import masked_record
    result = {}; roots = {}; prompts = {}
    for split in ('train', 'val'):
        result[split] = []; roots[split] = set(); prompts[split] = set()
        for row in data.stream_rows(path(args.corpus), report['manifests'][split]):
            meta = row.get('meta', {}); root = meta.get('parent_concept_id', meta.get('root_id', meta.get('root')))
            if isinstance(root, str): roots[split].add(root)
            prompts[split].add(conversation_split_key(row)); result[split].append(masked_record(row, tok))
    if roots['train'] & roots['val'] or prompts['train'] & prompts['val']: raise ValueError('frozen train/VAL root or question leakage')
    if (any(len(result[s]) != report['manifests'][s]['rows'] for s in ('train', 'val'))
            or sum(r.x_tokens for r in result['train']) != report['actual_unique_train_x_tokens']): raise ValueError('actual corpus rows/x denominator differs')
    if 'counts' in report:
        for split in ('train', 'val'):
            if (sum(r.targets for r in result[split]) != report['counts'][split]['assistant_targets']
                    or sum(r.x_tokens for r in result[split]) != report['counts'][split]['x_tokens']): raise ValueError('actual corrected-turn target/x counts differ')
    return result


def validation(torch, model, rows, pad, *, secondary=False, limit=None):
    from tinylm.train import mtp_sft as core
    from torch.nn.attention import sdpa_kernel, SDPBackend
    chosen = rows if limit is None else rows[:limit]; total = targets = visits = 0; seconds = []; receipts = []; model.eval()
    groups = math.ceil(len(chosen) / 8)
    with torch.no_grad(), sdpa_kernel(SDPBackend.MATH), torch.autocast('cuda', enabled=False):
        for i in range(groups):
            tick = time.perf_counter(); batch = chosen[i * 8:(i + 1) * 8]
            with model.route_scope(i, groups, 'secondary' if secondary else 'val', secondary=secondary) as receipt:
                model.freeze_quant(); x, y, owners = core.pad_records(batch, pad, 'cuda', fixed_width=1024, batch_size=8)
                sums, counts = core.components(model, model(x, return_hidden=True), y, owners, horizons=(), checkpoint_heads=False)
                total += float(sums[1]); targets += counts[1]; visits += receipt['visits']
                receipts.append(dict(batch=i, rows=len(batch), assistant_targets=counts[1], actual_repeats=receipt['actual_repeats'],
                    visits=receipt['visits'], route_sha256=receipt['route_sha256'], receipt_sha256=receipt['receipt_sha256']))
            torch.cuda.synchronize(); seconds.append(time.perf_counter() - tick)
    if targets != sum(r.targets for r in chosen) or not math.isfinite(total): raise ValueError('full actual validation denominator/nonfinite error')
    return dict(ce=total / targets, assistant_targets=targets, rows=len(chosen), batches=groups, sum_layer_visits=visits,
        padded_layer_visit_slots=8 * 1024 * visits, batch_seconds=seconds, precision='FP32_MATH',
        route_receipts=receipts,
        scope='COMMON_UNIFORM_MISMATCH_SECONDARY' if secondary else 'MATCHED_TRAIN_POLICY_PRIMARY')


def probes(torch, model, cfg, tok, *, limit=None):
    from scripts import interactive_research_infer as ui
    from tinylm.chat.serialize import serialize
    tree = ast.parse(path('scripts/p106b_repeat4_gate.py').read_text(encoding='utf-8'))
    node = next(n for n in tree.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'PROBES' for t in n.targets))
    cases = ast.literal_eval(node.value); cases = cases if limit is None else cases[:limit]
    sample, capture_type, forward_type = ui.generation_tools(ROOT); rows = []; model.eval()
    with torch.no_grad():
        for i, (ident, question) in enumerate(cases):
            prompt = serialize(dict(messages=[dict(role='user', content=question)]), 'chatml', add_generation_prompt=True)
            prefix = tok.encode(prompt).ids
            if len(prefix) + 160 > 1024: raise ValueError('full prompt plus160 must fit; no truncation')
            tick = time.perf_counter()
            with model.route_scope(i, len(cases), 'probe', route.QuestionPrefix(tuple(prefix))) as receipt:
                model.freeze_quant(); capture = capture_type(tok)
                _, meta = sample(forward_type(model, 'fp32_math'), cfg, capture, prompt, max_new=160, temperature=0., top_k=1,
                    device='cuda', use_cache=False, logits_last_only=True, return_metadata=True, mtp_tokens=1, stop_token_sequences=[[4]])
                answer, generation = ui.answer_from_tokens(tok, prefix, capture.decoded_ids, meta, 160)
            rows.append(dict(id=ident, question=question, prompt=prompt, prompt_ids=prefix, actual_answer=answer, generation=generation,
                route=receipt, seconds=time.perf_counter() - tick, attempts=1, semantic_score=None,
                precision='FP32_MATH', tf32=False, use_cache=False, mtp=False, temperature=0., top_k=1))
            print('[P078_ACTUAL_ANSWER] ' + json.dumps(rows[-1], ensure_ascii=False), flush=True)
    return rows


def closed(args, mode, arm):
    info = signature(args); value = read(report_name(mode, arm, args)); activity = read(activity_name(mode, arm, args))
    started, ended = (datetime.fromisoformat(activity[k]) for k in ('started_at', 'ended_at'))
    auth = activity.get('authorization', {})
    if (value.get('input') != info or activity.get('input') != info or activity.get('complete') is not True
            or activity.get('returncode') != 0 or activity.get('report_sha256') != digest(path(report_name(mode, arm, args)))
            or type(activity.get('seconds')) not in (int, float) or not math.isfinite(activity['seconds']) or activity['seconds'] < 0
            or started.tzinfo is None or ended.tzinfo is None or started > ended
            or activity.get('pid') != activity.get('pgid') or type(activity.get('pid')) is not int or activity['pid'] <= 0
            or type(activity.get('max_wall_sec')) is not int or not 60 <= activity['max_wall_sec'] <= 144000
            or activity['seconds'] > activity['max_wall_sec'] + 30
            or type(activity.get('admission_remaining')) not in (int, float) or not math.isfinite(activity['admission_remaining'])
            or activity['admission_remaining'] < activity['max_wall_sec']
            or ended > datetime.fromisoformat(activity['authority_expires_at'])
            or auth.get('schema') != 'P078_TRAIN_EXECUTION_AUTHORIZATION_V1' or auth.get('allow_gpu_training') is not True
            or auth.get('tag') != namespace(args) or auth.get('input_signature_sha256') != route.sha(info)
            or auth.get('max_family_seconds') != 144000 or auth.get('max_worker_seconds', 0) < activity['max_wall_sec']
            or auth.get('expires_at') != activity['authority_expires_at'] or activity.get('authorization_canonical_sha256') != route.sha(auth)
            or value.get('authorization') != auth or value.get('authorization_sha256') != activity.get('authorization_sha256')):
        raise ValueError('closed same-source/input stage required')
    return value


def budget(args):
    report = inputs(args); updates = update_count(report); val_batches = math.ceil(report['manifests']['val']['rows'] / 8)
    estimates = {}; evaluation = {}; spent = 0.
    for arm in route.ARMS:
        cost = cost_receipt(args, arm)
        if cost.get('status') != 'COST32_COMPLETE' or len(cost['update_seconds']) != 32: raise ValueError('all four actual cost32 receipts required')
        training_estimate, evaluation_estimate = cost_forecast(cost, updates, val_batches)
        if path(report_name('train', arm, args)).exists(): closed(args, 'train', arm); estimates[arm] = evaluation[arm] = 0.; continue
        estimates[arm] = training_estimate; evaluation[arm] = evaluation_estimate
    base = path('test_result/evidence/' + namespace(args))
    for file in base.glob('activity_*.json') if base.exists() else ():
        item = json.loads(file.read_bytes())
        if item.get('input') != signature(args) or not math.isfinite(item['seconds']) or item['seconds'] < 0: raise ValueError('same-family actual time ledger required')
        if item.get('complete') is not True: raise Hold('prior incomplete/failed family stage preserved; no automatic retry')
        spent += item['seconds']
    reserved = sum(estimates.values()) + sum(evaluation.values()) + 1800
    fits = spent + reserved <= 144000 and reserved <= authority(args, signature(args))
    return dict(status='BUDGET_READY' if fits else 'HOLD_BUDGET', fits=fits, actual_spent_seconds=spent,
        train_forecast_seconds=estimates, evaluation_forecast_seconds=evaluation, reserve_seconds=1800,
        total_pending_seconds=reserved, family_cap_seconds=144000, scope='CONSERVATIVE_MEASURED_FORECAST_NOT_COMPLETION_GUARANTEE')


def cost_receipt(args, arm):
    from scripts.p106b_shards import verify
    report = closed(args, 'cost', arm); corpus = inputs(args); total = update_count(corpus)
    relative = 'runs/eval/' + namespace(args) + '/cost_' + arm; directory = path(relative)
    if (report.get('status') != 'COST32_COMPLETE' or report.get('updates') != 32 or report.get('checkpoint_writes') != 0
            or read(relative + '/updates_shards_manifest.json') != report['raw_manifest']): raise ValueError('complete actual cost32/raw/no-CP receipt required')
    verify(directory, report['raw_manifest']); events = []
    for part in report['raw_manifest']['shards']:
        with path(relative + '/' + part['path']).open() as stream: events.extend(json.loads(line) for line in stream)
    if len(events) != 32 or report['update_seconds'] != [e['seconds'] for e in events]: raise ValueError('actual32 step timings differ from raw')
    geometry = SimpleNamespace(**report['geometry'])
    for i, event in enumerate(events):
        if event['route'] != route.plan(geometry, report['owners'], route.Policy(arm), i, total, 'train'):
            raise ValueError('actual cost32 route/compute receipt differs')
    for key in ('actual_rows', 'actual_x_tokens', 'assistant_targets', 'dummy_rows', 'padded_slots', 'layer_visit_slots'):
        if sum(e[key] for e in events) != report[key]: raise ValueError('cost raw denominator sum differs')
    return report


def cost_forecast(cost, updates, val_batches):
    times = cost['update_seconds']; validation_seconds = cost['validation_timing']['batch_seconds']; probes_timing = cost['probe_timing']
    if (type(updates) is not int or updates < 32 or type(val_batches) is not int or val_batches <= 0 or len(times) != 32
            or not validation_seconds or len(probes_timing) != 2
            or any(type(t) not in (int, float) or not math.isfinite(t) or t <= 0 for t in times + validation_seconds)
            or any(type(p['seconds']) not in (int, float) or not math.isfinite(p['seconds']) or p['seconds'] <= 0
                   or type(p['generation']['generated_tokens']) is not int or not 1 <= p['generation']['generated_tokens'] <= 160 for p in probes_timing)
            or cost.get('gpu_total_mib', 0) - cost.get('peak_reserved_mib', float('inf')) < 1024):
        raise Hold('actual32/eval/probe/1GiB observed margin resource forecast prerequisites failed')
    token_sec = max(p['seconds'] / p['generation']['generated_tokens'] for p in probes_timing)
    return (times[0] + max(times[1:]) * (updates - 1) * 1.35 + 600,
        max(validation_seconds) * val_batches * 7 * 1.5 + token_sec * 160 * 8 * 2 * 2)


def actual_spent(args, info):
    total = 0.; directory = path('test_result/evidence/' + namespace(args))
    for file in directory.glob('activity_*.json') if directory.exists() else ():
        item = json.loads(file.read_bytes())
        if (item.get('input') != info or type(item.get('seconds')) not in (int, float)
                or not math.isfinite(item['seconds']) or item['seconds'] < 0): raise ValueError('owned finite family time ledger required')
        if item.get('complete') is not True: raise Hold('prior failed/incomplete stage preserved')
        total += item['seconds']
    return total


def run_training(args, cost):
    from scripts.p106b_shards import ShardWriter
    corpus = inputs(args); info = signature(args); arm = args.arm; expected_updates = update_count(corpus)
    if not cost and not budget(args)['fits']: raise Hold('fresh all-pending40h budget does not fit')
    raw_relative = 'runs/eval/' + namespace(args) + '/' + ('cost_' if cost else 'train_') + arm
    directory = path(raw_relative)
    if directory.exists() or not cost and path(cp_name(arm, args)).exists(): raise FileExistsError('old raw/CP preserved')
    directory.mkdir(parents=True, exist_ok=False); writer = ShardWriter(path(raw_relative), 'updates', limit=19_999_999)
    events = []; complete = False
    try:
        with loaded(args, arm) as (torch, model, cfg, tok, initial, reference):
            rows = encoded(args, corpus, tok); pad = tok.token_to_id('<|pad|>')
            if pad is None: pad = tok.token_to_id('<pad>')
            if pad is None: raise ValueError('pinned PAD required')
            adam, muon = reference.optimizers(model); history = []
            for group in adam.param_groups: group['lr'] = args.adam_lr
            for group in muon.param_groups: group['lr'] = args.muon_lr
            torch.cuda.reset_peak_memory_stats()
            before = None if cost else dict(val=validation(torch, model, rows['val'], pad), answers=probes(torch, model, cfg, tok))
            for epoch in range(4):
                for groups in reference.batches(rows['train'], epoch):
                    authority(args, info)
                    records = [record for micro in groups for record in micro]
                    event = route.sft_update(model, records, (adam, muon), len(events), expected_updates, pad_id=pad, width=1024, device='cuda', amp=True)
                    event.update(epoch=epoch + 1, update=len(events) + 1); writer.append(event); events.append(event)
                    if len(events) == 1 or len(events) % 25 == 0: print('[P078_SFT_UPDATE] ' + json.dumps({k: event[k] for k in ('epoch', 'update', 'actual_rows', 'actual_x_tokens', 'assistant_targets', 'ce', 'seconds')}), flush=True)
                    if cost and len(events) == 32: break
                if cost: break
                history.append(dict(epoch=epoch + 1, updates=len(events), val=validation(torch, model, rows['val'], pad)))
            expected = 32 if cost else expected_updates
            if len(events) != expected or not cost and sum(e['actual_x_tokens'] for e in events) != 4 * corpus['actual_unique_train_x_tokens']:
                raise ValueError('actual complete four-pass/update/x counts differ')
            model.clear_quant(); final = reference.state_fingerprint(model)
            result = dict(input=info, arm=arm, status='COST32_COMPLETE' if cost else 'ROUTE_SFT_COMPLETE_EVAL_REVIEW_REQUIRED',
                initial_core_sha256=initial, final_core_sha256=final, updates=len(events),
                geometry=dict(n_layers=cfg.n_layers, n_prelude=cfg.n_prelude, n_middle=cfg.n_middle, n_coda=cfg.n_coda),
                owners=list(model.owner), student_cfg=asdict(cfg),
                update_seconds=[e['seconds'] for e in events], actual_x_tokens=sum(e['actual_x_tokens'] for e in events),
                assistant_targets=sum(e['assistant_targets'] for e in events), actual_rows=sum(e['actual_rows'] for e in events),
                dummy_rows=sum(e['dummy_rows'] for e in events), padded_slots=sum(e['padded_slots'] for e in events),
                layer_visit_slots=sum(e['layer_visit_slots'] for e in events), grad_max=max(e['gradient_max'] for e in events),
                before=before, history=history, model_constructions=1, checkpoint_tensor_loads=1, checkpoint_writes=0,
                optimizer_factory='PINNED_P101A_UNCHANGED', optimizer_factory_calls=1, optimizer_reset_between_updates=False)
            result['train_ce'] = sum(e['ce'] * e['assistant_targets'] for e in events) / result['assistant_targets']
            if cost:
                result.update(validation_timing=validation(torch, model, rows['val'], pad, limit=64), probe_timing=probes(torch, model, cfg, tok, limit=2))
            else:
                result.update(final_primary=validation(torch, model, rows['val'], pad),
                    final_secondary=validation(torch, model, rows['val'], pad, secondary=True), final_answers=probes(torch, model, cfg, tok))
                authority(args, info); destination = path(cp_name(arm, args)); destination.parent.mkdir(parents=True, exist_ok=True)
                with destination.open('xb') as stream:
                    torch.save(dict(model=model.state_dict(), cfg=asdict(cfg), step=expected_updates, tokenizer_sha256=TOK_SHA,
                        tokenizer_lineage='chat32', p078=dict(arm=arm, source=info, route_policy='FROZEN_SCOPE_REQUIRED',
                            dedicated_route_loader_required=True)), stream)
                result.update(checkpoint=cp_name(arm, args), checkpoint_sha256=digest(destination), checkpoint_writes=1)
            result['raw_manifest'] = writer.close(lineage=dict(tag=namespace(args), arm=arm, cost=cost, complete=True)); writer = None
            result.update(peak_allocated_mib=torch.cuda.max_memory_allocated() / 2**20,
                peak_reserved_mib=torch.cuda.max_memory_reserved() / 2**20,
                gpu_total_mib=torch.cuda.get_device_properties(0).total_memory / 2**20,
                memory_scope='OBSERVED_COST_PEAK_NOT_CONTINUOUS_OR_OOM_GUARANTEE')
            complete = True; return result
    finally:
        if writer is not None and events: writer.close(lineage=dict(tag=namespace(args), arm=arm, cost=cost, complete=False, partial=True))


def readback(args):
    from scripts.p106b_shards import verify
    corpus = inputs(args); updates = update_count(corpus); train_rows = corpus['manifests']['train']['rows']
    per_epoch = math.ceil(train_rows / 128); val_rows = corpus['manifests']['val']['rows']; val_batches = math.ceil(val_rows / 8)
    if digest(path(PARENT)) != PARENT_SHA: raise ValueError('original parent changed')
    results = {}
    for arm in route.ARMS:
        report = closed(args, 'train', arm); directory = path('runs/eval/' + namespace(args) + '/train_' + arm)
        if read('runs/eval/' + namespace(args) + '/train_' + arm + '/updates_shards_manifest.json') != report['raw_manifest']:
            raise ValueError('actual raw manifest differs from original closed report')
        verify(directory, report['raw_manifest']); events = []
        for part in report['raw_manifest']['shards']:
            with (directory / part['path']).open() as stream: events.extend(json.loads(line) for line in stream)
        if len(events) != updates or digest(path(cp_name(arm, args))) != report['checkpoint_sha256']: raise ValueError('complete actual training/raw/CP required')
        geometry = SimpleNamespace(**report['geometry'])
        for i, event in enumerate(events):
            expected = route.plan(geometry, report['owners'], route.Policy(arm), i, updates, 'train')
            real_rows = train_rows % 128 or 128 if i % per_epoch == per_epoch - 1 else 128
            if (event['route'] != expected or event['update'] != i + 1 or event['epoch'] != i // per_epoch + 1
                    or event['actual_rows'] != real_rows
                    or event['dummy_rows'] != 128 - event['actual_rows'] or event['padded_slots'] != 131072
                    or event['layer_visit_slots'] != 131072 * expected['visits']
                    or any(type(event.get(k)) not in (int, float) or not math.isfinite(event[k]) or event[k] <= 0 for k in ('ce', 'seconds'))):
                raise ValueError('actual full update route/order/shape/row/CE receipt differs')
        if len({e['model_id'] for e in events}) != 1 or len({tuple(e['optimizer_ids']) for e in events}) != 1:
            raise ValueError('actual model/optimizer continuity differs')
        for key in ('actual_x_tokens', 'assistant_targets', 'actual_rows', 'dummy_rows', 'padded_slots', 'layer_visit_slots'):
            if sum(e[key] for e in events) != report[key]: raise ValueError('independent raw count sum differs')
        if report['update_seconds'] != [e['seconds'] for e in events] or report['grad_max'] != max(e['gradient_max'] for e in events): raise ValueError('actual timing/gradient raw mismatch')
        if report['train_ce'] != sum(e['ce'] * e['assistant_targets'] for e in events) / report['assistant_targets']:
            raise ValueError('independent actual target-weighted train CE differs')
        for val in [report['before']['val'], *(h['val'] for h in report['history']), report['final_primary'], report['final_secondary']]:
            secondary = val['scope'] == 'COMMON_UNIFORM_MISMATCH_SECONDARY'; policy = route.Policy('uniform_r2' if secondary else arm)
            phase = 'secondary' if secondary else 'val'
            if val['rows'] != val_rows or val['batches'] != val_batches or len(val['route_receipts']) != val_batches: raise ValueError('full fixed VAL denominator required')
            for i, receipt in enumerate(val['route_receipts']):
                expected = route.plan(geometry, report['owners'], policy, i, val_batches, phase)
                if any(receipt[k] != expected[k] for k in ('actual_repeats', 'visits', 'route_sha256', 'receipt_sha256')): raise ValueError('VAL actual matched-policy route differs')
            if sum(r['assistant_targets'] for r in val['route_receipts']) != val['assistant_targets'] or sum(r['visits'] for r in val['route_receipts']) != val['sum_layer_visits']:
                raise ValueError('VAL targets/visits raw denominator mismatch')
        for observations in (report['before']['answers'], report['final_answers']):
            if len(observations) != 8: raise ValueError('all eight fixed original first answers required')
            for i, observation in enumerate(observations):
                if (observation['route'] != route.plan(geometry, report['owners'], route.Policy(arm), i, 8, 'probe')
                        or observation.get('attempts') != 1 or observation.get('precision') != 'FP32_MATH'
                        or observation.get('use_cache') is not False or observation.get('mtp') is not False):
                    raise ValueError('actual answer/session route receipt differs')
        results[arm] = {k: report[k] for k in ('initial_core_sha256', 'final_primary', 'final_secondary', 'final_answers', 'actual_x_tokens', 'assistant_targets', 'layer_visit_slots')}
    if len({r['initial_core_sha256'] for r in results.values()}) != 1 or len({r['actual_x_tokens'] for r in results.values()}) != 1 or len({r['assistant_targets'] for r in results.values()}) != 1:
        raise ValueError('common parent/data/exposure comparison differs')
    return dict(status='RAW_RECOUNTED_NO_AUTOMATIC_ADOPTION', results=results, model_loads=0, learned_router='NOT_IMPLEMENTED')


def worker(args):
    info = signature(args); started = time.perf_counter(); began = datetime.now(timezone.utc); code = 9; error = None
    if path(report_name(args.mode, args.arm, args)).exists() or path(activity_name(args.mode, args.arm, args)).exists(): raise FileExistsError('prior stage preserved')
    remaining = None; expires_at = None; authorization = None
    try:
        remaining = authority(args, info)
        authorization = read(args.authorization); expires_at = authorization['expires_at']
        if args.max_wall_sec > remaining or args.max_wall_sec + actual_spent(args, info) > 144000 or os.getpgrp() != os.getpid():
            raise Hold('whole cap/current authority/family40h/new PGID required')
        with wall(args.max_wall_sec):
            result = run_training(args, args.mode == 'cost') if args.mode in ('cost', 'train') else budget(args) if args.mode == 'budget' else readback(args)
            if result.get('fits') is False: raise Hold('HOLD_BUDGET')
            authority(args, info); result.update(input=info, max_wall_sec=args.max_wall_sec,
                authorization=authorization, authorization_sha256=args.authorization_sha256)
            write(report_name(args.mode, args.arm, args), result); code = 0
    except KeyboardInterrupt: code = 130; error = 'KeyboardInterrupt'
    except Hold as exc: code = 8; error = str(exc); print('[HOLD] ' + str(exc), flush=True)
    except Exception as exc: code = 9; error = type(exc).__name__; print('[ERROR] ' + type(exc).__name__ + ': ' + str(exc), flush=True)
    finally:
        end = datetime.now(timezone.utc)
        write(activity_name(args.mode, args.arm, args), dict(input=info, mode=args.mode, arm=args.arm, complete=code == 0,
            returncode=code, error=error, started_at=began.isoformat(), ended_at=end.isoformat(), seconds=time.perf_counter() - started,
            utc_seconds=(end - began).total_seconds(), pid=os.getpid(), pgid=os.getpgrp(), max_wall_sec=args.max_wall_sec,
            admission_remaining=remaining, authority_expires_at=expires_at,
            authorization=authorization, authorization_sha256=args.authorization_sha256,
            authorization_canonical_sha256=route.sha(authorization),
            report_sha256=digest(path(report_name(args.mode, args.arm, args))) if path(report_name(args.mode, args.arm, args)).is_file() else None))
    return code


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--mode', choices=MODES, required=True)
    p.add_argument('--arm', choices=route.ARMS, default='uniform_r2'); p.add_argument('--corpus-sha256')
    p.add_argument('--corpus', choices=CORPORA, default=CLEAN_CORPUS)
    p.add_argument('--adam-lr', type=float, default=5e-5); p.add_argument('--muon-lr', type=float, default=2e-4)
    p.add_argument('--authorization'); p.add_argument('--authorization-sha256'); p.add_argument('--max-wall-sec', type=int, default=1800)
    p.add_argument('--worker', action='store_true'); action = p.add_mutually_exclusive_group(required=True)
    action.add_argument('--check-only', action='store_true'); action.add_argument('--execute', action='store_true'); args = p.parse_args(argv)
    try:
        if args.mode == 'router': raise Hold('LEARNED_ROUTER_NOT_IMPLEMENTED; no fake-success launcher')
        if any(not math.isfinite(v) or v <= 0 for v in (args.adam_lr, args.muon_lr)): raise ValueError('positive explicit absolute learning rates required')
        if args.check_only:
            contract = signature(args)
            print('[STATIC_ONLY] ' + json.dumps(dict(ready=READY, sources=len(contract['source_sha256']), input_signature_sha256=route.sha(contract), model_loads=0, corpus_reads=0, checkpoint_tensor_loads=0,
                arms=list(route.ARMS), fixed_epochs=4, expected_updates='FROM_PINNED_REPORT', learned_router='NOT_IMPLEMENTED')), flush=True)
            return 0
        if args.mode == 'toy':
            import unittest
            from scripts import test_p078_route_training as tests
            return 0 if unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(tests)).wasSuccessful() else 9
        if not READY: raise Hold('implementation review/actual input binding pending; no real stage admitted')
        if not isinstance(args.corpus_sha256, str) or len(args.corpus_sha256) != 64: raise Hold('root must provide exact frozen corpus report SHA')
        if not 60 <= args.max_wall_sec <= 144000: raise ValueError('declared bounded worker cap required')
        if args.mode == 'evaluate': raise Hold('evaluation is bound to train final primary/secondary; separate evaluate NOT_IMPLEMENTED')
        if args.worker: return worker(args)
        command = [sys.executable, '-B', '-X', 'utf8', str(path('scripts/diag_p078_route_training.py')), *(sys.argv[1:] if argv is None else argv), '--worker']
        process = subprocess.Popen(command, cwd=ROOT, stdin=subprocess.DEVNULL, start_new_session=True)
        try: return process.wait(timeout=args.max_wall_sec)
        except (subprocess.TimeoutExpired, KeyboardInterrupt):
            os.killpg(process.pid, signal.SIGTERM)
            try: process.wait(timeout=30)
            except subprocess.TimeoutExpired: os.killpg(process.pid, signal.SIGKILL); process.wait()
            return 130
    except Hold as exc: print('[HOLD] ' + str(exc), flush=True); return 8
    except Exception as exc: print('[ERROR] ' + type(exc).__name__ + ': ' + str(exc), file=sys.stderr, flush=True); return 9


if __name__ == '__main__': raise SystemExit(main())
