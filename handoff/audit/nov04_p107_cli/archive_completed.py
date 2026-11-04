"""Preserve five exact completed launchers and source inputs before retirement."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import stat
import subprocess

from scripts.sync_experiments_tsv import batch_commands, norm

BASE=Path('handoff/audit/nov04_p107_cli')
WEIGHTS=Path('handoff/audit/nov04_weight_space')
MANIFEST=BASE/'COMPLETED_LAUNCHERS_v1.json'
RESULTS={107:Path('test_result/107_20261027131747_P107-가시성과-shift는-검산됐고-학습효과는-미확인.md'),
         108:Path('test_result/108_20261104190525_P108-방향수리는-실행됐지만-정답은-늘지-않았다.md')}
FILES={107:('run_P107_Stage8bW_document_cli_boundary.sh','run_P107_Stage8cW_document_cli_fresh_resume.sh'),
       108:('run_P108_Stage6aW_calibration_signal_cpu.sh','run_P108_Stage6bW_calibration_local_actual.sh',
            'run_P108_Stage6cW_calibration_local_cleanup.sh')}


def sha(data):return hashlib.sha256(data).hexdigest().upper()


def write_new(path,value):
    with path.open('x',encoding='utf-8') as stream:json.dump(value,stream,ensure_ascii=False,indent=2);stream.write(chr(10))


def blob(raw):
    if len(raw)>=20_000_000:raise ValueError('archive text exceeds file size boundary')
    path=WEIGHTS/'source_blobs'/(sha(raw)+'.txt')
    if path.exists():
        if path.read_bytes()!=raw:raise ValueError('immutable blob differs')
    else:
        with path.open('xb') as stream:stream.write(raw)
    return str(path)


def prepare():
    if MANIFEST.exists():raise FileExistsError(MANIFEST)
    directory=BASE/'completed_launchers_v1';directory.mkdir(exist_ok=False)
    entries=[];patches=[]
    for number,names in FILES.items():
        lines=['### 18.6 완료 명령 원형' if number==107 else '## 14. 후속 진단의 완료 명령 원형','',
            '아래 원문/명령/SHA는 종료한 시도의 보존이며 실패를 성공으로 바꾸지 않는다. '
            '실제 재현은 새 승인·새 namespace가 필요하고 현재 태그/snapshot을 덮어쓰지 않는다. '
            '정확 [보존 manifest](../handoff/audit/nov04_p107_cli/COMPLETED_LAUNCHERS_v1.json)를 확인한 뒤 -done으로 바꾸고 삭제한다.','']
        for name in names:
            path=Path(name);raw=path.read_bytes()
            if path.is_symlink() or any(x>=128 for x in raw):raise ValueError('exact ASCII launcher required')
            subprocess.run(['bash','-n',str(path)],check=True,capture_output=True)
            archived=directory/(name+'.txt')
            with archived.open('xb') as stream:stream.write(raw)
            log=Path('test_result')/(str(number)+'_log_20261104_'+path.stem.removeprefix('run_')+'.txt')
            codes=re.findall(r'종료코드\s+(-?\d+)',log.read_text(encoding='utf-8'))
            if not codes:raise ValueError('closed actual runlog required')
            commands=batch_commands(path)
            if not commands:raise ValueError('executable commands missing')
            entries.append(dict(original=name,after=path.stem+'-done.sh',archive=str(archived),
                sha256=sha(raw),bytes=len(raw),mode=stat.S_IMODE(path.stat().st_mode),
                result=str(RESULTS[number]),commands=commands,raw_log=str(log),
                raw_log_sha256=sha(log.read_bytes()),actual_exit=int(codes[-1]),
                disposition='CLOSED_ATTEMPT_DONE_THEN_DELETE_NOT_SCIENTIFIC_PASS'))
            lines+=['#### '+name,'','실제 마지막 종료코드 '+codes[-1]+'.','', '```sh',*raw.decode('ascii').splitlines(),'```','']
        result=RESULTS[number]
        context=result.read_text(encoding='utf-8').rstrip().splitlines()[-5:]
        patches+=['*** Update File: /home/uranus/tinyLM/'+str(result),'@@',*(' '+v for v in context),'+',*('+'+v for v in lines)]
    write_new(MANIFEST,dict(schema='P107_P108_COMPLETED_LAUNCHERS_V1',entries=entries,
        authority='USER107_AND_STANDING_COMMAND_PRESERVING_COMPLETED_LAUNCHER_RETIREMENT',
        original_logs_changed=0,checkpoint_actions=0,unrelated_launcher_actions=0))
    patch='*** Begin Patch'+chr(10)+chr(10).join(patches)+chr(10)+'*** End Patch'+chr(10)
    with (BASE/'COMPLETED_COMMANDS_v1.patch').open('x',encoding='utf-8') as stream:stream.write(patch)
    profiles=[BASE/'PROFILE_v1.json',
        Path('test_result/evidence/p108_attenuation_v1_20261104/new595-broad-q/profile.json'),
        Path('test_result/evidence/p108_attenuation_v1_20261104/new595-broad-q/gpu_profile.json'),
        Path('test_result/evidence/p108_attenuation_v1_20261104/new595-broad-q/gpu_profile_v2.json')]
    references=[]
    for path in profiles:
        data=json.loads(path.read_text(encoding='utf-8'))
        pins=data.get('source_pins',data.get('input_pins',{}))
        files=[]
        for name,expected in pins.items():
            if not name.endswith(('.py','.sh')):continue
            saved=WEIGHTS/'source_blobs'/(expected+'.txt')
            raw=saved.read_bytes() if saved.exists() else Path(name).read_bytes()
            if sha(raw)!=expected:raise ValueError('executed source unavailable: '+name)
            files.append(dict(path=name,sha256=expected,bytes=len(raw),blob=blob(raw)))
        references.append(dict(path=str(path),sha256=sha(path.read_bytes()),sources=files))
    inputs=[]
    for name in ('manifest.json','documents.jsonl'):
        path=Path('runs/isolated/p107_document_cli_v1_20261104/inputs/v1')/name
        raw=path.read_bytes();inputs.append(dict(path=str(path),bytes=len(raw),sha256=sha(raw),blob=blob(raw),
            interpretation='EXACT_SYNTHETIC_INPUT_BYTES_ORIGINAL_RELATIVE_PATH_CONTEXT_NOT_NEW_ADMISSION'))
    write_new(BASE/'SOURCE_ARCHIVE_v1.json',dict(schema='P107_P108_SEALED_SOURCE_ARCHIVE_V1',
        profiles=references,synthetic_inputs=inputs,original_source_overwrites=0,
        runtime_snapshot_and_tensor_packet_archived_to_git=False))
    print(json.dumps(dict(manifest_sha256=sha(MANIFEST.read_bytes()),closed_launchers=len(entries),
        result_patch=str(BASE/'COMPLETED_COMMANDS_v1.patch'),profile_archives=len(references))))


def retire(expected):
    if sha(MANIFEST.read_bytes())!=expected:raise ValueError('exact retirement manifest SHA required')
    value=json.loads(MANIFEST.read_text(encoding='utf-8'))
    renamed=BASE/'DONE_RENAME_v1.json';receipt=BASE/'RETIREMENT_v1.json'
    if renamed.exists() or receipt.exists():raise FileExistsError('retirement already started')
    for row in value['entries']:
        for name in ('original','archive'):
            if sha(Path(row[name]).read_bytes())!=row['sha256']:raise ValueError('source/archive changed')
        if Path(row['after']).exists() or Path(row['original']).is_symlink():raise ValueError('unsafe destination/source')
        result=norm(Path(row['result']).read_text(encoding='utf-8'))
        if any(norm(command) not in result for command in row['commands']):raise ValueError('result omitted exact command')
        if sha(Path(row['raw_log']).read_bytes())!=row['raw_log_sha256']:raise ValueError('original raw log changed')
    for row in value['entries']:Path(row['original']).rename(row['after'])
    write_new(renamed,dict(manifest_sha256=expected,done=[r['after'] for r in value['entries']]))
    for row in value['entries']:
        path=Path(row['after'])
        if sha(path.read_bytes())!=row['sha256']:raise ValueError('done launcher bytes changed')
        path.unlink()
    write_new(receipt,dict(schema='P107_P108_COMPLETED_RETIREMENT_V1',manifest_sha256=expected,
        renamed_done_then_deleted=[r['after'] for r in value['entries']],
        original_logs_preserved=True,checkpoint_actions=0,unrelated_paths_changed=0,
        restore_via='EXACT_ARCHIVED_BYTES_AND_RECORDED_MODE'))
    print(json.dumps(dict(deleted=len(value['entries']),raw_logs='PRESERVED',checkpoint_actions=0)))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode',choices=('prepare','retire'))
    parser.add_argument('sha256',nargs='?')
    args=parser.parse_args()
    prepare() if args.mode=='prepare' else retire(args.sha256)
