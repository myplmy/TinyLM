#!/usr/bin/env python3
"""Completed lossless transport readback; byte/range contracts, no semantic judge."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import argparse
from collections import Counter
import json
from scripts import diag_p106b_verbatim_source as source
from scripts.audit_p106b_source_layout import assess
from scripts.p106b_shards import verify


def inspect_record(record):
    row=record['candidate'];original=record['item']['source'];meta=row['meta']
    units=json.loads(record['payload']['messages'][1]['content'])['public_source_spans']
    expected=source.message_units(original);student=source.source.support.text(row['messages'][0])
    if units!=[dict(id=u['id'],source_role=u['role'],text=u['text']) for u in expected]:
        raise ValueError('actual teacher payload differs from complete originals/roles')
    ranges=meta['student_original_message_ranges']
    if len(ranges)!=len(expected):raise ValueError('student original-message range count differs')
    for unit,span in zip(expected,ranges):
        if (span['source_message_index']!=unit['source_message_index']
                or student[span['start']:span['end']]!=unit['text'] or span['sha256']!=unit['sha256']):
            raise ValueError('actual student range differs from complete original')
    if meta.get('teacher_reasoning_in_student') is not False:raise ValueError('reasoning/student contract absent')
    return assess(original,meta['source_reference_trace'],units,student)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--execute',action='store_true',required=True)
    args=p.parse_args()
    if not args.execute:p.error('explicit completed-source readback required')
    report=json.loads((source.EVIDENCE/'teacher_report.json').read_text())
    if report['status']!='TEACHER_COURSE_COMPLETE':raise ValueError('completed teacher prerequisite')
    verify(source.OUTPUT/'teacher',report['raw_manifest']);totals=Counter();requests=rows=completion=0;seconds=0.;reasons=Counter()
    for record in source.source.public.stream_rows(source.OUTPUT/'teacher',report['raw_manifest']):
        requests+=1;seconds+=record['seconds'];completion+=record['parsed']['usage'].get('completion_tokens',0)
        if record['structural_reason']:reasons[record['structural_reason']]+=1
        if record.get('candidate') is None:continue
        totals.update(inspect_record(record));rows+=1
    if (rows!=576 or totals['uncovered_whitespace'] or totals['uncovered_nonwhitespace']
            or totals['missing_leading_indent_characters'] or totals['student_has_all_complete_message_texts']!=576):
        raise ValueError('lossless full-cohort transport contract failed')
    value=dict(schema='P106B_COMPLETE_VERBATIM_READBACK_V1',rows=rows,physical_requests=requests,
        counts=dict(totals),structural_retries=dict(reasons),request_sum_sec=seconds,completion_tokens=completion,
        completion_tok_per_sec=completion/seconds,teacher_body_sec=report['whole_sec'],
        teacher_report_sha256=source.source.public.digest(source.EVIDENCE/'teacher_report.json'),
        code_sha256={path:source.source.public.digest(ROOT/path) for path in
            ('scripts/audit_p106b_verbatim_readback.py','scripts/audit_p106b_source_layout.py')},
        models_loaded=0,gpu_used=False,semantic_quality='NOT_ASSESSED',
        scope='full original messages and roles in actual teacher JSON and explicit student ranges; no correctness promotion')
    source.source.training.write(source.EVIDENCE/'transport_readback.json',value)
    print('[VERBATIM_TRANSPORT_READBACK] '+json.dumps(value),flush=True);return 0


if __name__=='__main__':raise SystemExit(main())
