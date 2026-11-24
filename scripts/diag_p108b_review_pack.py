#!/usr/bin/env python3
"""Readable complete FINAL Q/A packets; no automatic semantic ratings."""
import hashlib
import json
import random
from scripts import diag_p108b_evaluate as evaluation
from scripts import diag_p108b_geometry as atlas
from scripts import diag_p108b_value_library as library
from scripts import p106b_shards as shards
from scripts import interactive_research_infer as manual


def signature(row):
    return hashlib.sha256(json.dumps({k:row[k]for k in('question','actual_history','answer')},
        ensure_ascii=False,sort_keys=True).encode('utf-8')).hexdigest().upper()


def run():
    p=evaluation.verify();names=list(p['arms']);random.Random(20261116).shuffle(names)
    labels={name:chr(65+i)for i,name in enumerate(names)};all_rows=[];source_reports={}
    for name in p['arms']:
        directory=evaluation.OUT/'final'/name;report=json.loads((directory/'report.json').read_text(encoding='utf-8'))
        if(report['status']!='FINAL_GENERATION_COMPLETE_LANGUAGE_REVIEW_PENDING'or not report['original_restored']or
                report['cuda_allocated_after_bytes']or report['cuda_reserved_after_bytes']):
            raise ValueError('complete FINAL run and strict cleanup required')
        shards.verify(directory,report['answers_manifest']);source_reports[name]=manual.file_sha(directory/'report.json')
        for spec in report['answers_manifest']['shards']:
            for line in(directory/spec['path']).read_text(encoding='utf-8').splitlines():
                row=json.loads(line)
                if row['evaluation_regime']=='COMMON_GREEDY':all_rows.append(dict(row,masked_model=labels[name],model=name))
    if len(all_rows)!=960:raise ValueError('four models times240 actual calls required')
    by_signature={};unique=[]
    for row in all_rows:
        key=signature(row)
        if key not in by_signature:
            sample=dict(row,review_id=f'U{len(unique):04d}',qa_signature=key,occurrences=[])
            by_signature[key]=sample;unique.append(sample)
        sample=by_signature[key]
        if row['question']!=sample['question']or row['actual_history']!=sample['actual_history']or row['answer']!=sample['answer']:
            raise ValueError('hash collision or unequal review context')
        sample['occurrences'].append(dict(id=row['id'],model=row['model'],label=row['masked_model'],language=row['language'],
            family=row['family'],turn=row['turn'],scenario=row['scenario'],source_group=row['source_group']))
    directory=atlas.ROOT/'review_request/20261116_P108B_최종원답_v1'
    if directory.exists():raise FileExistsError('preserve prior readable review packet')
    directory.mkdir(parents=True);parts=[]
    for start in range(0,len(unique),20):
        group=unique[start:start+20];name=f'answers_{start//20+1:03d}.txt'
        lines=['P108B 최종 원답 전량 판독용',
            '동일 질문·전체 실제 이력·답이 모두 같은 경우에만 한 번 싣고 모델/문항 대응을 보존했습니다.',
            '모델명 가림은 독립 인간 맹검을 뜻하지 않습니다. 자동 진단은 의미 판정이 아닙니다.','']
        for row in group:
            lines.extend([row['review_id']+' / '+row['language']+' / '+row['family'],
                '대응: '+', '.join(x['label']+':'+x['id']for x in row['occurrences'])])
            if row['actual_history']:
                lines.append('앞선 실제 대화:')
                for m in row['actual_history']:lines.append(m['role']+'> '+m['content'])
            lines.extend(['질문> '+row['question'],'답변> '+row['answer'],
                '종료> '+row['generation']['finish_reason'],
                '엄격 정답> '+str(row['exact'])+' / 기준> '+str(row['expected']),
                '자동 참고> '+json.dumps(row['diagnostics'],ensure_ascii=False),''])
        path=directory/name;body=chr(10).join(lines)
        if len(body.encode('utf-8'))>=20_000_000:raise ValueError('split text before20MB')
        with path.open('x',encoding='utf-8')as f:f.write(body)
        parts.append(dict(path=str(path.relative_to(atlas.ROOT)),sha256=manual.file_sha(path),
            unique_ids=[r['review_id']for r in group],actual_answer_references=sum(len(r['occurrences'])for r in group)))
    library.write_new(directory/'READING_MANIFEST_v1.json',dict(schema='P108B_ROOT_READABLE_FINAL_V1',
        actual_answers=960,unique_full_context_answers=len(unique),parts=parts,source_reports=source_reports,
        labels=labels,automatic_semantic_judgment=False,root_review_status='NOT_YET_READ'))
    library.write_new(directory/'SOURCE_ROWS_v1.json',dict(rows=unique))
    print(json.dumps(dict(readable_directory=str(directory.relative_to(atlas.ROOT)),answers=960,unique=len(unique),parts=len(parts))))


if __name__=='__main__':run()
