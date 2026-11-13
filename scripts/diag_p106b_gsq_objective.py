"""Full-geometry technical GSQ/STE cost; no student-quality evaluation."""
from datetime import datetime, timezone
import gc
import hashlib
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
BASE = ROOT / 'test_result/evidence/p106b_gsq_objective_v2_20261105'
TRAIN = ROOT / 'HF/sft_ready/p106b_alm_train_ternary_v1_s1337'
MODEL = 'new595-broad-q'
SCHEMA = 'P106B_GSQ_OBJECTIVE_COST_V1'
DEADLINE = datetime(2026, 11, 5, 8, tzinfo=timezone.utc)
SOURCE = (
    'scripts/diag_p106b_gsq_objective.py', 'scripts/p106b_gsq_objective.py',
    'scripts/test_p106b_gsq_objective.py', 'scripts/test_p106b_gsq_objective_cost.py',
    'scripts/p093b_native_repair.py',
    'scripts/p101a_sft_mtp_data.py', 'scripts/interactive_research_infer.py',
    'scripts/p106b_weight_route.py', 'scripts/p106b_shards.py',
    'scripts/diag_p107_hybrid_mntp.py', 'tinylm/train/alm.py',
    'tinylm/train/mtp_sft.py', 'tinylm/model/ternary.py',
    'tinylm/model/transformer.py', 'tinylm/model/modules.py', 'tinylm/config.py',
)
POLICY = dict(micro=8, accum=16, width=1024, warmup_updates=1, timed_updates=2,
    optimizer='AdamW_COMMON_FOREACH_FALSE', lr=1e-5, betas=[.9, .95],
    eps=1e-8, weight_decay=0., clip=1., checkpoint=True, compile=False,
    head_chunk=64, temperature=100., alm_weight=1., gsq_logit_strength=4.6,
    precision='BF16_EAGER_TF32_OFF', mtp=False, recurrence='R1',
    quality_evaluation=False, checkpoint_saving=False)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest().upper()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')


def object_sha(value):
    return hashlib.sha256(canonical(value)).hexdigest().upper()


def write(path, value):
    path = Path(path)
    body = json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False).encode('utf-8')
    if len(body) >= 20_000_000:
        raise ValueError('technical report must stay below20MB')
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(body)


def guard(start=None, maximum=900):
    if (DEADLINE - datetime.now(timezone.utc)).total_seconds() < 600:
        raise TimeoutError('user109 final cleanup reserve reached')
    if start is not None and time.perf_counter() - start > maximum:
        raise TimeoutError('technical phase budget reached')


def selected_rows(prepared, rows):
    if (prepared.get('schema') != 'P106B_ALM_REFERENCE_TRAIN_TERNARY_V1'
            or prepared.get('status') != 'ALM_TRAIN_PREPARED'
            or len(rows) != 1024 or prepared.get('rows') != 1024
            or [object_sha(row) for row in rows] != prepared['row_sha256']):
        raise ValueError('closed original TRAIN1024 manifest and exact rows required')
    languages = {language: [row for row in rows if row['language'] == language][:64]
                 for language in ('ko', 'en')}
    if any(len(values) != 64 for values in languages.values()):
        raise ValueError('fixed64+64 technical exposure required')
    chosen = [row for pair in zip(languages['ko'], languages['en']) for row in pair]
    for row in chosen:
        record = row['record']
        if (object_sha(record) != row['record_sha256']
                or not len(record['x']) == len(record['y']) == len(record['segments']) <= 1024
                or sum(v != -100 for v in record['y']) != row['ce_targets']
                or len(row['chunks']) != row['kd_chunks']):
            raise ValueError('original already-shifted record/counts changed')
        seen = set()
        for chunk in row['chunks']:
            indices = chunk['positions']
            if (not indices or indices != list(range(indices[0], indices[0]+len(indices)))
                    or seen.intersection(indices)
                    or any(type(i) is not int or not 0 <= i < len(record['y'])
                           or record['y'][i] in (-100, 2, 4) for i in indices)
                    or not isinstance(chunk['teacher_logprob'], (int, float))
                    or not -1e30 < chunk['teacher_logprob'] <= 0):
                raise ValueError('original aligned teacher chunk changed')
            seen.update(indices)
    return chosen


def load_cpu():
    from scripts import interactive_research_infer as manual
    manifest = manual.verify_manifest()
    spec = manual.resolve_model(MODEL)
    entry = manifest['entries'][MODEL]
    torch, config_type, model_type, route = manual.inference_modules()
    torch.set_num_threads(2)
    payload = manual.read_selected_payload(torch, spec, entry)
    cfg = config_type(**payload['cfg'])
    manual.validate_cfg(cfg, entry['header'])
    with torch.device('cpu'), torch.random.fork_rng(devices=[]):
        torch.random.default_generator.manual_seed(61105)
        model = model_type(cfg)
    with route.weight_route(model, 'ternary'):
        route.load_routed_state(model, payload, 'ternary')
        if manual.state_fingerprint(model) != entry['core_sha256']:
            raise ValueError('exact completed checkpoint core changed')
    model.clear_quant()
    del payload
    return torch, model, manifest, entry, spec


def inventory(model):
    from tinylm.model.ternary import TLinear
    matrices = {id(m.weight): (m.weight, m.cfg.micro_group or m.weight.shape[1])
                for m in model.modules() if isinstance(m, TLinear)}
    for parameter in [model.emb.weight] + ([model.emb_up.weight] if model.emb_up is not None else []):
        matrices.setdefault(id(parameter), (parameter, model.cfg.micro_group or parameter.shape[1]))
    count = sum(p.numel() for p, _ in matrices.values())
    groups = sum(p.numel() // group for p, group in matrices.values())
    return dict(physical_banks=len(matrices), matrix_elements=count, scale_groups=groups,
        frozen_original_bytes=4*count, ste_bank_bytes=4*count,
        gsq_bank_bytes=8*count+4*groups,
        gsq_bank_grad_adam_moments_bytes=(8*count+4*groups)*4,
        warning='Arithmetic tensor lower bound only: excludes original norms, Gumbel graph, hard matrices, activations, workspaces and allocator reservation.')


def prepare():
    guard()
    if BASE.exists():
        raise FileExistsError('fresh technical namespace required')
    from scripts.p101a_sft_mtp_data import stream_rows
    report_path = TRAIN / 'report.json'
    prepared = json.loads(report_path.read_text(encoding='utf-8'))
    rows = selected_rows(prepared, list(stream_rows(TRAIN, prepared['manifest'])))
    torch, model, manifest, entry, spec = load_cpu()
    geometry = inventory(model)
    del model
    gc.collect()
    data_path = BASE / 'training_rows.json'
    write(data_path, dict(schema=SCHEMA, rows=rows))
    counts = dict(rows=128, language_rows=dict(ko=64, en=64),
        actual_x_tokens=sum(len(r['record']['x']) for r in rows),
        ce_targets=sum(r['ce_targets'] for r in rows),
        kd_chunks=sum(r['kd_chunks'] for r in rows), padded_slots=8*16*1024)
    profile = dict(schema=SCHEMA, status='PREPARED', authority_directive=109,
        deadline=DEADLINE.isoformat(), model=MODEL, policy=POLICY, counts=counts,
        sources={name:sha(ROOT/name) for name in SOURCE},
        training_report=dict(path=str(report_path.relative_to(ROOT)), sha256=sha(report_path)),
        training_data=dict(path=str(data_path.relative_to(ROOT)), sha256=sha(data_path)),
        manual_manifest_sha256=object_sha(manifest),
        entry=entry, checkpoint=str(spec.checkpoint), inventory=geometry,
        original_route='Historical checkpoint TLinear-only ternary; both new technical arms use the same native hard ternary embedding/main head too.',
        teacher_origin='Existing closed native Qwen logprob TRAIN cache. No new teacher calls, no benchmark answers or held-out rows selected.',
        semantics='TECHNICAL_GRADIENT_AND_COST_ONLY_NOT_SMALL_RUN_MODEL_QUALITY',
        corpus_cleaning_complete=False, additional300m=False, cpu_checkpoint_load=True,
        cpu_forward=False, gpu=False, checkpoint_writes=False)
    write(BASE / 'profile.json', profile)
    print('[GSQ_PREPARED] '+json.dumps(dict(counts=counts, inventory=geometry,
        profile_sha256=sha(BASE/'profile.json'), gpu=False)), flush=True)


def verify():
    profile = json.loads((BASE/'profile.json').read_text(encoding='utf-8'))
    if (profile.get('schema') != SCHEMA or profile.get('authority_directive') != 109
            or profile.get('deadline') != DEADLINE.isoformat() or profile.get('policy') != POLICY):
        raise ValueError('technical authority/policy changed')
    pins = dict(profile['sources'])
    for key in ('training_data', 'training_report'):
        pins[profile[key]['path']] = profile[key]['sha256']
    for name, expected in pins.items():
        if sha(ROOT/name) != expected:
            raise ValueError('frozen technical input changed: '+name)
    rows = json.loads((ROOT/profile['training_data']['path']).read_text(encoding='utf-8'))['rows']
    if len(rows) != 128:
        raise ValueError('fixed128 actual training records required')
    return profile, rows


def measure(torch, model, rows, arm, started, maximum):
    from scripts.p106b_gsq_objective import ObjectiveBridge
    from tinylm.train.mtp_sft import Record, pad_records
    from tinylm.train import alm
    bridge = ObjectiveBridge(model, arm, logit_strength=POLICY['gsq_logit_strength'])
    model.cfg.grad_checkpoint = True
    model.train()
    records = [Record(list(r['record']['x']), list(r['record']['y']),
                      list(r['record']['segments'])) for r in rows]
    totals = dict(ce_targets=sum(r['ce_targets'] for r in rows),
                  kl_chunks=sum(r['kd_chunks'] for r in rows))
    events = []
    with bridge.installed():
        parameters = bridge.parameters_for_optimizer()
        opt = torch.optim.AdamW(parameters, lr=POLICY['lr'], betas=tuple(POLICY['betas']),
            eps=POLICY['eps'], weight_decay=0., foreach=False)
        for update in range(3):
            guard(started, maximum)
            opt.zero_grad(set_to_none=True)
            torch.cuda.synchronize()
            begin = time.perf_counter()
            ce_sum = kl_sum = 0.
            for micro in range(16):
                guard(started, maximum)
                selected = records[micro*8:(micro+1)*8]
                x, y, _ = pad_records(selected, 0, 'cuda', fixed_width=1024, batch_size=8)
                chunks = [dict(chunk, row=i) for i, row in enumerate(rows[micro*8:(micro+1)*8])
                          for chunk in row['chunks']]
                with bridge.realization(6110500+update*16+micro):
                    with torch.autocast('cuda', dtype=torch.bfloat16):
                        terms = bridge.loss_terms(x, y, chunks, temperature=100., head_chunk=64)
                        loss = alm.normalized_loss(terms['ce_sum'], totals['ce_targets'],
                            terms['kl_sum'], totals['kl_chunks'], weight=1.)
                    bridge.backward(loss)
                ce_sum += float(terms['ce_sum'].detach())
                kl_sum += float(terms['kl_sum'].detach())
                del terms, loss, x, y
            norm = torch.nn.utils.clip_grad_norm_(parameters, 1., error_if_nonfinite=True)
            opt.step()
            bridge.project()
            torch.cuda.synchronize()
            seconds = time.perf_counter()-begin
            event = dict(update=update+1, warmup=update==0, seconds=seconds,
                ce_targets=totals['ce_targets'], kd_chunks=totals['kl_chunks'],
                ce_sum=ce_sum, kl_sum=kl_sum, grad_norm_before_clip=float(norm),
                padded_slots=131072, actual_x_tokens=sum(len(r.x) for r in records),
                allocated_bytes=torch.cuda.memory_allocated(), reserved_bytes=torch.cuda.memory_reserved())
            events.append(event)
            print('[GSQ_COST_UPDATE] '+json.dumps(dict(arm=arm, **event)), flush=True)
        info = bridge.inventory()
    return dict(events=events, bank_inventory=info,
        measured_update_seconds=sum(e['seconds'] for e in events[1:])/2,
        updates=3, quality_evaluation=False, checkpoint_saving=False)


def execute(arm, maximum=900):
    guard()
    profile, rows = verify()
    directory = BASE / arm
    directory.mkdir(exist_ok=False)
    started = time.perf_counter()
    result = dict(schema=SCHEMA, arm=arm, status='STARTED', returncode=9,
        profile_sha256=sha(BASE/'profile.json'), policy=POLICY,
        training_rows=128, benchmark=False, original_checkpoint_writes=0)
    torch = model = manifest = entry = spec = None
    try:
        from scripts import interactive_research_infer as manual
        result['gpu_admission'] = manual.require_idle_gpu()
        torch, model, manifest, entry, spec = load_cpu()
        if (object_sha(manifest) != profile['manual_manifest_sha256']
                or entry != profile['entry'] or str(spec.checkpoint) != profile['checkpoint']):
            raise ValueError('actual CPU load differs from fixed profile')
        torch.backends.cuda.matmul.allow_tf32 = False
        torch.backends.cudnn.allow_tf32 = False
        torch.cuda.reset_peak_memory_stats()
        model = model.cuda()
        result.update(measure(torch, model, rows, arm, started, maximum))
        result.update(status='TECHNICAL_COST_COMPLETE', returncode=0,
            peak_allocated_bytes=torch.cuda.max_memory_allocated(),
            peak_reserved_bytes=torch.cuda.max_memory_reserved())
    except BaseException as exc:
        result.update(status='TECHNICAL_COST_ERROR', error_type=type(exc).__name__,
                      error=str(exc), returncode=9)
    if torch is not None and torch.cuda.is_initialized():
        result.setdefault('peak_allocated_bytes', torch.cuda.max_memory_allocated())
        result.setdefault('peak_reserved_bytes', torch.cuda.max_memory_reserved())
    model = manifest = entry = spec = None
    gc.collect()
    if torch is not None:
        try:
            from scripts.diag_p107_hybrid_mntp import close_owned_cuda
            close_owned_cuda(torch, result)
        except BaseException as exc:
            result.update(status='CUDA_CLEANUP_UNVERIFIED', cleanup_error=str(exc), returncode=9)
    result['original_checkpoint_unchanged'] = sha(ROOT/profile['checkpoint']) == profile['entry']['checkpoint']['sha256']
    if not result['original_checkpoint_unchanged']:
        result.update(status='ORIGINAL_CHECKPOINT_CHANGED', returncode=9)
    result['wall_seconds_before_report_write'] = time.perf_counter()-started
    write(directory/'report.json', result)
    print('[GSQ_COST_FINAL] '+json.dumps(result), flush=True)
    return result['returncode']


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('prepare', 'cost'))
    parser.add_argument('--arm', choices=('ste', 'gsq'))
    parser.add_argument('--max-wall-sec', type=int, default=900)
    args = parser.parse_args()
    if args.mode == 'prepare':
        prepare()
        return 0
    if args.arm is None or not 60 <= args.max_wall_sec <= 900:
        parser.error('cost requires an explicit arm and60..900 seconds')
    return execute(args.arm, args.max_wall_sec)


if __name__ == '__main__':
    raise SystemExit(main())
