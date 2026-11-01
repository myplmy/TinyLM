"""Independent byte/row readback of completed full-shape KL cost; CPU only."""
from pathlib import Path
import hashlib
import json
import statistics
ROOT=Path(__file__).resolve().parents[3]


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def main():
    report_path=ROOT/'test_result/evidence/p107_causal_kd_cost_v1_20261101/cost/report.json'
    profile_path=ROOT/'handoff/audit/nov01_afternoon/P107_KD_PROFILE_v1.json'
    raw=ROOT/'test_result/107_log_20261101_P107_Stage6W_causal_teacher_kl_cost.txt'
    r=json.loads(report_path.read_text());p=json.loads(profile_path.read_text())
    assert r['status']=='COMPLETE' and r['final_exit']==0 and r['quality_claim'] is False
    assert r['corpus_training'] is False and r['teacher_quality_claim'] is False and r['checkpoint_writes']==0
    assert r['source']==p['source'] and r['source_unchanged'] and r['parent_unchanged']
    assert [b['mode'] for b in r['blocks']]==['none','causal_kl','causal_kl','none']
    assert len(r['blocks'])==4 and all(len(b['attempts'])==4 for b in r['blocks'])
    for name,expected in p['source']['files'].items():assert sha(ROOT/name)==expected
    native=json.loads((ROOT/p['native_reference']['path']).read_text())
    spec=next(x for x in native['models'] if x['id']=='native595-q')
    assert sha(ROOT/spec['checkpoint']['path'])==spec['checkpoint']['sha256']
    assert sha(ROOT/native['tokenizer']['path'])==p['tokenizer_sha256']
    summary={}
    for mode in ('none','causal_kl'):
        blocks=[b for b in r['blocks'] if b['mode']==mode]
        assert blocks[0]['final_equivalence']==blocks[1]['final_equivalence']
        assert blocks[0]['losses']==blocks[1]['losses']
        rows=[row for b in blocks for row in b['attempts']]
        for row in rows:
            assert row['status']=='COMPLETE' and row['model_forwards']==16
            assert row['executed_input_tokens']==8*16*1024
            assert row.get('teacher_forwards',0)==(8 if mode=='causal_kl' else 0)
            assert row['observed_micro_batches']==8 and row['masked_targets']>0 and row['causal_targets']>0
            assert row['peak_reserved_bytes']<=p['allocator_cap_bytes']
        summary[mode]=dict(median_seconds=statistics.median(row['seconds']
            for b in blocks for row in b['attempts'][1:]),
            peak_reserved_bytes=max(row['peak_reserved_bytes'] for row in rows))
        for key in summary[mode]:assert summary[mode][key]==r['summary'][mode][key]
    assert r['teacher_initial_core_sha256']==r['teacher_final_core_sha256']==p['native_core_sha256']
    assert r['teacher_unchanged'] and all(b['teacher_core_sha256']==p['native_core_sha256'] for b in r['blocks'])
    assert r['completed_optimizer_updates']==r['physical_optimizer_updates']==16
    assert not r['unfinished_update_records'] and r['vram_watch']['query_errors']==0
    assert r['vram_watch']['maximum_additional_bytes']<=p['vram_limit_bytes']
    assert r['vram_watch']['thread_stopped'] and r['vram_watch']['client']['closed']
    assert r['final_cuda_cleanup']['allocated_bytes']==r['final_cuda_cleanup']['reserved_bytes']==0
    text=raw.read_text();assert 'actual_exit=0' in text and 'exitcode": 0' in text
    result=dict(schema='P107_CAUSAL_KD_ACTUAL_ROOT_V1',actual_exit=0,
        report=dict(path=str(report_path.relative_to(ROOT)),sha256=sha(report_path)),
        profile_sha256=sha(profile_path),raw=dict(path=str(raw.relative_to(ROOT)),sha256=sha(raw)),
        original_parent_unchanged=True,source_files_unchanged=True,teacher_unchanged=True,
        synthetic_student_input_positions=16*8*16*1024,teacher_forward_calls=64,
        teacher_input_positions=64*8*1024,student_optimizer_updates=16,
        repeated_trajectories_exact=True,summary=summary,
        kl_overhead_percent=(summary['causal_kl']['median_seconds']/summary['none']['median_seconds']-1)*100,
        extra_peak_reserved_bytes=summary['causal_kl']['peak_reserved_bytes']-summary['none']['peak_reserved_bytes'],
        checkpoint_writes=0,quality_claim=False,full_static_or_smoke_claim=False,gpu_runs_here=0)
    output=ROOT/'handoff/audit/nov01_afternoon/P107_KD_ACTUAL_ROOT_v1.json'
    with output.open('x') as stream:json.dump(result,stream,indent=2)
    print(json.dumps(result))
    return 0


if __name__=='__main__':raise SystemExit(main())
