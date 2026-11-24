#!/usr/bin/env python3
"""Recount all external KoBEST raw rows and pair their rendered task identities."""
import json
from collections import Counter
from sklearn.metrics import f1_score
from scripts import diag_p108b_external_kobest as driver
from scripts import diag_p108b_official_readback as existing
from scripts import diag_p108b_value_library as library
from scripts import interactive_research_infer as manual
from scripts import p106b_shards as shards

def run():
    p,tasks,_=driver.verify();path=driver.OUT/'report.json';report=json.loads(path.read_text())
    if(report['status']!='OFFICIAL_KOBEST_FALCON_FIVE_COMPLETE'or report['cuda_allocated_after_bytes']or report['cuda_reserved_after_bytes']):
        raise ValueError('full official five-task close and strict cleanup required')
    original=json.loads((driver.atlas.ROOT/'handoff/audit/nov16_p108b/OFFICIAL11_READBACK_v1.json').read_text())
    checked={};identities={};sources={}
    for name,task in tasks.items():
        manifest=report['sample_manifests'][name];shards.verify(driver.OUT,manifest);rows=[]
        for spec in manifest['shards']:
            raw=driver.OUT/spec['path'];sources[str(raw.relative_to(driver.atlas.ROOT))]=manual.file_sha(raw)
            rows.extend(json.loads(line)for line in raw.read_text().splitlines())
        vectors=existing.recount_vectors(task,rows);n=len(rows);values=report['official_results'][name]['results'][name]
        accuracy=sum(vectors['acc'])/n;f1=float(f1_score(vectors['gold'],vectors['pred'],average='macro'))
        if abs(accuracy-values['acc,none'])>1e-12 or abs(f1-values['f1,none'])>1e-12:
            raise ValueError('independent choice/gold/macroF1 differs')
        normalized=sum(vectors['acc_norm'])/n
        if 'acc_norm,none'in values and abs(normalized-values['acc_norm,none'])>1e-12:
            raise ValueError('independent official length normalization differs')
        identity=manual.canonical_sha([{k:r[k]for k in('doc_id','doc_hash','prompt_hash','target_hash','arguments')}for r in rows])
        identities[name]=dict(sha256=identity,match_to_tiny_original=identity==original['correspondence'][name])
        if not identities[name]['match_to_tiny_original']:raise ValueError('rendered question/choices/order do not match original TinyLM')
        labels=Counter(vectors['gold']);predictions=Counter(vectors['pred'])
        checked[name]=dict(n=n,correct=sum(vectors['acc']),acc=accuracy,f1=f1,
            official_acc_norm=values.get('acc_norm,none'),posthoc_gold_counts=dict(labels),
            predicted_label_counts=dict(predictions),posthoc_majority_correct=max(labels.values()),
            random_expected_correct=sum(1/len(task.doc_to_choice(task.eval_docs[r['doc_id']]))for r in rows),
            baseline_warning='posthoc majority is descriptive, not a pretrained prior baseline')
    if sum(r['n']for r in checked.values())!=4561:raise ValueError('full denominator differs')
    result=dict(schema='P108B_EXTERNAL_KOBEST_READBACK_V1',status='ALL4561_RAW_MATCH',tasks=checked,
        task_mean_f1=sum(r['f1']for r in checked.values())/5,
        row_weighted_task_f1=sum(r['n']*r['f1']for r in checked.values())/4561,
        rendered_correspondence=identities,raw_shards=sources,source_report_sha256=manual.file_sha(path),
        original_tiny_recount_sha256=manual.file_sha(driver.atlas.ROOT/'handoff/audit/nov16_p108b/OFFICIAL11_READBACK_v1.json'),
        original_assets_and_core_unchanged=report['model_proof']['source_assets_unchanged']and
            report['model_proof']['initial_core_sha256']==report['model_proof']['final_core_sha256'],
        new_model_calls=0,f1_pair_significance='NOT_TESTED',fairness='same official questions/choice likelihood/normalization; different tokenizer/model/pretraining')
    library.write_new(driver.atlas.ROOT/'handoff/audit/nov16_p108b/EXTERNAL_KOBEST_READBACK_v1.json',result)
    print(json.dumps(dict(status=result['status'],tasks=checked,task_mean_f1=result['task_mean_f1'],new_model_calls=0)))

if __name__=='__main__':run()
