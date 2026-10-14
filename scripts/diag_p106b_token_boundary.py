"""CPU audit of first-answer supervision and train/inference token prefixes."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import argparse
from collections import Counter,defaultdict
import json
from scripts import diag_p106b_retention_course as course
from tinylm.chat.serialize import serialize,loss_spans
from tinylm.data.sft import mask_detail


def analyze(row,tok):
    detail=mask_detail(row,tok);spans=loss_spans(row,'chatml');results=[];index=0
    for j,message in enumerate(row['messages']):
        if message['role']!='assistant':continue
        start,end=spans[index];index+=1
        body=''.join(b['text'] for b in message['content'])
        prompt=serialize(dict(messages=row['messages'][:j]),'chatml',add_generation_prompt=True)
        ids=tok.encode(prompt).ids
        if not detail['text'].startswith(prompt):raise ValueError('serialized prompt differs')
        covered=set()
        for (a,b),keep in zip(detail['offsets'],detail['keep']):
            if keep:covered.update(range(max(a,start),min(b,start+len(body))))
        meaningful={start+i for i,c in enumerate(body) if not c.isspace()}
        results.append(dict(prefix_equal=ids==detail['ids'][:len(ids)],
            body_characters=len(meaningful),uncovered_body_characters=len(meaningful-covered),
            targets=sum(keep and a>=start and b<=end for (a,b),keep in zip(detail['offsets'],detail['keep']))))
    return results


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--execute',action='store_true');group.add_argument('--check-only',action='store_true')
    args=parser.parse_args()
    if args.check_only:print('[CHECK_ONLY] CPU token boundaries; no model/source opened');return 0
    target=course.EVIDENCE/'token_boundary_audit.json'
    if target.exists():raise FileExistsError('audit immutable')
    from tokenizers import Tokenizer
    tok=Tokenizer.from_file(str(course.training.data.TOKENIZER))
    report,rows=course.read_course();counts=defaultdict(Counter);failures=[]
    for split,values in rows.items():
        for row in values:
            kind=row['meta']['kind'];key=split+':'+kind
            for result in analyze(row,tok):
                counts[key].update(turns=1,prefix_mismatch=int(not result['prefix_equal']),
                    uncovered_body_characters=result['uncovered_body_characters'],
                    body_characters=result['body_characters'],targets=result['targets'])
                if not result['prefix_equal'] or result['uncovered_body_characters']:
                    failures.append(dict(split=split,kind=kind,root=row['meta']['semantic_root_id'],**result))
    output=dict(schema='P106B_FIRST_TARGET_TOKEN_BOUNDARY_V1',counts={k:dict(v) for k,v in counts.items()},
        failures=failures,model_runs=0,optimizer_updates=0,source_modified=False,
        code_sha256=course.training.data.digest(Path(__file__)),
        corpus_sha256=course.training.data.digest(course.CORPUS/'report.json'),
        scope='CPU tokenizer/mask parity only; neither model gradients nor semantic correctness')
    course.training.write(target,output)
    print('[TOKEN_BOUNDARY_AUDIT] '+json.dumps(dict(turns=sum(v['turns'] for v in counts.values()),
        failures=len(failures),model_runs=0)))
    return 8 if failures else 0


if __name__=='__main__':raise SystemExit(main())
