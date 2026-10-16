#!/usr/bin/env python3
"""Authorized overnight, paired grounded-QA CE / CE+consistency experiment.

Fresh versioned output only. Check-only never opens a model or starts CUDA.
The hard stop is this request's 2026-10-17 10:00 KST, not a standing permit.
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
from scripts import p106b_night_course as c
from scripts import p106b_night_learning as method
from scripts import diag_p101a_sft_mtp as runtime
from scripts.p106b_native_windows import reader as native_reader
from scripts.p106b_shards import ShardWriter


def checkpoint(arm):
    if arm not in c.ARMS: raise ValueError('registered arm required')
    return ROOT / 'runs/ckpt' / ('m100s10_ko-en_night_dense_chat32_' + c.TAG + '_' + arm + '.pt')


def deadline(training=False):
    limit = c.TRAIN_STOP if training else c.DEADLINE
    if datetime.now(timezone.utc) >= limit:
        raise RuntimeError('authorized overnight deadline reached')


def load_parent():
    from tinylm.infer.generate import _strip
    if c.data.digest(c.PARENT) != c.PARENT_SHA: raise ValueError('locked E970 changed')
    torch, base, cfg, tok, _ = runtime.load_runtime('parent_ntp')
    saved = torch.load(c.PARENT, map_location='cpu', weights_only=True)
    if (saved.get('tokenizer_sha256') != c.data.TOK_SHA
            or saved.get('evidence_recovery_curriculum') !=
            dict(tag='p106b_evidence_recovery_v1_s1337', arm='evidence_recovery', epoch=4)):
        raise ValueError('exact E970 final4/tokenizer lineage required')
    expected = asdict(cfg)
    for key in ('dim', 'emb_rank', 'n_heads', 'n_kv_heads', 'vocab_size', 'context_length'):
        if key in expected and saved['cfg'].get(key) != expected[key]:
            raise ValueError('E970 geometry differs: ' + key)
    base.load_state_dict(_strip(saved['model']), strict=True)
    del saved
    cfg.grad_checkpoint = True; cfg.mtp_aux = False; base.set_anneal(1.)
    return torch, base, cfg, tok, runtime.state_fingerprint(base)


def micro_records(micro, natural, replay):
    if micro.kind == 'natural':
        return [rec for i in micro.indices for rec in natural[i]]
    if micro.kind == 'replay': return [replay[i] for i in micro.indices]
    raise ValueError('unknown scheduled lane')


def denominators(group, natural, replay):
    words = sum(rec.targets for micro in group for rec in micro_records(micro, natural, replay))
    content = sum(natural[i][0].targets - 1 for micro in group if micro.kind == 'natural'
                  for i in micro.indices)
    return words, content


def actual_wire():
    import torch
    target = c.EVIDENCE / 'actual_cpu_wire.json'
    if target.exists(): raise FileExistsError('old CPU wire preserved')
    r, rows = c.read_night_course(); torch, base, cfg, tok, initial = load_parent()
    natural, replay = c.records(rows['train'], rows['replay'], tok)
    observation = c.counts(rows['train'], rows['replay'], tok)
    if observation != r['exposure']: raise ValueError('actual consumers differ from frozen contract')
    schedules = []
    for epoch in range(4):
        groups = method.schedule(len(natural), len(replay), epoch)
        seen = Counter(); exposure = Counter(); content = 0
        for group in groups:
            words, parts = denominators(group, natural, replay)
            if words <= 0: raise ValueError('zero supervised update')
            content += parts
            for micro in group:
                records = micro_records(micro, natural, replay)
                if len(records) != 8: raise ValueError('full eight-row micro required')
                seen[micro.kind] += len(micro.indices)
                for rec in records: exposure.update(rows=1, x_tokens=rec.x_tokens, assistant_targets=rec.targets)
        if dict(exposure) != r['exposure']['per_pass'] or seen != {'natural': 8192, 'replay': 4096}:
            raise ValueError('actual schedule duplicate/omission')
        if content != r['exposure']['natural_content_targets']: raise ValueError('KL denominator differs')
        schedules.append(dict(epoch=epoch + 1, updates=len(groups), exposure=dict(exposure),
            content_targets=content, schedule_sha256=c.data.sha([[asdict(m) for m in g] for g in groups])))
    if torch.cuda.is_initialized(): raise ValueError('CPU wire initialized CUDA')
    result = dict(schema=c.SCHEMA, status='ACTUAL_CPU_WIRE_VERIFIED', code_sha256=c.info()['code_sha256'],
        corpus_sha256=c.data.digest(c.CORPUS / 'report.json'), parent_sha256=c.PARENT_SHA,
        initial_core_sha256=initial, schedules=schedules, exposure=observation,
        pad=tok.token_to_id('<|pad|>'), eot=tok.token_to_id('<|im_end|>'),
        cuda_initialized=False, model_forward=False, optimizer_updates=0,
        checkpoint_written=False, model_loaded_cpu=True)
    c.write(target, result)
    print('[NIGHT_CPU_WIRE] ' + json.dumps(result, ensure_ascii=False), flush=True)
    return 0


def budget():
    estimates = {}
    for arm in c.ARMS:
        cost = c.required(c.EVIDENCE / ('cost_' + arm) / 'report.json')
        if (cost['status'] != 'COST_COMPLETE' or cost['updates'] != 8
                or cost['code_sha256'] != c.info()['code_sha256']
                or cost['corpus_sha256'] != c.data.digest(c.CORPUS / 'report.json')):
            raise ValueError('same-code/corpus successful cost8 required')
        warm = cost['step_seconds'][1:]
        if len(warm) != 7 or any(not math.isfinite(v) or v <= 0 for v in warm):
            raise ValueError('seven finite warmed steps required')
        estimates[arm] = max(warm) * 640 + 900
    completed = [arm for arm in c.ARMS if (c.EVIDENCE / arm / 'report.json').is_file()]
    needed = sum(v for arm, v in estimates.items() if arm not in completed) + 3600
    remaining = (c.TRAIN_STOP - datetime.now(timezone.utc)).total_seconds()
    return dict(estimates_sec=estimates, completed=completed, needed_sec=needed,
                remaining_before_closure_sec=remaining, fits=needed < remaining,
                note='forecast includes one-hour evaluation and fifteen-minute/arm setup; not upper bound')


def dev_loss(base, pairs, tok, pad, eot):
    import torch
    from tinylm.train import mtp_sft as core
    total = torch.zeros(4, device='cuda'); words = content = first = 0
    base.eval(); base.freeze_quant()
    try:
        with torch.no_grad():
            for start in range(0, len(pairs), 4):
                selected = pairs[start:start + 4]
                records = [core.encode_record(pair['views'][str(v)], tok) for pair in selected for v in (0, 1)]
                x, y, seg = core.pad_records(records, pad, 'cuda', fixed_width=1024, batch_size=len(records))
                with torch.autocast('cuda', dtype=torch.bfloat16):
                    hidden = base(x, return_hidden=True)
                    values, cn, fn = method.natural_sums(base, hidden, records, eot, False)
                total += values; words += sum(rec.targets for rec in records); content += cn; first += fn
    finally:
        base.clear_quant(); base.train()
    v = total.cpu().tolist()
    return dict(ce=v[0] / words, kl=v[1] / content, kl_first=v[2] / first,
        kl_remaining=v[3] / max(1, content - first), words=words, content=content, pairs=first,
        scope='teacher-forced DEV two wrappers; not free generation')


def run(arm, cost=False, max_wall_sec=7200):
    import torch
    from tinylm.train import mtp_sft as core
    from scripts.p106b_gate_runtime import idle_before_gpu, wall_limit
    r, rows = c.read_night_course(); proof = c.required(c.EVIDENCE / 'actual_cpu_wire.json')
    if (proof['code_sha256'] != c.info()['code_sha256'] or proof['status'] != 'ACTUAL_CPU_WIRE_VERIFIED'
            or proof['corpus_sha256'] != c.data.digest(c.CORPUS / 'report.json')):
        raise ValueError('same code/corpus CPU wire required')
    target = c.EVIDENCE / (('cost_' if cost else '') + arm)
    if target.exists() or (not cost and checkpoint(arm).exists()):
        raise FileExistsError('previous output/checkpoint preserved')
    if not cost:
        b = budget(); print('[NIGHT_BUDGET] ' + json.dumps(b), flush=True)
        if not b['fits']: raise ValueError('two full arms/evaluation do not fit before09:00KST')
    deadline(training=True); idle_before_gpu()
    target.mkdir(parents=True, exist_ok=False)
    events = ShardWriter(target, 'events')
    c.write(target / 'start.json', dict(mode='cost' if cost else 'train', arm=arm,
        weight=c.WEIGHTS[arm], code_sha256=c.info()['code_sha256'],
        started_at=datetime.now(timezone.utc).isoformat(), authority_end=c.DEADLINE.isoformat()))
    began = time.perf_counter()
    try:
        with wall_limit(max_wall_sec):
            torch, base, cfg, tok, initial = load_parent()
            if initial != proof['initial_core_sha256']: raise ValueError('initial body differs from CPU wire')
            natural, replay = c.records(rows['train'], rows['replay'], tok)
            native = native_reader(ROOT, r)
            pad = tok.token_to_id('<|pad|>'); eot = tok.token_to_id('<|im_end|>')
            if pad is None or eot is None: raise ValueError('chat32 pad/EOT required')
            base = base.cuda(); torch.cuda.reset_peak_memory_stats()
            before = None if cost else runtime.native_ce(base, c.NATIVE)
            before_dev = None if cost else dev_loss(base, rows['dev'], tok, pad, eot)
            os.environ['TORCHINDUCTOR_CACHE_DIR'] = tempfile.mkdtemp(prefix='p106b_night_')
            model = torch.compile(base, mode='default')
            adam, muon = runtime.optimizers(base)
            for opt in (adam, muon):
                for group in opt.param_groups: group['lr'] *= .5
            steps = sft_x = targets = native_x = slots = pairs_seen = content_seen = 0
            times = []; history = []; grad_max = 0.; clip_events = 0
            for epoch in range(4):
                epoch_values = torch.zeros(4, device='cuda'); epoch_words = epoch_content = epoch_pairs = 0
                for group in method.schedule(len(natural), len(replay), epoch):
                    deadline(training=True); tick = time.perf_counter()
                    words, content = denominators(group, natural, replay)
                    adam.zero_grad(set_to_none=True); muon.zero_grad(set_to_none=True)
                    stats = torch.zeros(4, device='cuda'); word_count = content_count = pair_count = 0
                    for micro in group:
                        records = micro_records(micro, natural, replay)
                        x, y, seg = core.pad_records(records, pad, 'cuda', fixed_width=1024, batch_size=8)
                        with torch.autocast('cuda', dtype=torch.bfloat16):
                            hidden = model(x, return_hidden=True)
                            if micro.kind == 'natural':
                                values, cn, pn = method.natural_sums(base, hidden, records, eot)
                                word, kl = values[0], values[1]
                                stats += values.detach(); content_count += cn; pair_count += pn
                            else:
                                sums, valid = core.components(base, hidden, y, seg, horizons=())
                                word = sums[1]; kl = word * 0.
                                stats[0] += word.detach()
                            loss = method.update_loss(word, words, kl, content, c.WEIGHTS[arm])
                        if not bool(torch.isfinite(loss)): raise ValueError('nonfinite scoped loss')
                        loss.backward()
                        sft_x += sum(rec.x_tokens for rec in records)
                        n = sum(rec.targets for rec in records); targets += n; word_count += n
                        slots += x.numel()
                    if words != word_count or content != content_count:
                        raise ValueError('whole-update actual denominator mismatch')
                    native_records = [core.Record(v[:-1].astype('int64').tolist(), v[1:].astype('int64').tolist(), [1] * 1024)
                                      for v in native[steps * 8:(steps + 1) * 8]]
                    if len(native_records) != 8: raise ValueError('native supply exhausted')
                    x, y, seg = core.pad_records(native_records, pad, 'cuda', fixed_width=1024, batch_size=8)
                    with torch.autocast('cuda', dtype=torch.bfloat16):
                        hidden = model(x, return_hidden=True)
                        sums, valid = core.components(base, hidden, y, seg, horizons=())
                        native_loss = sums[1] / 8192
                    if not bool(torch.isfinite(native_loss)): raise ValueError('nonfinite native loss')
                    native_loss.backward(); native_x += 8192
                    grad = torch.nn.utils.clip_grad_norm_(base.parameters(), 1.)
                    if not bool(torch.isfinite(grad)): raise ValueError('nonfinite gradient')
                    grad_max = max(grad_max, float(grad)); clip_events += int(grad > 1.)
                    adam.step(); muon.step(); steps += 1
                    pairs_seen += pair_count; content_seen += content_count
                    epoch_words += words; epoch_content += content; epoch_pairs += pair_count
                    epoch_values += stats
                    torch.cuda.synchronize(); elapsed = time.perf_counter() - tick; times.append(elapsed)
                    sv = stats.cpu().tolist()
                    event = dict(update=steps, epoch=epoch + 1, word_ce=sv[0] / words,
                        kl=sv[1] / max(1, content), kl_first=sv[2] / max(1, pair_count),
                        native_ce=float(native_loss.detach()), gradient_norm=float(grad),
                        word_targets=words, content_targets=content, sft_x=sft_x,
                        native_x=native_x, step_seconds=elapsed)
                    events.append(event)
                    if steps <= 8 or steps % 20 == 0:
                        print('[NIGHT_UPDATE] ' + json.dumps(dict(arm=arm, **event)), flush=True)
                    if cost and steps == 8: break
                if cost: break
                ev = epoch_values.cpu().tolist()
                entry = dict(epoch=epoch + 1, updates=steps,
                    train_ce=ev[0] / epoch_words, train_kl=ev[1] / epoch_content,
                    train_kl_first=ev[2] / epoch_pairs,
                    dev=dev_loss(base, rows['dev'], tok, pad, eot), native=runtime.native_ce(base, c.NATIVE))
                history.append(entry)
                print('[NIGHT_EPOCH] ' + json.dumps(dict(arm=arm, **entry)), flush=True)
            if not cost:
                expected = r['exposure']['expected_four_pass']
                if (steps != 640 or sft_x != expected['x_tokens'] or targets != expected['assistant_targets']
                        or native_x != r['exposure']['native_targets_four_pass']
                        or slots != r['exposure']['padded_sft_slots_four_pass']
                        or pairs_seen != 4 * 8192 or content_seen != 4 * r['exposure']['natural_content_targets']):
                    raise ValueError('exact final planned exposures differ')
            result = dict(c.info(), arm=arm, weight=c.WEIGHTS[arm],
                status='COST_COMPLETE' if cost else 'TRAIN_COMPLETE_EVALUATION_PENDING',
                initial_core_sha256=initial, corpus_sha256=c.data.digest(c.CORPUS / 'report.json'),
                updates=steps, sft_x_tokens=sft_x, assistant_targets=targets, native_x_tokens=native_x,
                padded_sft_slots=slots, natural_pairs_exposed=pairs_seen, content_targets=content_seen,
                step_seconds=times, whole_seconds=time.perf_counter() - began,
                peak_allocated_mib=torch.cuda.max_memory_allocated() / 2**20,
                peak_reserved_mib=torch.cuda.max_memory_reserved() / 2**20,
                device_peak_scope='torch process allocator, not complete WDDM/global peak',
                actual_oom=False, grad_max=grad_max, clip_events=clip_events,
                native_before=before, dev_before=before_dev, history=history,
                optimizer_saved=False, checkpoint_written=not cost)
            if not cost:
                cp = checkpoint(arm)
                with cp.open('xb') as stream:
                    torch.save(dict(model=base.state_dict(), cfg=asdict(cfg), step=steps,
                        tokenizer_sha256=c.data.TOK_SHA, tokenizer_lineage='chat32',
                        night_course=dict(tag=c.TAG, arm=arm, epoch=4, consistency=c.WEIGHTS[arm]),
                        optimizer_saved=False), stream)
                result.update(checkpoint=str(cp.relative_to(ROOT)), checkpoint_sha256=c.data.digest(cp))
            manifest = events.close(lineage=dict(status=result['status'], tag=c.TAG, arm=arm))
            result['event_manifest'] = manifest
            c.write(target / 'report.json', result)
    except BaseException as exc:
        error = dict(status='ERROR_OR_INTERRUPTED', arm=arm, exception=type(exc).__name__,
            message=str(exc), timestamp=datetime.now(timezone.utc).isoformat(),
            original_sources_preserved=True, checkpoint_policy='never overwrite')
        try: c.write(target / 'error.json', error)
        except Exception: pass
        raise
    print('[NIGHT_FINAL] ' + json.dumps(dict(arm=arm, status=result['status'], updates=steps,
        whole_seconds=result['whole_seconds'], peak_reserved_mib=result['peak_reserved_mib'])), flush=True)
    return 0


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mode', choices=('freeze', 'wire', 'cost', 'train'), required=True)
    p.add_argument('--arm', choices=c.ARMS)
    p.add_argument('--max-wall-sec', type=int, default=14400)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument('--execute', action='store_true'); g.add_argument('--check-only', action='store_true')
    a = p.parse_args()
    if not 60 <= a.max_wall_sec <= 21600: p.error('bounded60..21600 wall seconds required')
    if a.check_only:
        print('[NIGHT_CHECK_ONLY] ' + json.dumps(c.info(), ensure_ascii=False)); return 0
    if a.mode in ('cost', 'train') and a.arm is None: p.error('explicit arm required')
    try:
        deadline(training=True)
        a.max_wall_sec = min(a.max_wall_sec, int((c.TRAIN_STOP - datetime.now(timezone.utc)).total_seconds()))
        if a.max_wall_sec < 60: raise RuntimeError('closure margin reached')
        if a.mode == 'freeze': return c.freeze()
        if a.mode == 'wire': return actual_wire()
        return run(a.arm, cost=a.mode == 'cost', max_wall_sec=a.max_wall_sec)
    except KeyboardInterrupt:
        print('[NIGHT_INTERRUPTED] preserved original sources and partial output', flush=True); return 130
    except Exception as exc:
        import traceback
        traceback.print_exc(); print('[NIGHT_ERROR] ' + str(exc), flush=True); return 9


if __name__ == '__main__': raise SystemExit(main())
