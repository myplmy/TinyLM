#!/usr/bin/env python3
"""Paired incremental/total preservation using one unchanged controller body.

The inner source_profile_sha256 remains the base-controller profile. Each arm
gets an additional immutable method_profile_link.json binding this profile,
the solver override and the unchanged controller bytecode. No old report is
rewritten to hide the additional condition.
"""
import argparse
from dataclasses import asdict,replace
from functools import partial
import json
from types import SimpleNamespace

from scripts import diag_p108b_policy as owner
from scripts import diag_p108b_value_library as library
from scripts import p108b_policy as policy
from scripts import p108b_quadratic as quadratic
from scripts import p108b_decode as function_tools
from scripts import interactive_research_infer as manual

BASE=owner.BASE
OUT=BASE/'regularizer_v1'
SOURCES=('scripts/p108b_quadratic.py','scripts/test_p108b_quadratic.py',
         'scripts/diag_p108b_regularizer.py','scripts/test_p108b_regularizer.py',
         'scripts/p108b_decode.py','scripts/test_p108b_decode.py')


def specs():
    original={s.name:s for s in policy.primary_policies()}
    return [replace(original[name],name=prefix+'_'+name)for prefix in('REGINC','REGTOTAL')for name in('SAME4','ADAPT_R4')]


def prepare():
    p=owner.verify();sources=dict(p['sources']);sources.update({n:manual.file_sha(owner.ROOT/n)for n in SOURCES})
    profile=dict(p,schema='P108B_PRESERVATION_ORIGIN_V1',sources=sources,primary=[asdict(s)for s in specs()],diagnostic=[],
        parent_profile_sha256=manual.file_sha(BASE/'policy_profile_v1.json'),max_phase_seconds=7200,
        regularizer_modes=['CURRENT_INCREMENT','ORIGINAL_CUMULATIVE_DISPLACEMENT'],
        same_controller_body=True,new_quadratic_energy_search='eigenbasis norm, no dense reconstruction during bisection',
        inner_source_profile_field='BASE_CONTROLLER_PROFILE; mandatory per-arm method_profile_link binds override',
        initial_plan_sha256=manual.file_sha(owner.ROOT/library.PLAN),final_answers_consumed=False)
    library.write_new(BASE/'regularizer_profile_v1.json',profile)
    with (BASE/'regularizer_initial_plan_v1.md').open('xb')as stream:stream.write((owner.ROOT/library.PLAN).read_bytes())
    print('[REGULARIZER_PREPARED] paired SAME4/ADAPT_R4, same controller and norm budget',flush=True)


def verify():
    owner.verify();p=json.loads((BASE/'regularizer_profile_v1.json').read_text(encoding='utf-8'));library.Budget().check()
    for name,sha in p['sources'].items():
        if manual.file_sha(owner.ROOT/name)!=sha:raise ValueError('regularizer source changed: '+name)
    if manual.file_sha(BASE/'policy_profile_v1.json')!=p['parent_profile_sha256']:raise ValueError('base controller profile changed')
    if manual.file_sha(BASE/'regularizer_initial_plan_v1.md')!=p['initial_plan_sha256']:raise ValueError('initial regularizer plan changed')
    return p


def controller(total):
    solve=partial(quadratic.solve_increment,total_preservation=total)
    solver=SimpleNamespace(solve_increment=solve,physical_change=quadratic.physical_change,
        predicted_gain=quadratic.predicted_gain,remaining_layer_budget=quadratic.remaining_layer_budget,
        select_support=quadratic.select_support)
    proposal=function_tools.private_function(owner.propose,solver=solver)
    return function_tools.private_function(owner.run,OUT=OUT,verify=verify,propose=proposal,solver=solver)


def actual(mode):
    p=verify();prefix='REGTOTAL'if mode=='total'else'REGINC'
    names=[s['name']for s in p['primary']if s['name'].startswith(prefix+'_')]
    if len(names)!=2:raise ValueError('exact paired two-arm panel required')
    controller(mode=='total')(names)
    for name in names:
        path=OUT/name/'report.json'
        record=json.loads(path.read_text(encoding='utf-8'))
        if not record.get('original_restored'):raise ValueError('closed original-restored arm required')
        library.write_new(OUT/name/'method_profile_link.json',dict(
            schema=p['schema'],mode=mode,report_sha256=manual.file_sha(path),
            method_profile_sha256=manual.file_sha(BASE/'regularizer_profile_v1.json'),
            base_controller_profile_sha256=p['parent_profile_sha256'],
            controller_bytecode_reused=True,quadratic_source_sha256=p['sources']['scripts/p108b_quadratic.py'],
            inner_source_profile_field_is_base=True,final_answers_consumed=False))


def main():
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=['prepare','check','actual'])
    parser.add_argument('--mode',choices=['incremental','total']);a=parser.parse_args()
    if a.phase=='prepare':prepare()
    elif a.phase=='check':verify();print('[REGULARIZER_CHECK] sealed paired profiles, no model')
    else:
        if a.mode is None:parser.error('explicit incremental or total mode required')
        actual(a.mode)


if __name__=='__main__':main()
