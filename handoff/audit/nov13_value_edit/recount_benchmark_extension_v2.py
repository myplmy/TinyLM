"""Read-only score/identity recount and existing paired statistics, no model execution."""
import hashlib
import json
import math
from pathlib import Path
import sys
import time
from types import FunctionType

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from scripts import summarize_p106b_core6_pairs as core
from scripts import summarize_p106b_belebele_pairs as paired
from scripts.p106b_shards import verify as verify_shards

OUT=ROOT/'handoff/audit/nov13_value_edit/BENCHMARK_EXTENSION_v2.json'
E=ROOT/'test_result/evidence'
PRIMARY=core.PRIMARY;COUNTS=core.COUNTS
NAMES={'native595-f':'TinyLM Native595 F','native595-q':'TinyLM Native595 Q','new595-broad-f':'TinyLM Broad F',
    'falcon90m':'Falcon-H1-Tiny-90M Base','gemma270':'Gemma3-270M Base','qwen06':'Qwen3-0.6B Base',
    'gemma1b':'Gemma3-1B PT','format_muon':'TinyLM format+Muon 300M','format_normuon':'TinyLM format+NorMuon 300M',
    'qwen3508':'Qwen3.5-0.8B Base HF FP32'}


def main():
    start=time.perf_counter();inputs=core.Inputs();read=lambda p:core.read_json(p)
    inputs.add(Path(__file__))
    for f in ['scripts/summarize_p106b_core6_pairs.py','scripts/summarize_p106b_belebele_pairs.py','scripts/p106b_shards.py']:
        inputs.add(ROOT/f)
    qualified=E/'p106b_qwen35_fixedshape_v1_20261113';w=read(qualified/'ROOT_QUALIFICATION_v2.json')
    inputs.add(qualified/'ROOT_QUALIFICATION_v2.json')
    if w.get('fixed_shape_qualified') is not True or w.get('variable_shape_qualified') is not False:
        raise ValueError('closed fixed-runtime qualification required')
    reports={m:E/'p106b_official_core6_v2'/m/'full/report.json'for m in ['native595-f','native595-q','new595-broad-f','falcon90m']}
    reports.update({m:E/'p106b_external_core6_v3_s1337'/m/'full/report.json'for m in ['gemma270','qwen06','gemma1b']})
    reports.update({m:E/('p106b_native_format_official_v1_20261026_'+m+'_json_recovery_v3_full')/'report.json'for m in ['format_muon','format_normuon']})
    reports['qwen3508']=qualified/'full/report.json'
    loaded={};scores={}
    for model,path in reports.items():
        inputs.add(path);top=read(path)
        if top.get('returncode')!=0:raise ValueError('closed native report required')
        r=top.get('worker',top);loaded[model]=r;per={}
        for task,metric in PRIMARY.items():
            audit=r['independent_audits'][task];n=COUNTS[task];count=audit['correct_norm'if metric=='acc_norm'else'correct']
            score=r['official_results'][task]['results'][task][metric+',none']
            if audit['rows']!=n or abs(score-count/n)>1e-12:raise ValueError('original official/full aggregate differs')
            per[task]=100*score
        scores[model]=dict(label=NAMES[model],primary_percent=per,mean6_percent=sum(per.values())/6,report_path=str(path.relative_to(ROOT)),report_sha256=core.digest(path))
    for model,filename,label in [('gpt2_q4km','WIP_20261024_GPT2_FULL_ROOT_CLOSURE.json','GPT2 small Q4_K_M'),('qwen35_iq2','WIP_20261025_IQ2_FULL_ROOT_CLOSURE.json','Qwen3.5-0.8B UD-IQ2_XXS')]:
        path=ROOT/'handoff/audit'/filename;inputs.add(path);w=read(path);original=ROOT/w['report_path'];inputs.add(original,w['report_sha256'])
        if w.get('terminal_returncode')!=0 or not w['raw_recount']:raise ValueError('closed GGUF original terminal required')
        per=w['primary_scores_percent'];mean=sum(per.values())/6
        if abs(mean-w['equal_task_mean_percent'])>1e-10:raise ValueError('old GGUF mean changed')
        scores[model]=dict(label=label,primary_percent=per,mean6_percent=mean,original_primary_report_returncode=w['primary_report_returncode'],terminal_returncode=0,closure_path=str(path.relative_to(ROOT)))
    print('[RECOUNT] official aggregate12 complete',flush=True)
    vectors={};identity={}
    for model in ['native595-q','falcon90m','qwen06','qwen3508']:
        r=loaded[model];vectors[model]={}
        for task,metric in PRIMARY.items():
            m=r['sample_manifests'][task];directory=reports[model].parent
            inputs.add(directory/(task+'_samples_shards_manifest.json'));verify_shards(directory,m);rows=[]
            for s in m['shards']:
                inputs.add(directory/s['path'],s['sha256']);rows.extend(json.loads(line)for line in (directory/s['path']).read_text().splitlines())
            if len(rows)!=COUNTS[task]or [x['doc_id']for x in rows]!=list(range(COUNTS[task])):raise ValueError('complete ordered official cases required')
            signature=hashlib.sha256(b''.join(core.canonical({k:x[k]for k in ['doc','arguments','target','doc_hash','prompt_hash','target_hash']})for x in rows)).hexdigest()
            if task in identity and identity[task]!=signature:raise ValueError('paired raw docs/prompts/choices/targets differ')
            identity[task]=signature;v=[int(x[metric])for x in rows]
            if any(x[metric]not in (0,1)for x in rows)or abs(sum(v)/len(v)*100-scores[model]['primary_percent'][task])>1e-10:raise ValueError('raw/aggregate primary scores differ')
            vectors[model][task]=v
    intervals={m:core.paired_intervals(vectors[m],vectors['qwen3508'])for m in vectors if m!='qwen3508'}
    print('[RECOUNT] same19965 official raw cases and three paired Core6 intervals complete',flush=True)
    names=['native595-f','native595-q','new595-broad-f','falcon90m','gemma270','gemma1b','qwen06','qwen3508']
    values={};keys=None;common=None;be_scores={}
    for model in names:
        path=(E/'p106b_qwen35_extra_official_v2_20261113/belebele/report.json'if model=='qwen3508'else E/'p106b_belebele_v2_s1337'/model/'full/report.json')
        inputs.add(path);top=read(path)
        if top.get('returncode')!=0:raise ValueError('closed Belebele report required')
        r=top.get('belebele',top);directory=path.parent/('belebele'if model=='qwen3508'else'');values[model]={};be_scores[model]={}
        for lang,m in r['sample_manifests'].items():
            inputs.add(directory/(lang+'_samples_shards_manifest.json'));verify_shards(directory,m);rows=[]
            for s in m['shards']:
                inputs.add(directory/s['path'],s['sha256']);rows.extend(json.loads(line)for line in (directory/s['path']).read_text().splitlines())
            if len(rows)!=900 or [x['doc_id']for x in rows]!=list(range(900)):raise ValueError('ordered full900 Belebele required')
            rowkeys=[tuple(x['key'])for x in rows]
            if keys is None:keys=rowkeys
            if len(set(rowkeys))!=900 or set(rowkeys)!=set(keys):raise ValueError('same unique bilingual question keys required')
            v={};c=set()
            for x in rows:
                k=tuple(x['key']);v[k]=int(x['metrics']['acc']);gold=int(x['doc']['correct_answer_num'])-1
                pred=max(range(4),key=lambda i:x['responses'][i][0])
                if x['metrics']['acc']not in (0,1)or v[k]!=(pred==gold)or x['metrics']['acc']!=x['metrics']['acc_norm']:raise ValueError('Belebele native four-label likelihood recount differs')
                if not any(p['truncated_context_tokens']for p in x['plans']):c.add(k)
            common=c if common is None else common&c;values[model][lang]=v
            expected=r['independent_audits'][lang]['metrics']['acc']
            if abs(sum(v.values())/900-expected)>1e-12:raise ValueError('Belebele raw aggregate differs')
            be_scores[model][lang]=dict(correct=sum(v.values()),rows=900,accuracy=sum(v.values())/900)
    # Same implementation with an explicit eight-model registry; no shared module/library mutation.
    fn=FunctionType(paired.cluster_intervals.__code__,dict(paired.cluster_intervals.__globals__,MODELS=tuple(names)),paired.cluster_intervals.__name__,paired.cluster_intervals.__defaults__)
    fn.__kwdefaults__=dict(paired.cluster_intervals.__kwdefaults__)
    be_intervals=fn(values,keys,common,draws=100000,seed=20261024)
    print('[RECOUNT] eight-model Belebele900/common'+str(len(common))+' clustered intervals complete',flush=True)
    lambada={};lambda_keys=None
    for model in names:
        path=(E/'p106b_qwen35_extra_official_v2_20261113/lambada/report.json'if model=='qwen3508'else E/'p106b_lambada_default_v2_s1337'/model/'full/report.json')
        inputs.add(path);top=read(path)
        if top.get('returncode')!=0:raise ValueError('closed LAMBADA report required')
        r=top.get('lambada',top);directory=path.parent/('lambada'if model=='qwen3508'else'');m=r['sample_manifest'];verify_shards(directory,m);rows=[]
        for s in m['shards']:
            inputs.add(directory/s['path'],s['sha256']);rows.extend(json.loads(line)for line in (directory/s['path']).read_text().splitlines())
        if len(rows)!=5153 or [x['doc_id']for x in rows]!=list(range(5153)):raise ValueError('ordered full LAMBADA5153 required')
        ids=hashlib.sha256(b''.join(core.canonical({k:x[k]for k in ['doc','arguments']})for x in rows)).hexdigest()
        if lambda_keys is not None and ids!=lambda_keys:raise ValueError('same LAMBADA source and complete target required')
        lambda_keys=ids;correct=sum(x['response'][1]for x in rows);ppl=math.exp(-sum(x['response'][0]for x in rows)/5153)
        if abs(correct/5153-r['metrics']['acc'])>1e-12 or not math.isclose(ppl,r['metrics']['perplexity'],rel_tol=1e-12):raise ValueError('full-word LAMBADA raw aggregate differs')
        lambada[model]=dict(correct=correct,rows=5153,accuracy=correct/5153,perplexity=ppl)
    inputs.unchanged();report=dict(schema='NOV13_FULL_BENCHMARK_EXTENSION_V2',model_loads=0,gpu_calls=0,training=False,
        raw_aggregate_and_identity_recount=True,original_official_scoring_reused=True,core6=scores,core6_same_case_hashes=identity,
        core6_qwen35_pairs=intervals,belebele_full=be_scores,belebele_common_rows=len(common),belebele_cluster_statistics=be_intervals,
        lambada_full=lambada,lambada_same_case_sha256=lambda_keys,inputs=inputs.files,seconds=time.perf_counter()-start,
        scope='Existing trained checkpoints and frozen official tasks; pointwise exploratory intervals, not seed uncertainty or intelligence improvement.')
    with OUT.open('x',encoding='utf-8')as f:json.dump(report,f,ensure_ascii=False,indent=2);f.write(chr(10))
    print('[RECOUNT_FINAL] '+json.dumps(dict(models=len(scores),seconds=report['seconds'],common=len(common),report_sha256=core.digest(OUT))),flush=True)


if __name__=='__main__':main()
