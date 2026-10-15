#!/usr/bin/env python3
"""Offline character-coverage audit of completed v2 source transport, no meaning filter."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import argparse
from collections import Counter
import hashlib
import json
from scripts import diag_p106b_source_expand as source
from scripts.p106b_shards import verify


def assess(original,traces,teacher_units,student_text):
    by_id={u['id']:u for u in teacher_units}
    if set(by_id)!={t['id'] for t in traces}:raise ValueError('actual teacher payload/trace IDs differ')
    covered=[set() for _ in original['messages']]
    for span in traces:
        actual=source.source.support.text(original['messages'][span['source_message_index']])
        if actual[span['start']:span['end']]!=span['text']:raise ValueError('trace is not original slice')
        if by_id[span['id']]['text']!=span['text']:raise ValueError('actual teacher payload text differs from trace')
        covered[span['source_message_index']].update(range(span['start'],span['end']))
    counts=Counter();indent_missing=0;full=True
    for index,message in enumerate(original['messages']):
        text=source.source.support.text(message)
        counts['original_characters']+=len(text)
        counts['uncovered_nonwhitespace']+=sum(i not in covered[index] and not c.isspace() for i,c in enumerate(text))
        counts['uncovered_whitespace']+=sum(i not in covered[index] and c.isspace() for i,c in enumerate(text))
        position=0
        for line in text.splitlines(keepends=True):
            body=line.rstrip('\r\n');leading=len(body)-len(body.lstrip(' \t'))
            if body.strip() and leading:
                counts['original_indented_lines']+=1
                indent_missing+=sum(i not in covered[index] for i in range(position,position+leading))
            position+=len(line)
        full=full and text in student_text
        if message['role']=='system' and not covered[index]:counts['omitted_system_messages']+=1
    counts.update(missing_leading_indent_characters=indent_missing,student_has_all_complete_message_texts=int(full))
    return dict(counts)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--execute',action='store_true',required=True)
    args=p.parse_args()
    if not args.execute:p.error('explicit completed-source audit required')
    path=source.EVIDENCE/'layout_audit.json'
    if path.exists():raise FileExistsError('old audit preserved')
    r=json.loads((source.OUTPUT/'teacher/report.json').read_text())
    if r['status']!='TEACHER_COURSE_COMPLETE':raise ValueError('completed old v2 only')
    verify(source.OUTPUT/'teacher',r['raw_manifest']);totals=Counter();cases=[];rows=0
    for record in source.source.public.stream_rows(source.OUTPUT/'teacher',r['raw_manifest']):
        candidate=record.get('candidate')
        if candidate is None:continue
        units=json.loads(record['payload']['messages'][1]['content'])['public_source_spans']
        result=assess(record['item']['source'],candidate['meta']['source_reference_trace'],units,
            source.source.support.text(candidate['messages'][0]))
        totals.update(result);rows+=1
        totals['rows_with_missing_indentation']+=int(result['missing_leading_indent_characters']>0)
        if result['missing_leading_indent_characters'] and len(cases)<12:
            cases.append(dict(root=record['item']['root'],language=record['item']['language'],
                family=record['item']['family'],counts=result))
    if rows!=576:raise ValueError('all accepted old source records required')
    output=dict(schema='P106B_COMPLETED_SOURCE_LAYOUT_AUDIT_V1',rows=rows,counts=dict(totals),examples_without_text=cases,
        teacher_report_sha256=source.source.public.digest(source.OUTPUT/'teacher/report.json'),
        raw_manifest=r['raw_manifest'],code_sha256=source.source.public.digest(Path(__file__)),
        models_loaded=0,gpu_used=False,semantic_quality='NOT_ASSESSED',
        scope='actual teacher JSON text and student transport coverage; indentation loss is not an all-content quality classifier')
    source.source.training.write(path,output)
    print('[SOURCE_LAYOUT_AUDIT] '+json.dumps(dict(rows=rows,counts=dict(totals))),flush=True)
    return 0


if __name__=='__main__':raise SystemExit(main())
