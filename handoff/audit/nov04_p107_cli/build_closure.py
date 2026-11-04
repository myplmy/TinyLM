"""Bind the exact 27 owned result logs and two complete-smoke raw logs."""
import hashlib
import json
from pathlib import Path

BASE=Path('handoff/audit/nov04_p107_cli')
WEIGHTS=Path('handoff/audit/nov04_weight_space')
RESULT107='test_result/107_20261027131747_P107-가시성과-shift는-검산됐고-학습효과는-미확인.md'
RESULT108='test_result/108_20261104190525_P108-방향수리는-실행됐지만-정답은-늘지-않았다.md'
NEW107=('Stage8aW_document_input_cpu','Stage8aWb_document_cli_cpu','Stage8aWc_document_profile_prepare',
        'Stage8bW_document_cli_boundary','Stage8cW_document_cli_fresh_resume')
NEW108=('Stage6aW_calibration_signal_cpu','Stage6b0W_local_hook_cpu','Stage6bW_calibration_local_actual',
        'Stage6c0W_local_hook_cleanup_cpu','Stage6cW_calibration_local_cleanup')


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def write_new(path,value):
    with path.open('x',encoding='utf-8') as stream:json.dump(value,stream,ensure_ascii=False,indent=2);stream.write(chr(10))


def main():
    output=BASE/'RESULT_CLOSURE_v1.json'
    smoke_output=BASE/'SMOKE_RESULT_BINDINGS_v1.json'
    if output.exists() or smoke_output.exists():raise FileExistsError('closure already prepared')
    old=json.loads((WEIGHTS/'P108_RESULT_CLOSURE_v1.json').read_text(encoding='utf-8'))
    for number,names,result,section in ((107,NEW107,RESULT107,'### 18.2 선결과 원로그'),
                                      (108,NEW108,RESULT108,'### 13.1 질문·방법·원로그')):
        for name in names:
            log='test_result/'+str(number)+'_log_20261104_P'+str(number)+'_'+name+'.txt'
            if not Path(log).is_file():raise FileNotFoundError(log)
            old['input_logs'].append(log)
            old['mappings'].append(dict(log=log,result=result,section=section,status='RECORDED'))
    if len(old['input_logs'])!=27 or len(set(old['input_logs']))!=27:
        raise ValueError('exact unique result input set must have 27 logs')
    write_new(output,old)
    smoke=[]
    for version,name in ((1,'20261104121352_smoke_codex_nov04_p108_p107_v1_424f922.txt'),
                         (2,'20261104122620_smoke_codex_nov04_p108_p107_v2_424f922.txt')):
        raw=Path('smoketest_logs')/name
        report_path=Path('test_result/evidence/codex_smoke')/('nov04_p108_p107_v'+str(version))/'smoke_report.json'
        report=json.loads(report_path.read_text(encoding='utf-8'))
        if (sha(raw)!=report['log_sha256'] or report['action_count']!=106 or report['child_count']!=44
                or not report['original_synthetic_unchanged'] or not report['source_pins_unchanged']
                or report['returncode']!=(1 if version==1 else 0)):
            raise ValueError('actual smoke/original raw binding differs')
        smoke.append(dict(log=str(raw),sha256=sha(raw),bytes=raw.stat().st_size,
            report=str(report_path),report_sha256=sha(report_path),actual_exit=report['returncode'],
            action_count=106,child_count=44,training_count=report['training_count'],
            wall_seconds=report['whole_sec'],global_pass_eligible=False,
            result=RESULT108,section='## 12. 현재 소스 전체 스모크와 파일 CLI 선결'))
    latest=json.loads(Path(smoke[-1]['report']).read_text(encoding='utf-8'))
    pins=latest['source_pins_before']
    if isinstance(pins,list):pins={row['path']:row['sha256'] for row in pins}
    core={name:digest for name,digest in pins.items() if name.startswith('tinylm/')}
    if not core:raise ValueError('no pinned current model/trainer core found')
    for name,digest in core.items():
        if sha(Path(name))!=digest:raise ValueError('smoked core changed: '+name)
    write_new(smoke_output,dict(schema='P107_P108_EXACT_SMOKE_RESULT_BINDINGS_V1',smoke=smoke,
        current_model_trainer_core_pins=core,current_model_trainer_core_unchanged=True,
        scoped_collectors_not_global_checks=True,old_failure_preserved=True,
        no_new_global_static_or_model_quality_claim=True))
    print(json.dumps(dict(result_logs=27,smoke_logs=2,smoked_core_files=len(core),
        result_closure=str(output),smoke_bindings=str(smoke_output))))


if __name__=='__main__':main()
