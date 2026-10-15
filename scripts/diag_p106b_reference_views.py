#!/usr/bin/env python3
"""Same dev-selected body and16 questions; reference layout only, no learning."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import argparse
import copy
from datetime import datetime,timezone
import json
import time
from scripts import diag_p106b_state_update_aux as state
from scripts import p106b_reference_views as method
from scripts.p106b_shards import verify
from scripts.p106b_gate_runtime import idle_before_gpu,wall_limit,GateNegative
TAG='p106b_reference_views_v1_s1337'
SOURCE=ROOT/'test_result/evidence/p106b_binding_aux_v1_s1337/fresh_test/report.json'
EVIDENCE=ROOT/'test_result/evidence'/TAG
LOCAL=ROOT/'test_result/evidence/local'/TAG
CODE=('scripts/p106b_reference_views.py','scripts/test_p106b_reference_views.py','scripts/diag_p106b_reference_views.py')


def inputs():
    r=json.loads(SOURCE.read_text());parent=state.parent_ref(True)
    if r['status']!='AUXILIARY_FRESH_TEST_COLLECTED' or r['public_cases_per_arm']!=16:raise ValueError('completed earlier16 dev cases required')
    original=r['public_qa'][parent['arm']];folder=ROOT/original['raw_directory'];verify(folder,original['raw_manifest'])
    saved=[json.loads(line) for spec in original['raw_manifest']['shards'] for line in (folder/spec['path']).read_text().splitlines()]
    if len(saved)!=16:raise ValueError('exact16 original dev rows required')
    for path in ('tinylm/model/transformer.py','tinylm/infer/generate.py','scripts/diag_p101a_mtp_parity.py','scripts/diag_p106b_binding_auxiliary.py'):
        if state.driver.base.training.data.digest(ROOT/path)!=r['code_sha256'][path]:raise ValueError('saved full-path implementation changed')
    rows=[]
    for raw in saved:
        messages=copy.deepcopy(raw['messages'])+[dict(role='assistant',content=[dict(type='text',text=raw['gold'])])]
        rows.append(dict(messages=messages,meta=copy.deepcopy(raw['meta'])))
    variants={name:[method.view(row,name) for row in rows] for name in ('full','selected','empty')}
    if any(a['messages']!=b['messages'] for a,b in zip(rows,variants['full'])):raise ValueError('exact full16 messages required')
    return parent,original,saved,variants


def main():
    p=argparse.ArgumentParser(description=__doc__);mode=p.add_mutually_exclusive_group(required=True)
    mode.add_argument('--execute',action='store_true');mode.add_argument('--check-only',action='store_true')
    p.add_argument('--max-wall-sec',type=int,default=600);args=p.parse_args()
    if not 60<=args.max_wall_sec<=600:p.error('bounded60..600')
    state.driver.base.deadline();parent,original,saved,variants=inputs()
    if EVIDENCE.exists() or LOCAL.exists():raise FileExistsError('previous reference diagnostic retained')
    lengths={k:[len(v['messages'][0]['content'][0]['text']) for v in rows] for k,rows in variants.items()}
    from tokenizers import Tokenizer
    from tinylm.chat.serialize import serialize
    from tinylm.train.mtp_sft import encode_record
    training=state.driver.base.training
    if training.data.digest(training.data.TOKENIZER)!=training.data.TOK_SHA:raise ValueError('pinned tokenizer changed')
    tokenizer=Tokenizer.from_file(str(training.data.TOKENIZER))
    prefix_tokens={k:[len(tokenizer.encode(serialize(dict(messages=v['messages'][:-1]),'chatml',add_generation_prompt=True)).ids) for v in rows]
        for k,rows in variants.items()}
    targets={k:[encode_record(v,tokenizer).targets for v in rows] for k,rows in variants.items()}
    if any(values!=targets['full'] for values in targets.values()):raise ValueError('same teacher target token counts required')
    changed=[i for i,(a,b) in enumerate(zip(variants['full'],variants['selected'])) if a['messages']!=b['messages']]
    if args.check_only:
        print('[REFERENCE_VIEW_PREFLIGHT] '+json.dumps(dict(parent=parent,cases=16,characters=lengths,prefix_tokens=prefix_tokens,
            targets=targets['full'],selected_changed_indices=changed,identical_prompt_controls=16-len(changed),model_loaded=False,student_training_allowed=False)),flush=True);return 0
    if not args.execute:p.error('explicit execution required')
    if (state.driver.base.DEADLINE-datetime.now(timezone.utc)).total_seconds()<args.max_wall_sec+2700:
        raise GateNegative('retain closing margin before17')
    idle_before_gpu();began=time.perf_counter();observed={};seconds={}
    with wall_limit(args.max_wall_sec):
        torch,model,cfg,tok,initial=state.load_from_parent('parent_ntp');model=model.cuda()
        for variant,rows in variants.items():
            state.driver.base.deadline();torch.cuda.synchronize();tick=time.perf_counter()
            observed[variant]=state.driver.generate_public(model,cfg,tok,rows,LOCAL/variant)
            torch.cuda.synchronize();seconds[variant]=time.perf_counter()-tick
        full=observed['full'];folder=ROOT/full['raw_directory'];verify(folder,full['raw_manifest'])
        actual=[json.loads(line) for spec in full['raw_manifest']['shards'] for line in (folder/spec['path']).read_text().splitlines()]
        if len(actual)!=16:raise ValueError('full repeat16 absent')
        repeated=[a['answer']==b['answer'] for a,b in zip(saved,actual)]
        final=state.driver.base.training.state_fingerprint(model)
        if initial!=final:raise ValueError('reference display probe changed body')
        result=dict(schema='P106B_REFERENCE_VIEW_DEVELOPMENT_V1',tag=TAG,status='REFERENCE_VIEWS_COLLECTED',
            parent=parent,source_report_sha256=state.driver.base.training.data.digest(SOURCE),source_raw=original,
            code_sha256={v:state.driver.base.training.data.digest(ROOT/v) for v in CODE},
            variants=observed,characters=lengths,prefix_tokens=prefix_tokens,teacher_target_tokens=targets['full'],
            selected_changed_indices=changed,identical_prompt_controls=16-len(changed),
            variant_seconds=seconds,full_repeat_exact=sum(repeated),
            full_repeat_changed_indices=[i for i,v in enumerate(repeated) if not v],
            current_reference_ids={k:[row['meta']['current_reference_ids'] for row in values] for k,values in variants.items()},
            body_before=initial,body_after=final,whole_sec=time.perf_counter()-began,
            optimizer_updates=0,checkpoints_saved=0,student_training_allowed=False,source_world_truth='NOT_REVIEWED',
            quality_scope='agreement with stored teacher reference only, not semantic correctness; empty reference unscored',
            timing_scope='fixed full/selected/empty order, not counterbalanced performance benchmark',
            scope='posthoc same16 development diagnostic; no new teacher, learning, online filter or general-improvement claim')
        state.driver.base.training.write(EVIDENCE/'report.json',result)
    print('[REFERENCE_VIEW_COLLECTION] '+json.dumps(dict(status=result['status'],counts={k:v['counts'] for k,v in observed.items()},
        full_repeat_exact=sum(repeated),seconds=seconds,whole_sec=result['whole_sec'],updates=0)),flush=True);return 0


if __name__=='__main__':raise SystemExit(main())
