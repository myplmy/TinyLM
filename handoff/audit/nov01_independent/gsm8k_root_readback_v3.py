"""공식 GSM8K 전량의 실제 ID·원문·공식 필터·집계를 독립 재구성한다. CPU 전용."""
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
os.environ.update(CUDA_VISIBLE_DEVICES='', HF_HUB_OFFLINE='1', HF_DATASETS_OFFLINE='1',
                  TRANSFORMERS_OFFLINE='1', USE_HUB_KERNELS='0')
from scripts import diag_p106b_official_gsm8k as driver
from scripts import p106b_official_gsm8k as data
from scripts import interactive_research_infer as manual

PROFILE_SHA = '0EFFADD069945BEEE4739F4BCCD5D220D2348119FEA3329DBB1E0659A86A46F9'
READBACK = driver.OUTPUT / 'readback_v3'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def shards(folder, manifest):
    rows, content, size = [], hashlib.sha256(), 0
    for spec in manifest['shards']:
        path = folder / spec['path']
        raw = path.read_bytes()
        assert digest(path) == spec['sha256'] and len(raw) == spec['bytes'] < 20_000_000
        records = [json.loads(line) for line in raw.splitlines()]
        assert len(records) == spec['rows']
        rows.extend(records)
        size += len(raw)
        content.update(raw)
    assert len(rows) == manifest['rows'] and size == manifest['bytes']
    assert content.hexdigest().upper() == manifest['concat_sha256']
    return rows


def one(arm):
    assert arm in driver.ARMS
    model = driver.ARMS[arm]
    assert digest(driver.PROFILE) == PROFILE_SHA
    profile = json.loads(driver.PROFILE.read_text())
    assert profile['source'] == driver.identity() and profile['policy'] == driver.policy()
    folder = driver.OUTPUT / model / 'full'
    report = json.loads((folder / 'report.json').read_text())
    assert report['status'] == 'OFFICIAL_GSM8K_FULL_COMPLETE' and report['final_exit'] == 0
    assert report['source'] == profile['source'] and report['profile_sha256'] == PROFILE_SHA
    assert report['actual_rows'] == 1319 and report['model'] == model
    assert report['policy'] == profile['policy'] and report['model_metadata'] == profile['models'][model]
    assert report['source_unchanged'] and report['parent_unchanged'] and report['assets_unchanged']
    assert not report['final_verification_errors'] and report['vram_watch']['reason'] is None
    assert report['vram_watch']['thread_stopped'] and report['vram_watch']['client']['closed']
    assert report['vram_watch']['maximum_additional_bytes'] <= 8_000_000_000
    assert report['peak_reserved_bytes'] <= 6 * 2**30
    assert report['final_cuda_cleanup']['allocated_bytes'] == report['final_cuda_cleanup']['reserved_bytes'] == 0
    assert report['training'] == report['checkpoint_writes'] == 0
    assert all(row['float_close'] for row in report['cache_canary'])
    assert digest(ROOT / profile['models'][model]['checkpoint']) == profile['models'][model]['checkpoint_sha256']
    assert all(row['close'] for row in report['numerical_canary'])
    generations = shards(folder / 'generation', report['generation'])
    samples = shards(folder / 'samples', report['samples'])
    assert len(generations) == 1319 and len(samples) == 2638
    assert [row['doc_id'] for row in generations] == list(range(1319))
    task, assets = data.load_task()
    task.build_all_requests(limit=None, rank=0, world_size=1, cache_requests=False,
        rewrite_requests_cache=False, system_instruction=None, apply_chat_template=False, fewshot_as_multiturn=False)
    requests = task.instances
    assert len(requests) == 1319
    tokenizer = manual.local_tokenizer(manual.verify_manifest())
    vocab_size = tokenizer.get_vocab_size()
    from lm_eval.models.utils import postprocess_generated_text
    finishes, generated_tokens, prompt_tokens = Counter(), 0, 0
    originals = list(task.eval_docs)
    for index, (request, row, case) in enumerate(zip(requests, generations, profile['cases'])):
        assert request.doc_id == row['doc_id'] == case['doc_id'] == index
        context, kwargs = request.args
        assert request.doc == originals[index] and kwargs == case['generation_kwargs']
        assert hashlib.sha256(context.encode()).hexdigest().upper() == case['prompt_sha256'] == row['prompt_sha256']
        ids = tokenizer.encode(context, add_special_tokens=False).ids
        prefix = ids[-768:]
        meta = row['metadata']
        assert meta['actual_prefix_ids'] == prefix and len(ids) == case['original_prompt_tokens']
        assert len(prefix) == case['kept_prompt_tokens'] and len(ids)-len(prefix) == case['removed_prompt_tokens']
        assert meta['use_cache'] and not meta['mtp'] and meta['precision'] == 'FP32_MATH'
        assert meta['max_context'] == 1024 and meta['temperature'] == 0 and meta['top_k'] == 1
        generated = meta['generated_ids']
        assert len(generated) == meta['generated_tokens'] and 1 <= len(generated) <= 256
        assert all(type(value) is int and 0 <= value < vocab_size for value in generated)
        reason, terminal = meta['finish_reason'], meta['terminal_ids']
        if reason == 'MAX_NEW':
            assert len(generated) == 256 and terminal == [] and meta['matched_stop_sequence'] is None
        elif reason == 'EOS':
            assert terminal == [2] and generated[-1] == 2 and meta['matched_stop_sequence'] is None
        else:
            assert reason == 'STOP_SEQUENCE' and terminal == [4] and generated[-1] == 4
            assert meta['matched_stop_sequence'] == [4]
        content = generated[:-1] if terminal else generated
        assert not any(value in (2,4) for value in content)
        raw = tokenizer.decode(content, skip_special_tokens=True)
        assert raw == meta['raw_decoded_generation']
        _, stops = data.options(kwargs, eos=tokenizer.decode([2]))
        assert stops == meta['until']
        answer = postprocess_generated_text(generation=raw, stop=stops, think_end_token=None)
        assert answer == row['answer'] and row['role'] == 'OFFICIAL_TEST_GENERATION_NEVER_TRAIN'
        request.resps = [answer]
        finishes[reason] += 1
        generated_tokens += len(generated)
        prompt_tokens += len(prefix)
    task.apply_filters()
    counts = {'strict-match':0, 'flexible-extract':0}
    saved = {(row['doc_id'],row['filter']):row for row in samples}
    assert len(saved) == 2638
    decisions = []
    for index, request in enumerate(requests):
        decision = dict(doc_id=index, gold=originals[index]['answer'], filters={})
        assert set(request.filtered_resps) == set(counts)
        for name, answer in request.filtered_resps.items():
            row = saved[(index,name)]
            assert row['doc'] == originals[index] and row['filtered_resps'] == [answer]
            actual = float(task.process_results(originals[index], [answer])['exact_match'])
            assert actual in (0,1) and float(row['exact_match']) == actual
            counts[name] += int(actual)
            decision['filters'][name] = dict(extracted=answer, correct=int(actual))
        decisions.append(decision)
    for name, correct in counts.items():
        assert correct == report['audits'][name]['correct']
        assert math.isclose(correct/1319, report['official_result']['exact_match,' + name], abs_tol=1e-12)
    assert report['generated_tokens'] == generated_tokens
    suffix = 'Wa' if arm == 'native' else 'Wb'
    raw = ROOT / ('test_result/101_log_20261101_P106B_Stage8z'+suffix+'_gsm8k_'+arm+'_full.txt')
    text = raw.read_text()
    assert '[runlog] 종료코드 0' in text and 'actual_exit=0;' in text
    assert '[BODY_UNCHANGED] '+profile['models'][model]['core_sha256'] in text
    result = dict(schema='GSM8K_OFFICIAL_FULL_ROOT_READBACK_V3',
        checked_at=datetime.now(timezone.utc).isoformat(), model=model, rows=1319,
        official_prompts_reconstructed=1319, actual_prefix_and_generation_redecoded=1319,
        official_filter_rows_recomputed=2638, correct=counts,
        metrics={name:correct/1319 for name,correct in counts.items()}, finishes=dict(finishes),
        generated_tokens=generated_tokens, actual_prompt_tokens=prompt_tokens,
        report_sha256=digest(folder/'report.json'), raw_log_sha256=digest(raw), profile_sha256=PROFILE_SHA,
        auditor_sha256=digest(Path(__file__)), official_revision=assets['revision'],
        telemetry_query_errors=report['vram_watch']['query_errors'],
        scope='FULL_OFFICIAL_SCORE_WITH_DISCLOSED_1024_CONTEXT_TRUNCATION',
        new_training=0, benchmark_train_or_teacher_reuse=False, all_pretraining_contamination='UNKNOWN',
        decisions=decisions, errors=[])
    READBACK.mkdir(exist_ok=True)
    output = READBACK / ('gsm8k_'+arm+'_full_readback_v3.json')
    with output.open('x') as stream:
        json.dump(result,stream,ensure_ascii=False,indent=2)
        stream.write(chr(10))
    assert output.stat().st_size < 20_000_000
    print(json.dumps(dict(model=model,rows=1319,correct=counts,errors=[])))


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('native 또는 broad 필요')
    one(sys.argv[1])
