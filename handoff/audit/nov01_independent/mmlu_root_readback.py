"""완료 MMLU 전량만 원문/공식요청/label/우도에서 재집계한다. CPU·읽기+새 감사만."""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
os.environ.update(CUDA_VISIBLE_DEVICES='', HF_HUB_OFFLINE='1', HF_DATASETS_OFFLINE='1', TRANSFORMERS_OFFLINE='1')
from scripts import p106b_official_mmlu as data
from scripts.diag_p106b_official_mmlu import identity, policy

PROFILE_SHA = 'A2DA0A92D7B9E9264F7D558B581D50F36FA39E313FABD3152F56718C87CBCBFB'
AUDIT = ROOT / 'handoff/audit/nov01_independent'
READBACK = data.OUTPUT / 'readback'


def sha(path):
    return data.digest(path)


def read(path):
    return json.loads(path.read_text())


def shards(folder, manifest):
    raw = hashlib.sha256()
    rows = []
    size = 0
    for item in manifest['shards']:
        path = folder / item['path']
        part = path.read_bytes()
        assert len(part) == item['bytes'] < 20_000_000 and sha(path) == item['sha256']
        records = [json.loads(line) for line in part.splitlines()]
        assert len(records) == item['rows']
        raw.update(part)
        size += len(part)
        rows.extend(records)
    assert len(rows) == manifest['rows'] and size == manifest['bytes']
    assert raw.hexdigest().upper() == manifest['concat_sha256']
    return rows


def one(model, shot):
    assert model in data.MODELS and shot in (0, 5)
    profile = read(data.CACHE / 'profile_v2.json')
    assert sha(data.CACHE / 'profile_v2.json') == PROFILE_SHA and profile['source'] == identity()
    tasks, assets, framework = data.load_tasks(shot)
    folder = data.OUTPUT / model / ('shot' + str(shot)) / 'full'
    path = folder / 'report.json'
    report = read(path)
    assert report['status'] == 'OFFICIAL_MMLU_FULL_COMPLETE' and report['final_exit'] == 0
    assert report['actual_rows'] == 14042 and report['source'] == profile['source']
    assert report['model'] == model and report['shots'] == shot and report['profile_sha256'] == PROFILE_SHA
    assert report['policy'] == policy(shot) and report['model_metadata'] == profile['models'][model]
    assert report['framework'] == framework and report['dataset_revision'] == data.REVISION
    assert report['source_unchanged'] and report['parent_unchanged'] and report['original_assets_unchanged']
    assert report['final_verification_errors'] == []
    assert report['resource_limit_bytes'] == 8_000_000_000 and report['training'] == report['checkpoint_writes'] == 0
    assert report['peak_reserved_bytes'] <= 6 * 2**30
    assert report['final_cuda_cleanup']['allocated_bytes'] == report['final_cuda_cleanup']['reserved_bytes'] == 0
    assert report['vram_watch']['query_errors'] == 0 and report['vram_watch']['reason'] is None
    assert report['vram_watch']['maximum_additional_bytes'] <= 8_000_000_000
    assert all(row['close'] for row in report['numerical_canary'])
    assert sha(ROOT / profile['models'][model]['checkpoint']) == profile['models'][model]['checkpoint_sha256']
    assert set(report['samples']) == set(report['audits']) == set(tasks)
    answers, counts = [], {}
    official_args_verified = 0
    for name, task in tasks.items():
        rows = shards(folder / 'samples' / name, report['samples'][name])
        assert len(rows) == len(task.eval_docs) and [row['doc_id'] for row in rows] == list(range(len(rows)))
        correct, labels, predictions = 0, Counter(), Counter()
        for index, row in enumerate(rows):
            doc = task.eval_docs[index]
            assert row['doc'] == doc and row['filter'] == 'none'
            expected = [list(request.args) for request in data.requests(task, doc, shot, index)]
            assert row['arguments'] == expected
            official_args_verified += 4
            values = row['filtered_resps']
            assert len(values) == 4 and all(len(v) == 2 and math.isfinite(v[0]) and v[0] <= 0 for v in values)
            prediction = max(range(4), key=lambda i:values[i][0])
            gold = doc['answer']
            hit = int(prediction == gold)
            assert row['acc'] == hit
            correct += hit
            labels[gold] += 1
            predictions[prediction] += 1
            answers.append(dict(subject=doc['subject'], doc_id=index, gold=gold, prediction=prediction, correct=hit))
        assert correct == report['audits'][name]['correct']
        assert labels == Counter({int(k):v for k,v in report['audits'][name]['labels'].items()})
        assert predictions == Counter({int(k):v for k,v in report['audits'][name]['predictions'].items()})
        assert math.isclose(report['official_results'][name]['acc,none'], correct / len(rows), abs_tol=1e-12)
        counts[name] = dict(rows=len(rows), correct=correct, labels=dict(labels), predictions=dict(predictions))
    assert len(answers) == 14042 and official_args_verified == 56168
    total = sum(value['correct'] for value in counts.values())
    assert math.isclose(report['weighted_accuracy'], total / 14042, abs_tol=1e-12)
    lengths = shards(folder / 'lengths', report['lengths_manifest'])
    actual = dict(requests=len(lengths), input_positions=sum(row['context_tokens'] + row['continuation_tokens']
                  - 1 - row['truncated_context_tokens'] for row in lengths),
        truncated_requests=sum(row['truncated_context_tokens'] > 0 for row in lengths),
        removed_context_tokens=sum(row['truncated_context_tokens'] for row in lengths))
    declared = profile['shots'][str(shot)]
    assert all(actual[key] == declared[key] for key in actual)
    assert actual['input_positions'] == report['scored_input_positions']
    suffix = ('We' if model == 'native595-q' else 'Wf') if shot == 0 else ('Wg' if model == 'native595-q' else 'Wh')
    arm = ('native' if model == 'native595-q' else 'broad') + str(shot)
    raw = ROOT / ('test_result/101_log_20261101_P106B_Stage8w' + suffix + '_mmlu_' + arm + '_full.txt')
    text = raw.read_text()
    assert '[runlog] 종료코드 0' in text and 'actual_exit=0;' in text
    assert '[BODY_UNCHANGED] ' + profile['models'][model]['core_sha256'] in text
    result = dict(schema='MMLU_FULL_INDEPENDENT_ROOT_READBACK_V1', checked_at=datetime.now(timezone.utc).isoformat(),
        model=model, shots=shot, rows=14042, official_arguments_reconstructed=official_args_verified,
        report_sha256=sha(path), raw_log_sha256=sha(raw), profile_sha256=PROFILE_SHA,
        correct=total, accuracy=total / 14042, counts=counts, predictions=answers,
        token_lengths=actual, source_unchanged=True, parent_unchanged=True, new_training=0,
        auditor_sha256=sha(Path(__file__)),
        official_metric='DEFAULT_LETTER_MC_ACC_SIZE_WEIGHTED_1024_CONTEXT', errors=[])
    READBACK.mkdir(exist_ok=True)
    out = READBACK / ('mmlu_' + arm + '_full_readback_v1.json')
    with out.open('x') as stream:
        json.dump(result, stream, ensure_ascii=False, sort_keys=True, indent=2)
        stream.write(chr(10))
    print(json.dumps(dict(model=model, shots=shot, correct=total, rows=14042, official_args=56168, errors=[])))


def compare():
    import numpy as np
    baseline = read(AUDIT / 'mmlu_pre_model_baselines_v1.json')
    names = ['native0', 'broad0', 'native5', 'broad5']
    inputs = {name:read(READBACK / ('mmlu_' + name + '_full_readback_v1.json')) for name in names}
    arrays = {name:{subject:np.asarray([r['prediction'] for r in value['predictions'] if r['subject'] == subject], dtype=np.int64)
        for subject in baseline['subjects']} for name,value in inputs.items()}
    truth = {subject:np.asarray([r['gold'] for r in inputs['native0']['predictions'] if r['subject'] == subject], dtype=np.int64)
             for subject in baseline['subjects']}
    for name,value in inputs.items():
        assert [(r['subject'],r['doc_id'],r['gold']) for r in value['predictions']] == [
            (r['subject'],r['doc_id'],r['gold']) for r in inputs['native0']['predictions']]
    repeats = baseline['planned_label_permutation']['repeats']
    assert repeats == 2000
    null = {name:np.zeros(repeats, dtype=np.int64) for name in names}
    for subject in sorted(truth):
        label = truth[subject]
        seed = baseline['planned_label_permutation']['seed'] + int(hashlib.sha256(subject.encode()).hexdigest()[:8], 16)
        rng = np.random.default_rng(seed)
        shuffled = rng.permuted(np.broadcast_to(label, (repeats, len(label))), axis=1)
        for name in names:
            null[name] += (shuffled == arrays[name][subject]).sum(axis=1)
    result = {}
    for name,value in inputs.items():
        values = null[name]
        result[name] = dict(correct=value['correct'], rows=14042, accuracy=value['accuracy'],
            uniform_expectation=.25, posthoc_global_majority_accuracy=baseline['posthoc_global_majority_accuracy'],
            excess_over_posthoc_global_majority=value['accuracy'] - baseline['posthoc_global_majority_accuracy'],
            conditional_permutation=dict(repeats=repeats, minimum=int(values.min()), maximum=int(values.max()),
                mean=float(values.mean()), sd=float(values.std(ddof=1)), interval95_correct=[float(v) for v in np.quantile(values,[.025,.975])],
                exploratory_upper_tail=(1 + int((values >= value['correct']).sum())) / (1 + repeats),
                scope='CONDITIONAL_WITHIN_SUBJECT_LABEL_ASSOCIATION_NOT_GENERAL_INTELLIGENCE'))
    pairs = {}
    for left,right in [('native0','broad0'),('native5','broad5'),('native0','native5'),('broad0','broad5')]:
        a = np.asarray([r['correct'] for r in inputs[left]['predictions']])
        b = np.asarray([r['correct'] for r in inputs[right]['predictions']])
        pairs[left + '_to_' + right] = dict(rows=14042, gain=int(((a == 0) & (b == 1)).sum()),
            loss=int(((a == 1) & (b == 0)).sum()), both_correct=int(((a == 1) & (b == 1)).sum()),
            delta_accuracy=float((b - a).mean()), scope='PAIRED_FIXED_TEST_DESCRIPTIVE_NOT_SINGLE_METHOD_CAUSAL_EFFECT')
    payload = dict(schema='MMLU_FOUR_RUN_FROZEN_ROOT_COMPARISON_V1', rows_per_run=14042, runs=result,
        paired=pairs, benchmark_training_or_teacher_reuse=False, all_pretraining_contamination='UNKNOWN',
        uniform_and_posthoc_majority_are_diagnostics=True, new_intelligence_gain_claim=False,
        original_reports_preserved=True, conditional_permutation_protocol=baseline['planned_label_permutation'],
        auditor_sha256=sha(Path(__file__)), errors=[])
    with (READBACK / 'mmlu_four_run_comparison_v1.json').open('x') as stream:
        json.dump(payload, stream, ensure_ascii=False, sort_keys=True, indent=2)
        stream.write(chr(10))
    print(json.dumps(dict(runs=result, paired=pairs), ensure_ascii=False))


if __name__ == '__main__':
    if len(sys.argv) == 2 and sys.argv[1] == 'compare':
        compare()
    elif len(sys.argv) == 3:
        one(sys.argv[1], int(sys.argv[2]))
    else:
        raise SystemExit('모델명 shot 또는 compare 필요')
