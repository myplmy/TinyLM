#!/usr/bin/env python3
"""Exact old G270Tfull bridge into the existing packed reference, never training."""
from __future__ import annotations

import argparse
from contextlib import contextmanager, nullcontext
from dataclasses import asdict
from datetime import datetime, timezone
import gc
import importlib
import json
from pathlib import Path
import statistics
import sys
import time
from unittest.mock import patch
import weakref

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts import diag_p014e_packed_deploy as prior
from scripts import diag_p106b_resource_matrix as resource

TAG = 'p014e_g270_large_vocab_v2_20261027'
SCHEMA = 'P014E_G270_EXPLICIT_LARGE_VOCAB_DEPLOY_V1'
OWN = ('scripts/diag_p014e_large_vocab_deploy.py', 'scripts/test_p014e_large_vocab_deploy.py',
       'tinylm/infer/dialogue.py')
CAPS = {'export': 900, 'baseline-cpu': 1200, 'baseline-cuda': 900,
        'deploy-cpu': 5400, 'deploy-cuda': 1800}
CP = 'runs/ckpt/m100R1c_ko-en_300M_G270Tfull.pt'
CP_SHA = '0AC6D2E1F9378C1B10382EDD7205C0E82059B9649E124BA9F333056B40B144F0'
TOK_SHA = '7D4046BF0505A327DD5A0ABBB427ECD4FC82F99C2CEAA170BC61ECDE12809B0C'
need = resource.need


def identity():
    files = dict(prior.identity()['files'])
    files.update({name: resource.digest(resource.safe(name)) for name in OWN})
    return dict(files=files, sha256=resource.sha(files))


def folder():
    return resource.safe('runs/deploy/' + TAG)


def report_path(mode):
    return resource.safe('test_result/evidence/' + TAG + '/' + mode + '/report.json')


def validate_texts(base):
    expected = [('ko128', 'ko', 128), ('en128', 'en', 128),
                ('ko512', 'ko', 512), ('en512', 'en', 512)]
    actual = [(w['id'], w['language'], w['prompt_tokens']) for w in base['workloads']]
    need(actual == expected and all(type(w['text']) is str and w['text'].strip() for w in base['workloads']),
         'exact native prompt lengths/languages/order required')
    cases = base['answer_cases']
    need([(c['id'], c['language'], c['mode']) for c in cases] ==
         [('ko_arithmetic', 'ko', 'plain'), ('en_arithmetic', 'en', 'plain'),
          ('ko_context', 'ko', 'plain'), ('en_context', 'en', 'plain')]
         and all(type(c['question']) is str and c['question'].strip() for c in cases),
         'four unique plain question identities/languages required')


def validate(profile, args):
    need(profile.get('schema') == SCHEMA and profile.get('tag') == TAG
         and profile.get('root_approved') is True and profile.get('authority_directive') == 96
         and profile.get('source_sha256') == identity()['sha256'], 'exact current authority/source required')
    need(args.max_wall_sec == CAPS[args.mode] and profile['phase_caps'] == CAPS
         and profile.get('deadline') == '2026-10-27T08:00:00+00:00'
         and (resource.DEADLINE - datetime.now(timezone.utc)).total_seconds() > args.max_wall_sec + 180,
         'whole exact phase and closure must fit current authority')
    header = resource.read_ref(profile['header'])
    need(header['path'] == CP and header['sha256'] == CP_SHA
         and header['bytes'] == 1466892217 and header['step'] == 2289
         and (header['cfg']['vocab_size'], header['cfg']['emb_rank'], header['cfg']['tie_mlp'])
         == (262144, 256, True), 'only exact historical tied large-vocab CP supported')
    need(resource.digest(resource.safe(profile['tokenizer']['path'])) == profile['tokenizer']['sha256'] == TOK_SHA,
         'exact explicitly selected local tokenizer required')
    base = resource.read_ref(profile['texts_profile'])
    validate_texts(base)
    contract = profile['cpu_contract']
    need(contract['actual_exit'] == 0 and resource.digest(resource.safe(contract['path'])) == contract['sha256'],
         'closed meaningful CPU contract required')
    need(profile.get('tile_rows') == 4096 and profile.get('head_rows') == 1024
         and profile.get('forced_max_new') == 16 and profile.get('natural_max_new') == 32
         and profile.get('timing_repetitions') == 3 and profile.get('eos_id') == 1
         and profile.get('training_updates') == 0 and profile.get('additional_300m') is False,
         'no sample/tolerance/tokenizer/default changes')
    return header, base


def checked_state(model, state):
    """Check all keys/dtypes and shared alias values BEFORE product strict load."""
    import torch
    current = model.state_dict()
    need(set(state) == set(current), 'old state keys differ from current architecture')
    for key, value in current.items():
        other = state[key]
        need(isinstance(other, torch.Tensor) and other.shape == value.shape
             and other.dtype == value.dtype and bool(torch.isfinite(other).all()),
             'nonfinite or mismatched old state: ' + key)
    aliases = {}
    for name, parameter in model.named_parameters(remove_duplicate=False):
        aliases.setdefault(id(parameter), []).append(name)
    for names in aliases.values():
        first = state[names[0]]
        for name in names[1:]:
            other = state[name]
            same = other.data_ptr() == first.data_ptr() and other.stride() == first.stride()
            need(same or torch.equal(first, other), 'conflicting old shared parameter: ' + name)


def validate_legacy_header(payload, header):
    """Compare JSON-stable cfg identity, retaining exact keys, step and CP hash."""
    need(type(payload) is dict and set(payload) == {'model', 'opt', 'step', 'cfg'}
         and type(payload['cfg']) is dict and type(header['cfg']) is dict
         and type(payload['step']) is int and type(header['step']) is int
         and payload['step'] == header['step']
         and resource.sha(payload['cfg']) == resource.sha(header['cfg']),
         'exact legacy header changed')


@contextmanager
def legacy_source(header, device, budget, proof):
    import torch
    from tinylm.config import TMTConfig
    from tinylm.model import TiedMLPTransformer
    from scripts.interactive_research_infer import state_fingerprint
    path = resource.safe(CP)
    model = payload = state = None
    core = None
    primary_error = None
    try:
        need(resource.digest(path) == CP_SHA, 'original checkpoint bytes changed')
        before = path.stat()
        proof['checkpoint_tensor_load_attempts'] = 1
        with path.open('rb') as stream:
            payload = torch.load(stream, map_location='cpu', weights_only=True)
        proof['checkpoint_tensor_loads_completed'] = 1
        after = path.stat()
        need((before.st_size, before.st_ino, before.st_mtime_ns) == (after.st_size, after.st_ino, after.st_mtime_ns),
             'original checkpoint changed while reading')
        validate_legacy_header(payload, header)
        # Only the model is consumed; optimizer state is never restored or stepped.
        state = payload['model']
        payload = None
        cfg = TMTConfig(**header['cfg'])
        prior.packed.supported_config(cfg)
        with torch.random.fork_rng(devices=[]):
            model = TiedMLPTransformer(cfg)
        checked_state(model, state)
        model.load_state_dict(state, strict=True)
        state = None
        model.eval().requires_grad_(False)
        core = state_fingerprint(model)
        model.set_anneal(1.)
        threads = torch.get_num_threads()
        try:
            torch.set_num_threads(1)
            with torch.no_grad():
                model.freeze_quant()
        finally:
            torch.set_num_threads(threads)
        # Moving Parameters alone does not move the unregistered frozen cache.
        model.to(device)
        for module in model._tlinears():
            module._wq = module._wq.to(device)
            module._anneal_t = model._anneal
        proof.update(core_sha256=core, actual_parameters=sum(p.numel() for p in model.parameters()),
                     source_quantizer='ORIGINAL_PRODUCT_TWN_ON_CPU_ONE_THREAD_THEN_MOVE',
                     filled_current_cfg=asdict(cfg), historical_tokenizer_sha='NOT_RECORDED')
        yield model, cfg
    except BaseException as exc:
        primary_error = dict(type=type(exc).__name__, message=str(exc)[:2000])
        proof['primary_error'] = primary_error
        raise
    finally:
        errors = cleanup_legacy_source(model, core, path, budget, proof)
        model = payload = state = None
        gc.collect()
        if primary_error is None and errors:
            raise RuntimeError('legacy source verification/cleanup failed: '+str(errors))


def cleanup_legacy_source(model, core, path, budget, proof):
    """Attempt every final verification/release even when an earlier one fails."""
    from scripts.interactive_research_infer import state_fingerprint
    errors = []
    def attempt(stage, action):
        try:
            action()
        except BaseException as exc:
            errors.append(dict(stage=stage, type=type(exc).__name__, message=str(exc)[:1000]))
    def verify_core():
        proof['final_core_sha256'] = state_fingerprint(model)
        proof['core_unchanged'] = proof['final_core_sha256'] == core
        need(proof['core_unchanged'], 'legacy core changed')
    def verify_grads():
        proof['gradients_absent'] = all(p.grad is None for p in model.parameters())
        need(proof['gradients_absent'], 'legacy gradient appeared')
    def verify_checkpoint():
        proof['original_checkpoint_unchanged'] = resource.digest(path) == CP_SHA
        need(proof['original_checkpoint_unchanged'], 'original checkpoint changed')
    if model is not None:
        if core is not None:
            attempt('final_core', verify_core)
        attempt('gradients', verify_grads)
        attempt('clear_quant', model.clear_quant)
        attempt('model_to_cpu', lambda: model.to('cpu'))
    attempt('checkpoint_bytes', verify_checkpoint)
    attempt('budget', budget.check)
    proof['cleanup_diagnostics'] = errors
    return errors


def generation(model, cfg, tokenizer, ids, device, count, budget, *, natural=False, observed=False):
    """Use the unchanged product sampler; explicitly Gemma EOS1, never chat EOS2."""
    import torch
    gen = importlib.import_module('tinylm.infer.generate')
    from tinylm.infer.dialogue import validate_input_ids
    from scripts.bench_infer import _CpuWatch
    validate_input_ids(ids, cfg.vocab_size)
    capture = resource.FixedCapture(tokenizer, ids)
    forward = resource.ObservedForward(model, device) if observed else resource.FP32Forward(model, device)
    timestamps, original = [], gen._pick
    def pick(*args, **kwargs):
        token = original(*args, **kwargs)
        prior.sync(device)
        timestamps.append(time.perf_counter())
        budget.check()
        return token
    watch = _CpuWatch()
    need(watch.ps is not None, 'CPU observer unavailable')
    watch.start()
    prior.sync(device)
    started = time.perf_counter()
    try:
        with torch.no_grad(), patch.object(gen, '_pick', pick if observed else original):
            _, metadata = gen.sample(forward, cfg, capture, 'FIXED_IDS', max_new=count, temperature=0.,
                top_k=1, device=device, use_cache=True, stop_at_eos=natural, eos_id=1,
                logits_last_only=True, return_metadata=True, mtp_tokens=1)
        prior.sync(device)
        ended = time.perf_counter()
    finally:
        system, own, external = watch.stop()
    need(gen._pick is original, 'sampler hook not restored')
    output = capture.decoded_ids[len(ids):]
    need(len(output) == metadata['generated_tokens'] and (natural or len(output) == count)
         and (not observed or len(timestamps) == len(output)), 'incomplete generation or observer')
    result = dict(seconds=ended-started, prompt_ids=list(ids), generated_ids=output,
        answer=tokenizer.decode(output, skip_special_tokens=False), metadata=metadata,
        cpu_load=dict(system_percent=system, process_machine_percent=own, external_percent=external),
        eos_id=1, eos_stop_enabled=natural, timing_scope='PRODUCT_SAMPLER_FP32_MATH_TOKENIZATION_EXCLUDED')
    if observed:
        result.update(timing=resource.summarize_times(timestamps, started, ended, len(output)),
            pick_times_seconds=[t-started for t in timestamps],
            returned_kv_peak_bytes=forward.kv_peak_bytes,
            prior_plus_returned_kv_peak_bytes=forward.kv_prior_and_returned_peak_bytes)
    return result


def forecast(probes):
    """Count prefill per request; do not multiply prefill cost per output token."""
    need(len(probes) == 2 and all(len(p['pick_times_seconds']) == 4 for p in probes), 'two full4-token cost probes')
    prefill = max(p['pick_times_seconds'][0] for p in probes)
    step = max(b-a for p in probes for a, b in zip(p['pick_times_seconds'], p['pick_times_seconds'][1:]))
    need(prefill > 0 and step > 0, 'positive measured prefill/decode costs required')
    # Each fixed context: numerical4, warm16, timed3x16, observed16.
    # Then4 independent natural requests up to32. Threefold margin plus60s.
    seconds = 3 * (4 * ((prefill + 3*step) + 5*(prefill + 15*step))
                   + 4 * (prefill + 31*step)) + 60
    return dict(prefill_seconds=prefill, maximum_decode_step_seconds=step,
                conservative_seconds=seconds, factor=3, closure_margin_seconds=60)


def token_inputs(base, tokenizer):
    from tinylm.infer.dialogue import validate_input_ids
    rows = []
    for work in base['workloads']:
        ids = tokenizer.encode(work['text'] * 40).ids
        need(len(ids) >= work['prompt_tokens'], 'source text too short for native prompt')
        ids = ids[:work['prompt_tokens']]
        validate_input_ids(ids, 262144)
        rows.append(dict(id=work['id'], ids=ids))
    return rows


def oracle_path(device, variant, work):
    return folder() / 'oracle' / device / variant / (work + '.pt')


def save_oracle(path, value):
    import torch
    need(not path.exists(), 'new per-context oracle required')
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        torch.save(value, stream)
    need(path.stat().st_size < 20_000_000, 'per-context oracle must stay below20MB')
    return dict(path=path.relative_to(ROOT).as_posix(), sha256=resource.digest(path), bytes=path.stat().st_size)


def suite(model, cfg, tokenizer, base, profile, device, budget, result, *, variant, expected=None):
    import torch
    forward = resource.FP32Forward(model, device)
    inputs = token_inputs(base, tokenizer)
    result.update(records=[], answers=[], numeric=[], oracles=[])
    probes = [generation(model, cfg, tokenizer, inputs[i]['ids'], device, 4, budget, observed=True) for i in (0, 2)]
    cost = forecast(probes)
    result['cost_probes'], result['cost'] = probes, cost
    remaining = min(budget.seconds-(time.monotonic()-budget.started),
                    (resource.DEADLINE-datetime.now(timezone.utc)).total_seconds()-180)
    if cost['conservative_seconds'] > remaining:
        result.update(status='BUDGET_HOLD_NOT_FULL_SUITE', remaining_seconds=remaining)
        return 8
    for work in inputs:
        budget.check()
        oracle = None
        if expected is not None:
            ref = next(x for x in expected['oracles'] if x['workload'] == work['id'])
            need(ref['path'] == oracle_path(device, variant, work['id']).relative_to(ROOT).as_posix(), 'oracle namespace differs')
            path = resource.safe(ref['path'])
            need(resource.digest(path) == ref['sha256'], 'baseline oracle changed')
            oracle = torch.load(path, weights_only=True, map_location='cpu')
            need(oracle['input'] == work, 'baseline input IDs/order changed')
        kept, chosen = [], []
        with torch.no_grad():
            logits, kv = forward(torch.tensor([work['ids']], device=device), use_cache=True, logits_last_only=True)
            for index in range(4):
                value = logits.detach().cpu().clone()
                kept.append(value)
                if oracle is not None:
                    wanted = oracle['logits'][index]
                    delta = (value-wanted).abs()
                    row = dict(workload=work['id'], step=index, max_abs=float(delta.max()),
                        mean_abs=float(delta.mean()), allclose=bool(torch.allclose(value, wanted, rtol=2e-5, atol=2e-6)),
                        exact_equal=bool(torch.equal(value, wanted)), argmax_equal=bool(torch.equal(value.argmax(-1), wanted.argmax(-1))))
                    result['numeric'].append(row)
                    need(row['allclose'] and row['argmax_equal'], 'large-vocab same-device numerical criterion failed')
                token = int(value.argmax(-1).item()) if oracle is None else oracle['teacher_ids'][index]
                chosen.append(token)
                if index < 3:
                    logits, kv = forward(torch.tensor([[token]], device=device), past_kv=kv, use_cache=True, logits_last_only=True)
        del logits, kv, value
        if oracle is None:
            saved = save_oracle(oracle_path(device, variant, work['id']), dict(input=work, teacher_ids=chosen, logits=kept))
            result['oracles'].append(dict(workload=work['id'], **saved))
        del kept, oracle
        warm = generation(model, cfg, tokenizer, work['ids'], device, 16, budget)
        times = [generation(model, cfg, tokenizer, work['ids'], device, 16, budget) for _ in range(3)]
        seen = generation(model, cfg, tokenizer, work['ids'], device, 16, budget, observed=True)
        need(all(r['generated_ids'] == warm['generated_ids'] and r['metadata'] == warm['metadata'] for r in times+[seen]),
             'observer/unobserved generation or termination differs')
        if expected is not None:
            old = next(x for x in expected['records'] if x['workload'] == work['id'])['observed']
            need(seen['generated_ids'] == old['generated_ids'] and seen['metadata'] == old['metadata'], 'packed fixed IDs/stops changed')
        result['records'].append(dict(workload=work['id'], warmup=warm, repeats=times, observed=seen,
            median_seconds=statistics.median(x['seconds'] for x in times)))
        print(json.dumps(dict(variant=variant, device=device, workload=work['id'], complete=True)), flush=True)
    for case in base['answer_cases']:
        ids = tokenizer.encode(case['question']).ids
        seen = generation(model, cfg, tokenizer, ids, device, 32, budget, natural=True, observed=True)
        if expected is not None:
            old = next(x for x in expected['answers'] if x['case'] == case)['generation']
            need(seen['generated_ids'] == old['generated_ids'] and seen['metadata'] == old['metadata'], 'packed natural IDs/stops changed')
        result['answers'].append(dict(case=case, generation=seen))
    result.update(status='FULL_TECHNICAL_SUITE_NOT_QUALITY', storage=resource.model_storage(model), rss=resource.rss())
    return 0


def completed(mode, profile):
    path = report_path(mode)
    report = json.loads(path.read_text())
    need(report['exit_code'] == 0 and report['source'] == identity()
         and report['profile_sha256'] == profile['_sha256'] and report['status'] == 'TECHNICAL_COMPLETE_NOT_QUALITY',
         'closed same-source/profile predecessor required')
    return report


def predecessors(mode):
    if mode == 'export':
        return ()
    if mode.startswith('baseline-'):
        return ('export',)
    return ('export', 'baseline-'+mode.rsplit('-', 1)[-1])


def pending_predecessors(mode, profile):
    pending = []
    for predecessor in predecessors(mode):
        path = report_path(predecessor)
        if not path.exists():
            pending.append(dict(mode=predecessor, reason='NOT_RUN'))
            continue
        row = json.loads(path.read_text())
        need(row['source'] == identity() and row['profile_sha256'] == profile['_sha256']
             and row['mode'] == predecessor, 'predecessor identity changed')
        if row['exit_code'] != 0:
            pending.append(dict(mode=predecessor, reason=row['status'], actual_exit=row['exit_code']))
        else:
            completed(predecessor, profile)
    return pending


@contextmanager
def guarded_deploy_loads(report):
    """Deployment may read only new payload/oracle tensors, never the old CP."""
    import torch
    original = torch.load
    report['torch_load_files'] = []
    def checked(file, *args, **kwargs):
        path = Path(getattr(file, 'name', file)).resolve()
        need(path.is_relative_to(folder()) and path.suffix == '.pt'
             and kwargs.get('weights_only') is True, 'only new deployment/oracle safe loads allowed')
        report['torch_load_files'].append(path.relative_to(ROOT).as_posix())
        return original(file, *args, **kwargs)
    with patch.object(torch, 'load', checked):
        yield


def perform(args, profile, header, base, budget, report):
    import torch
    from tokenizers import Tokenizer
    from tinylm.infer.dialogue import validate_vocabulary
    tokenizer = Tokenizer.from_file(str(resource.safe(profile['tokenizer']['path'])))
    report['vocabulary_contract'] = validate_vocabulary(tokenizer, header['cfg'], allow_extra_special=True)
    need(tokenizer.token_to_id('<eos>') == 1 and tokenizer.token_to_id('<bos>') == 2,
         'actual Gemma EOS/BOS mapping differs')
    device = args.mode.rsplit('-', 1)[-1] if '-' in args.mode else 'cpu'
    if args.mode == 'export':
        folder().mkdir(parents=True, exist_ok=False)
    else:
        exported = completed('export', profile)
    report.update(variants=[], source_proof={})
    if args.mode == 'export' or args.mode.startswith('baseline-'):
        with legacy_source(header, device, budget, report['source_proof']) as loaded:
            model, cfg = loaded
            ref = weakref.ref(model)
            for variant in prior.VARIANTS:
                budget.check()
                row = dict(variant=variant)
                report['variants'].append(row)
                if device == 'cuda':
                    prior.sync(device)
                    torch.cuda.reset_peak_memory_stats()
                if args.mode == 'export':
                    data = prior.packed.export_payload(model, provenance=dict(checkpoint=header,
                        tokenizer=profile['tokenizer'], source_sha256=identity()['sha256'],
                        quality_claim=False, quantizer='ORIGINAL_CPU_TWN'), tile_rows=4096,
                        embedding_format=variant, head_rows=1024)
                    path = folder()/(variant+'.pt')
                    size = prior.packed.save_new(data, path)
                    row.update(path=path.relative_to(ROOT).as_posix(), bytes=size, sha256=resource.digest(path),
                               storage=prior.packed.payload_storage(data))
                    del data
                else:
                    row['result'] = {}
                    try:
                        with prior.reference_embedding(model, variant, 1024) as conversion:
                            row['conversion'] = conversion
                            rc = suite(model, cfg, tokenizer, base, profile, device, budget, row['result'], variant=variant)
                    except BaseException as exc:
                        row['primary_error'] = dict(type=type(exc).__name__, message=str(exc)[:2000])
                        raise
                    finally:
                        if device == 'cuda':
                            try:
                                prior.sync(device)
                                row.update(cuda_peak_allocated_bytes=torch.cuda.max_memory_allocated(),
                                    cuda_peak_reserved_bytes=torch.cuda.max_memory_reserved(),
                                    cuda_peak_scope='CONVERSION_PLUS_SUITE; EXCLUDES_CP_LOAD; RESTORATION_FP32_EMBEDDING_RETAINED')
                            except BaseException as exc:
                                row['cuda_peak_error'] = dict(type=type(exc).__name__, message=str(exc)[:1000])
                                if 'primary_error' not in row:
                                    raise
                    if rc != 0:
                        report['status'] = 'BUDGET_HOLD_NOT_FULL_SUITE'
                        break
            else:
                rc = 0
        del loaded, model, cfg
        gc.collect()
        report['source_model_released'] = ref() is None
        need(report['source_model_released'], 'legacy source remains referenced')
        return rc
    baseline = completed('baseline-'+device, profile)
    for entry in exported['variants']:
        path = resource.safe(entry['path'])
        need(path == folder()/(entry['variant']+'.pt') and resource.digest(path) == entry['sha256'], 'new payload identity differs')
        row = dict(variant=entry['variant'], result={}, original_checkpoint_loads=0)
        report['variants'].append(row)
        model = ref = None
        error = None
        cleanup_errors = []
        try:
            started = time.perf_counter()
            model = prior.packed.load_file(path, device=device, tile_rows=4096)
            ref = weakref.ref(model)
            row.update(load_seconds=time.perf_counter()-started, storage_after_load=resource.model_storage(model))
            expected = next(x['result'] for x in baseline['variants'] if x['variant'] == entry['variant'])
            rc = suite(model, model.cfg, tokenizer, base, profile, device, budget, row['result'], variant=entry['variant'], expected=expected)
            if device == 'cuda':
                prior.sync(device)
                row.update(cuda_peak_allocated_bytes=torch.cuda.max_memory_allocated(), cuda_peak_reserved_bytes=torch.cuda.max_memory_reserved())
        except BaseException as exc:
            error = dict(type=type(exc).__name__, message=str(exc)[:2000])
        finally:
            if model is not None:
                try:
                    model.to('cpu')
                except BaseException as exc:
                    cleanup_errors.append(dict(stage='model_to_cpu', type=type(exc).__name__, message=str(exc)[:1000]))
                model = None
            gc.collect()
            row['model_released'] = ref() is None if ref is not None else None
            row['cleanup_errors'] = cleanup_errors
            if device == 'cuda':
                try:
                    row['cleanup'] = resource.close_cuda(torch)
                    prior.assert_cuda_clean(row['cleanup'])
                    torch.cuda.reset_peak_memory_stats()
                except BaseException as exc:
                    cleanup_errors.append(dict(stage='cuda_close', type=type(exc).__name__, message=str(exc)[:1000]))
        row['execution_error'] = error
        need(error is None and not cleanup_errors and row['model_released'], 'packed failure/cleanup: '+str(error or cleanup_errors))
        need(resource.digest(path) == entry['sha256'], 'payload changed during execution')
        if rc != 0:
            report['status'] = 'BUDGET_HOLD_NOT_FULL_SUITE'
            return rc
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=CAPS, required=True)
    parser.add_argument('--profile', required=True)
    parser.add_argument('--profile-sha256', required=True)
    parser.add_argument('--max-wall-sec', type=int, required=True)
    action = parser.add_mutually_exclusive_group()
    action.add_argument('--execute', action='store_true')
    action.add_argument('--check-only', action='store_true')
    args = parser.parse_args()
    profile = resource.read_ref(dict(path=args.profile, sha256=args.profile_sha256))
    header, base = validate(profile, args)
    if args.check_only:
        print(json.dumps(dict(status='LARGE_VOCAB_METADATA_ONLY', model_loads=0, gpu_calls=0)))
        return 0
    need(args.execute, 'explicit model execution required')
    import torch
    from scripts.interactive_research_infer import require_idle_gpu
    from scripts.diag_p102a_logit_margin import memory_point
    torch.set_num_threads(2 if args.mode.endswith('cuda') else 1)
    torch.set_num_interop_threads(1)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    profile['_sha256'] = args.profile_sha256
    output = report_path(args.mode)
    need(not output.exists(), 'new phase report required')
    source = identity()
    budget = resource.Budget(args.max_wall_sec)
    report = dict(schema=SCHEMA, tag=TAG, mode=args.mode, source=source, profile_sha256=args.profile_sha256,
        checkpoint=header, tokenizer=profile['tokenizer'], status='STARTED', quality_claim=False,
        training_updates=0, checkpoint_writes=0, original_checkpoint_loads=0,
        started_at=datetime.now(timezone.utc).isoformat())
    rc = 9
    try:
        with resource.wall(args.max_wall_sec):
            missing = pending_predecessors(args.mode, profile)
            if missing:
                report.update(status='UPSTREAM_HOLD_MODEL_NOT_RUN', missing_predecessors=missing)
                rc = 8
            else:
                for mode in predecessors(args.mode):
                    completed(mode, profile)
                report['idle_before'] = require_idle_gpu()
                report['memory_before'] = memory_point()
                need(report['memory_before']['free_mib'] >= 4096, '4GiB free admission for bounded model/cleanup required')
                if args.mode.endswith('cuda'):
                    torch.cuda.init()
                    torch.cuda.reset_peak_memory_stats()
                guard = guarded_deploy_loads(report) if args.mode.startswith('deploy-') else nullcontext()
                with guard:
                    rc = perform(args, profile, header, base, budget, report)
                if rc == 0:
                    report['status'] = 'TECHNICAL_COMPLETE_NOT_QUALITY'
            need(identity() == source, 'frozen experiment source changed')
    except BaseException as exc:
        report['execution_error'] = dict(type=type(exc).__name__, message=str(exc)[:2000])
        report['status'], rc = 'ERROR_NOT_COMPLETE', 9
    finally:
        gc.collect()
        report['original_checkpoint_loads'] = report.get('source_proof', {}).get('checkpoint_tensor_loads_completed', 0)
        if torch.cuda.is_initialized():
            try:
                report['final_cuda_cleanup'] = resource.close_cuda(torch)
                prior.assert_cuda_clean(report['final_cuda_cleanup'])
            except BaseException as exc:
                report['final_cleanup_error'] = dict(type=type(exc).__name__, message=str(exc)[:1000])
                rc = 9
        try:
            report['idle_after'] = require_idle_gpu()
        except BaseException as exc:
            report['idle_after_error'] = dict(type=type(exc).__name__, message=str(exc)[:1000])
            rc = 9
        if rc == 9 and report['status'] == 'TECHNICAL_COMPLETE_NOT_QUALITY':
            report['status'] = 'ERROR_FINAL_CLEANUP_NOT_COMPLETE'
        report.update(exit_code=rc, seconds=time.monotonic()-budget.started, ended_at=datetime.now(timezone.utc).isoformat())
        resource.write_new(output, report)
        print(json.dumps(dict(mode=args.mode, status=report['status'], actual_exit=rc, seconds=report['seconds'])))
    return rc


if __name__ == '__main__':
    raise SystemExit(main())
