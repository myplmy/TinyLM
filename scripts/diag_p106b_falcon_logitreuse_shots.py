#!/usr/bin/env python3
"""Fresh Falcon5 official evaluation; preserve completed Falcon0 and old profiles."""
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import sys
import sysconfig

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import tinylm
from scripts import diag_p106b_falcon_logitreuse as completed

base = completed.base
COMPLETED_PROFILE = completed.PROFILE
OFF_OUTPUT = completed.ORIGIN_OUTPUT
PROFILE = ROOT/'data_cache/p106b_falcon_logitreuse_shots_v1_20261101/profile.json'
OUTPUT = ROOT/'test_result/evidence/p106b_falcon_logitreuse_shots_v1_20261101'
DEADLINE = datetime(2026, 11, 1, 6, 0, tzinfo=timezone.utc)
ORIGINAL_PRIOR, ORIGINAL_READ = base.prior, base.read_profile


class CurrentAuthority:
    DEADLINE = DEADLINE
    def __getattr__(self, name):
        return getattr(ORIGINAL_PRIOR, name)


def collator_proof():
    from scripts.p106b_official_lm_adapter import SOURCE, MANIFEST
    archive = Path(json.loads(MANIFEST.read_text())['archive_path'])
    return base.verify_files(['lm_eval/models/utils.py'], archive=archive,
        source=SOURCE, runtime=Path(sysconfig.get_paths()['purelib']))


def read_profile(path, sha):
    value = ORIGINAL_READ(path, sha)
    base.resource.need(value['authority_directive']==105 and value['deadline']==DEADLINE.isoformat(),
        '새 실행 허가·마감 계약 필요')
    base.resource.need(value['official_collator']==collator_proof(), '공식 Collator 변형')
    return value


def freeze():
    from scripts.prepare_p106b_official_eval import configure_hf_cache
    configure_hf_cache()
    old = json.loads(COMPLETED_PROFILE.read_text())
    assert all(base.data.digest(ROOT/p)==sha for p,sha in old['source']['files'].items())
    assert old['models']==base.model_assets() and old['runtime']==base.runtime_proof()
    assert old['inherited_cpu_contract']['one_token_continuations']==112336
    assert not PROFILE.exists() and not OUTPUT.exists()
    value = dict(old)
    value.update(created_at=datetime.now(timezone.utc).isoformat(), source=base.identity(),
        policies={str(n):base.prior.policy(n) for n in (0,5)},
        authority_directive=105, deadline=DEADLINE.isoformat(),
        official_collator=collator_proof(),
        inherited_completed_contract=dict(path=str(COMPLETED_PROFILE.relative_to(ROOT)),
            sha256=base.data.digest(COMPLETED_PROFILE), token_metadata_unchanged=True),
        active_arm='falcon5', model_loads=0, gpu_runs=0, training=0, checkpoint_writes=0)
    PROFILE.parent.mkdir(parents=True, exist_ok=False)
    OUTPUT.mkdir(parents=True, exist_ok=False)
    base.resource.write_new(PROFILE,value)
    base.resource.write_new(OUTPUT/'contract.json',value)
    print(json.dumps(dict(status='FALCON5_FRESH_CONTRACT', profile_sha256=base.data.digest(PROFILE),
        source=value['source']['sha256'], deadline=value['deadline'], gpu=0)))
    return 0


def compare_cost(shots, before_root, after_root, profile_sha):
    if isinstance(shots,bool) or shots not in (0,5):
        raise ValueError('정확한0/5shot 필요')
    rel = Path('shot'+str(shots))/'cost'
    old_path, new_path = before_root/rel/'report.json', after_root/rel/'report.json'
    old, new = json.loads(old_path.read_text()), json.loads(new_path.read_text())
    assert old['final_exit']==new['final_exit']==0
    assert old['actual_rows']==new['actual_rows']==114
    assert old['shots']==new['shots']==shots
    assert new['profile_sha256']==profile_sha
    assert set(old['samples'])==set(new['samples']) and len(new['samples'])==57
    maximum, checked = 0., 0
    for name in old['samples']:
        pairs=[]
        for folder,report in [(before_root,old),(after_root,new)]:
            rows=[]
            for part in report['samples'][name]['shards']:
                path=folder/rel/'samples'/name/part['path']
                assert base.data.digest(path)==part['sha256']
                rows.extend(json.loads(line) for line in path.read_text().splitlines())
            pairs.append(rows)
        assert len(pairs[0])==len(pairs[1])==2
        for a,b in zip(*pairs):
            assert a['doc_id']==b['doc_id'] and a['arguments']==b['arguments']
            left,right=[v[0] for v in a['filtered_resps']],[v[0] for v in b['filtered_resps']]
            assert len(left)==len(right)==4
            assert all(math.isfinite(v) for v in left+right)
            assert all(math.isclose(x,y,abs_tol=1e-4,rel_tol=1e-4) for x,y in zip(left,right))
            assert max(range(4),key=lambda i:left[i])==max(range(4),key=lambda i:right[i])
            maximum=max(maximum,max(abs(x-y) for x,y in zip(left,right)))
            checked+=1
    assert checked==114
    return dict(shots=shots,rows=checked,loglikelihoods=checked*4,all_argmax_equal=True,
        max_abs=maximum,atol=1e-4,rtol=1e-4,profile_sha256=profile_sha,
        original_cost_sha256=base.data.digest(old_path),variant_cost_sha256=base.data.digest(new_path),
        quality_selection=False)


def require_cost_parity(shots, *, save=False):
    value=compare_cost(shots,OFF_OUTPUT,OUTPUT,base.data.digest(PROFILE))
    path=OUTPUT/('cost_parity_shot'+str(shots)+'.json')
    if save:
        assert not path.exists()
        base.resource.write_new(path,value)
    else:
        assert json.loads(path.read_text())==value
    print(json.dumps(dict(cost_parity_rows=value['rows'],loglikelihoods=value['loglikelihoods'],
        shots=shots,max_abs=value['max_abs'])),flush=True)
    return value


base.PROFILE, base.OUTPUT = PROFILE, OUTPUT
base.prior, base.read_profile = CurrentAuthority(), read_profile
base.OWN = base.OWN + ('scripts/diag_p106b_falcon_logitreuse_shots.py',
    'scripts/test_p106b_falcon_logitreuse_shots.py')


def main():
    mode=sys.argv[sys.argv.index('--mode')+1]
    if mode=='contract' and '--execute' in sys.argv:
        return freeze()
    arm=sys.argv[sys.argv.index('--arm')+1]
    if arm!='falcon5':
        raise ValueError('완료한0shot 재실행 금지: 새5shot 경로만 허용')
    if mode=='full':
        require_cost_parity(5,save=False)
    code=base.main()
    if mode=='cost' and '--execute' in sys.argv and code==0:
        require_cost_parity(5,save=True)
    return code


if __name__=='__main__':
    raise SystemExit(main())
