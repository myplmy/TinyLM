"""Verify complete actual stdout bytes; measure transport, not human review speed."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[3];AUDIT=Path(__file__).resolve().parent
sys.path.insert(0,str(AUDIT))
from test_lossless_review_packet_v2 import decode_pair

runtime=json.loads((AUDIT/'LOSSLESS_REVIEW_FIXED_WRAPPERS_RUNTIME_V2.json').read_bytes())
samples=list(runtime['positives'])
scope=json.loads((AUDIT/'LOSSLESS_REVIEW_READER_SCOPE_V2.json').read_bytes())
guard=json.loads((ROOT/scope['contract']['path']).read_bytes())
manifest=json.loads((ROOT/scope['roles']['context_controls']['root12_independent_admission_counter_v1']['path']).read_bytes())
source=next(row for row in manifest['rows'] if row['id']=='expanded_train:805580')
assert source['role']=='context_controls'
samples.append(dict(role='context_controls',short='c',cohort='root12_independent_admission_counter_v1',
    id=source['id'],original=source['original'],candidate=source['candidate'],identity_control=True))
rows=[]
for sample in samples:
    assert sample['id'] not in guard['restricted_ids']
    assert all(sample[name]['sha256'] not in guard['restricted_hashes'] for name in ['original','candidate'])
    before=time.monotonic();cursor=0;parts=None;payload=[];stdout_bytes=0;part=1
    while parts is None or part<=parts:
        args=[sample['id'],'pair',str(part)]
        if sample['short'] in {'h','j','g'}:args.insert(0,str(int(sample['cohort'].split('_page_')[1].split('_')[0])))
        result=subprocess.run(['bash',str(ROOT/f"tmp/hold-{sample['short']}-lossless-v2"),*args],cwd=ROOT,capture_output=True)
        assert result.returncode==0,result.stderr.decode('utf-8')
        stdout_bytes+=len(result.stdout)
        header,rest=result.stdout.split(b'\n',1)
        assert header.startswith(b'TRUSTED_LOSSLESS_VIEW_V2 ')
        info=json.loads(header[len(b'TRUSTED_LOSSLESS_VIEW_V2 '):])
        assert info['source_id']==sample['id'] and info['role']==sample['role']
        assert info['contract']['sha256']==scope['contract']['sha256']
        assert info['original']==sample['original'] and info['candidate']==sample['candidate']
        assert info['part']==part and info['range_unit']=='UTF8_BYTES'
        parts=info['parts'];lo,hi=info['range'];assert lo==cursor and 0<=hi-lo<=4000
        prefix=b'SOURCE_DATA_VIEW_BEGIN\n';assert rest.startswith(prefix)
        raw=rest[len(prefix):len(prefix)+hi-lo];assert len(raw)==hi-lo;raw.decode('utf-8')
        ending=b'\nSOURCE_DATA_VIEW_EOF\n' if part==parts else b'\nSOURCE_DATA_VIEW_MORE_PARTS_REMAIN\n'
        assert rest[len(prefix)+len(raw):]==ending
        assert info['end_of_view']==(part==parts)
        payload.append(raw);cursor=hi;part+=1
    displayed=b''.join(payload).decode('utf-8')
    original,candidate=decode_pair(displayed,info)
    assert hashlib.sha256(original).hexdigest().upper()==sample['original']['sha256']
    assert hashlib.sha256(candidate).hexdigest().upper()==sample['candidate']['sha256']
    pin=scope['roles'][sample['role']][sample['cohort']]
    old_manifest=json.loads((ROOT/pin['path']).read_bytes());old_source=next(row for row in old_manifest['rows'] if row['id']==sample['id'])
    legacy_parts=old_source.get('reading_parts',[])
    rows.append(dict(role=sample['role'],id=sample['id'],cohort=sample['cohort'],
        original_bytes=len(original),candidate_bytes=len(candidate),representation=info['candidate_representation'],
        pair_parts_actual=parts,payload_UTF8_bytes=cursor,total_stdout_bytes=stdout_bytes,
        seconds=time.monotonic()-before,complete_actual_stdout_independently_reconstructed=True,
        original_and_candidate_SHA_exact=True,legacy_manifest_parts=len(legacy_parts),
        legacy_manifest_frame_characters=info['legacy_manifest_frame_characters'],
        identity_control=sample.get('identity_control',False),
        legacy_identity_skip_may_already_exist=original==candidate))
value=dict(status='SIX_ALREADY_REVIEWED_SAMPLES_COMPLETE_STDOUT_LOSSLESSLY_RECONSTRUCTED',
    rows=rows,selection_is_not_random=True,legacy_actual_role_call_count_measured=False,
    fixed_original_and_candidate_files_unchanged=True,human_review_speed_measured=False,
    actual_agent_trial_complete=False,new_first_review_credit=0,root_or_cache_admission=False,
    protocol_decoder_pin=dict(path=str((AUDIT/'test_lossless_review_packet_v2.py').relative_to(ROOT)),
        sha256=hashlib.sha256((AUDIT/'test_lossless_review_packet_v2.py').read_bytes()).hexdigest().upper()),
    goal_complete=False,training_authorized=False)
out=AUDIT/'LOSSLESS_REVIEW_V2_ACTUAL_TRANSPORT_BENCHMARK_V1.json';assert not out.exists()
with out.open('x',encoding='utf-8') as stream:json.dump(value,stream,ensure_ascii=False,indent=2);stream.write('\n')
print(json.dumps(dict(status=value['status'],samples=len(rows),new_first_review_credit=0,
    actual_pair_parts=sum(row['pair_parts_actual'] for row in rows),
    all_original_and_candidate_SHA_exact=True,sha256=hashlib.sha256(out.read_bytes()).hexdigest().upper())),flush=True)
