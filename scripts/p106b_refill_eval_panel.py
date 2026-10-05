"""Code-authored posthoc diagnostics; no model, data write or phrase blacklist.

Contract checks apply only to an explicit output contract, not to arbitrary
natural-language correctness. Free QA, translation and code remain manual.
"""
from __future__ import annotations
import ast
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def case(ident, axis, language, question, kind='manual', gold=None):
    return dict(id=ident, axis=axis, language=language, question=question,
                contract_kind=kind, reference=gold, scope='POSTHOC_CODE_AUTHORED_DIAGNOSTIC')


def singles():
    return [
        case('k_ko1','knowledge','ko','물이 얼면 무엇이 되나요? 한 문장으로 설명하세요.',gold='얼음이 됩니다.'),
        case('k_ko2','knowledge','ko','RAM과 SSD는 전원이 꺼졌을 때 어떤 차이가 있나요?',gold='RAM은 휘발성이며 SSD는 비휘발성 저장 장치이다.'),
        case('k_en1','knowledge','en','Which planet is home to human beings? Answer in one short sentence.',gold='Earth.'),
        case('k_en2','knowledge','en','Why do people add a day in a leap year? Give a short beginner explanation.',gold='To keep the calendar aligned with the solar year.'),
        case('c_ko1','context','ko','주어진 기록: 솔 회의실=301, 달 회의실=204. 달 회의실 번호만 숫자로 쓰세요.','literal','204'),
        case('c_ko2','context','ko','민수의 공=파랑, 지수의 공=빨강. 민수가 고른 색만 주어진 표현 그대로 쓰세요.','literal','파랑'),
        case('c_en1','context','en','Records: oak room=703, pine room=508. Write the pine room number only.','literal','508'),
        case('c_en2','context','en','Maple box is green; cedar box is red. Write the maple color only.','literal','green'),
        case('l_ko1','logic_math','ko','17 더하기 25의 값만 숫자로 답하세요.','literal','42'),
        case('l_ko2','logic_math','ko','가정: 모든 빨간 상자는 무겁다. 이 상자는 빨갛다. 이 상자가 무겁다는 결론이 따르나요? 예 또는 아니오만 쓰세요.','literal','예'),
        case('l_en1','logic_math','en','What is 23 minus 8? Write one integer only.','literal','15'),
        case('l_en2','logic_math','en','Assume all blue boxes are light. This box is blue. Does it follow that it is light? Write yes or no only.','literal','yes'),
        case('f_ko1','format','ko','result 키 하나와 정수 값 5만 가진 JSON 객체만 출력하세요.','json',{'result':5}),
        case('f_ko2','format','ko','사과와 배라는 두 단어만 이 순서로 쉼표로 구분해서 쓰세요.','literal','사과,배'),
        case('f_en1','format','en','Return only JSON containing exactly status="ok" and count=2 (integer).','json',{'status':'ok','count':2}),
        case('f_en2','format','en','Write exactly red,blue with no other text.','literal','red,blue'),
        case('p_ko1','code','ko','Python 코드 x=3; print(x*2+1)의 출력값만 숫자로 쓰세요.','literal','7'),
        case('p_ko2','code','ko','정수 n에 대해 1부터 n까지의 합을 반환하는 Python 함수 sum_to(n)를 작성하세요. 함수 코드만 쓰세요.','python_manual','def sum_to(n):\n    return n*(n+1)//2'),
        case('p_en1','code','en','For Python a=[2,4,6]; print(a[1]), write only the printed number.','literal','4'),
        case('p_en2','code','en','Write a Python function is_even(n) that returns whether an integer n is even. Output code only.','python_manual','def is_even(n):\n    return n % 2 == 0'),
        case('e_ko1','language','ko','Translate into Korean: I left the book on the table.','manual','나는 책을 탁자 위에 두었다.'),
        case('e_ko2','language','ko','친구에게 쓰는 "창문 좀 열어"를 정중한 한국어 요청 문장으로 바꾸세요.','manual','창문을 열어 주시겠어요?'),
        case('e_en1','language','en','Translate into English: 내일 도서관에서 만나요.','manual',"Let's meet at the library tomorrow."),
        case('e_en2','language','en','Make this request polite in natural English: Give me your pen.','manual','Could you lend me your pen, please?'),
    ]


def episodes():
    def steps(ident,language,rows):
        return dict(id=ident,language=language,turns=[case(f'{ident}_t{i+1}','multiturn',language,*row)
                                                  for i,row in enumerate(rows)])
    return [
        steps('travel_ko','ko',[
            ('여행 예약: 도시는 부산, 날짜는 17일, 예산은 8만원입니다. 기억했으면 기억 한 단어만 답하세요.','literal','기억'),
            ('다른 조건은 그대로 두고 예산만 12만원으로 바꿉니다. 수정 한 단어만 답하세요.','literal','수정'),
            ('현재 예약 도시와 예산을 city와 budget 키의 JSON으로만 답하세요. 예산은 원 단위 정수입니다.','json',{'city':'부산','budget':120000})]),
        steps('boxes_en','en',[
            ('Remember: maple box=green, cedar box=red. Reply only OK.','literal','OK'),
            ('Change only cedar to blue. Reply only UPDATED.','literal','UPDATED'),
            ('Return only JSON with the current maple and cedar colors.','json',{'maple':'green','cedar':'blue'})]),
        steps('secret_ko','ko',[
            ('학생 이름은 서윤이고 비밀 단어는 노을입니다. 확인 한 단어만 답하세요.','literal','확인'),
            ('이름은 그대로입니다. 비밀 단어만 별빛으로 바꿉니다. 변경 한 단어만 답하세요.','literal','변경'),
            ('학생 이름과 현재 비밀 단어를 name과 secret 키의 JSON으로만 쓰세요.','json',{'name':'서윤','secret':'별빛'})]),
        steps('schedule_en','en',[
            ('Meeting: Wednesday, room204. Remember this and reply only OK.','literal','OK'),
            ('Keep the day but change the room to305. Reply only UPDATED.','literal','UPDATED'),
            ('Return only JSON with day and room. Room must be an integer.','json',{'day':'Wednesday','room':305})]),
    ]


def panel():
    return dict(schema='P106B_REFILL_MULTITURN_PANEL_V1',singles=singles(),episodes=episodes(),
        replies_per_model=36,models=2,planned_model_calls=72,maximum_attempts=1,
        history='actual previous model replies; protocol markers escaped visibly, never corrected for meaning',
        benchmark_status='POSTHOC_DIAGNOSTIC_NOT_SEALED_BENCHMARK')


def panel_sha(value=None):
    return hashlib.sha256(json.dumps(value or panel(),ensure_ascii=False,sort_keys=True).encode()).hexdigest().upper()


def exact_types(left,right):
    if type(left) is not type(right):return False
    if isinstance(left,dict):return left.keys()==right.keys() and all(exact_types(left[k],right[k]) for k in left)
    if isinstance(left,list):return len(left)==len(right) and all(exact_types(a,b) for a,b in zip(left,right))
    return left==right


def score(value,answer):
    """Known explicit contracts only. Never execute generated code."""
    result=dict(contract_kind=value['contract_kind'],contract_pass=None,semantic_review='NOT_REVIEWED')
    text=answer.strip()
    if value['contract_kind']=='literal':result['contract_pass']=text==value['reference']
    elif value['contract_kind']=='json':
        try:result['contract_pass']=exact_types(json.loads(text),value['reference'])
        except (ValueError,TypeError):result['contract_pass']=False
    elif value['contract_kind']=='python_manual':
        code=text
        if code.startswith('```') and code.endswith('```'):
            code='\n'.join(code.splitlines()[1:-1]);result['fenced']=True
        try:ast.parse(code);result['python_syntax_valid']=bool(code)
        except (ValueError,SyntaxError):result['python_syntax_valid']=False
    return result


def history_text(text):
    """Keep all natural text. Escape only protocol delimiters to preserve role ownership."""
    from scripts.p106b_teacher_wrapper import BOUNDARY_MARKERS
    changed=[]
    for marker in BOUNDARY_MARKERS:
        if marker in text:
            text=text.replace(marker,marker.replace('<','&lt;').replace('>','&gt;'));changed.append(marker)
    return text,changed


def collect(infer, on_row=None):
    """Inject a pure inference callback for CPU fixtures; each episode resets history."""
    from tinylm.chat.serialize import serialize
    rows=[]
    def turn(value,history,episode=None,index=1):
        prompt=serialize({'messages':history+[dict(role='user',content=value['question'])]},
                         'chatml',add_generation_prompt=True)
        answer,metadata=infer(prompt,value)
        if not isinstance(answer,str):raise ValueError('inference must return text')
        rendered=answer.split('<|im_end|>',1)[0]
        row=dict(case=value,episode=episode,turn=index,prompt=prompt,raw_answer=answer,
                 rendered_answer=rendered,generation=metadata,model_call_attempted=True,
                 score=score(value,rendered),human_review='NOT_RUN')
        safe,markers=history_text(rendered);row['history_protocol_escapes']=markers
        rows.append(row)
        if on_row is not None:on_row(row)
        return safe
    for value in singles():turn(value,[])
    for episode in episodes():
        history=[]
        for index,value in enumerate(episode['turns'],1):
            text=turn(value,history,episode['id'],index)
            history.extend([dict(role='user',content=value['question']),dict(role='assistant',content=text)])
    if len(rows)!=36:raise ValueError('expected36 first-answer records per model')
    return rows


def summarize(rows):
    from collections import Counter
    groups={}
    for axis in sorted({r['case']['axis'] for r in rows}):
        subset=[r for r in rows if r['case']['axis']==axis]
        groups[axis]=dict(rows=len(subset),contract_scored=sum(r['score']['contract_pass'] is not None for r in subset),
                         contract_passed=sum(r['score']['contract_pass'] is True for r in subset),
                         manual_required=sum(r['score']['contract_pass'] is None for r in subset))
    return dict(axes=groups,finish_reasons=dict(Counter(r['generation'].get('finish_reason','NOT_RECORDED') for r in rows)),
        episode_final_contracts={r['episode']:r['score']['contract_pass'] for r in rows if r['episode'] and r['turn']==3},
        semantic_quality='NOT_REVIEWED',scope='explicit contracts are not general intelligence or all free-answer truth')
