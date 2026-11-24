"""Independent disk-row metrics and native rendered-input correspondence."""
import json
from collections import Counter
from sklearn.metrics import f1_score
from scripts import diag_p108b_external_gemma_kobest_v2 as driver
from scripts import diag_p108b_official_readback as shared
from scripts import interactive_research_infer as manual
from scripts import p106b_shards as shards


def run():
    p,tasks,_=driver.verify();root=driver.parent.ROOT
    path=driver.OUT/'report.json';r=json.loads(path.read_text())
    if(r['status']!='OFFICIAL_KOBEST_GEMMA_FIVE_COMPLETE' or not r['source_files_unchanged'] or
       r['cuda_allocated_after_bytes'] or r['cuda_reserved_after_bytes'] or
       not r['native_full_softmax_canary']['passed']):raise ValueError('full exact native closure required')
    original=json.loads((root/'handoff/audit/nov16_p108b/OFFICIAL11_READBACK_v1.json').read_text())
    metrics={};correspondence={};files={}
    for name,task in tasks.items():
        manifest=r['sample_manifests'][name];shards.verify(driver.OUT,manifest);rows=[]
        for spec in manifest['shards']:
            raw=driver.OUT/spec['path'];files[str(raw.relative_to(root))]=manual.file_sha(raw)
            rows.extend(json.loads(line)for line in raw.read_text().splitlines())
        v=shared.recount_vectors(task,rows);n=len(rows);values=r['official_results'][name]['results'][name]
        acc=sum(v['acc'])/n;f1=float(f1_score(v['gold'],v['pred'],average='macro'))
        if abs(acc-values['acc,none'])>1e-12 or abs(f1-values['f1,none'])>1e-12:
            raise ValueError('independent full disk score differs')
        if' acc_norm,none'.strip()in values and abs(sum(v['acc_norm'])/n-values['acc_norm,none'])>1e-12:
            raise ValueError('official length normalization differs')
        identity=manual.canonical_sha([{k:a[k]for k in('doc_id','doc_hash','prompt_hash','target_hash','arguments')}for a in rows])
        if identity!=original['correspondence'][name]:raise ValueError('question/choices/gold/order differs')
        correspondence[name]=identity;labels=Counter(v['gold'])
        metrics[name]=dict(n=n,correct=sum(v['acc']),acc=acc,f1=f1,
            official_acc_norm=values.get('acc_norm,none'),label_counts=dict(labels),prediction_counts=dict(Counter(v['pred'])),
            posthoc_majority_correct=max(labels.values()),random_expected_correct=sum(1/len(task.doc_to_choice(task.eval_docs[a['doc_id']]))for a in rows))
    assert sum(x['n']for x in metrics.values())==4561
    report=dict(schema='P108B_GEMMA_KOBEST_DISK_RECOUNT_V1',status='ALL4561_RAW_MATCH',metrics=metrics,
        task_mean_f1=sum(x['f1']for x in metrics.values())/5,rendered_correspondence=correspondence,
        source_report_sha256=manual.file_sha(path),raw_shards=files,new_model_calls=0,
        native_assets_and_core_unchanged=r['model_proof']['body_unchanged']and r['model_proof']['source_assets_unchanged'],
        baseline_policy='POSTHOC_MAJORITY_DIAGNOSTIC_ONLY',f1_difference_significance='NOT_TESTED',
        scope='external baseline;different models/tokenizers/pretraining;no new TinyLM intelligence evidence')
    driver.parent.library.write_new(root/'handoff/audit/nov16_pm_p108b/GEMMA_KOBEST_DISK_READBACK_v1.json',report)
    print(json.dumps({k:report[k]for k in('status','metrics','task_mean_f1','new_model_calls')},ensure_ascii=False))


if __name__=='__main__':run()
