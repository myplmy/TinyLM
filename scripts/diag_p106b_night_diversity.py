#!/usr/bin/env python3
"""Same640 updates: unique32k once versus the frozen original8k four times.

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
from scripts import p106b_night_diversity_data as data
from scripts import diag_p106b_night_foundation as foundation
from scripts import diag_p106b_night_prompt as other
from scripts import p106b_night_course as qa
from scripts import p106b_night_learning as method
from scripts import diag_p106b_night_train as previous
from scripts.p106b_shards import ShardWriter, verify
from scripts.p106b_native_windows import reader as native_reader

TAG, CORPUS, EVIDENCE = data.TAG, data.CORPUS, data.EVIDENCE
CODE = ('scripts/diag_p106b_night_diversity.py', 'scripts/test_p106b_night_diversity.py',
        'scripts/p106b_night_diversity_data.py', 'scripts/test_p106b_night_diversity_data.py', *other.CODE)


def info():
    return dict(schema='P106B_NIGHT_UNIQUE_QA_ACTUAL_V1', tag=TAG,
        code_sha256={p: qa.data.digest(ROOT / p) for p in sorted(set(CODE))},
        parent_sha256=foundation.data.PARENT_SHA, original_qa_sha256=foundation.data.LOCKED_QA_SHA,
        natural_epoch=1, logical_quarters=4, updates_planned=640, seed=1337,
        micro_bs=8, accum=16, seq=1024, grad_checkpoint=True, compile='default',
        adam_lr=5e-5, muon_lr=2e-4, weight_decay=0., clip=1., anneal=1.,
        scheduler='CONSTANT', fresh_moments=True, consistency_weight=0., prompt_loss_weight=0.,
        mtp=False, binary_aux=False, fact_aux=False, teacher_calls=0,
        comparison='same rows/updates; changed unique QA, repetition and about1pct actual input tokens',
        final_primary=True, best_selection='same DEV CE only; not TEST', protected_source=False,
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


def actual_exposure(quarters, replay, tok):
    total = Counter(); schedules = []; courses = []
    for index in range(4):
        natural, controls = data.quarter_records(quarters, index, replay, tok)
        groups = method.schedule(len(natural), len(controls), index)
        exposure = Counter(); seen = Counter(); denominators = []; content = 0
        if len(groups) != 160: raise ValueError('exact160 updates in each logical quarter required')
        for group in groups:
            words, parts = previous.denominators(group, natural, controls)
            if words <= 0: raise ValueError('nonempty whole-update supervision required')
            denominators.append(words); content += parts
            for micro in group:
                records = previous.micro_records(micro, natural, controls)
                if len(records) != 8: raise ValueError('actual micro8 required')
                seen[micro.kind] += len(micro.indices)
                for record in records: exposure.update(rows=1, x_tokens=record.x_tokens, assistant_targets=record.targets)
        if seen != dict(natural=8192, replay=4096): raise ValueError('complete quarter without duplicate rows required')
        total.update(exposure)
        schedules.append(dict(quarter=index + 1, updates=160, exposure=dict(exposure), content_targets=content,
            denominators=denominators, schedule_sha256=qa.data.sha([[asdict(m) for m in g] for g in groups])))
        courses.append((natural, controls))
    return dict(total), schedules, courses


def prepare():
    import torch
    from tokenizers import Tokenizer
    previous.deadline(training=True)
    if CORPUS.parent.exists() or EVIDENCE.exists(): raise FileExistsError('old diversity namespace preserved')
    native_identity()
    original, baseline = foundation.read_qa_source(); tok = Tokenizer.from_file(str(qa.data.TOKENIZER))
    documents = {}
    for language, splits in qa.data.SOURCES.items():
        documents[language] = {}
        for split, (relative, identity) in splits.items():
            if qa.data.digest(ROOT / relative) != identity: raise ValueError('immutable pinned source differs')
            documents[language][split] = dict(path=relative, sha256=identity,
                document=json.loads((ROOT / relative).read_text(encoding='utf-8')))
    expanded, source = qa.data.collect_documents(documents, tok, train_limit=16384, eval_limit=256,
        min_eval_contexts=128, context_question_cap=2, common_bpb_count=4000, seed=20261016)
    del documents
    quarters, proof = data.split_quarters(expanded, baseline)
    actual, schedules, courses = actual_exposure(quarters, baseline['replay'], tok)
    if actual != proof['candidate_total_sft']: raise ValueError('actual full encoder differs from metadata inventory')
    first_natural, first_controls = qa.records(baseline['train'], baseline['replay'], tok)
    if courses[0] != (first_natural, first_controls): raise ValueError('first160 actual x/y differs from fixed baseline')
    torch, model, cfg, actual_tok, initial, cp, identity = foundation.load_foundation_parent('base_qa')
    if actual_tok.to_str() != tok.to_str(): raise ValueError('actual parent tokenizer differs')
    pad, eot, _ = previous.special_ids(tok)
    from tinylm.train import mtp_sft as core
    px, py, ps = core.pad_records(courses[0][0][0] + courses[0][1][:6], pad, 'cpu', fixed_width=1024, batch_size=8)
    if list(px.shape) != [8, 1024] or pad != 0 or eot != 4: raise ValueError('same actual padding/EOT geometry required')
    if torch.cuda.is_initialized(): raise ValueError('CPU diversity initialized CUDA')
    CORPUS.mkdir(parents=True, exist_ok=False); manifests = {}
    for split in ('train', 'dev', 'test'):
        writer = ShardWriter(CORPUS, split)
        for row in expanded[split]: writer.append(row)
        manifests[split] = writer.close(lineage=info())
    result = dict(info(), status='DIVERSITY_CPU_FROZEN', manifests=manifests, source_contract=source,
        inventory=proof, actual_exposure=actual, schedules=schedules, initial_core_sha256=initial,
        actual_parent_loaded_cpu=True, cuda_initialized=False, padding=[pad, eot],
        same_replay_sha256=qa.data.sha(baseline['replay']), first160_actual_x_y_equal=True,
        checkpoints_written=0, optimizer_updates=0)
    qa.write(CORPUS / 'report.json', result); qa.write(EVIDENCE / 'cpu_contract.json', result)
    print('[DIVERSITY_CPU] ' + json.dumps(dict(status=result['status'], actual=actual, train_pairs=32768)), flush=True)
    return 0


def read_source():
    native_identity()
    report = qa.required(CORPUS / 'report.json'); _, baseline = foundation.read_qa_source()
    if (report['status'] != 'DIVERSITY_CPU_FROZEN' or report['code_sha256'] != info()['code_sha256']
            or qa.required(EVIDENCE / 'cpu_contract.json') != report
            or report['same_replay_sha256'] != qa.data.sha(baseline['replay'])):
        raise ValueError('complete same-code/source actual CPU contract required')
    for language, splits in qa.data.SOURCES.items():
        for _, (relative, identity) in splits.items():
            if qa.data.digest(ROOT / relative) != identity: raise ValueError('pinned read-only source changed')
    expanded = {split:list(stream(manifest)) for split, manifest in report['manifests'].items()}
    quarters, proof = data.split_quarters(expanded, baseline)
    from tokenizers import Tokenizer
    tok = Tokenizer.from_file(str(qa.data.TOKENIZER)); actual, schedules, courses = actual_exposure(quarters, baseline['replay'], tok)
    if proof != report['inventory'] or actual != report['actual_exposure'] or schedules != report['schedules']:
        raise ValueError('complete actual source/encoder/schedule differs from CPU freeze')
    original = qa.required(ROOT / foundation.data.QA_REPORT)
    return report, expanded, tok, courses, original


def cost_forecast(report):
    values = report.get('step_seconds', [])[1:]
    if (report.get('status') != 'DIVERSITY_COST_COMPLETE' or report.get('updates') != 8
            or report.get('code_sha256') != info()['code_sha256']
            or report.get('cpu_contract_sha256') != qa.data.digest(CORPUS / 'report.json')
            or len(values) != 7 or any(not math.isfinite(v) or v <= 0 for v in values)):
        raise ValueError('exact same-source actual successful cost8 required')
    return max(values) * 640 + 600


def save(torch, path, state, cfg, steps, quarter, core):
    with path.open('xb') as output:
        torch.save(dict(model=state, cfg=asdict(cfg), step=steps, optimizer_saved=False,
            tokenizer_sha256=qa.data.TOK_SHA, tokenizer_lineage='chat32',
            night_diversity=dict(tag=TAG, logical_quarter=quarter, natural_epoch=1,
                initializer_sha256=foundation.data.PARENT_SHA, core_sha256=core)), output)
    return dict(path=str(path.relative_to(ROOT)), sha256=qa.data.digest(path))


def run(cost, max_wall_sec):
    from tinylm.train import mtp_sft as core
    from scripts.p106b_gate_runtime import idle_before_gpu, wall_limit
    proof, expanded, tok, courses, original = read_source(); target = EVIDENCE / ('cost8' if cost else 'unique32k')
    if target.exists() or (not cost and checkpoint().exists()): raise FileExistsError('old complete/partial diversity preserved')
    if not cost:
        from scripts import diag_p106b_night_eval_recovery as evaluation
        evaluation.checkpoint_spec('base_qa')
        own = cost_forecast(qa.required(EVIDENCE / 'cost8/report.json'))
        rest = other.budget(qa.required(foundation.data.CORPUS / 'native_contract.json'))
        # Reserve both actual diversity endpoints plus the bounded Falcon reference.
        needed = own + rest['needed_seconds'] + 1800 + 2700
        remaining = (qa.TRAIN_STOP - datetime.now(timezone.utc)).total_seconds()
        print('[DIVERSITY_BUDGET] ' + json.dumps(dict(needed=needed, remaining=remaining, original=rest)), flush=True)
        if needed >= remaining: raise ValueError('all original/optional evaluation work does not fit before09:00')
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
            os.environ['TORCHINDUCTOR_CACHE_DIR'] = tempfile.mkdtemp(prefix='p106b_diversity_')
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
                    if steps <= 8 or steps % 100 == 0: print('[DIVERSITY_UPDATE] ' + json.dumps(event), flush=True)
                    if cost and steps == 8: break
                if cost: break
                entry = dict(logical_quarter=quarter + 1, updates=steps, train_ce=epoch_nll / epoch_words,
                    dev=previous.dev_loss(base, expanded['dev'], tok, pad, eot), native=foundation.runtime.native_ce(base, qa.NATIVE))
                history.append(entry)
                if entry['dev']['ce'] < best_ce:
                    best_ce = entry['dev']['ce']; best_quarter = quarter + 1
                    best_state = {k:v.detach().cpu().clone() for k,v in base.state_dict().items()}
                    best_core = foundation.runtime.state_fingerprint(base)
                print('[DIVERSITY_QUARTER] ' + json.dumps(entry), flush=True)
            if not cost and (steps != 640 or dict(rows=81920, x_tokens=x_tokens, assistant_targets=targets) != proof['actual_exposure']
                    or native_x != 5242880 or slots != 83886080 or pairs_n != 32768
                    or content_n != sum(s['content_targets'] for s in proof['schedules'])):
                raise ValueError('full actual same-update exposure differs')
            result = dict(info(), status='DIVERSITY_COST_COMPLETE' if cost else 'DIVERSITY_TRAIN_COMPLETE',
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
    print('[DIVERSITY_FINAL] ' + json.dumps(dict(status=result['status'], updates=steps, whole_seconds=result['whole_seconds'])), flush=True)
    return 0


def main():
    p = argparse.ArgumentParser(); p.add_argument('--mode', choices=('freeze', 'cost', 'train'), required=True)
    p.add_argument('--max-wall-sec', type=int, default=14400); p.add_argument('--execute', action='store_true'); a = p.parse_args()
    if not a.execute or not 60 <= a.max_wall_sec <= 14400: p.error('explicit execute and60..14400 bounded wall required')
    try: return prepare() if a.mode == 'freeze' else run(a.mode == 'cost', a.max_wall_sec)
    except KeyboardInterrupt:
        print('[DIVERSITY_INTERRUPTED] partial outputs preserved'); return 130
    except Exception as exc:
        print('[DIVERSITY_ERROR] ' + type(exc).__name__ + ': ' + str(exc)); return 9


if __name__ == '__main__': raise SystemExit(main())
