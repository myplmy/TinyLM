#!/usr/bin/env python3
"""Same32k/640 updates: training views0/3 versus the frozen views0/1.

Only local pinned source/data and a fresh original P090B copy. No product,
baseline code, old dataset, checkpoint or test answer is modified.
"""
from __future__ import annotations
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import argparse
from collections import Counter
from dataclasses import asdict
from datetime import datetime, timezone
import json
import math
import os
import tempfile
import time
from scripts import p106b_night_order_data as data
from scripts import diag_p106b_night_diversity as diversity
from scripts import diag_p106b_night_foundation as foundation
from scripts import diag_p106b_night_prompt as other
from scripts import p106b_night_course as qa
from scripts import p106b_night_learning as method
from scripts import diag_p106b_night_train as previous
from scripts.p106b_shards import ShardWriter, verify
from scripts.p106b_native_windows import reader as native_reader

TAG, CORPUS, EVIDENCE = data.TAG, data.CORPUS, data.EVIDENCE
CODE = ('scripts/diag_p106b_night_order.py', 'scripts/test_p106b_night_order.py',
        'scripts/p106b_night_order_data.py', 'scripts/test_p106b_night_order_data.py', *diversity.CODE, *other.CODE)


def info():
    return dict(schema='P106B_NIGHT_FIELD_ORDER_ACTUAL_V1', tag=TAG,
        code_sha256={p: qa.data.digest(ROOT / p) for p in sorted(set(CODE))},
        parent_sha256=foundation.data.PARENT_SHA, original_qa_sha256=foundation.data.LOCKED_QA_SHA,
        natural_epoch=1, logical_quarters=4, updates_planned=640, seed=1337,
        micro_bs=8, accum=16, seq=1024, grad_checkpoint=True, compile='default',
        adam_lr=5e-5, muon_lr=2e-4, weight_decay=0., clip=1., anneal=1.,
        scheduler='CONSTANT', fresh_moments=True, consistency_weight=0., prompt_loss_weight=0.,
        mtp=False, binary_aux=False, fact_aux=False, teacher_calls=0,
        comparison='same unique32k/rows/updates; only second TRAIN input field order changes',
        training_views=[0, 3], held_wrapper2_training=False,
        upstream_cpu_sha256=qa.data.digest(diversity.CORPUS / 'report.json'),
        final_primary=True, best_selection='same DEV CE only; not TEST', protected_source=False, formal_train_ready=False,
        gpu_stop_utc=qa.TRAIN_STOP.isoformat(), authority_end_utc=qa.DEADLINE.isoformat())


def checkpoint(best=False):
    return ROOT / 'runs/ckpt' / ('m100s10_ko-en_night_' + TAG + ('_best' if best else '') + '.pt')


def stream(manifest):
    verify(CORPUS, manifest)
    for shard in manifest['shards']:
        for line in (CORPUS / shard['path']).read_text(encoding='utf-8').splitlines(): yield json.loads(line)


def native_identity():
    for relative, identity in ((foundation.data.NATIVE_TRAIN, foundation.data.TRAIN_SHA),
                               (foundation.data.NATIVE_VAL, foundation.data.VAL_SHA)):
        if qa.data.digest(ROOT / relative) != identity: raise ValueError('same original read-only native assets required')


def construct():
    upstream, expanded, tok, old_courses, original = diversity.read_source()
    by_language = {lang:[p for p in expanded['train'] if p['language'] == lang] for lang in ('ko', 'en')}
    quarters = [by_language['ko'][q * 4096:(q + 1) * 4096] + by_language['en'][q * 4096:(q + 1) * 4096] for q in range(4)]
    for q, rows in enumerate(quarters):
        if qa.data.sha([p['root'] for p in rows]) != upstream['inventory']['quarters'][q]['ordered_roots_sha256']:
            raise ValueError('same fixed unique32k quarters required')
    courses, record_proofs, actual, schedules = data.transform(quarters, old_courses, tok)
    if (actual['rows'] != 81920 or actual['assistant_targets'] != upstream['actual_exposure']['assistant_targets']
            or any(v['updates'] != 160 for v in schedules) or len(record_proofs) != 32768):
        raise ValueError('same rows/targets/640 and complete32k field-order proofs required')
    return upstream, expanded, tok, courses, original, record_proofs, actual, schedules


def prepare():
    import torch
    from tinylm.train import mtp_sft as core
    previous.deadline(training=True)
    if CORPUS.parent.exists() or EVIDENCE.exists(): raise FileExistsError('old order namespace preserved')
    upstream, expanded, tok, courses, original, record_proofs, actual, schedules = construct()
    torch, model, cfg, actual_tok, initial, cp, identity = foundation.load_foundation_parent('base_qa')
    if initial != upstream['initial_core_sha256'] or actual_tok.to_str() != tok.to_str():
        raise ValueError('same original P090B body/tokenizer required')
    pad, eot, _ = previous.special_ids(tok)
    x, y, seg = core.pad_records(courses[0][0][0] + courses[0][1][:6], pad, 'cpu', fixed_width=1024, batch_size=8)
    if list(x.shape) != [8, 1024] or pad != 0 or eot != 4: raise ValueError('same actual padding/EOT required')
    if torch.cuda.is_initialized(): raise ValueError('CPU order preparation initialized CUDA')
    CORPUS.mkdir(parents=True, exist_ok=False); writer = ShardWriter(CORPUS, 'record_proofs')
    for value in record_proofs: writer.append(value)
    manifest = writer.close(lineage=info())
    result = dict(info(), status='ORDER_CPU_FROZEN', actual_exposure=actual, schedules=schedules,
        record_proof_manifest=manifest, initial_core_sha256=initial, actual_parent_cpu_loaded=True,
        cuda_initialized=False, all_char_multisets_equal=True, all_answer_target_ids_equal=True,
        upstream_exposure=upstream['actual_exposure'], natural_pairs=32768, checkpoints_written=0, optimizer_updates=0)
    qa.write(CORPUS / 'report.json', result); qa.write(EVIDENCE / 'cpu_contract.json', result)
    print('[ORDER_CPU] ' + json.dumps(dict(status=result['status'], exposure=actual, upstream=upstream['actual_exposure'])), flush=True)
    return 0


def read_source():
    proof = qa.required(CORPUS / 'report.json')
    if (proof['status'] != 'ORDER_CPU_FROZEN' or proof['code_sha256'] != info()['code_sha256']
            or proof['upstream_cpu_sha256'] != qa.data.digest(diversity.CORPUS / 'report.json')
            or qa.required(EVIDENCE / 'cpu_contract.json') != proof):
        raise ValueError('same actual CPU/source/code order contract required')
    upstream, expanded, tok, courses, original, record_proofs, actual, schedules = construct()
    verify(CORPUS, proof['record_proof_manifest'])
    stored = []
    for shard in proof['record_proof_manifest']['shards']:
        stored.extend(json.loads(line) for line in (CORPUS / shard['path']).read_text(encoding='utf-8').splitlines())
    if stored != record_proofs or actual != proof['actual_exposure'] or schedules != proof['schedules']:
        raise ValueError('actual same source/field order/ids/labels/schedule differs')
    return proof, expanded, tok, courses, original


def finished_original_work():
    from scripts import diag_p106b_night_eval_recovery as base_eval
    from scripts import diag_p106b_night_prompt_eval as prompt_eval
    from scripts import diag_p106b_night_diversity_eval as unique_eval
    for provider, filename in ((base_eval, 'foundation_readback.json'), (prompt_eval, 'paired_readback.json'), (unique_eval, 'paired_readback.json')):
        audit = qa.required(provider.EVIDENCE / filename)
        if audit['status'] != 'RAW_RECOUNTED' or audit['errors'] or audit['code_sha256'] != provider.info()['code_sha256']:
            raise ValueError('complete source-bound original readbacks required before extra order training')
        expected = set(base_eval.FOUNDATION_ENDPOINTS) if provider is base_eval else set(provider.ENDPOINTS)
        if provider is unique_eval: expected.update(('base_qa', 'base_qa_best'))
        if set(audit.get('endpoints_sha256', {})) != expected:
            raise ValueError('complete nonempty fixed original endpoint set required')
        values = provider.read_inputs()
        inputs, cases = values[-2:]
        for endpoint, identity in audit['endpoints_sha256'].items():
            chosen = base_eval if endpoint in base_eval.FOUNDATION_ENDPOINTS else provider
            path = chosen.EVIDENCE / (endpoint + '_report.json')
            if qa.data.digest(path) != identity: raise ValueError('recounted original endpoint changed')
            report = qa.required(path); chosen.endpoint_contract(report, endpoint, inputs)
            if (report['code_sha256'] != chosen.info()['code_sha256']
                    or report['input_report_sha256'] != qa.data.digest(chosen.FROZEN / 'report.json')):
                raise ValueError('same code/input of complete original endpoint required')
            for lane in chosen.evaluation.OUTPUTS if chosen is not base_eval else base_eval.OUTPUTS:
                receipt = chosen.read_receipt(endpoint, lane, cases) if chosen is base_eval else chosen.read_receipt(endpoint, lane, cases, inputs)
                if (receipt['output'] != report['outputs'][lane]
                        or qa.data.digest(chosen.receipt_path(endpoint, lane)) != report['receipt_sha256'][lane]):
                    raise ValueError('complete original raw/receipt changed')


def cost_forecast(report):
    values = report.get('step_seconds', [])[1:]
    if (report.get('status') != 'ORDER_COST_COMPLETE' or report.get('updates') != 8
            or report.get('code_sha256') != info()['code_sha256']
            or report.get('cpu_contract_sha256') != qa.data.digest(CORPUS / 'report.json')
            or len(values) != 7 or any(not math.isfinite(v) or v <= 0 for v in values)):
        raise ValueError('exact same-source actual successful cost8 required')
    return max(values) * 640 + 600


def completed(proof):
    def validate(report):
        expected = proof['actual_exposure']
        if (report.get('code_sha256') != info()['code_sha256'] or report.get('updates') != 640
                or report.get('cpu_contract_sha256') != qa.data.digest(CORPUS / 'report.json')
                or report.get('initial_core_sha256') != proof['initial_core_sha256']
                or report.get('initializer_sha256') != foundation.data.PARENT_SHA
                or report.get('actual_x_tokens') != expected['x_tokens']
                or report.get('assistant_targets') != expected['assistant_targets']
                or report.get('native_x_tokens') != 5242880 or report.get('padded_slots') != 83886080
                or report.get('pairs_seen') != 32768 or report.get('natural_epoch') != 1
                or report.get('logical_quarters') != 4 or report.get('actual_oom') is not False
                or report.get('training_views') != [0, 3] or report.get('held_wrapper2_training') is not False
                or report.get('checkpoint_written') is not True
                or report.get('checkpoint') != str(checkpoint().relative_to(ROOT))
                or qa.data.digest(checkpoint()) != report.get('checkpoint_sha256')
                or report.get('event_manifest', {}).get('rows') != 640):
            raise ValueError('complete same-source order640 exposure/body/checkpoint proof required')
        verify(EVIDENCE / 'question_first', report['event_manifest'])
    return other.completion(EVIDENCE / 'question_first/report.json', 'ORDER_TRAIN_COMPLETE', validate)


def save(torch, path, state, cfg, steps, quarter, core):
    with path.open('xb') as output:
        torch.save(dict(model=state, cfg=asdict(cfg), step=steps, optimizer_saved=False,
            tokenizer_sha256=qa.data.TOK_SHA, tokenizer_lineage='chat32',
            night_order=dict(tag=TAG, logical_quarter=quarter, natural_epoch=1,
                initializer_sha256=foundation.data.PARENT_SHA, core_sha256=core)), output)
    return dict(path=str(path.relative_to(ROOT)), sha256=qa.data.digest(path))


def run(cost, max_wall_sec):
    from tinylm.train import mtp_sft as core
    from scripts.p106b_gate_runtime import idle_before_gpu, wall_limit
    proof, expanded, tok, courses, original = read_source(); target = EVIDENCE / ('cost8' if cost else 'question_first')
    if target.exists() or (not cost and checkpoint().exists()): raise FileExistsError('old complete/partial diversity preserved')
    if not cost:
        upstream = qa.required(diversity.CORPUS / 'report.json')
        if not diversity.completed(upstream): raise ValueError('complete actual unique32k baseline640 required')
        finished_original_work()
        own = cost_forecast(qa.required(EVIDENCE / 'cost8/report.json'))
        # All original studies must already be source/raw-recount complete.
        # Reserve90min for both new endpoints, bounded Falcon and final audit.
        needed = own + 5400
        remaining = (qa.TRAIN_STOP - datetime.now(timezone.utc)).total_seconds()
        print('[ORDER_BUDGET] ' + json.dumps(dict(needed=needed, remaining=remaining, reserve_seconds=5400)), flush=True)
        if needed >= remaining: raise ValueError('extra order study and remaining reference/evaluation do not fit09:00')
    previous.deadline(training=True); idle_before_gpu(); target.mkdir(parents=True, exist_ok=False)
    began = time.perf_counter(); events = ShardWriter(target, 'events')
    qa.write(target / 'start.json', dict(info(), cost=cost, cpu_contract_sha256=qa.data.digest(CORPUS / 'report.json')))
    try:
        with wall_limit(min(max_wall_sec, int((qa.TRAIN_STOP - datetime.now(timezone.utc)).total_seconds()))):
            torch, base, cfg, actual_tok, initial, cp, identity = foundation.load_foundation_parent('base_qa')
            if initial != proof['initial_core_sha256'] or actual_tok.to_str() != tok.to_str(): raise ValueError('same original body/tokenizer required')
            pad, eot, _ = previous.special_ids(tok); windows = native_reader(ROOT, original)
            base = base.cuda(); torch.cuda.reset_peak_memory_stats()
            before = None if cost else foundation.runtime.native_ce(base, qa.NATIVE)
            dev_before = None if cost else previous.dev_loss(base, expanded['dev'], tok, pad, eot)
            os.environ['TORCHINDUCTOR_CACHE_DIR'] = tempfile.mkdtemp(prefix='p106b_order_')
            model = torch.compile(base, mode='default'); adam, muon = foundation.runtime.optimizers(base)
            for optimizer in (adam, muon):
                for group in optimizer.param_groups: group['lr'] *= .5
            steps = x_tokens = targets = native_x = slots = content_n = pairs_n = 0
            times = []; history = []; gmax = 0.; clips = 0; best_ce = math.inf; best_state = best_core = best_quarter = None
            for quarter, (natural, replay) in enumerate(courses):
                epoch_nll = 0.; epoch_words = 0
                for group in method.schedule(len(natural), len(replay), quarter):
                    previous.deadline(training=True); tick = time.perf_counter()
                    adam.zero_grad(set_to_none=True); muon.zero_grad(set_to_none=True)
                    denom = previous.denominators(group, natural, replay)[0]; nword = 0; step_nll = torch.zeros((), device='cuda')
                    for micro in group:
                        records = previous.micro_records(micro, natural, replay)
                        x, y, seg = core.pad_records(records, pad, 'cuda', fixed_width=1024, batch_size=8)
                        with torch.autocast('cuda', dtype=torch.bfloat16):
                            hidden = model(x, return_hidden=True)
                            if micro.kind == 'natural':
                                values, cn, pn = method.natural_sums(base, hidden, records, eot)
                                loss = values[0] / denom + values[1] * 0.; nll = values[0]
                                n = sum(r.targets for r in records); content_n += cn; pairs_n += pn
                            else:
                                sums, valid = core.components(base, hidden, y, seg, horizons=())
                                n, nll = valid[1], sums[1]; loss = nll / denom
                        if not bool(torch.isfinite(loss)): raise ValueError('nonfinite diversity assistant loss')
                        loss.backward(); nword += n; step_nll += nll.detach()
                        slots += x.numel(); x_tokens += sum(r.x_tokens for r in records)
                    if nword != denom: raise ValueError('actual complete-update denominator differs')
                    x, y, seg = foundation.native_batch(torch, windows, list(range(steps * 8, (steps + 1) * 8)))
                    with torch.autocast('cuda', dtype=torch.bfloat16):
                        hidden = model(x, return_hidden=True); sums, _ = core.components(base, hidden, y, seg, horizons=()); loss_native = sums[1] / 8192
                    if not bool(torch.isfinite(loss_native)): raise ValueError('nonfinite native replay')
                    loss_native.backward(); native_x += 8192
                    grad = torch.nn.utils.clip_grad_norm_(base.parameters(), 1.)
                    if not bool(torch.isfinite(grad)): raise ValueError('nonfinite diversity gradient')
                    gmax = max(gmax, float(grad)); clips += int(grad > 1.)
                    adam.step(); muon.step(); steps += 1; targets += nword
                    torch.cuda.synchronize(); times.append(time.perf_counter() - tick)
                    epoch_words += nword; epoch_nll += float(step_nll)
                    event = dict(updates=steps, logical_quarter=quarter + 1, natural_epoch=1,
                        x=x_tokens, assistant_targets=targets, native_x=native_x,
                        ce=float(step_nll) / nword, grad=float(grad), step_seconds=times[-1])
                    events.append(event)
                    if steps <= 8 or steps % 100 == 0: print('[ORDER_UPDATE] ' + json.dumps(event), flush=True)
                    if cost and steps == 8: break
                if cost: break
                entry = dict(logical_quarter=quarter + 1, updates=steps, train_ce=epoch_nll / epoch_words,
                    dev=previous.dev_loss(base, expanded['dev'], tok, pad, eot), native=foundation.runtime.native_ce(base, qa.NATIVE))
                history.append(entry)
                if entry['dev']['ce'] < best_ce:
                    best_ce = entry['dev']['ce']; best_quarter = quarter + 1
                    best_state = {k:v.detach().cpu().clone() for k,v in base.state_dict().items()}
                    best_core = foundation.runtime.state_fingerprint(base)
                print('[ORDER_QUARTER] ' + json.dumps(entry), flush=True)
            if not cost and (steps != 640 or dict(rows=81920, x_tokens=x_tokens, assistant_targets=targets) != proof['actual_exposure']
                    or native_x != 5242880 or slots != 83886080 or pairs_n != 32768
                    or content_n != sum(s['content_targets'] for s in proof['schedules'])):
                raise ValueError('full actual same-update exposure differs')
            result = dict(info(), status='ORDER_COST_COMPLETE' if cost else 'ORDER_TRAIN_COMPLETE',
                updates=steps, actual_x_tokens=x_tokens, assistant_targets=targets, native_x_tokens=native_x,
                padded_slots=slots, pairs_seen=pairs_n, content_targets=content_n, step_seconds=times,
                initial_core_sha256=initial, initializer_sha256=identity,
                cpu_contract_sha256=qa.data.digest(CORPUS / 'report.json'), native_before=before,
                dev_before=dev_before, history=history, grad_max=gmax, clip_events=clips, actual_oom=False,
                peak_allocated_mib=torch.cuda.max_memory_allocated() / 2**20,
                peak_reserved_mib=torch.cuda.max_memory_reserved() / 2**20,
                peak_scope='torch allocator only, not global WDDM peak', checkpoint_written=not cost)
            if not cost:
                final_core = foundation.runtime.state_fingerprint(base)
                saved = save(torch, checkpoint(), base.state_dict(), cfg, steps, 4, final_core)
                best = saved if best_quarter == 4 else save(torch, checkpoint(True), best_state, cfg, best_quarter * 160, best_quarter, best_core)
                result.update(checkpoint=saved['path'], checkpoint_sha256=saved['sha256'], final_core_sha256=final_core,
                    best_dev_checkpoint=best['path'], best_dev_checkpoint_sha256=best['sha256'],
                    best_dev_core_sha256=best_core, best_dev_quarter=best_quarter, best_dev_ce=best_ce)
            result['event_manifest'] = events.close(lineage=info()); result['whole_seconds'] = time.perf_counter() - began
            qa.write(target / 'report.json', result)
    except BaseException as exc:
        try: qa.write(target / 'error.json', dict(status='ERROR_OR_INTERRUPTED', message=str(exc), exception=type(exc).__name__))
        except Exception: pass
        raise
    print('[ORDER_FINAL] ' + json.dumps(dict(status=result['status'], updates=steps, whole_seconds=result['whole_seconds'])), flush=True)
    return 0


def main():
    p = argparse.ArgumentParser(); p.add_argument('--mode', choices=('freeze', 'cost', 'train'), required=True)
    p.add_argument('--max-wall-sec', type=int, default=14400); p.add_argument('--execute', action='store_true'); a = p.parse_args()
    if not a.execute or not 60 <= a.max_wall_sec <= 14400: p.error('explicit execute and60..14400 bounded wall required')
    try: return prepare() if a.mode == 'freeze' else run(a.mode == 'cost', a.max_wall_sec)
    except KeyboardInterrupt:
        print('[ORDER_INTERRUPTED] partial outputs preserved'); return 130
    except Exception as exc:
        print('[ORDER_ERROR] ' + type(exc).__name__ + ': ' + str(exc)); return 9


if __name__ == '__main__': raise SystemExit(main())
