#!/usr/bin/env python3
"""Frozen last-prompt value, realized local response and global-edit comparison."""
import argparse
from datetime import datetime, timezone
import gc
import json
from pathlib import Path
import subprocess
import time
import traceback
from types import FunctionType
import torch
from scripts import diag_p108_query_covariance as source
from scripts import diag_p108_query_value as query
from scripts import diag_p108_key_transport as old_transport
from scripts import p108_key_transport as geometry
from scripts import p108_wsp_attention as wsp
from scripts import p108_weight_space as metrics
from scripts import interactive_research_infer as manual
from scripts import diag_p108_weight_space as common
from scripts.p106b_shards import ShardWriter, verify as verify_shards
from scripts.diag_p107_hybrid_mntp import close_owned_cuda

ROOT = Path(__file__).resolve().parents[1]
TAG = 'p108_query_transport_v1_20261113'
BASE = ROOT/'test_result/evidence'/TAG
SOURCE = source.BASE
DEADLINE = datetime(2026, 11, 13, 8, tzinfo=timezone.utc)
SOURCES = tuple(dict.fromkeys((*source.SOURCES, 'scripts/diag_p108_query_transport.py',
    'scripts/test_p108_query_transport.py', 'scripts/diag_p108_key_transport.py',
    'scripts/p108_key_transport.py')))
CAPTURE = FunctionType(old_transport.capture.__code__, dict(old_transport.capture.__globals__, prior=query),
                       old_transport.capture.__name__, old_transport.capture.__defaults__)


class Budget:
    def __init__(self): self.start = time.monotonic()
    def check(self):
        if time.monotonic()-self.start > 1200 or (DEADLINE-datetime.now(timezone.utc)).total_seconds() < 900:
            raise TimeoutError('query transport phase/authority reserve')


def capture(active, module, row):
    """Reuse sealed prefill capture; root hook only retains CPU final logits."""
    logits = []
    def hook(_module, _args, output):
        if not isinstance(output, torch.Tensor) or output.ndim != 3 or output.shape[:2] != (1, 1):
            raise ValueError('batch-one final-position logits required')
        if not torch.isfinite(output).all(): raise ValueError('nonfinite prefill logits')
        logits.append(output.detach().cpu().flatten())
    handle = active['model'].register_forward_hook(hook)
    try: saved = CAPTURE(active, module, row)
    finally: handle.remove()
    if len(logits) != 1: raise RuntimeError('exactly one prefill required')
    return dict(saved, logits=logits[0])


def local_answer(active, module, row, delta, writer, variant):
    # inject() applies once per context: observation and generation must be separate.
    with query.oracle(active, module, row, delta): observed = capture(active, module, row)
    with query.oracle(active, module, row, delta):
        result = query.prior.generated(active, row, writer, variant)
    first_token_parity(observed['logits'], result)
    return observed, result


def first_token_parity(logits, row):
    ids = row['generation']['generated_ids']
    if not ids or int(logits.argmax()) != ids[0]:
        raise RuntimeError('no-cache prefill argmax differs from cached greedy first token')


def compare_logits(left, right):
    if left.shape != right.shape: raise ValueError('same vocabulary required')
    return dict(max_abs=float((left-right).abs().max()), argmax_equal=int(left.argmax()) == int(right.argmax()))


def prepare():
    if BASE.exists(): raise FileExistsError('fresh query transport namespace required')
    if datetime.now(timezone.utc) >= DEADLINE: raise TimeoutError('authority expired')
    p = source.verify(); r = common.read_json(SOURCE/'actual/report.json')
    if r['status'] != 'TECHNICAL_COMPLETE_QUALITY_SEPARATE' or not r['registered_core_unchanged']:
        raise ValueError('closed covariance actual required')
    manifest = common.read_json(SOURCE/'actual/answers_shards_manifest.json'); verify_shards(SOURCE/'actual', manifest)
    selected = p['selected']; facts = {s['fact'] for s in selected}
    rows = [row for row in common.read_json(SOURCE/'data.json')['rows'] if row['fact'] in facts]
    if len(rows) != 52 or len({r['id'] for r in rows}) != 52: raise ValueError('same52 target rows required')
    paths = [SOURCE/'profile.json', SOURCE/'data.json', SOURCE/'actual/report.json', SOURCE/'actual/answers_shards_manifest.json']
    paths += [SOURCE/'actual'/s['path'] for s in manifest['shards']]
    paths += [SOURCE/'actual'/f"{s['fact']}_{name}_packet.json" for s in selected for name in ('covariance', 'plain')]
    refs = {str(path.relative_to(ROOT)):manual.file_sha(path) for path in paths}
    sources = dict(manual.required_source_pins()); sources.update({n:manual.file_sha(ROOT/n) for n in SOURCES})
    common.write_json(BASE/'data.json', dict(rows=rows))
    (BASE/'initial_plan.txt').write_bytes((ROOT/query.prior.PLAN).read_bytes())
    common.write_json(BASE/'profile.json', dict(schema='P108_QUERY_TRANSPORT_V1', tag=TAG,
        authority_directive=115, deadline=DEADLINE.isoformat(), model=p['model'], sources=sources, references=refs,
        selected=selected, origin=r['origin'], data_sha256=manual.file_sha(BASE/'data.json'),
        plan_sha256=manual.file_sha(BASE/'initial_plan.txt'), manifest_sha256=manual.canonical_sha(manual.verify_manifest()),
        max_new=64, reused_test_not_independent=True, new_optimizer_updates=0, checkpoint_writes=0,
        prefill_logits='NO_CACHE_FP32_MATH; ARGMAX_CHECKED_AGAINST_CACHED_GREEDY_FIRST_TOKEN'))
    print('[PREPARED] '+TAG, flush=True)


def verify():
    p = common.read_json(BASE/'profile.json')
    if p['authority_directive'] != 115 or p['deadline'] != DEADLINE.isoformat(): raise ValueError('authority changed')
    for name, sha in dict(p['sources'], **p['references']).items():
        if manual.file_sha(ROOT/name) != sha: raise ValueError('source/reference changed: '+name)
    for name, key in (('data.json','data_sha256'), ('initial_plan.txt','plan_sha256')):
        if manual.file_sha(BASE/name) != p[key]: raise ValueError('frozen input changed')
    if manual.canonical_sha(manual.verify_manifest()) != p['manifest_sha256']: raise ValueError('model manifest changed')
    return p


def run():
    p = verify(); budget = Budget(); budget.check(); out = BASE/'actual'
    if out.exists(): raise FileExistsError('actual already attempted')
    writer = ShardWriter(out, 'answers', limit=3_000_000)
    report = dict(schema=p['schema'], tag=TAG, status='RUNNING', rows=[], reused_test_not_independent=True,
                  new_optimizer_updates=0, checkpoint_writes=0, parity_generations_outside_shards=0)
    active = modules = module = delta = None; failure = None
    try:
        manual.require_idle_gpu()
        free = subprocess.run(['nvidia-smi','--query-gpu=memory.free','--format=csv,noheader,nounits'],
            capture_output=True, text=True, check=True, timeout=10).stdout.strip()
        if not free.isdigit() or int(free) < 4096: raise MemoryError('4096MiB point free required')
        report['entry_free_mib'] = int(free)
        with manual.selected_runtime(manual.resolve_model(p['model'])) as active:
            torch.set_num_threads(4); torch.cuda.reset_peak_memory_stats()
            report['origin'] = {k:active[k] for k in ['name','checkpoint_sha256','core_sha256','tokenizer_sha256']}
            if report['origin'] != p['origin']: raise ValueError('source model changed')
            rows = common.read_json(BASE/'data.json')['rows']; modules = wsp.outputs(active['model'])
            manifest = common.read_json(SOURCE/'actual/answers_shards_manifest.json'); old = {}
            for s in manifest['shards']:
                for line in (SOURCE/'actual'/s['path']).read_text().splitlines():
                    row = json.loads(line); old[(row['variant'], row['id'])] = row
            probe = rows[0]; _, live = manual.emit(active, probe['question'], max_new=64)
            report['parity_generations_outside_shards'] += 1
            if live['generated_ids'] != old[('original',probe['id'])]['generation']['generated_ids']:
                raise RuntimeError('initial original token parity failed')
            for selected in p['selected']:
                fact, layer = selected['fact'], selected['layer']; module = modules[f'mlp:{layer}']
                v = torch.tensor(selected['value_delta'])
                packets = {}
                for name in ('covariance','plain'):
                    packet = common.read_json(SOURCE/'actual'/f'{fact}_{name}_packet.json')
                    if metrics.tensor_sha(module.weight) != packet['base_weight_sha256']: raise ValueError('matrix changed')
                    matrix = (torch.tensor(packet['left'],dtype=torch.float64)[:,None] @
                              torch.tensor(packet['right'],dtype=torch.float64)[None,:]).float()
                    if metrics.tensor_sha(matrix) != packet['delta_sha256']: raise ValueError('edit packet changed')
                    packets[name] = matrix
                for index, row in enumerate(r for r in rows if r['fact'] == fact):
                    budget.check(); baseline = old[('original',row['id'])]
                    writer.append(dict(baseline, reused_source=str(SOURCE.relative_to(ROOT))))
                    original = capture(active, module, row); first_token_parity(original['logits'], baseline)
                    fixed_obs, fixed = local_answer(active,module,row,v,writer,fact+':fixed_last_value')
                    rr = dict(id=row['id'],fact=fact,layer=layer,split=row['split'],original_exact=baseline['exact'],
                              fixed_exact=fixed['exact'],arms=[])
                    for name, matrix in packets.items():
                        budget.check(); previous = old[(fact+':'+name,row['id'])]
                        writer.append(dict(previous,reused_source=str(SOURCE.relative_to(ROOT))))
                        delta = matrix.to(module.weight)
                        with wsp.edit(active['model'],active['route'],[(f'mlp:{layer}',delta)]) as receipt:
                            edited = capture(active,module,row)
                            if not torch.equal(original['key'],edited['key']): raise RuntimeError('upstream last key changed')
                            first_token_parity(edited['logits'], previous)
                            if index == 0:
                                _, live = manual.emit(active,row['question'],max_new=64)
                                report['parity_generations_outside_shards'] += 1
                                if live['generated_ids'] != previous['generation']['generated_ids']:
                                    raise RuntimeError('global edit token parity failed')
                        response = edited['output']-original['output']
                        observed, result = local_answer(active,module,row,response,writer,fact+':'+name+':local_response')
                        flags = geometry.evidence_flags(baseline['exact'],fixed['exact'],result['exact'],previous['exact'])
                        flags['non_target_or_decode_involvement'] = flags.pop('non_subject_loss')
                        rr['arms'].append(dict(name=name,local_exact=result['exact'],global_exact=previous['exact'],
                            realized_geometry=geometry.response_geometry(response,v),
                            analytic_realized_max_abs=float((matrix.double()@original['key'].double()-response.double()).abs().max()),
                            fixed_local_logits=compare_logits(fixed_obs['logits'],observed['logits']),
                            local_global_logits=compare_logits(observed['logits'],edited['logits']),
                            evidence=flags,receipt=receipt))
                        delta = None
                    report['rows'].append(rr)
                module = None
                print('[QUERY_TRANSPORT] '+json.dumps(dict(fact=fact,rows=sum(r['fact']==fact for r in report['rows']))),flush=True)
            _, live = manual.emit(active,probe['question'],max_new=64); report['parity_generations_outside_shards'] += 1
            if live['generated_ids'] != old[('original',probe['id'])]['generation']['generated_ids']:
                raise RuntimeError('final rollback token parity failed')
            report.update(registered_core_unchanged=True,final_rollback_token_parity=True,
                          peak_allocated_bytes=torch.cuda.max_memory_allocated(),peak_reserved_bytes=torch.cuda.max_memory_reserved())
            modules = module = delta = None
        active = None; report['status'] = 'TECHNICAL_COMPLETE_QUALITY_SEPARATE'
    except BaseException as exc:
        traceback.print_exc();report.update(status='ERROR',error=repr(exc));failure=RuntimeError('Query transport: '+repr(exc))
    finally:
        active = modules = module = delta = None;gc.collect()
        try: close_owned_cuda(torch,report)
        except BaseException as exc:
            report.update(status='ERROR',cleanup_error=repr(exc));failure=failure or RuntimeError(repr(exc))
        try: verify();report['sources_assets_unchanged']=True
        except BaseException as exc:
            report.update(status='ERROR',source_error=repr(exc));failure=failure or RuntimeError(repr(exc))
        manifest=writer.close(lineage=dict(profile_sha256=manual.file_sha(BASE/'profile.json')));verify_shards(out,manifest)
        report.update(seconds=time.monotonic()-budget.start,answer_rows=manifest['rows']);common.write_json(out/'report.json',report)
    if failure is not None: raise failure
    print('[COMPLETE] '+json.dumps({k:report[k] for k in ['status','seconds','answer_rows']}),flush=True)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=['prepare','run']);a=parser.parse_args()
    (prepare if a.phase=='prepare' else run)()


if __name__=='__main__':main()
