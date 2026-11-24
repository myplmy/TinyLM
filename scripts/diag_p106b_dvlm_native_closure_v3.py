"""Explicit case0 closure/shape diagnostic around the immutable native v1 driver.

Only the output namespace, lossless report serializer and predeclared case0
selection change. Deadlines, input/source guards, native math and tolerances do
not change. The other7 cases are not resumed or counted as complete.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import unittest

from scripts import diag_p106b_dvlm_native as prior
from scripts.diag_p106b_external_core6 import write_json

ROOT=prior.ROOT
V1BASE=prior.BASE
NEWBASE=ROOT/'test_result/evidence/p106b_dvlm_native_closure_v3_20261117'
NEWPROFILE=NEWBASE/'profile.json'
SCHEMA='P106B_DVLM_FAILED_CASE0_CLOSURE_V3'
_PREREQUISITES=prior.prerequisite_cases
_NATIVE_CASE=prior.native.native_case
LINEAGE=None


def plain_strings(value):
    """Normalize primitive string subclasses, not arbitrary unknown objects."""
    if isinstance(value,str):return str(value)
    if isinstance(value,dict):return {plain_strings(key):plain_strings(item) for key,item in value.items()}
    if isinstance(value,list):return [plain_strings(item) for item in value]
    if isinstance(value,tuple):return tuple(plain_strings(item) for item in value)
    if isinstance(value,set):return {plain_strings(item) for item in value}
    if isinstance(value,frozenset):return frozenset(plain_strings(item) for item in value)
    return value


def select_case0(cases,evidence):
    if (len(cases)!=8 or not cases or cases[0]['row_id']!=evidence['row_id']
            or evidence['ordinal']!=0 or evidence['report']['passed'] is not False):
        raise ValueError('only the original negative first case of original8 may enter closure recovery')
    return cases[:1]


def write_scoped(path,value):
    path=Path(path)
    if not path.resolve().is_relative_to(NEWBASE.resolve()):
        raise ValueError('closure serializer must not write outside its new owned namespace')
    enriched=dict(value)
    enriched.update(scope_role='ONE_ORIGINAL_FAILED_CASE0_CLOSURE_AND_SHAPE_DIAGNOSTIC_ONLY',
        original_remaining_cases_NOT_RUN=7,original_v1_memory_closure_retroactively_recovered=False,
        original_gate_or_deadline_changed=False,closure_lineage=LINEAGE,new_closure_contracts=7,
        primitive_string_subclasses_normalized=True)
    if path.name in ('profile.json','report.json') and enriched.get('expected_cases')!=1:
        raise ValueError('closure profile/report must declare exactly1 diagnostic case, never8')
    if path.name=='report.json':
        enriched['status']=enriched.get('status','').replace('NATIVE_HPA','CASE0_CLOSURE_DIAGNOSTIC')
    try:
        write_json(path,plain_strings(enriched))
    except Exception as error:
        if path.name=='report.json':
            minimal=dict(schema=SCHEMA,status='CASE0_REPORT_WRITE_ERROR',returncode=9,
                original_primary_status=enriched.get('status'),original_primary_returncode=enriched.get('returncode'),
                error=dict(type=type(error).__name__,message=str(error)),expected_cases=1,
                original_remaining_cases_NOT_RUN=7,quality_claim=False,closure_lineage=LINEAGE)
            fallback=path if not path.exists() else path.with_name('report_closure_failure.json')
            write_json(fallback,plain_strings(minimal))
        raise


def shape_case(torch,model,layout,*,atol,rtol,guard=lambda:None):
    report,packet=_NATIVE_CASE(torch,model,layout,atol=atol,rtol=rtol,guard=guard)
    guard()
    n,t=len(layout.input_ids),layout.teacher_count
    pad=model.config.pad_token_id
    if pad is None:pad=0
    device=next(model.parameters()).device
    ids=torch.tensor([layout.input_ids[:t]+(pad,)*(n-t)],dtype=torch.long,device=device)
    valid=torch.tensor([[1]*t+[0]*(n-t)],dtype=torch.long,device=device)
    padded=model.model(input_ids=ids,attention_mask=valid,use_cache=False).last_hidden_state[0,:t].detach().cpu()
    compare=lambda a,b:prior.native.compare_hidden(torch,a,b,atol=atol,rtol=rtol)
    controls=dict(native_physical_length=t,padded_native_physical_length=n,
        standard_native_vs_standard_padded=compare(packet['serial_native'],padded),
        PTS_native_vs_standard_padded=compare(packet['pts_native'],padded),
        same_first_token_applicable=layout.input_ids[0]==layout.input_ids[t] and layout.position_ids[t]==0,
        affects_original_passed_gate=False,quality_claim=False,
        interpretation='Controlled numerical geometry diagnostics only; original FP32 HPA/serial gate remains unchanged.')
    if controls['same_first_token_applicable']:
        controls['same_first_token_within_PTS']=compare(packet['pts_native'][:1],packet['pts_private'][:1])
        controls['same_first_token_two_standard_references']=compare(packet['serial_native'][:1],packet['serial_private'][:1])
    report['shape_controls']=controls
    packet['standard_padded_native']=padded
    return report,packet


def bind_new_version():
    global LINEAGE
    if prior.BASE!=V1BASE:
        raise RuntimeError('bind once in a fresh process; never rebind an active driver')
    original,cases=prior.verify()
    case_path=V1BASE/'actual/case000_report.json'
    evidence=prior.admission.read(case_path)
    select_case0(cases,evidence)
    if (V1BASE/'actual/report.json').exists():
        raise ValueError('expected original missing main report; do not overwrite or reinterpret a new report')
    failure=ROOT/'handoff/audit/research_20261117_01a1e647/DVLM_NATIVE_GPU_PARTIAL_FAILURE_v1.json'
    closed=prior.admission.read(failure)
    if closed['actual_shell_exit']!=1 or closed['remaining_cases_NOT_RUN']!=7 or not closed['process_terminal']:
        raise ValueError('closed original operational/numerical failure evidence required')
    LINEAGE=dict(original_profile=dict(path=str((V1BASE/'profile.json').relative_to(ROOT)),sha256=prior.admission.digest(V1BASE/'profile.json')),
        original_case=dict(path=str(case_path.relative_to(ROOT)),sha256=prior.admission.digest(case_path)),
        original_packet=evidence['packet'],failure_receipt=dict(path=str(failure.relative_to(ROOT)),sha256=prior.admission.digest(failure)),
        original_selected_count=8,executed_case_ids=[evidence['row_id']],case0_only=True,
        immutable_v1_source=True,source_guards_deadline_tolerance_unchanged=True)
    def only_original_case0():
        cpu,report,all_cases=_PREREQUISITES()
        return cpu,report,select_case0(all_cases,prior.admission.read(case_path))
    prior.BASE=NEWBASE
    prior.PROFILE=NEWPROFILE
    prior.SCHEMA=SCHEMA
    prior.SOURCES=prior.SOURCES+('scripts/diag_p106b_dvlm_native_closure_v3.py','scripts/test_p106b_dvlm_native_closure_v3.py')
    prior.prerequisite_cases=only_original_case0
    prior.native.native_case=shape_case
    prior.admission.write_new=write_scoped


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('prepare','check','actual'))
    action=parser.parse_args().action
    bind_new_version()
    if action=='prepare':
        checked=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromName('scripts.test_p106b_dvlm_native_closure_v3'))
        if not checked.wasSuccessful() or checked.testsRun!=7:
            raise RuntimeError('all7 new closure/selection contracts required')
        with prior.wall_limit(600):prior.prepare()
    else:
        profile=prior.admission.read(NEWPROFILE)
        if (profile.get('closure_lineage')!=LINEAGE or profile.get('original_remaining_cases_NOT_RUN')!=7
                or profile.get('scope_role')!='ONE_ORIGINAL_FAILED_CASE0_CLOSURE_AND_SHAPE_DIAGNOSTIC_ONLY'):
            raise ValueError('exact closure lineage and original7 NOT_RUN required')
        if action=='check':prior.verify();print('[CASE0_CLOSURE_CHECK]original gate unchanged;other7 not resumed')
        else:return prior.actual()
    return 0


if __name__=='__main__':
    sys.modules.setdefault('scripts.diag_p106b_dvlm_native_closure_v3',sys.modules[__name__])
    raise SystemExit(main())

