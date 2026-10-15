"""Frozen complete-source jobs and common two-turn source-only rendering.

No model/download/protected path access. Exact overlap prevents literal source
reuse; cross-language semantic duplication remains explicitly unreviewed.
"""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from collections import Counter,defaultdict
import copy
from scripts import diag_p106b_grounded_span as source
from scripts import p106b_dualqa_teacher as teacher_fields
from scripts import p106b_dualqa_optional_note as parser
from tinylm.chat.canonical import normalize,validate
ORIGINAL_WRAP=teacher_fields.wrap
VERSION='P106B_DUAL_QA_SOURCE_SCOPE_V1'
SOURCE_TOKEN_LIMIT=736
TARGETS={'train':768,'dev':64,'test':128}
RESERVES={'train':64,'dev':16,'test':16}
SCOPE={'ko':'앞서 제시된 자료를 기준으로 답하세요.\n','en':'Answer using the reference provided earlier.\n'}


def job_from_row(row,split,reserve_order=0):
    m=row['meta'];pair=m['original_first_pair'];ref=pair['reference']
    return dict(root=m['semantic_root_id'],language=m['language'],split=split,reserve_order=reserve_order,
        target_per_lane=TARGETS[split],reference=ref,reference_sha256=teacher_fields.reference_sha(ref),
        bridge_question=pair['question'],bridge_gold=pair['answer'],
        provenance={k:m[k] for k in ('source_repo','source_revision','source_id','source_family','source_license','source_sha256','rights_status') if k in m})


def render(job,fields,tok,*,repeat_first=False,record_id=''):
    row=ORIGINAL_WRAP(job,fields,tok,repeat_first=repeat_first,record_id=record_id)
    if len(row['messages'])!=4:raise ValueError('two actual assistant turns required for this course')
    old=''.join(b['text'] for b in row['messages'][2]['content'])
    row['messages'][2]['content']=[dict(type='text',text=SCOPE[job['language']]+old)]
    row['meta'].update(course_version=VERSION,generation_version=parser.VERSION,teacher_parser_contract=parser.VERSION,
        source_split=job['split'],kind='public_qa',rubric='UNSCORED_PUBLIC_QA',
        known_output_contract='FACTORY_REPEAT_QA1_ALLOWED' if repeat_first else 'SOURCE_TWO_DISTINCT_QA',
        teacher_content_pairs=copy.deepcopy(fields['pairs']),teacher_note_defaulted=fields.get('empty_note_filled_by_code',False),
        source_scope_second_turn='CODE_SOURCE_SCOPE_V1',source_reference_sha256=job['reference_sha256'])
    from tinylm.train.mtp_sft import encode_record
    row=validate(normalize(row));rec=encode_record(row,tok)
    if rec.x_tokens>1024 or {s for s in rec.segments if s}!={1,2}:raise ValueError('complete two-turn scope1024; shorten new QA only')
    lo,hi=row['meta']['student_reference_range'];actual=''.join(b['text'] for b in row['messages'][0]['content'])
    if actual[lo:hi]!=job['reference']:raise ValueError('complete original reference changed')
    row['meta'].update(actual_x_tokens=rec.x_tokens,assistant_targets=rec.targets,assistant_turns=2)
    return row


def repeat_from_student(row,tok):
    m=row['meta'];lo,hi=m['student_reference_range'];first=''.join(b['text'] for b in row['messages'][0]['content'])
    job=dict(root=m['semantic_root_id'],language=m['language'],split=m['source_split'],reference=first[lo:hi],
        reference_sha256=m['source_reference_sha256'],provenance={k:m[k] for k in ('source_repo','source_revision','source_id','source_family','source_license','source_sha256') if k in m})
    fields=dict(status='QA_FIELDS_COMPLETE',pairs=m['teacher_content_pairs'],note=m['teacher_note'],empty_note_filled_by_code=m.get('teacher_note_defaulted',False))
    return render(job,fields,tok,repeat_first=True,record_id=m['teacher_record_id'])


def eligible(row,tok):
    return row['meta'].get('kind')=='natural_first_qa' and len(tok.encode(row['meta']['original_first_pair']['reference']).ids)<=SOURCE_TOKEN_LIMIT


def deck(tok,tag):
    from scripts import diag_p106b_dualqa_optional_note as pilot
    frozen,old,_=source.read_course();pilot_report=source.required(pilot.OUTPUT/'report.json')
    if pilot_report['status']!='DUALQA_TEACHER_PILOT_COLLECTED' or not pilot_report['technical_wire_ready']:
        raise ValueError('completed actual optional-NOTE pilot required')
    for p,sha in pilot_report['code_sha256'].items():
        if source.public.digest(ROOT/p)!=sha:raise ValueError('pilot code changed')
    pilot_jobs=list(source.public.stream_rows(pilot.OUTPUT,pilot_report['source_manifest']));exclude_pilot={x['root'] for x in pilot_jobs}
    pools=defaultdict(list);known_roots=set();known_keys=set();legacy_roots,legacy_keys,legacy=source.old_source_exclusions()
    for split,rows in old.items():
        for row in rows:
            m=row['meta']
            if m.get('kind')!='natural_first_qa':continue
            known_roots.add(m['parent_concept_id'].upper());known_keys.update(source.method.passage_keys(m['original_first_pair']['reference']))
            if split in ('train','dev') and m['semantic_root_id'] not in exclude_pilot and eligible(row,tok):pools[split,m['language']].append(row)
    previous_keys=known_keys|legacy_keys
    legacy_roots={root.upper() for root in legacy_roots}
    if source.public.digest(source.public.PUBLIC/'report.json')!=source.public.PUBLIC_SHA:raise ValueError('original public source changed')
    fresh=[];seen=set();rejections=Counter()
    for original_split in ('train','val'):
        manifest=source.required(source.public.PUBLIC/(original_split+'_shards_manifest.json'))
        for row in source.public.stream_rows(source.public.PUBLIC,manifest):
            m=row['meta']
            if m.get('selection_family')!='Flan-Coqa':continue
            lang=m.get('language');root=m['parent_concept_id'].upper()
            if root in known_roots or root in legacy_roots:continue
            try:
                pair=source.method.first_pair(row)
                if len(tok.encode(pair['answer']).ids)>24:continue
                natural=source.method.wrap(row,pair,'test')
                if not eligible(natural,tok):continue
                from tinylm.train.mtp_sft import encode_record
                encode_record(natural,tok)
            except ValueError:continue
            identity=natural['meta']['semantic_root_id']
            if identity in seen:continue
            seen.add(identity);keys=source.method.passage_keys(pair['reference'])
            if keys&previous_keys:rejections['previous_literal_passage']+=1;continue
            fresh.append((natural,keys))
    taken=set()
    for row,keys in sorted(fresh,key=lambda p:teacher_fields.sha([tag,p[0]['meta']['semantic_root_id']])):
        if keys&taken:rejections['fresh_exact_passage_overlap']+=1;continue
        taken.update(keys);pools['test',row['meta']['language']].append(row)
    supply={':'.join(k):len(v) for k,v in pools.items()};jobs=[]
    for split in TARGETS:
        for language in ('ko','en'):
            values=sorted(pools[split,language],key=lambda row:teacher_fields.sha([tag,split,row['meta']['semantic_root_id']]))
            need=TARGETS[split]+RESERVES[split]
            if len(values)<need:raise source.GateNegative('bounded unique source supply short: '+str(supply))
            jobs.extend(job_from_row(row,split,i) for i,row in enumerate(values[:need]))
    jobs.sort(key=lambda x:(x['reserve_order'],list(TARGETS).index(x['split']),x['language']))
    roots=defaultdict(set)
    for job in jobs:roots[job['split']].add(job['root'])
    if any(roots[a]&roots[b] for a,b in (('train','dev'),('train','test'),('dev','test'))):raise ValueError('root split overlap')
    info=dict(supply=supply,rejections=dict(rejections),source_report_sha256=source.public.digest(source.CORPUS/'report.json'),
        pilot_report_sha256=source.public.digest(pilot.OUTPUT/'report.json'),legacy_exclusion_refs=legacy,
        targets=TARGETS,reserves=RESERVES,source_token_limit=SOURCE_TOKEN_LIMIT,
        original_source_bytes_retained=True,exact_source_overlap=0,cross_language_semantic_overlap='NOT_AUDITED',
        prior_source0_test_not_reused_as_new_final=True,pilot_contexts_excluded=8,
        public_source_report_sha256=source.public.PUBLIC_SHA)
    return jobs,info
