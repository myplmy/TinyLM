"""One-shot readback of actual83799 closure; never execute a model."""
from pathlib import Path
import hashlib
import json
import statistics

ROOT=Path(__file__).resolve().parents[3]
AUDIT=Path(__file__).parent
BASE=ROOT/'test_result/evidence/p106b_hf_resources_v2_20261027'


def ref(path):
    path=Path(path)
    return dict(path=str(path.relative_to(ROOT)),bytes=path.stat().st_size,
        sha256=hashlib.sha256(path.read_bytes()).hexdigest().upper())


def load(path):
    return json.loads(Path(path).read_text())


def write(name,value):
    with (AUDIT/name).open('x',encoding='utf-8') as stream:
        json.dump(value,stream,ensure_ascii=False,indent=2);stream.write(chr(10))


def main():
    profile_path=AUDIT/'hf_resource_recovery_profile_v1.json'
    profile=load(profile_path); lanes=[];cases=[]
    names=['gemma270_cuda_probe']+[m+'_'+device for device in ('cuda','cpu') for m in ('falcon90m','gemma270','qwen06','gemma1b')]
    for name in names:
        p=BASE/name/'report.json'; report=load(p)
        assert report['returncode']==0 and report['originals_unchanged'] and report['model_object_released']
        assert report['source']['sha256']==profile['source_sha256'] and report['profile_sha256']==ref(profile_path)['sha256']
        assert report['checkpoint_writes']==report['training_updates']==0
        assert report['cuda_owned_cleanup']['allocated_bytes']==report['cuda_owned_cleanup']['reserved_bytes']==0
        assert not report['observation_failures']
        assert all(row['actual_token_ids_and_stop_equal'] for row in report['records'])
        assert all(row['generation']['actual_token_ids_and_stop_equal'] for row in report['natural_answers'])
        if name.endswith('_probe'):
            assert len(report['records'])==4 and len(report['natural_answers'])==1
            continue
        assert len(report['records'])==16 and len(report['natural_answers'])==4
        log=ROOT/('test_result/101_log_20261027_P106B_Stage11dW_hf_'+name+'.txt')
        assert '[runlog] 종료코드 0 ' in log.read_text()
        entry=dict(model=report['model'],device=report['device'],report=ref(p),log=ref(log),
            started_at=report['started_at'],ended_at=report['ended_at'],seconds=report['seconds'],
            parameters=report['parameters'],held_storage=report['held_after_generation'],
            rss_loaded=report['rss_loaded'],rss_closed=report['rss_closed'],
            cuda_validation_peak_allocated_bytes=report['cuda_validation_peak_allocated_bytes'],
            cuda_validation_peak_reserved_bytes=report['cuda_validation_peak_reserved_bytes'],
            cuda_generation_start=report['cuda_generation_start'],
            cuda_generation_peak_allocated_bytes=report['cuda_peak_allocated_bytes'],
            cuda_generation_peak_reserved_bytes=report['cuda_peak_reserved_bytes'],
            cleanup=report['cuda_owned_cleanup'],workloads=[],
            natural_cap_count=sum(r['generation']['unobserved']['finish_reason']=='MAX_NEW' for r in report['natural_answers']))
        for workload in profile['workloads']:
            measured=[r for r in report['records'] if r['workload']==workload['id'] and not r['warmup']]
            assert len(measured)==3
            entry['workloads'].append(dict(id=workload['id'],
                median_unobserved_seconds=statistics.median(r['unobserved']['seconds'] for r in measured),
                median_unobserved_tokens_per_second=statistics.median(r['unobserved']['tokens_per_second'] for r in measured),
                median_characters_per_second=statistics.median(r['unobserved']['characters_per_second'] for r in measured),
                median_utf8_bytes_per_second=statistics.median(r['unobserved']['utf8_bytes_per_second'] for r in measured),
                median_observed_first_token_ms=statistics.median(r['observed']['first_token_ms'] for r in measured),
                median_unobserved_external_cpu_percent=statistics.median(r['unobserved']['cpu_load']['external_percent'] for r in measured),
                max_returned_cache_bytes=max(r['unobserved']['returned_cache']['unique_storage_bytes'] for r in measured),
                max_forward_return_cache_bytes=max(r['observed']['max_forward_return_cache_bytes'] for r in measured),
                paired_ids_and_stops_equal=True))
        for row in report['natural_answers']:
            unobserved=row['generation']['unobserved']
            cases.append(dict(model=report['model'],device=report['device'],**row['case'],
                answer=unobserved['answer'],finish_reason=unobserved['finish_reason'],generated_tokens=unobserved['generated_tokens'],
                actual_paired_ids_and_stop_equal=True))
        lanes.append(entry)
    children=load(BASE/'launcher_receipt.json')
    assert set(children['child_codes'])==set(names[1:]) and set(children['child_codes'].values())=={'0'}
    closure=dict(schema='ROOT_ACTUAL_HF_RESOURCE_CLOSURE_V2',actual_parent_tool_session=83799,
        actual_os_parent_returncode=0,actual_child_returncodes={name:0 for name in names},
        source_sha256=profile['source_sha256'],profile=ref(profile_path),launcher_receipt=ref(BASE/'launcher_receipt.json'),
        profile_and_source_archive='handoff/audit/oct27_independent/hf_resource_execution_inputs_v2.json',
        original_first_attempt_parent_returncode=9,original_failure_preserved=True,
        training_updates=0,checkpoint_writes=0,not_a_new_quality_training=True)
    write('hf_v2_actual_closure.json',closure)
    write('hf_resource_v2_readback_v1.json',dict(schema='ROOT_HF_RESOURCE_READBACK_V1',lanes=lanes,
        source=ref(profile_path),actual_parent_returncode=0,claims='DESCRIPTIVE_RESOURCES_ONLY',
        concurrent_host_load='OTHER_CLEANUP_CPU_REPORTED_ACTIVE; EXACT_END_NOT_YET_CONFIRMED; EXTERNAL_CPU_PERCENT_RECORDED',
        cpu_startup='STRICT_LOADER_CUDA_VALIDATION_THEN_CPU1; NOT_CPU_ONLY_STARTUP',
        throughput='UNOBSERVED_INSTALLED_HF_GENERATE_PLUS_OUTPUT_DECODE; FIXED32; INPUT_UPLOAD_AND_TOKENIZATION_EXCLUDED',
        ttft='OBSERVER_STREAMER_AFTER_CPU_COPY; INCLUDES_HOOK_CACHE_AUDIT_AND_SYNC',
        precision='FP32_EAGER_MATH_TF32_OFF; NOT_QUANTIZED_DEPLOYMENT'))
    write('hf_natural_answers_v1.json',dict(schema='ROOT_HF_NATURAL_ANSWERS_V1',cases=cases,
        automated_quality_score=None,not_a_benchmark=True,template='PLAIN_BASE_PT_NO_CHAT_TEMPLATE'))
    lines=['# HF resource natural answer readback','',
        'Plain Base/PT prompts; four fixed cases; not a benchmark or new training.','']
    for case in cases:
        if case['device']!='cuda':continue
        lines.extend(['## '+case['model']+' / '+case['id'],'','질문: '+case['question'],'',
            '답변 원문:','',case['answer'],'','종료: '+case['finish_reason']+' / '+str(case['generated_tokens'])+' tokens',''])
    with (AUDIT/'hf_answers_v1.md').open('x',encoding='utf-8') as stream:stream.write(chr(10).join(lines))
    for lane in lanes:
        print(lane['model'],lane['device'],'heldMiB',round(lane['held_storage']['unique_storage_bytes']/2**20,3),
            'genPeakMiB',round(lane['cuda_generation_peak_allocated_bytes']/2**20,3),
            'tokps',[round(w['median_unobserved_tokens_per_second'],2) for w in lane['workloads']],
            'cap',lane['natural_cap_count'])
    return 0


if __name__=='__main__':
    raise SystemExit(main())
