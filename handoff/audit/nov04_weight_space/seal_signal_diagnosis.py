"""Independent calibration-only readback; no Torch/tensor/model/CUDA loading."""
import hashlib
import json
from pathlib import Path

ROOT=Path.cwd()
BASE=Path('handoff/audit/nov04_weight_space')
DATA=Path('test_result/evidence/p108_attenuation_v1_20261104/new595-broad-q')


def sha(path):
    result=hashlib.sha256()
    with path.open('rb') as stream:
        while True:
            block=stream.read(1<<20)
            if not block:break
            result.update(block)
    return result.hexdigest().upper()


def read(path):return json.loads(path.read_text(encoding='utf-8'))


def main():
    output=BASE/'ATTENUATION_ROOT_READBACK_v1.json'
    if output.exists():raise FileExistsError(output)
    profile=read(DATA/'gpu_profile_v2.json')
    report=read(DATA/'gpu_v2/report.json')
    cpu=read(DATA/'cpu/report.json')
    failure=read(BASE/'ATTENUATION_FIRST_FAILURE_v1.json')
    if (report['actual_exit']!=0 or report['status']!='TECHNICAL_COMPLETE'
            or report['profile_sha256']!=sha(DATA/'gpu_profile_v2.json')
            or report['final_verification_errors'] or not report['original_checkpoint_unchanged']
            or not report['old_inputs_unchanged'] or report['original_core_after']!=report['origin']['core_sha256']
            or any(report['final_cuda_cleanup'][k] for k in ('allocated_bytes','reserved_bytes'))):
        raise ValueError('new actual diagnosis/final verification failed')
    for name,expected in profile['source_pins'].items():
        if sha(Path(name))!=expected:raise ValueError('new source/input changed: '+name)
    for item in failure['archived_sources']:
        if sha(Path(item['blob']))!=item['sha256']:raise ValueError('first source archive changed')
    for field in ('profile','log'):
        if sha(Path(failure[field]['path']))!=failure[field]['sha256']:
            raise ValueError('preserved first failure changed')
    old_profile=Path('test_result/evidence/p108j_v1_20261104/new595-broad-q/profile.json')
    old=read(old_profile)
    for name,expected in old['sources'].items():
        if sha(Path(name))!=expected:raise ValueError('original calibrated source changed: '+name)
    checkpoint=Path('runs/ckpt/m100s10_ko-en_broad4_p106b_native595_broad_v1_s1337_ternary.pt')
    if sha(checkpoint)!=report['origin']['checkpoint_sha256']:
        raise ValueError('original checkpoint bytes changed')
    names=profile['variants']
    totals={name:dict(body_correct=0,eot_correct=0,total_correct=0) for name in names}
    first=[];physical_comparisons=0
    for item,(begin,end) in zip(report['records'],profile['offsets']):
        if not item['original_margin_exact'] or len(item['targets'])!=end-begin:
            raise ValueError('original calibration binding differs')
        if item['variants']['original']!=item['variants']['original_after']:
            raise ValueError('original actual logits readback differs')
        for name,value in item['variants'].items():
            if name not in totals:raise ValueError('unexpected diagnosis variant')
            if value['targets']!=end-begin:raise ValueError('target accounting differs')
            physical_comparisons+=value['targets']
            for index,token in enumerate(value['tokens']):
                if token['actual_margin']>token['fixed_margin']+1e-6:
                    raise ValueError('maximum competitor margin cannot exceed fixed-competitor margin')
                correct=token['argmax']==token['target']
                totals[name]['total_correct']+=int(correct)
                totals[name]['eot_correct' if index==value['targets']-1 else 'body_correct']+=int(correct)
        for receipt in item['edit_receipts'].values():
            if len(receipt)!=1 or receipt[0]['latent_changed']!=0:
                raise ValueError('registered/latent weight changed')
        first.append(dict(id=item['id'],question=item['question'],gold=item['gold'],
            first_token_actual_margin={name:value['tokens'][0]['actual_margin'] for name,value in item['variants'].items()}))
    if physical_comparisons!=40 or len(first)!=4:
        raise ValueError('fixed physical target comparisons differ')
    old_test=read(Path('test_result/evidence/p108j_v1_20261104/new595-broad-q/confirm/report.json'))
    if [r['exact'] for r in old_test['variants']]!=[34]*5:
        raise ValueError('old held-out negative was changed')
    proof=dict(schema='P108_ATTENUATION_INDEPENDENT_ROOT_V1',actual_exit=0,
        model_tensor_loads=0,cuda_calls=0,new_gold_positions=0,
        reused_unique_calibration_target_positions=8,actual_forward_calls=20,
        actual_target_comparisons=physical_comparisons,
        legacy_exposures_field_means_unique_positions_not_forward_comparisons=True,
        calibration_body_positions=4,calibration_eot_positions=4,totals=totals,rows=first,
        first_failure_preserved_actual_exit=1,old_test_exact_per_arm=[34]*5,
        old_test_gate_negative_unchanged=True,quality_claim=False,
        input_pins={str(p):sha(p) for p in (DATA/'gpu_profile_v2.json',DATA/'gpu_v2/report.json',
            DATA/'cpu/report.json',BASE/'ATTENUATION_FIRST_FAILURE_v1.json')},
        original_checkpoint_unchanged=True,original_sources_unchanged=True,
        owned_cuda_after=[0,0],wall_seconds=report['wall_seconds'])
    with output.open('x',encoding='utf-8') as stream:json.dump(proof,stream,ensure_ascii=False,indent=2);stream.write(chr(10))
    print(json.dumps({k:proof[k] for k in ('actual_exit','totals','actual_forward_calls','actual_target_comparisons','quality_claim')}))


if __name__=='__main__':main()
