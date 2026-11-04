#!/usr/bin/env python3
"""P108 write-once preparation, baseline, search, and frozen confirmation.

Usage: python -m scripts.diag_p108_weight_space PHASE TAG MODEL
No historical authority/profile is reused. No original checkpoint is written.
"""
from __future__ import annotations

import argparse
from contextlib import nullcontext
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import random
import re
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import interactive_research_infer as manual
from scripts import p108_weight_space as repair
from scripts.p106b_shards import ShardWriter, verify as verify_shards

DEADLINE = datetime(2026, 11, 4, 17, tzinfo=timezone.utc)
SCHEMA = 'P108_WEIGHT_SPACE_V1'
SOURCE_PATHS = ('scripts/p108_weight_space.py', 'scripts/diag_p108_weight_space.py',
                'scripts/test_p108_weight_space.py')
PLAN_PATH = 'test_plan/P108_직접가중치-방향수리와-학습개입.md'
OPEN = (
    '1+1은?', '2+2는?', 'A는 사과고 B는 당근이다. B는 무엇인가? 답만 쓰세요.',
    '문맥: 민수는 사과 3개, 영희는 사과 5개를 가지고 있습니다. 영희의 사과는 몇 개입니까?',
    '사과에 대해 두 문장으로 알려줘.', '농구란 무엇인가?', '안녕하세요. 오늘 처음 대화합니다.',
    '어제 산 그 물건은 어디에 두면 좋을까요?',
    'What is an apple? Answer in one sentence.', 'What is basketball?',
    'Alice has three apples. Bob has five apples. How many apples does Bob have?',
    'What is the capital of France?', 'Explain why plants need sunlight in two sentences.',
    'Hello. Please introduce yourself briefly.', 'I changed the number from 3 to 4. What is 2 plus the new number?',
    'Write the word blue exactly three times, separated by spaces.',
)


def write_json(path, value):
    raw = (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + chr(10)).encode('utf-8')
    if len(raw) >= 4_000_000:
        raise ValueError('small report exceeds 4MB')
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(raw)


def read_json(path):
    if path.is_symlink() or path.stat().st_size >= 4_000_000:
        raise ValueError('invalid small JSON path/size')
    return json.loads(path.read_text(encoding='utf-8'))


def make_data():
    rows = []
    for split, count, offset in (('repair', 8, 0), ('dev', 8, 100), ('test', 16, 200)):
        for family in ('arithmetic', 'entity', 'role', 'boolean', 'update', 'copy', 'repeat', 'format'):
            for i in range(count):
                n, ko = offset + i + 1, i % 2 == 0
                a, b = n % 19 + 1, n // 19 + 2
                if family == 'arithmetic':
                    q = f'{a}+{b}의 값만 쓰세요.' if ko else f'What is {a}+{b}? Write only the number.'
                    expected = str(a + b)
                elif family == 'entity':
                    q = (f'A{n}는 사과이고 B{n}는 당근입니다. B{n}는 무엇입니까? 단어만 쓰세요.' if ko else
                         f'A{n} is an apple and B{n} is a carrot. What is B{n}? Write only the noun.')
                    expected = '당근' if ko else 'carrot'
                elif family == 'role':
                    q = (f'민수{n}는 운전하고 영희{n}는 요리합니다. 누가 요리합니까? 이름만 쓰세요.' if ko else
                         f'Alice{n} drives and Bob{n} cooks. Who cooks? Write only the name.')
                    expected = f'영희{n}' if ko else f'Bob{n}'
                elif family == 'boolean':
                    truth = n % 3 != 0
                    q = (f'A{n}=참, B{n}=' + ('참' if truth else '거짓') + f'입니다. A{n} AND B{n}는? 참 또는 거짓만 쓰세요.' if ko else
                         f'A{n}=true, B{n}=' + ('true' if truth else 'false') + f'. What is A{n} AND B{n}? Write true or false.')
                    expected = ('참' if truth else '거짓') if ko else ('true' if truth else 'false')
                elif family == 'update':
                    q = (f'사과가 {a}개 있습니다. {b}개를 더 받았습니다. 지금 개수만 쓰세요.' if ko else
                         f'There are {a} apples. You receive {b} more. Write only the new count.')
                    expected = str(a + b)
                elif family == 'copy':
                    expected = f'key-{n}-value'
                    q = f'다음 문자열을 그대로 복사하세요: {expected}' if ko else f'Copy exactly this string: {expected}'
                elif family == 'repeat':
                    expected = ' '.join([str(n)] * 3)
                    q = f'{n}을 공백으로 구분해 정확히 세 번 쓰세요.' if ko else f'Write {n} exactly three times, separated by spaces.'
                else:
                    expected = json.dumps({'answer': str(a + b)}, separators=(',', ':'))
                    q = (f'{a}+{b}의 값을 문자열로 answer 항목 하나인 JSON으로 쓰세요.' if ko else
                         f'Write {a}+{b} as JSON with only the key answer and a string value.')
                rows.append(dict(id=f'{split}_{family}_{i:03d}', split=split, family=family,
                                 language='ko' if ko else 'en', question=q, expected=expected,
                                 protected=family in ('copy', 'repeat')))
    for i, question in enumerate(OPEN):
        rows.append(dict(id=f'open_{i:03d}', split='open', family='open_manual_review',
                         language='ko' if i < 8 else 'en', question=question,
                         expected=None, protected=i == 15))
    prompts = [row['question'] for row in rows if row['split'] != 'open']
    if len(set(prompts)) != len(prompts):
        raise ValueError('frozen split questions overlap')
    return rows


def locations(tag, model):
    if not re.fullmatch(r'p108w_v[0-9]+_20261104', tag):
        raise ValueError('fresh safe P108 tag required')
    manual.resolve_model(model)
    base = manual.owned_path(f'test_result/evidence/{tag}/{model}')
    runtime = manual.owned_path(f'runs/isolated/{tag}/{model}')
    return base, runtime


def prepare(tag, model):
    base, runtime = locations(tag, model)
    profile_path = base / 'profile.json'
    if base.exists() or runtime.exists():
        raise FileExistsError('new namespace required')
    manifest = manual.verify_manifest()
    data = make_data()
    write_json(base / 'data.json', dict(schema=SCHEMA, rows=data, provenance='NEW_CODE_VERIFIED_PRACTICE_NOT_OFFICIAL_BENCHMARK'))
    snapshot = (ROOT / PLAN_PATH).read_bytes()
    with (base / 'initial_plan.md').open('xb') as stream:
        stream.write(snapshot)
    sources = dict(manual.required_source_pins())
    sources.update({name: manual.file_sha(ROOT / name) for name in SOURCE_PATHS})
    profile = dict(schema=SCHEMA, tag=tag, model=model, authority_directive=107,
        deadline=DEADLINE.isoformat(), sources=sources, data_sha256=manual.file_sha(base / 'data.json'),
        manual_manifest_sha256=manual.canonical_sha(manifest), max_new=96,
        initial_plan_sha256=manual.file_sha(base / 'initial_plan.md'),
        changed_axis='DOWN_WEIGHT_DIRECTION_PROJECTION_ONLY', optimizer_updates=0, training_tokens=0,
        layers=2, columns=32, gains=[.25, .5, 1., 2.], random_seeds=[17, 29, 43],
        precision='FP32_MATH', tf32=False, mtp=False, recurrence='R1', cache=True,
        direction_protocol='OBSERVED_LOOP_IF_AT_LEAST_4_ELSE_FORCED_QUESTION_CYCLE_ORDER_CONTROL',
        direction_limit=32, max_phase_seconds=4800,
        exclusions=['OTHER_SESSION_CLEANING', 'TinyDataset', 'ORIGINAL_WRITES', 'NEW_300M', 'OFFICIAL_EVAL_FOR_SELECTION'])
    write_json(profile_path, profile)
    print('[PREPARED] ' + json.dumps(dict(profile=str(profile_path.relative_to(ROOT)),
        data_rows=len(data), profile_sha256=manual.file_sha(profile_path)), ensure_ascii=False), flush=True)


def verify_profile(base):
    profile = read_json(base / 'profile.json')
    if profile.get('schema') != SCHEMA or profile.get('authority_directive') != 107 or profile['deadline'] != DEADLINE.isoformat():
        raise ValueError('profile authority/schema/deadline differs')
    for path, sha in profile['sources'].items():
        if manual.file_sha(manual.owned_path(path)) != sha:
            raise ValueError('source changed after freeze: ' + path)
    if manual.file_sha(base / 'data.json') != profile['data_sha256']:
        raise ValueError('frozen practice data changed')
    if manual.file_sha(base / 'initial_plan.md') != profile['initial_plan_sha256']:
        raise ValueError('frozen initial protocol snapshot changed')
    if manual.canonical_sha(manual.verify_manifest()) != profile['manual_manifest_sha256']:
        raise ValueError('manual binding changed')
    return profile


class Budget:
    def __init__(self, profile):
        self.start = time.monotonic()
        self.max_sec = profile['max_phase_seconds']

    def check(self):
        if datetime.now(timezone.utc).timestamp() + 180 >= DEADLINE.timestamp():
            raise TimeoutError('authority deadline reserve reached')
        if time.monotonic() - self.start >= self.max_sec:
            raise TimeoutError('phase budget reached')


def evaluate(active, items, writer, variant, budget, limit):
    torch = active['torch']
    outputs = []
    torch.cuda.synchronize()
    start = time.monotonic()
    for i, item in enumerate(items):
        budget.check()
        answer, generation = manual.emit(active, item['question'], max_new=limit)
        ids = generation['generated_ids'][:-len(generation['terminal_ids'])] if generation['terminal_ids'] else generation['generated_ids']
        row = dict(item, variant=variant, answer=answer, generation=generation,
            exact=None if item['expected'] is None else repair.exact_answer(answer, item['expected']),
            diagnostics=repair.repetition_metrics(ids, answer, item['question']))
        writer.append(row)
        outputs.append(row)
        if (i + 1) % 16 == 0:
            print(f'[PROGRESS] {variant} {i + 1}/{len(items)}', flush=True)
    torch.cuda.synchronize()
    summary = repair.summarize(outputs)
    summary.update(seconds=time.monotonic() - start,
                   allocated_peak_bytes=torch.cuda.max_memory_allocated(),
                   reserved_peak_bytes=torch.cuda.max_memory_reserved())
    print('[VARIANT] ' + json.dumps(dict(variant=variant, **summary)), flush=True)
    return outputs, summary


def prompt_ids(active, question):
    from tinylm.chat.serialize import serialize
    text = serialize(dict(messages=manual.prompt_messages(question)), 'chatml', add_generation_prompt=True)
    return active['tokenizer'].encode(text).ids


def collect_directions(active, rows, profile, budget):
    torch, model = active['torch'], active['model']
    observed = [row for row in rows if row['diagnostics']['loop_indicator']]
    use_observed = len(observed) >= 4
    chosen = (observed if use_observed else [r for r in rows if not r['protected']])[:profile['direction_limit']]
    sums, records = {}, []
    gen = random.Random(1337)
    for row in chosen:
        budget.check()
        prefix = prompt_ids(active, row['question'])
        if use_observed:
            body = row['generation']['generated_ids'][-48:]
            body = [v for v in body if v not in (2, 4)]
        else:
            tokens = active['tokenizer'].encode(row['question']).ids
            body = (tokens * (48 // len(tokens) + 1))[:48]
        # Same length, token multiset, last token, and user prompt in both arms.
        interior = list(body[:-8])
        gen.shuffle(interior)
        control = interior + body[-8:]
        captures = []
        for suffix in (body, control):
            ids = torch.tensor([prefix + suffix], device='cuda', dtype=torch.long)
            from torch.nn.attention import sdpa_kernel, SDPBackend
            with torch.no_grad(), sdpa_kernel(SDPBackend.MATH), repair.capture_down(model) as values:
                active['route'].assert_active()
                model(ids, logits_last_only=True)
            captures.append(values)
        for layer, values in captures[0].items():
            other = captures[1][layer]
            if layer not in sums:
                sums[layer] = dict(diff=torch.zeros_like(values['output']),
                                   activity=torch.zeros_like(values['input']), scale=0.)
            sums[layer]['diff'] += values['output'] - other['output']
            sums[layer]['activity'] += values['input'].abs()
            sums[layer]['scale'] += float(values['output'].norm())
        records.append(dict(id=row['id'], generated_natural_loop=use_observed,
            prefix_sha256=manual.canonical_sha(prefix), history_sha256=manual.canonical_sha(body),
            control_sha256=manual.canonical_sha(control), history_tokens=len(body), same_multiset=sorted(body) == sorted(control),
            same_last_token=body[-1:] == control[-1:], same_last_eight=body[-8:] == control[-8:]))
    packed, ranking = {}, []
    for layer, values in sums.items():
        vector = values['diff'] / len(chosen)
        if float(vector.norm()) <= 1e-12:
            continue
        packed[str(layer)] = dict(direction=repair.unit_direction(vector), activity=values['activity'] / len(chosen))
        ranking.append(dict(layer=layer, contrast_norm=float(vector.norm()),
                            relative_contrast=float(vector.norm()) / max(1e-12, values['scale'] / len(chosen))))
    ranking.sort(key=lambda row: (-row['relative_contrast'], row['layer']))
    if len(ranking) < profile['layers']:
        raise ValueError('not enough identifiable layer directions')
    return packed, dict(protocol='OBSERVED_LOOP_ORDER_CONTROL' if use_observed else 'FORCED_QUESTION_CYCLE_ORDER_CONTROL',
                        observed_loop_items=len(observed), contrast_items=len(chosen), records=records,
                        ranking=ranking, selected_layers=[r['layer'] for r in ranking[:profile['layers']]],
                        causal_claim='ORDER_CONTRAST_NOT_PURE_LOOP_FEATURE_PROOF')


def make_edits(active, vectors, direction_report, profile, gain, realization):
    torch = active['torch']
    modules = dict(repair.down_modules(active['model']))
    edits, specs = [], []
    for layer in direction_report['selected_layers']:
        module, values = modules[layer], vectors[str(layer)]
        # Score columns on the EFFECTIVE matrix actually used for inference.
        u = values['direction'].to(module.weight)
        base = module._wq.detach() if realization == 'effective' else module.weight.detach()
        score = (u @ module._wq.detach()).abs() * values['activity'].to(module.weight)
        columns = torch.argsort(score, descending=True, stable=True)[:profile['columns']].cpu().tolist()
        delta = repair.projection_delta(base, u, columns, gain)
        edits.append((layer, delta))
        specs.append(dict(layer=layer, columns=columns, gain=gain, realization=realization,
                          delta_sha256=repair.tensor_sha(delta)))
    return edits, specs


def load_vectors(runtime, torch, report):
    path = runtime / 'directions.pt'
    if manual.file_sha(path) != report['directions_sha256']:
        raise ValueError('direction artifact changed')
    return torch.load(path, map_location='cpu', weights_only=True)


def run(phase, tag, model_name):
    base, runtime = locations(tag, model_name)
    profile = verify_profile(base)
    budget = Budget(profile)
    budget.check()
    if (base / phase).exists():
        raise FileExistsError('phase is write-once; use a fresh stage after changes')
    items = read_json(base / 'data.json')['rows']
    if phase != 'baseline' and not (base / 'baseline' / 'report.json').is_file():
        raise ValueError('baseline receipt missing')
    writer = ShardWriter(base / phase, 'answers', limit=3_000_000)
    final = dict(schema=SCHEMA, phase=phase, profile_sha256=manual.file_sha(base / 'profile.json'),
                 authority_directive=107, variants=[], training_tokens=0, optimizer_updates=0)
    with manual.selected_runtime(manual.resolve_model(model_name)) as active:
        torch = active['torch']
        torch.set_num_threads(4)
        torch.cuda.reset_peak_memory_stats()
        final['origin'] = {k: active[k] for k in ('name', 'checkpoint', 'checkpoint_sha256', 'core_sha256',
                                                'manifest_sha256', 'tokenizer_sha256', 'precision', 'quantization_route')}
        if phase == 'baseline':
            selected = [r for r in items if r['split'] == 'repair']
            # Verify GPU no-op in both routes before any nonzero intervention.
            original, original_meta = manual.emit(active, selected[0]['question'], max_new=profile['max_new'])
            noop = []
            module = repair.down_modules(active['model'])[0][1]
            for realization in ('effective', 'latent'):
                with repair.edit_weights(active['model'], active['route'], [(0, torch.zeros_like(module.weight))], realization) as receipt:
                    text, metadata = manual.emit(active, selected[0]['question'], max_new=profile['max_new'])
                exact = text == original and metadata['generated_ids'] == original_meta['generated_ids']
                if not exact:
                    raise RuntimeError('GPU no-op generated sequence changed')
                noop.append(dict(realization=realization, sequence_exact=exact, receipts=receipt))
            final['noop'] = noop
            rows, summary = evaluate(active, selected, writer, 'original_repair', budget, profile['max_new'])
            final['variants'].append(dict(name='original_repair', **summary))
            vectors, direction_report = collect_directions(active, rows, profile, budget)
            runtime.mkdir(parents=True, exist_ok=False)
            with (runtime / 'directions.pt').open('xb') as stream:
                torch.save(vectors, stream)
            final.update(direction_report=direction_report, directions_sha256=manual.file_sha(runtime / 'directions.pt'))
        elif phase == 'search':
            previous = read_json(base / 'baseline' / 'report.json')
            vectors = load_vectors(runtime, torch, previous)
            direction_report = previous['direction_report']
            selected = [r for r in items if r['split'] == 'dev']
            _, summary = evaluate(active, selected, writer, 'original_dev', budget, profile['max_new'])
            final['variants'].append(dict(name='original_dev', **summary))
            candidates = []
            for realization in ('effective', 'latent'):
                for gain in profile['gains']:
                    name = f'{realization}_g{gain}'
                    edits, specs = make_edits(active, vectors, direction_report, profile, gain, realization)
                    with repair.edit_weights(active['model'], active['route'], edits, realization) as receipts:
                        _, summary = evaluate(active, selected, writer, name, budget, profile['max_new'])
                    candidate = dict(name=name, **summary, realization=realization, gain=gain,
                                     specs=specs, receipts=receipts)
                    final['variants'].append(candidate)
                    candidates.append(candidate)
            def score(row):
                return (row['exact'], row['protected_exact'], -row['empty'], -row['question_echoes'],
                        -row['loop_indicators'], -sum(r['effective_delta_norm'] for r in row['receipts']))
            winner = max(candidates, key=score)
            final['selected'] = dict(name=winner['name'], realization=winner['realization'], gain=winner['gain'],
                                     selection_split='DEV_ONLY', criterion='EXACT_PROTECTED_EMPTY_ECHO_LOOP_DELTA')
        elif phase == 'confirm':
            previous = read_json(base / 'baseline' / 'report.json')
            search = read_json(base / 'search' / 'report.json')
            vectors = load_vectors(runtime, torch, previous)
            selected = [r for r in items if r['split'] in ('test', 'open')]
            _, summary = evaluate(active, selected, writer, 'original_test', budget, profile['max_new'])
            final['variants'].append(dict(name='original_test', **summary))
            winner = search['selected']
            edits, specs = make_edits(active, vectors, previous['direction_report'], profile, winner['gain'], winner['realization'])
            with repair.edit_weights(active['model'], active['route'], edits, winner['realization']) as receipts:
                _, summary = evaluate(active, selected, writer, 'targeted_test', budget, profile['max_new'])
                actual_deltas = [(layer, module._wq.detach().clone()) for layer, module in repair.down_modules(active['model'])
                                 if layer in {index for index, _ in edits}]
            modules = dict(repair.down_modules(active['model']))
            norms = {layer: float((actual - modules[layer]._wq.detach()).norm()) for layer, actual in actual_deltas}
            final['variants'].append(dict(name='targeted_test', **summary, specs=specs, receipts=receipts))
            for seed in profile['random_seeds']:
                random_edits = [(s['layer'], repair.matched_random_delta(modules[s['layer']]._wq.detach(),
                    s['columns'], norms[s['layer']], seed + s['layer'])) for s in specs]
                with repair.edit_weights(active['model'], active['route'], random_edits, 'effective') as controls:
                    _, summary = evaluate(active, selected, writer, f'random_{seed}_test', budget, profile['max_new'])
                final['variants'].append(dict(name=f'random_{seed}_test', **summary, receipts=controls,
                    matching='PER_LAYER_EFFECTIVE_FROBENIUS_NORM_SAME_SELECTED_COLUMNS',
                    caveat='LATENT_TARGET_MAY_CHANGE_GROUP_COLUMNS_OUTSIDE_REQUESTED_SUPPORT'))
            final['selected'] = winner
            final['selection_report_sha256'] = manual.file_sha(base / 'search' / 'report.json')
        else:
            raise ValueError('unknown GPU phase')
        final['vram'] = dict(torch_allocated_peak_bytes=torch.cuda.max_memory_allocated(),
                             torch_reserved_peak_bytes=torch.cuda.max_memory_reserved(),
                             global_free_bytes=torch.cuda.mem_get_info()[0], scope='TORCH_PROCESS_PEAK_AND_GLOBAL_POINT')
    # Strict runtime exits only after registered original core/source equality.
    verify_profile(base)
    final['original_registered_core_unchanged'] = True
    manifest = writer.close(lineage=dict(profile_sha256=final['profile_sha256'],
        checkpoint_sha256=final['origin']['checkpoint_sha256'], phase=phase))
    verify_shards(base / phase, manifest)
    final['answers_manifest_sha256'] = manual.file_sha(base / phase / 'answers_shards_manifest.json')
    final['wall_seconds'] = time.monotonic() - budget.start
    final['status'] = 'TECHNICAL_COMPLETE_QUALITY_SEPARATE'
    write_json(base / phase / 'report.json', final)
    print('[FINAL] ' + json.dumps(final, ensure_ascii=False), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=('prepare', 'baseline', 'search', 'confirm'))
    parser.add_argument('tag')
    parser.add_argument('model', choices=tuple(s.name for s in manual.MODELS))
    args = parser.parse_args()
    if args.phase == 'prepare':
        prepare(args.tag, args.model)
        return 0
    try:
        run(args.phase, args.tag, args.model)
    except TimeoutError as exc:
        print('[HOLD] ' + str(exc), flush=True)
        return 8
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
