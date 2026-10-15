#!/usr/bin/env python3
"""Same-case saved auxiliary-bit versus saved free-answer diagnosis; no training."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import argparse
from collections import Counter,defaultdict
from datetime import datetime,timezone
import gc
import json
import time
from scripts import diag_p106b_binding_auxiliary as auxiliary
from scripts import p106b_binding_auxiliary as method
from scripts import diag_p106b_prefix_probe as capture
from scripts.diag_p101a_mtp_parity import PrecisionForward
from scripts.p106b_gate_runtime import GateNegative,idle_before_gpu,wall_limit
from scripts.p106b_shards import ShardWriter,verify
from scripts.summarize_p106b_learning_pair import key
TAG='p106b_binding_readout_v1_s1337'
INPUTS=('p106b_binding_aux_v1_s1337','p106b_binding_scale_v1_s1337')


def known_bit(row):
    meta=row['meta'];mapping=meta.get('mapping',{});order=meta.get('ordered_entities',[]);asked=meta.get('requested_entity')
    if (meta.get('kind') not in ('binding_color','binding_department') or meta.get('rubric')!='EXACT_SCALAR'
            or meta.get('truth')!='PRODUCER_CODE_FACT_CONTRACT' or len(row['messages'])!=2
            or len(mapping)!=2 or len(set(mapping.values()))!=2 or len(order)!=2 or set(order)!=set(mapping)
            or asked not in mapping or auxiliary.base.data.text(row,-1)!=mapping[asked]):
        raise ValueError('frozen exact producer binding row required')
    return int(asked==order[0])


def contingency(values):
    counts=Counter();by_kind=defaultdict(Counter);roots=defaultdict(list)
    for value in values:
        if value['bit'] not in (0,1) or value['prediction'] not in (0,1) or type(value['free_exact']) is not bool:
            raise ValueError('binary labels and actual code free-judgment required')
        correct=value['prediction']==value['bit'];free=value['free_exact']
        increments=dict(cases=1,bit_correct=int(correct),free_correct=int(free))
        increments[f'bit_{int(correct)}_free_{int(free)}']=1
        counts.update(increments);by_kind[value['language']+':'+value['kind']].update(increments)
        roots[value['root']].append(correct)
    if not values or any(len(v)!=4 for v in roots.values()):raise ValueError('complete four-view roots required')
    counts.update(roots=len(roots),bit_all4_exact_roots=sum(all(v) for v in roots.values()))
    return dict(counts=dict(counts),by_kind={k:dict(v) for k,v in by_kind.items()},
        scope='same existing code test512; auxiliary bit is not a free-answer or truth score')


def execute(args):
    base=ROOT/'test_result/evidence'/args.tag;source=base/'fresh_test/report.json'
    report=auxiliary.required_json(source,'completed actual free-answer collection')
    if report['status']!='AUXILIARY_FRESH_TEST_COLLECTED':raise ValueError('actual completed auxiliary free answers required')
    corpus=ROOT/'HF/sft_ready'/args.tag/'corpus';frozen=auxiliary.required_json(corpus/'report.json','matching test corpus')
    verify(corpus,frozen['manifests']['test'])
    rows=[r for r in auxiliary.base.training.data.stream_rows(corpus,frozen['manifests']['test']) if r['meta']['kind'].startswith('binding_')]
    if len(rows)!=512:raise ValueError('same binding512 required')
    bits=[known_bit(row) for row in rows]
    target=ROOT/'test_result/evidence'/TAG/args.tag;local=ROOT/'test_result/evidence/local'/TAG/args.tag
    if target.exists() or local.exists():raise GateNegative('previous readout diagnosis preserved')
    subjects={};actual={}
    for arm,value in report['arms'].items():
        if arm=='parent':continue
        trained=auxiliary.required_json(base/arm/'report.json','completed actual trained arm')
        if trained['status']!='TRAINED_FRESH_TEST_PENDING':raise ValueError('completed trained arm prerequisite')
        if any(auxiliary.base.training.data.digest(ROOT/p)!=digest for p,digest in trained['code_sha256'].items()):
            raise ValueError('trained runtime code changed; preserve old result')
        path=ROOT/trained['checkpoint']
        if path.is_symlink() or auxiliary.base.training.data.digest(path)!=trained['checkpoint_sha256']:
            raise ValueError('exact saved checkpoint changed')
        subjects[arm]=trained
        folder=ROOT/value['raw_directory'];verify(folder,value['raw_manifest'])
        actual[arm]={key(r):r for r in auxiliary.base.training.data.stream_rows(folder,value['raw_manifest'])}
        for row in rows:
            signature=key(dict(messages=row['messages'][:-1]));saved=actual[arm].get(signature)
            if saved is None or saved['gold']!=auxiliary.base.data.text(row,-1) or type(saved['exact_code_contract']) is not bool:
                raise ValueError('same-case actual free-answer alignment failed')
    idle_before_gpu();began=time.perf_counter();summaries={};identities={}
    with wall_limit(args.max_wall_sec):
        for arm,trained in subjects.items():
            auxiliary.base.deadline();torch,model,cfg,tok,initial=auxiliary.base.training.load_runtime('parent_ntp')
            from tinylm.infer.generate import _strip
            from tinylm.chat.serialize import serialize
            state=torch.load(ROOT/trained['checkpoint'],map_location='cpu',weights_only=True)
            model.load_state_dict(_strip(state['model']),strict=True);head=method.new_head(cfg.dim,'cuda')
            head.load_state_dict(state['training_only_auxiliary'],strict=True);head.requires_grad_(False);del state
            before=auxiliary.base.training.state_fingerprint(model);model=capture.prepare_model(model)
            torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
            wrapped=PrecisionForward(model,'fp32_math');writer=ShardWriter(local/arm,'paired_bit_free');values=[];parity=None
            with torch.no_grad():
                for index,(row,bit) in enumerate(zip(rows,bits)):
                    auxiliary.base.deadline();prompt=serialize(dict(messages=row['messages'][:-1]),'chatml',add_generation_prompt=True)
                    ids=tok.encode(prompt).ids;x=torch.tensor([ids],device='cuda')
                    logits,hidden,kv=wrapped(x,use_cache=True,logits_last_only=True,return_mtp_hidden=True)
                    if hidden.shape!=(1,1,768):raise ValueError('last-prefix dense14 feature differs')
                    probability=head(hidden[0,-1]).float().softmax(-1)
                    if index==0:
                        plain,_=wrapped(x,use_cache=True,logits_last_only=True);parity=torch.equal(logits,plain)
                        if not parity:raise ValueError('hidden-return no-op logits parity failed')
                    signature=key(dict(messages=row['messages'][:-1]));saved=actual[arm][signature]
                    value=dict(root=row['meta']['semantic_root_id'],language=row['meta']['language'],kind=row['meta']['kind'],
                        bit=bit,prediction=int(probability.argmax()),probability_first=float(probability[1]),
                        free_exact=saved['exact_code_contract'],actual_free_answer=saved['answer'],gold=saved['gold'],
                        training_label_on_this_root=method.maybe_flip(bit,row['meta']['semantic_root_id'],trained['root_permuted']),
                        source_signature=signature,prefix_sha256=auxiliary.base.data.sha(ids),prefix_tokens=len(ids),
                        first_logit_token=int(logits[0,-1].argmax()),head_used_for_generation=False)
                    writer.append(value);values.append(value)
            manifest=writer.close(lineage=dict(input_tag=args.tag,arm=arm,precision='FP32_MATH_NO_TF32',
                cache=True,batch_size=1,model_prefix_has_answer_body=False,head_used_for_generation=False))
            verify(local/arm,manifest);model.clear_quant();after=auxiliary.base.training.state_fingerprint(model)
            if before!=after:raise ValueError('diagnosis changed backbone state')
            summaries[arm]=contingency(values);identities[arm]=dict(checkpoint=trained['checkpoint'],
                checkpoint_sha256=trained['checkpoint_sha256'],core_sha256_before=before,core_sha256_after=after,
                training_report_sha256=auxiliary.base.training.data.digest(base/arm/'report.json'),
                head_training_root_permuted=trained['root_permuted'],
                logits_parity=parity,raw_directory=str((local/arm).relative_to(ROOT)),raw_manifest=manifest)
            print('[PAIRED_BINDING_BIT_FREE] '+json.dumps(dict(arm=arm,summary=summaries[arm])),flush=True)
            del model,head,wrapped;gc.collect();torch.cuda.empty_cache()
    output=dict(schema='P106B_SAME_CASE_BINDING_READOUT_V1',tag=TAG,input_tag=args.tag,
        status='SAME_CASE_READOUT_COLLECTED',summaries=summaries,identities=identities,whole_sec=time.perf_counter()-began,
        source_report_sha256=auxiliary.base.training.data.digest(source),models_loaded=len(subjects),
        code_sha256={p:auxiliary.base.training.data.digest(ROOT/p) for p in
            ('scripts/diag_p106b_binding_readout.py','scripts/test_p106b_binding_readout.py',
             'scripts/diag_p106b_prefix_probe.py','scripts/diag_p101a_mtp_parity.py',
             'scripts/p106b_binding_auxiliary.py','tinylm/model/transformer.py','tinylm/train/mtp_sft.py')},
        optimizer_updates=0,checkpoint_saved=False,teacher_calls=0,actual_free_answers_regenerated=False,
        inference_mtp_tokens=1,auxiliary_head_used_to_generate_answers=False,
        interpretation='same-case observation, not causal proof/readout-only solution/general intelligence')
    auxiliary.base.training.write(target/'report.json',output);return 0


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--tag',choices=INPUTS,required=True)
    parser.add_argument('--max-wall-sec',type=int,default=600)
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--execute',action='store_true');group.add_argument('--check-only',action='store_true')
    args=parser.parse_args()
    if not 60<=args.max_wall_sec<=900:parser.error('bounded60..900')
    if args.check_only:print('[CHECK_ONLY] same-case binding bit/free; model0');return 0
    if not args.execute:parser.error('explicit execution required')
    try:
        auxiliary.base.deadline();remaining=int((auxiliary.base.DEADLINE-datetime.now(timezone.utc)).total_seconds())-600
        if remaining<60:raise GateNegative('17:00 deadline margin required')
        args.max_wall_sec=min(args.max_wall_sec,remaining);return execute(args)
    except GateNegative as exc:print('[BINDING_READOUT_HOLD] '+str(exc));return 8
    except KeyboardInterrupt:print('[BINDING_READOUT_INTERRUPTED] preserve raw');return 130
    except Exception as exc:print('[BINDING_READOUT_ERROR] '+type(exc).__name__+': '+str(exc));return 9


if __name__=='__main__':raise SystemExit(main())
