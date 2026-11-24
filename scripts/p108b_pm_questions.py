"""Fresh, closed-answer and open-language evaluation inputs; no training role."""
import json


def build():
    rows=[]
    facts=[('korea',('한국의 수도','서울'),('the capital of South Korea','Seoul')),
           ('france',('프랑스의 수도','파리'),('the capital of France','Paris')),
           ('water',('물의 화학식','H2O'),('the chemical formula of water','H2O')),
           ('earth',('지구가 공전하는 별','태양'),('the star that Earth orbits','Sun')),
           ('germany',('독일의 수도','베를린'),('the capital of Germany','Berlin')),
           ('italy',('이탈리아의 수도','로마'),('the capital of Italy','Rome')),
           ('oxygen',('산소 분자의 화학식','O2'),('the formula of an oxygen molecule','O2')),
           ('moon',('달이 공전하는 행성','지구'),('the planet that the Moon orbits','Earth'))]
    for language in ('ko','en'):
        def add(family,ident,question,expected=None,**extra):
            rows.append(dict(id=f'pm:{language}:{ident}',language=language,family=family,
                split='pm_frozen_final',question=question,expected=expected,protected=family=='protect',
                origin='ROOT_AUTHORED_EVALUATION_ONLY',**extra))
        for fact,ko,en in facts:
            relation,answer=ko if language=='ko' else en
            questions=([f'퀴즈입니다. {relation}에 해당하는 답 하나만 적어 주세요.',
                        f'빈칸 하나를 채우세요: {relation} = ___. 답만 적으세요.'] if language=='ko' else
                       [f'A short quiz: identify {relation}. Write just the answer.',
                        f'Fill one blank: {relation} = ___. Answer only.'])
            for j,q in enumerate(questions):
                add('target',f'{fact}:{j}',q,answer,fact_group=fact,
                    same_fact_in_edit_fit=language=='ko' or fact in {'germany','italy','oxygen','moon'})
        for i,(a,b) in enumerate(((3,6),(8,7),(12,4),(9,5),(4,11),(7,9),(13,6),(8,14))):
            q=(f'새 계산 카드 {i+1}: {a}에 {b}를 더한 결과를 숫자 하나로만 답하세요.' if language=='ko' else
               f'New calculation card {i+1}: add {a} and {b}. Reply with just one number.')
            add('other',f'add:{i}',q,str(a+b),proof=dict(operation='add',left=a,right=b))
        for i in range(8):
            q=(f'보관함 기록 {i+1}: 다온은 연필 {i+2}개, 서준은 연필 {i+11}개를 갖고 있습니다. 서준의 연필 수만 숫자로 답하세요.' if language=='ko' else
               f'Inventory record {i+1}: Dana has {i+2} pencils and Alex has {i+11} pencils. Give only the number of pencils Alex has.')
            add('other',f'role:{i}',q,str(i+11),proof=dict(selected_person='서준' if language=='ko' else 'Alex',value=i+11))
        for i,token in enumerate(('라온','나침반','파란상자','Q7Z','M42','벚나무') if language=='ko' else
                                 ('otter','compass','bluebox','Q7Z','M42','birch')):
            q=(f'검사표 {i+1}의 문자열 [{token}]에서 대괄호 안 글자만 정확히 옮겨 적으세요.' if language=='ko' else
               f'For copy card {i+1}, copy exactly the characters inside these brackets: [{token}].')
            add('protect',f'copy:{i}',q,token,protect_kind='copy')
        for i,token in enumerate(('솔','밤','별','눈') if language=='ko' else ('oak','bay','elm','ash')):
            q=(f'정상 반복 요청 {i+1}: 단어 "{token}"를 공백 하나로 구분해 세 번만 쓰세요.' if language=='ko' else
               f'Intentional repetition request {i+1}: write "{token}" exactly three times, separated by single spaces.')
            add('protect',f'repeat:{i}',q,' '.join([token]*3),protect_kind='requested_repetition',allow_repeat=True)
        for i,value in enumerate(('ready','done')):
            q=(f'기계 입력 {i+1}: status 항목의 값이 "{value}"인 JSON 객체 하나만 출력하세요. 다른 항목이나 설명은 쓰지 마세요.' if language=='ko' else
               f'Machine input {i+1}: output only a JSON object with one key "status" whose value is "{value}". No other keys or explanation.')
            add('protect',f'json:{i}',q,json.dumps(dict(status=value),separators=(',',':')),protect_kind='json')
        missing_ko=['방금 언급한 그곳까지 얼마나 걸리나요?','그 사람의 생일이 언제인지 알려 주세요.',
                    '그 물건의 가격을 지금 알려 주세요.','이전에 말한 건물의 이름을 적어 주세요.']
        missing_en=['How long does it take to get to the place just mentioned?',"What is that person's birthday?",
                    'Tell me the price of that item now.','Name the building mentioned earlier.']
        for i,q in enumerate(missing_ko if language=='ko' else missing_en):
            add('protect',f'missing:{i}',q,protect_kind='missing_referent',requires_clarification=True)
        topics=[('안녕하세요. 처음 만난 사람에게 짧게 인사해 주세요.','Hello. Give a short greeting to someone you just met.'),
            ('농구가 어떤 운동인지 처음 듣는 사람에게 두 문장으로 소개해 주세요.','Introduce basketball in two sentences to someone new to it.'),
            ('사과라는 과일을 모르는 사람에게 쉽게 설명해 주세요.','Explain what an apple is to someone unfamiliar with the fruit.'),
            ('비가 올 때 우산이 도움이 되는 이유를 설명해 주세요.','Explain why an umbrella is useful when it rains.'),
            ('책을 읽고 내용을 짧게 요약한다는 것이 무엇인지 설명해 주세요.','Explain what it means to summarize a book briefly.'),
            ('씨앗을 흙에 심은 뒤 식물이 자라려면 보통 무엇이 필요한가요?','What does a seed planted in soil usually need to grow?'),
            ('친구가 준 작은 선물에 고마움을 전하는 말을 써 주세요.','Write a brief thank-you message for a small gift from a friend.'),
            ('공원에서 쓰레기를 주워야 하는 이유를 쉽게 말해 주세요.','Explain simply why people should pick up litter in a park.'),
            ('자전거와 버스가 이동 수단이라는 공통점을 한 문장으로 설명해 주세요.','Explain in one sentence what bicycles and buses have in common.'),
            ('연필로 쓴 글을 지우개로 지울 수 있다는 내용을 자연스러운 문장으로 써 주세요.','Write a natural sentence explaining that an eraser can remove pencil marks.'),
            ('주어진 글을 한 문장으로 요약해 주세요: 민지는 아침에 도서관에 갔다. 책을 빌리고 집으로 돌아왔다.',
             'Summarize in one sentence: Mina went to the library in the morning. She borrowed a book and returned home.'),
            ('마음에 드는 음악을 들을 때 느낄 수 있는 기분을 두 문장으로 표현해 주세요.','Describe in two sentences how someone might feel while listening to music they enjoy.'),
            ('종이컵 두 개를 탁자 위에 놓는 간단한 지시문을 써 주세요.','Write a simple instruction to put two paper cups on a table.'),
            ('친구에게 내일 공원에서 만나자고 정중하게 제안해 주세요.','Politely suggest meeting a friend in the park tomorrow.'),
            ('뜨거운 컵과 차가운 컵이 온도에서 어떻게 다른지 쉽게 설명해 주세요.','Explain simply how a hot cup and a cold cup differ in temperature.'),
            ('사용자가 긴 설명 대신 짧은 답을 원할 때 어떻게 답하면 좋을까요?','How should you respond when someone asks for a short answer instead of a long explanation?')]
        for i,pair in enumerate(topics):
            follow=(['같은 내용을 더 쉬운 말로 한 문장으로 다시 설명해 주세요.'] if language=='ko' else
                    ['Restate the same idea in one simpler sentence.']) if i<8 else []
            add('open',f'open:{i}',pair[0 if language=='ko' else 1],followups=follow)
    return dict(schema='P108B_PM_FRESH_FINAL128_V1',role='FINAL_ONLY_NEVER_FIT_OR_SELECT',
        initial_inputs=128,actual_model_utterances=144,strict_expected=88,rows=rows,
        facts_are_not_independent_new_knowledge=True,prior_pretraining_overlap='UNKNOWN')


def validate(data,old_questions):
    rows=data['rows'];ids=[r['id'] for r in rows];questions=[r['question'] for r in rows]
    if len(rows)!=128 or len(set(ids))!=128 or len(set(questions))!=128:
        raise ValueError('exact128 distinct initial inputs required')
    if set(questions)&set(old_questions):raise ValueError('old FIT/DEV/FINAL question reused')
    if sum(r['expected'] is not None for r in rows)!=88:raise ValueError('strict denominator88 required')
    if sum(1+len(r.get('followups',[])) for r in rows)!=144:raise ValueError('exact144 actual turns required')
    for language in ('ko','en'):
        selected=[r for r in rows if r['language']==language]
        if len(selected)!=64 or any(sum(r['family']==f for r in selected)!=16 for f in ('target','other','protect','open')):
            raise ValueError('balanced64 input language panel required')
    return True
