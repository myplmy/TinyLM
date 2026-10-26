#!/usr/bin/env python3
"""완료 런처의 명령/원형을 보존하는 준비 단계이며 삭제는 하지 않는다."""
import argparse,contextlib,hashlib,io,json,re,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
import sync_experiments_tsv as s
if sys.flags.optimize:
    raise RuntimeError('archive preparation requires active invariant checks')
parser=argparse.ArgumentParser()
parser.add_argument('--suffix',default='v1')
parser.add_argument('--expected-count',type=int,default=28)
parser.add_argument('--names',nargs='+')
args=parser.parse_args()
if re.fullmatch(r'v[1-9][0-9]*',args.suffix) is None:
    raise ValueError('versioned manifest suffix required')
buffer=io.StringIO()
with contextlib.redirect_stdout(buffer):
    eligible=s.report_done(s.result_corpus())
print('eligible',len(eligible),'done_total',len(list(ROOT.glob('run_*-done.sh'))))
if args.names is not None:
    if len(set(args.names)) != len(args.names) or not set(args.names).issubset(eligible):
        raise ValueError('explicit completed launcher eligibility differs')
    eligible=sorted(args.names)
manifest=[]
dest=ROOT/'handoff/audit/oct26_research/launcher_archive'
dest.mkdir(parents=True,exist_ok=True)
for name in sorted(eligible):
    p=ROOT/name
    assert p.is_file() and not p.is_symlink() and p.name.endswith(('-done.sh','-done.bat'))
    raw=p.read_bytes()
    sha=hashlib.sha256(raw).hexdigest().upper()
    tracked=subprocess.run(['git','show','HEAD:'+name],cwd=ROOT,capture_output=True)
    tracked_source=name
    if tracked.returncode != 0 and name.endswith('-done.sh'):
        tracked_source=name[:-8]+'.sh'
        tracked=subprocess.run(['git','show','HEAD:'+tracked_source],cwd=ROOT,capture_output=True)
    if tracked.returncode==0:
        assert tracked.stdout==raw,'dirty tracked launcher: '+name
    else:
        assert name=='run_P106B_Stage6fW_gemma_capacity_probe-done.sh'
    q=dest/name
    if q.exists():
        assert q.read_bytes()==raw
    else:
        with q.open('xb') as out:
            out.write(raw)
    assert q.read_bytes()==raw
    manifest.append(dict(path=name,archive=str(q.relative_to(ROOT)),sha256=sha,bytes=len(raw),
        mode=p.stat().st_mode&0o777,commands=s.batch_commands(p),
        commands_present_in_result=True,tracked_before=tracked.returncode==0,tracked_source=tracked_source,
        rerun_disposition='NO_REUSE_OF_CLOSED_OR_EXPIRED_OUTPUT_NAMESPACE; future changes require a new explicit stage'))
assert len(manifest)==args.expected_count
target=ROOT/('handoff/audit/oct26_research/launcher_retirement_manifest_'+args.suffix+'.json')
with target.open('x',encoding='utf-8') as out:
    json.dump(dict(schema='TINYLM_CLOSED_LAUNCHER_RETIREMENT_V1',entries=manifest,
        approved_basis='사용자의 완료런처 명령보존 후 삭제 및 잔여런처 삭제가능성 판단·정리 지시',
        original_log_or_model_deletion=0,deletion='NOT_RUN'),out,ensure_ascii=False,indent=2)
    out.write('\n')
print('ARCHIVED',len(manifest),'bytes',sum(x['bytes'] for x in manifest),'manifest',target.relative_to(ROOT))

