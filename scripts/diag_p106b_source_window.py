#!/usr/bin/env python3
"""Posthoc source-window diagnosis with immutable primary actual histories."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import gc
import json
import time
from scripts import p106b_source_windows as method
from scripts import diag_p106b_original_qa3_evaluate_v2 as primary
from scripts.p106b_shards import ShardWriter, verify
from scripts.p106b_gate_runtime import GateNegative, idle_before_gpu, wall_limit

course = primary.course
training = course.training
TAG = 'p106b_source_window_diagnosis_v1_s1337'
CORPUS = ROOT / 'HF/sft_ready' / TAG / 'corpus'
EVIDENCE = ROOT / 'test_result/evidence' / TAG
LOCAL = ROOT / 'test_result/evidence/local' / TAG
PRIMARY_REPORT = primary.EVIDENCE / 'report.json'
PRIMARY_SHA = '009124B8174ACCB78A99010D1F29AE517AE83B5C741D04D343E5858F4416F7C0'
ENDPOINTS = ('parent', 'three')
CHECKPOINT_SHAS = dict(parent='687EBCC5E30EA674EF4742BFC2BA6B98BCAB937541BD5498F567A9084387E831',
    three='567D379E3F8F1B8BBE1F65303DE9AAF1D1F3A33AFE5F9EA51CD12EE06069F9AF')
CODE = (*primary.CODE, *primary.training.CODE, 'scripts/p106b_source_windows.py',
    'scripts/test_p106b_source_windows.py', 'scripts/diag_p106b_source_window.py',
    'scripts/test_p106b_source_window_consumer.py')


def required(path):
    if not path.is_file() or path.is_symlink():
        raise GateNegative('required regular evidence absent: ' + str(path.relative_to(ROOT)))
    return json.loads(path.read_text(encoding='utf8'))


def info():
    return dict(schema=method.VERSION, tag=TAG, code_sha256={p:training.data.digest(ROOT / p) for p in sorted(set(CODE))},
        endpoints=list(ENDPOINTS), checkpoints_sha256=CHECKPOINT_SHAS, source_primary_sha256=PRIMARY_SHA,
        tokenizer_sha256=training.data.TOK_SHA,
        modes=list(method.MODES), window_tokens=method.WIDTH, window_stride=method.STRIDE,
        query='character3 log-TF/smoothed local IDF/cosine; current question twice, earlier user questions once; no answers',
        gold_literal='label-assisted substring-containing window, NOT a semantic oracle, deployable method or accuracy upper bound',
        previous_answers='fixed actual answers from primary; new predictions NOT propagated',
        precision='FP32_MATH', temperature=0., top_k=1, max_new=64, student_mtp=False, training=False,
        optimizer_updates=0, new_checkpoints=0, train_ready=False, semantic_truth='ORIGINAL_PUBLIC_UNVERIFIED',
        sample_scope='same64 previously evaluated source roots, posthoc development diagnosis, NOT fresh TEST',
        whole_smoke='NOT_RUN', deadline_utc=course.prior.producer.legacy.source.DEADLINE.isoformat())


def source_inputs():
    if training.data.digest(PRIMARY_REPORT) != PRIMARY_SHA:
        raise ValueError('fixed primary evaluation changed')
    report = required(PRIMARY_REPORT)
    if report['status'] != 'ORIGINAL_QA3_ACTUAL_EVALUATED' or report['code_sha256'] != primary.info()['code_sha256']:
        raise ValueError('complete immutable original evaluation CODE required')
    original_report = required(course.CORPUS / 'report.json')
    if training.data.digest(course.CORPUS / 'report.json') != report['corpus_sha256']:
        raise ValueError('original corpus report changed')
    if original_report['code_sha256'] != course.frozen.info()['code_sha256']:
        raise ValueError('original frozen data CODE changed')
    verify(course.CORPUS,original_report['manifests']['test_natural_three'])
    rows = list(training.data.stream_rows(course.CORPUS, original_report['manifests']['test_natural_three']))
    originals = {r['meta']['semantic_root_id']: r for r in rows}
    if len(rows) != 64 or len(originals) != 64 or Counter(r['meta']['language'] for r in rows) != dict(ko=32,en=32):
        raise ValueError('exact64 bilingual source rows required')
    events = {}
    for endpoint in ENDPOINTS:
        result = report['endpoints'][endpoint]
        if result['checkpoint_sha256'] != CHECKPOINT_SHAS[endpoint]:
            raise ValueError('preselected endpoint changed')
        if training.data.digest(ROOT / result['checkpoint']) != CHECKPOINT_SHAS[endpoint]:
            raise ValueError('physical checkpoint changed')
        spec = result['metrics']['natural']; verify(ROOT / spec['directory'], spec['manifest'])
        full = list(training.data.stream_rows(ROOT / spec['directory'], spec['manifest']))
        if primary.method.counts(full) != spec['counts']:
            raise ValueError('primary raw counts differ')
        actual = [x for x in full if x['history'] == 'ACTUAL_MODEL']
        index = {(x['root'],x['turn']):x for x in actual}
        if len(actual) != 192 or len(index) != 192 or {r for r,_ in index} != set(originals):
            raise ValueError('all64x3 actual prefixes required')
        for event in actual:
            for position in range(1,len(event['messages']),2):
                previous = index[event['root'],(position+1)//2]['answer']
                if method.original.text(event['messages'][position]) != previous:
                    raise ValueError('primary prefix does not hold its actual previous answer')
        events[endpoint] = sorted(actual,key=lambda x:(x['root'],x['turn']))
    return report, originals, events


def construct():
    from tokenizers import Tokenizer
    import torch
    if torch.cuda.is_initialized():
        raise ValueError('actual input consumer proof must precede CUDA')
    if training.data.digest(training.data.TOKENIZER) != training.data.TOK_SHA:
        raise ValueError('tokenizer changed')
    report, originals, events = source_inputs()
    tok = Tokenizer.from_file(str(training.data.TOKENIZER)); cases = []
    eligibility = defaultdict(Counter); lengths = defaultdict(list); literal = defaultdict(Counter)
    for endpoint in ENDPOINTS:
        for event in events[endpoint]:
            case = method.make_case(originals[event['root']],event,endpoint,tok); cases.append(case)
            for variant in case['variants']:
                mode = variant['mode']; eligibility[endpoint][mode] += int(variant['eligible'])
                if variant['eligible']:
                    lengths[endpoint+'/'+mode].append(variant['prompt_tokens'])
                    literal[endpoint][mode] += int(variant['literal_in_window'])
    if len(cases) != 384:
        raise ValueError('actual384 case consumers required')
    for ep in ENDPOINTS:
        if any(eligibility[ep][mode] != 192 for mode in ('FULL','QUERY','RANDOM','REMOVE_REFERENCE')):
            raise ValueError('non-oracle variants must cover all192 cases')
    if eligibility['parent']['GOLD_LITERAL'] != eligibility['three']['GOLD_LITERAL']:
        raise ValueError('source-based eligibility must not depend on endpoint answers')
    observation = dict(cases=len(cases), source_roots=64, per_endpoint=192, fixed_previous_answers_verified=True,
        full_reconstruction_verified=True, no_cuda=True, eligibility={k:dict(v) for k,v in eligibility.items()},
        literal_containment={k:dict(v) for k,v in literal.items()}, input_signature=method.sha(cases),
        prompt_lengths={k:dict(min=min(v),max=max(v),sum=sum(v),cases=len(v)) for k,v in lengths.items()})
    return report,cases,observation


def cpu():
    path = EVIDENCE / 'cpu_consumer_report.json'
    if path.exists(): raise GateNegative('old actual CPU proof preserved')
    _,_,observation = construct()
    training.write(path,dict(info(),status='ACTUAL_INPUT_CONSUMERS_VERIFIED',observation=observation))
    print('[SOURCE_WINDOW_CPU] '+json.dumps(observation),flush=True); return 0


def cpu_proof(observation):
    proof = required(EVIDENCE / 'cpu_consumer_report.json')
    if proof['code_sha256'] != info()['code_sha256'] or proof['status'] != 'ACTUAL_INPUT_CONSUMERS_VERIFIED' or proof['observation'] != observation:
        raise ValueError('same-code actual CPU consumers required')


def freeze():
    if CORPUS.exists(): raise GateNegative('old diagnostic inputs preserved')
    _,cases,observation = construct(); cpu_proof(observation)
    writer = ShardWriter(CORPUS,'fixed_history_inputs')
    for case in cases: writer.append(case)
    manifest = writer.close(lineage=info()); verify(CORPUS,manifest)
    result = dict(info(),status='SOURCE_WINDOW_INPUTS_FROZEN',manifest=manifest,observation=observation)
    training.write(CORPUS/'report.json',result); training.write(EVIDENCE/'input_report.json',result)
    print('[SOURCE_WINDOW_FROZEN] '+json.dumps(observation),flush=True); return 0


def read_inputs():
    if training.data.digest(training.data.TOKENIZER)!=training.data.TOK_SHA:
        raise ValueError('physical tokenizer changed after input freeze')
    report = required(CORPUS/'report.json')
    if report['code_sha256'] != info()['code_sha256'] or report['status'] != 'SOURCE_WINDOW_INPUTS_FROZEN':
        raise ValueError('frozen diagnostic input CODE changed')
    cpu_proof(report['observation'])
    verify(CORPUS,report['manifest'])
    cases = list(training.data.stream_rows(CORPUS,report['manifest']))
    if len(cases) != 384 or method.sha(cases) != report['observation']['input_signature']:
        raise ValueError('frozen input consumers changed')
    prior = required(PRIMARY_REPORT)
    if training.data.digest(PRIMARY_REPORT) != PRIMARY_SHA:
        raise ValueError('primary evaluation changed')
    for ep in ENDPOINTS:
        if training.data.digest(ROOT/prior['endpoints'][ep]['checkpoint']) != CHECKPOINT_SHAS[ep]:
            raise ValueError('preselected checkpoint changed')
    return report,cases,prior


def load_model(endpoint, prior):
    from tinylm.infer.generate import _strip
    torch,model,cfg,tok,_,_ = primary.training.load_parent()
    identity = prior['endpoints'][endpoint]
    if endpoint == 'three':
        saved = torch.load(ROOT/identity['checkpoint'],map_location='cpu',weights_only=True)
        if saved['original_qa3_curriculum'] != dict(tag=course.TAG,arm='three',epoch=4):
            raise ValueError('fixed final three-QA lineage required')
        model.load_state_dict(_strip(saved['model']),strict=True); del saved
    body = training.state_fingerprint(model)
    if body != identity['core_before_after_sha256']:
        raise ValueError('same physical model body as primary required')
    return torch,model,cfg,tok,body


def collect_phase(endpoint, phase, cases, prior):
    torch,model,cfg,tok,body = load_model(endpoint,prior); model = model.cuda()
    directory = LOCAL/phase/endpoint; writer = ShardWriter(directory,'answers'); events = []; mismatch = 0
    emit = primary.reference.generation.emit_function(model,cfg,tok); started = time.perf_counter()
    torch.cuda.reset_peak_memory_stats(); model.eval(); model.freeze_quant()
    try:
        with torch.no_grad():
            for i,case in enumerate(cases):
                for variant in case['variants']:
                    mode = variant['mode']
                    if (phase=='full') != (mode=='FULL'): continue
                    record = {k:case[k] for k in ('endpoint','root','language','turn','case_id','gold','full_messages_sha256','original_reference_sha256','history_policy')}
                    record.update(mode=mode,semantic_truth='ORIGINAL_PUBLIC_UNVERIFIED',diagnostic_only=True)
                    if not variant['eligible']:
                        record.update(status='NOT_ELIGIBLE',reason=variant['reason']); writer.append(record); events.append(record); continue
                    tick=time.perf_counter(); answer,generation=emit(variant['messages'])
                    record.update(status='GENERATED',messages=variant['messages'],answer=answer,generation=generation,
                        scores=method.score(answer,case['gold'],generation),request_sec=time.perf_counter()-tick,
                        selected_char_range=variant['selected_char_range'],literal_in_window=variant['literal_in_window'],cosine=variant['cosine'])
                    if mode=='FULL':
                        record['same_as_primary_answer']=answer==case['baseline_answer']; mismatch+=int(not record['same_as_primary_answer'])
                    writer.append(record);events.append(record)
                if (i+1)%64==0:
                    print('[SOURCE_WINDOW_PROGRESS] '+json.dumps(dict(endpoint=endpoint,phase=phase,cases=i+1,total=len(cases))),flush=True)
        manifest=writer.close(lineage=info());verify(directory,manifest)
        if training.state_fingerprint(model)!=body:raise ValueError('diagnostic changed model body')
        result=dict(directory=str(directory.relative_to(ROOT)),manifest=manifest,counts=method.recount(events),
            body_before_after_sha256=body,full_replay_disagreements=mismatch,whole_sec=time.perf_counter()-started,
            peak_reserved_mib=torch.cuda.max_memory_reserved()/2**20,events=len(events))
        training.write(EVIDENCE/'probe'/(phase+'_'+endpoint+'_report.json'),dict(info(),**result))
        return result
    finally:
        model.clear_quant();model.train();del model;gc.collect();torch.cuda.empty_cache()


def probe(a):
    import torch
    report,cases,prior=read_inputs(); target=EVIDENCE/'probe'
    if target.exists() or LOCAL.exists():raise GateNegative('old diagnostic model outputs preserved')
    remaining=(course.prior.producer.legacy.source.DEADLINE-datetime.now(timezone.utc)).total_seconds()
    if remaining<a.max_wall_sec+2700:raise GateNegative('requested bounded diagnostic plus45minute closure margin required')
    idle_before_gpu();target.mkdir(parents=True,exist_ok=False); started=time.perf_counter()
    torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
    full={};variants={}
    with wall_limit(a.max_wall_sec):
        for ep in ENDPOINTS:
            selected=[c for c in cases if c['endpoint']==ep]
            full[ep]=collect_phase(ep,'full',selected,prior)
            if full[ep]['full_replay_disagreements']:
                training.write(target/'full_replay_failure.json',dict(info(),status='FULL_REPLAY_MISMATCH',full=full))
                raise ValueError('FULL byte replay mismatch; no interpretation or remaining variant calls')
        for ep in ENDPOINTS:
            variants[ep]=collect_phase(ep,'variants',[c for c in cases if c['endpoint']==ep],prior)
    result=dict(info(),status='SOURCE_WINDOW_PROBED',full=full,variants=variants,whole_sec=time.perf_counter()-started,
        input_report_sha256=training.data.digest(CORPUS/'report.json'),model_unchanged=True)
    training.write(target/'report.json',result)
    print('[SOURCE_WINDOW_FINAL] '+json.dumps(dict(status=result['status'],whole_sec=result['whole_sec'],full_disagreements={k:v['full_replay_disagreements'] for k,v in full.items()})),flush=True);return 0


def readback():
    report=required(EVIDENCE/'probe/report.json');target=EVIDENCE/'probe/readback.json'
    if target.exists():raise GateNegative('old diagnostic recount preserved')
    if report['code_sha256']!=info()['code_sha256'] or report['status']!='SOURCE_WINDOW_PROBED':raise ValueError('same-code complete diagnostic required')
    _,cases,_=read_inputs();events=[];pairs={}
    expected={(c['endpoint'],c['root'],c['turn'],v['mode']):v['eligible'] for c in cases for v in c['variants']}
    for ep in ENDPOINTS:
        lanes={}
        for phase in ('full','variants'):
            spec=report[phase][ep];verify(ROOT/spec['directory'],spec['manifest'])
            values=list(training.data.stream_rows(ROOT/spec['directory'],spec['manifest']))
            if method.recount(values)!=spec['counts']:raise ValueError('phase raw counter mismatch')
            lanes[phase]=values;events.extend(values)
        if any(not x['same_as_primary_answer'] for x in lanes['full']):raise ValueError('FULL mismatch cannot be reclassified')
        for mode in method.MODES[1:]:
            selected=[x for x in lanes['variants'] if x['mode']==mode]
            if not any(x['status']=='GENERATED' for x in selected):
                pairs[ep+'/'+mode]=dict(status='NO_ELIGIBLE_CASES');continue
            pairs[ep+'/'+mode+'/all']=method.paired(lanes['full'],selected)
            for language in ('ko','en'):
                subset=[x for x in selected if x['language']==language]
                if any(x['status']=='GENERATED' for x in subset):pairs[ep+'/'+mode+'/language='+language]=method.paired(lanes['full'],subset)
            for turn in (1,2,3):
                subset=[x for x in selected if x['turn']==turn]
                if any(x['status']=='GENERATED' for x in subset):pairs[ep+'/'+mode+'/turn='+str(turn)]=method.paired(lanes['full'],subset)
    counts=method.recount(events);actual={(x['endpoint'],x['root'],x['turn'],x['mode']):x['status']=='GENERATED' for x in events}
    if actual!=expected or len(events)!=1920:raise ValueError('all384x5 eligibility/consumer events required')
    training.write(target,dict(info(),status='SOURCE_WINDOW_RAW_RECOUNTED',counts=counts,pairs=pairs,events=len(events),
        report_sha256=training.data.digest(EVIDENCE/'probe/report.json'),scope='matched eligible cases; fixed old actual history, NOT new dialogue trajectories'))
    print('[SOURCE_WINDOW_READBACK] '+json.dumps({k:v for k,v in pairs.items() if k.endswith('/all')}),flush=True);return 0


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--mode',choices=('cpu','freeze','probe','readback'),required=True)
    p.add_argument('--max-wall-sec',type=int,default=1800);g=p.add_mutually_exclusive_group(required=True)
    g.add_argument('--execute',action='store_true');g.add_argument('--check-only',action='store_true');a=p.parse_args()
    if not 60<=a.max_wall_sec<=3600:p.error('bounded60..3600')
    if a.check_only:print('[SOURCE_WINDOW_CHECK_ONLY] '+json.dumps(info()));return 0
    try:
        course.prior.producer.legacy.source.deadline()
        if a.mode=='probe':return probe(a)
        return {'cpu':cpu,'freeze':freeze,'readback':readback}[a.mode]()
    except GateNegative as exc:print('[SOURCE_WINDOW_HOLD] '+str(exc));return 8
    except KeyboardInterrupt:print('[SOURCE_WINDOW_INTERRUPTED] partial owned outputs preserved');return 130
    except Exception as exc:
        import traceback
        traceback.print_exc();print('[SOURCE_WINDOW_ERROR] '+str(exc));return 9


if __name__=='__main__':raise SystemExit(main())
