#!/usr/bin/env python3
"""Preserve complete target-window Q/A text and independent protection deltas."""
import json
from collections import Counter
from pathlib import Path

from scripts import diag_p108b_geometry as atlas
from scripts import diag_p108b_policy as policy
from scripts import diag_p108b_value_library as library
from scripts import interactive_research_infer as manual
from scripts.diag_p108b_review_pack import signature

ROOT=atlas.ROOT
BASE=atlas.BASE
DIRECTORY=ROOT/'review_request/20261116_P108B_답전체범위_원답_v1'

def run():
    report_path=BASE/'target_values_v1/writes_v2/report.json'
    report=json.loads(report_path.read_text(encoding='utf-8'))
    if not report['original_core_restored']or report['cuda_allocated_after_bytes']or report['cuda_reserved_after_bytes']:
        raise ValueError('closed native original and CUDA cleanup required')
    geometry=json.loads((BASE/'geometry/report.json').read_text(encoding='utf-8'))
    original=policy.read_answers(BASE/'geometry',geometry['baseline']['answers_manifest'])
    required={r['id']for r in original if r['split']!='select_dev'and r['protected']and r['exact']}
    if len(original)!=164 or len(required)!=7:
        raise ValueError('exact original164 and seven correct legacy protection cases required')
    if DIRECTORY.exists():raise FileExistsError('preserve prior readable packet')
    unique={};models={};source_reports={}
    for arm in report['arms']:
        directory=(ROOT/arm['reused_from'])if arm.get('reused_from')else BASE/'target_values_v1/writes_v2'/arm['name']
        source_reports[arm['name']]=manual.file_sha(directory/'report.json')
        rows=policy.read_answers(directory,arm['answers_manifest'])
        if len(rows)!=164 or {r['id']for r in rows}!={r['id']for r in original}:
            raise ValueError('complete164 exact input IDs required')
        legacy=[r for r in rows if r['split']!='select_dev']
        dev=[r for r in rows if r['split']=='select_dev']
        kept={r['id']for r in legacy if r['protected']and r['exact']}
        models[arm['name']]=dict(legacy_protection_correct_ids=sorted(kept),
            lost_original_legacy_protection_ids=sorted(required-kept),
            legacy_protection_correct=len(kept),legacy_protection_scored=16,
            new_dev_protection=arm['dev'],legacy_empty=sum(r['diagnostics']['empty']for r in legacy),
            dev_empty=sum(r['diagnostics']['empty']for r in dev),
            dev_finish_reasons=dict(Counter(r['generation']['finish_reason']for r in dev)),
            dev_content_tokens=sum(r['generation']['content_tokens']for r in dev),
            dev_generated_tokens=sum(r['generation']['generated_tokens']for r in dev))
        for row in rows:
            key=signature(row)
            if key not in unique:
                unique[key]=dict(row,review_id=f'T{len(unique):04d}',qa_signature=key,occurrences=[])
            unique[key]['occurrences'].append(dict(model=arm['name'],id=row['id'],split=row['split'],
                family=row['family'],language=row['language']))
    rows=list(unique.values())
    if len(rows)!=387:raise ValueError('frozen four-arm unique answer count differs')
    DIRECTORY.mkdir(parents=True);parts=[]
    for start in range(0,len(rows),30):
        group=rows[start:start+30];path=DIRECTORY/f'answers_{start//30+1:03d}.txt'
        lines=['P108B 답전체범위 실제 답변 판독용',
            '정답성·문장성·자연스러움은 별개입니다. 새 FINAL이나 일반 대화 평가가 아닙니다.',
            '같은 질문/실제 이력/답만 중복 판독을 생략합니다. 원래 모델의164답과 정확히 대응합니다.','']
        for row in group:
            lines.extend([row['review_id']+' / '+row['language']+' / '+row['family'],
                '대응> '+', '.join(r['model']+':'+r['id']for r in row['occurrences']),
                '질문> '+row['question'],'답변> '+row['answer'],
                '기준> '+str(row['expected'])+' / 엄격 정답> '+str(row['exact']),
                '종료> '+row['generation']['finish_reason'],''])
        text='\n'.join(lines)+'\n'
        if len(text.encode())>=20_000_000:raise ValueError('readable part exceeds20MB')
        with path.open('x',encoding='utf-8')as stream:stream.write(text)
        parts.append(dict(path=str(path.relative_to(ROOT)),sha256=manual.file_sha(path),
            unique_ids=[r['review_id']for r in group]))
    library.write_new(DIRECTORY/'SOURCE_ROWS_v1.json',dict(rows=rows))
    library.write_new(DIRECTORY/'READING_MANIFEST_v1.json',dict(source_report_sha256=manual.file_sha(report_path),
        source_reports=source_reports,answers=656,unique_answers=387,parts=parts,semantic_grading='ROOT_PENDING'))
    library.write_new(ROOT/'handoff/audit/nov16_p108b/TARGET_WINDOW_READBACK_v1.json',dict(
        schema='P108B_TARGET_WINDOW_READBACK_V1',models=models,
        original_legacy_protection_ids=sorted(required),raw_reports_unchanged=True,
        note='original writer lost_original_protected_ids refers only to new SELECT-DEV protection, whose original score is zero; legacy protection transitions are independently recomputed here',
        root_text_status='PENDING',readable_directory=str(DIRECTORY.relative_to(ROOT))))
    print(json.dumps(dict(answers=656,unique=387,parts=len(parts),models=models),ensure_ascii=False))

if __name__=='__main__':run()
