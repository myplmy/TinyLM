"""Root-authored selection and sealed language evaluation, not a train corpus.

These common facts and deterministic problems are not official benchmark
items. Prior pretraining exposure is unknown. Paraphrases of edited facts
measure wording transfer, not new knowledge or independent fact acquisition.
"""
from collections import Counter


def row(ident, language, family, question, expected=None, **extras):
    return dict(id=ident, language=language, family=family, question=question,
                expected=expected, protected=family=='protect', **extras)


def selection(legacy):
    facts = list(dict.fromkeys(r['fact'] for r in legacy if r.get('fact')))
    result = []
    for fact in facts:
        item = next(r for r in legacy if r.get('fact')==fact and r['split']=='fit')
        subject, language = item['subject'], item['language']
        kind = ('capital' if 'capital' in fact else 'formula' if fact.startswith(('water','oxygen')) else 'orbit')
        relation = {'capital':('수도 도시 이름','capital city'),
                    'formula':('화학식','chemical formula'),
                    'orbit':('공전 중심 천체 이름','name of the body it orbits')}[kind]
        prompts = ([f"퀴즈: '{subject}'의 {relation[0]}을 적으세요. 다른 말은 생략하세요.",
                    f"확인하려는 항목은 '{subject}'의 {relation[0]}입니다. 그 값만 주세요.",
                    f"'{subject}'에 대한 질문입니다. {relation[0]}은 무엇인지 답만 적으세요.",
                    f"짧은 답을 원합니다. '{subject}'의 {relation[0]}에 해당하는 값은?"]
                   if language=='ko' else
                   [f"Quiz: give the {relation[1]} for {subject}, with no added words.",
                    f"The requested field for {subject} is its {relation[1]}. Supply just that value.",
                    f"About {subject}: what is its {relation[1]}? Only the answer, please.",
                    f"A short response is wanted: state the {relation[1]} for {subject}."])
        for i, prompt in enumerate(prompts):
            result.append(row(f'dev:target:{fact}:{i}',language,'target',prompt,item['expected'],
                              fact=fact,source_group=fact,split='select_dev'))
    stable = [
        ('캐나다의 수도는 어디인가요? 도시 이름만 답하세요.','What is the capital of Canada? City name only.','오타와','Ottawa'),
        ('호주의 수도를 도시 이름으로만 적으세요.','Give only the capital city of Australia.','캔버라','Canberra'),
        ('스페인의 수도는 어디인가요? 이름만 쓰세요.','Name only the capital of Spain.','마드리드','Madrid'),
        ('포르투갈의 수도 이름만 알려주세요.','Give just the capital city of Portugal.','리스본','Lisbon'),
        ('8과 17을 더한 값만 적으세요.','Write only the sum of 8 and 17.','25','25'),
        ('23에서 9를 뺀 답만 쓰세요.','Write only 23 minus 9.','14','14'),
        ('6 곱하기 7의 값만 적으세요.','Give only the value of 6 times 7.','42','42'),
        ('24를 3으로 나눈 값만 적으세요.','Write only 24 divided by 3.','8','8'),
        ('노아는 빨간 공, 가람은 파란 공을 가졌습니다. 가람의 공 색만 적으세요.',
         'Noa has a red ball; Garam has a blue ball. Give only the color of Garam\'s ball.','파랑','blue'),
        ('상자 A에는 배, 상자 B에는 복숭아가 있습니다. B의 내용물만 쓰세요.',
         'Box A contains a pear; box B contains a peach. Name only the contents of B.','복숭아','peach'),
        ('참 AND 거짓의 결과는? 참 또는 거짓만 쓰세요.','What is true AND false? Write true or false only.','거짓','false'),
        ('거짓 OR 참의 결과는? 참 또는 거짓만 쓰세요.','What is false OR true? Write true or false only.','참','true'),
    ]
    for i,(ko,en,ak,ae) in enumerate(stable):
        for language,question,answer in [('ko',ko,ak),('en',en,ae)]:
            result.append(row(f'dev:other:{i}:{language}',language,'other',question,answer,
                              source_group=f'dev:other:{i}',split='select_dev'))
    for i in range(12):
        for language in ('ko','en'):
            if i < 6:
                answer=f'COPY-{712+i}-ZX'
                question=(f'기호까지 보존하여 다음 문자열만 복사하세요: {answer}' if language=='ko' else
                          f'Copy only this string, retaining all punctuation: {answer}')
            elif i < 9:
                word=('라임','종이','차')[i-6] if language=='ko' else ('lime','paper','tea')[i-6]
                count=i-4;answer=' '.join([word]*count)
                question=(f"'{word}' 단어를 공백으로 구분해 {count}번만 적으세요." if language=='ko' else
                          f"Write '{word}' exactly {count} times with spaces only between words.")
            else:
                label=('ok','ready','done')[i-9]
                answer='{"answer":"'+label+'"}'
                question=(f'answer 키와 문자열 {label} 값만 가진 JSON 객체를 출력하세요. 다른 텍스트는 쓰지 마세요.'
                          if language=='ko' else f'Output only a JSON object with the key answer and string value {label}.')
            result.append(row(f'dev:protect:{i}:{language}',language,'protect',question,answer,
                              source_group=f'dev:protect:{i}',split='select_dev'))
    return result


def final_language():
    result=[]
    concepts=[('대한민국','South Korea','수도','capital','서울','Seoul'),
              ('프랑스','France','수도','capital','파리','Paris'),
              ('독일','Germany','수도','capital','베를린','Berlin'),
              ('이탈리아','Italy','수도','capital','로마','Rome'),
              ('물','water','분자 화학식','molecular formula','H2O','H2O'),
              ('산소 분자','an oxygen molecule','화학식','chemical formula','O2','O2'),
              ('지구','Earth','공전 중심 별','star at the center of its orbit','태양','Sun'),
              ('달','Moon','공전 중심 행성','planet at the center of its orbit','지구','Earth')]
    for i,(sk,se,rk,re,ak,ae) in enumerate(concepts):
        for variant in range(3):
            ko=[f"정답란에 '{sk}'의 {rk}만 써 넣는다면 무엇을 써야 하나요?",
                f"다음 항목을 채워주세요: 대상={sk}, 요청={rk}. 항목 값만 답하세요.",
                f"{sk}에 관해서 {rk}을 묻고 있습니다. 정확한 이름이나 기호만 응답하세요."][variant]
            en=[f"What belongs in the answer field for {se}'s {re}? Write only the value.",
                f"Fill this field: entity={se}; requested field={re}. Give the value only.",
                f"The question concerns {se} and asks for its {re}. Supply only the name or formula."][variant]
            for language,q,a in [('ko',ko,ak),('en',en,ae)]:
                result.append(row(f'final:target:{i}:{variant}:{language}',language,'target',q,a,
                    source_group=f'fact:{i}',scenario=f'target:{i}:{variant}',split='final_test'))
    for i in range(24):
        if i<8:
            a,b=13+i,7+2*i;answer=str(a+b)
            ko=f'두 수 {a}와 {b}를 더하세요. 계산 결과만 적으세요.'
            en=f'Add the two numbers {a} and {b}. Write the result only.'
        elif i<16:
            a,b=bool(i%2),bool((i//2)%2);operation='AND' if i<12 else 'OR'
            answer=str((a and b) if operation=='AND' else (a or b)).lower()
            ko=f'A={"참" if a else "거짓"}, B={"참" if b else "거짓"}입니다. A {operation} B의 결과만 참/거짓으로 적으세요.'
            en=f'A={str(a).lower()}; B={str(b).lower()}. Give only A {operation} B as true or false.'
        else:
            count=i+3;answer=str(count)
            ko=f'민서는 구슬 {count}개, 지후는 구슬 {count+4}개를 가졌습니다. 민서의 개수만 숫자로 적으세요.'
            en=f'Minseo has {count} marbles and Jihu has {count+4}. Give only Minseo\'s count as a number.'
        for language,q in [('ko',ko),('en',en)]:
            gold=('참' if answer=='true' else '거짓') if language=='ko' and i in range(8,16) else answer
            result.append(row(f'final:other:{i}:{language}',language,'other',q,gold,
                source_group=f'logic:{i}',scenario=f'other:{i}',split='final_test'))
    topics=[
        ('처음 읽는 사람에게 농구가 어떤 운동인지 두 문장으로 설명해주세요.','Explain basketball to a beginner in two sentences.'),
        ('사과의 생김새와 먹는 방법을 짧게 설명해주세요.','Briefly describe an apple and how it is eaten.'),
        ('비가 올 때 우산이 하는 일을 한 문장으로 설명하세요.','Explain in one sentence what an umbrella does in rain.'),
        ('도서관에서 조용히 해야 하는 이유를 설명해주세요.','Explain why people should be quiet in a library.'),
        ('친구에게 약속에 조금 늦는다고 정중하게 알려주세요.','Politely tell a friend that you will be a little late.'),
        ('버스 정류장이 어디인지 공손하게 묻는 문장을 써주세요.','Write a polite sentence asking where the bus stop is.'),
        ('뜨거운 차와 차가운 물의 차이를 온도를 중심으로 설명하세요.','Describe hot tea and cold water in terms of temperature.'),
        ('씨앗을 심은 뒤 물이 필요한 이유를 쉽게 설명해주세요.','Simply explain why a planted seed needs water.'),
        ('밤하늘의 달을 보고 느낀 점을 표현하는 짧은 문장을 써주세요.','Write a short sentence describing a feeling while looking at the Moon.'),
        ('새로 이사 온 이웃에게 할 수 있는 인사를 써주세요.','Write a greeting for a neighbor who has just moved in.'),
        ('운동 후 쉬는 시간이 왜 필요한지 일상적인 말로 설명하세요.','Explain in everyday language why rest is needed after exercise.'),
        ('지도와 달력의 쓰임새가 어떻게 다른지 설명해주세요.','Explain how a map and a calendar are used differently.'),
    ]
    for i in range(24):
        ko,en=topics[i%12]
        for language,q in [('ko',ko),('en',en)]:
            followups=[]
            if i>=12:
                q=('초등학생도 알 수 있도록 답해주세요. '+q if language=='ko' else 'Use language a child could understand. '+q)
                followups=(['이제 같은 뜻을 한 문장으로만 다시 설명해주세요.',
                            '방금 설명에서 가장 중요한 말을 한 가지 골라 그 이유도 짧게 알려주세요.']
                           if language=='ko' else
                           ['Now explain the same idea in just one sentence.',
                            'Choose one important point from your last answer and briefly say why it matters.'])
            result.append(row(f'final:open:{i}:{language}',language,'open',q,
                source_group=f'open_topic:{i%12}',scenario=f'open:{i}',split='final_test',followups=followups))
    for i in range(24):
        for language in ('ko','en'):
            if i<8:
                answer=f'NOTE_{841+i}_END'
                q=(f'출력에 다음 문자열 하나만 포함시키세요: {answer}' if language=='ko' else
                   f'Your output must consist of just this string: {answer}')
                behavior='copy'
            elif i<16:
                word=('연필','강','종','배')[i%4] if language=='ko' else ('pencil','river','bell','pear')[i%4]
                count=2+i%3;answer=' '.join([word]*count)
                q=(f"'{word}' 단어를 공백으로 구분해 정확히 {count}번 출력하세요." if language=='ko' else
                   f"Output the word '{word}' exactly {count} times, separated by single spaces.")
                behavior='requested_repeat'
            else:
                choices=[('그 건물의 입주 기관이 무엇인가요?','Which organization occupies that building?'),
                         ('그 사람이 맡았던 직책을 알려주세요.','What position did that person hold?'),
                         ('내 예약 시간을 알려주세요.','Tell me the time of my reservation.'),
                         ('그 사건은 언제 일어났나요?','When did that event happen?'),
                         ('앞서 보낸 표의 합계를 알려주세요.','Give me the sum from the table I sent earlier.'),
                         ('그 제품의 모델 번호는 무엇인가요?','What is the model number of that product?'),
                         ('우리 약속 장소를 다시 알려주세요.','Remind me where we agreed to meet.'),
                         ('그 책을 쓴 사람 이름을 알려주세요.','Name the person who wrote that book.')]
                q=choices[i-16][language=='en'];answer=None;behavior='clarify_missing_referent'
            result.append(row(f'final:protect:{i}:{language}',language,'protect',q,answer,
                source_group=f'protect:{i}',scenario=f'protect:{i}',split='final_test',expected_behavior=behavior))
    return result


def validate(dev, final, legacy):
    if len(dev)!=96 or len(final)!=192:
        raise ValueError('planned96 selection cases and192 paired final cases required')
    if Counter(r['family'] for r in dev)!=dict(target=48,other=24,protect=24):
        raise ValueError('selection axes differ')
    if Counter(r['family'] for r in final)!=dict(target=48,other=48,open=48,protect=48):
        raise ValueError('final axes differ')
    if Counter(r['language'] for r in final)!=dict(ko=96,en=96):
        raise ValueError('paired final languages differ')
    all_rows=dev+final
    if len({r['id'] for r in all_rows})!=len(all_rows) or len({r['question'] for r in all_rows})!=len(all_rows):
        raise ValueError('duplicate evaluation IDs or exact prompts')
    if {r['question'] for r in legacy}&{r['question'] for r in all_rows}:
        raise ValueError('new exact prompt is in the exposed legacy set')
    if any(r['split']!='select_dev' for r in dev) or any(r['split']!='final_test' for r in final):
        raise ValueError('selection/final roles differ')
    return dict(select_cases=96,final_cases=192,final_scenarios=len({r['scenario'] for r in final}),
                final_actual_user_turns=sum(1+len(r.get('followups',[])) for r in final),
                unknown_pretraining_overlap=True,official_benchmark_items_used=False)
