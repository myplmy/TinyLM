#!/usr/bin/env python3
"""Write-once local question/answer comparison; never interactive or a truth judge."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import argparse
import hashlib
import json
from scripts.p106b_shards import verify
from scripts.summarize_p106b_learning_pair import key

TAGS=('p106b_binding_aux_v1_s1337','p106b_binding_scale_v1_s1337')


def indented(text):return '\n'.join('    '+line for line in text.splitlines())+'\n'


def render(sections):
    parts=['# 저장된 실제 질문과 모델별 첫 답 비교\n',
        '모델 재실행·정답 심사·학습자료 수정은 하지 않았습니다. 코드 정답과 미검증 교사답을 구분합니다.\n']
    for label,arms in sections.items():
        reference=next(iter(arms.values()));indices={arm:{key(r):r for r in rows} for arm,rows in arms.items()}
        if any(len(i)!=len(reference) or set(i)!=set(next(iter(indices.values()))) for i in indices.values()):
            raise ValueError('identical unique question sets required')
        parts.append('\n## '+('코드가 정답을 계산한640문항' if label=='code' else '공개 개발16문항 — 교사 target 정답성 미검증')+'\n')
        for number,row in enumerate(reference,1):
            parts.append(f'\n### {number}. {row["meta"]["language"]} / {row["meta"]["kind"]}\n')
            parts.append('질문과 앞 문맥:\n')
            for message in row['messages']:
                parts.append(message['role']+':\n')
                content=message['content'];text=content if isinstance(content,str) else '\n'.join(b['text'] for b in content)
                parts.append(indented(text))
            parts.append(('코드 정답:\n' if label=='code' else '교사 target — 정답 확정 아님:\n')+indented(row['gold']))
            for arm,index in indices.items():
                actual=index[key(row)]
                if actual['gold']!=row['gold']:raise ValueError('same question/gold prerequisite')
                parts.append(arm+' 실제 첫 답 / 종료 '+str(actual['generation']['finish_reason'])+':\n'+indented(actual['answer']))
    return '\n'.join(parts)


def load_rows(value):
    directory=ROOT/value['raw_directory'];manifest=value['raw_manifest'];verify(directory,manifest)
    return [json.loads(line) for spec in manifest['shards'] for line in (directory/spec['path']).read_text().splitlines()]


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--tag',choices=TAGS,required=True)
    parser.add_argument('--execute',action='store_true',required=True);args=parser.parse_args()
    if not args.execute:parser.error('explicit local write required')
    source=ROOT/'test_result/evidence'/args.tag/'fresh_test/report.json';report=json.loads(source.read_text())
    if report['status']!='AUXILIARY_FRESH_TEST_COLLECTED':raise ValueError('completed actual collection required')
    sections=dict(code={arm:load_rows(v) for arm,v in report['arms'].items()},
        public={arm:load_rows(v) for arm,v in report['public_qa'].items()})
    if any(len(rows)!=count for label,count in (('code',640),('public',16)) for rows in sections[label].values()):
        raise ValueError('complete code640/public16 required')
    body=render(sections).encode('utf-8')
    if len(body)>=20_000_000:raise ValueError('20MB local review limit')
    target=ROOT/'test_result/evidence/local'/args.tag/'review/paired_answers.md'
    output=source.parent/'answer_view_receipt.json'
    if target.exists() or output.exists():raise FileExistsError('previous answer view/receipt preserved')
    if any(p.is_symlink() for p in (target,output,*target.parents)):
        raise ValueError('local answer view may not follow symlinks')
    target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('xb') as stream:stream.write(body)
    receipt=dict(schema='P106B_LOCAL_ANSWER_VIEW_RECEIPT_V1',tag=args.tag,path=str(target.relative_to(ROOT)),
        bytes=len(body),sha256=hashlib.sha256(body).hexdigest().upper(),source=str(source.relative_to(ROOT)),
        source_sha256=hashlib.sha256(source.read_bytes()).hexdigest().upper(),
        code_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest().upper(),
        sections={label:{arm:len(rows) for arm,rows in values.items()} for label,values in sections.items()},
        models_loaded=0,gpu_used=False,raw_modified=False,semantic_truth='NOT_ASSESSED',stage_full_view=False)
    with output.open('x',encoding='utf-8') as stream:stream.write(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
    for language in ('ko','en'):
        row=next(r for r in next(iter(sections['code'].values())) if r['meta']['language']==language)
        sample=dict(language=language,question=row['messages'],gold=row['gold'],
            actual_answers={arm:next(r['answer'] for r in values if key(r)==key(row)) for arm,values in sections['code'].items()})
        print('[ACTUAL_CODE_ANSWERS] '+json.dumps(sample,ensure_ascii=False),flush=True)
    print('[ANSWER_VIEW_RECEIPT] '+json.dumps(receipt,ensure_ascii=False),flush=True);return 0


if __name__=='__main__':raise SystemExit(main())
