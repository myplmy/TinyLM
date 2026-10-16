#!/usr/bin/env python3
"""Same original P090B: direct QA versus native continuation then identical QA.

Independent namespace, actual offset/parent/encoder CPU verification, cost gates
and a hard one-time overnight deadline. Original models/caches are read-only.
"""
from __future__ import annotations
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import json
import math
import os
import tempfile
import time
from scripts import p106b_night_foundation_data as data
from scripts import p106b_night_course as qa
from scripts import p106b_night_learning as method
from scripts import diag_p106b_night_train as previous
from scripts import diag_p101a_sft_mtp as runtime
from scripts.p106b_native_windows import reader as native_reader
from scripts.p106b_shards import ShardWriter

ARMS = ('base_qa', 'native', 'cpt_qa')
CODE = ('scripts/diag_p106b_night_foundation.py', 'scripts/test_p106b_night_foundation.py',
        'scripts/p106b_night_foundation_data.py', 'scripts/test_p106b_night_foundation_data.py',
        *qa.CODE)


def info():
    return dict(schema='P106B_NIGHT_FOUNDATION_RUNTIME_V1', tag=data.TAG,
        code_sha256={p: qa.data.digest(ROOT / p) for p in sorted(set(CODE))},
        parent_sha256=data.PARENT_SHA, qa_source_sha256=data.LOCKED_QA_SHA,
        arms=list(ARMS), micro_bs=8, accum=16, seq=1024, grad_checkpoint=True,
        compile='default', seed=1337, mtp=False, binary_aux=False, fact_aux=False,
        cpt_lr=1e-4, cpt_muon_lr=4e-4, qa_lr=5e-5, qa_muon_lr=2e-4,
        fresh_optimizer_each_phase=True, weight_decay=0., clip=1., quant_anneal=1.,
        schedule='constant', qa_updates=640, qa_epochs=4, consistency_weight=0.,
        checkpoint_policy='native final; QA final4 and separate minimum DEV CE representative, weight-only',
        teacher_calls=0, protected_data=False, formal_train_ready=False,
        deadline_utc=qa.DEADLINE.isoformat(), training_stop_utc=qa.TRAIN_STOP.isoformat())


def checkpoint(arm, best=False):
    if arm not in ARMS or (best and arm == 'native'): raise ValueError('registered independent arm required')
    return ROOT / 'runs/ckpt' / ('m100s10_ko-en_night_' + data.TAG + '_' + arm + ('_best' if best else '') + '.pt')


def load_foundation_parent(arm):
    from tinylm.infer.generate import _strip
    torch, model, cfg, tok, initial = runtime.load_runtime('parent_ntp')
    cp, identity = data.PARENT, data.PARENT_SHA
    if arm == 'cpt_qa':
        r = qa.required(data.EVIDENCE / 'native/report.json')
        if (r['status'] != 'FOUNDATION_TRAIN_COMPLETE' or r['arm'] != 'native'
                or r['code_sha256'] != info()['code_sha256']):
            raise ValueError('complete same-code native continuation required')
        cp, identity = ROOT / r['checkpoint'], r['checkpoint_sha256']
        if qa.data.digest(cp) != identity: raise ValueError('new CPT checkpoint identity changed')
        saved = torch.load(cp, map_location='cpu', weights_only=True)
        if (saved['foundation']['tag'] != data.TAG or saved['foundation']['arm'] != 'native'
                or saved['tokenizer_sha256'] != qa.data.TOK_SHA):
            raise ValueError('explicit native lineage/tokenizer required')
        model.load_state_dict(_strip(saved['model']), strict=True); del saved
        initial = runtime.state_fingerprint(model)
        if initial != r['final_core_sha256']: raise ValueError('CPT body differs from strict fresh loader')
    if qa.data.digest(data.PARENT) != data.PARENT_SHA:
        raise ValueError('original immutable P090B changed')
    model.set_anneal(1.); cfg.grad_checkpoint = True; cfg.mtp_aux = False
    return torch, model, cfg, tok, initial, cp, identity


def read_qa_source():
    """Reuse frozen DATA without requiring the unrelated E970 weight file."""
    path = ROOT / data.QA_REPORT
    if qa.data.digest(path) != data.LOCKED_QA_SHA:
        raise ValueError('locked V2 QA source report differs')
    report = qa.required(path)
    if report['status'] != 'FROZEN' or report['code_sha256'] != qa.info()['code_sha256']:
        raise ValueError('same frozen data/encoder CODE required')
    if qa.data.digest(qa.data.TOKENIZER) != qa.data.TOK_SHA:
        raise ValueError('same actual tokenizer required')
    return report, {name: list(qa.stream(manifest)) for name, manifest in report['manifests'].items()}


def source_course():
    r = qa.required(data.CORPUS / 'report.json')
    contract = qa.required(data.CORPUS / 'native_contract.json')
    data.validate_contract(contract)
    if (r['status'] != 'FOUNDATION_CPU_VERIFIED' or r['code_sha256'] != info()['code_sha256']
            or r['native_contract_sha256'] != qa.data.digest(data.CORPUS / 'native_contract.json')
            or qa.data.digest(ROOT / data.QA_REPORT) != data.LOCKED_QA_SHA):
        raise ValueError('same-code actual CPU/source contract required')
    for path, identity in ((data.PARENT, data.PARENT_SHA), (ROOT / data.NATIVE_TRAIN, data.TRAIN_SHA),
                           (ROOT / data.NATIVE_VAL, data.VAL_SHA), (qa.data.TOKENIZER, qa.data.TOK_SHA)):
        if qa.data.digest(path) != identity: raise ValueError('read-only foundation asset changed')
    if ((ROOT / data.NATIVE_TRAIN).stat().st_size // 2 != data.NATIVE_TRAIN_TOKENS
            or (ROOT / data.NATIVE_VAL).stat().st_size // 2 != data.NATIVE_VAL_TOKENS):
        raise ValueError('actual native cache length differs')
    qr, rows = read_qa_source()
    return r, contract, qr, rows


def prepare():
    import numpy as np
    import torch
    if data.CORPUS.parent.exists() or data.EVIDENCE.exists(): raise FileExistsError('old foundation namespace preserved')
    previous.deadline(training=True)
    if qa.data.digest(ROOT / data.QA_REPORT) != data.LOCKED_QA_SHA:
        raise ValueError('same frozen QA corpus required')
    qr, rows = read_qa_source()
    for path, identity in ((ROOT / data.NATIVE_TRAIN, data.TRAIN_SHA), (ROOT / data.NATIVE_VAL, data.VAL_SHA)):
        if qa.data.digest(path) != identity: raise ValueError('native source hash differs')
    tokens = np.memmap(ROOT / data.NATIVE_TRAIN, dtype=np.uint16, mode='r')
    if len(tokens) != data.NATIVE_TRAIN_TOKENS: raise ValueError('actual TRAIN length mismatch')
    contract = data.make_contract(len(tokens), data.TRAIN_SHA, data.VAL_SHA)
    torch, model, cfg, tok, initial, cp, identity = load_foundation_parent('base_qa')
    pad, eot, pad_name = previous.special_ids(tok)
    actual = qa.counts(rows['train'], rows['replay'], tok)
    if actual != qr['exposure']: raise ValueError('same actual QA inputs/targets required')
    natural, replay = qa.records(rows['train'], rows['replay'], tok)
    from tinylm.train import mtp_sft as core
    px, py, ps = core.pad_records(natural[0] + replay[:6], pad, 'cpu', fixed_width=1024, batch_size=8)
    windows = native_reader(ROOT, contract)
    for value in windows[:8]:
        if len(value) != 1025 or int(value.min()) < 0 or int(value.max()) >= cfg.vocab_size:
            raise ValueError('actual native CPU window/token vocabulary differs')
    maximum = int(tokens.max())
    if maximum >= cfg.vocab_size: raise ValueError('native full TRAIN contains out-of-vocabulary ID')
    if torch.cuda.is_initialized(): raise ValueError('CPU foundation wire initialized CUDA')
    data.CORPUS.mkdir(parents=True, exist_ok=False)
    qa.write(data.CORPUS / 'native_contract.json', contract)
    result = dict(info(), status='FOUNDATION_CPU_VERIFIED', original_core_sha256=initial,
        original_checkpoint_sha256=identity, actual_qa_exposure=actual, actual_parent_cpu_loaded=True,
        actual_pad_id=pad, actual_eot_id=eot, actual_pad_name=pad_name, actual_padded_shape=list(px.shape),
        actual_native_max_id=maximum, actual_native_train_tokens=len(tokens),
        native_contract_sha256=qa.data.digest(data.CORPUS / 'native_contract.json'),
        native_contract_summary={k: v for k, v in contract.items() if k != 'native_train_offsets'},
        cuda_initialized=False, model_forward=False, updates=0, checkpoints_written=0)
    qa.write(data.CORPUS / 'report.json', result); qa.write(data.EVIDENCE / 'actual_cpu_contract.json', result)
    print('[FOUNDATION_CPU] ' + json.dumps(dict(status=result['status'], steps=contract['steps'],
        actual_draw=contract['actual_draw_tokens'], pool_ratio=contract['pool_ratio'], pad=pad, native_max=maximum)), flush=True)
    return 0


def budget(arm, contract):
    estimates = {}
    for name in ('base_qa', 'native'):
        cost = qa.required(data.EVIDENCE / ('cost_' + name) / 'report.json')
        if (cost['status'] != 'FOUNDATION_COST_COMPLETE' or cost['updates'] != 8
                or cost['code_sha256'] != info()['code_sha256']
                or cost['source_qa_sha256'] != data.LOCKED_QA_SHA
                or cost['contract_sha256'] != qa.data.digest(data.CORPUS / 'native_contract.json')):
            raise ValueError('same-code successful foundation cost8 required')
        warm = cost['step_seconds'][1:]
        if len(warm) != 7 or any(not math.isfinite(v) or v <= 0 for v in warm):
            raise ValueError('seven finite warmed steps required')
        estimates[name] = max(warm) * (contract['steps'] if name == 'native' else 640) + 900
    estimates['cpt_qa'] = estimates['base_qa']
    own_cost = data.EVIDENCE / 'cost_cpt_qa/report.json'
    if own_cost.exists():
        extra = qa.required(own_cost)
        if (extra['status'] != 'FOUNDATION_COST_COMPLETE' or extra['updates'] != 8
                or extra['code_sha256'] != info()['code_sha256']
                or extra['source_qa_sha256'] != data.LOCKED_QA_SHA
                or extra['contract_sha256'] != qa.data.digest(data.CORPUS / 'native_contract.json')):
            raise ValueError('CPT QA successful cost8 required')
        estimates['cpt_qa'] = max(extra['step_seconds'][1:]) * 640 + 900
    complete = [name for name in ARMS if (data.EVIDENCE / name / 'report.json').is_file()]
    # Existing CE/consistency evaluation and four additional endpoint evaluations.
    needed = sum(value for name, value in estimates.items() if name not in complete) + 7200
    remaining = (qa.TRAIN_STOP - datetime.now(timezone.utc)).total_seconds()
    return dict(arm=arm, estimated_seconds=estimates, completed=complete,
        needed_seconds=needed, remaining_before09_seconds=remaining, fits=needed < remaining,
        scope='conservative forecast with two-hour evaluation, setup; no deadline extension')


def native_batch(torch, windows, indices):
    import numpy as np
    values = np.stack([windows[i] for i in indices]).astype('int64', copy=False)
    if values.shape != (8, 1025): raise ValueError('exact native micro8 x complete1025 required')
    ids = torch.tensor(values, dtype=torch.long, device='cuda')
    x, y = ids[:, :-1], ids[:, 1:]
    return x, y, torch.ones_like(y)


def save_model(torch, path, state, cfg, arm, steps, epoch, parent_sha, core_sha):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        torch.save(dict(model=state, cfg=asdict(cfg), step=steps,
            tokenizer_sha256=qa.data.TOK_SHA, tokenizer_lineage='chat32', optimizer_saved=False,
            foundation=dict(tag=data.TAG, arm=arm, epoch=epoch, parent_sha256=parent_sha,
                            core_sha256=core_sha)), stream)
    return dict(path=str(path.relative_to(ROOT)), sha256=qa.data.digest(path))


def run(arm, cost, max_wall_sec):
    from tinylm.train import mtp_sft as core
    from scripts.p106b_gate_runtime import idle_before_gpu, wall_limit
    proof, contract, qr, rows = source_course()
    target = data.EVIDENCE / (('cost_' if cost else '') + arm)
    if target.exists() or (not cost and checkpoint(arm).exists()): raise FileExistsError('existing trial preserved')
    if not cost:
        b = budget(arm, contract); print('[FOUNDATION_BUDGET] ' + json.dumps(b), flush=True)
        if not b['fits']: raise ValueError('all planned comparison/evaluation does not fit before09:00')
        own = qa.required(data.EVIDENCE / ('cost_' + arm) / 'report.json')
        if (own['status'] != 'FOUNDATION_COST_COMPLETE' or own['updates'] != 8
                or own['code_sha256'] != info()['code_sha256']
                or own['source_qa_sha256'] != data.LOCKED_QA_SHA
                or own['contract_sha256'] != proof['native_contract_sha256']):
            raise ValueError('own actual cost8 prerequisite missing')
    previous.deadline(training=True); idle_before_gpu()
    target.mkdir(parents=True, exist_ok=False); began = time.perf_counter()
    events = ShardWriter(target, 'events')
    qa.write(target / 'start.json', dict(info(), arm=arm, cost=cost, timestamp=datetime.now(timezone.utc).isoformat()))
    try:
        with wall_limit(max_wall_sec):
            torch, base, cfg, tok, initial, parent, identity = load_foundation_parent(arm)
            if arm != 'cpt_qa' and initial != proof['original_core_sha256']:
                raise ValueError('same original body differs from CPU proof')
            pad, eot, _ = previous.special_ids(tok)
            natural, replay = qa.records(rows['train'], rows['replay'], tok)
            windows = native_reader(ROOT, contract if arm == 'native' else qr)
            base = base.cuda(); torch.cuda.reset_peak_memory_stats()
            before = None if cost else runtime.native_ce(base, qa.NATIVE)
            dev_before = None if cost or arm == 'native' else previous.dev_loss(base, rows['dev'], tok, pad, eot)
            os.environ['TORCHINDUCTOR_CACHE_DIR'] = tempfile.mkdtemp(prefix='p106b_foundation_')
            model = torch.compile(base, mode='default'); adam, muon = runtime.optimizers(base)
            if arm != 'native':
                for optimizer in (adam, muon):
                    for group in optimizer.param_groups: group['lr'] *= .5
            steps = total_x = targets = native_x = slots = content_count = pairs_seen = 0
            times = []; history = []; grad_max = 0.; clip_events = 0
            best_ce = math.inf; best_state = None; best_epoch = None; best_core = None
            epochs = 1 if arm == 'native' else 4
            for epoch in range(epochs):
                groups = data.native_groups(contract) if arm == 'native' else method.schedule(len(natural), len(replay), epoch)
                epoch_words = 0; epoch_nll = 0.
                for group in groups:
                    previous.deadline(training=True); tick = time.perf_counter()
                    adam.zero_grad(set_to_none=True); muon.zero_grad(set_to_none=True)
                    word_total = contract['micro_bs'] * contract['accum'] * contract['seq'] if arm == 'native' else previous.denominators(group, natural, replay)[0]
                    word_n = 0; step_nll = torch.zeros((), device='cuda')
                    for micro in group:
                        if arm == 'native':
                            x, y, seg = native_batch(torch, windows, micro); records = None
                        else:
                            records = previous.micro_records(micro, natural, replay)
                            x, y, seg = core.pad_records(records, pad, 'cuda', fixed_width=1024, batch_size=8)
                        with torch.autocast('cuda', dtype=torch.bfloat16):
                            hidden = model(x, return_hidden=True)
                            if arm != 'native' and micro.kind == 'natural':
                                values, cn, pn = method.natural_sums(base, hidden, records, eot)
                                loss = values[0] / word_total + values[1] * 0.
                                n = sum(rec.targets for rec in records); nll = values[0]
                                content_count += cn; pairs_seen += pn
                            else:
                                sums, valid = core.components(base, hidden, y, seg, horizons=())
                                n = valid[1]; nll = sums[1]; loss = nll / word_total
                        if not bool(torch.isfinite(loss)): raise ValueError('nonfinite full-target or assistant loss')
                        loss.backward(); word_n += n; step_nll += nll.detach(); slots += x.numel()
                        if records is None: total_x += 8192
                        else: total_x += sum(rec.x_tokens for rec in records)
                    if word_n != word_total: raise ValueError('actual full-update denominator differs')
                    targets += word_n
                    if arm != 'native':
                        x, y, seg = native_batch(torch, windows, list(range(steps * 8, (steps + 1) * 8)))
                        with torch.autocast('cuda', dtype=torch.bfloat16):
                            hidden = model(x, return_hidden=True)
                            sums, valid = core.components(base, hidden, y, seg, horizons=())
                            native_loss = sums[1] / 8192
                        if not bool(torch.isfinite(native_loss)): raise ValueError('nonfinite replay-native loss')
                        native_loss.backward(); native_x += 8192
                    gradient = torch.nn.utils.clip_grad_norm_(base.parameters(), 1.)
                    if not bool(torch.isfinite(gradient)): raise ValueError('nonfinite foundation gradient')
                    grad_max = max(grad_max, float(gradient)); clip_events += int(gradient > 1.)
                    adam.step(); muon.step(); steps += 1
                    torch.cuda.synchronize(); seconds = time.perf_counter() - tick; times.append(seconds)
                    epoch_words += word_n; epoch_nll += float(step_nll)
                    event = dict(arm=arm, updates=steps, epoch=epoch + 1, x=total_x, targets=targets,
                        native_replay_x=native_x, ce=float(step_nll) / word_n, grad=float(gradient), step_seconds=seconds)
                    events.append(event)
                    if steps <= 8 or steps % 100 == 0:
                        print('[FOUNDATION_UPDATE] ' + json.dumps(event), flush=True)
                    if cost and steps == 8: break
                    if arm == 'native' and steps % 500 == 0:
                        nv = runtime.native_ce(base, qa.NATIVE)
                        history.append(dict(updates=steps, native=nv))
                        print('[FOUNDATION_NATIVE_PROBE] ' + json.dumps(history[-1]), flush=True)
                if cost: break
                entry = dict(epoch=epoch + 1, updates=steps, train_ce=epoch_nll / epoch_words,
                    native=runtime.native_ce(base, qa.NATIVE))
                if arm != 'native':
                    entry['dev'] = previous.dev_loss(base, rows['dev'], tok, pad, eot)
                    if entry['dev']['ce'] < best_ce:
                        best_ce = entry['dev']['ce']; best_epoch = epoch + 1
                        best_state = {k: v.detach().cpu().clone() for k, v in base.state_dict().items()}
                        best_core = runtime.state_fingerprint(base)
                history.append(entry); print('[FOUNDATION_EPOCH] ' + json.dumps(dict(arm=arm, **entry)), flush=True)
            planned = contract['steps'] if arm == 'native' else 640
            if not cost:
                if steps != planned: raise ValueError('full pre-registered steps incomplete')
                if arm == 'native':
                    if total_x != contract['actual_draw_tokens'] or targets != total_x or native_x:
                        raise ValueError('CPT actual native processed target count differs')
                elif (total_x != qr['exposure']['expected_four_pass']['x_tokens']
                        or targets != qr['exposure']['expected_four_pass']['assistant_targets']
                        or native_x != 5242880 or slots != qr['exposure']['padded_sft_slots_four_pass']
                        or pairs_seen != 32768 or content_count != 4 * qr['exposure']['natural_content_targets']):
                    raise ValueError('QA final actual matched exposure differs')
            result = dict(info(), arm=arm, status='FOUNDATION_COST_COMPLETE' if cost else 'FOUNDATION_TRAIN_COMPLETE',
                updates=steps, actual_x_tokens=total_x, actual_targets=targets, native_replay_x=native_x,
                padded_slots=slots, natural_pairs=pairs_seen, content_targets=content_count,
                initial_core_sha256=initial, initializer=str(parent.relative_to(ROOT)), initializer_sha256=identity,
                contract_sha256=proof['native_contract_sha256'], source_qa_sha256=data.LOCKED_QA_SHA,
                native_before=before, dev_before=dev_before, history=history, step_seconds=times,
                seconds_before_checkpoint_write=time.perf_counter() - began, grad_max=grad_max, clip_events=clip_events,
                actual_oom=False, peak_allocated_mib=torch.cuda.max_memory_allocated() / 2**20,
                peak_reserved_mib=torch.cuda.max_memory_reserved() / 2**20,
                peak_scope='torch allocator only, not global WDDM peak', checkpoint_written=not cost,
                optimizer_saved=False, original_assets_preserved=True)
            if not cost:
                final_core = runtime.state_fingerprint(base)
                saved = save_model(torch, checkpoint(arm), base.state_dict(), cfg, arm, steps, epochs, identity, final_core)
                result.update(checkpoint=saved['path'], checkpoint_sha256=saved['sha256'], final_core_sha256=final_core)
                if arm != 'native':
                    if best_epoch == 4: best = saved
                    else: best = save_model(torch, checkpoint(arm, True), best_state, cfg, arm,
                        best_epoch * 160, best_epoch, identity, best_core)
                    result.update(best_dev_checkpoint=best['path'], best_dev_checkpoint_sha256=best['sha256'],
                        best_dev_epoch=best_epoch, best_dev_ce=best_ce, selection='DEV loss only, not TEST; final4 remains primary')
            result['event_manifest'] = events.close(lineage=dict(tag=data.TAG, arm=arm, status=result['status']))
            result['whole_seconds'] = time.perf_counter() - began
            qa.write(target / 'report.json', result)
    except BaseException as exc:
        try: qa.write(target / 'error.json', dict(status='ERROR_OR_INTERRUPTED', arm=arm, error=type(exc).__name__, message=str(exc)))
        except Exception: pass
        raise
    print('[FOUNDATION_FINAL] ' + json.dumps(dict(arm=arm, status=result['status'], updates=steps,
        whole_seconds=result['whole_seconds'], peak_reserved_mib=result['peak_reserved_mib'])), flush=True)
    return 0


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mode', choices=('freeze', 'cost', 'train'), required=True)
    p.add_argument('--arm', choices=ARMS)
    p.add_argument('--max-wall-sec', type=int, default=14400)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument('--execute', action='store_true'); g.add_argument('--check-only', action='store_true')
    a = p.parse_args()
    if a.check_only: print('[FOUNDATION_CHECK] ' + json.dumps(info())); return 0
    if a.mode != 'freeze' and a.arm is None: p.error('explicit independent arm required')
    try:
        previous.deadline(training=True)
        remaining = int((qa.TRAIN_STOP - datetime.now(timezone.utc)).total_seconds())
        wall = min(a.max_wall_sec, remaining)
        if wall < 60 or not 60 <= a.max_wall_sec <= 21600: raise ValueError('bounded wall and final hour required')
        return prepare() if a.mode == 'freeze' else run(a.arm, a.mode == 'cost', wall)
    except KeyboardInterrupt:
        print('[FOUNDATION_INTERRUPTED] original assets and partial records preserved'); return 130
    except Exception as exc:
        import traceback
        traceback.print_exc(); print('[FOUNDATION_ERROR] ' + str(exc)); return 9


if __name__ == '__main__': raise SystemExit(main())
