"""CPU-only independent disk, schedule, execution and original-source readback."""
import hashlib
import json
import math
import os
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
os.environ['CUDA_VISIBLE_DEVICES']=''
import torch
from scripts import diag_p107_disk_resume as d
from tinylm.train.boundary_store import load_complete

torch.set_num_threads(1)


def main():
    profile=json.loads(d.PROFILE.read_text())
    expected_profile='8BDA8C4334925C178B83856F3DC02A3002888F13E193FAA8B0329F2E79DB8ECD'
    assert d.old.resource.digest(d.PROFILE)==expected_profile
    assert profile['source']==d.old.identity()
    path=d.OUTPUT/'resume/report.json'
    report=json.loads(path.read_text())
    assert report['status']=='COMPLETE' and report['final_exit']==0
    assert report['completed_optimizer_updates']==report['physical_optimizer_updates']==6
    assert report['source']==profile['source'] and report['source_unchanged'] and report['parent_unchanged']
    assert not report['final_verification_errors'] and not report['model_release_errors']
    assert report['expected_hashes']==report['actual_hashes']
    assert report['resume_equivalence']=='EXACT'
    assert report['checkpoint_writes']==1 and report['corpus_training'] is False
    assert report['fresh_optimizer_source_session'] and report['same_model_object_reloaded']
    assert report['separate_process_or_power_loss_test'] is False
    assert report['final_cuda_cleanup']['allocated_bytes']==report['final_cuda_cleanup']['reserved_bytes']==0
    watch=report['vram_watch']
    assert watch['reason'] is None and watch['thread_stopped'] and watch['client']['closed']
    assert watch['maximum_additional_bytes']<=profile['vram_limit_bytes']
    manifest=json.loads((d.SNAPSHOT/'manifest.json').read_text())
    assert manifest==report['snapshot']['manifest']
    full=hashlib.sha256();count=0
    for index,item in enumerate(manifest['parts']):
        assert item['path']==f'part_{index:06d}.bin'
        part=d.SNAPSHOT/item['path']
        raw=part.read_bytes()
        assert len(raw)==item['bytes'] and 0<len(raw)<=16_000_000
        assert hashlib.sha256(raw).hexdigest().upper()==item['sha256']
        full.update(raw);count+=len(raw)
    assert full.hexdigest().upper()==manifest['sha256'] and count==manifest['bytes']
    saved=load_complete(d.SNAPSHOT)
    assert d.hashes(saved)==report['snapshot_saved_state_hashes']
    assert saved['contract']==dict(total_updates=8,warmup_updates=2,schedule='cosine',decay_fraction=.2)
    assert saved['trainer']['cursor']==saved['trainer']['source']['cursor']==2
    assert saved['trainer']['policy']['next_update']==2
    generator=torch.Generator(device='cpu').manual_seed(20261101)
    corpus=hashlib.sha256()
    for i in range(4):
        name=('synthetic-'+str(i)).encode()
        tokens=torch.randint(35,32768,(4097,),generator=generator)
        corpus.update(len(name).to_bytes(8,'little'));corpus.update(name)
        corpus.update(tokens.numel().to_bytes(8,'little'));corpus.update(tokens.numpy().tobytes())
    assert corpus.hexdigest().upper()==report['explicit_source_contract']['corpus_sha256']
    assert corpus.hexdigest().upper()==saved['trainer']['config']['corpus_sha256']
    rows=report['prefix']+report['continued']+report['resumed']
    assert [r['update'] for r in rows]==[0,1,2,3,2,3]
    for row in rows:
        assert row['status']=='COMPLETE' and row['model_forwards']==16 and row['executed_input_tokens']==131072
        assert row['masked_targets']>0 and row['causal_targets']>0 and row['observed_micro_batches']==8
        assert math.isfinite(row['loss']) and math.isfinite(row['pre_clip_gradient_norm'])
        assert row['peak_reserved_bytes']<=profile['allocator_cap_bytes']
        step=row['update']
        factor=(step+1)/2 if step<2 else .1+.45*(1+math.cos(math.pi*(step-2)/6))
        expected=[[rate*factor for rate in group] for group in saved['base_lrs']]
        assert row['schedule_lrs']==expected
    for a,b in zip(report['continued'],report['resumed']):
        for key in ['loss','masked_targets','causal_targets','schedule_lrs']:
            assert a[key]==b[key]
    native=d.old.resource.read_ref(profile['native_reference'])
    spec=next(x for x in native['models'] if x['id']=='native595-q')
    assert d.old.resource.digest(d.old.resource.safe(spec['checkpoint']['path']))==spec['checkpoint']['sha256']
    raw=ROOT/'test_result/107_log_20261101_P107_Stage5W_document_schedule_disk_resume.txt'
    assert '[runlog] 종료코드 0' in raw.read_text() and 'actual_exit=0;' in raw.read_text()
    result=dict(schema='P107_DISK_ACTUAL_ROOT_V1',actual_parent_session=69640,actual_parent_exit=0,
        physical_updates=6,logical_cursor=4,executed_positions=786432,real_corpus_tokens=0,
        snapshot_parts=len(manifest['parts']),snapshot_bytes=count,all_parts_below20mb=True,
        disk_payload_exact=True,full_state_schedule_rng_source_exact=True,original_parent_unchanged=True,
        original_source_unchanged=True,final_cuda_bytes=0,telemetry_query_errors=watch['query_errors'],
        cpu_root_model_or_cuda_calls=0,profile_sha256=expected_profile,report_sha256=d.old.resource.digest(path),
        auditor_sha256=d.old.resource.digest(Path(__file__)),power_loss_or_new_process_claim=False,
        production_cli_or_quality_claim=False,errors=[])
    out=Path(__file__).with_name('P107_DISK_ACTUAL_ROOT_v1.json')
    d.old.resource.write_new(out,result)
    print(json.dumps(result))


if __name__=='__main__':main()
