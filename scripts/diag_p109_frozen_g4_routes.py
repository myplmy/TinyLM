"""Compare frozen G4 visit policies on two existing zero-shot choice tasks."""

import argparse
from datetime import datetime
import hashlib
import json
import math
import os
from pathlib import Path
import signal
import sysconfig
import time

from scripts import diag_p109_warm_visit_routes as prior
from scripts import p106b_official_lm_adapter as adapter
from scripts import prepare_p106b_official_eval as core6
from scripts import prepare_p106b_kobest_official_eval as kobest
from scripts import summarize_p106b_core6_pairs as audit
from scripts.p106b_official_tasks import task_requests


ROOT = prior.io.ROOT
TAG = 'p109_frozen_g4_route_ko_en_v1_20261119'
OUT = ROOT / 'test_result/evidence' / TAG
PLAN = ROOT / 'test_plan/P109_16층-공유-재귀-프리셋-통합.md'
TOKENIZER = ROOT / 'data_cache/tok-ko-en-32768.json'
PARENT_SHA = 'D576B9EB6DEF02DF5DCCAD91E484098AFB67A52553A7A735B21249DB2D9EC3D5'
TOKENIZER_SHA = '3A69001ECC28A5BDF1E951A1036B234C9BDCB847B310252C6D72CFC6C52C48E3'
KOBEST_SHA = '4635FD5DC408CBAF7D70A55369501F63B94195C47D623DE1F36FCB3C62A86501'
TASKS = {'winogrande': 1267, 'kobest_copa': 1000}
ARMS = ('uniform_r2', 'uniform_r1', 'uniform_r3', 'second_shuffle_r2')
BATCH_CHOICES, VOCAB, MAX_WALL = 16, 32768, 420
SOURCES = (*prior.SOURCES, 'scripts/diag_p109_frozen_g4_routes.py',
           'scripts/p106b_official_lm_adapter.py', 'scripts/prepare_p106b_official_eval.py',
           'scripts/prepare_p106b_kobest_official_eval.py', 'scripts/p106b_official_tasks.py',
           'scripts/summarize_p106b_core6_pairs.py', 'tinylm/data/prepare.py')


def read_json(path):
    return json.loads(path.read_bytes())


def checksum(value):
    return hashlib.sha256(adapter.canonical(value)).hexdigest().upper()


def prepare_inputs():
    for key in ('HF_HUB_OFFLINE', 'HF_DATASETS_OFFLINE', 'TRANSFORMERS_OFFLINE',
                'HF_EVALUATE_OFFLINE', 'HF_HUB_DISABLE_TELEMETRY'):
        os.environ[key] = '1'
    core6.configure_hf_cache()
    runtime = Path(sysconfig.get_paths()['purelib'])
    template, framework = adapter.prepare_harness(runtime_root=runtime)
    from datasets import Dataset
    from lm_eval.api.task import ConfigurableTask
    from lm_eval.tasks._yaml_loader import load_yaml
    import pyarrow.parquet as parquet
    from tinylm.data.prepare import load_tokenizer, tokenizer_path

    pins = audit.Inputs()
    for source in SOURCES:
        pins.add(ROOT / source)
    pins.add(prior.PARENT, PARENT_SHA)
    if tokenizer_path('ko-en', VOCAB) != TOKENIZER:
        raise ValueError('P079 ko-en tokenizer path differs')
    pins.add(TOKENIZER, TOKENIZER_SHA)
    tokenizer = load_tokenizer('ko-en', VOCAB)
    special = [tokenizer.token_to_id(token) for token in ('<pad>', '<bos>', '<eos>')]
    if tokenizer.get_vocab_size() != VOCAB or special != [0, 1, 2]:
        raise ValueError('P079 native vocabulary or special IDs differ')

    manifest = core6.ASSETS / 'manifest.json'
    pins.add(manifest, core6.MANIFEST_SHA)
    wino = next(spec for spec in core6.task_specs(read_json(manifest)) if spec['task'] == 'winogrande')
    audit.verify_pinned_task_code(pins, framework, [wino], runtime)
    pins.add(Path(wino['data_file']), wino['data_sha256'])
    wino_data = Dataset(parquet.read_table(wino['data_file']))

    manifest = kobest.ASSETS / 'manifest.json'
    pins.add(manifest, KOBEST_SHA)
    ko = read_json(manifest)
    if (ko['dataset_revision'], ko['source_commit']) != (kobest.REVISION, adapter.COMMIT):
        raise ValueError('KoBEST revision or evaluation framework differs')
    copa = next(spec for spec in ko['tests'] if spec['task'] == 'kobest_copa')
    source_tree = Path(framework['source_root'])
    archive = Path(read_json(Path(framework['manifest_path']))['archive_path'])
    ko_source = kobest.task_sources(source_tree, archive)
    for name in ('_kobest.yaml', 'kobest_copa.yaml', 'utils.py'):
        relative = 'lm_eval/tasks/kobest/' + name
        pins.add(source_tree / relative, ko_source[relative])
    copa_path = ROOT / copa['local_path']
    pins.add(copa_path, copa['sha256'])
    if kobest.scan_test(copa_path, 'copa')['ordered_json_sha256'] != copa['ordered_json_sha256']:
        raise ValueError('KoBEST COPA test order differs')
    copa_data = Dataset.from_list([json.loads(line, object_pairs_hook=kobest.unique_object)
                                  for line in copa_path.read_bytes().splitlines()])

    prepared = {}
    for name, yaml, overrides, split, data in (
        ('winogrande', wino['official_yaml'], wino['overrides'], 'validation', wino_data),
        ('kobest_copa', source_tree / 'lm_eval/tasks/kobest/kobest_copa.yaml',
         copa['storage_overrides'], 'test', copa_data),
    ):
        config = load_yaml(str(yaml), resolve_func=True, recursive=True)
        keys = ('doc_to_text', 'doc_to_target', 'doc_to_choice', 'process_docs', 'metric_list',
                'target_delimiter')
        original = {key: config.get(key) for key in keys}
        config.update(overrides)
        task = audit.memory_task(ConfigurableTask, config, {split: data})
        if (task.config.task != name or set(task.dataset) != {split} or data.cache_files
                or len(task.eval_docs) != TASKS[name]
                or any(getattr(task.config, key) != value for key, value in original.items()
                       if value is not None)):
            raise ValueError('official task, split, count or science fields differ: ' + name)
        prepared[name] = prepare_task(task, template, tokenizer)
    pins.unchanged()
    return pins, prepared


def prepare_task(task, template, tokenizer):
    rows, requests, batches = [], [], []
    for index, doc in enumerate(task.eval_docs):
        _, choices, cases = task_requests(task, dict(doc), index)
        gold = task.doc_to_text(doc) if task.multiple_input else task.doc_to_target(doc)
        gold = choices.index(gold) if isinstance(gold, str) else gold
        if (len(choices) != 2 or type(gold) is not int or gold not in (0, 1)
                or [case.idx for case in cases] != [0, 1]):
            raise ValueError('exactly two ordered official choices and a valid gold are required')
        rows.append(dict(index=index, doc=dict(doc), choices=choices, gold=gold))
        requests.extend(cases)

    def capture(batch):
        batches.append(batch)
        return [(-1.0, False)] * len(batch['input_ids'])

    planner = adapter.LikelihoodCore(vocab_size=VOCAB, pad_id=0, score_batch=capture,
                                     batch_size=BATCH_CHOICES)
    encoder = adapter._adapter_type(template)(core=planner, tokenizer=tokenizer, prefix_id=1,
                                              eos_id=2, provenance={'tokenizer_sha256': TOKENIZER_SHA})
    encoder.loglikelihood(requests, disable_tqdm=True)
    diagnostics = planner.diagnostics()
    encoder.close()
    if diagnostics['requests_scored'] != len(requests) or diagnostics['context_truncated_requests']:
        raise ValueError('all original continuations and complete contexts are required')
    max_width = max(len(batch['input_ids'][0]) for batch in batches)
    if max_width * BATCH_CHOICES * VOCAB * 4 > 512 * 1024**2:
        raise ValueError('planned full FP32 logits exceed the frozen 512 MiB budget')
    receipt = dict(rows=len(rows), choice_requests=len(requests), batches=len(batches),
                   request_sha256=checksum([[case.doc_id, case.idx, case.args] for case in requests]),
                   token_batch_sha256=checksum(batches), max_width=max_width,
                   scored_tokens=diagnostics['continuation_tokens_scored'], context_truncations=0)
    return dict(rows=rows, batches=batches, task=task, receipt=receipt)


def profile(pins, prepared):
    return dict(tag=TAG, files=pins.files, plan_sha256=prior.io.digest(PLAN), approval='WIP176',
                cutoff=prior.CUTOFF.isoformat(), batch_choices=BATCH_CHOICES,
                tasks={name: task['receipt'] for name, task in prepared.items()})


def check_authority(seconds=0):
    if time.time() + seconds >= prior.CUTOFF.timestamp() or (OUT / 'STOP').exists():
        raise RuntimeError('experiment authority or owned stop signal')


def evaluate(torch, prepared, frozen):
    from scripts.p070b_cla_routes import route_sha, schedule
    from torch.nn.attention import SDPBackend, sdpa_kernel

    cfg, state, checkpoint_step = prior.load_parent(torch)
    model = prior.build_model(cfg).eval()
    model.load_state_dict(state, strict=True)
    del state
    routes = prior.policy_schedules(cfg, model.owner)
    fixed = {'uniform_r1': schedule(cfg, model.owner, 'uniform', 1),
             'uniform_r2': routes['uniform_r2'][0],
             'uniform_r3': schedule(cfg, model.owner, 'uniform', 3)}
    if model._repeat_schedule(2.) != fixed['uniform_r2'] or [len(r) for r in fixed.values()] != [16, 28, 40]:
        raise ValueError('native R2 route or balanced launch counts differ')
    route_book = {arm: [route_sha(cfg, model.owner, route)] for arm, route in fixed.items()}
    route_book['second_shuffle_r2'] = [route_sha(cfg, model.owner, route)
                                      for route in routes['second_shuffle_r2']]
    torch.set_float32_matmul_precision('highest')
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    model = model.cuda().float()
    if torch.cuda.mem_get_info()[0] < 4 * 1024**3:
        raise RuntimeError('less than 4 GiB of CUDA memory is available')
    model.set_anneal(1.)
    scorer = adapter.TorchLikelihood(dict(torch=torch, model=model, cfg=cfg), model)
    raw = OUT / 'choice_batches.jsonl'
    first = prepared['winogrande']['batches'][0]
    with raw.open('x', encoding='utf-8') as stream, torch.inference_mode(), sdpa_kernel(SDPBackend.MATH):
        model.freeze_quant()
        model.set_route(fixed['uniform_r2'])
        observed = scorer(first)
        oracle = adapter.direct_label_oracle(torch, model, first, VOCAB)
        if any(a[1] != b[1] or not math.isclose(a[0], b[0], abs_tol=1e-4, rel_tol=1e-5)
               for a, b in zip(observed, oracle)):
            raise ValueError('frozen R2 continuation gather vs full-label CE differs')
        for route in (*fixed.values(), routes['second_shuffle_r2'][0]):
            model.set_route(route)
            scorer(first)
        for name, data in prepared.items():
            for index, batch in enumerate(data['batches']):
                check_authority()
                record = dict(task=name, index=index, choice_count=len(batch['input_ids']),
                              input_tokens=sum(batch['lengths']),
                              padded_tokens=len(batch['input_ids']) * len(batch['input_ids'][0]), arms={})
                selected = dict(fixed, second_shuffle_r2=routes['second_shuffle_r2'][index % prior.UPDATES])
                rotate = index % len(ARMS)
                for arm in ARMS[rotate:] + ARMS[:rotate]:
                    model.set_route(selected[arm])
                    torch.cuda.synchronize()
                    torch.cuda.reset_peak_memory_stats()
                    start = time.perf_counter()
                    scores = scorer(batch)
                    torch.cuda.synchronize()
                    record['arms'][arm] = dict(scores=scores, visits=len(selected[arm]),
                        route_sha256=model.route_sha256, seconds=time.perf_counter() - start,
                        peak_allocated_bytes=torch.cuda.max_memory_allocated(),
                        peak_reserved_bytes=torch.cuda.max_memory_reserved())
                print(adapter.canonical(record).decode('utf-8'), file=stream, flush=True)
                if (index + 1) % 32 == 0 or index + 1 == len(data['batches']):
                    print('P109_FROZEN_PROGRESS', name, index + 1, len(data['batches']), flush=True)
    scorer.close()
    return dict(tag=TAG, checkpoint_step=checkpoint_step, checkpoint_sha256=PARENT_SHA,
                tokenizer_sha256=TOKENIZER_SHA, profile_sha256=prior.io.digest(OUT / 'profile.json'),
                raw_sha256=prior.io.digest(raw), plan_sha256=frozen['plan_sha256'],
                device=torch.cuda.get_device_name(), torch=str(torch.__version__),
                full_label_oracle_choices=len(oracle), route_book=route_book,
                optimizer_updates=0, checkpoint_writes=0)


def paired_delta(delta, rng):
    import numpy as np

    values, counts = np.unique(delta, return_counts=True)
    means = rng.multinomial(len(delta), counts / len(delta), size=20000) @ values / len(delta)
    lo, hi = (float(q) for q in np.quantile(means, [0.00625, 0.99375]))
    return dict(delta=float(np.mean(delta)), ci_98_75=[lo, hi],
                wins=int(np.count_nonzero(delta > 0)), losses=int(np.count_nonzero(delta < 0)))


def readback(pins, prepared, recorded):
    from statistics import median
    import numpy as np

    if pins.files != recorded['files'] or profile(pins, prepared)['tasks'] != recorded['tasks']:
        raise ValueError('frozen input or request receipt differs')
    completion = read_json(OUT / 'gpu_report.json')
    raw = OUT / 'choice_batches.jsonl'
    if (prior.io.digest(raw) != completion['raw_sha256']
            or prior.io.digest(OUT / 'profile.json') != completion['profile_sha256']):
        raise ValueError('GPU completion receipt does not close the exact raw file')
    intervals = np.random.default_rng(1337)
    result = {}
    with raw.open(encoding='utf-8') as stream:
        for name, data in prepared.items():
            rows, batches, task = data['rows'], data['batches'], data['task']
            correct = {arm: np.zeros(len(rows), dtype=np.int8) for arm in ARMS}
            stats = {arm: [] for arm in ARMS}
            metrics = {arm: None for arm in ARMS}
            predictions = {arm: np.empty(len(rows), dtype=np.int8) for arm in ARMS}
            offset = 0
            for index, batch in enumerate(batches):
                record = json.loads(next(stream))
                size = len(batch['input_ids'])
                if (name, index, size, set(ARMS)) != (record['task'], record['index'],
                                                       record['choice_count'], set(record['arms'])):
                    raise ValueError('raw batch identity, coverage or arms differ')
                if record['input_tokens'] != sum(batch['lengths']) or record['padded_tokens'] != size * len(batch['input_ids'][0]):
                    raise ValueError('raw token accounting differs')
                for arm, event in record['arms'].items():
                    visits = {'uniform_r1': 16, 'uniform_r3': 40}.get(arm, 28)
                    book = completion['route_book'][arm]
                    if (event['visits'] != visits or len(event['scores']) != size
                            or event['route_sha256'] != book[index % len(book)]):
                        raise ValueError('raw visit count, route identity or choice count differs')
                    stats[arm].append(dict(event, padded_visits=visits * record['padded_tokens']))
                    for pair in range(0, size, 2):
                        ix = offset + pair // 2
                        row = rows[ix]
                        scores = event['scores'][pair:pair + 2]
                        if any(not math.isfinite(value) or value > 0 or type(greedy) is not bool
                               for value, greedy in scores):
                            raise ValueError('invalid choice response')
                        pred = max(range(2), key=lambda j: scores[j][0])
                        observed = task.process_results(row['doc'], scores)
                        hit = int(pred == row['gold'])
                        if (observed['acc'] != hit
                                or ('f1' in observed and tuple(observed['f1']) != (row['gold'], pred))):
                            raise ValueError('official metric disagrees with independent choice recount')
                        correct[arm][ix] = hit
                        predictions[arm][ix] = pred
                        if metrics[arm] is None:
                            metrics[arm] = {key: [] for key in observed}
                        for key, value in observed.items():
                            metrics[arm][key].append(value)
                offset += size // 2
            if offset != TASKS[name]:
                raise ValueError('incomplete raw denominator')
            summaries = {arm: {key: float(task.aggregation()[key](values))
                               for key, values in metrics[arm].items()} for arm in ARMS}
            balanced = (correct['uniform_r1'] + 2 * correct['uniform_r2'] + correct['uniform_r3']) / 4.
            visits = {arm: sum(e['padded_visits'] for e in events) for arm, events in stats.items()}
            if (visits['uniform_r1'] + 2 * visits['uniform_r2'] + visits['uniform_r3']
                    != 4 * visits['uniform_r2'] or visits['second_shuffle_r2'] != visits['uniform_r2']):
                raise ValueError('padded layer-token visit budget differs')
            changes = {arm: int(np.count_nonzero(values != predictions['uniform_r2']))
                       for arm, values in predictions.items()}
            result[name] = dict(rows=offset, by_arm=summaries, changed_choices=changes,
                balanced_expected_accuracy=float(balanced.mean()),
                balanced=paired_delta(balanced - correct['uniform_r2'], intervals),
                shuffle=paired_delta(correct['second_shuffle_r2'] - correct['uniform_r2'], intervals),
                timing={arm: dict(total_seconds=math.fsum(e['seconds'] for e in events),
                                  median_batch_ms=1000 * median(e['seconds'] for e in events),
                                  peak_allocated_bytes=max(e['peak_allocated_bytes'] for e in events),
                                  peak_reserved_bytes=max(e['peak_reserved_bytes'] for e in events),
                                  padded_layer_token_visits=visits[arm]) for arm, events in stats.items()},
                shuffle_unique_routes=len({e['route_sha256'] for e in stats['second_shuffle_r2']}))
        if stream.readline():
            raise ValueError('unsolicited rows after the two closed task ranges')
    pins.unchanged()
    return dict(tag=TAG, gpu_report_sha256=prior.io.digest(OUT / 'gpu_report.json'),
                raw_sha256=completion['raw_sha256'], tasks=result, bootstrap_resamples=20000)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('prepare', 'gpu', 'readback'))
    mode = parser.parse_args().mode
    if os.environ.get('CUDA_VISIBLE_DEVICES') != ('0' if mode == 'gpu' else ''):
        raise ValueError('explicit isolated CPU or selected single GPU is required')
    start = datetime.now(prior.CUTOFF.tzinfo)
    check_authority(MAX_WALL if mode == 'gpu' else 0)
    if mode == 'gpu':
        signal.alarm(MAX_WALL)
    pins, prepared = prepare_inputs()
    frozen = profile(pins, prepared)
    if mode == 'prepare':
        OUT.mkdir()
        prior.io.write(OUT / 'profile.json', frozen)
        print('P109_FROZEN_READY', {name: data['receipt'] for name, data in prepared.items()}, flush=True)
        return
    recorded = read_json(OUT / 'profile.json')
    if mode == 'readback':
        value = readback(pins, prepared, recorded)
        prior.io.write(OUT / 'report.json', value)
        print('P109_FROZEN_READBACK', {k: {x: v[x] for x in ('rows', 'balanced', 'shuffle')}
                                      for k, v in value['tasks'].items()}, flush=True)
        return
    if recorded != frozen or (OUT / 'choice_batches.jsonl').exists():
        raise ValueError('prepared inputs differ or raw output already exists')
    import torch

    torch.set_num_threads(2)
    torch.set_num_interop_threads(1)
    if not torch.cuda.is_available() or torch.cuda.device_count() != 1:
        raise RuntimeError('one visible CUDA device is required')
    value = evaluate(torch, prepared, frozen)
    pins.unchanged()
    if prior.io.digest(PLAN) != frozen['plan_sha256']:
        raise ValueError('experiment plan changed during evaluation')
    check_authority()
    value.update(started=start.isoformat(), ended=datetime.now(prior.CUTOFF.tzinfo).isoformat())
    prior.io.write(OUT / 'gpu_report.json', value)
    print('P109_FROZEN_GPU_COMPLETE', value['raw_sha256'], flush=True)
    signal.alarm(0)


if __name__ == '__main__':
    main()
