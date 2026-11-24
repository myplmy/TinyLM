"""One sealed afternoon candidate: fresh language questions and official11."""
import argparse
from contextlib import contextmanager
import gc
import json
import time
import traceback
import sysconfig
import torch
from torch.nn.attention import sdpa_kernel, SDPBackend
from scripts import p108b_pm_frozen as frozen
from scripts import p108b_pm_questions as questions
from scripts import p108b_norm_sweep as limits
from scripts import diag_p108b_evaluate as generation
from scripts import diag_p108b_norm_sweep as study
from scripts import diag_p108b_value_library as library
from scripts import diag_p108b_policy as raw
from scripts import p108b_replay as replay
from scripts import p108b_decode as decoder
from scripts.p108b_tinylm import TinyAdapter
from scripts import interactive_research_infer as manual
from scripts import p108_weight_space as metrics
from scripts import p108b_policy as devmetrics
from scripts import diag_p108_frozen_edit_official as official_owner
from scripts import diag_p108b_official as official_history
from scripts import p106b_official_lm_adapter as lm_adapter
from scripts.p106b_shards import ShardWriter

ROOT,BASE,SOURCE=frozen.ROOT,frozen.BASE,frozen.SOURCE
PROFILE=BASE/'pm_evaluation_profile_v1.json'
DATA=BASE/'pm_fresh_final128_v1.json'
CODE=('scripts/p108b_pm_frozen.py','scripts/p108b_pm_questions.py',
      'scripts/diag_p108b_pm_evaluate.py','scripts/test_p108b_pm_contract.py')


def old_questions():
    rows=study.read(SOURCE/'data.json')['rows']+study.read(SOURCE/'select_dev.json')['rows']
    rows+=study.read(SOURCE/'final_language.json')['rows']
    return [r['question'] for r in rows]


def prepare():
    study.verify();chosen=frozen.selection()
    if PROFILE.exists() or DATA.exists():raise FileExistsError('fresh evaluation namespace required')
    data=questions.build();questions.validate(data,old_questions())
    refs=dict(study.reference_set())
    for p in (study.PROFILE,BASE/'norm_selection_v1.json',ROOT/chosen['source'],ROOT/chosen['packet']['path']):
        refs[str(p.relative_to(ROOT))]=manual.file_sha(p)
    code=sorted(set(CODE)|set(official_owner.CODE)|set(study.CODE)|set(generation.SOURCES))
    library.write_new(DATA,data)
    library.write_new(PROFILE,dict(schema='P108B_PM_FROZEN_EVALUATION_V1',authority_directive=141,
        authority_end=limits.AUTHORITY_END.isoformat(),selected=chosen['name'],origin=study.read(study.PROFILE)['origin'],
        parent_model=study.read(study.PROFILE)['parent_model'],source_identity=frozen.source_identity(code),
        references=refs,data_sha256=manual.file_sha(DATA),selection_sha256=manual.file_sha(BASE/'norm_selection_v1.json'),
        arms=['original',chosen['name']],decoder=dict(name='GREEDY',temperature=0.,top_k=1,repetition_penalty=1.),
        initial_inputs=128,actual_turns_per_model=144,strict_items_per_model=88,max_new=128,seed=17,
        planned_generated_calls=290,final_used_for_selection=False,reselection_after_evaluation=False,
        initial_plan_sha256=manual.file_sha(ROOT/library.PLAN)))
    with (BASE/'pm_evaluation_initial_plan_v1.md').open('xb') as stream:stream.write((ROOT/library.PLAN).read_bytes())
    print(json.dumps(dict(status='FRESH_EVALUATION_SEALED',candidate=chosen['name'],inputs=128,actual_turns=144)))


def verify():
    limits.Budget().check();p=study.read(PROFILE);chosen=frozen.selection()
    if p['selected']!=chosen['name'] or p['selection_sha256']!=manual.file_sha(BASE/'norm_selection_v1.json'):
        raise ValueError('frozen pre-final candidate required')
    if p['authority_end']!=limits.AUTHORITY_END.isoformat() or p['authority_directive']!=141:
        raise ValueError('current exact authority required')
    if p['source_identity']!=frozen.source_identity(p['source_identity']['files']):
        raise ValueError('sealed evaluation source changed')
    for path,sha in p['references'].items():
        if manual.file_sha(ROOT/path)!=sha:raise ValueError('sealed reference changed: '+path)
    if p['data_sha256']!=manual.file_sha(DATA) or p['initial_plan_sha256']!=manual.file_sha(BASE/'pm_evaluation_initial_plan_v1.md'):
        raise ValueError('sealed data/initial plan changed')
    questions.validate(study.read(DATA),old_questions())
    return p


@contextmanager
def runtime(name,budget):
    p=verify();arm=frozen.arm(name);data=study.read(SOURCE/'data.json')
    adapter=active=None
    with manual.selected_runtime(manual.resolve_model(p['parent_model'])) as active:
        adapter=TinyAdapter(active,[r for r in data['rows'] if r['split']=='fit'],data['calibration_questions'],budget=budget)
        try:
            with replay.install(adapter,arm,packets_loader=frozen.packet_loader) as proof:
                canary=adapter.generate(arm['answers'][0],max_new=64,variant=name+':PM_FINAL_REPLAY')
                if canary['generation']['generated_ids']!=arm['answers'][0]['generation']['generated_ids']:
                    raise RuntimeError('exact native greedy replay differs')
                proof.update(canary=canary,complete_core_sha_replayed=True,generation_replay_count=1,
                             origin=p['origin'],final_data_did_not_fit_or_select_weights=True)
                yield active,adapter,proof
        finally:
            if adapter is not None:adapter.close()
    active=adapter=None;gc.collect()


def generate():
    p=verify();budget=limits.Budget(1800);data=study.read(DATA)
    torch.set_num_threads(4);torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
    for name in p['arms']:
        directory=BASE/'pm_fresh_final_v1'/name
        if directory.exists():raise FileExistsError('previous complete/failed evaluation preserved')
        directory.mkdir(parents=True);started=time.monotonic();failure=None
        result=dict(name=name,status='STARTED',source_profile_sha256=manual.file_sha(PROFILE),
            optimizer_updates=0,checkpoint_writes=0,new_generated_calls=0,answers_for_selection=False)
        writer=None
        try:
            result['entry_resources']=library.resources()
            with sdpa_kernel(SDPBackend.MATH),torch.no_grad(),runtime(name,budget) as (active,adapter,proof):
                result['weight_replay']=proof;result['new_generated_calls']+=1
                torch.cuda.reset_peak_memory_stats();writer=ShardWriter(directory,'answers',limit=3_000_000);answers=[]
                def emit(row,history):
                    budget.check()
                    record=generation.generated(active,row,decoder.Decoder('GREEDY'),p['seed'],p['max_new'],history)
                    record.update(variant=name,evaluation_role=data['role'])
                    result['new_generated_calls']+=1
                    return record
                for row in generation.dialogue(data['rows'],emit):writer.append(row);answers.append(row)
                if len(answers)!=144:raise RuntimeError('all144 actual dialogue calls required')
                result['answers_manifest']=writer.close(lineage=dict(arm=name,role=data['role'],core_sha256=proof['edited_core_sha256']))
                writer=None
                result.update(summary=metrics.summarize(answers),initial_summary=metrics.summarize([r for r in answers if r['turn']==1]),
                    unwanted_loops=devmetrics.unwanted_loops(answers),root_language_review='PENDING',
                    peak_allocated_mib=torch.cuda.max_memory_allocated()/2**20,
                    peak_reserved_mib=torch.cuda.max_memory_reserved()/2**20,status='FRESH_FINAL_COMPLETE_ROOT_REVIEW_PENDING')
            result['original_core_restored']=proof['original_core_restored']
        except BaseException as error:
            failure=error;result.update(status='FRESH_FINAL_ERROR',error=str(error),traceback=traceback.format_exc())
            if writer is not None:result['partial_answers_manifest']=writer.close(lineage=dict(partial=True))
        finally:
            gc.collect();cleanup_error=library.cleanup(result)
            if failure is None:failure=cleanup_error
            result['wall_seconds']=time.monotonic()-started;library.write_new(directory/'report.json',result)
            print('[PM_FINAL_END] '+json.dumps({k:result.get(k) for k in ('name','status','new_generated_calls','summary','unwanted_loops','original_core_restored','cuda_allocated_after_bytes','cuda_reserved_after_bytes','error')}),flush=True)
        if failure is not None:raise RuntimeError('preserved fresh evaluation error') from failure


def official():
    p=verify();name=p['selected'];baseline=official_history.baseline_reference()
    if baseline['origin']!=p['origin']:raise ValueError('existing original official baseline origin differs')
    def identity():return verify()['source_identity']
    def bundle():return {'actual/report.json':dict(origin=p['origin'])},None,None
    @contextmanager
    def official_runtime(_name,_frozen,_packets,_expected,_target):
        lm=None
        with runtime(_name,limits.Budget(1800)) as (active,_adapter,proof):
            try:
                lm=lm_adapter.create_adapter(active,runtime_root=Path(sysconfig.get_paths()['purelib']),batch_size=8)
                yield lm,proof
            finally:
                if lm is not None:lm.close()
    from pathlib import Path
    selected_files={path:manual.file_sha(BASE/path) for path in ('norm_selection_v1.json','pm_evaluation_profile_v1.json')}
    evaluator=decoder.private_function(official_owner.evaluate,identity=identity,bundle=bundle,
        model_runtime=official_runtime,OUTPUT=BASE/'pm_official_v1',BASE=BASE,FROZEN=selected_files,
        TAG='p108b_pm_frozen_official11_v1_s1337')
    failure=None;result=dict(status='STARTED')
    try:result=evaluator(name,p['source_identity']['sha256'],1800)
    except BaseException as error:failure=error;result.update(status='PM_OFFICIAL_ERROR',error=str(error))
    finally:
        gc.collect();cleanup_error=library.cleanup(result)
        if failure is None:failure=cleanup_error
        result.update(original_baseline_reused=baseline,source_identity_unchanged=identity()==p['source_identity'])
        library.write_new(BASE/'pm_official_v1'/(name+'_cleanup.json'),result)
        print('[PM_OFFICIAL_END] '+json.dumps({k:result.get(k) for k in ('status','seconds','cuda_allocated_after_bytes','cuda_reserved_after_bytes','error')}),flush=True)
    if failure is not None:raise RuntimeError('preserved official evaluation failure') from failure


def main():
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=['prepare','check','generate','official']);args=parser.parse_args()
    if args.phase=='prepare':prepare()
    elif args.phase=='check':verify();print('[PM_EVAL_CPU_CHECK] exact selected state/data/source role; no model')
    elif args.phase=='generate':generate()
    else:official()


if __name__=='__main__':main()
