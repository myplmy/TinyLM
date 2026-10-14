"""Code-known lookup target/order factorial; read-only four saved endpoints."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import argparse
from collections import defaultdict
import json
from unittest.mock import patch
from scripts import diag_p106b_source_course as course
from scripts import diag_p106b_source_format_mix as mix
from scripts import diag_p106b_context_transfer as engine
TAG='p106b_source_binding_v1_s1337'
TARGET=ROOT/'test_result/evidence'/TAG


def cases():
    result=[]
    for language in ('ko','en'):
        for family in ('color','department'):
            values=('빨강','파랑') if language=='ko' and family=='color' else (
                ('산수과','문법과') if language=='ko' else ('red','blue') if family=='color' else ('Physics','History'))
            names=('가온','나래') if language=='ko' else ('Mina','Noah')
            prefix=('제시된 자료만 근거로 답하세요. 자료가 주어지지 않으면 자료를 요청하세요.\n자료:\n' if language=='ko' else
                    'Answer using only the supplied reference. If it is not supplied, request the reference.\nReference:\n')
            for assignment in (0,1):
                facts={names[i]:values[i^assignment] for i in (0,1)}
                for order in (0,1):
                    ordered=names if not order else names[::-1]
                    if language=='ko':
                        sentences=[f'{name}의 색상은 {facts[name]}입니다.' if family=='color' else
                                   f'{name} 건물에는 {facts[name]}가 있습니다.' for name in ordered]
                    else:
                        sentences=[f'{name} is {facts[name]}.' if family=='color' else
                                   f'The {name} building houses {facts[name]}.' for name in ordered]
                    for asked in names:
                        question=(f'{asked}의 색상은 무엇입니까?' if family=='color' else f'{asked} 건물에는 어느 학과가 있습니까?') if language=='ko' else (
                                  f'What color is {asked}?' if family=='color' else f'What department is in the {asked} building?')
                        question+=(' 색상 단어만 답하세요.' if family=='color' else ' 학과 이름만 답하세요.') if language=='ko' else (
                                   ' Reply with only the color word.' if family=='color' else ' Reply with only the department name.')
                        mark='질문:\n' if language=='ko' else 'Question:\n'
                        result.append(dict(id=f'{language}_{family}_{assignment}_{order}_{asked}',
                            root=f'{language}_{family}_{assignment}',group=language+'_'+family,language=language,
                            question=prefix+' '.join(sentences)+'\n'+mark+question,gold=facts[asked],rubric='EXACT_SCALAR',
                            requested_entity=asked,ordered_entities=list(ordered),first_value=facts[ordered[0]],
                            target_is_first=asked==ordered[0],same_fact_mapping=facts,
                            source_truth='PROJECT_AUTHORED_FICTIONAL_CODE_CONTRACT'))
    if len(result)!=32:raise ValueError('fixed32 lookup factorial')
    return result


def preflight():
    if TARGET.exists():raise FileExistsError('fresh binding diagnostic output required')
    subjects=[dict(id='parent',path=str(course.training.PARENT.relative_to(ROOT)),sha=course.training.PARENT_SHA)]
    for folder,arm,name in ((course.EVIDENCE,'sft_only','sft_only'),(course.EVIDENCE,'reference_lm','reference_lm'),(mix.EVIDENCE,'sft_only','format_mix')):
        r=json.loads((folder/(arm+'_report.json')).read_text())
        if r['updates']!=32 or course.public.digest(ROOT/r['checkpoint'])!=r['checkpoint_sha256']:
            raise ValueError('saved completed32 endpoint required')
        subjects.append(dict(id=name,path=r['checkpoint'],sha=r['checkpoint_sha256']))
    if course.public.digest(course.training.PARENT)!=course.training.PARENT_SHA:raise ValueError('parent changed')
    return subjects,dict(schema='P106B_SOURCE_BINDING_V1',subjects=subjects,case_sha256=course.support.sha(cases()),
        code_sha256={p:course.public.digest(ROOT/p) for p in ('scripts/diag_p106b_source_binding.py','scripts/diag_p106b_context_transfer.py','tinylm/infer/generate.py')},
        tokenizer_sha256=course.public.TOK_SHA,precision='FP32_MATH_NO_TF32',cache=True,mtp_tokens=1,max_new=64,
        training='NOT_RUN',checkpoint_save=False,test_scope='POSTHOC_CODE_KNOWN_LOOKUP_CAUSAL_FACTORIAL_NOT_GENERAL_BENCHMARK',
        paired_axes='same facts; target entity and sentence order changed independently; assignment reversal')


def collect(args):
    with patch.object(engine,'TARGET',TARGET),patch.object(engine,'preflight',preflight),patch.object(engine,'cases',cases):
        return engine.execute(args)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--max-wall-sec',type=int,default=600)
    g=p.add_mutually_exclusive_group(required=True);g.add_argument('--execute',action='store_true');g.add_argument('--check-only',action='store_true')
    args=p.parse_args()
    if not 60<=args.max_wall_sec<=600:p.error('bounded60..600')
    if args.check_only:print('[CHECK_ONLY] '+json.dumps(preflight()[1]));return 0
    if args.execute:return collect(args)
    p.error('explicit mode required')

if __name__=='__main__':raise SystemExit(main())
