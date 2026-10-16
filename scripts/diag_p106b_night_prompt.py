#!/usr/bin/env python3
"""Fixed assistant CE/native replay plus separately normalized input-body LM.

Two fresh original-P090B arms differ only by beta0/.1. Existing frozen data,
training scripts, model files and product defaults are not modified.
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
from scripts import diag_p106b_night_foundation as foundation
from scripts import p106b_night_prompt_loss as prompt
from scripts import p106b_night_learning as method
from scripts import diag_p106b_night_train as previous
from scripts import p106b_night_course as qa
from scripts.p106b_shards import ShardWriter, verify
from scripts.p106b_native_windows import reader as native_reader

TAG = 'p106b_night_prompt_v1_s1337'
CORPUS = ROOT / 'HF/sft_ready' / TAG / 'corpus'
EVIDENCE = ROOT / 'test_result/evidence' / TAG
ARMS = ('prompt0', 'prompt01')
BETAS = dict(prompt0=0., prompt01=.1)
CODE = ('scripts/diag_p106b_night_prompt.py', 'scripts/test_p106b_night_prompt.py',
        'scripts/p106b_night_prompt_loss.py', 'scripts/test_p106b_night_prompt_loss.py',
        *foundation.CODE, 'tinylm/data/sft.py', 'tinylm/chat/serialize.py')


def info():
    return dict(schema='P106B_NIGHT_PROMPT_SEPARATE_MEAN_V1', tag=TAG,
        code_sha256={path: qa.data.digest(ROOT / path) for path in sorted(set(CODE))},
        parent_sha256=foundation.data.PARENT_SHA, source_qa_sha256=foundation.data.LOCKED_QA_SHA,
        betas=BETAS, seed=1337, micro_bs=8, accum=16, seq=1024, grad_checkpoint=True,
        compile='default', epochs=4, updates_planned=640, adam_lr=5e-5, muon_lr=2e-4,
        weight_decay=0., clip=1., anneal=1., scheduler='CONSTANT', fresh_moments=True,
        mtp=False, binary_aux=False, fact_aux=False, consistency_weight=0.,
        objective='original assistant mean + native mean + beta * natural input-body mean',
        prompt_target_scope='original context/question only; no static wrappers, roles, PAD or assistant',
        source_qa_body_gradient_already_exists=True, query_conditioned_retrieval_direct_supervision=False,
        paper_replication=False, teacher_calls=0, protected_source=False,
        deadline_utc=qa.DEADLINE.isoformat(), gpu_stop_utc=qa.TRAIN_STOP.isoformat())


def namespace():
    for target in (CORPUS, EVIDENCE):
        for parent in (target, *target.parents):
            if parent.is_symlink(): raise ValueError('linked prompt namespace')
            if parent == ROOT: break


def checkpoint(arm, best=False):
    if arm not in ARMS: raise ValueError('registered prompt arm required')
    return ROOT / 'runs/ckpt' / ('m100s10_ko-en_night_' + TAG + '_' + arm + ('_best' if best else '') + '.pt')


def mask_micros(micro, masks):
    if micro.kind == 'natural':
        return [masks[index][view] for index in micro.indices for view in (0, 1)]
    if micro.kind == 'replay': return []
    raise ValueError('registered natural/replay micro required')


def prompt_denominator(group, masks):
    return sum(sum(value != -100 for value in labels)
        for micro in group for labels in mask_micros(micro, masks))


def construct_masks(rows, natural, tok):
    if len(natural) != len(rows['train']): raise ValueError('complete actual TRAIN pair list required')
    all_masks = []; proofs = []; count = 0
    for index, (pair, records) in enumerate(zip(rows['train'], natural)):
        if len(records) != 2: raise ValueError('exact two natural wrappers required')
        pair_masks = []
        for view in (0, 1):
            result = prompt.prompt_labels(pair, view, tok, record=records[view])
            labels = result['prompt_y']; n = sum(y != -100 for y in labels)
            if (result['x'] != records[view].x or result['assistant_y'] != records[view].y
                    or len(labels) != len(records[view].x) or n <= 0
                    or any(a != -100 and b != -100 for a, b in zip(labels, records[view].y))):
                raise ValueError('same actual input/assistant and disjoint nonempty prompt targets required')
            pair_masks.append(labels); count += n
            proof = dict(root=pair['root'], language=pair['language'], index=index, view=view,
                x_sha256=qa.data.sha(result['x']), assistant_y_sha256=qa.data.sha(result['assistant_y']),
                prompt_y_sha256=qa.data.sha(labels), prompt_targets=n, proof=result['proof'])
            proofs.append(proof)
        all_masks.append(pair_masks)
    if len(all_masks) != len(rows['train']) or len(proofs) != len(rows['train']) * 2:
        raise ValueError('complete natural TRAIN occurrence coverage required')
    return all_masks, proofs, count


def prepare():
    from tinylm.train import mtp_sft as core
    namespace(); previous.deadline(training=True)
    if CORPUS.parent.exists() or EVIDENCE.exists() or any(checkpoint(arm).exists() for arm in ARMS):
        raise FileExistsError('old prompt artifacts preserved')
    proof, contract, qr, rows = foundation.source_course()
    torch, base, cfg, tok, initial, cp, identity = foundation.load_foundation_parent('base_qa')
    if initial != proof['original_core_sha256']: raise ValueError('same actual original parent body required')
    natural, replay = qa.records(rows['train'], rows['replay'], tok)
    masks, mask_proofs, targets = construct_masks(rows, natural, tok)
    schedules = []; all_counts = []; update_exposure = []
    for epoch in range(4):
        groups = method.schedule(len(natural), len(replay), epoch)
        counts = [prompt_denominator(group, masks) for group in groups]
        if len(groups) != 160 or sum(counts) != targets: raise ValueError('exact once-per-pass prompt coverage')
        schedules.append(qa.data.sha([[asdict(m) for m in group] for group in groups])); all_counts.extend(counts)
        for group, prompt_count in zip(groups, counts):
            records = [record for micro in group for record in previous.micro_records(micro, natural, replay)]
            words, content = previous.denominators(group, natural, replay)
            update_exposure.append(dict(x=sum(record.x_tokens for record in records), assistant_targets=words,
                prompt_targets=prompt_count, content_targets=content, rows=len(records)))
    pad, eot, pad_name = previous.special_ids(tok)
    sample = natural[0] + replay[:6]
    x, y, seg = core.pad_records(sample, pad, 'cpu', fixed_width=1024, batch_size=8)
    for labels, record in zip(masks[0], natural[0]):
        if len(labels) != record.x_tokens or any(i >= x.shape[1] for i, value in enumerate(labels) if value != -100):
            raise ValueError('actual causal prompt predictors exceed padded width')
    if torch.cuda.is_initialized(): raise ValueError('prompt CPU preparation initialized CUDA')
    CORPUS.mkdir(parents=True, exist_ok=False)
    writer = ShardWriter(CORPUS, 'mask_proofs')
    for row in mask_proofs: writer.append(row)
    manifest = writer.close(lineage=info())
    result = dict(info(), status='ACTUAL_PROMPT_CPU_FROZEN', mask_manifest=manifest,
        mask_proofs_sha256=qa.data.sha(mask_proofs), prompt_targets_per_pass=targets,
        prompt_targets_four_pass=targets * 4, prompt_targets_per_update=all_counts,
        update_exposure=update_exposure,
        schedule_sha256=schedules, actual_qa_exposure=qr['exposure'], initial_core_sha256=initial,
        actual_pad_id=pad, actual_eot_id=eot, actual_pad_name=pad_name,
        actual_padded_shape=list(x.shape), source_foundation_cpu_sha256=qa.data.digest(foundation.data.CORPUS / 'report.json'),
        actual_parent_cpu_loaded=True, cuda_initialized=False, model_forward=False, optimizer_updates=0,
        original_assistant_masks_unchanged=True, additional_prompt_targets_are_not_new_input_tokens=True)
    qa.write(CORPUS / 'report.json', result); qa.write(EVIDENCE / 'cpu_contract.json', result)
    print('[PROMPT_CPU] ' + json.dumps(dict(status=result['status'], pairs=len(natural),
        prompt_targets_per_pass=targets, additional_four_pass_targets=targets * 4,
        x_four_pass=qr['exposure']['expected_four_pass']['x_tokens'])), flush=True)
    return 0


def read_source():
    namespace(); result = qa.required(CORPUS / 'report.json')
    if (result['status'] != 'ACTUAL_PROMPT_CPU_FROZEN' or result['code_sha256'] != info()['code_sha256']
            or result['source_foundation_cpu_sha256'] != qa.data.digest(foundation.data.CORPUS / 'report.json')):
        raise ValueError('same-code actual prompt CPU contract required')
    _, contract, qr, rows = foundation.source_course()
    from tokenizers import Tokenizer
    tok = Tokenizer.from_file(str(qa.data.TOKENIZER))
    natural, replay = qa.records(rows['train'], rows['replay'], tok)
    masks, proofs, targets = construct_masks(rows, natural, tok)
    verify(CORPUS, result['mask_manifest'])
    saved = [json.loads(line) for shard in result['mask_manifest']['shards']
             for line in (CORPUS / shard['path']).read_text(encoding='utf-8').splitlines()]
    if (saved != proofs or qa.data.sha(proofs) != result['mask_proofs_sha256']
            or targets != result['prompt_targets_per_pass'] or qa.counts(rows['train'], rows['replay'], tok) != result['actual_qa_exposure']):
        raise ValueError('actual prompt encoder or source occurrence changed')
    return result, contract, qr, rows, tok, natural, replay, masks


def cost_estimate(report, expected_code, updates):
    if (report.get('updates') != 8 or report.get('code_sha256') != expected_code
            or report.get('actual_oom') is not False or report.get('checkpoint_written') is not False
            or report.get('status') not in ('PROMPT_COST_COMPLETE', 'FOUNDATION_COST_COMPLETE')):
        raise ValueError('same-code finite successful cost8 required')
    warm = report['step_seconds'][1:]
    if len(warm) != 7 or any(type(v) not in (float, int) or not math.isfinite(v) or v <= 0 for v in warm):
        raise ValueError('seven warmed finite step times required')
    return max(warm) * updates + 900


def completion(path, expected_status, validator):
    """File presence is not completion. Invalid/partial reports fail closed."""
    if not path.exists(): return False
    report = qa.required(path)
    if report.get('status') != expected_status: raise ValueError('invalid or incomplete completion report')
    validator(report)
    return True


def completed_prompt(arm, proof):
    def validate(report):
        expected = proof['actual_qa_exposure']['expected_four_pass']
        if (report.get('arm') != arm or report.get('beta') != BETAS[arm] or report.get('updates') != 640
                or report.get('code_sha256') != info()['code_sha256']
                or report.get('cpu_contract_sha256') != qa.data.digest(CORPUS / 'report.json')
                or report.get('source_qa_sha256') != foundation.data.LOCKED_QA_SHA
                or report.get('initializer_sha256') != foundation.data.PARENT_SHA
                or report.get('initial_core_sha256') != proof['initial_core_sha256']
                or report.get('actual_x_tokens') != expected['x_tokens']
                or report.get('assistant_targets') != expected['assistant_targets']
                or report.get('prompt_targets') != proof['prompt_targets_four_pass']
                or report.get('native_x_tokens') != 5242880 or report.get('actual_oom') is not False
                or report.get('checkpoint_written') is not True
                or report.get('checkpoint') != str(checkpoint(arm).relative_to(ROOT))
                or qa.data.digest(checkpoint(arm)) != report.get('checkpoint_sha256')
                or report.get('event_manifest', {}).get('rows') != 640):
            raise ValueError('complete prompt training conditions/checkpoint/exposure required')
        verify(EVIDENCE / arm, report['event_manifest'])
    return completion(EVIDENCE / arm / 'report.json', 'PROMPT_TRAIN_COMPLETE', validate)


def budget(contract):
    from scripts import diag_p106b_night_eval_recovery as evaluation
    proof = qa.required(CORPUS / 'report.json')
    _, eval_inputs, eval_cases = evaluation.read_inputs()
    own = {}; remaining_training = {}
    for arm in ARMS:
        report = qa.required(EVIDENCE / ('cost_' + arm) / 'report.json')
        if (report['status'] != 'PROMPT_COST_COMPLETE' or report['parent_sha256'] != foundation.data.PARENT_SHA
                or report['source_qa_sha256'] != foundation.data.LOCKED_QA_SHA
                or report['cpu_contract_sha256'] != qa.data.digest(CORPUS / 'report.json')):
            raise ValueError('complete own matched prompt cost required')
        own[arm] = cost_estimate(report, info()['code_sha256'], 640)
        if not completed_prompt(arm, proof): remaining_training[arm] = own[arm]
    base_cost = qa.required(foundation.data.EVIDENCE / 'cost_base_qa/report.json')
    for arm in foundation.ARMS:
        def foundation_done(report, arm=arm):
            endpoint = 'foundation_native' if arm == 'native' else arm
            cp, identity = evaluation.checkpoint_spec(endpoint)
            if (qa.data.digest(cp) != identity or report.get('event_manifest', {}).get('rows') != report['updates']):
                raise ValueError('complete foundation checkpoint/event proof required')
            verify(foundation.data.EVIDENCE / arm, report['event_manifest'])
        if completion(foundation.data.EVIDENCE / arm / 'report.json', 'FOUNDATION_TRAIN_COMPLETE', foundation_done): continue
        cost = qa.required(foundation.data.EVIDENCE / 'cost_native/report.json') if arm == 'native' else base_cost
        if arm == 'cpt_qa' and (foundation.data.EVIDENCE / 'cost_cpt_qa/report.json').exists():
            cost = qa.required(foundation.data.EVIDENCE / 'cost_cpt_qa/report.json')
        remaining_training['foundation_' + arm] = cost_estimate(cost, foundation.info()['code_sha256'], contract['steps'] if arm == 'native' else 640)
    old_endpoints = evaluation.ENDPOINTS + evaluation.FOUNDATION_ENDPOINTS
    pending_old_eval = []
    for endpoint in old_endpoints:
        def eval_done(report, endpoint=endpoint):
            evaluation.endpoint_contract(report, endpoint, eval_inputs)
            if (report.get('code_sha256') != evaluation.info()['code_sha256']
                    or report.get('input_report_sha256') != qa.data.digest(evaluation.FROZEN / 'report.json')):
                raise ValueError('same frozen complete evaluation source required')
            for lane in evaluation.OUTPUTS:
                checked = evaluation.read_receipt(endpoint, lane, eval_cases)
                if (checked['output'] != report['outputs'][lane]
                        or qa.data.digest(evaluation.receipt_path(endpoint, lane)) != report['receipt_sha256'][lane]):
                    raise ValueError('complete raw/receipt independent evaluation proof required')
        if not completion(evaluation.EVIDENCE / (endpoint + '_report.json'), 'ACTUAL_EVALUATION_COMPLETE', eval_done):
            pending_old_eval.append(endpoint)
    # Reserve all four new evaluations even if a file exists: never credit
    # unverified presence and never cannibalize the original pipeline budget.
    pending_new_eval = [*ARMS, *(arm + '_best' for arm in ARMS)]
    evaluation_seconds = 900 * (len(pending_old_eval) + len(pending_new_eval))
    needed = sum(remaining_training.values()) + evaluation_seconds + 600
    remaining = (qa.TRAIN_STOP - datetime.now(timezone.utc)).total_seconds()
    return dict(remaining_training_estimates=remaining_training, remaining_old_eval=pending_old_eval,
        remaining_prompt_eval=pending_new_eval, evaluation_seconds=evaluation_seconds,
        needed_seconds=needed, remaining_before09_seconds=remaining, fits=needed < remaining,
        scope='forecast, not upper bound; original committed foundation pipeline kept first;09:00 stop')


def save(torch, path, state, cfg, arm, steps, epoch, core):
    with path.open('xb') as output:
        torch.save(dict(model=state, cfg=asdict(cfg), step=steps, tokenizer_sha256=qa.data.TOK_SHA,
            tokenizer_lineage='chat32', optimizer_saved=False,
            night_prompt=dict(tag=TAG, arm=arm, beta=BETAS[arm], epoch=epoch,
                parent_sha256=foundation.data.PARENT_SHA, core_sha256=core)), output)
    return dict(path=str(path.relative_to(ROOT)), sha256=qa.data.digest(path))


def run(arm, cost, max_wall_sec):
    from tinylm.train import mtp_sft as core
    from scripts.p106b_gate_runtime import idle_before_gpu, wall_limit
    proof, contract, qr, rows, tok, natural, replay, masks = read_source()
    target = EVIDENCE / (('cost_' if cost else '') + arm)
    if target.exists() or (not cost and checkpoint(arm).exists()): raise FileExistsError('old prompt trial preserved')
    if not cost:
        forecast = budget(contract); print('[PROMPT_BUDGET] ' + json.dumps(forecast), flush=True)
        if not forecast['fits']: raise ValueError('all remaining original and prompt work exceeds09:00')
    previous.deadline(training=True); idle_before_gpu(); target.mkdir(parents=True, exist_ok=False)
    qa.write(target / 'start.json', dict(info(), arm=arm, beta=BETAS[arm], cost=cost))
    events = ShardWriter(target, 'events'); began = time.perf_counter()
    try:
        with wall_limit(max_wall_sec):
            torch, base, cfg, actual_tok, initial, parent, identity = foundation.load_foundation_parent('base_qa')
            if initial != proof['initial_core_sha256'] or qa.data.digest(parent) != identity:
                raise ValueError('exact original P090B body and file required')
            pad, eot, _ = previous.special_ids(actual_tok)
            if pad != proof['actual_pad_id'] or eot != proof['actual_eot_id']: raise ValueError('actual special IDs changed')
            windows = native_reader(ROOT, qr); base = base.cuda(); torch.cuda.reset_peak_memory_stats()
            native_before = None if cost else foundation.runtime.native_ce(base, qa.NATIVE)
            dev_before = None if cost else previous.dev_loss(base, rows['dev'], tok, pad, eot)
            os.environ['TORCHINDUCTOR_CACHE_DIR'] = tempfile.mkdtemp(prefix='p106b_prompt_')
            model = torch.compile(base, mode='default'); adam, muon = foundation.runtime.optimizers(base)
            for optimizer in (adam, muon):
                for group in optimizer.param_groups: group['lr'] *= .5
            steps = sft_x = words_seen = native_x = slots = prompt_seen = pairs_seen = content_seen = 0
            times = []; history = []; grad_max = 0.; clip_events = 0
            best_ce = math.inf; best_state = None; best_epoch = None; best_core = None
            for epoch in range(4):
                epoch_word_nll = epoch_prompt_nll = 0.; epoch_words = epoch_prompts = 0
                for group in method.schedule(len(natural), len(replay), epoch):
                    previous.deadline(training=True); tick = time.perf_counter()
                    word_total, content_total = previous.denominators(group, natural, replay)
                    prompt_total = prompt_denominator(group, masks)
                    if prompt_total != proof['prompt_targets_per_update'][steps]: raise ValueError('fixed whole-update prompt denominator changed')
                    adam.zero_grad(set_to_none=True); muon.zero_grad(set_to_none=True)
                    word_n = prompt_n = 0; word_nll = torch.zeros((), device='cuda'); prompt_nll = torch.zeros((), device='cuda')
                    for micro in group:
                        records = previous.micro_records(micro, natural, replay)
                        x, y, seg = core.pad_records(records, pad, 'cuda', fixed_width=1024, batch_size=8)
                        with torch.autocast('cuda', dtype=torch.bfloat16):
                            hidden = model(x, return_hidden=True)
                            if micro.kind == 'natural':
                                values, cn, pn = method.natural_sums(base, hidden, records, eot)
                                word = values[0]; loss = word / word_total + values[1] * 0.
                                body_sum, body_n = prompt.prompt_sums(base, hidden, mask_micros(micro, masks))
                                loss = loss + prompt.prompt_update_loss(body_sum, prompt_total, BETAS[arm])
                                prompt_n += body_n; prompt_nll += body_sum.detach()
                                pairs_seen += pn; content_seen += cn
                            else:
                                sums, valid = core.components(base, hidden, y, seg, horizons=())
                                word = sums[1]; loss = word / word_total
                        if not bool(torch.isfinite(loss)): raise ValueError('nonfinite matched prompt objective')
                        loss.backward(); word_n += sum(record.targets for record in records); word_nll += word.detach()
                        sft_x += sum(record.x_tokens for record in records); slots += x.numel()
                    if word_n != word_total or prompt_n != prompt_total: raise ValueError('actual whole-update denominators differ')
                    words_seen += word_n; prompt_seen += prompt_n
                    x, y, seg = foundation.native_batch(torch, windows, list(range(steps * 8, (steps + 1) * 8)))
                    with torch.autocast('cuda', dtype=torch.bfloat16):
                        hidden = model(x, return_hidden=True); sums, valid = core.components(base, hidden, y, seg, horizons=())
                        native_loss = sums[1] / 8192
                    if valid[1] != 8192 or not bool(torch.isfinite(native_loss)): raise ValueError('actual native replay denominator/finite loss required')
                    native_loss.backward(); native_x += 8192
                    grad = torch.nn.utils.clip_grad_norm_(base.parameters(), 1.)
                    if not bool(torch.isfinite(grad)): raise ValueError('nonfinite prompt gradient')
                    grad_max = max(grad_max, float(grad)); clip_events += int(grad > 1.)
                    adam.step(); muon.step(); steps += 1
                    torch.cuda.synchronize(); seconds = time.perf_counter() - tick; times.append(seconds)
                    wsum, psum = float(word_nll), float(prompt_nll)
                    epoch_word_nll += wsum; epoch_prompt_nll += psum; epoch_words += word_n; epoch_prompts += prompt_n
                    event = dict(arm=arm, beta=BETAS[arm], updates=steps, epoch=epoch + 1,
                        x=sft_x, assistant_targets=words_seen, prompt_targets=prompt_seen, native_x=native_x,
                        assistant_ce=wsum / word_n, prompt_ce=psum / prompt_n if prompt_n else None,
                        gradient=float(grad), step_seconds=seconds)
                    events.append(event)
                    if steps <= 8 or steps % 100 == 0: print('[PROMPT_UPDATE] ' + json.dumps(event), flush=True)
                    if cost and steps == 8: break
                if cost: break
                entry = dict(epoch=epoch + 1, updates=steps, assistant_ce=epoch_word_nll / epoch_words,
                    prompt_ce=epoch_prompt_nll / epoch_prompts, native=foundation.runtime.native_ce(base, qa.NATIVE),
                    dev=previous.dev_loss(base, rows['dev'], tok, pad, eot))
                history.append(entry); print('[PROMPT_EPOCH] ' + json.dumps(dict(arm=arm, **entry)), flush=True)
                if entry['dev']['ce'] < best_ce:
                    best_ce = entry['dev']['ce']; best_epoch = epoch + 1
                    best_state = {key: value.detach().cpu().clone() for key, value in base.state_dict().items()}
                    best_core = foundation.runtime.state_fingerprint(base)
            expected = qr['exposure']['expected_four_pass']
            if cost:
                first = proof['update_exposure'][:8]
                if (steps != 8 or sft_x != sum(e['x'] for e in first)
                        or words_seen != sum(e['assistant_targets'] for e in first)
                        or prompt_seen != sum(e['prompt_targets'] for e in first)
                        or content_seen != sum(e['content_targets'] for e in first)
                        or native_x != 65536 or slots != 1048576):
                    raise ValueError('exact first8 actual input/assistant/prompt/native exposure required')
            if not cost and (steps != 640 or sft_x != expected['x_tokens'] or words_seen != expected['assistant_targets']
                    or prompt_seen != proof['prompt_targets_four_pass'] or native_x != 5242880
                    or slots != qr['exposure']['padded_sft_slots_four_pass'] or pairs_seen != 32768
                    or content_seen != 4 * qr['exposure']['natural_content_targets']):
                raise ValueError('complete pre-registered input/answer/prompt/native exposure required')
            result = dict(info(), arm=arm, beta=BETAS[arm], status='PROMPT_COST_COMPLETE' if cost else 'PROMPT_TRAIN_COMPLETE',
                updates=steps, actual_x_tokens=sft_x, assistant_targets=words_seen, prompt_targets=prompt_seen,
                native_x_tokens=native_x, padded_slots=slots, natural_pairs=pairs_seen, content_targets=content_seen,
                cpu_contract_sha256=qa.data.digest(CORPUS / 'report.json'), initial_core_sha256=initial,
                initializer=str(parent.relative_to(ROOT)), initializer_sha256=identity, native_before=native_before,
                dev_before=dev_before, history=history, step_seconds=times, grad_max=grad_max, clip_events=clip_events,
                actual_oom=False, peak_reserved_mib=torch.cuda.max_memory_reserved() / 2**20,
                peak_scope='torch allocator only, not complete WDDM peak', checkpoint_written=not cost, optimizer_saved=False)
            if not cost:
                final_core = foundation.runtime.state_fingerprint(base)
                saved = save(torch, checkpoint(arm), base.state_dict(), cfg, arm, 640, 4, final_core)
                best = saved if best_epoch == 4 else save(torch, checkpoint(arm, True), best_state, cfg, arm, best_epoch * 160, best_epoch, best_core)
                result.update(checkpoint=saved['path'], checkpoint_sha256=saved['sha256'], final_core_sha256=final_core,
                    best_dev_checkpoint=best['path'], best_dev_checkpoint_sha256=best['sha256'], best_dev_core_sha256=best_core,
                    best_dev_epoch=best_epoch, best_dev_ce=best_ce, selection='DEV CE only; final4 primary, TEST never selects')
            result['event_manifest'] = events.close(lineage=dict(tag=TAG, arm=arm, status=result['status']))
            result['whole_seconds'] = time.perf_counter() - began; qa.write(target / 'report.json', result)
            print('[PROMPT_FINAL] ' + json.dumps(dict(arm=arm, updates=steps, status=result['status'], whole_seconds=result['whole_seconds'])), flush=True)
    except BaseException as exc:
        try: qa.write(target / 'error.json', dict(status='ERROR_OR_INTERRUPTED', error=type(exc).__name__, message=str(exc)))
        except Exception: pass
        raise
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=('freeze', 'cost', 'train'), required=True)
    parser.add_argument('--arm', choices=ARMS)
    parser.add_argument('--max-wall-sec', type=int, default=14400)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--execute', action='store_true'); group.add_argument('--check-only', action='store_true')
    args = parser.parse_args()
    if args.check_only: print('[PROMPT_CHECK] ' + json.dumps(info())); return 0
    if args.mode in ('cost', 'train') and args.arm is None: parser.error('explicit arm required')
    try:
        previous.deadline(training=True)
        if args.mode == 'freeze': return prepare()
        remaining = int((qa.TRAIN_STOP - datetime.now(timezone.utc)).total_seconds())
        if remaining < 60: raise ValueError('09:00 documentation reserve')
        return run(args.arm, args.mode == 'cost', min(args.max_wall_sec, remaining))
    except KeyboardInterrupt: print('[PROMPT_INTERRUPTED] original/partial artifacts preserved'); return 130
    except Exception as exc:
        import traceback
        traceback.print_exc(); print('[PROMPT_ERROR] ' + str(exc)); return 9


if __name__ == '__main__': raise SystemExit(main())
