"""Reuse proven build/consumer recorders with one immutable cache configuration."""
from pathlib import Path
from datetime import datetime,timezone
import argparse
import hashlib
import json
import os
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[3];AUDIT=Path(__file__).resolve().parent
parser=argparse.ArgumentParser();parser.add_argument('--config',required=True)
parser.add_argument('--phase',choices=['chain','build','verify'],default='chain')
parser.add_argument('--expected-config-sha');args=parser.parse_args()
path=(ROOT/args.config).resolve();assert path.is_relative_to(AUDIT) and not path.is_symlink()
raw=path.read_bytes();config_sha=hashlib.sha256(raw).hexdigest().upper()
if args.expected_config_sha:assert config_sha==args.expected_config_sha
c=json.loads(raw);number=c['cache_version'];roster=c['roster_version'];selection=c['selection_version']
assert all(isinstance(v,int) and 6<=v<=9999 for v in [number,roster,selection])
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest().upper()
if args.phase=='chain':
    out=AUDIT/f'CACHE{number}_BUILD_AND_CONSUMER_CHAIN_V1.json';assert not out.exists()
    env=dict(os.environ,CUDA_VISIBLE_DEVICES='',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',
        MKL_NUM_THREADS='1',RAYON_NUM_THREADS='1',TOKENIZERS_PARALLELISM='false')
    phases=[]
    for phase in ['build','verify']:
        log=AUDIT/f'cache{number}_{phase}_runner_stdout_v1.log';assert not log.exists()
        print(json.dumps(dict(phase=phase,status='ACTUAL_SUBPROCESS_START',utc=datetime.now(timezone.utc).isoformat())),flush=True)
        with log.open('xb') as stream:
            result=subprocess.run([sys.executable,'-I','-B',str(Path(__file__)),'--config',str(path),
                '--expected-config-sha',config_sha,'--phase',phase],cwd=ROOT,env=env,stdout=stream,stderr=subprocess.STDOUT)
        phases.append(dict(phase=phase,process_exit_code=result.returncode,runner_log=str(log.relative_to(ROOT))))
        print(json.dumps(phases[-1]),flush=True)
        if result.returncode:break
    status='ACTUAL_BUILD_AND_CONSUMER_EXIT_ZERO' if len(phases)==2 and all(p['process_exit_code']==0 for p in phases) else 'FAILED_PHASE_PRESERVED_NO_OVERWRITE'
    with out.open('x',encoding='utf-8') as stream:
        json.dump(dict(status=status,phases=phases,configuration=dict(path=str(path.relative_to(ROOT)),sha256=config_sha),
            runner_sha256=sha(Path(__file__)),consumer_requires_actual_build_exit_zero=True,CPU_threads=1,
            goal_complete=False,training_authorized=False),stream,ensure_ascii=False,indent=2);stream.write(chr(10))
    raise SystemExit(0 if status=='ACTUAL_BUILD_AND_CONSUMER_EXIT_ZERO' else 1)
if args.phase=='build':
    proof_path=AUDIT/c['roster_proof'];assert sha(proof_path)==c['roster_proof_sha256']
    proof=json.loads(proof_path.read_bytes());assert proof['expected_cache_HOLD_positions']==c['expected_HOLD_positions']
    for name,expected in proof['input_pins'].items():assert sha(ROOT/name)==expected
    frozen=AUDIT/'run_guarded_partial_cache_v3.py'
    assert sha(frozen)=='098030E9811E363FAC8C1E1A513A7BCC91C5540301C06E0E9E817C75E85F4E84'
    replacements={'cache_reviewed_partial_v3':f'cache_reviewed_partial_v{number}',
        'CACHE_REVIEWED_PARTIAL_V3':f'CACHE_REVIEWED_PARTIAL_V{number}',
        'guarded_reviewed_cache_v4.py':'guarded_reviewed_cache_v5.py',
        'roster_reviewed_partial_v3':f'roster_reviewed_partial_v{roster}',
        'reviewed_partial_adoptions_v3':f'reviewed_partial_adoptions_v{roster}',
        'ROOT_AUTHORED_SELECTIONS_V11.json':f'ROOT_AUTHORED_SELECTIONS_V{selection}.json',
        'guarded_partial_proposals_v3':f'guarded_partial_proposals_v{roster}'}
else:
    frozen=AUDIT/'run_guarded_partial_cache_v4_consumer_v1.py'
    assert sha(frozen)=='C7E7FC46394EB9954B36FB95CC5F3E2EAADB8F81262DE3659531B5EA1992596F'
    replacements={'cache_reviewed_partial_v4':f'cache_reviewed_partial_v{number}',
        'CACHE_REVIEWED_PARTIAL_V4':f'CACHE_REVIEWED_PARTIAL_V{number}',
        'roster_reviewed_partial_v4':f'roster_reviewed_partial_v{roster}',
        'ROOT_AUTHORED_SELECTIONS_V12.json':f'ROOT_AUTHORED_SELECTIONS_V{selection}.json'}
code=frozen.read_text(encoding='utf-8')
for before,after in replacements.items():
    assert before in code;code=code.replace(before,after)
exec(compile(code,str(frozen),'exec'),dict(__name__='actual_versioned_CPU_cache_phase',__file__=str(Path(__file__))))
