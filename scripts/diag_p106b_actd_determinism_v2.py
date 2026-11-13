"""Reuse sealed deterministic execution with an exact teacher-provenance mirror."""
import argparse
import hashlib
import json
from pathlib import Path
from types import FunctionType
import unittest
from scripts import diag_p106b_actd_determinism as first

ROOT=first.ROOT;TAG='p106b_actd_determinism_v2_20261113';BASE=ROOT/'test_result/evidence'/TAG
SOURCES=('scripts/diag_p106b_actd_determinism_v2.py','scripts/test_p106b_actd_determinism_v2.py')


def teacher_reference(raw,expected_sha):
    digest=hashlib.sha256(raw).hexdigest().upper()
    if digest!=expected_sha:raise ValueError('teacher provenance copy bytes changed')
    r=json.loads(raw.decode('utf-8'))
    if r.get('status')!='ACTD_NATIVE_TOP128_COMPLETE' or r.get('returncode')!=0 or r.get('rows_completed')!=128:
        raise ValueError('same complete native teacher128 report required')
    return digest


def build_runner(destination=BASE):
    runner=first.build_runner(destination);runner.__globals__['d'].TAG=TAG
    return runner


def prepare():
    first.verify();first.old.d.guard()
    if BASE.exists():raise FileExistsError('fresh deterministic V2 namespace required')
    failure=json.loads((first.BASE/'ROOT_PREMODEL_FAILURE_v1.json').read_text())
    if failure['actual_tool_exit']!=1 or failure['gpu_model_calls']!=0:raise ValueError('preserved original provenance-path error required')
    from scripts.test_p106b_actd_determinism_v2 import MirrorContracts
    result=unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.loadTestsFromTestCase(MirrorContracts))
    if not result.wasSuccessful() or result.testsRun!=2:raise RuntimeError('mirror CPU2 incomplete')
    teacher=first.old.d.BASE/'teacher/report.json';raw=teacher.read_bytes();sha=teacher_reference(raw,first.old.d.inventory.digest(teacher))
    mirror=BASE/'teacher/report.json';mirror.parent.mkdir(parents=True)
    with mirror.open('xb')as target:target.write(raw)
    # Exercise the exact relocated reader used by the immutable run before GPU entry.
    runner=build_runner()
    if runner.__globals__['d'].inventory.digest(runner.__globals__['d'].BASE/'teacher/report.json')!=sha:
        raise ValueError('immutable consumer relocated teacher reader mismatch')
    paths=[first.BASE/'profile.json',first.BASE/'ROOT_PREMODEL_FAILURE_v1.json',teacher]
    paths.extend(ROOT/s for s in SOURCES)
    first.old.d.write_new(BASE/'profile.json',dict(tag=TAG,authority_directive=115,deadline=first.old.d.DEADLINE.isoformat(),
        sources={str(p.relative_to(ROOT)):first.old.d.inventory.digest(p)for p in paths},teacher_mirror_sha256=sha,
        original_teacher_cache_used=True,teacher_reruns=0,model_calls=0,cpu_tests=2,
        old_consumer_code_reused=True,old_deterministic_policy_reused=True,optimizer_updates=0,checkpoint_writes=0,
        quality_claim=False))
    print('[ACTD_DETERMINISM_V2_PREPARED] '+TAG,flush=True)


def verify():
    first.verify();p=json.loads((BASE/'profile.json').read_text())
    if p['authority_directive']!=115 or p['deadline']!=first.old.d.DEADLINE.isoformat():raise ValueError('authority changed')
    for name,sha in p['sources'].items():
        if first.old.d.inventory.digest(ROOT/name)!=sha:raise ValueError('V2 sealed reference changed: '+name)
    if first.old.d.inventory.digest(BASE/'teacher/report.json')!=p['teacher_mirror_sha256']:
        raise ValueError('copied teacher provenance differs')
    return p


def run():
    runner=FunctionType(first.run.__code__,dict(first.run.__globals__,BASE=BASE,build_runner=build_runner,verify=verify),
                        first.run.__name__,first.run.__defaults__)
    runner()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=['prepare','actual']);args=parser.parse_args()
    (prepare if args.phase=='prepare'else run)()


if __name__=='__main__':main()
