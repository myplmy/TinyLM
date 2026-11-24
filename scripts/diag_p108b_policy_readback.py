#!/usr/bin/env python3
"""CPU-only complete policy readback, retaining unsafe and weak controls."""
import json
import numpy as np
import torch
from scripts import diag_p108b_geometry as atlas
from scripts import diag_p108b_policy as owner
from scripts import p108b_policy as policy
from scripts import p108b_replay as replay
from scripts import diag_p108b_value_library as library
from scripts import interactive_research_infer as manual


def run():
    root=atlas.BASE;geometry=json.loads((root/'geometry/report.json').read_text(encoding='utf-8'))
    original=replay.read_arm('original');baseline={r['id']:r for r in original['answers']}
    correct={r['id']for r in original['answers']if r['protected']and r['split']!='select_dev'and r['exact']}
    names=[f'atlas_layer{i:02d}'for i in range(14)]
    names.extend(s['name']for s in owner.verify()['primary'])
    for directory in('policies_v1','support_v2','regularizer_v1'):
        for path in sorted((root/directory).glob('*/report.json')):
            name=json.loads(path.read_text(encoding='utf-8'))['name']
            if name not in names:names.append(name)
    records=[];refs={};reference_j=geometry['baseline']['objective']['J']
    for name in names:
        arm=replay.read_arm(name);answers=arm['answers']
        if len(answers)!=164 or {r['id']for r in answers}!=set(baseline):raise ValueError('exact closed164 questions required')
        if name.startswith('atlas_layer'):
            layer=int(name[-2:]);raw=geometry['layers'][layer]
            path=root/f'geometry/layer{layer:02d}/report.json';physical=raw['geometry']['cpu_physical']
            rounds=[];counts=raw['counts'];wall=None
        else:
            directory='support_v2'if name.startswith('SELECT_')else'regularizer_v1'if name.startswith(('REGINC_','REGTOTAL_'))else'policies_v1'
            path=root/directory/name/'report.json';raw=json.loads(path.read_text(encoding='utf-8'))
            physical=raw['physical'];rounds=raw.get('rounds',[]);counts=raw.get('counts_new',{});wall=raw.get('wall_seconds')
        refs[str(path.relative_to(atlas.ROOT))]=manual.file_sha(path)
        legacy=[r for r in answers if r['split']!='select_dev'];dev=[r for r in answers if r['split']=='select_dev']
        kept={r['id']for r in legacy if r['protected']and r['exact']}
        records.append(dict(name=name,core_sha256=arm['core_sha256'],objective=raw['objective'],
            objective_gain=reference_j-raw['objective']['J'],physical=physical,wall_seconds=wall,counts_new=counts,
            legacy_exact=sum(bool(r['exact'])for r in legacy),fit_exact=sum(bool(r['exact'])for r in legacy if r['split']=='fit'),
            protected_exact=len(kept),lost_original_protected_ids=sorted(correct-kept),gained_original_protected_ids=sorted(kept-correct),
            dev=policy.dev_summary(dev),legacy_unwanted_loops=policy.unwanted_loops(legacy),
            legacy_question_echoes=sum(r['diagnostics']['question_echo']for r in legacy),
            legacy_empty=sum(r['diagnostics']['empty']for r in legacy),
            round_transitions=[dict(round=r['round'],layer=r.get('layer'),alpha=r.get('alpha'),
                cap=r.get('cap'),predicted_gain=r.get('chosen_predicted_gain'),actual_gain=r.get('chosen_actual_gain'),
                prediction_residual=(r.get('chosen_actual_gain',0)-r.get('chosen_predicted_gain',0)),
                fit_exact=sum(bool(x['exact'])for x in r.get('fit_answers',[])),
                lost_previous_fit=r.get('retention',{}).get('lost_previous_ids',[]),physical=r.get('physical'),
                candidates=[dict(layer=c['layer'],score=c['score'],predicted_gain=c['predicted_gain'],
                    norm=c['physical']['step_norm'],support=c['support'])for c in r.get('candidates',[])],
                trials=[dict(layer=t['layer'],alpha=t['alpha'],predicted_gain=t.get('predicted_gain'),
                    actual_gain=t.get('actual_gain'),lost_protected_ids=t.get('lost_protected_ids',[]),
                    status=t.get('status'))for t in r.get('trials',[])])for r in rounds]))
    by={r['name']:r for r in records};contrasts=[]
    for left,right in [('atlas_layer09','REGTOTAL_SAME4'),('SAME4','REGINC_SAME4'),('ADAPT_R4','REGINC_ADAPT_R4'),('REGINC_ADAPT_R4','REGTOTAL_ADAPT_R4')]:
        a,b=replay.read_arm(left),replay.read_arm(right);layers=set(p['layer']for p in a['packets']+b['packets']);differences=[]
        for layer in sorted(layers):
            def after(arm):
                references=[p for p in arm['packets']if p['layer']==layer]
                if not references:return None
                return replay.load_packet(references[-1])['after']
            x,y=after(a),after(b)
            if x is not None and y is not None:
                delta=x.double()-y.double();differences.append(dict(layer=layer,max_abs=float(delta.abs().max()),
                    norm=float(delta.norm()),different_entries=int((x!=y).sum())))
            else:differences.append(dict(layer=layer,status='LAYER_PRESENT_IN_ONLY_ONE_GLOBAL_STATE'))
        contrasts.append(dict(left=left,right=right,exact_core_equal=a['core_sha256']==b['core_sha256'],
            objective_difference=by[right]['objective']['J']-by[left]['objective']['J'],layer_differences=differences))
    result=dict(schema='P108B_COMPLETE_POLICY_CPU_READBACK_V1',new_gpu_execution=False,references=refs,
        original_protected_correct_ids=sorted(correct),baseline_objective=geometry['baseline']['objective'],
        global_weight_labels=len(records),records=records,regularizer_numerical_contrasts=contrasts,
        computational_caveat='fixed vs adaptive have different actual trial/generation cost and guard policy; no pure same-compute superiority claim',
        statistical_scope='one completed model, correlated FACT/FIT and reused legacy protection; DEV is model selection, not blind FINAL')
    library.write_new(atlas.ROOT/'handoff/audit/nov16_p108b/POLICY_READBACK_v1.json',result)
    for r in records:
        print(json.dumps(dict(name=r['name'],fit=r['fit_exact'],legacy=r['legacy_exact'],dev=r['dev']['target_exact'],
            protect=r['protected_exact'],lost=r['lost_original_protected_ids'],J=r['objective']['J'],
            net=r['physical']['net_norm'],path=r['physical'].get('path_norm'),loops=r['dev']['unwanted_loops']),ensure_ascii=False))
    print(json.dumps(contrasts))


if __name__=='__main__':run()
