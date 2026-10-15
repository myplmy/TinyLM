#!/usr/bin/env python3
"""V2 runtime adapter; immutable v1 rows with an exact indexed-native contract."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import argparse
import copy
import json
from scripts import diag_p106b_relation_interleaved_course as data
from scripts.p106b_native_windows import reader
from scripts.p106b_gate_runtime import GateNegative
base=data.base
prior=data.prior
training=data.training
factory=data.factory
PARENT,PARENT_SHA=data.PARENT,data.PARENT_SHA
TAG='p106b_relation_interleaved_v2_s1337'
CORPUS=data.CORPUS
EVIDENCE=ROOT/'test_result/evidence'/TAG
DATA_SHA='C65A23494178FB3C86409F3A2D25F9766C8977C4E1D72C63E5C9885A643108B8'
CODE=(*data.CODE,'scripts/diag_p106b_relation_interleaved_train.py','scripts/test_p106b_relation_interleaved_train.py',
    'scripts/diag_p106b_relation_interleaved_runtime_v2.py','scripts/test_p106b_relation_native_contract_v2.py')


def info():
    r=data.info();r.update(schema='P106B_RELATION_INTERLEAVED_RUNTIME_V2',tag=TAG,
        code_sha256={p:training.data.digest(ROOT/p) for p in sorted(set(CODE))},
        source_data_tag=data.TAG,source_data_report_sha256=DATA_SHA,
        repair='copy exact native_access from original indexed source; no example/objective changes',
        previous_failure='Stage4cb2W KeyError native_copy before updates; old namespace untouched')
    return r


def repaired_contract(contract,source):
    result=copy.deepcopy(contract)
    if source.get('native_access')!='INDEXED_TRAIN_ONLY':raise ValueError('exact original indexed native mode required')
    for k in ('native_train_file','native_train_offsets','native_train_sha256','native_val_sha256'):
        if result[k]!=source[k]:raise ValueError('unchanged native source contract required: '+k)
    result['native_access']=source['native_access']
    return result


def metadata_contract():
    if training.data.digest(CORPUS/'report.json')!=DATA_SHA:raise ValueError('immutable v1 dataset report changed')
    original=json.loads((CORPUS/'report.json').read_text())
    source=json.loads((base.CORPUS/'report.json').read_text())
    if training.data.digest(base.CORPUS/'report.json')!=original['source_course_report_sha256']:raise ValueError('original indexed source report changed')
    return original,source,repaired_contract(original,source)


def verify_native():
    import numpy as np
    original,source,fixed=metadata_contract()
    try:reader(ROOT,original)
    except KeyError as exc:
        if exc.args!=('native_copy',):raise
        reproduced=True
    else:raise ValueError('expected preserved v1 missing native_access was not reproduced')
    correct,expected=reader(ROOT,fixed),reader(ROOT,source)
    if len(correct)!=5504 or len(expected)!=5504:raise ValueError('same full native schedule required')
    indices=list(range(8))+list(range(len(correct)-8,len(correct)))
    if not all(np.array_equal(correct[i],expected[i]) for i in indices):raise ValueError('real indexed read values differ')
    if correct.tokens.flags.writeable:raise ValueError('native memory map must remain read-only')
    return dict(original_missing_marker_reproduced=reproduced,real_reader_verified=True,
        windows_compared=len(indices),tokens_per_window=1025,full_schedule_windows=len(correct),
        exact_source_mode=fixed['native_access'],cache_read_only=True,cache_copies=0,
        source_data_report_sha256=DATA_SHA,source_native_report_sha256=training.data.digest(base.CORPUS/'report.json'))


def write_verification():
    target=EVIDENCE/'runtime_reader_contract.json'
    if target.exists():raise GateNegative('old v2 reader proof preserved')
    report=dict(info(),status='CPU_REAL_NATIVE_READER_VERIFIED',observation=verify_native(),
        model_loading='NOT_RUN',optimizer_updates=0,new_checkpoints=0)
    training.write(target,report)
    print('[INTERLEAVED_NATIVE_V2] '+json.dumps(report['observation']),flush=True);return 0


def read_course():
    proof=prior.producer.legacy.source.required(EVIDENCE/'runtime_reader_contract.json')
    if proof['code_sha256']!=info()['code_sha256'] or proof['status']!='CPU_REAL_NATIVE_READER_VERIFIED':raise GateNegative('same-code actual CPU reader proof required')
    metadata_contract()
    r,rows,labels=data.read_course();source=json.loads((base.CORPUS/'report.json').read_text())
    fixed=repaired_contract(r,source);fixed['runtime_schema']='P106B_RELATION_INTERLEAVED_RUNTIME_V2'
    fixed['runtime_contract_proof_sha256']=training.data.digest(EVIDENCE/'runtime_reader_contract.json')
    return fixed,rows,labels


def main():
    p=argparse.ArgumentParser(description=__doc__);g=p.add_mutually_exclusive_group(required=True);g.add_argument('--execute',action='store_true');g.add_argument('--check-only',action='store_true');a=p.parse_args()
    if a.check_only:print('[INTERLEAVED_RUNTIME_V2_CHECK_ONLY] '+json.dumps(info()));return 0
    try:
        prior.producer.legacy.source.deadline();return write_verification()
    except GateNegative as exc:print('[INTERLEAVED_RUNTIME_V2_HOLD] '+str(exc));return 8
    except Exception as exc:
        import traceback
        traceback.print_exc();print('[INTERLEAVED_RUNTIME_V2_ERROR] '+str(exc));return 9


if __name__=='__main__':raise SystemExit(main())
