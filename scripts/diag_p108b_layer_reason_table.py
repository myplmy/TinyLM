"""Reuse every closed atlas raw answer for a readable layer-selection table."""
import json
from pathlib import Path
import numpy as np
from scripts import diag_p108b_geometry as atlas
from scripts import diag_p108b_policy as io
from scripts import p108_weight_space as metrics
from scripts import interactive_research_infer as manual
from scripts import diag_p108b_value_library as library


def run():
    root=atlas.ROOT;source=atlas.BASE/'geometry';report=json.loads((source/'report.json').read_text())
    if len(report['layers'])!=14 or not report['registered_core_unchanged']:raise ValueError('closed complete14 atlas required')
    old=io.read_answers(source,report['baseline']['answers_manifest'])
    required={r['id']for r in old if r['split']!='select_dev'and r['protected']and r['exact']}
    if len(required)!=7:raise ValueError('exact seven original-correct legacy guards')
    records=[]
    for record in report['layers']:
        layer=record['layer'];rows=io.read_answers(source/f'layer{layer:02d}',record['answers_manifest'])
        if len(rows)!=164 or {x['id']:x['question']for x in rows}!={x['id']:x['question']for x in old}:
            raise ValueError('same ordered atlas input identities required')
        fit=metrics.summarize([x for x in rows if x['split']=='fit'])
        dev=metrics.summarize([x for x in rows if x['split']=='select_dev'and x['family']=='target'])
        current={x['id']for x in rows if x['split']!='select_dev'and x['protected']and x['exact']}
        records.append(dict(layer=layer,predicted_gain=record['predicted_gain'],actual_gain=record['actual_gain'],
            signed_error=record['predicted_gain']-record['actual_gain'],fit_exact=fit['exact'],fit_n=fit['items'],
            dev_target_exact=dev['exact'],dev_target_n=dev['items'],old7_lost_ids=sorted(required-current),
            materialized_budget=record['geometry']['cpu_physical'],actual_core_sha256=record['after_core_sha256']))
    def correlation(a,b):
        x=np.asarray(a,dtype=float);y=np.asarray(b,dtype=float)
        return None if not x.std()or not y.std() else float(np.corrcoef(x,y)[0,1])
    result=dict(schema='P108B_ALL14_ACTUAL_SELECTION_REASONS_V1',source_report_sha256=manual.file_sha(source/'report.json'),
        model='new595-broad-f',scope='all14 MLP down matrices,not every parameter type;closed raw answers reused,no new model execution',
        original_common_net_budget=report['common_budget'],rows=records,existing_selection=report['selection'],
        correlations=dict(predicted_vs_actual_J_gain=correlation([x['predicted_gain']for x in records],[x['actual_gain']for x in records]),
            actual_J_gain_vs_FIT_exact=correlation([x['actual_gain']for x in records],[x['fit_exact']for x in records]),
            actual_J_gain_vs_DEV_target_exact=correlation([x['actual_gain']for x in records],[x['dev_target_exact']for x in records])),
        source_rows_reused=14*164,new_generated_answers=0,optimizer_updates=0,
        no_heldout_model_quality_claim=True,first_full_layer_sweep_was_not_repeated=True)
    directory=root/'handoff/audit/nov16_pm_p108b';library.write_new(directory/'ALL14_SELECTION_REASONS_v1.json',result)
    lines=['# 전체14층 선택 근거: 완료 원답 재사용','',
        '전14층 MLP down 행렬의 같은 실제 수정량 비교다. 새 모델 실행/편집은0이다.',
        '손실 예측·실제 손실 개선·정답·기존 정상7 손실은 서로 다른 기준이다.','',
        '| 층(0기준) | 예측 J 이득 | 실제 J 이득 | 예측−실제 | FIT 정답/24 | DEV 목표/48 | 기존 정상7 중 손실 |',
        '|---|---:|---:|---:|---:|---:|---:|']
    for x in records:lines.append(f"| {x['layer']} | {x['predicted_gain']:.6f} | {x['actual_gain']:.6f} | {x['signed_error']:.6f} | {x['fit_exact']} | {x['dev_target_exact']} | {len(x['old7_lost_ids'])} |")
    lines.extend(['','주 목적함수로 택한9층과 정상ID 보존으로 남긴7층은 같은 선택 기준의 승자가 아니다.',
        '정답을 한 개 더 맞혔더라도 기존에 맞힌 다른 항목을 잃을 수 있어 원래7개의 ID 전이를 남겼다.',
        '반복/분산 정책의 라운드별 현재 상태는 이 원본 단일층 표와 다르다. 원본 표의 이득을 그대로 더해 다층 효과를 예측하지 않는다.',
        '그림은 같은 원자료의 표시이며 별도 실험 결과가 아니다.'])
    with(directory/'ALL14_SELECTION_REASONS_v1.md').open('x',encoding='utf-8')as f:f.write('\n'.join(lines)+'\n')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,2,figsize=(12,4),layout='constrained');layers=[x['layer']for x in records]
    axes[0].plot(layers,[x['predicted_gain']for x in records],'o--',label='First-order predicted J gain')
    axes[0].plot(layers,[x['actual_gain']for x in records],'s-',label='Actual J gain')
    axes[0].set(ylabel='Objective decrease',xlabel='Physical layer index',title='Prediction versus native physical edit')
    for field,label in [('fit_exact','FIT exact / 24'),('dev_target_exact','DEV target exact / 48')]:
        axes[1].plot(layers,[x[field]for x in records],'o-',label=label)
    axes[1].plot(layers,[len(x['old7_lost_ids'])for x in records],'x--',label='Lost original-correct / 7')
    axes[1].set(ylabel='Count (denominators differ)',xlabel='Physical layer index',title='Answer success and protected-case loss')
    for ax in axes:ax.set_xticks(layers);ax.grid(alpha=.25);ax.legend(fontsize=8)
    fig.suptitle('Completed TinyLM14 atlas, common net norm13.882119; no new GPU experiment',fontsize=10)
    fig.savefig(directory/'ALL14_SELECTION_REASONS_v1.svg');plt.close(fig)
    print(json.dumps(dict(rows=14,new_model_calls=0,correlations=result['correlations']),ensure_ascii=False))


if __name__=='__main__':run()
