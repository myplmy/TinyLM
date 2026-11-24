"""Independent raw pairing/F1 recount; explicit project PRIMARY metric map."""
import json
from scripts import diag_p108b_pm_evaluate as driver
from scripts import diag_p108b_official as history
from scripts import diag_p108b_official_readback as common
from scripts import diag_p108_frozen_edit_official as owner
from scripts import diag_p108b_value_library as library
from scripts import interactive_research_infer as manual
from scripts import p106b_shards as shards
from scripts import eval_bench_suite as statistics

PRIMARY={'piqa':'acc','arc_easy':'acc_norm','arc_challenge':'acc_norm',
         'hellaswag':'acc_norm','winogrande':'acc','boolq':'acc'}


def run():
    from sklearn.metrics import f1_score
    selected=driver.study.read(driver.BASE/'norm_selection_v1.json')['name']
    paths={'original':history.BASELINE,selected:driver.BASE/'pm_official_v1'/selected/'report.json'}
    tasks,specs,provenance=owner.prepare_tasks();reports={};vectors={};identities={};sources={};table={}
    for name,path in paths.items():
        report=driver.study.read(path)
        if(report['status']!='OFFICIAL_ELEVEN_TASKS_COMPLETE' or report['returncode']!=0 or
                report['task_specs']!=specs or report['policy']!=owner.official.policy()):
            raise ValueError('complete same official task/metric specification required')
        if report['frozen_model_origin']!=driver.study.read(driver.PROFILE)['origin']:
            raise ValueError('same original model/tokenizer lineage required')
        sources[name]=dict(path=str(path.relative_to(driver.ROOT)),sha256=manual.file_sha(path))
        vectors[name]={};identities[name]={};table[name]={}
        for taskname,task in tasks.items():
            manifest=report['sample_manifests'][taskname];shards.verify(path.parent,manifest);rows=[]
            for part in manifest['shards']:
                rows.extend(json.loads(line)for line in(path.parent/part['path']).read_text(encoding='utf-8').splitlines())
            audit=owner.official.plain(owner.suite.audit_task(task,rows,len(task.eval_docs)))
            if audit!=report['independent_audits'][taskname]:raise ValueError('raw independent audit differs')
            vectors[name][taskname]=common.recount_vectors(task,rows)
            values=report['official_results'][taskname]['results'][taskname]
            if taskname.startswith('kobest_'):
                score=float(f1_score(vectors[name][taskname]['gold'],vectors[name][taskname]['pred'],average='macro'))
                if abs(score-values['f1,none'])>1e-12:raise ValueError('raw independent macro F1 differs')
            for metric in ('acc','acc_norm'):
                if metric+',none' in values:
                    v=vectors[name][taskname][metric]
                    if abs(sum(v)/len(v)-values[metric+',none'])>1e-12:raise ValueError('raw independent accuracy differs')
            identities[name][taskname]=manual.canonical_sha([{k:r[k]for k in ('doc_id','doc_hash','prompt_hash','target_hash','arguments')}for r in rows])
            point=values[PRIMARY[taskname]+',none'] if taskname in PRIMARY else values['f1,none']
            table[name][taskname]=dict(n=len(rows),project_primary_metric=PRIMARY.get(taskname,'f1'),
                project_primary=point,acc=values['acc,none'],acc_norm=values.get('acc_norm,none'),f1=values.get('f1,none'),
                diagnostic_baselines=audit)
        if name!='original' and identities[name]!=identities['original']:
            raise ValueError('official questions/order/targets/rendered choices differ')
        reports[name]=report
    tests=[]
    for taskname in tasks:
        metric=PRIMARY.get(taskname,'acc')
        left=vectors['original'][taskname][metric];right=vectors[selected][taskname][metric]
        lost=sum(bool(a)and not b for a,b in zip(left,right));gained=sum(bool(b)and not a for a,b in zip(left,right))
        tests.append(dict(task=taskname,accuracy_metric=metric,n=len(left),original_correct=sum(left),edited_correct=sum(right),
            gained=gained,lost=lost,delta_pp=100*(gained-lost)/len(left),
            p_unadjusted=statistics.mcnemar_exact_p(lost,gained),
            inference_scope='paired item accuracy only;KoBEST accuracy test is not a macroF1 test'))
    common.corrected_p(tests)
    summary={name:dict(core6_project_primary_mean=sum(m[t]['project_primary']for t in PRIMARY)/6,
        kobest_task_mean_macro_f1=sum(m[t]['f1']for t in m if t.startswith('kobest_'))/5)for name,m in table.items()}
    result=dict(schema='P108B_PM_OFFICIAL11_RAW_READBACK_V1',sources=sources,primary_metric_map=PRIMARY,
        metrics=table,summary=summary,paired_accuracy_tests=tests,exact_correspondence=identities['original'],
        new_model_calls=0,task_specs=specs,statistical_limit='one parent/one selected edit;11 accuracy tests Holm-family;no F1 significance test;item clustering remains',
        selection_not_changed=True,benchmark_used_for_training_or_editing=False)
    library.write_new(driver.ROOT/'handoff/audit/nov16_pm_p108b/OFFICIAL11_PRIMARY_READBACK_v1.json',result)
    print(json.dumps(dict(summary=summary,min_raw_p=min(t['p_unadjusted']for t in tests),
        min_holm_p=min(t['p_holm']for t in tests),paired_rows=24526,new_model_calls=0),ensure_ascii=False))


if __name__=='__main__':run()
