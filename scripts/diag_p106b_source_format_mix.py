"""Independent format-mix course: same source/targets, changed user formatting only."""
from __future__ import annotations
import argparse
from collections import Counter, defaultdict
import copy
from pathlib import Path
import sys
from unittest.mock import patch
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import json
from scripts import diag_p106b_source_course as course
from scripts import diag_p106b_context_quality as prior
from scripts.p106b_shards import ShardWriter, verify

TAG = 'p106b_source_format_mix_v1_s1337'
OUTPUT = ROOT / 'HF/sft_ready' / TAG
CORPUS = OUTPUT / 'corpus'
LOCAL = ROOT / 'test_result/evidence/local' / TAG
EVIDENCE = ROOT / 'test_result/evidence' / TAG
BASE_INFO = course.info
CODE = course.CODE + ('scripts/diag_p106b_source_format_mix.py',
                      'scripts/test_p106b_source_format_mix.py')


def info():
    value = BASE_INFO()
    value.update(schema='P106B_SOURCE_FORMAT_MIX_V1', tag=TAG,
                 reference_weight_options=[0.], reference_weight=0.,
                 format_axis='half supported rows natural reference+question; missing rows unchanged',
                 input_token_equality='NOT_EXPECTED; same sources/targets/32updates, measure separately',
                 code_sha256={p:course.public.digest(ROOT/p) for p in CODE})
    return value


def natural_selection(rows):
    lanes = defaultdict(list)
    for row in rows:
        if row['meta']['kind'] == 'source_qa':
            lanes[(row['meta']['language'], row['meta']['course_family'])].append(
                row['meta']['parent_concept_id'])
    selected = set()
    for lane, roots in lanes.items():
        if len(roots) != len(set(roots)) or len(roots) % 2:
            raise ValueError('unique even-sized supported lane required: '+str(lane))
        selected.update(sorted(roots, key=lambda x:course.support.sha([TAG,x]))[:len(roots)//2])
    return selected


def transform(row, question, natural):
    result = copy.deepcopy(row)
    meta = result['meta']
    reference = meta.get('reference_text', '')
    if natural:
        if meta['kind'] != 'source_qa' or not reference or not question.strip():
            raise ValueError('natural format requires supported question and exact reference')
        result['messages'][0]['content'] = reference+'\n\n'+question
    meta.update(format_view='NATURAL_REFERENCE_QUESTION' if natural else 'CONTROLLED_REFERENCE_CONTRACT',
                visible_reference_text=reference, reference_text='',
                original_source_course=meta['source_course'], source_course='P106B_SOURCE_FORMAT_MIX_V1',
                reference_auxiliary_enabled=False)
    if natural:
        meta['reference_required_contract']='SOURCE_VISIBLE_CONTENT_TASK; no global source-only instruction'
    return course.data.validate(course.data.normalize(result))


def corpus():
    if OUTPUT.exists() or OUTPUT.is_symlink():
        raise FileExistsError('fresh format namespace required')
    old_report, rows = course.read_course()
    teacher_report = json.loads((course.OUTPUT/'teacher/report.json').read_text())
    questions = {r['item']['root']:r['question'] for r in
                 course.public.stream_rows(course.OUTPUT/'teacher',teacher_report['candidate_manifest'])}
    from tokenizers import Tokenizer
    tok = Tokenizer.from_file(str(course.public.TOKENIZER))
    if course.public.digest(course.public.TOKENIZER) != course.public.TOK_SHA:
        raise ValueError('tokenizer changed')
    planned = {}; totals = {}; roots = {}
    for split, values in rows.items():
        natural = natural_selection(values)
        planned[split] = []; count = Counter(); roots[split] = set()
        for row in values:
            root = row['meta']['parent_concept_id']; roots[split].add(root)
            edited = transform(row,questions[root],root in natural and row['meta']['kind']=='source_qa')
            rec = course.data.record(edited,tok)
            if rec.x_tokens > 1024: raise ValueError('declared token budget exceeded')
            if edited['messages'][-1] != row['messages'][-1]: raise ValueError('assistant target changed')
            planned[split].append(edited)
            count.update(rows=1,actual_x_tokens=rec.x_tokens,assistant_targets=rec.targets)
            count[edited['meta']['format_view']+':'+edited['meta']['kind']] += 1
        totals[split] = dict(count)
        if count['assistant_targets'] != old_report['counts'][split]['assistant_targets']:
            raise ValueError('same target exposure required')
    if roots['train'] & roots['val']: raise ValueError('source split collision')
    CORPUS.mkdir(parents=True,exist_ok=False); manifests = {}
    for split, values in planned.items():
        writer = ShardWriter(CORPUS,split)
        for row in values: writer.append(row)
        manifests[split] = writer.close(lineage=info()); verify(CORPUS,manifests[split])
    report = dict(info(),status='COURSE_FROZEN',counts=totals,manifests=manifests,
                  parent_corpus=str(course.CORPUS.relative_to(ROOT)),
                  parent_corpus_sha256=course.public.digest(course.CORPUS/'report.json'),
                  teacher_report_sha256=course.public.digest(course.OUTPUT/'teacher/report.json'),
                  source_root_overlap=0,unique_source_groups={s:len(v) for s,v in roots.items()},
                  source_answer_truth='PSEUDO_UNVERIFIED; no new teacher or semantic filtering')
    course.training.write(CORPUS/'report.json',report)
    course.training.write(EVIDENCE/'corpus_report.json',report)
    print('[FORMAT_MIX_CORPUS] '+json.dumps(totals)); return 0


def read_course():
    report = json.loads((CORPUS/'report.json').read_text())
    if report['status']!='COURSE_FROZEN' or report['code_sha256']!=info()['code_sha256']:
        raise ValueError('frozen format corpus/code changed')
    for manifest in report['manifests'].values(): verify(CORPUS,manifest)
    return report,{s:list(course.public.stream_rows(CORPUS,m)) for s,m in report['manifests'].items()}


def train(args):
    args.arm = 'sft_only'
    with patch.object(prior,'TAG',TAG), patch.object(prior,'CORPUS',CORPUS), \
         patch.object(prior,'EVIDENCE',LOCAL), patch.object(prior,'read_course',read_course), \
         patch.object(prior,'info',info), patch.object(prior,'ARMS',{'sft_only':('parent_ntp',5e-5)}):
        with course.data.ReferenceObjective(0.) as objective:
            rc = prior.train(args)
    report = json.loads((LOCAL/'sft_only/report.json').read_text())
    report.update(reference_target_events=objective.executed_targets,reference_weight=0.,
                  raw_answers='LOCAL_ONLY_IGNORED',direct_val_comparison_with_original='NOT_VALID_DIFFERENT_PROMPTS',
                  same_sources_targets_not_same_x=True,model_adopted=False)
    course.training.write(EVIDENCE/'sft_only_report.json',report); return rc


def development(args):
    from scripts import diag_p106b_context_transfer as old
    target=EVIDENCE/'dev24'
    def preflight():
        if target.exists():raise FileExistsError('development raw preserved')
        subjects=[dict(id='parent',path=str(course.training.PARENT.relative_to(ROOT)),sha=course.training.PARENT_SHA)]
        for directory,arm,name in ((course.EVIDENCE,'sft_only','sft_only'),
                                   (course.EVIDENCE,'reference_lm','reference_lm'),
                                   (EVIDENCE,'sft_only','format_mix')):
            path=directory/(arm+'_report.json');report=json.loads(path.read_text())
            if report['updates']!=32 or report['status']!='CONTEXT_SFT_COMPLETE_REVIEW_PENDING':
                raise FileNotFoundError('same32 completed endpoint required')
            subjects.append(dict(id=name,path=report['checkpoint'],sha=report['checkpoint_sha256']))
        for item in subjects:
            if course.public.digest(ROOT/item['path'])!=item['sha']:raise ValueError('checkpoint changed')
        return subjects,dict(schema='P106B_SOURCE_FORMAT_MIX_DEVELOPMENT24_V1',subjects=subjects,
            case_sha256=course.support.sha(old.cases()),precision='FP32_MATH_NO_TF32',cache=True,mtp_tokens=1,max_new=64,
            code_sha256={p:course.public.digest(ROOT/p) for p in
                         CODE+('scripts/diag_p106b_context_transfer.py','tinylm/infer/generate.py')},
            test_scope='DEVELOPMENT_REPEAT_NOT_INDEPENDENT; old24 not inserted into current training',
            training='NOT_RUN',checkpoint_save=False)
    with patch.object(old,'TARGET',target),patch.object(old,'preflight',preflight):return old.execute(args)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--mode',choices=('corpus','train','dev'),required=True)
    p.add_argument('--max-wall-sec',type=int,default=1200)
    g=p.add_mutually_exclusive_group(required=True)
    g.add_argument('--execute',action='store_true');g.add_argument('--check-only',action='store_true')
    args=p.parse_args()
    if not 60<=args.max_wall_sec<=1200: p.error('bounded60..1200')
    try:
        if args.check_only:
            if args.mode=='train':read_course()
            print('[CHECK_ONLY] '+json.dumps(info()));return 0
        return {'corpus':corpus,'train':lambda:train(args),'dev':lambda:development(args)}[args.mode]()
    except (FileExistsError,FileNotFoundError) as exc:print('[HOLD] '+str(exc));return 8
    except Exception as exc:print('[FORMAT_MIX_ERROR] '+type(exc).__name__+': '+str(exc));return 9

if __name__=='__main__':raise SystemExit(main())
