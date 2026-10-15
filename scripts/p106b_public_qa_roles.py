"""Strict numbered public QA role repacking, with no content-quality filter."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import re
from scripts import p106b_grounded_span as source
from tinylm.chat.canonical import normalize,validate
VERSION='P106B_PUBLIC_ORIGINAL_THREE_QA_ROLES_V1'


def split_three(row):
    m=row['meta']
    if m.get('source')!='p106b_public_direct' or m.get('selection_family')!='Flan-Coqa':raise ValueError('declared existing CoQA list producer only')
    if len(row['messages'])<2 or [x['role'] for x in row['messages'][:2]]!=['user','assistant']:raise ValueError('original paired roles required')
    texts=[source.text(x) for x in row['messages'][:2]];marks=[]
    for text in texts:
        items=[list(re.finditer(r'(?<!\S)'+str(n)+r'\.\s+',text)) for n in range(1,5)]
        if any(len(v)!=1 for v in items):raise ValueError('unique explicit boundaries1..4 required, no inferred translated units')
        found=[v[0] for v in items]
        if [v.start() for v in found]!=sorted(v.start() for v in found):raise ValueError('increasing numbered boundaries required')
        marks.append(found)
    ref=texts[0][:marks[0][0].start()];pairs=[]
    for i in range(3):
        ranges=[[p[i].end(),p[i+1].start()] for p in marks]
        question,answer=[text[a:b].strip() for text,(a,b) in zip(texts,ranges)]
        if not question or not answer:raise ValueError('nonempty original question and answer required')
        pairs.append(dict(number=i+1,question=question,answer=answer,original_question_range=ranges[0],original_answer_range=ranges[1]))
    first=source.first_pair(row)
    if (first['reference'],first['question'],first['answer'])!=(ref,pairs[0]['question'],pairs[0]['answer']):raise ValueError('first QA must match prior source contract')
    return dict(reference=ref,pairs=pairs,original_reference_range=[0,marks[0][0].start()],original_messages_sha256=source.sha(row['messages'][:2]))


def wrap(row):
    p=split_three(row);language=row['meta']['language']
    if language not in ('ko','en'):raise ValueError('declared language required')
    prefix=('다음 자료를 읽고 현재 질문에 대한 짧은 답만 쓰세요.\n자료:\n' if language=='ko' else
        'Read the following reference and give only the short answer to the current question.\nReference:\n')
    marker='\n질문:\n' if language=='ko' else '\nQuestion:\n'
    messages=[]
    for i,pair in enumerate(p['pairs']):
        question=prefix+p['reference']+marker+pair['question'] if i==0 else pair['question']
        messages.extend([dict(role='user',content=question),dict(role='assistant',content=pair['answer'])])
    # Do not inherit a later JSON/control task's UNIQUE_JSON or precomputed token
    # counts from the old capability wrapper when reusing its original first pair.
    keys=('source_repo','source_revision','source_license','source_family','selection_family','source_id','source_sha256',
          'source_group_id','parent_concept_id','language','rights_status','source_split')
    meta={k:row['meta'][k] for k in keys if k in row['meta']}
    meta.update(kind='public_original_three_qa',source='original_public_qa_role_repack',course_version=VERSION,
        source_truth='ORIGINAL_PUBLIC_UNVERIFIED',semantic_truth='NOT_REVIEWED',teacher_calls=0,
        original_messages_sha256=p['original_messages_sha256'],original_reference_range=p['original_reference_range'],
        original_item_ranges=[{k:v for k,v in x.items() if k.endswith('_range') or k=='number'} for x in p['pairs']],
        role_origin='original numbered QA1,QA2,QA3 in source order; not teacher-generated or inferred role')
    return validate(normalize(dict(messages=messages,meta=meta))),p
