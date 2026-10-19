#!/usr/bin/env python3
"""Pinned R1 native checkpoint CPU function gate, not R2 training or quality.

Only the explicitly launched worker opens checkpoint tensors/tokenizer or builds
real models. Existing product/helper/producer code is never patched. A caught
TERM preserves failure activity; SIGKILL, power loss and filesystem failure do
not carry that guarantee. Public hashes are integrity bindings, not signatures
of authorship or proof that an untrusted writer actually executed the model.
"""
from __future__ import annotations

import argparse
from collections.abc import Mapping
from contextlib import contextmanager
from dataclasses import asdict, replace
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
import traceback
from types import SimpleNamespace
import zipfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

TAG = 'p070b_full_model_cache_v1_s1337'
SCHEMA = 'P070B_FULL_CHECKPOINT_CPU_V1'
SCRIPT = 'scripts/diag_p070b_full_checkpoint_cpu.py'
TEST = 'scripts/test_p070b_full_checkpoint_cpu.py'
CACHE, RAW, EVIDENCE = (ROOT / p / TAG for p in ('data_cache', 'runs/eval', 'test_result/evidence'))
PARENT = ROOT / 'runs/ckpt/m100s10_ko-en_p106b_native_weight_route_v1_s1337_ternary_native.pt'
PARENT_SHA = 'AF3644F5AA515AC1C5E02154582396D080B77E7CD7827F0D32A9EB947ECE747C'
PARENT_CORE = '68F8E780623C7699A411A6E35EDB9809C0911CD03AF719E60DBE4DA6582B6A6D'
TOKENIZER = ROOT / 'data_cache/tok-ko-en-32768-chat32.json'
TOKENIZER_SHA = '9716F40E4C504D6AF37DDE76CCA578E30B45E9CA86C8B6BB79B2FA095D3AC88E'
NATIVE_TAG = 'p106b_native_weight_route_v1_s1337'
NATIVE_REPORT = ROOT / 'test_result/evidence' / NATIVE_TAG / 'train_ternary/report.json'
NATIVE_ACTIVITY = NATIVE_REPORT.parent.parent / 'activity_train_ternary.json'
NATIVE_REFERENCE = ROOT / 'data_cache' / NATIVE_TAG / 'frozen_reference.json'
F4 = ROOT / 'handoff/audit/WIP_20261019b_P070B_FULL_CHECKPOINT_CPU_F4.json'
END = datetime(2026, 10, 20, 8, tzinfo=timezone.utc)
RECORD_RESERVE, MAX_WALL, PUBLIC_LIMIT = 600, 600, 20_000_000
ATOL, RTOL, SEED, MAX_IDS, PREFILL = 1e-5, 1e-4, 0, 64, 3
PROMPTS = (('ko', '한국어로 짧게 인사해 주세요.'),
           ('en', 'Please give a short greeting in English.'))
ROUTES = (('product_r1', None, 1), ('fixed_r1', 'uniform', 1),
          ('r2_uniform', 'uniform', 2), ('r2_reverse', 'reverse', 2), ('r2_shuffle', 'shuffle', 2))
THREAD_ENV = dict(OMP_NUM_THREADS='1', MKL_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1',
                  NUMEXPR_NUM_THREADS='1', TOKENIZERS_PARALLELISM='false', PYTHONDONTWRITEBYTECODE='1')
LIMITATIONS = dict(parent_is_r2_trained=False, old_stage1w_r2_parent_complete=False,
    route_training='NOT_RUN', language_quality='NOT_RUN', generation='NOT_RUN',
    optimizer_updates=0, checkpoint_writes=0, gpu_calls=0,
    route_semantics='same CLA-atomic permuted body in BOTH cycles, not old P070 second-cycle-only',
    claimed_scope='CPU_FUNCTION_ONLY_NOT_SCIENTIFIC_ADOPTION')


class Pending(RuntimeError):
    """An exact input, time or completed receipt is not available."""


class ToleranceFailure(ValueError):
    """Finite same-shape numerical failure, retaining bounded raw references."""
    def __init__(self, metrics, full, cached):
        self.metrics, self.full, self.cached = metrics, full, cached
        super().__init__('fixed tolerance failed: ' + json.dumps(metrics, sort_keys=True, allow_nan=False))


def canonical(value):
    return json.loads(json.dumps(value, ensure_ascii=False, sort_keys=True, allow_nan=False))


def sha(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
        separators=(',', ':'), allow_nan=False).encode('utf-8')).hexdigest().upper()


def safe(path):
    path = Path(path)
    if not path.is_absolute() or '..' in path.parts or not path.is_relative_to(ROOT):
        raise ValueError('exact repository-local absolute path required')
    for item in (path, *path.parents):
        if item.is_symlink(): raise ValueError('symlink input/output forbidden')
        if item == ROOT: break
    return path


def digest(path):
    path = safe(path)
    if not path.is_file(): raise Pending('missing pinned file: ' + str(path.relative_to(ROOT)))
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''): value.update(block)
    return value.hexdigest().upper()


def read_json(path):
    path = safe(path)
    if not path.is_file(): raise Pending('missing receipt: ' + str(path.relative_to(ROOT)))
    if path.stat().st_size >= PUBLIC_LIMIT: raise ValueError('JSON must be smaller than20MB')
    return json.loads(path.read_text(encoding='utf-8'))


def write_json(path, value):
    path = safe(path)
    if not any(path.is_relative_to(base) for base in (CACHE, RAW, EVIDENCE)):
        raise ValueError('only the new namespace may be written')
    payload = (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()
    if len(payload) >= PUBLIC_LIMIT: raise ValueError('public JSON must be smaller than20MB')
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream: stream.write(payload)


def native_module():
    # Its module body is stdlib/receipt-only. Never call its runtime/model APIs.
    from scripts import diag_p106b_native_weight_route as native
    return native


def info():
    native = native_module()
    code = sorted(set((*native.CODE, SCRIPT, TEST, 'scripts/p070b_cla_routes.py',
        'scripts/test_p070b_cla_routes.py', 'scripts/test_p070b_cla_nonidentity.py')))
    pins = {path: digest(ROOT / path) if safe(ROOT / path).is_file() else 'NOT_CREATED' for path in code}
    return canonical(dict(schema=SCHEMA, tag=TAG, code_sha256=pins,
        code_complete=all(value != 'NOT_CREATED' for value in pins.values()),
        f4_sha256=digest(F4), parent=str(PARENT.relative_to(ROOT)), parent_sha256=PARENT_SHA,
        parent_core_sha256=PARENT_CORE, parent_kind='COMPLETED_SCRATCH_TERNARY_R1_D768_L14',
        tokenizer=str(TOKENIZER.relative_to(ROOT)), tokenizer_sha256=TOKENIZER_SHA,
        native_report=str(NATIVE_REPORT.relative_to(ROOT)),
        routes=[dict(name=name, mode=mode, repeats=repeats) for name, mode, repeats in ROUTES],
        inputs=[dict(language=lang, text_sha256=sha(text)) for lang, text in PROMPTS],
        input_encoding='encode(add_special_tokens=False), no extra BOS, no truncation',
        max_input_ids=MAX_IDS, prefill_ids=PREFILL, shuffle_seed=SEED, atol=ATOL, rtol=RTOL,
        device='cpu', dtype='float32', attention='SDPA_MATH', torch_threads=1,
        shape=dict(vocab_size=32768, dim=768, ffn_dim=2048, n_q_heads=12, n_kv_heads=3,
            emb_rank=256, n_prelude=2, n_middle=10, n_coda=2, cla_group=2, cla_edges=True,
            tie_mlp=False, grad_checkpoint=True, max_seq_len=1024),
        authority_end_utc=END.isoformat(), record_reserve_seconds=RECORD_RESERVE,
        worker_max_seconds=MAX_WALL, public_file_limit_exclusive=PUBLIC_LIMIT,
        raw_policy='write-once NPZ ids/full/cached under ignored runs/eval; each file below20MB',
        integrity='unkeyed SHA256 integrity binding, not authenticity', limitations=LIMITATIONS))


def cap(value):
    if type(value) is not int or not 1 <= value <= MAX_WALL:
        raise ValueError('explicit integer worker cap1..600s required')
    return value


def authority(max_wall_sec=MAX_WALL, now=None):
    cap(max_wall_sec); now = datetime.now(timezone.utc) if now is None else now
    if now.tzinfo is None: raise ValueError('timezone-aware UTC time required')
    remaining = (END - now).total_seconds() - RECORD_RESERVE
    if remaining < max_wall_sec: raise Pending('worker cap cannot spend the final600s record reserve')
    return remaining


def validate_parent_receipt(report, activity, native_info, report_sha, reference_sha):
    native_module().validate_activity(activity, 'train_ternary', complete=True)
    if (any(report.get(k) != v for k, v in native_info.items())
            or report.get('status') != 'TRAIN_COMPLETE' or report.get('arm') != 'ternary'
            or report.get('endpoint') != 'native' or report.get('cost') is not False
            or report.get('updates') != 2281 or report.get('native_draw_tokens') != 298975232
            or report.get('totals', {}).get('targets') != 298975232
            or report.get('checkpoint') != str(PARENT.relative_to(ROOT)) or report.get('checkpoint_sha256') != PARENT_SHA
            or report.get('final_core_sha256') != PARENT_CORE or report.get('checkpoint_writes') != 1
            or report.get('optimizer_saved') is not False or report.get('parent_checkpoint_sha256') is not None
            or report.get('parent_core_sha256') is not None or report.get('parent_training_weights_copied') is not False
            or report.get('initializer') != 'load_runtime(scratch_ntp)'
            or report.get('initial_core_sha256') != report.get('scratch_core_sha256')
            or report.get('scratch_core_sha256') in (None, native_module().PARENT_CORE)
            or report.get('reference_sha256') != reference_sha):
        raise ValueError('exact completed scratch ternary R1 producer report required')
    if (activity.get('schema') != native_info['schema'] or activity.get('tag') != NATIVE_TAG
            or activity.get('key') != 'train_ternary' or activity.get('mode') != 'train'
            or activity.get('arm') != 'ternary' or activity.get('endpoint') is not None
            or activity.get('returncode') != 0 or activity.get('complete') is not True
            or activity.get('error_type') is not None or activity.get('result_sha256') != report_sha
            or activity.get('reference_sha256') != reference_sha
            or activity.get('code_sha256') != native_info['code_sha256']):
        raise ValueError('completed producer activity/report/reference/code binding required')


def preflight(max_wall_sec=MAX_WALL, *, require_fresh=True):
    authority(max_wall_sec)
    recipe = info()
    if not recipe['code_complete']: raise Pending('both new source files and all producer pins required')
    if require_fresh and any(safe(path).exists() for path in (CACHE, RAW, EVIDENCE)):
        raise FileExistsError('preserve prior complete or partial namespace; no automatic retry')
    for path in (PARENT, TOKENIZER):
        if not safe(path).is_file() or path.stat().st_size <= 0: raise Pending('missing pinned input file')
    if TOKENIZER.stat().st_size >= PUBLIC_LIMIT: raise ValueError('bounded tokenizer JSON required')
    native = native_module(); parent = read_json(NATIVE_REPORT); activity = read_json(NATIVE_ACTIVITY)
    report_sha, reference_sha = digest(NATIVE_REPORT), digest(NATIVE_REFERENCE)
    validate_parent_receipt(parent, activity, native.info(), report_sha, reference_sha)
    return dict(recipe_sha256=sha(recipe), native_report_sha256=report_sha,
        native_activity_sha256=digest(NATIVE_ACTIVITY), native_reference_sha256=reference_sha,
        parent_file_bytes=PARENT.stat().st_size, parent_file_sha256='WORKER_ONLY',
        tokenizer_bytes=TOKENIZER.stat().st_size, tokenizer_sha256='WORKER_ONLY',
        real_models_created=0, checkpoint_tensors_loaded=0, tokenizer_loaded=False, writes=0)


def fingerprint(model):
    value = hashlib.sha256()
    import torch
    for name, tensor in sorted(model.state_dict().items()):
        if name in ('mtp_up2', 'mtp_up3', 'mtp_up4'): continue
        tensor = tensor.detach().cpu().contiguous()
        value.update((name + str(tensor.shape) + str(tensor.dtype)).encode())
        value.update(tensor.view(-1).view(torch.uint8).numpy().tobytes())
    return value.hexdigest().upper()


def validate_cfg(cfg):
    from scripts.p106b_weight_route import _check_cfg
    _check_cfg(cfg)  # Pure metadata guard BEFORE changing the explicit visit count.
    for name, expected in info()['shape'].items():
        if getattr(cfg, name) != expected: raise ValueError('unsupported exact parent cfg: ' + name)
    if cfg.n_layers != 14 or cfg.quant_anneal != 1. or cfg.repeat_mode != 'uniform':
        raise ValueError('pinned unmodified R1 geometry and terminal anneal1 required')


def validate_payload(payload, cfg, report):
    from scripts.p106b_weight_route import validate_route_metadata
    if not isinstance(payload, Mapping) or set(payload) != {
            'model', 'cfg', 'step', 'tokenizer_sha256', 'tokenizer_lineage', 'quantization_route', 'experiment'}:
        raise ValueError('exact producer checkpoint envelope required')
    validate_route_metadata(payload['quantization_route'], 'ternary')
    if (payload['step'] != 2281 or payload['tokenizer_sha256'] != TOKENIZER_SHA
            or payload['tokenizer_lineage'] != 'chat32' or canonical(payload['cfg']) != canonical(asdict(cfg))
            or payload['experiment'] != native_module().cp_experiment(report)):
        raise ValueError('checkpoint cfg/tokenizer/step/producer lineage differs')


def strict_load(model, payload, expected_core):
    import torch
    native_module().validate_cpu_state(model, payload, torch)
    model.load_state_dict(payload['model'], strict=True); model.clear_quant()
    if fingerprint(model) != expected_core: raise ValueError('loaded parameter core differs from exact pinned parent')


def array_sha(array):
    return hashlib.sha256(array.tobytes(order='C')).hexdigest().upper()


def comparison(full, cached):
    import numpy as np
    if (full.shape != cached.shape or full.dtype != np.float32 or cached.dtype != np.float32
            or full.ndim != 3 or full.shape[0] != 1 or min(full.shape) <= 0
            or not np.isfinite(full).all() or not np.isfinite(cached).all()):
        raise ValueError('nonempty matching finite CPU FP32 logits required')
    diff = np.abs(full - cached)
    result = dict(shape=list(full.shape), elements=int(full.size), dtype='float32',
        max_abs=float(diff.max()), mean_abs=float(diff.mean(dtype=np.float64)),
        atol=ATOL, rtol=RTOL, close=bool(np.allclose(full, cached, atol=ATOL, rtol=RTOL)),
        full_sha256=array_sha(full), cached_sha256=array_sha(cached))
    if not result['close']: raise ToleranceFailure(result, full, cached)
    return result


def cache_receipt(model, bank, tokens, *, fixed):
    import torch
    from scripts import p070b_cla_routes as routes
    schedule = model.visit_schedule(); trace = routes.trace(model.cfg, model.owner, schedule)
    identity = routes.route_sha(model.cfg, model.owner, schedule)
    expected = {tuple(event['key']) if isinstance(event['key'], (list, tuple)) else event['key']
                for event in trace['events'] if event['layer'] == event['owner']}
    if fixed:
        if not isinstance(bank, routes.RouteCache) or bank.route_sha256 != identity:
            raise ValueError('cache must be bound to the exact actual fixed route SHA')
    elif type(bank) is not dict:
        raise ValueError('product R1 cache must use the original dict API')
    if set(bank) != expected or len(bank) != trace['kv_entries']:
        raise ValueError('actual owner/visit cache entries differ')
    expected_shape = (1, model.cfg.n_kv_heads, tokens, model.cfg.head_dim)
    for pair in bank.values():
        if not isinstance(pair, tuple) or len(pair) != 2: raise ValueError('K/V tuple required')
        for tensor in pair:
            if (tensor.device.type != 'cpu' or tensor.dtype != torch.float32 or tuple(tensor.shape) != expected_shape
                    or not bool(torch.isfinite(tensor).all())):
                raise ValueError('finite exact CPU FP32 K/V shape required')
    return dict(route_sha256=identity, route=schedule, owners=list(model.owner),
        visits=trace['visits'], kv_entries=len(bank), kv_shape=list(expected_shape),
        dtype='float32', tokens=tokens, keys=canonical(sorted(expected, key=str)))


def cache_case(model, ids, *, fixed):
    import torch
    if ids.device.type != 'cpu' or ids.dtype != torch.long or ids.ndim != 2 or ids.shape[0] != 1:
        raise ValueError('single CPU int64 input required')
    if not PREFILL < ids.shape[1] <= MAX_IDS: raise ValueError('input must contain4..64 IDs without truncation')
    from torch.nn.attention import sdpa_kernel, SDPBackend
    model.eval(); model.clear_quant()
    try:
        with torch.no_grad(), torch.autocast('cpu', enabled=False), sdpa_kernel(SDPBackend.MATH):
            model.freeze_quant()
            full = model(ids).detach().cpu().numpy().copy()
            first, past = model(ids[:, :PREFILL], use_cache=True); pieces = [first]
            cache_receipt(model, past, PREFILL, fixed=fixed)
            for index in range(PREFILL, ids.shape[1]):
                out, past = model(ids[:, index:index + 1], past_kv=past, use_cache=True)
                cache_receipt(model, past, index + 1, fixed=fixed); pieces.append(out)
            cached = torch.cat(pieces, dim=1).detach().cpu().numpy().copy()
            receipt = cache_receipt(model, past, ids.shape[1], fixed=fixed)
        return full, cached, dict(comparison= comparison(full, cached), cache=receipt)
    finally:
        model.clear_quant()


def route_change_rejected(model, ids):
    import torch
    from scripts import p070b_cla_routes as routes
    original = model.visit_schedule(); before = model.route_sha256
    changed = routes.schedule(model.cfg, model.owner, 'reverse', 2, SEED)
    if changed == original: raise ValueError('rejection probe requires an actual changed route')
    try:
        model.eval(); model.clear_quant()
        with torch.no_grad():
            model.freeze_quant(); _, past = model(ids[:, :PREFILL], use_cache=True)
            model.set_route(changed)
            try: model(ids[:, PREFILL:PREFILL + 1], past_kv=past, use_cache=True)
            except ValueError as exc:
                if 'route changed' not in str(exc): raise
            else: raise ValueError('changed-route cache was silently accepted')
        return dict(rejected=True, before_route_sha256=before, changed_route_sha256=model.route_sha256)
    finally:
        model.set_route(original); model.clear_quant()


def gradient_receipt(model):
    import torch
    observed, nonzero, norm2 = 0, 0, 0.
    for _, parameter in model.named_parameters():
        if parameter.grad is None: continue
        grad = parameter.grad.detach()
        if not bool(torch.isfinite(grad).all()): raise ValueError('nonfinite full-model gradient')
        observed += 1; nonzero += int(bool(grad.ne(0).any()))
        norm2 += float(grad.double().square().sum())
    linears = list(model._tlinear_cache)
    if (not linears or any(layer.weight.grad is None for layer in linears)
            or model.emb.weight.grad is None or not bool(model.emb.weight.grad.ne(0).any())
            or not any(bool(layer.weight.grad.ne(0).any()) for layer in linears)
            or not observed or not nonzero or not math.isfinite(norm2) or norm2 <= 0):
        raise ValueError('embedding and visited ternary-body positive gradient connection required')
    return dict(gradient_tensors=observed, nonzero_gradient_tensors=nonzero,
        connected_tlinear_weights=len(linears), positive_tlinear_weights=sum(bool(m.weight.grad.ne(0).any()) for m in linears),
        embedding_positive=True, finite=True, total_l2=math.sqrt(norm2), optimizer_updates=0)


def backward_case(model, ids):
    import torch
    from torch.nn.attention import sdpa_kernel, SDPBackend
    from tinylm.train import mtp_sft as core
    before = fingerprint(model)
    model.clear_quant(); model.train(); model.zero_grad(set_to_none=True)
    try:
        with torch.autocast('cpu', enabled=False), sdpa_kernel(SDPBackend.MATH):
            model.refresh_quant()
            if model._quant_frozen or any(not m._wq.requires_grad for m in model._tlinear_cache):
                raise ValueError('detached eval freeze cache cannot be used for backward')
            x, y = ids[:, :-1], ids[:, 1:]
            sums, counts = core.components(model, model(x, return_hidden=True), y, torch.ones_like(y),
                horizons=(), checkpoint_heads=False)
            if counts[1] != y.numel() or counts[1] <= 0: raise ValueError('exact next-token denominator required')
            loss = sums[1] / counts[1]
            if not bool(torch.isfinite(loss)): raise ValueError('nonfinite NTP loss')
            loss.backward(); gradients = gradient_receipt(model)
        after = fingerprint(model)
        if before != after: raise ValueError('backward without optimizer mutated weights')
        return dict(targets=counts[1], loss=float(loss.detach()), gradients=gradients,
            core_before=before, core_after=after, quant_cache='clear/train/grad-enabled refresh, not eval detached cache')
    finally:
        model.zero_grad(set_to_none=True); model.clear_quant(); model.eval()


def save_raw(name, ids, full, cached, *, allow_tolerance_failure=False):
    import numpy as np
    try: result = comparison(full, cached)
    except ToleranceFailure as exc:
        if not allow_tolerance_failure: raise
        result = exc.metrics
    path = safe(RAW / (name + '.npz'))
    if not path.is_relative_to(RAW) or path.name != name + '.npz': raise ValueError('exact raw filename required')
    if full.nbytes + cached.nbytes + ids.nbytes + 4096 >= PUBLIC_LIMIT:
        raise ValueError('comparison raw file must be smaller than20MB')
    with path.open('xb') as stream: np.savez(stream, ids=ids, full=full, cached=cached)
    if path.stat().st_size >= PUBLIC_LIMIT: raise ValueError('raw file reached20MB limit')
    return dict(path=str(path.relative_to(ROOT)), bytes=path.stat().st_size, sha256=digest(path),
        ids_sha256=array_sha(ids), comparison=result)


def record_tolerance_failure(route, language, ids, error, kind, route_sha256):
    """Preserve the first numerical negative; this never creates COMPLETE."""
    if (not isinstance(error, ToleranceFailure) or route not in {r[0] for r in ROUTES}
            or language not in {p[0] for p in PROMPTS}
            or kind not in ('FULL_VS_CACHED', 'PRODUCT_R1_VS_FIXED_R1')
            or type(route_sha256) is not str or len(route_sha256) != 64
            or any(c not in '0123456789ABCDEF' for c in route_sha256)):
        raise ValueError('only a declared finite numerical tolerance failure may be preserved')
    raw = save_raw('failure_' + route + '_' + language, ids, error.full, error.cached,
        allow_tolerance_failure=True)
    if raw['comparison']['close'] is not False or raw['comparison'] != error.metrics:
        raise ValueError('failure raw must reproduce the same close=False metrics')
    failure = seal(dict(recipe=info(), status='CPU_TOLERANCE_FAILED', complete=False,
        route=route, route_sha256=route_sha256, language=language, comparison_kind=kind, input_ids=int(ids.shape[1]),
        parent_sha256=PARENT_SHA, parent_core_sha256=PARENT_CORE, raw=raw,
        contract_sha256=digest(CACHE / 'contract.json'), limitations=LIMITATIONS))
    write_json(EVIDENCE / 'failure.json', failure)
    print('[P070B_CPU_TOLERANCE_FAILURE] ' + json.dumps(dict(route=route, language=language,
        comparison_kind=kind, comparison=error.metrics, raw_path=raw['path'], raw_sha256=raw['sha256'],
        failure_sha256=digest(EVIDENCE / 'failure.json'))), flush=True)


def read_raw(entry):
    import numpy as np
    path = safe(ROOT / entry['path'])
    if (not path.is_relative_to(RAW) or path.suffix != '.npz' or not 0 < entry['bytes'] < PUBLIC_LIMIT
            or path.stat().st_size != entry['bytes'] or digest(path) != entry['sha256']):
        raise ValueError('exact bounded raw bytes/hash required')
    with zipfile.ZipFile(path) as archive:
        members = archive.infolist()
        if (len(members) != 3 or {m.filename for m in members} != {'ids.npy', 'full.npy', 'cached.npy'}
                or sum(m.file_size for m in members) >= PUBLIC_LIMIT
                or any(m.compress_type != zipfile.ZIP_STORED for m in members)):
            raise ValueError('bounded uncompressed raw arrays required before allocation')
    with np.load(path, allow_pickle=False) as arrays:
        if set(arrays.files) != {'ids', 'full', 'cached'}: raise ValueError('exact raw array members required')
        ids, full, cached = (arrays[key] for key in ('ids', 'full', 'cached'))
        if (ids.dtype != np.int64 or ids.shape != (1, full.shape[1])
                or not PREFILL < ids.shape[1] <= MAX_IDS or array_sha(ids) != entry['ids_sha256']
                or comparison(full, cached) != entry['comparison']):
            raise ValueError('actual raw arrays/denominators differ from report')
        return ids.copy(), full.copy()


def run_gate(binding):
    import torch
    from tokenizers import Tokenizer
    from tinylm.config import TMTConfig
    from tinylm.model import TiedMLPTransformer
    from tinylm.data.prepare import verify_chat_tokenizer
    from scripts import p070b_cla_routes as routes
    if torch.cuda.is_initialized(): raise ValueError('CPU worker must never initialize CUDA')
    torch.set_num_threads(1)
    if torch.get_num_interop_threads() != 1: torch.set_num_interop_threads(1)
    if torch.get_num_threads() != 1 or torch.get_num_interop_threads() != 1:
        raise ValueError('single torch intra/inter-op thread required')
    before_parent, before_tok = digest(PARENT), digest(TOKENIZER)
    if before_parent != PARENT_SHA or before_tok != TOKENIZER_SHA: raise ValueError('pinned parent/tokenizer SHA differs')
    tok = Tokenizer.from_file(str(TOKENIZER)); verify_chat_tokenizer(tok, info()['shape']['vocab_size'])
    inputs = [(lang, torch.tensor([tok.encode(text, add_special_tokens=False).ids], dtype=torch.long)) for lang, text in PROMPTS]
    if any(not PREFILL < ids.shape[1] <= MAX_IDS for _, ids in inputs): raise ValueError('fixed input length outside4..64; never truncate')
    payload = torch.load(PARENT, map_location='cpu', weights_only=True)
    cfg = TMTConfig(**payload['cfg']); validate_cfg(cfg)
    validate_payload(payload, cfg, read_json(NATIVE_REPORT))
    cases, products, equality = [], {}, []
    backward, rejection, observed_routes, route_cfgs = None, None, {}, {}
    for name, mode, repeats in ROUTES:
        torch.manual_seed(1337)
        current_cfg = replace(cfg, train_repeat=float(repeats), infer_repeat=1.)
        route_cfgs[name] = canonical(asdict(current_cfg))
        model = TiedMLPTransformer(current_cfg) if mode is None else routes.FixedRouteTransformer(current_cfg, mode, repeats, SEED)
        strict_load(model, payload, PARENT_CORE)
        observed_routes[name] = model.visit_schedule()
        if name == 'r2_shuffle' and observed_routes[name] in (observed_routes['r2_uniform'], observed_routes['r2_reverse']):
            raise ValueError('seed0 must be an actual third, nonidentity full-model route')
        for lang, ids in inputs:
            try: full, cached, observed = cache_case(model, ids, fixed=mode is not None)
            except ToleranceFailure as exc:
                record_tolerance_failure(name, lang, ids.numpy(), exc, 'FULL_VS_CACHED',
                    routes.route_sha(model.cfg, model.owner, model.visit_schedule()))
                raise
            if observed['cache']['kv_entries'] != (7 if repeats == 1 else 12): raise ValueError('full parent requires7/12 KV entries')
            raw = save_raw(name + '_' + lang, ids.numpy(), full, cached)
            cases.append(dict(route=name, language=lang, input_ids=ids.shape[1], raw=raw, **observed))
            if name == 'product_r1': products[lang] = full.copy()
            if name == 'fixed_r1':
                try: paired = comparison(products[lang], full)
                except ToleranceFailure as exc:
                    record_tolerance_failure(name, lang, ids.numpy(), exc, 'PRODUCT_R1_VS_FIXED_R1',
                        routes.route_sha(model.cfg, model.owner, model.visit_schedule()))
                    raise
                equality.append(dict(language=lang, comparison=paired))
        if name == 'r2_uniform':
            rejection = route_change_rejected(model, inputs[0][1])
            backward = backward_case(model, inputs[1][1])
        if fingerprint(model) != PARENT_CORE: raise ValueError('route CPU diagnostics mutated loaded weights')
        for case in cases:
            if case['route'] == name: case['core_before'] = case['core_after'] = PARENT_CORE
        model.clear_quant(); del model; gc.collect()
    del payload
    if (digest(PARENT) != before_parent or digest(TOKENIZER) != before_tok or torch.cuda.is_initialized()):
        raise ValueError('input bytes changed or CUDA initialized during CPU gate')
    return dict(status='CPU_FUNCTION_COMPLETE', binding=binding, cases=cases, product_r1_equivalence=equality,
        parent_cfg=canonical(asdict(cfg)), parent_cfg_sha256=sha(asdict(cfg)), route_cfgs=route_cfgs,
        backward=backward, route_change_rejection=rejection,
        parent_sha256_before=before_parent, parent_sha256_after=before_parent,
        tokenizer_sha256_before=before_tok, tokenizer_sha256_after=before_tok,
        model_instances=5, real_checkpoint_tensor_loads=1, cuda_initialized=False, limitations=LIMITATIONS)


def seal(value):
    value = canonical(value)
    return dict(value, integrity_sha256=sha(value))


def validate_report_core(report, *, raw=True):
    from scripts import p070b_cla_routes as routes
    geometry = info()['shape']; layers = sum(geometry[k] for k in ('n_prelude', 'n_middle', 'n_coda'))
    cfg = SimpleNamespace(**geometry, n_layers=layers)
    owners = [i - i % cfg.cla_group for i in range(layers)]
    head_dim = cfg.dim // cfg.n_q_heads
    unsigned = {k: v for k, v in report.items() if k != 'integrity_sha256'}
    if (report.get('integrity_sha256') != sha(unsigned) or report.get('recipe') != info()
            or report.get('status') != 'CPU_FUNCTION_COMPLETE' or report.get('limitations') != LIMITATIONS
            or report.get('model_instances') != 5 or report.get('real_checkpoint_tensor_loads') != 1
            or report.get('cuda_initialized') is not False
            or any(report.get(key) != expected for key, expected in (
                ('parent_sha256_before', PARENT_SHA), ('parent_sha256_after', PARENT_SHA),
                ('tokenizer_sha256_before', TOKENIZER_SHA), ('tokenizer_sha256_after', TOKENIZER_SHA)))):
        raise ValueError('complete exact-code/source/recipe CPU function report required')
    contract = read_json(CACHE / 'contract.json')
    if (contract.get('recipe') != info() or report.get('binding') != contract.get('binding')
            or report['binding'].get('recipe_sha256') != sha(info())
            or report.get('contract_sha256') != digest(CACHE / 'contract.json')):
        raise ValueError('report/immutable contract/metadata binding differs')
    parent_cfg = report.get('parent_cfg', {})
    if (report.get('parent_cfg_sha256') != sha(parent_cfg)
            or any(parent_cfg.get(k) != v for k, v in geometry.items())
            or parent_cfg.get('train_repeat') != 1. or parent_cfg.get('infer_repeat') != 1.
            or set(report.get('route_cfgs', {})) != {name for name, _, _ in ROUTES}):
        raise ValueError('complete exact R1 cfg and all five cfg receipts required')
    for name, _, repeats in ROUTES:
        if report['route_cfgs'][name] != dict(parent_cfg, train_repeat=float(repeats), infer_repeat=1.):
            raise ValueError('only the explicitly declared repeat count may differ in runtime cfg')
    expected = {(name, lang) for name, _, _ in ROUTES for lang, _ in PROMPTS}
    cases = report.get('cases', [])
    if len(cases) != 10 or {(c['route'], c['language']) for c in cases} != expected:
        raise ValueError('all five routes times two inputs must be consumed')
    arrays, identities = {}, {}
    for case in cases:
        name, lang = case['route'], case['language']; cache = case['cache']; count = case['input_ids']
        repeats = 1 if name in ('product_r1', 'fixed_r1') else 2
        mode = next(mode for route, mode, _ in ROUTES if route == name) or 'uniform'
        scheduled = routes.schedule(cfg, owners, mode, repeats, SEED)
        traced = routes.trace(cfg, owners, scheduled)
        keys = {event['key'] for event in traced['events'] if event['layer'] == event['owner']}
        if (case.get('core_before') != PARENT_CORE or case.get('core_after') != PARENT_CORE
                or not PREFILL < count <= MAX_IDS or cache['kv_entries'] != (7 if repeats == 1 else 12)
                or cache['visits'] != cfg.n_prelude + cfg.n_coda + cfg.n_middle * repeats
                or cache['route'] != scheduled or cache['owners'] != owners
                or cache['keys'] != canonical(sorted(keys, key=str))
                or cache['route_sha256'] != routes.route_sha(cfg, owners, scheduled)
                or cache['tokens'] != count or cache['dtype'] != 'float32'
                or cache['kv_shape'] != [1, cfg.n_kv_heads, count, head_dim]
                or case['comparison'] != case['raw']['comparison'] or not case['comparison']['close']
                or case['comparison']['shape'] != [1, count, cfg.vocab_size]
                or case['comparison']['elements'] != count * cfg.vocab_size
                or case['comparison']['atol'] != ATOL or case['comparison']['rtol'] != RTOL):
            raise ValueError('exact full-model cache/raw/comparison denominators required')
        identity = sha([cache['route'], cache['owners'], cache['keys']])
        if name in identities and identities[name] != identity: raise ValueError('route changed between languages')
        identities[name] = identity
        if raw: arrays[(name, lang)] = read_raw(case['raw'])
    if (identities['product_r1'] != identities['fixed_r1']
            or len({identities[n] for n in ('r2_uniform', 'r2_reverse', 'r2_shuffle')}) != 3):
        raise ValueError('actual nonidentity shuffle/reverse and R1 equivalence required')
    equal = report.get('product_r1_equivalence', [])
    if len(equal) != 2 or {e['language'] for e in equal} != {'ko', 'en'}: raise ValueError('two R1 paired comparisons required')
    if raw:
        for lang, _ in PROMPTS:
            ids, product = arrays[('product_r1', lang)]
            for name, _, _ in ROUTES:
                if not __import__('numpy').array_equal(ids, arrays[(name, lang)][0]): raise ValueError('same actual input across all routes required')
            item = next(e for e in equal if e['language'] == lang)
            if item['comparison'] != comparison(product, arrays[('fixed_r1', lang)][1]): raise ValueError('raw R1 equivalence differs')
    gradients = report.get('backward', {}).get('gradients', {})
    backward = report.get('backward', {})
    targets = next(case['input_ids'] - 1 for case in cases if case['route'] == 'r2_uniform' and case['language'] == 'en')
    expected_tlinears = 5 * layers + 2 * (layers // cfg.cla_group)
    if (backward.get('core_before') != PARENT_CORE or backward.get('core_after') != PARENT_CORE
            or type(backward.get('targets')) is not int or backward['targets'] != targets
            or not isinstance(backward.get('loss'), (int, float)) or not math.isfinite(backward['loss'])
            or gradients.get('finite') is not True or gradients.get('embedding_positive') is not True
            or gradients.get('connected_tlinear_weights') != expected_tlinears
            or not 0 < gradients.get('positive_tlinear_weights', 0) <= expected_tlinears
            or not gradients.get('nonzero_gradient_tensors', 0) or not 0 < gradients.get('total_l2', 0) < math.inf
            or gradients.get('optimizer_updates') != 0
            or report.get('route_change_rejection', {}).get('rejected') is not True
            or report['route_change_rejection']['before_route_sha256'] == report['route_change_rejection']['changed_route_sha256']):
        raise ValueError('finite positive full-model backward and changed-cache rejection required')
    return report


@contextmanager
def termination_guard():
    previous, interrupted = signal.getsignal(signal.SIGTERM), False
    def terminate(*_):
        nonlocal interrupted
        if not interrupted:
            interrupted = True; raise KeyboardInterrupt('owned CPU worker received SIGTERM')
    signal.signal(signal.SIGTERM, terminate)
    try: yield
    finally: signal.signal(signal.SIGTERM, previous)


@contextmanager
def bounded_worker(seconds):
    cap(seconds); previous = signal.getsignal(signal.SIGALRM); previous_timer = signal.getitimer(signal.ITIMER_REAL)
    def expired(*_): raise TimeoutError('CPU worker600s/caller cap exceeded')
    signal.signal(signal.SIGALRM, expired); signal.setitimer(signal.ITIMER_REAL, seconds)
    environment = {key: os.environ.get(key) for key in THREAD_ENV}
    os.environ.update(THREAD_ENV)
    try: yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, *previous_timer); signal.signal(signal.SIGALRM, previous)
        for key, value in environment.items():
            if value is None: os.environ.pop(key, None)
            else: os.environ[key] = value


def worker(max_wall_sec=MAX_WALL):
    cap(max_wall_sec)
    if any(safe(path).exists() for path in (CACHE, RAW, EVIDENCE)):
        raise FileExistsError('preserve prior partial namespace; automatic rerun forbidden')
    recipe = info(); began = time.perf_counter(); started = datetime.now(timezone.utc).isoformat()
    code, error, owned = 9, None, False
    with termination_guard():
        try:
            safe(EVIDENCE).mkdir(parents=True, exist_ok=False); owned = True
            with bounded_worker(max_wall_sec):
                binding = preflight(max_wall_sec, require_fresh=False)
                for directory in (CACHE, RAW): safe(directory).mkdir(parents=True, exist_ok=False)
                write_json(CACHE / 'contract.json', dict(recipe=recipe, binding=binding))
                report = seal(dict(recipe=recipe, contract_sha256=digest(CACHE / 'contract.json'), **run_gate(binding)))
                validate_report_core(report)
                if recipe != info(): raise ValueError('code/recipe changed during CPU worker')
                write_json(EVIDENCE / 'report.json', report); code = 0
            return 0
        except BaseException as exc:
            error = type(exc).__name__
            code = 130 if isinstance(exc, KeyboardInterrupt) else 8 if isinstance(exc, (Pending, FileNotFoundError, FileExistsError)) else 9
            raise
        finally:
            if owned:
                report_path = EVIDENCE / 'report.json'; contract_path = CACHE / 'contract.json'
                failure_path = EVIDENCE / 'failure.json'
                write_json(EVIDENCE / 'activity.json', dict(schema=SCHEMA, tag=TAG, complete=code == 0,
                    returncode=code, error_type=error, seconds=time.perf_counter() - began,
                    started_at=started, ended_at=datetime.now(timezone.utc).isoformat(), max_wall_sec=max_wall_sec,
                    recipe_sha256=sha(recipe), code_sha256=recipe['code_sha256'],
                    report_sha256=digest(report_path) if report_path.is_file() else None,
                    contract_sha256=digest(contract_path) if contract_path.is_file() else None,
                    failure_sha256=digest(failure_path) if failure_path.is_file() else None,
                    signal_limit='TERM unwinds activity; SIGKILL/power/write failure not guaranteed'))


def readback():
    report = validate_report_core(read_json(EVIDENCE / 'report.json'))
    activity = read_json(EVIDENCE / 'activity.json'); recipe = info()
    if (activity.get('schema') != SCHEMA or activity.get('tag') != TAG or activity.get('complete') is not True
            or type(activity.get('returncode')) is not int or activity.get('returncode') != 0 or activity.get('error_type') is not None
            or activity.get('recipe_sha256') != sha(recipe) or activity.get('code_sha256') != recipe['code_sha256']
            or activity.get('report_sha256') != digest(EVIDENCE / 'report.json')
            or activity.get('contract_sha256') != report['contract_sha256']
            or type(activity.get('seconds')) not in (int, float) or not math.isfinite(activity['seconds'])
            or not 0 <= activity['seconds'] <= cap(activity['max_wall_sec'])):
        raise ValueError('same-code complete bounded activity/report/contract binding required')
    begin, end = (datetime.fromisoformat(activity[k]) for k in ('started_at', 'ended_at'))
    if (begin.tzinfo is None or end.tzinfo is None or end < begin
            or end > END or (END - begin).total_seconds() < activity['max_wall_sec'] + RECORD_RESERVE):
        raise ValueError('actual activity crosses authority/record reserve')
    return dict(status='CPU_FUNCTION_READBACK_COMPLETE', report_sha256=digest(EVIDENCE / 'report.json'),
        activity_sha256=digest(EVIDENCE / 'activity.json'), raw_cases=len(report['cases']), limitations=LIMITATIONS)


def phase_commands(max_wall_sec=MAX_WALL):
    cap(max_wall_sec); py = [sys.executable, '-B', '-X', 'utf8']; base = py + [SCRIPT]
    flags = ['--max-wall-sec', str(max_wall_sec)]
    return [('REGRESSION', py + ['-m', 'unittest', 'scripts.test_p070b_full_checkpoint_cpu', '-v']),
        ('PREFLIGHT', base + ['--preflight'] + flags), ('EXECUTE', base + ['--execute', '--worker'] + flags)]


def launch(command, timeout):
    if not 0 < timeout <= MAX_WALL: raise Pending('bounded positive remaining phase time required')
    env = dict(os.environ); env.update(THREAD_ENV)
    process = subprocess.Popen(command, cwd=ROOT, stdin=subprocess.DEVNULL, env=env, start_new_session=True)
    try: return process.wait(timeout=timeout)
    except (subprocess.TimeoutExpired, KeyboardInterrupt):
        interrupted = sys.exc_info()[0] is KeyboardInterrupt
        try:
            if process.poll() is None and os.getpgid(process.pid) == process.pid:
                os.killpg(process.pid, signal.SIGTERM)
                try: process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    if process.poll() is None: os.killpg(process.pid, signal.SIGKILL)
                    process.wait(timeout=5)
        except ProcessLookupError: pass
        return 130 if interrupted else 124


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--execute', action='store_true'); action.add_argument('--check-only', action='store_true')
    action.add_argument('--preflight', action='store_true')
    parser.add_argument('--worker', action='store_true'); parser.add_argument('--max-wall-sec', type=int, default=MAX_WALL)
    args = parser.parse_args(argv)
    try:
        cap(args.max_wall_sec)
        if args.worker and not args.execute: raise ValueError('--worker belongs only to --execute')
        if args.check_only:
            print('[P070B_FULL_CPU_CHECK_ONLY] ' + json.dumps(dict(recipe=info(), phases=phase_commands(args.max_wall_sec),
                actual_inputs_opened=False, models_created=0, writes=0)), flush=True); return 0
        if args.preflight:
            print('[P070B_FULL_CPU_PREFLIGHT] ' + json.dumps(preflight(args.max_wall_sec)), flush=True); return 0
        if args.worker: return worker(args.max_wall_sec)
        authority(args.max_wall_sec)
        if any(safe(path).exists() for path in (CACHE, RAW, EVIDENCE)):
            raise FileExistsError('preserve prior complete/partial namespace; no new final appended')
        from scripts.p106b_stage_receipt import pipeline
        phases = phase_commands(args.max_wall_sec); began = time.monotonic(); completed = None
        def run(command):
            nonlocal completed
            remaining = min(args.max_wall_sec - (time.monotonic() - began), authority(1))
            value = launch(command, min(remaining, 60) if command != phases[-1][1] else remaining)
            if command == phases[-1][1] and value == 0: completed = readback()
            return value
        receipt = pipeline(phases, run, lambda line: print(line, flush=True), experiment=SCHEMA)
        if receipt['returncode'] == 0 and completed is None: raise ValueError('no final actual model receipt; zero work is not success')
        final = seal(dict(recipe=info(), phases=receipt, readback=completed, limitations=LIMITATIONS))
        if EVIDENCE.is_dir(): write_json(EVIDENCE / 'final.json', final)
        print('[P070B_FULL_CPU_FINAL] ' + json.dumps(final), flush=True)
        return receipt['returncode']
    except (Pending, FileNotFoundError, FileExistsError) as exc:
        print('[P070B_FULL_CPU_FINAL] HOLD8: ' + str(exc), flush=True); return 8
    except KeyboardInterrupt:
        print('[P070B_FULL_CPU_FINAL] INTERRUPTED130; partial artifacts preserved', flush=True); return 130
    except BaseException as exc:
        if isinstance(exc, SystemExit): raise
        traceback.print_exc(); print('[P070B_FULL_CPU_FINAL] TOOL_ERROR9: ' + str(exc), flush=True); return 9


if __name__ == '__main__':
    raise SystemExit(main())
