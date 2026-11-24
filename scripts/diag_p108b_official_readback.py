#!/usr/bin/env python3
"""CPU recount of frozen official eleven-task outputs; no model execution."""
import json
from pathlib import Path
from scripts import diag_p108b_official as driver
from scripts import diag_p108_frozen_edit_official as owner
from scripts import diag_p108b_value_library as library
from scripts import interactive_research_infer as manual
from scripts import p106b_shards as shards
from scripts import eval_bench_suite as statistics


def corrected_p(tests):
    ordered=sorted(range(len(tests)),key=lambda i:(tests[i]['p_unadjusted'],i));previous=0.
    for rank,index in enumerate(ordered):
        previous=min(1.,max(previous,(len(tests)-rank)*tests[index]['p_unadjusted']))
        tests[index].update(holm_family_size=len(tests),holm_rank=rank+1,p_holm=previous)
    return tests


def recount_vectors(task,rows):
    checked=[]
    for row in rows:
        doc=task.eval_docs[row['doc_id']];choices=task.doc_to_choice(doc)
        gold=task.doc_to_text(doc)if task.multiple_input else task.doc_to_target(doc)
        if isinstance(gold,str):gold=choices.index(gold)
        checked.append(owner.official.independent_row(choices,gold,[r[0]for r in row['filtered_resps']]))
    result={metric:[r[metric]for r in checked]for metric in('acc','acc_norm','gold','pred')}
    return result


def run():
    from sklearn.metrics import f1_score
    driver.baseline_reference();tasks,specs,provenance=owner.prepare_tasks()
    paths={'original':driver.BASELINE}
    paths.update({name:driver.OUTPUT/name/'report.json'for name in('SINGLE1','atlas_layer07','ADAPT_D4')})
    reports={};vectors={};identities={};sources={}
    for name,path in paths.items():
        report=json.loads(path.read_text(encoding='utf-8'))
        if report['status']!='OFFICIAL_ELEVEN_TASKS_COMPLETE'or report['returncode']!=0 or report['task_specs']!=specs:
            raise ValueError('closed full same official eleven-task specification required')
        if report['policy']!=owner.official.policy():raise ValueError('same likelihood/normalization policy required')
        sources[name]=dict(path=str(path.relative_to(owner.ROOT)),sha256=manual.file_sha(path));vectors[name]={};identities[name]={}
        for task_name,task in tasks.items():
            manifest=report['sample_manifests'][task_name];shards.verify(path.parent,manifest);rows=[]
            for part in manifest['shards']:
                rows.extend(json.loads(line)for line in(path.parent/part['path']).read_text(encoding='utf-8').splitlines())
            audit=owner.official.plain(owner.suite.audit_task(task,rows,report['actual_counts'][task_name]))
            if audit!=report['independent_audits'][task_name]:raise ValueError('fresh independent raw recount differs')
            vectors[name][task_name]=recount_vectors(task,rows)
            if task_name.startswith('kobest_'):
                fresh=f1_score(vectors[name][task_name]['gold'],vectors[name][task_name]['pred'],average='macro')
                reported=report['official_results'][task_name]['results'][task_name]['f1,none']
                if abs(float(fresh)-reported)>1e-12:raise ValueError('independent task macro F1 recount differs')
            identities[name][task_name]=manual.canonical_sha([{k:row[k]for k in('doc_id','doc_hash','prompt_hash','target_hash','arguments')}for row in rows])
        if name!='original'and identities[name]!=identities['original']:raise ValueError('paired questions/order/prompt/target/choices changed')
        reports[name]=report
    tests=[]
    for name in list(paths)[1:]:
        for task in tasks:
            for metric in('acc','acc_norm'):
                left=vectors['original'][task][metric];right=vectors[name][task][metric]
                lost=sum(a and not b for a,b in zip(left,right));gained=sum(b and not a for a,b in zip(left,right))
                tests.append(dict(model=name,task=task,metric=metric,n=len(left),original_correct=sum(left),edited_correct=sum(right),
                    lost=lost,gained=gained,net=gained-lost,delta_percentage_points=100*(gained-lost)/len(left),
                    p_unadjusted=statistics.mcnemar_exact_p(lost,gained),inference_scope='secondary paired accuracy; not an F1 or training-seed test'))
    corrected_p(tests);metrics={}
    for name,report in reports.items():
        table={}
        for task in tasks:
            values=report['official_results'][task]['results'][task]
            audit=report['independent_audits'][task];count=report['actual_counts'][task]
            table[task]=dict(n=count,acc=values['acc,none'],acc_norm=values.get('acc_norm,none'),
                primary=values.get('acc_norm,none',values['acc,none']),diagnostic_all_choice_norm=audit['correct_norm']/count,
                f1=values.get('f1,none'),diagnostic_baselines=report['independent_audits'][task])
        core=[table[t]for t in owner.official.TASK_COUNTS];ko=[r for t,r in table.items()if t.startswith('kobest_')]
        metrics[name]=dict(tasks=table,core6_mean_acc=sum(x['acc']for x in core)/6,
            core6_mean_official_primary=sum(x['primary']for x in core)/6,
            kobest_task_mean_f1=sum(x['f1']for x in ko)/5,
            kobest_row_weighted_task_f1=sum(x['n']*x['f1']for x in ko)/sum(x['n']for x in ko),
            f1_weighting_scope='weighted mean of five task macro F1 scores, not a merged-label F1')
    result=dict(schema='P108B_OFFICIAL11_CPU_READBACK_V1',sources=sources,metrics=metrics,paired_accuracy_tests=tests,
        correspondence=identities['original'],task_specs=specs,new_model_calls=0,
        statistical_limit='66 exploratory secondary tests; Holm within this reported family only; item dependence and one trained parent limit inference',
        primary_f1_statistics='NOT_TESTED; task scores remain descriptive, no accuracy p used as an F1 p')
    path=owner.ROOT/'handoff/audit/nov16_p108b/OFFICIAL11_READBACK_v1.json';library.write_new(path,result)
    print(json.dumps({name:{k:v for k,v in r.items()if k!='tasks'}for name,r in metrics.items()},ensure_ascii=False))
    print(json.dumps(dict(secondary_tests=len(tests),min_raw_p=min(x['p_unadjusted']for x in tests),min_holm_p=min(x['p_holm']for x in tests),new_model_calls=0)))


if __name__=='__main__':run()
