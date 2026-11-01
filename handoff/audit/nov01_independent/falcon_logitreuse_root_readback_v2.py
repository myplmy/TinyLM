"""완료한 Falcon MMLU만 공식 원문·요청·점수에서 독립 재집계한다. CPU 전용."""
from collections import Counter
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
os.environ.update(CUDA_VISIBLE_DEVICES='', HF_HUB_OFFLINE='1', HF_DATASETS_OFFLINE='1',
                  TRANSFORMERS_OFFLINE='1', USE_HUB_KERNELS='0')
from scripts.prepare_p106b_official_eval import configure_hf_cache
configure_hf_cache()
from scripts.diag_p106b_falcon_logitreuse import base as driver
from scripts import p106b_official_mmlu as data
from scripts.diag_p106b_falcon_logitreuse import policy

AUDIT = Path(__file__).parent
PROFILE = ROOT/'data_cache/p106b_falcon_logitreuse_v1_20261101/profile.json'
PROFILE_SHA = 'A81C7258C81976B7CCE68C6E3E13835E4A18D22F6F3A6EB17EE0D0E640E14621'
spec = importlib.util.spec_from_file_location('completed_mmlu_root', AUDIT/'mmlu_root_readback_v3.py')
prior = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prior)


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def one(shot):
    assert shot in (0,5)
    from lm_eval.models.utils import Collator
    import inspect,sysconfig
    from scripts.p106b_official_archive import verify_files
    from scripts.p106b_official_lm_adapter import SOURCE,MANIFEST
    collator=read(AUDIT/'FALCON_LOGITREUSE_COLLATOR_ARCHIVE_v1.json')
    runtime=Path(sysconfig.get_paths()['purelib'])
    actual=Path(inspect.getsourcefile(Collator))
    assert actual==runtime/'lm_eval/models/utils.py'
    assert data.digest(actual)==collator['actual_collator_sha256']
    check=verify_files(['lm_eval/models/utils.py'],archive=Path(read(MANIFEST)['archive_path']),source=SOURCE,runtime=runtime)
    assert check['files']==collator['files'] and check['runtime_matches']
    profile = read(PROFILE)
    assert data.digest(PROFILE) == PROFILE_SHA and profile['source'] == driver.identity()
    assert profile['models'] == driver.model_assets() and profile['runtime'] == driver.runtime_proof()
    folder = driver.OUTPUT/('shot'+str(shot))/'full'
    path = folder/'report.json'
    report = read(path)
    assert report['status'] == 'OFFICIAL_MMLU_FULL_COMPLETE' and report['final_exit'] == 0
    assert report['actual_rows'] == 14042 and report['source'] == profile['source']
    assert report['model'] == 'falcon90m' and report['shots'] == shot and report['profile_sha256'] == PROFILE_SHA
    assert report['policy'] == policy(shot) and report['model_metadata'] == profile['models']
    assert report['source_unchanged'] and report['assets_unchanged'] and not report['final_verification_errors']
    proof = report['model_proof']
    assert proof['initial_core_sha256'] == proof['final_core_sha256'] and proof['source_assets_unchanged']
    assert proof['model_source_sha256'] == profile['runtime']['model_implementation_sha256']
    assert report['training'] == report['checkpoint_writes'] == 0
    assert report['resource_limit_bytes'] == 8_000_000_000
    assert report['peak_reserved_bytes'] <= report['torch_allocator_cap_bytes'] == 6*2**30
    assert report['scorer_seconds'] > 0 and report['completed_forward_batches'] > 0
    assert report['final_cuda_cleanup']['allocated_bytes'] == report['final_cuda_cleanup']['reserved_bytes'] == 0
    watch = report['vram_watch']
    assert watch['reason'] is None and watch['thread_stopped'] and watch['client']['closed']
    assert watch['maximum_additional_bytes'] <= 8_000_000_000
    assert type(watch['query_errors']) is int and watch['query_errors'] >= 0
    assert all(row['close'] for row in report['numerical_canary'])
    tasks, assets, framework = data.load_tasks(shot)
    assert report['framework'] == framework and set(report['samples']) == set(report['audits']) == set(tasks)
    counts, decisions, verified = {}, [], 0
    for name,task in tasks.items():
        rows = prior.shards(folder/'samples'/name, report['samples'][name])
        assert len(rows) == len(task.eval_docs) and [r['doc_id'] for r in rows] == list(range(len(rows)))
        labels, predictions, correct = Counter(), Counter(), 0
        for index,row in enumerate(rows):
            doc = task.eval_docs[index]
            assert row['doc'] == doc and row['filter'] == 'none'
            assert row['arguments'] == [list(r.args) for r in data.requests(task,doc,shot,index)]
            verified += 4
            values = row['filtered_resps']
            assert len(values) == 4 and all(len(v)==2 and math.isfinite(v[0]) and v[0]<=0 for v in values)
            prediction = max(range(4),key=lambda i:values[i][0])
            gold = doc['answer'];hit = int(prediction==gold)
            assert row['acc'] == hit
            labels[gold] += 1;predictions[prediction] += 1;correct += hit
            decisions.append(dict(subject=doc['subject'],doc_id=index,gold=gold,prediction=prediction,correct=hit))
        assert correct == report['audits'][name]['correct']
        assert labels == Counter({int(k):v for k,v in report['audits'][name]['labels'].items()})
        assert predictions == Counter({int(k):v for k,v in report['audits'][name]['predictions'].items()})
        assert math.isclose(report['official_results'][name]['acc,none'],correct/len(rows),abs_tol=1e-12)
        counts[name] = dict(rows=len(rows),correct=correct,labels=dict(labels),predictions=dict(predictions))
    assert len(decisions) == 14042 and verified == 56168
    from transformers import AutoTokenizer
    tokenizer=AutoTokenizer.from_pretrained(str(driver.old.FALCON),local_files_only=True,trust_remote_code=False)
    proxy=driver.tokenizer_only(tokenizer)
    contexts=set()
    for name,task in tasks.items():
        for index,doc in enumerate(task.eval_docs):
            for request in data.requests(task,doc,shot,index):
                context,continuation=proxy._encode_pair(*request.args)
                assert len(continuation)==1
                contexts.add(tuple(context))
    shapes=report['batch_shape_counts']
    forwards=sum(shapes.values());submitted=0
    for shape,number in shapes.items():
        n,t=map(int,shape.split('x'))
        assert 0<n<=4 and t<=1024 and n*t<=4096
        submitted+=n*number
    assert submitted==len(contexts) and forwards==math.ceil(len(contexts)/4)==report['completed_forward_batches']
    assert report['policy']['logits_cache'] is True
    assert report['model_proof']['official_context_logit_reuse_enabled'] is True
    correct = sum(r['correct'] for r in counts.values())
    assert math.isclose(report['weighted_accuracy'],correct/14042,abs_tol=1e-12)
    lengths = prior.shards(folder/'lengths', report['lengths_manifest'])
    observed = dict(requests=len(lengths),
        input_positions=sum(r['context_tokens']+r['continuation_tokens']-1-r['truncated_context_tokens'] for r in lengths),
        truncated_requests=sum(r['truncated_context_tokens']>0 for r in lengths),
        removed_context_tokens=sum(r['truncated_context_tokens'] for r in lengths))
    assert all(v == profile['shots'][str(shot)][k] for k,v in observed.items())
    assert observed['input_positions'] == report['scored_input_positions']
    assert shot==0
    suffix = 'Wa'
    raw = ROOT/('test_result/101_log_20261101_P106B_Stage14g'+suffix+'_mmlu_falcon'+str(shot)+'_logitreuse_full.txt')
    text = raw.read_text()
    assert '[runlog] 종료코드 0' in text and 'actual_exit=0;' in text
    result = dict(schema='FALCON_LOGITREUSE_MMLU_FULL_ROOT_READBACK_V2',checked_at=datetime.now(timezone.utc).isoformat(),
        model='falcon90m',shots=shot,rows=14042,official_arguments_reconstructed=verified,
        correct=correct,accuracy=correct/14042,official_context_logit_reuse=True,grouped_forward_contexts=len(contexts),forward_batches=forwards,counts=counts,predictions=decisions,token_lengths=observed,
        report_sha256=data.digest(path),raw_log_sha256=data.digest(raw),profile_sha256=PROFILE_SHA,
        dataset_revision=data.REVISION,model_assets_rehashed=True,model_state_fingerprint_unchanged=True,
        telemetry_query_errors=watch['query_errors'],telemetry_scope='SAMPLED_NOT_EXACT_PEAK',
        auditor_sha256=data.digest(Path(__file__)),reused_shard_verifier_sha256=data.digest(AUDIT/'mmlu_root_readback_v3.py'),
        new_training=0,benchmark_train_or_teacher_reuse=False,all_pretraining_contamination='UNKNOWN',errors=[])
    out = driver.OUTPUT/'readback';out.mkdir(exist_ok=True)
    with (out/('mmlu_falcon'+str(shot)+'_full_readback_v2.json')).open('x') as f:
        json.dump(result,f,ensure_ascii=False,indent=2)
        f.write(chr(10))
    print(json.dumps(dict(model='falcon90m',shots=shot,rows=14042,correct=correct,official_args=verified,errors=[])))


if __name__ == '__main__':
    assert len(sys.argv)==2
    one(int(sys.argv[1]))
